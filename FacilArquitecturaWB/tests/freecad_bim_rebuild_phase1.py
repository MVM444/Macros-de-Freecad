"""FreeCAD smoke test for native Building/Level and direct Sketch-to-Wall.

Descripcion: valida estructura espacial, Base directa, parametricidad y persistencia.
Objetivo: bloquear la fase 1 hasta comprobar que editar el Sketch modifica el Wall.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 21:24 UTC-06:00.
Version: 0.1.0.
Instrucciones de mantenimiento: guardar solo en .codex_tmp y nunca abrir un original.
"""

from __future__ import annotations

import os
import sys

import FreeCAD
import Part
import Sketcher


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.core.bim_structure_utils import ensure_bim_structure  # noqa: E402
from FacilArquitecturaWB.core.bim_utils import (  # noqa: E402
    create_walls_from_centerline_sketches,
    prepare_sketches_as_wall_centerlines,
)


def generated_walls(doc):
    return [
        obj
        for obj in doc.Objects
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == "FA_CreateWallsBIM"
    ]


def main():
    output = os.path.join(REPO_DIR, ".codex_tmp", "fa_bim_rebuild_phase1.FCStd")
    doc = FreeCAD.newDocument("FA_BIM_Rebuild_Phase1")
    doc.UndoMode = 1
    sketch = doc.addObject("Sketcher::SketchObject", "Sketch_Muros")
    sketch.Label = "Sketch_Muros"
    sketch.addGeometry(
        Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(5000, 0, 0)),
        False,
    )
    length_constraint = sketch.addConstraint(Sketcher.Constraint("Distance", 0, 5000.0))
    doc.openTransaction("Create native BIM phase 1")
    structure = ensure_bim_structure(doc, "Edificio de prueba", "Nivel 00", 0.0)
    prepare_sketches_as_wall_centerlines([sketch], 150.0, 3000.0, "interior")
    walls = create_walls_from_centerline_sketches(
        doc,
        structure["level"],
        [sketch],
        {"wall_height_mm": 3000.0},
        target_level=structure["level"],
    )
    doc.recompute()
    doc.commitTransaction()
    wall = walls[0]
    assert wall.Base is sketch
    assert wall.IfcType == "Wall"
    assert wall in structure["level"].Group
    assert structure["level"] in structure["building"].Group
    assert structure["building"].IfcType == "Building"
    assert structure["level"].IfcType == "Building Storey"
    assert doc.getObject("FA_Project") is None
    assert doc.getObject("FA_ReconstructedWallBase") is None
    initial_x = float(wall.Shape.BoundBox.XLength)

    sketch.setDatum(length_constraint, FreeCAD.Units.Quantity("6000 mm"))
    doc.recompute()
    changed_x = float(wall.Shape.BoundBox.XLength)
    assert changed_x > initial_x + 900.0

    doc.saveAs(output)
    sketch_name = sketch.Name
    wall_name = wall.Name
    level_name = structure["level"].Name
    building_name = structure["building"].Name
    FreeCAD.closeDocument(doc.Name)

    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    restored_sketch = reopened.getObject(sketch_name)
    restored_wall = reopened.getObject(wall_name)
    restored_level = reopened.getObject(level_name)
    restored_building = reopened.getObject(building_name)
    assert restored_wall.Base is restored_sketch
    assert restored_wall in restored_level.Group
    assert restored_level in restored_building.Group
    before_reopened_edit = float(restored_wall.Shape.BoundBox.XLength)
    restored_sketch.setDatum(length_constraint, FreeCAD.Units.Quantity("7000 mm"))
    reopened.recompute()
    assert float(restored_wall.Shape.BoundBox.XLength) > before_reopened_edit + 900.0

    reopened.openTransaction("Idempotent wall rebuild")
    structure_again = ensure_bim_structure(
        reopened,
        "Edificio de prueba",
        "Nivel 00",
        0.0,
    )
    create_walls_from_centerline_sketches(
        reopened,
        structure_again["level"],
        [restored_sketch],
        {"wall_height_mm": 3000.0},
        target_level=structure_again["level"],
    )
    reopened.recompute()
    reopened.commitTransaction()
    assert len(generated_walls(reopened)) == 1
    assert len([obj for obj in reopened.Objects if getattr(obj, "IfcType", "") == "Building"]) == 1
    assert len([obj for obj in reopened.Objects if getattr(obj, "IfcType", "") == "Building Storey"]) == 1
    reopened.undo()
    reopened.recompute()
    assert len(generated_walls(reopened)) == 1
    reopened.redo()
    reopened.recompute()
    assert len(generated_walls(reopened)) == 1
    reopened.save()
    FreeCAD.closeDocument(reopened.Name)
    print(
        "FA_BIM_REBUILD_PHASE1_OK",
        "base=direct parametricity=ok persistence=ok idempotence=ok undo_redo=ok",
        output,
    )


if __name__ == "__main__":
    main()
