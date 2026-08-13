"""FreeCADCmd smoke test for closing wall gaps from a selected BIM wall."""

from __future__ import annotations

import os
import sys

import FreeCAD
import Part


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.core.bim_utils import (  # noqa: E402
    create_walls_from_centerline_sketches,
    prepare_sketches_as_wall_centerlines,
)
from FacilArquitecturaWB.core.room_utils import (  # noqa: E402
    GENERATED_BY_CLOSED_WALLS,
    collect_selected_wall_candidates,
    create_closed_wall_sketches,
)


def _closed_sketches(doc):
    return [
        obj
        for obj in doc.Objects
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == GENERATED_BY_CLOSED_WALLS
    ]


def main():
    output = os.path.join(REPO_DIR, ".codex_tmp", "close_any_sketch_smoke.FCStd")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    doc = FreeCAD.newDocument("CloseAnySketchSmoke")
    doc.UndoMode = 1
    bim_group = doc.addObject("App::DocumentObjectGroup", "FA_BIM_Test")
    sketch_group = doc.addObject("App::DocumentObjectGroup", "FA_Sketches_Test")

    source = doc.addObject("Sketcher::SketchObject", "SketchMuroGenerico")
    source.addGeometry(
        Part.LineSegment(FreeCAD.Vector(0.0, 0.0), FreeCAD.Vector(1800.0, 0.0)), False
    )
    source.addGeometry(
        Part.LineSegment(FreeCAD.Vector(2600.0, 0.0), FreeCAD.Vector(5000.0, 0.0)), False
    )
    door = doc.addObject("Sketcher::SketchObject", "Sketch_Centros_Puertas")
    door.addGeometry(
        Part.LineSegment(FreeCAD.Vector(1800.0, 0.0), FreeCAD.Vector(2600.0, 0.0)), False
    )
    doc.recompute()

    prepared = prepare_sketches_as_wall_centerlines(
        [source], thickness=125.0, height=2850.0, wall_type="interior"
    )
    walls = create_walls_from_centerline_sketches(
        doc, bim_group, prepared, {"wall_height_mm": 3000.0}
    )
    doc.recompute()
    assert len(walls) == 1

    candidates = collect_selected_wall_candidates(walls, opening_sketches=[door])
    assert candidates == [source]

    doc.openTransaction("Close gaps from selected BIM wall")
    closed, summary = create_closed_wall_sketches(
        doc,
        sketch_group,
        candidates,
        [door],
        replace_previous=True,
    )
    doc.recompute()
    doc.commitTransaction()

    assert len(closed) == 1
    assert summary["closed_gap_count"] == 1
    assert closed[0].FA_SourceWallSketch is source
    assert closed[0].FA_ClosedGapCount == 1
    assert abs(closed[0].FA_WallThickness.Value - 125.0) < 1e-7
    assert len(_closed_sketches(doc)) == 1

    doc.undo()
    doc.recompute()
    assert len(_closed_sketches(doc)) == 0
    doc.redo()
    doc.recompute()
    assert len(_closed_sketches(doc)) == 1

    doc.saveAs(output)
    document_name = doc.Name
    FreeCAD.closeDocument(document_name)
    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    restored = _closed_sketches(reopened)
    assert len(restored) == 1
    assert restored[0].FA_SourceWallSketch is reopened.getObject("SketchMuroGenerico")
    assert restored[0].FA_ClosedGapCount == 1
    FreeCAD.closeDocument(reopened.Name)
    print("CLOSE_ANY_SKETCH_SMOKE_OK", output)


if __name__ == "__main__":
    main()
