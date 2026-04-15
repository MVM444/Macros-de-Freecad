"""HVAC routes based on Draft Wire with logical port connections."""

import math
import os

import FreeCAD as App
import Part

from ..utils import selection
from . import hvac_condensing
from . import hvac_equipment
from . import hvac_ports
from . import hvac_project

MEP_TYPE = "HVACRoute"
LOG_PREFIX = "[MEP-HVAC][Route] "
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "hvac.svg")
).replace(os.sep, "/")
PREF_PATH = "User parameter:BaseApp/Preferences/Macro/MEPWorkbenchCR"
DEFAULT_ROUTE_CLEARANCE_MM = 350.0
DEFAULT_BUNDLE_GAP_MM = 8.0
DEFAULT_INCLUDE_DRAIN = True
DEFAULT_REFRESH_EXISTING = True
DEFAULT_ROUTE_PATTERN = "L"
AUTO_ROUTE_TAG = "HVAC_AUTO_ROUTE"


def log(message):
    text = LOG_PREFIX + str(message)
    print(text)


def _prefs():
    try:
        return App.ParamGet(PREF_PATH)
    except Exception:
        return None


def _pref_get_bool(name, default):
    pref = _prefs()
    if pref is None:
        return bool(default)
    try:
        return bool(pref.GetBool(str(name), bool(default)))
    except Exception:
        return bool(default)


def _pref_get_float(name, default):
    pref = _prefs()
    if pref is None:
        return float(default)
    try:
        return float(pref.GetFloat(str(name), float(default)))
    except Exception:
        return float(default)


def _pref_get_str(name, default):
    pref = _prefs()
    if pref is None:
        return str(default)
    try:
        return str(pref.GetString(str(name), str(default)))
    except Exception:
        return str(default)


def _to_float(value, default=0.0):
    try:
        if hasattr(value, "Value"):
            return float(value.Value)
        return float(value)
    except Exception:
        return float(default)


def _route_type_from_port(port_obj):
    port_type = str(getattr(port_obj, "Type", "Gas"))
    if port_type == "Electric":
        return "Electric"
    if port_type == "Drain":
        return "Drain"
    return "Refrigerant"


def _normalize_route_pattern(value):
    raw = str(value or "").strip().upper()
    if raw in {"C"}:
        return "C"
    if raw in {"SNAKE", "SERPENTINE", "SERPIENTE"}:
        return "Snake"
    return "L"


def ensure_route_properties(obj):
    added_route_type = False
    added_length = False
    added_auto = False
    added_line_role = False

    if "MEPType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
    if str(getattr(obj, "MEPType", "")) != MEP_TYPE:
        obj.MEPType = MEP_TYPE

    if "RouteType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "RouteType", "HVAC Route", "Route system type")
        obj.RouteType = ["Refrigerant", "Electric", "Drain"]
        added_route_type = True
    if "StartPort" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "StartPort", "HVAC Route", "Start HVAC port")
    if "EndPort" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "EndPort", "HVAC Route", "End HVAC port")
    if "Length" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Length", "HVAC Route", "Route length (m)")
        added_length = True
    if "Level" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Level", "HVAC Route", "Average elevation (mm)")
    if "AutoFromPorts" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyBool",
            "AutoFromPorts",
            "HVAC Route",
            "When true, first and last points follow StartPort/EndPort",
        )
        added_auto = True
    if "LineRole" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "LineRole", "HVAC Route", "Detailed route line role")
        obj.LineRole = ["Gas", "Liquid", "Electric", "Drain", "Manual"]
        added_line_role = True
    if "RoutePattern" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "RoutePattern", "HVAC Route", "Orthogonal route pattern")
        obj.RoutePattern = ["L", "C", "Snake", "Manual"]
    if "NominalDiameterMM" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "NominalDiameterMM", "HVAC Route", "Nominal line diameter (mm)")
    if "InsulationDiameterMM" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "InsulationDiameterMM",
            "HVAC Route",
            "Insulated outer diameter used for spacing (mm)",
        )
    if "LineIndex" not in obj.PropertiesList:
        obj.addProperty("App::PropertyInteger", "LineIndex", "HVAC Route", "Line index in bundle (0-based)")
    if "LineCount" not in obj.PropertiesList:
        obj.addProperty("App::PropertyInteger", "LineCount", "HVAC Route", "Total lines in bundle")
    if "BundleKey" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "BundleKey", "HVAC Route", "Route bundle key per condenser/evaporator")
    if "AutoRouteKey" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "AutoRouteKey", "HVAC Route", "Stable key for auto-routed line")
    if "GeneratedBy" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "GeneratedBy", "HVAC Route", "Route generator tag")
    if "Condenser" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "Condenser", "HVAC Route", "Assigned condenser")
    if "Evaporator" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "Evaporator", "HVAC Route", "Assigned evaporator")
    if "RelatedEquipment" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyLinkList",
            "RelatedEquipment",
            "HVAC Route",
            "Equipments involved in this route",
        )

    if added_route_type:
        obj.RouteType = "Refrigerant"
    if added_auto:
        obj.AutoFromPorts = True
    if added_line_role:
        obj.LineRole = "Manual"
    if str(getattr(obj, "RoutePattern", "")) not in {"L", "C", "Snake", "Manual"}:
        obj.RoutePattern = "Manual"
    if added_length:
        obj.Length = 0.0


def _points_length(points):
    if len(points) < 2:
        return 0.0
    total = 0.0
    for idx in range(len(points) - 1):
        v = points[idx + 1].sub(points[idx])
        total += math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
    return total


def _sync_points_with_ports(route_obj):
    if not bool(getattr(route_obj, "AutoFromPorts", True)):
        return
    start = getattr(route_obj, "StartPort", None)
    end = getattr(route_obj, "EndPort", None)
    if start is None or end is None:
        return
    if not hasattr(route_obj, "Points"):
        return

    points = list(getattr(route_obj, "Points", []) or [])
    if len(points) < 2:
        points = [App.Vector(start.Position), App.Vector(end.Position)]
    else:
        points[0] = App.Vector(start.Position)
        points[-1] = App.Vector(end.Position)
    route_obj.Points = points


def update_route_metrics(route_obj):
    ensure_route_properties(route_obj)
    _sync_points_with_ports(route_obj)

    length_mm = 0.0
    if hasattr(route_obj, "Shape"):
        try:
            length_mm = float(route_obj.Shape.Length)
        except Exception:
            length_mm = 0.0
    if length_mm <= 0.0 and hasattr(route_obj, "Points"):
        length_mm = _points_length(list(route_obj.Points or []))

    route_obj.Length = round(length_mm / 1000.0, 3)

    level = 0.0
    points = list(getattr(route_obj, "Points", []) or [])
    if points:
        level = sum(point.z for point in points) / float(len(points))
    route_obj.Level = round(level, 2)


def _safe_name(obj):
    if obj is None:
        return ""
    try:
        return str(getattr(obj, "Name", "") or "")
    except Exception:
        return ""


def _is_evaporator_obj(obj):
    if obj is None:
        return False
    mep_type = str(selection.object_mep_type(obj) or "")
    if mep_type in {hvac_equipment.MEP_TYPE, "HVACEvaporator"}:
        return True
    type_id = str(getattr(obj, "TypeId", "") or "")
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    if type_id == "App::Link" and (
        name.startswith("EVAP_")
        or name.startswith("HVAC_Evaporator")
        or label.startswith("EVAP_")
        or label.startswith("HVAC_Evaporator")
    ):
        return True
    props = set(getattr(obj, "PropertiesList", []) or [])
    if {"CapacityBTU", "Model"}.issubset(props) and "ConnectedUnits" not in props:
        return True
    return False


def _is_condenser_obj(obj):
    if obj is None:
        return False
    mep_type = str(selection.object_mep_type(obj) or "")
    if mep_type in {hvac_condensing.MEP_TYPE, "HVACCondenser"}:
        return True
    props = set(getattr(obj, "PropertiesList", []) or [])
    return {"ConnectedUnits", "CapacityBTU", "ConnectedLoadBTU"}.issubset(props)


def _uniq_objects_by_name(objects):
    unique = []
    seen = set()
    for obj in list(objects or []):
        name = _safe_name(obj)
        if not name or name in seen:
            continue
        seen.add(name)
        unique.append(obj)
    return unique


def _selected_condensers():
    picked = []
    for obj in selection.get_selected_objects(resolve_links=False):
        if _is_condenser_obj(obj):
            picked.append(obj)
            continue
        linked = selection.unwrap_link(obj)
        if _is_condenser_obj(linked):
            picked.append(linked)
    return _uniq_objects_by_name(picked)


def _selected_evaporators():
    picked = []
    for obj in selection.get_selected_objects(resolve_links=False):
        if _is_evaporator_obj(obj):
            picked.append(obj)
            continue
        linked = selection.unwrap_link(obj)
        if _is_evaporator_obj(linked):
            picked.append(linked)
    return _uniq_objects_by_name(picked)


def _condenser_connected_units(condenser_obj):
    units = []
    if condenser_obj is None:
        return units
    for unit in list(getattr(condenser_obj, "ConnectedUnits", []) or []):
        if _is_evaporator_obj(unit):
            units.append(unit)
            continue
        linked = selection.unwrap_link(unit)
        if _is_evaporator_obj(linked):
            units.append(linked)
    return _uniq_objects_by_name(units)


def _find_condenser_for_evaporator(evap_obj, condensers):
    evap_name = _safe_name(evap_obj)
    if not evap_name:
        return None
    for condenser_obj in list(condensers or []):
        for linked_unit in _condenser_connected_units(condenser_obj):
            if _safe_name(linked_unit) == evap_name:
                return condenser_obj
    return None


def _iter_assigned_pairs(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []

    all_condensers = list(hvac_condensing.find_condensers(doc) or [])
    selected_condensers = _selected_condensers()
    selected_evaporators = _selected_evaporators()
    selected_evap_names = {_safe_name(obj) for obj in selected_evaporators}
    selected_evap_names.discard("")

    pairs = []
    if selected_condensers:
        for condenser_obj in selected_condensers:
            for evap_obj in _condenser_connected_units(condenser_obj):
                evap_name = _safe_name(evap_obj)
                if selected_evap_names and evap_name not in selected_evap_names:
                    continue
                pairs.append((condenser_obj, evap_obj))
    elif selected_evaporators:
        for evap_obj in selected_evaporators:
            condenser_obj = _find_condenser_for_evaporator(evap_obj, all_condensers)
            if condenser_obj is not None:
                pairs.append((condenser_obj, evap_obj))
    else:
        for condenser_obj in all_condensers:
            for evap_obj in _condenser_connected_units(condenser_obj):
                pairs.append((condenser_obj, evap_obj))

    # Fallback (Electric-CR style): if user explicitly selected condenser + evaporator(s),
    # allow routing even when condenser assignment is not yet persisted.
    if (not pairs) and selected_condensers and selected_evaporators:
        if len(selected_condensers) == 1:
            condenser_obj = selected_condensers[0]
            pairs = [(condenser_obj, evap_obj) for evap_obj in selected_evaporators]
            try:
                hvac_condensing.assign_units_to_condenser(condenser_obj, selected_evaporators, append=True)
                log(
                    "Fallback seleccion explicita: se enruta sin asignacion previa y se vinculan evaporadoras a {0}".format(
                        _safe_name(condenser_obj)
                    )
                )
            except Exception:
                log("Fallback seleccion explicita: enrute temporal sin persistir asignacion")
        else:
            mapped = []
            for evap_obj in selected_evaporators:
                ept = _anchor_point(evap_obj)
                best = None
                best_d2 = None
                for condenser_obj in selected_condensers:
                    cpt = _anchor_point(condenser_obj)
                    dx = float(cpt.x) - float(ept.x)
                    dy = float(cpt.y) - float(ept.y)
                    d2 = dx * dx + dy * dy
                    if best is None or d2 < float(best_d2):
                        best = condenser_obj
                        best_d2 = d2
                if best is not None:
                    mapped.append((best, evap_obj))
            pairs = mapped
            if pairs:
                log("Fallback seleccion explicita: asignacion por proximidad (multiples condensadoras)")

    # Keep deterministic order and remove duplicates.
    dedup = {}
    for condenser_obj, evap_obj in pairs:
        c_name = _safe_name(condenser_obj)
        e_name = _safe_name(evap_obj)
        if not c_name or not e_name:
            continue
        key = "{0}|{1}".format(c_name, e_name)
        if key not in dedup:
            dedup[key] = (condenser_obj, evap_obj)
    return list(dedup.values())


def _assignment_debug_snapshot(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return {
            "condensers": 0,
            "evaporators": 0,
            "raw_links": 0,
            "valid_links": 0,
            "details": [],
        }

    condensers = list(hvac_condensing.find_condensers(doc) or [])
    evaporators = list(hvac_equipment.find_equipments(doc) or [])
    raw_total = 0
    valid_total = 0
    details = []
    for condenser_obj in condensers:
        raw_units = []
        try:
            raw_units = list(getattr(condenser_obj, "ConnectedUnits", []) or [])
        except Exception:
            raw_units = []
        valid_units = _condenser_connected_units(condenser_obj)
        raw_count = len(raw_units)
        valid_count = len(valid_units)
        raw_total += raw_count
        valid_total += valid_count
        details.append(
            "{0}:raw={1},valid={2}".format(
                _safe_name(condenser_obj),
                raw_count,
                valid_count,
            )
        )
    return {
        "condensers": len(condensers),
        "evaporators": len(evaporators),
        "raw_links": raw_total,
        "valid_links": valid_total,
        "details": details,
    }


def _route_type_from_line_role(role):
    role_txt = str(role or "")
    if role_txt == "Electric":
        return "Electric"
    if role_txt == "Drain":
        return "Drain"
    return "Refrigerant"


def _line_spec_for_role(role, capacity_btu):
    cap = max(0.0, _to_float(capacity_btu, 0.0))
    role_txt = str(role or "Gas")
    if role_txt == "Gas":
        if cap <= 12000.0:
            return 9.52, 22.0
        if cap <= 18000.0:
            return 12.70, 25.0
        if cap <= 24000.0:
            return 15.88, 28.0
        if cap <= 36000.0:
            return 19.05, 32.0
        return 22.22, 36.0
    if role_txt == "Liquid":
        if cap <= 24000.0:
            return 6.35, 16.0
        if cap <= 36000.0:
            return 9.52, 19.0
        return 12.70, 22.0
    if role_txt == "Drain":
        if cap <= 18000.0:
            return 20.0, 24.0
        return 25.0, 30.0
    # Electric conduit/cable trunk.
    return 16.0, 18.0


def _bundle_roles(include_drain=True):
    roles = ["Gas", "Liquid", "Electric"]
    if bool(include_drain):
        roles.append("Drain")
    return roles


def _line_offsets_from_diameters(diameters_mm, min_gap_mm):
    widths = [max(1.0, _to_float(item, 1.0)) for item in list(diameters_mm or [])]
    if not widths:
        return []
    n = len(widths)
    if n == 1:
        return [0.0]
    gap = max(0.0, _to_float(min_gap_mm, DEFAULT_BUNDLE_GAP_MM))
    total = sum(widths) + gap * float(max(0, n - 1))
    offsets = []
    current = -0.5 * total
    for width in widths:
        center = current + 0.5 * width
        offsets.append(float(center))
        current += width + gap
    return offsets


def _vector_length_xy(vec):
    return math.sqrt(float(vec.x) * float(vec.x) + float(vec.y) * float(vec.y))


def _perpendicular_unit_xy(vec):
    length = _vector_length_xy(vec)
    if length <= 1e-9:
        return App.Vector(0.0, 1.0, 0.0)
    return App.Vector(-float(vec.y) / length, float(vec.x) / length, 0.0)


def _points_almost_equal(a, b, tol=0.1):
    if a is None or b is None:
        return False
    return (
        abs(float(a.x) - float(b.x)) <= tol
        and abs(float(a.y) - float(b.y)) <= tol
        and abs(float(a.z) - float(b.z)) <= tol
    )


def _compress_points(points, tol=0.1):
    compact = []
    for point in list(points or []):
        current = App.Vector(point)
        if compact and _points_almost_equal(compact[-1], current, tol=tol):
            continue
        compact.append(current)
    return compact


def _wire_ready_points(points):
    ready = _compress_points(points, tol=0.1)
    if len(ready) == 2:
        a = App.Vector(ready[0])
        b = App.Vector(ready[1])
        mid = App.Vector(
            (float(a.x) + float(b.x)) * 0.5,
            (float(a.y) + float(b.y)) * 0.5,
            (float(a.z) + float(b.z)) * 0.5,
        )
        ready = [a, mid, b]
    return ready


def _anchor_point(obj):
    if obj is None:
        return App.Vector(0.0, 0.0, 0.0)
    type_id = str(getattr(obj, "TypeId", "") or "")
    if type_id == "App::Link":
        try:
            link_placement = getattr(obj, "LinkPlacement", None)
            if link_placement is not None:
                lp = App.Vector(link_placement.Base)
                if (abs(float(lp.x)) + abs(float(lp.y)) + abs(float(lp.z))) > 0.001:
                    return lp
        except Exception:
            pass
    placement = getattr(obj, "Placement", None)
    if placement is not None:
        try:
            pb = App.Vector(placement.Base)
            if (abs(float(pb.x)) + abs(float(pb.y)) + abs(float(pb.z))) > 0.001:
                return pb
        except Exception:
            pass
    shape = getattr(obj, "Shape", None)
    try:
        if shape is not None and not shape.isNull():
            return App.Vector(shape.BoundBox.Center)
    except Exception:
        pass
    if placement is not None:
        try:
            return App.Vector(placement.Base)
        except Exception:
            pass
    return App.Vector(0.0, 0.0, 0.0)


def _bbox_lateral_face_points(obj):
    shape = getattr(obj, "Shape", None)
    if shape is None:
        return {}
    try:
        if shape.isNull():
            return {}
        bbox = shape.BoundBox
    except Exception:
        return {}
    cx = float(bbox.Center.x)
    cy = float(bbox.Center.y)
    cz = float(bbox.Center.z)
    return {
        "East": App.Vector(float(bbox.XMax), cy, cz),
        "West": App.Vector(float(bbox.XMin), cy, cz),
        "North": App.Vector(cx, float(bbox.YMax), cz),
        "South": App.Vector(cx, float(bbox.YMin), cz),
    }


def _lateral_face_anchor(obj, toward_point=None):
    base = _anchor_point(obj)
    target = App.Vector(toward_point) if toward_point is not None else App.Vector(base)
    candidates = _bbox_lateral_face_points(obj)
    if not candidates:
        vec = App.Vector(float(target.x) - float(base.x), float(target.y) - float(base.y), 0.0)
        if abs(float(vec.x)) >= abs(float(vec.y)):
            side = "East" if float(vec.x) >= 0.0 else "West"
            offset = App.Vector(150.0 if side == "East" else -150.0, 0.0, 0.0)
        else:
            side = "North" if float(vec.y) >= 0.0 else "South"
            offset = App.Vector(0.0, 150.0 if side == "North" else -150.0, 0.0)
        return base.add(offset), side

    def _score(item):
        side_key, point = item
        dx = float(point.x) - float(target.x)
        dy = float(point.y) - float(target.y)
        dz = float(point.z) - float(target.z)
        return dx * dx + dy * dy + 0.1 * dz * dz

    side, point = min(candidates.items(), key=_score)
    return App.Vector(point), str(side)


def _route_level(start_point, end_point):
    clearance = max(100.0, _pref_get_float("HVACRouteClearanceMM", DEFAULT_ROUTE_CLEARANCE_MM))
    return max(float(start_point.z), float(end_point.z)) + float(clearance)


def _pattern_xy_points(start_point, end_point, z_level, pattern):
    p0 = App.Vector(start_point)
    p5 = App.Vector(end_point)
    sx = float(p0.x)
    sy = float(p0.y)
    ex = float(p5.x)
    ey = float(p5.y)
    z = float(z_level)
    dx = ex - sx
    dy = ey - sy
    ax = abs(dx)
    ay = abs(dy)
    mode = _normalize_route_pattern(pattern)

    if mode == "C":
        if ax >= ay:
            xm = sx + 0.5 * dx
            return [
                App.Vector(sx, sy, z),
                App.Vector(xm, sy, z),
                App.Vector(xm, ey, z),
                App.Vector(ex, ey, z),
            ]
        ym = sy + 0.5 * dy
        return [
            App.Vector(sx, sy, z),
            App.Vector(sx, ym, z),
            App.Vector(ex, ym, z),
            App.Vector(ex, ey, z),
        ]

    if mode == "Snake":
        if ax >= ay:
            x1 = sx + 0.35 * dx
            x2 = sx + 0.70 * dx
            ym = sy + 0.50 * dy
            return [
                App.Vector(sx, sy, z),
                App.Vector(x1, sy, z),
                App.Vector(x1, ym, z),
                App.Vector(x2, ym, z),
                App.Vector(x2, ey, z),
                App.Vector(ex, ey, z),
            ]
        y1 = sy + 0.35 * dy
        y2 = sy + 0.70 * dy
        xm = sx + 0.50 * dx
        return [
            App.Vector(sx, sy, z),
            App.Vector(sx, y1, z),
            App.Vector(xm, y1, z),
            App.Vector(xm, y2, z),
            App.Vector(ex, y2, z),
            App.Vector(ex, ey, z),
        ]

    # Default L pattern.
    if ax >= ay:
        return [
            App.Vector(sx, sy, z),
            App.Vector(ex, sy, z),
            App.Vector(ex, ey, z),
        ]
    return [
        App.Vector(sx, sy, z),
        App.Vector(sx, ey, z),
        App.Vector(ex, ey, z),
    ]


def _centerline_points(start_point, end_point, z_level, pattern="L"):
    p0 = App.Vector(start_point)
    p5 = App.Vector(end_point)
    p1 = App.Vector(float(p0.x), float(p0.y), float(z_level))
    p4 = App.Vector(float(p5.x), float(p5.y), float(z_level))
    xy_points = _pattern_xy_points(p1, p4, z_level, pattern)
    return _compress_points([p0] + list(xy_points or [p1, p4]) + [p5], tol=0.1)


def _offset_bundle_points(centerline_points, offset_xy):
    points = list(centerline_points or [])
    if len(points) < 2:
        return points

    anchor_vec = App.Vector(
        float(points[-1].x) - float(points[0].x),
        float(points[-1].y) - float(points[0].y),
        0.0,
    )
    perp = _perpendicular_unit_xy(anchor_vec)
    full = App.Vector(float(perp.x) * float(offset_xy), float(perp.y) * float(offset_xy), 0.0)
    half = App.Vector(float(full.x) * 0.5, float(full.y) * 0.5, 0.0)

    result = []
    last_index = len(points) - 1
    for idx, point in enumerate(points):
        current = App.Vector(point)
        if idx == 0 or idx == last_index:
            result.append(current)
            continue
        if idx == 1 or idx == (last_index - 1):
            result.append(current.add(half))
        else:
            result.append(current.add(full))
    return _compress_points(result, tol=0.1)


def _route_points_with_port_ends(points, start_port=None, end_port=None):
    routed = _compress_points(points, tol=0.1)
    if len(routed) < 2:
        return routed
    if start_port is not None:
        try:
            routed[0] = App.Vector(start_port.Position)
        except Exception:
            pass
    if end_port is not None:
        try:
            routed[-1] = App.Vector(end_port.Position)
        except Exception:
            pass
    return _wire_ready_points(routed)


def _bundle_key(condenser_obj, evap_obj):
    return "HVACBundle:{0}:{1}".format(_safe_name(condenser_obj), _safe_name(evap_obj))


def _auto_route_key(condenser_obj, evap_obj, role):
    return "{0}:{1}:{2}:{3}".format(
        AUTO_ROUTE_TAG,
        _safe_name(condenser_obj),
        _safe_name(evap_obj),
        str(role or "Manual"),
    )


def _find_route_by_auto_key(doc, auto_key):
    key = str(auto_key or "")
    if not key:
        return None
    for route_obj in list(find_routes(doc) or []):
        if "AutoRouteKey" not in getattr(route_obj, "PropertiesList", []):
            continue
        if str(getattr(route_obj, "AutoRouteKey", "") or "") == key:
            return route_obj
    return None


def _apply_route_points(route_obj, points):
    if route_obj is None:
        return
    ready_points = _wire_ready_points(points)
    if hasattr(route_obj, "Points"):
        route_obj.Points = list(ready_points or [])
        return
    try:
        route_obj.Shape = Part.makePolygon(list(ready_points or []))
    except Exception:
        pass


def _port_by_type(equipment_obj, role):
    if equipment_obj is None:
        return None
    try:
        hvac_ports.ensure_equipment_ports(equipment_obj)
    except Exception:
        pass
    for port in list(getattr(equipment_obj, "Ports", []) or []):
        if str(getattr(port, "Type", "")) == str(role or ""):
            return port
    return None


def _pair_ports_for_role(evap_obj, condenser_obj, role):
    start_port = _port_by_type(evap_obj, role)
    end_port = _port_by_type(condenser_obj, role)
    if start_port is not None and end_port is not None:
        try:
            if hvac_ports.validate_port_pair(start_port, end_port):
                hvac_ports.connect_ports(start_port, end_port)
            else:
                start_port = None
                end_port = None
        except Exception:
            start_port = None
            end_port = None
    return start_port, end_port


def _apply_route_visual_style(route_obj, role):
    if route_obj is None:
        return
    role_txt = str(role or "")
    palette = {
        "Gas": (1.0, 0.0, 0.0),       # S1
        "Liquid": (0.0, 0.25, 1.0),   # S2
        "Electric": (1.0, 0.85, 0.0), # S3
        "Drain": (0.0, 0.75, 0.0),    # E
    }
    color = palette.get(role_txt, (0.2, 0.2, 0.2))
    view = getattr(route_obj, "ViewObject", None)
    if view is None:
        return
    try:
        view.LineColor = color
    except Exception:
        pass
    try:
        view.ShapeColor = color
    except Exception:
        pass
    try:
        view.PointColor = color
    except Exception:
        pass
    try:
        view.LineWidth = 4.0
    except Exception:
        pass


def _upsert_auto_route(
    doc,
    condenser_obj,
    evap_obj,
    role,
    points,
    line_index,
    line_count,
    nominal_mm,
    insulation_mm,
    route_pattern="L",
    start_port=None,
    end_port=None,
):
    auto_key = _auto_route_key(condenser_obj, evap_obj, role)
    route = _find_route_by_auto_key(doc, auto_key)
    created = False
    if route is not None and not hasattr(route, "Points"):
        # Legacy auto-routes could be Draft Line objects (2-point). Replace with Draft Wire.
        legacy_name = str(getattr(route, "Name", "") or "")
        try:
            doc.removeObject(route.Name)
        except Exception:
            pass
        if legacy_name:
            log("Ruta legacy reemplazada por Wire: {0}".format(legacy_name))
        route = None
    if route is None:
        route = _create_wire(doc, points)
        created = True
    else:
        _apply_route_points(route, points)

    ensure_route_properties(route)
    route.RouteType = _route_type_from_line_role(role)
    route.LineRole = str(role or "Manual")
    route.RoutePattern = _normalize_route_pattern(route_pattern)
    route.LineIndex = int(line_index)
    route.LineCount = int(max(1, line_count))
    route.NominalDiameterMM = round(float(nominal_mm), 2)
    route.InsulationDiameterMM = round(float(insulation_mm), 2)
    route.BundleKey = _bundle_key(condenser_obj, evap_obj)
    route.AutoRouteKey = auto_key
    route.GeneratedBy = AUTO_ROUTE_TAG
    route.Condenser = condenser_obj
    route.Evaporator = evap_obj
    route.RelatedEquipment = [evap_obj, condenser_obj]
    route.AutoFromPorts = False
    if start_port is not None and end_port is not None:
        route.StartPort = start_port
        route.EndPort = end_port
    else:
        route.StartPort = None
        route.EndPort = None
    try:
        route.Label = "HVAC_Route_{0}_{1}_{2}".format(
            _safe_name(condenser_obj),
            _safe_name(evap_obj),
            str(role or "Manual"),
        )
    except Exception:
        pass
    _apply_route_visual_style(route, role)
    update_route_metrics(route)
    return route, created


def _create_routes_for_pairs(doc, assigned_pairs, include_drain=True, refresh_existing=True, route_pattern="L"):
    created_routes = []
    created = 0
    updated = 0
    roles = _bundle_roles(include_drain=bool(include_drain))

    for condenser_obj, evap_obj in list(assigned_pairs or []):
        evap_anchor = _anchor_point(evap_obj)
        cond_anchor = _anchor_point(condenser_obj)
        base_start_point, _start_side = _lateral_face_anchor(evap_obj, toward_point=cond_anchor)
        base_end_point, _end_side = _lateral_face_anchor(condenser_obj, toward_point=evap_anchor)
        z_level = _route_level(base_start_point, base_end_point)
        centerline = _centerline_points(base_start_point, base_end_point, z_level, pattern=route_pattern)
        if len(centerline) < 2:
            continue

        capacity_btu = _to_float(getattr(evap_obj, "CapacityBTU", 0.0), 0.0)
        line_specs = []
        for role in roles:
            nominal_mm, insulation_mm = _line_spec_for_role(role, capacity_btu)
            line_specs.append((role, nominal_mm, insulation_mm))
        ins_diams = [item[2] for item in line_specs]
        min_gap = max(DEFAULT_BUNDLE_GAP_MM, 0.20 * max(ins_diams))
        offsets = _line_offsets_from_diameters(ins_diams, min_gap_mm=min_gap)

        for idx, spec in enumerate(line_specs):
            role, nominal_mm, insulation_mm = spec
            start_port, end_port = _pair_ports_for_role(evap_obj, condenser_obj, role)
            offset = offsets[idx] if idx < len(offsets) else 0.0
            line_points = _offset_bundle_points(centerline, offset)
            line_points = _route_points_with_port_ends(
                line_points,
                start_port=start_port,
                end_port=end_port,
            )
            if len(line_points) < 2:
                continue

            if not bool(refresh_existing):
                existing = _find_route_by_auto_key(doc, _auto_route_key(condenser_obj, evap_obj, role))
                if existing is not None:
                    continue
            route_obj, was_created = _upsert_auto_route(
                doc,
                condenser_obj,
                evap_obj,
                role,
                line_points,
                line_index=idx,
                line_count=len(line_specs),
                nominal_mm=nominal_mm,
                insulation_mm=insulation_mm,
                route_pattern=route_pattern,
                start_port=start_port,
                end_port=end_port,
            )
            created_routes.append(route_obj)
            if was_created:
                created += 1
            else:
                updated += 1

    if created_routes:
        log(
            "Rutas automaticas por asignacion: pares={0}, lineas={1}, creadas={2}, actualizadas={3}, drenaje={4}, patron={5}".format(
                len(list(assigned_pairs or [])),
                len(created_routes),
                created,
                updated,
                bool(include_drain),
                route_pattern,
            )
        )
    return created_routes


def create_routes_from_assignments(doc=None, include_drain=None, refresh_existing=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []

    if include_drain is None:
        include_drain = _pref_get_bool("HVACRouteIncludeDrain", DEFAULT_INCLUDE_DRAIN)
    if refresh_existing is None:
        refresh_existing = _pref_get_bool("HVACRouteRefreshExisting", DEFAULT_REFRESH_EXISTING)
    route_pattern = _normalize_route_pattern(_pref_get_str("HVACRoutePattern", DEFAULT_ROUTE_PATTERN))

    assigned_pairs = _iter_assigned_pairs(doc)
    if not assigned_pairs:
        snapshot = _assignment_debug_snapshot(doc)
        log(
            "Sin pares asignados: condensadoras={0}, evaporadoras={1}, conexiones_raw={2}, conexiones_validas={3}".format(
                int(snapshot.get("condensers", 0)),
                int(snapshot.get("evaporators", 0)),
                int(snapshot.get("raw_links", 0)),
                int(snapshot.get("valid_links", 0)),
            )
        )
        details = list(snapshot.get("details", []) or [])
        if details:
            log("Detalle condensadoras: {0}".format("; ".join(details)))
        return []
    return _create_routes_for_pairs(
        doc,
        assigned_pairs,
        include_drain=include_drain,
        refresh_existing=refresh_existing,
        route_pattern=route_pattern,
    )


def find_routes(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    routes = []
    for obj in doc.Objects:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == MEP_TYPE:
            routes.append(obj)
    return routes


def _selected_ports():
    ports = hvac_ports.selected_ports()
    if len(ports) >= 2:
        return ports[0], ports[1]
    return None, None


def _selected_points():
    points = selection.get_selected_points()
    if len(points) >= 2:
        return [App.Vector(points[0]), App.Vector(points[1])]

    picked_objects = selection.get_selected_objects(resolve_links=True)
    for obj in picked_objects:
        if hasattr(obj, "Placement"):
            points.append(App.Vector(obj.Placement.Base))
        if len(points) >= 2:
            break
    if len(points) >= 2:
        return [points[0], points[1]]
    return []


def _selected_equipments():
    equipments = []
    for obj in selection.get_selected_objects(resolve_links=False):
        candidate = obj
        linked = selection.unwrap_link(obj)
        for current in (candidate, linked):
            if current is None:
                continue
            if hasattr(current, "PropertiesList") and "MEPType" in current.PropertiesList:
                if str(getattr(current, "MEPType", "")) == hvac_equipment.MEP_TYPE:
                    equipments.append(current)
                    break
    return _uniq_objects_by_name(equipments)


def _equipment_port_by_type(equipment_obj, port_type):
    if "UsePorts" in getattr(equipment_obj, "PropertiesList", []):
        if not bool(getattr(equipment_obj, "UsePorts", False)):
            equipment_obj.UsePorts = True
    hvac_ports.ensure_equipment_ports(equipment_obj)
    for port in list(getattr(equipment_obj, "Ports", []) or []):
        if str(getattr(port, "Type", "")) == port_type:
            return port
    ports = list(getattr(equipment_obj, "Ports", []) or [])
    if ports:
        return ports[0]
    return None


def _create_wire(doc, points):
    ready_points = _wire_ready_points(points)
    wire = None
    try:
        import Draft

        wire = Draft.makeWire(ready_points, closed=False, face=False, support=None)
    except Exception:
        wire = doc.addObject("Part::Feature", "HVAC_Route")
        try:
            wire.Shape = Part.makePolygon(list(ready_points or []))
        except Exception:
            pass
    ensure_route_properties(wire)
    hvac_project.add_object_to_hvac_group(doc, wire)
    return wire


def _set_related_equipment(route_obj):
    related = []
    for port in [getattr(route_obj, "StartPort", None), getattr(route_obj, "EndPort", None)]:
        equipment = hvac_ports.get_port_equipment(port)
        if equipment is not None and equipment not in related:
            related.append(equipment)
    route_obj.RelatedEquipment = related


def create_route_from_selection(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return None

    selected_condensers = _selected_condensers()
    selected_evaporators = _selected_evaporators()
    auto_routes = create_routes_from_assignments(doc)
    if auto_routes:
        return auto_routes[0]
    if selected_condensers or selected_evaporators:
        log("No hay asignaciones evaporadora-condensadora para la seleccion actual")
        return None

    start_port, end_port = _selected_ports()
    if start_port is not None and end_port is not None:
        if not hvac_ports.validate_port_pair(start_port, end_port):
            log("Seleccione dos puertos del mismo tipo para crear la ruta")
            return None
        points = [App.Vector(start_port.Position), App.Vector(end_port.Position)]
        route = _create_wire(doc, points)
        route.StartPort = start_port
        route.EndPort = end_port
        route.RouteType = _route_type_from_port(start_port)
        hvac_ports.connect_ports(start_port, end_port)
        _set_related_equipment(route)
        update_route_metrics(route)
        log("Ruta creada entre puertos: {0} -> {1}".format(start_port.Label, end_port.Label))
        return route

    selected_equipment = _selected_equipments()
    if len(selected_equipment) >= 2:
        start_port = _equipment_port_by_type(selected_equipment[0], "Gas")
        end_port = _equipment_port_by_type(selected_equipment[1], str(getattr(start_port, "Type", "Gas")))
        if start_port is not None and end_port is not None and hvac_ports.validate_port_pair(start_port, end_port):
            points = [App.Vector(start_port.Position), App.Vector(end_port.Position)]
            route = _create_wire(doc, points)
            route.StartPort = start_port
            route.EndPort = end_port
            route.RouteType = _route_type_from_port(start_port)
            hvac_ports.connect_ports(start_port, end_port)
            _set_related_equipment(route)
            update_route_metrics(route)
            log(
                "Ruta creada por seleccion de equipos: {0} -> {1}".format(
                    selected_equipment[0].Name, selected_equipment[1].Name
                )
            )
            return route

    points = _selected_points()
    if len(points) < 2:
        log("No se detectaron puertos/puntos. No se crea ruta manual por defecto")
        log("Accion requerida: asigne evaporadora-condensadora o seleccione 2 puertos/puntos")
        return None

    route = _create_wire(doc, points)
    route.RouteType = "Refrigerant"
    update_route_metrics(route)
    return route


def update_all_routes(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return
    for route in find_routes(doc):
        update_route_metrics(route)


class HVACRouteViewProvider:
    def __init__(self, vobj):
        self.ViewObject = vobj

    def attach(self, vobj):
        self.Object = vobj.Object

    def getIcon(self):  # noqa: N802
        return ICON_PATH

    def updateData(self, obj, prop):  # noqa: N802
        pass

    def onChanged(self, vobj, prop):  # noqa: N802
        pass

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None
