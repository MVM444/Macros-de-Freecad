import FreeCAD


def _safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _log(msg):
    try:
        FreeCAD.Console.PrintMessage(f"[CONEX][INFO] {msg}\n")
    except Exception:
        pass


def is_group(obj):
    if obj is None:
        return False
    try:
        if obj.isDerivedFrom("App::DocumentObjectGroup"):
            return True
    except Exception:
        pass
    try:
        if obj.isDerivedFrom("App::Part"):
            return True
    except Exception:
        pass
    return hasattr(obj, "Group")


def is_conexiones_group(obj):
    label = _safe_text(getattr(obj, "Label", "")).lower()
    name = _safe_text(getattr(obj, "Name", "")).lower()
    return label.startswith("conexiones") or name.startswith("conexiones")


def get_parent_group(doc, obj):
    if obj is None or doc is None:
        return None
    if hasattr(obj, "getParentGroup"):
        try:
            pg = obj.getParentGroup()
            if pg:
                return pg
        except Exception:
            pass
    # InList suele ser la forma mas fiable de obtener padres en objetos agrupados.
    try:
        for p in (getattr(obj, "InList", []) or []):
            if is_group(p):
                return p
    except Exception:
        pass
    try:
        for g in doc.Objects:
            if not is_group(g):
                continue
            try:
                if obj in (getattr(g, "Group", []) or []):
                    return g
            except Exception:
                pass
    except Exception:
        pass
    return None


def _parent_chain(doc, obj):
    chain = []
    seen = set()
    cur = obj
    while True:
        pg = get_parent_group(doc, cur)
        if not pg:
            break
        key = _safe_text(getattr(pg, "Name", ""))
        if key in seen:
            break
        seen.add(key)
        chain.append(pg)
        cur = pg
    return chain


def _common_parent_group(doc, objects):
    objs = [o for o in (objects or []) if o is not None]
    if not objs:
        return None
    chains = [_parent_chain(doc, o) for o in objs]
    if not chains:
        return None
    first = chains[0]
    first_names = [_safe_text(getattr(g, "Name", "")) for g in first]
    other_sets = []
    for c in chains[1:]:
        other_sets.append(set(_safe_text(getattr(g, "Name", "")) for g in c))
    for i, g in enumerate(first):
        name = first_names[i]
        if all(name in s for s in other_sets):
            return g
    return first[0] if first else None


def _normalize_parent(doc, parent):
    cur = parent
    seen = set()
    while cur and is_conexiones_group(cur):
        key = _safe_text(getattr(cur, "Name", ""))
        if key in seen:
            break
        seen.add(key)
        up = get_parent_group(doc, cur)
        if not up or up is cur:
            break
        cur = up
    return cur


def _find_conexiones_children(parent):
    if not parent or not hasattr(parent, "Group"):
        return []
    out = []
    for child in (getattr(parent, "Group", []) or []):
        try:
            if is_group(child) and is_conexiones_group(child):
                out.append(child)
        except Exception:
            pass
    return out


def _pick_primary_conexiones(groups):
    if not groups:
        return None
    for child in groups:
        if _safe_text(getattr(child, "Label", "")).strip().lower() == "conexiones":
            return child
    for child in groups:
        if _safe_text(getattr(child, "Name", "")).strip().lower() == "conexiones":
            return child
    return groups[0]


def _group_children(group):
    try:
        return list(getattr(group, "Group", []) or [])
    except Exception:
        return []


def _move_group_children(target, source):
    for child in _group_children(source):
        if child is target:
            continue
        try:
            if child not in (_group_children(target) or []):
                target.addObject(child)
        except Exception:
            pass


def _remove_group(doc, parent, grp):
    try:
        if parent and hasattr(parent, "removeObject"):
            parent.removeObject(grp)
    except Exception:
        pass
    try:
        if doc and hasattr(grp, "Name"):
            doc.removeObject(grp.Name)
    except Exception:
        pass


def _merge_duplicate_conexiones(doc, parent, primary, duplicates):
    if len(duplicates) > 1:
        _log(
            "Unificando {} grupos 'Conexiones*' bajo '{}'".format(
                len(duplicates),
                _safe_text(getattr(parent, "Label", getattr(parent, "Name", "Grupo"))),
            )
        )
    for dup in duplicates:
        if dup is primary:
            continue
        _flatten_nested_conexiones(doc, dup)
        _move_group_children(primary, dup)
        _remove_group(doc, parent, dup)


def _flatten_nested_conexiones(doc, root):
    if not is_group(root):
        return
    nested = []
    for child in _group_children(root):
        if child is root:
            continue
        if is_group(child) and is_conexiones_group(child):
            nested.append(child)
    if nested:
        _log(
            "Aplanando {} subgrupos 'Conexiones*' en '{}'".format(
                len(nested),
                _safe_text(getattr(root, "Label", getattr(root, "Name", "Conexiones"))),
            )
        )
    for dup in nested:
        _flatten_nested_conexiones(doc, dup)
        _move_group_children(root, dup)
        _remove_group(doc, root, dup)


def _ensure_orphans_group(doc, orphans_name):
    target_label = _safe_text(orphans_name).strip() or "Conexiones_Huerfanas"
    for o in getattr(doc, "Objects", []) or []:
        if not is_group(o):
            continue
        if _safe_text(getattr(o, "Label", "")).strip().lower() == target_label.lower():
            return o
    g = doc.addObject("App::DocumentObjectGroup", target_label)
    try:
        g.Label = target_label
    except Exception:
        pass
    return g


def resolve_parent_group(doc, parent_group=None, objects=None):
    parent = parent_group if is_group(parent_group) else None
    if parent is None:
        parent = _common_parent_group(doc, objects or [])
    if parent is None:
        objs = [o for o in (objects or []) if o is not None]
        if objs:
            parent = get_parent_group(doc, objs[0])
    return _normalize_parent(doc, parent)


def ensure_conexiones_group(doc, parent_group=None, objects=None, orphans_name="Conexiones_Huerfanas"):
    parent = resolve_parent_group(doc, parent_group=parent_group, objects=objects)
    if parent is None:
        return _ensure_orphans_group(doc, orphans_name)
    if is_conexiones_group(parent):
        _flatten_nested_conexiones(doc, parent)
        return parent
    existing_all = _find_conexiones_children(parent)
    if existing_all:
        existing = _pick_primary_conexiones(existing_all)
        _merge_duplicate_conexiones(doc, parent, existing, existing_all)
        try:
            if _safe_text(getattr(existing, "Label", "")).strip().lower() != "conexiones":
                existing.Label = "Conexiones"
        except Exception:
            pass
        _flatten_nested_conexiones(doc, existing)
        return existing
    g = doc.addObject("App::DocumentObjectGroup", "Conexiones")
    try:
        g.Label = "Conexiones"
    except Exception:
        pass
    try:
        parent.addObject(g)
    except Exception:
        pass
    return g


def place_connection_object(doc, obj, parent_group=None, objects=None, orphans_name="Conexiones_Huerfanas"):
    target = ensure_conexiones_group(
        doc,
        parent_group=parent_group,
        objects=objects,
        orphans_name=orphans_name,
    )
    try:
        if obj not in (getattr(target, "Group", []) or []):
            target.addObject(obj)
    except Exception:
        pass
    return target
