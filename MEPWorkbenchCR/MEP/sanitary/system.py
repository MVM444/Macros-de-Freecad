"""
Nombre: system.py
Proposito: Orquestar calculos sanitarios sin depender de FreeCAD.
Funcionamiento: Ejecuta tanque septico, FAFA y drenaje; retorna resultado JSON-compatible y especificaciones geometricas preliminares.
Modificaciones futuras: Mantener el orquestador sin GUI; el adaptador FreeCAD debe consumir geometry_spec sin duplicar calculos.
Version: 0.3.0
Fecha: 2026-08-26
"""
from .septic import evaluate_rectangular_tank, commercial_septic_candidates
from .fafa import size_fafa, commercial_fafa_candidates
from .infiltration import size_infiltration_field, size_from_infiltration_tests
from .layout import layout_parallel_trenches


def _geometry_spec(data, septic, fafa, infiltration):
    """Contrato geometrico neutral; dimensiones en metros, sin importar FreeCAD."""
    s_in = data["septic"]
    f_in = data["fafa"]
    inf_in = data["infiltration"]
    trench_count = infiltration.data.get("minimum_trench_count", 0)
    trench_len = infiltration.data.get("equal_trench_length_m", 0.0)
    return {
        "septic_tank": {
            "shape": "rectangular_tank",
            "length_m": s_in.get("length_m"),
            "width_m": s_in.get("width_m"),
            "liquid_depth_m": s_in.get("liquid_depth_m"),
            "freeboard_m": s_in.get("freeboard_m"),
            "total_internal_height_m": septic.data.get("total_internal_height_m"),
        },
        "fafa": {
            "shape": "rectangular_filter",
            "required_plan_area_m2": fafa.data.get("required_plan_area_m2"),
            "media_height_m": f_in.get("media_height_m"),
            "media_bed_volume_m3": fafa.data.get("media_bed_volume_m3"),
        },
        "infiltration_field": {
            "shape": "parallel_trenches",
            "trench_count": trench_count,
            "equal_trench_length_m": trench_len,
            "width_m": inf_in.get("width_m", 0.50),
            "gravel_depth_m": inf_in.get("gravel_depth_m", 0.30),
            "center_spacing_m": max(
                infiltration.data.get("minimum_center_spacing_m", 0.0),
                infiltration.data.get("annex3_spacing_formula_m", 0.0),
            ),
            "trench_slope_percent": 0.0,
            "layout_rule": infiltration.data.get("layout_rule"),
        },
    }


def calculate_system(data):
    septic = evaluate_rectangular_tank(**data["septic"])
    fafa = size_fafa(**data["fafa"])

    inf_data = dict(data["infiltration"])
    tests = inf_data.pop("tests_min_cm", None)
    if tests is not None:
        infiltration = size_from_infiltration_tests(
            flow_l_day=inf_data.pop("flow_l_day"), tests_min_cm=tests, **inf_data
        )
    else:
        infiltration = size_infiltration_field(**inf_data)

    result = {
        "project": data.get("project", ""),
        "septic": septic.to_dict(),
        "fafa": fafa.to_dict(),
        "infiltration": infiltration.to_dict(),
        "ok": septic.ok and fafa.ok and infiltration.ok,
    }

    result["commercial_references"] = {
        "septic": commercial_septic_candidates(septic.data.get("required_volume_m3", 0.0)),
        "fafa": commercial_fafa_candidates(fafa.data.get("media_bed_volume_m3", 0.0)),
        "status": "REFERENCE_ONLY",
    }
    result["geometry_spec"] = _geometry_spec(data, septic, fafa, infiltration)

    # Optional neutral site layout. This does not write to FreeCAD and only
    # operates when a simple rectangular available area was explicitly supplied.
    site = data.get("site") or {}
    if site.get("available_length_m") is not None and site.get("available_width_m") is not None:
        inf_spec = result["geometry_spec"]["infiltration_field"]
        layout = layout_parallel_trenches(
            required_total_length_m=infiltration.data.get("required_total_trench_length_m", 0.0),
            available_length_m=site["available_length_m"],
            available_width_m=site["available_width_m"],
            trench_width_m=inf_spec["width_m"],
            center_spacing_m=inf_spec["center_spacing_m"],
            terrain_slope_percent=infiltration.data.get("terrain_slope_percent", 0.0),
        )
        result["site_layout"] = layout.to_dict()
        result["ok"] = result["ok"] and layout.ok
    else:
        result["site_layout"] = {
            "ok": True,
            "data": {"status": "NOT_REQUESTED"},
            "messages": [],
        }
    return result
