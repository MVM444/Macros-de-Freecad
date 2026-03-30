"""HVAC ports for equipment connectivity and validation."""

import os

import FreeCAD as App

from ..utils import selection

MEP_TYPE = "HVACPort"
PORT_TYPES = ["Gas", "Liquid", "Electric", "Drain"]
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
    if added_valid:
        obj.Valid = False
    if "ConnectedToName" in obj.PropertiesList and getattr(obj, "ConnectedToName", None) is None:
        obj.ConnectedToName = ""


def _equipment_dimensions(equipment_obj):
    eq_type = str(getattr(equipment_obj, "Type", "Wall"))
    if eq_type == "Cassette":
        return (600.0, 600.0, 320.0)
    if eq_type == "Duct":
        return (1200.0, 360.0, 320.0)
    return (900.0, 260.0, 220.0)


def _local_ports_for_equipment(equipment_obj):
    dx, dy, dz = _equipment_dimensions(equipment_obj)
    ports = {
        "Gas": (App.Vector(dx * 0.45, -dy * 0.5, dz * 0.55), App.Vector(0, -1, 0)),
        "Liquid": (App.Vector(-dx * 0.45, -dy * 0.5, dz * 0.55), App.Vector(0, -1, 0)),
        "Electric": (App.Vector(-dx * 0.40, -dy * 0.5, dz * 0.85), App.Vector(0, -1, 0)),
        "Drain": (App.Vector(dx * 0.40, -dy * 0.5, dz * 0.20), App.Vector(0, -1, -0.5)),
    }
    return ports


def _transform_port_vectors(equipment_obj, local_position, local_direction):
    placement = getattr(equipment_obj, "Placement", App.Placement())
    world_position = placement.multVec(local_position)
    world_direction = placement.Rotation.multVec(local_direction)
    return world_position, world_direction


def create_port(doc, equipment_obj, port_type):
    port = doc.addObject("App::FeaturePython", "HVAC_Port")
    HVACPortProxy(port)
    HVACPortViewProvider(port.ViewObject)
    ensure_port_properties(port)
    port.Type = port_type
    port.EquipmentName = str(getattr(equipment_obj, "Name", ""))
    if "ConnectedToName" in port.PropertiesList:
        port.ConnectedToName = ""
    port.Label = "{0}_{1}".format(equipment_obj.Label, port_type)
    if hasattr(port, "ViewObject"):
        port.ViewObject.Visibility = False
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
        if _vector_changed(getattr(port, "Position", App.Vector(0, 0, 0)), position):
            port.Position = position
        if _vector_changed(getattr(port, "Direction", App.Vector(0, -1, 0)), direction):
            port.Direction = direction
        equipment_name = str(getattr(equipment_obj, "Name", ""))
        if str(getattr(port, "EquipmentName", "")) != equipment_name:
            port.EquipmentName = equipment_name
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

    def execute(self, obj):
        ensure_port_properties(obj)


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
