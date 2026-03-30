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


def _is_label_like(obj):
    if obj is None:
        return False
    if _mep_type(obj) == "HVACLabel":
        return True
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    if name.startswith("HVAC_Label") or label.startswith("HVAC_Label"):
        return True
    if "Space" in getattr(obj, "PropertiesList", []) and "Text" in str(getattr(obj, "TypeId", "") or ""):
        return True
    return False


def _is_internal_like(obj):
    if obj is None:
        return False
    mep = _mep_type(obj)
    if mep in {"HVACPort"}:
        return True
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    if name.startswith("SYM2D_") or label.startswith("SYM2D_"):
        return True
    return False


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

    group = doc.addObject("App::DocumentObjectGroup", INTERNAL_GROUP_NAME)
    _ensure_internal_group_marker(group)
    _set_group_tree_visibility(group, show_in_tree=False)
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

    try:
        children = list(getattr(target_group, "Group", []) or [])
        if obj not in children:
            target_group.addObject(obj)
    except Exception:
        pass
    if target_group != root_group:
        try:
            root_children = list(getattr(root_group, "Group", []) or [])
            if obj in root_children:
                root_group.removeObject(obj)
        except Exception:
            pass
    if target_group is not root_group:
        _set_aux_object_tree_hidden(obj)
    return target_group


def organize_hvac_objects(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    group = ensure_hvac_root_group(doc)
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
        include = False
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
            mep_type = str(getattr(obj, "MEPType", "") or "")
            if mep_type == ROOT_GROUP_MEP_TYPE:
                continue
            if mep_type.startswith("HVAC"):
                include = True
        if not include:
            name = str(getattr(obj, "Name", "") or "")
            label = str(getattr(obj, "Label", "") or "")
            if name.startswith("HVAC_") or label.startswith("HVAC "):
                include = True
        if not include:
            continue

        target_group = group
        if _is_label_like(obj) and label_group is not None:
            target_group = label_group
        elif _is_internal_like(obj) and internal_group is not None:
            target_group = internal_group

        before = list(getattr(target_group, "Group", []) or [])
        try:
            if obj not in before:
                target_group.addObject(obj)
                moved += 1
            if target_group != group:
                root_before = list(getattr(group, "Group", []) or [])
                if obj in root_before:
                    group.removeObject(obj)
                _set_aux_object_tree_hidden(obj)
        except Exception:
            continue

    if moved > 0:
        log("HVAC objects organized into root group: {0}".format(moved))
    return moved


def ensure_project_properties(obj):
    """Create all required HVAC project properties."""

    added_location = False
    added_altitude = False
    added_outdoor = False
    added_humidity = False
    added_indoor = False
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
    if "IndoorTemp" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat", "IndoorTemp", "HVAC Project", tr("project.prop.indoor_temp")
        )
        added_indoor = True
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
    if added_indoor:
        obj.IndoorTemp = 22.0
    if added_factor:
        obj.ClimateFactor = 400.0
    if added_offset:
        obj.ClimateOffset = 0.0
    if added_bonus:
        obj.RegionalBonus = 0.0


def compute_climate_factor(project_obj):
    """Compute climate factor (BTU/h*m2) from project environment values."""

    altitude = max(0.0, _to_float(project_obj.Altitude, 0.0))
    outdoor = _to_float(project_obj.OutdoorTemp, 30.0)
    indoor = _to_float(project_obj.IndoorTemp, 22.0)
    humidity = max(20.0, min(100.0, _to_float(project_obj.Humidity, 100.0)))
    delta_t = max(2.0, outdoor - indoor)
    location = str(getattr(project_obj, "Location", "") or "")
    regional_bonus = _location_microclimate_bonus(location)
    manual_offset = _to_float(getattr(project_obj, "ClimateOffset", 0.0), 0.0)

    if "RegionalBonus" in project_obj.PropertiesList:
        old_bonus = _to_float(getattr(project_obj, "RegionalBonus", 0.0), 0.0)
        if abs(old_bonus - regional_bonus) > 0.001:
            project_obj.RegionalBonus = regional_bonus

    # Conservative pre-sizing formula.
    # Altitude must decrease cooling factor (lower air density at higher altitude).
    altitude_penalty = min(140.0, altitude * 0.035)  # 35 BTU/h*m2 per 1000 m
    factor = (
        260.0
        + (delta_t * 11.0)
        + (humidity * 0.75)
        - altitude_penalty
        + regional_bonus
        + manual_offset
    )
    return round(max(220.0, factor), 2)


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
        self._busy = False
        ensure_project_properties(obj)

    def onChanged(self, obj, prop):  # noqa: N802
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        if prop in {"Location", "Altitude", "OutdoorTemp", "Humidity", "IndoorTemp", "ClimateOffset"}:
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
