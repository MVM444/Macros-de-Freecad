"""FreeCAD adapter for ElementDataCore and Spreadsheet_Ventanas.

Version: 0.4.0.
Fecha y hora: 2026-09-01 15:25 America/Costa_Rica.
Mantenimiento: preferir Level -> Auxiliares FA para la tabla cuando el contexto sea inequívoco.
"""

from __future__ import annotations

import math

import FreeCAD

from .element_data_core import (
    CATEGORY_WINDOWS,
    SCHEMA_VERSION,
    build_table_data,
    plan_application,
    validate_records,
)
from .bim_structure_utils import ensure_auxiliary_parent, ensure_bim_structure
from .opening_utils import (
    GENERATED_BY_WINDOWS,
    LEGACY_GENERATORS,
    create_native_window_from_axis_plan,
    is_bim_wall,
    select_best_host,
    sketch_segments,
    wall_source_segments,
)
from .project_structure import msg, set_prop


SHEET_NAME = "Spreadsheet_Ventanas"
SHEET_LABEL = "Tabla de ventanas"
TABLE_GENERATOR = "FA_WindowTable"
DEFAULT_HOST_TOLERANCE_MM = 250.0

COLUMNS = (
    ("A", "ElementID", "ElementID"),
    ("B", "SourceSketch", "SourceSketch"),
    ("C", "GeometryIndex", "GeometryIndex"),
    ("D", "CenterX", "CenterX"),
    ("E", "CenterY", "CenterY"),
    ("F", "WidthSketch", "Length"),
    ("G", "AngleDeg", "AngleDeg"),
    ("H", "Height", "Height"),
    ("I", "SillHeight", "SillHeight"),
    ("J", "Preset", "Preset"),
    ("K", "Opening", "Opening"),
    ("L", "Room", "RoomKey"),
    ("M", "Level", "LevelKey"),
    ("N", "Status", "Status"),
    ("O", "Notes", "Notes"),
    ("P", "Frame", "Frame"),
    ("Q", "Offset", "Offset"),
    ("R", "IfcType", "IfcType"),
    ("S", "SchemaVersion", "SchemaVersion"),
)


def ensure_window_table(doc):
    """Create/reuse the editable window table in the native BIM support tree when possible."""
    sheet = doc.getObject(SHEET_NAME)
    if sheet is not None and sheet.TypeId != "Spreadsheet::Sheet":
        raise RuntimeError("%s existe pero no es una Spreadsheet" % SHEET_NAME)
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", SHEET_NAME)
        sheet.Label = SHEET_LABEL
    support_parent, _level = ensure_auxiliary_parent(doc, [sheet], legacy_key="tables")
    try:
        if sheet not in list(getattr(support_parent, "Group", []) or []):
            support_parent.addObject(sheet)
    except Exception:
        pass
    _tag_sheet(sheet)
    if not _cell_text(sheet, "A1"):
        _write_headers(sheet)
    return sheet


def write_window_records(sheet, records, statuses=None):
    """Replace table cells with normalized records, preserving the Sheet object."""
    data = build_table_data(CATEGORY_WINDOWS, records)
    statuses = dict(statuses or {})
    sheet.clearAll()
    _write_headers(sheet)
    for row_number, record in enumerate(data, start=2):
        for column, _header, field in COLUMNS:
            value = statuses.get(row_number - 2, "") if field == "Status" else record.get(field)
            if value is None or value == "":
                continue
            sheet.set("%s%d" % (column, row_number), _format_cell_value(field, value))
    _tag_sheet(sheet)
    sheet.recompute()
    return data


def read_window_records(sheet):
    """Read visible rows into JSON-compatible records."""
    last_row = _last_used_row(sheet)
    records = []
    for row in range(2, last_row + 1):
        raw = {}
        for column, _header, field in COLUMNS:
            if field == "Status":
                continue
            raw[field] = _cell_text(sheet, "%s%d" % (column, row))
        if not any(str(value or "").strip() for value in raw.values()):
            continue
        for field in ("CenterX", "CenterY", "Length", "AngleDeg", "Height", "SillHeight", "Opening", "Frame", "Offset"):
            raw[field] = _parse_number(raw.get(field))
        raw["GeometryIndex"] = _parse_int(raw.get("GeometryIndex"))
        raw["SchemaVersion"] = _parse_int(raw.get("SchemaVersion")) or SCHEMA_VERSION
        records.append(raw)
    return build_table_data(CATEGORY_WINDOWS, records)


def update_validation_statuses(sheet, report):
    """Write only the Status column after a completed read-only validation."""
    for entry in report.get("entries", []):
        sheet.set("N%d" % (int(entry["row_index"]) + 2), str(entry["status"]))
    sheet.recompute()


def geometry_records_from_sketches(sketches):
    records = []
    for sketch in _unique_objects(sketches):
        for item in sketch_segments(sketch):
            segment = item["segment"]
            dx = segment[3] - segment[0]
            dy = segment[4] - segment[1]
            records.append(
                {
                    "SourceSketch": str(sketch.Name),
                    "GeometryIndex": int(item["index"]),
                    "CenterX": (segment[0] + segment[3]) * 0.5,
                    "CenterY": (segment[1] + segment[4]) * 0.5,
                    "Length": math.hypot(dx, dy),
                    "AngleDeg": math.degrees(math.atan2(dy, dx)) % 180.0,
                }
            )
    return records


def extract_window_records(doc):
    """Extract native Arch/BIM windows without changing model geometry."""
    windows = [obj for obj in list(doc.Objects) if is_native_window(obj)]
    windows.sort(key=lambda obj: (str(getattr(obj, "Tag", "") or ""), obj.Name))
    records = []
    for index, window in enumerate(windows, start=1):
        source = getattr(window, "FA_SourceSketch", None)
        geometry_index = _property_int(window, "FA_SourceGeometryIndex")
        geometry = _geometry_for_window(window, source, geometry_index)
        host = next(iter(list(getattr(window, "Hosts", []) or [])), None)
        records.append(
            {
                "SchemaVersion": SCHEMA_VERSION,
                "ElementID": _element_id(window, index),
                "Category": CATEGORY_WINDOWS,
                "SourceSketch": str(getattr(source, "Name", "") or ""),
                "GeometryIndex": geometry_index,
                "CenterX": geometry.get("CenterX"),
                "CenterY": geometry.get("CenterY"),
                "Length": geometry.get("Length") or _quantity(window, "Width"),
                "AngleDeg": geometry.get("AngleDeg"),
                "Height": _quantity(window, "Height"),
                "SillHeight": window_sill_height(window, host=host),
                "Preset": window_preset_name(window),
                "Opening": _quantity(window, "Opening"),
                "Frame": _quantity(window, "Frame"),
                "Offset": _quantity(window, "Offset"),
                "IfcType": str(getattr(window, "IfcType", "Window") or "Window"),
                "RoomKey": str(getattr(window, "FA_RoomKey", "") or ""),
                "LevelKey": _level_key(window),
                "GeneratedBy": str(getattr(window, "FA_GeneratedBy", "") or ""),
                "Notes": str(getattr(window, "Description", "") or ""),
            }
        )
    return build_table_data(CATEGORY_WINDOWS, records)


def validate_window_records(records, sketches, tolerance=None):
    return validate_records(
        CATEGORY_WINDOWS,
        records,
        geometry_records_from_sketches(sketches),
        tolerance=tolerance,
    )


def apply_window_records(
    doc,
    target_container,
    records,
    sketches,
    walls,
    dry_run=True,
    tolerance=None,
    host_tolerance_mm=DEFAULT_HOST_TOLERANCE_MM,
):
    """Create/update only safe table rows; writes use one FreeCAD transaction."""
    sketches = _unique_objects(sketches)
    walls = [wall for wall in _unique_objects(walls) if is_bim_wall(wall)]
    geometry = geometry_records_from_sketches(sketches)
    plan = plan_application(CATEGORY_WINDOWS, records, geometry, tolerance=tolerance)
    source_map = {str(item.Name): item for item in sketches}
    segment_map = {
        (str(source.Name), int(item["index"])): item
        for source in sketches
        for item in sketch_segments(source)
    }
    wall_records = [
        {"wall": wall, "segments": [item["segment"] for item in wall_source_segments(wall)]}
        for wall in walls
    ]
    wall_records = [item for item in wall_records if item["segments"]]
    actions = []
    for item in plan["plans"]:
        geom = item["geometry"]
        source = source_map.get(str(geom["SourceSketch"]))
        axis = segment_map.get((str(geom["SourceSketch"]), int(geom["GeometryIndex"])))
        if source is None or axis is None:
            actions.append(_skipped_action(item, "NO_MATCH", "Sketch destino no disponible"))
            continue
        host_selection = select_best_host(axis["segment"], wall_records, float(host_tolerance_mm))
        if host_selection["ambiguous"]:
            actions.append(_skipped_action(item, "AMBIGUO", "Muro anfitrion ambiguo"))
            continue
        match = host_selection["match"]
        if match is None:
            actions.append(_skipped_action(item, "NO_MATCH", "Sin muro anfitrion compatible"))
            continue
        values = _window_values(item["record"], geom)
        existing = _find_generated_window(doc, source, int(axis["index"]))
        manual_conflict = _find_manual_element_id_conflict(doc, values["element_id"], existing)
        if manual_conflict is not None:
            actions.append(
                _skipped_action(
                    item,
                    "AMBIGUO",
                    "ElementID ya pertenece a una ventana manual: %s" % manual_conflict.Label,
                )
            )
            continue
        action = "KEEP" if existing is not None and _window_matches(existing, values, match["wall"]) else ("REPLACE" if existing is not None else "CREATE")
        actions.append(
            {
                "row_index": item["row_index"],
                "element_id": values["element_id"],
                "status": item["status"],
                "action": action,
                "record": item["record"],
                "source": source,
                "axis": axis,
                "match": match,
                "values": values,
                "existing": existing,
            }
        )

    report = _json_report(plan, actions, dry_run=dry_run)
    if dry_run:
        return report

    executable = [item for item in actions if item["action"] in ("CREATE", "REPLACE")]
    if not executable:
        report["dry_run"] = False
        return report

    transaction_open = False
    created = []
    wall_volumes_before = {item["match"]["wall"]: float(item["match"]["wall"].Shape.Volume) for item in executable}
    try:
        doc.openTransaction("FA Aplicar tabla de ventanas")
        transaction_open = True
        resolved_container = target_container
        if resolved_container is None:
            resolved_container = ensure_bim_structure(doc)["level"]
        for item in executable:
            values = item["values"]
            new = create_native_window_from_axis_plan(
                doc,
                resolved_container,
                item["source"],
                item["axis"],
                item["match"],
                values["height"],
                values["sill"],
                preset=values["preset"],
                opening_percent=values["opening"],
                frame_mm=values["frame"],
                offset_mm=values["offset"],
                element_id=values["element_id"],
            )
            _apply_transfer_metadata(new, item["record"], item["existing"])
            created.append((item, new))
        doc.recompute()
        for item, new in created:
            if getattr(new, "Base", None) is None or list(getattr(new, "Hosts", []) or []) != [item["match"]["wall"]]:
                raise RuntimeError("La nueva ventana no conservo Base/Hosts")
            subvolume = new.Proxy.getSubVolume(new, host=item["match"]["wall"])
            if subvolume is None or float(subvolume.Volume) <= 1.0:
                raise RuntimeError("La nueva ventana no produce un subvolumen valido")
        for item, _new in created:
            if item["existing"] is not None:
                _remove_generated_window(doc, item["existing"])
        for wall in wall_volumes_before:
            wall.touch()
        doc.recompute()
        for wall, before in wall_volumes_before.items():
            after = float(wall.Shape.Volume)
            has_create = any(item["match"]["wall"] is wall and item["existing"] is None for item, _new in created)
            if has_create and after >= before - 1.0:
                raise RuntimeError("La ventana nueva no produjo un corte real en %s" % wall.Label)
            if not has_create and after > before + 1.0:
                raise RuntimeError("El reemplazo no conservo el corte de %s" % wall.Label)
        doc.commitTransaction()
        transaction_open = False
    except Exception:
        if transaction_open:
            doc.abortTransaction()
        raise

    report = _json_report(plan, actions, dry_run=False)
    report["created_objects"] = [new.Name for _item, new in created]
    return report


def export_table_native(sheet, filename):
    """Use FreeCAD 1.1.3's stable Sheet export (tab-separated UTF-8)."""
    sheet.exportFile(str(filename))
    return str(filename)


def import_table_native(doc, filename):
    """Import with the native Sheet API into the canonical table object."""
    sheet = ensure_window_table(doc)
    sheet.clearAll()
    sheet.importFile(str(filename))
    _tag_sheet(sheet)
    try:
        support_parent, _level = ensure_auxiliary_parent(doc, [sheet], legacy_key="tables")
        if sheet not in list(getattr(support_parent, "Group", []) or []):
            support_parent.addObject(sheet)
    except Exception:
        pass
    sheet.recompute()
    return sheet


def is_native_window(obj):
    if str(getattr(obj, "IfcType", "") or "") != "Window":
        return False
    proxy = getattr(obj, "Proxy", None)
    return str(getattr(proxy.__class__, "__module__", "") or "") == "ArchWindow"


def window_preset_name(window):
    explicit = str(getattr(window, "FA_PresetName", "") or "").strip()
    if explicit:
        return explicit
    presets = native_window_presets(include_non_windows=True)
    try:
        index = int(getattr(window, "Preset", 0)) - 1
    except Exception:
        index = -1
    return presets[index] if 0 <= index < len(presets) else ""


def native_window_presets(include_non_windows=False):
    try:
        import ArchWindowPresets

        presets = list(ArchWindowPresets.WindowPresets or [])
    except Exception:
        presets = []
    if include_non_windows:
        return presets
    return [name for name in presets if "door" not in name.lower() and name != "Opening only"]


def window_sill_height(window, host=None):
    for name in ("FA_Sill_mm", "FA_SillHeight"):
        value = _quantity(window, name)
        if value is not None:
            return max(0.0, value)
    base = getattr(window, "Base", None)
    if base is None:
        return 0.0
    try:
        base_z = float(base.getGlobalPlacement().Base.z)
    except Exception:
        base_z = float(base.Placement.Base.z)
    if host is None:
        host = next(iter(list(getattr(window, "Hosts", []) or [])), None)
    host_z = float(getattr(getattr(getattr(host, "Placement", None), "Base", None), "z", 0.0)) if host is not None else 0.0
    return max(0.0, base_z - host_z)


def _write_headers(sheet):
    for column, header, _field in COLUMNS:
        sheet.set(column + "1", header)
    sheet.setStyle("A1:S1", "bold", "add")
    for column, _header, _field in COLUMNS:
        try:
            sheet.setColumnWidth(column, 110 if column in ("A", "B", "J", "O") else 85)
        except Exception:
            pass


def _tag_sheet(sheet):
    set_prop(sheet, "App::PropertyInteger", "FA_SchemaVersion", "FacilArquitectura", "Version del esquema", SCHEMA_VERSION)
    set_prop(sheet, "App::PropertyString", "FA_Category", "FacilArquitectura", "Categoria", CATEGORY_WINDOWS)
    set_prop(sheet, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", TABLE_GENERATOR)


def _last_used_row(sheet):
    try:
        cells = dict(sheet.getNonEmptyCells() or {})
        rows = [int("".join(char for char in address if char.isdigit())) for address in cells if any(char.isdigit() for char in address)]
        if rows:
            return max(rows)
    except Exception:
        pass
    last = 1
    empty_run = 0
    for row in range(2, 10002):
        if any(_cell_text(sheet, "%s%d" % (column, row)) for column, _header, _field in COLUMNS):
            last = row
            empty_run = 0
        else:
            empty_run += 1
            if empty_run >= 25:
                break
    return last


def _cell_text(sheet, address):
    try:
        value = sheet.getContents(address)
    except Exception:
        try:
            value = sheet.get(address)
        except Exception:
            return ""
    text = str(value or "").strip()
    # Spreadsheet returns its literal-text escape apostrophe through
    # ``getContents``. Keep it out of the transferable ElementData value.
    return text[1:] if text.startswith("'") else text


def _format_cell_value(field, value):
    if field in ("CenterX", "CenterY", "Length", "AngleDeg", "Height", "SillHeight", "Opening", "Frame", "Offset"):
        return ("%.6f" % float(value)).rstrip("0").rstrip(".")
    return str(value)


def _parse_number(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        try:
            return float(FreeCAD.Units.Quantity(text).Value)
        except Exception:
            return None


def _parse_int(value):
    number = _parse_number(value)
    return None if number is None else int(number)


def _geometry_for_window(window, source, geometry_index):
    if source is not None and geometry_index is not None:
        for item in geometry_records_from_sketches([source]):
            if int(item["GeometryIndex"]) == int(geometry_index):
                return item
    width = _quantity(window, "Width") or 0.0
    base = getattr(window, "Base", None)
    if base is None:
        return {}
    try:
        placement = base.getGlobalPlacement()
    except Exception:
        placement = base.Placement
    first = placement.multVec(FreeCAD.Vector(0, 0, 0))
    second = placement.multVec(FreeCAD.Vector(width, 0, 0))
    return {
        "CenterX": (first.x + second.x) * 0.5,
        "CenterY": (first.y + second.y) * 0.5,
        "Length": width,
        "AngleDeg": math.degrees(math.atan2(second.y - first.y, second.x - first.x)) % 180.0,
    }


def _window_values(record, geometry):
    width = float(geometry["Length"])
    presets = native_window_presets()
    preset = str(record.get("Preset") or "").strip()
    if preset not in presets:
        preset = "Open 1-pane" if width < 900.0 else "Sliding 2-pane"
    return {
        "element_id": str(record.get("ElementID") or "").strip(),
        "width": width,
        "height": float(record.get("Height") if record.get("Height") is not None else 1200.0),
        "sill": float(record.get("SillHeight") if record.get("SillHeight") is not None else 900.0),
        "preset": preset,
        "opening": float(record.get("Opening") if record.get("Opening") is not None else 0.0),
        "frame": float(record.get("Frame") if record.get("Frame") is not None else 40.0),
        "offset": float(record.get("Offset") if record.get("Offset") is not None else 0.0),
    }


def _find_generated_window(doc, source, index):
    generators = {GENERATED_BY_WINDOWS} | set(LEGACY_GENERATORS["window"])
    for obj in list(doc.Objects):
        if not is_native_window(obj) or str(getattr(obj, "FA_GeneratedBy", "") or "") not in generators:
            continue
        if getattr(obj, "FA_SourceSketch", None) is not source:
            continue
        if _property_int(obj, "FA_SourceGeometryIndex") == int(index):
            return obj
    return None


def _find_manual_element_id_conflict(doc, element_id, generated_match=None):
    key = str(element_id or "").strip()
    if not key:
        return None
    generators = {GENERATED_BY_WINDOWS} | set(LEGACY_GENERATORS["window"])
    for obj in list(doc.Objects):
        if obj is generated_match or not is_native_window(obj):
            continue
        candidate = str(getattr(obj, "FA_ElementID", "") or getattr(obj, "Tag", "") or "").strip()
        if candidate != key:
            continue
        if str(getattr(obj, "FA_GeneratedBy", "") or "") not in generators:
            return obj
    return None


def _window_matches(window, values, wall):
    checks = (
        (_quantity(window, "Width"), values["width"]),
        (_quantity(window, "Height"), values["height"]),
        (window_sill_height(window, host=wall), values["sill"]),
        (_quantity(window, "Opening"), values["opening"]),
        (_quantity(window, "Frame"), values["frame"]),
        (_quantity(window, "Offset"), values["offset"]),
    )
    return (
        list(getattr(window, "Hosts", []) or []) == [wall]
        and window_preset_name(window) == values["preset"]
        and all(first is not None and abs(float(first) - float(second)) <= 0.01 for first, second in checks)
    )


def _apply_transfer_metadata(window, record, previous=None):
    if previous is not None:
        window.Label = previous.Label
        for name in ("Description", "Tag", "Material"):
            if hasattr(previous, name) and hasattr(window, name):
                try:
                    setattr(window, name, getattr(previous, name))
                except Exception:
                    pass
    element_id = str(record.get("ElementID") or "").strip()
    if element_id:
        window.Tag = element_id
    set_prop(window, "App::PropertyString", "FA_ElementID", "FacilArquitectura", "Identificador transferible", element_id)
    set_prop(window, "App::PropertyString", "FA_RoomKey", "FacilArquitectura", "Recinto descriptivo", str(record.get("RoomKey") or ""))
    set_prop(window, "App::PropertyString", "FA_LevelKey", "FacilArquitectura", "Nivel descriptivo", str(record.get("LevelKey") or ""))
    set_prop(window, "App::PropertyString", "FA_TableNotes", "FacilArquitectura", "Notas de tabla", str(record.get("Notes") or ""))
    set_prop(window, "App::PropertyInteger", "FA_ElementDataSchema", "FacilArquitectura", "Version de esquema", SCHEMA_VERSION)


def _remove_generated_window(doc, window):
    base = getattr(window, "Base", None)
    try:
        window.Hosts = []
    except Exception:
        pass
    name = window.Name
    base_name = getattr(base, "Name", None)
    if doc.getObject(name) is not None:
        doc.removeObject(name)
    if base_name and doc.getObject(base_name) is not None:
        doc.removeObject(base_name)


def _json_report(plan, actions, dry_run):
    serial_actions = []
    counts = {"CREATE": 0, "REPLACE": 0, "KEEP": 0, "SKIP": 0}
    for item in actions:
        action = item["action"]
        counts[action if action in counts else "SKIP"] += 1
        serial_actions.append(
            {
                "row_index": item["row_index"],
                "element_id": item.get("element_id", ""),
                "status": item["status"],
                "action": action,
                "reason": item.get("reason", ""),
                "source_sketch": getattr(item.get("source"), "Name", ""),
                "geometry_index": int(item.get("axis", {}).get("index", -1)) if item.get("axis") else None,
                "host": getattr(item.get("match", {}).get("wall"), "Name", "") if item.get("match") else "",
            }
        )
    return {
        "category": CATEGORY_WINDOWS,
        "dry_run": bool(dry_run),
        "validation": plan["validation"],
        "actions": serial_actions,
        "action_counts": counts,
        "skipped_validation_count": len(plan["skipped"]),
    }


def _skipped_action(item, status, reason):
    return {"row_index": item["row_index"], "element_id": item["record"].get("ElementID", ""), "status": status, "action": "SKIP", "reason": reason}


def _element_id(window, fallback_index):
    for name in ("FA_ElementID", "Tag"):
        value = str(getattr(window, name, "") or "").strip()
        if value:
            return value
    return "V-%03d" % int(fallback_index)


def _level_key(window):
    value = str(getattr(window, "FA_LevelKey", "") or getattr(window, "FA_TargetLevel", "") or "").strip()
    if value:
        return value
    for parent in list(getattr(window, "InList", []) or []):
        if str(getattr(parent, "IfcType", "") or "") == "Building Storey":
            return str(parent.Label)
    return ""


def _quantity(obj, name):
    if not hasattr(obj, name):
        return None
    value = getattr(obj, name)
    try:
        return float(getattr(value, "Value", value))
    except Exception:
        return None


def _property_int(obj, name):
    try:
        return int(getattr(obj, name)) if hasattr(obj, name) else None
    except Exception:
        return None


def _unique_objects(objects):
    result = []
    seen = set()
    for obj in objects or []:
        key = (str(getattr(getattr(obj, "Document", None), "Name", "")), str(getattr(obj, "Name", "")))
        if key in seen:
            continue
        seen.add(key)
        result.append(obj)
    return result
