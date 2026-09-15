"""Pure tests for FA stair planning core.

Fecha y hora: 2026-09-14 20:00 America/Costa_Rica
FreeCAD objetivo: 1.1.3
"""

from __future__ import annotations

import json

from core.fa_stair_core import StairPlanError, plan_angled_stair, plan_stair_clearance


def test_right_angle_three_metre_stair_is_json_compatible():
    plan = plan_angled_stair(
        [(1000.0, 1000.0, 0.0), (1000.0, 4000.0, 0.0), (4000.0, 4000.0, 0.0)],
        0.0,
        3000.0,
        width_mm=1000.0,
        target_riser_mm=175.0,
    )
    assert plan["schema"] == "FA_AngledStairPlan_v1"
    assert abs(plan["geometry"]["turn_angle_deg"] - 90.0) < 1.0e-9
    assert plan["steps"]["total_risers"] >= 4
    assert plan["steps"]["flight1_risers"] >= 2
    assert plan["steps"]["flight2_risers"] >= 2
    assert 130.0 <= plan["steps"]["riser_mm"] <= 205.0
    json.dumps(plan, sort_keys=True)


def test_reverse_elevation_is_rejected():
    try:
        plan_angled_stair([(0, 0), (0, 3000), (3000, 3000)], 3000.0, 0.0)
    except StairPlanError:
        return
    raise AssertionError("Expected StairPlanError")


def test_too_short_wire_is_rejected():
    try:
        plan_angled_stair([(0, 0), (0, 900), (900, 900)], 0.0, 3000.0, width_mm=1000.0)
    except StairPlanError:
        return
    raise AssertionError("Expected StairPlanError")


def test_clearance_plan_distinguishes_slab_and_ceiling_planes():
    stair = plan_angled_stair(
        [(5200.0, 4200.0), (5200.0, 1900.0), (2700.0, 1900.0)],
        0.0,
        3000.0,
        width_mm=1000.0,
        target_riser_mm=175.0,
    )
    clearance = plan_stair_clearance(
        stair,
        [
            {"id": "upper_slab", "plane_z_mm": 2850.0},
            {"id": "lower_ceiling", "plane_z_mm": 2685.0},
        ],
        headroom_mm=2100.0,
        side_margin_mm=50.0,
        approach_margin_mm=100.0,
    )
    assert clearance["schema"] == "FA_StairClearancePlan_v2"
    assert clearance["model"] == "linear_nosing_envelope_l_union_v2"
    assert clearance["effective_width_mm"] == 1100.0
    planes = {item["id"]: item for item in clearance["planes"]}
    assert planes["upper_slab"]["zone_count"] == 2
    assert planes["lower_ceiling"]["zone_count"] == 2
    assert planes["upper_slab"]["opening_shape"] == "l_union_v2"
    assert planes["lower_ceiling"]["opening_shape"] == "l_union_v2"

    slab_lower = next(item for item in planes["upper_slab"]["zones"] if item["role"] == "lower_arm")
    slab_upper = next(item for item in planes["upper_slab"]["zones"] if item["role"] == "upper_arm")
    ceiling_lower = next(item for item in planes["lower_ceiling"]["zones"] if item["role"] == "lower_arm")
    assert ceiling_lower["active_from_fraction"] < slab_lower["active_from_fraction"]

    # The two corridor arms overlap through the full 1100 x 1100 turn square.
    # This is the regression for the former four-rectangle notch in the buque.
    def bounds(zone):
        xs = [point[0] for point in zone["polygon_mm"]]
        ys = [point[1] for point in zone["polygon_mm"]]
        return min(xs), max(xs), min(ys), max(ys)

    lower_bounds = bounds(slab_lower)
    upper_bounds = bounds(slab_upper)
    assert lower_bounds[0] <= 4650.0 and lower_bounds[1] >= 5750.0
    assert lower_bounds[2] <= 1350.0 and lower_bounds[3] >= 2450.0
    assert upper_bounds[0] <= 4650.0 and upper_bounds[1] >= 5750.0
    assert upper_bounds[2] <= 1350.0 and upper_bounds[3] >= 2450.0

    open_ends = planes["lower_ceiling"]["liner_open_ends"]
    assert [item["role"] for item in open_ends] == ["entry", "exit"]
    assert open_ends[0]["clear_width_mm"] == 1100.0
    assert open_ends[1]["point_mm"] == [2700.0, 1900.0]

    slab_ymax = max(point[1] for zone in planes["upper_slab"]["zones"] for point in zone["polygon_mm"])
    assert slab_ymax < 3440.0  # clear face of Nivel 01 partition at Y=3500, t=120
    json.dumps(clearance, sort_keys=True)
