import math
import unittest

from FacilArquitecturaWB.core.door_corner_utils import (
    desired_open_leaf_vector,
    plan_door_corner_snap,
    resolve_native_opening_mode,
)


def wall(key, width, *segments):
    return {"wall_key": key, "label": key, "width_mm": width, "segments": list(segments)}


class DoorCornerSnapTests(unittest.TestCase):
    def test_start_jamb_snaps_to_side_wall_face_and_swings_toward_wall(self):
        # Host x-axis. Side wall centerline x=0, width 100, extending +Y.
        opening = (80, 0, 0, 980, 0, 0)
        records = [
            wall("host", 100, (-2000, 0, 0, 5000, 0, 0)),
            wall("side", 100, (0, 0, 0, 0, 3000, 0)),
        ]
        plan = plan_door_corner_snap(opening, "host", records)
        self.assertTrue(plan["applied"])
        self.assertEqual("START", plan["hinge_endpoint"])
        self.assertEqual("LEFT", plan["opening_side"])
        self.assertTrue(plan["opens_inward"])
        self.assertAlmostEqual(-30.0, plan["shift_mm"], places=6)
        self.assertAlmostEqual(50.0, plan["projected_first"][0], places=6)
        self.assertAlmostEqual(950.0, plan["projected_second"][0], places=6)
        self.assertAlmostEqual(900.0, math.dist(plan["projected_first"][:2], plan["projected_second"][:2]), places=6)

    def test_end_jamb_is_detected_without_changing_width(self):
        opening = (1000, 0, 0, 1900, 0, 0)
        records = [
            wall("host", 100, (0, 0, 0, 4000, 0, 0)),
            wall("side", 120, (2000, 0, 0, 2000, 2500, 0)),
        ]
        plan = plan_door_corner_snap(opening, "host", records)
        self.assertTrue(plan["applied"])
        self.assertEqual("END", plan["hinge_endpoint"])
        self.assertEqual("LEFT", plan["opening_side"])
        self.assertAlmostEqual(40.0, plan["shift_mm"], places=6)
        self.assertAlmostEqual(1040.0, plan["projected_first"][0], places=6)
        self.assertAlmostEqual(1940.0, plan["projected_second"][0], places=6)

    def test_side_wall_beyond_tolerance_does_not_move(self):
        opening = (300, 0, 0, 1200, 0, 0)
        records = [
            wall("host", 100, (-1000, 0, 0, 4000, 0, 0)),
            wall("side", 100, (0, 0, 0, 0, 2500, 0)),
        ]
        plan = plan_door_corner_snap(opening, "host", records, tolerance_mm=180)
        self.assertFalse(plan["applied"])
        self.assertFalse(plan["ambiguous"])

    def test_two_equivalent_side_walls_are_ambiguous(self):
        opening = (80, 0, 0, 920, 0, 0)
        records = [
            wall("host", 100, (-1000, 0, 0, 2000, 0, 0)),
            wall("left", 100, (0, 0, 0, 0, 2500, 0)),
            wall("right", 100, (1000, 0, 0, 1000, 2500, 0)),
        ]
        plan = plan_door_corner_snap(opening, "host", records, ambiguity_margin_mm=20)
        self.assertFalse(plan["applied"])
        self.assertTrue(plan["ambiguous"])

    def test_crossing_side_wall_aligns_jamb_but_does_not_invent_swing(self):
        opening = (80, 0, 0, 980, 0, 0)
        records = [
            wall("host", 100, (-1000, 0, 0, 4000, 0, 0)),
            wall("cross", 100, (0, -1500, 0, 0, 1500, 0)),
        ]
        plan = plan_door_corner_snap(opening, "host", records)
        self.assertTrue(plan["applied"])
        self.assertEqual("JAMB_ONLY", plan["status"])
        self.assertEqual("START", plan["jamb_endpoint"])
        self.assertEqual("AUTO", plan["hinge_endpoint"])
        self.assertEqual("AUTO", plan["opening_side"])
        self.assertFalse(plan["swing_resolved"])
        self.assertIsNotNone(plan["jamb_face_candidate"])
        self.assertIsNone(plan["swing_direction_candidate"])

    def test_jamb_only_face_inside_opening_preserves_projected_position(self):
        # The crossing wall face is 50 mm along the opening itself.  It is not an
        # exterior jamb, so moving the entire door to it would create a regression.
        opening = (-14.386719, 0, 0, 804.823242, 0, 0)
        records = [
            wall("host", 100, (-2000, 0, 0, 3000, 0, 0)),
            wall("cross", 100, (0, -1500, 0, 0, 1500, 0)),
        ]

        plan = plan_door_corner_snap(opening, "host", records)

        self.assertFalse(plan["applied"])
        self.assertEqual("JAMB_ONLY", plan["status"])
        self.assertTrue(plan["face_inside_opening"])
        self.assertEqual("START", plan["jamb_endpoint"])
        self.assertEqual("AUTO", plan["hinge_endpoint"])
        self.assertAlmostEqual(64.386719, plan["proposed_shift_mm"], places=6)
        self.assertEqual(list(opening[:3]), plan["projected_first"])
        self.assertEqual(list(opening[3:]), plan["projected_second"])

    def test_real_1416_geometry_index_8_reports_exact_no_fit(self):
        opening = (51.499, 0, 0, 954.535, 0, 0)
        records = [
            wall("host", 100, (-1000, 0, 0, 3000, 0, 0)),
            wall("left", 100, (0, 0, 0, 0, 2500, 0)),
            wall("right", 100, (930, 0, 0, 930, 2500, 0)),
        ]

        plan = plan_door_corner_snap(opening, "host", records)

        self.assertFalse(plan["applied"])
        self.assertTrue(plan["no_fit"])
        self.assertEqual("NO_FIT", plan["status"])
        self.assertAlmostEqual(903.036, plan["opening_width_mm"], places=3)
        self.assertAlmostEqual(830.0, plan["available_width_mm"], places=3)
        self.assertAlmostEqual(73.036, plan["penetration_mm"], places=3)
        self.assertEqual(list(opening[:3]), plan["projected_first"])
        self.assertEqual(list(opening[3:]), plan["projected_second"])

    def test_real_1416_geometry_index_1_is_bounded_and_keeps_sketch_position(self):
        opening = (3919.002763613392, 9175.0, 0, 3255.1521616105833, 9175.0, 0)
        records = [
            wall("host", 150, (552.3444237317234, 9175, 0, 6665.344423731714, 9175, 0)),
            wall("right", 150, (4050.344423731714, 9175, 0, 4050.344423731714, 11995, 0)),
            wall("left", 150, (3070.344423731714, 7544, 0, 3070.344423731714, 9175, 0)),
        ]

        plan = plan_door_corner_snap(opening, "host", records)

        self.assertFalse(plan["applied"])
        self.assertEqual("BOUNDED", plan["status"])
        self.assertTrue(plan["position_preserved"])
        self.assertTrue(plan["bounded_by_opposite_faces"])
        self.assertTrue(plan["swing_resolved"])
        self.assertEqual("START", plan["hinge_endpoint"])
        self.assertEqual("RIGHT", plan["opening_side"])
        self.assertAlmostEqual(830.0, plan["available_width_mm"], places=5)
        self.assertAlmostEqual(166.149397997, plan["clearance_mm"], places=5)
        self.assertAlmostEqual(-56.341660119, plan["proposed_shift_mm"], places=5)
        self.assertEqual(list(opening[:3]), plan["projected_first"])
        self.assertEqual(list(opening[3:]), plan["projected_second"])

    def test_real_1416_geometry_index_3_keeps_face_but_swing_auto(self):
        opening = (6719.951637715584, 11995.0, 0, 7445.871678262161, 11995.0, 0)
        records = [
            wall("host", 150, (6000, 11995, 0, 8000, 11995, 0)),
            wall("cross", 150, (6590.344423731714, 11000, 0, 6590.344423731714, 13000, 0)),
        ]

        plan = plan_door_corner_snap(opening, "host", records)

        self.assertTrue(plan["applied"])
        self.assertEqual("JAMB_ONLY", plan["status"])
        self.assertEqual("START", plan["jamb_endpoint"])
        self.assertEqual("AUTO", plan["hinge_endpoint"])
        self.assertEqual("AUTO", plan["opening_side"])
        self.assertAlmostEqual(6665.344423731714, plan["projected_first"][0], places=6)

    def test_native_mode_uses_physical_vectors_and_is_direction_invariant(self):
        forward = (0, 0, 0, 900, 0, 0)
        reverse = (900, 0, 0, 0, 0, 0)
        desired_forward = desired_open_leaf_vector(forward, "LEFT")
        desired_reverse = desired_open_leaf_vector(reverse, "RIGHT")

        first = resolve_native_opening_mode(forward, (0, 0), desired_forward)
        second = resolve_native_opening_mode(reverse, (0, 0), desired_reverse)

        self.assertEqual((0.0, 1.0), desired_forward)
        self.assertEqual((0.0, 1.0), desired_reverse)
        self.assertTrue(first["resolved"])
        self.assertTrue(second["resolved"])
        self.assertEqual("Mode1", first["mode"])
        self.assertEqual("Mode1", second["mode"])
        self.assertEqual(first["desired_leaf_vector"], second["desired_leaf_vector"])

    def test_native_mode_selects_mode2_for_physical_right_normal(self):
        opening = (0, 0, 0, 900, 0, 0)
        desired = desired_open_leaf_vector(opening, "RIGHT")
        plan = resolve_native_opening_mode(opening, (0, 0), desired)

        self.assertTrue(plan["resolved"])
        self.assertEqual("Mode2", plan["mode"])
        self.assertEqual([0.0, -1.0], plan["desired_leaf_vector"])

    def test_oblique_side_wall_uses_actual_face_intersection(self):
        # 80-degree side wall relative to host, still within tolerance.
        angle = math.radians(80.0)
        end = (math.cos(angle) * 2500, math.sin(angle) * 2500)
        opening = (100, 0, 0, 1000, 0, 0)
        records = [
            wall("host", 100, (-1000, 0, 0, 4000, 0, 0)),
            wall("side", 100, (0, 0, 0, end[0], end[1], 0)),
        ]
        plan = plan_door_corner_snap(opening, "host", records)
        self.assertTrue(plan["applied"])
        expected_face = 50.0 / math.cos(math.radians(10.0))
        self.assertAlmostEqual(expected_face, plan["projected_first"][0], places=5)


if __name__ == "__main__":
    unittest.main()
