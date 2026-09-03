"""Pure geometry planner for door-to-corner snapping in FacilArquitecturaWB.

Nombre: door_corner_utils.py
Proposito: detectar una pared lateral unica cercana a un extremo de una puerta y
planificar el desplazamiento longitudinal necesario para alinear la jamba con la cara
real de esa pared, preservando el ancho del Sketch.
Funcionamiento: recibe solo tuplas/dicts JSON-compatible; no importa FreeCAD, Qt ni GUI.
Tambien infiere HingeEndpoint y OpeningSide hacia la pared lateral cuando la geometria
forma una esquina no ambigua.
FreeCAD objetivo: 1.1.3.
Version: 0.2.1.
Fecha y hora: 2026-08-30 18:30 UTC-06:00.
Mantenimiento: conservar este modulo puro. La adaptacion de objetos FreeCAD pertenece a
opening_utils.py. No adivinar cuando dos esquinas son equivalentes o la pared lateral
cruza claramente ambos lados del muro anfitrion.
"""

from __future__ import annotations

import math


DEFAULT_CORNER_SNAP_TOLERANCE_MM = 180.0
DEFAULT_PERPENDICULAR_TOLERANCE_DEG = 25.0
DEFAULT_SIDE_EXTENSION_TOLERANCE_MM = 120.0
DEFAULT_AMBIGUITY_MARGIN_MM = 20.0
DEFAULT_FIT_TOLERANCE_MM = 1.0
MIN_SEGMENT_MM = 1e-6


def plan_door_corner_snap(
    opening_segment,
    host_wall_key,
    wall_records,
    tolerance_mm=DEFAULT_CORNER_SNAP_TOLERANCE_MM,
    perpendicular_tolerance_deg=DEFAULT_PERPENDICULAR_TOLERANCE_DEG,
    side_extension_tolerance_mm=DEFAULT_SIDE_EXTENSION_TOLERANCE_MM,
    ambiguity_margin_mm=DEFAULT_AMBIGUITY_MARGIN_MM,
    fit_tolerance_mm=DEFAULT_FIT_TOLERANCE_MM,
):
    """Return a JSON-compatible corner-snap plan for one projected door segment.

    ``wall_records`` entries use::

        {"wall_key": "Wall001", "label": "...", "width_mm": 100.0,
         "segments": [(x1,y1,z1,x2,y2,z2), ...]}

    The opening width is never changed. When one unique corner is clear, both opening
    endpoints are translated by the same signed amount along the host axis so the
    selected jamb lands on the nearest *face* of the side wall, not its centerline.
    """
    opening = _segment(opening_segment)
    tolerance = max(0.0, float(tolerance_mm))
    perp_tol = max(0.0, min(89.0, float(perpendicular_tolerance_deg)))
    extension_tol = max(0.0, float(side_extension_tolerance_mm))
    ambiguity_margin = max(0.0, float(ambiguity_margin_mm))
    fit_tolerance = max(0.0, float(fit_tolerance_mm))

    dx = opening[3] - opening[0]
    dy = opening[4] - opening[1]
    length = math.hypot(dx, dy)
    if length <= MIN_SEGMENT_MM or tolerance <= 0.0:
        return _empty_plan(opening, "segmento de puerta invalido o tolerancia nula")
    ux, uy = dx / length, dy / length
    left_n = (-uy, ux)
    first = (opening[0], opening[1])
    second = (opening[3], opening[4])

    candidates = []
    for record in list(wall_records or []):
        wall_key = str(record.get("wall_key") or "")
        if wall_key and wall_key == str(host_wall_key or ""):
            continue
        width = _positive_float(record.get("width_mm"), 100.0)
        label = str(record.get("label") or wall_key or "Pared lateral")
        for seg_index, raw_side in enumerate(list(record.get("segments") or [])):
            side = _segment(raw_side)
            svx = side[3] - side[0]
            svy = side[4] - side[1]
            side_len = math.hypot(svx, svy)
            if side_len <= MIN_SEGMENT_MM:
                continue
            vx, vy = svx / side_len, svy / side_len
            dot_abs = abs(ux * vx + uy * vy)
            dot_abs = max(0.0, min(1.0, dot_abs))
            angle_between = math.degrees(math.acos(dot_abs))
            perpendicular_error = abs(90.0 - angle_between)
            if perpendicular_error > perp_tol:
                continue

            inter = _line_intersection(first, (ux, uy), (side[0], side[1]), (vx, vy))
            if inter is None:
                continue
            ix, iy, t_host, t_side_distance = inter
            side_param = t_side_distance / side_len
            allowed = extension_tol / side_len
            if side_param < -allowed or side_param > 1.0 + allowed:
                continue

            # Face alignment and swing inference are intentionally independent.  A
            # wall that crosses the host can still provide a safe face for a jamb,
            # but it cannot by itself choose the opening quadrant.
            side_extension = _side_extension_direction((ix, iy), side, (ux, uy), extension_tol)

            side_normal = (-vy, vx)
            face_denom = abs(side_normal[0] * ux + side_normal[1] * uy)
            if face_denom <= 1e-6:
                continue
            half_face = (width * 0.5) / face_denom

            for endpoint_name, endpoint, other in (
                ("START", first, second),
                ("END", second, first),
            ):
                endpoint_t = (endpoint[0] - ix) * ux + (endpoint[1] - iy) * uy
                other_t = (other[0] - ix) * ux + (other[1] - iy) * uy
                # The jamb must align with the face on the same side of the side-wall
                # centerline as the rest of the door opening.
                if abs(other_t) <= 1e-6:
                    continue
                target_face_t = half_face if other_t > 0.0 else -half_face
                shift = target_face_t - endpoint_t
                gap = abs(shift)
                if gap > tolerance:
                    continue

                opening_side = "AUTO"
                swing_resolved = False
                if side_extension is not None:
                    ex, ey = side_extension
                    swing_dot = ex * left_n[0] + ey * left_n[1]
                    if abs(swing_dot) >= math.cos(math.radians(perp_tol)):
                        opening_side = "LEFT" if swing_dot > 0.0 else "RIGHT"
                        swing_resolved = True
                target_x = ix + ux * target_face_t
                target_y = iy + uy * target_face_t
                target_axis = (target_x - first[0]) * ux + (target_y - first[1]) * uy
                score = gap + perpendicular_error * 2.0 + max(0.0, -side_param, side_param - 1.0) * 10.0
                candidates.append(
                    {
                        "score": score,
                        "gap_before_mm": gap,
                        "shift_mm": shift,
                        "hinge_endpoint": endpoint_name,
                        "jamb_endpoint": endpoint_name,
                        "opening_side": opening_side,
                        "opens_inward": True if swing_resolved else None,
                        "swing_resolved": swing_resolved,
                        "target_face_point": [float(target_x), float(target_y)],
                        "target_axis_mm": float(target_axis),
                        "side_wall_key": wall_key,
                        "side_wall_label": label,
                        "side_segment_index": int(seg_index),
                        "intersection": [float(ix), float(iy)],
                        "side_wall_width_mm": width,
                        "perpendicular_error_deg": perpendicular_error,
                    }
                )

    candidates.sort(key=lambda item: (item["score"], item["gap_before_mm"], item["side_wall_label"]))
    if not candidates:
        return _empty_plan(opening, "sin pared lateral unica dentro de tolerancia")

    best = candidates[0]
    fit_conflict = _opposite_jamb_fit_conflict(best, candidates, length, fit_tolerance)
    if fit_conflict is not None:
        limiter, available_width, penetration = fit_conflict
        plan = _empty_plan(
            opening,
            "NO_FIT: ancho %.3f mm excede luz util %.3f mm por %.3f mm"
            % (length, available_width, penetration),
        )
        plan.update(
            {
                "status": "NO_FIT",
                "no_fit": True,
                "opening_width_mm": float(length),
                "available_width_mm": float(available_width),
                "penetration_mm": float(penetration),
                "jamb_endpoint": best["jamb_endpoint"],
                "jamb_face_candidate": _public_candidate(best),
                "swing_direction_candidate": (
                    _public_candidate(best) if best.get("swing_resolved") else None
                ),
                "candidates": [_public_candidate(best), _public_candidate(limiter)],
            }
        )
        return plan

    equivalent = [
        item
        for item in candidates[1:]
        if item["hinge_endpoint"] != best["hinge_endpoint"]
        and item["score"] - best["score"] <= ambiguity_margin
    ]
    if equivalent:
        plan = _empty_plan(opening, "dos extremos tienen paredes laterales equivalentes")
        plan["status"] = "AMBIGUOUS"
        plan["ambiguous"] = True
        plan["candidates"] = [_public_candidate(best)] + [_public_candidate(item) for item in equivalent]
        return plan

    bounded = _opposite_jamb_bounded_span(best, candidates, length, fit_tolerance)
    if bounded is not None:
        limiter, available_width = bounded
        plan = _empty_plan(
            opening,
            "dos caras opuestas acotan el vano; posicion longitudinal del Sketch conservada",
        )
        hinge_point = opening[:3] if best["hinge_endpoint"] == "START" else opening[3:6]
        plan.update(
            {
                "status": "BOUNDED",
                "position_preserved": True,
                "bounded_by_opposite_faces": True,
                "opening_width_mm": float(length),
                "available_width_mm": float(available_width),
                "clearance_mm": float(available_width - length),
                "jamb_endpoint": best["jamb_endpoint"],
                "hinge_endpoint": best["hinge_endpoint"] if best.get("swing_resolved") else "AUTO",
                "opening_side": best["opening_side"],
                "opens_inward": best.get("opens_inward"),
                "swing_resolved": bool(best.get("swing_resolved")),
                "jamb_face_candidate": _public_candidate(best),
                "swing_direction_candidate": (
                    _public_candidate(best) if best.get("swing_resolved") else None
                ),
                "snap_distance_mm": best["gap_before_mm"],
                "proposed_shift_mm": best["shift_mm"],
                "side_wall_key": best["side_wall_key"],
                "side_wall_label": best["side_wall_label"],
                "side_segment_index": best["side_segment_index"],
                "side_wall_width_mm": best["side_wall_width_mm"],
                "perpendicular_error_deg": best["perpendicular_error_deg"],
                "hinge_point": [float(hinge_point[0]), float(hinge_point[1]), float(hinge_point[2])],
                "candidates": [_public_candidate(best), _public_candidate(limiter)],
            }
        )
        return plan

    # A crossing wall can expose a geometrically unique face without defining a
    # unique swing quadrant.  If that face already lies *inside* the opening
    # segment, translating the complete door would pull it away from its source
    # jamb.  Keep the projected Sketch position in that JAMB_ONLY case while
    # retaining the candidate as diagnostic evidence.  Faces before/after the
    # segment still align the jamb as before.
    target_axis = float(best.get("target_axis_mm") or 0.0)
    if (
        not best.get("swing_resolved")
        and fit_tolerance < target_axis < length - fit_tolerance
    ):
        plan = _empty_plan(
            opening,
            "cara de jamba dentro del tramo; posicion proyectada conservada",
        )
        plan.update(
            {
                "status": "JAMB_ONLY",
                "jamb_endpoint": best["jamb_endpoint"],
                "jamb_face_candidate": _public_candidate(best),
                "snap_distance_mm": best["gap_before_mm"],
                "proposed_shift_mm": best["shift_mm"],
                "side_wall_key": best["side_wall_key"],
                "side_wall_label": best["side_wall_label"],
                "side_segment_index": best["side_segment_index"],
                "side_wall_width_mm": best["side_wall_width_mm"],
                "perpendicular_error_deg": best["perpendicular_error_deg"],
                "face_inside_opening": True,
                "candidates": [_public_candidate(best)],
            }
        )
        return plan

    shift = best["shift_mm"]
    sx, sy = ux * shift, uy * shift
    shifted = (
        opening[0] + sx,
        opening[1] + sy,
        opening[2],
        opening[3] + sx,
        opening[4] + sy,
        opening[5],
    )
    hinge_point = shifted[:3] if best["hinge_endpoint"] == "START" else shifted[3:6]
    return {
        "status": "SNAPPED" if best.get("swing_resolved") else "JAMB_ONLY",
        "applied": True,
        "ambiguous": False,
        "no_fit": False,
        "reason": (
            "pared lateral unica cercana"
            if best.get("swing_resolved")
            else "cara de jamba unica; giro ambiguo"
        ),
        "jamb_endpoint": best["jamb_endpoint"],
        "hinge_endpoint": best["hinge_endpoint"] if best.get("swing_resolved") else "AUTO",
        "opening_side": best["opening_side"],
        "opens_inward": best.get("opens_inward"),
        "swing_resolved": bool(best.get("swing_resolved")),
        "jamb_face_candidate": _public_candidate(best),
        "swing_direction_candidate": (
            _public_candidate(best) if best.get("swing_resolved") else None
        ),
        "snap_distance_mm": best["gap_before_mm"],
        "shift_mm": shift,
        "side_wall_key": best["side_wall_key"],
        "side_wall_label": best["side_wall_label"],
        "side_segment_index": best["side_segment_index"],
        "side_wall_width_mm": best["side_wall_width_mm"],
        "perpendicular_error_deg": best["perpendicular_error_deg"],
        "projected_first": [shifted[0], shifted[1], shifted[2]],
        "projected_second": [shifted[3], shifted[4], shifted[5]],
        "hinge_point": [float(hinge_point[0]), float(hinge_point[1]), float(hinge_point[2])],
        "candidates": [_public_candidate(best)],
    }


def desired_open_leaf_vector(opening_segment, opening_side):
    """Return the requested physical XY leaf vector for LEFT/RIGHT semantics."""
    opening = _segment(opening_segment)
    dx = opening[3] - opening[0]
    dy = opening[4] - opening[1]
    length = math.hypot(dx, dy)
    side = str(opening_side or "AUTO").strip().upper()
    if length <= MIN_SEGMENT_MM or side not in ("LEFT", "RIGHT"):
        return None
    left = (-dy / length, dx / length)
    return left if side == "LEFT" else (-left[0], -left[1])


def resolve_native_opening_mode(
    opening_segment,
    hinge_point,
    desired_leaf_vector_xy,
    angular_tolerance_deg=5.0,
):
    """Resolve FreeCAD Mode1/Mode2 from physical hinge and leaf vectors.

    FreeCAD 1.1.3 rotates ``Mode1`` toward the left normal of the axis that
    starts at the physical hinge and ends at the opposite jamb; ``Mode2`` uses
    the right normal.  Endpoint names are diagnostic output only: the decision
    is made from coordinates and vectors.
    """
    opening = _segment(opening_segment)
    hx, hy = float(hinge_point[0]), float(hinge_point[1])
    desired = tuple(float(value) for value in desired_leaf_vector_xy[:2])
    desired_len = math.hypot(desired[0], desired[1])
    if desired_len <= MIN_SEGMENT_MM:
        return _empty_mode_plan("vector deseado invalido")
    desired = (desired[0] / desired_len, desired[1] / desired_len)
    endpoints = ((opening[0], opening[1]), (opening[3], opening[4]))
    distances = [math.hypot(hx - point[0], hy - point[1]) for point in endpoints]
    if abs(distances[0] - distances[1]) <= 1e-6:
        return _empty_mode_plan("bisagra no coincide inequivocamente con una jamba")
    hinge_index = 0 if distances[0] < distances[1] else 1
    other_index = 1 - hinge_index
    axis = (
        endpoints[other_index][0] - endpoints[hinge_index][0],
        endpoints[other_index][1] - endpoints[hinge_index][1],
    )
    axis_len = math.hypot(axis[0], axis[1])
    if axis_len <= MIN_SEGMENT_MM:
        return _empty_mode_plan("eje fisico invalido")
    axis = (axis[0] / axis_len, axis[1] / axis_len)
    mode1_vector = (-axis[1], axis[0])
    mode2_vector = (-mode1_vector[0], -mode1_vector[1])
    dot1 = desired[0] * mode1_vector[0] + desired[1] * mode1_vector[1]
    dot2 = desired[0] * mode2_vector[0] + desired[1] * mode2_vector[1]
    best_dot = max(dot1, dot2)
    minimum_dot = math.cos(math.radians(max(0.0, float(angular_tolerance_deg))))
    if best_dot < minimum_dot:
        return _empty_mode_plan("vector deseado no es perpendicular al eje fisico")
    return {
        "resolved": True,
        "mode": "Mode1" if dot1 >= dot2 else "Mode2",
        "hinge_endpoint": "START" if hinge_index == 0 else "END",
        "hinge_point": [hx, hy],
        "physical_axis": [float(axis[0]), float(axis[1])],
        "desired_leaf_vector": [float(desired[0]), float(desired[1])],
        "mode1_leaf_vector": [float(mode1_vector[0]), float(mode1_vector[1])],
        "mode2_leaf_vector": [float(mode2_vector[0]), float(mode2_vector[1])],
        "alignment": float(best_dot),
        "reason": "convencion nativa FreeCAD 1.1.3",
    }


def _empty_mode_plan(reason):
    return {
        "resolved": False,
        "mode": "",
        "hinge_endpoint": "AUTO",
        "hinge_point": None,
        "physical_axis": None,
        "desired_leaf_vector": None,
        "mode1_leaf_vector": None,
        "mode2_leaf_vector": None,
        "alignment": 0.0,
        "reason": str(reason),
    }


def _opposite_jamb_fit_conflict(best, candidates, opening_width, tolerance):
    spans = _opposite_jamb_spans(best, candidates, opening_width)
    conflicts = [item for item in spans if item[0] > float(tolerance)]
    if not conflicts:
        return None
    penetration, item, available = max(conflicts, key=lambda value: value[0])
    return item, available, penetration


def _opposite_jamb_bounded_span(best, candidates, opening_width, tolerance):
    """Return an opposite external face when both faces safely bound the Sketch."""
    length = float(opening_width)
    tol = float(tolerance)
    bounded = []
    for penetration, item, available in _opposite_jamb_spans(best, candidates, length):
        if penetration >= -tol:
            continue
        if best["jamb_endpoint"] == "START":
            external = best["target_axis_mm"] < -tol and item["target_axis_mm"] > length + tol
        else:
            external = best["target_axis_mm"] > length + tol and item["target_axis_mm"] < -tol
        if external:
            bounded.append((available - length, item, available))
    if not bounded:
        return None
    _clearance, item, available = min(bounded, key=lambda value: value[0])
    return item, available


def _opposite_jamb_spans(best, candidates, opening_width):
    opposite = "END" if best["jamb_endpoint"] == "START" else "START"
    spans = []
    for item in candidates:
        if item["jamb_endpoint"] != opposite:
            continue
        if best["jamb_endpoint"] == "START":
            available = item["target_axis_mm"] - best["target_axis_mm"]
        else:
            available = best["target_axis_mm"] - item["target_axis_mm"]
        penetration = float(opening_width) - float(available)
        spans.append((penetration, item, max(0.0, float(available))))
    return spans


def _side_extension_direction(intersection, segment, host_unit, tolerance_mm):
    """Return the unique direction in which a side wall leaves the host axis."""
    ix, iy = intersection
    ux, uy = host_unit
    left = (-uy, ux)
    points = ((segment[0], segment[1]), (segment[3], segment[4]))
    signed = [((px - ix) * left[0] + (py - iy) * left[1]) for px, py in points]
    substantial = max(20.0, min(float(tolerance_mm), 80.0))
    pos = [value for value in signed if value > substantial]
    neg = [value for value in signed if value < -substantial]
    if pos and neg:
        return None
    # Choose the endpoint farther from the host line; this also works when the
    # side segment ends a little before/after the host centerline.
    index = 0 if abs(signed[0]) >= abs(signed[1]) else 1
    px, py = points[index]
    dx, dy = px - ix, py - iy
    length = math.hypot(dx, dy)
    if length <= MIN_SEGMENT_MM:
        return None
    return (dx / length, dy / length)


def _line_intersection(p, u, q, v):
    cross = u[0] * v[1] - u[1] * v[0]
    if abs(cross) <= 1e-9:
        return None
    qpx, qpy = q[0] - p[0], q[1] - p[1]
    t = (qpx * v[1] - qpy * v[0]) / cross
    s = (qpx * u[1] - qpy * u[0]) / cross
    return p[0] + t * u[0], p[1] + t * u[1], t, s


def _public_candidate(item):
    return {
        "score": float(item["score"]),
        "gap_before_mm": float(item["gap_before_mm"]),
        "hinge_endpoint": item["hinge_endpoint"],
        "jamb_endpoint": item.get("jamb_endpoint", item["hinge_endpoint"]),
        "opening_side": item["opening_side"],
        "swing_resolved": bool(item.get("swing_resolved")),
        "target_face_point": list(item.get("target_face_point") or []),
        "target_axis_mm": float(item.get("target_axis_mm") or 0.0),
        "side_wall_key": item["side_wall_key"],
        "side_wall_label": item["side_wall_label"],
        "side_segment_index": int(item["side_segment_index"]),
    }


def _empty_plan(opening, reason):
    return {
        "status": "NO_CANDIDATE",
        "applied": False,
        "ambiguous": False,
        "no_fit": False,
        "reason": str(reason),
        "jamb_endpoint": "AUTO",
        "hinge_endpoint": "AUTO",
        "opening_side": "AUTO",
        "opens_inward": None,
        "swing_resolved": False,
        "jamb_face_candidate": None,
        "swing_direction_candidate": None,
        "snap_distance_mm": 0.0,
        "shift_mm": 0.0,
        "side_wall_key": "",
        "side_wall_label": "",
        "side_segment_index": -1,
        "projected_first": [opening[0], opening[1], opening[2]],
        "projected_second": [opening[3], opening[4], opening[5]],
        "hinge_point": None,
        "candidates": [],
    }


def _segment(value):
    data = tuple(float(item) for item in value)
    if len(data) != 6:
        raise ValueError("segment debe contener seis valores")
    return data


def _positive_float(value, default):
    try:
        number = float(value)
    except Exception:
        number = float(default)
    return number if number > 0.0 else float(default)
