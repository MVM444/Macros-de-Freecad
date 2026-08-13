# -*- coding: utf-8 -*-
"""Resolucion de circuito, tablero y equipo aguas arriba.

Separa la asignacion electrica de la geometria. Lee PropertyLinks primero y
mantiene compatibilidad con Asignacion_Red, Red_Origenes y aliases heredados.
No inventa asignaciones de equipos. Compatible con FreeCAD 1.1.3.
Creado: 2026-08-08 18:01 CST. Advertencia: no inferir tableros por proximidad.
"""

import re

from . import panels


SHEET_ASSIGN = "Asignacion_Red"
SHEET_ORIGINS = "Red_Origenes"


def _props(obj):
    return set(getattr(obj, "PropertiesList", []) or [])


def _sheet_get(sheet, cell):
    try:
        return panels.text(sheet.getContents(cell)).strip("'")
    except Exception:
        return ""


def _enabled(value, has_assignment=False):
    key = panels.normalized(value)
    if key in ("0", "false", "no", "off"):
        return False
    if key in ("1", "true", "si", "yes", "on"):
        return True
    return bool(has_assignment)


def circuit_id(obj):
    try:
        linked = getattr(obj, "Circuit", None)
        if linked is not None:
            for name in ("CircuitId", "CircuitoID", "Codigo"):
                value = panels.text(getattr(linked, name, "")).strip()
                if value:
                    return value
    except Exception:
        pass
    for name in ("CircuitId", "CircuitoID", "Circuito", "CircuitID", "CodigoCircuito"):
        value = panels.text(getattr(obj, name, "")).strip()
        if value:
            return value
    label = panels.text(getattr(obj, "Label", ""))
    match = re.match(r"^\s*([A-Za-z][A-Za-z0-9]*)\s*[-_]\s*(\d+)\b", label)
    if not match:
        return ""
    prefix = match.group(1).upper()
    digits = match.group(2)
    width = max(2, len(digits))
    return "{}-{:0{}d}".format(prefix, int(digits), width)


def circuit_prefix(value):
    match = re.match(r"^\s*([A-Za-z][A-Za-z0-9]*)\s*[-_]", panels.text(value))
    return match.group(1).upper() if match else ""


def _linked_panel(obj):
    for name in ("Panel", "UpstreamEquipment", "PanelRef", "TableroAsignado", "TableroDestino"):
        if name not in _props(obj):
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            continue
        if panels.is_panel(value):
            return value
    return None


def _text_panel_tokens(obj):
    values = []
    for name in ("PanelId", "PanelID", "ConectadoA", "Tablero", "TableroAsignado", "Panel"):
        if name not in _props(obj):
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            continue
        if isinstance(value, str) and panels.text(value):
            values.append(value)
    return values


def _assignment_row(doc, obj):
    sheet = doc.getObject(SHEET_ASSIGN)
    if sheet is None:
        return {}
    expected_key = "EQ::OBJ::{}".format(obj.Name)
    code = panels.normalized(getattr(obj, "Codigo", ""))
    fallback = {}
    empty_run = 0
    for row in range(2, 7000):
        use = _sheet_get(sheet, "A{}".format(row))
        panel = _sheet_get(sheet, "B{}".format(row))
        item = _sheet_get(sheet, "C{}".format(row))
        item_type = _sheet_get(sheet, "D{}".format(row))
        key = _sheet_get(sheet, "H{}".format(row))
        cid = _sheet_get(sheet, "K{}".format(row))
        if not any((use, panel, item, item_type, key, cid)):
            empty_run += 1
            if empty_run >= 100:
                break
            continue
        empty_run = 0
        data = {"row": row, "use": use, "panel": panel, "circuit": cid, "item": item, "key": key}
        if key == expected_key:
            return data
        if code and panels.normalized(item) == code:
            fallback = data
    return fallback


def _origin_row(doc, obj):
    sheet = doc.getObject(SHEET_ORIGINS)
    if sheet is None:
        return {}
    code = panels.normalized(getattr(obj, "Codigo", ""))
    fallback = {}
    empty_run = 0
    for row in range(2, 4000):
        use = _sheet_get(sheet, "A{}".format(row))
        item = _sheet_get(sheet, "B{}".format(row))
        source = _sheet_get(sheet, "D{}".format(row))
        object_name = _sheet_get(sheet, "E{}".format(row))
        if not any((use, item, source, object_name)):
            empty_run += 1
            if empty_run >= 100:
                break
            continue
        empty_run = 0
        data = {"row": row, "use": use, "panel": source}
        if object_name == obj.Name:
            return data
        if code and panels.normalized(item) == code:
            fallback = data
    return fallback


def resolve_equipment_assignment(doc, obj):
    assignment = _assignment_row(doc, obj)
    panel_token = ""
    source = ""
    if assignment and _enabled(assignment.get("use", ""), bool(assignment.get("panel"))):
        panel_token = panels.text(assignment.get("panel", ""))
        source = SHEET_ASSIGN
    panel = panels.find_panel_by_token(doc, panel_token) if panel_token else None

    linked = _linked_panel(obj)
    if panel is None and linked is not None:
        panel = linked
        panel_token = panels.panel_code(linked)
        source = "PropertyLink"

    origin = _origin_row(doc, obj)
    if panel is None and origin and _enabled(origin.get("use", ""), bool(origin.get("panel"))):
        panel_token = panels.text(origin.get("panel", ""))
        panel = panels.find_panel_by_token(doc, panel_token)
        source = SHEET_ORIGINS

    if panel is None:
        for token in _text_panel_tokens(obj):
            candidate = panels.find_panel_by_token(doc, token)
            if candidate is not None:
                panel = candidate
                panel_token = token
                source = "Alias heredado"
                break

    cid = panels.text(assignment.get("circuit", "")).strip() or circuit_id(obj)
    return {
        "object": obj,
        "panel": panel,
        "panel_token": panel_token,
        "circuit_id": cid,
        "source": source,
        "assignment_row": int(assignment.get("row", 0) or 0),
        "origin_row": int(origin.get("row", 0) or 0),
    }


def is_connectable_equipment(obj):
    if obj is None or panels.is_group(obj) or panels.is_library_object(obj):
        return False
    props = _props(obj)
    kind = panels.normalized(
        "{} {}".format(getattr(obj, "ClaseEquipo", ""), getattr(obj, "Tipo", ""))
    )
    if any(marker in kind for marker in ("alimentador", "conexion", "ramal", "ruta")):
        return False
    if {"PuntoOrigen", "PuntoDestino", "RutaJSON"}.issubset(props):
        return False
    blob = panels.normalized(
        "{} {} {} {}".format(
            getattr(obj, "ClaseEquipo", ""),
            getattr(obj, "Tipo", ""),
            getattr(obj, "ElementType", ""),
            getattr(obj, "IfcType", ""),
        )
    )
    markers = ("desconector", "disconnect", "interruptor", "switch", "tablero", "distributionboard", "panelboard")
    return any(marker in blob for marker in markers) or any(
        name in props for name in ("UpstreamEquipment", "PanelRef", "TableroAsignado")
    )


def analyze_equipment(doc, objects=None):
    if objects is None:
        objects = [obj for obj in list(doc.Objects) if is_connectable_equipment(obj)]
    return [resolve_equipment_assignment(doc, obj) for obj in list(objects or [])]


def resolve_circuit_panel(doc, circuit_group, forced_panel=None):
    if forced_panel is not None and panels.is_panel(forced_panel):
        return forced_panel, "Seleccion"
    linked = _linked_panel(circuit_group)
    if linked is not None:
        return linked, "PropertyLink"
    for token in _text_panel_tokens(circuit_group):
        panel = panels.find_panel_by_token(doc, token)
        if panel is not None:
            return panel, "Alias heredado"
    cid = circuit_id(circuit_group)
    prefix = circuit_prefix(cid)
    panel = panels.find_panel_by_token(doc, prefix) if prefix else None
    return (panel, "Prefijo de circuito") if panel is not None else (None, "")


def ensure_property(obj, ptype, name, group, description):
    if name not in _props(obj):
        obj.addProperty(ptype, name, group, description)


def sync_equipment_assignment(obj, panel, cid, generated_by):
    group = "ElectricCR Conexion"
    ensure_property(obj, "App::PropertyLink", "UpstreamEquipment", group, "Equipo o tablero aguas arriba")
    ensure_property(obj, "App::PropertyString", "PanelId", group, "Codigo derivado del tablero")
    ensure_property(obj, "App::PropertyString", "CircuitoID", group, "Codigo derivado del circuito")
    ensure_property(obj, "App::PropertyString", "ECR_ConexionGeneradaPor", "ElectricCR", "Servicio que actualizo la conexion")
    ensure_property(obj, "App::PropertyString", "ConectadoA", "Tablero", "Alias heredado del tablero")
    obj.UpstreamEquipment = panel
    obj.PanelId = panels.panel_code(panel)
    obj.CircuitoID = panels.text(cid)
    obj.ConectadoA = panels.panel_code(panel)
    obj.ECR_ConexionGeneradaPor = generated_by
    if "Panel" not in _props(obj):
        obj.addProperty("App::PropertyLink", "Panel", group, "Tablero electrico asignado")
    try:
        if "PropertyLink" in panels.text(obj.getTypeIdOfProperty("Panel")):
            obj.Panel = panel
    except Exception:
        pass
