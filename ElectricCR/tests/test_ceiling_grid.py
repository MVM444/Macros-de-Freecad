"""Tests for ElectricCR luminaire placement on suspended-ceiling modules."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "electriccr" / "features" / "ceiling_grid.py"
SPEC = importlib.util.spec_from_file_location("electriccr_ceiling_grid_test", MODULE_PATH)
ceiling_grid = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ceiling_grid)
full_module_cells = ceiling_grid.full_module_cells
modular_grid_positions = ceiling_grid.modular_grid_positions


class CeilingGridTests(unittest.TestCase):
    def test_full_cells_exclude_balanced_perimeter_cuts(self):
        cells = full_module_cells(3250.0, 600.0)

        self.assertEqual(5, len(cells))
        self.assertEqual(425.0, cells[0][1])
        self.assertEqual(2825.0, cells[-1][1])

    def test_two_by_two_layout_uses_real_module_centres(self):
        positions = modular_grid_positions(3000.0, 2400.0, 2, 2, 600.0)

        self.assertEqual(4, len(positions))
        self.assertEqual([900.0, 2100.0], sorted({item["x"] for item in positions}))
        self.assertEqual([900.0, 1500.0], sorted({item["y"] for item in positions}))
        for item in positions:
            self.assertAlmostEqual(300.0, item["x"] % 600.0)
            self.assertAlmostEqual(300.0, item["y"] % 600.0)

    def test_layout_rejects_more_fixtures_than_complete_cells(self):
        with self.assertRaises(ValueError):
            modular_grid_positions(1000.0, 1000.0, 2, 1, 600.0)


if __name__ == "__main__":
    unittest.main()
