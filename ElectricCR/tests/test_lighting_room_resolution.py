from CRBIMCore import room_resolver_core as core
from ElectricCR.electriccr.lighting.room_calculation import select_authoritative_rooms


def _candidate(name, source, x0=0.0, y0=0.0, x1=4000.0, y1=3000.0):
    return {
        "source_kind": source,
        "name": name,
        "object_name": name.replace(" ", "_"),
        "polygon_mm": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
        "room_uid": "UID-" + name,
        "room_id": name,
    }


def test_space_only_is_authoritative():
    result = select_authoritative_rooms([_candidate("Space A", core.SOURCE_NATIVE_SPACE)])
    assert [room["source_kind"] for room in result["rooms"]] == [core.SOURCE_NATIVE_SPACE]
    assert result["diagnostics"] == []


def test_legacy_only_keeps_existing_contract_source():
    result = select_authoritative_rooms([_candidate("Area A", core.SOURCE_LEGACY_AREA)])
    assert [room["source_kind"] for room in result["rooms"]] == [core.SOURCE_LEGACY_AREA]


def test_native_space_suppresses_overlapping_legacy_area():
    result = select_authoritative_rooms(
        [
            _candidate("Area A", core.SOURCE_LEGACY_AREA),
            _candidate("Space A", core.SOURCE_NATIVE_SPACE),
        ]
    )
    assert [room["object_name"] for room in result["rooms"]] == ["Space_A"]
    assert result["diagnostics"][0]["status"] == "SUPPRESSED"
    assert result["diagnostics"][0]["resolved_object_name"] == "Space_A"


def test_two_overlapping_spaces_are_ambiguous_and_not_selected():
    result = select_authoritative_rooms(
        [
            _candidate("Space A", core.SOURCE_NATIVE_SPACE),
            _candidate("Space B", core.SOURCE_NATIVE_SPACE),
        ]
    )
    assert result["rooms"] == []
    assert len(result["diagnostics"]) == 1
    assert result["diagnostics"][0]["status"] == core.STATUS_AMBIGUOUS


def test_empty_input_is_safe_not_found_equivalent():
    result = select_authoritative_rooms([])
    assert result["candidate_count"] == 0
    assert result["room_count"] == 0
    assert result["rooms"] == []


def test_result_is_json_compatible_and_contains_no_object_references():
    import json

    result = select_authoritative_rooms([_candidate("Space A", core.SOURCE_NATIVE_SPACE)])
    encoded = json.dumps(result, sort_keys=True)
    assert "Space_A" in encoded
