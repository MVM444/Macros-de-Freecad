"""JSON-compatible element data contracts and geometric matching.

This module deliberately has no FreeCAD, FreeCADGui or Qt dependency.  The
supported categories are ``windows`` and ``doors``; the common contract is kept small so
equipment and other element families can reuse it without inheriting GUI code.
"""

from __future__ import annotations

import json
import math


SCHEMA_VERSION = 1
CATEGORY_WINDOWS = "windows"
CATEGORY_DOORS = "doors"
VALID_STATUSES = ("MATCH", "CAMBIO", "NO_MATCH", "AMBIGUO")

COMMON_FIELDS = (
    "SchemaVersion",
    "ElementID",
    "Category",
    "SourceSketch",
    "GeometryIndex",
    "CenterX",
    "CenterY",
    "Length",
    "AngleDeg",
    "LevelKey",
    "RoomKey",
    "GeneratedBy",
    "Notes",
)
WINDOW_FIELDS = (
    "Height",
    "SillHeight",
    "Preset",
    "Opening",
    "Frame",
    "Offset",
    "IfcType",
)
DOOR_FIELDS = (
    "Height",
    "DoorType",
    "TypeSource",
    "TypeRef",
    "Preset",
    "LeafCount",
    "HingeEndpoint",
    "HingePointX",
    "HingePointY",
    "OpeningSide",
    "OpensInward",
    "Opening",
    "Frame",
    "Offset",
    "IfcType",
)

DEFAULT_TOLERANCE = {
    "center_mm": 250.0,
    "angle_deg": 7.5,
    "length_mm": 600.0,
    "length_ratio": 0.50,
    "change_center_mm": 1.0,
    "change_angle_deg": 0.25,
    "change_length_mm": 1.0,
    "ambiguity_score": 0.05,
}


def normalize_category(category):
    text = str(category or "").strip().lower()
    if text in ("window", "windows", "ventana", "ventanas"):
        return CATEGORY_WINDOWS
    if text in ("door", "doors", "puerta", "puertas"):
        return CATEGORY_DOORS
    raise ValueError("Categoria no soportada: %s" % category)


def normalize_record(category, record):
    """Return one JSON-compatible record with stable field types."""
    category = normalize_category(category)
    source = dict(record or {})
    normalized = {
        "SchemaVersion": _as_int(source.get("SchemaVersion"), SCHEMA_VERSION),
        "ElementID": str(source.get("ElementID") or "").strip(),
        "Category": category,
        "SourceSketch": str(source.get("SourceSketch") or "").strip(),
        "GeometryIndex": _optional_int(source.get("GeometryIndex")),
        "CenterX": _optional_float(source.get("CenterX")),
        "CenterY": _optional_float(source.get("CenterY")),
        "Length": _optional_float(source.get("Length", source.get("WidthSketch"))),
        "AngleDeg": _optional_float(source.get("AngleDeg")),
        "LevelKey": str(source.get("LevelKey", source.get("Level")) or "").strip(),
        "RoomKey": str(source.get("RoomKey", source.get("Room")) or "").strip(),
        "GeneratedBy": str(source.get("GeneratedBy") or "").strip(),
        "Notes": str(source.get("Notes") or ""),
    }
    if category == CATEGORY_WINDOWS:
        normalized.update(
            {
                "Height": _optional_float(source.get("Height")),
                "SillHeight": _optional_float(source.get("SillHeight")),
                "Preset": str(source.get("Preset") or "").strip(),
                "Opening": _optional_float(source.get("Opening")),
                "Frame": _optional_float(source.get("Frame")),
                "Offset": _optional_float(source.get("Offset")),
                "IfcType": str(source.get("IfcType") or "Window").strip() or "Window",
            }
        )
    elif category == CATEGORY_DOORS:
        normalized.update(
            {
                "Height": _optional_float(source.get("Height")),
                "DoorType": str(source.get("DoorType") or "").strip(),
                "TypeSource": str(source.get("TypeSource") or "").strip(),
                "TypeRef": str(source.get("TypeRef") or "").strip(),
                "Preset": str(source.get("Preset") or "").strip(),
                "LeafCount": _optional_int(source.get("LeafCount")),
                "HingeEndpoint": _normalize_hinge_endpoint(source.get("HingeEndpoint")),
                "HingePointX": _optional_float(source.get("HingePointX")),
                "HingePointY": _optional_float(source.get("HingePointY")),
                "OpeningSide": _normalize_opening_side(source.get("OpeningSide")),
                "OpensInward": _optional_bool(source.get("OpensInward")),
                "Opening": _optional_float(source.get("Opening")),
                "Frame": _optional_float(source.get("Frame")),
                "Offset": _optional_float(source.get("Offset")),
                "IfcType": str(source.get("IfcType") or "Door").strip() or "Door",
            }
        )
    return normalized


def build_table_data(category, records):
    """Normalize records for a visible category table."""
    category = normalize_category(category)
    return [normalize_record(category, item) for item in (records or [])]


def serialize_records(records, category=CATEGORY_WINDOWS, project_key=""):
    """Return the stable JSON-compatible envelope used by MCP and tests."""
    category = normalize_category(category)
    data = build_table_data(category, records)
    return {
        "schema_version": SCHEMA_VERSION,
        "project_key": str(project_key or ""),
        "categories": {category: data},
    }


def deserialize_records(payload, category=CATEGORY_WINDOWS):
    """Read either a serialized envelope, JSON text, or a plain record list."""
    category = normalize_category(category)
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = (payload.get("categories") or {}).get(category, [])
    else:
        raise TypeError("Los datos deben ser JSON, dict o list")
    return build_table_data(category, records)


def validate_records(category, records, geometry_source, tolerance=None):
    """Match table rows to current geometry without modifying either source.

    ``geometry_source`` is a list of JSON-compatible line records.  Accepted
    matches are always unique.  A changed width remains a safe match but is
    reported as ``CAMBIO`` so the caller can show that destination geometry is
    authoritative.
    """
    category = normalize_category(category)
    rows = build_table_data(category, records)
    geometry = [_normalize_geometry(item) for item in (geometry_source or [])]
    tol = dict(DEFAULT_TOLERANCE)
    tol.update(dict(tolerance or {}))
    entries = []
    counts = {name: 0 for name in VALID_STATUSES}
    element_id_counts = {}
    for row in rows:
        element_id = row.get("ElementID") or ""
        if element_id:
            element_id_counts[element_id] = element_id_counts.get(element_id, 0) + 1

    for row_index, row in enumerate(rows):
        element_id = row.get("ElementID") or ""
        duplicate_id = bool(element_id and element_id_counts.get(element_id, 0) > 1)
        invalid_reason = _record_error(category, row)
        if invalid_reason:
            result = {"status": "NO_MATCH", "reason": invalid_reason, "match": None, "candidates": []}
        else:
            result = _match_one(row, geometry, tol)
        if duplicate_id:
            result = {
                "status": "AMBIGUO",
                "reason": "ElementID duplicado en la tabla",
                "match": None,
                "candidates": [],
            }
        status = result["status"]
        counts[status] += 1
        entries.append(
            {
                "row_index": row_index,
                "element_id": element_id,
                "status": status,
                "reason": result["reason"],
                "record": row,
                "matched_geometry": result.get("match"),
                "candidate_count": len(result.get("candidates") or []),
            }
        )

    geometry_claims = {}
    for entry in entries:
        match = entry.get("matched_geometry")
        if entry["status"] not in ("MATCH", "CAMBIO") or not match:
            continue
        key = (str(match.get("SourceSketch") or ""), int(match.get("GeometryIndex")))
        geometry_claims.setdefault(key, []).append(entry)
    for key, claims in geometry_claims.items():
        if len(claims) < 2:
            continue
        for entry in claims:
            counts[entry["status"]] -= 1
            counts["AMBIGUO"] += 1
            entry["status"] = "AMBIGUO"
            entry["reason"] = "Varias filas reclaman la misma geometria %s:%s" % key
            entry["matched_geometry"] = None

    return {
        "category": category,
        "dry_run": True,
        "record_count": len(rows),
        "geometry_count": len(geometry),
        "counts": counts,
        "entries": entries,
        "tolerance": tol,
    }


def plan_application(category, records, geometry_source, tolerance=None):
    """Return safe application plans; ambiguous and unmatched rows are omitted."""
    report = validate_records(category, records, geometry_source, tolerance=tolerance)
    plans = []
    skipped = []
    for entry in report["entries"]:
        if entry["status"] in ("MATCH", "CAMBIO"):
            plans.append(
                {
                    "row_index": entry["row_index"],
                    "status": entry["status"],
                    "record": entry["record"],
                    "geometry": entry["matched_geometry"],
                }
            )
        else:
            skipped.append(entry)
    return {"validation": report, "plans": plans, "skipped": skipped}


def extract_elements(category, document=None):
    """Compatibility entry point; extraction requires the FreeCAD adapter."""
    normalize_category(category)
    if document is None:
        raise RuntimeError("extract_elements requiere el adaptador FreeCAD")
    extractor = getattr(document, "extract_elements", None)
    if not callable(extractor):
        raise RuntimeError("El adaptador no expone extract_elements")
    return extractor(category)


def apply_records(category, records, geometry_source, dry_run=True, tolerance=None, adapter=None):
    """Plan by default; delegate writes only to an explicit adapter."""
    plan = plan_application(category, records, geometry_source, tolerance=tolerance)
    if dry_run:
        return plan
    if adapter is None or not callable(adapter):
        raise RuntimeError("apply_records(dry_run=False) requiere un adaptador explicito")
    return adapter(plan)


def _match_one(row, geometry, tol):
    index = row.get("GeometryIndex")
    source = row.get("SourceSketch") or ""
    direct = []
    if index is not None:
        direct = [
            item
            for item in geometry
            if item["GeometryIndex"] == index
            and (not source or item["SourceSketch"] == source)
        ]
    direct = [item for item in direct if _compatible(row, item, tol, direct_index=True)]
    if len(direct) == 1:
        return _accepted(row, direct[0], tol, index_matched=True)
    if len(direct) > 1:
        return {
            "status": "AMBIGUO",
            "reason": "SourceSketch + GeometryIndex identifica varios candidatos",
            "match": None,
            "candidates": direct,
        }

    candidates = [item for item in geometry if _compatible(row, item, tol, direct_index=False)]
    if not candidates:
        return {"status": "NO_MATCH", "reason": "Sin geometria dentro de tolerancia", "match": None, "candidates": []}
    ranked = sorted((_score(row, item, tol), item) for item in candidates)
    if len(ranked) > 1:
        first, second = ranked[0][0], ranked[1][0]
        if abs(second - first) <= float(tol["ambiguity_score"]):
            return {
                "status": "AMBIGUO",
                "reason": "Dos candidatos geometricos equivalentes",
                "match": None,
                "candidates": [item for _score_value, item in ranked],
            }
    return _accepted(row, ranked[0][1], tol, index_matched=False)


def _accepted(row, match, tol, index_matched):
    changes = []
    for field, limit in (
        ("CenterX", tol["change_center_mm"]),
        ("CenterY", tol["change_center_mm"]),
        ("Length", tol["change_length_mm"]),
    ):
        if row.get(field) is not None and abs(row[field] - match[field]) > float(limit):
            changes.append(field)
    if row.get("AngleDeg") is not None and _angle_delta(row["AngleDeg"], match["AngleDeg"]) > float(tol["change_angle_deg"]):
        changes.append("AngleDeg")
    if not index_matched:
        changes.append("GeometryIndex")
    status = "CAMBIO" if changes else "MATCH"
    return {
        "status": status,
        "reason": "Geometria segura; cambios: %s" % ", ".join(changes) if changes else "Coincidencia geometrica",
        "match": dict(match),
        "candidates": [match],
    }


def _compatible(row, item, tol, direct_index=False):
    has_center = row.get("CenterX") is not None and row.get("CenterY") is not None
    if has_center:
        center = math.hypot(row["CenterX"] - item["CenterX"], row["CenterY"] - item["CenterY"])
        if center > float(tol["center_mm"]):
            return False
    elif not direct_index:
        return False
    if row.get("AngleDeg") is not None and _angle_delta(row["AngleDeg"], item["AngleDeg"]) > float(tol["angle_deg"]):
        return False
    if row.get("Length") is not None:
        maximum = max(float(tol["length_mm"]), abs(row["Length"]) * float(tol["length_ratio"]))
        if abs(row["Length"] - item["Length"]) > maximum:
            return False
    return True


def _score(row, item, tol):
    center = 0.0
    if row.get("CenterX") is not None and row.get("CenterY") is not None:
        center = math.hypot(row["CenterX"] - item["CenterX"], row["CenterY"] - item["CenterY"]) / max(float(tol["center_mm"]), 1.0)
    angle = 0.0 if row.get("AngleDeg") is None else _angle_delta(row["AngleDeg"], item["AngleDeg"]) / max(float(tol["angle_deg"]), 1.0)
    length = 0.0 if row.get("Length") is None else abs(row["Length"] - item["Length"]) / max(float(tol["length_mm"]), 1.0)
    return center + angle + length * 0.5


def _normalize_geometry(item):
    source = dict(item or {})
    return {
        "SourceSketch": str(source.get("SourceSketch") or "").strip(),
        "GeometryIndex": _as_int(source.get("GeometryIndex"), -1),
        "CenterX": float(source.get("CenterX", 0.0)),
        "CenterY": float(source.get("CenterY", 0.0)),
        "Length": float(source.get("Length", source.get("WidthSketch", 0.0))),
        "AngleDeg": _normalize_angle(float(source.get("AngleDeg", 0.0))),
    }


def _record_error(category, row):
    if not row.get("ElementID"):
        return "ElementID requerido"
    if category == CATEGORY_WINDOWS:
        if row.get("Height") is not None and row["Height"] <= 0.0:
            return "Height debe ser mayor que cero"
        if row.get("SillHeight") is not None and row["SillHeight"] < 0.0:
            return "SillHeight no puede ser negativo"
        if row.get("Opening") is not None and not 0.0 <= row["Opening"] <= 100.0:
            return "Opening debe estar entre 0 y 100"
    elif category == CATEGORY_DOORS:
        if row.get("Height") is not None and row["Height"] <= 0.0:
            return "Height debe ser mayor que cero"
        if row.get("LeafCount") is not None and row["LeafCount"] <= 0:
            return "LeafCount debe ser mayor que cero"
        if row.get("Opening") is not None and not 0.0 <= row["Opening"] <= 100.0:
            return "Opening debe estar entre 0 y 100"
        if not (row.get("DoorType") or row.get("Preset") or row.get("TypeRef")):
            return "DoorType, Preset o TypeRef requerido"
    return ""


def _normalize_angle(value):
    value = float(value) % 180.0
    return value + 180.0 if value < 0.0 else value


def _angle_delta(first, second):
    delta = abs(_normalize_angle(first) - _normalize_angle(second))
    return min(delta, 180.0 - delta)


def _normalize_hinge_endpoint(value):
    text = str(value or "AUTO").strip().upper()
    aliases = {
        "0": "START",
        "1": "END",
        "INICIO": "START",
        "START": "START",
        "FIN": "END",
        "END": "END",
        "AMBOS": "BOTH",
        "BOTH": "BOTH",
        "AUTO": "AUTO",
        "AUTOMATICO": "AUTO",
    }
    return aliases.get(text, text or "AUTO")


def _normalize_opening_side(value):
    text = str(value or "AUTO").strip().upper()
    aliases = {
        "IZQUIERDA": "LEFT",
        "LEFT": "LEFT",
        "DERECHA": "RIGHT",
        "RIGHT": "RIGHT",
        "INTERIOR": "IN",
        "IN": "IN",
        "EXTERIOR": "OUT",
        "OUT": "OUT",
        "AUTO": "AUTO",
        "AUTOMATICO": "AUTO",
    }
    return aliases.get(text, text or "AUTO")


def _optional_bool(value):
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "si", "sí", "y"):
        return True
    if text in ("0", "false", "no", "n"):
        return False
    return None


def _optional_float(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(getattr(value, "Value", value))
    except (TypeError, ValueError):
        return None


def _optional_int(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_int(value, default):
    result = _optional_int(value)
    return int(default if result is None else result)
