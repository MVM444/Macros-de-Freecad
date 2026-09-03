from __future__ import annotations

from CRBIMCore import room_operations_core as operations
from CRBIMCore import room_resolver_core as resolver


def _resolved(source=resolver.SOURCE_NATIVE_SPACE):
    return {
        "status": resolver.STATUS_RESOLVED,
        "source_kind": source,
        "object_name": "Space",
        "name": "Oficina",
        "room_uid": "uid-1",
        "room_id": "R-01",
        "level": "Level",
        "area_m2": 12.5,
        "diagnostics": [],
        "alternatives": [],
    }


def test_room_info_is_json_compatible_and_complete():
    info = operations.room_info_record(
        _resolved(),
        {"label": "Oficina 1", "base_name": "SpaceBase", "geometry_source": "Part::Feature"},
    )
    assert info == {
        "schema_version": 1,
        "status": "RESOLVED",
        "source_kind": "NATIVE_SPACE",
        "source_label": "Space",
        "object_name": "Space",
        "label": "Oficina 1",
        "area_m2": 12.5,
        "room_uid": "uid-1",
        "room_id": "R-01",
        "level": "Level",
        "base_name": "SpaceBase",
        "geometry_source": "Part::Feature",
        "diagnostics": [],
        "alternatives": [],
    }
    text = operations.format_room_info(info)
    assert "Estado: RESOLVED" in text
    assert "FA_RoomUID: uid-1" in text
    assert "Base: SpaceBase" in text


def test_area_legacy_label_is_explicit():
    info = operations.room_info_record(_resolved(resolver.SOURCE_LEGACY_AREA))
    assert info["source_label"] == "Area legacy"


def test_ambiguous_formats_candidates_without_choosing():
    info = operations.room_info_record(
        {
            "status": resolver.STATUS_AMBIGUOUS,
            "alternatives": [
                {"object_name": "Space", "source_kind": "NATIVE_SPACE"},
                {"object_name": "Space001", "source_kind": "NATIVE_SPACE"},
            ],
        }
    )
    assert info["object_name"] == ""
    assert "Space001 (NATIVE_SPACE)" in operations.format_room_info(info)


def test_label_plan_accepts_only_direct_physical_rooms():
    plan = operations.plan_label_changes(
        [
            {
                "object_name": "Space",
                "label": "Viejo",
                "source_kind": resolver.SOURCE_NATIVE_SPACE,
                "is_direct_physical_room": True,
            },
            {
                "object_name": "Area",
                "label": "Vieja",
                "source_kind": resolver.SOURCE_LEGACY_AREA,
                "is_direct_physical_room": True,
            },
            {
                "object_name": "Lamp",
                "label": "Luminaria",
                "source_kind": "",
                "is_direct_physical_room": False,
            },
        ],
        "Oficina",
    )
    assert plan["status"] == "READY"
    assert [item["object_name"] for item in plan["accepted"]] == ["Space", "Area"]
    assert plan["rejected"] == [
        {"object_name": "Lamp", "label": "Luminaria", "reason": "NOT_A_DIRECT_PHYSICAL_ROOM"}
    ]
    assert plan["changed"] == 2


def test_label_plan_rejects_empty_label_and_deduplicates():
    assert operations.plan_label_changes([], " ")["status"] == "INVALID"
    target = {
        "object_name": "Space",
        "label": "Oficina",
        "source_kind": resolver.SOURCE_NATIVE_SPACE,
        "is_direct_physical_room": True,
    }
    plan = operations.plan_label_changes([target, target], "Oficina")
    assert len(plan["accepted"]) == 1
    assert plan["changed"] == 0


def test_guide_covers_resolver_states_and_workbenches():
    text = operations.guide_text()
    assert "AMBIGUOUS" in text
    assert "NOT_FOUND" in text
    assert "Facil Arquitectura" in text
    assert "ElectricCR" in text
