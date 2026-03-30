"""HVAC evaporator equipment object."""

import os
import re
import unicodedata

import FreeCAD as App
import Part

from ..utils import selection
from . import hvac_ports
from . import hvac_project
from . import hvac_space

MEP_TYPE = "HVACEquipment"
MASTER_MEP_TYPE = "HVACEvaporatorMaster"
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
MASTER_PREFIX = "HVAC_EvapMaster_"
GROUP_MODEL_PREFIX = "Grupo::"
GROUP_MODEL_LABEL_ALIASES = {
    "modelos",
    "models",
    "model",
    "biblioteca",
    "hvac modelos",
    "hvac models",
}


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


def _normalize_text(value):
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))


def _is_group(obj):
    type_id = str(getattr(obj, "TypeId", "") or "")
    if type_id.startswith("App::DocumentObjectGroup"):
        return True
    return hasattr(obj, "Group") and hasattr(obj, "addObject")


def _shape_from_obj(obj):
    if obj is None or not hasattr(obj, "Shape"):
        return None
    try:
        shape = obj.Shape
        if shape is None or shape.isNull():
            return None
        bbox = shape.BoundBox
        if float(bbox.XLength) <= 0.1 or float(bbox.YLength) <= 0.1 or float(bbox.ZLength) <= 0.1:
            return None
        return shape
    except Exception:
        return None


def _find_model_group(doc):
    if doc is None:
        return None

    selected = list(selection.get_selected_objects(resolve_links=True) or [])
    for obj in selected:
        if not _is_group(obj):
            continue
        label_norm = _normalize_text(getattr(obj, "Label", ""))
        name_norm = _normalize_text(getattr(obj, "Name", ""))
        if label_norm in GROUP_MODEL_LABEL_ALIASES or name_norm in GROUP_MODEL_LABEL_ALIASES:
            return obj

    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_group(obj):
            continue
        label_norm = _normalize_text(getattr(obj, "Label", ""))
        name_norm = _normalize_text(getattr(obj, "Name", ""))
        if label_norm in GROUP_MODEL_LABEL_ALIASES or name_norm in GROUP_MODEL_LABEL_ALIASES:
            return obj
    return None


def _group_model_map(doc):
    result = {}
    group = _find_model_group(doc)
    if group is None:
        return result

    for child in list(getattr(group, "Group", []) or []):
        candidate = selection.unwrap_link(child)
        if _shape_from_obj(candidate) is None:
            continue
        label = str(getattr(candidate, "Label", "") or getattr(candidate, "Name", "") or "").strip()
        if not label:
            continue
        key_base = GROUP_MODEL_PREFIX + label
        key = key_base
        idx = 2
        while key in result:
            key = "{0} ({1})".format(key_base, idx)
            idx += 1
        result[key] = candidate
    return result


def _is_group_model_name(model_name):
    return str(model_name or "").startswith(GROUP_MODEL_PREFIX)


def _model_capacity_guess(model_name):
    tokens = re.findall(r"\d{4,6}", str(model_name or ""))
    if not tokens:
        return 0.0
    try:
        return float(tokens[0])
    except Exception:
        return 0.0


def _group_model_object(doc, model_name):
    return _group_model_map(doc).get(str(model_name or ""))


def _group_model_shape(doc, model_name):
    source_obj = _group_model_object(doc, model_name)
    source_shape = _shape_from_obj(source_obj)
    if source_shape is None:
        return None
    try:
        shape_copy = source_shape.copy()
        bbox = shape_copy.BoundBox
        shape_copy.translate(App.Vector(-float(bbox.Center.x), -float(bbox.Center.y), -float(bbox.ZMin)))
        return shape_copy
    except Exception:
        return None


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

    model_added = False
    if "Model" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "Model", "HVAC Equipment", "Concrete evaporator model")
        obj.Model = list(EVAPORATOR_LIBRARY.keys())
        model_added = True
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

    model_options = available_models(getattr(obj, "Document", None))
    if "Model" in obj.PropertiesList:
        current_model = str(getattr(obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
        try:
            obj.Model = model_options
        except Exception:
            pass
        if model_added:
            current_model = DEFAULT_MODEL
        if current_model not in model_options:
            current_model = DEFAULT_MODEL
        try:
            obj.Model = current_model
        except Exception:
            pass
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


def available_models(doc=None):
    models = list(EVAPORATOR_LIBRARY.keys())
    if doc is not None:
        models.extend(list(_group_model_map(doc).keys()))
    return models


def _model_spec(model_name):
    return EVAPORATOR_LIBRARY.get(str(model_name), EVAPORATOR_LIBRARY[DEFAULT_MODEL])


def set_equipment_model(equipment_obj, model_name, force=False):
    if equipment_obj is None:
        return
    ensure_equipment_properties(equipment_obj)
    doc = getattr(equipment_obj, "Document", None)
    model_options = available_models(doc)
    model = str(model_name or DEFAULT_MODEL)
    if model not in model_options:
        model = DEFAULT_MODEL
    if "Model" in equipment_obj.PropertiesList:
        equipment_obj.Model = model

    if _is_group_model_name(model):
        if force or str(getattr(equipment_obj, "Type", "")) not in {"Wall", "Cassette", "Duct"}:
            equipment_obj.Type = "Wall"
        if force or _to_float(getattr(equipment_obj, "CapacityBTU", 0.0), 0.0) <= 0.0:
            guessed_capacity = _model_capacity_guess(model)
            equipment_obj.CapacityBTU = guessed_capacity if guessed_capacity > 0 else 12000.0
        return

    spec = _model_spec(model)
    if force or str(getattr(equipment_obj, "Type", "")) not in {"Wall", "Cassette", "Duct"}:
        equipment_obj.Type = spec["Type"]
    if force or _to_float(getattr(equipment_obj, "CapacityBTU", 0.0), 0.0) <= 0.0:
        equipment_obj.CapacityBTU = float(spec["CapacityBTU"])


def _initialize_equipment_defaults(obj):
    doc = getattr(obj, "Document", None)
    model_options = available_models(doc)
    model = str(getattr(obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    if model not in model_options:
        model = DEFAULT_MODEL
    if "Model" in obj.PropertiesList:
        try:
            obj.Model = model_options
        except Exception:
            pass
        obj.Model = model

    if model in EVAPORATOR_LIBRARY:
        spec = _model_spec(model)
        if str(obj.Type) not in {"Wall", "Cassette", "Duct"}:
            obj.Type = spec["Type"]
        if _to_float(obj.CapacityBTU, 0) <= 0:
            obj.CapacityBTU = spec["CapacityBTU"]
    else:
        if str(obj.Type) not in {"Wall", "Cassette", "Duct"}:
            obj.Type = "Wall"
        if _to_float(obj.CapacityBTU, 0) <= 0:
            guessed_capacity = _model_capacity_guess(model)
            obj.CapacityBTU = guessed_capacity if guessed_capacity > 0 else 12000.0
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
    doc = getattr(equipment_obj, "Document", None)
    model = str(getattr(equipment_obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    if model in EVAPORATOR_LIBRARY:
        return tuple(EVAPORATOR_LIBRARY[model]["Size"])
    if _is_group_model_name(model):
        group_shape = _group_model_shape(doc, model)
        if group_shape is not None:
            bbox = group_shape.BoundBox
            return (
                max(100.0, float(bbox.XLength)),
                max(100.0, float(bbox.YLength)),
                max(100.0, float(bbox.ZLength)),
            )

    eq_type = str(getattr(equipment_obj, "Type", "Wall"))
    if eq_type == "Cassette":
        return (600.0, 600.0, 320.0)
    if eq_type == "Duct":
        return (1200.0, 360.0, 320.0)
    return (900.0, 260.0, 220.0)


def _is_link_equipment(equipment_obj):
    return str(getattr(equipment_obj, "TypeId", "") or "") == "App::Link"


def _sanitize_model_token(model_name):
    raw = str(model_name or DEFAULT_MODEL)
    token = "".join(char if (char.isalnum() or char == "_") else "_" for char in raw)
    token = "_".join([part for part in token.split("_") if part])
    return token or DEFAULT_MODEL


def _master_internal_name(model_name):
    return "{0}{1}".format(MASTER_PREFIX, _sanitize_model_token(model_name))


def _ensure_master_equipment(doc, model_name):
    if doc is None:
        return None
    model = str(model_name or DEFAULT_MODEL)
    if model not in EVAPORATOR_LIBRARY:
        return None
    internal_name = _master_internal_name(model)
    master = doc.getObject(internal_name)
    if master is None:
        master = doc.addObject("Part::Feature", internal_name)
        master.Label = "MASTER_EVAP_{0}".format(model)
    if hasattr(master, "PropertiesList"):
        if "MEPType" not in master.PropertiesList:
            master.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
        if str(getattr(master, "MEPType", "")) != MASTER_MEP_TYPE:
            master.MEPType = MASTER_MEP_TYPE
        if "Model" not in master.PropertiesList:
            master.addProperty("App::PropertyString", "Model", "HVAC Equipment", "Concrete evaporator model")
        if str(getattr(master, "Model", "")) != model:
            master.Model = model

    sx, sy, sz = EVAPORATOR_LIBRARY[model]["Size"]
    shape_expected = Part.makeBox(float(sx), float(sy), float(sz))
    try:
        if getattr(master, "Shape", None) is None or master.Shape.isNull():
            master.Shape = shape_expected
        else:
            bbox = master.Shape.BoundBox
            if abs(float(bbox.XLength) - float(sx)) > 0.1 or abs(float(bbox.YLength) - float(sy)) > 0.1 or abs(
                float(bbox.ZLength) - float(sz)
            ) > 0.1:
                master.Shape = shape_expected
    except Exception:
        try:
            master.Shape = shape_expected
        except Exception:
            pass

    if hasattr(master, "ViewObject"):
        try:
            master.ViewObject.Visibility = False
        except Exception:
            pass
        try:
            if hasattr(master.ViewObject, "ShowInTree"):
                master.ViewObject.ShowInTree = False
        except Exception:
            pass
    hvac_project.add_object_to_hvac_group(doc, master)
    return master


def _build_equipment_shape(equipment_obj):
    doc = getattr(equipment_obj, "Document", None)
    model = str(getattr(equipment_obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    if _is_group_model_name(model):
        group_shape = _group_model_shape(doc, model)
        if group_shape is not None:
            return group_shape
    sx, sy, sz = _equipment_size(equipment_obj)
    return Part.makeBox(float(sx), float(sy), float(sz))


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


def _space_center_point(space_obj):
    if space_obj is None:
        return None
    base = getattr(space_obj, "BaseSpace", None)
    if base is None or not hasattr(base, "Shape"):
        return None
    try:
        bbox = base.Shape.BoundBox
        return App.Vector(float(bbox.Center.x), float(bbox.Center.y), float(bbox.ZMin))
    except Exception:
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


def _master_link_changed(equipment_obj):
    if not _is_link_equipment(equipment_obj):
        return False
    expected_master = _ensure_master_equipment(equipment_obj.Document, getattr(equipment_obj, "Model", DEFAULT_MODEL))
    if expected_master is None:
        return False
    return getattr(equipment_obj, "LinkedObject", None) != expected_master


def _geometry_needs_sync(equipment_obj):
    if equipment_obj is None:
        return False
    if _is_link_equipment(equipment_obj):
        if _master_link_changed(equipment_obj):
            return True
    else:
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
        try:
            if hasattr(symbol_obj.ViewObject, "Selectable"):
                symbol_obj.ViewObject.Selectable = False
        except Exception:
            pass


def _sync_equipment_geometry(equipment_obj):
    if equipment_obj is None:
        return
    _apply_equipment_elevation(equipment_obj)
    if _is_link_equipment(equipment_obj):
        expected_master = _ensure_master_equipment(equipment_obj.Document, getattr(equipment_obj, "Model", DEFAULT_MODEL))
        if expected_master is not None and getattr(equipment_obj, "LinkedObject", None) != expected_master:
            equipment_obj.LinkedObject = expected_master
        try:
            equipment_obj.LinkTransform = True
        except Exception:
            pass
    else:
        equipment_obj.Shape = _build_equipment_shape(equipment_obj)
    _ensure_symbol2d(equipment_obj)
    if bool(getattr(equipment_obj, "UsePorts", False)):
        update_equipment_ports(equipment_obj)


def _pick_model_for_insert(doc=None):
    if not App.GuiUp:
        return DEFAULT_MODEL

    model_names = available_models(doc)
    group_models = [name for name in model_names if _is_group_model_name(name)]
    if group_models:
        log("Modelos detectados desde grupo: {0}".format(len(group_models)))
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
            "Modelo de evaporadora (incluye Grupo Modelos):",
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

    selected_model = str(model_name or _pick_model_for_insert(doc=doc))
    set_equipment_model(obj, selected_model, force=True)
    obj.Label = "EVAP_{0}".format(str(getattr(obj, "Model", selected_model)))
    log(
        "Evaporadora concreta seleccionada: {0} ({1} BTU/h)".format(
            obj.Model,
            int(_to_float(obj.CapacityBTU, 0.0)),
        )
    )

    space = _space_from_selection(doc)
    points = selection.get_selected_points()
    point = None
    if points:
        point = App.Vector(points[0])
        log("Evaporadora ubicada en punto seleccionado")
    elif space is not None:
        point = _space_center_point(space)
        if point is not None:
            log("Evaporadora ubicada en centro del recinto seleccionado")
    if point is not None:
        obj.BaseLevel = float(point.z)
        placement = getattr(obj, "Placement", App.Placement())
        placement.Base = App.Vector(point.x, point.y, point.z)
        obj.Placement = placement

    if space is not None:
        obj.Space = space
        log("Evaporadora asociada a recinto: {0}".format(space.Name))
    else:
        _auto_assign_space(obj, warn_if_not_found=True)

    _sync_equipment_geometry(obj)
    update_equipment_coverage(obj)
    hvac_project.add_object_to_hvac_group(doc, obj)
    return obj


def refresh_equipment(equipment_obj):
    if equipment_obj is None:
        return
    ensure_equipment_properties(equipment_obj)
    _initialize_equipment_defaults(equipment_obj)
    if _geometry_needs_sync(equipment_obj):
        _sync_equipment_geometry(equipment_obj)
    _auto_assign_space(equipment_obj)
    update_equipment_coverage(equipment_obj)


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
