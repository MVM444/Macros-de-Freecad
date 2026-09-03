"""FreeCAD 1.1.3 smoke for RoomResolver common phase 1 read-only."""

from __future__ import annotations

import json
import os
import pathlib
import sys

import Arch
import FreeCAD as App
import Part


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from CRBIMCore import freecad_room_adapter as resolver  # noqa: E402


DOC_NAME = "RoomResolverPhase1Smoke"
OUTPUT_NAME = "room_resolver_phase1_smoke.FCStd"


def _add_property(obj, property_type, name, value):
    if name not in obj.PropertiesList:
        obj.addProperty(property_type, name, "RoomResolver Smoke")
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


def _legacy_face(doc, name, x0, y0, width, depth):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = _face(x0, y0, width, depth)
    return obj


def _native_space(doc, base_name, x0, y0, width, depth, height=2700.0):
    base = doc.addObject("Part::Feature", base_name)
    base.Shape = Part.makeBox(width, depth, height, App.Vector(x0, y0, 0.0))
    space = Arch.makeSpace([base])
    return base, space


def _shape_signature(obj):
    if "Shape" not in list(getattr(obj, "PropertiesList", []) or []):
        return None
    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return None
    bounds = shape.BoundBox
    return {
        "type": str(shape.ShapeType),
        "area": round(float(shape.Area), 6),
        "volume": round(float(shape.Volume), 6),
        "bbox": [
            round(float(bounds.XMin), 6),
            round(float(bounds.YMin), 6),
            round(float(bounds.ZMin), 6),
            round(float(bounds.XMax), 6),
            round(float(bounds.YMax), 6),
            round(float(bounds.ZMax), 6),
        ],
    }


def _document_signature(doc):
    rows = []
    for obj in sorted(doc.Objects, key=lambda item: item.Name):
        row = {
            "name": obj.Name,
            "label": obj.Label,
            "type_id": obj.TypeId,
            "properties": sorted(obj.PropertiesList),
            "shape": _shape_signature(obj),
        }
        for name in (
            "ElectricCRTipo",
            "GeneratedBy",
            "FA_GeneratedBy",
            "FA_Role",
            "MEPType",
            "SourceMode",
            "AreaM2",
            "Recinto",
        ):
            if name in obj.PropertiesList:
                row[name] = str(getattr(obj, name, ""))
        if "BaseSpace" in obj.PropertiesList:
            row["BaseSpace"] = getattr(getattr(obj, "BaseSpace", None), "Name", "")
        rows.append(row)
    return rows


def _close_smoke_documents(output_path):
    target = os.path.normcase(os.path.abspath(output_path))
    for name, doc in list(App.listDocuments().items()):
        filename = str(getattr(doc, "FileName", "") or "")
        if name == DOC_NAME or (filename and os.path.normcase(os.path.abspath(filename)) == target):
            App.closeDocument(name)


def _assert_status(result, status, source_kind=None, object_name=None):
    assert result["status"] == status, result
    if source_kind is not None:
        assert result["source_kind"] == source_kind, result
    if object_name is not None:
        assert result["object_name"] == object_name, result


def main():
    output_dir = REPO_ROOT / ".codex_tmp"
    output_dir.mkdir(exist_ok=True)
    output_path = str(output_dir / OUTPUT_NAME)
    _close_smoke_documents(output_path)
    if os.path.isfile(output_path):
        os.remove(output_path)

    doc = App.newDocument(DOC_NAME)
    try:
        _manual_base, manual_space = _native_space(doc, "ManualSpaceBase", 0, 0, 4000, 3000)
        manual_space.Label = "Espacio BIM manual sin FA"

        overlap_area = _legacy_face(doc, "AreaOverlap", 0, 0, 4000, 3000)
        _add_property(overlap_area, "App::PropertyString", "ElectricCRTipo", "Area")
        _add_property(overlap_area, "App::PropertyString", "GeneratedBy", "AreaPorClick")
        _add_property(overlap_area, "App::PropertyFloat", "AreaM2", 12.0)

        legacy_area = _legacy_face(doc, "AreaLegacy", 5000, 0, 3000, 2500)
        _add_property(legacy_area, "App::PropertyString", "ElectricCRTipo", "Area")
        _add_property(legacy_area, "App::PropertyString", "GeneratedBy", "AreaPorClick")
        _add_property(legacy_area, "App::PropertyFloat", "AreaM2", 7.5)
        _add_property(legacy_area, "App::PropertyString", "Recinto", "Area heredada")

        rectangular = _legacy_face(doc, "AreaRectangular", 5000, 4000, 3000, 2000)
        _add_property(rectangular, "App::PropertyString", "FA_GeneratedBy", "FA_RectangularAreaAnalysis")
        _add_property(rectangular, "App::PropertyFloat", "AreaM2", 6.0)
        _add_property(rectangular, "App::PropertyString", "FA_RoomName", "Rectangular")

        polygonal = _legacy_face(doc, "AreaPolygonal", 0, 5000, 3500, 2200)
        _add_property(polygonal, "App::PropertyString", "FA_GeneratedBy", "FA_PolygonalRoomsFromArchWalls")
        _add_property(polygonal, "App::PropertyString", "FA_Role", "room_polygon")
        _add_property(polygonal, "App::PropertyFloat", "AreaM2", 7.7)

        draft_metadata = _legacy_face(doc, "DraftClosedRoom", 5000, 7500, 2500, 1800)
        _add_property(draft_metadata, "App::PropertyBool", "Closed", True)
        _add_property(draft_metadata, "App::PropertyBool", "MakeFace", True)
        _add_property(draft_metadata, "App::PropertyFloat", "AreaM2", 4.5)
        _add_property(draft_metadata, "App::PropertyString", "Recinto", "Draft con metadatos")

        _amb_base_1, ambiguous_space_1 = _native_space(doc, "AmbiguousBase1", 10000, 0, 3000, 3000)
        _amb_base_2, ambiguous_space_2 = _native_space(doc, "AmbiguousBase2", 10500, 500, 1800, 1800)

        hvac_linked = doc.addObject("App::FeaturePython", "HVACLinked")
        _add_property(hvac_linked, "App::PropertyString", "MEPType", "HVACSpace")
        _add_property(hvac_linked, "App::PropertyLink", "BaseSpace", manual_space)

        hvac_converted = doc.addObject("Part::FeaturePython", "HVACConverted")
        hvac_converted.Shape = _face(15000, 0, 2500, 2000)
        _add_property(hvac_converted, "App::PropertyString", "MEPType", "HVACSpace")
        _add_property(hvac_converted, "App::PropertyLink", "BaseSpace", None)
        _add_property(hvac_converted, "App::PropertyString", "SourceMode", "Converted")

        subarea = _legacy_face(doc, "SubAreaLighting", 0, 0, 1000, 1000)
        _add_property(subarea, "App::PropertyString", "ElectricCRTipo", "SubArea")

        group = doc.addObject("App::DocumentObjectGroup", "FA_RectangularAreas")
        group_only = _legacy_face(doc, "GroupNameOnly", 20000, 0, 2000, 2000)
        group.addObject(group_only)

        equipment = doc.addObject("Part::FeaturePython", "EquipmentInsideManualSpace")
        equipment.Placement.Base = App.Vector(1200, 900, 500)
        doc.recompute()

        signature_before = _document_signature(doc)
        object_count_before = len(doc.Objects)
        audit = resolver.collect_room_candidates(doc)
        json.dumps(audit, sort_keys=True)

        native_priority = resolver.resolve_room_for_point(doc, [1000, 1000, 0])
        legacy_fallback = resolver.resolve_room_for_point(doc, [6000, 1000, 0])
        rectangular_fallback = resolver.resolve_room_for_point(doc, [6000, 5000, 0])
        polygonal_fallback = resolver.resolve_room_for_point(doc, [1000, 6000, 0])
        draft_fallback = resolver.resolve_room_for_point(doc, [6000, 8000, 0])
        ambiguous = resolver.resolve_room_for_point(doc, [11000, 1000, 0])
        not_found = resolver.resolve_room_for_point(doc, [50000, 50000, 0])
        hvac_result = resolver.resolve_room_for_object(doc, hvac_linked)
        converted_result = resolver.resolve_room_for_object(doc, hvac_converted)
        subarea_result = resolver.resolve_room_for_object(doc, subarea)
        object_result = resolver.resolve_room_for_object(doc, equipment)

        _assert_status(native_priority, "RESOLVED", "NATIVE_SPACE", manual_space.Name)
        _assert_status(legacy_fallback, "RESOLVED", "LEGACY_AREA", legacy_area.Name)
        _assert_status(rectangular_fallback, "RESOLVED", "LEGACY_AREA", rectangular.Name)
        _assert_status(polygonal_fallback, "RESOLVED", "LEGACY_AREA", polygonal.Name)
        _assert_status(draft_fallback, "RESOLVED", "LEGACY_AREA", draft_metadata.Name)
        _assert_status(ambiguous, "AMBIGUOUS")
        _assert_status(not_found, "NOT_FOUND")
        _assert_status(hvac_result, "RESOLVED", "NATIVE_SPACE", manual_space.Name)
        _assert_status(converted_result, "NOT_FOUND")
        _assert_status(subarea_result, "NOT_FOUND")
        _assert_status(object_result, "RESOLVED", "NATIVE_SPACE", manual_space.Name)

        candidate_names = {candidate["object_name"] for candidate in audit["candidates"]}
        assert hvac_linked.Name not in candidate_names
        assert hvac_converted.Name not in candidate_names
        assert subarea.Name not in candidate_names
        assert group_only.Name not in candidate_names
        assert len(doc.Objects) == object_count_before
        signature_after = _document_signature(doc)
        if signature_after != signature_before:
            changed = []
            before_by_name = {row["name"]: row for row in signature_before}
            after_by_name = {row["name"]: row for row in signature_after}
            for name in sorted(set(before_by_name) | set(after_by_name)):
                if before_by_name.get(name) != after_by_name.get(name):
                    changed.append(
                        {"name": name, "before": before_by_name.get(name), "after": after_by_name.get(name)}
                    )
            raise AssertionError("RoomResolver modifico el documento: %s" % json.dumps(changed, sort_keys=True))

        expected_after_reopen = {
            "native": manual_space.Name,
            "legacy": legacy_area.Name,
            "ambiguous": sorted([ambiguous_space_1.Name, ambiguous_space_2.Name]),
            "candidate_names": sorted(candidate_names),
        }
        doc.saveAs(output_path)
        App.closeDocument(doc.Name)
        reopened = App.openDocument(output_path)
        reopened.recompute()
        reopened_signature_before = _document_signature(reopened)
        reopened_audit = resolver.collect_room_candidates(reopened)
        reopened_native = resolver.resolve_room_for_point(reopened, [1000, 1000, 0])
        reopened_legacy = resolver.resolve_room_for_point(reopened, [6000, 1000, 0])
        reopened_ambiguous = resolver.resolve_room_for_point(reopened, [11000, 1000, 0])
        reopened_hvac = resolver.resolve_room_for_object(reopened, reopened.getObject("HVACLinked"))

        _assert_status(reopened_native, "RESOLVED", "NATIVE_SPACE", expected_after_reopen["native"])
        _assert_status(reopened_legacy, "RESOLVED", "LEGACY_AREA", expected_after_reopen["legacy"])
        _assert_status(reopened_ambiguous, "AMBIGUOUS")
        _assert_status(reopened_hvac, "RESOLVED", "NATIVE_SPACE", expected_after_reopen["native"])
        assert sorted(item["object_name"] for item in reopened_ambiguous["alternatives"]) == expected_after_reopen["ambiguous"]
        assert sorted(candidate["object_name"] for candidate in reopened_audit["candidates"]) == expected_after_reopen["candidate_names"]
        reopened_signature_after = _document_signature(reopened)
        if reopened_signature_after != reopened_signature_before:
            raise AssertionError("RoomResolver modifico el documento reabierto")

        result = {
            "candidate_count": len(audit["candidates"]),
            "native_priority": native_priority["object_name"],
            "legacy_fallback": legacy_fallback["object_name"],
            "ambiguous_count": len(ambiguous["alternatives"]),
            "hvac_base_space": hvac_result["object_name"],
            "converted_hvac": converted_result["status"],
            "subarea": subarea_result["status"],
            "object_resolution": object_result["object_name"],
            "object_count": object_count_before,
            "read_only_signature": True,
            "reopen_stable": True,
        }
        print("ROOM_RESOLVER_FREECAD_SMOKE_OK", json.dumps(result, sort_keys=True))
    finally:
        _close_smoke_documents(output_path)
        if os.path.isfile(output_path):
            os.remove(output_path)


if __name__ == "__main__":
    main()
