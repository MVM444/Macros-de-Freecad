"""Quick example scene generators for GameEngineExportWB.

Descripcion rapida: genera escenas BIM pequenas para probar exportacion X3D.
Instrucciones clave:
- Usar sketches como fuente parametrica de paredes y buques.
- Crear Arch Wall cuando el modulo Arch este disponible.
- Mantener propiedades CGE/TestExample utiles para filtrar o exportar.
"""

from __future__ import annotations

import json
import random
import math
import time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import FreeCAD
import Part

try:
    import Arch
except Exception:  # pragma: no cover - depende de FreeCAD runtime
    Arch = None


LOG_PREFIX = "[GAMEEXPORT] "
RESULT_PREFIX = "GEE_QuickExample_"
EXAMPLE_OBJECT_PREFIXES = (
    RESULT_PREFIX,
    "GEE_SK_",
    "GEE_ArchWall_",
    "GEE_Cutter_",
    "GEE_Terrain_",
    "GEE_Building_Floor_",
    "AI_Contexto_QuickExample",
)
EXAMPLE_GROUP_LABELS = {"Sketches", "ArchWalls", "OpeningCutters", "SiteAndFloors"}

DEFAULT_EXT_WALL_MM = 200.0
DEFAULT_INT_WALL_MM = 100.0
DEFAULT_WALL_HEIGHT_MM = 3000.0
DEFAULT_DOOR_HEIGHT_MM = 2100.0
DEFAULT_WINDOW_SILL_MM = 900.0
DEFAULT_WINDOW_HEIGHT_MM = 1200.0
DEFAULT_TERRAIN_MARGIN_MM = 9000.0
DEFAULT_TERRAIN_VARIATION_MM = 650.0
DEFAULT_FLOOR_THICKNESS_MM = 180.0
DEFAULT_FLOOR_OVERHANG_MM = 350.0
DEFAULT_FLOOR_TOP_Z_MM = 60.0
DEFAULT_FLATTEN_PAD = True
DEFAULT_PAD_MARGIN_MM = 1800.0
DEFAULT_PAD_Z_MM = -260.0

Segment = Tuple[float, float, float, float]


def _info(message: str) -> None:
    FreeCAD.Console.PrintMessage(LOG_PREFIX + message + "\n")


def _warn(message: str) -> None:
    FreeCAD.Console.PrintWarning(LOG_PREFIX + message + "\n")


def _safe_name(value: str) -> str:
    text = str(value).strip()
    for old, new in {
        " ": "_",
        "-": "_",
        "/": "_",
        "\\": "_",
        ".": "_",
        "(": "",
        ")": "",
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }.items():
        text = text.replace(old, new)
    return "".join(ch for ch in text if ch.isalnum() or ch == "_") or "Object"


def _set_prop(obj, prop_type: str, name: str, group: str, desc: str, value) -> None:
    try:
        if not hasattr(obj, name):
            obj.addProperty(prop_type, name, group, desc)
        setattr(obj, name, value)
    except Exception:
        pass


def _set_view(obj, color=None, transparency: Optional[int] = None, line_width: Optional[float] = None) -> None:
    try:
        if color is not None:
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineColor = color
        if transparency is not None:
            obj.ViewObject.Transparency = transparency
        if line_width is not None:
            obj.ViewObject.LineWidth = line_width
    except Exception:
        pass


def _walk_related_objects(root):
    pending = [root]
    seen = set()
    while pending:
        obj = pending.pop()
        name = str(getattr(obj, "Name", ""))
        if not name or name in seen:
            continue
        seen.add(name)
        yield obj
        pending.extend(list(getattr(obj, "Group", []) or []))
        pending.extend(list(getattr(obj, "OutList", []) or []))


def _tag_quick_example_tree(root, building_type: str, seed: int, variant: str = "default") -> None:
    root_name = str(getattr(root, "Name", ""))
    for obj in _walk_related_objects(root):
        _set_prop(obj, "App::PropertyBool", "GEE_QuickExampleObject", "GameEngineExport", "Objeto de ejemplo rapido", True)
        _set_prop(obj, "App::PropertyString", "GEE_QuickExampleRoot", "GameEngineExport", "Raiz del ejemplo rapido", root_name)
        _set_prop(obj, "App::PropertyString", "GEE_ExampleType", "GameEngineExport", "Tipo de ejemplo", building_type)
        _set_prop(obj, "App::PropertyString", "GEE_ExampleVariant", "GameEngineExport", "Variante del ejemplo", variant)
        _set_prop(obj, "App::PropertyInteger", "GEE_Seed", "GameEngineExport", "Semilla", int(seed))


def _edge_key(x1: float, y1: float, x2: float, y2: float) -> Segment:
    values = [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]
    if values[0] == values[2] and values[1] > values[3]:
        values = [values[2], values[3], values[0], values[1]]
    if values[1] == values[3] and values[0] > values[2]:
        values = [values[2], values[3], values[0], values[1]]
    return tuple(values)  # type: ignore[return-value]


def _line(sketch, segment: Segment, construction: bool = False) -> None:
    x1, y1, x2, y2 = segment
    geo = Part.LineSegment(FreeCAD.Vector(x1, y1, 0), FreeCAD.Vector(x2, y2, 0))
    try:
        sketch.addGeometry(geo, construction)
    except TypeError:
        sketch.addGeometry(geo)


def _make_sketch(doc, group, name: str, label: str, role: str, color) -> object:
    sketch = doc.addObject("Sketcher::SketchObject", _safe_name(name))
    sketch.Label = label
    group.addObject(sketch)
    _set_prop(sketch, "App::PropertyString", "Role", "GameEngineExport", "Rol semantico", role)
    _set_prop(sketch, "App::PropertyString", "GEE_Role", "GameEngineExport", "Rol GameEngineExport", role)
    _set_view(sketch, color=color, line_width=2.0)
    return sketch


def _make_opening_solid(centerline: Sequence[float], depth: float, height: float, z_base: float):
    x1, y1, x2, y2 = [float(v) for v in centerline]
    if abs(y1 - y2) < 0.01:
        return Part.makeBox(abs(x2 - x1), depth, height, FreeCAD.Vector(min(x1, x2), y1 - depth / 2.0, z_base))
    return Part.makeBox(depth, abs(y2 - y1), height, FreeCAD.Vector(x1 - depth / 2.0, min(y1, y2), z_base))


def _compound_or_none(shapes: Iterable[object]):
    valid = [shape for shape in shapes if shape is not None]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0]
    return Part.makeCompound(valid)


def _make_box_feature(doc, group, name: str, shape, role: str, color, transparency: int = 0):
    obj = doc.addObject("Part::Feature", _safe_name(name))
    obj.Label = name
    obj.Shape = shape
    group.addObject(obj)
    _set_prop(obj, "App::PropertyString", "Role", "GameEngineExport", "Rol semantico", role)
    _set_prop(obj, "App::PropertyString", "GEE_Role", "GameEngineExport", "Rol GameEngineExport", role)
    _set_view(obj, color=color, transparency=transparency)
    return obj


def _make_bim_structure_from_shape(doc, group, name: str, shape, role: str, color, transparency: int = 0):
    """Create an Arch Structure from a base solid when possible, else a Part feature."""
    base = _make_box_feature(doc, group, name + "_Base", shape, role + "_base", color, transparency=80)
    try:
        base.ViewObject.Visibility = False
    except Exception:
        pass
    if Arch is None or not hasattr(Arch, "makeStructure"):
        base.Label = name
        _set_prop(base, "App::PropertyBool", "GEE_BIMFallback", "GameEngineExport", "Usa respaldo Part", True)
        _set_view(base, color=color, transparency=transparency)
        try:
            base.ViewObject.Visibility = True
        except Exception:
            pass
        return base
    try:
        structure = Arch.makeStructure(base, name=_safe_name(name))
    except TypeError:
        try:
            structure = Arch.makeStructure(base)
        except Exception:
            structure = None
    except Exception:
        structure = None
    if structure is None:
        base.Label = name
        _set_prop(base, "App::PropertyBool", "GEE_BIMFallback", "GameEngineExport", "Usa respaldo Part", True)
        _set_view(base, color=color, transparency=transparency)
        try:
            base.ViewObject.Visibility = True
        except Exception:
            pass
        return base
    structure.Label = name
    group.addObject(structure)
    _set_prop(structure, "App::PropertyString", "Role", "GameEngineExport", "Rol semantico", role)
    _set_prop(structure, "App::PropertyString", "GEE_Role", "GameEngineExport", "Rol GameEngineExport", role)
    _set_prop(structure, "App::PropertyBool", "GEE_BIMStructure", "GameEngineExport", "Creado con Arch.makeStructure", True)
    _set_view(structure, color=color, transparency=transparency)
    return structure


def _terrain_height(x: float, y: float, rng: random.Random, variation: float) -> float:
    # Small deterministic undulation; enough to test non-flat ground without burying the building.
    return (
        variation * 0.35 * random.Random(int(x * 0.03 + y * 0.07 + rng.random() * 10000)).uniform(-1.0, 1.0)
        + variation * 0.35 * math.sin(x / 6500.0)
        + variation * 0.25 * math.cos(y / 5200.0)
    )


def _make_terrain_shape(
    width: float,
    depth: float,
    margin: float,
    variation: float,
    rng: random.Random,
    flatten_pad: bool,
    pad_margin: float,
    pad_z: float,
):
    x0 = -margin
    x1 = width + margin
    y0 = -margin
    y1 = depth + margin

    def terrain_coords(start: float, flat_start: float, core_start: float, core_end: float, flat_end: float, end: float):
        values = [
            start,
            (start + flat_start) / 2.0,
            flat_start,
            core_start,
            (core_start + core_end) / 2.0,
            core_end,
            flat_end,
            (flat_end + end) / 2.0,
            end,
        ]
        clamped = [min(max(v, start), end) for v in values]
        return sorted({round(v, 1) for v in clamped})

    flat_x0 = max(x0, -pad_margin)
    flat_x1 = min(x1, width + pad_margin)
    flat_y0 = max(y0, -pad_margin)
    flat_y1 = min(y1, depth + pad_margin)
    xs = terrain_coords(x0, flat_x0, 0.0, width, flat_x1, x1)
    ys = terrain_coords(y0, flat_y0, 0.0, depth, flat_y1, y1)

    points = []
    for y in ys:
        row_points = []
        for x in xs:
            inside_pad = flat_x0 <= x <= flat_x1 and flat_y0 <= y <= flat_y1
            z = pad_z if flatten_pad and inside_pad else _terrain_height(x, y, rng, variation)
            row_points.append(FreeCAD.Vector(x, y, z))
        points.append(row_points)
    faces = []
    for row in range(len(ys) - 1):
        for col in range(len(xs) - 1):
            p00 = points[row][col]
            p10 = points[row][col + 1]
            p01 = points[row + 1][col]
            p11 = points[row + 1][col + 1]
            faces.append(Part.Face(Part.makePolygon([p00, p10, p11, p00])))
            faces.append(Part.Face(Part.makePolygon([p00, p11, p01, p00])))
    return Part.makeCompound(faces)


def _create_site_and_floor(doc, root, width: float, depth: float, rng: random.Random, options: Dict):
    site_group = doc.addObject("App::DocumentObjectGroup", "SiteAndFloors")
    root.addObject(site_group)
    terrain_margin = float(options.get("terrain_margin_mm", DEFAULT_TERRAIN_MARGIN_MM))
    terrain_variation = float(options.get("terrain_variation_mm", DEFAULT_TERRAIN_VARIATION_MM))
    floor_thickness = float(options.get("floor_thickness_mm", DEFAULT_FLOOR_THICKNESS_MM))
    floor_overhang = float(options.get("floor_overhang_mm", DEFAULT_FLOOR_OVERHANG_MM))
    floor_top_z = float(options.get("floor_top_z_mm", DEFAULT_FLOOR_TOP_Z_MM))
    flatten_pad = bool(options.get("flatten_pad", DEFAULT_FLATTEN_PAD))
    pad_margin = float(options.get("pad_margin_mm", DEFAULT_PAD_MARGIN_MM))
    pad_z = float(options.get("pad_z_mm", DEFAULT_PAD_Z_MM))

    terrain = _make_box_feature(
        doc,
        site_group,
        "GEE_Terrain_Irregular",
        _make_terrain_shape(width, depth, terrain_margin, terrain_variation, rng, flatten_pad, pad_margin, pad_z),
        "terrain",
        (0.34, 0.50, 0.28),
        transparency=0,
    )
    _set_prop(terrain, "App::PropertyBool", "CGE_GroundCandidate", "GameEngineExport", "Puede usarse como suelo", True)
    _set_prop(terrain, "App::PropertyBool", "FlattenPad", "GameEngineExport", "Plataforma aplanada bajo edificio", flatten_pad)
    _set_prop(terrain, "App::PropertyFloat", "PadMargin_mm", "GameEngineExport", "Margen de plataforma", pad_margin)
    _set_prop(terrain, "App::PropertyFloat", "PadZ_mm", "GameEngineExport", "Cota de plataforma", pad_z)
    _set_prop(terrain, "App::PropertyFloat", "TerrainMargin_mm", "GameEngineExport", "Margen de terreno", terrain_margin)
    _set_prop(terrain, "App::PropertyFloat", "TerrainVariation_mm", "GameEngineExport", "Variacion vertical", terrain_variation)

    slab_shape = Part.makeBox(
        width + floor_overhang * 2.0,
        depth + floor_overhang * 2.0,
        floor_thickness,
        FreeCAD.Vector(-floor_overhang, -floor_overhang, floor_top_z - floor_thickness),
    )
    slab = _make_bim_structure_from_shape(
        doc,
        site_group,
        "GEE_Building_Floor_Slab",
        slab_shape,
        "building_floor",
        (0.78, 0.74, 0.66),
        transparency=0,
    )
    _set_prop(slab, "App::PropertyFloat", "Thickness_mm", "GameEngineExport", "Espesor de losa", floor_thickness)
    _set_prop(slab, "App::PropertyFloat", "TopZ_mm", "GameEngineExport", "Cota superior de losa", floor_top_z)
    _set_prop(slab, "App::PropertyFloat", "Overhang_mm", "GameEngineExport", "Sobresaliente de losa", floor_overhang)
    return site_group, {"terrain": terrain, "floor_slab": slab}


class SketchOpeningCutterProxy:
    """Parametric cutter that rebuilds solids from a sketch's visible line segments."""

    def __init__(self, sketch=None, depth: float = 250.0, height: float = 2100.0, z_offset: float = 0.0):
        self.Type = "GameEngineExport_SketchOpeningCutter"
        self._fallback_sketch = sketch
        self._fallback_depth = float(depth)
        self._fallback_height = float(height)
        self._fallback_z_offset = float(z_offset)

    def execute(self, obj) -> None:
        sketch = getattr(obj, "SourceSketch", None) or self._fallback_sketch
        if sketch is None:
            return
        depth = float(getattr(obj, "Depth_mm", self._fallback_depth))
        height = float(getattr(obj, "Height_mm", self._fallback_height))
        z_offset = float(getattr(obj, "ZOffset_mm", self._fallback_z_offset))
        placement = getattr(sketch, "Placement", FreeCAD.Placement())
        shapes = []
        for index, geo in enumerate(list(getattr(sketch, "Geometry", []))):
            try:
                if hasattr(sketch, "getConstruction") and sketch.getConstruction(index):
                    continue
            except Exception:
                pass
            if not hasattr(geo, "StartPoint") or not hasattr(geo, "EndPoint"):
                continue
            p1 = placement.multVec(geo.StartPoint)
            p2 = placement.multVec(geo.EndPoint)
            if p1.distanceToPoint(p2) < 50.0:
                continue
            shapes.append(_make_opening_solid([p1.x, p1.y, p2.x, p2.y], depth, height, placement.Base.z + z_offset))
        compound = _compound_or_none(shapes)
        if compound is not None:
            obj.Shape = compound


def _make_cutter(doc, group, name: str, sketch, role: str, depth: float, height: float, z_offset: float, color):
    obj = doc.addObject("Part::FeaturePython", _safe_name(name))
    obj.Label = name
    obj.Proxy = SketchOpeningCutterProxy(sketch, depth, height, z_offset)
    group.addObject(obj)
    _set_prop(obj, "App::PropertyLink", "SourceSketch", "GameEngineExport", "Sketch fuente", sketch)
    _set_prop(obj, "App::PropertyString", "Role", "GameEngineExport", "Rol semantico", role)
    _set_prop(obj, "App::PropertyString", "GEE_Role", "GameEngineExport", "Rol GameEngineExport", role)
    _set_prop(obj, "App::PropertyFloat", "Depth_mm", "GameEngineExport", "Profundidad", float(depth))
    _set_prop(obj, "App::PropertyFloat", "Height_mm", "GameEngineExport", "Altura", float(height))
    _set_prop(obj, "App::PropertyFloat", "ZOffset_mm", "GameEngineExport", "Desfase Z", float(z_offset))
    _set_view(obj, color=color, transparency=80)
    obj.Proxy.execute(obj)
    return obj


def _set_subtractions(wall, cutters: List[object]) -> bool:
    cutters = [c for c in cutters if c is not None]
    if not cutters:
        return False
    for attr in ("Subtractions", "Subtraction"):
        if hasattr(wall, attr):
            try:
                setattr(wall, attr, cutters)
                return True
            except Exception:
                pass
    try:
        current = list(getattr(wall, "Subtractions"))
        wall.Subtractions = current + cutters
        return True
    except Exception:
        return False


def _make_wall(doc, group, name: str, sketch, thickness: float, height: float, wall_kind: str, color):
    if Arch is None:
        raise RuntimeError("No se pudo importar Arch. Active o instale el workbench Arch/BIM.")
    try:
        wall = Arch.makeWall(sketch, width=float(thickness), height=float(height), name=_safe_name(name))
    except TypeError:
        wall = Arch.makeWall(sketch, float(thickness), float(height), name=_safe_name(name))
    wall.Label = name
    group.addObject(wall)
    _set_prop(wall, "App::PropertyString", "Role", "GameEngineExport", "Rol semantico", "arch_wall")
    _set_prop(wall, "App::PropertyString", "GEE_Role", "GameEngineExport", "Rol GameEngineExport", "arch_wall")
    _set_prop(wall, "App::PropertyString", "WallKind", "GameEngineExport", "Tipo de muro", wall_kind)
    _set_prop(wall, "App::PropertyFloat", "Thickness_mm", "GameEngineExport", "Espesor", float(thickness))
    _set_prop(wall, "App::PropertyFloat", "Height_mm", "GameEngineExport", "Altura", float(height))
    _set_prop(wall, "App::PropertyLink", "SourceSketch", "GameEngineExport", "Sketch fuente", sketch)
    _set_view(wall, color=color, transparency=0)
    return wall


def _clear_previous(doc) -> int:
    targets = set()

    def is_quick_example_object(obj) -> bool:
        name = str(getattr(obj, "Name", ""))
        label = str(getattr(obj, "Label", ""))
        props = set(getattr(obj, "PropertiesList", []) or [])
        if name.startswith(RESULT_PREFIX) or label.startswith(RESULT_PREFIX):
            return True
        if "GEE_QuickExampleObject" in props or "GEE_QuickExampleRoot" in props:
            return True
        if "GEE_ExampleType" in props or "GEE_ContextJSON" in props:
            return True
        if any(name.startswith(prefix) or label.startswith(prefix) for prefix in EXAMPLE_OBJECT_PREFIXES):
            return True
        role = str(getattr(obj, "GEE_Role", ""))
        if role == "arch_wall" and "WallKind" in props:
            return True
        source = getattr(obj, "SourceSketch", None)
        source_name = str(getattr(source, "Name", ""))
        source_label = str(getattr(source, "Label", ""))
        return source_name.startswith("GEE_SK_") or source_label.startswith("GEE SK ")

    def mark(obj) -> None:
        if obj is None or obj in targets:
            return
        targets.add(obj)
        for child in list(getattr(obj, "Group", []) or []):
            mark(child)
        for child in list(getattr(obj, "OutList", []) or []):
            mark(child)

    for obj in list(doc.Objects):
        try:
            label = str(getattr(obj, "Label", ""))
            is_example_group = label in EXAMPLE_GROUP_LABELS and any(
                is_quick_example_object(child) for child in list(getattr(obj, "Group", []) or [])
            )
            if is_quick_example_object(obj) or is_example_group:
                mark(obj)
        except Exception:
            pass

    removed = 0
    remaining = {obj.Name for obj in targets if getattr(obj, "Name", None)}
    while remaining:
        progressed = False
        for name in list(remaining):
            obj = doc.getObject(name)
            if obj is None:
                remaining.remove(name)
                progressed = True
                continue
            dependents = [
                dep
                for dep in list(getattr(obj, "InList", []) or [])
                if getattr(dep, "Name", None) in remaining and dep.Name != name
            ]
            if dependents:
                continue
            try:
                doc.removeObject(name)
                removed += 1
            except Exception:
                pass
            remaining.remove(name)
            progressed = True
        if not progressed:
            # Break circular/group references by removing whatever is left.
            for name in list(remaining):
                try:
                    if doc.getObject(name) is not None:
                        doc.removeObject(name)
                        removed += 1
                except Exception:
                    pass
                remaining.remove(name)
    return removed


def _segments_to_json(segments: Sequence[Segment]) -> List[List[float]]:
    return [[round(v, 1) for v in segment] for segment in segments]


def _object_ref(obj) -> Dict[str, str]:
    return {
        "name": str(getattr(obj, "Name", "")),
        "label": str(getattr(obj, "Label", "")),
        "type_id": str(getattr(obj, "TypeId", "")),
    }


def _room(name: str, kind: str, x: float, y: float, width: float, depth: float) -> Dict:
    return {
        "name": name,
        "kind": kind,
        "x_mm": round(float(x), 1),
        "y_mm": round(float(y), 1),
        "w_mm": round(float(width), 1),
        "d_mm": round(float(depth), 1),
        "area_m2": round(float(width) * float(depth) / 1000000.0, 2),
    }


def _create_context_document(doc, root, payload: Dict):
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        obj = doc.addObject("App::TextDocument", "AI_Contexto_QuickExample")
        obj.Label = "AI_Contexto_QuickExample"
        obj.Text = (
            "Contexto generado por GameEngineExportWB Quick Example.\n"
            "Copiar este JSON para revisar o pedir cambios a una IA externa.\n\n"
            + text
        )
    except Exception:
        obj = doc.addObject("App::FeaturePython", "AI_Contexto_QuickExample")
        obj.Label = "AI_Contexto_QuickExample"
        _set_prop(obj, "App::PropertyString", "JSON", "GameEngineExport", "Contexto JSON", text[:32760])
    root.addObject(obj)
    _set_prop(root, "App::PropertyString", "GEE_ContextJSON", "GameEngineExport", "Contexto JSON", text[:32760])
    return obj, text


def _house_segments_banded(width: float, depth: float, rng: random.Random) -> Dict:
    x1 = width * rng.uniform(0.36, 0.43)
    x2 = width * rng.uniform(0.63, 0.72)
    y1 = depth * rng.uniform(0.32, 0.38)
    y2 = depth * rng.uniform(0.58, 0.64)
    exterior = [
        _edge_key(0, 0, width, 0),
        _edge_key(width, 0, width, depth),
        _edge_key(0, depth, width, depth),
        _edge_key(0, 0, 0, depth),
    ]
    interior = [
        _edge_key(x1, 0, x1, y2),
        _edge_key(x2, 0, x2, y2),
        _edge_key(0, y1, width, y1),
        _edge_key(0, y2, width, y2),
        _edge_key(width * 0.62, y2, width * 0.62, depth),
    ]
    doors = [
        _edge_key(width * 0.16, 0, width * 0.16 + 1200, 0),
        _edge_key(x1, y1 * 0.30, x1, y1 * 0.30 + 1400),
        _edge_key(x2, y1 * 0.30, x2, y1 * 0.30 + 1400),
        _edge_key(x1 * 0.42, y1, x1 * 0.42 + 1200, y1),
        _edge_key(x1 + (x2 - x1) * 0.28, y1, x1 + (x2 - x1) * 0.28 + 1200, y1),
        _edge_key(x2 + (width - x2) * 0.28, y1, x2 + (width - x2) * 0.28 + 1200, y1),
        _edge_key(x1, y1 + 450, x1, y1 + 1450),
        _edge_key(x2, y1 + 500, x2, y1 + 1500),
        _edge_key(x1 * 0.40, y2, x1 * 0.40 + 1100, y2),
        _edge_key(x1 + (x2 - x1) * 0.36, y2, x1 + (x2 - x1) * 0.36 + 1100, y2),
        _edge_key(x2 + (width - x2) * 0.30, y2, x2 + (width - x2) * 0.30 + 1100, y2),
        _edge_key(width * 0.62, y2 + 500, width * 0.62, y2 + 1500),
    ]
    windows = [
        _edge_key(width * 0.52, 0, width * 0.52 + 1400, 0),
        _edge_key(0, depth * 0.15, 0, depth * 0.15 + 1400),
        _edge_key(width, depth * 0.18, width, depth * 0.18 + 1400),
        _edge_key(width * 0.18, depth, width * 0.18 + 1600, depth),
        _edge_key(width * 0.70, depth, width * 0.70 + 1600, depth),
    ]
    rooms = [
        _room("Sala", "social", 0, 0, x1, y1),
        _room("Comedor", "social", x1, 0, x2 - x1, y1),
        _room("Cochera / acceso", "servicio", x2, 0, width - x2, y1),
        _room("Cocina", "servicio", 0, y1, x1, y2 - y1),
        _room("Servicios centrales", "servicio", x1, y1, x2 - x1, y2 - y1),
        _room("Pasillo / distribucion", "circulacion", x2, y1, width - x2, y2 - y1),
        _room("Dormitorio principal", "privado", 0, y2, width * 0.62, depth - y2),
        _room("Dormitorio secundario", "privado", width * 0.62, y2, width * 0.38, depth - y2),
    ]
    return {
        "variant": "casa_bandas_transversales",
        "exterior": exterior,
        "interior": interior,
        "doors": doors,
        "windows": windows,
        "rooms": rooms,
    }


def _house_segments_central_hall(width: float, depth: float, rng: random.Random) -> Dict:
    hall_x1 = width * rng.uniform(0.42, 0.47)
    hall_x2 = width * rng.uniform(0.55, 0.61)
    y1 = depth * rng.uniform(0.30, 0.36)
    y2 = depth * rng.uniform(0.66, 0.72)
    left_split = width * rng.uniform(0.24, 0.32)
    right_split = width * rng.uniform(0.72, 0.80)
    exterior = [
        _edge_key(0, 0, width, 0),
        _edge_key(width, 0, width, depth),
        _edge_key(0, depth, width, depth),
        _edge_key(0, 0, 0, depth),
    ]
    interior = [
        _edge_key(0, y1, width, y1),
        _edge_key(0, y2, width, y2),
        _edge_key(hall_x1, y1, hall_x1, depth),
        _edge_key(hall_x2, y1, hall_x2, depth),
        _edge_key(left_split, 0, left_split, y1),
        _edge_key(right_split, 0, right_split, y1),
    ]
    doors = [
        _edge_key(width * 0.48, 0, width * 0.48 + 1200, 0),
        _edge_key(hall_x1 + 250, y1, hall_x1 + 1450, y1),
        _edge_key(left_split * 0.42, y1, left_split * 0.42 + 1100, y1),
        _edge_key(right_split + (width - right_split) * 0.32, y1, right_split + (width - right_split) * 0.32 + 1100, y1),
        _edge_key(hall_x1, y1 + 850, hall_x1, y1 + 1950),
        _edge_key(hall_x2, y1 + 900, hall_x2, y1 + 2000),
        _edge_key(hall_x1, y2 - 1600, hall_x1, y2 - 500),
        _edge_key(hall_x2, y2 - 1500, hall_x2, y2 - 400),
        _edge_key(hall_x1 + 300, y2, hall_x1 + 1400, y2),
        _edge_key(width * 0.72, y2, width * 0.72 + 1100, y2),
    ]
    windows = [
        _edge_key(width * 0.12, 0, width * 0.12 + 1400, 0),
        _edge_key(width * 0.74, 0, width * 0.74 + 1400, 0),
        _edge_key(0, depth * 0.18, 0, depth * 0.18 + 1500),
        _edge_key(width, depth * 0.22, width, depth * 0.22 + 1500),
        _edge_key(width * 0.14, depth, width * 0.14 + 1600, depth),
        _edge_key(width * 0.68, depth, width * 0.68 + 1600, depth),
    ]
    rooms = [
        _room("Sala", "social", 0, 0, left_split, y1),
        _room("Acceso / comedor", "social", left_split, 0, right_split - left_split, y1),
        _room("Cochera / servicio", "servicio", right_split, 0, width - right_split, y1),
        _room("Dormitorio / estudio", "privado", 0, y1, hall_x1, y2 - y1),
        _room("Pasillo central", "circulacion", hall_x1, y1, hall_x2 - hall_x1, y2 - y1),
        _room("Cocina y servicios", "servicio", hall_x2, y1, width - hall_x2, y2 - y1),
        _room("Dormitorio principal", "privado", 0, y2, hall_x1, depth - y2),
        _room("Banos / closet", "servicio", hall_x1, y2, hall_x2 - hall_x1, depth - y2),
        _room("Dormitorio secundario", "privado", hall_x2, y2, width - hall_x2, depth - y2),
    ]
    return {
        "variant": "casa_pasillo_central",
        "exterior": exterior,
        "interior": interior,
        "doors": doors,
        "windows": windows,
        "rooms": rooms,
    }


def _house_segments_side_core(width: float, depth: float, rng: random.Random) -> Dict:
    core_x = width * rng.uniform(0.30, 0.38)
    hall_y1 = depth * rng.uniform(0.38, 0.45)
    hall_y2 = hall_y1 + depth * rng.uniform(0.16, 0.22)
    bed_split = width * rng.uniform(0.62, 0.70)
    service_split = depth * rng.uniform(0.18, 0.25)
    exterior = [
        _edge_key(0, 0, width, 0),
        _edge_key(width, 0, width, depth),
        _edge_key(0, depth, width, depth),
        _edge_key(0, 0, 0, depth),
    ]
    interior = [
        _edge_key(core_x, 0, core_x, depth),
        _edge_key(0, hall_y1, width, hall_y1),
        _edge_key(0, hall_y2, width, hall_y2),
        _edge_key(core_x, service_split, width, service_split),
        _edge_key(bed_split, hall_y2, bed_split, depth),
    ]
    doors = [
        _edge_key(width * 0.12, 0, width * 0.12 + 1200, 0),
        _edge_key(core_x, service_split * 0.45, core_x, service_split * 0.45 + 1200),
        _edge_key(core_x, hall_y1 + 350, core_x, hall_y1 + 1450),
        _edge_key(core_x * 0.40, hall_y1, core_x * 0.40 + 1100, hall_y1),
        _edge_key(core_x + (width - core_x) * 0.28, hall_y1, core_x + (width - core_x) * 0.28 + 1200, hall_y1),
        _edge_key(core_x + (width - core_x) * 0.62, hall_y1, core_x + (width - core_x) * 0.62 + 1200, hall_y1),
        _edge_key(core_x + (width - core_x) * 0.30, hall_y2, core_x + (width - core_x) * 0.30 + 1100, hall_y2),
        _edge_key(bed_split + (width - bed_split) * 0.30, hall_y2, bed_split + (width - bed_split) * 0.30 + 1100, hall_y2),
        _edge_key(bed_split, hall_y2 + 650, bed_split, hall_y2 + 1750),
    ]
    windows = [
        _edge_key(width * 0.38, 0, width * 0.38 + 1600, 0),
        _edge_key(width * 0.70, 0, width * 0.70 + 1600, 0),
        _edge_key(0, depth * 0.18, 0, depth * 0.18 + 1500),
        _edge_key(0, depth * 0.66, 0, depth * 0.66 + 1500),
        _edge_key(width, depth * 0.20, width, depth * 0.20 + 1500),
        _edge_key(width * 0.18, depth, width * 0.18 + 1600, depth),
        _edge_key(width * 0.74, depth, width * 0.74 + 1500, depth),
    ]
    rooms = [
        _room("Nucleo lateral / acceso", "circulacion", 0, 0, core_x, hall_y1),
        _room("Sala comedor", "social", core_x, 0, width - core_x, service_split),
        _room("Cocina y servicio", "servicio", core_x, service_split, width - core_x, hall_y1 - service_split),
        _room("Pasillo transversal", "circulacion", 0, hall_y1, width, hall_y2 - hall_y1),
        _room("Dormitorio principal", "privado", 0, hall_y2, bed_split, depth - hall_y2),
        _room("Dormitorio secundario", "privado", bed_split, hall_y2, width - bed_split, depth - hall_y2),
    ]
    return {
        "variant": "casa_nucleo_lateral",
        "exterior": exterior,
        "interior": interior,
        "doors": doors,
        "windows": windows,
        "rooms": rooms,
    }


def _house_segments(width: float, depth: float, rng: random.Random) -> Dict:
    generators = (_house_segments_banded, _house_segments_central_hall, _house_segments_side_core)
    return rng.choice(generators)(width, depth, rng)


def _office_segments(width: float, depth: float, rng: random.Random) -> Dict:
    del rng
    front = depth * 0.24
    corridor_y1 = depth * 0.52
    corridor_y2 = corridor_y1 + 1900.0
    exterior = [
        _edge_key(0, 0, width, 0),
        _edge_key(width, 0, width, depth),
        _edge_key(0, depth, width, depth),
        _edge_key(0, 0, 0, depth),
    ]
    xs = [width * f for f in (0.24, 0.42, 0.58, 0.76)]
    interior = [
        _edge_key(0, front, width, front),
        _edge_key(0, corridor_y1, width, corridor_y1),
        _edge_key(0, corridor_y2, width, corridor_y2),
    ]
    for x in xs:
        interior.append(_edge_key(x, 0, x, front))
        interior.append(_edge_key(x, front, x, corridor_y1))
        interior.append(_edge_key(x, corridor_y2, x, depth))
    doors = [
        _edge_key(width * 0.12, 0, width * 0.12 + 1400, 0),
        _edge_key(width * 0.12, front, width * 0.12 + 1200, front),
        _edge_key(width * 0.42, front, width * 0.42 + 1200, front),
        _edge_key(width * 0.72, front, width * 0.72 + 1200, front),
    ]
    for x in [width * f for f in (0.12, 0.32, 0.50, 0.68, 0.86)]:
        doors.append(_edge_key(x, corridor_y1, x + 900, corridor_y1))
        doors.append(_edge_key(x, corridor_y2, x + 900, corridor_y2))
    windows = [
        _edge_key(width * 0.36, 0, width * 0.36 + 1600, 0),
        _edge_key(width * 0.64, 0, width * 0.64 + 1600, 0),
        _edge_key(width * 0.12, depth, width * 0.12 + 1600, depth),
        _edge_key(width * 0.42, depth, width * 0.42 + 1600, depth),
        _edge_key(width * 0.72, depth, width * 0.72 + 1600, depth),
    ]
    rooms = [
        _room("Recepcion", "publico", 0, 0, width * 0.24, front),
        _room("Sala espera / atencion", "publico", width * 0.24, 0, width * 0.34, front),
        _room("Sala reuniones", "trabajo", width * 0.58, 0, width * 0.18, front),
        _room("Servicios", "sanitario", width * 0.76, 0, width * 0.24, front),
        _room("Oficinas frente", "trabajo", 0, front, width, corridor_y1 - front),
        _room("Pasillo central", "circulacion", 0, corridor_y1, width, corridor_y2 - corridor_y1),
        _room("Oficinas fondo", "administrativo", 0, corridor_y2, width, depth - corridor_y2),
    ]
    return {
        "variant": "oficina_pasillo_central",
        "exterior": exterior,
        "interior": interior,
        "doors": doors,
        "windows": windows,
        "rooms": rooms,
    }


def generate_quick_example(options: Optional[Dict] = None):
    """Generate a quick Arch Wall example scene and return the root group."""
    options = dict(options or {})
    doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("GameEngineExport_QuickExample")
    if options.get("clear_previous", True):
        removed = _clear_previous(doc)
        if removed:
            _info("Removed previous quick example objects: %d" % removed)

    seed = int(options.get("seed", 0) or 0)
    if seed <= 0:
        seed = int(time.time_ns() % 2147483647) or 1
    rng = random.Random(seed)

    building_type = options.get("building_type", "Casa")
    if building_type == "Aleatorio":
        building_type = rng.choice(["Casa", "Oficina"])
    width = float(options.get("width_mm", 0) or (12000 if building_type == "Casa" else 22000))
    depth = float(options.get("depth_mm", 0) or (9000 if building_type == "Casa" else 14000))
    ext_wall = float(options.get("ext_wall_mm", DEFAULT_EXT_WALL_MM))
    int_wall = float(options.get("int_wall_mm", DEFAULT_INT_WALL_MM))
    wall_height = float(options.get("wall_height_mm", DEFAULT_WALL_HEIGHT_MM))
    door_height = float(options.get("door_height_mm", DEFAULT_DOOR_HEIGHT_MM))
    window_sill = float(options.get("window_sill_mm", DEFAULT_WINDOW_SILL_MM))
    window_height = float(options.get("window_height_mm", DEFAULT_WINDOW_HEIGHT_MM))

    segments = _house_segments(width, depth, rng) if building_type == "Casa" else _office_segments(width, depth, rng)
    variant = str(segments.get("variant", "default"))
    stamp = int(time.time())
    root = doc.addObject("App::DocumentObjectGroup", RESULT_PREFIX + str(stamp))
    root.Label = RESULT_PREFIX + str(stamp)
    _set_prop(root, "App::PropertyString", "GEE_ExampleType", "GameEngineExport", "Tipo de ejemplo", building_type)
    _set_prop(root, "App::PropertyString", "GEE_ExampleVariant", "GameEngineExport", "Variante del ejemplo", variant)
    _set_prop(root, "App::PropertyInteger", "GEE_Seed", "GameEngineExport", "Semilla", seed)

    payload = {
        "macro": "GameEngineExportWB Quick Example",
        "root_group": root.Name,
        "building_type": building_type,
        "building_variant": variant,
        "seed": seed,
        "units": "mm",
        "dimensions": {
            "width_mm": round(width, 1),
            "depth_mm": round(depth, 1),
            "ext_wall_mm": round(ext_wall, 1),
            "int_wall_mm": round(int_wall, 1),
            "wall_height_mm": round(wall_height, 1),
            "door_height_mm": round(door_height, 1),
            "window_sill_mm": round(window_sill, 1),
            "window_height_mm": round(window_height, 1),
        },
        "terrain": {
            "enabled": bool(options.get("create_terrain", True)),
            "flatten_pad": bool(options.get("flatten_pad", DEFAULT_FLATTEN_PAD)),
            "pad_margin_mm": float(options.get("pad_margin_mm", DEFAULT_PAD_MARGIN_MM)),
            "terrain_margin_mm": float(options.get("terrain_margin_mm", DEFAULT_TERRAIN_MARGIN_MM)),
            "terrain_variation_mm": float(options.get("terrain_variation_mm", DEFAULT_TERRAIN_VARIATION_MM)),
            "floor_overhang_mm": float(options.get("floor_overhang_mm", DEFAULT_FLOOR_OVERHANG_MM)),
        },
        "segments": {
            "exterior_walls": _segments_to_json(segments["exterior"]),
            "interior_walls": _segments_to_json(segments["interior"]),
            "door_openings": _segments_to_json(segments["doors"]),
            "window_openings": _segments_to_json(segments["windows"]),
        },
        "rooms": segments.get("rooms", []),
        "objects": {},
    }

    sketch_group = doc.addObject("App::DocumentObjectGroup", "Sketches")
    wall_group = doc.addObject("App::DocumentObjectGroup", "ArchWalls")
    cutter_group = doc.addObject("App::DocumentObjectGroup", "OpeningCutters")
    for group in (sketch_group, wall_group, cutter_group):
        root.addObject(group)

    if options.get("create_terrain", True):
        site_group, site_objects = _create_site_and_floor(doc, root, width, depth, rng, options)
        payload["objects"]["site_group"] = _object_ref(site_group)
        payload["objects"]["site"] = {key: _object_ref(value) for key, value in site_objects.items()}

    exterior_sk = _make_sketch(doc, sketch_group, "GEE_SK_ExteriorWalls", "GEE SK Exterior Walls", "exterior_wall_axis", (0.05, 0.05, 0.05))
    interior_sk = _make_sketch(doc, sketch_group, "GEE_SK_InteriorWalls", "GEE SK Interior Walls", "interior_wall_axis", (0.15, 0.42, 0.75))
    door_sk = _make_sketch(doc, sketch_group, "GEE_SK_DoorOpenings", "GEE SK Door Openings", "door_opening_axis", (0.65, 0.28, 0.08))
    window_sk = _make_sketch(doc, sketch_group, "GEE_SK_WindowOpenings", "GEE SK Window Openings", "window_opening_axis", (0.05, 0.62, 0.88))
    payload["objects"]["sketches"] = {
        "exterior_walls": _object_ref(exterior_sk),
        "interior_walls": _object_ref(interior_sk),
        "door_openings": _object_ref(door_sk),
        "window_openings": _object_ref(window_sk),
    }

    for segment in segments["exterior"]:
        _line(exterior_sk, segment)
    for segment in segments["interior"]:
        _line(interior_sk, segment)
    for segment in segments["doors"]:
        _line(door_sk, segment)
    for segment in segments["windows"]:
        _line(window_sk, segment)

    exterior_wall = _make_wall(doc, wall_group, "GEE_ArchWall_Exterior", exterior_sk, ext_wall, wall_height, "exterior", (0.70, 0.70, 0.70))
    interior_wall = _make_wall(doc, wall_group, "GEE_ArchWall_Interior", interior_sk, int_wall, wall_height, "interior", (0.80, 0.84, 0.88))
    door_cutter = _make_cutter(doc, cutter_group, "GEE_Cutter_DoorOpenings", door_sk, "door_opening_cutter", max(ext_wall, int_wall) + 160.0, door_height, 0.0, (0.85, 0.36, 0.10))
    window_cutter = _make_cutter(doc, cutter_group, "GEE_Cutter_WindowOpenings", window_sk, "window_opening_cutter", ext_wall + 160.0, window_height, window_sill, (0.12, 0.62, 0.88))
    payload["objects"]["arch_walls"] = {
        "exterior": _object_ref(exterior_wall),
        "interior": _object_ref(interior_wall),
    }
    payload["objects"]["cutters"] = {
        "doors": _object_ref(door_cutter),
        "windows": _object_ref(window_cutter),
    }

    exterior_ok = _set_subtractions(exterior_wall, [door_cutter, window_cutter])
    interior_ok = _set_subtractions(interior_wall, [door_cutter])
    _set_prop(exterior_wall, "App::PropertyBool", "GEE_OpeningsLinked", "GameEngineExport", "Buques vinculados", exterior_ok)
    _set_prop(interior_wall, "App::PropertyBool", "GEE_OpeningsLinked", "GameEngineExport", "Buques vinculados", interior_ok)
    payload["objects"]["subtractions_linked"] = {
        "exterior": exterior_ok,
        "interior": interior_ok,
    }
    context_obj, context_text = _create_context_document(doc, root, payload)
    payload["objects"]["context"] = _object_ref(context_obj)
    _set_prop(
        root,
        "App::PropertyString",
        "GEE_ContextJSON",
        "GameEngineExport",
        "Contexto JSON",
        json.dumps(payload, ensure_ascii=False, indent=2)[:32760],
    )

    _tag_quick_example_tree(root, building_type, seed, variant)
    doc.recompute()
    _info("Quick example generated: %s | type=%s | variant=%s | seed=%d" % (root.Label, building_type, variant, seed))
    if options.get("copy_context", False):
        try:
            from PySide import QtGui

            app = QtGui.QApplication.instance()
            if app is not None:
                app.clipboard().setText(context_text)
                _info("Quick example JSON context copied to clipboard")
        except Exception as exc:
            _warn("Could not copy JSON context to clipboard: %s" % exc)
    return root
