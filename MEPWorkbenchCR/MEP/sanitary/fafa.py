"""
Nombre: fafa.py
Proposito: Dimensionamiento hidraulico preliminar y validacion de FAFA post-tanque septico.
Funcionamiento: Dimensiona por TRH, corrige por porosidad y verifica carga organica volumetrica cuando hay DBO.
Modificaciones futuras: Agregar perdida de carga, distribucion inferior y eficiencia solo con metodologia documentada.
Version: 0.2.0
Fecha: 2026-08-26
"""
from .models import CalculationResult, ValidationMessage

DEFAULT_TRH_H = 8.0
REFERENCE_TRH_MIN_H = 4.0
REFERENCE_TRH_MAX_H = 10.0
DEFAULT_VOID_RATIO = 0.70
REFERENCE_OLR_MIN = 0.15
REFERENCE_OLR_MAX = 0.50


def size_fafa(design_flow_m3_day, media_height_m, trh_h=DEFAULT_TRH_H, void_ratio=DEFAULT_VOID_RATIO, influent_bod_mg_l=None):
    msgs = []
    if design_flow_m3_day <= 0 or media_height_m <= 0:
        return CalculationResult(False, messages=[ValidationMessage("ERROR", "INVALID_INPUT", "Caudal y altura del medio deben ser mayores que cero")])
    if not 0 < void_ratio <= 1:
        return CalculationResult(False, messages=[ValidationMessage("ERROR", "INVALID_VOID_RATIO", "La porosidad debe estar entre 0 y 1")])
    hydraulic_volume = design_flow_m3_day * trh_h / 24.0
    media_bed_volume = hydraulic_volume / void_ratio
    plan_area = media_bed_volume / media_height_m
    upflow_velocity_m_h = (design_flow_m3_day / 24.0) / plan_area
    if not REFERENCE_TRH_MIN_H <= trh_h <= REFERENCE_TRH_MAX_H:
        msgs.append(ValidationMessage("WARNING", "FAFA_TRH_REFERENCE", "TRH fuera del intervalo de referencia 4-10 h; documentar metodologia usada"))
    data = {
        "design_flow_m3_day": design_flow_m3_day,
        "trh_h": trh_h,
        "hydraulic_volume_m3": hydraulic_volume,
        "void_ratio": void_ratio,
        "media_bed_volume_m3": media_bed_volume,
        "media_height_m": media_height_m,
        "required_plan_area_m2": plan_area,
        "upflow_velocity_m_h": upflow_velocity_m_h,
    }
    if influent_bod_mg_l is None:
        msgs.append(ValidationMessage("WARNING", "FAFA_BOD_MISSING", "Sin DBO post-tanque: calculo hidraulico valido como preliminar; falta verificacion organica"))
    else:
        bod_kg_m3 = influent_bod_mg_l / 1000.0
        olr = design_flow_m3_day * bod_kg_m3 / media_bed_volume
        data["influent_bod_mg_l"] = influent_bod_mg_l
        data["organic_loading_kg_bod_m3_day"] = olr
        if not REFERENCE_OLR_MIN <= olr <= REFERENCE_OLR_MAX:
            msgs.append(ValidationMessage("WARNING", "FAFA_OLR_REFERENCE", f"Carga organica {olr:.3f} kg DBO/m3.d fuera de 0.15-0.50; revisar criterio de diseno"))
    return CalculationResult(True, data, msgs)


# Referencias comerciales documentadas; el volumen nominal no equivale necesariamente
# al volumen util de medio filtrante. La seleccion siempre queda como preliminar.
COMMERCIAL_FAFA_REFERENCES = [
    {
        "manufacturer": "Fibromuebles",
        "model": "FAFA-1600",
        "nominal_volume_m3": 1.6,
        "length_m": 2.25,
        "width_m": 1.05,
        "media_type": "piedra_cuarta",
        "connection_nominal_in": 4.0,
        "vent_nominal_in": 2.0,
        "reference": "TSM-3000_v2018-1.pdf",
        "checked_date": "2026-08-26",
        "selection_status": "REFERENCE_ONLY",
    },
]


def commercial_fafa_candidates(required_media_bed_volume_m3):
    """Filtro preliminar por volumen nominal; requiere verificacion con ficha del fabricante."""
    if required_media_bed_volume_m3 <= 0:
        return []
    return [dict(item) for item in COMMERCIAL_FAFA_REFERENCES
            if item.get("nominal_volume_m3", 0) >= required_media_bed_volume_m3]
