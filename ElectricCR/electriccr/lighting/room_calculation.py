"""Read-only RoomResolver adoption for ElectricCR lighting calculations.

The module deliberately returns JSON-compatible records.  It never creates,
moves, renames, links, or edits FreeCAD objects.  The legacy lighting macro is
responsible for preserving its spreadsheet and layout-property contracts.
"""

from __future__ import annotations

from CRBIMCore import room_resolver_core as room_core


def _text(value):
    return str(value or "").strip()


def _diagnostic_key(result):
    alternatives = tuple(
        sorted(
            _text(item.get("object_name"))
            for item in list(result.get("alternatives") or [])
            if _text(item.get("object_name"))
        )
    )
    return result.get("status"), alternatives, tuple(result.get("diagnostics") or [])


def select_authoritative_rooms(candidates):
    """Select one physical room identity per footprint using RoomResolver.

    Each candidate is resolved at its own centroid.  A native Space therefore
    suppresses a superposed legacy Area through the common resolver priority.
    Ambiguous candidates are excluded instead of choosing silently.
    """
    normalized = room_core.normalize_candidates(candidates)
    selected = []
    diagnostics = []
    seen_diagnostics = set()

    for candidate in normalized:
        result = room_core.resolve_room_for_point(
            normalized,
            candidate["centroid_mm"],
            level=candidate.get("level", ""),
        )
        status = result.get("status")
        if status == room_core.STATUS_RESOLVED:
            resolved_name = _text(result.get("object_name"))
            if resolved_name == candidate["object_name"]:
                selected.append(dict(candidate))
            else:
                diagnostics.append(
                    {
                        "status": "SUPPRESSED",
                        "object_name": candidate["object_name"],
                        "source_kind": candidate["source_kind"],
                        "reason": "RESOLVED_TO_HIGHER_PRIORITY_ROOM",
                        "resolved_object_name": resolved_name,
                    }
                )
            continue

        key = _diagnostic_key(result)
        if key in seen_diagnostics:
            continue
        seen_diagnostics.add(key)
        diagnostics.append(
            {
                "status": status or room_core.STATUS_NOT_FOUND,
                "object_name": candidate["object_name"],
                "source_kind": candidate["source_kind"],
                "reason": ";".join(result.get("diagnostics") or []),
                "alternatives": list(result.get("alternatives") or []),
            }
        )

    selected.sort(
        key=lambda item: (
            _text(item.get("level")).casefold(),
            _text(item.get("name")).casefold(),
            _text(item.get("object_name")).casefold(),
        )
    )
    return {
        "schema_version": 1,
        "rooms": selected,
        "diagnostics": diagnostics,
        "candidate_count": len(normalized),
        "room_count": len(selected),
    }


def collect_lighting_rooms(doc, legacy_object_names=None):
    """Collect authoritative rooms from a FreeCAD document without mutation.

    ``legacy_object_names`` optionally restricts only legacy Areas to the group
    selected by the existing UI.  Native Spaces remain architectural sources
    regardless of their Building/Level container.
    """
    from CRBIMCore.freecad_room_adapter import collect_room_candidates

    collection = collect_room_candidates(doc, include_legacy=True)
    candidates = list(collection.get("candidates") or [])
    if legacy_object_names is not None:
        allowed = {_text(value) for value in legacy_object_names if _text(value)}
        candidates = [
            candidate
            for candidate in candidates
            if candidate.get("source_kind") != room_core.SOURCE_LEGACY_AREA
            or candidate.get("object_name") in allowed
        ]

    result = select_authoritative_rooms(candidates)
    result["adapter_diagnostics"] = list(collection.get("diagnostics") or [])
    return result


__all__ = ["collect_lighting_rooms", "select_authoritative_rooms"]
