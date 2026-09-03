"""
Nombre: test_sanitary_core.py
Proposito: Pruebas unitarias del nucleo sanitario independiente de FreeCAD.
Funcionamiento: Importa MEP.sanitary desde la raiz del Workbench y comprueba casos base.
Modificaciones futuras: Mantener estas pruebas sin dependencia de FreeCADGui ni Qt.
Version: 0.3.0
Fecha: 2026-08-26
"""
import sys
from pathlib import Path

WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
if str(WORKBENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKBENCH_ROOT))

from MEP.sanitary.septic import evaluate_rectangular_tank, commercial_septic_candidates
from MEP.sanitary.fafa import size_fafa, commercial_fafa_candidates
from MEP.sanitary.infiltration import (size_infiltration_field, infiltration_rate_min_cm, application_rate_from_test, select_design_infiltration_test, size_from_infiltration_tests, evaluate_field_infiltration_test)
from MEP.sanitary.system import calculate_system
from MEP.sanitary.layout import layout_parallel_trenches
from MEP.sanitary.freecad_adapter import create_preview_objects, preview_plan
from MEP.sanitary.freecad_objects import create_septic_tank, create_fafa, create_infiltration_trench
from MEP.sanitary.documentation import build_plan_documentation, build_section_documentation, render_svg
from MEP.sanitary.case import validate_case_input, calculate_case


def test_septic_valid_case():
    r = evaluate_rectangular_tank(1.2, 3.0, 1.0, 1.2, 0.30)
    assert r.ok
    assert round(r.data['useful_volume_m3'], 3) == 3.6


def test_septic_bad_ratio():
    r = evaluate_rectangular_tank(1.0, 2.0, 1.0, 1.0, 0.30)
    assert not r.ok
    assert any(m.code == 'SEPTIC_RATIO' for m in r.messages)


def test_fafa_preliminary_without_bod():
    r = size_fafa(1.2, media_height_m=1.2)
    assert r.ok
    assert any(m.code == 'FAFA_BOD_MISSING' for m in r.messages)


def test_fafa_with_bod():
    r = size_fafa(1.2, media_height_m=1.2, influent_bod_mg_l=150)
    assert r.ok
    assert 'organic_loading_kg_bod_m3_day' in r.data


def test_infiltration_geometry():
    r = size_infiltration_field(1200, 30, width_m=0.50, gravel_depth_m=0.30,
                                groundwater_clearance_m=1.5, center_spacing_m=2.0)
    assert r.ok
    assert r.data['trench_slope_percent'] == 0.0
    assert r.data['required_total_trench_length_m'] > 0


def test_infiltration_table_2_values():
    assert infiltration_rate_min_cm(15.0, 30.0) == 2.0
    r = application_rate_from_test(2.0)
    assert r.ok
    assert r.data["application_rate_l_m2_day"] == 90.33
    r24 = application_rate_from_test(24.0)
    assert r24.data["application_rate_l_m2_day"] == 26.08


def test_infiltration_rejects_outside_2_24():
    assert not application_rate_from_test(1.9).ok
    assert not application_rate_from_test(24.1).ok


def test_design_infiltration_uses_slowest_of_two_tests():
    r = select_design_infiltration_test([8.2, 12.4])
    assert r.ok
    assert r.data["design_test_min_cm"] == 12.4
    assert r.data["table_rate_min_cm"] == 13
    assert r.data["application_rate_l_m2_day"] == 35.43


def test_size_directly_from_tests():
    r = size_from_infiltration_tests(1200, [8, 10], groundwater_clearance_m=1.5)
    assert r.ok
    assert r.data["application_rate_l_m2_day"] == 40.40
    assert r.data["minimum_trench_count"] >= 1


def test_sloped_site_uses_five_meter_spacing():
    r = size_infiltration_field(1200, 30, terrain_slope_percent=5.0, center_spacing_m=5.0)
    assert r.ok
    assert r.data["minimum_center_spacing_m"] == 5.0
    assert r.data["layout_rule"] == "FOLLOW_CONTOURS"


def test_commercial_references_are_preliminary():
    assert commercial_septic_candidates(2.5)[0]["model"] == "TS-3000"
    assert commercial_fafa_candidates(1.5)[0]["model"] == "FAFA-1600"
    assert commercial_septic_candidates(4.0) == []


def test_system_geometry_and_adapter_dry_run():
    data = {
        "project": "Esparza_TEST",
        "septic": {"design_flow_m3_day": 1.2, "length_m": 3.0, "width_m": 1.0, "liquid_depth_m": 1.2, "freeboard_m": 0.30},
        "fafa": {"design_flow_m3_day": 1.2, "media_height_m": 1.2, "influent_bod_mg_l": 150},
        "infiltration": {"flow_l_day": 1200, "tests_min_cm": [8, 10], "groundwater_clearance_m": 1.5},
    }
    result = calculate_system(data)
    assert result["ok"]
    assert result["geometry_spec"]["infiltration_field"]["trench_count"] >= 1
    preview = create_preview_objects(None, result, dry_run=True)
    assert preview["dry_run"]
    assert any(op["name"] == "MEP_SepticTank" for op in preview["operations"])


def test_field_infiltration_uses_eighth_interval():
    r = evaluate_field_infiltration_test([3,3,3,3,3,3,3,3], saturation_hours=24)
    assert r.ok
    assert r.data["infiltration_rate_min_cm"] == 10.0
    assert r.data["application_rate_l_m2_day"] == 40.40


def test_field_infiltration_requires_8_intervals_and_24h_saturation():
    assert not evaluate_field_infiltration_test([3]*7, saturation_hours=24).ok
    assert not evaluate_field_infiltration_test([3]*8, saturation_hours=12).ok


def test_septic_outlet_submergence_requirement():
    r = evaluate_rectangular_tank(1.0, 3.0, 1.0, 1.2, 0.30, outlet_submergence_m=0.30)
    assert not r.ok
    assert any(m.code == "SEPTIC_OUTLET_SUBMERGENCE" for m in r.messages)
    good = evaluate_rectangular_tank(1.0, 3.0, 1.0, 1.2, 0.30, outlet_submergence_m=0.40, inlet_diameter_m=0.10, outlet_diameter_m=0.10, cover_opening_m=0.60, soil_cover_m=0.15)
    assert good.ok


def test_rectangular_layout_fits_and_centers():
    r = layout_parallel_trenches(48.0, 15.0, 8.0, 0.50, 2.0)
    assert r.ok
    assert r.data["trench_count"] == 4
    assert round(r.data["equal_trench_length_m"], 3) == 12.0
    assert len(r.data["trenches"]) == 4


def test_rectangular_layout_reports_not_fit():
    r = layout_parallel_trenches(100.0, 10.0, 4.0, 0.50, 2.0)
    assert not r.ok
    assert any(m.code == "LAYOUT_DOES_NOT_FIT" for m in r.messages)


def test_system_optional_site_layout():
    data = {
        "project": "Esparza_LAYOUT_TEST",
        "septic": {"design_flow_m3_day": 1.2, "length_m": 3.0, "width_m": 1.0, "liquid_depth_m": 1.2, "freeboard_m": 0.30},
        "fafa": {"design_flow_m3_day": 1.2, "media_height_m": 1.2, "influent_bod_mg_l": 150},
        "infiltration": {"flow_l_day": 1200, "tests_min_cm": [8, 10], "groundwater_clearance_m": 1.5},
        "site": {"available_length_m": 30.0, "available_width_m": 20.0},
    }
    result = calculate_system(data)
    assert result["site_layout"]["ok"]
    assert result["site_layout"]["data"]["trench_count"] >= 1


def test_adapter_uses_site_layout_coordinates():
    data = {
        "project": "Esparza_LAYOUT_PREVIEW",
        "septic": {"design_flow_m3_day": 1.2, "length_m": 3.0, "width_m": 1.0, "liquid_depth_m": 1.2, "freeboard_m": 0.30},
        "fafa": {"design_flow_m3_day": 1.2, "media_height_m": 1.2, "influent_bod_mg_l": 150},
        "infiltration": {"flow_l_day": 1200, "tests_min_cm": [8, 10], "groundwater_clearance_m": 1.5},
        "site": {"available_length_m": 30.0, "available_width_m": 20.0},
    }
    result = calculate_system(data)
    ops = preview_plan(result)
    trenches = [op for op in ops if op["name"].startswith("MEP_InfiltrationTrench_")]
    assert len(trenches) == result["site_layout"]["data"]["trench_count"]
    assert any("rectangulo disponible" in op.get("note", "") for op in trenches)


def test_parametric_object_creators_are_dry_run_safe():
    septic = create_septic_tank(None, Length=3.0, Width=1.0, LiquidDepth=1.2, Freeboard=0.30)
    fafa = create_fafa(None, Length=2.0, Width=1.0, MediaHeight=1.2)
    trench = create_infiltration_trench(None, Length=12.0, Width=0.5, GravelDepth=0.30)
    assert septic["object_type"] == "Part::FeaturePython"
    assert septic["component_type"] == "SANITARY_SEPTIC_TANK"
    assert fafa["component_type"] == "SANITARY_FAFA"
    assert trench["component_type"] == "SANITARY_INFILTRATION_TRENCH"


def test_documentation_plan_section_and_svg():
    data = {
        "project": "Esparza_DOC_TEST",
        "septic": {"design_flow_m3_day": 1.2, "length_m": 3.0, "width_m": 1.0, "liquid_depth_m": 1.2, "freeboard_m": 0.30},
        "fafa": {"design_flow_m3_day": 1.2, "media_height_m": 1.2, "influent_bod_mg_l": 150},
        "infiltration": {"flow_l_day": 1200, "tests_min_cm": [8, 10], "groundwater_clearance_m": 1.5},
        "site": {"available_length_m": 30.0, "available_width_m": 20.0},
    }
    result = calculate_system(data)
    plan = build_plan_documentation(result)
    section = build_section_documentation(result)
    assert plan["view"] == "PLAN" and plan["primitives"]
    assert section["view"] == "SECTION" and section["primitives"]
    svg = render_svg(plan)
    assert svg.startswith("<svg") and "MEP_SepticTank" in svg


def test_incomplete_esparza_template_is_safe():
    incomplete = {
        "project": "Sucursal Esparza - sanitario",
        "septic": {"design_flow_m3_day": None, "length_m": None, "width_m": None, "liquid_depth_m": None, "freeboard_m": 0.30},
        "fafa": {"design_flow_m3_day": None, "media_height_m": None},
        "infiltration": {"flow_l_day": None, "tests_min_cm": [None, None], "groundwater_clearance_m": None},
        "site": {"available_length_m": None, "available_width_m": None},
    }
    validation = validate_case_input(incomplete)
    assert not validation["ready_for_calculation"]
    result = calculate_case(incomplete)
    assert result["status"] == "INPUT_INCOMPLETE"
    assert "septic.design_flow_m3_day" in result["input_validation"]["missing"]


from MEP.sanitary.boundary import Boundary2D
from MEP.sanitary.spatial import validate_spatial_references

def test_boundary2d_rectangle_metrics():
    b = Boundary2D.from_points("lot", "PROPERTY_BOUNDARY", [(0,0),(20,0),(20,10),(0,10)])
    assert round(b.area, 3) == 200.0
    assert round(b.perimeter, 3) == 60.0
    assert b.to_dict()["closed"] is True


def test_boundary2d_rejects_self_intersection():
    try:
        Boundary2D.from_points("bad", "DRAINAGE_AREA", [(0,0),(4,4),(0,4),(4,0)])
    except ValueError as exc:
        assert "autointersecta" in str(exc)
    else:
        raise AssertionError("Se esperaba ValueError")


def test_spatial_references_valid_case():
    lot = Boundary2D.from_points("lot", "PROPERTY_BOUNDARY", [(0,0),(30,0),(30,20),(0,20)])
    building = Boundary2D.from_points("bld", "BUILDING_FOOTPRINT", [(2,2),(12,2),(12,8),(2,8)])
    tanks = Boundary2D.from_points("tank", "TANKS_AREA", [(15,2),(22,2),(22,7),(15,7)])
    drainage = Boundary2D.from_points("drn", "DRAINAGE_AREA", [(14,10),(28,10),(28,19),(14,19)])
    r = validate_spatial_references(lot, building, tanks, drainage)
    assert r.ok
    assert r.data["ready_for_layout"] is True


def test_spatial_references_detect_building_overlap():
    lot = Boundary2D.from_points("lot", "PROPERTY_BOUNDARY", [(0,0),(30,0),(30,20),(0,20)])
    building = Boundary2D.from_points("bld", "BUILDING_FOOTPRINT", [(2,2),(12,2),(12,8),(2,8)])
    drainage = Boundary2D.from_points("drn", "DRAINAGE_AREA", [(10,6),(20,6),(20,15),(10,15)])
    r = validate_spatial_references(lot, building_footprint=building, drainage_area=drainage)
    assert not r.ok
    assert any(m.code == "DRAINAGE_AREA_INTERSECTS_BUILDING" for m in r.messages)
