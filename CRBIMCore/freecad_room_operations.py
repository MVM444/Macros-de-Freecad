"""Thin FreeCAD adapter for the common room operations.

The adapter has no FreeCADGui or Qt dependency.  Selection and dialogs remain
in ``CRBIMCore.commands.common_rooms``.
"""

from __future__ import annotations

from . import room_operations_core as operations
from . import room_resolver_core as resolver
from .freecad_room_adapter import resolve_room_for_object, resolve_room_for_point, resolve_room_reference


def _text(value):
    try:
        return str(value or "").strip()
    except Exception:
        return ""


def _object_name(obj):
    return _text(getattr(obj, "Name", ""))


def _linked_name(value):
    return _object_name(value) or _text(getattr(value, "Label", "")) if value is not None else ""


def _metadata(obj):
    if obj is None:
        return {}
    base = getattr(obj, "Base", None) or getattr(obj, "BaseGeometry", None)
    geometry_source = _text(getattr(obj, "FA_GeometrySource", ""))
    if not geometry_source:
        geometry_source = _text(getattr(obj, "FA_GeometryType", ""))
    if not geometry_source:
        geometry_source = _text(getattr(obj, "TypeId", ""))
    return {
        "label": _text(getattr(obj, "Label", "")),
        "base_name": _linked_name(base),
        "geometry_source": geometry_source,
    }


def _ambiguous(results):
    alternatives = []
    seen = set()
    for result in results:
        if result.get("status") == resolver.STATUS_AMBIGUOUS:
            values = result.get("alternatives") or []
        elif result.get("status") == resolver.STATUS_RESOLVED:
            values = [result]
        else:
            values = []
        for item in values:
            name = _text(item.get("object_name"))
            if not name or name in seen:
                continue
            seen.add(name)
            alternatives.append(
                {
                    key: item.get(key)
                    for key in (
                        "source_kind", "room_uid", "room_id", "name", "object_name",
                        "level", "area_m2", "centroid_mm", "confidence",
                        "is_native_space", "is_legacy",
                    )
                }
            )
    return {
        "schema_version": resolver.SCHEMA_VERSION,
        "status": resolver.STATUS_AMBIGUOUS,
        "source_kind": "",
        "room_uid": "",
        "room_id": "",
        "name": "",
        "object_name": "",
        "level": "",
        "area_m2": 0.0,
        "centroid_mm": [],
        "polygon_mm": [],
        "confidence": 0.0,
        "is_native_space": False,
        "is_legacy": False,
        "diagnostics": ["MULTIPLE_SELECTION_ROOM_IDENTITIES"],
        "alternatives": alternatives,
    }


def resolve_selected_objects(doc, objects):
    """Resolve the current selection without writing to the document."""
    selected = [obj for obj in list(objects or []) if obj is not None]
    if not selected:
        return resolver.resolve_room_for_object([], {})
    results = [resolve_room_for_object(doc, obj) for obj in selected]
    resolved_names = {
        _text(result.get("object_name"))
        for result in results
        if result.get("status") == resolver.STATUS_RESOLVED and _text(result.get("object_name"))
    }
    ambiguous = [result for result in results if result.get("status") == resolver.STATUS_AMBIGUOUS]
    if len(resolved_names) == 1 and not ambiguous:
        return next(result for result in results if result.get("object_name") in resolved_names)
    if len(resolved_names) > 1 or ambiguous:
        return _ambiguous(results)
    return results[0]


def resolve_clicked_point(doc, point_mm):
    return resolve_room_for_point(doc, point_mm)


def physical_object(doc, resolution):
    name = _text(dict(resolution or {}).get("object_name"))
    return doc.getObject(name) if doc is not None and name else None


def room_info(doc, resolution):
    """Return JSON-compatible room information; this operation is read-only."""
    obj = physical_object(doc, resolution)
    return operations.room_info_record(resolution, _metadata(obj))


def _direct_target(doc, obj):
    object_name = _object_name(obj)
    result = resolve_room_reference(doc, obj)
    direct = bool(
        result.get("status") == resolver.STATUS_RESOLVED
        and _text(result.get("object_name")) == object_name
    )
    return {
        "object_name": object_name,
        "label": _text(getattr(obj, "Label", "")),
        "source_kind": _text(result.get("source_kind")),
        "is_direct_physical_room": direct,
        "reason": "" if direct else ";".join(result.get("diagnostics") or []) or "NOT_A_DIRECT_PHYSICAL_ROOM",
    }


def prepare_room_label_change(doc, objects, new_label):
    targets = [_direct_target(doc, obj) for obj in list(objects or []) if obj is not None]
    return operations.plan_label_changes(targets, new_label)


def apply_room_labels(doc, objects, new_label, dry_run=True):
    """Apply one Label-only transaction to valid direct Space/Area objects."""
    plan = prepare_room_label_change(doc, objects, new_label)
    plan["dry_run"] = bool(dry_run)
    plan["applied"] = 0
    if dry_run or not plan.get("accepted") or not plan.get("changed"):
        return plan
    by_name = {_object_name(obj): obj for obj in list(objects or []) if obj is not None}
    opened = False
    document_preferences = None
    duplicate_labels_before = None
    try:
        # FreeCAD makes Label unique by default.  The user-facing room name is
        # allowed to repeat, so enable the native preference only while assigning
        # labels and restore it unconditionally before returning.
        import FreeCAD as App

        document_preferences = App.ParamGet("User parameter:BaseApp/Preferences/Document")
        duplicate_labels_before = document_preferences.GetBool("DuplicateLabels", False)
        document_preferences.SetBool("DuplicateLabels", True)
        doc.openTransaction("CRBIM: Nombrar recinto")
        opened = True
        for item in plan["accepted"]:
            if not item.get("will_change"):
                continue
            obj = by_name.get(item["object_name"])
            if obj is None:
                raise RuntimeError("El recinto dejo de existir: %s" % item["object_name"])
            obj.Label = plan["new_label"]
            if _text(getattr(obj, "Label", "")) != plan["new_label"]:
                raise RuntimeError("FreeCAD no permitio conservar el Label solicitado en %s" % obj.Name)
            plan["applied"] += 1
        doc.recompute()
        doc.commitTransaction()
        opened = False
        plan["status"] = "APPLIED"
        return plan
    except Exception:
        if opened:
            try:
                doc.abortTransaction()
            except Exception:
                pass
        raise
    finally:
        if document_preferences is not None and duplicate_labels_before is not None:
            try:
                document_preferences.SetBool("DuplicateLabels", bool(duplicate_labels_before))
            except Exception:
                pass


def standard_room_names(doc):
    """Read the compatible NombresEstandar sheet without creating or editing it."""
    sheet = doc.getObject("NombresEstandar") if doc is not None else None
    names = []
    if sheet is not None:
        for row in range(1, 1001):
            try:
                value = _text(sheet.get("A%d" % row))
            except Exception:
                break
            if not value:
                break
            if value not in names:
                names.append(value)
    return names or list(operations.DEFAULT_ROOM_NAMES)


__all__ = [
    "apply_room_labels",
    "physical_object",
    "prepare_room_label_change",
    "resolve_clicked_point",
    "resolve_selected_objects",
    "room_info",
    "standard_room_names",
]
