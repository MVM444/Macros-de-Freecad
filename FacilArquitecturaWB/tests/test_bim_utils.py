"""Synthetic tests for BIM wall sketch selection and generated wall replacement."""

from __future__ import annotations

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
    if "Arch" not in sys.modules:
        sys.modules["Arch"] = types.ModuleType("Arch")


_install_freecad_stubs()

from FacilArquitecturaWB.core import bim_utils  # noqa: E402


class Quantity:
    def __init__(self, value):
        self.Value = float(value)


class FakeSketch:
    def __init__(self, name, thickness=0.0, kind="walls"):
        self.Name = name
        self.Label = name
        self.TypeId = "Sketcher::SketchObject"
        self.Geometry = [object()]
        self.FA_Role = "centerlines"
        self.FA_CenterlineKind = kind
        self.FA_WallThickness = Quantity(thickness)
        self.FA_RelatedCenterlineSketches = []

    def addProperty(self, _kind, name, _group, _description):
        setattr(self, name, None)


class GenericSketch:
    def __init__(self, name="SketchGenerico", geometry=True):
        self.Name = name
        self.Label = name
        self.TypeId = "Sketcher::SketchObject"
        self.Geometry = [object()] if geometry else []

    def addProperty(self, _kind, name, _group, _description):
        setattr(self, name, None)


class FakeGroup:
    def __init__(self, objects):
        self.Name = "Group"
        self.Group = list(objects)


class FakeWall:
    def __init__(self, name, source):
        self.Name = name
        self.PropertiesList = ["FA_GeneratedBy", "FA_SourceSketch"]
        self.FA_GeneratedBy = bim_utils.GENERATED_BY_WALLS
        self.FA_SourceSketch = source


class FakeNativeWall:
    def __init__(self, name, source, link_sub=False):
        self.Name = name
        self.Label = name
        self.TypeId = "PartDesign::FeaturePython"
        self.Base = (source, ["Edge1"]) if link_sub else source


class FakeDocument:
    def __init__(self, objects):
        self.Objects = list(objects)

    def getObject(self, name):
        return next((obj for obj in self.Objects if obj.Name == name), None)

    def removeObject(self, name):
        self.Objects = [obj for obj in self.Objects if obj.Name != name]


class BIMUtilsTests(unittest.TestCase):
    def test_selected_bim_wall_resolves_its_base_sketch(self):
        source = FakeSketch("Sketch_Base_Muro", 140.0)

        sketches = bim_utils.collect_wall_sketches_from_selection(
            [FakeNativeWall("Wall", source)]
        )

        self.assertEqual([source], sketches)

    def test_selected_link_sub_resolves_its_source_sketch(self):
        source = GenericSketch("Sketch_Base_Generico")

        sketches = bim_utils.collect_any_sketches_from_selection(
            [FakeNativeWall("WallLinkSub", source, link_sub=True)]
        )

        self.assertEqual([source], sketches)

    def test_any_sketch_collector_accepts_unclassified_sketches(self):
        generic = GenericSketch()
        opening = FakeSketch("Sketch_Centros_Ventanas", 0.0)

        sketches = bim_utils.collect_any_sketches_from_selection([FakeGroup([generic, opening])])

        self.assertEqual([generic, opening], sketches)

    def test_generic_sketch_can_be_prepared_as_wall_centerline(self):
        generic = GenericSketch()

        missing = bim_utils.sketches_requiring_wall_metadata([generic])
        prepared = bim_utils.prepare_sketches_as_wall_centerlines(
            missing, thickness=120.0, height=3000.0, wall_type="interior"
        )

        self.assertEqual([generic], prepared)
        self.assertAlmostEqual(120.0, generic.FA_WallThickness)
        self.assertAlmostEqual(3000.0, generic.FA_WallHeight)
        self.assertEqual("centerlines", generic.FA_Role)
        self.assertEqual("walls", generic.FA_CenterlineKind)
        self.assertEqual("interior", generic.FA_ElementType)
        self.assertTrue(generic.FA_ConvertedToWallCenterline)
        self.assertEqual([generic], bim_utils.collect_wall_sketches_from_selection([generic]))

    def test_existing_wall_sketch_without_height_requests_missing_metadata(self):
        wall = FakeSketch("Sketch_Centros_Muro_Espesor_120mm", 120.0)

        missing = bim_utils.sketches_requiring_wall_metadata([wall])

        self.assertEqual([wall], missing)

    def test_conversion_preserves_existing_positive_dimensions_and_previous_role(self):
        generic = GenericSketch("SketchConDatos")
        generic.FA_WallThickness = Quantity(175.0)
        generic.FA_WallHeight = Quantity(2800.0)
        generic.FA_Role = "reference_geometry"
        generic.FA_ElementType = "guide"

        bim_utils.prepare_sketches_as_wall_centerlines(
            [generic], thickness=100.0, height=3000.0, wall_type="exterior"
        )

        self.assertAlmostEqual(175.0, generic.FA_WallThickness.Value)
        self.assertAlmostEqual(2800.0, generic.FA_WallHeight.Value)
        self.assertEqual("reference_geometry", generic.FA_PreviousRole)
        self.assertEqual("guide", generic.FA_PreviousElementType)
        self.assertEqual("exterior", generic.FA_ElementType)

    def test_empty_generic_sketch_is_omitted_during_preparation(self):
        empty = GenericSketch(geometry=False)

        prepared = bim_utils.prepare_sketches_as_wall_centerlines(
            [empty], thickness=100.0, height=3000.0
        )

        self.assertEqual([], prepared)

    def test_primary_centerline_collects_related_thickness_sketches(self):
        primary = FakeSketch("Sketch_Centros_Muro_Espesor_100mm", 100.0)
        related = FakeSketch("Sketch_Centros_Muro_Espesor_200mm", 200.0)
        column = FakeSketch("Sketch_Centros_Muro_Columnas", 0.0, kind="columns")
        primary.FA_RelatedCenterlineSketches = [related, column]

        sketches = bim_utils.collect_wall_sketches_from_selection([primary])

        self.assertEqual([primary, related], sketches)

    def test_group_selection_excludes_columns_and_opening_sketches(self):
        wall = FakeSketch("Sketch_Centros_Muro_Espesor_150mm", 150.0)
        column = FakeSketch("Sketch_Centros_Muro_Columnas", 0.0, kind="columns")
        opening = FakeSketch("Sketch_Centros_Ventanas", 0.0)

        sketches = bim_utils.collect_wall_sketches_from_selection([FakeGroup([wall, column, opening])])

        self.assertEqual([wall], sketches)

    def test_grid_wall_trace_is_accepted_when_it_has_wall_thickness(self):
        trace = FakeSketch("FA_GridWallTrace", 120.0)
        trace.FA_Role = "grid_clipped_lines"

        sketches = bim_utils.collect_wall_sketches_from_selection([trace])

        self.assertEqual([trace], sketches)

    def test_thickness_falls_back_to_generated_label(self):
        sketch = FakeSketch("Sketch_Centros_Muro_Espesor_117.5mm", 0.0)

        self.assertAlmostEqual(117.5, bim_utils.wall_thickness_from_sketch(sketch))

    def test_legacy_master_uses_spreadsheet_thickness(self):
        sketch = FakeSketch("Sketch_Muros_Ext_200", 0.0)

        self.assertAlmostEqual(
            250.0,
            bim_utils.wall_thickness_from_sketch(sketch, params={"ext_wall_thickness_mm": 250.0}),
        )

    def test_replacement_removes_only_walls_from_selected_sources(self):
        first_source = FakeSketch("Sketch_Centros_100", 100.0)
        second_source = FakeSketch("Sketch_Centros_200", 200.0)
        first_wall = FakeWall("Wall100", first_source)
        second_wall = FakeWall("Wall200", second_source)
        doc = FakeDocument([first_source, second_source, first_wall, second_wall])
        group = types.SimpleNamespace(Group=[first_wall, second_wall])

        removed = bim_utils.remove_previous_generated_walls(doc, group, source_sketches=[first_source])

        self.assertEqual(1, removed)
        self.assertIsNone(doc.getObject("Wall100"))
        self.assertIsNotNone(doc.getObject("Wall200"))


if __name__ == "__main__":
    unittest.main()
