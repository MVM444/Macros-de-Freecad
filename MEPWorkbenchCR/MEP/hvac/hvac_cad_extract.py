"""Extract HVAC inventory records from an imported DWG/DXF document.

The extractor is deliberately conservative: equipment type and capacity come
from explicit CAD blocks and nearby technical annotations, while room names
remain candidates until an actual HVAC Space can prove containment.
"""

from __future__ import annotations

import datetime
import json
import math
import os
import re
import unicodedata

try:
    import FreeCAD as App
except ImportError:  # Pure parsing helpers are testable outside FreeCAD.
    App = None

try:
    import Draft
except Exception:
    Draft = None

from . import hvac_project


LOG_PREFIX = "[MEP-HVAC][CAD Extract] "
EXTRACTION_REVISION = "2026-07-31-r1"
GENERATOR_TAG = "MEP_HVAC_ExtractCAD"
RECORD_MEP_TYPE = "HVACCADInventory"
GROUP_NAME = "HVAC_CAD_Extraction"
GROUP_LABEL = "HVAC - Inventario extraido de CAD"
SHEET_NAME = "HVAC_CAD_Equipment_Schedule"
SHEET_LABEL = "HVAC - Inventario CAD"

# Known block meanings from the Puriscal reference. Descriptive block names are
# still preferred, so future drawings do not depend on these anonymous names.
ANONYMOUS_BLOCK_TYPE_HINTS = {
    "block u160": "Cassette",
    "block u157": "FloorCeiling",
}

TYPE_MODEL_PREFIX = {
    "Wall": "Pared",
    "Cassette": "Cassette",
    "FloorCeiling": "PisoCielo",
}

ROOM_EXCLUDE_TOKENS = {
    "aire acondicionado",
    "btu",
    "cfm",
    "evaporador",
    "mini split",
    "piso cielo",
    "cassette",
    "descarga",
    "exterior",
    "refrigerante",
    "condensado",
    "tuberia",
    "cobre",
    "simbolo",
    "simbologia",
    "escala",
    "detalle",
    "plano",
    "nota",
    "existente",
    "demoler",
    "construir",
    "alimentacion",
    "circuito",
    "volt",
    "fase",
}


def log(message):
    text = LOG_PREFIX + str(message)
    print(text)


def _repair_mojibake(value):
    text = str(value or "")
    if "Ã" not in text and "Â" not in text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except Exception:
        return text


def clean_cad_text(value):
    """Return readable text from Draft/DXF strings, including MTEXT \P."""
    if isinstance(value, (list, tuple)):
        value = " ".join(str(item) for item in value)
    text = _repair_mojibake(value)
    text = re.sub(r"\\[Pp]", " ", text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\\[A-Za-z][^;]*;", " ", text)
    text = re.sub(r"[{}]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalized_text(value):
    text = clean_cad_text(value).lower().replace("_", " ").replace("-", " ")
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _display_text(value):
    text = clean_cad_text(value)
    if not text:
        return ""
    return text.upper()


def parse_equipment_annotation(value):
    """Parse an evaporator CAD annotation into a normalized equipment spec."""
    raw = clean_cad_text(value)
    norm = normalized_text(raw)
    if "evaporador" not in norm or "btu" not in norm:
        return None

    if "cassette" in norm:
        equipment_type = "Cassette"
    elif "piso cielo" in norm or "floor ceiling" in norm:
        equipment_type = "FloorCeiling"
    elif "pared" in norm or "wall" in norm:
        equipment_type = "Wall"
    else:
        return None

    capacity = 0
    before_btu = norm.split("btu", 1)[0]
    matches = re.findall(r"(?:^|\s)(\d(?:[\s.,]*\d){3,6})(?=\s*$|\s)", before_btu)
    if matches:
        digits = re.sub(r"\D", "", matches[-1])
        try:
            capacity = int(digits)
        except ValueError:
            capacity = 0
    if capacity < 1000 or capacity > 500000:
        capacity = 0

    circuit_match = re.search(r"\bAC[-\s][A-Z0-9]+[-\s]\d+\b", raw.upper())
    quantity = 2 if re.search(r"\bEVAPORADORAS\b", raw.upper()) else 1
    prefix = TYPE_MODEL_PREFIX[equipment_type]
    return {
        "equipment_type": equipment_type,
        "capacity_btu": capacity,
        "model": "%s_%d" % (prefix, capacity) if capacity else "",
        "quantity": quantity,
        "circuit": circuit_match.group(0).replace(" ", "-") if circuit_match else "",
        "raw": raw,
    }


def parse_airflow_annotation(value):
    raw = clean_cad_text(value)
    norm = normalized_text(raw)
    match = re.search(r"\b(\d{2,6})\s*cfm\b", norm)
    if not match:
        return None
    return {"airflow_cfm": int(match.group(1)), "raw": raw}


def is_room_annotation(value, parent_labels=None):
    """Conservative room-label filter for imported Draft Text objects."""
    raw = clean_cad_text(value)
    norm = normalized_text(raw)
    if not norm or len(raw) > 64 or len(norm.split()) > 6:
        return False
    if re.search(r"\d", norm):
        return False
    if any(token in norm for token in ROOM_EXCLUDE_TOKENS):
        return False
    parents = " ".join(normalized_text(item) for item in (parent_labels or []))
    if any(token in parents for token in ("aire acondicionado", "air", "cota", "dimension")):
        return False
    letters = re.sub(r"[^a-z]", "", norm)
    return len(letters) >= 3


def classify_symbol(linked_name="", linked_label="", object_name="", object_label=""):
    combined = normalized_text(" ".join((linked_name, linked_label, object_name, object_label)))
    linked_keys = {normalized_text(linked_name), normalized_text(linked_label)}
    if "fan ceiling" in combined or "extractor" in combined:
        return "CeilingFan"
    if "evaporadora pared" in combined or "evaporator wall" in combined:
        return "Wall"
    if "cassette" in combined:
        return "Cassette"
    if "piso cielo" in combined or "floor ceiling" in combined:
        return "FloorCeiling"
    for block_hint, equipment_type in ANONYMOUS_BLOCK_TYPE_HINTS.items():
        if block_hint in linked_keys:
            return equipment_type
    return ""


def _draft_type(obj):
    if Draft is None:
        return ""
    try:
        return str(Draft.getType(obj) or "")
    except Exception:
        return ""


def _object_text(obj):
    return clean_cad_text(getattr(obj, "Text", ""))


def _object_position(obj):
    try:
        getter = getattr(obj, "getGlobalPlacement", None)
        placement = getter() if callable(getter) else obj.Placement
        base = placement.Base
        return (float(base.x), float(base.y), float(base.z))
    except Exception:
        try:
            base = obj.Placement.Base
            return (float(base.x), float(base.y), float(base.z))
        except Exception:
            return (0.0, 0.0, 0.0)


def _object_rotation_deg(obj):
    try:
        getter = getattr(obj, "getGlobalPlacement", None)
        placement = getter() if callable(getter) else obj.Placement
        rotation = placement.Rotation
        yaw, _pitch, _roll = rotation.getYawPitchRoll()
        return float(yaw) % 360.0
    except Exception:
        try:
            return math.degrees(float(obj.Placement.Rotation.Angle)) % 360.0
        except Exception:
            return 0.0


def _distance_xy(first, second):
    return math.hypot(float(first[0]) - float(second[0]), float(first[1]) - float(second[1]))


def _parent_map(doc):
    result = {}
    for parent in list(getattr(doc, "Objects", []) or []):
        for child in list(getattr(parent, "Group", []) or []):
            result.setdefault(str(getattr(child, "Name", "")), []).append(
                str(getattr(parent, "Label", "") or getattr(parent, "Name", ""))
            )
    return result


def scan_document(doc):
    """Scan imported CAD links/texts without creating or modifying objects."""
    if doc is None:
        raise RuntimeError("No hay documento activo para extraer HVAC.")
    parents = _parent_map(doc)
    symbols = []
    equipment_annotations = []
    airflow_annotations = []
    room_annotations = []

    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "MEPType", "") or "") == RECORD_MEP_TYPE:
            continue
        type_id = str(getattr(obj, "TypeId", "") or "")
        if type_id == "App::Link":
            linked = getattr(obj, "LinkedObject", None)
            equipment_type = classify_symbol(
                getattr(linked, "Name", ""),
                getattr(linked, "Label", ""),
                getattr(obj, "Name", ""),
                getattr(obj, "Label", ""),
            )
            if equipment_type:
                symbols.append(
                    {
                        "object": obj,
                        "source_name": str(getattr(obj, "Name", "") or ""),
                        "source_label": str(getattr(obj, "Label", "") or ""),
                        "equipment_type": equipment_type,
                        "position": _object_position(obj),
                        "rotation_deg": _object_rotation_deg(obj),
                    }
                )
            continue

        if _draft_type(obj) != "Text" and "Text" not in type_id:
            continue
        raw = _object_text(obj)
        if not raw:
            continue
        position = _object_position(obj)
        spec = parse_equipment_annotation(raw)
        if spec:
            row = dict(spec)
            row.update({"object": obj, "position": position})
            equipment_annotations.append(row)
            continue
        airflow = parse_airflow_annotation(raw)
        if airflow:
            row = dict(airflow)
            row.update({"object": obj, "position": position})
            airflow_annotations.append(row)
            continue
        if is_room_annotation(raw, parents.get(str(getattr(obj, "Name", "")), [])):
            room_annotations.append(
                {
                    "object": obj,
                    "name": _display_text(raw),
                    "key": normalized_text(raw),
                    "position": position,
                }
            )

    return {
        "symbols": symbols,
        "equipment_annotations": equipment_annotations,
        "airflow_annotations": airflow_annotations,
        "room_annotations": room_annotations,
    }


def _annotation_distance_limit(equipment_type):
    if equipment_type == "CeilingFan":
        return 1500.0
    if equipment_type in ("Cassette", "FloorCeiling"):
        return 4500.0
    return 3500.0


def _match_equipment_annotations(symbols, annotations):
    slots = []
    for annotation in annotations:
        for slot_index in range(max(1, int(annotation.get("quantity", 1) or 1))):
            slots.append((annotation, slot_index))

    pairs = []
    for symbol_index, symbol in enumerate(symbols):
        if symbol["equipment_type"] == "CeilingFan":
            continue
        for slot_index, slot in enumerate(slots):
            annotation = slot[0]
            if annotation["equipment_type"] != symbol["equipment_type"]:
                continue
            distance = _distance_xy(symbol["position"], annotation["position"])
            if distance <= _annotation_distance_limit(symbol["equipment_type"]):
                pairs.append((distance, symbol_index, slot_index))
    pairs.sort(key=lambda row: row[0])

    used_symbols = set()
    used_slots = set()
    matches = {}
    for distance, symbol_index, slot_index in pairs:
        if symbol_index in used_symbols or slot_index in used_slots:
            continue
        used_symbols.add(symbol_index)
        used_slots.add(slot_index)
        matches[symbol_index] = (slots[slot_index][0], distance)
    return matches


def _match_airflow_annotations(symbols, annotations):
    pairs = []
    for symbol_index, symbol in enumerate(symbols):
        if symbol["equipment_type"] != "CeilingFan":
            continue
        for annotation_index, annotation in enumerate(annotations):
            distance = _distance_xy(symbol["position"], annotation["position"])
            if distance <= _annotation_distance_limit("CeilingFan"):
                pairs.append((distance, symbol_index, annotation_index))
    pairs.sort(key=lambda row: row[0])
    used_symbols = set()
    used_annotations = set()
    matches = {}
    for distance, symbol_index, annotation_index in pairs:
        if symbol_index in used_symbols or annotation_index in used_annotations:
            continue
        used_symbols.add(symbol_index)
        used_annotations.add(annotation_index)
        matches[symbol_index] = (annotations[annotation_index], distance)
    return matches


def _mark_outliers(symbols):
    if len(symbols) < 4:
        return set()
    xs = sorted(float(row["position"][0]) for row in symbols)
    ys = sorted(float(row["position"][1]) for row in symbols)
    mid = len(symbols) // 2
    median_x = xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2.0
    median_y = ys[mid] if len(ys) % 2 else (ys[mid - 1] + ys[mid]) / 2.0
    distances = sorted(_distance_xy(row["position"], (median_x, median_y, 0.0)) for row in symbols)
    typical = distances[mid] if len(distances) % 2 else (distances[mid - 1] + distances[mid]) / 2.0
    limit = max(30000.0, typical * 5.0)
    return {
        index
        for index, row in enumerate(symbols)
        if _distance_xy(row["position"], (median_x, median_y, 0.0)) > limit
    }


def _back_to_back_indices(symbols):
    result = set()
    for first in range(len(symbols)):
        if symbols[first]["equipment_type"] != "Wall":
            continue
        for second in range(first + 1, len(symbols)):
            if symbols[second]["equipment_type"] != "Wall":
                continue
            if _distance_xy(symbols[first]["position"], symbols[second]["position"]) > 300.0:
                continue
            delta = abs((symbols[first]["rotation_deg"] - symbols[second]["rotation_deg"]) % 360.0)
            delta = min(delta, 360.0 - delta)
            if abs(delta - 180.0) <= 20.0:
                result.update((first, second))
    return result


def _room_candidates(point, room_annotations):
    by_key = {}
    for room in room_annotations:
        distance = _distance_xy(point, room["position"])
        previous = by_key.get(room["key"])
        if previous is None or distance < previous["distance_mm"]:
            candidate = dict(room)
            candidate["distance_mm"] = distance
            by_key[room["key"]] = candidate
    return sorted(by_key.values(), key=lambda row: row["distance_mm"])


def _associate_room(item, room_annotations, back_to_back=False):
    candidates = _room_candidates(item["position"], room_annotations)
    if not candidates or item.get("outlier"):
        return {
            "room_candidate": "",
            "room_alternatives": [],
            "room_distance_mm": 0.0,
            "room_confidence": 0.0,
            "room_status": "Fuera de planta" if item.get("outlier") else "Sin candidato",
            "room_text_object": None,
        }

    first = candidates[0]
    max_distance = 4500.0 if item["equipment_class"] == "Evaporator" else 3500.0
    if first["distance_mm"] > max_distance:
        return {
            "room_candidate": first["name"],
            "room_alternatives": [row["name"] for row in candidates[1:3]],
            "room_distance_mm": first["distance_mm"],
            "room_confidence": 0.15,
            "room_status": "Revisar: etiqueta lejana",
            "room_text_object": first["object"],
        }

    second_distance = candidates[1]["distance_mm"] if len(candidates) > 1 else max_distance * 1.5
    gap = max(0.0, second_distance - first["distance_mm"])
    distance_score = max(0.0, 1.0 - first["distance_mm"] / max_distance)
    gap_score = min(1.0, gap / 1600.0)
    confidence = round(0.55 * distance_score + 0.45 * gap_score, 3)
    if back_to_back:
        confidence = min(confidence, 0.45)
        status = "Revisar: espalda con espalda"
    elif (
        item["equipment_class"] == "Evaporator"
        and confidence >= 0.52
        and gap >= 650.0
        and first["distance_mm"] <= 3000.0
    ):
        status = "Probable"
    else:
        status = "Revisar: proximidad ambigua"
    return {
        "room_candidate": first["name"],
        "room_alternatives": [row["name"] for row in candidates[1:3]],
        "room_distance_mm": first["distance_mm"],
        "room_confidence": confidence,
        "room_status": status,
        "room_text_object": first["object"],
    }


def build_inventory(scan):
    symbols = list(scan.get("symbols", []) or [])
    annotations = list(scan.get("equipment_annotations", []) or [])
    airflow_annotations = list(scan.get("airflow_annotations", []) or [])
    room_annotations = list(scan.get("room_annotations", []) or [])
    equipment_matches = _match_equipment_annotations(symbols, annotations)
    airflow_matches = _match_airflow_annotations(symbols, airflow_annotations)
    outliers = _mark_outliers(symbols)
    back_to_back = _back_to_back_indices(symbols)

    inventory = []
    for index, symbol in enumerate(symbols):
        item = dict(symbol)
        item["equipment_class"] = "ExhaustFan" if symbol["equipment_type"] == "CeilingFan" else "Evaporator"
        item["capacity_btu"] = 0
        item["airflow_cfm"] = 0
        item["model"] = "ExtractorTecho" if item["equipment_class"] == "ExhaustFan" else ""
        item["circuit"] = ""
        item["annotation_object"] = None
        item["annotation_text"] = ""
        item["annotation_distance_mm"] = 0.0
        item["annotation_status"] = "Sin etiqueta tecnica"
        item["outlier"] = index in outliers

        if index in equipment_matches:
            annotation, distance = equipment_matches[index]
            item.update(
                {
                    "capacity_btu": int(annotation.get("capacity_btu", 0) or 0),
                    "model": str(annotation.get("model", "") or ""),
                    "circuit": str(annotation.get("circuit", "") or ""),
                    "annotation_object": annotation.get("object"),
                    "annotation_text": str(annotation.get("raw", "") or ""),
                    "annotation_distance_mm": distance,
                    "annotation_status": "Coincidente" if distance <= 2500.0 else "Revisar distancia",
                }
            )
        elif index in airflow_matches:
            annotation, distance = airflow_matches[index]
            item.update(
                {
                    "airflow_cfm": int(annotation.get("airflow_cfm", 0) or 0),
                    "annotation_object": annotation.get("object"),
                    "annotation_text": str(annotation.get("raw", "") or ""),
                    "annotation_distance_mm": distance,
                    "annotation_status": "Coincidente" if distance <= 800.0 else "Revisar distancia",
                }
            )

        item.update(_associate_room(item, room_annotations, back_to_back=index in back_to_back))
        inventory.append(item)

    evaporators = [row for row in inventory if row["equipment_class"] == "Evaporator" and not row["outlier"]]
    fans = [row for row in inventory if row["equipment_class"] == "ExhaustFan" and not row["outlier"]]
    outlier_evaporators = [row for row in inventory if row["equipment_class"] == "Evaporator" and row["outlier"]]
    outlier_fans = [row for row in inventory if row["equipment_class"] == "ExhaustFan" and row["outlier"]]
    spatial_key = lambda row: (-round(row["position"][1], 3), round(row["position"][0], 3), row["source_name"])
    for item_index, item in enumerate(sorted(evaporators, key=spatial_key), 1):
        item["equipment_id"] = "EV-%02d" % item_index
    for item_index, item in enumerate(sorted(fans, key=spatial_key), 1):
        item["equipment_id"] = "EX-%02d" % item_index
    for item_index, item in enumerate(sorted(outlier_evaporators, key=spatial_key), 1):
        item["equipment_id"] = "EV-X%02d" % item_index
    for item_index, item in enumerate(sorted(outlier_fans, key=spatial_key), 1):
        item["equipment_id"] = "EX-X%02d" % item_index
    return sorted(inventory, key=lambda row: row["equipment_id"])


def analyze_document(doc=None):
    if doc is None:
        if App is None:
            raise RuntimeError("FreeCAD no esta disponible.")
        doc = App.ActiveDocument
    scan = scan_document(doc)
    inventory = build_inventory(scan)
    return {
        "revision": EXTRACTION_REVISION,
        "document_name": str(getattr(doc, "Name", "") or ""),
        "document_label": str(getattr(doc, "Label", "") or ""),
        "inventory": inventory,
        "counts": {
            "evaporators": sum(row["equipment_class"] == "Evaporator" and not row["outlier"] for row in inventory),
            "fans": sum(row["equipment_class"] == "ExhaustFan" and not row["outlier"] for row in inventory),
            "outliers": sum(bool(row["outlier"]) for row in inventory),
            "room_review": sum(row["room_status"] != "Probable" for row in inventory if not row["outlier"]),
            "missing_technical_label": sum(row["annotation_status"] == "Sin etiqueta tecnica" for row in inventory),
        },
    }


def _ensure_property(obj, property_type, name, group, description=""):
    if name not in list(getattr(obj, "PropertiesList", []) or []):
        obj.addProperty(property_type, name, group, description)


def _safe_name(value):
    text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "")).strip("_")
    return text or "Item"


def _get_or_create_group(doc):
    group = doc.getObject(GROUP_NAME)
    if group is None:
        group = doc.addObject("App::DocumentObjectGroup", GROUP_NAME)
    group.Label = GROUP_LABEL
    for property_type, name, description in (
        ("App::PropertyString", "GeneratedBy", "Extractor que mantiene este inventario"),
        ("App::PropertyString", "ExtractionRevision", "Version de las reglas de extraccion"),
        ("App::PropertyString", "SourceDocument", "Documento CAD analizado"),
        ("App::PropertyString", "ExtractedAt", "Fecha y hora de la ultima extraccion"),
        ("App::PropertyInteger", "EvaporatorCount", "Evaporadoras validas detectadas"),
        ("App::PropertyInteger", "ExhaustFanCount", "Extractores validos detectados"),
        ("App::PropertyInteger", "ReviewCount", "Asociaciones de recinto por revisar"),
        ("App::PropertyInteger", "OutlierCount", "Simbolos fuera del conjunto principal"),
    ):
        _ensure_property(group, property_type, name, "Extraccion CAD", description)
    group.GeneratedBy = GENERATOR_TAG
    group.ExtractionRevision = EXTRACTION_REVISION
    group.SourceDocument = str(getattr(doc, "Label", "") or getattr(doc, "Name", ""))

    root = hvac_project.ensure_hvac_root_group(doc)
    if root is not None:
        try:
            if group not in list(getattr(root, "Group", []) or []):
                root.addObject(group)
        except Exception:
            pass
    return group


def _get_or_create_record(doc, source_name):
    name = "HVAC_CAD_%s" % _safe_name(source_name)
    record = doc.getObject(name)
    if record is None:
        record = doc.addObject("App::FeaturePython", name)
    properties = (
        ("App::PropertyString", "MEPType", "MEP"),
        ("App::PropertyString", "GeneratedBy", "Extraccion CAD"),
        ("App::PropertyString", "ExtractionRevision", "Extraccion CAD"),
        ("App::PropertyString", "EquipmentId", "Equipo HVAC"),
        ("App::PropertyString", "EquipmentClass", "Equipo HVAC"),
        ("App::PropertyString", "Type", "Equipo HVAC"),
        ("App::PropertyString", "Model", "Equipo HVAC"),
        ("App::PropertyFloat", "CapacityBTU", "Equipo HVAC"),
        ("App::PropertyFloat", "AirflowCFM", "Equipo HVAC"),
        ("App::PropertyString", "Circuit", "Equipo HVAC"),
        ("App::PropertyVector", "CADPositionMM", "Fuente CAD"),
        ("App::PropertyAngle", "CADRotation", "Fuente CAD"),
        ("App::PropertyLink", "CADSourceSymbol", "Fuente CAD"),
        ("App::PropertyLink", "CADSourceAnnotation", "Fuente CAD"),
        ("App::PropertyString", "CADAnnotationText", "Fuente CAD"),
        ("App::PropertyFloat", "CADAnnotationDistanceMM", "Fuente CAD"),
        ("App::PropertyString", "CADAnnotationStatus", "Fuente CAD"),
        ("App::PropertyString", "RoomCandidate", "Recinto candidato"),
        ("App::PropertyString", "RoomAlternatives", "Recinto candidato"),
        ("App::PropertyFloat", "RoomConfidence", "Recinto candidato"),
        ("App::PropertyFloat", "RoomDistanceMM", "Recinto candidato"),
        ("App::PropertyString", "RoomStatus", "Recinto candidato"),
        ("App::PropertyLink", "CADRoomText", "Recinto candidato"),
        ("App::PropertyBool", "Outlier", "Validacion"),
        ("App::PropertyString", "ReviewNote", "Validacion"),
    )
    for property_type, prop_name, group in properties:
        _ensure_property(record, property_type, prop_name, group)
    return record


def _update_record(record, item):
    record.MEPType = RECORD_MEP_TYPE
    record.GeneratedBy = GENERATOR_TAG
    record.ExtractionRevision = EXTRACTION_REVISION
    record.EquipmentId = item["equipment_id"]
    record.EquipmentClass = item["equipment_class"]
    record.Type = item["equipment_type"]
    record.Model = item["model"]
    record.CapacityBTU = float(item["capacity_btu"])
    record.AirflowCFM = float(item["airflow_cfm"])
    record.Circuit = item["circuit"]
    if App is not None:
        record.CADPositionMM = App.Vector(*item["position"])
    record.CADRotation = float(item["rotation_deg"])
    record.CADSourceSymbol = item["object"]
    record.CADSourceAnnotation = item["annotation_object"]
    record.CADAnnotationText = item["annotation_text"]
    record.CADAnnotationDistanceMM = float(item["annotation_distance_mm"])
    record.CADAnnotationStatus = item["annotation_status"]
    record.RoomCandidate = item["room_candidate"]
    record.RoomAlternatives = " | ".join(item["room_alternatives"])
    record.RoomConfidence = float(item["room_confidence"])
    record.RoomDistanceMM = float(item["room_distance_mm"])
    record.RoomStatus = item["room_status"]
    record.CADRoomText = item["room_text_object"]
    record.Outlier = bool(item["outlier"])
    notes = []
    if item["annotation_status"] != "Coincidente":
        notes.append(item["annotation_status"])
    if item["room_status"] != "Probable":
        notes.append(item["room_status"])
    record.ReviewNote = "; ".join(notes)
    capacity = "%d BTU/h" % item["capacity_btu"] if item["capacity_btu"] else "%d CFM" % item["airflow_cfm"]
    room = item["room_candidate"] or "SIN RECINTO"
    record.Label = "%s | %s | %s | %s" % (item["equipment_id"], item["equipment_type"], capacity, room)


def _get_or_create_sheet(doc):
    sheet = doc.getObject(SHEET_NAME)
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", SHEET_NAME)
    sheet.Label = SHEET_LABEL
    return sheet


def _sheet_set(sheet, cell, value):
    sheet.set(cell, str(value))


def _column_name(index):
    value = index + 1
    result = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _update_sheet(sheet, inventory):
    try:
        sheet.clearAll()
    except Exception:
        pass
    headers = [
        "ID", "Clase", "Tipo", "Modelo", "Capacidad_BTUh", "Caudal_CFM", "Circuito",
        "X_mm", "Y_mm", "Rotacion_deg", "Recinto_candidato", "Alternativas",
        "Confianza", "Estado_recinto", "Estado_etiqueta", "Dist_etiqueta_mm",
        "Fuente_bloque", "Fuente_texto", "Fuera_planta",
    ]
    for column_index, header in enumerate(headers):
        _sheet_set(sheet, "%s1" % _column_name(column_index), header)
    for row_index, item in enumerate(inventory, 2):
        values = [
            item["equipment_id"], item["equipment_class"], item["equipment_type"], item["model"],
            item["capacity_btu"], item["airflow_cfm"], item["circuit"],
            "%.3f" % item["position"][0], "%.3f" % item["position"][1], "%.2f" % item["rotation_deg"],
            item["room_candidate"], " | ".join(item["room_alternatives"]),
            "%.3f" % item["room_confidence"], item["room_status"], item["annotation_status"],
            "%.1f" % item["annotation_distance_mm"], item["source_name"],
            str(getattr(item["annotation_object"], "Name", "") or ""), "SI" if item["outlier"] else "NO",
        ]
        for column_index, value in enumerate(values):
            _sheet_set(sheet, "%s%d" % (_column_name(column_index), row_index), value)
    try:
        sheet.setStyle("A1:S1", "bold", "add")
        sheet.setBackground("A1:S1", (0.82, 0.90, 0.96))
        sheet.setAlignment("A1:S%d" % max(1, len(inventory) + 1), "left", "keep")
        widths = [10, 14, 14, 20, 18, 14, 12, 14, 14, 14, 24, 34, 12, 30, 24, 20, 28, 20, 14]
        for column_index, width in enumerate(widths):
            sheet.setColumnWidth(_column_name(column_index), width)
    except Exception:
        pass


def materialize_inventory(doc, analysis):
    group = _get_or_create_group(doc)
    inventory = list(analysis.get("inventory", []) or [])
    active_names = set()
    records = []
    for item in inventory:
        record = _get_or_create_record(doc, item["source_name"])
        _update_record(record, item)
        active_names.add(str(record.Name))
        records.append(record)
        try:
            if record not in list(getattr(group, "Group", []) or []):
                group.addObject(record)
        except Exception:
            pass

    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "MEPType", "") or "") != RECORD_MEP_TYPE:
            continue
        if str(getattr(obj, "GeneratedBy", "") or "") != GENERATOR_TAG:
            continue
        if str(getattr(obj, "Name", "") or "") not in active_names:
            doc.removeObject(obj.Name)

    sheet = _get_or_create_sheet(doc)
    _update_sheet(sheet, inventory)
    try:
        if sheet not in list(getattr(group, "Group", []) or []):
            group.addObject(sheet)
    except Exception:
        pass

    counts = analysis["counts"]
    group.ExtractedAt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    group.EvaporatorCount = int(counts["evaporators"])
    group.ExhaustFanCount = int(counts["fans"])
    group.ReviewCount = int(counts["room_review"])
    group.OutlierCount = int(counts["outliers"])
    doc.recompute()
    return {"group": group, "sheet": sheet, "records": records}


def extract_document(doc=None, create_objects=True):
    """Analyze a CAD document and optionally create/update MEP inventory objects."""
    if doc is None:
        if App is None:
            raise RuntimeError("FreeCAD no esta disponible.")
        doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No hay documento activo.")

    analysis = analyze_document(doc)
    if create_objects:
        transaction_open = False
        try:
            doc.openTransaction("HVAC: Extraer inventario desde CAD")
            transaction_open = True
        except Exception:
            pass
        try:
            created = materialize_inventory(doc, analysis)
            analysis.update(created)
            if transaction_open:
                doc.commitTransaction()
        except Exception:
            if transaction_open:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            raise

    counts = analysis["counts"]
    log(
        "Extraccion lista: evaporadoras={evaporators}, extractores={fans}, "
        "fuera_planta={outliers}, recintos_por_revisar={room_review}".format(**counts)
    )
    return analysis


def serializable_report(analysis):
    rows = []
    for item in analysis.get("inventory", []):
        rows.append(
            {
                key: value
                for key, value in item.items()
                if key not in {"object", "annotation_object", "room_text_object"}
            }
        )
    return {
        "revision": analysis.get("revision", EXTRACTION_REVISION),
        "document_name": analysis.get("document_name", ""),
        "document_label": analysis.get("document_label", ""),
        "counts": analysis.get("counts", {}),
        "inventory": rows,
    }


def write_json_report(path, analysis):
    target = os.path.abspath(os.path.expanduser(str(path)))
    with open(target, "w", encoding="utf-8") as stream:
        json.dump(serializable_report(analysis), stream, ensure_ascii=False, indent=2)
    return target
