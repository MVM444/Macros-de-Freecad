"""HVAC project object: global climate settings and factor calculation."""

import os
import unicodedata

import FreeCAD as App

try:
    from ..i18n import tr
except Exception:
    from MEP.i18n import tr

MEP_TYPE = "HVACProject"
ROOT_GROUP_MEP_TYPE = "HVACRootGroup"
ROOT_GROUP_NAME = "HVAC_Air_Ventilation"
ROOT_GROUP_LABEL = "HVAC Air and Ventilation"
SPACES_GROUP_MEP_TYPE = "HVACSpacesGroup"
SPACES_GROUP_NAME = "HVAC_Espacios"
SPACES_GROUP_LABEL = "Espacios"
EQUIPMENT_GROUP_MEP_TYPE = "HVACEquipmentsGroup"
EQUIPMENT_GROUP_NAME = "HVAC_Equipos"
EQUIPMENT_GROUP_LABEL = "Equipos"
LABEL_GROUP_MEP_TYPE = "HVACLabelGroup"
LABEL_GROUP_NAME = "HVAC_Labels"
LABEL_GROUP_LABEL = "HVAC Labels"
INTERNAL_GROUP_MEP_TYPE = "HVACInternalGroup"
INTERNAL_GROUP_NAME = "HVAC_Internal"
INTERNAL_GROUP_LABEL = "HVAC Internal"
LOG_PREFIX = "[MEP-HVAC][Project] "
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


def _clamp(value, min_value, max_value):
    try:
        value_f = float(value)
    except Exception:
        value_f = float(min_value)
    return max(float(min_value), min(float(max_value), value_f))


def _normalize_text(value):
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
    return text


def _location_microclimate_bonus(location):
    """Return regional microclimate bonus in BTU/h*m2."""

    text = _normalize_text(location)
    if not text:
        return 0.0

    # Regional calibration for CR coastal/hot zones.
    if "la cruz" in text:
        return 210.0
    if "liberia" in text:
        return 170.0
    if "guanacaste" in text:
        return 140.0
    if "puntarenas" in text:
        return 120.0
    if "limon" in text:
        return 100.0
    if any(token in text for token in ("costa", "playa", "litoral", "coastal")):
        return 90.0
    return 0.0


def _is_group(obj):
    type_id = str(getattr(obj, "TypeId", "") or "")
    if type_id.startswith("App::DocumentObjectGroup"):
        return True
    return hasattr(obj, "Group") and hasattr(obj, "addObject")


def _mep_type(obj):
    if obj is None:
        return ""
    try:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
            return str(getattr(obj, "MEPType", "") or "")
    except Exception:
        return ""
    return ""


def _ensure_root_group_marker(group_obj):
    if group_obj is None or not hasattr(group_obj, "PropertiesList"):
        return
    if "MEPType" not in group_obj.PropertiesList:
        group_obj.addProperty(
            "App::PropertyString",
            "MEPType",
            "MEP",
            "Internal marker for HVAC root group",
        )
    if str(getattr(group_obj, "MEPType", "")) != ROOT_GROUP_MEP_TYPE:
        group_obj.MEPType = ROOT_GROUP_MEP_TYPE
    if getattr(group_obj, "Label", "") != ROOT_GROUP_LABEL:
        group_obj.Label = ROOT_GROUP_LABEL


def _ensure_label_group_marker(group_obj):
    if group_obj is None or not hasattr(group_obj, "PropertiesList"):
        return
    if "MEPType" not in group_obj.PropertiesList:
        group_obj.addProperty(
            "App::PropertyString",
            "MEPType",
            "MEP",
            "Internal marker for HVAC labels group",
        )
    if str(getattr(group_obj, "MEPType", "")) != LABEL_GROUP_MEP_TYPE:
        group_obj.MEPType = LABEL_GROUP_MEP_TYPE
    if getattr(group_obj, "Label", "") != LABEL_GROUP_LABEL:
        group_obj.Label = LABEL_GROUP_LABEL


def _ensure_spaces_group_marker(group_obj):
    if group_obj is None or not hasattr(group_obj, "PropertiesList"):
        return
    if "MEPType" not in group_obj.PropertiesList:
        group_obj.addProperty(
            "App::PropertyString",
            "MEPType",
            "MEP",
            "Internal marker for HVAC spaces group",
        )
    if str(getattr(group_obj, "MEPType", "")) != SPACES_GROUP_MEP_TYPE:
        group_obj.MEPType = SPACES_GROUP_MEP_TYPE
    if getattr(group_obj, "Label", "") != SPACES_GROUP_LABEL:
        group_obj.Label = SPACES_GROUP_LABEL


def _ensure_equipment_group_marker(group_obj):
    if group_obj is None or not hasattr(group_obj, "PropertiesList"):
        return
    if "MEPType" not in group_obj.PropertiesList:
        group_obj.addProperty(
            "App::PropertyString",
            "MEPType",
            "MEP",
            "Internal marker for HVAC equipment group",
        )
    if str(getattr(group_obj, "MEPType", "")) != EQUIPMENT_GROUP_MEP_TYPE:
        group_obj.MEPType = EQUIPMENT_GROUP_MEP_TYPE
    if getattr(group_obj, "Label", "") != EQUIPMENT_GROUP_LABEL:
        group_obj.Label = EQUIPMENT_GROUP_LABEL


def _ensure_internal_group_marker(group_obj):
    if group_obj is None or not hasattr(group_obj, "PropertiesList"):
        return
    if "MEPType" not in group_obj.PropertiesList:
        group_obj.addProperty(
            "App::PropertyString",
            "MEPType",
            "MEP",
            "Internal marker for HVAC internal objects group",
        )
    if str(getattr(group_obj, "MEPType", "")) != INTERNAL_GROUP_MEP_TYPE:
        group_obj.MEPType = INTERNAL_GROUP_MEP_TYPE
    if getattr(group_obj, "Label", "") != INTERNAL_GROUP_LABEL:
        group_obj.Label = INTERNAL_GROUP_LABEL


def _set_group_tree_visibility(group_obj, show_in_tree=True):
    if group_obj is None:
        return
    vobj = getattr(group_obj, "ViewObject", None)
    if vobj is None:
        return
    try:
        if hasattr(vobj, "ShowInTree"):
            vobj.ShowInTree = bool(show_in_tree)
    except Exception:
        pass


def _set_aux_object_tree_hidden(obj):
    if obj is None:
        return
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return
    try:
        if hasattr(vobj, "ShowInTree"):
            vobj.ShowInTree = False
    except Exception:
        pass


def _detach_from_hvac_subgroups(root_group, obj, keep_group=None):
    if root_group is None or obj is None:
        return
    for child in list(getattr(root_group, "Group", []) or []):
        if not _is_group(child):
            continue
        if keep_group is not None and child == keep_group:
            continue
        try:
            children = list(getattr(child, "Group", []) or [])
            if obj in children:
                child.removeObject(obj)
        except Exception:
            continue


def _remove_object_from_group(group_obj, obj):
    if group_obj is None or obj is None:
        return False
    removed = False
    doc = getattr(group_obj, "Document", None)
    obj_name = str(getattr(obj, "Name", "") or "")
    obj_by_name = None
    if doc is not None and obj_name:
        try:
            obj_by_name = doc.getObject(obj_name)
        except Exception:
            obj_by_name = None
    try:
        for _ in range(4):
            children = list(getattr(group_obj, "Group", []) or [])
            if obj not in children:
                if obj_by_name is None or obj_by_name not in children:
                    break
            try:
                group_obj.removeObject(obj)
                removed = True
            except Exception:
                if obj_by_name is not None:
                    group_obj.removeObject(obj_by_name)
                    removed = True
                else:
                    break
    except Exception:
        pass
    return removed


def _is_label_like(obj):
    if obj is None:
        return False
    mep = _mep_type(obj)
    if mep in {"HVACLabel", "HVACEquipmentInfo2D", "HVACCondenserInfo2D"}:
        return True
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    if (
        name.startswith("HVAC_Label")
        or name.startswith("HVAC_EvapInfo2D")
        or name.startswith("HVAC_CondInfo2D")
        or label.startswith("HVAC_Label")
        or label.startswith("HVAC_INFO2D_")
        or label.startswith("HVAC_INFO2D_COND_")
    ):
        return True
    props = list(getattr(obj, "PropertiesList", []) or [])
    type_id = str(getattr(obj, "TypeId", "") or "")
    if "Text" in type_id:
        if "Space" in props:
            return True
        if "EquipmentName" in props or "CondenserName" in props:
            return True
    if "Space" in props and "Text" in type_id:
        return True
    return False


def _is_internal_like(obj):
    if obj is None:
        return False
    mep = _mep_type(obj)
    if mep in {"HVACPort", "HVACEvaporatorMaster", "HVACCondenserMaster"}:
        return True
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    if (
        name.startswith("SYM2D_")
        or label.startswith("SYM2D_")
        or name.startswith("HVAC_EvapMaster_")
        or name.startswith("HVAC_CondMaster_")
        or label.startswith("MASTER_COND_")
    ):
        return True
    return False


def _is_space_like(obj):
    if obj is None:
        return False
    mep = _mep_type(obj)
    if mep == "HVACSpace":
        return True
    props = getattr(obj, "PropertiesList", [])
    if ("AreaObject" in props and "CoolingLoadBTU" in props) or ("BaseSpace" in props and "CoolingLoadBTU" in props):
        return True
    name = str(getattr(obj, "Name", "") or "")
    if name.startswith("HVAC_") and "BaseSpace" in props and "Area" in props:
        return True
    return False


def _is_equipment_like(obj):
    if obj is None:
        return False
    mep = _mep_type(obj)
    if mep in {"HVACEquipment", "HVACCondenser", "HVACRoute", "HVACEquipment2D", "HVACCondenser2D"}:
        return True
    props = getattr(obj, "PropertiesList", [])
    if "Model" in props and "CapacityBTU" in props and "Space" in props:
        return True
    if "ConnectedUnits" in props and "CoveragePct" in props:
        return True
    if "RouteType" in props and ("StartPort" in props or "EndPort" in props):
        return True
    name = str(getattr(obj, "Name", "") or "")
    if name.startswith("HVAC_Evaporator") or name.startswith("HVAC_Condenser") or name.startswith("HVAC_Route"):
        return True
    return False


def _is_project_like(obj):
    if obj is None:
        return False
    if _mep_type(obj) == MEP_TYPE:
        return True
    return str(getattr(obj, "Name", "") or "").startswith("HVAC_Project")


def _is_hvac_object_like(obj):
    if obj is None:
        return False
    mep = _mep_type(obj)
    if mep.startswith("HVAC") and mep not in {
        ROOT_GROUP_MEP_TYPE,
        SPACES_GROUP_MEP_TYPE,
        EQUIPMENT_GROUP_MEP_TYPE,
        LABEL_GROUP_MEP_TYPE,
        INTERNAL_GROUP_MEP_TYPE,
    }:
        return True
    if _is_space_like(obj) or _is_equipment_like(obj) or _is_label_like(obj) or _is_project_like(obj):
        return True
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    # Conservative legacy fallback: do not accept generic "HVAC " labels
    # (e.g. imported CAD like "HVAC Externo.ipt"). Only keep known HVAC families.
    known_name_prefixes = (
        "HVAC_Project",
        "HVAC_Space",
        "HVAC_Label",
        "HVAC_EvapInfo2D",
        "HVAC_CondInfo2D",
        "HVAC_Evaporator",
        "HVAC_Condenser",
        "HVAC_Route",
        "EVAP_",
    )
    known_label_prefixes = (
        "HVAC_Project",
        "HVAC_Space",
        "HVAC_Label",
        "HVAC_INFO2D_",
        "HVAC_INFO2D_COND_",
        "EVAP_",
    )
    return name.startswith(known_name_prefixes) or label.startswith(known_label_prefixes)


def _cleanup_hvac_groups(root_group, spaces_group, equipment_group, label_group, internal_group):
    if root_group is None:
        return 0
    cleaned = 0

    # Root should keep only HVAC project-like objects and managed HVAC subgroups.
    for child in list(getattr(root_group, "Group", []) or []):
        if child is None:
            continue
        if _is_group(child):
            continue
        if _is_project_like(child):
            continue
        if _is_hvac_object_like(child):
            # Keep generic HVAC-like object only if it does not fit a subgroup class.
            if not (_is_space_like(child) or _is_equipment_like(child) or _is_label_like(child) or _is_internal_like(child)):
                continue
        try:
            root_group.removeObject(child)
            cleaned += 1
        except Exception:
            continue

    group_rules = (
        (spaces_group, _is_space_like),
        (equipment_group, _is_equipment_like),
        (label_group, _is_label_like),
        (internal_group, _is_internal_like),
    )
    for grp, predicate in group_rules:
        if grp is None:
            continue
        for child in list(getattr(grp, "Group", []) or []):
            if child is None or _is_group(child):
                continue
            if predicate(child):
                continue
            try:
                grp.removeObject(child)
                cleaned += 1
            except Exception:
                continue

    return cleaned


def find_root_groups(doc):
    if doc is None:
        return []
    groups = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_group(obj):
            continue
        mep_type = ""
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
            mep_type = str(getattr(obj, "MEPType", ""))
        if mep_type == ROOT_GROUP_MEP_TYPE:
            groups.append(obj)
            continue

        name_norm = _normalize_text(getattr(obj, "Name", ""))
        label_norm = _normalize_text(getattr(obj, "Label", ""))
        if name_norm == _normalize_text(ROOT_GROUP_NAME) or label_norm in {
            _normalize_text(ROOT_GROUP_LABEL),
            "hvac ventilation",
        }:
            groups.append(obj)
    return groups


def ensure_hvac_label_group(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return None
    root = ensure_hvac_root_group(doc)
    if root is None:
        return None

    for child in list(getattr(root, "Group", []) or []):
        if not _is_group(child):
            continue
        marker = _mep_type(child)
        if marker == LABEL_GROUP_MEP_TYPE:
            _ensure_label_group_marker(child)
            return child
        child_name = _normalize_text(getattr(child, "Name", ""))
        child_label = _normalize_text(getattr(child, "Label", ""))
        if child_name == _normalize_text(LABEL_GROUP_NAME) or child_label == _normalize_text(LABEL_GROUP_LABEL):
            _ensure_label_group_marker(child)
            return child

    # Reuse existing label group found at document root (legacy state), then attach to HVAC root.
    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_group(obj):
            continue
        marker = _mep_type(obj)
        obj_name = _normalize_text(getattr(obj, "Name", ""))
        obj_label = _normalize_text(getattr(obj, "Label", ""))
        if marker == LABEL_GROUP_MEP_TYPE or obj_name == _normalize_text(LABEL_GROUP_NAME) or obj_label == _normalize_text(
            LABEL_GROUP_LABEL
        ):
            _ensure_label_group_marker(obj)
            _set_group_tree_visibility(obj, show_in_tree=True)
            try:
                root_children = list(getattr(root, "Group", []) or [])
                if obj not in root_children:
                    root.addObject(obj)
            except Exception:
                pass
            return obj

    group = doc.addObject("App::DocumentObjectGroup", LABEL_GROUP_NAME)
    _ensure_label_group_marker(group)
    _set_group_tree_visibility(group, show_in_tree=True)
    try:
        root.addObject(group)
    except Exception:
        pass
    return group


def ensure_hvac_internal_group(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return None
    root = ensure_hvac_root_group(doc)
    if root is None:
        return None

    for child in list(getattr(root, "Group", []) or []):
        if not _is_group(child):
            continue
        marker = _mep_type(child)
        if marker == INTERNAL_GROUP_MEP_TYPE:
            _ensure_internal_group_marker(child)
            _set_group_tree_visibility(child, show_in_tree=False)
            return child
        child_name = _normalize_text(getattr(child, "Name", ""))
        child_label = _normalize_text(getattr(child, "Label", ""))
        if child_name == _normalize_text(INTERNAL_GROUP_NAME) or child_label == _normalize_text(INTERNAL_GROUP_LABEL):
            _ensure_internal_group_marker(child)
            _set_group_tree_visibility(child, show_in_tree=False)
            return child

    # Reuse existing internal group found at document root (legacy state), then attach to HVAC root.
    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_group(obj):
            continue
        marker = _mep_type(obj)
        obj_name = _normalize_text(getattr(obj, "Name", ""))
        obj_label = _normalize_text(getattr(obj, "Label", ""))
        if marker == INTERNAL_GROUP_MEP_TYPE or obj_name == _normalize_text(INTERNAL_GROUP_NAME) or obj_label == _normalize_text(
            INTERNAL_GROUP_LABEL
        ):
            _ensure_internal_group_marker(obj)
            _set_group_tree_visibility(obj, show_in_tree=False)
            try:
                root_children = list(getattr(root, "Group", []) or [])
                if obj not in root_children:
                    root.addObject(obj)
            except Exception:
                pass
            return obj

    group = doc.addObject("App::DocumentObjectGroup", INTERNAL_GROUP_NAME)
    _ensure_internal_group_marker(group)
    _set_group_tree_visibility(group, show_in_tree=False)
    try:
        root.addObject(group)
    except Exception:
        pass
    return group


def ensure_hvac_spaces_group(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return None
    root = ensure_hvac_root_group(doc)
    if root is None:
        return None

    for child in list(getattr(root, "Group", []) or []):
        if not _is_group(child):
            continue
        marker = _mep_type(child)
        if marker == SPACES_GROUP_MEP_TYPE:
            _ensure_spaces_group_marker(child)
            _set_group_tree_visibility(child, show_in_tree=True)
            return child
        child_name = _normalize_text(getattr(child, "Name", ""))
        child_label = _normalize_text(getattr(child, "Label", ""))
        if child_name == _normalize_text(SPACES_GROUP_NAME) or child_label == _normalize_text(SPACES_GROUP_LABEL):
            _ensure_spaces_group_marker(child)
            _set_group_tree_visibility(child, show_in_tree=True)
            return child

    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_group(obj):
            continue
        marker = _mep_type(obj)
        obj_name = _normalize_text(getattr(obj, "Name", ""))
        obj_label = _normalize_text(getattr(obj, "Label", ""))
        if marker == SPACES_GROUP_MEP_TYPE or obj_name == _normalize_text(SPACES_GROUP_NAME) or obj_label == _normalize_text(
            SPACES_GROUP_LABEL
        ):
            _ensure_spaces_group_marker(obj)
            _set_group_tree_visibility(obj, show_in_tree=True)
            try:
                root_children = list(getattr(root, "Group", []) or [])
                if obj not in root_children:
                    root.addObject(obj)
            except Exception:
                pass
            return obj

    group = doc.addObject("App::DocumentObjectGroup", SPACES_GROUP_NAME)
    _ensure_spaces_group_marker(group)
    _set_group_tree_visibility(group, show_in_tree=True)
    try:
        root.addObject(group)
    except Exception:
        pass
    return group


def ensure_hvac_equipment_group(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return None
    root = ensure_hvac_root_group(doc)
    if root is None:
        return None

    for child in list(getattr(root, "Group", []) or []):
        if not _is_group(child):
            continue
        marker = _mep_type(child)
        if marker == EQUIPMENT_GROUP_MEP_TYPE:
            _ensure_equipment_group_marker(child)
            _set_group_tree_visibility(child, show_in_tree=True)
            return child
        child_name = _normalize_text(getattr(child, "Name", ""))
        child_label = _normalize_text(getattr(child, "Label", ""))
        if child_name == _normalize_text(EQUIPMENT_GROUP_NAME) or child_label == _normalize_text(EQUIPMENT_GROUP_LABEL):
            _ensure_equipment_group_marker(child)
            _set_group_tree_visibility(child, show_in_tree=True)
            return child

    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_group(obj):
            continue
        marker = _mep_type(obj)
        obj_name = _normalize_text(getattr(obj, "Name", ""))
        obj_label = _normalize_text(getattr(obj, "Label", ""))
        if marker == EQUIPMENT_GROUP_MEP_TYPE or obj_name == _normalize_text(EQUIPMENT_GROUP_NAME) or obj_label == _normalize_text(
            EQUIPMENT_GROUP_LABEL
        ):
            _ensure_equipment_group_marker(obj)
            _set_group_tree_visibility(obj, show_in_tree=True)
            try:
                root_children = list(getattr(root, "Group", []) or [])
                if obj not in root_children:
                    root.addObject(obj)
            except Exception:
                pass
            return obj

    group = doc.addObject("App::DocumentObjectGroup", EQUIPMENT_GROUP_NAME)
    _ensure_equipment_group_marker(group)
    _set_group_tree_visibility(group, show_in_tree=True)
    try:
        root.addObject(group)
    except Exception:
        pass
    return group


def ensure_hvac_root_group(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return None

    groups = find_root_groups(doc)
    if groups:
        group = groups[0]
        _ensure_root_group_marker(group)
        return group

    group = doc.addObject("App::DocumentObjectGroup", ROOT_GROUP_NAME)
    _ensure_root_group_marker(group)
    log("HVAC root group created: {0}".format(group.Name))
    return group


def add_object_to_hvac_group(doc, obj):
    if doc is None or obj is None:
        return None
    root_group = ensure_hvac_root_group(doc)
    if root_group is None:
        return None
    if obj == root_group:
        return root_group
    if _is_group(obj):
        return root_group

    target_group = root_group
    if _is_label_like(obj):
        label_group = ensure_hvac_label_group(doc)
        if label_group is not None:
            target_group = label_group
    elif _is_internal_like(obj):
        internal_group = ensure_hvac_internal_group(doc)
        if internal_group is not None:
            target_group = internal_group
    elif _is_space_like(obj):
        spaces_group = ensure_hvac_spaces_group(doc)
        if spaces_group is not None:
            target_group = spaces_group
    elif _is_equipment_like(obj):
        equipment_group = ensure_hvac_equipment_group(doc)
        if equipment_group is not None:
            target_group = equipment_group

    try:
        children = list(getattr(target_group, "Group", []) or [])
        if obj not in children:
            target_group.addObject(obj)
    except Exception:
        pass
    if target_group != root_group:
        _remove_object_from_group(root_group, obj)

        # Defensive fallback: some Draft text objects may fail to move
        # unless detached first from root/other groups.
        try:
            target_children = list(getattr(target_group, "Group", []) or [])
        except Exception:
            target_children = []
        if obj not in target_children:
            try:
                _detach_from_hvac_subgroups(root_group, obj, keep_group=None)
            except Exception:
                pass
            _remove_object_from_group(root_group, obj)
            try:
                target_group.addObject(obj)
            except Exception:
                pass

    _detach_from_hvac_subgroups(root_group, obj, keep_group=target_group if target_group is not root_group else None)
    if target_group != root_group:
        _remove_object_from_group(root_group, obj)

    if target_group != root_group:
        try:
            target_children = list(getattr(target_group, "Group", []) or [])
            if obj not in target_children:
                target_group.addObject(obj)
        except Exception:
            pass

    if _is_internal_like(obj):
        _set_aux_object_tree_hidden(obj)

    if _is_label_like(obj):
        try:
            target_children = list(getattr(target_group, "Group", []) or [])
            root_children = list(getattr(root_group, "Group", []) or [])
            in_target = obj in target_children
            in_root = obj in root_children
            if target_group != root_group and (not in_target or in_root):
                log(
                    "Route warning etiqueta: obj={0} mep={1} in_target={2} in_root={3} target={4}".format(
                        str(getattr(obj, "Name", "") or "?"),
                        str(_mep_type(obj) or ""),
                        int(bool(in_target)),
                        int(bool(in_root)),
                        str(getattr(target_group, "Name", "") or "?"),
                    )
                )
        except Exception:
            pass
    return target_group


def organize_hvac_objects(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    group = ensure_hvac_root_group(doc)
    spaces_group = ensure_hvac_spaces_group(doc)
    equipment_group = ensure_hvac_equipment_group(doc)
    label_group = ensure_hvac_label_group(doc)
    internal_group = ensure_hvac_internal_group(doc)
    if group is None:
        return 0

    moved = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if obj == group:
            continue
        if _is_group(obj):
            continue
        if not _is_hvac_object_like(obj):
            continue

        target_group = group
        if _is_project_like(obj):
            target_group = group
        elif _is_label_like(obj) and label_group is not None:
            target_group = label_group
        elif _is_internal_like(obj) and internal_group is not None:
            target_group = internal_group
        elif _is_space_like(obj) and spaces_group is not None:
            target_group = spaces_group
        elif _is_equipment_like(obj) and equipment_group is not None:
            target_group = equipment_group

        before = list(getattr(target_group, "Group", []) or [])
        try:
            if obj not in before:
                target_group.addObject(obj)
                moved += 1
            if target_group != group:
                _remove_object_from_group(group, obj)
            _detach_from_hvac_subgroups(group, obj, keep_group=target_group if target_group is not group else None)
            if target_group != group:
                _remove_object_from_group(group, obj)
            if _is_internal_like(obj):
                _set_aux_object_tree_hidden(obj)
        except Exception:
            continue

    cleaned = _cleanup_hvac_groups(group, spaces_group, equipment_group, label_group, internal_group)
    if cleaned > 0:
        log("HVAC group cleanup aplicado: removidos={0}".format(cleaned))

    if moved > 0:
        log("HVAC objects organized into root group: {0}".format(moved))
    return moved + cleaned


def toggle_hvac_visibility(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return False

    ensure_hvac_root_group(doc)
    organize_hvac_objects(doc)

    candidates = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if _is_group(obj):
            continue
        if not _is_hvac_object_like(obj):
            continue
        if _is_internal_like(obj):
            continue
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            continue
        candidates.append(obj)

    if not candidates:
        log("No hay objetos HVAC para mostrar/ocultar")
        return False

    visible_any = False
    for obj in candidates:
        if bool(getattr(obj.ViewObject, "Visibility", False)):
            visible_any = True
            break
    target_visibility = not visible_any

    for obj in candidates:
        try:
            obj.ViewObject.Visibility = target_visibility
        except Exception:
            continue

    state = "visibles" if target_visibility else "ocultos"
    log("Objetos HVAC {0}: {1}".format(state, len(candidates)))
    return target_visibility


def ensure_project_properties(obj):
    """Create all required HVAC project properties."""

    added_location = False
    added_altitude = False
    added_outdoor = False
    added_humidity = False
    added_outdoor_humidity = False
    added_indoor_humidity = False
    added_indoor = False
    added_base_factor = False
    added_factor = False
    added_offset = False
    added_bonus = False

    if "MEPType" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyString",
            "MEPType",
            "MEP",
            "Internal marker for MEP HVAC objects",
        )
    if str(getattr(obj, "MEPType", "")) != MEP_TYPE:
        obj.MEPType = MEP_TYPE

    if "Location" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "Location", "HVAC Project", tr("project.prop.location"))
        added_location = True
    if "Altitude" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat", "Altitude", "HVAC Project", tr("project.prop.altitude")
        )
        added_altitude = True
    if "OutdoorTemp" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat", "OutdoorTemp", "HVAC Project", tr("project.prop.outdoor_temp")
        )
        added_outdoor = True
    if "Humidity" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Humidity", "HVAC Project", tr("project.prop.humidity"))
        added_humidity = True
    if "OutdoorHumidity" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "OutdoorHumidity",
            "HVAC Project",
            "Outdoor relative humidity (%)",
        )
        added_outdoor_humidity = True
    if "IndoorHumidity" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "IndoorHumidity",
            "HVAC Project",
            "Indoor relative humidity (%)",
        )
        added_indoor_humidity = True
    if "IndoorTemp" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat", "IndoorTemp", "HVAC Project", tr("project.prop.indoor_temp")
        )
        added_indoor = True
    if "BaseFactor" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "BaseFactor",
            "HVAC Project",
            "Base cooling factor (BTU/h*m2)",
        )
        added_base_factor = True
    if "ClimateFactor" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "ClimateFactor",
            "HVAC Project",
            tr("project.prop.climate_factor"),
        )
        added_factor = True
    if "ClimateOffset" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "ClimateOffset",
            "HVAC Project",
            tr("project.prop.climate_offset"),
        )
        added_offset = True
    if "RegionalBonus" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "RegionalBonus",
            "HVAC Project",
            tr("project.prop.regional_bonus"),
        )
        added_bonus = True

    if added_location:
        obj.Location = "CR"
    if added_altitude:
        obj.Altitude = 0.0
    if added_outdoor:
        obj.OutdoorTemp = 30.0
    if added_humidity:
        obj.Humidity = 100.0
    if added_outdoor_humidity:
        obj.OutdoorHumidity = _to_float(getattr(obj, "Humidity", 100.0), 100.0)
    if added_indoor_humidity:
        obj.IndoorHumidity = 55.0
    if added_indoor:
        obj.IndoorTemp = 22.0
    if added_base_factor:
        obj.BaseFactor = 600.0
    if added_factor:
        obj.ClimateFactor = 400.0
    if added_offset:
        obj.ClimateOffset = 0.0
    if added_bonus:
        obj.RegionalBonus = 0.0


def compute_climate_factor(project_obj):
    """Compute climate factor (BTU/h*m2) from max outdoor temp and altitude."""

    # Inputs aligned with climate_factor_btu macro convention.
    altitude = max(0.0, _to_float(project_obj.Altitude, 0.0))
    temp_max = _to_float(project_obj.OutdoorTemp, 30.0)
    humidity_out = _clamp(
        _to_float(
            getattr(project_obj, "OutdoorHumidity", getattr(project_obj, "Humidity", 100.0)),
            100.0,
        ),
        20.0,
        100.0,
    )
    humidity_in = _clamp(_to_float(getattr(project_obj, "IndoorHumidity", 55.0), 55.0), 20.0, 100.0)
    factor_base = max(0.0, _to_float(getattr(project_obj, "BaseFactor", 600.0), 600.0))
    location = str(getattr(project_obj, "Location", "") or "")
    regional_bonus = _location_microclimate_bonus(location)
    manual_offset = _to_float(getattr(project_obj, "ClimateOffset", 0.0), 0.0)

    if "RegionalBonus" in project_obj.PropertiesList:
        old_bonus = _to_float(getattr(project_obj, "RegionalBonus", 0.0), 0.0)
        if abs(old_bonus - regional_bonus) > 0.001:
            project_obj.RegionalBonus = regional_bonus

    # Apply clamp on thermal component first, then altitude attenuation.
    # This keeps the expected monotonic behavior: higher altitude -> lower factor.
    thermal_component_raw = (temp_max - 22.0) / 8.0
    thermal_component = _clamp(thermal_component_raw, 0.7, 1.5)
    altitude_component = max(0.0, 1.0 - 0.06 * (altitude / 1000.0))

    # Humidity correction:
    #  - outdoor humidity above indoor humidity increases latent load
    #  - outdoor humidity below indoor humidity decreases latent load
    humidity_delta = humidity_out - humidity_in
    humidity_component = _clamp(1.0 + (humidity_delta / 100.0) * 0.5, 0.8, 1.2)

    climate_raw = thermal_component * altitude_component * humidity_component
    climate_multiplier = _clamp(climate_raw, 0.7, 1.5)

    # Preserve existing regional calibration and manual offset on top of macro base formula.
    factor = (factor_base * climate_multiplier) + regional_bonus + manual_offset
    factor = max(0.0, factor)

    w_m2 = factor / 3.412
    log(
        "Clima rapido: temp_max={0} C, altitud={1} m, hr_ext={2} %, hr_int={3} %, term_temp={4}, term_alt={5}, term_hum={6}, f_raw={7}, f_clima={8}, factor={9} BTU/h*m2, {10} W/m2".format(
            round(temp_max, 2),
            round(altitude, 2),
            round(humidity_out, 2),
            round(humidity_in, 2),
            round(thermal_component, 3),
            round(altitude_component, 3),
            round(humidity_component, 3),
            round(climate_raw, 3),
            round(climate_multiplier, 3),
            round(factor, 2),
            round(w_m2, 2),
        )
    )
    return round(factor, 2)


def recalculate_project(project_obj):
    """Refresh project factor."""

    if project_obj is None:
        return
    factor = compute_climate_factor(project_obj)
    old_factor = _to_float(project_obj.ClimateFactor, 0.0)
    if abs(old_factor - factor) > 0.001:
        project_obj.ClimateFactor = factor
        log(tr("project.log.factor", factor=factor))


def find_projects(doc):
    if doc is None:
        return []
    projects = []
    for obj in doc.Objects:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
            if str(obj.MEPType) == MEP_TYPE:
                projects.append(obj)
    return projects


def get_or_create_project(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log(tr("project.log.no_active_doc"))
        return None

    ensure_hvac_root_group(doc)

    projects = find_projects(doc)
    if projects:
        add_object_to_hvac_group(doc, projects[0])
        log(tr("project.log.use_existing", name=projects[0].Name))
        return projects[0]

    obj = doc.addObject("App::FeaturePython", "HVAC_Project")
    HVACProjectProxy(obj)
    HVACProjectViewProvider(obj.ViewObject)
    ensure_project_properties(obj)
    recalculate_project(obj)
    add_object_to_hvac_group(doc, obj)
    organize_hvac_objects(doc)
    log(tr("project.log.created", name=obj.Name))
    return obj


class HVACProjectProxy:
    """FeaturePython proxy for HVAC project."""

    def __init__(self, obj):
        obj.Proxy = self
        self._busy = True
        try:
            ensure_project_properties(obj)
        finally:
            self._busy = False

    def onChanged(self, obj, prop):  # noqa: N802
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        if prop in {"Humidity", "OutdoorHumidity"}:
            self._busy = True
            try:
                if prop == "Humidity" and "OutdoorHumidity" in obj.PropertiesList:
                    current = _to_float(getattr(obj, "Humidity", 100.0), 100.0)
                    if abs(_to_float(getattr(obj, "OutdoorHumidity", 100.0), 100.0) - current) > 0.001:
                        obj.OutdoorHumidity = current
                elif prop == "OutdoorHumidity" and "Humidity" in obj.PropertiesList:
                    current = _to_float(getattr(obj, "OutdoorHumidity", 100.0), 100.0)
                    if abs(_to_float(getattr(obj, "Humidity", 100.0), 100.0) - current) > 0.001:
                        obj.Humidity = current
            finally:
                self._busy = False
        if prop in {
            "Location",
            "Altitude",
            "OutdoorTemp",
            "Humidity",
            "OutdoorHumidity",
            "IndoorHumidity",
            "IndoorTemp",
            "BaseFactor",
            "ClimateOffset",
        }:
            self._busy = True
            try:
                recalculate_project(obj)
            finally:
                self._busy = False

    def execute(self, obj):
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        self._busy = True
        try:
            recalculate_project(obj)
        finally:
            self._busy = False


class HVACProjectViewProvider:
    """View provider for HVAC project."""

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
