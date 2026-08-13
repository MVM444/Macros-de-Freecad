# -*- coding: utf-8 -*-
"""Puertos tipados y heredados para conexiones ElectricCR.

Lee primero objetos vinculados mediante ``Ports`` y mantiene compatibilidad
con ``PuertosJSON`` de las cajas actuales. Centraliza reserva y seleccion de
puertos para alimentadores y backbone. Compatible con FreeCAD 1.1.3.
Creado: 2026-08-08 18:01 CST. Advertencia: ``Ports`` tipados tienen prioridad.
"""

import json
import math

import FreeCAD as App

from .panels import text


EPS = 1.0e-7


def normalize_xy(vector):
    length = math.hypot(float(vector.x), float(vector.y))
    if length <= EPS:
        return App.Vector(1.0, 0.0, 0.0)
    return App.Vector(float(vector.x) / length, float(vector.y) / length, 0.0)


def _global_placement(obj):
    try:
        return obj.getGlobalPlacement()
    except Exception:
        return getattr(obj, "Placement", App.Placement())


def _typed_port_data(owner, port):
    name = text(getattr(port, "PortName", getattr(port, "Name", "")))
    point = None
    direction = None
    for prop in ("Position", "Point", "LocalPosition"):
        try:
            value = getattr(port, prop)
            if hasattr(value, "x"):
                point = App.Vector(value)
                break
        except Exception:
            continue
    for prop in ("Direction", "Normal", "LocalDirection"):
        try:
            value = getattr(port, prop)
            if hasattr(value, "x"):
                direction = App.Vector(value)
                break
        except Exception:
            continue
    if point is None:
        try:
            point = App.Vector(_global_placement(port).Base)
        except Exception:
            return None
    else:
        try:
            point = _global_placement(owner).multVec(point)
        except Exception:
            pass
    if direction is None:
        direction = App.Vector(0.0, 0.0, 0.0)
    else:
        try:
            direction = _global_placement(owner).Rotation.multVec(direction)
        except Exception:
            pass
    return {"name": name or port.Name, "point": point, "dir": direction, "object": port}


def world_ports(obj):
    out = []
    seen = set()
    try:
        for port in list(getattr(obj, "Ports", []) or []):
            data = _typed_port_data(obj, port)
            if data is None or data["name"] in seen:
                continue
            seen.add(data["name"])
            out.append(data)
    except Exception:
        pass

    raw = text(getattr(obj, "PuertosJSON", "")).strip()
    if raw:
        try:
            items = json.loads(raw)
        except Exception:
            items = []
        placement = _global_placement(obj)
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            name = text(item.get("name", ""))
            position = item.get("position")
            direction = item.get("direction")
            if not name or name in seen or not isinstance(position, list) or len(position) != 3:
                continue
            try:
                local = App.Vector(float(position[0]), float(position[1]), float(position[2]))
                point = placement.multVec(local)
                if isinstance(direction, list) and len(direction) == 3:
                    local_dir = App.Vector(float(direction[0]), float(direction[1]), float(direction[2]))
                    world_dir = placement.Rotation.multVec(local_dir)
                else:
                    world_dir = App.Vector(0.0, 0.0, 0.0)
            except Exception:
                continue
            seen.add(name)
            out.append({"name": name, "point": point, "dir": world_dir, "object": None})
    return out


def fallback_port(obj, toward_point=None):
    try:
        bb = obj.Shape.BoundBox
        point = App.Vector(float(bb.Center.x), float(bb.Center.y), float(bb.ZMax))
    except Exception:
        point = App.Vector(_global_placement(obj).Base)
    toward = App.Vector(toward_point) if toward_point is not None else point + App.Vector(1.0, 0.0, 0.0)
    return {"name": "Superior", "point": point, "dir": normalize_xy(toward - point), "object": None}


def choose_port(obj, toward_point, occupied=None, allow_bottom=False):
    occupied = set(occupied or [])
    ports = []
    for port in world_ports(obj):
        if not allow_bottom and port["name"].strip().lower() in ("bottom", "inferior", "abajo"):
            continue
        ports.append(port)
    if not ports:
        return fallback_port(obj, toward_point)

    target = App.Vector(toward_point)

    def score(port):
        toward = normalize_xy(target - port["point"])
        direction = normalize_xy(port["dir"])
        alignment = float(direction.dot(toward))
        distance = math.hypot(float(target.x - port["point"].x), float(target.y - port["point"].y))
        return (1 if port["name"] in occupied else 0, -alignment, distance, port["name"])

    chosen = sorted(ports, key=score)[0]
    direction = normalize_xy(chosen["dir"])
    if chosen["dir"].Length <= EPS:
        direction = normalize_xy(target - chosen["point"])
    result = dict(chosen)
    result["dir"] = direction
    result["reused"] = chosen["name"] in occupied
    return result


def _linked_name(value):
    try:
        return text(value.Name)
    except Exception:
        return text(value)


def occupied_port_map(doc, owners, ignored_generators=None):
    owner_names = {obj.Name for obj in list(owners or [])}
    occupied = {name: set() for name in owner_names}
    ignored = set(ignored_generators or [])
    for route in list(doc.Objects):
        if text(getattr(route, "GeneradoPor", "")) in ignored:
            continue
        props = set(getattr(route, "PropertiesList", []) or [])
        for object_prop, port_prop in (
            ("CajaOrigen", "PuertoOrigen"),
            ("CajaDestinoLink", "PuertoDestino"),
            ("Origen", "PuertoOrigen"),
            ("Destino", "PuertoDestino"),
        ):
            if object_prop not in props or port_prop not in props:
                continue
            try:
                owner_name = _linked_name(getattr(route, object_prop))
                port_name = text(getattr(route, port_prop, ""))
            except Exception:
                continue
            if owner_name in occupied and port_name:
                occupied[owner_name].add(port_name)
        if "CajaDestino" in props and "PuertoDestino" in props:
            owner_name = text(getattr(route, "CajaDestino", ""))
            port_name = text(getattr(route, "PuertoDestino", ""))
            if owner_name in occupied and port_name:
                occupied[owner_name].add(port_name)
    return occupied
