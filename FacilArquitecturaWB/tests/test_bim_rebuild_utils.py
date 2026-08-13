"""Pure tests for BIM rebuild Sketch classification.

Descripcion: valida prioridad de metadatos, nombres y asignacion manual.
Fecha y hora: 2026-08-09 23:05 UTC-06:00.
Version: 0.1.0.
"""

from __future__ import annotations

import sys
import types
import unittest


def _install_stubs():
    if "FreeCAD" not in sys.modules:
        freecad = types.ModuleType("FreeCAD")
        freecad.Placement = lambda *args, **kwargs: object()
        freecad.Vector = lambda *args, **kwargs: object()
        freecad.Rotation = lambda *args, **kwargs: object()
        freecad.Console = types.SimpleNamespace(
            PrintMessage=lambda _message: None,
            PrintWarning=lambda _message: None,
            PrintError=lambda _message: None,
        )
        sys.modules["FreeCAD"] = freecad
    if "Arch" not in sys.modules:
        sys.modules["Arch"] = types.ModuleType("Arch")


_install_stubs()

from FacilArquitecturaWB.core import bim_rebuild_utils as rebuild  # noqa: E402


class FakeSketch:
    TypeId = "Sketcher::SketchObject"

    def __init__(self, name, kind="", element="", thickness=0.0, role="centerlines"):
        self.Name = name
        self.Label = name
        self.Geometry = [object()]
        self.FA_CenterlineKind = kind
        self.FA_ElementType = element
        self.FA_WallThickness = thickness
        self.FA_Role = role


class FakeDocument:
    def __init__(self, objects):
        self.Objects = list(objects)


class RebuildClassificationTests(unittest.TestCase):
    def test_grid_wall_trace_beats_older_closed_wall_sketch(self):
        trace = FakeSketch("FA_GridWallTrace", "walls", thickness=150.0, role="grid_clipped_lines")
        closed = FakeSketch("Sketch_Cerrado_Sketch001", "walls", thickness=150.0)

        analysis = rebuild.suggest_rebuild_assignments(FakeDocument([closed, trace]))

        self.assertIs(trace, analysis["assignments"]["walls"])

    def test_la_cruz_columns_doors_and_all_named_windows_are_suggested(self):
        columns = FakeSketch("Sketch_Centros_Columna_Metalica_Columnas", "columns", "Columnas")
        doors = FakeSketch("Sketch_Centros_Puertas", "walls", "Puertas")
        window_a = FakeSketch("Sketch_Centros_Ventanas_de_S_S", "walls", "Ventanas")
        window_b = FakeSketch("Sketch_Centros_Ventanas001", "walls", "Ventanas")
        window_c = FakeSketch("Sketch_Centros_Ventanales", "walls", "Ventanales")
        generic = FakeSketch("Sketch_Centros_Seleccion_14_objetos", "walls", "Por definir")

        analysis = rebuild.suggest_rebuild_assignments(
            FakeDocument([columns, doors, window_a, window_b, window_c, generic])
        )

        self.assertIs(columns, analysis["assignments"]["columns"])
        self.assertIs(doors, analysis["assignments"]["doors"])
        self.assertEqual({window_a, window_b, window_c}, set(analysis["assignments"]["windows"]))
        generic_record = next(
            item for item in analysis["records"] if item["sketch"] is generic
        )
        self.assertIsNone(generic_record["suggested_role"])


if __name__ == "__main__":
    unittest.main()
