"""
Nombre: infiltration.py
Proposito: Calculo reglamentario preliminar del campo de infiltracion por zanjas.
Funcionamiento: Convierte la prueba de infiltracion a Vp usando la Tabla 2 del Anexo 3, valida geometria y calcula area, separacion y longitud.
Modificaciones futuras: Mantener separada la optimizacion espacial FreeCAD; no sustituir la prueba de campo ni el criterio profesional.
Version: 0.2.1
Fecha: 2026-08-26
"""
import math
from .models import CalculationResult, ValidationMessage

MIN_WIDTH_M = 0.30
MAX_WIDTH_M = 0.90
MIN_GRAVEL_DEPTH_M = 0.30
MAX_GRAVEL_DEPTH_M = 0.90
MIN_CENTER_SPACING_M = 1.80
MAX_TRENCH_LENGTH_M = 60.0
MIN_GROUNDWATER_CLEARANCE_M = 1.50
MIN_PRECIPITATION_FACTOR = 2.5
MIN_INFILTRATION_RATE_MIN_CM = 2.0
MAX_INFILTRATION_RATE_MIN_CM = 24.0

# Decreto Ejecutivo 42075-S-MINAE, Anexo 3, Tabla 2.
# Tasa T [min/cm] -> Vp [L/m2/dia].
APPLICATION_RATE_TABLE_L_M2_DAY = {
    2: 90.33, 3: 73.76, 4: 63.88, 5: 57.13, 6: 52.15, 7: 48.28,
    8: 45.17, 9: 42.58, 10: 40.40, 11: 38.52, 12: 36.88, 13: 35.43,
    14: 34.14, 15: 32.98, 16: 31.94, 17: 30.98, 18: 30.11, 19: 29.31,
    20: 28.57, 21: 27.88, 22: 27.24, 23: 26.64, 24: 26.08,
}


def infiltration_rate_min_cm(drop_cm, interval_minutes=30.0):
    """Calcula T con la lectura del ultimo intervalo, como exige el Anexo 3."""
    if drop_cm <= 0 or interval_minutes <= 0:
        raise ValueError("Descenso e intervalo deben ser mayores que cero")
    return interval_minutes / drop_cm


def application_rate_from_test(t_min_cm, conservative=True):
    """Obtiene Vp de Tabla 2. Para T no entero usa la fila superior por conservadurismo."""
    if not MIN_INFILTRATION_RATE_MIN_CM <= t_min_cm <= MAX_INFILTRATION_RATE_MIN_CM:
        return CalculationResult(False, messages=[ValidationMessage(
            "ERROR", "INFILTRATION_RATE_NOT_ALLOWED",
            "La tasa de infiltracion debe estar entre 2 y 24 min/cm para usar zanjas"
        )])
    if conservative:
        table_t = min(24, max(2, int(math.ceil(t_min_cm))))
        vp = APPLICATION_RATE_TABLE_L_M2_DAY[table_t]
        method = "ANEXO3_TABLE2_CONSERVATIVE_CEIL"
    else:
        low = int(math.floor(t_min_cm))
        high = int(math.ceil(t_min_cm))
        if low == high:
            vp = APPLICATION_RATE_TABLE_L_M2_DAY[low]
        else:
            v0 = APPLICATION_RATE_TABLE_L_M2_DAY[low]
            v1 = APPLICATION_RATE_TABLE_L_M2_DAY[high]
            vp = v0 + (v1 - v0) * ((t_min_cm - low) / (high - low))
        table_t = t_min_cm
        method = "ANEXO3_TABLE2_LINEAR_INTERPOLATION"
    return CalculationResult(True, {
        "infiltration_rate_min_cm": t_min_cm,
        "table_rate_min_cm": table_t,
        "application_rate_l_m2_day": vp,
        "method": method,
    })



def evaluate_field_infiltration_test(interval_drops_cm, interval_minutes=30.0, saturation_hours=24.0):
    """Evalua una prueba de campo del Anexo 3 a partir de los 8 descensos por intervalo."""
    drops = [float(v) for v in interval_drops_cm]
    msgs = []
    if len(drops) != 8:
        return CalculationResult(False, {"interval_count": len(drops)}, [ValidationMessage(
            "ERROR", "INFILTRATION_INTERVAL_COUNT", "La prueba debe contener 8 intervalos de medicion"
        )])
    if saturation_hours < 24.0:
        msgs.append(ValidationMessage(
            "ERROR", "INFILTRATION_SATURATION_TIME", "El terreno debe saturarse por al menos 24 horas"
        ))
    if any(v <= 0 for v in drops):
        msgs.append(ValidationMessage(
            "ERROR", "INFILTRATION_DROP_INVALID", "Todos los descensos deben ser mayores que cero"
        ))
    if msgs:
        return CalculationResult(False, {"interval_drops_cm": drops}, msgs)
    last_drop = drops[-1]
    t = infiltration_rate_min_cm(last_drop, interval_minutes)
    vp = application_rate_from_test(t, conservative=True)
    data = {
        "interval_drops_cm": drops,
        "interval_minutes": interval_minutes,
        "saturation_hours": saturation_hours,
        "last_interval_drop_cm": last_drop,
        "infiltration_rate_min_cm": t,
    }
    data.update(vp.data)
    return CalculationResult(vp.ok, data, msgs + vp.messages)

def select_design_infiltration_test(tests_min_cm):
    """Selecciona la prueba mas lenta (mayor min/cm) como criterio conservador."""
    vals = [float(v) for v in tests_min_cm]
    if len(vals) < 2:
        return CalculationResult(False, messages=[ValidationMessage(
            "ERROR", "INFILTRATION_TEST_COUNT", "Se requieren al menos dos pruebas de infiltracion"
        )])
    invalid = [v for v in vals if not MIN_INFILTRATION_RATE_MIN_CM <= v <= MAX_INFILTRATION_RATE_MIN_CM]
    if invalid:
        return CalculationResult(False, {"tests_min_cm": vals}, [ValidationMessage(
            "ERROR", "INFILTRATION_TEST_NOT_ALLOWED",
            "Una o mas pruebas estan fuera del intervalo permitido de 2-24 min/cm"
        )])
    design_t = max(vals)
    vp_result = application_rate_from_test(design_t, conservative=True)
    data = {"tests_min_cm": vals, "design_test_min_cm": design_t, **vp_result.data}
    return CalculationResult(vp_result.ok, data, vp_result.messages)


def effective_perimeter_m(width_m, gravel_depth_m):
    w_cm = width_m * 100.0
    d_cm = gravel_depth_m * 100.0
    return 0.77 * ((w_cm + 56.0 + 2.0 * d_cm) / (w_cm + 116.0))


def size_infiltration_field(flow_l_day, application_rate_l_m2_day, width_m=0.50, gravel_depth_m=0.30,
                            precipitation_factor=MIN_PRECIPITATION_FACTOR, groundwater_clearance_m=None,
                            center_spacing_m=None, terrain_slope_percent=0.0):
    msgs = []
    if flow_l_day <= 0 or application_rate_l_m2_day <= 0:
        return CalculationResult(False, messages=[ValidationMessage("ERROR", "INVALID_INPUT", "Gasto y Vp deben ser mayores que cero")])
    if not MIN_WIDTH_M <= width_m <= MAX_WIDTH_M:
        msgs.append(ValidationMessage("ERROR", "TRENCH_WIDTH", "Ancho de zanja fuera de 0.30-0.90 m"))
    if not MIN_GRAVEL_DEPTH_M <= gravel_depth_m <= MAX_GRAVEL_DEPTH_M:
        msgs.append(ValidationMessage("ERROR", "GRAVEL_DEPTH", "Profundidad D fuera de 0.30-0.90 m"))
    if precipitation_factor < MIN_PRECIPITATION_FACTOR:
        msgs.append(ValidationMessage("ERROR", "PRECIPITATION_FACTOR", "Factor de precipitacion menor a 2.5"))
    if groundwater_clearance_m is not None and groundwater_clearance_m < MIN_GROUNDWATER_CLEARANCE_M:
        msgs.append(ValidationMessage("ERROR", "GROUNDWATER_CLEARANCE", "Separacion al nivel freatico menor a 1.50 m"))
    if terrain_slope_percent < 0 or terrain_slope_percent > 30:
        msgs.append(ValidationMessage("ERROR", "TERRAIN_SLOPE", "Las zanjas no se permiten con pendiente de terreno mayor a 30%"))

    if terrain_slope_percent > 1.0:
        min_spacing = 5.0
        layout_rule = "FOLLOW_CONTOURS"
    else:
        min_spacing = max(width_m + 1.50, MIN_CENTER_SPACING_M)
        layout_rule = "PARALLEL_OR_SERIES"
    if center_spacing_m is not None and center_spacing_m < min_spacing:
        msgs.append(ValidationMessage("ERROR", "TRENCH_SPACING", f"Separacion centro-centro menor a {min_spacing:.2f} m"))

    base_area = flow_l_day / application_rate_l_m2_day
    required_site_surface = base_area * precipitation_factor
    pe = effective_perimeter_m(width_m, gravel_depth_m)
    total_length = base_area / pe
    ls_formula = required_site_surface / total_length if total_length > 0 else 0.0
    minimum_trench_count = max(1, int(math.ceil(total_length / MAX_TRENCH_LENGTH_M)))
    equal_trench_length = total_length / minimum_trench_count

    return CalculationResult(not any(m.level == "ERROR" for m in msgs), {
        "flow_l_day": flow_l_day,
        "application_rate_l_m2_day": application_rate_l_m2_day,
        "basic_infiltration_area_m2": base_area,
        "precipitation_factor": precipitation_factor,
        "required_site_surface_m2": required_site_surface,
        "effective_perimeter_m": pe,
        "required_total_trench_length_m": total_length,
        "annex3_spacing_formula_m": ls_formula,
        "minimum_center_spacing_m": min_spacing,
        "layout_rule": layout_rule,
        "terrain_slope_percent": terrain_slope_percent,
        "maximum_single_trench_length_m": MAX_TRENCH_LENGTH_M,
        "minimum_trench_count": minimum_trench_count,
        "equal_trench_length_m": equal_trench_length,
        "trench_slope_percent": 0.0,
    }, msgs)


def size_from_infiltration_tests(flow_l_day, tests_min_cm, **kwargs):
    """Atajo reglamentario: dos o mas pruebas -> T de diseno -> Vp -> campo."""
    test_result = select_design_infiltration_test(tests_min_cm)
    if not test_result.ok:
        return test_result
    field = size_infiltration_field(
        flow_l_day, test_result.data["application_rate_l_m2_day"], **kwargs
    )
    data = {**test_result.data, **field.data}
    return CalculationResult(field.ok, data, test_result.messages + field.messages)
