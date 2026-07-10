"""Generic BIM doors/windows from the selected sketch.

This helper is intentionally independent from GameEngineExport quick examples.
The selected sketch must contain line segments representing centerlines of
openings. Door mode creates visible leaves opened at 90 degrees. Window mode
creates a simple glass panel. Both modes try Arch.makeWindow first and fall
back to Part geometry when Arch/BIM rejects the generated profile.
"""

from __future__ import annotations

import math
import time

import FreeCAD
import Part

try:
    import FreeCADGui
except Exception:  # pragma: no cover - FreeCAD runtime only
    FreeCADGui = None

try:
    import Arch
except Exception:  # pragma: no cover - FreeCAD runtime only
    Arch = None


LOG_PREFIX = "[BIM-SKETCH] "

DEFAULT_DOOR_HEIGHT = 2100.0
DEFAULT_DOOR_LEAF_THICKNESS = 45.0
DEFAULT_WINDOW_SILL = 900.0
DEFAULT_WINDOW_HEIGHT = 1200.0
DEFAULT_GLASS_THICKNESS = 30.0


def _msg(text):
    FreeCAD.Console.PrintMessage(LOG_PREFIX + str(text) + "\n")


def _warn(text):
    FreeCAD.Console.PrintWarning(LOG_PREFIX + str(text) + "\n")


def _safe_name(text):
    value = str(text).strip()
    for old, new in {
        " ": "_",
        "-": "_",
        "/": "_",
        "\\": "_",
        ".": "_",
        "(": "",
        ")": "",
    }.items():
        value = value.replace(old, new)
    return "".join(ch for ch in value if ch.isalnum() or ch == "_") or "Object"


def _set_prop(obj, prop_type, name, group, desc, value):
    try:
        if not hasattr(obj, name):
            obj.addProperty(prop_type, name, group, desc)
        setattr(obj, name, value)
    except Exception:
        pass


def _set_view(obj, color=None, transparency=None):
    try:
        if color is not None:
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineColor = color
        if transparency is not None:
            obj.ViewObject.Transparency = int(transparency)
    except Exception:
        pass


def _selected_sketch():
    if FreeCADGui is None:
        raise RuntimeError("FreeCADGui no esta disponible.")
    selection = list(FreeCADGui.Selection.getSelection() or [])
    sketches = [obj for obj in selection if "Sketch" in str(getattr(obj, "TypeId", ""))]
    if not sketches:
        raise RuntimeError("Seleccione un sketch con lineas de centro para puertas o ventanas.")
    if len(sketches) > 1:
        _warn("Hay varios sketches seleccionados; se usara el primero: " + str(sketches[0].Label))
    return sketches[0]


def _iter_segments(sketch):
    placement = getattr(sketch, "Placement", FreeCAD.Placement())
    for index, geo in enumerate(list(getattr(sketch, "Geometry", []) or [])):
        try:
            if hasattr(sketch, "getConstruction") and sketch.getConstruction(index):
                continue
        except Exception:
            pass
        if not hasattr(geo, "StartPoint") or not hasattr(geo, "EndPoint"):
            continue
        p1 = placement.multVec(geo.StartPoint)
        p2 = placement.multVec(geo.EndPoint)
        if p1.distanceToPoint(p2) > 50.0:
            yield index, p1, p2


def _segment_info(p1, p2):
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    length = math.sqrt(dx * dx + dy * dy)
    if length <= 0.0:
        return None
    return {
        "length": length,
        "horizontal": abs(dx) >= abs(dy),
    }


def _make_profile_face(p1, p2, z0, height):
    a = FreeCAD.Vector(p1.x, p1.y, z0)
    b = FreeCAD.Vector(p2.x, p2.y, z0)
    c = FreeCAD.Vector(p2.x, p2.y, z0 + height)
    d = FreeCAD.Vector(p1.x, p1.y, z0 + height)
    return Part.Face(Part.makePolygon([a, b, c, d, a]))


def _make_base_profile(doc, group, name, p1, p2, z0, height, source_sketch, color):
    obj = doc.addObject("Part::Feature", _safe_name(name))
    obj.Label = name
    obj.Shape = _make_profile_face(p1, p2, z0, height)
    group.addObject(obj)
    _set_prop(obj, "App::PropertyString", "GEE_Role", "GameEngineExport", "Rol GameEngineExport", "bim_opening_profile")
    _set_prop(obj, "App::PropertyLink", "SourceSketch", "GameEngineExport", "Sketch fuente", source_sketch)
    _set_view(obj, color=color, transparency=85)
    return obj


def _make_arch_window_or_fallback(doc, group, name, base, role, height, sill, open_percent, color):
    obj = None
    if Arch is not None and hasattr(Arch, "makeWindow"):
        try:
            obj = Arch.makeWindow(base, name=_safe_name(name))
        except TypeError:
            try:
                obj = Arch.makeWindow(base)
            except Exception:
                obj = None
        except Exception:
            obj = None

    if obj is None:
        obj = doc.addObject("Part::Feature", _safe_name(name + "_Fallback"))
        obj.Label = name
        obj.Shape = base.Shape
        _set_prop(obj, "App::PropertyBool", "GEE_BIMFallback", "GameEngineExport", "Arch.makeWindow no disponible", True)
    else:
        obj.Label = name

    group.addObject(obj)
    _set_prop(obj, "App::PropertyString", "GEE_Role", "GameEngineExport", "Rol GameEngineExport", role)
    _set_prop(obj, "App::PropertyString", "GEE_BIMType", "GameEngineExport", "Tipo BIM", role)
    _set_prop(obj, "App::PropertyLink", "GEE_BaseProfile", "GameEngineExport", "Perfil base", base)
    _set_prop(obj, "App::PropertyFloat", "Height_mm", "GameEngineExport", "Altura", float(height))
    _set_prop(obj, "App::PropertyFloat", "Sill_mm", "GameEngineExport", "Antepecho", float(sill))
    _set_prop(obj, "App::PropertyFloat", "GEE_OpeningPercent", "GameEngineExport", "Apertura porcentual", float(open_percent))
    for attr in ("Opening", "Open", "OpeningPercent"):
        if hasattr(obj, attr):
            try:
                setattr(obj, attr, float(open_percent))
            except Exception:
                pass
    _set_view(obj, color=color, transparency=0 if role.startswith("bim_door") else 35)
    return obj


def _make_box(doc, group, name, shape, role, color, transparency=0):
    obj = doc.addObject("Part::Feature", _safe_name(name))
    obj.Label = name
    obj.Shape = shape
    group.addObject(obj)
    _set_prop(obj, "App::PropertyString", "GEE_Role", "GameEngineExport", "Rol GameEngineExport", role)
    _set_view(obj, color=color, transparency=transparency)
    return obj


def _door_open_direction(info, p1):
    if info["horizontal"]:
        return 1.0 if p1.y < 100.0 else (-1.0 if int(p1.x / 1000.0) % 2 else 1.0)
    return 1.0 if int(p1.y / 1000.0) % 2 else -1.0


def _make_open_door_leaf(doc, group, name, p1, p2, height):
    info = _segment_info(p1, p2)
    if info is None:
        return None
    leaf_width = max(min(info["length"] - 80.0, 1200.0), 650.0)
    thickness = DEFAULT_DOOR_LEAF_THICKNESS
    open_dir = _door_open_direction(info, p1)
    hinge = p1
    if info["horizontal"]:
        x0 = hinge.x - thickness / 2.0
        y0 = hinge.y if open_dir > 0 else hinge.y - leaf_width
        shape = Part.makeBox(thickness, leaf_width, height, FreeCAD.Vector(x0, y0, 0.0))
    else:
        x0 = hinge.x if open_dir > 0 else hinge.x - leaf_width
        y0 = hinge.y - thickness / 2.0
        shape = Part.makeBox(leaf_width, thickness, height, FreeCAD.Vector(x0, y0, 0.0))
    leaf = _make_box(doc, group, name, shape, "door_leaf_open_90_visual", (0.55, 0.28, 0.10), transparency=0)
    _set_prop(leaf, "App::PropertyFloat", "GEE_OpeningAngle_deg", "GameEngineExport", "Angulo de apertura", 90.0)
    _set_prop(leaf, "App::PropertyFloat", "GEE_OpeningPercent", "GameEngineExport", "Apertura porcentual", 100.0)
    return leaf


def _make_window_glass(doc, group, name, p1, p2, sill, height):
    info = _segment_info(p1, p2)
    if info is None:
        return None
    length = max(info["length"] - 160.0, 200.0)
    depth = DEFAULT_GLASS_THICKNESS
    z = sill + 80.0
    glass_height = max(height - 160.0, 200.0)
    min_x = min(p1.x, p2.x)
    min_y = min(p1.y, p2.y)
    if info["horizontal"]:
        shape = Part.makeBox(length, depth, glass_height, FreeCAD.Vector(min_x + 80.0, p1.y - depth / 2.0, z))
    else:
        shape = Part.makeBox(depth, length, glass_height, FreeCAD.Vector(p1.x - depth / 2.0, min_y + 80.0, z))
    return _make_box(doc, group, name, shape, "window_glass_visual", (0.35, 0.75, 0.95), transparency=55)


def _make_group(doc, sketch, mode):
    label = ("BIM_Puertas_desde_" if mode == "doors" else "BIM_Ventanas_desde_") + str(sketch.Name)
    group = doc.addObject("App::DocumentObjectGroup", _safe_name(label + "_" + str(int(time.time()))))
    group.Label = label
    _set_prop(group, "App::PropertyLink", "SourceSketch", "GameEngineExport", "Sketch fuente", sketch)
    _set_prop(group, "App::PropertyString", "GEE_Role", "GameEngineExport", "Rol GameEngineExport", mode + "_from_selected_sketch")
    return group


def run(mode):
    if mode not in {"doors", "windows"}:
        raise ValueError("mode debe ser 'doors' o 'windows'")
    doc = FreeCAD.ActiveDocument
    if doc is None:
        raise RuntimeError("No hay documento activo.")
    sketch = _selected_sketch()
    segments = list(_iter_segments(sketch))
    if not segments:
        raise RuntimeError("El sketch seleccionado no tiene lineas validas.")

    group = _make_group(doc, sketch, mode)
    created = 0
    for index, p1, p2 in segments:
        if mode == "doors":
            base = _make_base_profile(
                doc,
                group,
                "BIM_Door_Profile_%02d" % (index + 1),
                p1,
                p2,
                0.0,
                DEFAULT_DOOR_HEIGHT,
                sketch,
                (0.85, 0.35, 0.10),
            )
            opening = _make_arch_window_or_fallback(
                doc,
                group,
                "BIM_Door_Open100_%02d" % (index + 1),
                base,
                "bim_door_open_100",
                DEFAULT_DOOR_HEIGHT,
                0.0,
                100.0,
                (0.85, 0.35, 0.10),
            )
            leaf = _make_open_door_leaf(doc, group, "BIM_Door_Leaf_Open90_%02d" % (index + 1), p1, p2, DEFAULT_DOOR_HEIGHT - 50.0)
            for obj in (opening, leaf):
                if obj is not None:
                    _set_prop(obj, "App::PropertyLink", "SourceSketch", "GameEngineExport", "Sketch fuente", sketch)
        else:
            base = _make_base_profile(
                doc,
                group,
                "BIM_Window_Profile_%02d" % (index + 1),
                p1,
                p2,
                DEFAULT_WINDOW_SILL,
                DEFAULT_WINDOW_HEIGHT,
                sketch,
                (0.12, 0.62, 0.88),
            )
            opening = _make_arch_window_or_fallback(
                doc,
                group,
                "BIM_Window_%02d" % (index + 1),
                base,
                "bim_window",
                DEFAULT_WINDOW_HEIGHT,
                DEFAULT_WINDOW_SILL,
                0.0,
                (0.12, 0.62, 0.88),
            )
            glass = _make_window_glass(doc, group, "BIM_Window_Glass_%02d" % (index + 1), p1, p2, DEFAULT_WINDOW_SILL, DEFAULT_WINDOW_HEIGHT)
            for obj in (opening, glass):
                if obj is not None:
                    _set_prop(obj, "App::PropertyLink", "SourceSketch", "GameEngineExport", "Sketch fuente", sketch)
        created += 1

    doc.recompute()
    if FreeCADGui is not None:
        try:
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(group)
            FreeCADGui.SendMsgToActiveView("ViewFit")
        except Exception:
            pass
    _msg("Listo. Modo=%s | Sketch=%s | Elementos=%d | Grupo=%s" % (mode, sketch.Label, created, group.Label))
    return group
