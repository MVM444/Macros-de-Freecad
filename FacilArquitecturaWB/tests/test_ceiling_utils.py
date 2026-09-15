"""Tests for the 600x600 suspended-ceiling planner."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


if "FreeCAD" not in sys.modules:
    freecad = types.ModuleType("FreeCAD")
    freecad.Console = types.SimpleNamespace(
        PrintMessage=lambda _message: None,
        PrintWarning=lambda _message: None,
        PrintError=lambda _message: None,
    )
    freecad.Vector = lambda x=0.0, y=0.0, z=0.0: types.SimpleNamespace(x=x, y=y, z=z)
    freecad.Placement = lambda *args, **kwargs: types.SimpleNamespace(
        Base=freecad.Vector(), Rotation=types.SimpleNamespace()
    )
    freecad.Rotation = lambda *args, **kwargs: types.SimpleNamespace()
    sys.modules["FreeCAD"] = freecad
if "Part" not in sys.modules:
    part = types.ModuleType("Part")
    part.Shape = lambda: None
    part.LineSegment = lambda start, end: (start, end)
    sys.modules["Part"] = part

from FacilArquitecturaWB.core import ceiling_utils as ceilings  # noqa: E402


class CeilingUtilsTests(unittest.TestCase):
    def test_multilevel_ceiling_namespace_options_are_additive(self):
        source = Path(ceilings.__file__).read_text(encoding="utf-8")
        self.assertIn('options.get("group_name") or CEILING_GROUP_NAME', source)
        self.assertIn('options.get("sheet_name") or CEILING_SHEET_NAME', source)
        self.assertIn('def _write_ceiling_schedule(doc, plans, parent_group, options, sheet_name=CEILING_SHEET_NAME):', source)


    def test_balanced_grid_has_equal_perimeter_cuts(self):
        phase = ceilings.balanced_phase(3250.0, 600.0)
        segments = ceilings.axis_segments(3250.0, 600.0, phase)

        self.assertEqual(125.0, phase)
        self.assertAlmostEqual(segments[0][1] - segments[0][0], 125.0)
        self.assertAlmostEqual(segments[-1][1] - segments[-1][0], 125.0)

    def test_luminaire_reserves_one_full_module(self):
        plan = ceilings.plan_modular_ceiling(
            3000.0,
            2400.0,
            luminaires=[{"x": 900.0, "y": 900.0, "name": "L1"}],
            module=600.0,
            alignment_tolerance=5.0,
        )

        self.assertEqual(1, plan["reserved_count"])
        self.assertEqual(0, plan["incompatible_luminaires"])
        self.assertTrue(plan["assignments"][0]["aligned"])
        self.assertEqual(19, plan["full_panels"])

    def test_incompatible_positions_are_reported_without_moving_them(self):
        lights = [
            {"x": 600.0, "y": 900.0, "name": "L1"},
            {"x": 1000.0, "y": 900.0, "name": "L2"},
        ]
        plan = ceilings.plan_modular_ceiling(
            3000.0,
            2400.0,
            luminaires=lights,
            module=600.0,
            alignment_tolerance=10.0,
        )

        self.assertGreaterEqual(plan["incompatible_luminaires"], 1)
        self.assertEqual([600.0, 1000.0], [item["light"]["x"] for item in plan["assignments"]])

    def test_app_link_reads_tipo_from_master(self):
        master = types.SimpleNamespace(Tipo="Luminaria", Label="Panel LED 60x60")
        link = types.SimpleNamespace(
            TypeId="App::Link", Name="Luminaria001", Label="Luminaria 001", LinkedObject=master
        )
        doc = types.SimpleNamespace(Objects=[link])

        self.assertEqual([link], ceilings.collect_electriccr_luminaires(doc))

    def test_hidden_link_master_is_not_counted_as_an_instance(self):
        master = types.SimpleNamespace(
            TypeId="Part::FeaturePython",
            Name="MasterLink_panel",
            Label="Master Link panel LED",
            Tipo="Luminaria",
            LnkMasterKey="panel_led_60x60",
        )
        doc = types.SimpleNamespace(Objects=[master])

        self.assertEqual([], ceilings.collect_electriccr_luminaires(doc))

    def test_automatic_room_collection_prefers_wall_derived_polygons(self):
        polygon = types.SimpleNamespace(
            Name="FA_PolygonalRoom",
            Label="Poligono - Archivo",
            FA_Role="room_polygon",
            FA_GeneratedBy="FA_PolygonalRoomsFromArchWalls",
            ElectricCRTipo="Area",
            Shape=types.SimpleNamespace(Faces=[object()]),
        )
        rectangle = types.SimpleNamespace(
            Name="Rectangle",
            Label="ARCHIVO",
            FA_Role="room_area",
            FA_GeneratedBy="FA_RectangularAreaAnalysis",
            Length=3000.0,
            Height=2400.0,
        )
        doc = types.SimpleNamespace(Objects=[rectangle, polygon])

        self.assertEqual([polygon], ceilings.collect_rooms(doc))

    def test_explicit_room_collection_accepts_polygon_and_rectangle(self):
        polygon = types.SimpleNamespace(
            Name="FA_PolygonalRoom",
            Label="Poligono - Archivo",
            FA_Role="room_polygon",
            FA_GeneratedBy="FA_PolygonalRoomsFromArchWalls",
            ElectricCRTipo="Area",
            Shape=types.SimpleNamespace(Faces=[object()]),
        )
        rectangle = types.SimpleNamespace(
            Name="Rectangle",
            Label="ARCHIVO",
            FA_Role="room_area",
            FA_GeneratedBy="FA_RectangularAreaAnalysis",
            Length=3000.0,
            Height=2400.0,
        )
        doc = types.SimpleNamespace(Objects=[rectangle, polygon])

        self.assertEqual([polygon, rectangle], ceilings.collect_rooms(doc, [polygon, rectangle]))

    def test_exclusion_cut_stops_after_panel_becomes_null(self):
        class DummyShape:
            def __init__(self, null=False, calls=None):
                self.null = bool(null)
                self.calls = calls if calls is not None else []

            def isNull(self):
                return self.null

            def cut(self, _other):
                self.calls.append("cut")
                return DummyShape(True, self.calls)

        calls = []
        result = ceilings._cut_face_by_exclusions(
            DummyShape(False, calls),
            [DummyShape(False), DummyShape(False)],
        )
        self.assertTrue(result.isNull())
        self.assertEqual(["cut"], calls)

    def test_stair_exclusion_zones_are_supported_by_generator(self):
        source = Path(ceilings.__file__).read_text(encoding="utf-8")
        self.assertIn('options.get("exclusion_zones_world_mm", [])', source)
        self.assertIn('def _world_exclusion_faces(', source)
        self.assertIn('def _cut_face_by_exclusions(', source)
        self.assertIn('FA_ExclusionZoneCount', source)
        self.assertIn('FA_ExclusionOwnerName', source)


if __name__ == "__main__":
    unittest.main()
