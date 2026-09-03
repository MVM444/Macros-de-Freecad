"""
Nombre: spatial.py
Proposito: Validar referencias espaciales para el sistema sanitario MEP.
Funcionamiento principal: Verifica que propiedad, edificio, area de tanques y area de drenaje sean poligonos validos y coherentes entre si.
Instrucciones para futuras modificaciones: Mantener reglas geometricas separadas de las reglas sanitarias/normativas. No asumir tipos de objeto FreeCAD.
Version: 0.5.0
Fecha y hora: 2026-08-26 11:50 America/Costa_Rica
"""
from __future__ import annotations

from typing import Dict, Optional
from .boundary import Boundary2D, polygon_contains, polygons_overlap
from .models import CalculationResult, ValidationMessage


def _msg(level, code, message):
    return ValidationMessage(level, code, message)


def validate_spatial_references(
    property_boundary: Boundary2D,
    building_footprint: Optional[Boundary2D] = None,
    tanks_area: Optional[Boundary2D] = None,
    drainage_area: Optional[Boundary2D] = None,
) -> CalculationResult:
    messages = []
    refs: Dict[str, dict] = {"property_boundary": property_boundary.to_dict()}

    for key, item in (
        ("building_footprint", building_footprint),
        ("tanks_area", tanks_area),
        ("drainage_area", drainage_area),
    ):
        if item is None:
            continue
        refs[key] = item.to_dict()
        if not polygon_contains(property_boundary.points, item.points):
            messages.append(_msg("ERROR", "OUTSIDE_PROPERTY", f"{item.role} no esta completamente dentro del limite de propiedad"))

    if building_footprint and tanks_area and polygons_overlap(building_footprint.points, tanks_area.points):
        messages.append(_msg("ERROR", "TANKS_AREA_INTERSECTS_BUILDING", "El area propuesta para tanques intersecta la huella del edificio"))

    if building_footprint and drainage_area and polygons_overlap(building_footprint.points, drainage_area.points):
        messages.append(_msg("ERROR", "DRAINAGE_AREA_INTERSECTS_BUILDING", "El area propuesta para drenaje intersecta la huella del edificio"))

    if tanks_area and drainage_area and polygons_overlap(tanks_area.points, drainage_area.points):
        messages.append(_msg("WARNING", "TANKS_DRAINAGE_OVERLAP", "Las areas de tanques y drenaje se superponen; revisar si la superposicion es intencional"))

    ok = not any(m.level == "ERROR" for m in messages)
    return CalculationResult(ok, {
        "references": refs,
        "ready_for_layout": bool(tanks_area and drainage_area) and ok,
    }, messages)
