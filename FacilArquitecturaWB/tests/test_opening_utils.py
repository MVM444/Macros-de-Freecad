"""Pure tests for BIM opening host selection and idempotence."""

from __future__ import annotations

import sys
import types
import unittest


def _install_freecad_stubs():
    if "FreeCAD" not in sys.modules:
        freecad = types.ModuleType("FreeCAD")
        freecad.Placement = lambda: object()
        freecad.Console = types.SimpleNamespace(
            PrintMessage=lambda _message: None,
            PrintWarning=lambda _message: None,
            PrintError=lambda _message: None,
        )
        sys.modules["FreeCAD"] = freecad
    if "Arch" not in sys.modules:
        sys.modules["Arch"] = types.ModuleType("Arch")
    if "Part" not in sys.modules:
        sys.modules["Part"] = types.ModuleType("Part")


_install_freecad_stubs()

from FacilArquitecturaWB.core import opening_utils as openings  # noqa: E402


class FakeSketch:
    def __init__(self, name, kind=""):
        self.Name = name
        self.Label = name
        self.TypeId = "Sketcher::SketchObject"
        self.Geometry = [object()]
        self.FA_CenterlineKind = kind


class FakeOpening:
    def __init__(self, source, index, generator, role, indices=""):
        self.Name = "%s_%d" % (role, index)
        self.FA_SourceSketch = source
        self.FA_SourceGeometryIndex = index
        self.FA_SourceGeometryIndices = indices
        self.FA_GeneratedBy = generator
        self.FA_Role = role


class FakeDocument:
    def __init__(self, objects):
        self.Objects = list(objects)


class FakeLink:
    def __init__(self, name, linked_object):
        self.Name = name
        self.Label = name
        self.TypeId = "App::Link"
        self.LinkedObject = linked_object


class FakeWall:
    def __init__(self, source):
        self.Name = "Wall"
        self.Label = "Wall"
        self.TypeId = "Part::FeaturePython"
        self.Proxy = types.SimpleNamespace(Type="Wall")
        self.IfcType = "Wall"
        self.Base = source
        self.Shape = types.SimpleNamespace(Solids=[object()])


class OpeningGeometryTests(unittest.TestCase):
    def test_bounded_door_expands_only_native_base_around_authoritative_leaf(self):
        adjustment = openings.bounded_door_base_adjustment(
            663.850602,
            50.0,
            50.0,
            {"status": "BOUNDED", "applied": False},
        )

        self.assertEqual("bounded_leaf_authoritative", adjustment["mode"])
        self.assertAlmostEqual(-50.0, adjustment["origin_shift_mm"])
        self.assertAlmostEqual(763.850602, adjustment["outer_width_mm"])
        self.assertIsNone(
            openings.bounded_door_base_adjustment(
                629.668593,
                50.0,
                50.0,
                {"status": "SNAPPED", "applied": True},
            )
        )

    def test_native_door_mode_changes_only_the_single_swing_token(self):
        door = types.SimpleNamespace(
            WindowParts=[
                "OuterFrame", "Frame", "Wire0,Wire1", "60.0+V", "0.00+V",
                "Door", "Solid panel", "Wire1,Edge8,Mode1", "40.0", "30.0+V",
            ]
        )

        count = openings.set_native_door_opening_mode(door, "Mode2")

        self.assertEqual(1, count)
        self.assertEqual("Mode2", openings.native_door_opening_mode(door))
        self.assertEqual("Wire1,Edge8,Mode2", door.WindowParts[7])
        self.assertEqual("OuterFrame", door.WindowParts[0])

    def test_native_door_mode_resolver_uses_physical_hinge(self):
        forward = openings.resolve_door_native_mode(
            (0, 0, 0, 900, 0, 0), (0, 0, 0), "LEFT"
        )
        reverse = openings.resolve_door_native_mode(
            (900, 0, 0, 0, 0, 0), (0, 0, 0), "RIGHT"
        )

        self.assertEqual("Mode1", forward["mode"])
        self.assertEqual("Mode1", reverse["mode"])

    def test_opening_length_comes_from_axis_geometry(self):
        self.assertAlmostEqual(1000.0, openings.segment_length((0, 0, 600, 800)))

    def test_projection_reports_distance_and_unclamped_parameter(self):
        distance, point, parameter = openings.project_point_to_line(
            (1200, 40), (0, 0, 0, 1000, 0, 0)
        )

        self.assertAlmostEqual(40.0, distance)
        self.assertEqual((1200.0, 0.0, 0.0), point)
        self.assertAlmostEqual(1.2, parameter)

    def test_collinear_support_across_wall_gap_accepts_opening(self):
        wall_segments = [
            (0, 0, 0, 1800, 0, 0),
            (2600, 0, 0, 5000, 0, 0),
        ]

        match = openings.evaluate_wall_candidate(
            (1800, 20, 0, 2600, 20, 0), wall_segments, max_distance_mm=100
        )

        self.assertIsNotNone(match)
        self.assertAlmostEqual(20.0, match["distance"])
        self.assertAlmostEqual(0.0, match["overhang"])
        self.assertAlmostEqual(800.0, openings.segment_length(
            match["projected_first"] + match["projected_second"]
        ))

    def test_perpendicular_wall_is_rejected(self):
        match = openings.evaluate_wall_candidate(
            (0, 0, 0, 1000, 0, 0),
            [(500, -1000, 0, 500, 1000, 0)],
            max_distance_mm=500,
        )

        self.assertIsNone(match)

    def test_best_host_uses_orientation_and_projection_not_only_distance(self):
        compatible = object()
        perpendicular = object()
        records = [
            {"wall": perpendicular, "segments": [(500, -100, 0, 500, 100, 0)]},
            {"wall": compatible, "segments": [(-500, 40, 0, 1500, 40, 0)]},
        ]

        result = openings.select_best_host(
            (0, 0, 0, 1000, 0, 0), records, max_distance_mm=100
        )

        self.assertFalse(result["ambiguous"])
        self.assertIs(compatible, result["match"]["wall"])

    def test_equivalent_hosts_are_reported_as_ambiguous(self):
        first = object()
        second = object()
        records = [
            {"wall": first, "segments": [(-500, 20, 0, 1500, 20, 0)]},
            {"wall": second, "segments": [(-500, -20, 0, 1500, -20, 0)]},
        ]

        result = openings.select_best_host(
            (0, 0, 0, 1000, 0, 0), records, max_distance_mm=100
        )

        self.assertTrue(result["ambiguous"])
        self.assertIsNone(result["match"])

    def test_corner_snap_uses_other_segment_of_same_multisegment_wall(self):
        wall = types.SimpleNamespace(
            Name="Wall",
            Label="Wall network",
            Width=types.SimpleNamespace(Value=100.0),
        )
        records = [
            {
                "wall": wall,
                "segments": [
                    (-1000, 0, 0, 5000, 0, 0),
                    (0, 0, 0, 0, 3000, 0),
                ],
            }
        ]
        match = openings.select_best_host(
            (80, 0, 0, 980, 0, 0), records, max_distance_mm=100
        )["match"]

        plan = openings.resolve_door_corner_snap(match, records, tolerance_mm=180)

        self.assertTrue(plan["applied"])
        self.assertIs(wall, plan["side_wall"])
        self.assertEqual("START", plan["hinge_endpoint"])
        self.assertEqual("LEFT", plan["opening_side"])
        self.assertAlmostEqual(50.0, plan["projected_first"][0])
        self.assertAlmostEqual(900.0, openings.segment_length(
            tuple(plan["projected_first"]) + tuple(plan["projected_second"])
        ))


class OpeningCompatibilityTests(unittest.TestCase):
    def test_opening_only_accepts_named_source_and_rejects_door_source(self):
        opening = FakeSketch("Sketch_Centros_Aberturas", "openings")
        door = FakeSketch("Sketch_Centros_Puertas", "doors")

        self.assertEqual(
            [opening],
            openings.collect_opening_sketches_from_selection([opening, door], "opening"),
        )

    def test_opening_only_idempotence_is_isolated_from_doors_and_windows(self):
        source = FakeSketch("Sketch_Centros_Aberturas", "openings")
        generated = FakeOpening(
            source, 2, openings.GENERATED_BY_OPENINGS, "opening"
        )
        door = FakeOpening(source, 2, openings.GENERATED_BY_DOORS, "door")
        window = FakeOpening(source, 2, openings.GENERATED_BY_WINDOWS, "window")

        keys = openings.existing_opening_keys(
            FakeDocument([generated, door, window]), [source], "opening"
        )

        self.assertEqual({(("name", source.Name), 2)}, keys)

    def test_explicit_generic_sketch_is_accepted_by_requested_command(self):
        generic = FakeSketch("SketchGenerico")

        result = openings.collect_opening_sketches_from_selection([generic], "door")

        self.assertEqual([generic], result)

    def test_window_sketch_is_not_accepted_as_door_source(self):
        window = FakeSketch("Sketch_Centros_Ventanas", "windows")

        result = openings.collect_opening_sketches_from_selection([window], "door")

        self.assertEqual([], result)

    def test_selected_app_link_resolves_generic_sketch(self):
        generic = FakeSketch("SketchGenerico")
        link = FakeLink("LinkVentanas", generic)

        result = openings.collect_opening_sketches_from_selection([link], "window")

        self.assertEqual([generic], result)

    def test_explicit_historical_window_sketches_override_wrong_wall_kind(self):
        names = (
            "Sketch_Centros_Ventanas_de_S_S",
            "Sketch_Centros_Ventanas001",
            "Sketch_Centros_Ventanales",
            "Sketch_Centros_Seleccion_14_objetos",
        )
        sketches = [FakeSketch(name, "walls") for name in names]
        sketches[0].FA_ElementType = "Ventanas de S.S"
        sketches[1].FA_ElementType = "Ventanas"
        sketches[2].FA_ElementType = "Ventanales"
        sketches[3].FA_ElementType = "Por definir"

        result = openings.collect_opening_sketches_from_selection(sketches, "window")

        self.assertEqual(sketches, result)

    def test_automatic_discovery_accepts_named_windows_but_not_generic_wrong_kind(self):
        named = FakeSketch("Sketch_Centros_Ventanas001", "walls")
        generic = FakeSketch("Sketch_Centros_Seleccion_14_objetos", "walls")

        result = openings.collect_opening_sketches_from_document(
            FakeDocument([named, generic]), "window"
        )

        self.assertEqual([named], result)

    def test_selected_wall_does_not_contribute_its_base_as_opening(self):
        wall_axis = FakeSketch("SketchGenerico")
        wall = FakeWall(wall_axis)

        result = openings.collect_opening_sketches_from_selection([wall], "window")

        self.assertEqual([], result)

    def test_document_fallback_finds_named_window_center_sketch(self):
        wall_axis = FakeSketch("Sketch_Muros")
        windows = FakeSketch("Sketch_Centros_Ventanas", "windows")
        duplicate = FakeSketch("Sketch_Centros_Ventanas001", "windows")
        generated_base = FakeSketch("Sketch_Window_Base")
        generated_base.FA_Role = "window_base"
        generated_base.FA_GeneratedBy = openings.GENERATED_BY_WINDOWS

        result = openings.collect_opening_sketches_from_document(
            FakeDocument([wall_axis, windows, duplicate, generated_base]), "window"
        )

        self.assertEqual([windows], result)

    def test_document_fallback_prefers_source_referenced_by_existing_openings(self):
        canonical = FakeSketch("Sketch_Centros_Ventanas", "windows")
        referenced = FakeSketch("Sketch_Centros_Ventanas001", "windows")
        existing = FakeOpening(
            referenced, 0, openings.GENERATED_BY_WINDOWS, "window"
        )

        result = openings.collect_opening_sketches_from_document(
            FakeDocument([canonical, referenced, existing]), "window"
        )

        self.assertEqual([referenced], result)

    def test_document_fallback_never_accepts_an_unidentified_generic_sketch(self):
        generic = FakeSketch("SketchGenerico")

        result = openings.collect_opening_sketches_from_document(
            FakeDocument([generic]), "window"
        )

        self.assertEqual([], result)

    def test_legacy_source_indices_prevent_duplicates(self):
        source = FakeSketch("Sketch_Centros_Puertas", "doors")
        legacy = FakeOpening(
            source,
            0,
            "FA_InsertDoorsBIM",
            "door",
            indices="0,18",
        )
        doc = FakeDocument([source, legacy])

        keys = openings.existing_opening_keys(doc, [source], "door")

        self.assertEqual(
            {
                (("name", source.Name), 0),
                (("name", source.Name), 18),
            },
            keys,
        )

    def test_other_source_is_not_part_of_idempotence_key_set(self):
        source = FakeSketch("Sketch_Centros_Puertas_A", "doors")
        other = FakeSketch("Sketch_Centros_Puertas_B", "doors")
        existing = FakeOpening(other, 3, openings.GENERATED_BY_DOORS, "door")

        keys = openings.existing_opening_keys(FakeDocument([existing]), [source], "door")

        self.assertEqual(set(), keys)



class FakeContainer:
    def __init__(self, ifc_type=""):
        self.Name = "Container"
        self.IfcType = ifc_type
        self.Group = []
        self.InList = []
        self.PropertiesList = []

    def addProperty(self, _prop_type, name, _group, _description):
        self.PropertiesList.append(name)

    def addObject(self, obj):
        if obj not in self.Group:
            self.Group.append(obj)


class FakeTreeObject:
    def __init__(self, name):
        self.Name = name
        self.Label = name
        self.InList = []
        self.PropertiesList = []

    def addProperty(self, _prop_type, name, _group, _description):
        self.PropertiesList.append(name)


class OpeningTreeTests(unittest.TestCase):
    def test_hosted_opening_is_not_added_directly_to_level_group(self):
        level = FakeContainer("Building Storey")
        opening = FakeTreeObject("Window001")
        base = FakeTreeObject("Sketch001")

        openings.place_hosted_opening_in_tree(level, opening, base)

        self.assertNotIn(opening, level.Group)
        self.assertNotIn(base, level.Group)
        self.assertEqual(level.Name, opening.FA_TargetLevel)
        self.assertEqual(level.Name, base.FA_TargetLevel)

    def test_legacy_container_keeps_only_opening_not_base(self):
        group = FakeContainer()
        opening = FakeTreeObject("Window001")
        base = FakeTreeObject("Sketch001")

        openings.place_hosted_opening_in_tree(group, opening, base)

        self.assertEqual([opening], group.Group)


if __name__ == "__main__":
    unittest.main()
