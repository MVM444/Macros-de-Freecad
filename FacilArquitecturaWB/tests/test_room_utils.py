"""Synthetic tests for closed-room polygonization."""

from __future__ import annotations

import json
from pathlib import Path
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


class SelectionSketch:
    def __init__(self, name, thickness=0.0, kind=""):
        self.Name = name
        self.Label = name
        self.TypeId = "Sketcher::SketchObject"
        self.Geometry = [object()]
        self.FA_WallThickness = thickness
        self.FA_CenterlineKind = kind
        if thickness > 0.0:
            self.FA_Role = "centerlines"


class SelectionWall:
    def __init__(self, source):
        self.Name = "Wall"
        self.TypeId = "PartDesign::FeaturePython"
        self.Base = source


class WallSelectionTests(unittest.TestCase):
    def test_selected_bim_wall_uses_base_sketch(self):
        source = SelectionSketch("Sketch_Muro", thickness=125.0, kind="walls")

        candidates = rooms.collect_selected_wall_candidates([SelectionWall(source)])

        self.assertEqual([source], candidates)

    def test_generic_candidate_excludes_selected_opening(self):
        generic = SelectionSketch("Sketch_Generico")
        door = SelectionSketch("Sketch_Centros_Puertas")

        candidates = rooms.collect_selected_wall_candidates(
            [generic, door], opening_sketches=[door]
        )

        self.assertEqual([generic], candidates)

    def test_explicit_column_is_not_a_wall_conversion_candidate(self):
        column = SelectionSketch("Sketch_Columnas", kind="columns")

        candidates = rooms.collect_selected_wall_candidates([column])

        self.assertEqual([], candidates)

    def test_explicit_opening_selection_has_priority_over_document_scan(self):
        wall = SelectionSketch("Sketch_Muro", thickness=150.0, kind="walls")
        selected_door = SelectionSketch("Sketch_Centros_Puertas", kind="doors")
        other_window = SelectionSketch("Sketch_Centros_Ventanas", kind="windows")
        doc = types.SimpleNamespace(Objects=[other_window])

        openings, mode = rooms.resolve_opening_sketches(
            doc, selection=[wall, selected_door]
        )

        self.assertEqual("selection", mode)
        self.assertEqual([selected_door], openings)

    def test_no_selected_opening_uses_automatic_document_scan(self):
        wall = SelectionSketch("Sketch_Muro", thickness=150.0, kind="walls")
        door = SelectionSketch("Sketch_Centros_Puertas", kind="doors")
        window = SelectionSketch("Sketch_Centros_Ventanas", kind="windows")
        doc = types.SimpleNamespace(Objects=[door, window])

        openings, mode = rooms.resolve_opening_sketches(doc, selection=[wall])

        self.assertEqual("automatic", mode)
        self.assertEqual([door, window], openings)


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
    def test_opening_segment_maps_between_distinct_sketch_placements(self):
        class Vector:
            def __init__(self, x, y, z=0.0):
                self.x, self.y, self.z = float(x), float(y), float(z)

        class Placement:
            def __init__(self, dx, dy):
                self.dx, self.dy = float(dx), float(dy)

            def multVec(self, point):
                return Vector(point.x + self.dx, point.y + self.dy, point.z)

            def inverse(self):
                return Placement(-self.dx, -self.dy)

        old_vector = getattr(sys.modules["FreeCAD"], "Vector", None)
        sys.modules["FreeCAD"].Vector = Vector
        source = types.SimpleNamespace(getGlobalPlacement=lambda: Placement(100.0, 50.0))
        target = types.SimpleNamespace(getGlobalPlacement=lambda: Placement(20.0, 10.0))
        try:
            mapped = rooms._map_segment_between_sketches(
                (0.0, 0.0, 100.0, 0.0), source, target
            )
        finally:
            if old_vector is None:
                delattr(sys.modules["FreeCAD"], "Vector")
            else:
                sys.modules["FreeCAD"].Vector = old_vector

        self.assertEqual((80.0, 40.0, 180.0, 40.0), mapped)

    def test_real_1416_fixture_matches_every_known_opening(self):
        fixture_path = Path(__file__).with_name("fixtures") / "close_wall_gaps_1416.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        openings = [item["segment"] for item in fixture["openings"]]

        adjusted, bridges, report = rooms.bridge_wall_gaps(
            fixture["wall_segments"],
            openings,
            max_gap_mm=fixture["max_gap_mm"],
            alignment_tolerance_mm=fixture["alignment_tolerance_mm"],
            angle_tolerance_deg=fixture["angle_tolerance_deg"],
            wall_thickness_mm=fixture["wall_thickness_mm"],
            opening_mode="selection",
            opening_metadata=fixture["openings"],
            allow_mocheta_fallback=False,
            return_diagnostics=True,
        )

        expected = fixture["expected"]
        self.assertEqual(expected["opening_count"], report["candidate_openings"])
        self.assertEqual(expected["opening_region_count"], report["opening_region_count"])
        self.assertEqual(expected["matched_openings"], report["matched_openings"])
        self.assertEqual(expected["ambiguous_openings"], report["ambiguous_openings"])
        self.assertEqual(expected["rejected_openings"], report["rejected_openings"])
        self.assertEqual(expected["result_segment_count"], len(adjusted))
        self.assertEqual(expected["merge_count"], sum(1 for item in bridges if item["mode"] == "merge"))
        self.assertEqual(
            expected["extend_to_support_count"],
            sum(1 for item in bridges if item["mode"] == "extend_to_support"),
        )
        self.assertTrue(all(item["opening_refs"] for item in report["closures"]))

    def test_opening_longer_than_generic_gap_limit_is_valid_local_evidence(self):
        walls = [
            (0.0, 0.0, 1000.0, 0.0),
            (3900.0, 0.0, 5000.0, 0.0),
        ]
        openings = [(1050.0, 0.0, 3900.0, 0.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(
            walls,
            openings,
            max_gap_mm=2500.0,
        )

        self.assertEqual([(0.0, 0.0, 5000.0, 0.0)], adjusted)
        self.assertEqual(1, len(bridges))
        self.assertGreater(bridges[0]["gap_length"], 2500.0)

    def test_door_at_t_extends_wall_only_to_existing_support(self):
        walls = [
            (0.0, 0.0, 3000.0, 0.0),
            (2000.0, 1000.0, 2000.0, 3000.0),
        ]
        openings = [(2005.0, 100.0, 2005.0, 950.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(
            walls,
            openings,
            wall_thickness_mm=150.0,
        )

        self.assertEqual(1, len(bridges))
        self.assertEqual("extend_to_support", bridges[0]["mode"])
        self.assertIn((0.0, 0.0, 3000.0, 0.0), adjusted)
        self.assertIn((2000.0, 0.0, 2000.0, 3000.0), adjusted)

    def test_two_equivalent_physical_gaps_are_ambiguous(self):
        walls = [
            (0.0, -10.0, 1000.0, -10.0),
            (2000.0, -10.0, 3000.0, -10.0),
            (0.0, 10.0, 1000.0, 10.0),
            (2000.0, 10.0, 3000.0, 10.0),
        ]
        openings = [(1000.0, 0.0, 2000.0, 0.0)]

        adjusted, bridges, report = rooms.bridge_wall_gaps(
            walls,
            openings,
            alignment_tolerance_mm=5.0,
            allow_mocheta_fallback=False,
            return_diagnostics=True,
        )

        self.assertEqual(walls, adjusted)
        self.assertEqual([], bridges)
        self.assertEqual(1, report["ambiguous_openings"])
        self.assertEqual("AMBIGUOUS", report["rejections"][0]["reason"])

    def test_dry_run_report_does_not_mutate_inputs(self):
        walls = [(0.0, 0.0, 1000.0, 0.0), (2000.0, 0.0, 3000.0, 0.0)]
        openings = [(1000.0, 0.0, 2000.0, 0.0)]
        original_walls = list(walls)
        original_openings = list(openings)

        report = rooms.diagnose_wall_gap_closures(walls, openings)

        self.assertEqual(original_walls, walls)
        self.assertEqual(original_openings, openings)
        self.assertTrue(report["dry_run"])
        self.assertEqual(1, report["matched_openings"])

    def test_empty_optional_opening_list_is_valid(self):
        self.assertEqual([], rooms._unique_sources([]))

    def test_horizontal_opening_becomes_one_continuous_segment(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]
        openings = [(1800.0, 0.0, 2600.0, 0.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(1, len(bridges))
        self.assertEqual([(0.0, 0.0, 5000.0, 0.0)], adjusted)

    def test_vertical_opening_becomes_one_continuous_segment(self):
        walls = [
            (1250.0, 0.0, 1250.0, 1700.0),
            (1250.0, 2500.0, 1250.0, 5000.0),
        ]
        openings = [(1250.0, 1700.0, 1250.0, 2500.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(1, len(bridges))
        self.assertEqual([(1250.0, 0.0, 1250.0, 5000.0)], adjusted)

    def test_diagonal_opening_keeps_original_diagonal_axis(self):
        walls = [
            (0.0, 0.0, 1000.0, 1000.0),
            (2000.0, 2000.0, 3000.0, 3000.0),
        ]
        openings = [(1000.0, 1000.0, 2000.0, 2000.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(1, len(bridges))
        self.assertEqual(1, len(adjusted))
        for actual, expected in zip(adjusted[0], (0.0, 0.0, 3000.0, 3000.0)):
            self.assertAlmostEqual(expected, actual, places=6)

    def test_small_lateral_offset_projects_to_one_common_axis(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 4.0, 5000.0, 4.0),
        ]
        openings = [(1800.0, 2.0, 2600.0, 2.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(
            walls,
            openings,
            alignment_tolerance_mm=5.0,
        )

        self.assertEqual(1, len(bridges))
        self.assertEqual(1, len(adjusted))
        self.assertAlmostEqual(adjusted[0][1], adjusted[0][3], places=6)
        self.assertGreater(adjusted[0][1], 0.0)
        self.assertLess(adjusted[0][1], 4.0)

    def test_perpendicular_opening_crossing_gap_is_valid_zone_evidence(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]
        openings = [(2200.0, -400.0, 2200.0, 400.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(1, len(bridges))
        self.assertEqual([(0.0, 0.0, 5000.0, 0.0)], adjusted)

    def test_perpendicular_opening_far_from_gap_does_not_close(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]
        openings = [(3500.0, -400.0, 3500.0, 400.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual([], bridges)
        self.assertEqual(walls, adjusted)

    def test_parallel_opening_offset_from_wall_axis_is_valid_zone_evidence(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]
        openings = [(1800.0, 120.0, 2600.0, 120.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(1, len(bridges))
        self.assertEqual([(0.0, 0.0, 5000.0, 0.0)], adjusted)

    def test_selected_opening_scope_accepts_local_offset_evidence(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]
        # Deliberately offset from the wall axis. In explicit selection mode the
        # user already chose this opening sketch, so it is authoritative local
        # evidence for the nearby buque.
        openings = [(2200.0, 650.0, 2200.0, 950.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(
            walls,
            openings,
            opening_mode="selection",
            wall_thickness_mm=150.0,
        )

        self.assertEqual(1, len(bridges))
        self.assertEqual("selection", bridges[0].get("opening_mode"))
        self.assertEqual([(0.0, 0.0, 5000.0, 0.0)], adjusted)

    def test_automatic_scope_keeps_same_offset_evidence_conservative(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]
        openings = [(2200.0, 650.0, 2200.0, 950.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(
            walls,
            openings,
            opening_mode="automatic",
            wall_thickness_mm=150.0,
        )

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

    def test_unmarked_gap_is_not_closed_only_by_distance(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
        ]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, [], allow_unmarked=True)

        self.assertEqual([], bridges)
        self.assertEqual(walls, adjusted)

    def test_missing_opening_can_close_when_pair_of_mochetas_is_present(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
            (1800.0, 0.0, 1800.0, 150.0),
            (2600.0, 0.0, 2600.0, 155.0),
        ]

        adjusted, bridges = rooms.bridge_wall_gaps(
            walls,
            [],
            wall_thickness_mm=150.0,
            allow_mocheta_fallback=True,
        )

        self.assertEqual(1, len(bridges))
        self.assertEqual("mocheta", bridges[0].get("evidence"))
        self.assertIn((0.0, 0.0, 5000.0, 0.0), adjusted)

    def test_single_mocheta_is_not_enough_to_close_missing_opening(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
            (1800.0, 0.0, 1800.0, 150.0),
        ]

        adjusted, bridges = rooms.bridge_wall_gaps(
            walls,
            [],
            wall_thickness_mm=150.0,
            allow_mocheta_fallback=True,
        )

        self.assertEqual([], bridges)
        self.assertEqual(walls, adjusted)

    def test_two_openings_on_same_wall_reduce_three_segments_to_one(self):
        walls = [
            (0.0, 0.0, 1000.0, 0.0),
            (2000.0, 0.0, 3000.0, 0.0),
            (4000.0, 0.0, 5000.0, 0.0),
        ]
        openings = [
            (1000.0, 0.0, 2000.0, 0.0),
            (3000.0, 0.0, 4000.0, 0.0),
        ]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(2, len(bridges))
        self.assertEqual([(0.0, 0.0, 5000.0, 0.0)], adjusted)

    def test_consecutive_window_and_door_can_jointly_close_one_gap(self):
        walls = [
            (0.0, 0.0, 1000.0, 0.0),
            (3000.0, 0.0, 5000.0, 0.0),
        ]
        openings = [
            (1000.0, 0.0, 2000.0, 0.0),
            (2000.0, 0.0, 3000.0, 0.0),
        ]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual([(0.0, 0.0, 5000.0, 0.0)], adjusted)
        self.assertEqual(1, len(bridges))
        self.assertEqual((0, 1), bridges[0].get("opening_indices"))

    def test_perpendicular_wall_ends_extend_to_true_intersection(self):
        walls = [
            (0.0, 0.0, 1000.0, 0.0),
            (1400.0, 400.0, 1400.0, 1600.0),
        ]
        openings = [(1000.0, 0.0, 1400.0, 400.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(1, len(bridges))
        self.assertEqual("intersection", bridges[0].get("mode"))
        self.assertEqual(2, len(adjusted))
        self.assertEqual((0.0, 0.0, 1400.0, 0.0), adjusted[0])
        self.assertEqual((1400.0, 0.0, 1400.0, 1600.0), adjusted[1])

    def test_oblique_wall_end_extends_without_orthogonalizing(self):
        walls = [
            (0.0, 0.0, 700.0, 0.0),
            (1200.0, 400.0, 1800.0, 1000.0),
        ]
        openings = [(700.0, 0.0, 1200.0, 400.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual(1, len(bridges))
        self.assertEqual("intersection", bridges[0].get("mode"))
        self.assertEqual(2, len(adjusted))
        self.assertAlmostEqual(800.0, adjusted[0][2], places=6)
        self.assertAlmostEqual(0.0, adjusted[0][3], places=6)
        self.assertAlmostEqual(800.0, adjusted[1][0], places=6)
        self.assertAlmostEqual(0.0, adjusted[1][1], places=6)
        dx = adjusted[1][2] - adjusted[1][0]
        dy = adjusted[1][3] - adjusted[1][1]
        self.assertAlmostEqual(dx, dy, places=6)

    def test_crossing_wall_inside_opening_blocks_automatic_merge(self):
        walls = [
            (0.0, 0.0, 1800.0, 0.0),
            (2600.0, 0.0, 5000.0, 0.0),
            (2200.0, -500.0, 2200.0, 500.0),
        ]
        openings = [(1800.0, 0.0, 2600.0, 0.0)]

        adjusted, bridges = rooms.bridge_wall_gaps(walls, openings)

        self.assertEqual([], bridges)
        self.assertEqual(walls, adjusted)

    def test_opening_metadata_has_priority_over_name_heuristic(self):
        opening = SelectionSketch("Elemento_001", kind="windows")
        opening.Geometry = [types.SimpleNamespace(StartPoint=types.SimpleNamespace(x=0, y=0),
                                                  EndPoint=types.SimpleNamespace(x=1000, y=0))]
        self.assertTrue(rooms._is_opening_sketch(opening))

    def test_wall_metadata_is_never_treated_as_opening(self):
        wall = SelectionSketch("Puerta_que_en_realidad_es_muro", thickness=150.0, kind="walls")
        wall.Geometry = [types.SimpleNamespace(StartPoint=types.SimpleNamespace(x=0, y=0),
                                               EndPoint=types.SimpleNamespace(x=1000, y=0))]
        self.assertFalse(rooms._is_opening_sketch(wall))


if __name__ == "__main__":
    unittest.main()
