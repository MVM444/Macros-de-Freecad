"""Tests for native ArchGrid inference from building alignments."""

from __future__ import annotations

import sys
import types
import unittest


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

from FacilArquitecturaWB.core import building_grid_utils as grids  # noqa: E402


WALLS = [
    (0, 0, 0, 0, 9000, 0),
    (4000, 0, 0, 4000, 9000, 0),
    (9000, 0, 0, 9000, 9000, 0),
    (0, 0, 0, 9000, 0, 0),
    (0, 3000, 0, 9000, 3000, 0),
    (0, 9000, 0, 9000, 9000, 0),
]


class BuildingGridUtilsTests(unittest.TestCase):
    def test_supported_walls_create_arch_grid_rows_and_columns(self):
        model = grids.infer_building_grid(WALLS, wall_min_support=3000)

        self.assertEqual([4000.0, 5000.0], model["column_sizes"])
        self.assertEqual([6000.0, 3000.0], model["row_sizes"])
        self.assertEqual((0.0, 9000.0, 0.0), model["origin"])

    def test_opening_centres_do_not_add_grid_divisions(self):
        doors = [
            (2000, 0, 0, 3000, 0, 0),
            (2500, 3000, 0, 2500, 4000, 0),
        ]

        model = grids.infer_building_grid(
            WALLS,
            doors,
            wall_min_support=3000,
            max_lines_per_direction=6,
        )

        self.assertNotIn(2500.0, model["x_positions"])
        self.assertNotIn(3500.0, model["y_positions"])
        self.assertEqual(0, len(model["opening_x_lines"]) + len(model["opening_y_lines"]))

    def test_short_partition_is_not_promoted_to_grid_line(self):
        walls = list(WALLS) + [(6500, 0, 0, 6500, 900, 0)]

        model = grids.infer_building_grid(walls, wall_min_support=3000)

        self.assertNotIn(6500.0, model["x_positions"])

    def test_closed_wall_sketch_is_preferred_over_original_centres(self):
        original = types.SimpleNamespace(
            Name="Original",
            TypeId="Sketcher::SketchObject",
            Geometry=[object()],
            FA_CenterlineKind="walls",
            FA_ThicknessDetected=True,
            FA_WallThickness=120.0,
            FA_GeneratedBy="",
        )
        closed = types.SimpleNamespace(
            Name="Closed",
            TypeId="Sketcher::SketchObject",
            Geometry=[object()],
            FA_CenterlineKind="walls",
            FA_ThicknessDetected=True,
            FA_WallThickness=120.0,
            FA_GeneratedBy="FA_CloseWallSketch",
        )
        doc = types.SimpleNamespace(Objects=[original, closed])

        sources = grids.collect_building_grid_sources(doc)

        self.assertEqual([closed], sources["walls"])

    def test_grid_outer_limits_follow_full_wall_segment_extents(self):
        walls = [
            (4000, 0, 0, 4000, 9000, 0),
            (9000, 0, 0, 9000, 9000, 0),
            (0, 0, 0, 9000, 0, 0),
            (0, 9000, 0, 9000, 9000, 0),
        ]

        model = grids.infer_building_grid(walls, wall_min_support=3000)

        self.assertEqual(0.0, model["x_positions"][0])
        self.assertEqual(9000.0, model["x_positions"][-1])
        self.assertEqual(0.0, model["y_positions"][0])
        self.assertEqual(9000.0, model["y_positions"][-1])
        self.assertGreaterEqual(model["extent_boundary_count"], 1)

    def test_opening_axis_is_snapped_and_connected_to_wall_centre(self):
        closures = grids.infer_opening_closure_segments(
            [(0, 0, 4000, 0)],
            [(4050, 50, 5000, 50)],
        )

        self.assertEqual(1, len(closures))
        self.assertEqual((4000.0, 0.0, 0.0, 5000.0, 0.0, 0.0), closures[0])

    def test_isolated_or_perpendicular_opening_axis_is_not_added(self):
        closures = grids.infer_opening_closure_segments(
            [(0, 0, 4000, 0)],
            [
                (8000, 50, 9000, 50),
                (4000, 50, 4000, 1000),
            ],
        )

        self.assertEqual([], closures)

    def test_connected_network_splits_crossings_into_shared_endpoints(self):
        network = grids.build_connected_orthogonal_network(
            [
                (0, 0, 1000, 0),
                (1000, 0, 2000, 0),
                (1000, -500, 1000, 500),
            ]
        )

        self.assertEqual(4, len(network))
        shared = (1000.0, 0.0)
        endpoint_count = sum(
            shared in ((segment[0], segment[1]), (segment[3], segment[4]))
            for segment in network
        )
        self.assertEqual(4, endpoint_count)

    def test_connected_network_closes_small_corner_gap(self):
        network = grids.build_connected_orthogonal_network(
            [
                (0, 0, 950, 0),
                (1000, 0, 1000, 1000),
            ],
            corner_tolerance=100.0,
        )

        self.assertIn((0.0, 0.0, 0.0, 1000.0, 0.0, 0.0), network)
        joined = sum(
            (1000.0, 0.0) in ((segment[0], segment[1]), (segment[3], segment[4]))
            for segment in network
        )
        self.assertEqual(2, joined)


if __name__ == "__main__":
    unittest.main()
