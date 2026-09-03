"""FreeCAD 1.1.3 smoke for FA Opening Elements from Sketch lines.

Descripcion: cubre lotes, Placement, hosts, reemplazo, persistencia y corte real.
Fecha y hora: 2026-08-12 18:20 UTC-06:00.
Version: 0.1.0.
Mantenimiento: usar solo documentos temporales y no cerrar documentos del usuario.
"""

from __future__ import annotations

import math
import os
import sys

import Arch
import FreeCAD
import Part
import Sketcher


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from FacilArquitecturaWB.core.bim_structure_utils import add_to_level, ensure_bim_structure  # noqa: E402
from FacilArquitecturaWB.core.opening_utils import (  # noqa: E402
    GENERATED_BY_OPENINGS,
    create_openings_from_centerlines,
)


def add_line(sketch, first, second):
    return sketch.addGeometry(
        Part.LineSegment(FreeCAD.Vector(*first), FreeCAD.Vector(*second)), False
    )


def point_on_segment(first, second, distance):
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    length = math.hypot(dx, dy)
    return first[0] + dx * distance / length, first[1] + dy * distance / length, 0.0


def make_wall(doc, level, name, first, second, width=200.0):
    axis = doc.addObject("Sketcher::SketchObject", name + "Axis")
    add_line(axis, (*first, 0.0), (*second, 0.0))
    wall = Arch.makeWall(axis, width=width, height=3000.0, name=name)
    add_to_level(level, wall, source_sketch=axis)
    return wall


def generated(doc):
    return [
        obj
        for obj in doc.Objects
        if str(getattr(obj, "FA_GeneratedBy", "")) == GENERATED_BY_OPENINGS
        and str(getattr(obj, "FA_Role", "")) == "opening"
    ]


def make_manual_marker(doc, name, role, generator="manual"):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = Part.Shape()
    obj.addProperty("App::PropertyString", "FA_Role", "Test")
    obj.addProperty("App::PropertyString", "FA_GeneratedBy", "Test")
    obj.FA_Role = role
    obj.FA_GeneratedBy = generator
    return obj


def main():
    output_dir = os.path.join(PROJECT_ROOT, ".codex_tmp")
    os.makedirs(output_dir, exist_ok=True)
    output = os.path.join(output_dir, "FA_openings_only_end_to_end.FCStd")
    doc = FreeCAD.newDocument("FAOpeningsOnlyEndToEnd")
    structure = ensure_bim_structure(doc, "Edificio abertura", "Nivel 00", 0.0)
    level = structure["level"]

    diagonal_first = (8000.0, 0.0)
    diagonal_second = (12000.0, 3000.0)
    walls = [
        make_wall(doc, level, "WallHorizontal", (0.0, 0.0), (6000.0, 0.0)),
        make_wall(doc, level, "WallVertical", (0.0, 8000.0), (0.0, 14000.0)),
        make_wall(doc, level, "WallDiagonal", diagonal_first, diagonal_second, 150.0),
        make_wall(doc, level, "WallAmbiguousA", (0.0, 16000.0), (4000.0, 16000.0)),
        make_wall(doc, level, "WallAmbiguousB", (0.0, 16040.0), (4000.0, 16040.0)),
        make_wall(doc, level, "WallElevated", (0.0, 5000.0), (5000.0, 5000.0)),
    ]

    source = doc.addObject("Sketcher::SketchObject", "Sketch_Centros_Aberturas")
    source.addProperty("App::PropertyString", "FA_CenterlineKind", "FacilArquitectura")
    source.FA_CenterlineKind = "openings"
    add_line(source, (500.0, 0.0, 0.0), (1300.0, 0.0, 0.0))
    add_line(source, (3500.0, 0.0, 0.0), (4700.0, 0.0, 0.0))
    add_line(source, (0.0, 11000.0, 0.0), (0.0, 11900.0, 0.0))
    add_line(
        source,
        point_on_segment(diagonal_first, diagonal_second, 900.0),
        point_on_segment(diagonal_first, diagonal_second, 1900.0),
    )
    add_line(source, (10000.0, 10000.0, 0.0), (10800.0, 10000.0, 0.0))
    add_line(source, (1000.0, 16020.0, 0.0), (2000.0, 16020.0, 0.0))

    translated = doc.addObject("Sketcher::SketchObject", "Sketch_Aberturas_Trasladado")
    add_line(translated, (0.0, 0.0, 0.0), (1100.0, 0.0, 0.0))
    translated.Placement.Base = FreeCAD.Vector(2000.0, 0.0, 0.0)

    rotated = doc.addObject("Sketcher::SketchObject", "Sketch_Aberturas_Rotado")
    add_line(rotated, (0.0, 0.0, 0.0), (1000.0, 0.0, 0.0))
    rotated.Placement = FreeCAD.Placement(
        FreeCAD.Vector(0.0, 9000.0, 0.0),
        FreeCAD.Rotation(FreeCAD.Vector(0.0, 0.0, 1.0), 90.0),
    )

    elevated = doc.addObject("Sketcher::SketchObject", "Sketch_Abertura_Elevada")
    add_line(elevated, (1500.0, 5000.0, 0.0), (2800.0, 5000.0, 0.0))
    doc.recompute()

    before_volumes = {wall.Name: float(wall.Shape.Volume) for wall in walls}
    manual = make_manual_marker(doc, "ManualOpening", "opening")
    door = make_manual_marker(doc, "ExistingDoor", "door", "FA_CreateDoorsFromSketch")
    window = make_manual_marker(doc, "ExistingWindow", "window", "FA_CreateWindowsFromSketch")

    created, summary = create_openings_from_centerlines(
        doc,
        level,
        [source, translated, rotated],
        walls,
        "opening",
        height_mm=2100.0,
        sill_mm=0.0,
        host_tolerance_mm=100.0,
        replace_existing=True,
    )
    assert len(created) == 6, summary
    assert summary["rejected_count"] == 2, summary
    assert sorted(round(float(obj.FA_Width_mm), 3) for obj in created) == [800.0, 900.0, 1000.0, 1000.0, 1100.0, 1200.0]
    assert all(abs(float(obj.FA_Height_mm) - 2100.0) < 0.01 for obj in created)
    assert all(abs(float(obj.FA_Sill_mm)) < 0.01 for obj in created)
    assert all(obj.IfcType == "Opening Element" for obj in created)
    assert all(list(obj.WindowParts) == [] for obj in created)
    assert all(len(obj.Shape.Solids) == 0 for obj in created)
    assert all(not bool(obj.SymbolPlan) for obj in created)
    assert all(obj.Hosts == [obj.FA_HostWall] for obj in created)
    assert all(obj not in level.Group and obj.Base not in level.Group for obj in created)
    assert all(
        obj.FA_TargetLevel == level.Name and obj.Base.FA_TargetLevel == level.Name
        for obj in created
    )
    assert all(float(obj.FA_CutVolume_mm3) > 1.0 for obj in created)
    for wall in {obj.FA_HostWall for obj in created}:
        assert float(wall.Shape.Volume) < before_volumes[wall.Name] - 1.0

    elevated_created, elevated_summary = create_openings_from_centerlines(
        doc,
        level,
        [elevated],
        walls,
        "opening",
        height_mm=2400.0,
        sill_mm=300.0,
        host_tolerance_mm=100.0,
        replace_existing=True,
    )
    assert elevated_summary["created_count"] == 1
    assert abs(float(elevated_created[0].FA_Height_mm) - 2400.0) < 0.01
    assert abs(float(elevated_created[0].FA_Sill_mm) - 300.0) < 0.01
    assert abs(float(elevated_created[0].Base.Shape.BoundBox.ZMin) - 300.0) < 0.01

    repeated, repeated_summary = create_openings_from_centerlines(
        doc,
        level,
        [source, translated, rotated],
        walls,
        "opening",
        height_mm=2100.0,
        sill_mm=0.0,
        host_tolerance_mm=100.0,
        replace_existing=True,
    )
    assert len(repeated) == 6
    assert repeated_summary["removed_count"] == 6
    assert len(generated(doc)) == 7
    assert doc.getObject(manual.Name) is manual
    assert doc.getObject(door.Name) is door
    assert doc.getObject(window.Name) is window

    doc.saveAs(output)
    FreeCAD.closeDocument(doc.Name)
    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    restored = generated(reopened)
    assert len(restored) == 7
    assert all(obj.IfcType == "Opening Element" for obj in restored)
    assert all(list(obj.WindowParts) == [] and len(obj.Shape.Solids) == 0 for obj in restored)
    assert all(obj.Hosts == [obj.FA_HostWall] for obj in restored)
    reopened_level = next(
        obj for obj in reopened.Objects
        if getattr(obj, "IfcType", "") == "Building Storey"
    )
    assert all(
        obj not in reopened_level.Group and obj.Base not in reopened_level.Group
        for obj in restored
    )
    assert all(
        obj.FA_TargetLevel == reopened_level.Name
        and obj.Base.FA_TargetLevel == reopened_level.Name
        for obj in restored
    )
    assert reopened.getObject("ManualOpening") is not None
    assert reopened.getObject("ExistingDoor") is not None
    assert reopened.getObject("ExistingWindow") is not None
    FreeCAD.closeDocument(reopened.Name)
    print(
        "FA_OPENINGS_ONLY_END_TO_END_OK",
        "created=6 elevated=1 rejected=2 replacement=ok semantics=ok persistence=ok",
        output,
    )


if __name__ == "__main__":
    main()
