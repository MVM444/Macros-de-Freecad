"""Room-label collection helpers for FacilArquitecturaWB.

Descripcion: recopila rotulos Draft/Text y los consolida en una hoja de calculo.
Fecha: 2026-07-25
Version: 0.3.0
"""

from __future__ import annotations

import re
import unicodedata

from .project_structure import msg, set_prop


SHEET_NAME = "Spreadsheet_Rotulos_Recintos"
SHEET_LABEL = "Rotulos de recintos"
GENERATED_BY = "FA_CollectRoomLabels"
AREA_RE = re.compile(r"^\s*([0-9]+(?:[.,][0-9]+)?)\s*m(?:2|\u00b2)\s*$", re.IGNORECASE)


def text_lines(obj):
    """Return non-empty visible lines from a Draft/Feature text object."""
    if not hasattr(obj, "Text"):
        return []
    try:
        value = obj.Text
    except Exception:
        return []
    if isinstance(value, (list, tuple)):
        lines = [str(item).strip() for item in value]
    else:
        lines = [line.strip() for line in str(value).replace("\r", "\n").split("\n")]
    return [line for line in lines if line]


def normalized_name(value):
    """Normalize a room name while preserving accents for display."""
    value = " ".join(str(value or "").strip().split())
    return unicodedata.normalize("NFKC", value).upper()


def area_value(lines):
    """Read the first area written as '<number> m2' from text lines."""
    for line in list(lines or [])[1:]:
        match = AREA_RE.match(str(line))
        if match:
            return float(match.group(1).replace(",", "."))
    return None


def looks_like_room_label(obj, lines):
    """Recognize structured room labels and ordinary Draft text candidates."""
    if not lines:
        return False
    label = str(getattr(obj, "Label", "") or "").lower()
    if label.startswith("etiqueta_") or area_value(lines) is not None:
        return True
    type_id = str(getattr(obj, "TypeId", "") or "").lower()
    return "text" in type_id and len(lines[0]) <= 120


def object_position(obj):
    """Return the global XYZ insertion point of a label."""
    try:
        point = obj.getGlobalPlacement().Base
    except Exception:
        try:
            point = obj.Placement.Base
        except Exception:
            return (0.0, 0.0, 0.0)
    return (float(point.x), float(point.y), float(point.z))


def collect_room_labels(doc):
    """Collect room labels, consolidating duplicates by normalized name."""
    records = {}
    for obj in list(getattr(doc, "Objects", []) or []):
        lines = text_lines(obj)
        if not looks_like_room_label(obj, lines):
            continue
        name = normalized_name(lines[0])
        if not name:
            continue
        x, y, z = object_position(obj)
        area = area_value(lines)
        room_type = lines[2] if len(lines) > 2 and not AREA_RE.match(lines[2]) else ""
        occupancy = lines[3] if len(lines) > 3 else ""
        record = records.get(name)
        if record is None:
            records[name] = {
                "name": name,
                "area": area,
                "type": room_type,
                "occupancy": occupancy,
                "x": x,
                "y": y,
                "z": z,
                "source": str(getattr(obj, "Label", "") or getattr(obj, "Name", "")),
                "count": 1,
            }
            continue
        record["count"] += 1
        if record["area"] is None and area is not None:
            record["area"] = area
        if not record["type"] and room_type:
            record["type"] = room_type
        if not record["occupancy"] and occupancy:
            record["occupancy"] = occupancy
    return [records[key] for key in sorted(records)]


def clear_sheet(sheet):
    """Clear an existing sheet across FreeCAD spreadsheet API variants."""
    try:
        sheet.clearAll()
        return
    except Exception:
        pass
    for row in range(1, 1001):
        for column in "ABCDEFGHI":
            try:
                sheet.clear("%s%d" % (column, row))
            except Exception:
                pass


def write_room_label_spreadsheet(doc, records, parent_group=None):
    """Create or update the canonical room-label spreadsheet."""
    sheet = doc.getObject(SHEET_NAME)
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", SHEET_NAME)
    sheet.Label = SHEET_LABEL
    clear_sheet(sheet)

    headers = ("Nombre", "Area_m2", "Tipo", "Ocupacion", "X_mm", "Y_mm", "Z_mm", "Fuente", "Cantidad")
    for index, header in enumerate(headers):
        column = chr(ord("A") + index)
        sheet.set(column + "1", header)
        try:
            sheet.setStyle(column + "1", "bold", "add")
        except Exception:
            pass

    for row, record in enumerate(records, 2):
        values = (
            record["name"],
            "" if record["area"] is None else "%.3f" % record["area"],
            record["type"],
            record["occupancy"],
            "%.3f" % record["x"],
            "%.3f" % record["y"],
            "%.3f" % record["z"],
            record["source"],
            str(record["count"]),
        )
        for index, value in enumerate(values):
            sheet.set("%s%d" % (chr(ord("A") + index), row), str(value))

    for column, width in zip("ABCDEFGHI", (220, 90, 150, 90, 100, 100, 100, 190, 80)):
        try:
            sheet.setColumnWidth(column, width)
        except Exception:
            pass
    try:
        sheet.setFrozenRows(1)
    except Exception:
        pass
    if parent_group is not None:
        try:
            parent_group.addObject(sheet)
        except Exception:
            pass
    set_prop(
        sheet,
        "App::PropertyString",
        "FA_GeneratedBy",
        "FacilArquitectura",
        "Comando que actualizo la hoja",
        GENERATED_BY,
    )
    set_prop(
        sheet,
        "App::PropertyInteger",
        "FA_RoomLabelCount",
        "FacilArquitectura",
        "Cantidad de rotulos consolidados",
        len(records),
    )
    doc.recompute()
    msg("Rotulos recopilados: %d | hoja: %s" % (len(records), sheet.Label))
    return sheet
