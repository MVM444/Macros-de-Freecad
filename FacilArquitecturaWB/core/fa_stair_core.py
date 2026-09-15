"""
FA Stair Between Slabs - independent planning core.

Purpose:
    Plan an L/angled stair from one three-point path and two floor elevations.
Main behavior:
    Splits one plan path into lower flight + corner landing + upper flight,
    chooses a practical riser distribution, and returns JSON-compatible data.
Maintenance:
    Keep this module independent from FreeCAD, FreeCADGui and Qt.
    FreeCAD object creation belongs in the .FCMacro adapter.
Version: 0.3.0
Date: 2026-09-14 20:00 America/Costa_Rica
"""

from __future__ import annotations
import math


class StairPlanError(ValueError):
    pass


def _point3(value):
    if len(value) < 2:
        raise StairPlanError("Cada punto necesita por lo menos X e Y.")
    return (float(value[0]), float(value[1]), float(value[2]) if len(value) > 2 else 0.0)


def _length_xy(a, b):
    return math.hypot(float(b[0]) - float(a[0]), float(b[1]) - float(a[1]))


def _unit_xy(a, b):
    length = _length_xy(a, b)
    if length <= 1e-9:
        raise StairPlanError("El Wire contiene un tramo de longitud cero.")
    return ((float(b[0]) - float(a[0])) / length, (float(b[1]) - float(a[1])) / length)


def _turn_angle_deg(p0, p1, p2):
    d1 = _unit_xy(p0, p1)
    d2 = _unit_xy(p1, p2)
    dot = max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1]))
    return math.degrees(math.acos(dot))


def _candidate_score(total_h, target_riser, run1, run2, total_risers, n1):
    n2 = total_risers - n1
    if n1 < 2 or n2 < 2:
        return None
    riser = total_h / total_risers
    tread1 = run1 / (n1 - 1)
    tread2 = run2 / (n2 - 1)
    blondel1 = 2.0 * riser + tread1
    blondel2 = 2.0 * riser + tread2

    score = (
        abs(riser - target_riser) * 1.25
        + abs(tread1 - tread2) * 0.85
        + abs(blondel1 - 630.0) * 0.45
        + abs(blondel2 - 630.0) * 0.45
    )
    if riser < 130.0:
        score += (130.0 - riser) * 8.0
    if riser > 205.0:
        score += (riser - 205.0) * 12.0
    if tread1 < 220.0:
        score += (220.0 - tread1) * 10.0
    if tread2 < 220.0:
        score += (220.0 - tread2) * 10.0
    if tread1 > 420.0:
        score += (tread1 - 420.0) * 4.0
    if tread2 > 420.0:
        score += (tread2 - 420.0) * 4.0

    return {
        "score": score,
        "total_risers": int(total_risers),
        "flight1_risers": int(n1),
        "flight2_risers": int(n2),
        "riser_mm": float(riser),
        "tread1_mm": float(tread1),
        "tread2_mm": float(tread2),
        "blondel1_mm": float(blondel1),
        "blondel2_mm": float(blondel2),
    }


def plan_angled_stair(
    points,
    lower_top_z,
    upper_top_z,
    width_mm=1000.0,
    target_riser_mm=175.0,
    landing_depth_mm=None,
):
    if len(points) != 3:
        raise StairPlanError("Se requieren exactamente tres puntos: inicio, angulo y llegada.")

    p0, p1, p2 = [_point3(p) for p in points]
    z0 = float(lower_top_z)
    z1 = float(upper_top_z)
    width = float(width_mm)
    target_riser = float(target_riser_mm)
    landing_depth = float(landing_depth_mm if landing_depth_mm is not None else width)

    if z1 <= z0 + 1e-6:
        raise StairPlanError("La losa superior debe estar por encima de la losa inferior.")
    if width <= 200.0:
        raise StairPlanError("El ancho de escalera es demasiado pequeno.")
    if target_riser <= 50.0:
        raise StairPlanError("La contrahuella objetivo es invalida.")
    if landing_depth <= 0.0:
        raise StairPlanError("La profundidad del descanso debe ser positiva.")

    len1 = _length_xy(p0, p1)
    len2 = _length_xy(p1, p2)
    angle = _turn_angle_deg(p0, p1, p2)

    if angle < 20.0 or angle > 160.0:
        raise StairPlanError(
            "Los dos tramos del Wire son casi colineales. "
            "Esta version requiere una escalera realmente en angulo."
        )

    half_landing = landing_depth / 2.0
    min_remaining_run = 500.0
    if len1 <= half_landing + min_remaining_run or len2 <= half_landing + min_remaining_run:
        raise StairPlanError(
            "Uno de los tramos del Wire es demasiado corto para el descanso y la escalera."
        )

    d1 = _unit_xy(p0, p1)
    d2 = _unit_xy(p1, p2)
    landing_start_xy = (p1[0] - d1[0] * half_landing, p1[1] - d1[1] * half_landing)
    landing_end_xy = (p1[0] + d2[0] * half_landing, p1[1] + d2[1] * half_landing)

    run1 = _length_xy(p0, landing_start_xy)
    run2 = _length_xy(landing_end_xy, p2)
    total_h = z1 - z0

    ideal_total = max(4, int(round(total_h / target_riser)))
    best = None
    for total_risers in range(max(4, ideal_total - 4), ideal_total + 5):
        for n1 in range(2, total_risers - 1):
            candidate = _candidate_score(total_h, target_riser, run1, run2, total_risers, n1)
            if candidate is not None and (best is None or candidate["score"] < best["score"]):
                best = candidate

    if best is None:
        raise StairPlanError("No se pudo distribuir los peldanos entre los dos tramos.")

    landing_z = z0 + best["flight1_risers"] * best["riser_mm"]

    warnings = []
    if best["riser_mm"] > 190.0 or best["riser_mm"] < 140.0:
        warnings.append(
            "Contrahuella calculada %.1f mm: revisar criterios del proyecto." % best["riser_mm"]
        )
    for index, tread in enumerate((best["tread1_mm"], best["tread2_mm"]), start=1):
        if tread < 250.0:
            warnings.append(
                "Huella calculada del tramo %d = %.1f mm: revisar criterios del proyecto."
                % (index, tread)
            )
    if abs(best["tread1_mm"] - best["tread2_mm"]) > 35.0:
        warnings.append(
            "Las huellas de ambos tramos difieren %.1f mm porque el Wire fija recorridos distintos."
            % abs(best["tread1_mm"] - best["tread2_mm"])
        )

    return {
        "schema": "FA_AngledStairPlan_v1",
        "input": {
            "points_xy": [[p0[0], p0[1]], [p1[0], p1[1]], [p2[0], p2[1]]],
            "lower_top_z_mm": z0,
            "upper_top_z_mm": z1,
            "width_mm": width,
            "target_riser_mm": target_riser,
            "landing_depth_mm": landing_depth,
        },
        "geometry": {
            "turn_angle_deg": angle,
            "flight1_run_mm": run1,
            "flight2_run_mm": run2,
            "landing_center_xy": [p1[0], p1[1]],
            "landing_start_xy": [landing_start_xy[0], landing_start_xy[1]],
            "landing_end_xy": [landing_end_xy[0], landing_end_xy[1]],
            "landing_z_mm": landing_z,
            "flight1_start_xyz": [p0[0], p0[1], z0],
            "flight1_end_xyz": [landing_start_xy[0], landing_start_xy[1], landing_z],
            "landing_xyz": [
                [landing_start_xy[0], landing_start_xy[1], landing_z],
                [p1[0], p1[1], landing_z],
                [landing_end_xy[0], landing_end_xy[1], landing_z],
            ],
            "flight2_start_xyz": [landing_end_xy[0], landing_end_xy[1], landing_z],
            "flight2_end_xyz": [p2[0], p2[1], z1],
        },
        "steps": {
            "total_risers": best["total_risers"],
            "flight1_risers": best["flight1_risers"],
            "flight2_risers": best["flight2_risers"],
            "riser_mm": best["riser_mm"],
            "tread1_mm": best["tread1_mm"],
            "tread2_mm": best["tread2_mm"],
            "blondel1_mm": best["blondel1_mm"],
            "blondel2_mm": best["blondel2_mm"],
        },
        "warnings": warnings,
    }


def _lerp_xy(a, b, t):
    return (
        float(a[0]) + (float(b[0]) - float(a[0])) * float(t),
        float(a[1]) + (float(b[1]) - float(a[1])) * float(t),
    )


def _buffered_segment_quad(a, b, width_mm, start_back_mm=0.0, end_forward_mm=0.0):
    """Return a JSON-safe rectangular quad around one XY centerline segment."""
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        raise StairPlanError("No se puede generar una zona de holgura sobre un tramo nulo.")
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    half = float(width_mm) * 0.5
    start_back = max(0.0, min(float(start_back_mm), length))
    end_forward = max(0.0, float(end_forward_mm))
    sx, sy = ax - ux * start_back, ay - uy * start_back
    ex, ey = bx + ux * end_forward, by + uy * end_forward
    return [
        [sx + nx * half, sy + ny * half],
        [ex + nx * half, ey + ny * half],
        [ex - nx * half, ey - ny * half],
        [sx - nx * half, sy - ny * half],
    ]


def _flight_clearance_zone(role, a_xy, b_xy, z_start, z_end, plane_z, headroom, width, approach_margin):
    """Return the portion of one ascending flight requiring an opening at plane_z."""
    z_start = float(z_start)
    z_end = float(z_end)
    threshold = float(plane_z) - float(headroom)
    if z_end <= z_start + 1e-9:
        return None
    if threshold >= z_end - 1e-9:
        return None
    if threshold <= z_start + 1e-9:
        fraction = 0.0
    else:
        fraction = (threshold - z_start) / (z_end - z_start)
        fraction = max(0.0, min(1.0, fraction))
    start_xy = _lerp_xy(a_xy, b_xy, fraction)
    total_length = _length_xy(a_xy, b_xy)
    distance_from_start = total_length * fraction
    back = min(max(0.0, float(approach_margin)), distance_from_start)
    return {
        "role": str(role),
        "threshold_z_mm": threshold,
        "active_from_fraction": float(fraction),
        "active_from_xy": [float(start_xy[0]), float(start_xy[1])],
        "polygon_mm": _buffered_segment_quad(start_xy, b_xy, width, start_back_mm=back),
    }


def _open_end_descriptor(role, point_xy, direction_xy, width_mm):
    """Return JSON-safe metadata for a passage end that must remain free of liner."""
    length = math.hypot(float(direction_xy[0]), float(direction_xy[1]))
    if length <= 1e-9:
        raise StairPlanError("No se puede definir un extremo abierto con direccion nula.")
    return {
        "role": str(role),
        "point_mm": [float(point_xy[0]), float(point_xy[1])],
        "direction_xy": [float(direction_xy[0]) / length, float(direction_xy[1]) / length],
        "clear_width_mm": float(width_mm),
    }


def _complete_l_clearance_zones(
    inputs,
    geometry,
    f1_zone,
    plane_z,
    headroom,
    width,
    approach_margin,
):
    """Build two overlapping corridor arms whose union is one complete L opening.

    The old clearance model described the landing as two additional narrow
    rectangles between the shortened native flight bases. Their union left a
    missing corner beside the turn. The opening is instead a circulation
    corridor around the original three-point path: lower arm -> corner -> upper
    arm. Both arms deliberately overlap by half the effective width at the
    corner, so a boolean union produces one continuous L without a notch.
    """
    p0, corner, p2 = [list(point[:2]) for point in inputs["points_xy"]]
    d1 = _unit_xy(p0, corner)
    d2 = _unit_xy(corner, p2)
    half = float(width) * 0.5

    active_start = list(f1_zone["active_from_xy"])
    flight1_start = list(geometry["flight1_start_xyz"][:2])
    distance_from_start = _length_xy(flight1_start, active_start)
    entry_back = min(max(0.0, float(approach_margin)), distance_from_start)
    entry_center = [
        float(active_start[0]) - d1[0] * entry_back,
        float(active_start[1]) - d1[1] * entry_back,
    ]

    lower_arm = {
        "role": "lower_arm",
        "threshold_z_mm": float(plane_z) - float(headroom),
        "active_from_fraction": float(f1_zone["active_from_fraction"]),
        "active_from_xy": [float(active_start[0]), float(active_start[1])],
        "polygon_mm": _buffered_segment_quad(
            active_start,
            corner,
            width,
            start_back_mm=entry_back,
            end_forward_mm=half,
        ),
    }
    upper_arm = {
        "role": "upper_arm",
        "threshold_z_mm": float(plane_z) - float(headroom),
        "active_from_fraction": 0.0,
        "active_from_xy": [float(corner[0]), float(corner[1])],
        "polygon_mm": _buffered_segment_quad(
            corner,
            p2,
            width,
            start_back_mm=half,
        ),
    }
    open_ends = [
        _open_end_descriptor("entry", entry_center, d1, width),
        _open_end_descriptor("exit", p2, d2, width),
    ]
    return [lower_arm, upper_arm], open_ends


def plan_stair_clearance(
    stair_plan,
    obstacle_planes,
    headroom_mm=2100.0,
    side_margin_mm=50.0,
    approach_margin_mm=100.0,
):
    """Plan 2D clearance zones where horizontal obstacles would violate headroom.

    ``obstacle_planes`` is a list of JSON-compatible dictionaries with ``id`` and
    ``plane_z_mm``. The function does not cut FreeCAD geometry. When the corner
    landing itself requires clearance, the result uses two overlapping corridor
    arms whose union is one complete L. This avoids the notch produced by the
    former four-rectangle representation and gives the adapter explicit open
    entry/exit ends for non-obstructing tapicheles.
    """
    plan = dict(stair_plan or {})
    geometry = dict(plan.get("geometry", {}) or {})
    inputs = dict(plan.get("input", {}) or {})
    if not geometry or not inputs:
        raise StairPlanError("Se requiere un plan de escalera valido para calcular la altura libre.")

    headroom = float(headroom_mm)
    side_margin = max(0.0, float(side_margin_mm))
    approach_margin = max(0.0, float(approach_margin_mm))
    if headroom <= 0.0:
        raise StairPlanError("La altura libre debe ser mayor que cero.")

    width = float(inputs.get("width_mm", 0.0)) + 2.0 * side_margin
    if width <= 0.0:
        raise StairPlanError("El ancho efectivo de la envolvente debe ser positivo.")

    f1_a = list(geometry["flight1_start_xyz"][:2])
    f1_b = list(geometry["flight1_end_xyz"][:2])
    f2_a = list(geometry["flight2_start_xyz"][:2])
    f2_b = list(geometry["flight2_end_xyz"][:2])
    landing = list(geometry.get("landing_xyz", []) or [])
    landing_z = float(geometry["landing_z_mm"])
    z0 = float(inputs["lower_top_z_mm"])
    z1 = float(inputs["upper_top_z_mm"])

    plane_results = []
    for raw in list(obstacle_planes or []):
        item = dict(raw or {})
        plane_id = str(item.get("id") or "obstacle")
        plane_z = float(item.get("plane_z_mm"))
        f1 = _flight_clearance_zone(
            "flight1", f1_a, f1_b, z0, landing_z, plane_z, headroom, width, approach_margin
        )
        f2 = _flight_clearance_zone(
            "flight2", f2_a, f2_b, landing_z, z1, plane_z, headroom, width, approach_margin
        )
        landing_active = bool(landing_z + headroom > plane_z + 1e-9 and len(landing) >= 3)

        opening_shape = "segmented_clearance_v1"
        liner_open_ends = []
        if landing_active and f1 is not None and f2 is not None:
            zones, liner_open_ends = _complete_l_clearance_zones(
                inputs, geometry, f1, plane_z, headroom, width, approach_margin
            )
            opening_shape = "l_union_v2"
        else:
            # Conservative fallback for unusual planes that intersect only part
            # of the stair. Preserve the previous segmented behavior.
            zones = []
            if f1 is not None:
                zones.append(f1)
            if landing_active:
                for role, a, b in (
                    ("landing_in", landing[0], landing[1]),
                    ("landing_out", landing[1], landing[2]),
                ):
                    zones.append(
                        {
                            "role": role,
                            "threshold_z_mm": plane_z - headroom,
                            "active_from_fraction": 0.0,
                            "active_from_xy": [float(a[0]), float(a[1])],
                            "polygon_mm": _buffered_segment_quad(a, b, width),
                        }
                    )
            if f2 is not None:
                zones.append(f2)

        plane_results.append(
            {
                "id": plane_id,
                "role": str(item.get("role") or plane_id),
                "plane_z_mm": plane_z,
                "threshold_z_mm": plane_z - headroom,
                "opening_shape": opening_shape,
                "liner_open_ends": liner_open_ends,
                "zones": zones,
                "zone_count": len(zones),
            }
        )

    return {
        "schema": "FA_StairClearancePlan_v2",
        "model": "linear_nosing_envelope_l_union_v2",
        "headroom_mm": headroom,
        "side_margin_mm": side_margin,
        "approach_margin_mm": approach_margin,
        "effective_width_mm": width,
        "planes": plane_results,
    }

