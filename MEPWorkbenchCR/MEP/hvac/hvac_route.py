"""HVAC routes based on Draft Wire with logical port connections."""

import math
import os

import FreeCAD as App

from ..utils import selection
from . import hvac_equipment
from . import hvac_ports

MEP_TYPE = "HVACRoute"
LOG_PREFIX = "[MEP-HVAC][Route] "
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "hvac.svg")
).replace(os.sep, "/")


def log(message):
    text = LOG_PREFIX + str(message)
    print(text)


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


def ensure_route_properties(obj):
    added_route_type = False
    added_length = False
    added_auto = False

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
    for obj in selection.get_selected_objects(resolve_links=True):
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
            if str(obj.MEPType) == hvac_equipment.MEP_TYPE:
                equipments.append(obj)
    return equipments


def _equipment_port_by_type(equipment_obj, port_type):
    hvac_ports.ensure_equipment_ports(equipment_obj)
    for port in list(getattr(equipment_obj, "Ports", []) or []):
        if str(getattr(port, "Type", "")) == port_type:
            return port
    ports = list(getattr(equipment_obj, "Ports", []) or [])
    if ports:
        return ports[0]
    return None


def _create_wire(doc, points):
    import Draft

    wire = Draft.makeWire(points, closed=False, face=False, support=None)
    ensure_route_properties(wire)
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
        points = [App.Vector(0, 0, 0), App.Vector(2000, 0, 0)]
        log("No se detectaron puertos/puntos. Se crea ruta manual por defecto")

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
