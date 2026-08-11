# -*- coding: utf-8 -*-
"""Geometria comun de rutas ElectricCR.

Provee ruteo ortogonal directo, ruteo guiado opcional, carriles, limpieza de
retrocesos y curvas. Reemplaza primitivas duplicadas en macros TP/TCOM y en el
flujo tablero-tablero. Compatible con FreeCAD 1.1.3. Creado: 2026-08-08 18:01 CST.
Advertencia: una guia mejora la ruta, pero nunca es requisito de ejecucion.
"""

import math

import FreeCAD as App
import Part

from .panels import normalized, text
from .ports import normalize_xy


EPS = 1.0e-7


def dedupe(points, tolerance=0.01):
    result = []
    for point in list(points or []):
        value = App.Vector(point)
        if not result or result[-1].distanceToPoint(value) > tolerance:
            result.append(value)
    return result


def _collinear(a, b, c, tolerance=0.01):
    first = b - a
    second = c - b
    if first.Length <= tolerance or second.Length <= tolerance:
        return True
    return first.cross(second).Length <= tolerance * first.Length * second.Length


def simplify(points, tolerance=0.01):
    pts = dedupe(points, tolerance)
    if len(pts) < 3:
        return pts
    changed = True
    while changed and len(pts) >= 3:
        changed = False
        out = [pts[0]]
        for index in range(1, len(pts) - 1):
            a, b, c = out[-1], pts[index], pts[index + 1]
            if _collinear(a, b, c, tolerance):
                # Elimina tanto puntos en el mismo sentido como sobrepasos
                # A-B-A. Esto evita backtracking antes de aplicar fillet.
                changed = True
                continue
            out.append(b)
        out.append(pts[-1])
        pts = dedupe(out, tolerance)
    return pts


def polyline_length(points):
    pts = list(points or [])
    return sum(a.distanceToPoint(b) for a, b in zip(pts[:-1], pts[1:]))


def rounded_wire(points, radius):
    pts = simplify(points)
    if len(pts) < 2:
        raise RuntimeError("Ruta con menos de dos puntos.")
    if len(pts) == 2 or float(radius) <= 0.1:
        return Part.makePolygon(pts)
    edges = []
    cursor = pts[0]
    for index in range(1, len(pts) - 1):
        a, b, c = pts[index - 1], pts[index], pts[index + 1]
        incoming, outgoing = b - a, c - b
        len_in, len_out = incoming.Length, outgoing.Length
        if len_in <= EPS or len_out <= EPS:
            continue
        vin, vout = incoming / len_in, outgoing / len_out
        if abs(float(vin.dot(vout))) > 0.999:
            if cursor.distanceToPoint(b) > EPS:
                edges.append(Part.makeLine(cursor, b))
            cursor = b
            continue
        cut = min(float(radius), 0.35 * len_in, 0.35 * len_out)
        if cut <= 0.5:
            if cursor.distanceToPoint(b) > EPS:
                edges.append(Part.makeLine(cursor, b))
            cursor = b
            continue
        q1 = b - vin * cut
        q2 = b + vout * cut
        if cursor.distanceToPoint(q1) > EPS:
            edges.append(Part.makeLine(cursor, q1))
        center = b - vin * cut + vout * cut
        radial = (q1 - center) + (q2 - center)
        if radial.Length <= EPS:
            edges.append(Part.makeLine(q1, q2))
        else:
            midpoint = center + radial / radial.Length * cut
            try:
                edges.append(Part.Arc(q1, midpoint, q2).toShape())
            except Exception:
                edges.append(Part.makeLine(q1, q2))
        cursor = q2
    if cursor.distanceToPoint(pts[-1]) > EPS:
        edges.append(Part.makeLine(cursor, pts[-1]))
    try:
        return Part.Wire(edges)
    except Exception:
        return Part.makePolygon(pts)


def polyline_points(obj):
    points = []
    try:
        values = list(getattr(obj, "Points", []) or [])
        if len(values) >= 2:
            points = [App.Vector(value) for value in values]
    except Exception:
        points = []
    if len(points) < 2:
        try:
            points = [App.Vector(vertex.Point) for vertex in list(obj.Shape.Vertexes)]
        except Exception:
            points = []
    return dedupe(points)


def is_guide(obj, explicit=False):
    if obj is None or hasattr(obj, "Group") or len(polyline_points(obj)) < 2:
        return False
    if explicit:
        return True
    probe = normalized(
        "{} {} {} {}".format(
            getattr(obj, "Name", ""),
            getattr(obj, "Label", ""),
            getattr(obj, "Tipo", ""),
            getattr(obj, "GeneradoPor", ""),
        )
    )
    return "guia" in probe or "guide" in probe or "rutapropuesta" in probe


def _orthogonal_leg(a, b, z, first_axis=None):
    start = App.Vector(float(a.x), float(a.y), float(z))
    end = App.Vector(float(b.x), float(b.y), float(z))
    if start.distanceToPoint(end) <= 0.01:
        return [start]
    axis = str(first_axis or "").lower()
    if axis not in ("x", "y"):
        axis = "x" if abs(float(end.x - start.x)) >= abs(float(end.y - start.y)) else "y"
    corner = App.Vector(end.x, start.y, z) if axis == "x" else App.Vector(start.x, end.y, z)
    return simplify([start, corner, end])


def _orthogonalize(points, z):
    source = [App.Vector(float(p.x), float(p.y), float(z)) for p in list(points or [])]
    if len(source) < 2:
        return source
    out = [source[0]]
    for point in source[1:]:
        out.extend(_orthogonal_leg(out[-1], point, z)[1:])
    return simplify(out)


def offset_polyline(points, offset, z):
    pts = _orthogonalize(points, z)
    if len(pts) < 2 or abs(float(offset)) <= 0.01:
        return pts
    normals = []
    for a, b in zip(pts[:-1], pts[1:]):
        direction = normalize_xy(b - a)
        normals.append(App.Vector(-direction.y, direction.x, 0.0))
    out = []
    for index, point in enumerate(pts):
        if index == 0:
            normal = normals[0]
        elif index == len(pts) - 1:
            normal = normals[-1]
        else:
            normal = normals[index - 1] + normals[index]
            if normal.Length <= EPS:
                normal = normals[index]
            else:
                normal = normal / normal.Length
        out.append(App.Vector(point.x + normal.x * offset, point.y + normal.y * offset, z))
    return simplify(out)


def project_to_polyline(point, points):
    target = App.Vector(point)
    best = None
    traversed = 0.0
    pts = list(points or [])
    for index, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
        vector = b - a
        length2 = float(vector.dot(vector))
        if length2 <= EPS:
            continue
        factor = max(0.0, min(1.0, float((target - a).dot(vector)) / length2))
        projected = a + vector * factor
        distance = target.distanceToPoint(projected)
        along = traversed + a.distanceToPoint(projected)
        candidate = (distance, along, index, factor, projected)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
        traversed += a.distanceToPoint(b)
    return best


def _subpath(points, first_projection, second_projection):
    if first_projection is None or second_projection is None:
        return []
    pts = list(points or [])
    _d1, along1, index1, _t1, point1 = first_projection
    _d2, along2, index2, _t2, point2 = second_projection
    reverse = along1 > along2
    if reverse:
        index1, index2 = index2, index1
        point1, point2 = point2, point1
    out = [App.Vector(point1)]
    for index in range(index1 + 1, index2 + 1):
        out.append(App.Vector(pts[index]))
    out.append(App.Vector(point2))
    out = simplify(out)
    if reverse:
        out.reverse()
    return out


def best_guide(guides, source, destination, lane_offset=0.0, route_z=0.0):
    best = None
    for guide in list(guides or []):
        raw = polyline_points(guide)
        if len(raw) < 2:
            continue
        points = offset_polyline(raw, lane_offset, route_z)
        first = project_to_polyline(source, points)
        second = project_to_polyline(destination, points)
        if first is None or second is None:
            continue
        score = float(first[0]) + float(second[0]) + 0.05 * abs(float(first[1]) - float(second[1]))
        candidate = (score, text(getattr(guide, "Name", "")), guide, points, first, second)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return best


def guided_route(source, source_direction, destination, guides, lane_index, lane_count, cfg):
    route_z = max(float(cfg["route_z"]), float(source.z) + 50.0, float(destination.z) + 50.0)
    stub = float(cfg["port_stub"])
    spacing = float(cfg["lane_spacing"])
    centered = float(lane_index) - 0.5 * float(max(0, lane_count - 1))
    offset = centered * spacing
    p0 = App.Vector(source)
    direction = normalize_xy(source_direction)
    p1 = App.Vector(p0.x + direction.x * stub, p0.y + direction.y * stub, p0.z)
    p2 = App.Vector(p1.x, p1.y, route_z)
    end_plan = App.Vector(destination.x, destination.y, route_z)
    choice = best_guide(guides, p2, end_plan, offset, route_z)
    if choice is None:
        return None
    _score, _name, guide, points, first, second = choice
    corridor = _subpath(points, first, second)
    if len(corridor) < 2:
        return None
    start_axis = "x" if abs(direction.x) >= abs(direction.y) else "y"
    route = [p0, p1, p2]
    route.extend(_orthogonal_leg(route[-1], corridor[0], route_z, first_axis=start_axis)[1:])
    route.extend(corridor[1:])
    route.extend(_orthogonal_leg(route[-1], end_plan, route_z)[1:])
    route.append(App.Vector(destination))
    return simplify(route), guide


def direct_circuit_route(source, source_direction, destination, panel_bb, rank, cfg):
    route_z = max(float(cfg["route_z"]), float(source.z) + 50.0, float(destination.z) + 50.0)
    stub = float(cfg["port_stub"])
    spacing = float(cfg["lane_spacing"])
    clearance = float(cfg["approach_clearance"])
    p0 = App.Vector(source)
    direction = normalize_xy(source_direction)
    p1 = App.Vector(p0.x + direction.x * stub, p0.y + direction.y * stub, p0.z)
    p2 = App.Vector(p1.x, p1.y, route_z)
    center = panel_bb.Center
    dx = float(p2.x - center.x)
    dy = float(p2.y - center.y)
    side = "North" if abs(dy) >= abs(dx) and dy >= 0.0 else "South" if abs(dy) >= abs(dx) else "East" if dx >= 0.0 else "West"
    offset = clearance + float(rank) * spacing
    if side == "North":
        lane = float(panel_bb.YMax) + offset
        middle = [App.Vector(p2.x, lane, route_z), App.Vector(destination.x, lane, route_z)]
    elif side == "South":
        lane = float(panel_bb.YMin) - offset
        middle = [App.Vector(p2.x, lane, route_z), App.Vector(destination.x, lane, route_z)]
    elif side == "East":
        lane = float(panel_bb.XMax) + offset
        middle = [App.Vector(lane, p2.y, route_z), App.Vector(lane, destination.y, route_z)]
    else:
        lane = float(panel_bb.XMin) - offset
        middle = [App.Vector(lane, p2.y, route_z), App.Vector(lane, destination.y, route_z)]
    end_plan = App.Vector(destination.x, destination.y, route_z)
    return simplify([p0, p1, p2] + middle + [end_plan, App.Vector(destination)]), side


def direct_equipment_route(source, destination, lane_index, lane_count, cfg):
    route_z = max(float(cfg["route_z"]), float(source.z), float(destination.z))
    spacing = float(cfg["lane_spacing"])
    centered = float(lane_index) - 0.5 * float(max(0, lane_count - 1))
    p0 = App.Vector(source)
    p1 = App.Vector(source.x, source.y, route_z)
    end_plan = App.Vector(destination.x, destination.y, route_z)
    if abs(float(destination.x - source.x)) >= abs(float(destination.y - source.y)):
        lane = 0.5 * float(source.y + destination.y) + centered * spacing
        middle = [App.Vector(source.x, lane, route_z), App.Vector(destination.x, lane, route_z)]
    else:
        lane = 0.5 * float(source.x + destination.x) + centered * spacing
        middle = [App.Vector(lane, source.y, route_z), App.Vector(lane, destination.y, route_z)]
    return simplify([p0, p1] + middle + [end_plan, App.Vector(destination)])
