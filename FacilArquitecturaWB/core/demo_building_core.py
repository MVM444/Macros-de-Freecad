"""Generador independiente de especificaciones para la demo de Facil Arquitectura.

Nombre: demo_building_core.py
Proposito: producir una especificacion JSON-compatible de una casa rectangular
simple y reproducible, sin importar FreeCAD, FreeCADGui ni Qt.
Funcion principal: build_demo_spec(seed, randomized) devuelve huella, muros,
aberturas, recintos/Espacios BIM, cielorraso modular, piso y techo para que un adaptador FreeCAD los materialice.
Instrucciones relevantes:
- Mantener este modulo libre de FreeCAD/Qt y apto para pruebas unitarias.
- La misma semilla debe producir exactamente la misma especificacion.
- Toda abertura debe conservar margenes seguros respecto a esquinas y otras
  aberturas del mismo muro.
- El caso fijo es el ejemplo canonico de demostracion; el modo aleatorio solo
  varia dentro de limites deliberadamente conservadores.
Version: 0.2.1
Fecha y hora: 2026-09-01 09:50 America/Costa_Rica
"""

from __future__ import annotations

import json
import math
import random
from typing import Dict, Iterable, List, Sequence, Tuple

SCHEMA_VERSION = 1
CANONICAL_SEED = 20260831
MIN_EDGE_MARGIN_MM = 400.0
MIN_OPENING_GAP_MM = 250.0


def _q(value: float, step: float = 100.0) -> float:
    """Round to a construction-friendly increment."""
    return float(round(float(value) / float(step)) * float(step))


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(float(lo), min(float(hi), float(value)))


def _segment(x1: float, y1: float, x2: float, y2: float, role: str, name: str) -> Dict:
    return {
        "name": str(name),
        "role": str(role),
        "start_mm": [float(x1), float(y1)],
        "end_mm": [float(x2), float(y2)],
    }


def _centered_segment_on_horizontal(
    center_x: float,
    width: float,
    y: float,
    role: str,
    name: str,
) -> Dict:
    half = float(width) * 0.5
    return _segment(center_x - half, y, center_x + half, y, role, name)


def _centered_segment_on_vertical(
    x: float,
    center_y: float,
    width: float,
    role: str,
    name: str,
) -> Dict:
    half = float(width) * 0.5
    return _segment(x, center_y - half, x, center_y + half, role, name)


def _length(seg: Dict) -> float:
    a = seg["start_mm"]
    b = seg["end_mm"]
    return math.hypot(float(b[0]) - float(a[0]), float(b[1]) - float(a[1]))


def _canonical_values() -> Dict:
    return {
        "width_mm": 6000.0,
        "depth_mm": 8000.0,
        "wall_height_mm": 3000.0,
        "ext_wall_thickness_mm": 200.0,
        "int_wall_thickness_mm": 120.0,
        "partition_y_mm": 5200.0,
        "front_door_width_mm": 1000.0,
        "front_door_center_x_mm": 3000.0,
        "interior_door_width_mm": 900.0,
        "interior_door_center_x_mm": 2000.0,
        "window_width_mm": 1200.0,
        "side_window_width_mm": 1000.0,
        "window_height_mm": 1200.0,
        "window_sill_mm": 900.0,
        "floor_thickness_mm": 150.0,
        "roof_pitch_deg": 22.0,
        "roof_overhang_mm": 500.0,
        "truss_spacing_mm": 2800.0,
        "purlin_spacing_mm": 800.0,
    }


def _random_values(seed: int) -> Dict:
    rng = random.Random(int(seed))
    width = float(rng.choice(range(52, 77)) * 100)
    min_depth = max(7000.0, width + 1000.0)
    depth_steps = list(range(int(min_depth // 100), 106))
    depth = float(rng.choice(depth_steps) * 100)
    wall_height = float(rng.choice([2700, 2800, 2900, 3000, 3200]))
    partition_y = _q(depth * rng.uniform(0.55, 0.70), 100.0)
    partition_y = _clamp(partition_y, 3600.0, depth - 1800.0)

    front_door_width = float(rng.choice([900, 1000, 1100]))
    front_door_center = _q(width * (0.50 + rng.uniform(-0.04, 0.04)), 100.0)
    front_door_center = _clamp(
        front_door_center,
        MIN_EDGE_MARGIN_MM + front_door_width * 0.5,
        width - MIN_EDGE_MARGIN_MM - front_door_width * 0.5,
    )

    interior_door_width = float(rng.choice([800, 900, 1000]))
    interior_fraction = rng.choice([0.34, 0.40, 0.60, 0.66])
    interior_door_center = _q(width * interior_fraction, 100.0)
    interior_door_center = _clamp(
        interior_door_center,
        MIN_EDGE_MARGIN_MM + interior_door_width * 0.5,
        width - MIN_EDGE_MARGIN_MM - interior_door_width * 0.5,
    )

    window_width = _q(_clamp(width * rng.uniform(0.16, 0.19), 900.0, 1200.0), 100.0)
    side_window_width = float(rng.choice([900, 1000, 1100, 1200]))

    return {
        "width_mm": width,
        "depth_mm": depth,
        "wall_height_mm": wall_height,
        "ext_wall_thickness_mm": float(rng.choice([180, 200, 220])),
        "int_wall_thickness_mm": float(rng.choice([100, 120, 150])),
        "partition_y_mm": partition_y,
        "front_door_width_mm": front_door_width,
        "front_door_center_x_mm": front_door_center,
        "interior_door_width_mm": interior_door_width,
        "interior_door_center_x_mm": interior_door_center,
        "window_width_mm": window_width,
        "side_window_width_mm": side_window_width,
        "window_height_mm": float(rng.choice([1000, 1200, 1400])),
        "window_sill_mm": float(rng.choice([800, 900, 1000])),
        "floor_thickness_mm": float(rng.choice([120, 150, 180])),
        "roof_pitch_deg": float(rng.choice([18, 20, 22, 25, 28, 30])),
        "roof_overhang_mm": float(rng.choice([450, 500, 600])),
        "truss_spacing_mm": float(rng.choice([2500, 2800, 3000])),
        "purlin_spacing_mm": float(rng.choice([700, 750, 800])),
    }


def _build_openings(values: Dict) -> Tuple[List[Dict], List[Dict]]:
    width = float(values["width_mm"])
    depth = float(values["depth_mm"])
    partition_y = float(values["partition_y_mm"])
    front_door_width = float(values["front_door_width_mm"])
    front_door_center = float(values["front_door_center_x_mm"])
    interior_door_width = float(values["interior_door_width_mm"])
    interior_door_center = float(values["interior_door_center_x_mm"])
    window_width = float(values["window_width_mm"])
    side_window_width = float(values["side_window_width_mm"])

    doors = [
        _centered_segment_on_horizontal(
            front_door_center,
            front_door_width,
            0.0,
            "door",
            "Puerta principal",
        ),
        _centered_segment_on_horizontal(
            interior_door_center,
            interior_door_width,
            partition_y,
            "door",
            "Puerta interior",
        ),
    ]

    # Fracciones deliberadamente conservadoras. Se mantienen lejos de esquinas,
    # de la puerta principal y del tabique para que la demo sea estable.
    windows = [
        _centered_segment_on_horizontal(width * 0.20, window_width, 0.0, "window", "Ventana frente izquierda"),
        _centered_segment_on_horizontal(width * 0.80, window_width, 0.0, "window", "Ventana frente derecha"),
        _centered_segment_on_horizontal(width * 0.28, window_width, depth, "window", "Ventana posterior izquierda"),
        _centered_segment_on_horizontal(width * 0.72, window_width, depth, "window", "Ventana posterior derecha"),
        _centered_segment_on_vertical(0.0, depth * 0.30, side_window_width, "window", "Ventana lateral izquierda"),
        _centered_segment_on_vertical(width, depth * 0.80, side_window_width, "window", "Ventana lateral derecha"),
    ]
    return doors, windows


def _opening_axis(seg: Dict, width: float, depth: float) -> Tuple[str, float, float, float]:
    """Return (wall_key, start_scalar, end_scalar, wall_length)."""
    x1, y1 = map(float, seg["start_mm"])
    x2, y2 = map(float, seg["end_mm"])
    tol = 1e-6
    if abs(y1) <= tol and abs(y2) <= tol:
        return "front", min(x1, x2), max(x1, x2), float(width)
    if abs(y1 - depth) <= tol and abs(y2 - depth) <= tol:
        return "rear", min(x1, x2), max(x1, x2), float(width)
    if abs(x1) <= tol and abs(x2) <= tol:
        return "left", min(y1, y2), max(y1, y2), float(depth)
    if abs(x1 - width) <= tol and abs(x2 - width) <= tol:
        return "right", min(y1, y2), max(y1, y2), float(depth)
    return "interior", min(x1, x2), max(x1, x2), float(width)


def _build_rooms(values: Dict) -> List[Dict]:
    """Return two clear-room rectangles derived from wall centerlines/thicknesses."""
    width = float(values["width_mm"])
    depth = float(values["depth_mm"])
    partition_y = float(values["partition_y_mm"])
    ext = float(values["ext_wall_thickness_mm"])
    interior = float(values["int_wall_thickness_mm"])
    wall_height = float(values["wall_height_mm"])
    ceiling_elevation = max(2400.0, min(2700.0, wall_height - 150.0))
    x0 = ext * 0.5
    x1 = width - ext * 0.5
    front_y0 = ext * 0.5
    front_y1 = partition_y - interior * 0.5
    rear_y0 = partition_y + interior * 0.5
    rear_y1 = depth - ext * 0.5

    def room(room_id: str, name: str, xa: float, ya: float, xb: float, yb: float) -> Dict:
        polygon = [[xa, ya], [xb, ya], [xb, yb], [xa, yb]]
        return {
            "id": room_id,
            "name": name,
            "polygon_mm": polygon,
            "area_m2": ((xb - xa) * (yb - ya)) / 1000000.0,
            "space_height_mm": ceiling_elevation,
        }

    return [
        room("R01", "Estar-comedor", x0, front_y0, x1, front_y1),
        room("R02", "Dormitorio", x0, rear_y0, x1, rear_y1),
    ]


def validate_demo_spec(spec: Dict) -> Dict:
    """Validate a generated specification and return it unchanged."""
    footprint = spec["footprint"]
    width = float(footprint["width_mm"])
    depth = float(footprint["depth_mm"])
    if width < 5000.0 or depth < 6500.0:
        raise ValueError("La huella demo es demasiado pequena para las aberturas previstas.")
    if float(spec["walls"]["height_mm"]) <= 0.0:
        raise ValueError("La altura de muro debe ser positiva.")

    by_wall: Dict[str, List[Tuple[float, float, str]]] = {}
    for seg in list(spec["openings"]["doors"]) + list(spec["openings"]["windows"]):
        if _length(seg) < 600.0:
            raise ValueError("Abertura demo demasiado angosta: %s" % seg["name"])
        wall_key, start, end, wall_length = _opening_axis(seg, width, depth)
        if start < MIN_EDGE_MARGIN_MM - 1e-6 or end > wall_length - MIN_EDGE_MARGIN_MM + 1e-6:
            if wall_key != "interior":
                raise ValueError("Abertura demasiado cerca de una esquina: %s" % seg["name"])
        by_wall.setdefault(wall_key, []).append((start, end, str(seg["name"])))

    for wall_key, spans in by_wall.items():
        if wall_key == "interior":
            continue
        ordered = sorted(spans)
        for left, right in zip(ordered, ordered[1:]):
            if right[0] - left[1] < MIN_OPENING_GAP_MM - 1e-6:
                raise ValueError(
                    "Aberturas demasiado proximas en %s: %s / %s"
                    % (wall_key, left[2], right[2])
                )

    rooms = list(spec.get("rooms", {}).get("items", []) or [])
    if len(rooms) != 2:
        raise ValueError("La demo v2 debe definir exactamente dos recintos simples.")
    for room in rooms:
        polygon = list(room.get("polygon_mm", []) or [])
        if len(polygon) < 4 or float(room.get("area_m2", 0.0)) < 2.0:
            raise ValueError("Recinto demo invalido: %s" % room.get("name", "?"))
        if float(room.get("space_height_mm", 0.0)) <= 0.0:
            raise ValueError("Altura de Espacio BIM invalida: %s" % room.get("name", "?"))
    if abs(float(spec.get("ceiling", {}).get("module_mm", 0.0)) - 600.0) > 1e-6:
        raise ValueError("La Casa demo v2 usa cielorraso modular nominal de 600 mm.")
    site = dict(spec.get("site", {}) or {})
    if bool(site.get("garden_enabled", False)) and float(site.get("terrain_margin_mm", 0.0)) < 500.0:
        raise ValueError("El jardin demo requiere al menos 500 mm de margen alrededor del edificio.")

    json.dumps(spec, sort_keys=True)
    return spec


def build_demo_spec(seed: int = CANONICAL_SEED, randomized: bool = False) -> Dict:
    """Build a deterministic, JSON-compatible demo house specification."""
    seed = int(seed)
    values = _random_values(seed) if bool(randomized) else _canonical_values()
    width = float(values["width_mm"])
    depth = float(values["depth_mm"])
    partition_y = float(values["partition_y_mm"])
    doors, windows = _build_openings(values)
    rooms = _build_rooms(values)

    exterior = [
        _segment(0.0, 0.0, width, 0.0, "wall", "Muro frente"),
        _segment(width, 0.0, width, depth, "wall", "Muro derecho"),
        _segment(width, depth, 0.0, depth, "wall", "Muro posterior"),
        _segment(0.0, depth, 0.0, 0.0, "wall", "Muro izquierdo"),
    ]
    interior = [
        _segment(0.0, partition_y, width, partition_y, "wall", "Muro divisor"),
    ]

    spec = {
        "schema_version": SCHEMA_VERSION,
        "generator": "FA_DemoBuilding",
        "seed": seed,
        "randomized": bool(randomized),
        "name": "Casa demo aleatoria" if randomized else "Casa demo canonica 6x8",
        "inspiration": {
            "type": "microcasa rectangular de una planta con cubierta a dos aguas",
            "note": "Tipologia generica inspirada en microcabinas rectangulares; no reproduce un plano comercial.",
        },
        "footprint": {
            "width_mm": width,
            "depth_mm": depth,
        },
        "walls": {
            "height_mm": float(values["wall_height_mm"]),
            "exterior_thickness_mm": float(values["ext_wall_thickness_mm"]),
            "interior_thickness_mm": float(values["int_wall_thickness_mm"]),
            "exterior_segments": exterior,
            "interior_segments": interior,
        },
        "floor": {
            "thickness_mm": float(values["floor_thickness_mm"]),
            "overhang_mm": float(values["ext_wall_thickness_mm"]) * 0.5,
            "top_z_mm": 0.0,
        },
        "site": {
            "garden_enabled": True,
            "terrain_margin_mm": 2500.0,
            "pad_margin_mm": 750.0,
            "terrain_variation_mm": 0.0,
            "landscape_role": "garden",
        },
        "openings": {
            "door_height_mm": 2100.0,
            "window_height_mm": float(values["window_height_mm"]),
            "window_sill_mm": float(values["window_sill_mm"]),
            "host_tolerance_mm": 300.0,
            "doors": doors,
            "windows": windows,
        },
        "rooms": {
            "minimum_area_m2": 2.0,
            "snap_tolerance_mm": 5.0,
            "items": rooms,
        },
        "ceiling": {
            "module_mm": 600.0,
            "elevation_mm": float(rooms[0]["space_height_mm"]),
            "panel_thickness_mm": 15.0,
            "joint_gap_mm": 5.0,
            "alignment_tolerance_mm": 50.0,
        },
        "roof": {
            "pitch_deg": float(values["roof_pitch_deg"]),
            "overhang_mm": float(values["roof_overhang_mm"]),
            "thickness_mm": 50.0,
            "truss_spacing_mm": float(values["truss_spacing_mm"]),
            "truss_height_start_mm": 150.0,
            "purlin_spacing_mm": float(values["purlin_spacing_mm"]),
            "purlin_width_mm": 50.0,
            "purlin_height_mm": 100.0,
        },
    }
    return validate_demo_spec(spec)


def spec_summary(spec: Dict) -> str:
    """Compact summary suitable for logs and tests."""
    footprint = spec["footprint"]
    return (
        "%s | seed=%d | %.1fx%.1f m | recintos=%d | puertas=%d | ventanas=%d | techo=%.1f deg | jardin=%s"
        % (
            spec["name"],
            int(spec["seed"]),
            float(footprint["width_mm"]) / 1000.0,
            float(footprint["depth_mm"]) / 1000.0,
            len(spec["rooms"]["items"]),
            len(spec["openings"]["doors"]),
            len(spec["openings"]["windows"]),
            float(spec["roof"]["pitch_deg"]),
            "si" if bool(spec.get("site", {}).get("garden_enabled", False)) else "no",
        )
    )
