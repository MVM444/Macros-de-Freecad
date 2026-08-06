"""Sketch utilities for FacilArquitecturaWB.

Descripcion: crea sketches maestros editables en plano XY.
Fecha: 2026-07-13
Version: 0.1.0
Instrucciones: no crear un sketch por objeto; crear sketches maestros por sistema.
"""

from __future__ import annotations

import FreeCAD
import Part

from .naming import safe_name
from .project_structure import find_by_name_or_label, msg, set_prop, warn


SKETCH_DEFINITIONS = [
    ("Sketch_Terreno", "terrain", "site", (0.22, 0.50, 0.22)),
    ("Sketch_Ejes", "axes", "grid", (0.85, 0.65, 0.15)),
    ("Sketch_Columnas", "columns", "structure", (0.55, 0.30, 0.65)),
    ("Sketch_Muros_Ext_200", "walls_exterior_200", "walls", (0.10, 0.10, 0.10)),
    ("Sketch_Muros_Int_100", "walls_interior_100", "walls", (0.15, 0.35, 0.75)),
    ("Sketch_Puertas_900", "doors_900", "openings", (0.75, 0.35, 0.12)),
    ("Sketch_Ventanas_1200x1200", "windows_1200x1200", "openings", (0.05, 0.55, 0.80)),
    ("Sketch_Losa_Piso", "floor_slab", "slab", (0.55, 0.55, 0.55)),
]


def ensure_master_sketches(doc, parent_group, params: dict, create_sample_geometry: bool = False):
    """Create all master sketches; sample geometry is optional."""
    created = {}
    for name, role, system, color in SKETCH_DEFINITIONS:
        sketch = ensure_sketch(doc, parent_group, name, role, system, color)
        if create_sample_geometry and _geometry_count(sketch) == 0:
            _add_initial_geometry(sketch, name, params)
            msg("Geometria de muestra creada en %s" % name)
        elif create_sample_geometry:
            msg("Sketch existente conservado sin agregar muestra: %s" % name)
        else:
            msg("Sketch maestro listo: %s" % name)
        created[name] = sketch
    return created


def add_sample_geometry_to_master_sketches(doc, parent_group, params: dict):
    """Fill empty master sketches with simple sample geometry."""
    return ensure_master_sketches(doc, parent_group, params, create_sample_geometry=True)


def ensure_sketch(doc, parent_group, name: str, role: str, system: str, color):
    """Create or reuse a Sketcher::SketchObject."""
    sketch = find_by_name_or_label(doc, safe_name(name), name)
    if sketch is None:
        sketch = doc.addObject("Sketcher::SketchObject", safe_name(name))
        sketch.Label = name
        msg("Sketch creado: %s" % name)
    try:
        sketch.Placement = FreeCAD.Placement()
    except Exception:
        pass
    set_prop(sketch, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", role)
    set_prop(sketch, "App::PropertyString", "FA_System", "FacilArquitectura", "Sistema", system)
    try:
        if sketch not in list(getattr(parent_group, "Group", []) or []):
            parent_group.addObject(sketch)
    except Exception:
        pass
    _set_view(sketch, color)
    return sketch


def _set_view(obj, color):
    try:
        obj.ViewObject.LineColor = color
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineWidth = 2.0
    except Exception:
        pass


def _geometry_count(sketch) -> int:
    try:
        return len(list(getattr(sketch, "Geometry", []) or []))
    except Exception:
        return 0


def _add_line(sketch, x1, y1, x2, y2, construction=False) -> None:
    line = Part.LineSegment(FreeCAD.Vector(float(x1), float(y1), 0.0), FreeCAD.Vector(float(x2), float(y2), 0.0))
    try:
        sketch.addGeometry(line, bool(construction))
    except TypeError:
        sketch.addGeometry(line)


def _add_rectangle(sketch, x, y, w, d) -> None:
    _add_line(sketch, x, y, x + w, y)
    _add_line(sketch, x + w, y, x + w, y + d)
    _add_line(sketch, x + w, y + d, x, y + d)
    _add_line(sketch, x, y + d, x, y)


def _add_initial_geometry(sketch, name: str, params: dict) -> None:
    width = float(params.get("building_width_mm", 12000.0))
    depth = float(params.get("building_depth_mm", 9000.0))
    margin = 1500.0

    if name == "Sketch_Terreno":
        _add_rectangle(sketch, -margin, -margin, width + margin * 2.0, depth + margin * 2.0)
    elif name == "Sketch_Ejes":
        _add_line(sketch, 0, depth / 2.0, width, depth / 2.0, True)
        _add_line(sketch, width / 2.0, 0, width / 2.0, depth, True)
        _add_line(sketch, 0, 0, width, 0, True)
        _add_line(sketch, 0, depth, width, depth, True)
    elif name == "Sketch_Columnas":
        size = 180.0
        for x, y in ((0, 0), (width, 0), (width, depth), (0, depth)):
            _add_line(sketch, x - size, y, x + size, y)
            _add_line(sketch, x, y - size, x, y + size)
    elif name == "Sketch_Muros_Ext_200":
        _add_rectangle(sketch, 0, 0, width, depth)
    elif name == "Sketch_Muros_Int_100":
        _add_line(sketch, width * 0.35, 0, width * 0.35, depth)
        _add_line(sketch, width * 0.35, depth * 0.55, width, depth * 0.55)
    elif name == "Sketch_Puertas_900":
        door = float(params.get("door_width_900_mm", 900.0))
        _add_line(sketch, width * 0.12, 0, width * 0.12 + door, 0)
        _add_line(sketch, width * 0.35, depth * 0.25, width * 0.35, depth * 0.25 + door)
    elif name == "Sketch_Ventanas_1200x1200":
        _add_line(sketch, width * 0.55, 0, width * 0.55 + 1200.0, 0)
        _add_line(sketch, width, depth * 0.25, width, depth * 0.25 + 1200.0)
        _add_line(sketch, width * 0.20, depth, width * 0.20 + 1200.0, depth)
    elif name == "Sketch_Losa_Piso":
        _add_rectangle(sketch, 0, 0, width, depth)
    else:
        warn("No hay geometria inicial definida para %s" % name)
