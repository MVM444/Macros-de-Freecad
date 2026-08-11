"""Pure tests for native BIM structure selection and idempotence helpers."""

from __future__ import annotations

import sys
import types
import unittest


if "FreeCAD" not in sys.modules:
    freecad = types.ModuleType("FreeCAD")
    freecad.Placement = lambda value=None: value
    freecad.Console = types.SimpleNamespace(
        PrintMessage=lambda _message: None,
        PrintWarning=lambda _message: None,
        PrintError=lambda _message: None,
    )
    sys.modules["FreeCAD"] = freecad
if "Arch" not in sys.modules:
    sys.modules["Arch"] = types.ModuleType("Arch")

from FacilArquitecturaWB.core import bim_structure_utils as structure  # noqa: E402


class FakeObject:
    def __init__(self, name, ifc_type=""):
        self.Name = name
        self.Label = name
        self.IfcType = ifc_type
        self.Group = []
        self.InList = []
        self.PropertiesList = []

    def addProperty(self, _prop_type, name, _group, _description):
        self.PropertiesList.append(name)

    def addObject(self, obj):
        if obj not in self.Group:
            self.Group.append(obj)
        if self not in obj.InList:
            obj.InList.append(self)


class FakeDocument:
    def __init__(self, objects=None):
        self.Objects = list(objects or [])

    def recompute(self):
        pass


class FakeArch:
    def __init__(self, doc):
        self.doc = doc

    def makeBuilding(self, name=None):
        obj = FakeObject("Building", "Building")
        obj.Label = name or "Building"
        self.doc.Objects.append(obj)
        return obj

    def makeFloor(self, name=None):
        obj = FakeObject("Level", "Building Storey")
        obj.Label = name or "Level"
        obj.LevelOffset = 0.0
        obj.Placement = types.SimpleNamespace(Base=types.SimpleNamespace(z=0.0))
        self.doc.Objects.append(obj)
        return obj


class BIMStructureTests(unittest.TestCase):
    def setUp(self):
        self.previous_arch = structure.Arch

    def tearDown(self):
        structure.Arch = self.previous_arch

    def test_native_building_and_level_are_reused(self):
        doc = FakeDocument()
        structure.Arch = FakeArch(doc)

        first = structure.ensure_bim_structure(doc, "Sucursal", "Nivel 00", 0.0)
        second = structure.ensure_bim_structure(doc, "Sucursal", "Nivel 00", 0.0)

        self.assertIs(first["building"], second["building"])
        self.assertIs(first["level"], second["level"])
        self.assertEqual(1, len(structure.collect_buildings(doc)))
        self.assertEqual(1, len(structure.collect_levels(doc)))
        self.assertIn(first["level"], first["building"].Group)

    def test_add_to_level_creates_real_group_and_property_links(self):
        level = FakeObject("Level", "Building Storey")
        wall = FakeObject("Wall", "Wall")
        sketch = FakeObject("Sketch_Muros")

        structure.add_to_level(level, wall, source_sketch=sketch)

        self.assertIn(wall, level.Group)
        self.assertEqual(level.Name, wall.FA_TargetLevel)
        self.assertFalse(hasattr(sketch, "FA_TargetLevel"))

    def test_selected_child_resolves_its_level(self):
        level = FakeObject("Level", "Building Storey")
        wall = FakeObject("Wall", "Wall")
        level.addObject(wall)

        self.assertIs(level, structure.selected_level([wall]))


if __name__ == "__main__":
    unittest.main()
