"""HVAC evaporator equipment object."""

import os

import FreeCAD as App
import Part

from ..utils import selection
from . import hvac_ports
from . import hvac_space

MEP_TYPE = "HVACEquipment"
LOG_PREFIX = "[MEP-HVAC][Equipment] "
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


def ensure_equipment_properties(obj):
    added_type = False
    added_capacity = False
    added_height = False
    added_auto_detect = False
    added_coverage = False

    if "MEPType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
    if str(getattr(obj, "MEPType", "")) != MEP_TYPE:
        obj.MEPType = MEP_TYPE

    if "Type" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "Type", "HVAC Equipment", "Equipment type")
        obj.Type = ["Wall", "Cassette", "Duct"]
        added_type = True
    if "CapacityBTU" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "CapacityBTU", "HVAC Equipment", "Equipment capacity")
        added_capacity = True
    if "Space" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "Space", "HVAC Equipment", "Assigned HVAC space")
    if "Height" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Height", "HVAC Equipment", "Mounting height (m)")
        added_height = True
    if "CoveragePct" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "CoveragePct",
            "HVAC Equipment",
            "Coverage percentage for assigned space",
        )
        added_coverage = True
    if "AutoDetectSpace" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyBool",
            "AutoDetectSpace",
            "HVAC Equipment",
            "Auto assign nearest/selected HVAC space",
        )
        added_auto_detect = True
    if "Ports" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLinkList", "Ports", "HVAC Equipment", "Equipment port objects")

    if added_type:
        obj.Type = "Wall"
    if added_capacity:
        obj.CapacityBTU = 12000.0
    if added_height:
        obj.Height = 2.3
    if added_coverage:
        obj.CoveragePct = 0.0
    if added_auto_detect:
        obj.AutoDetectSpace = True


def _initialize_equipment_defaults(obj):
    if str(obj.Type) not in {"Wall", "Cassette", "Duct"}:
        obj.Type = "Wall"
    if _to_float(obj.CapacityBTU, 0) <= 0:
        obj.CapacityBTU = 12000.0
    if _to_float(obj.Height, 0) <= 0:
        obj.Height = 2.3
    if not isinstance(getattr(obj, "AutoDetectSpace", True), bool):
        obj.AutoDetectSpace = True
    if _to_float(obj.CoveragePct, 0) < 0:
        obj.CoveragePct = 0.0


def _equipment_size(eq_type):
    if eq_type == "Cassette":
        return (600.0, 600.0, 320.0)
    if eq_type == "Duct":
        return (1200.0, 360.0, 320.0)
    return (900.0, 260.0, 220.0)


def _build_equipment_shape(equipment_obj):
    eq_type = str(getattr(equipment_obj, "Type", "Wall"))
    sx, sy, sz = _equipment_size(eq_type)
    return Part.makeBox(sx, sy, sz)


def find_equipments(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    equipments = []
    for obj in doc.Objects:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == MEP_TYPE:
            equipments.append(obj)
    return equipments


def _space_from_selection(doc):
    selected = selection.get_selected_objects(resolve_links=True)
    for obj in selected:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == hvac_space.MEP_TYPE:
            return obj
        if hasattr(obj, "PropertiesList") and "Space" in obj.PropertiesList and getattr(obj, "Space", None):
            return obj.Space
        for space in hvac_space.find_spaces(doc):
            if getattr(space, "BaseSpace", None) == obj:
                return space
    return None


def _space_from_position(doc, point):
    if point is None:
        return None
    for space in hvac_space.find_spaces(doc):
        base = getattr(space, "BaseSpace", None)
        if base is None or not hasattr(base, "Shape"):
            continue
        try:
            if base.Shape.BoundBox.isInside(point):
                return space
        except Exception:
            continue
    return None


def detect_space_for_equipment(equipment_obj):
    if equipment_obj is None:
        return None
    doc = equipment_obj.Document
    space = _space_from_selection(doc)
    if space is not None:
        return space

    point = getattr(equipment_obj, "Placement", App.Placement()).Base
    space = _space_from_position(doc, point)
    if space is not None:
        return space

    spaces = hvac_space.find_spaces(doc)
    if len(spaces) == 1:
        return spaces[0]
    return None


def update_equipment_coverage(equipment_obj):
    if equipment_obj is None:
        return 0.0
    load = 0.0
    if getattr(equipment_obj, "Space", None) is not None:
        load = _to_float(equipment_obj.Space.CoolingLoadBTU, 0.0)
    capacity = _to_float(equipment_obj.CapacityBTU, 0.0)
    if load > 0:
        equipment_obj.CoveragePct = round((capacity / load) * 100.0, 2)
    else:
        equipment_obj.CoveragePct = 0.0
    return equipment_obj.CoveragePct


def update_equipment_ports(equipment_obj):
    hvac_ports.update_equipment_ports(equipment_obj)


def _auto_assign_space(equipment_obj):
    if not bool(getattr(equipment_obj, "AutoDetectSpace", True)):
        return
    space = detect_space_for_equipment(equipment_obj)
    if space is not None and space != getattr(equipment_obj, "Space", None):
        equipment_obj.Space = space
        log("Recinto detectado para {0}: {1}".format(equipment_obj.Name, space.Name))


def insert_evaporator_from_selection(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return None

    obj = doc.addObject("Part::FeaturePython", "HVAC_Evaporator")
    HVACEquipmentProxy(obj)
    HVACEquipmentViewProvider(obj.ViewObject)
    ensure_equipment_properties(obj)
    _initialize_equipment_defaults(obj)

    points = selection.get_selected_points()
    if points:
        placement = getattr(obj, "Placement", App.Placement())
        placement.Base = points[0]
        obj.Placement = placement
        log("Evaporadora ubicada en punto seleccionado")

    space = _space_from_selection(doc)
    if space is not None:
        obj.Space = space
        log("Evaporadora asociada a recinto: {0}".format(space.Name))
    else:
        _auto_assign_space(obj)

    obj.Shape = _build_equipment_shape(obj)
    update_equipment_ports(obj)
    update_equipment_coverage(obj)
    return obj


class HVACEquipmentProxy:
    def __init__(self, obj):
        obj.Proxy = self
        self._busy = False
        ensure_equipment_properties(obj)
        _initialize_equipment_defaults(obj)

    def onChanged(self, obj, prop):  # noqa: N802
        if self._busy:
            return
        if prop in {"Type", "CapacityBTU", "Space", "Height", "Placement", "AutoDetectSpace"}:
            self._busy = True
            try:
                if prop in {"Placement", "AutoDetectSpace"}:
                    _auto_assign_space(obj)
                if prop in {"Type", "Placement", "Height"}:
                    update_equipment_ports(obj)
                if prop in {"CapacityBTU", "Space", "Placement", "AutoDetectSpace"}:
                    update_equipment_coverage(obj)
            finally:
                self._busy = False

    def execute(self, obj):
        if self._busy:
            return
        self._busy = True
        try:
            ensure_equipment_properties(obj)
            _initialize_equipment_defaults(obj)
            obj.Shape = _build_equipment_shape(obj)
            _auto_assign_space(obj)
            update_equipment_ports(obj)
            update_equipment_coverage(obj)
        finally:
            self._busy = False


class HVACEquipmentViewProvider:
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
