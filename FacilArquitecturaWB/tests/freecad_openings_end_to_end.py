"""FreeCAD 1.1.3 end-to-end test for hosted FA BIM doors and windows.

Descripcion: valida Level nativo, dos muros, dos puertas, dos ventanas, cortes,
Undo, idempotencia y persistencia sin grupos FA de aberturas.
Fecha y hora: 2026-08-09 22:35 UTC-06:00.
Version: 0.2.0.
Instrucciones: ejecutar con FreeCADCmd aislado y guardar solo en .codex_tmp.
"""

from __future__ import annotations

import math
import os
import sys

import FreeCAD
import Part
import Arch


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.core.opening_utils import (  # noqa: E402
    GENERATED_BY_DOORS,
    GENERATED_BY_WINDOWS,
    create_openings_from_centerlines,
)
from FacilArquitecturaWB.core.bim_structure_utils import (  # noqa: E402
    add_to_level,
    ensure_bim_structure,
)


def add_line(sketch, first, second):
    return sketch.addGeometry(
        Part.LineSegment(
            FreeCAD.Vector(float(first[0]), float(first[1]), 0.0),
            FreeCAD.Vector(float(second[0]), float(second[1]), 0.0),
        ),
        False,
    )


def point_on_segment(first, second, distance):
    dx = float(second[0]) - float(first[0])
    dy = float(second[1]) - float(first[1])
    length = math.hypot(dx, dy)
    return first[0] + dx * distance / length, first[1] + dy * distance / length


def generated(doc, generator):
    return [
        obj
        for obj in doc.Objects
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == generator
        and str(getattr(obj, "FA_Role", "") or "") in ("door", "window")
    ]


def main():
    output = os.path.join(REPO_DIR, ".codex_tmp", "fa_openings_end_to_end.FCStd")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    doc = FreeCAD.newDocument("FAOpeningsEndToEnd")
    doc.UndoMode = 1
    structure = ensure_bim_structure(doc, "Edificio de prueba", "Nivel 00", 0.0)
    level = structure["level"]
    sketch_group = doc.addObject("App::DocumentObjectGroup", "FA_Sketches_Test")

    wall_a_axis = doc.addObject("Sketcher::SketchObject", "WallAxisA")
    add_line(wall_a_axis, (0.0, 0.0), (6000.0, 0.0))
    wall_a = Arch.makeWall(wall_a_axis, width=200.0, height=3000.0, name="WallA")
    wall_a.Label = "Wall A"
    add_to_level(level, wall_a, source_sketch=wall_a_axis)

    wall_b_first = (0.0, 3500.0)
    wall_b_second = (6000.0, 5500.0)
    wall_b_axis = doc.addObject("Sketcher::SketchObject", "WallAxisB")
    add_line(wall_b_axis, wall_b_first, wall_b_second)
    wall_b = Arch.makeWall(wall_b_axis, width=150.0, height=3000.0, name="WallB")
    wall_b.Label = "Wall B diagonal"
    add_to_level(level, wall_b, source_sketch=wall_b_axis)

    door_axes = doc.addObject("Sketcher::SketchObject", "Sketch_Centros_Puertas")
    door_axes.addProperty("App::PropertyString", "FA_CenterlineKind", "FacilArquitectura")
    door_axes.FA_CenterlineKind = "doors"
    add_line(door_axes, (700.0, 0.0), (1600.0, 0.0))
    add_line(
        door_axes,
        point_on_segment(wall_b_first, wall_b_second, 900.0),
        point_on_segment(wall_b_first, wall_b_second, 1800.0),
    )
    sketch_group.addObject(door_axes)

    window_axes = doc.addObject("Sketcher::SketchObject", "Sketch_Centros_Ventanas")
    window_axes.addProperty("App::PropertyString", "FA_CenterlineKind", "FacilArquitectura")
    window_axes.FA_CenterlineKind = "windows"
    add_line(window_axes, (2500.0, 0.0), (3700.0, 0.0))
    add_line(
        window_axes,
        point_on_segment(wall_b_first, wall_b_second, 3000.0),
        point_on_segment(wall_b_first, wall_b_second, 4200.0),
    )
    sketch_group.addObject(window_axes)
    doc.recompute()

    initial_volumes = {wall_a.Name: wall_a.Shape.Volume, wall_b.Name: wall_b.Shape.Volume}
    doc.openTransaction("Create FA doors")
    doors, door_summary = create_openings_from_centerlines(
        doc,
        level,
        [door_axes],
        [wall_a, wall_b],
        "door",
        height_mm=2100.0,
        host_tolerance_mm=100.0,
        replace_existing=True,
    )
    doc.commitTransaction()
    assert len(doors) == 2
    assert door_summary["created_count"] == 2
    assert len({door.FA_HostWall.Name for door in doors}) == 2
    assert all(door.TypeId == "Part::FeaturePython" for door in doors)
    assert all(door.Proxy.__class__.__module__ == "ArchWindow" for door in doors)
    assert all(door.Hosts == [door.FA_HostWall] for door in doors)
    assert all(door not in level.Group and door.Base not in level.Group for door in doors)
    assert all(door.FA_TargetLevel == level.Name and door.Base.FA_TargetLevel == level.Name for door in doors)
    assert doc.getObject("FA_Doors") is None
    door_volumes = {wall_a.Name: wall_a.Shape.Volume, wall_b.Name: wall_b.Shape.Volume}
    assert all(door_volumes[name] < volume for name, volume in initial_volumes.items())

    doc.undo()
    doc.recompute()
    assert len(generated(doc, GENERATED_BY_DOORS)) == 0
    assert all(abs(doc.getObject(name).Shape.Volume - volume) < 1.0 for name, volume in initial_volumes.items())
    doc.redo()
    doc.recompute()
    assert len(generated(doc, GENERATED_BY_DOORS)) == 2

    doc.openTransaction("Create FA windows")
    windows, window_summary = create_openings_from_centerlines(
        doc,
        level,
        [window_axes],
        [wall_a, wall_b],
        "window",
        height_mm=1200.0,
        sill_mm=900.0,
        host_tolerance_mm=100.0,
        replace_existing=True,
    )
    doc.commitTransaction()
    assert len(windows) == 2
    assert window_summary["created_count"] == 2
    assert len({window.FA_HostWall.Name for window in windows}) == 2
    assert all(window.Hosts == [window.FA_HostWall] for window in windows)
    assert all(window not in level.Group and window.Base not in level.Group for window in windows)
    assert all(window.FA_TargetLevel == level.Name and window.Base.FA_TargetLevel == level.Name for window in windows)
    assert doc.getObject("FA_Windows") is None

    doc.openTransaction("Repeat FA doors")
    repeated_doors, repeated_door_summary = create_openings_from_centerlines(
        doc,
        level,
        [door_axes],
        [wall_a, wall_b],
        "door",
        height_mm=2100.0,
        host_tolerance_mm=100.0,
        replace_existing=True,
    )
    doc.commitTransaction()
    assert len(repeated_doors) == 2
    assert repeated_door_summary["removed_count"] == 2
    assert len(generated(doc, GENERATED_BY_DOORS)) == 2
    assert len(generated(doc, GENERATED_BY_WINDOWS)) == 2

    doc.saveAs(output)
    document_name = doc.Name
    FreeCAD.closeDocument(document_name)
    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    reopened.recompute()
    reopened_doors = generated(reopened, GENERATED_BY_DOORS)
    reopened_windows = generated(reopened, GENERATED_BY_WINDOWS)
    assert len(reopened_doors) == 2
    assert len(reopened_windows) == 2
    assert all(obj.Hosts == [obj.FA_HostWall] for obj in reopened_doors + reopened_windows)
    assert all(float(obj.FA_CutVolume_mm3) > 0.0 for obj in reopened_doors + reopened_windows)
    reopened_level = next(obj for obj in reopened.Objects if getattr(obj, "IfcType", "") == "Building Storey")
    assert all(obj not in reopened_level.Group and obj.Base not in reopened_level.Group for obj in reopened_doors + reopened_windows)
    assert all(obj.FA_TargetLevel == reopened_level.Name and obj.Base.FA_TargetLevel == reopened_level.Name for obj in reopened_doors + reopened_windows)
    assert reopened.getObject("FA_Doors") is None
    assert reopened.getObject("FA_Windows") is None
    FreeCAD.closeDocument(reopened.Name)
    print(
        "FA_OPENINGS_END_TO_END_OK",
        output,
        "doors=2 windows=2 walls=2 undo=ok idempotence=ok persistence=ok",
    )


if __name__ == "__main__":
    main()
