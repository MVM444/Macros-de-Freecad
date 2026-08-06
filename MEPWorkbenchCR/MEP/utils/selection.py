"""Selection helpers with App::Link awareness."""

import FreeCAD as App
import Part

try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - console mode
    Gui = None


def _safe_gui_selection():
    if Gui is None:
        return []
    try:
        return Gui.Selection.getSelectionEx() or []
    except Exception:
        return []


def get_selection_ex():
    """Return the native extended selection, including selected subelements."""

    return list(_safe_gui_selection() or [])


def unwrap_link(obj):
    """Return linked target when the input is App::Link, otherwise itself."""

    if obj is None:
        return None
    if hasattr(obj, "isDerivedFrom"):
        try:
            if obj.isDerivedFrom("App::Link") and getattr(obj, "LinkedObject", None):
                return obj.LinkedObject
        except Exception:
            pass
    return obj


def get_selected_objects(resolve_links=True):
    """Return current GUI selection as document objects."""

    objects = []
    for sel in _safe_gui_selection():
        obj = getattr(sel, "Object", None)
        if resolve_links:
            obj = unwrap_link(obj)
        if obj is not None:
            objects.append(obj)
    return objects


def first_selected_object(resolve_links=True):
    """Return first selected object or None."""

    objects = get_selected_objects(resolve_links=resolve_links)
    if objects:
        return objects[0]
    return None


def get_selected_points():
    """Collect point vectors from selected sub-elements when available."""

    points = []
    for sel in _safe_gui_selection():
        for sub in getattr(sel, "SubObjects", []) or []:
            if hasattr(sub, "Point"):
                points.append(App.Vector(sub.Point))
            elif hasattr(sub, "CenterOfMass"):
                points.append(App.Vector(sub.CenterOfMass))
    return points


def _edge_midpoint_and_tangent(edge):
    """Return the half-length point and tangent of a selected Part edge."""

    if edge is None:
        return None, None
    try:
        first = float(edge.FirstParameter)
        last = float(edge.LastParameter)
    except Exception:
        try:
            first, last = [float(value) for value in edge.ParameterRange]
        except Exception:
            return None, None

    parameter = (first + last) * 0.5
    try:
        parameter = float(edge.getParameterByLength(float(edge.Length) * 0.5))
    except Exception:
        pass

    try:
        point = App.Vector(edge.valueAt(parameter))
    except Exception:
        return None, None
    try:
        tangent = App.Vector(edge.tangentAt(parameter))
    except Exception:
        tangent = None
    return point, tangent


def _nearest_edge_to_point(edges, point):
    """Return ``(index, edge)`` nearest to a native picked point."""

    try:
        picked = App.Vector(point)
        vertex = Part.Vertex(picked)
    except Exception:
        return None, None

    best = None
    for index, edge in enumerate(list(edges or [])):
        try:
            distance = float(edge.distToShape(vertex)[0])
        except Exception:
            try:
                midpoint, _tangent = _edge_midpoint_and_tangent(edge)
                distance = float((midpoint - picked).Length) if midpoint is not None else float("inf")
            except Exception:
                distance = float("inf")
        candidate = (distance, index, edge)
        if best is None or candidate[0] < best[0]:
            best = candidate
    if best is None:
        return None, None
    return int(best[1]), best[2]


def _owner_edge_name(obj, edge, fallback_index=None):
    shape = getattr(obj, "Shape", None) if obj is not None else None
    try:
        owner_edges = list(shape.Edges or [])
    except Exception:
        owner_edges = []
    for index, candidate in enumerate(owner_edges):
        try:
            if candidate.isSame(edge):
                return "Edge{0}".format(index + 1)
        except Exception:
            continue
    if fallback_index is not None:
        return "Edge{0}".format(int(fallback_index) + 1)
    return "Edge1"


def get_selected_linear_reference():
    """Return the first selected edge or whole single-edge object.

    The returned mapping keeps the native owner so downstream commands can
    preserve BIM/MEP relationships instead of reducing the selection to a
    coordinate only.
    """

    selected = get_selection_ex()

    # An explicitly selected subedge always has priority.
    for sel in selected:
        obj = getattr(sel, "Object", None)
        subobjects = list(getattr(sel, "SubObjects", []) or [])
        names = list(getattr(sel, "SubElementNames", []) or [])
        picked_points = list(getattr(sel, "PickedPoints", []) or [])
        for index, subobject in enumerate(subobjects):
            try:
                is_edge = isinstance(subobject, Part.Edge)
            except Exception:
                is_edge = str(getattr(subobject, "ShapeType", "") or "") == "Edge"
            if not is_edge:
                continue
            point, tangent = _edge_midpoint_and_tangent(subobject)
            if point is None:
                continue
            subelement = names[index] if index < len(names) else ""
            return {
                "object": obj,
                "subobject": subobject,
                "subelement": str(subelement or ""),
                "point": point,
                "tangent": tangent,
                "source": "subedge",
            }

        # In shaded/flat-lines display FreeCAD may report Face1 even when the
        # user clicked its visible border.  Pick the nearest boundary edge to
        # the native mouse hit point instead of falling back to the face centre.
        for index, subobject in enumerate(subobjects):
            if index >= len(picked_points):
                continue
            try:
                edges = list(subobject.Edges or [])
            except Exception:
                edges = []
            if not edges:
                continue
            local_index, edge = _nearest_edge_to_point(edges, picked_points[index])
            if edge is None:
                continue
            point, tangent = _edge_midpoint_and_tangent(edge)
            if point is None:
                continue
            return {
                "object": obj,
                "subobject": edge,
                "subelement": _owner_edge_name(obj, edge, fallback_index=local_index),
                "selected_subelement": names[index] if index < len(names) else "",
                "point": point,
                "tangent": tangent,
                "picked_point": App.Vector(picked_points[index]),
                "source": "picked-boundary-edge",
            }

    # Draft/Part lines selected as complete objects have no SubObjects.
    for sel in selected:
        if list(getattr(sel, "SubObjects", []) or []):
            continue
        obj = getattr(sel, "Object", None)
        shape = getattr(obj, "Shape", None) if obj is not None else None
        try:
            edges = list(shape.Edges or [])
        except Exception:
            edges = []
        if len(edges) != 1:
            continue
        point, tangent = _edge_midpoint_and_tangent(edges[0])
        if point is None:
            continue
        return {
            "object": obj,
            "subobject": edges[0],
            "subelement": "Edge1",
            "point": point,
            "tangent": tangent,
            "source": "single-edge-object",
        }
    return None


def object_mep_type(obj):
    """Read MEPType property defensively."""

    if obj is None:
        return ""
    if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
        try:
            return str(obj.MEPType)
        except Exception:
            return ""
    return ""

