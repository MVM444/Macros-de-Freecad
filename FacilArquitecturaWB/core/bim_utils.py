"""BIM helpers for FacilArquitecturaWB.

Descripcion: usa herramientas existentes Arch/BIM para generar objetos arquitectonicos.
Fecha: 2026-07-15
Version: 0.2.0
Instrucciones: no crear objetos BIM propios si Arch/BIM ya tiene herramientas.
"""

from __future__ import annotations

import re

import FreeCAD

from .command_errors import UserFacingError
from .naming import safe_name
from .project_structure import find_by_name_or_label, msg, set_prop, warn

try:
    import Arch
except Exception:  # pragma: no cover - depende del runtime de FreeCAD
    Arch = None


def supports_arch_window() -> bool:
    """Return whether this FreeCAD build exposes the native Arch window factory."""
    return Arch is not None and hasattr(Arch, "makeWindow")


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


GENERATED_BY_WALLS = "FA_CreateWallsBIM"
MASTER_WALL_SPECS = {
    "Sketch_Muros_Ext_200": ("exterior", 200.0, "ext_wall_thickness_mm"),
    "Sketch_Muros_Int_100": ("interior", 100.0, "int_wall_thickness_mm"),
}
THICKNESS_PATTERN = re.compile(r"Espesor[_ ]([0-9]+(?:[.,][0-9]+)?)mm", re.IGNORECASE)


def collect_wall_sketches_from_selection(objects):
    """Collect selected wall centerline sketches, including related thickness groups."""
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

        for attr in ("Group", "Objects"):
            try:
                pending.extend(list(getattr(obj, attr, []) or []))
            except Exception:
                pass
    return result


def collect_master_wall_sketches(doc):
    """Return the legacy exterior/interior master sketches when no selection is supplied."""
    result = []
    for label in MASTER_WALL_SPECS:
        sketch = find_by_name_or_label(doc, label, label)
        if sketch is not None and _geometry_count(sketch) > 0:
            result.append(sketch)
    return result


def create_walls_from_centerline_sketches(doc, bim_group, sketches, params: dict):
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


def create_walls_from_master_sketches(doc, bim_group, params: dict):
    """Compatibility wrapper for the original exterior/interior master sketch flow."""
    sketches = collect_master_wall_sketches(doc)
    if not sketches:
        raise UserFacingError("No se encontraron sketches maestros de muro con geometria.")
    return create_walls_from_centerline_sketches(doc, bim_group, sketches, params)


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
    is_sketch = str(getattr(obj, "TypeId", "") or "").startswith("Sketcher::") or hasattr(obj, "Geometry")
    if not is_sketch:
        return False
    if label in MASTER_WALL_SPECS:
        return True
    compatible_roles = ("centerlines", "grid_clipped_lines")
    return (role in compatible_roles or label.startswith("Sketch_Centros")) and wall_thickness_from_sketch(obj) > 0.0


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
        color = (0.72, 0.72, 0.72) if wall_type == "exterior" else (0.78, 0.84, 0.90)
        wall.ViewObject.ShapeColor = color
        wall.ViewObject.LineColor = color
    except Exception:
        pass
