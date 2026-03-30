"""HVAC condenser object and capacity validation."""

import os

import FreeCAD as App
import Part

from ..utils import selection
from . import hvac_equipment
from . import hvac_project

MEP_TYPE = "HVACCondenser"
LOG_PREFIX = "[MEP-HVAC][Condenser] "
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


def ensure_condenser_properties(obj):
    added_capacity = False
    added_load = False
    added_coverage = False
    added_auto = False

    if "MEPType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
    if str(getattr(obj, "MEPType", "")) != MEP_TYPE:
        obj.MEPType = MEP_TYPE

    if "CapacityBTU" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "CapacityBTU", "HVAC Condenser", "Condenser capacity")
        added_capacity = True
    if "ConnectedUnits" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyLinkList",
            "ConnectedUnits",
            "HVAC Condenser",
            "Evaporator units connected to this condenser",
        )
    if "ConnectedLoadBTU" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "ConnectedLoadBTU",
            "HVAC Condenser",
            "Sum of connected evaporator capacities",
        )
        added_load = True
    if "CoveragePct" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "CoveragePct",
            "HVAC Condenser",
            "Condenser coverage over connected load",
        )
        added_coverage = True
    if "AutoCollect" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyBool",
            "AutoCollect",
            "HVAC Condenser",
            "When true, use all evaporators if list is empty",
        )
        added_auto = True

    if added_capacity:
        obj.CapacityBTU = 36000.0
    if added_load:
        obj.ConnectedLoadBTU = 0.0
    if added_coverage:
        obj.CoveragePct = 0.0
    if added_auto:
        obj.AutoCollect = True


def _initialize_condenser_defaults(obj):
    if _to_float(obj.CapacityBTU, 0.0) <= 0:
        obj.CapacityBTU = 36000.0
    if _to_float(obj.ConnectedLoadBTU, 0.0) < 0:
        obj.ConnectedLoadBTU = 0.0
    if _to_float(obj.CoveragePct, 0.0) < 0:
        obj.CoveragePct = 0.0
    if not isinstance(getattr(obj, "AutoCollect", True), bool):
        obj.AutoCollect = True


def _build_condenser_shape():
    return Part.makeBox(1200.0, 500.0, 900.0)


def find_condensers(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    condensers = []
    for obj in doc.Objects:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == MEP_TYPE:
            condensers.append(obj)
    return condensers


def _selected_equipments(doc):
    picked = []
    for obj in selection.get_selected_objects(resolve_links=True):
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
            if str(obj.MEPType) == hvac_equipment.MEP_TYPE:
                picked.append(obj)
    if picked:
        return picked
    return []


def _selected_condensers(doc):
    picked = []
    for obj in selection.get_selected_objects(resolve_links=True):
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
            if str(obj.MEPType) == MEP_TYPE:
                picked.append(obj)
    if picked:
        return picked
    return []


def _deduplicate_units(units):
    unique = []
    seen = set()
    for unit in units:
        if unit is None:
            continue
        if not hasattr(unit, "PropertiesList") or "MEPType" not in unit.PropertiesList:
            continue
        if str(getattr(unit, "MEPType", "")) != hvac_equipment.MEP_TYPE:
            continue
        key = str(getattr(unit, "Name", ""))
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(unit)
    return unique


def assign_units_to_condenser(condenser_obj, units, append=True):
    if condenser_obj is None:
        return 0
    ensure_condenser_properties(condenser_obj)

    selected_units = _deduplicate_units(list(units or []))
    if append:
        current_units = _deduplicate_units(list(getattr(condenser_obj, "ConnectedUnits", []) or []))
        by_name = {str(unit.Name): unit for unit in current_units}
        for unit in selected_units:
            by_name[str(unit.Name)] = unit
        final_units = list(by_name.values())
    else:
        final_units = selected_units

    condenser_obj.ConnectedUnits = final_units
    if final_units:
        condenser_obj.AutoCollect = False
    recalculate_condenser(condenser_obj)
    log(
        "Condenser {0}: evaporadoras asignadas={1} (append={2})".format(
            condenser_obj.Name, len(final_units), bool(append)
        )
    )
    return len(final_units)


def assign_selected_units_to_selected_condenser(doc=None, append=True):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return None

    condensers = _selected_condensers(doc)
    if not condensers:
        log("Seleccione una condensadora para asignar evaporadoras")
        return None
    if len(condensers) > 1:
        log("Se detectaron multiples condensadoras. Se usa la primera seleccionada")
    condenser = condensers[0]

    units = _selected_equipments(doc)
    if not units:
        log("Seleccione una o mas evaporadoras para asignar")
        return condenser

    assign_units_to_condenser(condenser, units, append=append)
    return condenser


def recalculate_condenser(condenser_obj):
    if condenser_obj is None:
        return 0.0
    ensure_condenser_properties(condenser_obj)

    old_connected = _to_float(getattr(condenser_obj, "ConnectedLoadBTU", 0.0), 0.0)
    old_coverage = _to_float(getattr(condenser_obj, "CoveragePct", 0.0), 0.0)

    units = list(getattr(condenser_obj, "ConnectedUnits", []) or [])
    if not units and bool(getattr(condenser_obj, "AutoCollect", True)):
        units = hvac_equipment.find_equipments(condenser_obj.Document)
        condenser_obj.ConnectedUnits = units

    connected_load = 0.0
    for unit in units:
        connected_load += _to_float(getattr(unit, "CapacityBTU", 0.0), 0.0)
    condenser_obj.ConnectedLoadBTU = round(connected_load, 2)

    capacity = _to_float(condenser_obj.CapacityBTU, 0.0)
    if connected_load > 0:
        condenser_obj.CoveragePct = round((capacity / connected_load) * 100.0, 2)
    else:
        condenser_obj.CoveragePct = 0.0

    if abs(old_connected - condenser_obj.ConnectedLoadBTU) > 0.01 or abs(old_coverage - condenser_obj.CoveragePct) > 0.01:
        log(
            "Condenser {0}: capacidad={1}, conectada={2}, cobertura={3}%".format(
                condenser_obj.Name,
                round(capacity, 2),
                round(connected_load, 2),
                round(_to_float(condenser_obj.CoveragePct, 0.0), 2),
            )
        )
    return condenser_obj.CoveragePct


def insert_condenser_from_selection(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return None

    obj = doc.addObject("Part::FeaturePython", "HVAC_Condenser")
    HVACCondenserProxy(obj)
    HVACCondenserViewProvider(obj.ViewObject)
    ensure_condenser_properties(obj)
    _initialize_condenser_defaults(obj)
    obj.Shape = _build_condenser_shape()

    points = selection.get_selected_points()
    if points:
        point = App.Vector(points[0])
        placement = getattr(obj, "Placement", App.Placement())
        placement.Base = point
        obj.Placement = placement
        log("Condenser ubicada en punto seleccionado")
    else:
        log("Condenser creada sin conexiones automaticas. Ubique y asigne manualmente.")

    recalculate_condenser(obj)
    hvac_project.add_object_to_hvac_group(doc, obj)
    return obj


class HVACCondenserProxy:
    def __init__(self, obj):
        obj.Proxy = self
        self._busy = False
        ensure_condenser_properties(obj)
        _initialize_condenser_defaults(obj)

    def onChanged(self, obj, prop):  # noqa: N802
        if self._busy:
            return
        if prop in {"CapacityBTU", "ConnectedUnits", "AutoCollect"}:
            self._busy = True
            try:
                recalculate_condenser(obj)
            finally:
                self._busy = False

    def execute(self, obj):
        if self._busy:
            return
        self._busy = True
        try:
            ensure_condenser_properties(obj)
            _initialize_condenser_defaults(obj)
            obj.Shape = _build_condenser_shape()
            recalculate_condenser(obj)
        finally:
            self._busy = False


class HVACCondenserViewProvider:
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
