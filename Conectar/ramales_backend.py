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
import sys
import types
from pathlib import Path

try:
    from collections import defaultdict
except Exception:  # pragma: no cover
    defaultdict = dict  # type: ignore


_BACKEND_V1 = None
EPS = 1e-6


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


def collect_circuit_objects(circuit_group, include_apagadores):
    backend = cargar_backend_v1()
    get_component_type = backend._import_component_classifier()
    return backend._collect_circuit_objects(
        circuit_group,
        get_component_type=get_component_type,
        include_apagadores=bool(include_apagadores),
    )


def map_boxes_by_source(boxes):
    return cargar_backend_v1()._map_boxes_by_source(boxes)


def source_key(obj):
    return cargar_backend_v1()._source_key(obj)


def order_boxes_by_perimeter(boxes, board_obj=None):
    return cargar_backend_v1()._order_boxes_by_perimeter(boxes, board_obj=board_obj)


def build_plan_for_circuit(circuit_group, devices, boxes, cfg, board_obj=None):
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
    use_perimeter = _should_use_backbone_perimeter(
        backend=backend,
        src_obj=src_obj,
        dst_obj=dst_obj,
        route_by_perimeter=route_by_perimeter if str(link_kind or "").strip().lower() == "backbone" else False,
        route_rect=route_rect,
        route_z=route_z,
    ) if str(link_kind or "").strip().lower() == "backbone" else bool(route_by_perimeter)
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
