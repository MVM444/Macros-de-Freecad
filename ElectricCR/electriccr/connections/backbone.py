# -*- coding: utf-8 -*-
"""Motor general de backbone de cajas octogonales ElectricCR.

Conecta cajas del mismo circuito mediante un arbol minimo, reserva puertos,
crea rutas ortogonales con curvas y actualiza por clave sin depender del nombre
TP o TCOM. Compatible con FreeCAD 1.1.3. Creado: 2026-08-08 18:01 CST.
Advertencia: conservar grupos de ruta fuera del grupo de circuito para evitar DAG.
"""

import json
import math
import re

import FreeCAD as App

from . import feeders, panels, ports, routing


TAG = "[ElectricCR][BACKBONE]"
GENERATED_BY = "ElectricCR.Connections.Backbone.v1"
LEGACY_GENERATORS = {
    "Conectar_Octogonales_Ortogonal_por_Circuito_TP",
    "Conectar_Octogonales_Ortogonal_por_Circuito_TCOM",
}
DEFAULT_CONFIG = {
    "route_z": 3400.0,
    "bend_radius": 100.0,
    "port_stub": 80.0,
    "diameter": 22.2,
}
EPS = 1.0e-7


def _log(message):
    App.Console.PrintMessage("{} {}\n".format(TAG, message))


def _warn(message):
    App.Console.PrintWarning("{} {}\n".format(TAG, message))


def _ensure(obj, ptype, name, group, description):
    if name not in set(getattr(obj, "PropertiesList", []) or []):
        obj.addProperty(ptype, name, group, description)


def _unique_name(doc, prefix):
    if doc.getObject(prefix) is None:
        return prefix
    index = 1
    while doc.getObject("{}_{:03d}".format(prefix, index)) is not None:
        index += 1
    return "{}_{:03d}".format(prefix, index)


def _center(box):
    bb = box.Shape.BoundBox
    return App.Vector(float(bb.Center.x), float(bb.Center.y), float(bb.Center.z))


def _distance_xy(first, second):
    return math.hypot(float(first.x - second.x), float(first.y - second.y))


def minimum_spanning_edges(boxes, root_box=None):
    nodes = list(boxes or [])
    if len(nodes) < 2:
        return []
    root = root_box if root_box in nodes else sorted(nodes, key=lambda item: item.Name)[0]
    visited = {root.Name}
    result = []
    while len(visited) < len(nodes):
        best = None
        for source in nodes:
            if source.Name not in visited:
                continue
            for destination in nodes:
                if destination.Name in visited:
                    continue
                candidate = (_distance_xy(_center(source), _center(destination)), source.Name, destination.Name, source, destination)
                if best is None or candidate[:3] < best[:3]:
                    best = candidate
        if best is None:
            raise RuntimeError("No se pudo completar el arbol de cajas.")
        _weight, _source_name, _destination_name, source, destination = best
        result.append((source, destination))
        visited.add(destination.Name)
    return result


def _root_from_feeder(doc, cid, boxes):
    allowed = {feeders.GENERATED_BY} | feeders.LEGACY_GENERATORS
    for obj in list(doc.Objects):
        if panels.text(getattr(obj, "GeneradoPor", "")) not in allowed:
            continue
        if panels.text(getattr(obj, "CircuitoID", "")) != cid:
            continue
        try:
            source = getattr(obj, "CajaOrigen", None)
            if source in boxes:
                return source
        except Exception:
            pass
    return None


def _segment_distance_xy(point, first, second):
    ax, ay = float(first.x), float(first.y)
    bx, by = float(second.x), float(second.y)
    px, py = float(point.x), float(point.y)
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 <= EPS:
        return math.hypot(px - ax, py - ay)
    factor = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + factor * dx), py - (ay + factor * dy))


def _candidate_penalty(points, boxes, endpoints):
    penalty = 0.0
    for box in boxes:
        if box.Name in endpoints:
            continue
        center = _center(box)
        for first, second in zip(points[:-1], points[1:]):
            distance = _segment_distance_xy(center, first, second)
            if distance < 120.0:
                penalty += (120.0 - distance) * 10.0
    return penalty + routing.polyline_length(points)


def _route(source, destination, source_port, destination_port, boxes, cfg):
    route_z = max(float(cfg["route_z"]), float(source_port["point"].z) + 50.0, float(destination_port["point"].z) + 50.0)
    stub = float(cfg["port_stub"])
    p0 = App.Vector(source_port["point"])
    p1 = App.Vector(p0.x + source_port["dir"].x * stub, p0.y + source_port["dir"].y * stub, p0.z)
    p2 = App.Vector(p1.x, p1.y, route_z)
    q0 = App.Vector(destination_port["point"])
    q1 = App.Vector(q0.x + destination_port["dir"].x * stub, q0.y + destination_port["dir"].y * stub, q0.z)
    q2 = App.Vector(q1.x, q1.y, route_z)
    candidates = [
        routing.simplify([p2, App.Vector(q2.x, p2.y, route_z), q2]),
        routing.simplify([p2, App.Vector(p2.x, q2.y, route_z), q2]),
    ]
    middle = min(candidates, key=lambda points: _candidate_penalty(points, boxes, {source.Name, destination.Name}))
    return routing.simplify([p0, p1] + middle + [q1, q0])


def connection_key(cid, source, destination):
    names = sorted((source.Name, destination.Name))
    return "{}|{}|{}".format(cid, names[0], names[1])


def _find_existing(doc, key):
    for obj in list(doc.Objects):
        generated = panels.text(getattr(obj, "GeneradoPor", ""))
        if generated != GENERATED_BY and generated not in LEGACY_GENERATORS:
            continue
        if panels.text(getattr(obj, "ConexionKey", "")) == key:
            return obj
    return None


def _route_group(doc):
    root = doc.getObject("ElectricCR_Conexiones")
    if root is None:
        root = doc.addObject("App::DocumentObjectGroup", "ElectricCR_Conexiones")
        root.Label = "Conexiones ElectricCR"
    group = doc.getObject("ElectricCR_Backbone")
    if group is None:
        group = doc.addObject("App::DocumentObjectGroup", "ElectricCR_Backbone")
        group.Label = "Circuitos / Backbone"
    if group not in list(getattr(root, "Group", []) or []):
        root.addObject(group)
    return group


def _move_to_group(route, group):
    for parent in list(getattr(route, "InList", []) or []):
        if parent is group or not panels.is_group(parent):
            continue
        try:
            parent.removeObject(route)
        except Exception:
            pass
    if route not in list(getattr(group, "Group", []) or []):
        group.addObject(route)


def _style(route):
    try:
        color = (0.10, 0.72, 0.95)
        route.ViewObject.LineColor = color
        route.ViewObject.PointColor = color
        route.ViewObject.ShapeColor = color
        route.ViewObject.LineWidth = 3.0
    except Exception:
        pass


def _write(doc, circuit_group, cid, index, source, destination, source_port, destination_port, points, cfg):
    key = connection_key(cid, source, destination)
    route = _find_existing(doc, key)
    created = route is None
    if route is None:
        token = re.sub(r"[^0-9A-Za-z_]+", "_", cid)
        route = doc.addObject("Part::Feature", _unique_name(doc, "Backbone_{}_{:02d}".format(token, index)))
    group = _route_group(doc)
    _move_to_group(route, group)
    route.Shape = routing.rounded_wire(points, cfg["bend_radius"])
    route.Label = "Backbone {}: {} -> {}".format(cid, source.Label, destination.Label)
    definitions = (
        ("App::PropertyString", "Tipo", "ElectricCR", "Tipo logico"),
        ("App::PropertyString", "GeneradoPor", "ElectricCR", "Motor generador"),
        ("App::PropertyString", "CircuitoID", "ElectricCR", "Circuito"),
        ("App::PropertyString", "ConexionKey", "ElectricCR", "Clave idempotente"),
        ("App::PropertyLink", "Circuit", "Vinculos", "Objeto o grupo de circuito"),
        ("App::PropertyLink", "CajaOrigen", "Vinculos", "Caja origen"),
        ("App::PropertyLink", "CajaDestinoLink", "Vinculos", "Caja destino"),
        ("App::PropertyLink", "Origen", "Vinculos", "Origen generico"),
        ("App::PropertyLink", "Destino", "Vinculos", "Destino generico"),
        ("App::PropertyString", "PuertoOrigen", "Puertos", "Puerto origen"),
        ("App::PropertyString", "PuertoDestino", "Puertos", "Puerto destino"),
        ("App::PropertyVector", "PuntoOrigen", "Puertos", "Punto inicial"),
        ("App::PropertyVector", "PuntoDestino", "Puertos", "Punto final"),
        ("App::PropertyVectorList", "Points", "Ruta", "Puntos mundiales"),
        ("App::PropertyString", "RutaJSON", "Ruta", "Puntos mundiales JSON"),
        ("App::PropertyString", "EstadoConexion", "Ruta", "Estado"),
        ("App::PropertyFloat", "AlturaRuta", "Ruta", "Cota de distribucion"),
        ("App::PropertyFloat", "DiametroEMT", "Ruta", "Diametro EMT"),
        ("App::PropertyFloat", "Longitud_m", "Calculo", "Longitud en metros"),
    )
    for definition in definitions:
        _ensure(route, *definition)
    route.Tipo = "BackboneCircuito"
    route.GeneradoPor = GENERATED_BY
    route.CircuitoID = cid
    route.ConexionKey = key
    route.Circuit = circuit_group
    route.CajaOrigen = source
    route.CajaDestinoLink = destination
    route.Origen = source
    route.Destino = destination
    route.PuertoOrigen = source_port["name"]
    route.PuertoDestino = destination_port["name"]
    route.PuntoOrigen = App.Vector(source_port["point"])
    route.PuntoDestino = App.Vector(destination_port["point"])
    route.Points = [App.Vector(point) for point in points]
    route.RutaJSON = json.dumps([[p.x, p.y, p.z] for p in points], separators=(",", ":"))
    route.EstadoConexion = "Conectado"
    route.AlturaRuta = float(cfg["route_z"])
    route.DiametroEMT = float(cfg["diameter"])
    route.Longitud_m = float(route.Shape.Length) / 1000.0
    _style(route)
    return route, created


def _delete_stale(doc, processed_ids, valid_keys):
    deleted = 0
    for obj in list(doc.Objects):
        generated = panels.text(getattr(obj, "GeneradoPor", ""))
        if generated != GENERATED_BY and generated not in LEGACY_GENERATORS:
            continue
        cid = panels.text(getattr(obj, "CircuitoID", ""))
        key = panels.text(getattr(obj, "ConexionKey", ""))
        if cid in processed_ids and key and key not in valid_keys:
            doc.removeObject(obj.Name)
            deleted += 1
    return deleted


def _cleanup_groups(doc):
    for group in list(doc.Objects):
        if not panels.is_group(group) or list(getattr(group, "Group", []) or []):
            continue
        generated = panels.text(getattr(group, "GeneradoPor", ""))
        if generated in LEGACY_GENERATORS:
            try:
                doc.removeObject(group.Name)
            except Exception:
                pass


def connect_backbone(doc, circuit_groups=None, cfg=None, circuit_prefix=None):
    config = dict(DEFAULT_CONFIG)
    config.update(dict(cfg or {}))
    for key in DEFAULT_CONFIG:
        config[key] = float(config[key])
    selected_names = {obj.Name for obj in list(circuit_groups or []) if panels.is_group(obj)}
    candidates = feeders.candidate_circuit_groups(doc, prefix=circuit_prefix)
    if selected_names:
        candidates = [item for item in candidates if item[1].Name in selected_names]
    if not candidates:
        return {"routes": [], "created": 0, "updated": 0, "deleted": 0, "errors": ["No se encontraron circuitos con cajas"]}

    all_boxes = list({box.Name: box for _cid, _group, boxes in candidates for box in boxes}.values())
    occupied = ports.occupied_port_map(doc, all_boxes, ignored_generators={GENERATED_BY} | LEGACY_GENERATORS)
    plans = []
    for cid, group, boxes in candidates:
        root = _root_from_feeder(doc, cid, boxes)
        plans.append((cid, group, boxes, minimum_spanning_edges(boxes, root_box=root)))

    routes = []
    created = updated = 0
    valid_keys = set()
    processed_ids = {cid for cid, _group, _boxes, _edges in plans}
    doc.openTransaction("ElectricCR: conectar backbone general")
    try:
        for cid, group, boxes, edges in plans:
            for index, (source, destination) in enumerate(edges, start=1):
                source_port = ports.choose_port(source, _center(destination), occupied.get(source.Name, set()))
                occupied.setdefault(source.Name, set()).add(source_port["name"])
                destination_port = ports.choose_port(destination, _center(source), occupied.get(destination.Name, set()))
                occupied.setdefault(destination.Name, set()).add(destination_port["name"])
                points = _route(source, destination, source_port, destination_port, boxes, config)
                route, was_created = _write(
                    doc, group, cid, index, source, destination, source_port, destination_port, points, config
                )
                routes.append(route)
                valid_keys.add(route.ConexionKey)
                created += int(was_created)
                updated += int(not was_created)
                _log(
                    "Circuito={} Origen={} Destino={} PuertoOrigen={} PuertoDestino={} Resultado={}".format(
                        cid,
                        source.Name,
                        destination.Name,
                        source_port["name"],
                        destination_port["name"],
                        "CREADO" if was_created else "ACTUALIZADO",
                    )
                )
        deleted = _delete_stale(doc, processed_ids, valid_keys)
        _cleanup_groups(doc)
        doc.recompute()
        doc.commitTransaction()
    except Exception as exc:
        try:
            doc.abortTransaction()
        except Exception:
            pass
        _warn("Fallo general: {}".format(exc))
        return {"routes": [], "created": 0, "updated": 0, "deleted": 0, "errors": [panels.text(exc)]}
    return {
        "routes": routes,
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "errors": [],
        "single_box_circuits": [cid for cid, _group, boxes, _edges in plans if len(boxes) == 1],
    }
