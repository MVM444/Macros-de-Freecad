"""Synthetic tests for closed-room polygonization."""

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
    if "Sketcher" not in sys.modules:
        sketcher = types.ModuleType("Sketcher")
        sketcher.Constraint = lambda *args: args
        sys.modules["Sketcher"] = sketcher


_install_freecad_stubs()

from FacilArquitecturaWB.core import room_utils as rooms  # noqa: E402


class RoomTopologyTests(unittest.TestCase):
    def setUp(self):
        self.walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2200.0, 0.0, 4000.0, 0.0),
            (4000.0, 0.0, 4000.0, 4000.0),
            (4000.0, 4000.0, 0.0, 4000.0),
            (0.0, 4000.0, 0.0, 0.0),
            (2000.0, 0.0, 2000.0, 1700.0),
            (2000.0, 2500.0, 2000.0, 4000.0),
        ]
        self.window = [(1800.0, 0.0, 2200.0, 0.0)]
        self.door = [(2000.0, 1700.0, 2000.0, 2500.0)]

    def test_wall_window_and_door_centers_create_two_rooms(self):
        topology = rooms.build_room_topology(
            self.walls + self.window + self.door,
            snap_tolerance=10.0,
            minimum_room_area_mm2=100000.0,
        )

        self.assertEqual(2, len(topology["faces"]))
        self.assertEqual([8.0, 8.0], sorted(round(face["area"] / 1000000.0, 3) for face in topology["faces"]))
        keys = {
            tuple(sorted((rooms._node_key(first), rooms._node_key(second))))
            for first, second in topology["edges"]
        }
        self.assertEqual(len(keys), len(topology["edges"]))

    def test_missing_door_keeps_one_combined_room(self):
        topology = rooms.build_room_topology(
            self.walls + self.window,
            snap_tolerance=10.0,
            minimum_room_area_mm2=100000.0,
        )

        self.assertEqual(1, len(topology["faces"]))
        self.assertAlmostEqual(16.0, topology["faces"][0]["area"] / 1000000.0)

    def test_missing_exterior_window_bridge_leaves_no_closed_room(self):
        topology = rooms.build_room_topology(
            self.walls + self.door,
            snap_tolerance=10.0,
            minimum_room_area_mm2=100000.0,
        )

        self.assertEqual(0, len(topology["faces"]))

    def test_nearby_endpoints_snap_into_closed_room(self):
        segments = [
            (0.0, 0.0, 4000.0, 0.0),
            (4006.0, 3.0, 4000.0, 4000.0),
            (4000.0, 4000.0, 0.0, 4000.0),
            (-4.0, 3997.0, 0.0, 0.0),
        ]

        topology = rooms.build_room_topology(
            segments,
            snap_tolerance=10.0,
            minimum_room_area_mm2=100000.0,
        )

        self.assertEqual(1, len(topology["faces"]))


class WallGapClosingTests(unittest.TestCase):
    def test_empty_optional_opening_list_is_valid(self):
        self.assertEqual([], rooms._unique_sources([]))

    def test_horizontal_opening_extends_both_lines_to_shared_midpoint(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]
        openings = [(1800.0, 0.0, 2600.0, 0.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(1, len(bridges))
        self.assertEqual((0.0, 0.0, 2200.0, 0.0), adjusted[0])
        self.assertEqual((2200.0, 0.0, 5000.0, 0.0), adjusted[1])

    def test_vertical_opening_preserves_line_position_and_orientation(self):
        walls = [
            (1250.0, 0.0, 1250.0, 1700.0),
            (1250.0, 2500.0, 1250.0, 5000.0),
        ]
        openings = [(1250.0, 1700.0, 1250.0, 2500.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(1, len(bridges))
        self.assertEqual((1250.0, 0.0, 1250.0, 2100.0), adjusted[0])
        self.assertEqual((1250.0, 2100.0, 1250.0, 5000.0), adjusted[1])

    def test_diagonal_opening_keeps_original_diagonal_axis(self):
        walls = [
            (0.0, 0.0, 1000.0, 1000.0),
            (2000.0, 2000.0, 3000.0, 3000.0),
        ]
        openings = [(1000.0, 1000.0, 2000.0, 2000.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(1, len(bridges))
        self.assertEqual((0.0, 0.0, 1500.0, 1500.0), adjusted[0])
        self.assertEqual((1500.0, 1500.0, 3000.0, 3000.0), adjusted[1])

    def test_perpendicular_opening_does_not_close_wall_gap(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]
        openings = [(2200.0, -400.0, 2200.0, 400.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual([], bridges)
        self.assertEqual(walls, adjusted)

    def test_gap_without_opening_remains_unchanged_by_default(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, [])

        self.assertEqual([], bridges)
        self.assertEqual(walls, adjusted)

    def test_unmarked_gap_can_be_closed_explicitly(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, [], allow_unmarked=True)

        self.assertEqual(1, len(bridges))
        self.assertEqual(adjusted[0][2:], adjusted[1][:2])


if __name__ == "__main__":
    unittest.main()
