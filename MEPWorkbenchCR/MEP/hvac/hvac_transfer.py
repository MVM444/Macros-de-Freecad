"""Idempotent HVAC transfer between compatible FreeCAD documents.

The transfer copies only objects carrying an HVAC ``MEPType`` marker.  Spatial
geometry is explicitly reconciled with authoritative objects in the target
document so recursive document copies cannot pull walls or other disciplines.
"""

import os
import unicodedata
import uuid
from collections import Counter

import FreeCAD as App

from ..utils import draft_text_compat


TRANSFER_KEY_PROP = "CRTransferSourceKey"
TRANSFER_DOC_PROP = "CRTransferSourceDocument"
TRANSFER_OBJECT_PROP = "CRTransferSourceObject"
PERSISTENT_ID_PROP = "PersistentId"
OWNER_PROP = "Owner"
ROLE_PROP = "RepresentationRole"

LINK_PROPERTIES = {
    "BaseSpace",
    "Project",
    "RoomLabel",
    "Space",
    "Symbol2D",
    "Info2D",
    "Ports",
    "LinkedObject",
    "System",
    "Circuit",
    "Panel",
    "Host",
    "BuildingStorey",
    "StartPort",
    "EndPort",
    "UpstreamEquipment",
}

SCALAR_SKIP = {
    "ExpressionEngine",
    "Label",
    "Placement",
    "Proxy",
    "Visibility",
}


def _mep_type(obj):
    if obj is None:
        return ""
    try:
        if "MEPType" in list(getattr(obj, "PropertiesList", []) or []):
            return str(getattr(obj, "MEPType", "") or "")
    except Exception:
        pass
    return ""


def _is_hvac(obj):
    return _mep_type(obj).startswith("HVAC")


def _is_group(obj):
    type_id = str(getattr(obj, "TypeId", "") or "")
    return type_id.startswith("App::DocumentObjectGroup") or (
        hasattr(obj, "Group") and hasattr(obj, "addObject")
    )


def _normalize(value):
    text = str(value or "").strip().lower()
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return " ".join(text.split())


def _source_document_id(doc):
    filename = str(getattr(doc, "FileName", "") or "")
    if filename:
        return os.path.splitext(os.path.basename(filename))[0]
    return str(getattr(doc, "Name", "") or "HVAC_Source")


def _source_key(source_doc, source_obj):
    return "{0}::{1}".format(_source_document_id(source_doc), source_obj.Name)


def _persistent_id(source_doc, source_obj):
    key = "freecad-cr:hvac:{0}".format(_source_key(source_doc, source_obj))
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def _shape_signature(obj):
    if obj is None:
        return None
    try:
        shape = obj.Shape
        if bool(getattr(shape, "isNull", lambda: True)()):
            return None
        bbox = shape.BoundBox
        return (
            round(float(shape.Area), 2),
            round(float(bbox.XMin), 2),
            round(float(bbox.YMin), 2),
            round(float(bbox.XMax), 2),
            round(float(bbox.YMax), 2),
        )
    except Exception:
        return None


def _placement_xyz(obj):
    try:
        placement = obj.getGlobalPlacement() if hasattr(obj, "getGlobalPlacement") else obj.Placement
        point = placement.Base
        return (round(float(point.x), 2), round(float(point.y), 2), round(float(point.z), 2))
    except Exception:
        return None


def _ensure_property(obj, property_type, name, group, description):
    if name not in list(getattr(obj, "PropertiesList", []) or []):
        obj.addProperty(property_type, name, group, description)
    return name in list(getattr(obj, "PropertiesList", []) or [])


def _set_transfer_identity(target_obj, source_doc, source_obj):
    key = _source_key(source_doc, source_obj)
    _ensure_property(
        target_obj,
        "App::PropertyString",
        TRANSFER_KEY_PROP,
        "CR Transfer",
        "Stable source identity used for idempotent document transfer",
    )
    _ensure_property(
        target_obj,
        "App::PropertyString",
        TRANSFER_DOC_PROP,
        "CR Transfer",
        "Source FreeCAD document",
    )
    _ensure_property(
        target_obj,
        "App::PropertyString",
        TRANSFER_OBJECT_PROP,
        "CR Transfer",
        "Source FreeCAD object name",
    )
    target_obj.CRTransferSourceKey = key
    target_obj.CRTransferSourceDocument = _source_document_id(source_doc)
    target_obj.CRTransferSourceObject = str(source_obj.Name)

    if _is_hvac(source_obj):
        _ensure_property(
            target_obj,
            "App::PropertyString",
            PERSISTENT_ID_PROP,
            "CR Identity",
            "Stable UUID for reconciliation and export",
        )
        if not str(getattr(target_obj, PERSISTENT_ID_PROP, "") or ""):
            target_obj.PersistentId = _persistent_id(source_doc, source_obj)
    return key


def _find_by_transfer_key(doc, key):
    matches = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if TRANSFER_KEY_PROP not in list(getattr(obj, "PropertiesList", []) or []):
            continue
        try:
            if str(getattr(obj, TRANSFER_KEY_PROP, "") or "") == key:
                matches.append(obj)
        except Exception:
            continue
    if len(matches) > 1:
        raise RuntimeError("Identidad de transferencia duplicada: {0}".format(key))
    return matches[0] if matches else None


def _find_existing_hvac(source_doc, source_obj, target_doc):
    key = _source_key(source_doc, source_obj)
    matched = _find_by_transfer_key(target_doc, key)
    if matched is not None:
        return matched

    mep_type = _mep_type(source_obj)
    candidates = [obj for obj in target_doc.Objects if _mep_type(obj) == mep_type]
    if _is_group(source_obj) or mep_type == "HVACProject":
        if len(candidates) == 1:
            return candidates[0]

    if mep_type == "HVACEquipment":
        model = str(getattr(source_obj, "Model", "") or "")
        xyz = _placement_xyz(source_obj)
        for obj in candidates:
            if str(getattr(obj, "Model", "") or "") != model:
                continue
            if _placement_xyz(obj) == xyz:
                return obj

    if mep_type in {
        "HVACEvaporatorMaster",
        "HVACCADReference",
        "HVACCADReconciliation",
        "HVACCADUpdateMetadata",
    }:
        source_label = _normalize(getattr(source_obj, "Label", ""))
        label_matches = [
            obj for obj in candidates if _normalize(getattr(obj, "Label", "")) == source_label
        ]
        if len(label_matches) == 1:
            return label_matches[0]
    return None


def _copy_view_state(source_obj, target_obj):
    source_view = getattr(source_obj, "ViewObject", None)
    target_view = getattr(target_obj, "ViewObject", None)
    if source_view is None or target_view is None:
        return
    for prop in (
        "Visibility",
        "ShapeColor",
        "LineColor",
        "PointColor",
        "TextColor",
        "LineWidth",
        "PointSize",
        "Transparency",
        "FontSize",
        "DisplayMode",
        "ShowInTree",
        "Selectable",
    ):
        if not hasattr(source_view, prop) or not hasattr(target_view, prop):
            continue
        try:
            setattr(target_view, prop, getattr(source_view, prop))
        except Exception:
            continue


def _sync_scalar_properties(source_obj, target_obj):
    try:
        target_obj.Label = str(getattr(source_obj, "Label", "") or source_obj.Name)
    except Exception:
        pass

    for prop in list(getattr(source_obj, "PropertiesList", []) or []):
        if prop in SCALAR_SKIP or prop in LINK_PROPERTIES:
            continue
        if prop.startswith("_") or prop.startswith("CRTransfer"):
            continue
        try:
            property_type = str(source_obj.getTypeIdOfProperty(prop) or "")
        except Exception:
            property_type = ""
        if "Link" in property_type:
            continue
        if prop not in list(getattr(target_obj, "PropertiesList", []) or []):
            continue
        try:
            if hasattr(target_obj, "getEditorMode") and target_obj.getEditorMode(prop) == 1:
                continue
        except Exception:
            pass
        try:
            setattr(target_obj, prop, getattr(source_obj, prop))
        except Exception:
            continue

    try:
        target_obj.Placement = source_obj.Placement
    except Exception:
        pass
    _copy_view_state(source_obj, target_obj)


def _copy_shallow(target_doc, source_obj):
    copied = target_doc.copyObject(source_obj, False)
    if isinstance(copied, (list, tuple)):
        if not copied:
            return None
        return copied[0]
    return copied


def _mapped_object(source_ref, object_map, base_map):
    if source_ref is None:
        return None
    name = str(getattr(source_ref, "Name", "") or "")
    return object_map.get(name) or base_map.get(name)


def _sync_links(source_obj, target_obj, object_map, base_map):
    for prop in LINK_PROPERTIES:
        if prop not in list(getattr(source_obj, "PropertiesList", []) or []):
            continue
        if prop not in list(getattr(target_obj, "PropertiesList", []) or []):
            continue
        try:
            source_value = getattr(source_obj, prop)
        except Exception:
            continue

        try:
            property_type = str(source_obj.getTypeIdOfProperty(prop) or "")
        except Exception:
            property_type = ""

        try:
            if "LinkList" in property_type or prop == "Ports":
                mapped = []
                for item in list(source_value or []):
                    target_item = _mapped_object(item, object_map, base_map)
                    if target_item is not None and target_item not in mapped:
                        mapped.append(target_item)
                setattr(target_obj, prop, mapped)
            else:
                mapped = _mapped_object(source_value, object_map, base_map)
                setattr(target_obj, prop, mapped)
        except Exception:
            continue


def _ensure_representation_owner(rep_obj, owner_obj, role):
    if rep_obj is None or owner_obj is None:
        return
    _ensure_property(
        rep_obj,
        "App::PropertyLink",
        OWNER_PROP,
        "CR Representation",
        "Semantic owner of this representation",
    )
    _ensure_property(
        rep_obj,
        "App::PropertyString",
        ROLE_PROP,
        "CR Representation",
        "Role of this child representation",
    )
    rep_obj.Owner = owner_obj
    rep_obj.RepresentationRole = str(role)


def _resolve_base_map(source_doc, target_doc, base_name_map):
    base_map = {}
    created = []
    reused = []
    spaces = [obj for obj in source_doc.Objects if _mep_type(obj) == "HVACSpace"]
    for source_space in spaces:
        source_base = getattr(source_space, "BaseSpace", None)
        if source_base is None:
            raise RuntimeError("Espacio HVAC sin BaseSpace: {0}".format(source_space.Name))
        source_name = str(source_base.Name)
        target_name = str((base_name_map or {}).get(source_name, "") or "")
        target_base = target_doc.getObject(target_name) if target_name else None

        if target_base is None:
            key = _source_key(source_doc, source_base)
            target_base = _find_by_transfer_key(target_doc, key)
        if target_base is None:
            target_base = _copy_shallow(target_doc, source_base)
            if target_base is None:
                raise RuntimeError("No se pudo copiar base espacial: {0}".format(source_name))
            _set_transfer_identity(target_base, source_doc, source_base)
            created.append(target_base.Name)
        else:
            reused.append(target_base.Name)

        source_signature = _shape_signature(source_base)
        target_signature = _shape_signature(target_base)
        if source_signature is None or source_signature != target_signature:
            raise RuntimeError(
                "Base espacial incompatible {0} -> {1}: {2} != {3}".format(
                    source_name,
                    target_base.Name,
                    source_signature,
                    target_signature,
                )
            )
        base_map[source_name] = target_base
    return base_map, created, reused


def transfer_hvac(source_doc, target_doc, base_name_map=None):
    """Copy or update the complete HVAC system without duplicate identities."""

    if source_doc is None or target_doc is None:
        raise ValueError("Se requieren documentos de origen y destino")
    if source_doc is target_doc:
        raise ValueError("Origen y destino deben ser documentos distintos")

    source_hvac = [obj for obj in source_doc.Objects if _is_hvac(obj)]
    if not source_hvac:
        raise RuntimeError("El documento origen no contiene objetos HVAC")

    base_map, bases_created, bases_reused = _resolve_base_map(
        source_doc,
        target_doc,
        base_name_map or {},
    )

    object_map = {}
    created = []
    updated = []

    ordered = sorted(source_hvac, key=lambda obj: (0 if _is_group(obj) else 1, obj.Name))
    for source_obj in ordered:
        target_obj = _find_existing_hvac(source_doc, source_obj, target_doc)
        if target_obj is None:
            target_obj = _copy_shallow(target_doc, source_obj)
            if target_obj is None:
                raise RuntimeError("No se pudo copiar objeto HVAC: {0}".format(source_obj.Name))
            created.append(target_obj.Name)
        else:
            updated.append(target_obj.Name)
        object_map[source_obj.Name] = target_obj
        _set_transfer_identity(target_obj, source_doc, source_obj)

    # Resolve all semantic links only after every target object exists.
    for source_obj in ordered:
        target_obj = object_map[source_obj.Name]
        _sync_links(source_obj, target_obj, object_map, base_map)
        _sync_scalar_properties(source_obj, target_obj)

    # Preserve navigation groups without removing any unrelated target member.
    for source_group in [obj for obj in ordered if _is_group(obj)]:
        target_group = object_map[source_group.Name]
        for source_child in list(getattr(source_group, "Group", []) or []):
            target_child = object_map.get(source_child.Name)
            if target_child is None:
                continue
            try:
                if target_child not in list(getattr(target_group, "Group", []) or []):
                    target_group.addObject(target_child)
            except Exception:
                continue

    # Canonical Owner-role links make 2D representations independently auditable.
    for source_owner in [obj for obj in ordered if _mep_type(obj) == "HVACEquipment"]:
        target_owner = object_map[source_owner.Name]
        source_symbol = getattr(source_owner, "Symbol2D", None)
        source_info = getattr(source_owner, "Info2D", None)
        target_symbol = object_map.get(str(getattr(source_symbol, "Name", "") or ""))
        target_info = object_map.get(str(getattr(source_info, "Name", "") or ""))
        _ensure_representation_owner(target_symbol, target_owner, "Symbol2D")
        _ensure_representation_owner(target_info, target_owner, "Info2D")

    for source_label in [obj for obj in ordered if _mep_type(obj) == "HVACLabel"]:
        target_label = object_map[source_label.Name]
        source_space = getattr(source_label, "Space", None)
        target_space = object_map.get(str(getattr(source_space, "Name", "") or ""))
        _ensure_representation_owner(target_label, target_space, "SpaceLabel")

    draft_text_compat.repair_document(target_doc, mep_only=True)
    target_doc.recompute()
    target_doc.recompute()

    return {
        "source_hvac_count": len(source_hvac),
        "created": created,
        "updated": updated,
        "bases_created": bases_created,
        "bases_reused": bases_reused,
        "object_map": object_map,
        "base_map": base_map,
    }


def audit_transfer(source_doc, target_doc):
    """Validate identities, counts, links, roles and placements after transfer."""

    source_hvac = [obj for obj in source_doc.Objects if _is_hvac(obj)]
    target_hvac = [obj for obj in target_doc.Objects if _is_hvac(obj)]
    issues = []
    by_key = {}
    for obj in target_doc.Objects:
        if TRANSFER_KEY_PROP not in list(getattr(obj, "PropertiesList", []) or []):
            continue
        key = str(getattr(obj, TRANSFER_KEY_PROP, "") or "")
        if not key:
            continue
        by_key.setdefault(key, []).append(obj)
    duplicate_keys = sorted(key for key, values in by_key.items() if len(values) != 1)
    if duplicate_keys:
        issues.append("Identidades duplicadas: {0}".format(", ".join(duplicate_keys)))

    missing_keys = []
    placement_mismatches = []
    cross_document_links = []
    for source_obj in source_hvac:
        key = _source_key(source_doc, source_obj)
        matches = by_key.get(key, [])
        if len(matches) != 1:
            missing_keys.append(key)
            continue
        target_obj = matches[0]
        if _mep_type(source_obj) == "HVACEquipment":
            if _placement_xyz(source_obj) != _placement_xyz(target_obj):
                placement_mismatches.append(source_obj.Name)
        for prop in LINK_PROPERTIES:
            if prop not in list(getattr(target_obj, "PropertiesList", []) or []):
                continue
            try:
                value = getattr(target_obj, prop)
            except Exception:
                continue
            values = list(value or []) if isinstance(value, (list, tuple)) and prop == "Ports" else [value]
            for linked in values:
                linked_doc = getattr(linked, "Document", None)
                if linked is not None and linked_doc is not target_doc:
                    cross_document_links.append("{0}.{1}".format(target_obj.Name, prop))
    if missing_keys:
        issues.append("Objetos sin identidad unica: {0}".format(", ".join(missing_keys)))
    if placement_mismatches:
        issues.append("Placement distinto: {0}".format(", ".join(placement_mismatches)))
    if cross_document_links:
        issues.append("Enlaces externos: {0}".format(", ".join(cross_document_links)))

    owner_roles = Counter()
    equipment_without_rep = []
    for owner in [obj for obj in target_hvac if _mep_type(obj) == "HVACEquipment"]:
        symbol = getattr(owner, "Symbol2D", None)
        info = getattr(owner, "Info2D", None)
        if symbol is None or info is None:
            equipment_without_rep.append(owner.Name)
            continue
        owner_roles[(owner.Name, "Symbol2D")] += 1
        owner_roles[(owner.Name, "Info2D")] += 1
        if getattr(symbol, OWNER_PROP, None) is not owner:
            issues.append("Owner incorrecto en simbolo: {0}".format(owner.Name))
        if getattr(info, OWNER_PROP, None) is not owner:
            issues.append("Owner incorrecto en texto: {0}".format(owner.Name))
    if equipment_without_rep:
        issues.append("Equipos sin representacion: {0}".format(", ".join(equipment_without_rep)))

    source_counts = Counter(_mep_type(obj) for obj in source_hvac)
    target_counts = Counter(_mep_type(obj) for obj in target_hvac)
    for mep_type, expected in source_counts.items():
        if int(target_counts.get(mep_type, 0)) != int(expected):
            issues.append(
                "Conteo {0}: esperado {1}, obtenido {2}".format(
                    mep_type,
                    expected,
                    target_counts.get(mep_type, 0),
                )
            )

    return {
        "ok": not issues,
        "issues": issues,
        "source_hvac_count": len(source_hvac),
        "target_hvac_count": len(target_hvac),
        "source_counts": dict(sorted(source_counts.items())),
        "target_counts": dict(sorted(target_counts.items())),
        "duplicate_transfer_keys": duplicate_keys,
        "equipment_count": int(target_counts.get("HVACEquipment", 0)),
        "symbol2d_count": int(target_counts.get("HVACEquipment2D", 0)),
        "info2d_count": int(target_counts.get("HVACEquipmentInfo2D", 0)),
        "space_count": int(target_counts.get("HVACSpace", 0)),
        "space_label_count": int(target_counts.get("HVACLabel", 0)),
    }
