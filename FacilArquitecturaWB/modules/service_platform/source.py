"""Resolve one authoritative straight source line and an optional BIM wall host."""

from __future__ import annotations

from dataclasses import dataclass

from ...core.opening_utils import (
    collect_bim_walls,
    is_bim_wall,
    select_best_host,
    wall_source_segments,
)
from .frame import build_axis_frame
from .validation import PlatformValidationError


@dataclass(frozen=True)
class AxisReference:
    source_object: object
    source_subelement: str
    first: tuple[float, float, float]
    second: tuple[float, float, float]
    source_kind: str

    def frame(self, invert=False):
        return build_axis_frame(self.first, self.second, invert=invert)

    @property
    def segment(self):
        return self.first + self.second


def resolve_axis_from_selection(selection_ex) -> AxisReference:
    """Accept one Sketch with one line or one directly selected linear edge."""
    records = [item for item in list(selection_ex or []) if getattr(item, "Object", None) is not None]
    if len(records) != 1:
        raise PlatformValidationError(
            "Seleccione exactamente una linea recta o un Sketch con una sola linea principal."
        )
    record = records[0]
    obj = record.Object
    if _is_sketch(obj):
        return _axis_from_sketch(obj)
    names = [str(name) for name in list(getattr(record, "SubElementNames", []) or [])]
    edge_names = [name for name in names if name.startswith("Edge")]
    if len(edge_names) > 1:
        raise PlatformValidationError("Seleccione una sola arista lineal, no varias aristas.")
    return axis_reference_from_source(obj, edge_names[0] if edge_names else "")


def axis_reference_from_source(obj, subelement="") -> AxisReference:
    """Reread a stored source object during an idempotent update."""
    if obj is None:
        raise PlatformValidationError("La plataforma perdio el enlace SourceObject.")
    if _is_sketch(obj):
        return _axis_from_sketch(obj)
    shape = getattr(obj, "Shape", None)
    if shape is None:
        raise PlatformValidationError("El objeto fuente ya no contiene una Shape lineal.")
    edge = None
    subelement = str(subelement or "")
    if subelement:
        try:
            edge = shape.getElement(subelement)
        except Exception as exc:
            raise PlatformValidationError(
                "No se pudo recuperar %s del objeto fuente." % subelement
            ) from exc
    else:
        edges = list(getattr(shape, "Edges", []) or [])
        if len(edges) != 1:
            raise PlatformValidationError(
                "El objeto seleccionado contiene %d aristas; seleccione una arista recta especifica."
                % len(edges)
            )
        edge = edges[0]
        subelement = "Edge1"
    first, second = _linear_edge_points(edge)
    build_axis_frame(first, second)
    return AxisReference(obj, subelement, first, second, "edge")


def find_host_wall(doc, axis_reference, existing=None, tolerance_mm=250.0):
    """Reuse a unique collinear native BIM wall; never creates a wall."""
    walls = collect_bim_walls(doc)
    records = []
    for wall in walls:
        segments = [item["segment"] for item in wall_source_segments(wall)]
        if segments:
            records.append({"wall": wall, "segments": segments})
    primary_records = [record for record in records if not _is_auxiliary_wall(record["wall"])]
    if primary_records:
        records = primary_records
    if not records:
        return existing if is_bim_wall(existing) else None, False
    result = select_best_host(axis_reference.segment, records, max_distance_mm=float(tolerance_mm))
    if result["ambiguous"]:
        return existing if is_bim_wall(existing) else None, True
    match = result["match"]
    if match is not None:
        return match["wall"], False
    return existing if is_bim_wall(existing) else None, False


def _axis_from_sketch(sketch):
    placement = _global_placement(sketch)
    candidates = []
    for index, geometry in enumerate(list(getattr(sketch, "Geometry", []) or [])):
        try:
            if bool(sketch.getConstruction(index)):
                continue
        except Exception:
            pass
        if not _is_line_geometry(geometry):
            raise PlatformValidationError(
                "El Sketch contiene geometria no lineal; debe tener una sola linea principal recta."
            )
        try:
            first = placement.multVec(geometry.StartPoint)
            second = placement.multVec(geometry.EndPoint)
        except Exception as exc:
            raise PlatformValidationError("No se pudieron leer los extremos del Sketch.") from exc
        candidates.append((index, _point(first), _point(second)))
    if len(candidates) != 1:
        raise PlatformValidationError(
            "El Sketch contiene %d lineas principales; debe contener exactamente una."
            % len(candidates)
        )
    index, first, second = candidates[0]
    build_axis_frame(first, second)
    return AxisReference(sketch, "Geometry%d" % (index + 1), first, second, "sketch")


def _linear_edge_points(edge):
    if str(getattr(edge, "ShapeType", "")) != "Edge":
        raise PlatformValidationError("El subelemento seleccionado no es una arista.")
    curve = getattr(edge, "Curve", None)
    type_id = str(getattr(curve, "TypeId", "") or "").lower()
    class_name = type(curve).__name__.lower()
    if "line" not in type_id and "line" not in class_name:
        raise PlatformValidationError("La arista seleccionada no es una linea recta.")
    vertices = list(getattr(edge, "Vertexes", []) or [])
    if len(vertices) != 2:
        raise PlatformValidationError("La arista lineal no tiene dos extremos utilizables.")
    return _point(vertices[0].Point), _point(vertices[1].Point)


def _is_sketch(obj):
    return str(getattr(obj, "TypeId", "") or "").startswith("Sketcher::")


def _is_line_geometry(geometry):
    type_id = str(getattr(geometry, "TypeId", "") or "").lower()
    class_name = type(geometry).__name__.lower()
    return (
        "line" in type_id
        or "linesegment" in class_name
    ) and hasattr(geometry, "StartPoint") and hasattr(geometry, "EndPoint")


def _global_placement(obj):
    try:
        return obj.getGlobalPlacement()
    except Exception:
        return obj.Placement


def _point(value):
    return float(value.x), float(value.y), float(getattr(value, "z", 0.0))


def _is_auxiliary_wall(wall):
    """Deprioritize explicit electrical/reference copies of an architectural wall."""
    text = " ".join(
        str(getattr(wall, name, "") or "")
        for name in ("Name", "Label", "FA_Role", "FA_ElementType")
    ).casefold()
    return any(
        token in text
        for token in (
            "auxiliar",
            "reference",
            "referencia electrica",
            "referencias electricas",
            "referencia eléctrica",
            "referencias eléctricas",
        )
    )
