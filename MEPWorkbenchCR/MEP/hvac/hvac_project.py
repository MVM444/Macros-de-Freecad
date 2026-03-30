"""HVAC project object: global climate settings and factor calculation."""

import os
import unicodedata

import FreeCAD as App

try:
    from ..i18n import tr
except Exception:
    from MEP.i18n import tr

MEP_TYPE = "HVACProject"
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

    projects = find_projects(doc)
    if projects:
        log(tr("project.log.use_existing", name=projects[0].Name))
        return projects[0]

    obj = doc.addObject("App::FeaturePython", "HVAC_Project")
    HVACProjectProxy(obj)
    HVACProjectViewProvider(obj.ViewObject)
    ensure_project_properties(obj)
    recalculate_project(obj)
    log(tr("project.log.created", name=obj.Name))
    return obj


class HVACProjectProxy:
    """FeaturePython proxy for HVAC project."""

    def __init__(self, obj):
        obj.Proxy = self
        self._busy = False
        ensure_project_properties(obj)

    def onChanged(self, obj, prop):  # noqa: N802
        if self._busy:
            return
        if prop in {"Location", "Altitude", "OutdoorTemp", "Humidity", "IndoorTemp", "ClimateOffset"}:
            self._busy = True
            try:
                recalculate_project(obj)
            finally:
                self._busy = False

    def execute(self, obj):
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
