"""Pure inbound JSON command contract for Facil Arquitectura.

Nombre: json_command_core.py
Proposito: validar y normalizar instrucciones JSON pegadas desde un agente externo
(ChatGPT/MCP) antes de que el adaptador FreeCAD planifique o aplique cambios.
Funcion principal: parse_command_text() + validate_command().
Instrucciones relevantes para futuras modificaciones:
- Mantener este modulo independiente de FreeCAD, FreeCADGui y Qt.
- Ninguna operacion debe ejecutar codigo Python arbitrario.
- Toda ampliacion del contrato debe ser explicita, versionada y compatible con dry-run.
- El adaptador FreeCAD es responsable de transacciones, conversion de propiedades y undo.
Version: 0.2.0
Fecha y hora: 2026-09-02 17:15 America/Costa_Rica
"""

from __future__ import annotations

import json
import re

SCHEMA_NAME = "facil-arquitectura.command"
SCHEMA_VERSION = 1
SUPPORTED_OPS = ("set_properties", "apply_elements", "create_demo", "create_site_object")
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_command_text(text):
    text = str(text or "").strip()
    if not text:
        raise ValueError("El JSON de entrada esta vacio")
    try:
        payload = json.loads(text)
    except Exception as exc:
        raise ValueError("JSON invalido: %s" % exc) from exc
    return validate_command(payload)


def validate_command(payload):
    if not isinstance(payload, dict):
        raise ValueError("El JSON de entrada debe ser un objeto")
    schema = str(payload.get("schema", "") or "")
    if schema != SCHEMA_NAME:
        raise ValueError("schema debe ser '%s'" % SCHEMA_NAME)
    version = int(payload.get("schema_version", 0) or 0)
    if version != SCHEMA_VERSION:
        raise ValueError("schema_version no soportado: %s" % version)
    operations = payload.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("operations debe contener al menos una operacion")

    normalized = {
        "schema": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "document": str(payload.get("document", "") or ""),
        "note": str(payload.get("note", "") or ""),
        "operations": [],
    }
    create_demo_count = 0
    for index, raw in enumerate(operations, start=1):
        if not isinstance(raw, dict):
            raise ValueError("operations[%d] debe ser un objeto" % (index - 1))
        op = str(raw.get("op", "") or "")
        if op not in SUPPORTED_OPS:
            raise ValueError("Operacion no soportada en #%d: %s" % (index, op or "<vacia>"))
        if op == "set_properties":
            target = str(raw.get("target", "") or "").strip()
            values = raw.get("values")
            if not target:
                raise ValueError("set_properties #%d requiere target" % index)
            if not isinstance(values, dict) or not values:
                raise ValueError("set_properties #%d requiere values" % index)
            normalized["operations"].append({"op": op, "target": target, "values": values})
        elif op == "apply_elements":
            category = str(raw.get("category", "") or "").strip().lower()
            records = raw.get("records")
            if category not in ("windows", "doors"):
                raise ValueError("apply_elements #%d solo admite windows o doors" % index)
            if not isinstance(records, list) or not records:
                raise ValueError("apply_elements #%d requiere records" % index)
            normalized["operations"].append(
                {
                    "op": op,
                    "category": category,
                    "records": records,
                    "tolerance": raw.get("tolerance"),
                    "host_tolerance_mm": raw.get("host_tolerance_mm"),
                }
            )
        elif op == "create_demo":
            create_demo_count += 1
            spec = raw.get("specification")
            execution = str(raw.get("execution", "immediate") or "immediate").lower()
            if not isinstance(spec, dict) or not spec:
                raise ValueError("create_demo #%d requiere specification" % index)
            if execution not in ("immediate", "guided"):
                raise ValueError("create_demo #%d: execution debe ser immediate o guided" % index)
            normalized["operations"].append(
                {"op": op, "specification": spec, "execution": execution}
            )
        elif op == "create_site_object":
            object_type = str(raw.get("object_type", "") or "").strip().lower()
            name = str(raw.get("name", "") or "").strip()
            label = str(raw.get("label", name) or name).strip()
            placement = raw.get("placement")
            geometry = raw.get("geometry")
            if object_type != "tree":
                raise ValueError("create_site_object #%d solo admite object_type='tree' por ahora" % index)
            if not name or not _NAME_RE.match(name):
                raise ValueError("create_site_object #%d requiere name ASCII valido" % index)
            if not isinstance(placement, dict):
                raise ValueError("create_site_object #%d requiere placement" % index)
            if not isinstance(geometry, dict):
                raise ValueError("create_site_object #%d requiere geometry" % index)
            try:
                x_mm = float(placement.get("x_mm", 0.0))
                y_mm = float(placement.get("y_mm", 0.0))
                z_mm = float(placement.get("z_mm", 0.0))
                height_mm = float(geometry["height_mm"])
                crown_diameter_mm = float(geometry["crown_diameter_mm"])
                trunk_diameter_mm = float(geometry["trunk_diameter_mm"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("create_site_object #%d contiene dimensiones no validas" % index) from exc
            if height_mm <= 300.0:
                raise ValueError("create_site_object #%d: height_mm debe ser > 300" % index)
            if crown_diameter_mm <= 100.0 or crown_diameter_mm >= height_mm:
                raise ValueError("create_site_object #%d: crown_diameter_mm fuera de rango" % index)
            if trunk_diameter_mm <= 20.0 or trunk_diameter_mm >= crown_diameter_mm:
                raise ValueError("create_site_object #%d: trunk_diameter_mm fuera de rango" % index)
            normalized["operations"].append(
                {
                    "op": op,
                    "object_type": object_type,
                    "name": name,
                    "label": label,
                    "placement": {"x_mm": x_mm, "y_mm": y_mm, "z_mm": z_mm},
                    "geometry": {
                        "height_mm": height_mm,
                        "crown_diameter_mm": crown_diameter_mm,
                        "trunk_diameter_mm": trunk_diameter_mm,
                    },
                    "container": str(raw.get("container", "Site") or "Site"),
                    "plan_symbol": bool(raw.get("plan_symbol", True)),
                }
            )
    if create_demo_count and len(normalized["operations"]) != 1:
        raise ValueError("create_demo debe enviarse como unica operacion del sobre")
    return normalized


def example_command():
    """Return a visually obvious Demo test: three JSON-created trees around the house."""
    return {
        "schema": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "document": "",
        "note": "Ejemplo visual JSON: agregar tres arboles alrededor de la casa Demo",
        "operations": [
            {
                "op": "create_site_object",
                "object_type": "tree",
                "name": "Tree_01",
                "label": "Arbol frente",
                "placement": {"x_mm": -1800.0, "y_mm": 1800.0, "z_mm": 0.0},
                "geometry": {"height_mm": 4200.0, "trunk_diameter_mm": 220.0, "crown_diameter_mm": 2400.0},
            },
            {
                "op": "create_site_object",
                "object_type": "tree",
                "name": "Tree_02",
                "label": "Arbol lateral",
                "placement": {"x_mm": 8200.0, "y_mm": 3000.0, "z_mm": 0.0},
                "geometry": {"height_mm": 3300.0, "trunk_diameter_mm": 180.0, "crown_diameter_mm": 1900.0},
            },
            {
                "op": "create_site_object",
                "object_type": "tree",
                "name": "Tree_03",
                "label": "Arbol posterior",
                "placement": {"x_mm": 4500.0, "y_mm": 9800.0, "z_mm": 0.0},
                "geometry": {"height_mm": 5000.0, "trunk_diameter_mm": 260.0, "crown_diameter_mm": 2800.0},
            },
        ],
    }


def dumps_command(payload, pretty=True):
    kwargs = {"ensure_ascii": False, "sort_keys": True}
    if pretty:
        kwargs["indent"] = 2
    else:
        kwargs["separators"] = (",", ":")
    return json.dumps(payload, **kwargs)
