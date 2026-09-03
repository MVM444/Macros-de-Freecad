"""
Nombre: case.py
Proposito: Validacion de casos sanitarios antes de ejecutar calculos.
Funcionamiento: Detecta datos faltantes/invalidos en plantillas como Esparza y
  ejecuta calculate_system solamente cuando el caso esta listo.
Modificaciones futuras: Agregar perfiles de entrada por modo (tanque existente,
  tanque nuevo, FAFA comercial) sin incorporar GUI al nucleo.
Version: 0.1.0
Fecha: 2026-08-26
"""
from .system import calculate_system


REQUIRED_PATHS = (
    "septic.design_flow_m3_day",
    "septic.length_m",
    "septic.width_m",
    "septic.liquid_depth_m",
    "septic.freeboard_m",
    "fafa.design_flow_m3_day",
    "fafa.media_height_m",
    "infiltration.flow_l_day",
    "infiltration.groundwater_clearance_m",
)


def _get(data, path):
    value = data
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def validate_case_input(data):
    missing = [path for path in REQUIRED_PATHS if _get(data, path) is None]
    invalid = []
    for path in REQUIRED_PATHS:
        value = _get(data, path)
        if value is not None:
            try:
                if float(value) <= 0:
                    invalid.append(path)
            except (TypeError, ValueError):
                invalid.append(path)

    infiltration = data.get("infiltration", {}) if isinstance(data, dict) else {}
    tests = infiltration.get("tests_min_cm")
    direct_vp = infiltration.get("application_rate_l_m2_day")
    if direct_vp is None:
        if not isinstance(tests, (list, tuple)) or len(tests) < 2 or any(v is None for v in tests):
            missing.append("infiltration.tests_min_cm>=2_or_application_rate_l_m2_day")

    # Site dimensions are optional: without them the hydraulic/drain sizing can
    # run, but an automatic rectangular layout is not requested.
    site = data.get("site", {}) if isinstance(data, dict) else {}
    layout_ready = site.get("available_length_m") is not None and site.get("available_width_m") is not None

    ready = not missing and not invalid
    return {
        "ready_for_calculation": ready,
        "missing": sorted(set(missing)),
        "invalid": sorted(set(invalid)),
        "layout_ready": bool(layout_ready),
        "project": data.get("project", "") if isinstance(data, dict) else "",
    }


def calculate_case(data):
    validation = validate_case_input(data)
    if not validation["ready_for_calculation"]:
        return {
            "ok": False,
            "status": "INPUT_INCOMPLETE",
            "input_validation": validation,
            "project": validation["project"],
        }
    result = calculate_system(data)
    result["input_validation"] = validation
    result["status"] = "CALCULATED" if result.get("ok") else "CALCULATED_WITH_ERRORS"
    return result
