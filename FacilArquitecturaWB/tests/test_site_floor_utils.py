"""Tests for plan-sketch collection and floor bounds."""

from __future__ import annotations

import sys
import types
import unittest


def _install_freecad_stubs():
    if "FreeCAD" not in sys.modules:
        freecad = types.ModuleType("FreeCAD")
        freecad.Console = types.SimpleNamespace(
            PrintMessage=lambda _message: None,
            PrintWarning=lambda _message: None,
            PrintError=lambda _message: None,
        )
        sys.modules["FreeCAD"] = freecad
    if "Part" not in sys.modules:
        sys.modules["Part"] = types.ModuleType("Part")


_install_freecad_stubs()

from FacilArquitecturaWB.core import site_floor_utils as site_floor  # noqa: E402


class BoundBox:
    def __init__(self, x_min, y_min, x_max, y_max):
        self.XMin = float(x_min)
        self.YMin = float(y_min)
        self.XMax = float(x_max)
        self.YMax = float(y_max)


class Sketch:
    def __init__(self, name, bounds, role="centerlines", kind="walls"):
        self.Name = name
        self.Label = name
        self.TypeId = "Sketcher::SketchObject"
        self.Geometry = [object()]
        self.Shape = types.SimpleNamespace(BoundBox=BoundBox(*bounds), Edges=[object()])
        self.FA_Role = role
        self.FA_CenterlineKind = kind


class SiteFloorUtilsTests(unittest.TestCase):
    def test_collects_plan_sketches_and_excludes_axes_columns_and_floor(self):
        wall = Sketch("Sketch_Centros_Muros", (0.0, 0.0, 10000.0, 8000.0))
        door = Sketch("Sketch_Centros_Puertas", (1000.0, 0.0, 2000.0, 100.0))
        axes = Sketch("Sketch_Ejes", (0.0, 0.0, 10000.0, 8000.0), role="")
        columns = Sketch("Sketch_Centros_Columnas", (0.0, 0.0, 1000.0, 1000.0), kind="columns")
        floor = Sketch("Sketch_Losa_Piso", (0.0, 0.0, 10000.0, 8000.0), role="")
        doc = types.SimpleNamespace(Objects=[wall, door, axes, columns, floor])

        result = site_floor.collect_plan_sketches(doc)

        self.assertEqual([wall, door], result)

    def test_combined_bounds_use_all_architectural_sketches(self):
        wall = Sketch("Sketch_Centros_Muros", (0.0, 0.0, 10000.0, 8000.0))
        window = Sketch("Sketch_Centros_Ventanas", (-200.0, 1000.0, 10200.0, 7000.0))

        bounds = site_floor.combined_sketch_bounds([wall, window])

        self.assertEqual((-200.0, 0.0, 10200.0, 8000.0), bounds)


if __name__ == "__main__":
    unittest.main()
