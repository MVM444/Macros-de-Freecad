"""HVAC ports for equipment connectivity and validation."""

import os

import FreeCAD as App
import Part

from ..utils import selection

MEP_TYPE = "HVACPort"
PORT_TYPES = ["Gas", "Liquid", "Electric", "Drain"]
MARKER_RADIUS_BIG_MM = 30.0
MARKER_RADIUS_SMALL_MM = 16.0
LOG_PREFIX = "[MEP-HVAC][Port] "
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "hvac.svg")
).replace(os.sep, "/")


def log(message):
    text = LOG_PREFIX + str(message)
    print(text)


def _vector_changed(current, target, tol=0.01):
    try:
        cur = App.Vector(current)
        tgt = App.Vector(target)
    except Exception:
        return True
    return (
        abs(float(cur.x) - float(tgt.x)) > tol
        or abs(float(cur.y) - float(tgt.y)) > tol
        or abs(float(cur.z) - float(tgt.z)) > tol
    )


def _list_changed(existing, updated):
    old_names = [str(getattr(obj, "Name", "")) for obj in list(existing or []) if obj is not None]
    new_names = [str(getattr(obj, "Name", "")) for obj in list(updated or []) if obj is not None]
    return old_names != new_names


def _port_marker_radius_mm(port_type):
    role = str(port_type or "")
    if role == "Drain":
        return float(MARKER_RADIUS_SMALL_MM)
    return float(MARKER_RADIUS_BIG_MM)


def _port_marker_color(port_type):
    role = str(port_type or "")
    palette = {
        "Gas": (1.0, 0.0, 0.0),
        "Liquid": (0.0, 0.25, 1.0),
        "Electric": (1.0, 0.85, 0.0),
        "Drain": (0.0, 0.75, 0.0),
    }
    return palette.get(role, (0.9, 0.9, 0.9))


def _safe_normal(direction):
    try:
        vec = App.Vector(direction)
    except Exception:
        return App.Vector(1, 0, 0)
    length = float(vec.Length)
    if length <= 1e-6:
        return App.Vector(1, 0, 0)
    return App.Vector(float(vec.x) / length, float(vec.y) / length, float(vec.z) / length)


def _update_port_shape(port_obj):
    if port_obj is None:
        return
    if "Shape" not in getattr(port_obj, "PropertiesList", []):
        return
    center = App.Vector(getattr(port_obj, "Position", App.Vector(0, 0, 0)))
    normal = _safe_normal(getattr(port_obj, "Direction", App.Vector(1, 0, 0)))
    radius = _port_marker_radius_mm(getattr(port_obj, "Type", "Gas"))
    if "MarkerRadiusMM" in getattr(port_obj, "PropertiesList", []):
        try:
            current = float(getattr(port_obj, "MarkerRadiusMM", radius))
            if abs(current - radius) > 0.01:
                port_obj.MarkerRadiusMM = radius
            else:
                radius = current
        except Exception:
            try:
                port_obj.MarkerRadiusMM = radius
            except Exception:
                pass
    try:
        port_obj.Shape = Part.makeCircle(float(radius), center, normal)
    except Exception:
        pass


def _update_port_view(port_obj):
    view_obj = getattr(port_obj, "ViewObject", None)
    if view_obj is None:
        return
    color = _port_marker_color(getattr(port_obj, "Type", "Gas"))
    try:
        view_obj.Visibility = True
    except Exception:
        pass
    if hasattr(view_obj, "ShowInTree"):
        try:
            view_obj.ShowInTree = True
        except Exception:
            pass
    try:
        view_obj.LineColor = color
    except Exception:
        pass
    try:
        view_obj.ShapeColor = color
    except Exception:
        pass
    try:
        view_obj.PointColor = color
    except Exception:
        pass
    try:
        view_obj.LineWidth = 3.0
    except Exception:
        pass


def ensure_port_properties(obj):
    added_type = False
    added_position = False
    added_direction = False
    added_valid = False

    if "MEPType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
    if str(getattr(obj, "MEPType", "")) != MEP_TYPE:
        obj.MEPType = MEP_TYPE

    if "Type" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "Type", "HVAC Port", "Port system type")
        obj.Type = PORT_TYPES
        added_type = True
    if "Position" not in obj.PropertiesList:
        obj.addProperty("App::PropertyVector", "Position", "HVAC Port", "Port absolute position")
        added_position = True
    if "Direction" not in obj.PropertiesList:
        obj.addProperty("App::PropertyVector", "Direction", "HVAC Port", "Connection direction vector")
        added_direction = True
    if "Shape" not in obj.PropertiesList:
        obj.addProperty("Part::PropertyPartShape", "Shape", "HVAC Port", "Port visual circle marker")
    if "MarkerRadiusMM" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "MarkerRadiusMM", "HVAC Port", "Port marker radius (mm)")
    if "EquipmentName" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "EquipmentName", "HVAC Port", "Owner equipment object name")
    if "ConnectedToName" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "ConnectedToName", "HVAC Port", "Connected compatible port name")
    if "Valid" not in obj.PropertiesList:
        obj.addProperty("App::PropertyBool", "Valid", "HVAC Port", "Connection validation status")
        added_valid = True

    # Cleanup legacy link properties from previous versions to avoid DAG cycles.
    if "Equipment" in obj.PropertiesList:
        try:
            if getattr(obj, "Equipment", None) is not None:
                obj.Equipment = None
        except Exception:
            pass
    if "ConnectedTo" in obj.PropertiesList:
        try:
            if getattr(obj, "ConnectedTo", None) is not None:
                obj.ConnectedTo = None
        except Exception:
            pass

    if added_type:
        obj.Type = "Gas"
    if added_position:
        obj.Position = App.Vector(0, 0, 0)
    if added_direction:
        obj.Direction = App.Vector(0, -1, 0)
    if "MarkerRadiusMM" in obj.PropertiesList and float(getattr(obj, "MarkerRadiusMM", 0.0) or 0.0) <= 0.0:
        obj.MarkerRadiusMM = _port_marker_radius_mm(getattr(obj, "Type", "Gas"))
    if added_valid:
        obj.Valid = False
    if "ConnectedToName" in obj.PropertiesList and getattr(obj, "ConnectedToName", None) is None:
        obj.ConnectedToName = ""
    _update_port_shape(obj)
    _update_port_view(obj)


def _equipment_dimensions(equipment_obj):
    shape = getattr(equipment_obj, "Shape", None)
    if shape is not None:
        try:
            if not shape.isNull():
                bbox = shape.BoundBox
                sx = float(bbox.XLength)
                sy = float(bbox.YLength)
                sz = float(bbox.ZLength)
                if sx > 1.0 and sy > 1.0 and sz > 1.0:
                    return (sx, sy, sz)
        except Exception:
            pass

    mep_type = str(getattr(equipment_obj, "MEPType", "") or "")
    if mep_type == "HVACCondenser":
        return (1200.0, 500.0, 900.0)

    eq_type = str(getattr(equipment_obj, "Type", "Wall"))
    if eq_type == "Cassette":
        return (600.0, 600.0, 320.0)
    if eq_type == "FloorCeiling":
        return (1100.0, 300.0, 260.0)
    if eq_type == "Duct":
        return (1200.0, 360.0, 320.0)
    return (900.0, 260.0, 220.0)


def _equipment_kind(equipment_obj):
    if equipment_obj is None:
        return "Evaporator"
    mep_type = str(getattr(equipment_obj, "MEPType", "") or "")
    if mep_type == "HVACCondenser":
        return "Condenser"
    props = set(getattr(equipment_obj, "PropertiesList", []) or [])
    if "ConnectedUnits" in props:
        return "Condenser"
    return "Evaporator"


def _local_ports_for_evaporator(dx, dy, dz):
    # Indoor unit connectors are grouped near one side toward the wall.
    y_wall = -float(dy) * 0.5
    x_side = float(dx) * 0.45
    return {
        "Gas": (App.Vector(x_side, y_wall, float(dz) * 0.58), App.Vector(1, 0, 0)),
        "Liquid": (App.Vector(x_side - float(dx) * 0.09, y_wall, float(dz) * 0.50), App.Vector(1, 0, 0)),
        "Electric": (App.Vector(x_side - float(dx) * 0.17, y_wall, float(dz) * 0.70), App.Vector(1, 0, 0)),
        "Drain": (App.Vector(x_side - float(dx) * 0.04, y_wall, float(dz) * 0.26), App.Vector(1, 0, -0.5)),
    }


def _local_ports_for_condenser(equipment_obj, dx, dy, dz):
    # Outdoor unit service valves and electrical cover are typically on one side.
    x_side = float(dx) * 0.5
    discharge = str(getattr(equipment_obj, "Discharge", "Horizontal") or "Horizontal")
    is_vertical = discharge.lower().startswith("v")
    electric_y = float(dy) * (0.25 if is_vertical else 0.35)
    return {
        "Gas": (App.Vector(x_side, -float(dy) * 0.22, float(dz) * 0.26), App.Vector(1, 0, 0)),
        "Liquid": (App.Vector(x_side, -float(dy) * 0.34, float(dz) * 0.20), App.Vector(1, 0, 0)),
        "Electric": (App.Vector(x_side, electric_y, float(dz) * 0.72), App.Vector(1, 0, 0)),
        "Drain": (App.Vector(x_side, -float(dy) * 0.08, float(dz) * 0.15), App.Vector(1, 0, -0.5)),
    }


def _local_ports_for_equipment(equipment_obj):
    dx, dy, dz = _equipment_dimensions(equipment_obj)
    kind = _equipment_kind(equipment_obj)
    if kind == "Condenser":
        return _local_ports_for_condenser(equipment_obj, dx, dy, dz)
    return _local_ports_for_evaporator(dx, dy, dz)


def _transform_port_vectors(equipment_obj, local_position, local_direction):
    placement = getattr(equipment_obj, "Placement", App.Placement())
    world_position = placement.multVec(local_position)
    world_direction = placement.Rotation.multVec(local_direction)
    return world_position, world_direction


def create_port(doc, equipment_obj, port_type):
    port = doc.addObject("App::FeaturePython", "HVAC_Port")
    HVACPortProxy(port)
    view_obj = getattr(port, "ViewObject", None)
    if view_obj is not None:
        HVACPortViewProvider(view_obj)
    ensure_port_properties(port)
    port.Type = port_type
    port.EquipmentName = str(getattr(equipment_obj, "Name", ""))
    if "ConnectedToName" in port.PropertiesList:
        port.ConnectedToName = ""
    port.Label = "{0}_{1}".format(equipment_obj.Label, port_type)
    _update_port_shape(port)
    _update_port_view(port)
    return port


def _existing_ports_by_type(equipment_obj):
    mapped = {}
    ports = []
    if hasattr(equipment_obj, "PropertiesList") and "Ports" in equipment_obj.PropertiesList:
        ports = list(getattr(equipment_obj, "Ports", []) or [])
    for port in ports:
        if port is None:
            continue
        if hasattr(port, "PropertiesList") and "MEPType" in port.PropertiesList and str(port.MEPType) == MEP_TYPE:
            mapped[str(port.Type)] = port
    return mapped


def ensure_equipment_ports(equipment_obj):
    if equipment_obj is None:
        return []
    if "Ports" not in equipment_obj.PropertiesList:
        equipment_obj.addProperty(
            "App::PropertyLinkList",
            "Ports",
            "HVAC Equipment",
            "HVAC ports attached to this equipment",
        )

    existing = _existing_ports_by_type(equipment_obj)
    local_ports = _local_ports_for_equipment(equipment_obj)
    updated_ports = []

    for port_type in PORT_TYPES:
        port = existing.get(port_type)
        if port is None:
            port = create_port(equipment_obj.Document, equipment_obj, port_type)
        position, direction = _transform_port_vectors(
            equipment_obj,
            local_ports[port_type][0],
            local_ports[port_type][1],
        )
        if str(getattr(port, "Type", "")) != port_type:
            port.Type = port_type
            if "MarkerRadiusMM" in port.PropertiesList:
                try:
                    port.MarkerRadiusMM = _port_marker_radius_mm(port_type)
                except Exception:
                    pass
        if _vector_changed(getattr(port, "Position", App.Vector(0, 0, 0)), position):
            port.Position = position
        if _vector_changed(getattr(port, "Direction", App.Vector(0, -1, 0)), direction):
            port.Direction = direction
        equipment_name = str(getattr(equipment_obj, "Name", ""))
        if str(getattr(port, "EquipmentName", "")) != equipment_name:
            port.EquipmentName = equipment_name
        _update_port_shape(port)
        _update_port_view(port)
        updated_ports.append(port)

    if _list_changed(getattr(equipment_obj, "Ports", []), updated_ports):
        equipment_obj.Ports = updated_ports
    return updated_ports


def update_equipment_ports(equipment_obj):
    return ensure_equipment_ports(equipment_obj)


def validate_port_pair(port_a, port_b):
    if port_a is None or port_b is None:
        return False
    if port_a == port_b:
        return False
    if str(port_a.Type) != str(port_b.Type):
        return False
    return True


def connect_ports(port_a, port_b):
    if not validate_port_pair(port_a, port_b):
        log("Conexion invalida entre puertos")
        return False
    port_a.ConnectedToName = str(getattr(port_b, "Name", ""))
    port_b.ConnectedToName = str(getattr(port_a, "Name", ""))
    port_a.Valid = True
    port_b.Valid = True
    log("Puertos conectados: {0} <-> {1}".format(port_a.Label, port_b.Label))
    return True


def get_connected_port(port_obj):
    if port_obj is None:
        return None
    name = str(getattr(port_obj, "ConnectedToName", "") or "")
    if not name:
        return None
    doc = getattr(port_obj, "Document", None)
    if doc is None:
        return None
    try:
        return doc.getObject(name)
    except Exception:
        return None


def get_port_equipment(port_obj):
    if port_obj is None:
        return None
    if "Equipment" in getattr(port_obj, "PropertiesList", []) and getattr(port_obj, "Equipment", None) is not None:
        return port_obj.Equipment
    name = ""
    if "EquipmentName" in getattr(port_obj, "PropertiesList", []):
        name = str(getattr(port_obj, "EquipmentName", "") or "")
    if not name:
        return None
    doc = getattr(port_obj, "Document", None)
    if doc is None:
        return None
    try:
        return doc.getObject(name)
    except Exception:
        return None


def find_ports(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    ports = []
    for obj in doc.Objects:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == MEP_TYPE:
            ports.append(obj)
    return ports


def selected_ports():
    ports = []
    for obj in selection.get_selected_objects(resolve_links=True):
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == MEP_TYPE:
            ports.append(obj)
    return ports


def sanitize_all_ports(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return
    for port in find_ports(doc):
        ensure_port_properties(port)


def prune_unused_ports(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    linked_names = set()
    try:
        from . import hvac_route

        for route in list(hvac_route.find_routes(doc) or []):
            for port in [getattr(route, "StartPort", None), getattr(route, "EndPort", None)]:
                if port is not None:
                    linked_names.add(str(getattr(port, "Name", "") or ""))
    except Exception:
        pass

    removed = 0
    for port in list(find_ports(doc)):
        port_name = str(getattr(port, "Name", "") or "")
        if port_name in linked_names:
            continue
        equipment = get_port_equipment(port)
        if equipment is not None and bool(getattr(equipment, "UsePorts", False)):
            continue
        try:
            doc.removeObject(port.Name)
            removed += 1
        except Exception:
            continue
    if removed > 0:
        log("Puertos tecnicos eliminados por modo compacto: {0}".format(removed))
    return removed


class HVACPortProxy:
    def __init__(self, obj):
        obj.Proxy = self
        ensure_port_properties(obj)

    def onChanged(self, obj, prop):  # noqa: N802
        if prop == "ConnectedToName":
            target = get_connected_port(obj)
            new_valid = target is not None and validate_port_pair(obj, target)
            if bool(getattr(obj, "Valid", False)) != bool(new_valid):
                obj.Valid = new_valid
        if prop in {"Type", "Position", "Direction", "MarkerRadiusMM"}:
            _update_port_shape(obj)
            _update_port_view(obj)

    def execute(self, obj):
        ensure_port_properties(obj)
        _update_port_shape(obj)
        _update_port_view(obj)


class HVACPortViewProvider:
    def __init__(self, vobj):
        vobj.Proxy = self

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
