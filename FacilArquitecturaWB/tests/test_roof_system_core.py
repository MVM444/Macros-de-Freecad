"""Pruebas focales del nucleo independiente de FA Techo.

Nombre: test_roof_system_core.py
Proposito: comprobar planificacion JSON de cerchas, clavadores y cubierta sin FreeCAD.
Version: 0.4.1
Fecha y hora: 2026-08-30 16:08 America/Costa_Rica
"""

import json
import math
import pytest

from core.roof_system_core import (
    RoofPlanError,
    build_roof_system_plan,
    plan_purlins,
    plan_projected_purlins,
    plan_roof,
    plan_trusses,
)


def test_parallel_truss_axes_plan_one_master_truss_spread_by_axis():
    plan = plan_trusses([
        ((0, 0, 3000), (8000, 0, 3000)),
        ((0, 3000, 3000), (8000, 3000, 3000)),
        ((0, 6000, 3000), (8000, 6000, 3000)),
    ])
    assert plan["count"] == 3
    assert plan["slant_type"] == "Double"
    assert plan["representation"] == "ONE_TRUSS_AXIS_SPREAD"
    assert plan["materialized_truss_objects"] == 1
    assert plan["axis_spread_compatible"] is True
    assert plan["items"][1]["id"] == "TRUSS-002"
    assert plan["items"][0]["baseline"]["length_mm"] == pytest.approx(8000.0)


def test_double_truss_derives_ridge_height_from_half_span_and_pitch():
    plan = plan_trusses(
        [((0, 0, 3000), (8000, 0, 3000))],
        {"slant_type": "Double", "pitch_deg": 20.0, "height_start_mm": 150.0},
    )
    params = plan["items"][0]["parameters"]
    expected = 150.0 + 4000.0 * math.tan(math.radians(20.0))
    assert params["resolved_run_mm"] == pytest.approx(4000.0)
    assert params["height_end_mm"] == pytest.approx(expected)
    assert params["height_end_mode"] == "pitch"


def test_truss_native_baseline_is_lowered_so_top_face_matches_support_line():
    plan = plan_trusses(
        [((0, 0, 3000), (8000, 0, 3000))],
        {"slant_type": "Double", "pitch_deg": 20.0, "height_start_mm": 150.0},
    )
    item = plan["items"][0]
    assert item["support_line"]["start"][2] == pytest.approx(3000.0)
    assert item["native_baseline"]["start"][2] == pytest.approx(2850.0)
    assert item["native_baseline"]["end"][2] == pytest.approx(2850.0)
    assert item["parameters"]["height_start_mm"] == pytest.approx(150.0)


def test_simple_truss_uses_full_span_for_pitch():
    plan = plan_trusses(
        [((0, 0, 3000), (8000, 0, 3000))],
        {"slant_type": "Simple", "pitch_deg": 10.0, "height_start_mm": 100.0},
    )
    params = plan["items"][0]["parameters"]
    assert params["resolved_run_mm"] == pytest.approx(8000.0)
    assert params["height_end_mm"] == pytest.approx(100.0 + 8000.0 * math.tan(math.radians(10.0)))


def test_truss_axes_reject_mixed_directions():
    with pytest.raises(RoofPlanError):
        plan_trusses([
            ((0, 0, 0), (8000, 0, 0)),
            ((0, 0, 0), (0, 8000, 0)),
        ])


def test_truss_axis_rejects_non_horizontal_base():
    with pytest.raises(RoofPlanError):
        plan_trusses([((0, 0, 3000), (8000, 0, 3010))])


def test_truss_axis_spread_rejects_different_spans():
    with pytest.raises(RoofPlanError):
        plan_trusses([
            ((0, 0, 3000), (8000, 0, 3000)),
            ((0, 3000, 3000), (7900, 3000, 3000)),
        ])


def test_truss_axis_spread_rejects_longitudinal_stagger():
    with pytest.raises(RoofPlanError):
        plan_trusses([
            ((0, 0, 3000), (8000, 0, 3000)),
            ((100, 3000, 3000), (8100, 3000, 3000)),
        ])


def test_truss_axis_spread_accepts_reversed_source_line():
    plan = plan_trusses([
        ((0, 0, 3000), (8000, 0, 3000)),
        ((8000, 3000, 3000), (0, 3000, 3000)),
    ])
    assert plan["count"] == 2
    assert plan["representation"] == "ONE_TRUSS_AXIS_SPREAD"
    assert plan["items"][1]["baseline"]["start"] == pytest.approx([0.0, 3000.0, 3000.0])
    assert plan["items"][1]["baseline"]["end"] == pytest.approx([8000.0, 3000.0, 3000.0])


def test_purlin_plan_uses_one_frame_multiple_edges_and_c_profile():
    plan = plan_purlins([
        ((0, 0, 3500), (0, 6000, 3500)),
        ((2000, 0, 4000), (2000, 6000, 4000)),
    ])
    assert plan["count"] == 2
    assert plan["representation"] == "ONE_FRAME_MULTIPLE_EDGES"
    assert plan["profile"]["profile_type"] == "C"



def test_projected_purlins_follow_gable_roof_height_from_plan_lines():
    roof = plan_roof([(0, 0, 3500), (8000, 0, 3500), (8000, 6000, 3500), (0, 6000, 3500)])
    purlins = plan_projected_purlins(
        [
            ((0, 1000, 0), (8000, 1000, 0)),
            ((0, 3000, 0), (8000, 3000, 0)),
            ((0, 5000, 0), (8000, 5000, 0)),
        ],
        roof,
        {"layout_mode": "project_plan_to_gable"},
    )
    eave_z = 3500.0 + 1000.0 * math.tan(math.radians(20.0))
    ridge_z = 3500.0 + 3000.0 * math.tan(math.radians(20.0))
    assert purlins["representation"] == "PROJECTED_GABLE_LAYOUT"
    assert purlins["items"][0]["elevation_mm"] == pytest.approx(eave_z)
    assert purlins["items"][1]["elevation_mm"] == pytest.approx(ridge_z)
    assert purlins["items"][1]["roof_side"] == "RIDGE"
    assert purlins["items"][2]["elevation_mm"] == pytest.approx(eave_z)



def test_projected_purlins_support_rotated_rectangular_roof():
    angle = math.radians(30.0)
    ux, uy = math.cos(angle), math.sin(angle)
    vx, vy = -math.sin(angle), math.cos(angle)
    p0 = (0.0, 0.0, 3500.0)
    p1 = (8000.0 * ux, 8000.0 * uy, 3500.0)
    p2 = (p1[0] + 6000.0 * vx, p1[1] + 6000.0 * vy, 3500.0)
    p3 = (6000.0 * vx, 6000.0 * vy, 3500.0)
    roof = plan_roof([p0, p1, p2, p3])
    start = (1000.0 * vx, 1000.0 * vy, 0.0)
    end = (start[0] + 8000.0 * ux, start[1] + 8000.0 * uy, 0.0)
    purlins = plan_projected_purlins(
        [(start, end)], roof, {"layout_mode": "project_plan_to_gable"}
    )
    expected_z = 3500.0 + 1000.0 * math.tan(math.radians(20.0))
    assert purlins["items"][0]["elevation_mm"] == pytest.approx(expected_z)

def test_projected_purlins_have_opposite_upward_side_normals_and_bottom_contact_paths():
    roof = plan_roof([(0, 0, 3000), (8000, 0, 3000), (8000, 12000, 3000), (0, 12000, 3000)])
    purlins = plan_projected_purlins(
        [
            ((1000, 0, 0), (1000, 12000, 0)),
            ((7000, 12000, 0), (7000, 0, 0)),
        ],
        roof,
        {"layout_mode": "project_plan_to_gable"},
    )
    left, right = purlins["items"]
    assert purlins["frame_strategy"] == "ONE_FRAME_PER_ROOF_SIDE"
    assert left["support_path"] == left["path"]
    assert right["support_path"] == right["path"]
    assert left["plane_normal"][2] > 0.0
    assert right["plane_normal"][2] > 0.0
    assert left["plane_normal"][0] == pytest.approx(-right["plane_normal"][0])
    # La segunda linea se dibujo al reves, pero el path materializado queda canonico.
    assert right["path"]["end"][1] > right["path"]["start"][1]


def test_complete_projected_system_stacks_roof_on_top_of_purlins():
    plan = build_roof_system_plan(
        truss_segments=[
            ((0, 0, 3000), (8000, 0, 3000)),
            ((0, 6000, 3000), (8000, 6000, 3000)),
            ((0, 12000, 3000), (8000, 12000, 3000)),
        ],
        purlin_segments=[
            ((1000, 0, 0), (1000, 12000, 0)),
            ((2800, 0, 0), (2800, 12000, 0)),
            ((5200, 0, 0), (5200, 12000, 0)),
            ((7000, 0, 0), (7000, 12000, 0)),
        ],
        roof_outline=[(0, 0, 3000), (8000, 0, 3000), (8000, 12000, 3000), (0, 12000, 3000)],
        purlin_defaults={"layout_mode": "project_plan_to_gable", "profile_height_mm": 100.0},
    )
    stack = plan["roof"]["stacking"]
    expected_offset = 100.0 / math.cos(math.radians(20.0))
    assert plan["schema_version"] == 4
    assert plan["trusses"]["roof_coupled"] is True
    assert stack["mode"] == "TRUSS_PURLIN_ROOF"
    assert stack["roof_base_vertical_offset_mm"] == pytest.approx(expected_offset)
    assert stack["roof_base_outline"][0][2] == pytest.approx(3000.0 + expected_offset)


def test_complete_system_rejects_truss_level_not_on_master_surface():
    with pytest.raises(RoofPlanError, match="superficie maestra"):
        build_roof_system_plan(
            truss_segments=[((0, 0, 2850), (8000, 0, 2850))],
            purlin_segments=[((1000, 0, 0), (1000, 12000, 0))],
            roof_outline=[(0, 0, 3000), (8000, 0, 3000), (8000, 12000, 3000), (0, 12000, 3000)],
            purlin_defaults={"layout_mode": "project_plan_to_gable"},
        )


def test_projected_purlins_reject_nonparallel_line_to_ridge():
    roof = plan_roof([(0, 0, 3500), (8000, 0, 3500), (8000, 6000, 3500), (0, 6000, 3500)])
    with pytest.raises(RoofPlanError, match="paralelo"):
        plan_projected_purlins(
            [((1000, 0, 0), (1000, 6000, 0))],
            roof,
            {"layout_mode": "project_plan_to_gable"},
        )


def test_projected_purlins_reject_line_outside_eave_band():
    roof = plan_roof([(0, 0, 3500), (8000, 0, 3500), (8000, 6000, 3500), (0, 6000, 3500)])
    with pytest.raises(RoofPlanError, match="fuera"):
        plan_projected_purlins(
            [((0, 7000, 0), (8000, 7000, 0))],
            roof,
            {"layout_mode": "project_plan_to_gable"},
        )


def test_complete_plan_can_project_2d_purlins_to_gable_roof():
    plan = build_roof_system_plan(
        truss_segments=[((0, 0, 3500), (0, 6000, 3500)), ((4000, 0, 3500), (4000, 6000, 3500))],
        purlin_segments=[((0, 1000, 0), (8000, 1000, 0)), ((0, 5000, 0), (8000, 5000, 0))],
        roof_outline=[(0, 0, 3500), (8000, 0, 3500), (8000, 6000, 3500), (0, 6000, 3500)],
        purlin_defaults={"layout_mode": "project_plan_to_gable"},
    )
    assert plan["purlins"]["representation"] == "PROJECTED_GABLE_LAYOUT"
    assert plan["purlins"]["items"][0]["path"]["start"][2] > 3500.0
    json.dumps(plan)

def test_roof_outline_rejects_degenerate_polygon():
    with pytest.raises(RoofPlanError):
        plan_roof([(0, 0), (10, 0), (20, 0)])


def test_gable_roof_rectangle_maps_short_edges_to_gables():
    plan = plan_roof([(0, 0, 3500), (8000, 0, 3500), (8000, 6000, 3500), (0, 6000, 3500)])
    assert plan["roof_type"] == "gable"
    assert plan["native"]["gable_edge_indices"] == [1, 3]
    assert plan["native"]["eave_edge_indices"] == [0, 2]
    assert plan["native"]["angles"] == [20.0, 90.0, 20.0, 90.0]
    assert plan["native"]["runs"][0] == pytest.approx(3000.0)
    assert plan["native"]["runs"][2] == pytest.approx(3000.0)
    assert plan["native"]["ridge"]["rise_mm"] == pytest.approx(3000.0 * math.tan(math.radians(20.0)))


def test_square_gable_roof_requires_explicit_direction():
    with pytest.raises(RoofPlanError, match="ambigua"):
        plan_roof([(0, 0), (6000, 0), (6000, 6000), (0, 6000)])


def test_square_gable_roof_accepts_explicit_gable_edges():
    plan = plan_roof(
        [(0, 0), (6000, 0), (6000, 6000), (0, 6000)],
        {"gable_edge_indices": (0, 2), "slope_deg": 15.0},
    )
    assert plan["native"]["gable_edge_indices"] == [0, 2]
    assert plan["native"]["angles"] == [90.0, 15.0, 90.0, 15.0]


def test_complete_plan_is_json_serializable_and_geometric_only():
    plan = build_roof_system_plan(
        truss_segments=[
            ((0, 0, 3500), (0, 6000, 3500)),
            ((4000, 0, 3500), (4000, 6000, 3500)),
            ((8000, 0, 3500), (8000, 6000, 3500)),
        ],
        purlin_segments=[
            ((0, 1000, 3600), (8000, 1000, 3600)),
            ((0, 5000, 4000), (8000, 5000, 4000)),
        ],
        roof_outline=[(0, 0, 3500), (8000, 0, 3500), (8000, 6000, 3500), (0, 6000, 3500)],
        source_names={"trusses": "Sketch_Cerchas", "purlins": "Sketch_Clavadores", "roof": "Sketch_Cubierta"},
    )
    assert plan["schema_version"] == 4
    assert plan["structural_design_status"] == "GEOMETRIC_ONLY"
    assert plan["validation_status"] == "PENDING_FREECAD_MCP"
    assert plan["trusses"]["count"] == 3
    assert plan["purlins"]["count"] == 2
    assert plan["roof"]["edge_count"] == 4
    json.dumps(plan)

