"""Shared geometry-selection and fillet helpers for Conectar tools.

FreeCAD target: 1.1.3.

The selection resolver intentionally preserves one record per selected
subelement.  Do not reduce selection identity to DocumentObject.Name: two
faces, edges, or vertices of the same object are valid distinct endpoints.
"""

import math

import FreeCAD as App

try:
    import Part
except Exception:  # pragma: no cover - available inside FreeCAD
    Part = None


POINT_TOLERANCE_MM = 0.1
PICK_EDGE_TOLERANCE_MM = 0.5


def _vector(value):
    if value is None:
        return None
    try:
        return App.Vector(value)
    except Exception:
        pass
    try:
        return App.Vector(float(value.x), float(value.y), float(value.z))
    except Exception:
        return None


def _shape_type(subobject):
    return str(getattr(subobject, "ShapeType", "") or "").strip().upper()


def _edge_parameter_range(edge):
    try:
        return float(edge.FirstParameter), float(edge.LastParameter)
    except Exception:
        pass
    try:
        first, last = edge.ParameterRange
        return float(first), float(last)
    except Exception:
        return None


def _edge_midpoint(edge):
    limits = _edge_parameter_range(edge)
    if limits is not None:
        parameter = 0.5 * (limits[0] + limits[1])
        try:
            parameter = float(edge.getParameterByLength(float(edge.Length) * 0.5))
        except Exception:
            pass
        try:
            return _vector(edge.valueAt(parameter))
        except Exception:
            pass

    vertices = list(getattr(edge, "Vertexes", []) or [])
    if len(vertices) >= 2:
        p1 = _vector(vertices[0].Point)
        p2 = _vector(vertices[-1].Point)
        if p1 is not None and p2 is not None:
            return App.Vector(
                0.5 * (p1.x + p2.x),
                0.5 * (p1.y + p2.y),
                0.5 * (p1.z + p2.z),
            )
    if len(vertices) == 1:
        return _vector(vertices[0].Point)
    return None


def _is_linear_edge(edge):
    curve = getattr(edge, "Curve", None)
    if curve is None:
        return False
    text = "{} {}".format(
        getattr(curve, "TypeId", ""),
        curve.__class__.__name__,
    ).lower()
    return "line" in text and "bspline" not in text


def _circular_edge_center(edge):
    curve = getattr(edge, "Curve", None)
    if curve is None:
        return None
    text = "{} {}".format(
        getattr(curve, "TypeId", ""),
        curve.__class__.__name__,
    ).lower()
    if "circle" not in text and "arc" not in text:
        return None
    return _vector(getattr(curve, "Center", None))


def _picked_point_on_edge(edge, picked_point, tolerance=PICK_EDGE_TOLERANCE_MM):
    point = _vector(picked_point)
    if edge is None or point is None or Part is None:
        return None
    try:
        distance = float(edge.distToShape(Part.Vertex(point))[0])
    except Exception:
        return None
    if math.isfinite(distance) and distance <= max(0.0, float(tolerance)):
        return point
    return None


def point_from_edge(edge, picked_point=None):
    """Resolve a selected edge to a stable point.

    Circular edges always use the geometric center, even though FreeCAD also
    reports the point clicked on the circumference. For other edges, a native
    picked point is preferred only when it lies on the selected edge. Without
    a reliable hit, lines and other curves use their half-length/parameter
    point.
    """

    center = _circular_edge_center(edge)
    if center is not None:
        return center, "CIRCLE_CENTER"

    picked = _picked_point_on_edge(edge, picked_point)
    if picked is not None:
        return picked, "PICKEDPOINT"

    if _is_linear_edge(edge):
        return _edge_midpoint(edge), "EDGE"

    return _edge_midpoint(edge), "EDGE"


def point_from_subobject(subobject, picked_point=None):
    """Return ``(point, selection_type)`` for one FreeCAD subobject."""

    if subobject is None:
        return None, "UNKNOWN"
    kind = _shape_type(subobject)

    if kind == "VERTEX":
        return _vector(getattr(subobject, "Point", None)), "VERTEX"

    if kind == "FACE":
        return _vector(getattr(subobject, "CenterOfMass", None)), "FACE"

    if kind == "EDGE":
        return point_from_edge(subobject, picked_point=picked_point)

    point = _vector(getattr(subobject, "Point", None))
    if point is not None:
        return point, kind or "SUBOBJECT"
    point = _vector(getattr(subobject, "CenterOfMass", None))
    if point is not None:
        return point, kind or "SUBOBJECT"
    return None, kind or "UNKNOWN"


def _record(obj, subobject, subelement, point, selection_type, source, ordinal):
    return {
        "object": obj,
        "subobject": subobject,
        "subelement": str(subelement or ""),
        "point": _vector(point),
        "selection_type": str(selection_type or "UNKNOWN").upper(),
        "source": str(source or "unknown"),
        "ordinal": int(ordinal),
    }


def resolve_selection_ex_entry(selection_ex, fallback_resolver=None, ordinal_start=0):
    """Flatten one ``Gui.SelectionObject`` into ordered endpoint records."""

    obj = getattr(selection_ex, "Object", None)
    if obj is None:
        return []

    subobjects = list(getattr(selection_ex, "SubObjects", []) or [])
    names = list(getattr(selection_ex, "SubElementNames", []) or [])
    picked_points = list(getattr(selection_ex, "PickedPoints", []) or [])
    records = []

    for index, subobject in enumerate(subobjects):
        picked = picked_points[index] if index < len(picked_points) else None
        point, selection_type = point_from_subobject(subobject, picked_point=picked)
        if point is None:
            continue
        subelement = names[index] if index < len(names) else ""
        if not subelement:
            subelement = "{}{}".format(_shape_type(subobject).title(), index + 1)
        source = "picked" if selection_type == "PICKEDPOINT" else "subobject"
        records.append(
            _record(
                obj,
                subobject,
                subelement,
                point,
                selection_type,
                source,
                ordinal_start + len(records),
            )
        )

    if records:
        return records

    # A native picked point without a subelement is still an explicit 3D hit.
    for picked in picked_points:
        point = _vector(picked)
        if point is None:
            continue
        records.append(
            _record(
                obj,
                None,
                "",
                point,
                "PICKEDPOINT",
                "picked",
                ordinal_start + len(records),
            )
        )
    if records:
        return records

    point = fallback_resolver(obj) if callable(fallback_resolver) else None
    if point is None:
        placement = getattr(obj, "Placement", None)
        point = getattr(placement, "Base", None) if placement is not None else None
    point = _vector(point)
    if point is None:
        return []
    return [_record(obj, None, "", point, "OBJECT", "object", ordinal_start)]


def selection_identity(record, decimals=6):
    obj = record.get("object") if isinstance(record, dict) else None
    document = getattr(getattr(obj, "Document", None), "Name", "")
    object_name = getattr(obj, "Name", "") or "id:{}".format(id(obj))
    point = _vector(record.get("point")) if isinstance(record, dict) else None
    coords = None
    if point is not None:
        coords = tuple(round(float(value), int(decimals)) for value in (point.x, point.y, point.z))
    return (
        str(document or ""),
        str(object_name),
        str(record.get("subelement", "") or ""),
        str(record.get("selection_type", "") or ""),
        coords,
    )


def resolve_selection_ex_list(selection_ex_list, fallback_resolver=None):
    """Return ordered, distinct geometric selections from SelectionEx."""

    records = []
    ordinal = 0
    for selection_ex in list(selection_ex_list or []):
        current = resolve_selection_ex_entry(
            selection_ex,
            fallback_resolver=fallback_resolver,
            ordinal_start=ordinal,
        )
        records.extend(current)
        ordinal += len(current)

    output = []
    seen = set()
    for record in records:
        key = selection_identity(record)
        if key in seen:
            continue
        seen.add(key)
        output.append(record)
    return output


def deduplicate_points(points, tolerance=POINT_TOLERANCE_MM):
    output = []
    tol = max(0.0, float(tolerance))
    for value in list(points or []):
        point = _vector(value)
        if point is None:
            continue
        if output and float(output[-1].distanceToPoint(point)) <= tol:
            continue
        output.append(point)
    return output


def max_uniform_fillet_radius(points, tolerance=POINT_TOLERANCE_MM):
    """Return the maximum uniform fillet radius supported by the segments."""

    pts = deduplicate_points(points, tolerance=tolerance)
    if len(pts) < 3:
        return 0.0

    coefficients = [0.0] * len(pts)
    found_corner = False
    for index in range(1, len(pts) - 1):
        before = pts[index] - pts[index - 1]
        after = pts[index + 1] - pts[index]
        if before.Length <= tolerance or after.Length <= tolerance:
            continue
        before.normalize()
        after.normalize()
        dot = max(-1.0, min(1.0, float(before.dot(after))))
        turn = math.acos(dot)
        if turn <= 1e-6:
            continue
        if abs(math.pi - turn) <= 1e-6:
            return 0.0
        coefficient = math.tan(0.5 * turn)
        if not math.isfinite(coefficient) or coefficient <= 1e-9:
            continue
        coefficients[index] = coefficient
        found_corner = True

    if not found_corner:
        return 0.0

    capacity = float("inf")
    for index in range(len(pts) - 1):
        consumption = coefficients[index] + coefficients[index + 1]
        if consumption <= 1e-9:
            continue
        length = float(pts[index].distanceToPoint(pts[index + 1]))
        capacity = min(capacity, length / consumption)

    if not math.isfinite(capacity):
        return 0.0
    return max(0.0, capacity)


def effective_fillet_radius(points, requested_radius, safety_factor=0.98):
    requested = max(0.0, float(requested_radius or 0.0))
    capacity = max_uniform_fillet_radius(points)
    if requested <= 0.0 or capacity <= 0.0:
        return 0.0, capacity
    if requested < capacity:
        return requested, capacity
    return max(0.0, capacity * max(0.0, min(1.0, float(safety_factor)))), capacity
