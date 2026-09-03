"""Room-label collection helpers for FacilArquitecturaWB.

Descripcion: recopila rotulos Draft/Text y los consolida en una hoja de calculo.
Funcionamiento principal: si el comando recibe capas Draft seleccionadas, toma
sus textos como alcance explicito sin intentar adivinar su contenido; sin capas
seleccionadas, usa deteccion automatica conservadora sobre el documento.
Mantenimiento: la seleccion de capa tiene prioridad sobre las heuristicas. No
endurecer reglas CAD (altura de texto, nombre de layer, etc.) como universales.
Version: 0.4.0
Fecha y hora: 2026-08-27 08:45 America/Costa_Rica
"""

from __future__ import annotations

import re
import unicodedata

from .project_structure import msg, set_prop


SHEET_NAME = "Spreadsheet_Rotulos_Recintos"
SHEET_LABEL = "Rotulos de recintos"
GENERATED_BY = "FA_CollectRoomLabels"
AREA_RE = re.compile(r"^\s*([0-9]+(?:[.,][0-9]+)?)\s*m(?:2|\u00b2)\s*$", re.IGNORECASE)
HEIGHT_RE = re.compile(r"^\s*H\s*=\s*[+-]?[0-9]+(?:[.,][0-9]+)?(?:\s*m)?\s*$", re.IGNORECASE)
NUMBER_ONLY_RE = re.compile(r"^\s*[+-]?[0-9]+(?:[.,][0-9]+)?\s*$")


def text_lines(obj):
    """Return non-empty lines from an object exposing FreeCAD's Text property."""
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


def _proxy_identity(obj):
    """Return a stable lower-case module/class identity for a FeaturePython proxy."""
    try:
        proxy = obj.Proxy
    except Exception:
        return ""
    if proxy is None:
        return ""
    cls = getattr(proxy, "__class__", None)
    module = str(getattr(cls, "__module__", "") or "")
    name = str(getattr(cls, "__name__", "") or "")
    return (module + "." + name).strip(".").lower()


def is_draft_text(obj):
    """Recognize Draft Text even though its TypeId is App::FeaturePython."""
    if not text_lines(obj):
        return False
    proxy_id = _proxy_identity(obj)
    if proxy_id == "draftobjects.text.text" or proxy_id.endswith(".text.text"):
        return True
    # Fallback for FreeCAD/Draft variants where Proxy introspection differs.
    type_id = str(getattr(obj, "TypeId", "") or "").lower()
    if "text" in type_id:
        return True
    return hasattr(obj, "Text") and hasattr(obj, "DxfTextHeight")


def is_draft_layer(obj):
    """Return True for a Draft Layer, but not for the LayerContainer itself."""
    if str(getattr(obj, "TypeId", "") or "") != "App::FeaturePython":
        return False
    if not hasattr(obj, "Group"):
        return False
    proxy_id = _proxy_identity(obj)
    if "layer" in proxy_id:
        return True
    # Conservative fallback: Draft layers expose Group as a LinkList and are
    # App::FeaturePython. Avoid accepting arbitrary FeaturePython groups unless
    # the property type can be confirmed as a link list.
    try:
        return str(obj.getTypeIdOfProperty("Group")) == "App::PropertyLinkList"
    except Exception:
        return False


def selected_draft_layers(selection):
    """Filter a GUI selection down to explicit Draft Layer objects."""
    return [obj for obj in list(selection or []) if is_draft_layer(obj)]


def layer_objects(layers):
    """Return unique direct members of selected Draft Layers, preserving order."""
    objects = []
    seen = set()
    for layer in list(layers or []):
        try:
            members = list(layer.Group or [])
        except Exception:
            members = []
        for obj in members:
            key = str(getattr(obj, "Name", "") or id(obj))
            if key in seen:
                continue
            seen.add(key)
            objects.append(obj)
    return objects


def _visible(obj):
    """Read object visibility without requiring FreeCADGui."""
    try:
        return bool(obj.Visibility)
    except Exception:
        try:
            return bool(obj.ViewObject.Visibility)
        except Exception:
            return True


def _automatic_text_candidate(obj, lines):
    """Conservative heuristic used only when the user did not select a layer."""
    if not lines or not is_draft_text(obj):
        return False
    first = str(lines[0]).strip()
    if not first or len(first) > 120:
        return False
    # Structured FA labels remain valid even if hidden.
    label = str(getattr(obj, "Label", "") or "").lower()
    if label.startswith("etiqueta_") or area_value(lines) is not None:
        return True
    # CAD texts such as Upala's H=2.62 are annotations, not room names.
    if HEIGHT_RE.match(first) or NUMBER_ONLY_RE.match(first) or AREA_RE.match(first):
        return False
    # In automatic mode, favor currently visible Draft text. Explicit layer
    # selection intentionally bypasses this heuristic.
    return _visible(obj)


def looks_like_room_label(obj, lines, explicit_scope=False):
    """Recognize a room label according to explicit-layer or automatic mode."""
    if not lines:
        return False
    if explicit_scope:
        # User chose the layer: do not guess semantic content. The only check is
        # that the member is a real text object with non-empty Text.
        return is_draft_text(obj)
    return _automatic_text_candidate(obj, lines)


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


def collect_room_labels(doc, objects=None, explicit_scope=False):
    """Collect room labels, consolidating duplicates by normalized name.

    objects=None means automatic document-wide discovery. When explicit_scope is
    True, objects are assumed to come from user-selected Draft Layers and no
    semantic guessing is performed beyond confirming they are Draft Text.
    """
    records = {}
    source_objects = list(objects) if objects is not None else list(getattr(doc, "Objects", []) or [])
    for obj in source_objects:
        lines = text_lines(obj)
        if not looks_like_room_label(obj, lines, explicit_scope=explicit_scope):
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
