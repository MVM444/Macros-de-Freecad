"""FreeCAD 1.1.3 smoke for the common Espacios y Recintos v0.1 commands."""

from __future__ import annotations

import json
import os
import pathlib
import sys

import Arch
import FreeCAD as App
import FreeCADGui as Gui
import Part


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from CRBIMCore import freecad_room_adapter as room_resolver  # noqa: E402
from CRBIMCore import freecad_room_operations as operations  # noqa: E402
from CRBIMCore import room_resolver_core as resolver_core  # noqa: E402
from CRBIMCore.commands import common_rooms  # noqa: E402


DOC_NAME = "CRBIMCommonRoomsSmoke"
OUTPUT_NAME = "crbim_common_rooms_smoke.FCStd"


def _add_property(obj, property_type, name, value):
    if name not in obj.PropertiesList:
        obj.addProperty(property_type, name, "CRBIM smoke")
    setattr(obj, name, value)


def _face(x0, y0, width, depth, z=0.0):
    points = [
        App.Vector(x0, y0, z),
        App.Vector(x0 + width, y0, z),
        App.Vector(x0 + width, y0 + depth, z),
        App.Vector(x0, y0 + depth, z),
        App.Vector(x0, y0, z),
    ]
    return Part.Face(Part.makePolygon(points))


def _space(doc, base_name, x0, y0, width, depth, height=2700.0):
    base = doc.addObject("Part::Feature", base_name)
    base.Shape = Part.makeBox(width, depth, height, App.Vector(x0, y0, 0.0))
    space = Arch.makeSpace([base])
    return base, space


def _area(doc, name, x0, y0, width, depth):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = _face(x0, y0, width, depth)
    _add_property(obj, "App::PropertyString", "ElectricCRTipo", "Area")
    _add_property(obj, "App::PropertyString", "GeneratedBy", "AreaPorClick")
    _add_property(obj, "App::PropertyFloat", "AreaM2", width * depth / 1000000.0)
    return obj


def _shape_signature(obj):
    shape = obj.Shape
    bounds = shape.BoundBox
    return {
        "area": round(float(shape.Area), 6),
        "volume": round(float(shape.Volume), 6),
        "bbox": [
            round(float(bounds.XMin), 6), round(float(bounds.YMin), 6), round(float(bounds.ZMin), 6),
            round(float(bounds.XMax), 6), round(float(bounds.YMax), 6), round(float(bounds.ZMax), 6),
        ],
    }


def _room_signature(obj):
    base = getattr(obj, "Base", None)
    return {
        "name": obj.Name,
        "label": obj.Label,
        "uid": str(getattr(obj, "FA_RoomUID", "") or ""),
        "room_id": str(getattr(obj, "FA_RoomID", "") or ""),
        "base": getattr(base, "Name", ""),
        "shape": _shape_signature(obj),
        "placement": [round(float(value), 9) for value in obj.Placement.toMatrix().A],
        "parents": sorted(parent.Name for parent in list(getattr(obj, "InList", []) or [])),
    }


def _close_owned(output_path):
    target = os.path.normcase(os.path.abspath(output_path))
    for name, doc in list(App.listDocuments().items()):
        filename = str(getattr(doc, "FileName", "") or "")
        if name == DOC_NAME or (filename and os.path.normcase(os.path.abspath(filename)) == target):
            App.closeDocument(name)


def main():
    output_dir = REPO_ROOT / ".codex_tmp"
    output_dir.mkdir(exist_ok=True)
    output_path = str(output_dir / OUTPUT_NAME)
    _close_owned(output_path)
    if os.path.isfile(output_path):
        os.remove(output_path)

    assert App.Version()[0:3] == ["1", "1", "3"], App.Version()
    assert "Arch_Space" in Gui.listCommands()
    assert "BIM_Space" not in Gui.listCommands()
    first_registration = common_rooms.ensure_common_room_commands_registered()
    second_registration = common_rooms.ensure_common_room_commands_registered()
    assert first_registration == second_registration == list(common_rooms.COMMAND_IDS)
    listed = list(Gui.listCommands())
    assert all(listed.count(command_id) == 1 for command_id in common_rooms.COMMAND_IDS)

    doc = App.newDocument(DOC_NAME)
    doc.UndoMode = 1
    try:
        level = doc.addObject("App::DocumentObjectGroup", "Level")
        _add_property(level, "App::PropertyString", "IfcType", "Building Storey")

        base, space = _space(doc, "SpaceBase", 0, 0, 4000, 3000)
        space.Label = "Espacio original"
        _add_property(space, "App::PropertyString", "FA_RoomUID", "uid-space-1")
        _add_property(space, "App::PropertyString", "FA_RoomID", "S-01")
        level.addObject(space)

        overlap = _area(doc, "AreaOverlap", 0, 0, 4000, 3000)
        overlap.Label = "Area superpuesta"
        area = _area(doc, "AreaLegacy", 5000, 0, 3000, 2500)
        area.Label = "Area original"
        _add_property(area, "App::PropertyString", "FA_RoomUID", "uid-area-1")
        _add_property(area, "App::PropertyString", "FA_RoomID", "A-01")

        _base_a, space_a = _space(doc, "AmbiguousBaseA", 10000, 0, 3000, 3000)
        _base_b, space_b = _space(doc, "AmbiguousBaseB", 10500, 500, 1800, 1800)

        hvac = doc.addObject("App::FeaturePython", "HVACSpace")
        _add_property(hvac, "App::PropertyString", "MEPType", "HVACSpace")
        _add_property(hvac, "App::PropertyLink", "BaseSpace", space)

        subarea = _area(doc, "SubArea", 0, 0, 1000, 1000)
        subarea.ElectricCRTipo = "SubArea"

        equipment = doc.addObject("Part::FeaturePython", "Equipment")
        equipment.Shape = Part.makeBox(100, 100, 100, App.Vector(1000, 1000, 100))
        doc.recompute()

        native = room_resolver.resolve_room_for_point(doc, [1000, 1000, 0])
        legacy = room_resolver.resolve_room_for_point(doc, [6000, 1000, 0])
        ambiguous = room_resolver.resolve_room_for_point(doc, [11000, 1000, 0])
        outside = room_resolver.resolve_room_for_point(doc, [50000, 50000, 0])
        hvac_result = room_resolver.resolve_room_for_object(doc, hvac)
        subarea_result = room_resolver.resolve_room_for_object(doc, subarea)
        assert (native["status"], native["source_kind"], native["object_name"]) == (
            "RESOLVED", "NATIVE_SPACE", space.Name,
        )
        assert overlap.Name != native["object_name"]
        assert (legacy["status"], legacy["source_kind"], legacy["object_name"]) == (
            "RESOLVED", "LEGACY_AREA", area.Name,
        )
        assert ambiguous["status"] == "AMBIGUOUS"
        assert sorted(item["object_name"] for item in ambiguous["alternatives"]) == sorted(
            [space_a.Name, space_b.Name]
        )
        assert outside["status"] == "NOT_FOUND"
        assert hvac_result["object_name"] == space.Name
        assert subarea_result["status"] == "NOT_FOUND"

        # Actual command wrapper: related equipment resolves to the physical Space.
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, equipment.Name)
        Gui.runCommand(common_rooms.SELECT_ROOM, 0)
        assert [obj.Name for obj in Gui.Selection.getSelection()] == [space.Name]

        before_info = [_room_signature(space), _room_signature(area)]
        info_space = operations.room_info(doc, native)
        info_area = operations.room_info(doc, legacy)
        json.dumps([info_space, info_area], sort_keys=True)
        assert info_space["source_label"] == "Space"
        assert info_space["base_name"] == base.Name
        assert info_space["level"] == level.Name
        assert info_area["source_label"] == "Area legacy"
        assert [_room_signature(space), _room_signature(area)] == before_info

        dry_run = operations.apply_room_labels(doc, [space, area, equipment], "Oficina", dry_run=True)
        assert dry_run["changed"] == 2 and dry_run["applied"] == 0
        assert [item["object_name"] for item in dry_run["rejected"]] == [equipment.Name]
        assert [_room_signature(space), _room_signature(area)] == before_info

        document_preferences = App.ParamGet("User parameter:BaseApp/Preferences/Document")
        duplicate_labels_before = document_preferences.GetBool("DuplicateLabels", False)
        applied = operations.apply_room_labels(doc, [space, area, equipment], "Oficina", dry_run=False)
        assert document_preferences.GetBool("DuplicateLabels", False) == duplicate_labels_before
        assert applied["applied"] == 2
        after_rename = [_room_signature(space), _room_signature(area)]
        for before, after in zip(before_info, after_rename):
            assert after["label"] == "Oficina", (before, after, applied)
            for key in ("name", "uid", "room_id", "base", "shape", "placement", "parents"):
                assert after[key] == before[key], (key, before, after)

        doc.undo()
        doc.recompute()
        assert [space.Label, area.Label] == ["Espacio original", "Area original"]
        doc.redo()
        doc.recompute()
        assert [space.Label, area.Label] == ["Oficina", "Oficina"]
        assert [_room_signature(space), _room_signature(area)] == after_rename

        expected = {
            "space": _room_signature(space),
            "area": _room_signature(area),
            "hvac_base": hvac.BaseSpace.Name,
        }
        names = {
            "space": space.Name,
            "area": area.Name,
            "hvac": hvac.Name,
            "subarea": subarea.Name,
        }
        doc.saveAs(output_path)
        App.closeDocument(doc.Name)
        reopened = App.openDocument(output_path)
        reopened.recompute()
        restored_space = reopened.getObject(names["space"])
        restored_area = reopened.getObject(names["area"])
        restored_hvac = reopened.getObject(names["hvac"])
        assert _room_signature(restored_space) == expected["space"]
        assert _room_signature(restored_area) == expected["area"]
        assert restored_hvac.BaseSpace.Name == expected["hvac_base"]
        assert room_resolver.resolve_room_for_object(reopened, restored_hvac)["object_name"] == restored_space.Name
        assert room_resolver.resolve_room_for_object(reopened, reopened.getObject(names["subarea"]))["status"] == "NOT_FOUND"

        result = {
            "arch_space_command": "Arch_Space",
            "common_commands": first_registration,
            "space_priority": native["object_name"],
            "legacy_fallback": legacy["object_name"],
            "ambiguous_count": len(ambiguous["alternatives"]),
            "outside": outside["status"],
            "info_read_only": True,
            "renamed": applied["applied"],
            "rejected_non_rooms": len(applied["rejected"]),
            "undo_redo": True,
            "reopen_stable": True,
            "hvac_base_space": hvac_result["object_name"],
            "subarea": subarea_result["status"],
        }
        print("CRBIM_COMMON_ROOMS_SMOKE_OK", json.dumps(result, sort_keys=True))
    finally:
        Gui.Selection.clearSelection()
        _close_owned(output_path)
        if os.path.isfile(output_path):
            os.remove(output_path)


if __name__ == "__main__":
    main()
