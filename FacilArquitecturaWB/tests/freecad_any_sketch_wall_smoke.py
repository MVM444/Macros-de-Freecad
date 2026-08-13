"""FreeCADCmd smoke test for converting an arbitrary Sketch into an Arch Wall."""

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
    GENERATED_BY_WALLS,
    create_walls_from_centerline_sketches,
    prepare_sketches_as_wall_centerlines,
)


def _generated_walls(doc):
    return [
        obj
        for obj in doc.Objects
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == GENERATED_BY_WALLS
    ]


def main():
    output = os.path.join(REPO_DIR, ".codex_tmp", "any_sketch_wall_smoke.FCStd")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    doc = FreeCAD.newDocument("AnySketchWallSmoke")
    doc.UndoMode = 1
    bim_group = doc.addObject("App::DocumentObjectGroup", "FA_BIM_Test")
    sketch = doc.addObject("Sketcher::SketchObject", "SketchSinMetadatos")
    sketch.Label = "Sketch cualquiera sin metadatos"
    sketch.addGeometry(
        Part.LineSegment(FreeCAD.Vector(0.0, 0.0, 0.0), FreeCAD.Vector(4000.0, 0.0, 0.0)),
        False,
    )
    doc.recompute()

    doc.openTransaction("Convert generic Sketch to Arch Wall")
    prepared = prepare_sketches_as_wall_centerlines(
        [sketch], thickness=125.0, height=2850.0, wall_type="interior"
    )
    walls = create_walls_from_centerline_sketches(
        doc, bim_group, prepared, {"wall_height_mm": 3000.0}
    )
    doc.recompute()
    doc.commitTransaction()

    assert len(walls) == 1
    wall = walls[0]
    assert wall.FA_SourceSketch is sketch
    assert wall.Base is sketch
    assert abs(sketch.FA_WallThickness.Value - 125.0) < 1e-7
    assert abs(sketch.FA_WallHeight.Value - 2850.0) < 1e-7
    assert sketch.FA_CenterlineKind == "walls"
    assert sketch.FA_Role == "centerlines"
    assert len(_generated_walls(doc)) == 1

    doc.undo()
    doc.recompute()
    assert len(_generated_walls(doc)) == 0
    assert doc.getObject("SketchSinMetadatos") is sketch
    doc.redo()
    doc.recompute()
    assert len(_generated_walls(doc)) == 1

    # Repeating the generator replaces the wall from this source without duplication.
    walls = create_walls_from_centerline_sketches(
        doc, bim_group, [sketch], {"wall_height_mm": 3000.0}
    )
    doc.recompute()
    assert len(walls) == 1
    assert len(_generated_walls(doc)) == 1
    doc.saveAs(output)
    document_name = doc.Name
    FreeCAD.closeDocument(document_name)

    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    reopened.recompute()
    restored_sketch = reopened.getObject("SketchSinMetadatos")
    restored_walls = _generated_walls(reopened)
    assert restored_sketch is not None
    assert len(restored_walls) == 1
    assert restored_walls[0].FA_SourceSketch is restored_sketch
    assert restored_walls[0].Base is restored_sketch
    FreeCAD.closeDocument(reopened.Name)
    print("ANY_SKETCH_WALL_SMOKE_OK", output)


if __name__ == "__main__":
    main()

