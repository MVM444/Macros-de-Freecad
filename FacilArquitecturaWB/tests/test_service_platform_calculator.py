"""Pure regression tests for the service platform layout calculator."""

from __future__ import annotations

import unittest

from FacilArquitecturaWB.modules.service_platform.calculator import calculate_layout, position_origins
from FacilArquitecturaWB.modules.service_platform.model import PlatformOptions
from FacilArquitecturaWB.modules.service_platform.validation import PlatformValidationError


class ServicePlatformCalculatorTests(unittest.TestCase):
    def test_two_positions_match_pl01_starting_dimensions(self):
        options = PlatformOptions(
            total_width_mm=3840.0,
            service_positions=2,
            side_margin_mm=100.0,
            divider_thickness_mm=40.0,
        )
        layout = calculate_layout(options)
        self.assertEqual(1, layout.divider_count)
        self.assertAlmostEqual(3600.0, layout.usable_width_mm)
        self.assertAlmostEqual(1800.0, layout.position_width_mm)
        self.assertEqual([100.0, 1940.0], position_origins(options, layout))

    def test_four_positions_and_three_dividers(self):
        options = PlatformOptions(
            total_width_mm=7200.0,
            service_positions=4,
            side_margin_mm=100.0,
            divider_thickness_mm=40.0,
        )
        layout = calculate_layout(options)
        self.assertEqual(3, layout.divider_count)
        self.assertAlmostEqual(6880.0, layout.usable_width_mm)
        self.assertAlmostEqual(1720.0, layout.position_width_mm)
        self.assertEqual(4, len(position_origins(options, layout)))

    def test_insufficient_width_reports_required_total(self):
        options = PlatformOptions(
            total_width_mm=2400.0,
            service_positions=2,
            minimum_position_width_mm=1200.0,
            side_margin_mm=100.0,
            divider_thickness_mm=40.0,
        )
        with self.assertRaisesRegex(PlatformValidationError, r"2640\.0 mm"):
            calculate_layout(options)

    def test_single_position_has_no_divider(self):
        options = PlatformOptions(total_width_mm=1400.0, service_positions=1)
        layout = calculate_layout(options)
        self.assertEqual(0, layout.divider_count)
        self.assertAlmostEqual(1200.0, layout.position_width_mm)
        self.assertEqual([100.0], position_origins(options, layout))

    def test_invalid_position_count_is_rejected(self):
        with self.assertRaises(PlatformValidationError):
            calculate_layout(PlatformOptions(service_positions=0))


if __name__ == "__main__":
    unittest.main()
