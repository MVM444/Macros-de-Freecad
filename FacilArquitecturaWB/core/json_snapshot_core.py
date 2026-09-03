"""Pure JSON snapshot helpers for Facil Arquitectura.

Nombre: json_snapshot_core.py
Proposito: construir y serializar un contrato JSON estable para diagnostico,
pruebas y futura integracion MCP de Facil Arquitectura.
Funcion principal: recibir datos ya normalizados por el adaptador FreeCAD y
producir un envelope JSON determinista, sin importar FreeCAD, FreeCADGui ni Qt.
Instrucciones relevantes para futuras modificaciones:
- Mantener este modulo independiente de FreeCAD y GUI.
- No introducir geometria pesada ni objetos Python no serializables.
- Conservar orden determinista para facilitar diffs y pruebas reproducibles.
- Ampliar el schema de forma compatible y versionada.
Version: 0.1.0
Fecha y hora: 2026-09-02 16:22 America/Costa_Rica
"""

from __future__ import annotations

import json


SCHEMA_NAME = "facil-arquitectura.snapshot"
SCHEMA_VERSION = 1


def json_compatible(value):
    """Return a recursively JSON-compatible representation."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {
            str(key): json_compatible(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [json_compatible(item) for item in value]
    return str(value)


def build_snapshot(*, workbench, document, objects, demo=None, element_data=None, selection=None):
    """Build the stable read-only snapshot envelope used by FA JSON."""
    object_rows = [json_compatible(item) for item in (objects or [])]
    object_rows.sort(key=lambda row: (str(row.get("name", "")), str(row.get("type_id", ""))))
    payload = {
        "schema": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "workbench": json_compatible(workbench or {}),
        "document": json_compatible(document or {}),
        "selection": json_compatible(selection or []),
        "demo": json_compatible(demo or {}),
        "element_data": json_compatible(element_data or {}),
        "objects": object_rows,
    }
    return payload


def dumps_snapshot(snapshot, *, pretty=True):
    """Serialize one snapshot as deterministic UTF-8 JSON text."""
    kwargs = {
        "ensure_ascii": False,
        "sort_keys": True,
    }
    if pretty:
        kwargs.update({"indent": 2})
    else:
        kwargs.update({"separators": (",", ":")})
    return json.dumps(json_compatible(snapshot), **kwargs)
