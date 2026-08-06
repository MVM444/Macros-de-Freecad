"""Synthetic tests for BIM axis-family and source-cross detection."""

from __future__ import annotations

import math
import sys
import types
import unittest


def _install_freecad_stubs():
    if "FreeCAD" not in sys.modules:
        freecad = types.ModuleType("FreeCAD")
        freecad.Vector = lambda x, y, z=0.0: (float(x), float(y), float(z))
        freecad.Placement = lambda *args, **kwargs: object()
        freecad.Rotation = lambda *args, **kwargs: object()
        freecad.Console = types.SimpleNamespace(
            PrintMessage=lambda _message: None,
            PrintWarning=lambda _message: None,
            PrintError=lambda _message: None,
        )
        sys.modules["FreeCAD"] = freecad
    if "Arch" not in sys.modules:
        sys.modules["Arch"] = types.ModuleType("Arch")


_install_freecad_stubs()

from FacilArquitecturaWB.core import axis_utils  # noqa: E402


def _cross(x, y, half_length=200.0, angle_deg=0.0):
    angle = math.radians(float(angle_deg))
    u = (math.cos(angle), math.sin(angle))
    n = (-u[1], u[0])
    return [
        (
            x - half_length * u[0],
            y - half_length * u[1],
            0.0,
            x + half_length * u[0],
            y + half_length * u[1],
            0.0,
        ),
        (
            x - half_length * n[0],
            y - half_length * n[1],
            0.0,
            x + half_length * n[0],
            y + half_length * n[1],
            0.0,
        ),
    ]


def _grid_crosses(x_values, y_values, missing=None):
    missing = set(missing or [])
    segments = []
    for x_value in x_values:
        for y_value in y_values:
            if (x_value, y_value) not in missing:
                segments.extend(_cross(x_value, y_value))
    return segments


class Point:
    def __init__(self, x, y, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)


class Line:
    def __init__(self):
        self.StartPoint = Point(0.0, 0.0)
        self.EndPoint = Point(100.0, 0.0)


class FakeSketch:
    TypeId = "Sketcher::SketchObject"

    def __init__(self, name, kind="walls"):
        self.Name = name
        self.Label = name
        self.Geometry = [Line()]
        self.FA_CenterlineKind = kind


class AxisUtilsTests(unittest.TestCase):
    def test_non_uniform_complete_grid_preserves_axis_distances(self):
        segments = _grid_crosses([0.0, 4000.0, 9000.0], [0.0, 3000.0])

        specs, omitted = axis_utils.axis_family_specs_from_segments(segments)
        points = axis_utils.source_cross_points_from_specs(specs)

        self.assertEqual(0, omitted)
        self.assertEqual([3, 2], [len(spec["positions"]) for spec in specs])
        self.assertEqual([0.0, 4000.0, 5000.0], specs[0]["distances"])
        self.assertEqual([0.0, 3000.0], specs[1]["distances"])
        self.assertEqual(6, len(points))

    def test_partial_grid_keeps_only_crosses_drawn_in_sketch(self):
        segments = _grid_crosses(
            [0.0, 4000.0],
            [0.0, 3000.0],
            missing={(4000.0, 3000.0)},
        )

        specs, _omitted = axis_utils.axis_family_specs_from_segments(segments)
        points = axis_utils.source_cross_points_from_specs(specs)

        self.assertEqual(4, len(specs[0]["positions"]) * len(specs[1]["positions"]))
        self.assertEqual(3, len(points))
        self.assertNotIn((4000.0, 3000.0, 0.0), points)

    def test_rotated_cross_grid_is_detected_as_two_families(self):
        angle = math.radians(27.0)
        origin = (1250.0, -800.0)
        segments = []
        for local_x in (0.0, 3500.0, 8200.0):
            for local_y in (0.0, 2700.0):
                world_x = origin[0] + local_x * math.cos(angle) - local_y * math.sin(angle)
                world_y = origin[1] + local_x * math.sin(angle) + local_y * math.cos(angle)
                segments.extend(_cross(world_x, world_y, angle_deg=27.0))

        specs, omitted = axis_utils.axis_family_specs_from_segments(segments)
        points = axis_utils.source_cross_points_from_specs(specs)

        self.assertEqual(0, omitted)
        self.assertEqual([2, 3], sorted(len(spec["positions"]) for spec in specs))
        self.assertEqual(6, len(points))

    def test_third_direction_is_reported(self):
        segments = _grid_crosses([0.0, 4000.0], [0.0, 3000.0])
        segments.append((0.0, 0.0, 0.0, 2000.0, 2000.0, 0.0))

        _specs, omitted = axis_utils.axis_family_specs_from_segments(segments)

        self.assertEqual(1, omitted)

    def test_column_axis_sketch_is_preferred_in_mixed_selection(self):
        wall = FakeSketch("Sketch_Centros_Muros")
        columns = FakeSketch("Sketch_Centros_Plano_Columnas", kind="columns")

        selected = axis_utils.find_axis_sketch_from_selection([wall, columns])

        self.assertIs(columns, selected)


if __name__ == "__main__":
    unittest.main()
