"""Shared backend for ElectricCR branch-circuit routing.

This module centralizes the branch routing engine used by:
- Conectar_Circuitos_Ramales_Auto.FCMacro
- future extractions from Conectar_Cajas_a_Tablero_Auto.FCMacro

Current state:
- wraps the stable branch-routing internals from the v1 macro
- keeps a small public API so the calling macros do not depend on v1 internals
- prepares the codebase for a future step where the mature v1 functions are
  copied here and the runtime dependency on the v1 macro is removed
"""

from __future__ import annotations

import importlib.machinery
import re
import sys
import types
from pathlib import Path

try:
    from collections import defaultdict
except Exception:  # pragma: no cover
    defaultdict = dict  # type: ignore


_BACKEND_V1 = None
EPS = 1e-6


def _safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _macro_dir():
    return Path(__file__).resolve().parent


def ruta_macro_v1():
    return _macro_dir() / "Conectar_Cajas_a_Tablero_Auto.FCMacro"


def cargar_backend_v1(force_reload=False):
    global _BACKEND_V1
    if (not force_reload) and (_BACKEND_V1 is not None):
        return _BACKEND_V1
    macro_path = ruta_macro_v1()
    if not macro_path.exists():
        raise RuntimeError(f"No se encontro la macro base v1: {macro_path}")
    folder = str(macro_path.parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    loader = importlib.machinery.SourceFileLoader("electriccr_ramal_backend_v1", str(macro_path))
    module = types.ModuleType(loader.name)
    module.__file__ = str(macro_path)
    loader.exec_module(module)
    _BACKEND_V1 = module
    return module


def import_component_classifier():
    return cargar_backend_v1()._import_component_classifier()


def _component_type_for_obj(backend, get_component_type, obj):
    ctype = ""
    if callable(get_component_type):
        try:
            ctype = _safe_text(get_component_type(obj)).strip()
        except Exception:
            ctype = ""
    if not ctype:
        try:
            ctype = _safe_text(backend._fallback_component_type(obj)).strip()
        except Exception:
            ctype = ""
    return ctype


def _is_luminaria_obj(backend, obj):
    if obj is None:
        return False
    try:
        fn = getattr(backend, "_is_luminaria_like", None)
        if callable(fn):
            return bool(fn(obj))
    except Exception:
        pass
    txt = (
        f"{_safe_text(getattr(obj, 'Tipo', ''))} "
        f"{_safe_text(getattr(obj, 'TipoLogico', ''))} "
        f"{_safe_text(getattr(obj, 'Categoria', ''))} "
        f"{_safe_text(getattr(obj, 'Label', ''))} "
        f"{_safe_text(getattr(obj, 'Name', ''))}"
    ).strip().lower()
    if not txt:
        return False
    if any(tok in txt for tok in ("apagador", "switch", "interruptor", "conmutador", "toma", "tablero")):
        return False
    return ("lumin" in txt) or (" lum" in f" {txt}") or ("luz" in txt)


def _is_switch_obj(backend, obj):
    if obj is None:
        return False
    try:
        ctype = _safe_text(backend._fallback_component_type(obj)).strip().lower()
        if ctype == "apagador":
            return True
    except Exception:
        pass
    txt = (
        f"{_safe_text(getattr(obj, 'Tipo', ''))} "
        f"{_safe_text(getattr(obj, 'TipoLogico', ''))} "
        f"{_safe_text(getattr(obj, 'Categoria', ''))} "
        f"{_safe_text(getattr(obj, 'Label', ''))} "
        f"{_safe_text(getattr(obj, 'Name', ''))}"
    ).strip().lower()
    compact = re.sub(r"[\s_\-]+", "", txt)
    if ("3way" in compact) or ("3vias" in compact) or ("tresvias" in compact):
        return True
    return any(tok in txt for tok in ("apagador", "switch", "interruptor", "conmutador", "triway", "threeway"))


def _iter_circuit_descendants(backend, circuit_group):
    for obj in list(backend._iter_non_group_descendants(circuit_group, skip_conexiones=True) or []):
        if obj is None:
            continue
        yield obj


def _anchor_point(backend, obj):
    try:
        return backend._anchor_point(obj)
    except Exception:
        try:
            return backend._vec(obj.Placement.Base.x, obj.Placement.Base.y, obj.Placement.Base.z)
        except Exception:
            return backend._vec(0.0, 0.0, 0.0)


def _dist_xy(backend, a, b):
    pa = _anchor_point(backend, a)
    pb = _anchor_point(backend, b)
    try:
        return float(backend._dist_xy(pa, pb))
    except Exception:
        dx = float(pa.x) - float(pb.x)
        dy = float(pa.y) - float(pb.y)
        return float((dx * dx + dy * dy) ** 0.5)


def _same_level(backend, a, b, tolerance):
    pa = _anchor_point(backend, a)
    pb = _anchor_point(backend, b)
    return abs(float(pa.z) - float(pb.z)) <= max(0.0, float(tolerance))


def _nearest_obj_xy(backend, ref_obj, candidates, same_level_only=False, level_tol=10.0):
    ref = ref_obj
    best = None
    best_d = None
    for obj in list(candidates or []):
        if obj is None or obj is ref:
            continue
        if bool(same_level_only) and (not _same_level(backend, ref, obj, level_tol)):
            continue
        d = _dist_xy(backend, ref, obj)
        if best is None or d < best_d:
            best = obj
            best_d = d
    if best is not None:
        return best
    if bool(same_level_only):
        return _nearest_obj_xy(backend, ref, candidates, same_level_only=False, level_tol=level_tol)
    return None


def _dedup_objects(objs):
    out = []
    seen = set()
    for obj in list(objs or []):
        name = _safe_text(getattr(obj, "Name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(obj)
    return out


def _group_uid(group_obj):
    name = _safe_text(getattr(group_obj, "Name", "")).strip()
    if name:
        return f"NAME:{name}"
    label = _safe_text(getattr(group_obj, "Label", "")).strip()
    if label:
        return f"LABEL:{label}"
    return ""


def _is_technical_group_like(group_obj):
    txt = (
        _safe_text(getattr(group_obj, "Label", "")).strip().lower()
        or _safe_text(getattr(group_obj, "Name", "")).strip().lower()
    )
    if not txt:
        return True
    norm = re.sub(r"[\s\-]+", "_", txt)
    if re.match(r"^g[0-9]{2}_", norm):
        return True
    tokens = (
        "cajas_",
        "cajaoct_",
        "cajas_octogonales",
        "cajas_tp",
        "tuberias_",
        "ramales_",
        "alimentadores",
        "conexiones",
        "conexiones_luminarias_cajas",
        "electrico",
        "_lib",
        "tomacorrientes",
        "apagadores",
        "luminarias",
        "dispositivos",
        "componentes",
        "recintos",
        "sin_recinto",
        "sin_circuito",
        "rutas_guia",
        "etiquetas",
        "shape2dview",
        "origin",
        "origen",
    )
    return any(tok in norm for tok in tokens)


def _circuit_group_uid(circuit_group):
    return _group_uid(circuit_group)


def _room_key_for_device(backend, circuit_group, obj):
    try:
        chain = list(backend._group_chain_topdown(obj) or [])
    except Exception:
        chain = []
    if not chain:
        return "__SIN_RECINTO__"

    circuit_uid = _circuit_group_uid(circuit_group)
    start_idx = -1
    for idx, grp in enumerate(chain):
        if _group_uid(grp) == circuit_uid:
            start_idx = idx
    tail = chain[(start_idx + 1) :] if start_idx >= 0 else list(chain)
    if not tail:
        return "__SIN_RECINTO__"

    for grp in reversed(tail):
        if _is_technical_group_like(grp):
            continue
        key = _group_uid(grp)
        if key:
            return key
    return "__SIN_RECINTO__"


def _collect_room_order(backend, circuit_group):
    out = {}
    if circuit_group is None:
        return out
    queue = list(getattr(circuit_group, "Group", []) or [])
    rank = 0
    seen = set()
    while queue:
        grp = queue.pop(0)
        if grp is None:
            continue
        is_group = False
        try:
            if bool(getattr(backend, "_is_group", None)):
                is_group = bool(backend._is_group(grp))
            else:
                is_group = hasattr(grp, "Group")
        except Exception:
            is_group = hasattr(grp, "Group")
        if not is_group:
            continue
        uid = _group_uid(grp)
        if uid and uid in seen:
            continue
        if uid:
            seen.add(uid)
        children = list(getattr(grp, "Group", []) or [])
        queue.extend(children)
        if (not _is_technical_group_like(grp)) and uid and uid not in out:
            out[uid] = rank
            rank += 1
    return out


def _order_spine_nodes(backend, nodes, board_obj=None):
    ordered = _dedup_objects(nodes)
    if len(ordered) < 3:
        return ordered
    try:
        if all(bool(backend._is_octagon_box(o)) for o in ordered):
            return list(backend._order_boxes_by_perimeter(ordered, board_obj=board_obj))
    except Exception:
        pass

    # Greedy nearest-neighbor keeps local continuity when the node set is mixed.
    rest = list(ordered)
    rest.sort(key=lambda o: (float(_anchor_point(backend, o).x), float(_anchor_point(backend, o).y)))
    current = rest.pop(0)
    out = [current]
    while rest:
        nxt = min(rest, key=lambda o: _dist_xy(backend, current, o))
        out.append(nxt)
        rest.remove(nxt)
        current = nxt
    return out


def _is_lighting_circuit(circuit_group, counts):
    label = (
        _safe_text(getattr(circuit_group, "Label", "")).strip().lower()
        or _safe_text(getattr(circuit_group, "Name", "")).strip().lower()
    )
    has_ilum_token = any(tok in label for tok in ("ilumin", "luz", "lighting"))
    if has_ilum_token and counts.get("Luminaria", 0) > 0:
        return True
    if counts.get("Luminaria", 0) > 0 and counts.get("Apagador", 0) > 0 and counts.get("Toma", 0) == 0:
        return True
    return False


def _build_lighting_plan(backend, circuit_group, devices, boxes, box_by_source, cfg, board_obj=None):
    get_component_type = backend._import_component_classifier()
    mode = _safe_text(cfg.get("circuit_mode", "auto")).strip().lower()
    force_lighting = mode == "luminarias"
    skip_lum_drop_box = bool(cfg.get("skip_lum_drop_box", False))
    skip_switch_to_lum = bool(cfg.get("skip_switch_to_lum", False))
    connect_room_boxes_from_switch = bool(cfg.get("connect_room_boxes_from_switch", True))
    by_type = {"Apagador": [], "Luminaria": [], "Toma": [], "Otros": []}
    for dev in list(devices or []):
        ctype = _component_type_for_obj(backend, get_component_type, dev)
        if ctype in ("Apagador", "Luminaria", "Toma"):
            by_type[ctype].append(dev)
        else:
            by_type["Otros"].append(dev)

    switches = list(by_type["Apagador"])
    lights = list(by_type["Luminaria"])
    if not switches:
        # Not a true lighting-control topology; keep legacy behavior.
        return backend._build_plan_for_circuit(
            circuit_group=circuit_group,
            devices=devices,
            boxes=boxes,
            box_by_source=box_by_source,
            board_obj=board_obj,
            cfg=cfg,
        )
    if (not lights) and (not force_lighting):
        return backend._build_plan_for_circuit(
            circuit_group=circuit_group,
            devices=devices,
            boxes=boxes,
            box_by_source=box_by_source,
            board_obj=board_obj,
            cfg=cfg,
        )

    same_level_only = bool(cfg.get("direct_same_level_only", True))
    level_tol = max(0.0, float(cfg.get("device_level_tolerance", 10.0)))
    seen_pairs = set()
    plan = []

    def push(a_obj, b_obj, kind):
        if a_obj is None or b_obj is None or a_obj is b_obj:
            return
        try:
            key = backend._planned_pair_key(a_obj, b_obj)
        except Exception:
            an = _safe_text(getattr(a_obj, "Name", "")).strip()
            bn = _safe_text(getattr(b_obj, "Name", "")).strip()
            if not an or not bn:
                return
            x, y = sorted([an, bn])
            key = f"{x}|{y}"
        if not key or key in seen_pairs:
            return
        seen_pairs.add(key)
        plan.append((a_obj, b_obj, _safe_text(kind)))

    room_order = _collect_room_order(backend, circuit_group)
    switch_nodes = []
    room_to_nodes = {}
    for sw in switches:
        sw_box = box_by_source.get(backend._source_key(sw))
        room_key = _room_key_for_device(backend, circuit_group, sw)
        if sw_box is not None:
            push(sw, sw_box, "drop_box")
            switch_nodes.append(sw_box)
            room_to_nodes.setdefault(room_key, []).append(sw_box)
        else:
            switch_nodes.append(sw)
            room_to_nodes.setdefault(room_key, []).append(sw)
    switch_nodes = _dedup_objects(switch_nodes)

    # 1) Troncal local dentro de cada recinto/grupo.
    room_reps = []
    for room_key, nodes in list(room_to_nodes.items()):
        ordered_nodes = _order_spine_nodes(backend, _dedup_objects(nodes), board_obj=board_obj)
        if len(ordered_nodes) >= 2:
            for a_obj, b_obj in zip(ordered_nodes[:-1], ordered_nodes[1:]):
                push(a_obj, b_obj, "switch_backbone")
        if ordered_nodes:
            # Representative node nearest to room centroid.
            if len(ordered_nodes) == 1:
                rep = ordered_nodes[0]
            else:
                cx = sum(float(_anchor_point(backend, o).x) for o in ordered_nodes) / float(len(ordered_nodes))
                cy = sum(float(_anchor_point(backend, o).y) for o in ordered_nodes) / float(len(ordered_nodes))
                rep = min(
                    ordered_nodes,
                    key=lambda o: ((float(_anchor_point(backend, o).x) - cx) ** 2) + ((float(_anchor_point(backend, o).y) - cy) ** 2),
                )
            room_reps.append((room_key, rep))

    # 2) Troncal entre recintos, siguiendo orden del arbol cuando exista.
    if len(room_reps) >= 2:
        ranked = []
        unranked = []
        for key, rep in room_reps:
            if key in room_order:
                ranked.append((int(room_order.get(key, 10**9)), key, rep))
            else:
                unranked.append((key, rep))
        ranked.sort(key=lambda t: t[0])
        ordered_rep_nodes = [rep for _rk, _k, rep in ranked]
        if unranked:
            un_nodes = _order_spine_nodes(backend, [rep for _k, rep in unranked], board_obj=board_obj)
            ordered_rep_nodes.extend(un_nodes)
        ordered_rep_nodes = _dedup_objects(ordered_rep_nodes)
        if len(ordered_rep_nodes) >= 2:
            for a_obj, b_obj in zip(ordered_rep_nodes[:-1], ordered_rep_nodes[1:]):
                push(a_obj, b_obj, "switch_backbone")

    if connect_room_boxes_from_switch:
        source_by_key = {}
        for dev in list(devices or []):
            source_by_key[_safe_text(backend._source_key(dev)).strip()] = dev
        room_to_boxes = {}
        for bx in list(boxes or []):
            bkey = _safe_text(getattr(bx, "CajaOrigenKey", "")).strip()
            src_obj = source_by_key.get(bkey)
            room_key = _room_key_for_device(backend, circuit_group, src_obj if src_obj is not None else bx)
            room_to_boxes.setdefault(room_key, []).append(bx)
        for room_key, room_boxes in list(room_to_boxes.items()):
            local_switches = _dedup_objects(room_to_nodes.get(room_key, []))
            for bx in _dedup_objects(room_boxes):
                if bx in local_switches:
                    continue
                if local_switches:
                    sw_node = _nearest_obj_xy(
                        backend,
                        bx,
                        local_switches,
                        same_level_only=same_level_only,
                        level_tol=level_tol,
                    )
                else:
                    sw_node = _nearest_obj_xy(
                        backend,
                        bx,
                        switch_nodes,
                        same_level_only=same_level_only,
                        level_tol=level_tol,
                    )
                if sw_node is not None and sw_node is not bx:
                    push(sw_node, bx, "switch_backbone")

    # Branches from the switch trunk to luminaria nodes.
    for lum in lights:
        lum_box = box_by_source.get(backend._source_key(lum))
        lum_node = lum_box if lum_box is not None else lum
        if (lum_box is not None) and (not skip_lum_drop_box):
            push(lum, lum_box, "drop_box")

        lum_room_key = _room_key_for_device(backend, circuit_group, lum)
        room_switch_candidates = _dedup_objects(room_to_nodes.get(lum_room_key, []))
        sw_node = None
        if room_switch_candidates:
            sw_node = _nearest_obj_xy(
                backend,
                lum_node,
                room_switch_candidates,
                same_level_only=same_level_only,
                level_tol=level_tol,
            )
        if sw_node is None:
            sw_node = _nearest_obj_xy(
                backend,
                lum_node,
                switch_nodes,
                same_level_only=same_level_only,
                level_tol=level_tol,
            )
        if (not skip_switch_to_lum) and sw_node is not None and sw_node is not lum_node:
            push(sw_node, lum_node, "drop_nearest")

    # Keep legacy handling for non-lighting devices that may coexist.
    legacy_devices = list(by_type["Toma"]) + list(by_type["Otros"])
    if legacy_devices:
        legacy_plan = backend._build_plan_for_circuit(
            circuit_group=circuit_group,
            devices=legacy_devices,
            boxes=boxes,
            box_by_source=box_by_source,
            board_obj=board_obj,
            cfg=cfg,
        )
        for src_obj, dst_obj, link_kind in list(legacy_plan or []):
            push(src_obj, dst_obj, link_kind)

    return plan


def collect_circuit_objects(circuit_group, include_apagadores, mode="auto"):
    backend = cargar_backend_v1()
    get_component_type = backend._import_component_classifier()
    mode_txt = _safe_text(mode).strip().lower()
    if mode_txt == "tomas":
        allowed = {"Toma"}
        if bool(include_apagadores):
            allowed.add("Apagador")
    elif mode_txt == "luminarias":
        allowed = {"Luminaria", "Apagador"}
    else:
        allowed = {"Toma", "Luminaria"}
        if bool(include_apagadores):
            allowed.add("Apagador")

    devices = []
    boxes = []
    for obj in _iter_circuit_descendants(backend, circuit_group):
        if backend._is_octagon_box(obj):
            boxes.append(obj)
            continue
        ctype = _component_type_for_obj(backend, get_component_type, obj)
        if ctype in allowed:
            devices.append(obj)

    devices = sorted(devices, key=backend._device_order_key)
    return devices, boxes


def map_boxes_by_source(boxes):
    return cargar_backend_v1()._map_boxes_by_source(boxes)


def source_key(obj):
    return cargar_backend_v1()._source_key(obj)


def order_boxes_by_perimeter(boxes, board_obj=None):
    return cargar_backend_v1()._order_boxes_by_perimeter(boxes, board_obj=board_obj)


def build_plan_for_circuit(circuit_group, devices, boxes, cfg, board_obj=None):
    backend = cargar_backend_v1()
    box_by_source = backend._map_boxes_by_source(boxes)
    get_component_type = backend._import_component_classifier()
    counts = {"Apagador": 0, "Luminaria": 0, "Toma": 0}
    for dev in list(devices or []):
        ctype = _component_type_for_obj(backend, get_component_type, dev)
        if ctype in counts:
            counts[ctype] += 1

    mode = _safe_text(cfg.get("circuit_mode", "auto")).strip().lower()
    if mode == "tomas":
        use_lighting_plan = False
    elif mode == "luminarias":
        use_lighting_plan = True
    else:
        use_lighting_plan = bool(cfg.get("lighting_switch_spine", True)) and _is_lighting_circuit(circuit_group, counts)
    if use_lighting_plan:
        plan = _build_lighting_plan(
            backend=backend,
            circuit_group=circuit_group,
            devices=devices,
            boxes=boxes,
            box_by_source=box_by_source,
            cfg=cfg,
            board_obj=board_obj,
        )
    else:
        plan = backend._build_plan_for_circuit(
            circuit_group=circuit_group,
            devices=devices,
            boxes=boxes,
            box_by_source=box_by_source,
            board_obj=board_obj,
            cfg=cfg,
        )
    ordered_boxes = []
    seen_box = set()
    for dev in devices:
        bx = box_by_source.get(backend._source_key(dev))
        if bx is None:
            continue
        bname = str(getattr(bx, "Name", "") or "")
        if bname and bname not in seen_box:
            seen_box.add(bname)
            ordered_boxes.append(bx)
    for bx in boxes:
        bname = str(getattr(bx, "Name", "") or "")
        if bname and bname not in seen_box:
            seen_box.add(bname)
            ordered_boxes.append(bx)
    if len(ordered_boxes) >= 3:
        try:
            ordered_boxes = backend._order_boxes_by_perimeter(ordered_boxes, board_obj=board_obj)
        except Exception:
            pass
    return plan, ordered_boxes, box_by_source


def route_rect_for_circuit(boxes, cfg):
    return cargar_backend_v1()._route_rect_for_circuit([], boxes, cfg, board_obj=None, use_box_ports=False)


def collect_existing_route_keys(group_obj):
    return cargar_backend_v1()._collect_existing_route_keys(group_obj)


def reserve_existing_ports(group_obj, used_ports):
    return cargar_backend_v1()._reserve_existing_ports(group_obj, used_ports)


def new_used_ports():
    return defaultdict(set)


def vec(x=0.0, y=0.0, z=0.0):
    return cargar_backend_v1()._vec(x, y, z)


def _polyline_len(points):
    total = 0.0
    pts = list(points or [])
    for a, b in zip(pts[:-1], pts[1:]):
        try:
            total += float(a.distanceToPoint(b))
        except Exception:
            pass
    return float(total)


def _iter_group_objects_recursive(group_obj):
    if group_obj is None:
        return []
    out = []
    queue = [group_obj]
    seen = set()
    while queue:
        cur = queue.pop(0)
        gname = _safe_text(getattr(cur, "Name", "")).strip()
        if gname:
            if gname in seen:
                continue
            seen.add(gname)
        for child in list(getattr(cur, "Group", []) or []):
            try:
                is_group = bool(hasattr(child, "Group"))
            except Exception:
                is_group = False
            if is_group:
                queue.append(child)
            else:
                out.append(child)
    return out


def _find_route_obj_by_key(group_obj, route_key):
    want = _safe_text(route_key).strip()
    if not want or group_obj is None:
        return None
    for obj in _iter_group_objects_recursive(group_obj):
        key = _safe_text(getattr(obj, "AutoRouteKey", "")).strip()
        if key and key == want:
            return obj
    return None


def _dedup_points_backend(backend, points):
    out = []
    for p in list(points or []):
        if not out:
            out.append(p)
            continue
        try:
            if float(out[-1].distanceToPoint(p)) > 0.1:
                out.append(p)
        except Exception:
            out.append(p)
    return out


def _route_points_from_obj(backend, obj):
    pts = []
    if obj is None:
        return pts
    raw = getattr(obj, "Points", None)
    if raw:
        try:
            for p in list(raw):
                pts.append(backend._vec(float(p.x), float(p.y), float(p.z)))
            return _dedup_points_backend(backend, pts)
        except Exception:
            pts = []
    try:
        shape = getattr(obj, "Shape", None)
        if shape is not None and (not shape.isNull()) and shape.Edges:
            for edge in list(shape.Edges or []):
                for vv in list(edge.Vertexes or []):
                    pp = getattr(vv, "Point", None)
                    if pp is not None:
                        pts.append(backend._vec(float(pp.x), float(pp.y), float(pp.z)))
    except Exception:
        pass
    return _dedup_points_backend(backend, pts)


def _axis_segments_xy(pts, tol=0.1):
    segs = []
    arr = list(pts or [])
    for a, b in zip(arr[:-1], arr[1:]):
        try:
            dx = float(b.x) - float(a.x)
            dy = float(b.y) - float(a.y)
            if abs(dx) <= float(tol) and abs(dy) <= float(tol):
                continue
            z = 0.5 * (float(a.z) + float(b.z))
            if abs(dy) <= float(tol) and abs(dx) > float(tol):
                y = 0.5 * (float(a.y) + float(b.y))
                x0 = min(float(a.x), float(b.x))
                x1 = max(float(a.x), float(b.x))
                segs.append(("h", y, x0, x1, z))
            elif abs(dx) <= float(tol) and abs(dy) > float(tol):
                x = 0.5 * (float(a.x) + float(b.x))
                y0 = min(float(a.y), float(b.y))
                y1 = max(float(a.y), float(b.y))
                segs.append(("v", x, y0, y1, z))
        except Exception:
            continue
    return segs


def _segments_overlap_xy(seg_a, seg_b, tol_xy=1.2, tol_z=2.0, min_overlap=45.0):
    ka, ca, a0, a1, za = seg_a
    kb, cb, b0, b1, zb = seg_b
    if ka != kb:
        return False
    if abs(float(ca) - float(cb)) > float(tol_xy):
        return False
    if abs(float(za) - float(zb)) > float(tol_z):
        return False
    lo = max(float(a0), float(b0))
    hi = min(float(a1), float(b1))
    return (hi - lo) >= float(min_overlap)


def _route_overlaps_existing_trunk(backend, group_obj, new_route_key, new_route_obj):
    if group_obj is None or new_route_obj is None:
        return False
    new_pts = _route_points_from_obj(backend, new_route_obj)
    new_segs = _axis_segments_xy(new_pts)
    if not new_segs:
        return False
    trunk_kinds = {"feeder", "backbone", "switch_backbone"}
    new_name = _safe_text(getattr(new_route_obj, "Name", "")).strip()
    for obj in _iter_group_objects_recursive(group_obj):
        if obj is None:
            continue
        oname = _safe_text(getattr(obj, "Name", "")).strip()
        if oname and oname == new_name:
            continue
        key = _safe_text(getattr(obj, "AutoRouteKey", "")).strip()
        if key and key == _safe_text(new_route_key).strip():
            continue
        kind = _safe_text(getattr(obj, "LinkKind", "")).strip().lower()
        if kind not in trunk_kinds:
            continue
        old_segs = _axis_segments_xy(_route_points_from_obj(backend, obj))
        if not old_segs:
            continue
        for s1 in new_segs:
            for s2 in old_segs:
                if _segments_overlap_xy(s1, s2):
                    return True
    return False


def _snapshot_used_ports(used_ports):
    snap = defaultdict(set)
    for k, vals in (used_ports or {}).items():
        try:
            snap[str(k)] = set(vals or [])
        except Exception:
            snap[str(k)] = set()
    return snap


def _restore_used_ports(used_ports, snapshot):
    try:
        used_ports.clear()
    except Exception:
        pass
    for k, vals in (snapshot or {}).items():
        try:
            used_ports[str(k)] = set(vals or [])
        except Exception:
            used_ports[str(k)] = set()


def _remove_route_by_key(doc, group_obj, route_key):
    obj = _find_route_obj_by_key(group_obj, route_key)
    if obj is None:
        return
    name = _safe_text(getattr(obj, "Name", "")).strip()
    if not name:
        return
    try:
        if doc.getObject(name) is not None:
            doc.removeObject(name)
    except Exception:
        pass


def _is_reverse_corner_backend(backend, p_prev, p_mid, p_next):
    try:
        v1 = backend._vec(
            float(p_mid.x) - float(p_prev.x),
            float(p_mid.y) - float(p_prev.y),
            float(p_mid.z) - float(p_prev.z),
        )
        v2 = backend._vec(
            float(p_next.x) - float(p_mid.x),
            float(p_next.y) - float(p_mid.y),
            float(p_next.z) - float(p_mid.z),
        )
        l1 = float(v1.Length)
        l2 = float(v2.Length)
        if l1 <= 0.1 or l2 <= 0.1:
            return False
        dot = float(v1.dot(v2) / (l1 * l2))
        return dot < -0.25
    except Exception:
        return False


def _has_endpoint_backtrack_backend(backend, points, at_start=False):
    pts = list(points or [])
    if len(pts) < 4:
        return False
    if at_start:
        return _is_reverse_corner_backend(backend, pts[0], pts[1], pts[2]) or _is_reverse_corner_backend(backend, pts[1], pts[2], pts[3])
    return _is_reverse_corner_backend(backend, pts[-1], pts[-2], pts[-3]) or _is_reverse_corner_backend(backend, pts[-2], pts[-3], pts[-4])


def _crosses_box_interior_xy_backend(obj, points, margin=2.0):
    pts = list(points or [])
    if obj is None or len(pts) < 3:
        return False
    try:
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull():
            return False
        bb = shape.BoundBox
    except Exception:
        return False
    xmin = float(bb.XMin) + float(margin)
    xmax = float(bb.XMax) - float(margin)
    ymin = float(bb.YMin) + float(margin)
    ymax = float(bb.YMax) - float(margin)
    if xmin >= xmax or ymin >= ymax:
        return False
    for p in pts[1:-1]:
        try:
            x = float(p.x)
            y = float(p.y)
        except Exception:
            continue
        if (xmin < x < xmax) and (ymin < y < ymax):
            return True
    return False


def _trunk_route_issues(backend, src_obj, dst_obj, points):
    issues = []
    pts = list(points or [])
    if _has_endpoint_backtrack_backend(backend, pts, at_start=True):
        issues.append("retroceso_salida")
    if _has_endpoint_backtrack_backend(backend, pts, at_start=False):
        issues.append("retroceso_llegada")
    if _crosses_box_interior_xy_backend(src_obj, pts):
        issues.append("atraviesa_origen")
    if _crosses_box_interior_xy_backend(dst_obj, pts):
        issues.append("atraviesa_destino")
    return issues


def _should_use_backbone_perimeter(backend, src_obj, dst_obj, route_by_perimeter, route_rect, route_z):
    if not bool(route_by_perimeter):
        return False
    if route_rect is None:
        return False
    if not (backend._is_octagon_box(src_obj) and backend._is_octagon_box(dst_obj)):
        return bool(route_by_perimeter)

    p1 = backend._anchor_point(src_obj)
    p2 = backend._anchor_point(dst_obj)
    dx = abs(float(p2.x) - float(p1.x))
    dy = abs(float(p2.y) - float(p1.y))

    # If the boxes are already aligned, forcing the perimeter usually creates
    # a U or C shape and also blocks the most convenient ports.
    if dx <= EPS or dy <= EPS:
        return False

    try:
        p1z = backend._vec(p1.x, p1.y, route_z)
        p2z = backend._vec(p2.x, p2.y, route_z)
        a_anchor, _side_a = backend._point_to_rect_border(p1z, route_rect)
        b_anchor, _side_b = backend._point_to_rect_border(p2z, route_rect)
        border_pts = backend._border_path_between(a_anchor, b_anchor, route_rect)
        perim_len = (
            float(p1z.distanceToPoint(a_anchor)) +
            _polyline_len(border_pts) +
            float(b_anchor.distanceToPoint(p2z))
        )
        direct_len = dx + dy
        if perim_len > (direct_len * 1.35):
            return False
    except Exception:
        pass
    return True


def connect_branch_pair(
    doc,
    src_obj,
    dst_obj,
    link_kind,
    circuit_id,
    conduit_type,
    diameter,
    bend_radius,
    route_z,
    route_by_perimeter,
    route_rect,
    used_ports,
    group_target,
    existing_keys,
    skip_existing=True,
):
    return connect_branch_pair_with_kind(
        doc=doc,
        src_obj=src_obj,
        dst_obj=dst_obj,
        link_kind=link_kind,
        circuit_id=circuit_id,
        conduit_type=conduit_type,
        diameter=diameter,
        bend_radius=bend_radius,
        route_z=route_z,
        route_by_perimeter=route_by_perimeter,
        route_rect=route_rect,
        used_ports=used_ports,
        group_target=group_target,
        existing_keys=existing_keys,
        skip_existing=skip_existing,
    )


def connect_branch_pair_with_kind(
    doc,
    src_obj,
    dst_obj,
    link_kind,
    circuit_id,
    conduit_type,
    diameter,
    bend_radius,
    route_z,
    route_by_perimeter,
    route_rect,
    used_ports,
    group_target,
    existing_keys,
    skip_existing=True,
):
    backend = cargar_backend_v1()
    kind_low = str(link_kind or "").strip().lower()
    src_is_lum = _is_luminaria_obj(backend, src_obj)
    dst_is_lum = _is_luminaria_obj(backend, dst_obj)
    src_is_switch = _is_switch_obj(backend, src_obj)
    dst_is_switch = _is_switch_obj(backend, dst_obj)
    is_lum_drop = kind_low in ("drop_box", "drop_nearest") and (src_is_lum or dst_is_lum)
    is_switch_drop = kind_low in ("drop_box", "drop_nearest") and (src_is_switch or dst_is_switch) and (not is_lum_drop)
    use_perimeter = _should_use_backbone_perimeter(
        backend=backend,
        src_obj=src_obj,
        dst_obj=dst_obj,
        route_by_perimeter=route_by_perimeter if kind_low == "backbone" else False,
        route_rect=route_rect,
        route_z=route_z,
    ) if kind_low == "backbone" else bool(route_by_perimeter)
    prev_patch = bool(getattr(backend, "RAMAL_LUZ_PATCH_ACTIVE", False))
    prev_allow_diag = getattr(backend, "ALLOW_DIAGONAL_PORTS_FOR_SWITCH_BOXES", None)
    prev_strict_cardinal = getattr(backend, "STRICT_BACKBONE_CARDINAL", None)
    prev_pref_ports_fn = getattr(backend, "_preferred_ports_for_link_end", None)
    prev_world_ports_fn = getattr(backend, "_world_ports", None)
    prev_rename_oct_ports_fn = getattr(backend, "_rename_octagon_ports_world", None)
    prev_backbone_pair_fn = getattr(backend, "_preferred_backbone_port_pair", None)
    trunk_cardinal_mode = kind_low in ("backbone", "switch_backbone", "feeder")
    # Mantener patch solo en bajadas (luminaria/apagador).
    # En troncales lo dejamos inactivo para preservar el comportamiento
    # estable de _connect_pair (stubs perpendiculares en cara de caja).
    patch_active_for_call = bool(is_lum_drop or is_switch_drop)
    try:
        setattr(backend, "RAMAL_LUZ_PATCH_ACTIVE", patch_active_for_call)
        # Perfil estable:
        # - Troncales cardinales estrictos para evitar snake/retrocesos.
        # - Bajante apagador->octogonal prioriza Bottom.
        if trunk_cardinal_mode:
            try:
                setattr(backend, "ALLOW_DIAGONAL_PORTS_FOR_SWITCH_BOXES", False)
            except Exception:
                pass
            try:
                setattr(backend, "STRICT_BACKBONE_CARDINAL", True)
            except Exception:
                pass
        if trunk_cardinal_mode and callable(prev_backbone_pair_fn):
            def _preferred_backbone_pair_trunk_stable(src_obj_inner, dst_obj_inner):
                pair = prev_backbone_pair_fn(src_obj_inner, dst_obj_inner)
                try:
                    if not (bool(backend._is_octagon_box(src_obj_inner)) and bool(backend._is_octagon_box(dst_obj_inner))):
                        return pair
                    p1 = backend._anchor_point(src_obj_inner)
                    p2 = backend._anchor_point(dst_obj_inner)
                    dx = abs(float(p2.x) - float(p1.x))
                    dy = abs(float(p2.y) - float(p1.y))
                    near_tol = max(25.0, min(float(bend_radius), 90.0))
                    if dx <= near_tol and dy <= near_tol:
                        ddx = float(p2.x) - float(p1.x)
                        if abs(ddx) <= EPS:
                            sname = _safe_text(getattr(src_obj_inner, "Name", ""))
                            dname = _safe_text(getattr(dst_obj_inner, "Name", ""))
                            ddx = 1.0 if sname <= dname else -1.0
                        if ddx >= 0.0:
                            return {"src": ("East",), "dst": ("West",), "final_axis": "x"}
                        return {"src": ("West",), "dst": ("East",), "final_axis": "x"}
                except Exception:
                    return pair
                return pair
            try:
                setattr(backend, "_preferred_backbone_port_pair", _preferred_backbone_pair_trunk_stable)
            except Exception:
                pass
        if trunk_cardinal_mode and callable(prev_rename_oct_ports_fn):
            def _rename_oct_ports_external_ring(obj, ports):
                prev_flag = bool(getattr(backend, "RAMAL_LUZ_PATCH_ACTIVE", False))
                try:
                    # Activar solo durante el renombrado para forzar filtro
                    # de puertos externos (anillo/perimetro), sin dejar patch
                    # activo en _connect_pair.
                    setattr(backend, "RAMAL_LUZ_PATCH_ACTIVE", True)
                    return prev_rename_oct_ports_fn(obj, ports)
                finally:
                    try:
                        setattr(backend, "RAMAL_LUZ_PATCH_ACTIVE", prev_flag)
                    except Exception:
                        pass
            try:
                setattr(backend, "_rename_octagon_ports_world", _rename_oct_ports_external_ring)
            except Exception:
                pass
        if is_switch_drop and callable(prev_pref_ports_fn):
            def _preferred_ports_switch_side(end_obj, other_obj, link_kind_inner, toward_point=None):
                base = prev_pref_ports_fn(end_obj, other_obj, link_kind_inner, toward_point=toward_point)
                try:
                    if not bool(backend._is_octagon_box(end_obj)):
                        return base
                except Exception:
                    return base
                if _is_luminaria_obj(backend, other_obj):
                    return base
                if not _is_switch_obj(backend, other_obj):
                    return base
                return ("Bottom", "North", "East", "South", "West")
            try:
                setattr(backend, "_preferred_ports_for_link_end", _preferred_ports_switch_side)
            except Exception:
                pass
        if is_switch_drop and callable(prev_world_ports_fn):
            def _world_ports_switch_bottom_fix(obj):
                ports = list(prev_world_ports_fn(obj) or [])
                try:
                    if not bool(backend._is_octagon_box(obj)):
                        return ports
                except Exception:
                    return ports
                out = []
                for p in ports:
                    if not isinstance(p, dict):
                        out.append(p)
                        continue
                    q = dict(p)
                    pname = _safe_text(q.get("name", "")).strip()
                    if pname == "Bottom":
                        try:
                            sh = getattr(obj, "Shape", None)
                            bb = getattr(sh, "BoundBox", None) if sh is not None else None
                            if bb is not None:
                                q["point"] = backend._vec(
                                    0.5 * (float(bb.XMin) + float(bb.XMax)),
                                    0.5 * (float(bb.YMin) + float(bb.YMax)),
                                    float(bb.ZMin),
                                )
                            q["dir"] = backend._vec(0.0, 0.0, -1.0)
                        except Exception:
                            pass
                    out.append(q)
                return out
            try:
                setattr(backend, "_world_ports", _world_ports_switch_bottom_fix)
            except Exception:
                pass
    except Exception:
        pass
    try:
        connect_kwargs = dict(
            doc=doc,
            src_obj=src_obj,
            dst_obj=dst_obj,
            circuit_id=circuit_id,
            conduit_type=conduit_type,
            diameter=float(diameter),
            bend_radius=float(bend_radius),
            route_z=float(route_z),
            orthogonal_route=True,
            route_by_perimeter=bool(use_perimeter),
            route_rect=(route_rect if use_perimeter else None),
            guide_objs=[],
            guide_section_key="",
            link_kind=str(link_kind or ""),
            board_obj=None,
            anchor_face="Auto",
            anchor_faces=[],
            feeder_lane_vec=backend._vec(0.0, 0.0, 0.0),
            feeder_board_lane_index=0,
            feeder_board_lane_count=1,
            feeder_board_lane_separation=0.0,
            feeder_board_section_index=0,
            feeder_board_section_count=1,
            feeder_board_section_lane_index=0,
            feeder_board_section_lane_count=1,
            reserve_ports=True,
            used_ports=used_ports,
            group_target=group_target,
            existing_keys=existing_keys,
            skip_existing=bool(skip_existing),
        )

        def _run_connect_with_forced_pair(pair_payload=None):
            prev_pair_local = getattr(backend, "_preferred_backbone_port_pair", None)
            if pair_payload is not None:
                def _forced_pair(_src_obj_inner, _dst_obj_inner):
                    return pair_payload
                try:
                    setattr(backend, "_preferred_backbone_port_pair", _forced_pair)
                except Exception:
                    pass
            try:
                return backend._connect_pair(**connect_kwargs)
            finally:
                if pair_payload is not None:
                    try:
                        setattr(backend, "_preferred_backbone_port_pair", prev_pair_local)
                    except Exception:
                        pass

        def _pair_payload_for_axis(axis_name):
            try:
                p1 = backend._anchor_point(src_obj)
                p2 = backend._anchor_point(dst_obj)
                dx = float(p2.x) - float(p1.x)
                dy = float(p2.y) - float(p1.y)
            except Exception:
                return None
            ax = _safe_text(axis_name).strip().lower()
            if ax == "x":
                if abs(dx) <= EPS:
                    sname = _safe_text(getattr(src_obj, "Name", ""))
                    dname = _safe_text(getattr(dst_obj, "Name", ""))
                    dx = 1.0 if sname <= dname else -1.0
                if dx >= 0.0:
                    return {"src": ("East",), "dst": ("West",), "final_axis": "x"}
                return {"src": ("West",), "dst": ("East",), "final_axis": "x"}
            if abs(dy) <= EPS:
                sname = _safe_text(getattr(src_obj, "Name", ""))
                dname = _safe_text(getattr(dst_obj, "Name", ""))
                dy = 1.0 if sname <= dname else -1.0
            if dy >= 0.0:
                return {"src": ("North",), "dst": ("South",), "final_axis": "y"}
            return {"src": ("South",), "dst": ("North",), "final_axis": "y"}

        used_ports_snapshot = _snapshot_used_ports(used_ports) if trunk_cardinal_mode else None
        status, route_key = _run_connect_with_forced_pair(None)

        if (
            trunk_cardinal_mode
            and status == "created"
            and bool(route_key)
            and (group_target is not None)
            and (used_ports_snapshot is not None)
        ):
            route_obj = _find_route_obj_by_key(group_target, route_key)
            issues = _trunk_route_issues(backend, src_obj, dst_obj, _route_points_from_obj(backend, route_obj))
            if issues:
                _remove_route_by_key(doc, group_target, route_key)
                _restore_used_ports(used_ports, used_ports_snapshot)
                try:
                    existing_keys.discard(route_key)
                except Exception:
                    pass

                p1 = backend._anchor_point(src_obj)
                p2 = backend._anchor_point(dst_obj)
                dx = abs(float(p2.x) - float(p1.x))
                dy = abs(float(p2.y) - float(p1.y))
                dominant_axis = "x" if dx >= dy else "y"
                alternate_axis = "y" if dominant_axis == "x" else "x"
                retry_axes = [alternate_axis, dominant_axis]
                tried = set()
                retried_ok = False
                for axis in retry_axes:
                    if axis in tried:
                        continue
                    tried.add(axis)
                    payload = _pair_payload_for_axis(axis)
                    if payload is None:
                        continue
                    status_retry, route_key_retry = _run_connect_with_forced_pair(payload)
                    if status_retry != "created" or not route_key_retry:
                        _restore_used_ports(used_ports, used_ports_snapshot)
                        continue
                    route_obj_retry = _find_route_obj_by_key(group_target, route_key_retry)
                    issues_retry = _trunk_route_issues(backend, src_obj, dst_obj, _route_points_from_obj(backend, route_obj_retry))
                    if issues_retry:
                        _remove_route_by_key(doc, group_target, route_key_retry)
                        _restore_used_ports(used_ports, used_ports_snapshot)
                        try:
                            existing_keys.discard(route_key_retry)
                        except Exception:
                            pass
                        continue
                    status, route_key = status_retry, route_key_retry
                    retried_ok = True
                    break

                if not retried_ok:
                    _restore_used_ports(used_ports, used_ports_snapshot)
                    status, route_key = _run_connect_with_forced_pair(None)

        return status, route_key
    finally:
        try:
            if callable(prev_pref_ports_fn):
                setattr(backend, "_preferred_ports_for_link_end", prev_pref_ports_fn)
        except Exception:
            pass
        try:
            if callable(prev_backbone_pair_fn):
                setattr(backend, "_preferred_backbone_port_pair", prev_backbone_pair_fn)
        except Exception:
            pass
        try:
            if callable(prev_rename_oct_ports_fn):
                setattr(backend, "_rename_octagon_ports_world", prev_rename_oct_ports_fn)
        except Exception:
            pass
        try:
            if callable(prev_world_ports_fn):
                setattr(backend, "_world_ports", prev_world_ports_fn)
        except Exception:
            pass
        try:
            if prev_allow_diag is not None:
                setattr(backend, "ALLOW_DIAGONAL_PORTS_FOR_SWITCH_BOXES", prev_allow_diag)
        except Exception:
            pass
        try:
            if prev_strict_cardinal is not None:
                setattr(backend, "STRICT_BACKBONE_CARDINAL", prev_strict_cardinal)
        except Exception:
            pass
        try:
            setattr(backend, "RAMAL_LUZ_PATCH_ACTIVE", prev_patch)
        except Exception:
            pass
