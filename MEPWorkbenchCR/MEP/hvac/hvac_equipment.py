"""HVAC evaporator equipment object."""

import os

import FreeCAD as App
import Part

from ..utils import selection
from . import hvac_ports
from . import hvac_project
from . import hvac_space

MEP_TYPE = "HVACEquipment"
LOG_PREFIX = "[MEP-HVAC][Equipment] "
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "hvac.svg")
).replace(os.sep, "/")
EVAPORATOR_LIBRARY = {
    "Pared_9000": {"Type": "Wall", "CapacityBTU": 9000.0, "Size": (760.0, 230.0, 220.0)},
    "Pared_12000": {"Type": "Wall", "CapacityBTU": 12000.0, "Size": (900.0, 260.0, 220.0)},
    "Pared_18000": {"Type": "Wall", "CapacityBTU": 18000.0, "Size": (1040.0, 280.0, 240.0)},
    "Cassette_24000": {"Type": "Cassette", "CapacityBTU": 24000.0, "Size": (600.0, 600.0, 320.0)},
    "Cassette_36000": {"Type": "Cassette", "CapacityBTU": 36000.0, "Size": (840.0, 840.0, 350.0)},
    "Ducto_36000": {"Type": "Duct", "CapacityBTU": 36000.0, "Size": (1200.0, 360.0, 320.0)},
    "Ducto_60000": {"Type": "Duct", "CapacityBTU": 60000.0, "Size": (1600.0, 450.0, 380.0)},
}
DEFAULT_MODEL = "Pared_12000"
DEFAULT_SYMBOL_SIZE = 450.0


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
    added_model = False
    added_type = False
    added_capacity = False
    added_height = False
    added_base_level = False
    added_symbol_size = False
    added_show_symbol = False
    added_auto_detect = False
    added_use_ports = False
    added_coverage = False

    if "MEPType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
    if str(getattr(obj, "MEPType", "")) != MEP_TYPE:
        obj.MEPType = MEP_TYPE

    if "Model" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "Model", "HVAC Equipment", "Concrete evaporator model")
        obj.Model = list(EVAPORATOR_LIBRARY.keys())
        added_model = True
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
    if "BaseLevel" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "BaseLevel", "HVAC Equipment", "Base elevation reference (mm)")
        added_base_level = True
    if "Symbol2DSize" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Symbol2DSize", "HVAC Equipment", "2D symbol size (mm)")
        added_symbol_size = True
    if "ShowSymbol2D" not in obj.PropertiesList:
        obj.addProperty("App::PropertyBool", "ShowSymbol2D", "HVAC Equipment", "Show 2D symbol in plan")
        added_show_symbol = True
    if "Symbol2D" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "Symbol2D", "HVAC Equipment", "Linked 2D symbol object")
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
    if "UsePorts" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyBool",
            "UsePorts",
            "HVAC Equipment",
            "Generate technical ports for routes/system flow",
        )
        added_use_ports = True
    if "Ports" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLinkList", "Ports", "HVAC Equipment", "Equipment port objects")

    if added_model:
        obj.Model = DEFAULT_MODEL
    if added_type:
        obj.Type = EVAPORATOR_LIBRARY[DEFAULT_MODEL]["Type"]
    if added_capacity:
        obj.CapacityBTU = EVAPORATOR_LIBRARY[DEFAULT_MODEL]["CapacityBTU"]
    if added_height:
        obj.Height = 2.3
    if added_base_level:
        obj.BaseLevel = 0.0
    if added_symbol_size:
        obj.Symbol2DSize = DEFAULT_SYMBOL_SIZE
    if added_show_symbol:
        obj.ShowSymbol2D = True
    if added_coverage:
        obj.CoveragePct = 0.0
    if added_auto_detect:
        obj.AutoDetectSpace = True
    if added_use_ports:
        obj.UsePorts = False


def available_models():
    return list(EVAPORATOR_LIBRARY.keys())


def _model_spec(model_name):
    return EVAPORATOR_LIBRARY.get(str(model_name), EVAPORATOR_LIBRARY[DEFAULT_MODEL])


def set_equipment_model(equipment_obj, model_name, force=False):
    if equipment_obj is None:
        return
    ensure_equipment_properties(equipment_obj)
    model = str(model_name or DEFAULT_MODEL)
    if model not in EVAPORATOR_LIBRARY:
        model = DEFAULT_MODEL
    if "Model" in equipment_obj.PropertiesList:
        equipment_obj.Model = model

    spec = _model_spec(model)
    if force or str(getattr(equipment_obj, "Type", "")) not in {"Wall", "Cassette", "Duct"}:
        equipment_obj.Type = spec["Type"]
    if force or _to_float(getattr(equipment_obj, "CapacityBTU", 0.0), 0.0) <= 0.0:
        equipment_obj.CapacityBTU = float(spec["CapacityBTU"])


def _initialize_equipment_defaults(obj):
    model = str(getattr(obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    if model not in EVAPORATOR_LIBRARY:
        model = DEFAULT_MODEL
    if "Model" in obj.PropertiesList:
        obj.Model = model

    spec = _model_spec(model)
    if str(obj.Type) not in {"Wall", "Cassette", "Duct"}:
        obj.Type = spec["Type"]
    if _to_float(obj.CapacityBTU, 0) <= 0:
        obj.CapacityBTU = spec["CapacityBTU"]
    if _to_float(obj.Height, 0) <= 0:
        obj.Height = 2.3
    if _to_float(getattr(obj, "Symbol2DSize", 0.0), 0.0) <= 0:
        obj.Symbol2DSize = DEFAULT_SYMBOL_SIZE
    if not isinstance(getattr(obj, "ShowSymbol2D", True), bool):
        obj.ShowSymbol2D = True
    if not isinstance(getattr(obj, "AutoDetectSpace", True), bool):
        obj.AutoDetectSpace = True
    if not isinstance(getattr(obj, "UsePorts", False), bool):
        obj.UsePorts = False
    if _to_float(obj.CoveragePct, 0) < 0:
        obj.CoveragePct = 0.0


def _equipment_size(equipment_obj):
    model = str(getattr(equipment_obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    if model in EVAPORATOR_LIBRARY:
        return tuple(EVAPORATOR_LIBRARY[model]["Size"])

    eq_type = str(getattr(equipment_obj, "Type", "Wall"))
    if eq_type == "Cassette":
        return (600.0, 600.0, 320.0)
    if eq_type == "Duct":
        return (1200.0, 360.0, 320.0)
    return (900.0, 260.0, 220.0)


def _build_equipment_shape(equipment_obj):
    sx, sy, sz = _equipment_size(equipment_obj)
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
    if equipment_obj is None:
        return []
    if not bool(getattr(equipment_obj, "UsePorts", False)):
        return list(getattr(equipment_obj, "Ports", []) or [])
    hvac_ports.update_equipment_ports(equipment_obj)


def _height_to_mm(equipment_obj):
    return _to_float(getattr(equipment_obj, "Height", 0.0), 0.0) * 1000.0


def _vector_changed(a, b, tol=0.01):
    try:
        va = App.Vector(a)
        vb = App.Vector(b)
    except Exception:
        return True
    return (
        abs(float(va.x) - float(vb.x)) > tol
        or abs(float(va.y) - float(vb.y)) > tol
        or abs(float(va.z) - float(vb.z)) > tol
    )


def _shape_size_changed(shape_obj, expected_size_mm, tol=0.1):
    try:
        if shape_obj is None or not hasattr(shape_obj, "BoundBox"):
            return True
        bbox = shape_obj.BoundBox
        return (
            abs(float(bbox.XLength) - float(expected_size_mm)) > tol
            or abs(float(bbox.YLength) - float(expected_size_mm)) > tol
        )
    except Exception:
        return True


def _equipment_shape_changed(equipment_obj, tol=0.1):
    try:
        expected = _equipment_size(equipment_obj)
        shape_obj = getattr(equipment_obj, "Shape", None)
        if shape_obj is None or shape_obj.isNull():
            return True
        bbox = shape_obj.BoundBox
        return (
            abs(float(bbox.XLength) - float(expected[0])) > tol
            or abs(float(bbox.YLength) - float(expected[1])) > tol
            or abs(float(bbox.ZLength) - float(expected[2])) > tol
        )
    except Exception:
        return True


def _geometry_needs_sync(equipment_obj):
    if equipment_obj is None:
        return False
    if _equipment_shape_changed(equipment_obj):
        return True

    placement = getattr(equipment_obj, "Placement", App.Placement())
    target_z = _to_float(getattr(equipment_obj, "BaseLevel", 0.0), 0.0) + _height_to_mm(equipment_obj)
    if abs(float(placement.Base.z) - float(target_z)) > 0.01:
        return True

    show_symbol = bool(getattr(equipment_obj, "ShowSymbol2D", True))
    symbol_obj = getattr(equipment_obj, "Symbol2D", None)
    if show_symbol:
        if symbol_obj is None or getattr(symbol_obj, "Document", None) is None:
            return True
        size_mm = _to_float(getattr(equipment_obj, "Symbol2DSize", DEFAULT_SYMBOL_SIZE), DEFAULT_SYMBOL_SIZE)
        if _shape_size_changed(getattr(symbol_obj, "Shape", None), size_mm):
            return True
        expected_base = App.Vector(
            placement.Base.x,
            placement.Base.y,
            _to_float(getattr(equipment_obj, "BaseLevel", 0.0), 0.0),
        )
        current_placement = getattr(symbol_obj, "Placement", App.Placement())
        if _vector_changed(current_placement.Base, expected_base):
            return True
    return False


def _apply_equipment_elevation(equipment_obj):
    if equipment_obj is None:
        return
    placement = getattr(equipment_obj, "Placement", App.Placement())
    base = App.Vector(placement.Base)
    base_level = _to_float(getattr(equipment_obj, "BaseLevel", 0.0), 0.0)
    target_z = base_level + _height_to_mm(equipment_obj)
    if abs(base.z - target_z) > 0.01:
        base.z = target_z
        placement.Base = base
        equipment_obj.Placement = placement


def _build_symbol_shape(size_mm):
    radius = max(50.0, float(size_mm) * 0.5)
    p1 = App.Vector(-radius, -radius, 0.0)
    p2 = App.Vector(radius, radius, 0.0)
    p3 = App.Vector(-radius, radius, 0.0)
    p4 = App.Vector(radius, -radius, 0.0)
    line_1 = Part.makeLine(p1, p2)
    line_2 = Part.makeLine(p3, p4)
    circle = Part.makeCircle(radius * 0.9, App.Vector(0.0, 0.0, 0.0), App.Vector(0, 0, 1))
    return Part.Compound([line_1, line_2, circle])


def _ensure_symbol2d(equipment_obj):
    if equipment_obj is None:
        return
    if "Symbol2D" not in getattr(equipment_obj, "PropertiesList", []):
        return
    if not bool(getattr(equipment_obj, "ShowSymbol2D", True)):
        symbol_obj = getattr(equipment_obj, "Symbol2D", None)
        if symbol_obj is not None and hasattr(symbol_obj, "ViewObject"):
            if bool(getattr(symbol_obj.ViewObject, "Visibility", True)):
                symbol_obj.ViewObject.Visibility = False
        return

    doc = equipment_obj.Document
    if doc is None:
        return

    symbol_obj = getattr(equipment_obj, "Symbol2D", None)
    if symbol_obj is None:
        symbol_obj = doc.addObject("Part::Feature", "HVAC_Evaporator2D")
        symbol_obj.Label = "SYM2D_{0}".format(str(getattr(equipment_obj, "Label", equipment_obj.Name)))
        equipment_obj.Symbol2D = symbol_obj
        hvac_project.add_object_to_hvac_group(doc, symbol_obj)
        if hasattr(symbol_obj, "ViewObject") and hasattr(symbol_obj.ViewObject, "ShowInTree"):
            symbol_obj.ViewObject.ShowInTree = False

    size_mm = _to_float(getattr(equipment_obj, "Symbol2DSize", DEFAULT_SYMBOL_SIZE), DEFAULT_SYMBOL_SIZE)
    if _shape_size_changed(getattr(symbol_obj, "Shape", None), size_mm):
        symbol_obj.Shape = _build_symbol_shape(size_mm)

    eq_placement = getattr(equipment_obj, "Placement", App.Placement())
    symbol_placement = App.Placement(eq_placement)
    symbol_placement.Base = App.Vector(
        eq_placement.Base.x,
        eq_placement.Base.y,
        _to_float(getattr(equipment_obj, "BaseLevel", 0.0), 0.0),
    )
    current_placement = getattr(symbol_obj, "Placement", App.Placement())
    placement_changed = _vector_changed(current_placement.Base, symbol_placement.Base)
    try:
        rot_changed = float(current_placement.Rotation.Angle - symbol_placement.Rotation.Angle)
        placement_changed = placement_changed or abs(rot_changed) > 0.0001
    except Exception:
        pass
    if placement_changed:
        symbol_obj.Placement = symbol_placement
    if hasattr(symbol_obj, "ViewObject"):
        if not bool(getattr(symbol_obj.ViewObject, "Visibility", False)):
            symbol_obj.ViewObject.Visibility = True


def _sync_equipment_geometry(equipment_obj):
    if equipment_obj is None:
        return
    _apply_equipment_elevation(equipment_obj)
    equipment_obj.Shape = _build_equipment_shape(equipment_obj)
    _ensure_symbol2d(equipment_obj)
    if bool(getattr(equipment_obj, "UsePorts", False)):
        update_equipment_ports(equipment_obj)


def _pick_model_for_insert():
    if not App.GuiUp:
        return DEFAULT_MODEL

    model_names = available_models()
    current_index = 0
    try:
        current_index = max(0, model_names.index(DEFAULT_MODEL))
    except Exception:
        current_index = 0

    try:
        from PySide2 import QtWidgets
    except Exception:
        try:
            from PySide import QtGui as QtWidgets  # FreeCAD legacy fallback
        except Exception:
            return DEFAULT_MODEL

    try:
        selected, ok = QtWidgets.QInputDialog.getItem(
            None,
            "Insertar Evaporadora HVAC",
            "Modelo de evaporadora:",
            model_names,
            current_index,
            False,
        )
        if ok and selected:
            return str(selected)
    except Exception as exc:
        log("Selector de modelo no disponible, se usa default: {0}".format(exc))
    return DEFAULT_MODEL


def _auto_assign_space(equipment_obj, warn_if_not_found=False):
    if not bool(getattr(equipment_obj, "AutoDetectSpace", True)):
        return False
    space = detect_space_for_equipment(equipment_obj)
    if space is not None and space != getattr(equipment_obj, "Space", None):
        equipment_obj.Space = space
        log("Recinto detectado para {0}: {1}".format(equipment_obj.Name, space.Name))
        return True
    if space is not None:
        return True
    if warn_if_not_found:
        log("Evaporadora sin recinto detectado. Asignela manualmente si es necesario.")
    return False


def insert_evaporator_from_selection(doc=None, model_name=None):
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

    selected_model = str(model_name or _pick_model_for_insert())
    set_equipment_model(obj, selected_model, force=True)
    obj.Label = "EVAP_{0}".format(str(getattr(obj, "Model", selected_model)))
    log(
        "Evaporadora concreta seleccionada: {0} ({1} BTU/h)".format(
            obj.Model,
            int(_to_float(obj.CapacityBTU, 0.0)),
        )
    )

    points = selection.get_selected_points()
    if points:
        point = App.Vector(points[0])
        obj.BaseLevel = float(point.z)
        placement = getattr(obj, "Placement", App.Placement())
        placement.Base = App.Vector(point.x, point.y, point.z)
        obj.Placement = placement
        log("Evaporadora ubicada en punto seleccionado")

    space = _space_from_selection(doc)
    if space is not None:
        obj.Space = space
        log("Evaporadora asociada a recinto: {0}".format(space.Name))
    else:
        _auto_assign_space(obj, warn_if_not_found=True)

    _sync_equipment_geometry(obj)
    update_equipment_coverage(obj)
    hvac_project.add_object_to_hvac_group(doc, obj)
    return obj


class HVACEquipmentProxy:
    def __init__(self, obj):
        obj.Proxy = self
        self._busy = False
        ensure_equipment_properties(obj)
        _initialize_equipment_defaults(obj)

    def onChanged(self, obj, prop):  # noqa: N802
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        if prop in {
            "Model",
            "Type",
            "CapacityBTU",
            "Space",
            "Height",
            "BaseLevel",
            "Placement",
            "Symbol2DSize",
            "ShowSymbol2D",
            "AutoDetectSpace",
            "UsePorts",
        }:
            self._busy = True
            try:
                if prop == "Model":
                    set_equipment_model(obj, getattr(obj, "Model", DEFAULT_MODEL), force=True)
                if prop == "Placement":
                    placement = getattr(obj, "Placement", App.Placement())
                    inferred_base_level = float(placement.Base.z) - _height_to_mm(obj)
                    if abs(_to_float(getattr(obj, "BaseLevel", 0.0), 0.0) - inferred_base_level) > 0.01:
                        obj.BaseLevel = inferred_base_level
                if prop in {"Placement", "AutoDetectSpace"}:
                    _auto_assign_space(obj)
                if prop in {
                    "Model",
                    "Type",
                    "Placement",
                    "Height",
                    "BaseLevel",
                    "Symbol2DSize",
                    "ShowSymbol2D",
                    "UsePorts",
                }:
                    _sync_equipment_geometry(obj)
                if prop in {"Model", "CapacityBTU", "Space", "Placement", "AutoDetectSpace", "Height", "BaseLevel"}:
                    update_equipment_coverage(obj)
            finally:
                self._busy = False

    def execute(self, obj):
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        self._busy = True
        try:
            ensure_equipment_properties(obj)
            _initialize_equipment_defaults(obj)
            if _geometry_needs_sync(obj):
                _sync_equipment_geometry(obj)
            _auto_assign_space(obj)
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
