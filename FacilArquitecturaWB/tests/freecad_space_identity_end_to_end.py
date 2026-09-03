"""FreeCAD 1.1.3 end-to-end smoke for non-destructive FA BIM Space sync.

Creates only a temporary document.  Validates persistent Space/Base identity,
external PropertyLinks, geometry updates, NO_MATCH, AMBIGUO, stale preservation,
Undo/Redo and save/reopen behavior.
"""

from __future__ import annotations

import json
import os

import FreeCAD as App
import Part
import Sketcher  # noqa: F401

from FacilArquitecturaWB.core.bim_structure_utils import add_to_level, ensure_bim_structure
from FacilArquitecturaWB.core.project_structure import set_prop
from FacilArquitecturaWB.core.space_utils import (
    SPACE_GENERATOR,
    create_bim_spaces,
    room_records_from_sketch,
)


DOC = "FASpaceIdentityE2E"


def _same_path(first, second):
    if not first or not second:
        return False
    return os.path.normcase(os.path.abspath(first)) == os.path.normcase(os.path.abspath(second))


def _close_test_documents(output_path):
    """Close only documents owned by this smoke, including a saved/reopened copy."""
    for name, candidate in list(App.listDocuments().items()):
        if name == DOC or _same_path(getattr(candidate, "FileName", ""), output_path):
            App.closeDocument(name)


def _add_rectangle(sketch, x0, y0, x1, y1):
    first = int(sketch.GeometryCount)
    sketch.addGeometry(
        [
            Part.LineSegment(App.Vector(x0, y0, 0), App.Vector(x1, y0, 0)),
            Part.LineSegment(App.Vector(x1, y0, 0), App.Vector(x1, y1, 0)),
            Part.LineSegment(App.Vector(x1, y1, 0), App.Vector(x0, y1, 0)),
            Part.LineSegment(App.Vector(x0, y1, 0), App.Vector(x0, y0, 0)),
        ],
        False,
    )
    return list(range(first, first + 4))


def _space_objects(doc):
    return [
        obj
        for obj in doc.Objects
        if str(getattr(obj, "FA_Role", "") or "") == "bim_space"
    ]


def _snapshot(spaces):
    return {
        obj.Name: {
            "room_id": str(obj.FA_RoomID),
            "uid": str(obj.FA_RoomUID),
            "base": obj.Base.Name,
            "area_mm2": float(obj.FA_RoomArea.Value),
            "source": getattr(obj.FA_SourceRoomSketch, "Name", None),
        }
        for obj in spaces
    }


def _assert_excluded(spaces):
    for space in spaces:
        assert bool(space.GameExportExclude) is True, space.Name
        assert bool(space.Base.GameExportExclude) is True, space.Base.Name


def main():
    repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(repo_dir, ".codex_tmp")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "fa_space_identity_end_to_end.FCStd")
    active_before = getattr(App.ActiveDocument, "Name", None)
    _close_test_documents(output_path)
    if os.path.exists(output_path):
        os.remove(output_path)

    try:
        doc = App.newDocument(DOC)
        level = ensure_bim_structure(doc)["level"]
        room_sketch = doc.addObject("Sketcher::SketchObject", "Sketch_Recintos_E2E")
        first_room = _add_rectangle(room_sketch, 0.0, 0.0, 4000.0, 3000.0)
        _add_rectangle(room_sketch, 5000.0, 0.0, 9000.0, 3000.0)
        _add_rectangle(room_sketch, 0.0, 4000.0, 4000.0, 7000.0)
        set_prop(room_sketch, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", "FA_CreateClosedRooms")
        set_prop(room_sketch, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "closed_rooms")
        set_prop(room_sketch, "App::PropertyInteger", "FA_RoomCount", "FacilArquitectura", "Cantidad", 3)
        set_prop(room_sketch, "App::PropertyLength", "FA_SnapTolerance", "FacilArquitectura", "Tolerancia", 25.0)
        set_prop(room_sketch, "App::PropertyFloat", "FA_MinRoomAreaM2", "FacilArquitectura", "Area minima", 0.25)
        add_to_level(level, room_sketch, source_sketch=room_sketch)
        doc.recompute()

        initial_records = room_records_from_sketch(room_sketch, 2700.0)
        assert len(initial_records) == 3, initial_records
        doc.openTransaction("FA E2E crear 3 Spaces")
        initial_result = create_bim_spaces(
            doc, level, room_sketch, room_records=initial_records,
            default_height_mm=2700.0, replace_existing=True,
        )
        doc.commitTransaction()
        initial_spaces = list(initial_result["spaces"])
        assert len(initial_spaces) == 3
        assert initial_result["created"] == 3
        initial = _snapshot(initial_spaces)
        _assert_excluded(initial_spaces)

        probes = {}
        doc.openTransaction("FA E2E crear enlaces externos")
        for index, space in enumerate(initial_spaces, 1):
            probe = doc.addObject("App::FeaturePython", "FA_SpaceLinkProbe%02d" % index)
            probe.addProperty("App::PropertyLink", "TargetSpace", "E2E")
            probe.TargetSpace = space
            probes[space.Name] = probe
        doc.recompute()
        doc.commitTransaction()
        probe_names = {name: probe.Name for name, probe in probes.items()}

        doc.openTransaction("FA E2E cambiar un recinto")
        for geometry_index in reversed(first_room):
            room_sketch.delGeometry(geometry_index)
        _add_rectangle(room_sketch, 0.0, 0.0, 4200.0, 3000.0)
        changed_records = room_records_from_sketch(room_sketch, 2700.0)
        preview = create_bim_spaces(
            doc, level, room_sketch, room_records=changed_records,
            default_height_mm=2700.0, replace_existing=True, dry_run=True,
        )
        assert preview["plan"]["counts"]["CAMBIO"] == 1, preview["plan"]["counts"]
        assert preview["plan"]["counts"]["MATCH"] == 2, preview["plan"]["counts"]
        changed_result = create_bim_spaces(
            doc, level, room_sketch, room_records=changed_records,
            default_height_mm=2700.0, replace_existing=True,
        )
        doc.commitTransaction()
        changed_spaces = _space_objects(doc)
        changed = _snapshot(changed_spaces)
        assert set(changed) == set(initial)
        assert changed_result["created"] == 0
        assert changed_result["updated"] == 1
        for name in initial:
            assert changed[name]["room_id"] == initial[name]["room_id"]
            assert changed[name]["uid"] == initial[name]["uid"]
            assert changed[name]["base"] == initial[name]["base"]
            assert probes[name].TargetSpace.Name == name
        assert sum(changed[name]["area_mm2"] != initial[name]["area_mm2"] for name in initial) == 1
        _assert_excluded(changed_spaces)

        doc.undo()
        doc.recompute()
        undone = _snapshot(_space_objects(doc))
        assert set(undone) == set(initial)
        assert all(probes[name].TargetSpace.Name == name for name in initial)
        doc.redo()
        doc.recompute()
        redone = _snapshot(_space_objects(doc))
        assert redone == changed

        doc.openTransaction("FA E2E agregar recinto")
        _add_rectangle(room_sketch, 5000.0, 4000.0, 9000.0, 7000.0)
        room_sketch.FA_RoomCount = 4
        four_records = room_records_from_sketch(room_sketch, 2700.0)
        add_preview = create_bim_spaces(
            doc, level, room_sketch, room_records=four_records,
            default_height_mm=2700.0, replace_existing=True, dry_run=True,
        )
        assert add_preview["plan"]["counts"]["NO_MATCH"] == 1, add_preview["plan"]["counts"]
        added_result = create_bim_spaces(
            doc, level, room_sketch, room_records=four_records,
            default_height_mm=2700.0, replace_existing=True,
        )
        doc.commitTransaction()
        four_spaces = _space_objects(doc)
        assert len(four_spaces) == 4
        assert added_result["created"] == 1
        assert all(doc.getObject(name) is not None for name in initial)

        stale_preview = create_bim_spaces(
            doc, level, room_sketch, room_records=[four_records[0]],
            default_height_mm=2700.0, replace_existing=True, dry_run=True,
        )
        assert len(stale_preview["stale"]) == 3, stale_preview["stale"]
        stale_names = {obj.Name for obj in four_spaces}
        stale_result = create_bim_spaces(
            doc, level, room_sketch, room_records=[four_records[0]],
            default_height_mm=2700.0, replace_existing=True,
        )
        assert {obj.Name for obj in _space_objects(doc)} == stale_names
        assert len(stale_result["stale"]) == 3

        duplicate_result = create_bim_spaces(
            doc, level, room_sketch, room_records=[four_records[0]],
            default_height_mm=2700.0, replace_existing=False,
            label_suffix=" - duplicado E2E",
        )
        duplicate = duplicate_result["spaces"][0]
        candidates_before = {
            obj.Name: (str(obj.FA_RoomUID), obj.Base.Name, float(obj.FA_RoomArea.Value))
            for obj in _space_objects(doc)
        }
        ambiguous_preview = create_bim_spaces(
            doc, level, room_sketch, room_records=[four_records[0]],
            default_height_mm=2700.0, replace_existing=True, dry_run=True,
        )
        assert ambiguous_preview["plan"]["counts"]["AMBIGUO"] == 1
        ambiguous_result = create_bim_spaces(
            doc, level, room_sketch, room_records=[four_records[0]],
            default_height_mm=2700.0, replace_existing=True,
        )
        assert ambiguous_result["ambiguous"] == 1
        assert ambiguous_result["created"] == 0
        assert ambiguous_result["updated"] == 0
        candidates_after = {
            obj.Name: (str(obj.FA_RoomUID), obj.Base.Name, float(obj.FA_RoomArea.Value))
            for obj in _space_objects(doc)
        }
        assert candidates_after == candidates_before
        assert duplicate.Name in candidates_after
        _assert_excluded(_space_objects(doc))

        doc.recompute()
        doc.saveAs(output_path)
        App.closeDocument(doc.Name)
        reopened = App.openDocument(output_path)
        reopened.recompute()
        count_before = len(reopened.Objects)
        reopened.recompute()
        assert len(reopened.Objects) == count_before
        restored_spaces = _space_objects(reopened)
        assert len(restored_spaces) == 5
        for name, probe_name in probe_names.items():
            restored_probe = reopened.getObject(probe_name)
            assert restored_probe is not None
            assert restored_probe.TargetSpace is not None
            assert restored_probe.TargetSpace.Name == name
            restored_space = reopened.getObject(name)
            assert str(restored_space.FA_RoomUID) == initial[name]["uid"]
            assert restored_space.Base.Name == initial[name]["base"]
        _assert_excluded(restored_spaces)

        result = {
            "initial_spaces": 3,
            "changed": changed_result["updated"],
            "new_spaces": added_result["created"],
            "stale_preserved": len(stale_result["stale"]),
            "ambiguous": ambiguous_result["ambiguous"],
            "restored_spaces": len(restored_spaces),
            "restored_objects": len(reopened.Objects),
            "saved": output_path,
        }
        App.closeDocument(reopened.Name)
        print("FA_SPACE_IDENTITY_E2E_OK", json.dumps(result, sort_keys=True))
    finally:
        _close_test_documents(output_path)
        if active_before and active_before in App.listDocuments():
            App.setActiveDocument(active_before)


if __name__ == "__main__":
    main()
