"""Generic native BIM double-door factory for FacilArquitecturaWB.

Descripcion: crea una puerta Arch Window de dos hojas, con perfiles, paneles y
vidrios definidos mediante WindowParts.
Objetivo: reutilizar la puerta validada en Puriscal como herramienta generica,
con Placement real y alojamiento opcional en un muro BIM.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-27 17:24 UTC-06:00.
Version: 0.2.0.
"""

from __future__ import annotations

import math

import FreeCAD
import Part

from .bim_structure_utils import add_to_level, is_level, tag_target_level
from .bim_utils import make_arch_window
from .command_errors import UserFacingError
from .opening_utils import project_point_to_line, segment_length, wall_source_segments
from .project_structure import set_prop

try:
    import Arch
except Exception:  # pragma: no cover - depende del runtime de FreeCAD
    Arch = None


GENERATOR = "FA_InsertDoubleDoorBIM"
SPEC_ID = "architecture.door.double_leaf.glazed.europa"
MATERIAL_SET_ID = "architecture.materialset.door.double_leaf.europa"
DEFAULTS = {
    "width_mm": 2000.0,
    "height_mm": 2100.0,
    "outer_frame_mm": 50.0,
    "leaf_gap_mm": 10.0,
    "leaf_frame_mm": 50.0,
    "rail_thickness_mm": 40.0,
    "lower_protection_top_mm": 460.0,
    "second_rail_level_mm": 1000.0,
    "glass_thickness_mm": 6.0,
}
MATERIAL_SPECS = (
    (
        "architecture.material.aluminum.gray_satin",
        "Aluminio gris satinado",
        (0.62, 0.64, 0.66),
        0,
    ),
    (
        "architecture.material.panel.gray",
        "Panel inferior gris",
        (0.38, 0.40, 0.42),
        0,
    ),
    (
        "architecture.material.glass.laminated.6mm",
        "Vidrio laminado 6 mm",
        (0.42, 0.72, 0.90),
        70,
    ),
)
CUT_VOLUME_TOLERANCE_MM3 = 1.0


def normalized_parameters(values=None):
    """Return a validated numeric parameter dictionary."""
    result = dict(DEFAULTS)
    result.update(dict(values or {}))
    for name in tuple(result):
        try:
            result[name] = float(result[name])
        except Exception as exc:
            raise UserFacingError("Parametro invalido para puerta doble: %s" % name) from exc
    _validate_parameters(result)
    return result


def create_double_door_bim(
    doc,
    placement=None,
    host=None,
    target_container=None,
    parameters=None,
    opening=0.0,
    label="Puerta doble BIM - Europa",
    host_context=None,
):
    """Create one native Arch door and return ``(door, profile)``.

    The profile remains local and hidden. The semantic door owns the insertion
    Placement, so a hosted object can be moved or restored by FreeCAD without
    baking global coordinates into the source geometry.
    """
    if doc is None:
        raise UserFacingError("No hay documento activo para insertar la puerta doble BIM.")
    if FreeCAD.ActiveDocument is not doc:
        raise UserFacingError("El documento destino debe estar activo durante la insercion BIM.")
    params = normalized_parameters(parameters)
    insertion = FreeCAD.Placement(placement) if placement is not None else FreeCAD.Placement()
    opening_value = int(round(max(0.0, min(100.0, float(opening)))))

    profile = doc.addObject("Part::Feature", "FA_DoubleDoorProfile")
    profile.Label = "Perfil base - puerta doble BIM"
    profile.Shape = build_profile_shape(params)
    _tag_profile(profile)
    doc.recompute()

    door = make_arch_window(
        baseobj=profile,
        width=params["width_mm"],
        height=params["height_mm"],
        parts=build_window_parts(params),
        name="Puerta doble BIM Europa",
    )
    if door is None:
        raise UserFacingError("Arch.makeWindow no pudo crear la puerta doble BIM.")
    door.Label = str(label or "Puerta doble BIM - Europa")
    door.IfcType = "Door"
    door.Width = params["width_mm"]
    door.Height = params["height_mm"]
    door.Normal = FreeCAD.Vector(0.0, -1.0, 0.0)
    door.Placement = insertion
    door.Opening = opening_value
    door.SymbolPlan = True
    if hasattr(door, "SymbolElevation"):
        door.SymbolElevation = True
    door.HoleWire = 1
    door.HoleDepth = 0
    door.Material = ensure_material_definition(doc)
    if hasattr(door, "MoveWithHost"):
        door.MoveWithHost = bool(host is not None)
    door.Hosts = [host] if host is not None else []
    _tag_door(door, profile, host, params, host_context=host_context)
    _add_to_container(target_container, profile, hosted=host is not None, is_base=True)
    _add_to_container(target_container, door, hosted=host is not None, is_base=False)
    doc.recompute()

    if FreeCAD.GuiUp:
        profile.ViewObject.Visibility = False
        door.ViewObject.LineColor = (0.18, 0.18, 0.18)
        import ArchWindow

        ArchWindow.recolorize(door)
    return door, profile


def placement_for_wall(wall, width_mm, picked_point=None):
    """Return a centered/clamped door Placement on a selected BIM wall."""
    return host_insertion_for_wall(wall, width_mm, picked_point)["placement"]


def host_insertion_for_wall(wall, width_mm, picked_point=None):
    """Return placement and wall-segment evidence for a hosted insertion."""
    records = list(wall_source_segments(wall) or [])
    if not records:
        raise UserFacingError("El muro seleccionado no tiene un eje Base utilizable.")
    point = _vector_values(picked_point) if picked_point is not None else None
    if point is None:
        record = max(records, key=lambda item: segment_length(item["segment"]))
        segment = record["segment"]
        center = (
            (segment[0] + segment[3]) * 0.5,
            (segment[1] + segment[4]) * 0.5,
            (segment[2] + segment[5]) * 0.5,
        )
    else:
        scored = []
        for item in records:
            distance, projected, parameter = project_point_to_line(point, item["segment"])
            segment = item["segment"]
            finite_parameter = max(0.0, min(1.0, float(parameter)))
            finite_projected = (
                segment[0] + finite_parameter * (segment[3] - segment[0]),
                segment[1] + finite_parameter * (segment[4] - segment[1]),
                segment[2] + finite_parameter * (segment[5] - segment[2]),
            )
            finite_distance = math.hypot(
                point[0] - finite_projected[0], point[1] - finite_projected[1]
            )
            scored.append((finite_distance, item, finite_projected, finite_parameter))
        _distance, record, center, parameter = min(scored, key=lambda item: item[0])
        segment = record["segment"]
        length = segment_length(segment)
        if length <= 1e-9:
            raise UserFacingError("El eje del muro seleccionado tiene longitud nula.")
        half_ratio = float(width_mm) * 0.5 / length
        parameter = max(half_ratio, min(1.0 - half_ratio, float(parameter)))
        center = (
            segment[0] + parameter * (segment[3] - segment[0]),
            segment[1] + parameter * (segment[4] - segment[1]),
            segment[2] + parameter * (segment[5] - segment[2]),
        )
    length = segment_length(segment)
    if length + 1e-6 < float(width_mm):
        raise UserFacingError(
            "La puerta de %.1f mm no cabe en el tramo de muro de %.1f mm."
            % (float(width_mm), length)
        )
    dx = float(segment[3] - segment[0])
    dy = float(segment[4] - segment[1])
    angle = math.degrees(math.atan2(dy, dx))
    base_z = _wall_base_z(wall, center[2])
    normal = (-dy / length, dx / length, 0.0)
    placement = FreeCAD.Placement(
        FreeCAD.Vector(float(center[0]), float(center[1]), base_z),
        FreeCAD.Rotation(FreeCAD.Vector(0.0, 0.0, 1.0), angle),
    )
    return {
        "placement": placement,
        "segment": tuple(float(value) for value in segment),
        "segment_index": int(record.get("index", -1)),
        "normal": normal,
        "base_z": base_z,
        "wall_width_mm": _wall_width(wall),
        "wall_height_mm": _wall_height(wall),
        "picked_point": point,
    }


def validate_host_opening(door, wall, wall_shape_before=None, host_context=None):
    """Confirm a native BIM opening without using the visible door Shape."""
    if door is None or wall is None:
        raise UserFacingError("Faltan la puerta o el muro para validar el alojamiento.")
    if wall not in list(getattr(door, "Hosts", []) or []):
        raise UserFacingError("La puerta doble no conservo el muro en Hosts.")
    if not bool(getattr(door, "MoveWithHost", False)):
        raise UserFacingError("La puerta doble no activo MoveWithHost.")
    reference_shape = wall_shape_before
    if reference_shape is None:
        reference_shape = getattr(wall, "Shape", None)
    try:
        subvolume = door.Proxy.getSubVolume(door, host=wall)
        if subvolume is None or subvolume.isNull():
            raise ValueError("ArchWindow no produjo Subvolume")
        intersection_before = float(reference_shape.common(subvolume).Volume)
        intersection_after = float(wall.Shape.common(subvolume).Volume)
    except Exception as exc:
        raise UserFacingError("No fue posible calcular el hueco de la puerta doble.") from exc
    removed_volume = max(0.0, intersection_before - intersection_after)
    nominal_overlap = 0.0
    if host_context:
        try:
            support = _nominal_wall_support(host_context)
            nominal_overlap = float(support.common(subvolume).Volume)
        except Exception:
            nominal_overlap = 0.0

    if intersection_before > CUT_VOLUME_TOLERANCE_MM3:
        if removed_volume <= CUT_VOLUME_TOLERANCE_MM3:
            raise UserFacingError(
                "El volumen BIM de la puerta intersecta el muro, pero el host no lo recorto."
            )
        cut_status = "new_bim_cut"
        confirmed_volume = removed_volume
    else:
        if nominal_overlap <= CUT_VOLUME_TOLERANCE_MM3:
            raise UserFacingError(
                "El volumen BIM de la puerta no coincide con el tramo del muro seleccionado."
            )
        cut_status = "preexisting_opening"
        confirmed_volume = 0.0

    set_prop(
        door,
        "App::PropertyFloat",
        "FA_CutVolume_mm3",
        "FacilArquitectura",
        "Volumen de muro intersectado durante validacion",
        confirmed_volume,
    )
    set_prop(
        door,
        "App::PropertyString",
        "FA_CutStatus",
        "FacilArquitectura",
        "Estado del hueco BIM",
        cut_status,
    )
    for name, description, value in (
        ("FA_HoleIntersectionBefore_mm3", "Interseccion antes del corte", intersection_before),
        ("FA_HoleIntersectionAfter_mm3", "Interseccion despues del corte", intersection_after),
        ("FA_NominalWallOverlap_mm3", "Interseccion con soporte nominal", nominal_overlap),
    ):
        set_prop(
            door,
            "App::PropertyFloat",
            name,
            "FacilArquitectura",
            description,
            value,
        )
    return {
        "cut_status": cut_status,
        "cut_volume_mm3": confirmed_volume,
        "intersection_before_mm3": intersection_before,
        "intersection_after_mm3": intersection_after,
        "nominal_overlap_mm3": nominal_overlap,
        "subvolume": subvolume,
    }


def validate_host_intersection(door, wall, wall_shape_before=None, host_context=None):
    """Compatibility wrapper returning the confirmed new cut volume."""
    result = validate_host_opening(
        door,
        wall,
        wall_shape_before=wall_shape_before,
        host_context=host_context,
    )
    return result["cut_volume_mm3"]


def build_profile_shape(parameters=None):
    """Build the 16 closed local XZ wires used by the Arch Window."""
    p = normalized_parameters(parameters)
    width = p["width_mm"]
    height = p["height_mm"]
    outer = p["outer_frame_mm"]
    gap = p["leaf_gap_mm"]
    leaf_frame = p["leaf_frame_mm"]
    rail = p["rail_thickness_mm"]
    lower = p["lower_protection_top_mm"]
    second = p["second_rail_level_mm"]

    half_width = width * 0.5
    half_gap = gap * 0.5
    leaf_bottom = outer
    leaf_top = height - outer
    left_outer_x0 = -half_width + outer
    left_outer_x1 = -half_gap
    right_outer_x0 = half_gap
    right_outer_x1 = half_width - outer
    left_inner_x0 = left_outer_x0 + leaf_frame
    left_inner_x1 = left_outer_x1 - leaf_frame
    right_inner_x0 = right_outer_x0 + leaf_frame
    right_inner_x1 = right_outer_x1 - leaf_frame
    inner_bottom = leaf_bottom + leaf_frame
    inner_top = leaf_top - leaf_frame
    rail1_z0 = lower - rail * 0.5
    rail1_z1 = lower + rail * 0.5
    rail2_z0 = second - rail * 0.5
    rail2_z1 = second + rail * 0.5

    wires = [
        _rectangle_wire(-half_width, 0.0, half_width, height),
        _rectangle_wire(-half_width + outer, outer, half_width - outer, height - outer),
        _rectangle_wire(left_outer_x0, leaf_bottom, left_outer_x1, leaf_top),
        _rectangle_wire(left_inner_x0, inner_bottom, left_inner_x1, inner_top),
        _rectangle_wire(right_outer_x0, leaf_bottom, right_outer_x1, leaf_top),
        _rectangle_wire(right_inner_x0, inner_bottom, right_inner_x1, inner_top),
        _rectangle_wire(left_inner_x0, inner_bottom, left_inner_x1, rail1_z0),
        _rectangle_wire(left_inner_x0, rail1_z0, left_inner_x1, rail1_z1),
        _rectangle_wire(left_inner_x0, rail1_z1, left_inner_x1, rail2_z0),
        _rectangle_wire(left_inner_x0, rail2_z0, left_inner_x1, rail2_z1),
        _rectangle_wire(left_inner_x0, rail2_z1, left_inner_x1, inner_top),
        _rectangle_wire(right_inner_x0, inner_bottom, right_inner_x1, rail1_z0),
        _rectangle_wire(right_inner_x0, rail1_z0, right_inner_x1, rail1_z1),
        _rectangle_wire(right_inner_x0, rail1_z1, right_inner_x1, rail2_z0),
        _rectangle_wire(right_inner_x0, rail2_z0, right_inner_x1, rail2_z1),
        _rectangle_wire(right_inner_x0, rail2_z1, right_inner_x1, inner_top),
    ]
    return Part.makeCompound(wires)


def build_window_parts(parameters=None):
    """Return the flat 13-component WindowParts definition."""
    p = normalized_parameters(parameters)
    glass = p["glass_thickness_mm"]
    parts = []
    parts += _component("MarcoExterior", "Frame", "Wire0,Wire1", 100.0, -50.0)
    parts += _component("MarcoHojaIzquierda", "Frame", "Wire2,Wire3,Edge12,Mode1", 50.0, -25.0)
    parts += _component("PanelInferiorIzquierdo", "Solid panel", "Wire6", 20.0, -10.0)
    parts += _component("Travesano460Izquierdo", "Frame", "Wire7", 50.0, -25.0)
    parts += _component("VidrioIntermedioIzquierdo", "Glass panel", "Wire8", glass, -glass * 0.5)
    parts += _component("Travesano1000Izquierdo", "Frame", "Wire9", 50.0, -25.0)
    parts += _component("VidrioSuperiorIzquierdo", "Glass panel", "Wire10", glass, -glass * 0.5)
    parts += _component("MarcoHojaDerecha", "Frame", "Wire4,Wire5,Edge18,Mode2", 50.0, -25.0)
    parts += _component("PanelInferiorDerecho", "Solid panel", "Wire11", 20.0, -10.0)
    parts += _component("Travesano460Derecho", "Frame", "Wire12", 50.0, -25.0)
    parts += _component("VidrioIntermedioDerecho", "Glass panel", "Wire13", glass, -glass * 0.5)
    parts += _component("Travesano1000Derecho", "Frame", "Wire14", 50.0, -25.0)
    parts += _component("VidrioSuperiorDerecho", "Glass panel", "Wire15", glass, -glass * 0.5)
    return parts


def ensure_material_definition(doc):
    """Return one reusable Arch MultiMaterial per document."""
    if Arch is None or not hasattr(Arch, "makeMaterial"):
        raise UserFacingError("Arch.makeMaterial no esta disponible en esta instalacion.")
    materials = [_ensure_material(doc, *spec) for spec in MATERIAL_SPECS]
    material_set = _find_marker(doc, "FA_MaterialSetId", MATERIAL_SET_ID)
    if material_set is None:
        material_set = Arch.makeMultiMaterial("Materiales puerta doble BIM Europa")
    material_set.Names = ["Frame", "Solid panel", "Glass panel"]
    material_set.Materials = materials
    material_set.Thicknesses = [50.0, 20.0, DEFAULTS["glass_thickness_mm"]]
    material_set.Description = "Aluminio gris satinado, panel inferior y vidrio laminado"
    set_prop(material_set, "App::PropertyString", "FA_MaterialSetId", "FacilArquitectura", "Identificador del conjunto", MATERIAL_SET_ID)
    return material_set


def _ensure_material(doc, spec_id, label, color, transparency):
    material = _find_marker(doc, "FA_MaterialSpecId", spec_id)
    if material is None:
        material = Arch.makeMaterial(label, color, transparency)
    _set_material_appearance(material, color, transparency)
    set_prop(material, "App::PropertyString", "FA_MaterialSpecId", "FacilArquitectura", "Identificador del material", spec_id)
    return material


def _set_material_appearance(material, color, transparency):
    """Write RGB plus an explicit transparency key for ArchWindow 1.1.3."""
    rgb = tuple(float(value) for value in color[:3])
    alpha_percent = int(round(max(0.0, min(100.0, float(transparency)))))
    material.Color = rgb
    material.Transparency = alpha_percent
    card = dict(getattr(material, "Material", {}) or {})
    card["DiffuseColor"] = str(rgb)
    card["Transparency"] = str(alpha_percent)
    card.setdefault("Name", str(getattr(material, "Label", "") or ""))
    material.Material = card


def _find_marker(doc, property_name, value):
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, property_name, "") or "") == str(value):
            return obj
    return None


def _tag_profile(profile):
    set_prop(profile, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", GENERATOR)
    set_prop(profile, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "door_profile")
    set_prop(profile, "App::PropertyString", "RepresentationRole", "FacilArquitectura", "Rol de representacion", "Profile")


def _tag_door(door, profile, host, params, host_context=None):
    values = (
        ("App::PropertyString", "CRSchemaVersion", "Version del contrato", "1.0"),
        ("App::PropertyString", "SpecId", "Identificador estable", SPEC_ID),
        ("App::PropertyString", "Discipline", "Disciplina", "Architecture"),
        ("App::PropertyString", "ElementType", "Tipo logico", "Door"),
        ("App::PropertyString", "Subtype", "Subtipo", "DoubleLeafGlazed"),
        ("App::PropertyString", "SystemType", "Sistema", "Europa"),
        ("App::PropertyString", "FrameMaterial", "Material del marco", "Aluminio"),
        ("App::PropertyString", "FrameFinish", "Acabado", "Gris satinado"),
        ("App::PropertyString", "GlassType", "Tipo de vidrio", "Vidrio laminado 6 mm"),
        ("App::PropertyInteger", "LeafCount", "Cantidad de hojas", 2),
        ("App::PropertyLength", "LowerProtectionTop", "Nivel superior de proteccion", params["lower_protection_top_mm"]),
        ("App::PropertyLength", "SecondRailLevel", "Nivel del segundo travesano", params["second_rail_level_mm"]),
        ("App::PropertyLength", "GlassThickness", "Espesor del vidrio", params["glass_thickness_mm"]),
        ("App::PropertyString", "FA_GeneratedBy", "Generador", GENERATOR),
        ("App::PropertyString", "FA_Role", "Rol", "door"),
        ("App::PropertyString", "FA_ElementType", "Tipo de elemento", "door"),
        ("App::PropertyLength", "FA_Width_mm", "Ancho BIM", params["width_mm"]),
        ("App::PropertyLength", "FA_Height_mm", "Altura BIM", params["height_mm"]),
        ("App::PropertyString", "FA_PresetName", "Tipo BIM", "Double leaf glazed Europa"),
        ("App::PropertyLink", "Profile", "Perfil base", profile),
        (
            "App::PropertyString",
            "FA_HostWallName",
            "Nombre estable del muro anfitrion; la relacion autoritativa es Hosts",
            str(getattr(host, "Name", "") or ""),
        ),
    )
    for prop_type, name, description, value in values:
        set_prop(door, prop_type, name, "FacilArquitectura", description, value)
    if host_context:
        normal = host_context.get("normal", (0.0, 0.0, 0.0))
        set_prop(
            door,
            "App::PropertyInteger",
            "FA_HostSegmentIndex",
            "FacilArquitectura",
            "Indice del tramo anfitrion",
            int(host_context.get("segment_index", -1)),
        )
        set_prop(
            door,
            "App::PropertyVector",
            "FA_HostNormalGlobal",
            "FacilArquitectura",
            "Normal global calculada",
            FreeCAD.Vector(*normal),
        )
    set_prop(profile, "App::PropertyLinkHidden", "Owner", "FacilArquitectura", "Propietario semantico", door)


def _add_to_container(container, obj, hosted=False, is_base=False):
    """Keep native tree ownership singular for doors and their Base profiles."""
    if container is None or obj is None:
        return
    try:
        if is_level(container):
            if hosted or is_base:
                tag_target_level(container, obj)
            else:
                add_to_level(container, obj)
        elif not hosted and not is_base:
            container.addObject(obj)
    except Exception:
        pass


def _rectangle_wire(x0, z0, x1, z1):
    return Part.makePolygon(
        (
            FreeCAD.Vector(float(x0), 0.0, float(z0)),
            FreeCAD.Vector(float(x1), 0.0, float(z0)),
            FreeCAD.Vector(float(x1), 0.0, float(z1)),
            FreeCAD.Vector(float(x0), 0.0, float(z1)),
            FreeCAD.Vector(float(x0), 0.0, float(z0)),
        )
    )


def _component(name, component_type, wires, depth, offset):
    return [name, component_type, wires, str(float(depth)), str(float(offset))]


def _validate_parameters(p):
    width = p["width_mm"]
    height = p["height_mm"]
    outer = p["outer_frame_mm"]
    leaf_frame = p["leaf_frame_mm"]
    gap = p["leaf_gap_mm"]
    rail = p["rail_thickness_mm"]
    lower = p["lower_protection_top_mm"]
    second = p["second_rail_level_mm"]
    glass = p["glass_thickness_mm"]
    if width < 800.0 or height < 1200.0:
        raise UserFacingError("La puerta doble requiere al menos 800 x 1200 mm.")
    if min(outer, leaf_frame, gap, rail, glass) <= 0.0:
        raise UserFacingError("Marcos, separacion, travesanos y vidrio deben ser positivos.")
    clear_leaf_width = (width - gap) * 0.5 - outer - leaf_frame * 2.0
    if clear_leaf_width <= 50.0:
        raise UserFacingError("El ancho no deja espacio util dentro de las hojas.")
    inner_bottom = outer + leaf_frame
    inner_top = height - outer - leaf_frame
    if not inner_bottom < lower - rail * 0.5 < lower + rail * 0.5:
        raise UserFacingError("El primer travesano invade el marco inferior.")
    if not lower + rail * 0.5 < second - rail * 0.5:
        raise UserFacingError("Los dos travesanos se superponen.")
    if not second + rail * 0.5 < inner_top:
        raise UserFacingError("El segundo travesano invade el marco superior.")


def _vector_values(value):
    if value is None:
        return None
    try:
        return (float(value.x), float(value.y), float(value.z))
    except Exception:
        try:
            return (float(value[0]), float(value[1]), float(value[2]))
        except Exception:
            return None


def _wall_base_z(wall, fallback):
    try:
        box = wall.Shape.BoundBox
        if float(box.ZLength) > 0.0:
            return float(box.ZMin)
    except Exception:
        pass
    return float(fallback)


def _wall_width(wall):
    for attr in ("Width", "FA_Thickness_mm", "FA_WallThickness"):
        try:
            value = float(getattr(getattr(wall, attr), "Value", getattr(wall, attr)))
            if value > 0.0:
                return value
        except Exception:
            pass
    try:
        box = wall.Shape.BoundBox
        if min(float(box.XLength), float(box.YLength)) > 0.0:
            return min(float(box.XLength), float(box.YLength))
    except Exception:
        pass
    return 100.0


def _wall_height(wall):
    try:
        value = float(getattr(getattr(wall, "Height"), "Value", wall.Height))
        if value > 0.0:
            return value
    except Exception:
        pass
    try:
        value = float(wall.Shape.BoundBox.ZLength)
        if value > 0.0:
            return value
    except Exception:
        pass
    return DEFAULTS["height_mm"]


def _nominal_wall_support(host_context):
    segment = tuple(host_context["segment"])
    length = segment_length(segment)
    width = float(host_context["wall_width_mm"])
    height = float(host_context["wall_height_mm"])
    if min(length, width, height) <= 0.0:
        raise ValueError("Dimensiones nominales de muro invalidas")
    angle = math.degrees(
        math.atan2(segment[4] - segment[1], segment[3] - segment[0])
    )
    support = Part.makeBox(
        length,
        width,
        height,
        FreeCAD.Vector(0.0, -width * 0.5, 0.0),
    )
    support.Placement = FreeCAD.Placement(
        FreeCAD.Vector(segment[0], segment[1], float(host_context["base_z"])),
        FreeCAD.Rotation(FreeCAD.Vector(0.0, 0.0, 1.0), angle),
    )
    return support
