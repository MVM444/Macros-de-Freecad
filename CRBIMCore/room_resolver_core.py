"""Pure, JSON-compatible room identity resolution.

This module deliberately has no dependency on FreeCAD, FreeCADGui, Qt, Draft,
Arch, or any discipline workbench.  Adapters must translate document objects to
candidate dictionaries before calling this core.
"""

from __future__ import annotations

import math


SCHEMA_VERSION = 1
STATUS_RESOLVED = "RESOLVED"
STATUS_AMBIGUOUS = "AMBIGUOUS"
STATUS_NOT_FOUND = "NOT_FOUND"
SOURCE_NATIVE_SPACE = "NATIVE_SPACE"
SOURCE_LEGACY_AREA = "LEGACY_AREA"
SOURCE_PRIORITY = (SOURCE_NATIVE_SPACE, SOURCE_LEGACY_AREA)
EPSILON = 1.0e-9


def _text(value):
    return str(value or "").strip()


def _point(value):
    if value is None or len(value) < 2:
        raise ValueError("Cada punto debe contener X e Y")
    return float(value[0]), float(value[1])


def normalize_polygon(points):
    """Return a non-repeated open polygon represented by JSON-compatible lists."""
    cleaned = []
    for value in list(points or []):
        point = _point(value)
        if not cleaned or not _same_point(cleaned[-1], point):
            cleaned.append(point)
    if len(cleaned) > 1 and _same_point(cleaned[0], cleaned[-1]):
        cleaned.pop()
    if len(cleaned) < 3:
        raise ValueError("El contorno no contiene tres vertices distintos")
    area_magnitude, _centroid = polygon_area_centroid(cleaned)
    if area_magnitude <= EPSILON:
        raise ValueError("El contorno tiene area cero")
    return [[float(x), float(y)] for x, y in cleaned]


def _same_point(first, second, tolerance=EPSILON):
    return (
        abs(float(first[0]) - float(second[0])) <= float(tolerance)
        and abs(float(first[1]) - float(second[1])) <= float(tolerance)
    )


def polygon_area_centroid(points):
    """Return absolute area in mm2 and centroid in mm for an open polygon."""
    vertices = [_point(point) for point in list(points or [])]
    if len(vertices) < 3:
        return 0.0, [0.0, 0.0]
    cross_sum = 0.0
    cx_sum = 0.0
    cy_sum = 0.0
    for index, first in enumerate(vertices):
        second = vertices[(index + 1) % len(vertices)]
        cross = first[0] * second[1] - second[0] * first[1]
        cross_sum += cross
        cx_sum += (first[0] + second[0]) * cross
        cy_sum += (first[1] + second[1]) * cross
    signed_area = cross_sum * 0.5
    if abs(signed_area) <= EPSILON:
        return 0.0, [0.0, 0.0]
    factor = 1.0 / (6.0 * signed_area)
    return abs(signed_area), [cx_sum * factor, cy_sum * factor]


def _distance_to_segment(point, first, second):
    px, py = _point(point)
    ax, ay = _point(first)
    bx, by = _point(second)
    vx, vy = bx - ax, by - ay
    length_sq = vx * vx + vy * vy
    if length_sq <= EPSILON:
        return math.hypot(px - ax, py - ay)
    parameter = ((px - ax) * vx + (py - ay) * vy) / length_sq
    parameter = max(0.0, min(1.0, parameter))
    closest_x = ax + parameter * vx
    closest_y = ay + parameter * vy
    return math.hypot(px - closest_x, py - closest_y)


def point_in_polygon(point_mm, polygon_mm, tolerance_mm=1.0):
    """Return True when an XY point is inside or on the polygon boundary."""
    point = _point(point_mm)
    polygon = [_point(value) for value in list(polygon_mm or [])]
    if len(polygon) < 3:
        return False
    tolerance = max(0.0, float(tolerance_mm))
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        if _distance_to_segment(point, first, second) <= tolerance:
            return True
    x, y = point
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current[1] > y) != (previous[1] > y):
            denominator = previous[1] - current[1]
            if abs(denominator) > EPSILON:
                crossing_x = current[0] + (
                    (y - current[1]) * (previous[0] - current[0]) / denominator
                )
                if x < crossing_x:
                    inside = not inside
        previous = current
    return inside


def normalize_candidate(candidate):
    """Validate and normalize one adapter candidate without retaining object refs."""
    record = dict(candidate or {})
    source_kind = _text(record.get("source_kind")).upper()
    if source_kind not in SOURCE_PRIORITY:
        raise ValueError("source_kind no soportado: %s" % source_kind)
    polygon = normalize_polygon(record.get("polygon_mm") or [])
    area_mm2, centroid = polygon_area_centroid(polygon)
    diagnostics = [str(value) for value in list(record.get("diagnostics") or [])]
    confidence = float(record.get("confidence", 1.0 if source_kind == SOURCE_NATIVE_SPACE else 0.5))
    confidence = max(0.0, min(1.0, confidence))
    return {
        "schema_version": SCHEMA_VERSION,
        "source_kind": source_kind,
        "room_uid": _text(record.get("room_uid")),
        "room_id": _text(record.get("room_id")),
        "name": _text(record.get("name")),
        "object_name": _text(record.get("object_name")),
        "level": _text(record.get("level")),
        "area_m2": float(area_mm2) / 1000000.0,
        "centroid_mm": [float(centroid[0]), float(centroid[1])],
        "polygon_mm": polygon,
        "confidence": confidence,
        "is_native_space": source_kind == SOURCE_NATIVE_SPACE,
        "is_legacy": source_kind == SOURCE_LEGACY_AREA,
        "diagnostics": diagnostics,
    }


def normalize_candidates(candidates):
    result = []
    seen = set()
    for candidate in list(candidates or []):
        normalized = normalize_candidate(candidate)
        identity = (normalized["source_kind"], normalized["object_name"])
        if identity in seen:
            continue
        seen.add(identity)
        result.append(normalized)
    return result


def _empty_result(status, diagnostics=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "status": str(status),
        "source_kind": "",
        "room_uid": "",
        "room_id": "",
        "name": "",
        "object_name": "",
        "level": "",
        "area_m2": 0.0,
        "centroid_mm": [],
        "polygon_mm": [],
        "confidence": 0.0,
        "is_native_space": False,
        "is_legacy": False,
        "diagnostics": [str(value) for value in list(diagnostics or [])],
        "alternatives": [],
    }


def _candidate_summary(candidate):
    return {
        key: candidate[key]
        for key in (
            "source_kind",
            "room_uid",
            "room_id",
            "name",
            "object_name",
            "level",
            "area_m2",
            "centroid_mm",
            "confidence",
            "is_native_space",
            "is_legacy",
        )
    }


def _resolved(candidate, diagnostics=None):
    result = _empty_result(STATUS_RESOLVED, diagnostics)
    result.update(candidate)
    result["status"] = STATUS_RESOLVED
    result["diagnostics"] = list(candidate.get("diagnostics") or []) + list(diagnostics or [])
    result["alternatives"] = []
    return result


def _ambiguous(candidates, diagnostics=None):
    result = _empty_result(STATUS_AMBIGUOUS, diagnostics)
    result["alternatives"] = [_candidate_summary(candidate) for candidate in candidates]
    return result


def _level_scope(candidates, level):
    requested = _text(level)
    if not requested:
        return list(candidates), []
    exact = [candidate for candidate in candidates if candidate.get("level") == requested]
    if exact:
        return exact, ["LEVEL_EXACT:%s" % requested]
    unknown = [candidate for candidate in candidates if not candidate.get("level")]
    if unknown:
        return unknown, ["LEVEL_UNKNOWN_FALLBACK:%s" % requested]
    return [], ["LEVEL_MISMATCH:%s" % requested]


def _choose_by_priority(candidates, diagnostics=None):
    diagnostics = list(diagnostics or [])
    for source_kind in SOURCE_PRIORITY:
        matches = [candidate for candidate in candidates if candidate["source_kind"] == source_kind]
        if len(matches) == 1:
            if source_kind == SOURCE_NATIVE_SPACE and any(
                candidate["source_kind"] == SOURCE_LEGACY_AREA for candidate in candidates
            ):
                diagnostics.append("NATIVE_SPACE_PRIORITY_OVER_LEGACY")
            return _resolved(matches[0], diagnostics)
        if len(matches) > 1:
            diagnostics.append("MULTIPLE_%s_CANDIDATES" % source_kind)
            return _ambiguous(matches, diagnostics)
    return _empty_result(STATUS_NOT_FOUND, diagnostics + ["NO_PHYSICAL_ROOM_CANDIDATE"])


def resolve_room_for_point(candidates, point_mm, level="", tolerance_mm=1.0):
    """Resolve a room containing a point without ever choosing by smallest area."""
    normalized = normalize_candidates(candidates)
    plausible = [
        candidate
        for candidate in normalized
        if point_in_polygon(point_mm, candidate["polygon_mm"], tolerance_mm=tolerance_mm)
    ]
    scoped, diagnostics = _level_scope(plausible, level)
    if not scoped:
        reason = "POINT_OUTSIDE_ALL_CANDIDATES" if not plausible else "NO_CANDIDATE_IN_LEVEL"
        return _empty_result(STATUS_NOT_FOUND, diagnostics + [reason])
    return _choose_by_priority(scoped, diagnostics)


def resolve_room_reference(candidates, object_name):
    """Resolve an explicit candidate reference by its stable document object name."""
    target = _text(object_name)
    normalized = normalize_candidates(candidates)
    matches = [candidate for candidate in normalized if candidate["object_name"] == target]
    if len(matches) == 1:
        return _resolved(matches[0], ["EXPLICIT_OBJECT_REFERENCE"])
    if len(matches) > 1:
        return _ambiguous(matches, ["DUPLICATE_OBJECT_REFERENCE:%s" % target])
    return _empty_result(STATUS_NOT_FOUND, ["REFERENCE_NOT_A_PHYSICAL_ROOM:%s" % target])


def resolve_room_for_object(candidates, subject, tolerance_mm=1.0):
    """Resolve a pure subject descriptor by explicit reference, then by point."""
    record = dict(subject or {})
    reference = _text(record.get("reference_object_name"))
    if reference:
        return resolve_room_reference(candidates, reference)
    point_mm = record.get("point_mm")
    if point_mm is None:
        return _empty_result(STATUS_NOT_FOUND, ["OBJECT_WITHOUT_REFERENCE_OR_POINT"])
    return resolve_room_for_point(
        candidates,
        point_mm,
        level=_text(record.get("level")),
        tolerance_mm=tolerance_mm,
    )

