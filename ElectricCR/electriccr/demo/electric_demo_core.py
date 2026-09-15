# -*- coding: utf-8 -*-
"""ElectricCR canonical demo specification.

Purpose:
- Define a small, deterministic ElectricCR A1 demo without importing FreeCAD.
- Keep the scenario JSON-compatible so it can be inspected, tested and reused by MCP.

Main behavior:
- ``build_fixed_demo_spec()`` always returns the same two-space, seven-device scenario.
- Device UUIDs are deterministic UUIDv5 values derived from stable demo keys.

Future modification guidance:
- Add scenarios by extending pure data first; do not add FreeCAD/GUI logic here.
- Keep internal identifiers ASCII-safe and preserve existing demo IDs once published.

Version: 0.1.0
Date/time: 2026-09-09 22:09 America/Costa_Rica
Target: FreeCAD 1.1.3 through the separate FreeCAD adapter.
"""

from __future__ import annotations

import copy
import uuid


SCHEMA_VERSION = 1
DEMO_ID = "electriccr-a1-canonical-v1"
DEMO_NAMESPACE = uuid.UUID("f4b5b889-6b13-5cc7-92c1-a27a013dd94a")


def _uid(device_id: str) -> str:
    return str(uuid.uuid5(DEMO_NAMESPACE, "%s:%s" % (DEMO_ID, str(device_id))))


def _device(
    device_id,
    label,
    key_registro,
    tipo_logico,
    space_key,
    host_key,
    x,
    y,
    yaw_deg,
    altura_rel,
    orientacion_pared,
    circuit_id,
):
    return {
        "id": str(device_id),
        "internal_name": "ECR_Demo_%s" % str(device_id).replace("-", "_"),
        "label": str(label),
        "element_uid": _uid(device_id),
        "key_registro": str(key_registro),
        "tipo_logico": str(tipo_logico),
        "space_key": str(space_key),
        "host_key": str(host_key or ""),
        "placement": {"x": float(x), "y": float(y), "z": 0.0, "yaw_deg": float(yaw_deg)},
        "altura_rel": float(altura_rel),
        "orientacion_pared": str(orientacion_pared),
        "modo_visual": "Ambos",
        "circuit_id": str(circuit_id),
    }


def build_fixed_demo_spec():
    """Return the canonical ElectricCR A1 demo as JSON-compatible data."""

    spec = {
        "schema_version": SCHEMA_VERSION,
        "demo_id": DEMO_ID,
        "document": {
            "name_prefix": "ElectricCR_Demo_A1",
            "label": "ElectricCR Demo A1 - Canonica",
        },
        "building": {"key": "building", "label": "Edificio Demo ElectricCR"},
        "level": {"key": "level_00", "label": "Nivel 00", "elevation_mm": 0.0},
        "floor": {
            "key": "floor_00",
            "label": "Losa Demo",
            "x": 0.0,
            "y": 0.0,
            "z": -150.0,
            "length": 8000.0,
            "width": 5000.0,
            "height": 150.0,
        },
        "spaces": [
            {
                "key": "space_office",
                "label": "Oficina",
                "base_name": "ECR_Demo_SpaceBase_Office",
                "x": 75.0,
                "y": 75.0,
                "z": -25.0,
                "length": 4650.0,
                "width": 4850.0,
                "height": 3050.0,
            },
            {
                "key": "space_storage",
                "label": "Bodega",
                "base_name": "ECR_Demo_SpaceBase_Storage",
                "x": 4875.0,
                "y": 75.0,
                "z": -25.0,
                "length": 3050.0,
                "width": 4850.0,
                "height": 3050.0,
            },
        ],
        "walls": [
            {"key": "wall_south", "label": "Muro Sur", "start": [0.0, 0.0], "end": [8000.0, 0.0]},
            {"key": "wall_north", "label": "Muro Norte", "start": [0.0, 5000.0], "end": [8000.0, 5000.0]},
            {"key": "wall_west", "label": "Muro Oeste", "start": [0.0, 0.0], "end": [0.0, 5000.0]},
            {"key": "wall_east", "label": "Muro Este", "start": [8000.0, 0.0], "end": [8000.0, 5000.0]},
            {"key": "wall_partition", "label": "Muro Division", "start": [4800.0, 0.0], "end": [4800.0, 5000.0]},
        ],
        "wall_defaults": {"width": 150.0, "height": 3000.0, "align": "Center"},
        "devices": [
            _device(
                "outlet-office-01", "Toma Oficina 01", "Tomacorriente_120V", "Toma",
                "space_office", "wall_south", 900.0, 110.0, 0.0, 300.0, "Vertical", "T-01"
            ),
            _device(
                "outlet-storage-01", "Toma Bodega 01", "Tomacorriente_120V", "Toma",
                "space_storage", "wall_south", 6500.0, 110.0, 0.0, 300.0, "Vertical", "T-01"
            ),
            _device(
                "switch-office-01", "Apagador Oficina 01", "Apagador_Simple", "Apagador",
                "space_office", "wall_south", 4200.0, 110.0, 0.0, 1200.0, "Vertical", "IL-01"
            ),
            _device(
                "switch-storage-01", "Apagador Bodega 01", "Apagador_Simple", "Apagador",
                "space_storage", "wall_partition", 4900.0, 1200.0, 90.0, 1200.0, "Vertical", "IL-01"
            ),
            _device(
                "light-office-01", "Luminaria Oficina 01", "Luminaria LED Redonda 1000lm", "Luminaria",
                "space_office", "", 2400.0, 2500.0, 0.0, 2700.0, "Horizontal", "IL-01"
            ),
            _device(
                "light-storage-01", "Luminaria Bodega 01", "Luminaria LED Redonda 1000lm", "Luminaria",
                "space_storage", "", 6400.0, 2500.0, 0.0, 2700.0, "Horizontal", "IL-01"
            ),
            _device(
                "smoke-storage-01", "Sensor Humo Bodega 01", "Sensor_Humo", "Sensor",
                "space_storage", "", 6500.0, 3800.0, 0.0, 2800.0, "Horizontal", "FA-01"
            ),
        ],
        "expected": {
            "spaces": 2,
            "walls": 5,
            "owners": 7,
            "plans": 7,
            "physical_masters": 4,
        },
        "scope": {
            "ifc_export": False,
            "circuit_objects": False,
            "control_objects": False,
            "random_variants": False,
        },
    }
    return copy.deepcopy(spec)


def demo_summary(spec=None):
    """Return a compact JSON-compatible summary used by UI/tests."""
    data = spec or build_fixed_demo_spec()
    return {
        "demo_id": data["demo_id"],
        "schema_version": data["schema_version"],
        "spaces": len(data["spaces"]),
        "walls": len(data["walls"]),
        "devices": len(data["devices"]),
        "device_ids": [item["id"] for item in data["devices"]],
        "element_uids": [item["element_uid"] for item in data["devices"]],
    }


__all__ = [
    "SCHEMA_VERSION",
    "DEMO_ID",
    "DEMO_NAMESPACE",
    "build_fixed_demo_spec",
    "demo_summary",
]
