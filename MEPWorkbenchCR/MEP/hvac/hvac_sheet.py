"""HVAC quick calculation spreadsheet output."""

import FreeCAD as App

from . import hvac_equipment
from . import hvac_project
from . import hvac_space

SHEET_NAME = "HVAC_QuickCalc"
SHEET_LABEL = "HVAC Quick Calculation"
LOG_PREFIX = "[MEP-HVAC][Sheet] "


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


def _space_capacity_and_count(doc, space_obj):
    capacity = 0.0
    count = 0
    for equipment in hvac_equipment.find_equipments(doc):
        if getattr(equipment, "Space", None) == space_obj:
            capacity += _to_float(getattr(equipment, "CapacityBTU", 0.0), 0.0)
            count += 1
    return round(capacity, 2), count


def _space_display_name(space_obj):
    base = getattr(space_obj, "BaseSpace", None)
    if base is not None and getattr(base, "Label", ""):
        return str(base.Label)
    if getattr(space_obj, "Label", ""):
        return str(space_obj.Label)
    return str(space_obj.Name)


def _find_sheet(doc):
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "TypeId", "")) != "Spreadsheet::Sheet":
            continue
        if str(getattr(obj, "Name", "")) == SHEET_NAME or str(getattr(obj, "Label", "")) == SHEET_LABEL:
            return obj
    return None


def _set(sheet, cell, value):
    try:
        sheet.set(cell, str(value))
    except Exception:
        pass


def _clear_range(sheet, max_rows=500):
    if hasattr(sheet, "clearAll"):
        try:
            sheet.clearAll()
            return
        except Exception:
            pass

    columns = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
    for row in range(1, max_rows + 1):
        for column in columns:
            _set(sheet, "{0}{1}".format(column, row), "")


def get_or_create_sheet(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return None

    sheet = _find_sheet(doc)
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", SHEET_NAME)
        sheet.Label = SHEET_LABEL
        log("Quick calculation sheet created: {0}".format(sheet.Name))

    hvac_project.add_object_to_hvac_group(doc, sheet)
    return sheet


def update_quickcalc_sheet(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return None

    sheet = get_or_create_sheet(doc)
    if sheet is None:
        return None

    _clear_range(sheet)
    headers = [
        "Space",
        "Area_m2",
        "Occupancy_People",
        "Occupancy_Activity",
        "Mode",
        "Load_BTUh",
        "Calculated_Equipment_BTUh",
        "Selected_Equipment_BTUh",
        "Selected_Model",
        "Coverage_pct",
        "Equipment_Count",
        "Base_Object",
    ]
    for idx, title in enumerate(headers):
        col = chr(ord("A") + idx)
        _set(sheet, "{0}1".format(col), title)

    row = 2
    spaces = list(hvac_space.find_spaces(doc) or [])
    spaces.sort(key=lambda s: str(getattr(s, "Label", "") or getattr(s, "Name", "")))
    for space_obj in spaces:
        area = _to_float(getattr(space_obj, "Area", 0.0), 0.0)
        try:
            occupancy = max(0, int(getattr(space_obj, "Occupancy", 0) or 0))
        except Exception:
            occupancy = 0
        default_activity = str(
            getattr(hvac_space, "DEFAULT_OCCUPANCY_ACTIVITY", "Oficina") or "Oficina"
        )
        occupancy_activity = str(
            getattr(space_obj, "OccupancyActivity", default_activity) or default_activity
        )
        mode = str(getattr(space_obj, "Mode", "Rapido"))
        load = _to_float(getattr(space_obj, "CoolingLoadBTU", 0.0), 0.0)
        installed, equipment_count = _space_capacity_and_count(doc, space_obj)
        calculated = _to_float(
            getattr(space_obj, "CalculatedEquipmentBTU", load),
            load,
        )
        selected = _to_float(
            getattr(space_obj, "SelectedEquipmentBTU", installed),
            installed,
        )
        selected_model = str(getattr(space_obj, "SelectedEquipmentModel", "") or "")
        if not selected_model:
            selected_model = " + ".join(
                str(getattr(equipment, "Model", "") or "")
                for equipment in hvac_equipment.find_equipments(doc)
                if getattr(equipment, "Space", None) == space_obj
            )
        coverage = (installed / load * 100.0) if load > 0 else 0.0
        base = getattr(space_obj, "BaseSpace", None)
        base_name = ""
        if base is not None:
            base_name = str(getattr(base, "Label", "") or getattr(base, "Name", ""))

        values = [
            _space_display_name(space_obj),
            "{0:.3f}".format(area),
            str(occupancy),
            occupancy_activity,
            mode,
            "{0:.2f}".format(load),
            "{0:.2f}".format(calculated),
            "{0:.2f}".format(selected),
            selected_model,
            "{0:.2f}".format(coverage),
            str(equipment_count),
            base_name,
        ]
        for idx, value in enumerate(values):
            col = chr(ord("A") + idx)
            _set(sheet, "{0}{1}".format(col, row), value)
        row += 1

    log("Quick calculation sheet updated with {0} space row(s)".format(max(0, row - 2)))
    return sheet
