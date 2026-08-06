"""Synthetic tests for centerline topology, thickness grouping and constraints."""

from __future__ import annotations

import math
import sys
import types
import unittest


def _install_freecad_stubs():
    if "FreeCAD" not in sys.modules:
        freecad = types.ModuleType("FreeCAD")
        freecad.Vector = lambda x, y, z=0.0: (float(x), float(y), float(z))
        freecad.Placement = lambda: object()
        freecad.Console = types.SimpleNamespace(
            PrintMessage=lambda _message: None,
            PrintWarning=lambda _message: None,
            PrintError=lambda _message: None,
        )
        sys.modules["FreeCAD"] = freecad
    if "Part" not in sys.modules:
        part = types.ModuleType("Part")
        part.LineSegment = lambda start, end: (start, end)
        sys.modules["Part"] = part
    if "Sketcher" not in sys.modules:
        sketcher = types.ModuleType("Sketcher")

        class Constraint:
            def __init__(self, *args):
                self.args = args

        sketcher.Constraint = Constraint
        sys.modules["Sketcher"] = sketcher


_install_freecad_stubs()

from FacilArquitecturaWB.core import centerline_utils as centerlines  # noqa: E402


class FakeSketch:
    def __init__(self):
        self.geometry = []
        self.constraints = []

    def addGeometry(self, geometry, _construction=False):
        self.geometry.append(geometry)
        return len(self.geometry) - 1

    def addConstraint(self, constraint):
        self.constraints.append(constraint)
        return len(self.constraints) - 1


class FakeViewObject:
    pass


class FakeDocumentSketch(FakeSketch):
    def __init__(self, name):
        super().__init__()
        self.Name = name
        self.Label = name
        self.ViewObject = FakeViewObject()

    def addProperty(self, _prop_type, name, _group, _description):
        setattr(self, name, None)


class FakeDocument:
    def __init__(self):
        self.Objects = []

    def addObject(self, object_type, name):
        self.assert_object_type = object_type
        sketch = FakeDocumentSketch(name)
        self.Objects.append(sketch)
        return sketch


class FakeGroup:
    def __init__(self):
        self.Group = []

    def addObject(self, obj):
        self.Group.append(obj)


class Point:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)


class Vertex:
    def __init__(self, x, y):
        self.Point = Point(x, y)


class Edge:
    def __init__(self, x1, y1, x2, y2):
        self.Vertexes = [Vertex(x1, y1), Vertex(x2, y2)]


class BoundBox:
    def __init__(self, x_min, y_min, x_max, y_max):
        self.XMin = float(x_min)
        self.YMin = float(y_min)
        self.XMax = float(x_max)
        self.YMax = float(y_max)
        self.XLength = self.XMax - self.XMin
        self.YLength = self.YMax - self.YMin


class RectangleShape:
    def __init__(self, x_min, y_min, x_max, y_max):
        self.BoundBox = BoundBox(x_min, y_min, x_max, y_max)
        self.Edges = [
            Edge(x_min, y_min, x_max, y_min),
            Edge(x_max, y_min, x_max, y_max),
            Edge(x_max, y_max, x_min, y_max),
            Edge(x_min, y_max, x_min, y_min),
        ]
        self.Wires = []


class ShapeObject:
    def __init__(self, name, shape):
        self.Name = name
        self.Label = name
        self.Shape = shape


def _record(segment, thickness, source_ids=()):
    return centerlines._centerline_record(segment, thickness, source_ids=source_ids)


def _topology_context(profiles_by_source=None, compact_profiles=None):
    return {
        "profiles_by_source": profiles_by_source or {},
        "compact_profiles": compact_profiles or [],
    }


class CenterlineNetworkTests(unittest.TestCase):
    def test_specialized_opening_strategies_are_not_tagged_as_walls(self):
        self.assertEqual(
            "doors",
            centerlines._centerline_kind_for_strategy("walls", "door_swing"),
        )
        self.assertEqual(
            "windows",
            centerlines._centerline_kind_for_strategy("walls", "profile_axis"),
        )
        self.assertEqual(
            "columns",
            centerlines._centerline_kind_for_strategy("columns", "profile_axis"),
        )

    def test_geometry_scale_diagnostic_detects_microscopic_dxf_units(self):
        context = _topology_context(
            profiles_by_source={
                "legacy_block": [
                    [
                        (0.0, 0.0),
                        (0.004352228, 0.0),
                        (0.004352228, 0.00015),
                        (0.0, 0.00015),
                    ],
                    [
                        (0.000025, 0.000025),
                        (0.004327228, 0.000025),
                        (0.004327228, 0.000125),
                        (0.000025, 0.000125),
                    ],
                ]
            }
        )

        diagnostic = centerlines._geometry_scale_diagnostic(context)

        self.assertEqual("invalid", diagnostic["status"])
        self.assertEqual(1000000.0, diagnostic["suggested_factor"])
        self.assertAlmostEqual(125.0, diagnostic["estimated_thickness_mm"])

    def test_geometry_scale_diagnostic_preserves_normal_millimeter_geometry(self):
        context = _topology_context(
            profiles_by_source={
                "wall": [
                    [
                        (0.0, 0.0),
                        (4352.228, 0.0),
                        (4352.228, 150.0),
                        (0.0, 150.0),
                    ]
                ]
            }
        )

        diagnostic = centerlines._geometry_scale_diagnostic(context)

        self.assertEqual("ok", diagnostic["status"])
        self.assertEqual(1.0, diagnostic["suggested_factor"])

    def test_geometry_scale_validation_is_limited_to_wall_extraction(self):
        self.assertTrue(centerlines._should_validate_geometry_scale("auto", False))
        self.assertFalse(centerlines._should_validate_geometry_scale("auto", True))
        self.assertFalse(centerlines._should_validate_geometry_scale("profile_axis", False))
        self.assertFalse(centerlines._should_validate_geometry_scale("door_swing", False))

    def test_structural_column_profile_creates_one_cross_per_source(self):
        column_profile = [
            (0.0, 0.0),
            (254.0, 0.0),
            (254.0, 40.0),
            (147.0, 40.0),
            (147.0, 214.0),
            (254.0, 214.0),
            (254.0, 254.0),
            (0.0, 254.0),
            (0.0, 214.0),
            (107.0, 214.0),
            (107.0, 40.0),
            (0.0, 40.0),
        ]
        bolt_profile = [
            (300.0, 300.0),
            (340.0, 300.0),
            (350.0, 320.0),
            (340.0, 340.0),
            (300.0, 340.0),
            (290.0, 320.0),
        ]
        context = _topology_context(
            profiles_by_source={
                "column_1": [column_profile, bolt_profile],
                "column_2": [
                    [(x + 1000.0, y) for x, y in column_profile],
                    [(x + 1000.0, y) for x, y in bolt_profile],
                ],
            }
        )

        crosses = centerlines._column_centerline_records_from_source_profiles(context)

        self.assertEqual(4, len(crosses))
        self.assertEqual({"column_1", "column_2"}, {next(iter(record["source_ids"])) for record in crosses})

    def test_legacy_block_edge_stations_create_rectangular_centerline_loop(self):
        def rectangle_edges(x1, y1, x2, y2):
            return [
                Edge(x1, y1, x2, y1),
                Edge(x2, y1, x2, y2),
                Edge(x2, y2, x1, y2),
                Edge(x1, y2, x1, y1),
            ]

        shape = types.SimpleNamespace(
            Edges=rectangle_edges(0.0, 0.0, 5000.0, 4000.0)
            + rectangle_edges(100.0, 100.0, 4900.0, 3900.0),
        )

        records = centerlines._centerline_records_from_block_perimeter(
            shape,
            source_ids=("legacy_room",),
        )
        keys = {centerlines._segment_key(*record["segment"]) for record in records}

        self.assertEqual(4, len(records))
        self.assertEqual(
            {
                centerlines._segment_key(50.0, 50.0, 4950.0, 50.0),
                centerlines._segment_key(4950.0, 50.0, 4950.0, 3950.0),
                centerlines._segment_key(4950.0, 3950.0, 50.0, 3950.0),
                centerlines._segment_key(50.0, 3950.0, 50.0, 50.0),
            },
            keys,
        )
        self.assertTrue(all(abs(record["thickness"] - 100.0) < 1e-6 for record in records))

    def test_small_concentric_block_remains_available_for_column_detection(self):
        shape = types.SimpleNamespace(
            Edges=[
                Edge(0.0, 0.0, 400.0, 0.0),
                Edge(400.0, 0.0, 400.0, 400.0),
                Edge(400.0, 400.0, 0.0, 400.0),
                Edge(0.0, 400.0, 0.0, 0.0),
                Edge(50.0, 50.0, 350.0, 50.0),
                Edge(350.0, 50.0, 350.0, 350.0),
                Edge(350.0, 350.0, 50.0, 350.0),
                Edge(50.0, 350.0, 50.0, 50.0),
            ],
        )

        records = centerlines._centerline_records_from_block_perimeter(shape)

        self.assertEqual([], records)

    def test_legacy_block_point_cloud_recovers_rotated_wall_axis(self):
        angle = 0.37
        u = (math.cos(angle), math.sin(angle))
        n = (-u[1], u[0])
        center = (2500.0, 1800.0)
        half_length = 1500.0
        half_thickness = 60.0
        corners = [
            (
                center[0] + u[0] * along + n[0] * across,
                center[1] + u[1] * along + n[1] * across,
            )
            for along, across in (
                (-half_length, -half_thickness),
                (half_length, -half_thickness),
                (half_length, half_thickness),
                (-half_length, half_thickness),
            )
        ]
        shape = types.SimpleNamespace(
            Vertexes=[Vertex(x, y) for x, y in (corners[2], corners[0], corners[3], corners[1])],
            Edges=[],
        )

        record = centerlines._centerline_record_from_block_shape(shape, source_ids=("legacy",))

        self.assertIsNotNone(record)
        self.assertAlmostEqual(3000.0, centerlines._segment_length(record["segment"]), places=5)
        self.assertAlmostEqual(120.0, record["thickness"], places=5)
        midpoint = (
            (record["segment"][0] + record["segment"][2]) / 2.0,
            (record["segment"][1] + record["segment"][3]) / 2.0,
        )
        self.assertAlmostEqual(center[0], midpoint[0], places=5)
        self.assertAlmostEqual(center[1], midpoint[1], places=5)

    def test_wire_edges_restore_polygon_when_vertex_list_is_scrambled(self):
        wire = types.SimpleNamespace(
            isClosed=lambda: True,
            Edges=[
                Edge(0.0, 0.0, 5000.0, 0.0),
                Edge(5000.0, 0.0, 5000.0, 4000.0),
                Edge(5000.0, 4000.0, 0.0, 4000.0),
                Edge(0.0, 4000.0, 0.0, 0.0),
            ],
            Vertexes=[
                Vertex(0.0, 0.0),
                Vertex(5000.0, 4000.0),
                Vertex(5000.0, 0.0),
                Vertex(0.0, 4000.0),
            ],
        )

        polygon = centerlines._wire_polygon_points(wire)
        metrics = centerlines._oriented_polygon_metrics(polygon)

        self.assertAlmostEqual(20000000.0, centerlines._polygon_area(polygon))
        self.assertAlmostEqual(1.0, metrics["fill_ratio"])

    def test_concentric_rectangles_create_four_perimeter_centerlines(self):
        outer = (
            [(float(x), 0.0) for x in range(0, 1001, 100)]
            + [(1000.0, float(y)) for y in range(100, 801, 100)]
            + [(float(x), 800.0) for x in range(900, -1, -100)]
            + [(0.0, float(y)) for y in range(700, 0, -100)]
        )
        inner = (
            [(float(x), 100.0) for x in range(100, 901, 100)]
            + [(900.0, float(y)) for y in range(200, 701, 100)]
            + [(float(x), 700.0) for x in range(800, 99, -100)]
            + [(100.0, float(y)) for y in range(600, 100, -100)]
        )
        context = {
            "profiles_by_source": {"room_block": [outer, inner]},
            "compact_profiles": [],
            "compact_source_ids": set(),
        }

        records = centerlines._centerline_records_from_closed_profiles(context)
        keys = {centerlines._segment_key(*record["segment"]) for record in records}

        self.assertEqual(4, len(records))
        self.assertEqual(
            {
                centerlines._segment_key(50.0, 50.0, 950.0, 50.0),
                centerlines._segment_key(950.0, 50.0, 950.0, 750.0),
                centerlines._segment_key(50.0, 750.0, 950.0, 750.0),
                centerlines._segment_key(50.0, 50.0, 50.0, 750.0),
            },
            keys,
        )
        self.assertTrue(all(abs(record["thickness"] - 100.0) < 1e-6 for record in records))

    def test_block_reference_pairs_displaced_rectangles_without_strict_containment(self):
        first = [(0.0, 0.0), (5000.0, 0.0), (5000.0, 4000.0), (0.0, 4000.0)]
        second = [(100.0, -100.0), (5100.0, -100.0), (5100.0, 3900.0), (100.0, 3900.0)]
        context = {
            "profiles_by_source": {"imperfect_block": [first, second]},
            "compact_profiles": [],
            "compact_source_ids": set(),
        }

        records = centerlines._centerline_records_from_closed_profiles(context)

        self.assertEqual(4, len(records))
        self.assertTrue(centerlines._records_span_multiple_directions(records))
        self.assertTrue(all(record["thickness"] is not None for record in records))

    def test_block_reference_recovers_jagged_rectangles_from_oriented_bounds(self):
        def jagged_rectangle(x1, y1, x2, y2, step=100.0, offset=3.0):
            points = []
            count_x = int(round((x2 - x1) / step))
            count_y = int(round((y2 - y1) / step))
            points.extend(
                (x1 + index * step, y1 + (offset if index % 2 else -offset))
                for index in range(count_x + 1)
            )
            points.extend(
                (x2 + (offset if index % 2 else -offset), y1 + index * step)
                for index in range(1, count_y + 1)
            )
            points.extend(
                (x2 - index * step, y2 + (offset if index % 2 else -offset))
                for index in range(1, count_x + 1)
            )
            points.extend(
                (x1 + (offset if index % 2 else -offset), y2 - index * step)
                for index in range(1, count_y)
            )
            return points

        first = jagged_rectangle(0.0, 0.0, 5000.0, 4000.0)
        second = jagged_rectangle(100.0, 100.0, 4900.0, 3900.0)
        context = {
            "profiles_by_source": {"jagged_block": [first, second]},
            "compact_profiles": [],
            "compact_source_ids": set(),
        }

        records = centerlines._centerline_records_from_closed_profiles(context)

        self.assertEqual(4, len(records))
        self.assertTrue(centerlines._records_span_multiple_directions(records))

    def test_parallel_thin_profile_layers_create_wall_axis_and_merge_modules(self):
        context = {
            "profiles_by_source": {
                "module_1": [
                    [(0.0, 0.0), (150.0, 0.0), (150.0, 10.0), (0.0, 10.0)],
                    [(0.0, 90.0), (150.0, 90.0), (150.0, 100.0), (0.0, 100.0)],
                ],
                "module_2": [
                    [(150.0, 0.0), (300.0, 0.0), (300.0, 10.0), (150.0, 10.0)],
                    [(150.0, 90.0), (300.0, 90.0), (300.0, 100.0), (150.0, 100.0)],
                ],
            },
            "compact_profiles": [],
            "compact_source_ids": set(),
        }

        records = centerlines._centerline_records_from_closed_profiles(context)

        self.assertEqual(1, len(records))
        for actual, expected in zip(records[0]["segment"], (0.0, 50.0, 300.0, 50.0)):
            self.assertAlmostEqual(expected, actual)
        self.assertAlmostEqual(100.0, records[0]["thickness"])
        self.assertEqual(frozenset(("module_1", "module_2")), records[0]["source_ids"])

    def test_touching_short_profiles_are_consolidated_before_length_filter(self):
        context = {
            "profiles_by_source": {
                "module_1": [[(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0)]],
                "module_2": [[(100.0, 0.0), (200.0, 0.0), (200.0, 50.0), (100.0, 50.0)]],
                "module_3": [[(200.0, 0.0), (300.0, 0.0), (300.0, 50.0), (200.0, 50.0)]],
                "module_4": [[(300.0, 0.0), (400.0, 0.0), (400.0, 50.0), (300.0, 50.0)]],
            },
            "compact_profiles": [],
            "compact_source_ids": set(),
        }

        records = centerlines._centerline_records_from_closed_profiles(context)

        self.assertEqual(1, len(records))
        for actual, expected in zip(records[0]["segment"], (0.0, 25.0, 400.0, 25.0)):
            self.assertAlmostEqual(expected, actual)
        self.assertAlmostEqual(50.0, records[0]["thickness"])
        self.assertEqual(
            frozenset(("module_1", "module_2", "module_3", "module_4")),
            records[0]["source_ids"],
        )

    def test_visible_gap_between_short_profiles_is_not_closed(self):
        context = {
            "profiles_by_source": {
                "left": [[(0.0, 0.0), (150.0, 0.0), (150.0, 50.0), (0.0, 50.0)]],
                "right": [[(160.0, 0.0), (310.0, 0.0), (310.0, 50.0), (160.0, 50.0)]],
            },
            "compact_profiles": [],
            "compact_source_ids": set(),
        }

        records = centerlines._centerline_records_from_closed_profiles(context)

        self.assertEqual([], records)

    def test_visible_gap_inside_same_link_is_not_closed_by_aggregate_axis(self):
        context = {
            "profiles_by_source": {
                "same_link": [
                    [(0.0, 0.0), (150.0, 0.0), (150.0, 50.0), (0.0, 50.0)],
                    [(160.0, 0.0), (310.0, 0.0), (310.0, 50.0), (160.0, 50.0)],
                ],
            },
            "compact_profiles": [],
            "compact_source_ids": set(),
        }

        records = centerlines._centerline_records_from_closed_profiles(context)

        self.assertEqual([], records)

    def test_closed_link_profiles_with_only_short_edges_recover_centerlines(self):
        def coordinates(start, end, step):
            count = int(round((end - start) / step))
            return [start + index * step for index in range(count + 1)]

        def subdivided_rectangle(x_min, y_min, x_max, y_max, step=200.0):
            bottom = [(x, y_min) for x in coordinates(x_min, x_max, step)]
            right = [(x_max, y_max)]
            top = [(x, y_max) for x in reversed(coordinates(x_min, x_max - step, step))]
            return bottom + right + top

        first = subdivided_rectangle(0.0, 0.0, 1000.0, 100.0)
        second = subdivided_rectangle(0.0, 2000.0, 1000.0, 2100.0)
        context = {
            "profiles_by_source": {"U21": [first, second]},
            "compact_profiles": [],
            "compact_source_ids": set(),
        }

        records = centerlines._centerline_records_from_closed_profiles(context)
        segments = sorted(
            (
                round(min(record["segment"][0], record["segment"][2]), 3),
                round((record["segment"][1] + record["segment"][3]) / 2.0, 3),
                round(max(record["segment"][0], record["segment"][2]), 3),
            )
            for record in records
        )

        self.assertEqual([(0.0, 50.0, 1000.0), (0.0, 2050.0, 1000.0)], segments)
        self.assertTrue(all(abs(record["thickness"] - 100.0) < 1e-6 for record in records))

    def test_layer_keeps_each_link_instance_instead_of_forwarded_source_group(self):
        shape = types.SimpleNamespace(Edges=[object()], isNull=lambda: False)
        source_shape = types.SimpleNamespace(
            Name="ShapeBase",
            Label="ShapeBase",
            TypeId="Part::Feature",
            Shape=shape,
        )
        first_link = types.SimpleNamespace(
            Name="U21",
            Label="U21",
            TypeId="App::Link",
            Shape=shape,
            Group=[source_shape],
            OutList=[source_shape],
        )
        second_link = types.SimpleNamespace(
            Name="U008",
            Label="U008",
            TypeId="App::Link",
            Shape=shape,
            Group=[source_shape],
            OutList=[source_shape],
        )
        layer = types.SimpleNamespace(
            Name="Layer",
            Label="Pared Muro Seco",
            TypeId="App::DocumentObjectGroup",
            Group=[first_link, second_link],
            OutList=[first_link, second_link],
        )

        result = centerlines._collect_leaf_objects([layer])

        self.assertEqual([first_link, second_link], result)
        self.assertNotIn(source_shape, result)

    def test_generated_centerline_sketch_is_never_reused_as_wall_source(self):
        generated = types.SimpleNamespace(
            Name="Sketch_Centros_Test",
            Label="Sketch_Centros_Test",
            FA_Role="centerlines",
            Shape=object(),
        )

        self.assertTrue(centerlines._is_generated_centerline_object(generated))
        self.assertEqual([], centerlines._collect_leaf_objects([generated]))

    def test_small_corner_patch_is_not_classified_as_column(self):
        small_corner = [(0.0, 0.0), (150.0, 0.0), (150.0, 150.0), (0.0, 150.0)]
        structural_column = [(0.0, 0.0), (400.0, 0.0), (400.0, 350.0), (0.0, 350.0)]

        self.assertFalse(centerlines._polygon_is_compact_profile(small_corner))
        self.assertTrue(centerlines._polygon_is_compact_profile(structural_column))

    def test_l_shaped_patch_is_not_classified_as_column(self):
        l_patch = [
            (0.0, 0.0),
            (800.0, 0.0),
            (800.0, 250.0),
            (250.0, 250.0),
            (250.0, 800.0),
            (0.0, 800.0),
        ]

        self.assertFalse(centerlines._polygon_is_compact_profile(l_patch))

    def test_overshooting_closed_corner_is_trimmed_to_axis_intersection(self):
        records = [
            _record((0.0, 0.0, 1000.0, 0.0), 100.0),
            centerlines._centerline_record(
                (1000.0, -50.0, 1000.0, 1000.0),
                100.0,
                closed_endpoints=(1,),
            ),
        ]

        groups, joined = centerlines._prepare_centerline_groups(records, True)
        segments = [record["segment"] for group in groups for record in group["records"]]

        self.assertEqual(1, joined)
        self.assertIn((1000.0, 0.0, 1000.0, 1000.0), segments)

    def test_abutting_closed_wall_ends_stop_at_visible_faces(self):
        records = [
            centerlines._centerline_record(
                (0.0, 0.0, 950.0, 0.0),
                100.0,
                closed_endpoints=(2,),
            ),
            centerlines._centerline_record(
                (1000.0, 50.0, 1000.0, 1000.0),
                100.0,
                closed_endpoints=(1,),
            ),
        ]

        groups, joined = centerlines._prepare_centerline_groups(records, True)
        segments = [record["segment"] for group in groups for record in group["records"]]

        self.assertEqual(0, joined)
        self.assertIn((0.0, 0.0, 950.0, 0.0), segments)
        self.assertIn((1000.0, 50.0, 1000.0, 1000.0), segments)

    def test_t_branch_with_end_cap_stops_at_main_wall_face(self):
        records = [
            _record((0.0, 0.0, 2000.0, 0.0), 100.0),
            centerlines._centerline_record(
                (1000.0, 50.0, 1000.0, 1200.0),
                100.0,
                closed_endpoints=(1,),
            ),
        ]

        groups, joined = centerlines._prepare_centerline_groups(records, True)
        segments = [record["segment"] for group in groups for record in group["records"]]

        self.assertEqual(0, joined)
        self.assertIn((1000.0, 50.0, 1000.0, 1200.0), segments)

    def test_explicit_wall_end_prevents_false_corner_join(self):
        records = [
            _record((0.0, 0.0, 900.0, 0.0), 100.0, ("horizontal",)),
            _record((1050.0, 0.0, 1050.0, 1000.0), 100.0, ("vertical",)),
        ]
        context = _topology_context(
            {
                "horizontal": [[(0.0, -50.0), (900.0, -50.0), (900.0, 50.0), (0.0, 50.0)]],
                "vertical": [[(1000.0, 0.0), (1100.0, 0.0), (1100.0, 1000.0), (1000.0, 1000.0)]],
            }
        )

        groups, joined = centerlines._prepare_centerline_groups(records, True, topology_context=context)
        segments = [record["segment"] for group in groups for record in group["records"]]

        self.assertEqual(0, joined)
        self.assertIn((0.0, 0.0, 900.0, 0.0), segments)
        self.assertIn((1050.0, 0.0, 1050.0, 1000.0), segments)

    def test_filled_l_profile_still_allows_real_corner_join(self):
        records = [
            _record((100.0, 0.0, 1000.0, 0.0), 100.0, ("continuous_l",)),
            _record((0.0, 100.0, 0.0, 1000.0), 100.0, ("continuous_l",)),
        ]
        l_profile = [
            (-100.0, -100.0),
            (1000.0, -100.0),
            (1000.0, 100.0),
            (100.0, 100.0),
            (100.0, 1000.0),
            (-100.0, 1000.0),
        ]
        context = _topology_context({"continuous_l": [l_profile]})

        groups, joined = centerlines._prepare_centerline_groups(records, True, topology_context=context)
        segments = [record["segment"] for group in groups for record in group["records"]]

        self.assertEqual(2, joined)
        self.assertIn((0.0, 0.0, 1000.0, 0.0), segments)
        self.assertIn((0.0, 0.0, 0.0, 1000.0), segments)

    def test_compact_profile_blocks_join_through_column(self):
        records = [
            _record((-1000.0, 0.0, -100.0, 0.0), 100.0),
            _record((0.0, 100.0, 0.0, 1000.0), 100.0),
        ]
        column = [(-150.0, -150.0), (150.0, -150.0), (150.0, 150.0), (-150.0, 150.0)]
        context = _topology_context(compact_profiles=[column])

        groups, joined = centerlines._prepare_centerline_groups(records, True, topology_context=context)
        segments = [record["segment"] for group in groups for record in group["records"]]

        self.assertEqual(0, joined)
        self.assertIn((-1000.0, 0.0, -100.0, 0.0), segments)
        self.assertIn((0.0, 100.0, 0.0, 1000.0), segments)

    def test_separate_collinear_profiles_keep_visible_division(self):
        records = [
            _record((-1000.0, 0.0, -100.0, 0.0), 100.0, ("left",)),
            _record((100.0, 0.0, 1000.0, 0.0), 100.0, ("right",)),
        ]
        context = _topology_context(
            {
                "left": [[(-1000.0, -50.0), (-100.0, -50.0), (-100.0, 50.0), (-1000.0, 50.0)]],
                "right": [[(100.0, -50.0), (1000.0, -50.0), (1000.0, 50.0), (100.0, 50.0)]],
            }
        )

        groups, joined = centerlines._prepare_centerline_groups(records, True, topology_context=context)
        segments = [record["segment"] for group in groups for record in group["records"]]

        self.assertEqual(0, joined)
        self.assertEqual(2, len(segments))

    def test_source_edge_cleanup_preserves_small_gap_between_closed_profiles(self):
        records = [
            _record((-1000.0, -50.0, -20.0, -50.0), None, ("compound",)),
            _record((20.0, -50.0, 1000.0, -50.0), None, ("compound",)),
        ]
        context = _topology_context(
            {
                "compound": [
                    [(-1000.0, -50.0), (-20.0, -50.0), (-20.0, 50.0), (-1000.0, 50.0)],
                    [(20.0, -50.0), (1000.0, -50.0), (1000.0, 50.0), (20.0, 50.0)],
                ]
            }
        )

        merged = centerlines._merge_source_edge_records(records, topology_context=context)

        self.assertEqual(2, len(merged))

    def test_source_edge_cleanup_merges_fragments_on_same_profile_boundary(self):
        records = [
            _record((-1000.0, -50.0, -20.0, -50.0), None, ("continuous",)),
            _record((20.0, -50.0, 1000.0, -50.0), None, ("continuous",)),
        ]
        context = _topology_context(
            {
                "continuous": [
                    [(-1000.0, -50.0), (1000.0, -50.0), (1000.0, 50.0), (-1000.0, 50.0)]
                ]
            }
        )

        merged = centerlines._merge_source_edge_records(records, topology_context=context)

        self.assertEqual(1, len(merged))
        self.assertEqual((-1000.0, -50.0, 1000.0, -50.0), merged[0]["segment"])

    def test_independent_dxf_fragments_rebuild_full_wall_axis(self):
        raw_records = [
            _record((0.0, 0.0, 500.0, 0.0), None, ("bottom_a",)),
            _record((500.0, 0.0, 1000.0, 0.0), None, ("bottom_b",)),
            _record((0.0, 100.0, 1000.0, 100.0), None, ("top",)),
        ]
        topology_segments = [
            record["segment"] for record in raw_records
        ] + [(0.0, 0.0, 0.0, 100.0), (1000.0, 0.0, 1000.0, 100.0)]

        merged = centerlines._merge_source_edge_records(
            raw_records,
            topology_segments=topology_segments,
        )
        centers = centerlines._centerline_records_from_parallel_edges(
            merged,
            topology_segments=topology_segments,
        )

        self.assertEqual(2, len(merged))
        self.assertEqual(1, len(centers))
        self.assertEqual((0.0, 50.0, 1000.0, 50.0), centers[0]["segment"])
        self.assertEqual(frozenset((1, 2)), centers[0]["closed_endpoints"])

    def test_wall_axis_reaches_longer_face_when_real_end_cap_exists(self):
        raw_records = [
            _record((0.0, 0.0, 1000.0, 0.0), None, ("bottom",)),
            _record((0.0, 100.0, 700.0, 100.0), None, ("top",)),
        ]
        topology_segments = [record["segment"] for record in raw_records] + [
            (0.0, -500.0, 0.0, 500.0),
            (1000.0, -500.0, 1000.0, 500.0),
        ]

        centers = centerlines._centerline_records_from_parallel_edges(
            raw_records,
            topology_segments=topology_segments,
        )

        self.assertEqual(1, len(centers))
        self.assertEqual((0.0, 50.0, 1000.0, 50.0), centers[0]["segment"])
        self.assertEqual(frozenset((1, 2)), centers[0]["closed_endpoints"])

        vertical = _record((1100.0, 50.0, 1100.0, 1000.0), 100.0)
        groups, joined = centerlines._prepare_centerline_groups([centers[0], vertical], True)
        segments = [record["segment"] for group in groups for record in group["records"]]
        self.assertEqual(0, joined)
        self.assertIn((0.0, 50.0, 1000.0, 50.0), segments)

    def test_short_end_cap_prevents_merging_independent_dxf_edges(self):
        records = [
            _record((0.0, 0.0, 500.0, 0.0), None, ("left",)),
            _record((500.0, 0.0, 1000.0, 0.0), None, ("right",)),
        ]
        topology_segments = [record["segment"] for record in records] + [(500.0, -50.0, 500.0, 50.0)]

        merged = centerlines._merge_source_edge_records(
            records,
            topology_segments=topology_segments,
        )

        self.assertEqual(2, len(merged))

    def test_independent_dxf_rectangle_restores_column_cross(self):
        edge_records = [
            _record((0.0, 0.0, 400.0, 0.0), None, ("edge_1",)),
            _record((400.0, 0.0, 400.0, 350.0), None, ("edge_2",)),
            _record((400.0, 350.0, 0.0, 350.0), None, ("edge_3",)),
            _record((0.0, 350.0, 0.0, 0.0), None, ("edge_4",)),
        ]
        context = _topology_context()

        centerlines._augment_topology_context_from_edges(context, edge_records)
        crosses = centerlines._column_centerline_records(context)

        self.assertEqual(1, len(context["compact_profiles"]))
        self.assertEqual(2, len(crosses))
        keys = {centerlines._segment_key(*record["segment"]) for record in crosses}
        self.assertIn(centerlines._segment_key(0.0, 175.0, 400.0, 175.0), keys)
        self.assertIn(centerlines._segment_key(200.0, 0.0, 200.0, 350.0), keys)

    def test_t_junction_merges_collinear_axis_and_snaps_branch(self):
        records = [
            _record((-1000.0, 0.0, -50.0, 0.0), 100.0),
            _record((50.0, 0.0, 1000.0, 0.0), 100.0),
            _record((0.0, 50.0, 0.0, 1000.0), 100.0),
        ]
        groups, joined = centerlines._prepare_centerline_groups(records, True)
        segments = [record["segment"] for record in groups[0]["records"]]

        self.assertEqual(1, len(groups))
        self.assertEqual(2, len(segments))
        self.assertEqual(1, joined)
        self.assertIn((-1000.0, 0.0, 1000.0, 0.0), segments)
        self.assertIn((0.0, 0.0, 0.0, 1000.0), segments)

        sketch = FakeSketch()
        centerlines._populate_parametric_sketch(sketch, segments)
        kinds = [constraint.args[0] for constraint in sketch.constraints]
        self.assertIn("Horizontal", kinds)
        self.assertIn("Vertical", kinds)
        self.assertIn("PointOnObject", kinds)

    def test_l_corner_snaps_both_endpoints_and_adds_coincident(self):
        records = [
            _record((0.0, 0.0, 950.0, 0.0), 100.0),
            _record((1000.0, 50.0, 1000.0, 1000.0), 100.0),
        ]
        groups, joined = centerlines._prepare_centerline_groups(records, True)
        segments = [record["segment"] for record in groups[0]["records"]]

        self.assertEqual(2, joined)
        self.assertIn((0.0, 0.0, 1000.0, 0.0), segments)
        self.assertIn((1000.0, 0.0, 1000.0, 1000.0), segments)

        sketch = FakeSketch()
        centerlines._populate_parametric_sketch(sketch, segments)
        kinds = [constraint.args[0] for constraint in sketch.constraints]
        self.assertIn("Coincident", kinds)

    def test_different_thicknesses_create_separate_joined_groups(self):
        records = [
            _record((0.0, 0.0, 950.0, 0.0), 100.0),
            _record((1000.0, 100.0, 1000.0, 1200.0), 200.0),
        ]
        groups, joined = centerlines._prepare_centerline_groups(records, True)

        self.assertEqual(2, len(groups))
        self.assertEqual([100.0, 200.0], [round(group["thickness"], 1) for group in groups])
        self.assertEqual(2, joined)
        flattened = [record["segment"] for group in groups for record in group["records"]]
        self.assertIn((0.0, 0.0, 1000.0, 0.0), flattened)
        self.assertIn((1000.0, 0.0, 1000.0, 1200.0), flattened)

    def test_profile_depth_is_retained_as_thickness(self):
        rectangle = [
            (0.0, 0.0, 1200.0, 0.0),
            (1200.0, 0.0, 1200.0, 200.0),
            (1200.0, 200.0, 0.0, 200.0),
            (0.0, 200.0, 0.0, 0.0),
        ]
        centerline = centerlines._centerline_from_segments(rectangle)
        thickness = centerlines._profile_thickness_from_segments(rectangle, centerline)

        self.assertAlmostEqual(200.0, thickness)

    def test_complete_extraction_creates_one_parametric_sketch_per_thickness(self):
        doc = FakeDocument()
        parent = FakeGroup()
        objects = [
            ShapeObject("Muro100", RectangleShape(0.0, 0.0, 2000.0, 100.0)),
            ShapeObject("Muro200", RectangleShape(1900.0, 50.0, 2100.0, 2000.0)),
        ]

        primary, segments = centerlines.create_centerline_sketch_from_objects(doc, parent, objects)

        self.assertEqual(2, len(doc.Objects))
        self.assertEqual(2, len(segments))
        self.assertEqual(1, len(primary.FA_RelatedCenterlineSketches))
        thicknesses = sorted(round(sketch.FA_WallThickness, 1) for sketch in doc.Objects)
        self.assertEqual([100.0, 200.0], thicknesses)
        self.assertTrue(all(sketch.FA_ParametricConstraintCount >= 1 for sketch in doc.Objects))
        self.assertTrue(any("Espesor_100mm" in sketch.Label for sketch in doc.Objects))
        self.assertTrue(any("Espesor_200mm" in sketch.Label for sketch in doc.Objects))


if __name__ == "__main__":
    unittest.main()
