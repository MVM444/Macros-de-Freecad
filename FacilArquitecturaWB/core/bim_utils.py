"""BIM helpers for FacilArquitecturaWB.

Descripcion: usa herramientas existentes Arch/BIM para generar objetos arquitectonicos.
Objetivo: crear muros y aberturas nativos con fuentes Sketch parametricas directas.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 21:24 UTC-06:00.
Version: 0.3.0.
Instrucciones de mantenimiento: no crear objetos BIM propios si Arch/BIM ya ofrece
la herramienta; conservar las fuentes y el destino Building Storey mediante enlaces.
"""

from __future__ import annotations

import re

import FreeCAD

from .command_errors import UserFacingError
from .bim_structure_utils import add_to_level, is_level
from .naming import safe_name
from .project_structure import find_by_name_or_label, msg, set_prop, warn

try:
    import Arch
except Exception:  # pragma: no cover - depende del runtime de FreeCAD
    Arch = None


def supports_arch_window() -> bool:
    """Return whether this FreeCAD build exposes the native Arch window factory."""
    return Arch is not None and hasattr(Arch, "makeWindow")


def supports_arch_window_preset() -> bool:
    """Return whether this FreeCAD build exposes native BIM window presets."""
    return Arch is not None and hasattr(Arch, "makeWindowPreset")


def make_arch_window(baseobj=None, width=None, height=None, parts=None, name=None):
    """Version-isolated wrapper for the native BIM/Arch window factory.

    FreeCAD 1.1.x exposes this factory from ``Arch`` even though its
    implementation lives in ``ArchWindow``. Callers must still define placement
    and the wall host explicitly.
    """
    if not supports_arch_window():
        raise UserFacingError("Arch.makeWindow no esta disponible en esta instalacion de FreeCAD.")
    try:
        return Arch.makeWindow(
            baseobj=baseobj,
            width=width,
            height=height,
            parts=parts,
            name=name,
        )
    except TypeError:
        return Arch.makeWindow(baseobj, width, height, parts, name)


def make_arch_window_preset(preset, **kwargs):
    """Version-isolated wrapper for native BIM door and window presets."""
    if not supports_arch_window_preset():
        raise UserFacingError(
            "Arch.makeWindowPreset no esta disponible en esta instalacion de FreeCAD."
        )
    return Arch.makeWindowPreset(str(preset), **kwargs)


GENERATED_BY_WALLS = "FA_CreateWallsBIM"
WALL_METADATA_GROUP = "FacilArquitectura"
MASTER_WALL_SPECS = {
    "Sketch_Muros_Ext_200": ("exterior", 200.0, "ext_wall_thickness_mm"),
    "Sketch_Muros_Int_100": ("interior", 100.0, "int_wall_thickness_mm"),
}
THICKNESS_PATTERN = re.compile(r"Espesor[_ ]([0-9]+(?:[.,][0-9]+)?)mm", re.IGNORECASE)


def collect_wall_sketches_from_selection(objects):
    """Collect selected wall sketches, including sources linked by BIM walls."""
    result = []
    pending = list(objects or [])
    seen = set()
    while pending:
        obj = pending.pop(0)
        name = str(getattr(obj, "Name", "") or "")
        identity = name or str(id(obj))
        if identity in seen:
            continue
        seen.add(identity)

        if _is_wall_sketch(obj):
            result.append(obj)
            try:
                pending.extend(list(getattr(obj, "FA_RelatedCenterlineSketches", []) or []))
            except Exception:
                pass
            continue

        for attr in ("FA_SourceSketch", "Base", "Group", "Objects"):
            try:
                pending.extend(_linked_objects(getattr(obj, attr, None)))
            except Exception:
                pass
    return result


def collect_any_sketches_from_selection(objects):
    """Collect any selected Sketcher object, including sketches inside groups.

    Unlike :func:`collect_wall_sketches_from_selection`, this function does not
    require Facil Arquitectura metadata. It is intended only for an explicit
    conversion workflow that asks the user for the missing wall parameters.
    """
    result = []
    pending = list(objects or [])
    seen = set()
    while pending:
        obj = pending.pop(0)
        name = str(getattr(obj, "Name", "") or "")
        identity = name or str(id(obj))
        if identity in seen:
            continue
        seen.add(identity)
        if _is_sketch(obj):
            result.append(obj)
            try:
                pending.extend(list(getattr(obj, "FA_RelatedCenterlineSketches", []) or []))
            except Exception:
                pass
            continue
        for attr in ("FA_SourceSketch", "Base", "Group", "Objects"):
            try:
                pending.extend(_linked_objects(getattr(obj, attr, None)))
            except Exception:
                pass
    return result


def _linked_objects(value):
    """Normalize FreeCAD link, LinkSub and group-like property values."""
    if value is None:
        return []
    if isinstance(value, tuple):
        # App::PropertyLinkSub is commonly exposed as ``(object, ["Edge1"])``.
        if value and hasattr(value[0], "TypeId"):
            return [value[0]]
        result = []
        for item in value:
            result.extend(_linked_objects(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_linked_objects(item))
        return result
    if hasattr(value, "TypeId") or hasattr(value, "Geometry"):
        return [value]
    return []


def sketches_requiring_wall_metadata(sketches):
    """Return sketches that cannot yet be used as parametric wall centerlines."""
    result = []
    for sketch in sketches or []:
        missing_thickness = wall_thickness_from_sketch(sketch) <= 0.0
        missing_height = _quantity_value(getattr(sketch, "FA_WallHeight", 0.0)) <= 0.0
        if not _is_wall_sketch(sketch) or missing_thickness or missing_height:
            result.append(sketch)
    return result


def prepare_sketches_as_wall_centerlines(
    sketches,
    thickness: float,
    height: float,
    wall_type: str = "interior",
):
    """Add missing wall metadata to arbitrary sketches without altering geometry.

    Existing positive dimensions are preserved. Classification properties are
    normalized only for sketches that were not already valid wall centerlines.
    The operation is idempotent and safe to include in the command transaction.
    """
    thickness = float(thickness)
    height = float(height)
    if thickness <= 0.0:
        raise UserFacingError("El espesor del muro debe ser mayor que cero.")
    if height <= 0.0:
        raise UserFacingError("La altura del muro debe ser mayor que cero.")
    normalized_type = str(wall_type or "interior").strip().lower() or "interior"
    prepared = []
    for sketch in sketches or []:
        if not _is_sketch(sketch):
            continue
        if _geometry_count(sketch) == 0:
            warn("Sketch sin geometria omitido: %s" % _object_label(sketch))
            continue
        was_wall_sketch = _is_wall_sketch(sketch)
        previous_role = str(getattr(sketch, "FA_Role", "") or "").strip()
        previous_element_type = str(getattr(sketch, "FA_ElementType", "") or "").strip()
        if not was_wall_sketch:
            if previous_role and previous_role.lower() not in ("centerlines", "grid_clipped_lines"):
                set_prop(
                    sketch,
                    "App::PropertyString",
                    "FA_PreviousRole",
                    WALL_METADATA_GROUP,
                    "Rol anterior antes de convertir a eje de muro",
                    previous_role,
                )
            if previous_element_type and previous_element_type.lower() not in ("muro", "wall", normalized_type):
                set_prop(
                    sketch,
                    "App::PropertyString",
                    "FA_PreviousElementType",
                    WALL_METADATA_GROUP,
                    "Tipo anterior antes de convertir a eje de muro",
                    previous_element_type,
                )
            set_prop(
                sketch,
                "App::PropertyString",
                "FA_Role",
                WALL_METADATA_GROUP,
                "Rol",
                "centerlines",
            )
            set_prop(
                sketch,
                "App::PropertyString",
                "FA_CenterlineKind",
                WALL_METADATA_GROUP,
                "Tipo de eje",
                "walls",
            )
            set_prop(
                sketch,
                "App::PropertyString",
                "FA_ElementType",
                WALL_METADATA_GROUP,
                "Tipo de elemento",
                normalized_type,
            )
            set_prop(
                sketch,
                "App::PropertyBool",
                "FA_ConvertedToWallCenterline",
                WALL_METADATA_GROUP,
                "Convertido explicitamente a eje de muro",
                True,
            )
            set_prop(
                sketch,
                "App::PropertyString",
                "FA_ConvertedBy",
                WALL_METADATA_GROUP,
                "Comando de conversion",
                GENERATED_BY_WALLS,
            )
        current_thickness = wall_thickness_from_sketch(sketch)
        if current_thickness <= 0.0:
            set_prop(
                sketch,
                "App::PropertyLength",
                "FA_WallThickness",
                WALL_METADATA_GROUP,
                "Espesor parametrico del muro BIM",
                thickness,
            )
        current_height = _quantity_value(getattr(sketch, "FA_WallHeight", 0.0))
        if current_height <= 0.0:
            set_prop(
                sketch,
                "App::PropertyLength",
                "FA_WallHeight",
                WALL_METADATA_GROUP,
                "Altura parametrica del muro BIM",
                height,
            )
        prepared.append(sketch)
        if not was_wall_sketch:
            msg(
                "Sketch convertido a eje de muro: %s | espesor %.1f mm | altura %.1f mm"
                % (
                    _object_label(sketch),
                    wall_thickness_from_sketch(sketch),
                    _quantity_value(getattr(sketch, "FA_WallHeight", height)),
                )
            )
    return prepared


def collect_master_wall_sketches(doc):
    """Return the legacy exterior/interior master sketches when no selection is supplied."""
    result = []
    for label in MASTER_WALL_SPECS:
        sketch = find_by_name_or_label(doc, label, label)
        if sketch is not None and _geometry_count(sketch) > 0:
            result.append(sketch)
    return result


def create_walls_from_centerline_sketches(
    doc, bim_group, sketches, params: dict, target_level=None
):
    """Create one parametric Arch Wall for each selected centerline thickness sketch."""
    if Arch is None or not hasattr(Arch, "makeWall"):
        raise UserFacingError("Arch/BIM no esta disponible. Active o instale el Workbench BIM/Arch.")

    usable = []
    seen = set()
    for sketch in sketches or []:
        name = str(getattr(sketch, "Name", "") or "")
        if not name or name in seen or not _is_wall_sketch(sketch):
            continue
        seen.add(name)
        if _geometry_count(sketch) == 0:
            warn("Sketch sin geometria omitido: %s" % _object_label(sketch))
            continue
        usable.append(sketch)
    if not usable:
        raise UserFacingError("No hay Sketches de centros de muro utilizables en la seleccion.")

    removed = remove_previous_generated_walls(doc, bim_group, source_sketches=usable)
    if removed:
        msg("Muros BIM anteriores reemplazados para los sketches seleccionados: %d" % removed)

    default_height = float(params.get("wall_height_mm", 3000.0))
    created = []
    for sketch in usable:
        thickness = wall_thickness_from_sketch(sketch, params=params)
        if thickness <= 0.0:
            warn("No se pudo determinar el espesor de %s" % _object_label(sketch))
            continue
        height = _ensure_sketch_wall_parameters(sketch, thickness, default_height)
        wall_type = _wall_type_from_sketch(sketch)
        wall_name = safe_name("FA_Wall_" + _object_label(sketch), "FA_Wall")
        wall = _make_arch_wall(sketch, wall_name, thickness, height)
        wall.Label = "Muro BIM - " + _object_label(sketch)
        if target_level is not None:
            add_to_level(target_level, wall, source_sketch=sketch)
        elif is_level(bim_group):
            add_to_level(bim_group, wall, source_sketch=sketch)
        else:
            try:
                bim_group.addObject(wall)
            except Exception:
                pass
        _tag_wall(wall, sketch, wall_type, thickness, height)
        _link_wall_parameters(wall, sketch)
        created.append(wall)
        msg(
            "Muro BIM creado: %s | espesor %.1f mm | altura %.1f mm | base %s"
            % (wall.Label, thickness, height, _object_label(sketch))
        )
    if not created:
        raise UserFacingError("No fue posible crear muros BIM desde los sketches seleccionados.")
    return created


def create_walls_from_master_sketches(doc, bim_group, params: dict, target_level=None):
    """Compatibility wrapper for the original exterior/interior master sketch flow."""
    sketches = collect_master_wall_sketches(doc)
    if not sketches:
        raise UserFacingError("No se encontraron sketches maestros de muro con geometria.")
    return create_walls_from_centerline_sketches(
        doc, bim_group, sketches, params, target_level=target_level
    )


def _geometry_count(sketch) -> int:
    try:
        return len(list(getattr(sketch, "Geometry", []) or []))
    except Exception:
        return 0


def remove_previous_generated_walls(doc, bim_group, source_sketches=None) -> int:
    """Remove generated walls, optionally limited to the supplied source sketches."""
    source_names = {
        str(getattr(sketch, "Name", "") or "")
        for sketch in (source_sketches or [])
        if getattr(sketch, "Name", None)
    }
    candidates = []
    for obj in list(getattr(bim_group, "Group", []) or []) + list(doc.Objects):
        props = set(getattr(obj, "PropertiesList", []) or [])
        if "FA_GeneratedBy" in props and str(getattr(obj, "FA_GeneratedBy", "")) == GENERATED_BY_WALLS:
            if source_names:
                source = getattr(obj, "FA_SourceSketch", None)
                if str(getattr(source, "Name", "") or "") not in source_names:
                    continue
            if obj not in candidates:
                candidates.append(obj)
    count = 0
    for obj in candidates:
        try:
            if doc.getObject(obj.Name) is not None:
                doc.removeObject(obj.Name)
                count += 1
        except Exception:
            pass
    return count


def _make_arch_wall(sketch, name: str, thickness: float, height: float):
    try:
        return Arch.makeWall(sketch, width=float(thickness), height=float(height), name=name)
    except TypeError:
        return Arch.makeWall(sketch, float(thickness), float(height), name=name)


def wall_thickness_from_sketch(sketch, params=None) -> float:
    """Read detected wall thickness from the sketch property, label or legacy master name."""
    label = _object_label(sketch)
    legacy = MASTER_WALL_SPECS.get(label)
    if legacy and params:
        try:
            configured = float(params.get(legacy[2], legacy[1]))
            if configured > 0.0:
                return configured
        except Exception:
            pass
    value = _quantity_value(getattr(sketch, "FA_WallThickness", 0.0))
    if value > 0.0:
        return value
    match = THICKNESS_PATTERN.search(label)
    if match:
        try:
            return float(match.group(1).replace(",", "."))
        except Exception:
            pass
    return float(legacy[1]) if legacy else 0.0


def _is_wall_sketch(obj) -> bool:
    if obj is None:
        return False
    kind = str(getattr(obj, "FA_CenterlineKind", "") or "").strip().lower()
    element_type = str(getattr(obj, "FA_ElementType", "") or "").strip().lower()
    if kind == "columns" or element_type in ("columnas", "columns"):
        return False
    label = _object_label(obj)
    role = str(getattr(obj, "FA_Role", "") or "").strip().lower()
    if not _is_sketch(obj):
        return False
    if label in MASTER_WALL_SPECS:
        return True
    compatible_roles = ("centerlines", "grid_clipped_lines")
    return (role in compatible_roles or label.startswith("Sketch_Centros")) and wall_thickness_from_sketch(obj) > 0.0


def _is_sketch(obj) -> bool:
    """Return True only for Sketcher objects, including lightweight test doubles."""
    if obj is None:
        return False
    type_id = str(getattr(obj, "TypeId", "") or "")
    return type_id.startswith("Sketcher::") or (not type_id and hasattr(obj, "Geometry"))


def _ensure_sketch_wall_parameters(sketch, thickness: float, default_height: float) -> float:
    if not hasattr(sketch, "FA_WallThickness"):
        set_prop(
            sketch,
            "App::PropertyLength",
            "FA_WallThickness",
            "FacilArquitectura",
            "Espesor parametrico del muro BIM",
            float(thickness),
        )
    else:
        try:
            sketch.FA_WallThickness = float(thickness)
        except Exception:
            pass
    current_height = _quantity_value(getattr(sketch, "FA_WallHeight", 0.0))
    if not hasattr(sketch, "FA_WallHeight"):
        set_prop(
            sketch,
            "App::PropertyLength",
            "FA_WallHeight",
            "FacilArquitectura",
            "Altura parametrica del muro BIM",
            float(default_height),
        )
        current_height = float(default_height)
    elif current_height <= 0.0:
        try:
            sketch.FA_WallHeight = float(default_height)
            current_height = float(default_height)
        except Exception:
            pass
    return current_height if current_height > 0.0 else float(default_height)


def _link_wall_parameters(wall, sketch) -> None:
    if not hasattr(wall, "setExpression"):
        return
    sketch_name = str(getattr(sketch, "Name", "") or "")
    if not sketch_name:
        return
    for wall_property, sketch_property in (("Width", "FA_WallThickness"), ("Height", "FA_WallHeight")):
        try:
            wall.setExpression(wall_property, "%s.%s" % (sketch_name, sketch_property))
        except Exception as exc:
            warn("No se pudo vincular %s de %s: %s" % (wall_property, getattr(wall, "Name", "Muro"), exc))


def _wall_type_from_sketch(sketch) -> str:
    label = _object_label(sketch)
    if label in MASTER_WALL_SPECS:
        return MASTER_WALL_SPECS[label][0]
    return str(getattr(sketch, "FA_ElementType", "") or getattr(sketch, "FA_SourceSelection", "") or "muro")


def _quantity_value(value) -> float:
    try:
        return float(getattr(value, "Value", value))
    except Exception:
        return 0.0


def _object_label(obj) -> str:
    return str(getattr(obj, "Label", getattr(obj, "Name", "Sketch")) or "Sketch")


def _tag_wall(wall, sketch, wall_type: str, thickness: float, height: float) -> None:
    set_prop(wall, "App::PropertyLink", "FA_SourceSketch", "FacilArquitectura", "Sketch fuente", sketch)
    set_prop(wall, "App::PropertyString", "FA_WallType", "FacilArquitectura", "Tipo de muro", wall_type)
    set_prop(wall, "App::PropertyFloat", "FA_Thickness_mm", "FacilArquitectura", "Espesor", thickness)
    set_prop(wall, "App::PropertyFloat", "FA_Height_mm", "FacilArquitectura", "Altura", height)
    set_prop(wall, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generado por", GENERATED_BY_WALLS)
    set_prop(wall, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "wall")
    try:
        wall.IfcType = "Wall"
    except Exception:
        pass
    try:
        color = (0.72, 0.72, 0.72) if wall_type == "exterior" else (0.78, 0.84, 0.90)
        wall.ViewObject.ShapeColor = color
        wall.ViewObject.LineColor = color
    except Exception:
        pass
