"""
Nombre: septic.py
Proposito: Calculo y validacion preliminar de tanque septico rectangular.
Funcionamiento: Calcula volumen hidraulico minimo por TRH y valida criterios geometricos principales.
Modificaciones futuras: Incorporar almacenamiento de lodos y metodos adicionales solo con fuente tecnica documentada.
Version: 0.2.1
Fecha: 2026-08-26
"""
from .models import CalculationResult, ValidationMessage

MIN_USEFUL_VOLUME_M3 = 1.20
MAX_USEFUL_VOLUME_M3 = 5.00
MIN_LIQUID_DEPTH_M = 1.00
MAX_LIQUID_DEPTH_M = 2.80
MIN_FREEBOARD_M = 0.30
MIN_WIDTH_M = 0.70
MIN_RATIO = 3.0
MAX_RATIO = 4.0
MIN_TRH_DAYS = 1.0
MIN_PIPE_DIAMETER_M = 0.10
MIN_INLET_OUTLET_DROP_M = 0.075
MIN_INLET_SUBMERGENCE_M = 0.15
MIN_OUTLET_SUBMERGENCE_M = 0.40
MIN_COVER_OPENING_M = 0.60
MIN_SOIL_COVER_M = 0.15


def required_volume(design_flow_m3_day, trh_days=MIN_TRH_DAYS):
    if design_flow_m3_day <= 0 or trh_days <= 0:
        raise ValueError("Caudal y TRH deben ser mayores que cero")
    return max(design_flow_m3_day * trh_days, MIN_USEFUL_VOLUME_M3)


def evaluate_rectangular_tank(design_flow_m3_day, length_m, width_m, liquid_depth_m, freeboard_m, trh_days=MIN_TRH_DAYS, inlet_diameter_m=None, outlet_diameter_m=None, inlet_outlet_drop_m=None, inlet_submergence_m=None, outlet_submergence_m=None, cover_opening_m=None, soil_cover_m=None, number_of_chambers=1, first_chamber_ratio=None):
    msgs = []
    vals = [design_flow_m3_day, length_m, width_m, liquid_depth_m, freeboard_m]
    if any(v <= 0 for v in vals):
        return CalculationResult(False, messages=[ValidationMessage("ERROR", "INVALID_INPUT", "Todos los valores deben ser mayores que cero")])
    volume = length_m * width_m * liquid_depth_m
    req = required_volume(design_flow_m3_day, trh_days)
    ratio = length_m / width_m
    achieved_trh = volume / design_flow_m3_day
    if volume < req:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_VOLUME_LOW", f"Volumen {volume:.3f} m3 menor al requerido {req:.3f} m3"))
    if volume > MAX_USEFUL_VOLUME_M3:
        msgs.append(ValidationMessage("WARNING", "SEPTIC_VOLUME_HIGH", f"Volumen {volume:.3f} m3 excede 5.0 m3; revisar aplicabilidad reglamentaria del metodo"))
    if not MIN_LIQUID_DEPTH_M <= liquid_depth_m <= MAX_LIQUID_DEPTH_M:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_DEPTH", "Profundidad util fuera de 1.00-2.80 m"))
    if freeboard_m < MIN_FREEBOARD_M:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_FREEBOARD", "Borde libre menor a 0.30 m"))
    if width_m < MIN_WIDTH_M:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_WIDTH", "Ancho interior menor a 0.70 m"))
    if not MIN_RATIO <= ratio <= MAX_RATIO:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_RATIO", f"Relacion largo/ancho {ratio:.2f} fuera de 3:1 a 4:1"))
    if achieved_trh < trh_days:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_TRH", f"TRH logrado {achieved_trh:.2f} d menor a {trh_days:.2f} d"))
    if inlet_diameter_m is not None and inlet_diameter_m < MIN_PIPE_DIAMETER_M:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_INLET_DIAMETER", "Diametro de entrada menor a 0.10 m"))
    if outlet_diameter_m is not None and outlet_diameter_m < MIN_PIPE_DIAMETER_M:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_OUTLET_DIAMETER", "Diametro de salida menor a 0.10 m"))
    if inlet_outlet_drop_m is not None and inlet_outlet_drop_m < MIN_INLET_OUTLET_DROP_M:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_INLET_OUTLET_DROP", "Diferencia de elevacion entrada-salida menor a 0.075 m"))
    if inlet_submergence_m is not None and inlet_submergence_m < MIN_INLET_SUBMERGENCE_M:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_INLET_SUBMERGENCE", "Sumergencia de entrada menor a 0.15 m"))
    required_outlet_submergence = max(liquid_depth_m / 3.0, MIN_OUTLET_SUBMERGENCE_M)
    if outlet_submergence_m is not None and outlet_submergence_m < required_outlet_submergence:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_OUTLET_SUBMERGENCE", f"Sumergencia de salida menor a {required_outlet_submergence:.3f} m"))
    if cover_opening_m is not None and cover_opening_m < MIN_COVER_OPENING_M:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_COVER_OPENING", "Abertura de inspeccion menor a 0.60 m"))
    if soil_cover_m is not None and soil_cover_m < MIN_SOIL_COVER_M:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_SOIL_COVER", "Recubrimiento de terreno menor a 0.15 m"))
    if number_of_chambers < 1:
        msgs.append(ValidationMessage("ERROR", "SEPTIC_CHAMBERS", "El numero de camaras debe ser al menos 1"))
    if number_of_chambers > 1 and first_chamber_ratio is not None and not 0.60 <= first_chamber_ratio <= 0.75:
        msgs.append(ValidationMessage("WARNING", "SEPTIC_FIRST_CHAMBER_RATIO", "Relacion de primera camara fuera del intervalo recomendado 0.60-0.75"))
    return CalculationResult(not any(m.level == "ERROR" for m in msgs), {
        "required_volume_m3": req,
        "useful_volume_m3": volume,
        "achieved_trh_days": achieved_trh,
        "length_width_ratio": ratio,
        "total_internal_height_m": liquid_depth_m + freeboard_m,
        "minimum_pipe_diameter_m": MIN_PIPE_DIAMETER_M,
        "minimum_inlet_outlet_drop_m": MIN_INLET_OUTLET_DROP_M,
        "minimum_inlet_submergence_m": MIN_INLET_SUBMERGENCE_M,
        "required_outlet_submergence_m": required_outlet_submergence,
        "minimum_cover_opening_m": MIN_COVER_OPENING_M,
        "minimum_soil_cover_m": MIN_SOIL_COVER_M,
        "number_of_chambers": number_of_chambers,
        "first_chamber_ratio": first_chamber_ratio,
    }, msgs)


# Referencias comerciales documentadas; no sustituyen seleccion profesional ni ficha vigente.
COMMERCIAL_SEPTIC_REFERENCES = [
    {
        "manufacturer": "Fibromuebles",
        "model": "TS-3000",
        "nominal_volume_m3": 3.0,
        "length_m": 3.30,
        "width_m": 1.15,
        "material": "fibra_de_vidrio",
        "connection_nominal_in": 4.0,
        "reference": "TSM-3000_v2018-1.pdf",
        "checked_date": "2026-08-26",
        "selection_status": "REFERENCE_ONLY",
    },
]


def commercial_septic_candidates(required_volume_m3):
    """Devuelve referencias cuyo volumen nominal no sea menor al requerido."""
    if required_volume_m3 <= 0:
        return []
    return [dict(item) for item in COMMERCIAL_SEPTIC_REFERENCES
            if item.get("nominal_volume_m3", 0) >= required_volume_m3]
