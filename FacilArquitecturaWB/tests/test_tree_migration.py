"""Pure tests for FA legacy-tree migration into the native BIM Level.

Version: 1.0
Fecha y hora: 2026-09-01 14:40 America/Costa_Rica.
"""
from __future__ import annotations

import sys
import types

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
    def __init__(self, name, type_id="App::DocumentObjectGroup", ifc_type=""):
        self.Name = name
        self.Label = name
        self.TypeId = type_id
        self.IfcType = ifc_type
        self.Group = []
        self.InList = []
        self.PropertiesList = []

    def addProperty(self, _prop_type, name, _group, _description):
        if name not in self.PropertiesList:
            self.PropertiesList.append(name)

    def addObject(self, obj):
        if obj not in self.Group:
            self.Group.append(obj)
        if self not in obj.InList:
            obj.InList.append(self)

    def removeObject(self, obj):
        if obj in self.Group:
            self.Group.remove(obj)
        if self in obj.InList:
            obj.InList.remove(self)


class FakeDocument:
    def __init__(self):
        self.Objects = []

    def add(self, obj):
        self.Objects.append(obj)
        return obj

    def getObject(self, name):
        return next((obj for obj in self.Objects if obj.Name == name), None)

    def addObject(self, type_id, name):
        return self.add(FakeObject(name, type_id))

    def removeObject(self, name):
        obj = self.getObject(name)
        if obj is None:
            return
        for parent in list(obj.InList):
            if hasattr(parent, "removeObject"):
                parent.removeObject(obj)
        self.Objects.remove(obj)


def test_legacy_support_collapses_to_auxiliary_group_without_duplicate_base():
    doc = FakeDocument()
    level = doc.add(FakeObject("Level", "App::GeometryPython", "Building Storey"))
    root = doc.add(FakeObject("FA_Project")); root.FA_Workbench = True
    areas = doc.add(FakeObject("FA_Areas")); master = doc.add(FakeObject("FA_MasterSketches")); params = doc.add(FakeObject("FA_Parameters"))
    root.addObject(areas); root.addObject(master); root.addObject(params)
    room = doc.add(FakeObject("RoomSketch", "Sketcher::SketchObject")); areas.addObject(room)
    sheet = doc.add(FakeObject("Spreadsheet_Parametros", "Spreadsheet::Sheet")); params.addObject(sheet)
    base = doc.add(FakeObject("WallBase", "Sketcher::SketchObject")); master.addObject(base)
    wall = doc.add(FakeObject("Wall", "Part::FeaturePython")); wall.Base = base; base.InList.append(wall)

    result = structure.migrate_legacy_support_to_level(doc, level)
    aux = doc.getObject("FA_Auxiliary_Level")

    assert room in aux.Group and sheet in aux.Group
    assert base not in aux.Group
    assert doc.getObject("FA_Project") is None
    assert result == {"moved": 3, "removed_groups": 3, "removed_root": True}


def test_adoption_respects_unrelated_user_groups():
    doc = FakeDocument()
    level = doc.add(FakeObject("Level", "App::GeometryPython", "Building Storey"))
    root_sketch = doc.add(FakeObject("SketchRoot", "Sketcher::SketchObject"))
    level_sketch = doc.add(FakeObject("SketchLevel", "Sketcher::SketchObject")); level.addObject(level_sketch)
    user_group = doc.add(FakeObject("UserGroup"))
    user_sketch = doc.add(FakeObject("SketchCustom", "Sketcher::SketchObject")); user_group.addObject(user_sketch)

    moved = structure.adopt_auxiliary_sources(doc, level, [root_sketch, level_sketch, user_sketch])
    aux = doc.getObject("FA_Auxiliary_Level")

    assert root_sketch in aux.Group and level_sketch in aux.Group
    assert level_sketch not in level.Group
    assert user_sketch in user_group.Group and user_sketch not in aux.Group
    assert user_sketch not in moved
