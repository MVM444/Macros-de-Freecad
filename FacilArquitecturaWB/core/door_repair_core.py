"""Pure planning core for FA door repairs.

Name: door_repair_core.py
Purpose: diagnose and plan deterministic repairs for BIM doors whose native
outer frame no longer lies inside the effective opening ("buque").
Main behavior: supports the current contract where the Sketch segment is the
complete buque and a controlled legacy contract where historical FA metadata
stores the leaf segment; preserves Width whenever the complete frame fits and
resizes only when it truly exceeds the effective buque.
Maintenance: keep this module FreeCAD/FreeCADGui/Qt independent and JSON
compatible. Do not add document mutations here. Preserve explicit user choice
of opening semantics over automatic inference.
Version: 0.6.0
Date/time: 2026-09-03 15:05 America/Costa_Rica
"""

from __future__ import annotations

import math

CORE_VERSION = "0.6.0"
DEFAULT_TOLERANCE_MM = 2.0

OPENING_SEMANTIC_AUTO = "AUTO"
OPENING_SEMANTIC_BUQUE = "BUQUE_COMPLETE"
OPENING_SEMANTIC_LEGACY_LEAF = "LEGACY_LEAF"
_OPENING_SEMANTICS = {
    OPENING_SEMANTIC_AUTO,
    OPENING_SEMANTIC_BUQUE,
    OPENING_SEMANTIC_LEGACY_LEAF,
}


def _point2(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return (float(value.get("x", 0.0)), float(value.get("y", 0.0)))
    seq = list(value)
    if len(seq) < 2:
        raise ValueError("point requires at least x and y")
    return (float(seq[0]), float(seq[1]))


def _distance(a, b):
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def endpoint_match_error(authoritative_first, authoritative_second, leaf_first, leaf_second):
    """Return the smallest max endpoint error, allowing reversed segment direction."""
    a = _point2(authoritative_first)
    b = _point2(authoritative_second)
    c = _point2(leaf_first)
    d = _point2(leaf_second)
    if None in (a, b, c, d):
        raise ValueError("all four endpoints are required")
    direct = max(_distance(a, c), _distance(b, d))
    reverse = max(_distance(a, d), _distance(b, c))
    if direct <= reverse:
        return {"error_mm": direct, "reversed": False}
    return {"error_mm": reverse, "reversed": True}


def _dot(a, b):
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1])


def _normalize_semantic(value):
    text = str(value or OPENING_SEMANTIC_AUTO).strip().upper()
    aliases = {
        "AUTO": OPENING_SEMANTIC_AUTO,
        "BUQUE": OPENING_SEMANTIC_BUQUE,
        "BUQUE_COMPLETO": OPENING_SEMANTIC_BUQUE,
        "BUQUE_COMPLETE": OPENING_SEMANTIC_BUQUE,
        "COMPLETE_BUQUE": OPENING_SEMANTIC_BUQUE,
        "LEGACY": OPENING_SEMANTIC_LEGACY_LEAF,
        "HOJA_HEREDADA": OPENING_SEMANTIC_LEGACY_LEAF,
        "LEGACY_LEAF": OPENING_SEMANTIC_LEGACY_LEAF,
        "LEAF": OPENING_SEMANTIC_LEGACY_LEAF,
    }
    normalized = aliases.get(text, text)
    if normalized not in _OPENING_SEMANTICS:
        raise ValueError("unsupported opening semantic: %s" % value)
    return normalized


def _axis(authoritative_first, authoritative_second):
    a = _point2(authoritative_first)
    b = _point2(authoritative_second)
    if a is None or b is None:
        raise ValueError("authoritative endpoints are required")
    vx, vy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(vx, vy)
    if length <= 1e-9:
        raise ValueError("authoritative opening has zero length")
    return a, b, length, (vx / length, vy / length)


def infer_opening_semantic(record, tolerance_mm=DEFAULT_TOLERANCE_MM):
    """Infer legacy metadata only when its numeric signature is explicit.

    Historical FA BOUNDED doors stored FA_ProjectedFirst/Second as the leaf
    segment while native Width was leaf + Frame2 + Frame3. A close equality to
    that signature is considered a legacy candidate. Explicit metadata hints,
    when present, take precedence over the numeric heuristic.
    """
    tolerance = max(0.0, float(tolerance_mm))
    hint = str(record.get("opening_semantic_hint") or "").strip()
    if hint:
        try:
            hinted = _normalize_semantic(hint)
        except ValueError:
            hinted = OPENING_SEMANTIC_AUTO
        if hinted != OPENING_SEMANTIC_AUTO:
            return {
                "semantic": hinted,
                "reason": "explicit metadata hint",
                "legacy_signature_error_mm": None,
            }

    _a, _b, source_length, _u = _axis(
        record.get("authoritative_first"), record.get("authoritative_second")
    )
    outer_width = float(record.get("outer_width_mm") or 0.0)
    frame_start = float(record.get("frame_start_mm") or 0.0)
    frame_end = float(record.get("frame_end_mm") or 0.0)
    expected_legacy_width = source_length + frame_start + frame_end
    signature_error = abs(outer_width - expected_legacy_width) if outer_width > 0.0 else float("inf")
    signature_tolerance = max(tolerance, 0.5)
    if (
        outer_width > 0.0
        and frame_start >= 0.0
        and frame_end >= 0.0
        and (frame_start + frame_end) > tolerance
        and signature_error <= signature_tolerance
    ):
        return {
            "semantic": OPENING_SEMANTIC_LEGACY_LEAF,
            "reason": "legacy signature: Width ~= projected segment + Frame2 + Frame3",
            "legacy_signature_error_mm": signature_error,
        }
    return {
        "semantic": OPENING_SEMANTIC_BUQUE,
        "reason": "no legacy signature; use current complete-buque contract",
        "legacy_signature_error_mm": signature_error if math.isfinite(signature_error) else None,
    }


def resolve_effective_opening(record, opening_semantic=OPENING_SEMANTIC_AUTO, tolerance_mm=DEFAULT_TOLERANCE_MM):
    """Return the effective complete-buque endpoints for planning.

    BUQUE_COMPLETE: FA_ProjectedFirst/Second already delimit the complete buque.
    LEGACY_LEAF: historical projected endpoints delimit the leaf; expand the
    segment by Frame2 at the first end and Frame3 at the second end.
    AUTO: use explicit metadata hint or the historical numeric signature.
    """
    requested = _normalize_semantic(opening_semantic)
    detected = infer_opening_semantic(record, tolerance_mm=tolerance_mm)
    used = detected["semantic"] if requested == OPENING_SEMANTIC_AUTO else requested

    a, b, source_length, (ux, uy) = _axis(
        record.get("authoritative_first"), record.get("authoritative_second")
    )
    frame_start = max(0.0, float(record.get("frame_start_mm") or 0.0))
    frame_end = max(0.0, float(record.get("frame_end_mm") or 0.0))

    if used == OPENING_SEMANTIC_LEGACY_LEAF:
        first = (a[0] - frame_start * ux, a[1] - frame_start * uy)
        second = (b[0] + frame_end * ux, b[1] + frame_end * uy)
        reason = "historical leaf segment expanded by Frame2/Frame3 to recover complete buque"
    else:
        first, second = a, b
        reason = "projected segment used directly as complete buque"

    return {
        "requested_semantic": requested,
        "detected_semantic": detected["semantic"],
        "used_semantic": used,
        "detection_reason": detected["reason"],
        "resolution_reason": reason,
        "legacy_signature_error_mm": detected.get("legacy_signature_error_mm"),
        "source_first": a,
        "source_second": b,
        "effective_first": first,
        "effective_second": second,
        "source_length_mm": source_length,
        "effective_length_mm": _distance(first, second),
        "frame_start_mm": frame_start,
        "frame_end_mm": frame_end,
    }


def opening_fit_metrics(authoritative_first, authoritative_second, frame_first, frame_second):
    """Measure containment of the outer frame inside the opening segment."""
    a = _point2(authoritative_first)
    b = _point2(authoritative_second)
    c = _point2(frame_first)
    d = _point2(frame_second)
    if None in (a, b, c, d):
        raise ValueError("all four endpoints are required")
    vx, vy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(vx, vy)
    if length <= 1e-9:
        raise ValueError("authoritative opening has zero length")
    ux, uy = vx / length, vy / length
    nx, ny = -uy, ux

    def coords(p):
        rel = (p[0] - a[0], p[1] - a[1])
        return (_dot(rel, (ux, uy)), _dot(rel, (nx, ny)))

    tc, pc = coords(c)
    td, pd = coords(d)
    left, right = min(tc, td), max(tc, td)
    return {
        "opening_length_mm": length,
        "frame_left_mm": left,
        "frame_right_mm": right,
        "projected_frame_width_mm": max(0.0, right - left),
        "perpendicular_offset_mm": 0.5 * (pc + pd),
        "parallel_error_mm": abs(pd - pc),
        "overflow_start_mm": max(0.0, -left),
        "overflow_end_mm": max(0.0, right - length),
        "direction_sign": 1.0 if td >= tc else -1.0,
        "axis_unit": (ux, uy),
        "normal_unit": (nx, ny),
    }


def plan_door_repair(record, tolerance_mm=DEFAULT_TOLERANCE_MM, opening_semantic=OPENING_SEMANTIC_AUTO):
    """Preserve Width if the frame fits; resize only when wider than effective buque."""
    tolerance = max(0.0, float(tolerance_mm))
    result = {
        "door_name": str(record.get("door_name") or ""),
        "status": "UNSUPPORTED",
        "repairable": False,
        "needs_repair": False,
        "reason": "",
        "error_mm": None,
        "action": None,
        "core_version": CORE_VERSION,
        "opening_semantic": None,
    }
    try:
        opening = resolve_effective_opening(
            record, opening_semantic=opening_semantic, tolerance_mm=tolerance
        )
        metrics = opening_fit_metrics(
            opening["effective_first"],
            opening["effective_second"],
            record.get("frame_first"),
            record.get("frame_second"),
        )
    except Exception as exc:
        result["reason"] = "missing or invalid geometry: %s" % exc
        return result

    result["opening_semantic"] = opening["used_semantic"]
    result["opening_semantic_requested"] = opening["requested_semantic"]
    result["opening_semantic_detected"] = opening["detected_semantic"]
    result["opening_semantic_reason"] = opening["detection_reason"]
    result["source_opening_length_mm"] = float(opening["source_length_mm"])
    result["effective_opening_length_mm"] = float(opening["effective_length_mm"])

    opening_length = float(metrics["opening_length_mm"])
    current_width = float(record.get("outer_width_mm") or 0.0)
    if current_width <= 0.0:
        current_width = float(metrics["projected_frame_width_mm"])
    frame_start = float(record.get("frame_start_mm") or 0.0)
    frame_end = float(record.get("frame_end_mm") or 0.0)
    if current_width <= 0.0 or frame_start < 0.0 or frame_end < 0.0:
        result.update(status="OUTSIDE_BUQUE_UNSUPPORTED", reason="invalid native frame width or frame margins")
        return result

    outside_error = max(
        float(metrics["overflow_start_mm"]),
        float(metrics["overflow_end_mm"]),
        abs(float(metrics["perpendicular_offset_mm"])),
        float(metrics["parallel_error_mm"]),
    )
    result["error_mm"] = outside_error
    fits = current_width <= opening_length + tolerance
    inside = (
        metrics["overflow_start_mm"] <= tolerance
        and metrics["overflow_end_mm"] <= tolerance
        and abs(metrics["perpendicular_offset_mm"]) <= tolerance
        and metrics["parallel_error_mm"] <= tolerance
        and fits
    )
    if inside:
        result.update(
            status="OK",
            reason="complete native outer frame already lies inside effective opening",
        )
        return result

    result["needs_repair"] = True
    if str(record.get("corner_status") or "").strip().upper() != "BOUNDED":
        result.update(
            status="OUTSIDE_BUQUE_UNSUPPORTED",
            reason="phase 1 only repairs deterministic BOUNDED doors",
        )
        return result
    if metrics["parallel_error_mm"] > tolerance:
        result.update(
            status="OUTSIDE_BUQUE_UNSUPPORTED",
            reason="native frame is not parallel to effective opening",
        )
        return result

    ux, uy = metrics["axis_unit"]
    nx, ny = metrics["normal_unit"]
    perp = float(metrics["perpendicular_offset_mm"])
    resize = not fits
    target_width = opening_length if resize else current_width

    if resize:
        frame_first = _point2(record.get("frame_first"))
        target = (
            _point2(opening["effective_first"])
            if metrics["direction_sign"] >= 0.0
            else _point2(opening["effective_second"])
        )
        shift_x = target[0] - frame_first[0]
        shift_y = target[1] - frame_first[1]
        mode = "resize_and_move"
        reason = "outer frame is wider than effective opening; reduce Width and place frame inside buque"
    else:
        shift_x, shift_y = -perp * nx, -perp * ny
        left, right = float(metrics["frame_left_mm"]), float(metrics["frame_right_mm"])
        along = 0.0
        if left < -tolerance:
            along = -left
        elif right > opening_length + tolerance:
            along = opening_length - right
        shift_x += along * ux
        shift_y += along * uy
        mode = "move_only"
        reason = "outer frame fits effective opening; preserve Width and move complete frame inside buque"

    result.update(
        {
            "status": "OUTSIDE_BUQUE_REPAIRABLE",
            "repairable": True,
            "reason": reason,
            "action": {
                "mode": mode,
                "resize_required": resize,
                "origin_shift_mm": math.hypot(shift_x, shift_y),
                "shift_vector_xy_mm": (shift_x, shift_y),
                "current_outer_width_mm": current_width,
                "target_outer_width_mm": target_width,
                "outer_width_mm": target_width,
                "opening_length_mm": opening_length,
                "source_opening_length_mm": float(opening["source_length_mm"]),
                "effective_opening_length_mm": float(opening["effective_length_mm"]),
                "opening_semantic": opening["used_semantic"],
                "opening_semantic_requested": opening["requested_semantic"],
                "opening_semantic_detected": opening["detected_semantic"],
                "opening_semantic_reason": opening["detection_reason"],
                "frame_start_mm": frame_start,
                "frame_end_mm": frame_end,
                "clear_leaf_width_mm": max(0.0, target_width - frame_start - frame_end),
                "overflow_start_mm": float(metrics["overflow_start_mm"]),
                "overflow_end_mm": float(metrics["overflow_end_mm"]),
                "perpendicular_offset_mm": perp,
                "measured_before_error_mm": outside_error,
            },
        }
    )
    return result



def plan_jamb_alignment(record, jamb_point, tolerance_mm=DEFAULT_TOLERANCE_MM, frame_endpoint=None):
    """Plan a user-guided move that aligns one outer-frame end to a selected jamb.

    The selected jamb is authoritative. This planner never resizes the door: it
    preserves native ``Width`` and translates the Base so the chosen outer-frame
    endpoint coincides with the jamb in XY. When ``frame_endpoint`` is omitted,
    the nearest current frame endpoint is chosen deterministically (first wins a
    tie). Pass ``first`` or ``second`` during post-apply verification to lock the
    same endpoint used by the original plan.
    """
    tolerance = max(0.0, float(tolerance_mm))
    result = {
        "door_name": str(record.get("door_name") or ""),
        "status": "UNSUPPORTED",
        "repairable": False,
        "needs_repair": False,
        "reason": "",
        "error_mm": None,
        "action": None,
        "core_version": CORE_VERSION,
    }
    try:
        jamb = _point2(jamb_point)
        first = _point2(record.get("frame_first"))
        second = _point2(record.get("frame_second"))
        if None in (jamb, first, second):
            raise ValueError("jamb and both frame endpoints are required")
    except Exception as exc:
        result["reason"] = "missing or invalid jamb geometry: %s" % exc
        return result

    requested = str(frame_endpoint or "").strip().lower()
    if requested and requested not in {"first", "second"}:
        result["reason"] = "frame_endpoint must be 'first' or 'second'"
        return result

    distance_first = _distance(first, jamb)
    distance_second = _distance(second, jamb)
    endpoint = requested or ("first" if distance_first <= distance_second else "second")
    source = first if endpoint == "first" else second
    error = _distance(source, jamb)
    shift_x = float(jamb[0]) - float(source[0])
    shift_y = float(jamb[1]) - float(source[1])
    width = float(record.get("outer_width_mm") or _distance(first, second))

    result.update(
        {
            "frame_endpoint": endpoint,
            "jamb_point_xy_mm": jamb,
            "distance_first_mm": distance_first,
            "distance_second_mm": distance_second,
            "error_mm": error,
        }
    )
    if error <= tolerance:
        result.update(
            status="OK",
            reason="selected outer-frame endpoint already coincides with selected jamb",
        )
        return result

    result.update(
        {
            "status": "JAMB_ALIGNMENT_REPAIRABLE",
            "repairable": True,
            "needs_repair": True,
            "reason": "preserve Width and move selected outer-frame endpoint to selected jamb",
            "action": {
                "mode": "align_to_jamb",
                "resize_required": False,
                "frame_endpoint": endpoint,
                "jamb_point_xy_mm": jamb,
                "shift_vector_xy_mm": (shift_x, shift_y),
                "origin_shift_mm": error,
                "current_outer_width_mm": width,
                "target_outer_width_mm": width,
                "outer_width_mm": width,
                "frame_start_mm": float(record.get("frame_start_mm") or 0.0),
                "frame_end_mm": float(record.get("frame_end_mm") or 0.0),
                "measured_before_error_mm": error,
            },
        }
    )
    return result
