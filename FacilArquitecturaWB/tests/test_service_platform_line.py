"""Pure tests for line-driven platform orientation and compact modular planning."""

from __future__ import annotations

import math
import unittest

from FacilArquitecturaWB.modules.service_platform.frame import build_axis_frame
from FacilArquitecturaWB.modules.service_platform.calculator import calculate_layout
from FacilArquitecturaWB.modules.service_platform.model import PlatformOptions
from FacilArquitecturaWB.modules.service_platform.planner import plan_compact_platform
from FacilArquitecturaWB.modules.service_platform.validation import PlatformValidationError


class ServicePlatformLineTests(unittest.TestCase):
    def test_horizontal_vertical_diagonal_and_translated_frames(self):
        horizontal = build_axis_frame((10, 20, 0), (3010, 20, 0))
        vertical = build_axis_frame((50, 75, 0), (50, 3075, 0))
        diagonal = build_axis_frame((100, 200, 0), (3100, 3200, 0))
        self.assertEqual((10.0, 20.0, 0.0), horizontal.local_to_global(0, 0))
        self.assertAlmostEqual(3000.0, horizontal.length_mm)
        self.assertAlmostEqual(90.0, vertical.angle_deg)
        self.assertEqual((-1.0, 0.0), tuple(round(value, 6) for value in vertical.left_unit))
        self.assertAlmostEqual(3000.0 * math.sqrt(2.0), diagonal.length_mm)
        self.assertEqual((100.0, 200.0, 0.0), diagonal.local_to_global(0, 0))

    def test_endpoint_inversion_is_independent_from_staff_side(self):
        normal = build_axis_frame((0, 0, 0), (3000, 0, 0))
        inverted = build_axis_frame((0, 0, 0), (3000, 0, 0), invert=True)
        self.assertEqual((0.0, 1.0), normal.left_unit)
        self.assertEqual((0.0, -1.0), inverted.left_unit)
        self.assertEqual((3000.0, 0.0, 0.0), inverted.p0)

    def test_three_positions_use_exact_line_length_without_deductions(self):
        plan = plan_compact_platform(
            PlatformOptions(total_width_mm=3000.0, service_positions=3, staff_side="left")
        )
        self.assertAlmostEqual(1000.0, plan.position_width_mm)
        desks = [item for item in plan.body if item.role == "employee_desk"]
        self.assertEqual([0.0, 1000.0, 2000.0], [item.x for item in desks])
        self.assertEqual(3, plan.glass_opening_count)
        self.assertEqual(9, len(plan.glass))

    def test_staff_side_switch_mirrors_depth_without_changing_stationing(self):
        left = plan_compact_platform(
            PlatformOptions(total_width_mm=3000.0, service_positions=3, staff_side="left")
        )
        right = plan_compact_platform(
            PlatformOptions(total_width_mm=3000.0, service_positions=3, staff_side="right")
        )
        left_desks = [item for item in left.body if item.role == "employee_desk"]
        right_desks = [item for item in right.body if item.role == "employee_desk"]
        self.assertEqual([item.x for item in left_desks], [item.x for item in right_desks])
        self.assertTrue(all(item.y == 0.0 for item in left_desks))
        self.assertTrue(all(item.y == -600.0 for item in right_desks))

    def test_one_and_many_positions_have_expected_repetition(self):
        one = plan_compact_platform(PlatformOptions(total_width_mm=1800.0, service_positions=1))
        many = plan_compact_platform(PlatformOptions(total_width_mm=8000.0, service_positions=8))
        self.assertEqual(3, len(one.glass))
        self.assertEqual(24, len(many.glass))
        self.assertEqual(7, len([item for item in many.body if item.role == "lateral_divider"]))

    def test_one_three_and_five_positions_create_one_real_opening_per_module(self):
        for positions in (1, 3, 5):
            plan = plan_compact_platform(
                PlatformOptions(total_width_mm=1000.0 * positions, service_positions=positions)
            )
            self.assertEqual(positions, plan.glass_opening_count)
            for index in range(1, positions + 1):
                pieces = [item for item in plan.glass if item.index == index]
                self.assertEqual(
                    {
                        "glass_left_of_opening",
                        "glass_right_of_opening",
                        "glass_above_opening",
                    },
                    {item.role for item in pieces},
                )

    def test_opening_dimensions_are_parametric_and_centered(self):
        options = PlatformOptions(
            total_width_mm=3000.0,
            service_positions=3,
            glass_opening_width_mm=420.0,
            glass_opening_height_mm=260.0,
            glass_opening_bottom_mm=800.0,
        )
        plan = plan_compact_platform(options)
        first = [item for item in plan.glass if item.index == 1]
        left = next(item for item in first if item.role == "glass_left_of_opening")
        right = next(item for item in first if item.role == "glass_right_of_opening")
        below = next(item for item in first if item.role == "glass_below_opening")
        above = next(item for item in first if item.role == "glass_above_opening")
        self.assertAlmostEqual(270.0, left.length)
        self.assertAlmostEqual(710.0, right.x)
        self.assertAlmostEqual(420.0, right.x - (left.x + left.length))
        self.assertAlmostEqual(60.0, below.height)
        self.assertAlmostEqual(260.0, left.height)
        self.assertAlmostEqual(1060.0, above.z)

    def test_opening_can_be_disabled(self):
        plan = plan_compact_platform(
            PlatformOptions(
                total_width_mm=3000.0,
                service_positions=3,
                glass_opening_enabled=False,
            )
        )
        self.assertEqual(0, plan.glass_opening_count)
        self.assertEqual(3, len(plan.glass))
        self.assertTrue(all(item.role == "glass_pane" for item in plan.glass))

    def test_impossible_openings_are_rejected(self):
        cases = (
            PlatformOptions(
                total_width_mm=3000.0,
                service_positions=3,
                glass_opening_width_mm=960.0,
            ),
            PlatformOptions(glass_opening_bottom_mm=700.0),
            PlatformOptions(glass_opening_bottom_mm=1600.0, glass_opening_height_mm=300.0),
        )
        for options in cases:
            with self.assertRaises(PlatformValidationError):
                plan_compact_platform(options)

    def test_opening_rules_do_not_change_the_historical_six_sketch_calculator(self):
        layout = calculate_layout(
            PlatformOptions(
                total_width_mm=3840.0,
                service_positions=2,
                desk_height_mm=900.0,
                glass_opening_bottom_mm=740.0,
            )
        )
        self.assertAlmostEqual(1800.0, layout.position_width_mm)


if __name__ == "__main__":
    unittest.main()
