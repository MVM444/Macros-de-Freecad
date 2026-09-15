"""FA model diagnostic - FreeCAD read-only snapshot adapter.

Name: model_diagnostic_freecad.py
Purpose: capture the visual tree, essential object state, geometry bounds and
internal relations from the active FreeCAD document without modifying it.
Main behavior: prefer ViewProvider.claimChildren() for Tree View hierarchy,
fall back to Group, and return a JSON-compatible snapshot consumed by
model_diagnostic_core.py.
Future modifications: keep capture read-only, never substitute OutList for the
visual tree, and add only bounded/diagnostic properties that are safe to read.
Version: 0.2.0
Date and time: 2026-09-14 15:30 America/Costa_Rica
FreeCAD target: 1.1.3.
"""

from __future__ import annotations

import datetime
import os

import FreeCAD as App

try:
    import FreeCADGui as Gui
except Exception:
    Gui = None

from .constants import BUILD_ID, VERSION

SNAPSHOT_SCHEMA = "FA_MODEL_SNAPSHOT/1"
RELATION_FIELDS = (
    "Base",
    "Hosts",
    "LinkedObject",
    "Owner",
    "FA_LowerSlab",
    "FA_UpperSlab",
    "FA_SourceWire",
    "FA_LowerLevel",
    "FA_UpperLevel",
    "FA_SlabOpening",
    "FA_SlabOpeningPlan",
    "FA_CeilingExclusionPlan",
    "FA_CeilingObjects",
    "Subtractions",
    "FA_TargetLevel",
    "InList",
    "OutList",
)
PROPERTY_FIELDS = (
    "IfcType",
    "FA_GeneratedBy",
    "FA_Role",
    "FA_ElementType",
    "FA_Schema",
    "DocumentationOnly",
    "RepresentationRole",
    "FA_SlabOpeningStatus",
    "FA_CeilingExclusionStatus",
    "FA_PreviewOnly",
)


def _text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _object_key(obj):
    return _text(getattr(obj, "Name", "")) or "@%x" % id(obj)


def _unique_objects(objects):
    result = []
    seen = set()
    for obj in list(objects or []):
        if obj is None:
            continue
        key = _object_key(obj)
        if key in seen:
            continue
        seen.add(key)
        result.append(obj)
    return result


def _belongs(obj, doc):
    try:
        return getattr(obj, "Document", None) is doc
    except Exception:
        return False


def _show_in_tree(obj):
    try:
        view = getattr(obj, "ViewObject", None)
        method = getattr(view, "showInTree", None)
        if callable(method):
            return bool(method())
    except Exception:
        pass
    return True


def _visibility(obj):
    try:
        return bool(obj.ViewObject.Visibility)
    except Exception:
        return None


def _call_claim_children(provider):
    if provider is None:
        return None
    method = getattr(provider, "claimChildren", None)
    if not callable(method):
        return None
    try:
        return list(method() or [])
    except Exception:
        return None


def tree_children(obj, doc):
    """Return Tree View children, preferring ViewProvider.claimChildren()."""
    try:
        view = getattr(obj, "ViewObject", None)
    except Exception:
        view = None
    children = _call_claim_children(view)
    if children is None and view is not None:
        try:
            children = _call_claim_children(getattr(view, "Proxy", None))
        except Exception:
            children = None
    if children is None:
        try:
            children = list(getattr(obj, "Group", []) or []) if hasattr(obj, "Group") else []
        except Exception:
            children = []
    result = [child for child in _unique_objects(children) if _belongs(child, doc) and _show_in_tree(child)]
    result.sort(key=lambda item: (_text(getattr(item, "Label", "")) or _text(getattr(item, "Name", ""))).lower())
    return result


def build_tree_index(doc):
    visible = [obj for obj in list(getattr(doc, "Objects", []) or []) if _show_in_tree(obj)]
    children_by_key = {}
    parents_by_key = {}
    for obj in visible:
        key = _object_key(obj)
        children = tree_children(obj, doc)
        children_by_key[key] = children
        for child in children:
            parents_by_key.setdefault(_object_key(child), []).append(obj)
    return visible, children_by_key, parents_by_key


def _selected_objects(doc, selection=None):
    if selection is None and Gui is not None:
        try:
            selection = list(Gui.Selection.getSelection() or [])
        except Exception:
            selection = []
    return _unique_objects([obj for obj in list(selection or []) if _belongs(obj, doc) and _show_in_tree(obj)])


def _descendants(root, children_by_key):
    result = set()
    stack = list(children_by_key.get(_object_key(root), []) or [])
    while stack:
        obj = stack.pop()
        key = _object_key(obj)
        if key in result:
            continue
        result.add(key)
        stack.extend(children_by_key.get(key, []) or [])
    return result


def _normalize_selected_roots(selection, children_by_key):
    selected = _unique_objects(selection)
    selected_keys = {_object_key(obj) for obj in selected}
    covered = set()
    for obj in selected:
        covered.update(_descendants(obj, children_by_key).intersection(selected_keys))
    roots = [obj for obj in selected if _object_key(obj) not in covered]
    roots.sort(key=lambda item: (_text(getattr(item, "Label", "")) or _text(getattr(item, "Name", ""))).lower())
    return roots


def _document_roots(visible, parents_by_key):
    roots = [obj for obj in visible if _object_key(obj) not in parents_by_key]
    roots.sort(key=lambda item: (_text(getattr(item, "Label", "")) or _text(getattr(item, "Name", ""))).lower())
    return _unique_objects(roots)


def _relation_ref(obj):
    return {
        "name": _text(getattr(obj, "Name", "")),
        "label": _text(getattr(obj, "Label", "")),
        "type_id": _text(getattr(obj, "TypeId", "")),
    }


def _relation_objects(value, doc):
    result = []

    def visit(item):
        if item is None:
            return
        if _belongs(item, doc):
            result.append(item)
            return
        if isinstance(item, (list, tuple)):
            for sub in item:
                visit(sub)

    visit(value)
    return _unique_objects(result)


def _safe_properties(obj):
    values = {}
    property_names = set(list(getattr(obj, "PropertiesList", []) or []))
    for name in PROPERTY_FIELDS:
        if name not in property_names and not hasattr(obj, name):
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            continue
        if isinstance(value, (bool, int, float, str)) or value is None:
            values[name] = value
        else:
            values[name] = _text(value)
    return values


def _state(obj):
    try:
        value = getattr(obj, "State", [])
        if isinstance(value, (list, tuple)):
            return [_text(item) for item in value if _text(item)]
        return [_text(value)] if _text(value) else []
    except Exception:
        return []


def _placement(obj):
    try:
        base = obj.Placement.Base
        return {"x": float(base.x), "y": float(base.y), "z": float(base.z)}
    except Exception:
        return None


def _bbox(obj):
    try:
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull():
            return None
        bb = shape.BoundBox
        return {
            "xmin": float(bb.XMin), "xmax": float(bb.XMax),
            "ymin": float(bb.YMin), "ymax": float(bb.YMax),
            "zmin": float(bb.ZMin), "zmax": float(bb.ZMax),
        }
    except Exception:
        return None


def _object_record(obj, parents_by_key, children_by_key, root_keys):
    name = _object_key(obj)
    props = _safe_properties(obj)
    return {
        "name": name,
        "label": _text(getattr(obj, "Label", "")),
        "type_id": _text(getattr(obj, "TypeId", "")),
        "visibility": _visibility(obj),
        "ifc_type": _text(props.get("IfcType")),
        "state": _state(obj),
        "properties": props,
        "placement": _placement(obj),
        "bbox": _bbox(obj),
        "tree_parents": [_object_key(parent) for parent in _unique_objects(parents_by_key.get(name, []) or [])],
        "tree_children": [_object_key(child) for child in list(children_by_key.get(name, []) or [])],
        "is_root": name in root_keys,
    }


def _build_node(obj, children_by_key, cycles, branch=None):
    branch = set(branch or [])
    key = _object_key(obj)
    node = {
        "name": key,
        "label": _text(getattr(obj, "Label", "")),
        "type_id": _text(getattr(obj, "TypeId", "")),
        "visibility": _visibility(obj),
        "children": [],
    }
    if key in branch:
        node["loop"] = True
        cycles.append({"path": list(branch) + [key]})
        return node
    next_branch = set(branch)
    next_branch.add(key)
    for child in list(children_by_key.get(key, []) or []):
        child_key = _object_key(child)
        if child_key in next_branch:
            node["children"].append({
                "name": child_key,
                "label": _text(getattr(child, "Label", "")),
                "type_id": _text(getattr(child, "TypeId", "")),
                "visibility": _visibility(child),
                "loop": True,
                "children": [],
            })
            cycles.append({"path": list(next_branch) + [child_key]})
        else:
            node["children"].append(_build_node(child, children_by_key, cycles, next_branch))
    return node


def _collect_exported(roots, children_by_key):
    result = []
    seen = set()
    stack = list(reversed(list(roots or [])))
    while stack:
        obj = stack.pop()
        key = _object_key(obj)
        if key in seen:
            continue
        seen.add(key)
        result.append(obj)
        stack.extend(reversed(list(children_by_key.get(key, []) or [])))
    return result


def _document_file(doc):
    try:
        value = _text(getattr(doc, "FileName", ""))
    except Exception:
        value = ""
    return os.path.abspath(value) if value else "(documento aun no guardado)"


def capture_document_snapshot(doc, selection=None):
    """Capture a read-only JSON-compatible snapshot of one FreeCAD document."""
    if doc is None:
        raise ValueError("Se requiere un documento FreeCAD activo.")

    visible, children_by_key, parents_by_key = build_tree_index(doc)
    selected = _selected_objects(doc, selection=selection)
    if selected:
        roots = _normalize_selected_roots(selected, children_by_key)
        scope = "seleccion"
    else:
        roots = _document_roots(visible, parents_by_key)
        scope = "documento_completo"
    if not roots:
        raise RuntimeError("No se encontraron objetos raiz para diagnosticar.")

    exported = _collect_exported(roots, children_by_key)
    root_keys = {_object_key(obj) for obj in roots}
    capture_errors = []
    relations = []
    for obj in exported:
        source = _object_key(obj)
        for field in RELATION_FIELDS:
            if field not in list(getattr(obj, "PropertiesList", []) or []) and field not in ("InList", "OutList"):
                continue
            try:
                value = getattr(obj, field)
                targets = [_relation_ref(target) for target in _relation_objects(value, doc)]
            except Exception as exc:
                capture_errors.append({"object": source, "field": field, "message": _text(exc)})
                continue
            if targets:
                relations.append({"source": source, "field": field, "targets": targets})

    cycles = []
    root_nodes = [_build_node(root, children_by_key, cycles, set()) for root in roots]
    records = [_object_record(obj, parents_by_key, children_by_key, root_keys) for obj in exported]

    freecad_version = ""
    try:
        version = App.Version()
        freecad_version = ".".join(str(part) for part in list(version)[:3])
    except Exception:
        freecad_version = ""

    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "schema": SNAPSHOT_SCHEMA,
        "meta": {
            "generated_at": now,
            "freecad_version": freecad_version,
            "workbench_version": VERSION,
            "workbench_build": BUILD_ID,
            "scope": scope,
        },
        "document": {
            "name": _text(getattr(doc, "Name", "")),
            "label": _text(getattr(doc, "Label", "")),
            "file": _document_file(doc),
        },
        "selected_objects": [_object_key(obj) for obj in selected],
        "roots": root_nodes,
        "objects": records,
        "relations": relations,
        "tree_cycles": cycles,
        "capture_errors": capture_errors,
    }
