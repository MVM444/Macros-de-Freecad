"""FreeCAD adapter for FA stair-between-slabs.

Nombre: stair_freecad_adapter.py
Proposito: adaptar dos losas y un Wire/Sketch de dos segmentos a una escalera Arch nativa.
Funcion principal: leer seleccion/geometria en coordenadas globales, crear las bases nativas,
llamar Arch.makeStairs() y producir una representacion documental PLAN 2D enlazada.
Mantenimiento: mantener la planificacion numerica en fa_stair_core.py; no crear solidos de
escalera paralelos a Arch Stairs; los huecos estructurales deben usar Subtractions nativas
y conservar un PLAN 2D documental separado.
Version: 0.6.1
Fecha y hora: 2026-09-14 21:55 America/Costa_Rica
FreeCAD objetivo: 1.1.3
"""

from __future__ import annotations

import json

import Draft
import FreeCAD as App
import Part
import Arch

from .bim_structure_utils import (
    add_to_container,
    add_to_level,
    adopt_auxiliary_sources,
    is_building,
    resolve_level_context,
    tag_target_level,
)
from .command_errors import UserFacingError
from .project_structure import set_prop, warn


GENERATED_BY = "FA_StairBetweenSlabs_v0.6.1"
TOOL_LABEL = "FA Escalera entre losas"


def _global_placement(obj):
    try:
        return obj.getGlobalPlacement()
    except Exception:
        return getattr(obj, "Placement", App.Placement())


def _world_point(obj, point):
    return _global_placement(obj).multVec(App.Vector(point.x, point.y, point.z))


def is_path_candidate(obj):
    """Return True for an open, non-solid path-like object."""
    try:
        shape = getattr(obj, "Shape", None)
        if shape is None or not list(getattr(shape, "Edges", []) or []):
            return False
        if list(getattr(shape, "Solids", []) or []) or list(getattr(shape, "Faces", []) or []):
            return False
        type_id = str(getattr(obj, "TypeId", "") or "")
        draft_type = str(Draft.getType(obj) or "")
        if type_id.startswith("Sketcher::"):
            return True
        if draft_type in ("Wire", "BSpline"):
            return True
        if hasattr(obj, "Points"):
            return True
    except Exception:
        return False
    return False


def _path_points_from_draft_wire(obj):
    points = list(getattr(obj, "Points", []) or [])
    if len(points) != 3:
        return None
    return [_world_point(obj, point) for point in points]


def _path_points_from_sketch(obj):
    geometry = list(getattr(obj, "Geometry", []) or [])
    lines = [geom for geom in geometry if isinstance(geom, Part.LineSegment)]
    if len(lines) != 2:
        return None

    g1, g2 = lines
    a, b = g1.StartPoint, g1.EndPoint
    c, d = g2.StartPoint, g2.EndPoint
    tol = 1.0e-5

    def close(p, q):
        return (App.Vector(p) - App.Vector(q)).Length <= tol

    if close(b, c):
        local = [a, b, d]
    elif close(b, d):
        local = [a, b, c]
    elif close(a, c):
        local = [b, a, d]
    elif close(a, d):
        local = [b, a, c]
    else:
        return None
    return [_world_point(obj, App.Vector(point)) for point in local]


def _path_points_from_shape(obj):
    edges = list(getattr(getattr(obj, "Shape", None), "Edges", []) or [])
    if len(edges) != 2:
        return None
    try:
        parent_xf = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
    except Exception:
        parent_xf = App.Placement()

    e1, e2 = edges
    points = [
        parent_xf.multVec(e1.Vertexes[0].Point),
        parent_xf.multVec(e1.Vertexes[-1].Point),
        parent_xf.multVec(e2.Vertexes[0].Point),
        parent_xf.multVec(e2.Vertexes[-1].Point),
    ]
    tol = 1.0e-4

    def close(a, b):
        return (a - b).Length <= tol

    if close(points[1], points[2]):
        return [points[0], points[1], points[3]]
    if close(points[1], points[3]):
        return [points[0], points[1], points[2]]
    if close(points[0], points[2]):
        return [points[1], points[0], points[3]]
    if close(points[0], points[3]):
        return [points[1], points[0], points[2]]
    return None


def extract_path_points(obj):
    points = _path_points_from_draft_wire(obj)
    if points is None and str(getattr(obj, "TypeId", "") or "").startswith("Sketcher::"):
        points = _path_points_from_sketch(obj)
    if points is None:
        points = _path_points_from_shape(obj)
    if points is None or len(points) != 3:
        raise UserFacingError(
            "El Wire/Sketch debe ser abierto, continuo y tener exactamente dos segmentos rectos."
        )
    return points


def _shape_global_bbox(obj):
    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        raise UserFacingError("El objeto %s no tiene Shape utilizable." % getattr(obj, "Label", obj))

    bb = shape.BoundBox
    try:
        parent_xf = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
    except Exception:
        parent_xf = App.Placement()

    corners = []
    for x in (bb.XMin, bb.XMax):
        for y in (bb.YMin, bb.YMax):
            for z in (bb.ZMin, bb.ZMax):
                corners.append(parent_xf.multVec(App.Vector(x, y, z)))
    return {
        "xmin": min(point.x for point in corners),
        "xmax": max(point.x for point in corners),
        "ymin": min(point.y for point in corners),
        "ymax": max(point.y for point in corners),
        "zmin": min(point.z for point in corners),
        "zmax": max(point.z for point in corners),
    }


def slab_info(obj):
    bb = _shape_global_bbox(obj)
    return {
        "object": obj,
        "top_z": float(bb["zmax"]),
        "bottom_z": float(bb["zmin"]),
        "thickness": max(0.0, float(bb["zmax"] - bb["zmin"])),
    }


def build_stair_context(doc, lower, upper, source):
    """Build a read-only stair context from explicit objects.

    This is the reusable adapter entry point used by both the interactive
    command and FA Demo edificio. No GUI state is read and the document is not
    modified.
    """
    if doc is None or lower is None or upper is None or source is None:
        raise UserFacingError("Se requieren documento, losa inferior, losa superior y recorrido.")
    slab_data = [slab_info(lower), slab_info(upper)]
    slab_data.sort(key=lambda item: item["top_z"])
    lower_info, upper_info = slab_data
    if upper_info["top_z"] <= lower_info["top_z"] + 100.0:
        raise UserFacingError("No hay diferencia de nivel suficiente entre las dos losas.")

    resolved_lower = lower_info["object"]
    resolved_upper = upper_info["object"]
    points = extract_path_points(source)
    return {
        "source": source,
        "lower": resolved_lower,
        "upper": resolved_upper,
        "lower_info": lower_info,
        "upper_info": upper_info,
        "lower_level": resolve_level_context(doc, objects=[resolved_lower]),
        "upper_level": resolve_level_context(doc, objects=[resolved_upper]),
        "points": points,
    }


def analyze_selection(doc, selection):
    """Resolve exactly two slabs plus one two-segment path without modifying the document."""
    selection = list(selection or [])
    if len(selection) != 3:
        raise UserFacingError(
            "Seleccione exactamente tres objetos: las dos losas y un Wire/Sketch de dos segmentos."
        )
    paths = [obj for obj in selection if is_path_candidate(obj)]
    if len(paths) != 1:
        raise UserFacingError(
            "No se pudo identificar un unico Wire/Sketch abierto de dos segmentos en la seleccion."
        )
    source = paths[0]
    slabs = [obj for obj in selection if obj is not source]
    return build_stair_context(doc, slabs[0], slabs[1], source)

def _vec(values):
    return App.Vector(float(values[0]), float(values[1]), float(values[2]))


def _make_base_objects(doc, plan):
    geom = plan["geometry"]
    f1 = doc.addObject("Part::Feature", "FA_StairBase_Flight1")
    f1.Label = "FA Escalera - Base tramo 1"
    f1.Shape = Part.makeLine(_vec(geom["flight1_start_xyz"]), _vec(geom["flight1_end_xyz"]))

    landing = doc.addObject("Part::Feature", "FA_StairBase_Landing")
    landing.Label = "FA Escalera - Base descanso"
    landing.Shape = Part.makePolygon([_vec(point) for point in geom["landing_xyz"]])

    f2 = doc.addObject("Part::Feature", "FA_StairBase_Flight2")
    f2.Label = "FA Escalera - Base tramo 2"
    f2.Shape = Part.makeLine(_vec(geom["flight2_start_xyz"]), _vec(geom["flight2_end_xyz"]))

    for obj in (f1, landing, f2):
        set_prop(obj, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", GENERATED_BY)
    return f1, landing, f2


def _set_if_possible(obj, prop, value):
    try:
        if prop in list(getattr(obj, "PropertiesList", []) or []):
            setattr(obj, prop, value)
            return True
    except Exception:
        pass
    return False


def _tag_master(master, context, plan, railings_mode="native"):
    lower = context["lower"]
    upper = context["upper"]
    source = context["source"]
    lower_level = context.get("lower_level")
    upper_level = context.get("upper_level")
    props = (
        ("App::PropertyString", "FA_GeneratedBy", GENERATED_BY),
        ("App::PropertyLink", "FA_LowerSlab", lower),
        ("App::PropertyLink", "FA_UpperSlab", upper),
        ("App::PropertyLink", "FA_SourceWire", source),
        ("App::PropertyLink", "FA_LowerLevel", lower_level),
        ("App::PropertyLink", "FA_UpperLevel", upper_level),
        ("App::PropertyLength", "FA_StartZ", float(plan["input"]["lower_top_z_mm"])),
        ("App::PropertyLength", "FA_EndZ", float(plan["input"]["upper_top_z_mm"])),
        ("App::PropertyLength", "FA_LandingZ", float(plan["geometry"]["landing_z_mm"])),
        ("App::PropertyLength", "FA_StairWidth", float(plan["input"]["width_mm"])),
        ("App::PropertyInteger", "FA_TotalRisers", int(plan["steps"]["total_risers"])),
        ("App::PropertyString", "FA_Schema", str(plan["schema"])),
        ("App::PropertyString", "FA_RailingMode", str(railings_mode or "native")),
    )
    for prop_type, name, value in props:
        set_prop(master, prop_type, name, "FacilArquitectura", name, value)

def _rect_wire(a, b, width, z):
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    dx, dy = bx - ax, by - ay
    length = (dx * dx + dy * dy) ** 0.5
    if length <= 1.0e-9:
        return None
    nx, ny = -dy / length * width / 2.0, dx / length * width / 2.0
    points = [
        App.Vector(ax + nx, ay + ny, z),
        App.Vector(bx + nx, by + ny, z),
        App.Vector(bx - nx, by - ny, z),
        App.Vector(ax - nx, ay - ny, z),
        App.Vector(ax + nx, ay + ny, z),
    ]
    return Part.makePolygon(points)


def _make_plan2d(doc, master, plan):
    z = float(plan["input"]["lower_top_z_mm"]) + 10.0
    width = float(plan["input"]["width_mm"])
    p0, pc, p2 = plan["input"]["points_xy"]
    landing_start = plan["geometry"]["landing_start_xy"]
    landing_end = plan["geometry"]["landing_end_xy"]

    shapes = []
    for a, b in ((p0, landing_start), (landing_end, p2), (landing_start, pc), (pc, landing_end)):
        wire = _rect_wire(a, b, width, z)
        if wire is not None:
            shapes.append(wire)
    shapes.append(
        Part.makePolygon(
            [
                App.Vector(p0[0], p0[1], z),
                App.Vector(pc[0], pc[1], z),
                App.Vector(p2[0], p2[1], z),
            ]
        )
    )

    dx, dy = p2[0] - pc[0], p2[1] - pc[1]
    length = (dx * dx + dy * dy) ** 0.5
    if length > 1.0e-6:
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        back = max(150.0, min(300.0, width * 0.25))
        wing = back * 0.45
        tip = App.Vector(p2[0], p2[1], z)
        left = App.Vector(p2[0] - ux * back + px * wing, p2[1] - uy * back + py * wing, z)
        right = App.Vector(p2[0] - ux * back - px * wing, p2[1] - uy * back - py * wing, z)
        shapes.append(Part.makeLine(tip, left))
        shapes.append(Part.makeLine(tip, right))

    obj = doc.addObject("Part::Feature", "FA_Stair_PLAN")
    obj.Label = "FA Escalera PLAN 2D"
    obj.Shape = Part.makeCompound(shapes)
    set_prop(obj, "App::PropertyBool", "DocumentationOnly", "Documentacion", "Solo documentacion", True)
    set_prop(obj, "App::PropertyString", "RepresentationRole", "Documentacion", "Rol documental", "PLAN")
    set_prop(obj, "App::PropertyLink", "Owner", "Documentacion", "Escalera propietaria", master)
    set_prop(obj, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", GENERATED_BY)
    try:
        obj.ViewObject.Visibility = False
    except Exception:
        pass
    return obj





def _clearance_wire(polygon, z):
    points = [App.Vector(float(x), float(y), float(z)) for x, y in list(polygon or [])]
    if len(points) < 3:
        return None
    points.append(App.Vector(points[0]))
    return Part.makePolygon(points)


def create_clearance_previews(
    doc,
    master,
    clearance_plan,
    plane_containers=None,
    visible=True,
):
    """Create documentary PLAN outlines for calculated stair clearance zones.

    This function is intentionally preview-only: it does not modify a slab or
    ceiling. The same JSON-compatible clearance plan can later feed native Arch
    Subtractions and ceiling exclusion zones after the geometry is validated in
    real FreeCAD.
    """
    containers = dict(plane_containers or {})
    created = {}
    plan = dict(clearance_plan or {})
    headroom = float(plan.get("headroom_mm", 0.0) or 0.0)
    for plane in list(plan.get("planes", []) or []):
        plane_id = str(plane.get("id") or "obstacle")
        role = str(plane.get("role") or plane_id)
        plane_z = float(plane.get("plane_z_mm", 0.0))
        wires = []
        zones = list(plane.get("zones", []) or [])
        # For the complete-L clearance model document the resulting outer
        # boundary, not the two overlapping construction rectangles.
        if str(plane.get("opening_shape") or "") == "l_union_v2":
            unified = _fused_clearance_face(zones, plane_z + 5.0)
            for face in list(getattr(unified, "Faces", []) or []):
                outer = getattr(face, "OuterWire", None)
                if outer is not None:
                    wires.append(outer)
        else:
            for zone in zones:
                wire = _clearance_wire(zone.get("polygon_mm"), plane_z + 5.0)
                if wire is not None:
                    wires.append(wire)
        if not wires:
            continue

        safe_id = "".join(ch if ch.isalnum() else "_" for ch in plane_id).strip("_") or "Obstacle"
        obj = doc.addObject("Part::Feature", "FA_StairClearance_%s_PLAN" % safe_id)
        if "slab" in role.lower():
            obj.Label = "PREVIEW - Hueco losa escalera"
            representation = "STAIR_SLAB_OPENING_PLAN"
        elif "ceiling" in role.lower() or "cielo" in role.lower():
            obj.Label = "PREVIEW - Exclusion cielorraso escalera"
            representation = "STAIR_CEILING_EXCLUSION_PLAN"
        else:
            obj.Label = "PREVIEW - Holgura escalera - %s" % plane_id
            representation = "STAIR_CLEARANCE_PLAN"
        obj.Shape = Part.makeCompound(wires)
        set_prop(obj, "App::PropertyBool", "DocumentationOnly", "Documentacion", "Solo documentacion", True)
        set_prop(obj, "App::PropertyBool", "FA_PreviewOnly", "FacilArquitectura", "Previsualizacion sin corte", True)
        set_prop(obj, "App::PropertyString", "RepresentationRole", "Documentacion", "Rol documental", representation)
        # The stair master links to this PLAN object below; keep the reverse
        # reference as text to avoid a PropertyLink dependency cycle.
        set_prop(obj, "App::PropertyString", "FA_OwnerName", "Documentacion", "Escalera propietaria", str(getattr(master, "Name", "") or ""))
        set_prop(obj, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", GENERATED_BY)
        set_prop(obj, "App::PropertyString", "FA_ClearanceSchema", "FacilArquitectura", "Esquema de holgura", str(plan.get("schema", "")))
        set_prop(obj, "App::PropertyString", "FA_OpeningShape", "FacilArquitectura", "Forma logica del buque", str(plane.get("opening_shape") or ""))
        set_prop(obj, "App::PropertyLength", "FA_Headroom", "FacilArquitectura", "Altura libre de calculo", headroom)
        set_prop(obj, "App::PropertyLength", "FA_PlaneZ", "FacilArquitectura", "Cota del obstaculo", plane_z)
        set_prop(
            obj,
            "App::PropertyString",
            "FA_ClearanceZonesJSON",
            "FacilArquitectura",
            "Zonas 2D JSON",
            json.dumps(list(plane.get("zones", []) or []), sort_keys=True, separators=(",", ":")),
        )
        container = containers.get(plane_id)
        if container is not None:
            add_to_level(container, obj)
        try:
            obj.ViewObject.Visibility = bool(visible)
            obj.ViewObject.LineWidth = 3.0
        except Exception:
            pass
        created[plane_id] = obj

    if master is not None:
        slab_preview = next((obj for key, obj in created.items() if "slab" in key.lower()), None)
        ceiling_preview = next((obj for key, obj in created.items() if "ceiling" in key.lower() or "cielo" in key.lower()), None)
        if slab_preview is not None:
            set_prop(master, "App::PropertyLink", "FA_SlabOpeningPreview", "FacilArquitectura", "Preview hueco de losa", slab_preview)
        if ceiling_preview is not None:
            set_prop(master, "App::PropertyLink", "FA_CeilingExclusionPreview", "FacilArquitectura", "Preview exclusion de cielorraso", ceiling_preview)
        set_prop(master, "App::PropertyString", "FA_ClearanceSchema", "FacilArquitectura", "Esquema de holgura", str(plan.get("schema", "")))
        set_prop(master, "App::PropertyLength", "FA_Headroom", "FacilArquitectura", "Altura libre de calculo", headroom)
    doc.recompute()
    return created


def _clearance_plane(clearance_plan, plane_id):
    """Return one named obstacle plane from a JSON-compatible clearance plan."""
    target = str(plane_id or "")
    for plane in list((clearance_plan or {}).get("planes", []) or []):
        if str(plane.get("id") or "") == target:
            return dict(plane)
    return {}


def _solid_from_clearance_zone(zone, z_min, z_max):
    """Build one transient solid cutter from a clearance-zone polygon."""
    polygon = list((zone or {}).get("polygon_mm", []) or [])
    wire = _clearance_wire(polygon, float(z_min))
    if wire is None:
        return None
    face = Part.Face(wire)
    height = float(z_max) - float(z_min)
    if height <= 1.0e-6 or float(face.Area) <= 1.0:
        return None
    return face.extrude(App.Vector(0.0, 0.0, height))


def _fused_clearance_solid(zones, z_min, z_max):
    """Fuse all valid zone solids so Arch receives one stable subtraction object."""
    solids = []
    for zone in list(zones or []):
        solid = _solid_from_clearance_zone(zone, z_min, z_max)
        if solid is not None and not solid.isNull():
            solids.append(solid)
    if not solids:
        return Part.Shape()
    shape = solids[0]
    for solid in solids[1:]:
        shape = shape.fuse(solid)
    try:
        shape = shape.removeSplitter()
    except Exception:
        pass
    return shape


def create_native_slab_opening(
    doc,
    master,
    upper_slab,
    clearance_plan,
    plane_id="upper_slab",
    vertical_margin_mm=20.0,
    dry_run=False,
):
    """Create/reuse one Arch-native subtraction volume for the stair opening.

    The host slab remains the authoritative Arch object. The cutter is a normal
    Part::Feature registered in the slab ``Subtractions`` list through the native
    Arch Remove API, so the operation is reversible by removing that link/object.
    ``dry_run`` returns the planned metadata without modifying the document.
    """
    if doc is None or upper_slab is None:
        raise UserFacingError("Se requiere la losa superior para crear el buque de escalera.")
    if not hasattr(upper_slab, "Subtractions"):
        raise UserFacingError(
            "La losa superior no expone Subtractions de Arch y no puede recibir un hueco nativo."
        )

    plane = _clearance_plane(clearance_plan, plane_id)
    zones = list(plane.get("zones", []) or [])
    if not zones:
        raise UserFacingError("El plan de holgura no contiene zonas para abrir la losa superior.")

    info = slab_info(upper_slab)
    margin = max(1.0, float(vertical_margin_mm))
    z_min = float(info["bottom_z"]) - margin
    z_max = float(info["top_z"]) + margin
    metadata = {
        "status": "planned",
        "plane_id": str(plane_id),
        "zone_count": len(zones),
        "z_min_mm": z_min,
        "z_max_mm": z_max,
    }
    if bool(dry_run):
        return metadata

    cutter = getattr(master, "FA_SlabOpening", None) if master is not None else None
    if cutter is None or getattr(cutter, "Document", None) is not doc:
        cutter = doc.addObject("Part::Feature", "FA_StairSlabOpeningVolume")
    cutter.Label = "Buque escalera - sustraccion losa"
    cutter.Shape = _fused_clearance_solid(zones, z_min, z_max)
    if cutter.Shape.isNull() or not list(getattr(cutter.Shape, "Solids", []) or []):
        raise RuntimeError("No se pudo construir un volumen solido para el hueco de escalera.")

    set_prop(cutter, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", GENERATED_BY)
    set_prop(cutter, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "stair_slab_opening_volume")
    # No back-links to master/host: both the stair and the slab already link to
    # this cutter. Keeping only names here avoids a dependency cycle in FreeCAD.
    set_prop(cutter, "App::PropertyString", "FA_OwnerName", "FacilArquitectura", "Escalera propietaria", str(getattr(master, "Name", "") or ""))
    set_prop(cutter, "App::PropertyString", "FA_HostSlabName", "FacilArquitectura", "Losa anfitriona", str(getattr(upper_slab, "Name", "") or ""))
    set_prop(cutter, "App::PropertyBool", "FA_ConstructionOnly", "FacilArquitectura", "Volumen auxiliar de construccion", True)
    set_prop(cutter, "App::PropertyBool", "GameExportExclude", "FacilArquitectura", "Excluir de exportacion de juego", True)
    set_prop(cutter, "App::PropertyString", "FA_ClearanceSchema", "FacilArquitectura", "Esquema de holgura", str((clearance_plan or {}).get("schema", "")))
    set_prop(cutter, "App::PropertyString", "FA_ClearanceZonesJSON", "FacilArquitectura", "Zonas 2D JSON", json.dumps(zones, sort_keys=True, separators=(",", ":")))

    before_volume = 0.0
    try:
        before_volume = float(upper_slab.Shape.Volume)
    except Exception:
        pass

    current = list(getattr(upper_slab, "Subtractions", []) or [])
    newly_added = cutter not in current
    if newly_added:
        remove_components = getattr(Arch, "removeComponents", None)
        if callable(remove_components):
            try:
                remove_components([cutter], upper_slab)
            except TypeError:
                remove_components(cutter, upper_slab)
        else:
            current.append(cutter)
            upper_slab.Subtractions = current
    try:
        cutter.ViewObject.Visibility = False
    except Exception:
        pass
    doc.recompute()

    if cutter not in list(getattr(upper_slab, "Subtractions", []) or []):
        raise RuntimeError("FreeCAD no registro el buque dentro de Subtractions de la losa superior.")

    after_volume = 0.0
    try:
        after_volume = float(upper_slab.Shape.Volume)
    except Exception:
        pass
    if newly_added and before_volume > 1.0 and after_volume >= before_volume - 1.0:
        raise RuntimeError(
            "La sustraccion fue enlazada pero la Shape de la losa no redujo su volumen; revisar el buque."
        )

    if master is not None:
        set_prop(master, "App::PropertyLink", "FA_SlabOpening", "FacilArquitectura", "Buque nativo en losa superior", cutter)
        set_prop(master, "App::PropertyString", "FA_SlabOpeningStatus", "FacilArquitectura", "Estado hueco de losa", "native_subtraction_applied")

    metadata.update(
        {
            "status": "native_subtraction_applied",
            "cutter": cutter,
            "before_volume_mm3": before_volume,
            "after_volume_mm3": after_volume,
            "newly_added": bool(newly_added),
        }
    )
    return metadata



def _fused_clearance_face(zones, z_mm):
    """Fuse clearance-zone polygons into one planar opening face."""
    faces = []
    for zone in list(zones or []):
        polygon = list((zone or {}).get("polygon_mm", []) or [])
        wire = _clearance_wire(polygon, float(z_mm))
        if wire is None:
            continue
        try:
            face = Part.Face(wire)
        except Exception:
            continue
        if face.isNull() or float(face.Area) <= 1.0:
            continue
        faces.append(face)
    if not faces:
        return Part.Shape()
    result = faces[0]
    for face in faces[1:]:
        result = result.fuse(face)
    try:
        result = result.removeSplitter()
    except Exception:
        pass
    return result


def _outside_liner_polygon(opening_face, edge, thickness_mm):
    """Return the XY footprint of one liner segment outside the clear opening."""
    vertices = list(getattr(edge, "Vertexes", []) or [])
    if len(vertices) < 2:
        return None
    a = vertices[0].Point
    b = vertices[-1].Point
    dx = float(b.x) - float(a.x)
    dy = float(b.y) - float(a.y)
    length = (dx * dx + dy * dy) ** 0.5
    thickness = max(1.0, float(thickness_mm))
    if length <= 1.0e-6:
        return None
    nx = -dy / length
    ny = dx / length
    mx = (float(a.x) + float(b.x)) * 0.5
    my = (float(a.y) + float(b.y)) * 0.5
    probe = min(max(2.0, thickness * 0.20), 20.0)

    def inside(sign):
        point = App.Vector(mx + nx * probe * sign, my + ny * probe * sign, float(a.z))
        try:
            return bool(opening_face.isInside(point, 0.5, True))
        except Exception:
            return False

    plus_inside = inside(1.0)
    minus_inside = inside(-1.0)
    if plus_inside and not minus_inside:
        outward = -1.0
    elif minus_inside and not plus_inside:
        outward = 1.0
    else:
        outward = -1.0

    ox = nx * thickness * outward
    oy = ny * thickness * outward
    return [
        [float(a.x), float(a.y)],
        [float(b.x), float(b.y)],
        [float(b.x) + ox, float(b.y) + oy],
        [float(a.x) + ox, float(a.y) + oy],
    ]


def _outside_liner_segment(opening_face, edge, thickness_mm, z_min, z_max):
    """Create one vertical liner segment outside an opening boundary edge."""
    polygon = _outside_liner_polygon(opening_face, edge, thickness_mm)
    height = float(z_max) - float(z_min)
    if polygon is None or height <= 1.0e-6:
        return None
    points = [App.Vector(float(x), float(y), float(z_min)) for x, y in polygon]
    wire = Part.makePolygon(points + [points[0]])
    face = Part.Face(wire)
    if face.isNull() or float(face.Area) <= 1.0:
        return None
    return face.extrude(App.Vector(0.0, 0.0, height))


def _edge_matches_open_end(edge, open_end, default_width_mm):
    """Return True when a boundary edge is the transverse entry/exit of the stair void."""
    vertices = list(getattr(edge, "Vertexes", []) or [])
    if len(vertices) < 2:
        return False
    a = vertices[0].Point
    b = vertices[-1].Point
    dx = float(b.x) - float(a.x)
    dy = float(b.y) - float(a.y)
    length = (dx * dx + dy * dy) ** 0.5
    if length <= 1.0e-6:
        return False
    tangent = (dx / length, dy / length)
    data = dict(open_end or {})
    point = list(data.get("point_mm", []) or [])
    direction = list(data.get("direction_xy", []) or [])
    if len(point) < 2 or len(direction) < 2:
        return False
    direction_length = (float(direction[0]) ** 2 + float(direction[1]) ** 2) ** 0.5
    if direction_length <= 1.0e-9:
        return False
    direction = (float(direction[0]) / direction_length, float(direction[1]) / direction_length)
    # An open-end edge is transverse to travel and centred on the declared end.
    if abs(tangent[0] * direction[0] + tangent[1] * direction[1]) > 0.20:
        return False
    mx = (float(a.x) + float(b.x)) * 0.5
    my = (float(a.y) + float(b.y)) * 0.5
    distance = ((mx - float(point[0])) ** 2 + (my - float(point[1])) ** 2) ** 0.5
    clear_width = max(1.0, float(data.get("clear_width_mm", default_width_mm) or default_width_mm))
    return bool(distance <= max(5.0, clear_width * 0.10) and length >= clear_width * 0.70)


def _edge_is_open_liner_end(edge, open_ends, default_width_mm):
    return any(_edge_matches_open_end(edge, item, default_width_mm) for item in list(open_ends or []))


def build_ceiling_finish_exclusion_zones(
    clearance_plan,
    plane_id="lower_ceiling",
    liner_thickness_mm=100.0,
    edge_gap_mm=3.0,
):
    """Return ceiling exclusions for both clear passage and liner footprint.

    The suspended ceiling must terminate against the *outside* face of the
    tapichel.  Reusing only the clear stair void makes ceiling panels continue
    underneath the outward-growing liner, causing overlap/z-fighting.  This
    read-only adapter derives the same closed boundary segments used by the
    liner and adds their outward footprint plus a small finish joint.
    """
    plane = _clearance_plane(clearance_plan, plane_id)
    zones = [dict(item) for item in list(plane.get("zones", []) or [])]
    open_ends = list(plane.get("liner_open_ends", []) or [])
    effective_width = float((clearance_plan or {}).get("effective_width_mm", 0.0) or 0.0)
    finish_depth = max(1.0, float(liner_thickness_mm)) + max(0.0, float(edge_gap_mm))
    if not zones:
        return {
            "zones": [],
            "liner_band_count": 0,
            "finish_depth_mm": finish_depth,
            "opening_shape": str(plane.get("opening_shape") or ""),
        }

    z = float(plane.get("plane_z_mm", 0.0))
    opening_face = _fused_clearance_face(zones, z)
    if opening_face.isNull() or not list(getattr(opening_face, "Faces", []) or []):
        raise RuntimeError("No se pudo construir la cara del buque para calcular la terminacion del cielorraso.")

    bands = []
    boundary_edges = []
    for face in list(getattr(opening_face, "Faces", []) or []):
        outer = getattr(face, "OuterWire", None)
        if outer is not None:
            boundary_edges.extend(list(getattr(outer, "Edges", []) or []))
    for index, edge in enumerate(boundary_edges):
        if _edge_is_open_liner_end(edge, open_ends, effective_width):
            continue
        polygon = _outside_liner_polygon(opening_face, edge, finish_depth)
        if polygon is None:
            continue
        bands.append(
            {
                "id": "liner_finish_%d" % (index + 1),
                "role": "stair_opening_liner_finish",
                "polygon_mm": polygon,
            }
        )
    return {
        "zones": zones + bands,
        "liner_band_count": len(bands),
        "finish_depth_mm": finish_depth,
        "opening_shape": str(plane.get("opening_shape") or ""),
    }


def create_stair_opening_liner(
    doc,
    master,
    upper_slab,
    clearance_plan,
    level=None,
    plane_id="lower_ceiling",
    thickness_mm=100.0,
    dry_run=False,
    ceiling_plane_id=None,
    target_container=None,
):
    """Create side tapicheles between suspended ceiling and slab underside.

    The liner follows the unified ceiling-side opening but deliberately leaves
    the stair entry and exit open. Its solids grow outward from the clear void
    and are finally cut by that void prism, so the architectural finish cannot
    reduce the calculated passage/headroom envelope.
    """
    # Compatibility aliases protect hot-reload/sync windows where one module
    # reaches the workstation before the other. New callers use plane_id/level.
    if ceiling_plane_id not in (None, ""):
        plane_id = str(ceiling_plane_id)
    if level is None and target_container is not None:
        level = target_container

    if doc is None or upper_slab is None:
        raise UserFacingError("Se requiere la losa superior para crear el tapichel del buque.")
    thickness = max(1.0, float(thickness_mm))
    plane = _clearance_plane(clearance_plan, plane_id)
    zones = list(plane.get("zones", []) or [])
    open_ends = list(plane.get("liner_open_ends", []) or [])
    effective_width = float((clearance_plan or {}).get("effective_width_mm", 0.0) or 0.0)
    if not zones:
        raise UserFacingError("El plan de holgura no contiene zonas de cielorraso para el tapichel.")

    info = slab_info(upper_slab)
    z_min = float(plane.get("plane_z_mm", 0.0))
    z_max = float(info["bottom_z"])
    if z_max <= z_min + 1.0:
        raise UserFacingError(
            "No existe altura util entre el cielorraso y la cara inferior de la losa para crear el tapichel."
        )
    metadata = {
        "status": "planned",
        "plane_id": str(plane_id),
        "opening_shape": str(plane.get("opening_shape") or ""),
        "zone_count": len(zones),
        "open_end_count": len(open_ends),
        "thickness_mm": thickness,
        "z_min_mm": z_min,
        "z_max_mm": z_max,
        "height_mm": z_max - z_min,
    }
    if bool(dry_run):
        return metadata

    opening_face = _fused_clearance_face(zones, z_min)
    if opening_face.isNull() or not list(getattr(opening_face, "Faces", []) or []):
        raise RuntimeError("No se pudo construir la cara del buque para generar el tapichel.")

    boundary_edges = []
    for face in list(getattr(opening_face, "Faces", []) or []):
        outer = getattr(face, "OuterWire", None)
        if outer is not None:
            boundary_edges.extend(list(getattr(outer, "Edges", []) or []))

    solids = []
    skipped_edges = 0
    for edge in boundary_edges:
        if _edge_is_open_liner_end(edge, open_ends, effective_width):
            skipped_edges += 1
            continue
        solid = _outside_liner_segment(opening_face, edge, thickness, z_min, z_max)
        if solid is not None and not solid.isNull():
            solids.append(solid)
    if not solids:
        raise RuntimeError("No se pudo construir ningun tramo vertical del tapichel.")

    shape = solids[0]
    for solid in solids[1:]:
        shape = shape.fuse(solid)

    # Geometric safety net: even if an OCCT edge orientation is ambiguous, the
    # tapichel may never occupy the clear stair void.
    try:
        clear_void = opening_face.extrude(App.Vector(0.0, 0.0, z_max - z_min))
        shape = shape.cut(clear_void)
    except Exception as exc:
        warn("No se pudo aplicar la proteccion final del paso libre del tapichel: %s" % exc)
    try:
        shape = shape.removeSplitter()
    except Exception:
        pass

    liner = getattr(master, "FA_OpeningLiner", None) if master is not None else None
    if liner is None or getattr(liner, "Document", None) is not doc:
        liner = doc.addObject("Part::Feature", "FA_StairOpeningLiner")
    liner.Label = "Tapichel lateral - buque escalera"
    liner.Shape = shape
    if liner.Shape.isNull() or not list(getattr(liner.Shape, "Solids", []) or []):
        raise RuntimeError("El tapichel calculado no produjo geometria solida valida.")

    set_prop(liner, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", GENERATED_BY)
    set_prop(liner, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "stair_opening_liner")
    set_prop(liner, "App::PropertyString", "FA_OwnerName", "FacilArquitectura", "Escalera propietaria", str(getattr(master, "Name", "") or ""))
    set_prop(liner, "App::PropertyString", "FA_HostSlabName", "FacilArquitectura", "Losa superior", str(getattr(upper_slab, "Name", "") or ""))
    set_prop(liner, "App::PropertyLength", "FA_LinerThickness", "FacilArquitectura", "Espesor del tapichel", thickness)
    set_prop(liner, "App::PropertyLength", "FA_LinerBottomZ", "FacilArquitectura", "Cota inferior", z_min)
    set_prop(liner, "App::PropertyLength", "FA_LinerTopZ", "FacilArquitectura", "Cota superior", z_max)
    set_prop(liner, "App::PropertyInteger", "FA_LinerSkippedOpenEnds", "FacilArquitectura", "Extremos de paso dejados abiertos", int(skipped_edges))
    set_prop(liner, "App::PropertyString", "FA_OpeningShape", "FacilArquitectura", "Forma logica del buque", str(plane.get("opening_shape") or ""))
    set_prop(liner, "App::PropertyString", "FA_LinerOpenEndsJSON", "FacilArquitectura", "Extremos abiertos del paso", json.dumps(open_ends, sort_keys=True, separators=(",", ":")))
    set_prop(liner, "App::PropertyString", "FA_ClearanceSchema", "FacilArquitectura", "Esquema de holgura", str((clearance_plan or {}).get("schema", "")))
    set_prop(liner, "App::PropertyString", "FA_ClearanceZonesJSON", "FacilArquitectura", "Zonas 2D JSON", json.dumps(zones, sort_keys=True, separators=(",", ":")))
    set_prop(liner, "App::PropertyBool", "GameExportExclude", "FacilArquitectura", "Excluir de exportacion de juego", False)
    if level is not None:
        add_to_level(level, liner)
    try:
        liner.ViewObject.Visibility = True
    except Exception:
        pass
    if master is not None:
        set_prop(master, "App::PropertyLink", "FA_OpeningLiner", "FacilArquitectura", "Tapichel lateral del buque", liner)
        set_prop(master, "App::PropertyString", "FA_OpeningLinerStatus", "FacilArquitectura", "Estado tapichel del buque", "applied_open_ends")
    doc.recompute()
    metadata.update(
        {
            "status": "applied_open_ends",
            "liner": liner,
            "edge_count": len(boundary_edges),
            "skipped_edge_count": int(skipped_edges),
            "solid_count": len(solids),
        }
    )
    return metadata


def mark_clearance_plans_applied(previews):
    """Promote preview outlines to hidden documentary PLAN objects after success."""
    for key, obj in dict(previews or {}).items():
        if obj is None:
            continue
        if "slab" in str(key).lower():
            obj.Label = "PLAN - Hueco losa escalera"
        elif "ceiling" in str(key).lower() or "cielo" in str(key).lower():
            obj.Label = "PLAN - Exclusion cielorraso escalera"
        set_prop(obj, "App::PropertyBool", "FA_PreviewOnly", "FacilArquitectura", "Previsualizacion sin corte", False)
        set_prop(obj, "App::PropertyBool", "FA_Applied", "FacilArquitectura", "Aplicado al modelo", True)
        try:
            obj.ViewObject.Visibility = False
        except Exception:
            pass
    return dict(previews or {})


def _stair_segments(master):
    additions = list(getattr(master, "Additions", []) or [])
    segments = [obj for obj in additions if str(Draft.getType(obj) or "") == "Stairs"]
    if len(segments) == 3:
        return segments
    return []


def find_existing_stairs_between_slabs(doc, lower, upper):
    """Return FA stair masters already linking the same ordered slab pair."""
    found = []
    for obj in list(getattr(doc, "Objects", []) or []):
        generated_by = str(getattr(obj, "FA_GeneratedBy", "") or "")
        if not generated_by.startswith("FA_StairBetweenSlabs"):
            continue
        if getattr(obj, "FA_LowerSlab", None) is lower and getattr(obj, "FA_UpperSlab", None) is upper:
            found.append(obj)
    return found


def _native_railing_objects(segments):
    railings = []
    for stair in list(segments or []):
        for name in ("RailingLeft", "RailingRight"):
            try:
                obj = getattr(stair, name, None)
            except Exception:
                obj = None
            if obj is not None and obj not in railings:
                railings.append(obj)
    return railings


def _apply_railing_policy(master, segments, mode):
    """Keep native railings but hide them for the known 1.1.3 multi-segment issue.

    No custom railing geometry is created. A future FreeCAD version can use
    mode='native' after the upstream multi-segment railing fixes are verified.
    """
    normalized = str(mode or "native").strip() or "native"
    railings = _native_railing_objects(segments)
    visible = normalized == "native"
    for railing in railings:
        try:
            railing.ViewObject.Visibility = bool(visible)
        except Exception:
            pass
    status = "native_visible" if visible else "native_hidden_freecad_1_1_3_multisegment"
    set_prop(master, "App::PropertyString", "FA_RailingStatus", "FacilArquitectura", "Estado barandillas", status)
    return railings, status



def _building_parent_for_level(level):
    """Return the unique native Building that directly contains one Level.

    Inter-storey stairs must not be inserted back into the same Level they link
    through FA_LowerLevel: BuildingPart containment plus that reverse PropertyLink
    creates a dependency cycle in FreeCAD. The Building is the neutral native
    container for an element spanning two Levels.
    """
    if level is None:
        return None
    parents = [
        parent
        for parent in list(getattr(level, "InList", []) or [])
        if is_building(parent)
    ]
    unique = []
    for parent in parents:
        if parent not in unique:
            unique.append(parent)
    return unique[0] if len(unique) == 1 else None


def create_native_stair(
    doc,
    context,
    plan,
    structure_thickness_mm=150.0,
    create_plan=True,
    railings_mode="native",
    prevent_duplicate=True,
):
    """Create one native Arch Stairs object and optional documentary PLAN.

    The Arch stair remains the geometry authority. FA only orchestrates native
    bases, BIM context, duplicate protection, source containment and a temporary
    native-railing visibility policy for FreeCAD 1.1.3.
    """
    lower = context["lower"]
    upper = context["upper"]
    if bool(prevent_duplicate):
        duplicates = find_existing_stairs_between_slabs(doc, lower, upper)
        if duplicates:
            labels = ", ".join(str(getattr(obj, "Label", getattr(obj, "Name", "Stair"))) for obj in duplicates)
            raise UserFacingError(
                "Ya existe una escalera FA entre las mismas losas: %s." % labels
            )

    lower_level = context.get("lower_level")
    upper_level = context.get("upper_level")
    source = context["source"]
    if lower_level is not None:
        # Root support paths are adopted into the standard Level auxiliary
        # branch. Paths already living in a deliberate user/demo group remain
        # untouched by adopt_auxiliary_sources().
        adopt_auxiliary_sources(doc, lower_level, [source], allow_any_type=True)
        tag_target_level(lower_level, source)

    bases = _make_base_objects(doc, plan)
    width = float(plan["input"]["width_mm"])
    total_h = float(plan["input"]["upper_top_z_mm"] - plan["input"]["lower_top_z_mm"])
    total_steps = int(plan["steps"]["total_risers"])

    master = Arch.makeStairs(
        baseobj=list(bases),
        width=width,
        height=total_h,
        steps=total_steps,
        name=TOOL_LABEL,
    )
    if master is None:
        raise RuntimeError("Arch.makeStairs no devolvio un objeto.")

    segments = _stair_segments(master)
    if len(segments) != 3:
        raise RuntimeError(
            "FreeCAD no creo los tres segmentos nativos esperados mediante Arch.makeStairs. "
            "Segmentos detectados: %d." % len(segments)
        )

    flight1, landing, flight2 = segments
    step_data = plan["steps"]
    for stair in segments:
        _set_if_possible(stair, "Width", width)
        _set_if_possible(stair, "Align", "Center")
        _set_if_possible(stair, "Structure", "Massive")
        _set_if_possible(stair, "StructureThickness", float(structure_thickness_mm))
        _set_if_possible(stair, "TreadDepthEnforce", 0.0)
        _set_if_possible(stair, "RiserHeightEnforce", 0.0)
        _set_if_possible(stair, "Landings", "None")

    _set_if_possible(flight1, "NumberOfSteps", int(step_data["flight1_risers"]))
    _set_if_possible(landing, "NumberOfSteps", 1)
    _set_if_possible(flight2, "NumberOfSteps", int(step_data["flight2_risers"]))
    try:
        landing.WidthOfLanding = [width]
    except Exception:
        pass

    lower_info = context["lower_info"]
    upper_info = context["upper_info"]
    if lower_info["thickness"] > 1.0:
        _set_if_possible(flight1, "DownSlabThickness", lower_info["thickness"])
    if upper_info["thickness"] > 1.0:
        _set_if_possible(flight2, "UpSlabThickness", upper_info["thickness"])
        _set_if_possible(flight2, "ConnectionEndStairsUp", "toSlabThickness")

    master.Label = TOOL_LABEL
    _tag_master(master, context, plan, railings_mode=railings_mode)

    # A stair spanning two storeys keeps explicit FA_LowerLevel/FA_UpperLevel
    # links. Placing that same master inside lower_level would create the cycle
    # lower_level -> master -> lower_level in FreeCAD's dependency graph.
    # Keep the native spatial organization by placing the spanning master in the
    # common Building instead; bases and PLAN documentation remain level-local.
    building = _building_parent_for_level(lower_level) or _building_parent_for_level(upper_level)
    if building is not None:
        add_to_container(building, master)
        if lower_level is not None:
            tag_target_level(lower_level, master)
    elif lower_level is not None:
        tag_target_level(lower_level, master)
        warn(
            "Escalera inter-nivel creada sin Building padre unico; se deja sin contenedor "
            "para evitar un ciclo DAG con FA_LowerLevel."
        )
    elif upper_level is not None:
        warn("Escalera creada sin Level inferior resuelto; se conservan los enlaces a las losas.")

    if lower_level is not None:
        for base in bases:
            tag_target_level(lower_level, base)

    for obj in tuple(segments) + (master,):
        try:
            obj.recompute()
        except Exception:
            pass
    doc.recompute()

    railings, railing_status = _apply_railing_policy(master, segments, railings_mode)

    for base in bases:
        try:
            base.ViewObject.Visibility = False
        except Exception:
            pass

    plan_obj = _make_plan2d(doc, master, plan) if bool(create_plan) else None
    if plan_obj is not None and lower_level is not None:
        add_to_level(lower_level, plan_obj)
    doc.recompute()
    return {
        "master": master,
        "segments": segments,
        "bases": bases,
        "railings": railings,
        "railing_status": railing_status,
        "plan2d": plan_obj,
        "source": source,
        "lower_level": lower_level,
        "upper_level": upper_level,
    }

