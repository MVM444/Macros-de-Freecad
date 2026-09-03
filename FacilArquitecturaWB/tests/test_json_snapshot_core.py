"""Focused tests for Facil Arquitectura JSON snapshot core.

Nombre: test_json_snapshot_core.py
Proposito: validar el contrato puro y determinista usado por FA JSON.
Funcion principal: comprobar orden estable, envelope read-only y serializacion.
Instrucciones: estas pruebas no deben requerir FreeCAD, FreeCADGui ni Qt.
Version: 0.1.0
Fecha y hora: 2026-09-02 16:22 America/Costa_Rica
"""

import json

from FacilArquitecturaWB.core.json_snapshot_core import build_snapshot, dumps_snapshot


def _sample_snapshot():
    return build_snapshot(
        workbench={"version": "0.14.11", "build": "test"},
        document={"name": "Demo", "object_count": 2},
        objects=[
            {"name": "Wall002", "type_id": "Part::Feature"},
            {"name": "Wall001", "type_id": "Part::Feature"},
        ],
        demo={"present": True, "seed": 1234},
        element_data={"categories": {"windows": [{"ElementID": "W-01"}], "doors": []}},
        selection=["Wall001"],
    )


def test_snapshot_is_read_only_and_sorted():
    data = _sample_snapshot()
    assert data["read_only"] is True
    assert [row["name"] for row in data["objects"]] == ["Wall001", "Wall002"]


def test_snapshot_serialization_is_deterministic():
    data = _sample_snapshot()
    first = dumps_snapshot(data, pretty=False)
    second = dumps_snapshot(data, pretty=False)
    assert first == second
    assert json.loads(first)["demo"]["seed"] == 1234


def test_snapshot_keeps_element_data_contract():
    data = json.loads(dumps_snapshot(_sample_snapshot(), pretty=True))
    assert data["element_data"]["categories"]["windows"][0]["ElementID"] == "W-01"
