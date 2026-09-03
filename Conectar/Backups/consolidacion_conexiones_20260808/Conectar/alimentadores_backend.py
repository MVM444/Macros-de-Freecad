"""Shared backend for ElectricCR feeder routing.

Current state:
- wraps the stable feeder routing internals from Conectar_Cajas_a_Tablero_Auto.FCMacro
- exposes a smaller API for a dedicated feeders-only macro
- keeps the runtime dependency encapsulated in one file
"""

from __future__ import annotations

import importlib.machinery
import re
import sys
import types
from pathlib import Path

import FreeCAD as App

try:
    import networkx as nx  # noqa: F401
    NETWORKX_AVAILABLE = True
except Exception:
    nx = None  # type: ignore
    NETWORKX_AVAILABLE = False


_BACKEND_V1 = None


def _log(msg):
    try:
        App.Console.PrintMessage(f"[ALIM_BACKEND] {msg}\n")
    except Exception:
        pass


def _safe_name_token(value, fallback="X"):
    txt = str(value or "").strip()
    if not txt:
        return fallback
    txt = re.sub(r"[^0-9A-Za-z_]+", "_", txt)
    txt = re.sub(r"_+", "_", txt).strip("_")
    return txt or fallback


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
    loader = importlib.machinery.SourceFileLoader("electriccr_alimentadores_backend_v1", str(macro_path))
    module = types.ModuleType(loader.name)
    module.__file__ = str(macro_path)
    loader.exec_module(module)
    _BACKEND_V1 = module
    return module


def networkx_available():
    return bool(NETWORKX_AVAILABLE)


def default_engine_config():
    return dict(cargar_backend_v1()._default_config())


def selection_context(doc):
    return cargar_backend_v1()._selection_context(doc)


def candidate_circuit_groups(doc, selected_groups):
    return cargar_backend_v1()._candidate_circuit_groups(doc, selected_groups)


def sort_circuit_groups_manual(circuit_groups, cfg):
    return cargar_backend_v1()._sort_circuit_groups_manual(circuit_groups, cfg)


def find_object_by_name(doc, name):
    return cargar_backend_v1()._find_object_by_name(doc, name)


def objects_by_names(doc, names):
    return cargar_backend_v1()._objects_by_names(doc, names)


def anchor_allowed_faces(cfg):
    return cargar_backend_v1()._anchor_allowed_faces(cfg)


def group_id(group_obj):
    return cargar_backend_v1()._group_id(group_obj)


def circuit_id_for_group(group_obj):
    return cargar_backend_v1()._circuit_id_for_group(group_obj)


def import_component_classifier():
    return cargar_backend_v1()._import_component_classifier()


def _is_real_octagon_box(obj):
    if obj is None:
        return False
    try:
        type_id = str(getattr(obj, "TypeId", "") or "").strip()
        tipo = str(getattr(obj, "Tipo", "") or "").strip()
        puertos = getattr(obj, "PuertosJSON", None)
        if tipo == "EMT_Octagon_Box":
            return True
        if puertos is not None and str(puertos).strip():
            return True
        if hasattr(obj, "CajaOrigenKey") and puertos is not None:
            return True
        if type_id.startswith("Part::Part2DObject") and tipo == "ConduitPath":
            return False
    except Exception:
        return False
    return False


def _is_real_device(obj):
    if obj is None:
        return False
    try:
        tipo = str(getattr(obj, "Tipo", "") or "").strip()
        type_id = str(getattr(obj, "TypeId", "") or "").strip()
        if tipo == "ConduitPath":
            return False
        if type_id.startswith("Part::Part2DObject") and "Wire" in str(getattr(obj, "Name", "") or ""):
            return False
    except Exception:
        return False
    return True


def collect_circuit_objects(circuit_group, include_apagadores):
    backend = cargar_backend_v1()
    get_component_type = backend._import_component_classifier()
    devices, boxes = backend._collect_circuit_objects(
        circuit_group,
        get_component_type=get_component_type,
        include_apagadores=bool(include_apagadores),
    )
    real_boxes = []
    for obj in list(boxes or []):
        if _is_real_octagon_box(obj):
            real_boxes.append(obj)
        else:
            _log(
                "Caja descartada por filtro estricto | circuito={} | obj={} | tipo={} | typeid={}".format(
                    str(getattr(circuit_group, "Label", "") or getattr(circuit_group, "Name", "") or "-"),
                    str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "-"),
                    str(getattr(obj, "Tipo", "") or "-"),
                    str(getattr(obj, "TypeId", "") or "-"),
                )
            )
    real_devices = [obj for obj in list(devices or []) if _is_real_device(obj)]
    return real_devices, real_boxes


def map_boxes_by_source(boxes):
    return cargar_backend_v1()._map_boxes_by_source(boxes)


def build_plan_for_circuit(circuit_group, devices, boxes, cfg, board_obj):
    backend = cargar_backend_v1()
    box_by_source = backend._map_boxes_by_source(boxes)
    plan = backend._build_plan_for_circuit(
        circuit_group=circuit_group,
        devices=devices,
        boxes=boxes,
        box_by_source=box_by_source,
        board_obj=board_obj,
        cfg=cfg,
    )
    best_source = _best_feeder_source(circuit_group, devices, boxes, board_obj, cfg)
    if best_source is not None:
        plan = _replace_feeder_source(plan, best_source, board_obj)
    feeder_count = sum(1 for _a, _b, kind in list(plan or []) if str(kind or "").strip().lower() == "feeder")
    _log(
        "Plan de alimentador | circuito={} | cajas={} | dispositivos={} | feeders={}".format(
            str(getattr(circuit_group, "Label", "") or getattr(circuit_group, "Name", "") or "-"),
            len(list(boxes or [])),
            len(list(devices or [])),
            feeder_count,
        )
    )
    return plan, box_by_source


def feeder_source_from_plan(plan):
    return cargar_backend_v1()._feeder_source_from_plan(plan)


def feeder_lane_map(jobs, board_obj, guide_objs, cfg):
    backend = cargar_backend_v1()
    with _patched_board_top_spacing(backend, cfg.get("bend_radius", 100.0), cfg.get("board_slot_rows", 2)), _patched_effective_fillet_radius(backend):
        lane_map, lane_count, lane_meta = backend._feeder_lane_map(jobs, board_obj, guide_objs, cfg)
    lane_map, lane_count, lane_meta = _retune_top_bottom_lane_meta(
        backend, jobs, board_obj, guide_objs, lane_map, lane_count, lane_meta, cfg
    )
    # Por ahora no imponemos la tabla manual del tablero en el ruteo.
    # El usuario pidio que la entrada se resuelva desde el orden real de alimentadores.
    return _annotate_global_guide_lanes(backend, jobs, guide_objs, lane_map, lane_count, lane_meta, cfg)


def lane_offset_vector(lane_index, lane_count, separation, axis):
    return cargar_backend_v1()._lane_offset_vector(lane_index, lane_count, separation, axis)


def _guide_object_for_section(section_key, guide_objs):
    key = str(section_key or "").strip()
    if not key:
        return None
    for obj in list(guide_objs or []):
        if obj is None:
            continue
        name = str(getattr(obj, "Name", "") or "").strip()
        label = str(getattr(obj, "Label", "") or "").strip()
        if key and (key == name or key == label):
            return obj
    return None


def _offset_axis_for_guide(section_key, guide_objs):
    backend = cargar_backend_v1()
    obj = _guide_object_for_section(section_key, guide_objs)
    if obj is None:
        return "Horizontal"
    pts = list(backend._polyline_points_from_object(obj) or [])
    if len(pts) < 2:
        return "Horizontal"
    total_dx = 0.0
    total_dy = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        total_dx += abs(float(b.x) - float(a.x))
        total_dy += abs(float(b.y) - float(a.y))
    # Guia horizontal -> offset vertical. Guia vertical -> offset horizontal.
    return "Vertical" if total_dx >= total_dy else "Horizontal"


def _guide_flow_vector_for_section(section_key, guide_objs, board_obj=None):
    backend = cargar_backend_v1()
    obj = _guide_object_for_section(section_key, guide_objs)
    if obj is None:
        return App.Vector(1.0, 0.0, 0.0)
    pts = list(backend._polyline_points_from_object(obj) or [])
    if len(pts) < 2:
        return App.Vector(1.0, 0.0, 0.0)
    if board_obj is not None:
        try:
            board_pt = backend._anchor_point(board_obj)
            d0 = float(pts[0].distanceToPoint(board_pt))
            d1 = float(pts[-1].distanceToPoint(board_pt))
            if d0 <= d1:
                return App.Vector(float(pts[1].x) - float(pts[0].x), float(pts[1].y) - float(pts[0].y), 0.0)
            return App.Vector(float(pts[-2].x) - float(pts[-1].x), float(pts[-2].y) - float(pts[-1].y), 0.0)
        except Exception:
            pass
    return App.Vector(float(pts[1].x) - float(pts[0].x), float(pts[1].y) - float(pts[0].y), 0.0)


def lane_offset_vector_for_section(lane_index, lane_count, separation, section_key, guide_objs, board_obj=None):
    axis = _offset_axis_for_guide(section_key, guide_objs)
    flow = _guide_flow_vector_for_section(section_key, guide_objs, board_obj=board_obj)
    effective_lane_index = int(lane_index)
    if axis == "Vertical" and float(getattr(flow, "y", 0.0)) > 0.0:
        effective_lane_index = max(0, int(max(1, lane_count)) - 1 - int(lane_index))
    vec = cargar_backend_v1()._lane_offset_vector(effective_lane_index, lane_count, separation, axis)
    if axis == "Vertical" and float(getattr(flow, "x", 0.0)) < 0.0:
        vec = App.Vector(-float(getattr(vec, "x", 0.0)), -float(getattr(vec, "y", 0.0)), -float(getattr(vec, "z", 0.0)))
    elif axis == "Horizontal" and float(getattr(flow, "y", 0.0)) < 0.0:
        vec = App.Vector(-float(getattr(vec, "x", 0.0)), -float(getattr(vec, "y", 0.0)), -float(getattr(vec, "z", 0.0)))
    _log(
        "Vector de offset | seccion={} | eje={} | lane={}/{} | lane_eff={}/{} | sep={:.1f} | flow=({:.1f},{:.1f}) | vec=({:.1f},{:.1f},{:.1f})".format(
            str(section_key or "AUTO"),
            axis,
            int(lane_index),
            int(max(1, lane_count)),
            int(effective_lane_index),
            int(max(1, lane_count)),
            float(separation or 0.0),
            float(getattr(flow, "x", 0.0)),
            float(getattr(flow, "y", 0.0)),
            float(getattr(vec, "x", 0.0)),
            float(getattr(vec, "y", 0.0)),
            float(getattr(vec, "z", 0.0)),
        )
    )
    return vec


def _annotate_global_guide_lanes(backend, jobs, guide_objs, lane_map, lane_count, lane_meta, cfg=None):
    if not isinstance(lane_meta, dict) or not lane_meta:
        return lane_map, lane_count, lane_meta
    job_map = {
        str(job.get("job_key", "")).strip(): job
        for job in list(jobs or [])
        if str(job.get("job_key", "")).strip()
    }
    manual_enabled = bool((cfg or {}).get("manual_section_circuit_order_enabled", False))
    manual_map_cfg = dict((cfg or {}).get("manual_section_circuit_order_map", {}) or {})
    manual_global_enabled = bool((cfg or {}).get("manual_circuit_order_enabled", False))
    manual_global_order = {
        str(job_key).strip(): idx
        for idx, job_key in enumerate(list((cfg or {}).get("manual_circuit_order", []) or []))
        if str(job_key).strip()
    }
    grouped = {}
    for job_key, meta in list(lane_meta.items()):
        sec_key = str((meta or {}).get("section_key", "") or "").strip()
        if not sec_key or sec_key == "AUTO":
            continue
        guide_obj = _guide_object_for_section(sec_key, guide_objs)
        job = job_map.get(str(job_key).strip())
        if guide_obj is None or job is None:
            continue
        src_obj = backend._feeder_source_from_plan(job.get("plan"))
        if src_obj is None:
            continue
        src_pt = backend._anchor_point(src_obj)
        pts = list(backend._polyline_points_from_object(guide_obj) or [])
        proj = backend._project_point_to_polyline_xy(src_pt, pts) if len(pts) >= 2 else None
        s_val = float((proj or {}).get("s", 0.0))
        grouped.setdefault(sec_key, []).append((s_val, str(job_key).strip(), str(job.get("circuit_id", "") or "")))

    for sec_key, items in grouped.items():
        sec_manual = {
            str(job_key).strip(): idx
            for idx, job_key in enumerate(list(manual_map_cfg.get(sec_key, []) or []))
            if str(job_key).strip()
        } if manual_enabled else {}
        items = sorted(
            items,
            key=lambda it: (
                int(sec_manual.get(it[1], 10 ** 8)),
                int(manual_global_order.get(it[1], 10 ** 8 if manual_global_enabled else 10 ** 9)),
                float(it[0]),
                str(it[2]),
            ),
        )
        count = max(1, len(items))
        for idx, (_s, job_key, _label) in enumerate(items):
            meta = dict(lane_meta.get(job_key, {}) or {})
            meta["guide_lane_index"] = int(idx)
            meta["guide_lane_count"] = int(count)
            lane_meta[job_key] = meta
        _log(
            "Carriles globales por guia | seccion={} | orden={}".format(
                sec_key,
                " -> ".join(
                    "{}[{}/{}]".format(label or job_key, idx, count)
                    for idx, (_s, job_key, label) in enumerate(items)
                ),
            )
        )
    return lane_map, lane_count, lane_meta


class _patched_board_manual_point(object):
    def __init__(self, backend, board_obj, face_name, point):
        self.backend = backend
        self.board_obj = board_obj
        self.face_name = str(face_name or "").strip()
        self.point = point
        self.original = None

    def __enter__(self):
        self.original = getattr(self.backend, "_board_face_endpoint", None)
        if self.original is None or self.board_obj is None or self.point is None or self.face_name not in ("Top", "Bottom"):
            return self
        backend = self.backend
        original = self.original
        board_name = str(getattr(self.board_obj, "Name", "") or "")
        point = self.point
        face_name = self.face_name

        def _override(obj, toward_point=None, forced_face="Auto", tangent_offset=0.0, allowed_faces=None, lane_index=0, lane_count=1, lane_separation=50.0, section_index=0, section_count=1, section_lane_index=0, section_lane_count=1):
            name = str(getattr(obj, "Name", "") or "")
            face = str(forced_face or "").strip() or face_name
            if name == board_name and face in ("Top", "Bottom"):
                result = original(
                    obj,
                    toward_point=toward_point,
                    forced_face=face_name,
                    tangent_offset=tangent_offset,
                    allowed_faces=allowed_faces,
                    lane_index=lane_index,
                    lane_count=lane_count,
                    lane_separation=lane_separation,
                    section_index=section_index,
                    section_count=section_count,
                    section_lane_index=section_lane_index,
                    section_lane_count=section_lane_count,
                )
                result = dict(result or {})
                result["point"] = point
                return result
            return original(
                obj,
                toward_point=toward_point,
                forced_face=forced_face,
                tangent_offset=tangent_offset,
                allowed_faces=allowed_faces,
                lane_index=lane_index,
                lane_count=lane_count,
                lane_separation=lane_separation,
                section_index=section_index,
                section_count=section_count,
                section_lane_index=section_lane_index,
                section_lane_count=section_lane_count,
            )

        setattr(self.backend, "_board_face_endpoint", _override)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.original is not None:
            setattr(self.backend, "_board_face_endpoint", self.original)
        return False


class _patched_global_board_top_bottom_endpoint(object):
    def __init__(self, backend, board_obj):
        self.backend = backend
        self.board_obj = board_obj
        self.original = None

    def __enter__(self):
        self.original = getattr(self.backend, "_board_face_endpoint", None)
        if self.original is None or self.board_obj is None:
            return self

        backend = self.backend
        original = self.original
        board_name = str(getattr(self.board_obj, "Name", "") or "")

        def _override(obj, toward_point=None, forced_face="Auto", tangent_offset=0.0, allowed_faces=None, lane_index=0, lane_count=1, lane_separation=50.0, section_index=0, section_count=1, section_lane_index=0, section_lane_count=1):
            name = str(getattr(obj, "Name", "") or "")
            face = str(forced_face or "").strip() or "Auto"
            if name == board_name and face in ("Top", "Bottom"):
                try:
                    bb = getattr(getattr(obj, "Shape", None), "BoundBox", None)
                except Exception:
                    bb = None
                if bb is not None:
                    x, y = backend._board_top_section_lane_point(
                        bb,
                        section_index=section_index,
                        section_count=section_count,
                        lane_index=section_lane_index,
                        lane_count=section_lane_count,
                        separation=lane_separation,
                    )
                    z = float(bb.ZMax) if face == "Top" else float(bb.ZMin)
                    return {
                        "point": backend._vec(float(x), float(y), z),
                        "port": face,
                        "dir": backend._vec(0.0, 0.0, 1.0 if face == "Top" else -1.0),
                    }
            return original(
                obj,
                toward_point=toward_point,
                forced_face=forced_face,
                tangent_offset=tangent_offset,
                allowed_faces=allowed_faces,
                lane_index=lane_index,
                lane_count=lane_count,
                lane_separation=lane_separation,
                section_index=section_index,
                section_count=section_count,
                section_lane_index=section_lane_index,
                section_lane_count=section_lane_count,
            )

        setattr(self.backend, "_board_face_endpoint", _override)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.original is not None:
            setattr(self.backend, "_board_face_endpoint", self.original)
        return False


def route_rect_for_backbone(boxes, cfg):
    return cargar_backend_v1()._route_rect_for_circuit([], boxes, cfg, board_obj=None, use_box_ports=False)


def route_rect_for_feeder(devices, boxes, cfg, board_obj):
    return cargar_backend_v1()._route_rect_for_circuit(devices, boxes, cfg, board_obj=board_obj, use_box_ports=True)


def ensure_child_group(doc, parent, label, prefix="Group"):
    return cargar_backend_v1()._ensure_child_group(doc, parent, label, prefix=prefix)


def find_child_group_by_label(parent, label):
    return cargar_backend_v1()._find_child_group_by_label(parent, label)


def _child_groups(parent):
    seen = set()
    out = []
    for attr in ("Group", "OutList"):
        try:
            values = list(getattr(parent, attr, []) or [])
        except Exception:
            values = []
        for obj in values:
            key = str(getattr(obj, "Name", "") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(obj)
    return out


def _child_groups_by_exact_label(parent, label):
    label_txt = str(label or "").strip()
    if not label_txt:
        return []
    seen = set()
    pending = list(_child_groups(parent) or [])
    out = []
    while pending:
        obj = pending.pop(0)
        key = str(getattr(obj, "Name", "") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        try:
            obj_label = str(getattr(obj, "Label", "") or "").strip()
            obj_name = str(getattr(obj, "Name", "") or "").strip()
            if obj_label == label_txt or obj_name == label_txt:
                out.append(obj)
        except Exception:
            pass
        pending.extend(_child_groups(obj))
    return out


def _group_has_ancestor(obj, parent):
    if obj is None or parent is None:
        return False
    parent_name = str(getattr(parent, "Name", "") or "")
    if not parent_name:
        return False
    seen = set()
    pending = list(getattr(obj, "InList", []) or [])
    while pending:
        cur = pending.pop(0)
        name = str(getattr(cur, "Name", "") or "")
        if not name or name in seen:
            continue
        if name == parent_name:
            return True
        seen.add(name)
        try:
            pending.extend(list(getattr(cur, "InList", []) or []))
        except Exception:
            pass
    return False


def _document_groups_by_exact_label(doc, label):
    label_txt = str(label or "").strip()
    if not label_txt or doc is None:
        return []
    out = []
    for obj in list(getattr(doc, "Objects", []) or []):
        try:
            obj_label = str(getattr(obj, "Label", "") or "").strip()
            obj_name = str(getattr(obj, "Name", "") or "").strip()
            if obj_label != label_txt and obj_name != label_txt:
                continue
            if not hasattr(obj, "Group") and not getattr(obj, "isDerivedFrom", None):
                continue
            out.append(obj)
        except Exception:
            continue
    return out


def _expected_child_group_base(parent, label, prefix):
    return "{}_{}_{}".format(
        str(prefix or "Group"),
        _safe_name_token(getattr(parent, "Name", "Root"), "Root"),
        _safe_name_token(label, "Grupo"),
    )


def _document_groups_by_expected_name(doc, parent, label, prefix):
    if doc is None or parent is None:
        return []
    base = _expected_child_group_base(parent, label, prefix)
    out = []
    seen = set()
    for obj in list(getattr(doc, "Objects", []) or []):
        try:
            name = str(getattr(obj, "Name", "") or "").strip()
            obj_label = str(getattr(obj, "Label", "") or "").strip()
            if not name:
                continue
            if name != base and not name.startswith(base + "_"):
                continue
            if obj_label != str(label or "").strip() and name != str(label or "").strip() and not name.startswith(base):
                continue
            if name in seen:
                continue
            seen.add(name)
            out.append(obj)
        except Exception:
            continue
    return out


def _move_group_children(target, source):
    try:
        children = list(getattr(source, "Group", []) or [])
    except Exception:
        children = []
    for child in children:
        if child is None or child is target:
            continue
        try:
            if child not in list(getattr(target, "Group", []) or []):
                target.addObject(child)
        except Exception:
            pass


def _remove_group(doc, parent, grp):
    try:
        if parent is not None and hasattr(parent, "removeObject"):
            parent.removeObject(grp)
    except Exception:
        pass
    try:
        if doc is not None and hasattr(grp, "Name"):
            doc.removeObject(grp.Name)
    except Exception:
        pass


def _matches_generated_group_prefix(obj, prefixes):
    label = str(getattr(obj, "Label", "") or "").strip()
    name = str(getattr(obj, "Name", "") or "").strip()
    return any(label.startswith(prefix) or name.startswith(prefix) for prefix in list(prefixes or []))


def cleanup_empty_generated_groups(doc, prefixes=None):
    if doc is None:
        return 0
    prefixes = tuple(prefixes or ("Alimentadores_", "Tuberias_", "Ramales_"))
    removed = 0
    seen = set()
    for obj in list(getattr(doc, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        if not hasattr(obj, "Group") and not getattr(obj, "isDerivedFrom", None):
            continue
        if not _matches_generated_group_prefix(obj, prefixes):
            continue
        try:
            children = list(getattr(obj, "Group", []) or [])
        except Exception:
            children = []
        if children:
            continue
        for parent in list(getattr(obj, "InList", []) or []):
            try:
                if hasattr(parent, "removeObject"):
                    parent.removeObject(obj)
            except Exception:
                pass
        try:
            doc.removeObject(name)
            removed += 1
        except Exception:
            pass
    if removed:
        _log("Grupos generados vacios eliminados | cantidad={}".format(int(removed)))
    return int(removed)


def ensure_unique_child_group(doc, parent, label, prefix="Group", create_if_missing=True):
    groups = list(_child_groups_by_exact_label(parent, label) or [])
    if not groups:
        grp = find_child_group_by_label(parent, label)
        if grp is not None:
            groups = [grp]
    if not groups and doc is not None and parent is not None:
        doc_groups = list(_document_groups_by_expected_name(doc, parent, label, prefix) or [])
        if not doc_groups:
            doc_groups = [
                grp for grp in _document_groups_by_exact_label(doc, label)
                if grp is not None and (_group_has_ancestor(grp, parent) or _group_has_ancestor(parent, grp))
            ]
        if doc_groups:
            groups = doc_groups
    if not groups and bool(create_if_missing):
        grp = ensure_child_group(doc, parent, label, prefix=prefix)
        groups = [grp] if grp is not None else []
    if not groups:
        return None
    primary = groups[0]
    try:
        if parent is not None and primary not in list(getattr(parent, "Group", []) or []):
            parent.addObject(primary)
    except Exception:
        pass
    duplicates = [grp for grp in groups[1:] if grp is not None and grp is not primary]
    if duplicates:
        _log(
            "Grupos duplicados unificados | padre={} | label={} | duplicados={}".format(
                str(getattr(parent, "Label", getattr(parent, "Name", "Grupo")) or "Grupo"),
                str(label or "-"),
                int(len(duplicates)),
            )
        )
    for dup in duplicates:
        _move_group_children(primary, dup)
        _remove_group(doc, parent, dup)
    return primary


def collect_existing_route_keys(group_obj):
    return cargar_backend_v1()._collect_existing_route_keys(group_obj)


def delete_autoroute_objects(doc, group_obj):
    return cargar_backend_v1()._delete_autoroute_objects(doc, group_obj)


def delete_autoroute_feeders(doc, group_obj, board_name):
    return cargar_backend_v1()._delete_autoroute_feeders(doc, group_obj, board_name)


def reserve_existing_ports(group_obj, used_ports):
    return cargar_backend_v1()._reserve_existing_ports(group_obj, used_ports)


def connect_pair(
    doc,
    src_obj,
    dst_obj,
    circuit_id,
    conduit_type,
    diameter,
    bend_radius,
    route_z,
    route_by_perimeter,
    route_rect,
    guide_objs,
    guide_section_key,
    board_obj,
    anchor_face,
    anchor_faces,
    feeder_lane_vec,
    feeder_board_lane_index,
    feeder_board_lane_count,
    feeder_board_lane_separation,
    board_align_distance,
    feeder_board_section_index,
    feeder_board_section_count,
    feeder_board_section_lane_index,
    feeder_board_section_lane_count,
    used_ports,
    group_target,
    existing_keys,
    skip_existing=True,
    feeder_board_face="",
    manual_board_slot=False,
    board_slot_rows=2,
    board_entry_x=None,
    board_entry_y=None,
    guide_lane_index=0,
    guide_lane_count=1,
    guide_straight_priority=False,
):
    backend = cargar_backend_v1()
    manual_board_point = None
    board_rows = max(1, int(board_slot_rows or 2))
    with _patched_board_top_spacing(backend, bend_radius, board_rows), _patched_effective_fillet_radius(backend), _patched_port_stub(backend, bend_radius), _patched_top_bottom_board_route(backend, board_obj, feeder_board_face, bend_radius, feeder_board_lane_separation, feeder_board_section_lane_count, feeder_board_lane_index, guide_lane_count=guide_lane_count, guide_lane_index=guide_lane_index, guide_straight_priority=guide_straight_priority, board_align_distance=board_align_distance):
        if bool(manual_board_slot) and board_obj is not None and str(feeder_board_face or "").strip() in ("Top", "Bottom"):
            try:
                manual_board_point = backend._board_face_endpoint(
                    board_obj,
                    toward_point=None,
                    forced_face=str(feeder_board_face or "").strip(),
                    tangent_offset=0.0,
                    allowed_faces=[str(feeder_board_face or "").strip()],
                    lane_index=0,
                    lane_count=1,
                    lane_separation=float(feeder_board_lane_separation),
                    section_index=int(feeder_board_section_index),
                    section_count=int(feeder_board_section_count),
                    section_lane_index=int(feeder_board_section_lane_index),
                    section_lane_count=int(feeder_board_section_lane_count),
                ).get("point")
                if manual_board_point is not None:
                    _log(
                        "Punto manual tablero fijado | face={} | p=({:.1f},{:.1f},{:.1f})".format(
                            str(feeder_board_face or "-"),
                            float(getattr(manual_board_point, "x", 0.0)),
                            float(getattr(manual_board_point, "y", 0.0)),
                            float(getattr(manual_board_point, "z", 0.0)),
                        )
                    )
            except Exception:
                manual_board_point = None
        elif board_obj is not None and str(feeder_board_face or "").strip() in ("Top", "Bottom") and board_entry_x is not None and board_entry_y is not None:
            try:
                bb = getattr(getattr(board_obj, "Shape", None), "BoundBox", None)
            except Exception:
                bb = None
            if bb is not None:
                z = float(bb.ZMax) if str(feeder_board_face or "").strip() == "Top" else float(bb.ZMin)
                manual_board_point = backend._vec(float(board_entry_x), float(board_entry_y), float(z))
                _log(
                    "Punto auto tablero ajustado | face={} | p=({:.1f},{:.1f},{:.1f})".format(
                        str(feeder_board_face or "-"),
                        float(getattr(manual_board_point, "x", 0.0)),
                        float(getattr(manual_board_point, "y", 0.0)),
                        float(getattr(manual_board_point, "z", 0.0)),
                    )
                )
        with _patched_guide_hint_points(backend), _patched_global_board_top_bottom_endpoint(backend, board_obj), _patched_board_manual_point(backend, board_obj, feeder_board_face, manual_board_point):
            return backend._connect_pair(
                doc=doc,
                src_obj=src_obj,
                dst_obj=dst_obj,
            circuit_id=circuit_id,
            conduit_type=conduit_type,
            diameter=float(diameter),
            bend_radius=float(bend_radius),
            route_z=float(route_z),
            orthogonal_route=True,
            route_by_perimeter=bool(route_by_perimeter),
            route_rect=route_rect,
            guide_objs=list(guide_objs or []),
            guide_section_key=str(guide_section_key or ""),
            link_kind="feeder",
            board_obj=board_obj,
            anchor_face=str(anchor_face or "Auto"),
            anchor_faces=list(anchor_faces or []),
            feeder_lane_vec=feeder_lane_vec,
            feeder_board_lane_index=int(feeder_board_lane_index),
            feeder_board_lane_count=int(feeder_board_lane_count),
            feeder_board_lane_separation=float(feeder_board_lane_separation),
            feeder_board_section_index=int(feeder_board_section_index),
            feeder_board_section_count=int(feeder_board_section_count),
            feeder_board_section_lane_index=int(feeder_board_section_lane_index),
            feeder_board_section_lane_count=int(feeder_board_section_lane_count),
            reserve_ports=True,
            used_ports=used_ports,
            group_target=group_target,
            existing_keys=existing_keys,
            skip_existing=bool(skip_existing),
            )


def find_route_object_by_key(group_obj, route_key):
    backend = cargar_backend_v1()
    queue = [group_obj] if group_obj is not None else []
    seen = set()
    while queue:
        cur = queue.pop(0)
        gname = str(getattr(cur, "Name", "") or "")
        if gname:
            if gname in seen:
                continue
            seen.add(gname)
        for child in list(getattr(cur, "Group", []) or []):
            if backend._is_group(child):
                queue.append(child)
                continue
            key = str(getattr(child, "AutoRouteKey", "") or "").strip()
            if key and key == str(route_key or ""):
                return child
    return None


def mark_generated_by(route_obj, tag):
    if route_obj is None:
        return
    try:
        route_obj.GeneradoPor = str(tag)
    except Exception:
        pass


def _guide_objects_from_cfg(doc, cfg):
    backend = cargar_backend_v1()
    if doc is None:
        return []
    names = list(cfg.get("guide_names", []) or [])
    return [
        obj for obj in backend._objects_by_names(doc, names)
        if backend._is_guide_route_candidate(obj)
    ]


def _best_feeder_source(circuit_group, devices, boxes, board_obj, cfg):
    backend = cargar_backend_v1()
    if board_obj is None:
        return None
    candidates = list(boxes or []) or list(devices or [])
    if not candidates:
        return None
    doc = getattr(circuit_group, "Document", None)
    guide_objs = _guide_objects_from_cfg(doc, cfg)
    forced_face = str(cfg.get("anchor_face", "Auto") or "Auto")
    allowed_faces = backend._anchor_allowed_faces(cfg)
    best_obj = None
    best_key = None
    best_guide = "-"
    for obj in candidates:
        src_pt = backend._anchor_point(obj)
        board_ep = backend._board_face_endpoint(
            board_obj,
            toward_point=src_pt,
            forced_face=forced_face,
            tangent_offset=0.0,
            allowed_faces=allowed_faces,
        )
        board_pt = board_ep.get("point")
        if board_pt is None:
            continue
        guide_info = None
        if guide_objs:
            guide_info = backend._best_guide_for_pair(
                src_pt,
                board_pt,
                guide_objs,
                offset_vec=backend._vec(0.0, 0.0, 0.0),
                offset_scalar=0.0,
                prefer_start=True,
            )
        if guide_info is not None:
            cost = float(guide_info.get("cost", 0.0))
            guide_name = str(getattr(guide_info.get("obj"), "Label", "") or getattr(guide_info.get("obj"), "Name", "") or "-")
        else:
            cost = float(backend._distance_xy(src_pt, board_pt))
            guide_name = "-"
        key = (
            cost,
            float(backend._distance_xy(src_pt, board_pt)),
            backend._natural_key(str(getattr(obj, "Label", "") or getattr(obj, "Name", ""))),
        )
        if best_obj is None or key < best_key:
            best_obj = obj
            best_key = key
            best_guide = guide_name
    if best_obj is not None:
        _log(
            "Caja origen de alimentador seleccionada | circuito={} | caja={} | guia={} | costo={:.1f}".format(
                str(getattr(circuit_group, "Label", "") or getattr(circuit_group, "Name", "") or "-"),
                str(getattr(best_obj, "Label", "") or getattr(best_obj, "Name", "") or "-"),
                best_guide,
                float(best_key[0]),
            )
        )
    return best_obj


def _replace_feeder_source(plan, source_obj, board_obj):
    out = []
    replaced = False
    for src_obj, dst_obj, link_kind in list(plan or []):
        kind = str(link_kind or "").strip().lower()
        if kind == "feeder":
            if (not replaced) and source_obj is not None and board_obj is not None:
                out.append((source_obj, board_obj, "feeder"))
                replaced = True
            continue
        out.append((src_obj, dst_obj, link_kind))
    if (not replaced) and source_obj is not None and board_obj is not None:
        out.append((source_obj, board_obj, "feeder"))
    return out


class _patched_board_top_spacing(object):
    def __init__(self, backend, bend_radius, board_rows=2):
        self.backend = backend
        self.bend_radius = float(bend_radius or 100.0)
        self.board_rows = max(1, int(board_rows or 2))
        self.original = None

    def __enter__(self):
        self.original = getattr(self.backend, "_board_top_section_lane_point", None)
        if self.original is None:
            return self

        bend_radius = max(0.0, float(self.bend_radius))

        def _override(bb, section_index=0, section_count=1, lane_index=0, lane_count=1, separation=50.0):
            xmin = float(bb.XMin)
            xmax = float(bb.XMax)
            ymin = float(bb.YMin)
            ymax = float(bb.YMax)
            width = max(1e-6, xmax - xmin)
            depth = max(1e-6, ymax - ymin)
            total_slots = max(1, int(section_count))
            slot_start = max(0, min(total_slots - 1, int(section_index)))
            slot_span = max(1, int(lane_count))
            base_margin = min(max(4.0, 0.010 * width), 0.06 * width)
            span_min = xmin + base_margin
            span_max = xmax - base_margin
            if span_max <= span_min:
                span_min = xmin
                span_max = xmax
            slot_pitch = max(1e-6, (span_max - span_min) / float(total_slots))
            available_slots = max(1, total_slots - slot_start)
            slot_span = max(1, min(slot_span, available_slots))
            sec_xmin = span_min + (slot_pitch * float(slot_start))
            sec_xmax = sec_xmin + (slot_pitch * float(slot_span))
            section_width = max(1e-6, sec_xmax - sec_xmin)
            edge_pad = min(max(4.0, 0.006 * width), 0.03 * section_width)
            if slot_start <= 0:
                sec_xmin += edge_pad
            if (slot_start + slot_span) >= total_slots:
                sec_xmax -= edge_pad
            inner = min(max(2.0, 0.01 * section_width), 0.05 * section_width)
            sec_xmin += inner
            sec_xmax -= inner
            if sec_xmax <= sec_xmin:
                mid = 0.5 * (sec_xmin + sec_xmax)
                sec_xmin = mid
                sec_xmax = mid
            section_width = max(1e-6, sec_xmax - sec_xmin)

            n = max(1, int(lane_count))
            idx = max(0, min(n - 1, int(lane_index)))
            sep = max(0.0, float(separation))
            row_margin = min(max(max(24.0, 1.10 * sep, 0.55 * bend_radius), 0.0), 0.18 * depth)
            y_top = ymax - row_margin
            y_bottom = ymin + row_margin
            if y_bottom >= y_top:
                y_mid = 0.5 * (ymin + ymax)
                y_top = y_mid
                y_bottom = y_mid
            if n <= 1 or sec_xmax <= sec_xmin:
                x = 0.5 * (sec_xmin + sec_xmax)
                y = y_top
            else:
                nrows = max(1, min(int(self.board_rows), n))
                ncols = max(1, int((int(n) + int(nrows) - 1) // int(nrows)))
                col = int(idx // nrows)
                row = int(idx % nrows)
                block_width = max(1e-6, sec_xmax - sec_xmin)
                if ncols <= 1:
                    stagger = min(block_width, max(24.0, 0.90 * sep, 0.90 * bend_radius, 0.45 * block_width))
                    row_center = float(row) - (0.5 * float(max(1, nrows - 1)))
                    x = (0.5 * (sec_xmin + sec_xmax)) + (row_center * stagger)
                else:
                    pitch = max(1e-6, (sec_xmax - sec_xmin) / float(ncols - 1))
                    x_base = sec_xmin + ((sec_xmax - sec_xmin) * (float(col) / float(ncols - 1)))
                    stagger = min(0.70 * pitch, max(20.0, 0.65 * sep, 0.65 * bend_radius))
                    row_center = float(row) - (0.5 * float(max(1, nrows - 1)))
                    x = x_base + (row_center * stagger)
                x = max(sec_xmin, min(sec_xmax, x))
                if nrows <= 1:
                    y = 0.5 * (y_top + y_bottom)
                else:
                    y = y_top - ((y_top - y_bottom) * (float(row) / float(nrows - 1)))
            return x, y

        setattr(self.backend, "_board_top_section_lane_point", _override)
        _log(f"Parrilla Top ajustada para radio={bend_radius:.1f} mm | modo=cara_completa")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.original is not None:
            setattr(self.backend, "_board_top_section_lane_point", self.original)
        return False


class _patched_effective_fillet_radius(object):
    def __init__(self, backend):
        self.backend = backend
        self.original = None

    def __enter__(self):
        self.original = getattr(self.backend, "_effective_fillet_radius", None)
        if self.original is None:
            return self

        def _override(points, requested_radius):
            req = max(0.0, float(requested_radius or 0.0))
            if req <= 0.0:
                return 0.0
            pts = list(self.backend._dedup_points(points) or [])
            seg_lens = []
            for a, b in zip(pts[:-1], pts[1:]):
                try:
                    d = float(a.distanceToPoint(b))
                except Exception:
                    d = 0.0
                if d > 0.1:
                    seg_lens.append(d)
            if not seg_lens:
                return 0.0
            usable = list(seg_lens)
            if len(usable) >= 3:
                if usable[0] < req and len(usable) > 1:
                    usable = usable[1:]
                if usable and usable[-1] < req and len(usable) > 1:
                    usable = usable[:-1]
            limit = max(0.0, min(usable or seg_lens) * 0.98)
            return min(req, limit)

        setattr(self.backend, "_effective_fillet_radius", _override)
        _log("Radio efectivo de fillet ajustado | modo=ignora_stubs_cortos_en_extremos")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.original is not None:
            setattr(self.backend, "_effective_fillet_radius", self.original)
        return False


class _patched_port_stub(object):
    def __init__(self, backend, bend_radius):
        self.backend = backend
        self.bend_radius = float(bend_radius or 0.0)
        self.original = None

    def __enter__(self):
        self.original = getattr(self.backend, "DEFAULT_PORT_STUB", None)
        if self.original is None:
            return self
        try:
            new_val = max(float(self.original), float(self.bend_radius))
            setattr(self.backend, "DEFAULT_PORT_STUB", float(new_val))
            _log("Stub de puerto ajustado | valor={:.1f} mm".format(float(new_val)))
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.original is not None:
            try:
                setattr(self.backend, "DEFAULT_PORT_STUB", self.original)
            except Exception:
                pass
        return False


class _patched_guide_hint_points(object):
    def __init__(self, backend):
        self.backend = backend
        self.original = None

    def __enter__(self):
        self.original = getattr(self.backend, "_guide_hint_point_for_endpoint", None)
        if self.original is None:
            return self

        backend = self.backend
        original = self.original

        def _override(guide_info, end, z_level):
            if guide_info:
                proj_key = "src_proj" if str(end or "").strip().lower() == "src" else "dst_proj"
                proj = guide_info.get(proj_key)
                point = (proj or {}).get("point")
                if point is not None:
                    out = backend._vec(point.x, point.y, z_level)
                    _log(
                        "Hint de guia por proyeccion | end={} | p=({:.1f},{:.1f},{:.1f})".format(
                            str(end or "-"),
                            float(out.x),
                            float(out.y),
                            float(out.z),
                        )
                    )
                    return out
            return original(guide_info, end, z_level)

        setattr(self.backend, "_guide_hint_point_for_endpoint", _override)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.original is not None:
            setattr(self.backend, "_guide_hint_point_for_endpoint", self.original)
        return False


def _top_bottom_approach_strip(board_obj, guide_prev, guide_point, board_point, align_dist, final_axis=None):
    if board_obj is None or guide_point is None or board_point is None:
        return None
    gx = float(getattr(guide_point, "x", 0.0))
    gy = float(getattr(guide_point, "y", 0.0))
    bx = float(getattr(board_point, "x", 0.0))
    by = float(getattr(board_point, "y", 0.0))
    px = float(getattr(guide_prev, "x", gx))
    py = float(getattr(guide_prev, "y", gy))
    dir_x = float(gx - px)
    dir_y = float(gy - py)
    dx = float(bx - gx)
    dy = float(by - gy)
    align = max(200.0, float(align_dist))
    axis_hint = str(final_axis or "").strip().lower()
    if axis_hint not in ("x", "y"):
        axis_hint = "y" if abs(dir_y) >= abs(dir_x) else "x"
    if axis_hint == "y":
        dist = max(200.0, min(float(abs(dy)), align))
        sign = 1.0 if dy >= 0.0 else -1.0
        band = float(by - (sign * dist))
        lo = min(gy, by)
        hi = max(gy, by)
        band = max(lo, min(hi, band))
        return {"axis": "y", "band": float(band)}
    dist = max(200.0, min(float(abs(dx)), align))
    sign = 1.0 if dx >= 0.0 else -1.0
    band = float(bx - (sign * dist))
    lo = min(gx, bx)
    hi = max(gx, bx)
    band = max(lo, min(hi, band))
    return {"axis": "x", "band": float(band)}


def _trim_path_from_end(backend, points, trim_dist):
    pts = list(points or [])
    remain = max(0.0, float(trim_dist))
    if len(pts) < 2 or remain <= 1e-6:
        return pts
    out = list(pts)
    while len(out) >= 2 and remain > 1e-6:
        a = out[-2]
        b = out[-1]
        seg = ((float(getattr(b, "x", 0.0)) - float(getattr(a, "x", 0.0))) ** 2 + (float(getattr(b, "y", 0.0)) - float(getattr(a, "y", 0.0))) ** 2) ** 0.5
        if seg <= 1e-6:
            out.pop()
            continue
        if seg <= remain + 1e-6:
            out.pop()
            remain -= seg
            continue
        ratio = max(0.0, min(1.0, float((seg - remain) / seg)))
        out[-1] = backend._vec(
            float(getattr(a, "x", 0.0)) + ((float(getattr(b, "x", 0.0)) - float(getattr(a, "x", 0.0))) * ratio),
            float(getattr(a, "y", 0.0)) + ((float(getattr(b, "y", 0.0)) - float(getattr(a, "y", 0.0))) * ratio),
            float(getattr(b, "z", 0.0)),
        )
        remain = 0.0
    return out


class _patched_top_bottom_board_route(object):
    def __init__(self, backend, board_obj, face_name, bend_radius, lane_separation, lane_count, route_lane_index=0, guide_lane_count=1, guide_lane_index=0, guide_straight_priority=False, board_align_distance=None):
        self.backend = backend
        self.board_obj = board_obj
        self.face_name = str(face_name or "").strip()
        self.bend_radius = float(bend_radius or 100.0)
        self.lane_separation = float(lane_separation or 50.0)
        self.lane_count = max(1, int(lane_count or 1))
        self.route_lane_index = max(0, int(route_lane_index or 0))
        self.guide_lane_count = max(1, int(guide_lane_count or 1))
        self.guide_lane_index = max(0, int(guide_lane_index or 0))
        self.guide_straight_priority = bool(guide_straight_priority)
        self.board_align_distance = None if board_align_distance is None else float(board_align_distance)
        self.original = None

    def __enter__(self):
        self.original = getattr(self.backend, "_route_points_via_guide", None)
        if (
            self.original is None
            or self.board_obj is None
            or self.face_name not in ("Top", "Bottom")
            or getattr(self.backend, "_guide_path_between", None) is None
            or getattr(self.backend, "_orth2d", None) is None
            or getattr(self.backend, "_dedup_points", None) is None
            or getattr(self.backend, "_vec", None) is None
        ):
            return self

        backend = self.backend
        original = self.original
        board_obj = self.board_obj
        face_name = self.face_name
        lane_center = 0.5 * float(max(0, self.guide_lane_count - 1))
        lane_rank = abs(float(self.guide_lane_index) - lane_center)
        requested_align = 0.0 if self.board_align_distance is None else max(0.0, float(self.board_align_distance))
        default_align = max(700.0, (4.5 * self.bend_radius), (7.0 * self.lane_separation))
        align_base = max(requested_align if requested_align > 0.0 else default_align, (2.5 * self.bend_radius), (4.0 * self.lane_separation))
        align_step = max(20.0, (0.50 * self.lane_separation), (0.30 * self.bend_radius))
        straight_tol = max(25.0, (0.65 * self.lane_separation), (0.35 * self.bend_radius))

        def _override(p1, p2, z_level, guide_info, final_axis=None, entry_axis=None):
            if not guide_info:
                return original(p1, p2, z_level, guide_info, final_axis=final_axis, entry_axis=entry_axis)
            z = max(float(z_level), float(getattr(p1, "z", 0.0)), float(getattr(p2, "z", 0.0)))
            gp1 = (guide_info or {}).get("src_proj")
            gp2 = (guide_info or {}).get("dst_proj")
            guide_pts = list(backend._guide_path_between((guide_info or {}).get("points", []), gp1, gp2, z) or [])
            if not guide_pts:
                return original(p1, p2, z_level, guide_info, final_axis=final_axis, entry_axis=entry_axis)
            guide_end = guide_pts[-1]
            board_xy = backend._vec(float(getattr(p2, "x", 0.0)), float(getattr(p2, "y", 0.0)), z)
            lateral_delta = abs(float(getattr(board_xy, "x", 0.0)) - float(getattr(guide_end, "x", 0.0)))
            align_dist = float(align_base + (lane_rank * align_step) + (1.75 * lateral_delta))

            trimmed = _trim_path_from_end(backend, guide_pts, align_dist)
            if len(trimmed) >= 2:
                guide_prev = trimmed[-2]
                guide_last = trimmed[-1]
            else:
                guide_prev = guide_pts[-2] if len(guide_pts) >= 2 else guide_pts[-1]
                guide_last = guide_pts[-1]
            strip = _top_bottom_approach_strip(board_obj, guide_prev, guide_last, board_xy, align_dist, final_axis="Y")
            if not strip:
                return original(p1, p2, z_level, guide_info, final_axis=final_axis, entry_axis=entry_axis)

            pts = [p1, backend._vec(float(getattr(p1, "x", 0.0)), float(getattr(p1, "y", 0.0)), z)]
            pts.extend(list(backend._orth2d(pts[-1], guide_pts[0], z, final_axis=entry_axis) or [])[1:])
            pts.extend(trimmed[1:] if len(trimmed) >= 2 else guide_pts[1:])
            if str(strip.get("axis", "")).strip().lower() == "y":
                if self.guide_straight_priority and lateral_delta <= straight_tol:
                    pts.append(backend._vec(float(getattr(guide_last, "x", 0.0)), float(getattr(board_xy, "y", 0.0)), z))
                else:
                    band_y = float(strip.get("band", float(getattr(board_xy, "y", 0.0))))
                    pts.append(backend._vec(float(getattr(guide_last, "x", 0.0)), band_y, z))
                    pts.append(backend._vec(float(getattr(board_xy, "x", 0.0)), band_y, z))
            else:
                band_x = float(strip.get("band", float(getattr(board_xy, "x", 0.0))))
                pts.append(backend._vec(band_x, float(getattr(guide_last, "y", 0.0)), z))
                pts.append(backend._vec(band_x, float(getattr(board_xy, "y", 0.0)), z))
            pts.append(board_xy)
            pts.append(p2)
            out = list(backend._dedup_points(pts) or pts)
            _log(
                "Remate tablero en banda | face={} | eje={} | dist={:.1f} | guia=({:.1f},{:.1f}) | board=({:.1f},{:.1f})".format(
                    face_name,
                    str(strip.get("axis", "-")).upper(),
                    float(align_dist),
                    float(getattr(guide_last, "x", 0.0)),
                    float(getattr(guide_last, "y", 0.0)),
                    float(getattr(board_xy, "x", 0.0)),
                    float(getattr(board_xy, "y", 0.0)),
                )
            )
            return out

        setattr(self.backend, "_route_points_via_guide", _override)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.original is not None:
            setattr(self.backend, "_route_points_via_guide", self.original)
        return False


def _board_local_xy(backend, board_obj, point):
    if backend is None or board_obj is None or point is None:
        return 0.0, 0.0
    try:
        return float(getattr(point, "x", 0.0)), float(getattr(point, "y", 0.0))
    except Exception:
        return float(getattr(point, "x", 0.0)), float(getattr(point, "y", 0.0))


def _preview_board_top_section_lane_point(board_obj, bend_radius, board_rows, separation, section_index, section_count, lane_index, lane_count):
    if board_obj is None:
        return None
    try:
        bb = getattr(getattr(board_obj, "Shape", None), "BoundBox", None)
    except Exception:
        bb = None
    if bb is None:
        return None
    xmin = float(bb.XMin)
    xmax = float(bb.XMax)
    ymin = float(bb.YMin)
    ymax = float(bb.YMax)
    width = max(1e-6, xmax - xmin)
    depth = max(1e-6, ymax - ymin)
    bend_radius = max(0.0, float(bend_radius or 0.0))
    total_slots = max(1, int(section_count))
    slot_start = max(0, min(total_slots - 1, int(section_index)))
    slot_span = max(1, int(lane_count))
    base_margin = min(max(4.0, 0.010 * width), 0.06 * width)
    span_min = xmin + base_margin
    span_max = xmax - base_margin
    if span_max <= span_min:
        span_min = xmin
        span_max = xmax
    slot_pitch = max(1e-6, (span_max - span_min) / float(total_slots))
    available_slots = max(1, total_slots - slot_start)
    slot_span = max(1, min(slot_span, available_slots))
    sec_xmin = span_min + (slot_pitch * float(slot_start))
    sec_xmax = sec_xmin + (slot_pitch * float(slot_span))
    section_width = max(1e-6, sec_xmax - sec_xmin)
    edge_pad = min(max(4.0, 0.006 * width), 0.03 * section_width)
    if slot_start <= 0:
        sec_xmin += edge_pad
    if (slot_start + slot_span) >= total_slots:
        sec_xmax -= edge_pad
    section_width = max(1e-6, sec_xmax - sec_xmin)
    inner = min(max(2.0, 0.01 * section_width), 0.05 * section_width)
    sec_xmin += inner
    sec_xmax -= inner
    if sec_xmax <= sec_xmin:
        mid = 0.5 * (sec_xmin + sec_xmax)
        sec_xmin = mid
        sec_xmax = mid
    section_width = max(1e-6, sec_xmax - sec_xmin)
    n = max(1, int(lane_count))
    idx = max(0, min(n - 1, int(lane_index)))
    sep = max(0.0, float(separation))
    row_margin = min(max(max(24.0, 1.10 * sep, 0.55 * bend_radius), 0.0), 0.18 * depth)
    y_top = ymax - row_margin
    y_bottom = ymin + row_margin
    if y_bottom >= y_top:
        y_mid = 0.5 * (ymin + ymax)
        y_top = y_mid
        y_bottom = y_mid
    if n <= 1 or sec_xmax <= sec_xmin:
        x = 0.5 * (sec_xmin + sec_xmax)
        y = y_top
        return x, y
    nrows = max(1, min(int(board_rows or 2), n))
    ncols = max(1, int((int(n) + int(nrows) - 1) // int(nrows)))
    col = int(idx // nrows)
    row = int(idx % nrows)
    block_width = max(1e-6, sec_xmax - sec_xmin)
    if ncols <= 1:
        stagger = min(block_width, max(24.0, 0.90 * sep, 0.90 * bend_radius, 0.45 * block_width))
        row_center = float(row) - (0.5 * float(max(1, nrows - 1)))
        x = (0.5 * (sec_xmin + sec_xmax)) + (row_center * stagger)
    else:
        pitch = max(1e-6, (sec_xmax - sec_xmin) / float(ncols - 1))
        x_base = sec_xmin + ((sec_xmax - sec_xmin) * (float(col) / float(ncols - 1)))
        stagger = min(0.70 * pitch, max(20.0, 0.65 * sep, 0.65 * bend_radius))
        row_center = float(row) - (0.5 * float(max(1, nrows - 1)))
        x = x_base + (row_center * stagger)
    x = max(sec_xmin, min(sec_xmax, x))
    if nrows <= 1:
        y = 0.5 * (y_top + y_bottom)
    else:
        y = y_top - ((y_top - y_bottom) * (float(row) / float(nrows - 1)))
    return x, y


def _guide_section_order(backend, board_obj, guide_objs, cfg):
    if board_obj is None:
        return []
    manual_enabled = bool((cfg or {}).get("manual_guide_order_enabled", False))
    manual_order = [str(sec or "").strip() for sec in list((cfg or {}).get("manual_guide_order", []) or []) if str(sec or "").strip()]
    available = []
    seen = set()
    for obj in list(guide_objs or []):
        key = str(getattr(obj, "Name", "") or "").strip()
        if key and key not in seen:
            available.append(obj)
            seen.add(key)
    if manual_enabled:
        ordered = []
        used = set()
        for key in manual_order:
            if key in seen and key not in used:
                ordered.append(key)
                used.add(key)
        for obj in available:
            key = str(getattr(obj, "Name", "") or "").strip()
            if key and key not in used:
                ordered.append(key)
                used.add(key)
        return ordered

    scored = []
    for obj in available:
        pts = list(backend._polyline_points_from_object(obj) or [])
        if not pts:
            continue
        xs = []
        for pt in pts:
            local_x, _local_y = _board_local_xy(backend, board_obj, pt)
            xs.append(float(local_x))
        avg_x = sum(xs) / max(1, len(xs))
        key = str(getattr(obj, "Name", "") or "").strip()
        scored.append((float(avg_x), key))
    scored.sort(key=lambda it: (float(it[0]), str(it[1])))
    return [key for _x, key in scored]


def _board_table_visual_orientation(_backend, _board_obj):
    # The table follows global XY, not the local rotation of the board.
    return True, True


def _apply_manual_board_slot_map(backend, jobs, board_obj, guide_objs, lane_map, lane_count, lane_meta, cfg):
    if not isinstance(lane_meta, dict) or not lane_meta or board_obj is None:
        return lane_map, lane_count, lane_meta

    raw_slot_map = dict((cfg or {}).get("manual_board_slot_map", {}) or {})
    if not raw_slot_map:
        return lane_map, lane_count, lane_meta

    job_map = {
        str(job.get("job_key", "")).strip(): job
        for job in list(jobs or [])
        if str(job.get("job_key", "")).strip()
    }
    if not job_map:
        return lane_map, lane_count, lane_meta

    cols_cfg = max(0, int((cfg or {}).get("board_slot_columns", 0) or 0))
    rows_cfg = max(1, int((cfg or {}).get("board_slot_rows", 2) or 2))
    parsed = []
    used_cells = set()
    for raw_job_key, raw_slot in list(raw_slot_map.items()):
        job_key = str(raw_job_key or "").strip()
        if not job_key or job_key not in job_map:
            continue
        meta = dict(lane_meta.get(job_key, {}) or {})
        face = str(meta.get("face", "") or "").strip()
        if face not in ("Top", "Bottom"):
            continue
        row = None
        col = None
        if isinstance(raw_slot, dict):
            row = raw_slot.get("row", None)
            col = raw_slot.get("col", None)
        elif isinstance(raw_slot, (list, tuple)) and len(raw_slot) >= 2:
            row = raw_slot[0]
            col = raw_slot[1]
        try:
            row = int(row)
            col = int(col)
        except Exception:
            continue
        if row < 0 or row >= rows_cfg or col < 0:
            continue
        cell_key = (face, row, col)
        if cell_key in used_cells:
            _log(
                "Celda manual repetida ignorada | face={} | row={} | col={} | circuito={}".format(
                    face,
                    row,
                    col,
                    str(job_map.get(job_key, {}).get("circuit_id", "") or job_key),
                )
            )
            continue
        used_cells.add(cell_key)
        parsed.append((face, job_key, row, col))

    if not parsed:
        return lane_map, lane_count, lane_meta

    max_col = max(int(col) for _face, _job_key, _row, col in parsed)
    cols = max(1, cols_cfg, max_col + 1)
    col_left_to_right, row_top_to_bottom = _board_table_visual_orientation(backend, board_obj)
    _log(
        "Orientacion tabla tablero | izquierda_a_derecha={} | arriba_abajo={}".format(
            "SI" if col_left_to_right else "NO",
            "SI" if row_top_to_bottom else "NO",
        )
    )

    for face in ("Top", "Bottom"):
        face_job_keys = [
            str(job_key)
            for job_key, meta in list(lane_meta.items())
            if str((meta or {}).get("face", "") or "").strip() == face
        ]
        if not face_job_keys:
            continue

        mapped = [
            (int(col), int(row), str(job_key))
            for cur_face, job_key, row, col in parsed
            if cur_face == face and str(job_key) in face_job_keys
        ]
        if not mapped:
            continue

        mapped.sort(key=lambda item: (int(item[0]), int(item[1]), str(job_map.get(item[2], {}).get("circuit_id", "") or item[2])))
        mapped_keys = []
        for col, row, job_key in mapped:
            meta = dict(lane_meta.get(job_key, {}) or {})
            actual_col = int(col)
            actual_row = int(row)
            if not col_left_to_right:
                actual_col = (cols - 1) - actual_col
            if not row_top_to_bottom:
                actual_row = (rows_cfg - 1) - actual_row
            meta["section_index"] = int((cols - 1) - int(actual_col))
            meta["section_count"] = int(cols)
            meta["section_lane_index"] = int(actual_row)
            meta["section_lane_count"] = int(rows_cfg)
            meta["manual_board_slot"] = True
            meta["manual_board_col"] = int(actual_col)
            meta["manual_board_row"] = int(actual_row)
            meta["manual_board_cols"] = int(cols)
            meta["manual_board_rows"] = int(rows_cfg)
            lane_meta[job_key] = meta
            mapped_keys.append(job_key)
            _log(
                "Slot manual tablero aplicado | circuito={} | face={} | col_ui={} | row_ui={} | col_real={} | row_real={} | sec={} | lane={}".format(
                    str(job_map.get(job_key, {}).get("circuit_id", "") or job_key),
                    face,
                    int(col),
                    int(row),
                    int(actual_col),
                    int(actual_row),
                    int(meta["section_index"]),
                    int(meta["section_lane_index"]),
                )
            )

        remaining = [job_key for job_key in face_job_keys if job_key not in mapped_keys]
        remaining.sort(
            key=lambda job_key: (
                int(lane_meta.get(job_key, {}).get("face_index", 10 ** 9)),
                str(job_map.get(job_key, {}).get("circuit_id", "") or job_key),
            )
        )
        face_order = mapped_keys + remaining
        face_count = max(1, len(face_order))
        for face_idx, job_key in enumerate(face_order):
            meta = dict(lane_meta.get(job_key, {}) or {})
            meta["face_index"] = int(face_idx)
            meta["face_count"] = int(face_count)
            meta["route_index"] = int(face_idx)
            meta["route_count"] = int(face_count)
            meta["plan_order"] = int(face_idx)
            lane_meta[job_key] = meta
            lane_map[job_key] = int(face_idx)
        lane_count = max(int(lane_count or 0), int(face_count))
        _log(
            "Tabla tablero aplicada | face={} | columnas={} | orden={}".format(
                face,
                int(cols),
                " -> ".join(
                    "{}[c{},r{}]".format(
                        str(job_map.get(job_key, {}).get("circuit_id", "") or job_key),
                        int(next((col for col, row, cur_key in mapped if cur_key == job_key), -1)),
                        int(next((row for col, row, cur_key in mapped if cur_key == job_key), -1)),
                    )
                    for job_key in face_order
                ),
            )
        )
    return lane_map, lane_count, lane_meta


def _retune_top_bottom_lane_meta(backend, jobs, board_obj, guide_objs, lane_map, lane_count, lane_meta, cfg):
    if not isinstance(lane_meta, dict) or not lane_meta or board_obj is None:
        return lane_map, lane_count, lane_meta

    bend_cfg = float((cfg or {}).get("bend_radius", 100.0) or 100.0)
    rows_cfg = max(1, int((cfg or {}).get("board_slot_rows", 2) or 2))
    sep_cfg = float((cfg or {}).get("separation", 50.0) or 50.0)
    job_map = {str(job.get("job_key", "")).strip(): job for job in list(jobs or [])}
    guide_points_by_key = {}
    for obj in list(guide_objs or []):
        key = str(getattr(obj, "Name", "") or "").strip()
        if not key:
            continue
        pts = list(backend._polyline_points_from_object(obj) or [])
        if len(pts) >= 2:
            guide_points_by_key[key] = pts
    grouped = {}
    for job_key, meta in list(lane_meta.items()):
        face = str(meta.get("face", "") or "").strip()
        if face not in ("Top", "Bottom"):
            continue
        section_index = int(meta.get("section_index", 0))
        section_key = str(meta.get("section_key", "") or "").strip()
        job = job_map.get(str(job_key).strip())
        if job is None:
            continue
        src_obj = backend._feeder_source_from_plan(job.get("plan"))
        if src_obj is None:
            continue
        src_pt = backend._anchor_point(src_obj)
        local_x, local_y = _board_local_xy(backend, board_obj, src_pt)
        proj_x = None
        proj_y = None
        proj_s = None
        guide_pts = list(guide_points_by_key.get(section_key, []) or [])
        if len(guide_pts) >= 2:
            try:
                proj = backend._project_point_to_polyline_xy(src_pt, guide_pts)
            except Exception:
                proj = None
            if proj:
                p = proj.get("point")
                if p is not None:
                    proj_x = float(getattr(p, "x", local_x))
                    proj_y = float(getattr(p, "y", local_y))
                try:
                    proj_s = float(proj.get("s", 0.0))
                except Exception:
                    proj_s = None
        grouped.setdefault(face, {}).setdefault((section_index, section_key), []).append({
            "job_key": str(job_key).strip(),
            "local_x": float(local_x),
            "local_y": float(local_y),
            "guide_proj_x": proj_x,
            "guide_proj_y": proj_y,
            "guide_proj_s": proj_s,
            "label": str(job.get("circuit_id", "") or ""),
        })

    if not grouped:
        return lane_map, lane_count, lane_meta

    manual_section_order = bool((cfg or {}).get("manual_guide_order_enabled", False))
    manual_section_circuit_order = bool((cfg or {}).get("manual_section_circuit_order_enabled", False))
    manual_section_circuit_map = dict((cfg or {}).get("manual_section_circuit_order_map", {}) or {})
    global_section_order = _guide_section_order(backend, board_obj, guide_objs, cfg)
    global_section_rank = {str(key or "").strip(): idx for idx, key in enumerate(global_section_order) if str(key or "").strip()}
    for face, section_map in grouped.items():
        expected_x_by_job = {}
        straight_priority_by_job = set()
        if manual_section_order:
            ordered_sections = [
                key for key in sorted(
                    section_map.keys(),
                    key=lambda pair: (
                        int(global_section_rank.get(str(pair[1] or "").strip(), 10 ** 8)),
                        str(pair[1]),
                    ),
                )
            ]
        else:
            ordered_sections = [
                key for key in sorted(
                    section_map.keys(),
                key=lambda pair: (
                        (
                            sum(
                                float(
                                    it.get("guide_proj_x")
                                    if it.get("guide_proj_x") is not None
                                    else it.get("local_x", 0.0)
                                )
                                for it in list(section_map.get(pair, []) or [])
                            )
                            / max(1, len(list(section_map.get(pair, []) or [])))
                        ),
                        str(pair[1]),
                    ),
                )
            ]
        face_order = []
        auto_used = any((str(pair[1] or "").strip() == "AUTO") for pair in ordered_sections)
        section_slot_sizes = {}
        section_total_slots = 0
        for pair in ordered_sections:
            items = list(section_map.get(pair, []) or [])
            span = max(1, len(items))
            section_slot_sizes[pair] = int(span)
            section_total_slots += int(span)
        section_total_slots = max(1, section_total_slots)
        section_slot_start = 0
        for new_sec_idx, (sec_idx, sec_key) in enumerate(ordered_sections):
            items = list(section_map.get((sec_idx, sec_key), []) or [])
            sec_key_txt = str(sec_key or "").strip()
            axis = _offset_axis_for_guide(sec_key_txt, guide_objs)
            flow = _guide_flow_vector_for_section(sec_key_txt, guide_objs, board_obj=board_obj)

            def _expected_guide_x(item):
                base_x = item.get("guide_proj_x")
                if base_x is None:
                    base_x = item.get("local_x", 0.0)
                job_key_txt = str(item.get("job_key", "")).strip()
                meta0 = dict(lane_meta.get(job_key_txt, {}) or {})
                guide_lane_idx0 = max(0, int(meta0.get("guide_lane_index", 0)))
                guide_lane_count0 = max(1, int(meta0.get("guide_lane_count", max(1, len(items)))))
                eff_idx = int(guide_lane_idx0)
                if axis == "Vertical" and float(getattr(flow, "y", 0.0)) > 0.0:
                    eff_idx = max(0, int(guide_lane_count0) - 1 - int(guide_lane_idx0))
                try:
                    vec = backend._lane_offset_vector(eff_idx, guide_lane_count0, sep_cfg, axis)
                except Exception:
                    vec = None
                vx = float(getattr(vec, "x", 0.0)) if vec is not None else 0.0
                if axis == "Vertical" and float(getattr(flow, "x", 0.0)) < 0.0:
                    vx = -vx
                elif axis == "Horizontal" and float(getattr(flow, "y", 0.0)) < 0.0:
                    vx = -vx
                return float(base_x) + float(vx)

            items = [dict(it, expected_guide_x=_expected_guide_x(it)) for it in items]
            manual_rank = {
                str(job_key).strip(): idx
                for idx, job_key in enumerate(list(manual_section_circuit_map.get(sec_key_txt, []) or []))
                if str(job_key).strip()
            } if manual_section_circuit_order else {}
            items = sorted(
                items,
                key=lambda it: (
                    int(manual_rank.get(str(it.get("job_key", "")).strip(), 10 ** 8)),
                    float(it.get("expected_guide_x", 0.0)),
                    -float(it.get("local_y", 0.0)),
                    str(it.get("label", "")),
                ),
            )
            if sec_key_txt in global_section_rank:
                actual_sec_idx = int(section_slot_start)
            elif sec_key_txt == "AUTO":
                actual_sec_idx = int(section_slot_start)
            else:
                actual_sec_idx = int(section_slot_start)
            straight_priority_keys = set()
            straight_priority_items = []
            if len(items) >= 5:
                scored_items = []
                for lane_idx, it in enumerate(items):
                    preview = _preview_board_top_section_lane_point(
                        board_obj,
                        bend_cfg,
                        rows_cfg,
                        sep_cfg,
                        actual_sec_idx,
                        section_total_slots,
                        lane_idx,
                        len(items),
                    )
                    if preview is None:
                        continue
                    guide_x = it.get("expected_guide_x", 0.0)
                    dx = abs(float(preview[0]) - float(guide_x))
                    scored_items.append((float(dx), lane_idx, str(it.get("job_key", "")).strip()))
                if scored_items:
                    scored_items.sort(key=lambda it: (float(it[0]), int(it[1]), str(it[2])))
                    straight_limit = max(20.0, (0.60 * sep_cfg), (0.30 * bend_cfg))
                    straight_max = 2 if len(items) >= 8 else 1
                    chosen = [(dx, job_key) for dx, _lane_idx, job_key in scored_items if float(dx) <= float(straight_limit)]
                    if not chosen:
                        chosen = [(
                            float(scored_items[0][0]),
                            str(scored_items[0][2]).strip(),
                        )]
                    chosen = list(chosen[:straight_max])
                    straight_priority_keys = {str(job_key).strip() for _dx, job_key in chosen if str(job_key).strip()}
                    straight_priority_items = list(chosen)
            preview_points = []
            for lane_idx, _it in enumerate(items):
                preview = _preview_board_top_section_lane_point(
                    board_obj,
                    bend_cfg,
                    rows_cfg,
                    sep_cfg,
                    actual_sec_idx,
                    section_total_slots,
                    lane_idx,
                    len(items),
                )
                if preview is None:
                    preview = (0.0, 0.0)
                preview_points.append((float(preview[0]), float(preview[1])))
            if preview_points:
                try:
                    bb = getattr(getattr(board_obj, "Shape", None), "BoundBox", None)
                except Exception:
                    bb = None
                if bb is not None:
                    width = max(1e-6, float(bb.XMax) - float(bb.XMin))
                    base_margin = min(max(4.0, 0.010 * width), 0.06 * width)
                    hard_min = float(bb.XMin) + base_margin
                    hard_max = float(bb.XMax) - base_margin
                else:
                    hard_min = min(pt[0] for pt in preview_points)
                    hard_max = max(pt[0] for pt in preview_points)
                preview_xs = [float(pt[0]) for pt in preview_points]
                expected_xs = [float(it.get("expected_guide_x", 0.0)) for it in items]
                shift_x = (
                    sum(expected_xs) / max(1, len(expected_xs))
                    - sum(preview_xs) / max(1, len(preview_xs))
                )
                band_pad = max(10.0, (0.50 * sep_cfg), (0.35 * bend_cfg))
                section_min = max(float(hard_min), min(preview_xs) - band_pad)
                section_max = min(float(hard_max), max(preview_xs) + band_pad)
                target_xs = [
                    max(section_min, min(section_max, float(px + shift_x)))
                    for px in preview_xs
                ]
                for idx, it in enumerate(items):
                    if str(it.get("job_key", "")).strip() in straight_priority_keys:
                        target_xs[idx] = max(
                            section_min,
                            min(section_max, float(it.get("expected_guide_x", target_xs[idx]))),
                        )
                if len(target_xs) >= 2 and section_max > section_min:
                    raw_gap = (section_max - section_min) / float(max(1, len(target_xs) - 1))
                    min_gap = min(max(6.0, (0.25 * sep_cfg)), max(0.0, raw_gap))
                    for idx in range(1, len(target_xs)):
                        target_xs[idx] = max(float(target_xs[idx]), float(target_xs[idx - 1]) + float(min_gap))
                    overflow = float(target_xs[-1]) - float(section_max)
                    if overflow > 0.0:
                        target_xs = [float(x - overflow) for x in target_xs]
                    for idx in range(len(target_xs) - 2, -1, -1):
                        target_xs[idx] = min(float(target_xs[idx]), float(target_xs[idx + 1]) - float(min_gap))
                    underflow = float(section_min) - float(target_xs[0])
                    if underflow > 0.0:
                        target_xs = [float(x + underflow) for x in target_xs]
                preview_points = [
                    (float(target_xs[idx]), float(preview_points[idx][1]))
                    for idx in range(len(preview_points))
                ]
            for lane_idx, it in enumerate(items):
                meta = lane_meta.get(it["job_key"], {})
                meta["section_index"] = int(actual_sec_idx)
                meta["section_count"] = int(section_total_slots)
                meta["section_lane_index"] = int(lane_idx)
                meta["section_lane_count"] = int(len(items))
                meta["guide_straight_priority"] = bool(str(it["job_key"]).strip() in straight_priority_keys)
                if lane_idx < len(preview_points):
                    meta["board_entry_x"] = float(preview_points[lane_idx][0])
                    meta["board_entry_y"] = float(preview_points[lane_idx][1])
                lane_meta[it["job_key"]] = meta
                face_order.append(it["job_key"])
                expected_x_by_job[str(it["job_key"]).strip()] = float(it.get("expected_guide_x", 0.0))
                if bool(meta["guide_straight_priority"]):
                    straight_priority_by_job.add(str(it["job_key"]).strip())
            if straight_priority_items:
                chosen_labels = []
                for dx, job_key_txt in straight_priority_items:
                    chosen = next((it for it in items if str(it.get("job_key", "")).strip() == str(job_key_txt).strip()), None)
                    chosen_labels.append(
                        "{}(dx={:.1f})".format(
                            str((chosen or {}).get("label", "") or job_key_txt),
                            float(dx),
                        )
                    )
                _log(
                    "Guia recta priorizada | face={} | seccion={} | circuitos={}".format(
                        face,
                        sec_key_txt or "-",
                        " | ".join(chosen_labels),
                    )
                )
            if preview_points:
                _log(
                    "Bloque tablero alineado | face={} | seccion={} | shift={:.1f} | xmin={:.1f} | xmax={:.1f}".format(
                        face,
                        sec_key_txt or "-",
                        float(
                            (sum((pt[0] for pt in preview_points)) / max(1, len(preview_points)))
                            - (sum((pt[0] for pt in [
                                _preview_board_top_section_lane_point(
                                    board_obj,
                                    bend_cfg,
                                    rows_cfg,
                                    sep_cfg,
                                    actual_sec_idx,
                                    section_total_slots,
                                    idx,
                                    len(items),
                                ) or (0.0, 0.0)
                                for idx in range(len(items))
                            ])) / max(1, len(items)))
                        ),
                        float(min((pt[0] for pt in preview_points), default=0.0)),
                        float(max((pt[0] for pt in preview_points), default=0.0)),
                    )
                )
            section_slot_start += int(section_slot_sizes.get((sec_idx, sec_key), max(1, len(items))))
        face_count = max(1, len(face_order))
        for face_idx, job_key in enumerate(face_order):
            meta = lane_meta.get(job_key, {})
            meta["face_index"] = int(face_idx)
            meta["face_count"] = int(face_count)
            meta["route_index"] = int(face_idx)
            meta["route_count"] = int(face_count)
            meta["plan_order"] = int(face_idx)
            lane_meta[job_key] = meta
            lane_map[job_key] = int(face_idx)
        global_preview = []
        for face_idx, _job_key in enumerate(face_order):
            preview = _preview_board_top_section_lane_point(
                board_obj,
                bend_cfg,
                rows_cfg,
                sep_cfg,
                0,
                1,
                face_idx,
                face_count,
            )
            if preview is None:
                preview = (0.0, 0.0)
            global_preview.append((float(preview[0]), float(preview[1])))
        if global_preview:
            try:
                bb = getattr(getattr(board_obj, "Shape", None), "BoundBox", None)
            except Exception:
                bb = None
            if bb is not None:
                width = max(1e-6, float(bb.XMax) - float(bb.XMin))
                base_margin = min(max(8.0, 0.020 * width), 0.10 * width)
                hard_min = float(bb.XMin) + base_margin
                hard_max = float(bb.XMax) - base_margin
            else:
                hard_min = min(pt[0] for pt in global_preview)
                hard_max = max(pt[0] for pt in global_preview)
            preview_xs = [float(pt[0]) for pt in global_preview]
            expected_xs = [float(expected_x_by_job.get(str(job_key).strip(), preview_xs[idx])) for idx, job_key in enumerate(face_order)]
            anchor_idx = None
            if straight_priority_by_job:
                center_idx = 0.5 * float(max(0, face_count - 1))
                priority_indices = [
                    idx for idx, job_key in enumerate(face_order)
                    if str(job_key).strip() in straight_priority_by_job
                ]
                if priority_indices:
                    anchor_idx = min(priority_indices, key=lambda idx: abs(float(idx) - center_idx))
            if anchor_idx is None and face_count > 0:
                anchor_idx = int(round(0.5 * float(max(0, face_count - 1))))
            if anchor_idx is None:
                shift_x = 0.0
            else:
                shift_x = float(expected_xs[anchor_idx]) - float(preview_xs[anchor_idx])
            target_xs = [max(float(hard_min), min(float(hard_max), float(px + shift_x))) for px in preview_xs]
            if len(target_xs) >= 2 and hard_max > hard_min:
                raw_gap = (float(hard_max) - float(hard_min)) / float(max(1, len(target_xs) - 1))
                min_gap = min(max(8.0, (0.35 * sep_cfg)), max(0.0, raw_gap))
                if anchor_idx is not None:
                    anchor_min = float(hard_min) + (float(anchor_idx) * float(min_gap))
                    anchor_max = float(hard_max) - (float(max(0, len(target_xs) - 1 - anchor_idx)) * float(min_gap))
                    target_xs[anchor_idx] = max(
                        float(anchor_min),
                        min(float(anchor_max), float(expected_xs[anchor_idx])),
                    )
                    for idx in range(anchor_idx - 1, -1, -1):
                        low_bound = float(hard_min) + (float(idx) * float(min_gap))
                        target_xs[idx] = max(
                            float(low_bound),
                            min(float(target_xs[idx]), float(target_xs[idx + 1]) - float(min_gap)),
                        )
                    for idx in range(anchor_idx + 1, len(target_xs)):
                        high_bound = float(hard_max) - (float(max(0, len(target_xs) - 1 - idx)) * float(min_gap))
                        target_xs[idx] = min(
                            float(high_bound),
                            max(float(target_xs[idx]), float(target_xs[idx - 1]) + float(min_gap)),
                        )
                else:
                    for idx in range(1, len(target_xs)):
                        target_xs[idx] = max(float(target_xs[idx]), float(target_xs[idx - 1]) + float(min_gap))
                    overflow = float(target_xs[-1]) - float(hard_max)
                    if overflow > 0.0:
                        target_xs = [float(x - overflow) for x in target_xs]
                    for idx in range(len(target_xs) - 2, -1, -1):
                        target_xs[idx] = min(float(target_xs[idx]), float(target_xs[idx + 1]) - float(min_gap))
                    underflow = float(hard_min) - float(target_xs[0])
                    if underflow > 0.0:
                        target_xs = [float(x + underflow) for x in target_xs]
            for idx, job_key in enumerate(face_order):
                meta = dict(lane_meta.get(job_key, {}) or {})
                if idx < len(global_preview):
                    meta["board_entry_x"] = float(target_xs[idx])
                    meta["board_entry_y"] = float(global_preview[idx][1])
                if str(job_key).strip() in straight_priority_by_job:
                    meta["guide_straight_priority"] = True
                    meta["board_entry_x"] = max(
                        float(hard_min),
                        min(float(hard_max), float(expected_x_by_job.get(str(job_key).strip(), target_xs[idx]))),
                    )
                lane_meta[job_key] = meta
            _log(
                "Array tablero global | face={} | entradas={} | xmin={:.1f} | xmax={:.1f} | shift={:.1f}".format(
                    face,
                    int(face_count),
                    float(min((x for x in target_xs), default=0.0)),
                    float(max((x for x in target_xs), default=0.0)),
                    float(shift_x),
                )
            )
        _log(
            "Orden Top/Bottom reajustado | face={} | manual_guias={} | manual_circuitos={} | orden={}".format(
                face,
                "SI" if manual_section_order else "NO",
                "SI" if manual_section_circuit_order else "NO",
                " -> ".join(
                    "{}[x={:.1f},y={:.1f}]".format(
                        str(job_map.get(job_key, {}).get("circuit_id", "") or job_key),
                        float(next((it["local_x"] for sec in section_map.values() for it in sec if it["job_key"] == job_key), 0.0)),
                        float(next((it["local_y"] for sec in section_map.values() for it in sec if it["job_key"] == job_key), 0.0)),
                    )
                    for job_key in face_order
                ),
            )
        )
    return lane_map, lane_count, lane_meta
