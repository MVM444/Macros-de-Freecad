"""Pure regression tests for RoomResolver phase 1."""

import importlib
import json
import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _core():
    return importlib.import_module("CRBIMCore.room_resolver_core")


def _candidate(name, kind, x0, y0, x1, y1, level="", **extra):
    record = {
        "source_kind": kind,
        "object_name": name,
        "name": extra.pop("name", name),
        "level": level,
        "polygon_mm": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
        "confidence": extra.pop("confidence", 1.0 if kind == "NATIVE_SPACE" else 0.8),
    }
    record.update(extra)
    return record


def test_core_imports_without_freecad_modules():
    core = _core()
    source_names = set(core.__dict__)
    assert "FreeCAD" not in source_names
    assert "FreeCADGui" not in source_names
    assert "PySide" not in source_names


def test_native_space_wins_over_overlapping_legacy_area():
    core = _core()
    candidates = [
        _candidate("Space", "NATIVE_SPACE", 0, 0, 4000, 3000, room_uid="UID-1"),
        _candidate("Area001", "LEGACY_AREA", 0, 0, 4000, 3000),
    ]
    result = core.resolve_room_for_point(candidates, [1000, 1000])
    assert result["status"] == "RESOLVED"
    assert result["source_kind"] == "NATIVE_SPACE"
    assert result["object_name"] == "Space"
    assert "NATIVE_SPACE_PRIORITY_OVER_LEGACY" in result["diagnostics"]


def test_manual_native_space_without_fa_metadata_is_valid():
    core = _core()
    candidate = _candidate("ManualSpace", "NATIVE_SPACE", 0, 0, 2000, 2000)
    result = core.resolve_room_for_point([candidate], [500, 500])
    assert result["status"] == "RESOLVED"
    assert result["room_uid"] == ""
    assert result["room_id"] == ""
    assert result["is_native_space"] is True


def test_legacy_area_is_fallback_when_no_native_space_exists():
    core = _core()
    candidate = _candidate("AreaClick", "LEGACY_AREA", 0, 0, 2000, 1500, confidence=0.76)
    result = core.resolve_room_for_point([candidate], [1000, 500])
    assert result["status"] == "RESOLVED"
    assert result["source_kind"] == "LEGACY_AREA"
    assert result["is_legacy"] is True
    assert abs(result["confidence"] - 0.76) < 1.0e-9


def test_rectangular_analysis_is_a_normal_legacy_candidate():
    core = _core()
    candidate = _candidate(
        "RectangleAnalysis", "LEGACY_AREA", 5000, 0, 9000, 3000, room_id="FA_001"
    )
    result = core.resolve_room_reference([candidate], "RectangleAnalysis")
    assert result["status"] == "RESOLVED"
    assert result["room_id"] == "FA_001"


def test_two_plausible_native_spaces_are_ambiguous_not_smallest_wins():
    core = _core()
    candidates = [
        _candidate("SpaceLarge", "NATIVE_SPACE", 0, 0, 4000, 4000),
        _candidate("SpaceSmall", "NATIVE_SPACE", 500, 500, 2000, 2000),
    ]
    result = core.resolve_room_for_point(candidates, [1000, 1000])
    assert result["status"] == "AMBIGUOUS"
    assert {item["object_name"] for item in result["alternatives"]} == {
        "SpaceLarge",
        "SpaceSmall",
    }


def test_not_found_is_normal_json_compatible_result():
    core = _core()
    result = core.resolve_room_for_point([], [123, 456])
    assert result["status"] == "NOT_FOUND"
    assert result["object_name"] == ""
    json.dumps(result, sort_keys=True)


def test_explicit_reference_resolves_legacy_without_geometry_ranking():
    core = _core()
    candidates = [
        _candidate("Space", "NATIVE_SPACE", 0, 0, 4000, 3000),
        _candidate("Area", "LEGACY_AREA", 0, 0, 4000, 3000),
    ]
    result = core.resolve_room_reference(candidates, "Area")
    assert result["status"] == "RESOLVED"
    assert result["source_kind"] == "LEGACY_AREA"
    assert "EXPLICIT_OBJECT_REFERENCE" in result["diagnostics"]


def test_object_descriptor_prefers_reference_then_supports_point():
    core = _core()
    candidates = [_candidate("Space", "NATIVE_SPACE", 0, 0, 4000, 3000)]
    linked = core.resolve_room_for_object(
        candidates, {"reference_object_name": "Space", "point_mm": [9999, 9999]}
    )
    spatial = core.resolve_room_for_object(candidates, {"point_mm": [1000, 1000]})
    assert linked["status"] == "RESOLVED"
    assert spatial["status"] == "RESOLVED"


def test_level_can_disambiguate_but_unknown_level_never_overrides_exact():
    core = _core()
    candidates = [
        _candidate("SpaceL1", "NATIVE_SPACE", 0, 0, 4000, 3000, level="Level1"),
        _candidate("SpaceL2", "NATIVE_SPACE", 0, 0, 4000, 3000, level="Level2"),
        _candidate("AreaUnknown", "LEGACY_AREA", 0, 0, 4000, 3000),
    ]
    result = core.resolve_room_for_point(candidates, [1000, 1000], level="Level2")
    assert result["status"] == "RESOLVED"
    assert result["object_name"] == "SpaceL2"
    assert "LEVEL_EXACT:Level2" in result["diagnostics"]


def test_candidate_metrics_are_recomputed_from_polygon():
    core = _core()
    candidate = _candidate("Space", "NATIVE_SPACE", 0, 0, 4000, 3000)
    candidate["area_m2"] = 999.0
    candidate["centroid_mm"] = [99, 99]
    normalized = core.normalize_candidate(candidate)
    assert abs(normalized["area_m2"] - 12.0) < 1.0e-9
    assert normalized["centroid_mm"] == [2000.0, 1500.0]


if __name__ == "__main__":
    namespace = globals()
    names = sorted(name for name in namespace if name.startswith("test_") and callable(namespace[name]))
    for name in names:
        namespace[name]()
    print("ROOM_RESOLVER_CORE_TESTS_OK", len(names))
