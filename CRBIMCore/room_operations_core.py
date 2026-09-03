"""Pure room-operation contracts shared by the CR FreeCAD workbenches.

This module intentionally has no FreeCAD, FreeCADGui or Qt dependency.  Every
public result is JSON-compatible so the same decisions can be tested outside
FreeCAD and reused by more than one workbench.
"""

from __future__ import annotations

from . import room_resolver_core as resolver


SCHEMA_VERSION = 1
DEFAULT_ROOM_NAMES = (
    "Oficina",
    "Sala de Espera",
    "Bodega",
    "Recepcion",
    "Pasillo",
)


def _text(value):
    try:
        return str(value or "").strip()
    except Exception:
        return ""


def _number(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def room_info_record(resolution, metadata=None):
    """Build a stable, read-only information record from a resolver result."""
    result = dict(resolution or {})
    meta = dict(metadata or {})
    source_kind = _text(result.get("source_kind"))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": _text(result.get("status")) or resolver.STATUS_NOT_FOUND,
        "source_kind": source_kind,
        "source_label": (
            "Space"
            if source_kind == resolver.SOURCE_NATIVE_SPACE
            else "Area legacy"
            if source_kind == resolver.SOURCE_LEGACY_AREA
            else ""
        ),
        "object_name": _text(result.get("object_name")),
        "label": _text(meta.get("label")) or _text(result.get("name")),
        "area_m2": _number(result.get("area_m2")),
        "room_uid": _text(result.get("room_uid")),
        "room_id": _text(result.get("room_id")),
        "level": _text(result.get("level")),
        "base_name": _text(meta.get("base_name")),
        "geometry_source": _text(meta.get("geometry_source")),
        "diagnostics": [str(value) for value in list(result.get("diagnostics") or [])],
        "alternatives": [dict(value) for value in list(result.get("alternatives") or [])],
    }


def format_room_info(info):
    """Return concise user-facing text without depending on a GUI toolkit."""
    record = dict(info or {})
    lines = ["Estado: %s" % (_text(record.get("status")) or resolver.STATUS_NOT_FOUND)]
    if record.get("source_label"):
        lines.append("Fuente: %s" % record["source_label"])
    if record.get("object_name"):
        lines.append("Name: %s" % record["object_name"])
    if record.get("label"):
        lines.append("Label: %s" % record["label"])
    if record.get("source_kind"):
        lines.append("Tipo: %s" % record["source_kind"])
    if _number(record.get("area_m2")) > 0.0:
        lines.append("Area: %.3f m2" % _number(record.get("area_m2")))
    if record.get("room_uid"):
        lines.append("FA_RoomUID: %s" % record["room_uid"])
    if record.get("room_id"):
        lines.append("FA_RoomID: %s" % record["room_id"])
    if record.get("level"):
        lines.append("Level: %s" % record["level"])
    if record.get("base_name"):
        lines.append("Base: %s" % record["base_name"])
    if record.get("geometry_source"):
        lines.append("Geometria: %s" % record["geometry_source"])
    alternatives = list(record.get("alternatives") or [])
    if alternatives:
        names = [
            "%s (%s)" % (_text(item.get("object_name")), _text(item.get("source_kind")))
            for item in alternatives
        ]
        lines.append("Candidatos: %s" % ", ".join(name for name in names if name.strip(" ()")))
    return "\n".join(lines)


def plan_label_changes(targets, new_label):
    """Validate direct physical-room targets and plan Label-only changes."""
    label = _text(new_label)
    accepted = []
    rejected = []
    if not label:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "INVALID",
            "new_label": "",
            "accepted": [],
            "rejected": [{"object_name": "", "reason": "EMPTY_LABEL"}],
            "changed": 0,
        }
    seen = set()
    for value in list(targets or []):
        target = dict(value or {})
        object_name = _text(target.get("object_name"))
        if not object_name or object_name in seen:
            if object_name:
                rejected.append({"object_name": object_name, "reason": "DUPLICATE_TARGET"})
            continue
        seen.add(object_name)
        source_kind = _text(target.get("source_kind"))
        if not bool(target.get("is_direct_physical_room")) or source_kind not in {
            resolver.SOURCE_NATIVE_SPACE,
            resolver.SOURCE_LEGACY_AREA,
        }:
            rejected.append(
                {
                    "object_name": object_name,
                    "label": _text(target.get("label")),
                    "reason": _text(target.get("reason")) or "NOT_A_DIRECT_PHYSICAL_ROOM",
                }
            )
            continue
        accepted.append(
            {
                "object_name": object_name,
                "source_kind": source_kind,
                "old_label": _text(target.get("label")),
                "new_label": label,
                "will_change": _text(target.get("label")) != label,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "READY" if accepted else "REJECTED",
        "new_label": label,
        "accepted": accepted,
        "rejected": rejected,
        "changed": sum(1 for item in accepted if item["will_change"]),
    }


def guide_text():
    return (
        "1. Obtenga el recinto con las herramientas del Workbench activo.\n"
        "2. Un Space BIM es la identidad fisica preferida; una Area valida es el fallback compatible.\n"
        "3. Seleccionar recinto resuelve la seleccion actual o un punto, sin crear objetos.\n"
        "4. Info recinto es solo lectura. Nombrar recinto cambia unicamente Label.\n"
        "5. Facil Arquitectura detecta contornos 2D y crea o actualiza Spaces BIM.\n"
        "6. ElectricCR y MEP consumen la misma identidad mediante CRBIMCore.\n"
        "7. AMBIGUOUS significa que hay varios recintos plausibles y no se elige ninguno.\n"
        "8. NOT_FOUND significa que no existe un recinto fisico valido; no se crea ni asigna nada."
    )


__all__ = [
    "DEFAULT_ROOM_NAMES",
    "format_room_info",
    "guide_text",
    "plan_label_changes",
    "room_info_record",
]
