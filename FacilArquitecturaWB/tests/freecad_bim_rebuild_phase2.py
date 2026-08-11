"""FreeCAD smoke test for native columns generated from one Sketch.

Descripcion: valida columnas Arch Structure dentro de Level, trazabilidad,
parametricidad, persistencia e idempotencia sin grupos FA intermedios.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 22:10 UTC-06:00.
Version: 0.1.0.
Instrucciones de mantenimiento: guardar solo en .codex_tmp y nunca abrir un original.
"""

from __future__ import annotations

import os
import sys

import FreeCAD
import Part


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.core.axis_utils import (  # noqa: E402
    GENERATED_BY_AXES_COLUMNS,
    create_bim_axes_and_columns_from_sketch,
)
from FacilArquitecturaWB.core.bim_structure_utils import ensure_bim_structure  # noqa: E402


def _add_cross(sketch, x_value, y_value, half_length=250.0):
    sketch.addGeometry(
        Part.LineSegment(
            FreeCAD.Vector(x_value - half_length, y_value, 0),
            FreeCAD.Vector(x_value + half_length, y_value, 0),
        ),
        False,
    )
    sketch.addGeometry(
        Part.LineSegment(
            FreeCAD.Vector(x_value, y_value - half_length, 0),
            FreeCAD.Vector(x_value, y_value + half_length, 0),
        ),
        False,
    )


def _generated_columns(doc):
    return [
        obj
        for obj in doc.Objects
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == GENERATED_BY_AXES_COLUMNS
        and str(getattr(obj, "IfcType", "") or "") == "Column"
    ]


def main():
    output = os.path.join(REPO_DIR, ".codex_tmp", "fa_bim_rebuild_phase2.FCStd")
    doc = FreeCAD.newDocument("FA_BIM_Rebuild_Phase2")
    doc.UndoMode = 1
    sketch = doc.addObject("Sketcher::SketchObject", "Sketch_Columnas")
    for x_value in (0.0, 4000.0):
        for y_value in (0.0, 3000.0):
            _add_cross(sketch, x_value, y_value)
    params = {
        "axis_extension_mm": 500.0,
        "axis_cluster_tolerance_mm": 10.0,
        "column_width_mm": 400.0,
        "column_depth_mm": 300.0,
        "column_height_mm": 3000.0,
    }

    doc.openTransaction("Create native BIM phase 2")
    structure = ensure_bim_structure(doc, "Edificio de prueba", "Nivel 00", 0.0)
    result = create_bim_axes_and_columns_from_sketch(
        doc, structure["level"], sketch, params
    )
    doc.recompute()
    doc.commitTransaction()
    assert len(result["points"]) == 4
    assert len(result["columns"]) == 1
    column = result["columns"][0]
    assert column.IfcType == "Column"
    assert column in structure["level"].Group
    assert result["system"] in structure["level"].Group
    assert all(axis in structure["level"].Group for axis in result["axes"])
    assert column.FA_SourceSketch is sketch
    assert len(column.Shape.Solids) == 4
    assert not any(
        str(getattr(obj, "FA_Role", "") or "") == "columns_group"
        for obj in doc.Objects
    )

    original_x = float(column.Shape.BoundBox.XLength)
    sketch.FA_ColumnWidth = 600.0
    doc.recompute()
    assert float(column.Shape.BoundBox.XLength) > original_x + 150.0

    doc.saveAs(output)
    sketch_name = sketch.Name
    column_name = column.Name
    level_name = structure["level"].Name
    FreeCAD.closeDocument(doc.Name)

    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    restored_sketch = reopened.getObject(sketch_name)
    restored_column = reopened.getObject(column_name)
    restored_level = reopened.getObject(level_name)
    assert restored_column in restored_level.Group
    assert restored_column.FA_SourceSketch is restored_sketch
    restored_sketch.FA_ColumnDepth = 500.0
    reopened.recompute()
    assert abs(float(restored_column.Width.Value) - 500.0) < 0.01

    reopened.openTransaction("Idempotent column rebuild")
    again = create_bim_axes_and_columns_from_sketch(
        reopened, restored_level, restored_sketch, params
    )
    reopened.recompute()
    reopened.commitTransaction()
    assert len(_generated_columns(reopened)) == 1
    assert not any(
        str(getattr(obj, "FA_Role", "") or "") == "columns_group"
        for obj in reopened.Objects
    )
    reopened.undo()
    reopened.recompute()
    assert len(_generated_columns(reopened)) == 1
    reopened.redo()
    reopened.recompute()
    assert len(_generated_columns(reopened)) == 1
    assert len(again["points"]) == 4
    reopened.save()
    FreeCAD.closeDocument(reopened.Name)
    print(
        "FA_BIM_REBUILD_PHASE2_OK",
        "columns=native level=ok parametricity=ok persistence=ok idempotence=ok undo_redo=ok",
        output,
    )


if __name__ == "__main__":
    main()
