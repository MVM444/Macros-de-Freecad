"""
Nombre: layout.py
Proposito: Distribucion geometrica neutral de zanjas sanitarias dentro de un area rectangular util.
Funcionamiento: Calcula cantidad de ramales y coordenadas locales respetando longitud maxima y separacion entre centros.
Modificaciones futuras: Agregar poligonos arbitrarios, obstaculos y orientacion por curvas de nivel en modulo separado.
Version: 0.1.0
Fecha: 2026-08-26
"""
import math
from .models import CalculationResult, ValidationMessage

MAX_TRENCH_LENGTH_M = 60.0


def layout_parallel_trenches(required_total_length_m, available_length_m, available_width_m,
                              trench_width_m, center_spacing_m, max_single_length_m=MAX_TRENCH_LENGTH_M,
                              terrain_slope_percent=0.0):
    vals = [required_total_length_m, available_length_m, available_width_m, trench_width_m, center_spacing_m]
    if any(v <= 0 for v in vals):
        return CalculationResult(False, messages=[ValidationMessage(
            "ERROR", "LAYOUT_INVALID_INPUT", "Longitudes, ancho y separacion deben ser mayores que cero"
        )])
    usable_single_length = min(available_length_m, max_single_length_m)
    if usable_single_length <= 0:
        return CalculationResult(False, messages=[ValidationMessage("ERROR", "LAYOUT_NO_LENGTH", "No existe longitud util")])

    required_count = int(math.ceil(required_total_length_m / usable_single_length))
    max_count_width = 1 + int(math.floor(max(0.0, available_width_m - trench_width_m) / center_spacing_m))
    if required_count > max_count_width:
        return CalculationResult(False, {
            "required_trench_count": required_count,
            "maximum_trench_count_by_width": max_count_width,
            "required_total_length_m": required_total_length_m,
        }, [ValidationMessage(
            "ERROR", "LAYOUT_DOES_NOT_FIT",
            "La longitud requerida no cabe en el rectangulo disponible respetando separacion y longitud maxima"
        )])

    count = max(1, required_count)
    equal_length = required_total_length_m / count
    if equal_length > usable_single_length + 1e-9:
        return CalculationResult(False, messages=[ValidationMessage("ERROR", "LAYOUT_LENGTH_EXCEEDED", "Longitud individual excedida")])

    used_width = trench_width_m + (count - 1) * center_spacing_m
    y0 = max(0.0, (available_width_m - used_width) / 2.0)
    x0 = max(0.0, (available_length_m - equal_length) / 2.0)
    trenches = []
    for idx in range(count):
        y = y0 + idx * center_spacing_m
        trenches.append({
            "index": idx + 1,
            "start_m": [x0, y],
            "end_m": [x0 + equal_length, y],
            "length_m": equal_length,
            "width_m": trench_width_m,
        })

    return CalculationResult(True, {
        "available_length_m": available_length_m,
        "available_width_m": available_width_m,
        "required_total_length_m": required_total_length_m,
        "trench_count": count,
        "equal_trench_length_m": equal_length,
        "center_spacing_m": center_spacing_m,
        "used_width_m": used_width,
        "terrain_slope_percent": terrain_slope_percent,
        "orientation_rule": "FOLLOW_CONTOURS" if terrain_slope_percent > 1.0 else "FREE_PARALLEL",
        "trenches": trenches,
    })
