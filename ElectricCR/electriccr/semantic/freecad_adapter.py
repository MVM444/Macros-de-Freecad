"""FreeCAD adapter for one semantic ElectricCR luminaire prototype.

The adapter enriches the existing ``App::Link`` identity; it does not create a
parallel device class.  Tree projection is dry-run by default and treats
semantic links as authority instead of treating current visual membership as
source data.
"""

from __future__ import annotations

import hashlib
import uuid

from CRBIMCore import room_resolver_core as room_core
from CRBIMCore.freecad_room_adapter import resolve_room_for_point, resolve_room_reference
from ElectricCR.electriccr.features import objeto_toma_uno

from . import device_core


PROPERTY_GROUP = "ElectricCR Semantic"
PROJECTION_GROUP = "ElectricCR Projection"
ROOT_LABEL = "electrico"


def _text(value):
    try:
        return str(value or "").strip()
    except Exception:
        return ""


def _properties(obj):
    return set(getattr(obj, "PropertiesList", []) or [])


def _first_text(obj, names):
    for name in tuple(names or ()):
        if name not in _properties(obj):
            continue
        value = _text(getattr(obj, name, ""))
        if value:
            return value
    return ""


def _is_group(obj):
    return _text(getattr(obj, "TypeId", "")) == "App::DocumentObjectGroup"


def _direct_groups(parent):
    return [obj for obj in list(getattr(parent, "Group", []) or []) if _is_group(obj)]


def _is_native_space(obj):
    if obj is None:
        return False
    proxy_type = _text(getattr(getattr(obj, "Proxy", None), "Type", "")).casefold()
    ifc_type = _text(getattr(obj, "IfcType", "")).replace(" ", "").casefold()
    return proxy_type == "space" or ifc_type == "space"


def _space_name(space):
    for name in ("FA_RoomName", "LongName", "Label", "Name"):
        value = _text(getattr(space, name, ""))
        if value:
            return value
    return ""


def _identity_snapshot(obj):
    placement = obj.Placement
    linked = getattr(obj, "LinkedObject", None)
    return {
        "linked_name": _text(getattr(linked, "Name", "")),
        "placement": (
            float(placement.Base.x),
            float(placement.Base.y),
            float(placement.Base.z),
            tuple(float(value) for value in placement.Rotation.Q),
        ),
    }


def _assert_identity_unchanged(obj, before):
    after = _identity_snapshot(obj)
    if after != before:
        raise RuntimeError("La operacion semantica altero LinkedObject o Placement")


def is_semantic_luminaire_candidate(obj):
    return bool(
        obj is not None
        and _text(getattr(obj, "TypeId", "")) == "App::Link"
        and not (
            "ECR_ProjectionReference" in _properties(obj)
            and bool(getattr(obj, "ECR_ProjectionReference", False))
        )
        and objeto_toma_uno.is_electriccr_device(obj)
        and _first_text(obj, ("Tipo",)) == "Luminaria"
    )


def _uid_conflicts(doc, obj, uid):
    if not uid:
        return []
    return [
        other.Name
        for other in list(getattr(doc, "Objects", []) or [])
        if other is not obj
        and "ElementUID" in _properties(other)
        and _text(getattr(other, "ElementUID", "")) == uid
    ]


def ensure_luminaire_semantics(luminaire, dry_run=True, uid_factory=None):
    """Plan or apply ``ElementUID`` and canonical ``Space`` to one App::Link.

    ``AMBIGUOUS`` and ``NOT_FOUND`` never write ``Space``.  A resolved legacy
    area is diagnostic only because the property contract requires a native
    Arch/BIM Space.
    """
    if not is_semantic_luminaire_candidate(luminaire):
        raise ValueError("Se requiere una luminaria ElectricCR App::Link")
    doc = luminaire.Document
    before = _identity_snapshot(luminaire)
    props = _properties(luminaire)
    current_uid = _text(getattr(luminaire, "ElementUID", "")) if "ElementUID" in props else ""
    conflicts = _uid_conflicts(doc, luminaire, current_uid)
    if conflicts:
        return {
            "status": "UID_CONFLICT",
            "dry_run": bool(dry_run),
            "material_changes": 0,
            "actions": [],
            "uid": current_uid,
            "conflicts": conflicts,
            "room_result": {},
        }

    current_space = getattr(luminaire, "Space", None) if "Space" in props else None
    if current_space is not None:
        room_result = resolve_room_reference(doc, current_space)
    else:
        try:
            point = luminaire.getGlobalPlacement().Base
        except Exception:
            point = luminaire.Placement.Base
        room_result = resolve_room_for_point(
            doc,
            [float(point.x), float(point.y), float(point.z)],
        )
    resolved_space = None
    if room_result.get("status") == room_core.STATUS_RESOLVED:
        candidate = doc.getObject(_text(room_result.get("object_name")))
        if room_result.get("source_kind") == room_core.SOURCE_NATIVE_SPACE and _is_native_space(candidate):
            resolved_space = candidate

    actions = []
    if "ElementUID" not in props:
        actions.append("ADD_ELEMENT_UID_PROPERTY")
    if not current_uid:
        actions.append("SET_ELEMENT_UID")
    if "Space" not in props:
        actions.append("ADD_SPACE_PROPERTY")
    if resolved_space is not None and current_space is None:
        actions.append("ASSIGN_SPACE")

    if dry_run:
        _assert_identity_unchanged(luminaire, before)
        return {
            "status": _text(room_result.get("status")) or room_core.STATUS_NOT_FOUND,
            "dry_run": True,
            "material_changes": len(actions),
            "actions": actions,
            "uid": current_uid,
            "space_name": _text(getattr(resolved_space, "Name", "")),
            "room_result": room_result,
        }

    doc.openTransaction("ElectricCR semantic luminaire")
    material_changes = 0
    try:
        if "ElementUID" not in _properties(luminaire):
            luminaire.addProperty(
                "App::PropertyString",
                "ElementUID",
                PROPERTY_GROUP,
                "Identificador persistente y unico de la instancia",
            )
            material_changes += 1
        if not _text(getattr(luminaire, "ElementUID", "")):
            factory = uid_factory or uuid.uuid4
            luminaire.ElementUID = _text(factory())
            material_changes += 1
        if "Space" not in _properties(luminaire):
            luminaire.addProperty(
                "App::PropertyLink",
                "Space",
                PROPERTY_GROUP,
                "Arch/BIM Space canonico resuelto por RoomResolver",
            )
            material_changes += 1
        if resolved_space is not None and getattr(luminaire, "Space", None) is None:
            luminaire.Space = resolved_space
            material_changes += 1
        if _uid_conflicts(doc, luminaire, _text(luminaire.ElementUID)):
            raise RuntimeError("ElementUID duplicado dentro del documento")
        _assert_identity_unchanged(luminaire, before)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    if material_changes:
        doc.recompute()
    return {
        "status": _text(room_result.get("status")) or room_core.STATUS_NOT_FOUND,
        "dry_run": False,
        "material_changes": material_changes,
        "actions": actions,
        "uid": _text(luminaire.ElementUID),
        "space_name": _text(getattr(getattr(luminaire, "Space", None), "Name", "")),
        "room_result": room_result,
    }


def _control_identity(doc, luminaire):
    controls = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if "Luminarias" not in _properties(obj):
            continue
        try:
            if luminaire in list(getattr(obj, "Luminarias", []) or []):
                controls.append(obj)
        except Exception:
            continue
    if len(controls) > 1:
        return {"status": "AMBIGUOUS_CONTROL", "switch_id": "", "source": None}
    if len(controls) == 1:
        control = controls[0]
        switches = list(getattr(control, "Apagadores", []) or []) if "Apagadores" in _properties(control) else []
        if len(switches) > 1:
            return {"status": "AMBIGUOUS_SWITCH", "switch_id": "", "source": control}
        if len(switches) == 1:
            switch = switches[0]
            value = _first_text(switch, ("ApagadorID", "ControlID", "Label", "Name"))
            if value:
                return {"status": "RESOLVED", "switch_id": value, "source": control, "switch": switch}
        value = _first_text(control, ("ApagadorID", "ControlID", "Label", "Name"))
        if value:
            return {"status": "RESOLVED", "switch_id": value, "source": control}
    value = _first_text(luminaire, ("ApagadorID", "ControlID"))
    if value:
        return {"status": "LEGACY_FALLBACK", "switch_id": value, "source": None}
    return {"status": "NOT_FOUND", "switch_id": "", "source": None}


def _projection_name(role, key):
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return "ECRP_%s_%s" % (role, digest)


def _find_root(doc):
    by_name = doc.getObject(ROOT_LABEL)
    if _is_group(by_name):
        return by_name, "REUSE"
    matches = [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if _is_group(obj) and _text(getattr(obj, "Label", "")).casefold() == ROOT_LABEL
    ]
    if len(matches) == 1:
        return matches[0], "REUSE"
    if len(matches) > 1:
        raise RuntimeError("Raiz electrico ambigua")
    return None, "CREATE"


def _find_direct_group(parent, node):
    children = _direct_groups(parent)
    keyed = [
        child
        for child in children
        if "ECR_ProjectionKey" in _properties(child)
        and _text(getattr(child, "ECR_ProjectionKey", "")) == node["key"]
    ]
    if len(keyed) > 1:
        raise RuntimeError("Clave de proyeccion duplicada: %s" % node["key"])
    if keyed:
        return keyed[0]
    labelled = [
        child
        for child in children
        if _text(getattr(child, "Label", "")).casefold() == node["label"].casefold()
    ]
    if len(labelled) > 1:
        raise RuntimeError("Contenedor visual ambiguo: %s" % node["label"])
    return labelled[0] if labelled else None


def _group_needs_metadata(group, node):
    return not (
        "ECR_ProjectionNode" in _properties(group)
        and bool(getattr(group, "ECR_ProjectionNode", False))
        and _text(getattr(group, "ECR_ProjectionRole", "")) == node["role"]
        and _text(getattr(group, "ECR_ProjectionKey", "")) == node["key"]
    )


def _apply_group_metadata(group, node):
    definitions = (
        ("App::PropertyBool", "ECR_ProjectionNode", "Nodo reproducible ElectricCR"),
        ("App::PropertyString", "ECR_ProjectionRole", "Rol del contenedor visual"),
        ("App::PropertyString", "ECR_ProjectionKey", "Clave semantica estable"),
    )
    for property_type, name, description in definitions:
        if name not in _properties(group):
            group.addProperty(property_type, name, PROJECTION_GROUP, description)
    group.ECR_ProjectionNode = True
    group.ECR_ProjectionRole = node["role"]
    group.ECR_ProjectionKey = node["key"]


def _ensure_source_link(group, property_name, source, description):
    changed = False
    if property_name not in _properties(group):
        group.addProperty("App::PropertyLink", property_name, PROJECTION_GROUP, description)
        changed = True
    if source is not None and getattr(group, property_name, None) is not source:
        setattr(group, property_name, source)
        changed = True
    return changed


def _projection_luminaire_groups(doc):
    return [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if _is_group(obj)
        and "ECR_ProjectionNode" in _properties(obj)
        and bool(getattr(obj, "ECR_ProjectionNode", False))
        and _text(getattr(obj, "ECR_ProjectionRole", "")) == "Luminaires"
    ]


def _is_projection_reference(obj):
    return bool(
        _text(getattr(obj, "TypeId", "")) == "App::Link"
        and "ECR_ProjectionReference" in _properties(obj)
        and bool(getattr(obj, "ECR_ProjectionReference", False))
    )


def _projection_references(doc, luminaire):
    uid = _first_text(luminaire, ("ElementUID",))
    matches = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_projection_reference(obj):
            continue
        linked = getattr(obj, "LinkedObject", None)
        source_uid = _first_text(obj, ("ECR_SourceElementUID",))
        if linked is luminaire or (uid and source_uid == uid):
            matches.append(obj)
    return matches


def _create_projection_reference(doc, luminaire):
    uid = _first_text(luminaire, ("ElementUID",))
    name = "ECRP_Luminaire_%s" % hashlib.sha1(uid.encode("utf-8")).hexdigest()[:10]
    reference = doc.addObject("App::Link", name)
    reference.LinkedObject = luminaire
    try:
        reference.LinkTransform = False
    except Exception:
        pass
    reference.Label = _text(getattr(luminaire, "Label", "")) or luminaire.Name
    reference.addProperty(
        "App::PropertyBool",
        "ECR_ProjectionReference",
        PROJECTION_GROUP,
        "Referencia visual; no es una segunda identidad electromecanica",
    )
    reference.addProperty(
        "App::PropertyString",
        "ECR_SourceElementUID",
        PROJECTION_GROUP,
        "ElementUID de la instancia fisica autoritativa",
    )
    reference.ECR_ProjectionReference = True
    reference.ECR_SourceElementUID = uid
    return reference


def _plan_one(doc, luminaire):
    if not is_semantic_luminaire_candidate(luminaire):
        return {"status": "SKIPPED", "object_name": _text(getattr(luminaire, "Name", ""))}
    uid = _first_text(luminaire, ("ElementUID",))
    space = getattr(luminaire, "Space", None) if "Space" in _properties(luminaire) else None
    circuit = _first_text(luminaire, ("CircuitoID", "CircuitId", "CircuitID", "Circuito"))
    control = _control_identity(doc, luminaire)
    core_plan = device_core.build_lighting_projection(
        uid,
        _space_name(space),
        circuit,
        control.get("switch_id", ""),
    )
    return {
        "status": core_plan["status"],
        "object_name": luminaire.Name,
        "element_uid": uid,
        "space_name": _text(getattr(space, "Name", "")),
        "control_status": control.get("status"),
        "control_name": _text(getattr(control.get("source"), "Name", "")),
        "switch_name": _text(getattr(control.get("switch"), "Name", "")),
        "core": core_plan,
        "space": space,
        "control": control.get("source"),
    }


def project_lighting_tree(doc, luminaires=None, dry_run=True):
    """Plan or materialize the semantic lighting tree; dry-run is default."""
    if doc is None:
        raise ValueError("Se requiere un documento FreeCAD")
    if luminaires is None:
        luminaires = [obj for obj in doc.Objects if is_semantic_luminaire_candidate(obj)]
    plans = [_plan_one(doc, obj) for obj in list(luminaires or [])]
    actionable = [plan for plan in plans if plan.get("status") == device_core.STATUS_READY]
    if dry_run:
        material_changes = 0
        for plan in actionable:
            root, root_state = _find_root(doc)
            if root_state == "CREATE":
                material_changes += 1 + len(plan["core"]["nodes"]) + 1
                continue
            parent = root
            chain_missing = False
            for node in plan["core"]["nodes"]:
                if chain_missing:
                    material_changes += 1
                    continue
                group = _find_direct_group(parent, node)
                if group is None:
                    chain_missing = True
                    material_changes += 1
                else:
                    if _group_needs_metadata(group, node):
                        material_changes += 1
                    parent = group
            references = _projection_references(doc, doc.getObject(plan["object_name"]))
            if len(references) > 1:
                raise RuntimeError("Referencia de proyeccion duplicada para %s" % plan["object_name"])
            if not references:
                material_changes += 1
            elif not chain_missing and references[0] not in list(getattr(parent, "Group", []) or []):
                material_changes += 1
        return {
            "dry_run": True,
            "material_changes": material_changes,
            "plans": [{key: value for key, value in plan.items() if key not in {"space", "control"}} for plan in plans],
        }

    before = {
        plan["object_name"]: _identity_snapshot(doc.getObject(plan["object_name"]))
        for plan in actionable
    }
    material_changes = 0
    created_groups = []
    projection_references = []
    change_reasons = []
    doc.openTransaction("ElectricCR semantic lighting tree")
    try:
        for plan in actionable:
            luminaire = doc.getObject(plan["object_name"])
            root, root_state = _find_root(doc)
            if root_state == "CREATE":
                root = doc.addObject("App::DocumentObjectGroup", ROOT_LABEL)
                root.Label = ROOT_LABEL
                material_changes += 1
                created_groups.append(root.Name)
            parent = root
            role_groups = {}
            for node in plan["core"]["nodes"]:
                group = _find_direct_group(parent, node)
                if group is None:
                    group = doc.addObject("App::DocumentObjectGroup", _projection_name(node["role"], node["key"]))
                    group.Label = node["label"]
                    parent.addObject(group)
                    _apply_group_metadata(group, node)
                    material_changes += 1
                    created_groups.append(group.Name)
                elif _group_needs_metadata(group, node):
                    _apply_group_metadata(group, node)
                    material_changes += 1
                role_groups[node["role"]] = group
                parent = group

            room_group = role_groups.get("Room")
            if room_group is not None and _ensure_source_link(
                room_group, "ECR_SourceSpace", plan["space"], "Space arquitectonico autoritativo"
            ):
                material_changes += 1
            switch_group = role_groups.get("Switch")
            if switch_group is not None and plan["control"] is not None and _ensure_source_link(
                switch_group, "ECR_SourceControl", plan["control"], "Control ElectricCR autoritativo"
            ):
                material_changes += 1

            target = role_groups["Luminaires"]
            references = _projection_references(doc, luminaire)
            if len(references) > 1:
                raise RuntimeError("Referencia de proyeccion duplicada para %s" % luminaire.Name)
            if references:
                reference = references[0]
            else:
                reference = _create_projection_reference(doc, luminaire)
                material_changes += 1
                change_reasons.append("CREATE_PROJECTION_REFERENCE")
            projection_references.append(reference.Name)
            for old_group in _projection_luminaire_groups(doc):
                if old_group is target:
                    continue
                if reference in list(getattr(old_group, "Group", []) or []):
                    old_group.removeObject(reference)
                    material_changes += 1
                    change_reasons.append("REMOVE_PROJECTION_REFERENCE_OLD_NODE")
            if reference not in list(getattr(target, "Group", []) or []):
                target.addObject(reference)
                material_changes += 1
                change_reasons.append("ADD_PROJECTION_REFERENCE_TARGET")
            _assert_identity_unchanged(luminaire, before[luminaire.Name])
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    if material_changes:
        doc.recompute()
    return {
        "dry_run": False,
        "material_changes": material_changes,
        "created_groups": created_groups,
        "projection_references": projection_references,
        "change_reasons": change_reasons,
        "plans": [{key: value for key, value in plan.items() if key not in {"space", "control"}} for plan in plans],
    }


__all__ = [
    "ensure_luminaire_semantics",
    "is_semantic_luminaire_candidate",
    "project_lighting_tree",
]
