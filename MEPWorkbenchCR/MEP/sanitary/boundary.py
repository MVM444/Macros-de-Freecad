"""
Nombre: boundary.py
Proposito: Contrato geometrico 2D neutral para referencias espaciales sanitarias.
Funcionamiento principal: Normaliza poligonos cerrados, calcula area/perimetro/centroide/bounding box y valida relaciones espaciales sin depender de FreeCAD.
Instrucciones para futuras modificaciones: Mantener este modulo independiente de FreeCAD, FreeCADGui, Qt y Draft. Los adaptadores de FreeCAD deben convertir sus objetos a listas de puntos XY antes de llamar este nucleo.
Version: 0.5.0
Fecha y hora: 2026-08-26 11:50 America/Costa_Rica
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import hypot
from typing import Iterable, List, Sequence, Tuple

Point2D = Tuple[float, float]
EPS = 1e-9


def _pt(value) -> Point2D:
    if len(value) < 2:
        raise ValueError("Cada punto debe contener X e Y")
    return float(value[0]), float(value[1])


def _same(a: Point2D, b: Point2D, eps: float = EPS) -> bool:
    return abs(a[0] - b[0]) <= eps and abs(a[1] - b[1]) <= eps


def normalize_closed_points(points: Iterable[Sequence[float]]) -> List[Point2D]:
    pts = [_pt(p) for p in points]
    if len(pts) < 3:
        raise ValueError("Se requieren al menos tres vertices")

    cleaned: List[Point2D] = []
    for p in pts:
        if not cleaned or not _same(cleaned[-1], p):
            cleaned.append(p)

    if len(cleaned) >= 2 and _same(cleaned[0], cleaned[-1]):
        cleaned.pop()
    if len(cleaned) < 3:
        raise ValueError("El contorno no contiene tres vertices distintos")

    cleaned.append(cleaned[0])
    return cleaned


def signed_area(points: Sequence[Point2D]) -> float:
    return 0.5 * sum(
        a[0] * b[1] - b[0] * a[1]
        for a, b in zip(points[:-1], points[1:])
    )


def polygon_area(points: Sequence[Point2D]) -> float:
    return abs(signed_area(points))


def polygon_perimeter(points: Sequence[Point2D]) -> float:
    return sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points[:-1], points[1:]))


def polygon_centroid(points: Sequence[Point2D]) -> Point2D:
    a = signed_area(points)
    if abs(a) <= EPS:
        raise ValueError("No se puede calcular centroide de un poligono de area cero")
    cx = cy = 0.0
    for p, q in zip(points[:-1], points[1:]):
        cross = p[0] * q[1] - q[0] * p[1]
        cx += (p[0] + q[0]) * cross
        cy += (p[1] + q[1]) * cross
    factor = 1.0 / (6.0 * a)
    return cx * factor, cy * factor


def bounding_box(points: Sequence[Point2D]):
    xs = [p[0] for p in points[:-1]]
    ys = [p[1] for p in points[:-1]]
    return {"min_x": min(xs), "min_y": min(ys), "max_x": max(xs), "max_y": max(ys)}


def _orient(a: Point2D, b: Point2D, c: Point2D) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Point2D, b: Point2D, p: Point2D) -> bool:
    return (
        min(a[0], b[0]) - EPS <= p[0] <= max(a[0], b[0]) + EPS
        and min(a[1], b[1]) - EPS <= p[1] <= max(a[1], b[1]) + EPS
        and abs(_orient(a, b, p)) <= EPS
    )


def segments_intersect(a: Point2D, b: Point2D, c: Point2D, d: Point2D) -> bool:
    o1, o2, o3, o4 = _orient(a, b, c), _orient(a, b, d), _orient(c, d, a), _orient(c, d, b)
    if ((o1 > EPS and o2 < -EPS) or (o1 < -EPS and o2 > EPS)) and ((o3 > EPS and o4 < -EPS) or (o3 < -EPS and o4 > EPS)):
        return True
    return any((
        abs(o1) <= EPS and _on_segment(a, b, c),
        abs(o2) <= EPS and _on_segment(a, b, d),
        abs(o3) <= EPS and _on_segment(c, d, a),
        abs(o4) <= EPS and _on_segment(c, d, b),
    ))


def polygon_is_simple(points: Sequence[Point2D]) -> bool:
    edges = list(zip(points[:-1], points[1:]))
    n = len(edges)
    for i, (a, b) in enumerate(edges):
        for j in range(i + 1, n):
            if j in (i, i + 1) or (i == 0 and j == n - 1):
                continue
            c, d = edges[j]
            if segments_intersect(a, b, c, d):
                return False
    return True


def point_in_polygon(point: Point2D, polygon: Sequence[Point2D], include_boundary: bool = True) -> bool:
    x, y = point
    inside = False
    for a, b in zip(polygon[:-1], polygon[1:]):
        if _on_segment(a, b, point):
            return include_boundary
        if (a[1] > y) != (b[1] > y):
            x_cross = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < x_cross:
                inside = not inside
    return inside


def polygon_contains(container: Sequence[Point2D], candidate: Sequence[Point2D]) -> bool:
    return all(point_in_polygon(p, container, include_boundary=True) for p in candidate[:-1])


def polygons_overlap(a: Sequence[Point2D], b: Sequence[Point2D]) -> bool:
    for e1 in zip(a[:-1], a[1:]):
        for e2 in zip(b[:-1], b[1:]):
            if segments_intersect(e1[0], e1[1], e2[0], e2[1]):
                return True
    return point_in_polygon(a[0], b) or point_in_polygon(b[0], a)


@dataclass(frozen=True)
class Boundary2D:
    boundary_id: str
    role: str
    points: List[Point2D]
    source_object: str = ""
    source_type: str = "GENERIC"

    @classmethod
    def from_points(cls, boundary_id: str, role: str, points, source_object: str = "", source_type: str = "GENERIC"):
        normalized = normalize_closed_points(points)
        if polygon_area(normalized) <= EPS:
            raise ValueError("El contorno tiene area cero")
        if not polygon_is_simple(normalized):
            raise ValueError("El contorno se autointersecta")
        return cls(boundary_id, role, normalized, source_object, source_type)

    @property
    def area(self) -> float:
        return polygon_area(self.points)

    @property
    def perimeter(self) -> float:
        return polygon_perimeter(self.points)

    @property
    def centroid(self) -> Point2D:
        return polygon_centroid(self.points)

    @property
    def bbox(self):
        return bounding_box(self.points)

    def to_dict(self):
        data = asdict(self)
        data.update({
            "area": self.area,
            "perimeter": self.perimeter,
            "centroid": list(self.centroid),
            "bbox": self.bbox,
            "closed": True,
        })
        return data
