"""Wall-continuity helpers for FacilArquitecturaWB.

Nombre: room_utils.py
Proposito: reconstruir continuidad de centros de muro sobre buques conocidos y
mantener las utilidades de topologia de recintos.
Funcionamiento principal: detecta buques respaldados por puertas/ventanas,
fusiona tramos de muro colineales usando la direccion real del muro y conserva
la topologia necesaria sin ortogonalizar paredes inclinadas.
Instrucciones para futuras modificaciones: mantener la operacion no destructiva,
los identificadores internos de compatibilidad y la trazabilidad BIM; no cerrar
discontinuidades no justificadas por defecto.
Version: 0.9.1
Fecha y hora: 2026-09-01 America/Costa_Rica
"""

from __future__ import annotations

import copy
import math

import FreeCAD
import Part
import Sketcher

from .bim_utils import (
    collect_any_sketches_from_selection,
    collect_wall_sketches_from_selection,
    wall_thickness_from_sketch,
)
from .command_errors import UserFacingError
from .naming import safe_name
from .project_structure import msg, set_prop, warn
from .site_floor_utils import collect_plan_sketches


GENERATED_BY_ROOMS = "FA_CreateClosedRooms"
GENERATED_BY_CLOSED_WALLS = "FA_CloseWallSketch"
ROOM_SKETCH_PREFIX = "Sketch_Recintos_Cerrados"
CLOSED_WALL_SKETCH_PREFIX = "Sketch_Cerrado"
DEFAULT_SNAP_TOLERANCE_MM = 25.0
DEFAULT_MIN_ROOM_AREA_M2 = 0.25
DEFAULT_MAX_GAP_MM = 2500.0
DEFAULT_ALIGNMENT_TOLERANCE_MM = 25.0
DEFAULT_ANGLE_TOLERANCE_DEG = 3.0
DEFAULT_MOCHETA_MAX_LENGTH_MM = 450.0
DEFAULT_MOCHETA_PERP_TOLERANCE_DEG = 20.0
NODE_PRECISION_MM = 0.1
AXIS_TOLERANCE_DEG = 0.25
OPENING_KEYWORDS = (
    "ventana",
    "window",
    "puerta",
    "door",
    "opening",
    "buque",
    "vano",
    "abertura",
)


def collect_selected_wall_sketches(selection):
    """Return only wall centerline sketches represented by the selection."""
    return collect_wall_sketches_from_selection(list(selection or []))


def collect_selected_wall_candidates(selection, opening_sketches=None):
    """Resolve valid wall sources or safe generic Sketch conversion candidates.

    A selected native Arch/BIM wall resolves to its ``Base`` or
    ``FA_SourceSketch``. Generic Sketches are returned only when no already
    classified wall was selected, and known openings or columns are excluded.
    """
    recognized = collect_selected_wall_sketches(selection)
    if recognized:
        return recognized
    opening_keys = {_source_key(obj) for obj in list(opening_sketches or [])}
    result = []
    seen = set()
    for sketch in collect_any_sketches_from_selection(selection):
        key = _source_key(sketch)
        if key in seen or key in opening_keys or _is_explicit_column_sketch(sketch):
            continue
        seen.add(key)
        result.append(sketch)
    return result


def collect_opening_sketches(doc, selection=None):
    """Find door and window centerline sketches without treating walls as openings."""
    selected = list(selection or [])
    pending = selected + list(getattr(doc, "Objects", []) or [])
    result = []
    seen = set()
    while pending:
        obj = pending.pop(0)
        identity = str(getattr(obj, "Name", "") or "") or str(id(obj))
        if identity in seen:
            continue
        seen.add(identity)
        if _is_opening_sketch(obj):
            result.append(obj)
            continue
        for child in list(getattr(obj, "Group", []) or []):
            pending.append(child)
    return result


def resolve_opening_sketches(doc, selection=None):
    """Resolve opening scope, giving explicit selection priority over guessing.

    If the current selection contains one or more door/window sketches (directly
    or inside a selected group), only those sketches are used. If the selection
    contains no opening sketch, the document is scanned automatically.

    Returns ``(sketches, mode)`` where mode is ``"selection"`` or ``"automatic"``.
    """
    selected_openings = collect_opening_sketches(None, selection=selection)
    if selected_openings:
        return selected_openings, "selection"
    return collect_opening_sketches(doc), "automatic"


def create_closed_wall_sketches(
    doc,
    parent_group,
    wall_sketches,
    opening_sketches,
    max_gap_mm=DEFAULT_MAX_GAP_MM,
    alignment_tolerance_mm=DEFAULT_ALIGNMENT_TOLERANCE_MM,
    angle_tolerance_deg=DEFAULT_ANGLE_TOLERANCE_DEG,
    close_unmarked_gaps=False,
    close_mocheta_gaps=True,
    opening_mode="automatic",
    replace_previous=True,
):
    """Copy wall sketches and reconstruct continuity only over justified openings."""
    walls = _unique_sources(wall_sketches)
    if not walls:
        raise UserFacingError("Seleccione al menos un sketch de centros de paredes.")
    openings = [
        sketch
        for sketch in _unique_sources(opening_sketches)
        if sketch not in walls and _is_opening_sketch(sketch)
    ]
    opening_mode = (
        "selection"
        if str(opening_mode or "").strip().lower() == "selection"
        else "automatic"
    )

    if replace_previous:
        removed = remove_previous_closed_wall_sketches(doc, walls)
        if removed:
            msg("Sketches cerrados anteriores reemplazados: %d" % removed)

    created = []
    total_bridges = 0
    total_reduction = 0
    total_mocheta = 0
    total_matched_openings = 0
    total_ambiguous_openings = 0
    total_rejected_openings = 0
    used_openings = set()
    for source in walls:
        records = _geometry_records_from_sketch(source)
        line_records = [record for record in records if record["kind"] == "line"]
        if not line_records:
            warn("Sketch omitido porque no contiene lineas: %s" % _object_label(source))
            continue

        opening_records = _opening_segments_in_target(openings, source)
        reconstructed, bridges, diagnostics = bridge_wall_gaps(
            [record["segment"] for record in line_records],
            [record["segment"] for record in opening_records],
            max_gap_mm=float(max_gap_mm),
            alignment_tolerance_mm=float(alignment_tolerance_mm),
            angle_tolerance_deg=float(angle_tolerance_deg),
            allow_unmarked=bool(close_unmarked_gaps),
            allow_mocheta_fallback=bool(close_mocheta_gaps),
            wall_thickness_mm=float(wall_thickness_from_sketch(source) or 0.0),
            opening_mode=opening_mode,
            opening_metadata=opening_records,
            return_records=True,
            return_diagnostics=True,
        )
        for bridge in bridges:
            opening_indices = bridge.get("opening_indices")
            if opening_indices is None:
                opening_index = bridge.get("opening_index")
                opening_indices = () if opening_index is None else (opening_index,)
            for opening_index in opening_indices:
                if 0 <= opening_index < len(opening_records):
                    used_openings.add(opening_records[opening_index]["source"])

        sketch, constraint_count = _create_wall_sketch_copy(
            doc,
            parent_group,
            source,
            records,
            reconstructed,
            bridges,
            opening_records,
            opening_candidates=openings,
            opening_mode=opening_mode,
            mocheta_fallback_enabled=bool(close_mocheta_gaps),
            max_gap_mm=float(max_gap_mm),
            alignment_tolerance_mm=float(alignment_tolerance_mm),
            angle_tolerance_deg=float(angle_tolerance_deg),
            diagnostics=diagnostics,
        )
        created.append(sketch)
        total_bridges += len(bridges)
        mocheta_count = sum(1 for bridge in bridges if bridge.get("evidence") == "mocheta")
        total_mocheta += mocheta_count
        reduction = max(0, len(line_records) - len(reconstructed))
        total_reduction += reduction
        total_matched_openings += diagnostics["matched_openings"]
        total_ambiguous_openings += diagnostics["ambiguous_openings"]
        total_rejected_openings += diagnostics["rejected_openings"]
        msg(
            "Sketch de pared copiado: %s | lineas=%d->%d | buques_cerrados=%d | "
            "mochetas=%d | reduccion=%d | aberturas=%d usadas, %d ambiguas, "
            "%d sin cierre | restricciones=%d"
            % (
                sketch.Label,
                len(line_records),
                len(reconstructed),
                len(bridges),
                mocheta_count,
                reduction,
                diagnostics["matched_openings"],
                diagnostics["ambiguous_openings"],
                diagnostics["rejected_openings"],
                constraint_count,
            )
        )

    if not created:
        raise UserFacingError("Los sketches seleccionados no contienen lineas utilizables.")

    if len(created) > 1:
        set_prop(
            created[0],
            "App::PropertyLinkList",
            "FA_RelatedCenterlineSketches",
            "FacilArquitectura",
            "Sketches cerrados de otros espesores creados en la misma operacion",
            created[1:],
        )
    doc.recompute()
    return created, {
        "source_count": len(walls),
        "opening_sketch_count": len(openings),
        "opening_candidate_count": len(openings),
        "opening_mode": opening_mode,
        "closed_gap_count": total_bridges,
        "mocheta_gap_count": total_mocheta,
        "segment_reduction_count": total_reduction,
        "used_opening_sketch_count": len(used_openings),
        "matched_opening_count": total_matched_openings,
        "ambiguous_opening_count": total_ambiguous_openings,
        "rejected_opening_count": total_rejected_openings,
    }


def bridge_wall_gaps(
    wall_segments,
    opening_segments,
    max_gap_mm=DEFAULT_MAX_GAP_MM,
    alignment_tolerance_mm=DEFAULT_ALIGNMENT_TOLERANCE_MM,
    angle_tolerance_deg=DEFAULT_ANGLE_TOLERANCE_DEG,
    allow_unmarked=False,
    allow_mocheta_fallback=True,
    wall_thickness_mm=0.0,
    opening_mode="automatic",
    opening_metadata=None,
    return_records=False,
    return_diagnostics=False,
):
    """Reconstruct wall continuity over justified openings.

    Priority 1 is explicit door/window evidence. If an opening is missing from
    those sketches, a second conservative pass may close only a collinear gap
    whose two ends show short, approximately perpendicular wall returns
    (mochetas). A short gap by itself is never enough evidence.

    ``opening_mode="selection"`` means the user explicitly selected the
    door/window sketches. In that mode those sketches are authoritative local
    evidence: their geometry only needs to identify the physical gap locally;
    it is not required to mimic the wall axis. Automatic mode remains more
    conservative.

    ``allow_unmarked`` is retained only for API compatibility; it no longer
    enables a generic close-by-distance fallback.
    """
    records = [
        {
            "segment": tuple(float(value) for value in segment),
            "source_indices": {index},
        }
        for index, segment in enumerate(wall_segments)
    ]
    openings = [tuple(float(value) for value in segment) for segment in opening_segments]
    bridges = []
    explicit_openings = str(opening_mode or "automatic").strip().lower() == "selection"

    metadata = _normalized_opening_metadata(openings, opening_metadata)
    regions = _opening_regions(
        openings,
        metadata,
        alignment_tolerance_mm=float(alignment_tolerance_mm),
        angle_tolerance_deg=float(angle_tolerance_deg),
        wall_thickness_mm=float(wall_thickness_mm or 0.0),
    )
    report = {
        "dry_run": True,
        "source_wall_sketch": "",
        "original_segment_count": len(records),
        "candidate_openings": len(openings),
        "opening_region_count": len(regions),
        "matched_openings": 0,
        "ambiguous_openings": 0,
        "rejected_openings": 0,
        "already_continuous_openings": 0,
        "closures": [],
        "rejections": [],
        "result_segment_count": len(records),
        "opening_mode": "selection" if explicit_openings else "automatic",
    }

    def pair_candidates():
        segments = [record["segment"] for record in records]
        result = []
        for first_index in range(len(records)):
            for second_index in range(first_index + 1, len(records)):
                candidate = _wall_gap_candidate(
                    records[first_index]["segment"],
                    records[second_index]["segment"],
                    first_index,
                    second_index,
                    max_gap_mm=float(max_gap_mm),
                    alignment_tolerance_mm=float(alignment_tolerance_mm),
                    angle_tolerance_deg=float(angle_tolerance_deg),
                )
                if candidate is None:
                    candidate = _wall_intersection_gap_candidate(
                        records[first_index]["segment"],
                        records[second_index]["segment"],
                        first_index,
                        second_index,
                        max_gap_mm=float(max_gap_mm),
                        alignment_tolerance_mm=float(alignment_tolerance_mm),
                        angle_tolerance_deg=float(angle_tolerance_deg),
                    )
                if candidate is None:
                    continue
                if _gap_contains_topology_node(
                    candidate,
                    segments,
                    ignored_indices=(first_index, second_index),
                    tolerance_mm=max(1.0, float(alignment_tolerance_mm)),
                ):
                    continue
                result.append(candidate)
        return result

    # The opening is examined first. This avoids discarding long legitimate
    # openings or openings that terminate at an existing corner/T before their
    # local evidence is considered.
    for region in regions:
        already_continuous = _opening_region_already_continuous(
            records,
            region,
            alignment_tolerance_mm=float(alignment_tolerance_mm),
            angle_tolerance_deg=float(angle_tolerance_deg),
            wall_thickness_mm=float(wall_thickness_mm or 0.0),
        )
        if already_continuous:
            _append_region_rejection(report, region, "ALREADY_CONTINUOUS", 0)
            continue

        ranked = _opening_directed_wall_candidates(
            records,
            region,
            max_gap_mm=float(max_gap_mm),
            alignment_tolerance_mm=float(alignment_tolerance_mm),
            angle_tolerance_deg=float(angle_tolerance_deg),
            wall_thickness_mm=float(wall_thickness_mm or 0.0),
        )
        if not ranked:
            # Compatibility path for perpendicular/oblique legacy opening
            # geometry. The current pair engine remains the source of wall
            # direction and topology; only the region is matched to it.
            for candidate in pair_candidates():
                score = (
                    _selected_opening_match_score(
                        candidate,
                        region["segment"],
                        alignment_tolerance_mm=float(alignment_tolerance_mm),
                        wall_thickness_mm=float(wall_thickness_mm or 0.0),
                    )
                    if explicit_openings
                    else _opening_match_score(
                        candidate,
                        region["segment"],
                        alignment_tolerance_mm=float(alignment_tolerance_mm),
                        angle_tolerance_deg=float(angle_tolerance_deg),
                    )
                )
                if score is not None:
                    current = dict(candidate)
                    current["score"] = float(score)
                    current["match_method"] = "legacy_local_region"
                    ranked.append(current)

        ranked = _dedupe_physical_candidates(ranked, float(alignment_tolerance_mm))
        ranked.sort(
            key=lambda item: (
                float(item.get("score", 1e99)),
                float(item.get("gap_length", 0.0)),
                str(item.get("mode", "")),
            )
        )
        if not ranked:
            _append_region_rejection(report, region, "NO_SAFE_CANDIDATE", 0)
            continue
        if _candidate_choice_is_ambiguous(
            ranked,
            alignment_tolerance_mm=float(alignment_tolerance_mm),
            wall_thickness_mm=float(wall_thickness_mm or 0.0),
        ):
            _append_region_rejection(report, region, "AMBIGUOUS", len(ranked))
            continue

        candidate = dict(ranked[0])
        candidate["evidence"] = "opening"
        candidate["opening_mode"] = "selection" if explicit_openings else "automatic"
        candidate["opening_indices"] = tuple(region["opening_indices"])
        candidate["opening_index"] = candidate["opening_indices"][0]
        candidate["opening_refs"] = tuple(
            _opening_reference(metadata[index]) for index in candidate["opening_indices"]
        )
        _capture_candidate_source_indices(records, candidate)
        _apply_wall_candidate(records, candidate)
        bridges.append(candidate)
        _append_region_closure(report, region, candidate, len(ranked))

    # Missing door/window fallback: only collinear gaps with a clear pair of
    # mochetas are allowed. It runs even when other openings were successfully
    # found, because the imported door/window sketch can be incomplete.
    if allow_mocheta_fallback:
        while True:
            segments = [record["segment"] for record in records]
            candidates = []
            for first_index in range(len(records)):
                for second_index in range(first_index + 1, len(records)):
                    candidate = _wall_gap_candidate(
                        records[first_index]["segment"],
                        records[second_index]["segment"],
                        first_index,
                        second_index,
                        max_gap_mm=float(max_gap_mm),
                        alignment_tolerance_mm=float(alignment_tolerance_mm),
                        angle_tolerance_deg=float(angle_tolerance_deg),
                    )
                    if candidate is None:
                        continue
                    if _gap_contains_topology_node(
                        candidate,
                        segments,
                        ignored_indices=(first_index, second_index),
                        tolerance_mm=max(1.0, float(alignment_tolerance_mm)),
                    ):
                        continue
                    mocheta_indices = _mocheta_pair_for_gap(
                        candidate,
                        segments,
                        ignored_indices=(first_index, second_index),
                        wall_thickness_mm=float(wall_thickness_mm or 0.0),
                        alignment_tolerance_mm=float(alignment_tolerance_mm),
                    )
                    if mocheta_indices is None:
                        continue
                    current = dict(candidate)
                    current["evidence"] = "mocheta"
                    current["opening_index"] = None
                    current["opening_indices"] = ()
                    current["mocheta_indices"] = tuple(mocheta_indices)
                    candidates.append(current)
            if not candidates:
                break
            candidate = min(candidates, key=lambda item: item["gap_length"])
            _capture_candidate_source_indices(records, candidate)
            _apply_wall_candidate(records, candidate)
            bridges.append(candidate)
            report["closures"].append(
                {
                    "decision": "CLOSE",
                    "opening_indices": [],
                    "opening_refs": [],
                    "wall_segment_indices": [
                        int(candidate.get("first_index", -1)),
                        int(candidate.get("second_index", -1)),
                    ],
                    "wall_source_indices": [
                        list(item) for item in candidate.get("wall_source_indices", ())
                    ],
                    "mode": str(candidate.get("mode", "")),
                    "match_method": "mocheta_pair",
                    "gap_mm": float(candidate.get("gap_length", 0.0)),
                    "score": 0.0,
                    "candidate_count": len(candidates),
                }
            )

    # Legacy argument intentionally ignored: arbitrary short discontinuities are
    # unsafe and must not be closed without opening or mocheta evidence.
    _ = bool(allow_unmarked)

    normalized = [
        {
            "segment": tuple(record["segment"]),
            "source_indices": tuple(sorted(record["source_indices"])),
        }
        for record in records
    ]
    report["result_segment_count"] = len(normalized)
    matched_indices = {
        int(index)
        for closure in report["closures"]
        for index in closure.get("opening_indices", [])
    }
    report["unused_openings"] = [
        _opening_reference(item)
        for index, item in enumerate(metadata)
        if index not in matched_indices
    ]
    result = normalized if return_records else [record["segment"] for record in normalized]
    if return_diagnostics:
        return result, bridges, report
    return result, bridges


def diagnose_wall_gap_closures(
    wall_segments,
    opening_segments,
    max_gap_mm=DEFAULT_MAX_GAP_MM,
    alignment_tolerance_mm=DEFAULT_ALIGNMENT_TOLERANCE_MM,
    angle_tolerance_deg=DEFAULT_ANGLE_TOLERANCE_DEG,
    allow_mocheta_fallback=False,
    wall_thickness_mm=0.0,
    opening_mode="automatic",
    opening_metadata=None,
):
    """Return a JSON-compatible, read-only closure plan."""
    _result, _bridges, report = bridge_wall_gaps(
        wall_segments,
        opening_segments,
        max_gap_mm=max_gap_mm,
        alignment_tolerance_mm=alignment_tolerance_mm,
        angle_tolerance_deg=angle_tolerance_deg,
        allow_unmarked=False,
        allow_mocheta_fallback=allow_mocheta_fallback,
        wall_thickness_mm=wall_thickness_mm,
        opening_mode=opening_mode,
        opening_metadata=opening_metadata,
        return_records=False,
        return_diagnostics=True,
    )
    return report


def diagnose_closed_wall_sketches(
    wall_sketches,
    opening_sketches,
    max_gap_mm=DEFAULT_MAX_GAP_MM,
    alignment_tolerance_mm=DEFAULT_ALIGNMENT_TOLERANCE_MM,
    angle_tolerance_deg=DEFAULT_ANGLE_TOLERANCE_DEG,
    close_mocheta_gaps=False,
    opening_mode="automatic",
):
    """Inspect real Sketch geometry without creating or changing document objects."""
    reports = []
    openings = [obj for obj in _unique_sources(opening_sketches) if _is_opening_sketch(obj)]
    for source in _unique_sources(wall_sketches):
        wall_records = [
            record
            for record in _geometry_records_from_sketch(source)
            if record["kind"] == "line" and not record.get("construction")
        ]
        opening_records = _opening_segments_in_target(openings, source)
        report = diagnose_wall_gap_closures(
            [record["segment"] for record in wall_records],
            [record["segment"] for record in opening_records],
            max_gap_mm=max_gap_mm,
            alignment_tolerance_mm=alignment_tolerance_mm,
            angle_tolerance_deg=angle_tolerance_deg,
            allow_mocheta_fallback=close_mocheta_gaps,
            wall_thickness_mm=float(wall_thickness_from_sketch(source) or 0.0),
            opening_mode=opening_mode,
            opening_metadata=opening_records,
        )
        report["source_wall_sketch"] = str(getattr(source, "Name", "") or "")
        report["source_wall_label"] = _object_label(source)
        reports.append(report)
    return {"dry_run": True, "wall_count": len(reports), "walls": reports}


def _normalized_opening_metadata(openings, opening_metadata):
    source = list(opening_metadata or [])
    result = []
    for index in range(len(openings)):
        raw = source[index] if index < len(source) and isinstance(source[index], dict) else {}
        source_object = raw.get("source")
        source_name = str(
            raw.get("source_sketch")
            or getattr(source_object, "Name", "")
            or ""
        )
        source_label = str(
            raw.get("source_label")
            or getattr(source_object, "Label", "")
            or source_name
        )
        kind = str(
            raw.get("kind")
            or getattr(source_object, "FA_CenterlineKind", "")
            or ""
        )
        geometry_index = raw.get("geometry_index", index)
        try:
            geometry_index = int(geometry_index)
        except Exception:
            geometry_index = index
        result.append(
            {
                "opening_index": index,
                "source_sketch": source_name,
                "source_label": source_label,
                "geometry_index": geometry_index,
                "kind": kind,
            }
        )
    return result


def _opening_reference(metadata):
    return {
        "opening_index": int(metadata.get("opening_index", -1)),
        "source_sketch": str(metadata.get("source_sketch", "") or ""),
        "source_label": str(metadata.get("source_label", "") or ""),
        "geometry_index": int(metadata.get("geometry_index", -1)),
        "kind": str(metadata.get("kind", "") or ""),
    }


def _normalized_axis(segment):
    vector = (segment[2] - segment[0], segment[3] - segment[1])
    length = math.hypot(vector[0], vector[1])
    if length <= 1e-9:
        return None
    axis = (vector[0] / length, vector[1] / length)
    if axis[0] < -1e-12 or (abs(axis[0]) <= 1e-12 and axis[1] < 0.0):
        axis = (-axis[0], -axis[1])
    return axis


def _opening_regions(
    openings,
    metadata,
    alignment_tolerance_mm,
    angle_tolerance_deg,
    wall_thickness_mm,
):
    """Group only consecutive collinear openings into one local region."""
    count = len(openings)
    if not count:
        return []
    angle_limit = math.sin(math.radians(max(5.0, float(angle_tolerance_deg))))
    line_tolerance = max(
        25.0,
        float(alignment_tolerance_mm),
        float(wall_thickness_mm or 0.0) * 0.25,
    )
    chain_gap = max(
        100.0,
        float(alignment_tolerance_mm) * 4.0,
        float(wall_thickness_mm or 0.0) * 1.5,
    )
    axes = [_normalized_axis(segment) for segment in openings]
    adjacent = {index: set() for index in range(count)}
    for first_index in range(count):
        first_axis = axes[first_index]
        if first_axis is None:
            continue
        first = openings[first_index]
        first_origin = (first[0], first[1])
        first_normal = (-first_axis[1], first_axis[0])
        first_values = sorted(
            _dot2(_subtract(point, first_origin), first_axis)
            for point in ((first[0], first[1]), (first[2], first[3]))
        )
        for second_index in range(first_index + 1, count):
            second_axis = axes[second_index]
            if second_axis is None or abs(_cross2(first_axis, second_axis)) > angle_limit:
                continue
            second = openings[second_index]
            second_points = ((second[0], second[1]), (second[2], second[3]))
            offsets = [
                abs(_dot2(_subtract(point, first_origin), first_normal))
                for point in second_points
            ]
            if max(offsets) > line_tolerance:
                continue
            second_values = sorted(
                _dot2(_subtract(point, first_origin), first_axis)
                for point in second_points
            )
            if first_values[1] < second_values[0]:
                gap = second_values[0] - first_values[1]
            elif second_values[1] < first_values[0]:
                gap = first_values[0] - second_values[1]
            else:
                gap = 0.0
            if gap <= chain_gap:
                adjacent[first_index].add(second_index)
                adjacent[second_index].add(first_index)

    regions = []
    pending = set(range(count))
    while pending:
        seed = min(pending)
        component = []
        stack = [seed]
        pending.remove(seed)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbour in sorted(adjacent[current]):
                if neighbour in pending:
                    pending.remove(neighbour)
                    stack.append(neighbour)
        authority_index = max(
            component,
            key=lambda index: _distance(
                (openings[index][0], openings[index][1]),
                (openings[index][2], openings[index][3]),
            ),
        )
        axis = axes[authority_index]
        authority = openings[authority_index]
        origin = (authority[0], authority[1])
        projections = []
        for index in component:
            segment = openings[index]
            projections.extend(
                _dot2(_subtract(point, origin), axis)
                for point in ((segment[0], segment[1]), (segment[2], segment[3]))
            )
        start = min(projections)
        end = max(projections)
        start_point = (origin[0] + axis[0] * start, origin[1] + axis[1] * start)
        end_point = (origin[0] + axis[0] * end, origin[1] + axis[1] * end)
        indices = tuple(sorted(component))
        references = tuple(_opening_reference(metadata[index]) for index in indices)
        regions.append(
            {
                "opening_indices": indices,
                "opening_refs": references,
                "axis": axis,
                "origin": start_point,
                "span": end - start,
                "segment": (start_point[0], start_point[1], end_point[0], end_point[1]),
            }
        )
    regions.sort(key=lambda item: item["opening_indices"])
    return regions


def _parallel_support_records(
    records,
    region,
    alignment_tolerance_mm,
    angle_tolerance_deg,
    wall_thickness_mm,
):
    angle_limit = math.sin(math.radians(max(5.0, float(angle_tolerance_deg))))
    line_tolerance = max(
        25.0,
        float(alignment_tolerance_mm),
        float(wall_thickness_mm or 0.0) * 0.25,
    )
    axis = region["axis"]
    normal = (-axis[1], axis[0])
    origin = region["origin"]
    supports = []
    for index, record in enumerate(records):
        segment = record["segment"]
        wall_axis = _normalized_axis(segment)
        if wall_axis is None or abs(_cross2(axis, wall_axis)) > angle_limit:
            continue
        points = ((segment[0], segment[1]), (segment[2], segment[3]))
        offsets = [abs(_dot2(_subtract(point, origin), normal)) for point in points]
        if max(offsets) > line_tolerance:
            continue
        values = sorted(_dot2(_subtract(point, origin), axis) for point in points)
        supports.append(
            {
                "index": index,
                "segment": segment,
                "start": values[0],
                "end": values[1],
            }
        )
    return supports


def _opening_region_already_continuous(
    records,
    region,
    alignment_tolerance_mm,
    angle_tolerance_deg,
    wall_thickness_mm,
):
    margin = max(
        50.0,
        float(alignment_tolerance_mm) * 2.0,
        float(wall_thickness_mm or 0.0) * 0.5,
    )
    for support in _parallel_support_records(
        records,
        region,
        alignment_tolerance_mm,
        angle_tolerance_deg,
        wall_thickness_mm,
    ):
        if support["start"] <= margin and support["end"] >= region["span"] - margin:
            return True
    return False


def _score_region_on_candidate(
    candidate,
    region,
    alignment_tolerance_mm,
    wall_thickness_mm,
):
    gap_segments = _candidate_gap_segments(candidate)
    if not gap_segments:
        return None
    first = candidate.get("first_boundary")
    second = candidate.get("second_boundary")
    if first is None or second is None:
        return None
    gap_axis = _normalized_axis((first[0], first[1], second[0], second[1]))
    if gap_axis is None or abs(_cross2(gap_axis, region["axis"])) > math.sin(math.radians(7.0)):
        return None
    gap_origin = first
    gap_values = sorted(
        _dot2(_subtract(point, gap_origin), gap_axis) for point in (first, second)
    )
    opening = region["segment"]
    opening_values = sorted(
        _dot2(_subtract(point, gap_origin), gap_axis)
        for point in ((opening[0], opening[1]), (opening[2], opening[3]))
    )
    overlap = max(
        0.0,
        min(gap_values[1], opening_values[1]) - max(gap_values[0], opening_values[0]),
    )
    gap_length = max(1e-9, gap_values[1] - gap_values[0])
    uncovered = max(0.0, gap_length - overlap)
    uncovered_limit = max(
        400.0,
        gap_length * 0.45,
        float(wall_thickness_mm or 0.0) * 3.0,
    )
    if overlap / gap_length < 0.50 or uncovered > uncovered_limit:
        return None
    path_distance = min(
        _segment_to_segment_distance(
            opening,
            gap,
            tolerance_mm=max(1.0, float(alignment_tolerance_mm)),
        )
        for gap in gap_segments
    )
    corridor = max(
        75.0,
        float(alignment_tolerance_mm) * 2.0,
        float(wall_thickness_mm or 0.0) * 0.5,
    )
    if path_distance > corridor:
        return None
    gap_center = (gap_values[0] + gap_values[1]) * 0.5
    opening_center = (opening_values[0] + opening_values[1]) * 0.5
    return path_distance * 2.0 + uncovered + abs(gap_center - opening_center) * 0.25


def _infinite_line_intersection(first, second):
    p = (first[0], first[1])
    r = (first[2] - first[0], first[3] - first[1])
    q = (second[0], second[1])
    s = (second[2] - second[0], second[3] - second[1])
    cross = _cross2(r, s)
    if abs(cross) <= 1e-12:
        return None
    delta = _subtract(q, p)
    first_parameter = _cross2(delta, s) / cross
    second_parameter = _cross2(delta, r) / cross
    point = (p[0] + first_parameter * r[0], p[1] + first_parameter * r[1])
    return point, first_parameter, second_parameter


def _opening_directed_wall_candidates(
    records,
    region,
    max_gap_mm,
    alignment_tolerance_mm,
    angle_tolerance_deg,
    wall_thickness_mm,
):
    segments = [record["segment"] for record in records]
    supports = _parallel_support_records(
        records,
        region,
        alignment_tolerance_mm,
        angle_tolerance_deg,
        wall_thickness_mm,
    )
    margin = max(
        150.0,
        float(alignment_tolerance_mm) * 4.0,
        float(wall_thickness_mm or 0.0),
    )
    allowed_gap = max(float(max_gap_mm), float(region["span"]) + margin * 2.0)
    merges = []
    for first_pos in range(len(supports)):
        for second_pos in range(first_pos + 1, len(supports)):
            first = supports[first_pos]
            second = supports[second_pos]
            candidate = _wall_gap_candidate(
                first["segment"],
                second["segment"],
                first["index"],
                second["index"],
                max_gap_mm=allowed_gap,
                alignment_tolerance_mm=float(alignment_tolerance_mm),
                angle_tolerance_deg=max(5.0, float(angle_tolerance_deg)),
            )
            if candidate is None:
                continue
            if _gap_contains_topology_node(
                candidate,
                segments,
                ignored_indices=(first["index"], second["index"]),
                tolerance_mm=max(1.0, float(alignment_tolerance_mm)),
            ):
                continue
            score = _score_region_on_candidate(
                candidate,
                region,
                alignment_tolerance_mm,
                wall_thickness_mm,
            )
            if score is None:
                continue
            current = dict(candidate)
            current["score"] = float(score)
            current["match_method"] = "opening_axis_pair"
            merges.append(current)
    if merges:
        return merges

    # A legitimate opening can end at an existing corner/T. In that case only
    # the collinear wall support is extended; the intersected topology wall is
    # kept untouched.
    extensions = []
    region_center = (
        (region["segment"][0] + region["segment"][2]) * 0.5,
        (region["segment"][1] + region["segment"][3]) * 0.5,
    )
    for support in supports:
        if support["end"] <= margin:
            side = "before"
            endpoint = 0 if _dot2(
                _subtract((support["segment"][0], support["segment"][1]), region["origin"]),
                region["axis"],
            ) >= _dot2(
                _subtract((support["segment"][2], support["segment"][3]), region["origin"]),
                region["axis"],
            ) else 1
        elif support["start"] >= region["span"] - margin:
            side = "after"
            endpoint = 0 if _dot2(
                _subtract((support["segment"][0], support["segment"][1]), region["origin"]),
                region["axis"],
            ) <= _dot2(
                _subtract((support["segment"][2], support["segment"][3]), region["origin"]),
                region["axis"],
            ) else 1
        else:
            continue
        support_boundary = (
            (support["segment"][0], support["segment"][1])
            if endpoint == 0
            else (support["segment"][2], support["segment"][3])
        )
        toward_region = _subtract(region_center, support_boundary)
        for boundary_index, boundary in enumerate(segments):
            if boundary_index == support["index"]:
                continue
            boundary_axis = _normalized_axis(boundary)
            support_axis = _normalized_axis(support["segment"])
            if boundary_axis is None or support_axis is None:
                continue
            if abs(_cross2(boundary_axis, support_axis)) <= math.sin(math.radians(7.0)):
                continue
            intersection = _infinite_line_intersection(support["segment"], boundary)
            if intersection is None:
                continue
            point, _support_parameter, boundary_parameter = intersection
            boundary_length = _distance((boundary[0], boundary[1]), (boundary[2], boundary[3]))
            parameter_tolerance = max(
                1e-9,
                float(alignment_tolerance_mm) / max(boundary_length, 1.0),
            )
            if not -parameter_tolerance <= boundary_parameter <= 1.0 + parameter_tolerance:
                continue
            extension_vector = _subtract(point, support_boundary)
            extension_length = math.hypot(extension_vector[0], extension_vector[1])
            if extension_length <= 1e-6 or extension_length > allowed_gap:
                continue
            if _dot2(extension_vector, toward_region) <= 0.0:
                continue
            point_projection = _dot2(_subtract(point, region["origin"]), region["axis"])
            if side == "before" and point_projection < region["span"] - margin:
                continue
            if side == "after" and point_projection > margin:
                continue
            candidate = {
                "mode": "extend_to_support",
                "first_index": support["index"],
                "second_index": boundary_index,
                "support_endpoint": endpoint,
                "first_endpoint": endpoint,
                "first_boundary": support_boundary,
                "second_boundary": point,
                "intersection": point,
                "gap_length": extension_length,
            }
            if _gap_contains_topology_node(
                candidate,
                segments,
                ignored_indices=(support["index"], boundary_index),
                tolerance_mm=max(1.0, float(alignment_tolerance_mm)),
            ):
                continue
            score = _score_region_on_candidate(
                candidate,
                region,
                alignment_tolerance_mm,
                wall_thickness_mm,
            )
            if score is None:
                continue
            candidate["score"] = float(score) + 100.0
            candidate["match_method"] = "opening_axis_to_topology_support"
            extensions.append(candidate)
    return extensions


def _candidate_physical_key(candidate, tolerance_mm):
    tolerance = max(1.0, float(tolerance_mm))
    points = []
    for gap in _candidate_gap_segments(candidate):
        pair = [
            (round(gap[0] / tolerance), round(gap[1] / tolerance)),
            (round(gap[2] / tolerance), round(gap[3] / tolerance)),
        ]
        pair.sort()
        points.append(tuple(pair))
    return tuple(sorted(points))


def _dedupe_physical_candidates(candidates, tolerance_mm):
    unique = {}
    mode_priority = {"merge": 0, "extend_to_support": 1, "intersection": 2}
    for candidate in candidates:
        key = _candidate_physical_key(candidate, tolerance_mm)
        ranking = (
            float(candidate.get("score", 1e99)),
            mode_priority.get(str(candidate.get("mode", "")), 9),
        )
        current = unique.get(key)
        if current is None or ranking < current[0]:
            unique[key] = (ranking, candidate)
    return [item[1] for item in unique.values()]


def _candidate_choice_is_ambiguous(
    ranked,
    alignment_tolerance_mm,
    wall_thickness_mm,
):
    if len(ranked) < 2:
        return False
    ambiguity = max(
        5.0,
        float(alignment_tolerance_mm) * 0.25,
        float(wall_thickness_mm or 0.0) * 0.05,
    )
    return float(ranked[1].get("score", 1e99)) <= float(ranked[0].get("score", 0.0)) + ambiguity


def _capture_candidate_source_indices(records, candidate):
    captured = []
    for key in ("first_index", "second_index"):
        index = int(candidate.get(key, -1))
        if 0 <= index < len(records):
            captured.append(tuple(sorted(records[index].get("source_indices", ()))))
        else:
            captured.append(())
    candidate["wall_source_indices"] = tuple(captured)


def _append_region_closure(report, region, candidate, candidate_count):
    count = len(region["opening_indices"])
    report["matched_openings"] += count
    report["closures"].append(
        {
            "decision": "CLOSE",
            "opening_indices": list(region["opening_indices"]),
            "opening_refs": [dict(item) for item in region["opening_refs"]],
            "wall_segment_indices": [
                int(candidate.get("first_index", -1)),
                int(candidate.get("second_index", -1)),
            ],
            "wall_source_indices": [
                list(item) for item in candidate.get("wall_source_indices", ())
            ],
            "mode": str(candidate.get("mode", "")),
            "match_method": str(candidate.get("match_method", "")),
            "gap_mm": float(candidate.get("gap_length", 0.0)),
            "score": float(candidate.get("score", 0.0)),
            "candidate_count": int(candidate_count),
        }
    )


def _append_region_rejection(report, region, reason, candidate_count):
    count = len(region["opening_indices"])
    if reason == "AMBIGUOUS":
        report["ambiguous_openings"] += count
        decision = "AMBIGUOUS"
    elif reason == "ALREADY_CONTINUOUS":
        report["already_continuous_openings"] += count
        decision = "NO_CHANGE"
    else:
        report["rejected_openings"] += count
        decision = "REJECT"
    report["rejections"].append(
        {
            "decision": decision,
            "reason": reason,
            "opening_indices": list(region["opening_indices"]),
            "opening_refs": [dict(item) for item in region["opening_refs"]],
            "candidate_count": int(candidate_count),
        }
    )

def _apply_wall_candidate(records, candidate):
    """Apply either a collinear merge or an angled endpoint extension."""
    if candidate.get("mode") == "extend_to_support":
        support_index = int(candidate["first_index"])
        point = candidate["intersection"]
        records[support_index]["segment"] = _replace_segment_endpoint(
            records[support_index]["segment"],
            candidate["support_endpoint"],
            point,
        )
        candidate["extended_segments"] = (records[support_index]["segment"],)
        return
    if candidate.get("mode") == "intersection":
        first_index = int(candidate["first_index"])
        second_index = int(candidate["second_index"])
        point = candidate["intersection"]
        records[first_index]["segment"] = _replace_segment_endpoint(
            records[first_index]["segment"],
            candidate["first_endpoint"],
            point,
        )
        records[second_index]["segment"] = _replace_segment_endpoint(
            records[second_index]["segment"],
            candidate["second_endpoint"],
            point,
        )
        candidate["extended_segments"] = (
            records[first_index]["segment"],
            records[second_index]["segment"],
        )
        return
    _merge_wall_candidate(records, candidate)


def _merge_wall_candidate(records, candidate):
    """Replace a validated collinear pair by one segment on the common axis."""
    first_index = int(candidate["first_index"])
    second_index = int(candidate["second_index"])
    first_record = records[first_index]
    second_record = records[second_index]
    merged = _merged_collinear_segment(
        first_record["segment"],
        second_record["segment"],
    )
    combined_sources = set(first_record["source_indices"]) | set(second_record["source_indices"])
    first_record["segment"] = merged
    first_record["source_indices"] = combined_sources
    candidate["merged_segment"] = merged
    candidate["merged_source_indices"] = tuple(sorted(combined_sources))
    del records[second_index]


def _merged_collinear_segment(first, second):
    """Return one span projected to the weighted common axis of two wall pieces."""
    first_points = ((first[0], first[1]), (first[2], first[3]))
    second_points = ((second[0], second[1]), (second[2], second[3]))
    first_vector = _subtract(first_points[1], first_points[0])
    second_vector = _subtract(second_points[1], second_points[0])
    first_length = math.hypot(first_vector[0], first_vector[1])
    second_length = math.hypot(second_vector[0], second_vector[1])
    if first_length <= 1e-9 or second_length <= 1e-9:
        raise ValueError("No se puede fusionar un segmento de longitud cero.")

    authority = first_vector if first_length >= second_length else second_vector
    authority_length = math.hypot(authority[0], authority[1])
    axis = (authority[0] / authority_length, authority[1] / authority_length)
    normal = (-axis[1], axis[0])

    first_offset = sum(_dot2(point, normal) for point in first_points) * 0.5
    second_offset = sum(_dot2(point, normal) for point in second_points) * 0.5
    common_offset = (
        first_offset * first_length + second_offset * second_length
    ) / (first_length + second_length)

    projections = [_dot2(point, axis) for point in first_points + second_points]
    start = min(projections)
    end = max(projections)
    return (
        axis[0] * start + normal[0] * common_offset,
        axis[1] * start + normal[1] * common_offset,
        axis[0] * end + normal[0] * common_offset,
        axis[1] * end + normal[1] * common_offset,
    )


def _gap_contains_topology_node(candidate, segments, ignored_indices=(), tolerance_mm=1.0):
    """Reject a closure when another wall crosses the missing local path."""
    ignored = set(int(index) for index in ignored_indices)
    gap_segments = _candidate_gap_segments(candidate)
    if not gap_segments:
        return False

    for gap in gap_segments:
        first = (gap[0], gap[1])
        second = (gap[2], gap[3])
        gap_length = _distance(first, second)
        if gap_length <= 1e-9:
            continue
        endpoint_margin = min(max(float(tolerance_mm), 1.0), gap_length * 0.20)
        for index, segment in enumerate(segments):
            if index in ignored:
                continue
            parameter = _segment_intersection_parameter(
                gap, segment, tolerance_mm=float(tolerance_mm)
            )
            if parameter is not None:
                distance_along = parameter * gap_length
                if endpoint_margin < distance_along < gap_length - endpoint_margin:
                    return True
            for point in ((segment[0], segment[1]), (segment[2], segment[3])):
                distance, parameter = _project_to_segment(point, gap)
                if distance <= float(tolerance_mm):
                    distance_along = parameter * gap_length
                    if endpoint_margin < distance_along < gap_length - endpoint_margin:
                        return True
    return False


def _segment_intersection_parameter(first, second, tolerance_mm=1.0):
    """Return intersection parameter on first segment, or None when they do not cross."""
    p = (first[0], first[1])
    r = (first[2] - first[0], first[3] - first[1])
    q = (second[0], second[1])
    s = (second[2] - second[0], second[3] - second[1])
    rxs = _cross2(r, s)
    qmp = _subtract(q, p)
    scale = max(
        math.hypot(r[0], r[1]),
        math.hypot(s[0], s[1]),
        1.0,
    )
    epsilon = max(1e-9, float(tolerance_mm) / scale * 1e-3)
    if abs(rxs) <= epsilon:
        return None
    t = _cross2(qmp, s) / rxs
    u = _cross2(qmp, r) / rxs
    parameter_tolerance = max(
        1e-9,
        float(tolerance_mm) / max(math.hypot(r[0], r[1]), 1.0),
    )
    parameter_u_tolerance = max(
        1e-9,
        float(tolerance_mm) / max(math.hypot(s[0], s[1]), 1.0),
    )
    if (
        -parameter_tolerance <= t <= 1.0 + parameter_tolerance
        and -parameter_u_tolerance <= u <= 1.0 + parameter_u_tolerance
    ):
        return max(0.0, min(1.0, t))
    return None


def remove_previous_closed_wall_sketches(doc, source_sketches=None):
    """Remove generated copies for the current sources and legacy room sketches."""
    source_names = {
        str(getattr(source, "Name", "") or "")
        for source in list(source_sketches or [])
        if getattr(source, "Name", None)
    }
    candidates = []
    for obj in list(getattr(doc, "Objects", []) or []):
        generated_by = str(getattr(obj, "FA_GeneratedBy", "") or "")
        if generated_by == GENERATED_BY_ROOMS:
            candidates.append(obj)
            continue
        if generated_by != GENERATED_BY_CLOSED_WALLS:
            continue
        source = getattr(obj, "FA_SourceWallSketch", None)
        source_name = str(getattr(source, "Name", "") or "")
        if not source_names or not source_name or source_name in source_names:
            candidates.append(obj)

    removed = 0
    for obj in candidates:
        try:
            name = str(getattr(obj, "Name", "") or "")
            if name and doc.getObject(name) is not None:
                doc.removeObject(name)
                removed += 1
        except Exception as exc:
            warn("No se pudo eliminar %s: %s" % (_object_label(obj), exc))
    return removed


def _create_wall_sketch_copy(
    doc,
    parent_group,
    source,
    geometry_records,
    reconstructed_records,
    bridges,
    opening_records,
    opening_candidates,
    opening_mode,
    mocheta_fallback_enabled,
    max_gap_mm,
    alignment_tolerance_mm,
    angle_tolerance_deg,
    diagnostics=None,
):
    diagnostics = dict(diagnostics or {})
    label = _unique_closed_wall_label(doc, source)
    sketch = doc.addObject("Sketcher::SketchObject", safe_name(label, CLOSED_WALL_SKETCH_PREFIX))
    sketch.Label = label
    try:
        sketch.Placement = FreeCAD.Placement(getattr(source, "Placement"))
    except Exception:
        try:
            sketch.Placement = getattr(source, "Placement")
        except Exception:
            pass
    try:
        parent_group.addObject(sketch)
    except Exception:
        pass

    source_line_records = [record for record in geometry_records if record["kind"] == "line"]
    line_indices = []
    line_segments = []
    for reconstructed in reconstructed_records:
        segment = reconstructed["segment"]
        source_indices = list(reconstructed.get("source_indices", ()))
        construction_flags = [
            bool(source_line_records[index].get("construction", False))
            for index in source_indices
            if 0 <= index < len(source_line_records)
        ]
        construction = bool(construction_flags) and all(construction_flags)
        geometry = Part.LineSegment(
            FreeCAD.Vector(segment[0], segment[1], 0.0),
            FreeCAD.Vector(segment[2], segment[3], 0.0),
        )
        try:
            geometry_index = sketch.addGeometry(geometry, construction)
        except TypeError:
            geometry_index = sketch.addGeometry(geometry)
            if construction:
                try:
                    sketch.toggleConstruction(geometry_index)
                except Exception:
                    pass
        line_indices.append(int(geometry_index))
        line_segments.append(segment)

    # Non-line geometry is preserved, but line geometry is rebuilt from the
    # simplified continuity model so opening boundaries do not survive as
    # redundant split points.
    for record in geometry_records:
        if record["kind"] == "line":
            continue
        geometry = _clone_geometry(record["geometry"])
        try:
            sketch.addGeometry(geometry, bool(record.get("construction", False)))
        except TypeError:
            geometry_index = sketch.addGeometry(geometry)
            if record.get("construction"):
                try:
                    sketch.toggleConstruction(geometry_index)
                except Exception:
                    pass

    constraint_count = _add_copy_constraints(sketch, line_indices, line_segments)
    _copy_wall_properties(source, sketch)
    opening_sources = []
    for bridge in bridges:
        opening_indices = bridge.get("opening_indices")
        if opening_indices is None:
            opening_index = bridge.get("opening_index")
            opening_indices = () if opening_index is None else (opening_index,)
        for opening_index in opening_indices:
            if not (0 <= opening_index < len(opening_records)):
                continue
            opening_source = opening_records[opening_index]["source"]
            if opening_source not in opening_sources:
                opening_sources.append(opening_source)

    set_prop(
        sketch,
        "App::PropertyString",
        "FA_GeneratedBy",
        "FacilArquitectura",
        "Comando que genero el sketch",
        GENERATED_BY_CLOSED_WALLS,
    )
    set_prop(sketch, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "centerlines")
    set_prop(
        sketch,
        "App::PropertyString",
        "FA_CenterlineKind",
        "FacilArquitectura",
        "Tipo de ejes contenido en el sketch",
        "walls",
    )
    set_prop(
        sketch,
        "App::PropertyLink",
        "FA_SourceWallSketch",
        "FacilArquitectura",
        "Sketch de paredes copiado",
        source,
    )
    set_prop(
        sketch,
        "App::PropertyString",
        "FA_OpeningSourceMode",
        "FacilArquitectura",
        "Origen de los sketches de abertura: selection o automatic",
        str(opening_mode),
    )
    set_prop(
        sketch,
        "App::PropertyLinkList",
        "FA_OpeningCandidateSketches",
        "FacilArquitectura",
        "Sketches de puertas o ventanas considerados como evidencia",
        list(opening_candidates or []),
    )
    set_prop(
        sketch,
        "App::PropertyLinkList",
        "FA_SourceOpeningSketches",
        "FacilArquitectura",
        "Sketches de puertas o ventanas que realmente justificaron buques cerrados",
        opening_sources,
    )
    set_prop(
        sketch,
        "App::PropertyBool",
        "FA_MochetaFallbackEnabled",
        "FacilArquitectura",
        "Indica si se permitio completar buques por evidencia de mochetas",
        bool(mocheta_fallback_enabled),
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_ClosedGapCount",
        "FacilArquitectura",
        "Cantidad de buques cerrados",
        len(bridges),
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_MochetaClosureCount",
        "FacilArquitectura",
        "Buques cerrados por evidencia geometrica de mochetas",
        sum(1 for bridge in bridges if bridge.get("evidence") == "mocheta"),
    )
    set_prop(
        sketch,
        "App::PropertyLength",
        "FA_MaxClosingGap",
        "FacilArquitectura",
        "Longitud maxima de buque permitida",
        float(max_gap_mm),
    )
    set_prop(
        sketch,
        "App::PropertyLength",
        "FA_AlignmentTolerance",
        "FacilArquitectura",
        "Tolerancia entre ejes colineales",
        float(alignment_tolerance_mm),
    )
    set_prop(
        sketch,
        "App::PropertyFloat",
        "FA_AngleToleranceDeg",
        "FacilArquitectura",
        "Tolerancia angular usada",
        float(angle_tolerance_deg),
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_ParametricConstraintCount",
        "FacilArquitectura",
        "Restricciones geometricas agregadas",
        constraint_count,
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_OriginalGeometryCount",
        "FacilArquitectura",
        "Cantidad de geometrias del sketch fuente",
        len(geometry_records),
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_OriginalLineCount",
        "FacilArquitectura",
        "Cantidad de lineas del sketch fuente",
        len(source_line_records),
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_ReconstructedLineCount",
        "FacilArquitectura",
        "Cantidad de lineas despues de reconstruir continuidad",
        len(reconstructed_records),
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_SegmentReductionCount",
        "FacilArquitectura",
        "Segmentos redundantes eliminados al cerrar buques",
        max(0, len(source_line_records) - len(reconstructed_records)),
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_MatchedOpeningGeometryCount",
        "FacilArquitectura",
        "Geometrias de abertura que justificaron continuidad",
        int(diagnostics.get("matched_openings", 0)),
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_AmbiguousOpeningGeometryCount",
        "FacilArquitectura",
        "Geometrias ambiguas que no se aplicaron",
        int(diagnostics.get("ambiguous_openings", 0)),
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_RejectedOpeningGeometryCount",
        "FacilArquitectura",
        "Geometrias sin candidato seguro",
        int(diagnostics.get("rejected_openings", 0)),
    )
    try:
        sketch.ViewObject.LineColor = (0.12, 0.72, 0.36)
        sketch.ViewObject.PointColor = (1.0, 0.72, 0.10)
        sketch.ViewObject.LineWidth = 3.0
    except Exception:
        pass
    return sketch, constraint_count


def _copy_wall_properties(source, target):
    text_properties = (
        "FA_System",
        "FA_SourceSelection",
        "FA_ElementType",
        "FA_ExtractionMode",
    )
    for name in text_properties:
        if hasattr(source, name):
            set_prop(
                target,
                "App::PropertyString",
                name,
                "FacilArquitectura",
                "Propiedad copiada del sketch fuente",
                str(getattr(source, name, "") or ""),
            )
    for name in ("FA_WallThickness", "FA_WallHeight"):
        value = _quantity_value(getattr(source, name, 0.0))
        if value > 0.0:
            set_prop(
                target,
                "App::PropertyLength",
                name,
                "FacilArquitectura",
                "Propiedad BIM copiada del sketch fuente",
                value,
            )
    if not hasattr(target, "FA_WallThickness"):
        thickness = wall_thickness_from_sketch(source)
        if thickness > 0.0:
            set_prop(
                target,
                "App::PropertyLength",
                "FA_WallThickness",
                "FacilArquitectura",
                "Espesor BIM copiado del sketch fuente",
                thickness,
            )
    if hasattr(source, "FA_ThicknessDetected"):
        set_prop(
            target,
            "App::PropertyBool",
            "FA_ThicknessDetected",
            "FacilArquitectura",
            "El espesor fue detectado en la geometria fuente",
            bool(getattr(source, "FA_ThicknessDetected", False)),
        )


def _geometry_records_from_sketch(sketch):
    records = []
    try:
        geometries = list(getattr(sketch, "Geometry", []) or [])
    except Exception:
        geometries = []
    for index, geometry in enumerate(geometries):
        segment = _line_segment_from_geometry(geometry)
        record = {
            "kind": "line" if segment is not None else "other",
            "construction": _is_construction_geometry(sketch, index),
        }
        if segment is not None:
            record["segment"] = segment
        else:
            record["geometry"] = geometry
        records.append(record)
    return records


def _opening_segments_in_target(opening_sketches, target_sketch):
    records = []
    for opening in opening_sketches:
        for geometry_index, record in enumerate(_geometry_records_from_sketch(opening)):
            if record["kind"] != "line":
                continue
            records.append(
                {
                    "segment": _map_segment_between_sketches(
                        record["segment"],
                        opening,
                        target_sketch,
                    ),
                    "source": opening,
                    "source_sketch": str(getattr(opening, "Name", "") or ""),
                    "source_label": _object_label(opening),
                    "geometry_index": int(geometry_index),
                    "kind": str(getattr(opening, "FA_CenterlineKind", "") or ""),
                }
            )
    return records


def _wall_gap_candidate(
    first,
    second,
    first_index,
    second_index,
    max_gap_mm,
    alignment_tolerance_mm,
    angle_tolerance_deg,
):
    first_points = ((first[0], first[1]), (first[2], first[3]))
    second_points = ((second[0], second[1]), (second[2], second[3]))
    first_vector = _subtract(first_points[1], first_points[0])
    second_vector = _subtract(second_points[1], second_points[0])
    first_length = math.hypot(first_vector[0], first_vector[1])
    second_length = math.hypot(second_vector[0], second_vector[1])
    if first_length <= 1e-9 or second_length <= 1e-9:
        return None
    axis = (first_vector[0] / first_length, first_vector[1] / first_length)
    second_axis = (second_vector[0] / second_length, second_vector[1] / second_length)
    if abs(_cross2(axis, second_axis)) > math.sin(math.radians(float(angle_tolerance_deg))):
        return None

    offsets = [
        abs(_cross2(axis, _subtract(point, first_points[0])))
        for point in second_points
    ]
    if max(offsets) > float(alignment_tolerance_mm):
        return None

    first_interval = (0.0, first_length)
    second_projection = [
        _dot2(_subtract(point, first_points[0]), axis)
        for point in second_points
    ]
    second_interval = (min(second_projection), max(second_projection))
    if first_interval[1] < second_interval[0] - 1e-9:
        gap_start = first_interval[1]
        gap_end = second_interval[0]
        first_endpoint = 1
        second_endpoint = second_projection.index(second_interval[0])
    elif second_interval[1] < first_interval[0] - 1e-9:
        gap_start = second_interval[1]
        gap_end = first_interval[0]
        first_endpoint = 0
        second_endpoint = second_projection.index(second_interval[1])
    else:
        return None

    gap_length = gap_end - gap_start
    if gap_length <= 1e-6 or gap_length > float(max_gap_mm):
        return None
    first_boundary = first_points[first_endpoint]
    second_boundary = second_points[second_endpoint]
    join_point = (
        (first_boundary[0] + second_boundary[0]) * 0.5,
        (first_boundary[1] + second_boundary[1]) * 0.5,
    )
    return {
        "mode": "merge",
        "first_index": first_index,
        "second_index": second_index,
        "first_endpoint": first_endpoint,
        "second_endpoint": second_endpoint,
        "gap_length": gap_length,
        "gap_start": gap_start,
        "gap_end": gap_end,
        "origin": first_points[0],
        "axis": axis,
        "join_point": join_point,
        "first_boundary": first_boundary,
        "second_boundary": second_boundary,
    }



def _wall_intersection_gap_candidate(
    first,
    second,
    first_index,
    second_index,
    max_gap_mm,
    alignment_tolerance_mm,
    angle_tolerance_deg,
):
    """Return a safe endpoint-extension candidate for angled wall segments.

    The infinite supporting lines must intersect outside (or exactly at) an end
    of each finite segment. Intersections through the interior of an existing
    segment are not treated as missing buques because they represent existing
    T/X topology.
    """
    p = (first[0], first[1])
    r = (first[2] - first[0], first[3] - first[1])
    q = (second[0], second[1])
    s = (second[2] - second[0], second[3] - second[1])
    first_length = math.hypot(r[0], r[1])
    second_length = math.hypot(s[0], s[1])
    if first_length <= 1e-9 or second_length <= 1e-9:
        return None

    cross = _cross2(r, s)
    sin_angle = abs(cross) / (first_length * second_length)
    parallel_limit = math.sin(math.radians(max(float(angle_tolerance_deg), 2.0)))
    if sin_angle <= parallel_limit:
        return None

    qmp = _subtract(q, p)
    t = _cross2(qmp, s) / cross
    u = _cross2(qmp, r) / cross
    intersection = (p[0] + t * r[0], p[1] + t * r[1])

    def endpoint_extension(parameter, length):
        parameter_tolerance = max(1e-9, float(alignment_tolerance_mm) / max(length, 1.0))
        if parameter < -parameter_tolerance:
            return 0, -parameter * length
        if parameter > 1.0 + parameter_tolerance:
            return 1, (parameter - 1.0) * length
        if -parameter_tolerance <= parameter <= parameter_tolerance:
            return 0, 0.0
        if 1.0 - parameter_tolerance <= parameter <= 1.0 + parameter_tolerance:
            return 1, 0.0
        return None

    first_extension = endpoint_extension(t, first_length)
    second_extension = endpoint_extension(u, second_length)
    if first_extension is None or second_extension is None:
        return None
    first_endpoint, first_extension_length = first_extension
    second_endpoint, second_extension_length = second_extension
    if first_extension_length <= 1e-6 and second_extension_length <= 1e-6:
        return None
    if (
        first_extension_length > float(max_gap_mm)
        or second_extension_length > float(max_gap_mm)
    ):
        return None

    first_boundary = (first[0], first[1]) if first_endpoint == 0 else (first[2], first[3])
    second_boundary = (second[0], second[1]) if second_endpoint == 0 else (second[2], second[3])
    boundary_gap = _distance(first_boundary, second_boundary)
    if boundary_gap <= 1e-6 or boundary_gap > float(max_gap_mm):
        return None

    return {
        "mode": "intersection",
        "first_index": first_index,
        "second_index": second_index,
        "first_endpoint": first_endpoint,
        "second_endpoint": second_endpoint,
        "first_boundary": first_boundary,
        "second_boundary": second_boundary,
        "intersection": intersection,
        "first_extension_length": first_extension_length,
        "second_extension_length": second_extension_length,
        "gap_length": boundary_gap,
        "path_length": first_extension_length + second_extension_length,
    }


def _candidate_gap_segments(candidate):
    """Return the missing local path represented by a candidate."""
    first = candidate.get("first_boundary")
    second = candidate.get("second_boundary")
    if first is None or second is None:
        return []
    if candidate.get("mode") == "extend_to_support":
        return [(first[0], first[1], second[0], second[1])]
    if candidate.get("mode") == "intersection":
        point = candidate.get("intersection")
        if point is None:
            return []
        result = []
        if _distance(first, point) > 1e-9:
            result.append((first[0], first[1], point[0], point[1]))
        if _distance(point, second) > 1e-9:
            result.append((point[0], point[1], second[0], second[1]))
        return result
    return [(first[0], first[1], second[0], second[1])]


def _segment_to_segment_distance(first, second, tolerance_mm=1.0):
    """Return minimum distance between finite 2D segments."""
    if _segment_intersection_parameter(first, second, tolerance_mm=tolerance_mm) is not None:
        return 0.0
    a0 = (first[0], first[1])
    a1 = (first[2], first[3])
    b0 = (second[0], second[1])
    b1 = (second[2], second[3])
    return min(
        _point_to_segment_distance(a0, b0, b1),
        _point_to_segment_distance(a1, b0, b1),
        _point_to_segment_distance(b0, a0, a1),
        _point_to_segment_distance(b1, a0, a1),
    )


def _mocheta_pair_for_gap(
    candidate,
    segments,
    ignored_indices=(),
    wall_thickness_mm=0.0,
    alignment_tolerance_mm=DEFAULT_ALIGNMENT_TOLERANCE_MM,
):
    """Return a conservative pair of short wall returns attached to gap ends."""
    if candidate.get("mode") != "merge" or candidate.get("axis") is None:
        return None
    ignored = {int(index) for index in ignored_indices}
    axis = candidate["axis"]
    thickness = float(wall_thickness_mm or 0.0)
    max_length = max(
        DEFAULT_MOCHETA_MAX_LENGTH_MM,
        thickness * 3.0 if thickness > 0.0 else 0.0,
    )
    min_length = max(25.0, thickness * 0.25 if thickness > 0.0 else 25.0)
    attach_tolerance = max(25.0, float(alignment_tolerance_mm) * 1.5)
    perpendicular_limit = math.sin(math.radians(DEFAULT_MOCHETA_PERP_TOLERANCE_DEG))

    def attached(boundary):
        found = []
        for index, segment in enumerate(segments):
            if index in ignored:
                continue
            points = ((segment[0], segment[1]), (segment[2], segment[3]))
            vector = _subtract(points[1], points[0])
            length = math.hypot(vector[0], vector[1])
            if length < min_length or length > max_length:
                continue
            segment_axis = (vector[0] / length, vector[1] / length)
            if abs(_dot2(axis, segment_axis)) > perpendicular_limit:
                continue
            if min(_distance(boundary, points[0]), _distance(boundary, points[1])) <= attach_tolerance:
                found.append((index, segment_axis, length))
        return found

    first = attached(candidate["first_boundary"])
    second = attached(candidate["second_boundary"])
    if not first or not second:
        return None
    parallel_limit = math.sin(math.radians(DEFAULT_MOCHETA_PERP_TOLERANCE_DEG))
    for first_item in first:
        for second_item in second:
            if abs(_cross2(first_item[1], second_item[1])) > parallel_limit:
                continue
            ratio = max(first_item[2], second_item[2]) / max(min(first_item[2], second_item[2]), 1e-9)
            if ratio > 2.5:
                continue
            return first_item[0], second_item[0]
    return None


def _selected_opening_match_score(
    candidate,
    opening,
    alignment_tolerance_mm,
    wall_thickness_mm=0.0,
):
    """Score explicit selected opening geometry as authoritative local evidence.

    The user has already decided which door/window sketches define the scope.
    Therefore this matcher does not require the opening line to be parallel to
    the wall or centered exactly on its axis. It only requires the selected
    opening geometry to be locally close to the missing wall path. The wall
    segments remain the sole authority for final direction and topology.
    """
    first = (opening[0], opening[1])
    second = (opening[2], opening[3])
    opening_length = _distance(first, second)
    if opening_length <= 1e-9:
        return None

    gap_segments = _candidate_gap_segments(candidate)
    if not gap_segments:
        return None
    opening_segment = (first[0], first[1], second[0], second[1])
    path_distance = min(
        _segment_to_segment_distance(
            opening_segment,
            gap_segment,
            tolerance_mm=max(1.0, float(alignment_tolerance_mm)),
        )
        for gap_segment in gap_segments
    )

    opening_midpoint = ((first[0] + second[0]) * 0.5, (first[1] + second[1]) * 0.5)
    midpoint_distance = min(
        _point_to_segment_distance(
            opening_midpoint,
            (gap_segment[0], gap_segment[1]),
            (gap_segment[2], gap_segment[3]),
        )
        for gap_segment in gap_segments
    )

    local_extent = max(
        float(candidate.get("gap_length", 0.0)),
        float(candidate.get("path_length", 0.0)),
        opening_length,
        1.0,
    )
    thickness = max(0.0, float(wall_thickness_mm or 0.0))
    corridor_limit = max(
        200.0,
        thickness * 2.5,
        min(1200.0, local_extent * 0.85),
    )
    midpoint_limit = max(
        300.0,
        thickness * 3.0,
        min(1600.0, local_extent * 1.25),
    )
    if path_distance > corridor_limit or midpoint_distance > midpoint_limit:
        return None

    length_penalty = abs(float(candidate.get("gap_length", 0.0)) - opening_length) * 0.05
    return path_distance + midpoint_distance * 0.35 + length_penalty


def _opening_match_score(candidate, opening, alignment_tolerance_mm, angle_tolerance_deg):
    """Score whether an opening line identifies the candidate wall gap.

    Door/window centerlines are local evidence only. They may be parallel,
    perpendicular or oblique to the wall geometry.
    """
    first = (opening[0], opening[1])
    second = (opening[2], opening[3])
    vector = _subtract(second, first)
    length = math.hypot(vector[0], vector[1])
    if length <= 1e-9:
        return None

    if candidate.get("mode") == "intersection":
        opening_segment = (first[0], first[1], second[0], second[1])
        gap_segments = _candidate_gap_segments(candidate)
        if not gap_segments:
            return None
        path_distance = min(
            _segment_to_segment_distance(
                opening_segment,
                gap_segment,
                tolerance_mm=max(1.0, float(alignment_tolerance_mm)),
            )
            for gap_segment in gap_segments
        )
        midpoint = ((first[0] + second[0]) * 0.5, (first[1] + second[1]) * 0.5)
        midpoint_distance = min(
            _point_to_segment_distance(
                midpoint,
                (gap_segment[0], gap_segment[1]),
                (gap_segment[2], gap_segment[3]),
            )
            for gap_segment in gap_segments
        )
        local_extent = max(
            float(candidate.get("gap_length", 0.0)),
            float(candidate.get("path_length", 0.0)),
            1.0,
        )
        proximity_limit = max(250.0, min(900.0, local_extent * 0.80))
        midpoint_limit = max(350.0, min(1200.0, local_extent * 1.10))
        if path_distance > proximity_limit or midpoint_distance > midpoint_limit:
            return None
        return 1200.0 + path_distance + midpoint_distance * 0.5

    axis = candidate["axis"]
    opening_axis = (vector[0] / length, vector[1] / length)
    projections = [
        _dot2(_subtract(point, candidate["origin"]), axis)
        for point in (first, second)
    ]
    opening_start, opening_end = min(projections), max(projections)
    opening_center = (opening_start + opening_end) * 0.5
    gap_center = (candidate["gap_start"] + candidate["gap_end"]) * 0.5

    opening_angle_tolerance = max(float(angle_tolerance_deg), 5.0)
    if abs(_cross2(axis, opening_axis)) <= math.sin(math.radians(opening_angle_tolerance)):
        midpoint = ((first[0] + second[0]) * 0.5, (first[1] + second[1]) * 0.5)
        offset = abs(_cross2(axis, _subtract(midpoint, candidate["origin"])))
        opening_alignment = max(10.0, float(alignment_tolerance_mm) * 2.0)
        if offset <= opening_alignment:
            overlap = max(
                0.0,
                min(candidate["gap_end"], opening_end)
                - max(candidate["gap_start"], opening_start),
            )
            minimum_overlap = min(
                candidate["gap_length"], opening_end - opening_start
            ) * 0.5
            center_limit = max(200.0, candidate["gap_length"] * 0.35)
            if (
                overlap + 1e-6 >= minimum_overlap
                and abs(opening_center - gap_center) <= center_limit
            ):
                return (
                    offset
                    + abs(candidate["gap_length"] - (opening_end - opening_start)) * 0.1
                    + abs(opening_center - gap_center) * 0.25
                )

    gap_center_point = (
        candidate["origin"][0] + axis[0] * gap_center,
        candidate["origin"][1] + axis[1] * gap_center,
    )
    spatial_distance = _point_to_segment_distance(gap_center_point, first, second)
    if opening_start <= gap_center <= opening_end:
        projection_distance = 0.0
    else:
        projection_distance = min(
            abs(gap_center - opening_start),
            abs(gap_center - opening_end),
        )

    projection_limit = max(250.0, candidate["gap_length"] * 0.55)
    proximity_limit = max(200.0, min(750.0, candidate["gap_length"] * 0.75))
    if projection_distance > projection_limit or spatial_distance > proximity_limit:
        return None
    return (
        1000.0
        + spatial_distance
        + projection_distance * 0.5
        + abs(opening_center - gap_center) * 0.15
    )


def _point_to_segment_distance(point, first, second):
    """Return the Euclidean 2D distance from point to a finite segment."""
    vector = _subtract(second, first)
    length_sq = _dot2(vector, vector)
    if length_sq <= 1e-12:
        return math.hypot(point[0] - first[0], point[1] - first[1])
    t = _dot2(_subtract(point, first), vector) / length_sq
    t = max(0.0, min(1.0, t))
    closest = (first[0] + vector[0] * t, first[1] + vector[1] * t)
    return math.hypot(point[0] - closest[0], point[1] - closest[1])


def _add_copy_constraints(sketch, geometry_indices, segments):
    constraint_count = 0
    endpoint_records = []
    axis_limit = math.sin(math.radians(AXIS_TOLERANCE_DEG))
    for geometry_index, segment in zip(geometry_indices, segments):
        dx = segment[2] - segment[0]
        dy = segment[3] - segment[1]
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            continue
        if abs(dy) / length <= axis_limit:
            constraint_count += _add_constraint(
                sketch,
                Sketcher.Constraint("Horizontal", geometry_index),
            )
        elif abs(dx) / length <= axis_limit:
            constraint_count += _add_constraint(
                sketch,
                Sketcher.Constraint("Vertical", geometry_index),
            )
        else:
            constraint_count += _add_constraint(
                sketch,
                Sketcher.Constraint("Angle", geometry_index, math.atan2(dy, dx)),
            )
        endpoint_records.extend(
            (
                (geometry_index, 1, (segment[0], segment[1])),
                (geometry_index, 2, (segment[2], segment[3])),
            )
        )

    coincident_endpoints = set()
    for group in _group_points(endpoint_records, NODE_PRECISION_MM):
        if len(group) < 2:
            continue
        anchor = group[0]
        for current in group[1:]:
            if anchor[0] == current[0]:
                continue
            constraint_count += _add_constraint(
                sketch,
                Sketcher.Constraint(
                    "Coincident",
                    anchor[0],
                    anchor[1],
                    current[0],
                    current[1],
                ),
            )
            coincident_endpoints.update(((anchor[0], anchor[1]), (current[0], current[1])))

    for geometry_index, endpoint, point in endpoint_records:
        if (geometry_index, endpoint) in coincident_endpoints:
            continue
        best = None
        for other_index, other_segment in zip(geometry_indices, segments):
            if geometry_index == other_index:
                continue
            distance, parameter = _project_to_segment(point, other_segment)
            if distance > NODE_PRECISION_MM or not (1e-6 < parameter < 1.0 - 1e-6):
                continue
            if best is None or distance < best[0]:
                best = (distance, other_index)
        if best is not None:
            constraint_count += _add_constraint(
                sketch,
                Sketcher.Constraint("PointOnObject", geometry_index, endpoint, best[1]),
            )
    return constraint_count


def _add_constraint(sketch, constraint):
    try:
        result = sketch.addConstraint(constraint)
        return 0 if isinstance(result, int) and result < 0 else 1
    except Exception as exc:
        warn("Restriccion omitida para evitar sobrerrestriccion: %s" % exc)
        return 0


def _group_points(records, tolerance):
    groups = []
    for record in records:
        target = None
        for group in groups:
            if _distance(record[2], group[0][2]) <= tolerance:
                target = group
                break
        if target is None:
            groups.append([record])
        else:
            target.append(record)
    return groups


def _project_to_segment(point, segment):
    dx = segment[2] - segment[0]
    dy = segment[3] - segment[1]
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-12:
        return _distance(point, (segment[0], segment[1])), 0.0
    parameter = ((point[0] - segment[0]) * dx + (point[1] - segment[1]) * dy) / length_squared
    projected = (segment[0] + parameter * dx, segment[1] + parameter * dy)
    return _distance(point, projected), parameter


def _line_segment_from_geometry(geometry):
    type_text = (
        geometry.__class__.__name__
        + " "
        + str(getattr(geometry, "TypeId", "") or "")
    ).lower()
    if "arc" in type_text or "circle" in type_text or "ellipse" in type_text:
        return None
    if "line" not in type_text and not (
        hasattr(geometry, "StartPoint") and hasattr(geometry, "EndPoint")
    ):
        return None
    try:
        first = geometry.StartPoint
        second = geometry.EndPoint
        return (float(first.x), float(first.y), float(second.x), float(second.y))
    except Exception:
        return None


def _is_construction_geometry(sketch, index):
    try:
        return bool(sketch.getConstruction(index))
    except Exception:
        return False


def _clone_geometry(geometry):
    try:
        return geometry.copy()
    except Exception:
        return copy.copy(geometry)


def _map_segment_between_sketches(segment, source, target):
    if source is target:
        return segment
    try:
        source_placement = _global_placement(source)
        target_inverse = _global_placement(target).inverse()
        points = []
        for x, y in ((segment[0], segment[1]), (segment[2], segment[3])):
            global_point = source_placement.multVec(FreeCAD.Vector(x, y, 0.0))
            local_point = target_inverse.multVec(global_point)
            points.extend((float(local_point.x), float(local_point.y)))
        return tuple(points)
    except Exception:
        return segment


def _global_placement(obj):
    try:
        return obj.getGlobalPlacement()
    except Exception:
        return getattr(obj, "Placement")


def _is_opening_sketch(obj):
    if obj is None:
        return False
    type_id = str(getattr(obj, "TypeId", "") or "")
    if not (type_id.startswith("Sketcher::") or hasattr(obj, "Geometry")):
        return False
    if wall_thickness_from_sketch(obj) > 0.0:
        return False
    kind = str(getattr(obj, "FA_CenterlineKind", "") or "").strip().lower()
    if kind in ("wall", "walls", "column", "columns"):
        return False
    if kind in ("door", "doors", "puerta", "puertas", "window", "windows", "ventana", "ventanas"):
        return bool(_geometry_records_from_sketch(obj))
    text = " ".join(
        str(getattr(obj, name, "") or "")
        for name in (
            "Name",
            "Label",
            "FA_ElementType",
            "FA_SourceSelection",
            "FA_ExtractionMode",
        )
    ).lower()
    return any(keyword in text for keyword in OPENING_KEYWORDS) and bool(
        _geometry_records_from_sketch(obj)
    )


def _is_explicit_column_sketch(obj):
    kind = str(getattr(obj, "FA_CenterlineKind", "") or "").strip().lower()
    element_type = str(getattr(obj, "FA_ElementType", "") or "").strip().lower()
    return kind == "columns" or element_type in ("column", "columns", "columna", "columnas")


def _source_key(obj):
    name = str(getattr(obj, "Name", "") or "")
    return ("name", name) if name else ("id", id(obj))


def _replace_segment_endpoint(segment, endpoint, point):
    values = list(segment)
    offset = 0 if int(endpoint) == 0 else 2
    values[offset] = float(point[0])
    values[offset + 1] = float(point[1])
    return tuple(values)


def _unique_closed_wall_label(doc, source):
    base = "%s_%s" % (CLOSED_WALL_SKETCH_PREFIX, safe_name(_object_label(source), "Pared"))
    labels = {
        str(getattr(obj, "Label", "") or "")
        for obj in list(getattr(doc, "Objects", []) or [])
    }
    if base not in labels:
        return base
    index = 2
    while "%s_%02d" % (base, index) in labels:
        index += 1
    return "%s_%02d" % (base, index)


def _quantity_value(value):
    try:
        return float(getattr(value, "Value", value))
    except Exception:
        return 0.0


def _object_label(obj):
    return str(getattr(obj, "Label", getattr(obj, "Name", "Sketch")) or "Sketch")


def _subtract(first, second):
    return (float(first[0]) - float(second[0]), float(first[1]) - float(second[1]))


def _dot2(first, second):
    return first[0] * second[0] + first[1] * second[1]


def _cross2(first, second):
    return first[0] * second[1] - first[1] * second[0]


def collect_room_source_sketches(doc, selection=None):
    """Reuse the architectural sketch collector for walls, doors and windows."""
    return collect_plan_sketches(doc, selection=selection)


def _generated_room_sketches(doc):
    """Return documentary room Sketches generated by this command."""
    return [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == GENERATED_BY_ROOMS
        and str(getattr(obj, "TypeId", "") or "").startswith("Sketcher::")
    ]


def _clear_room_sketch_geometry(sketch):
    """Clear a generated room Sketch in place so external PropertyLinks survive."""
    constraint_count = int(getattr(sketch, "ConstraintCount", 0) or 0)
    geometry_count = int(getattr(sketch, "GeometryCount", 0) or 0)
    for index in range(constraint_count - 1, -1, -1):
        sketch.delConstraint(index)
    for index in range(geometry_count - 1, -1, -1):
        sketch.delGeometry(index)
    return geometry_count, constraint_count


def create_closed_room_sketch(
    doc,
    parent_group,
    source_sketches,
    snap_tolerance=DEFAULT_SNAP_TOLERANCE_MM,
    minimum_room_area_m2=DEFAULT_MIN_ROOM_AREA_M2,
    replace_previous=True,
):
    """Create one constrained Sketcher network containing all bounded rooms."""
    sources = _unique_sources(source_sketches)
    segments = _segments_from_sketches(sources)
    if not segments:
        raise UserFacingError("Los sketches seleccionados no contienen lineas utilizables.")

    topology = build_room_topology(
        segments,
        snap_tolerance=float(snap_tolerance),
        minimum_room_area_mm2=float(minimum_room_area_m2) * 1000000.0,
    )
    if not topology["faces"]:
        raise UserFacingError(
            "No se detectaron recintos cerrados. Revise que puertas y ventanas completen "
            "los huecos de los sketches de paredes."
        )

    sketch = None
    if replace_previous:
        previous = _generated_room_sketches(doc)
        if len(previous) == 1:
            sketch = previous[0]
            geometry_count, previous_constraint_count = _clear_room_sketch_geometry(sketch)
            msg(
                "Sketch de recintos actualizado en sitio: %s | geometria anterior=%d | restricciones anteriores=%d"
                % (sketch.Label, geometry_count, previous_constraint_count)
            )
        elif previous:
            removed = remove_previous_room_sketches(doc)
            if removed:
                msg("Sketches de recintos anteriores reemplazados: %d" % removed)

    if sketch is None:
        sketch = doc.addObject("Sketcher::SketchObject", ROOM_SKETCH_PREFIX)
        sketch.Label = _unique_room_label(doc, sketch)
    try:
        parent_group.addObject(sketch)
    except Exception:
        pass

    geometry_indices = []
    endpoint_refs = {}
    for first, second in topology["edges"]:
        index = sketch.addGeometry(
            Part.LineSegment(
                FreeCAD.Vector(first[0], first[1], 0.0),
                FreeCAD.Vector(second[0], second[1], 0.0),
            ),
            False,
        )
        geometry_indices.append(index)
        endpoint_refs.setdefault(_node_key(first), []).append((index, 1))
        endpoint_refs.setdefault(_node_key(second), []).append((index, 2))

    constraint_count = 0
    for index, (first, second) in zip(geometry_indices, topology["edges"]):
        dx = second[0] - first[0]
        dy = second[1] - first[1]
        angle = math.degrees(math.atan2(abs(dy), abs(dx)))
        try:
            if angle <= AXIS_TOLERANCE_DEG:
                sketch.addConstraint(Sketcher.Constraint("Horizontal", index))
                constraint_count += 1
            elif abs(angle - 90.0) <= AXIS_TOLERANCE_DEG:
                sketch.addConstraint(Sketcher.Constraint("Vertical", index))
                constraint_count += 1
        except Exception:
            pass

    for refs in endpoint_refs.values():
        if len(refs) < 2:
            continue
        anchor = refs[0]
        for current in refs[1:]:
            try:
                sketch.addConstraint(
                    Sketcher.Constraint(
                        "Coincident",
                        anchor[0],
                        anchor[1],
                        current[0],
                        current[1],
                    )
                )
                constraint_count += 1
            except Exception:
                pass

    set_prop(
        sketch,
        "App::PropertyString",
        "FA_GeneratedBy",
        "FacilArquitectura",
        "Comando que genero el sketch",
        GENERATED_BY_ROOMS,
    )
    set_prop(sketch, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "closed_rooms")
    set_prop(
        sketch,
        "App::PropertyLinkList",
        "FA_SourceSketches",
        "FacilArquitectura",
        "Sketches de muros, puertas y ventanas usados",
        sources,
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_RoomCount",
        "FacilArquitectura",
        "Cantidad de recintos cerrados detectados",
        len(topology["faces"]),
    )
    set_prop(
        sketch,
        "App::PropertyStringList",
        "FA_RoomAreas",
        "FacilArquitectura",
        "Areas de los recintos detectados",
        [
            "Recinto %02d: %.3f m2" % (index + 1, face["area"] / 1000000.0)
            for index, face in enumerate(topology["faces"])
        ],
    )
    set_prop(
        sketch,
        "App::PropertyLength",
        "FA_SnapTolerance",
        "FacilArquitectura",
        "Tolerancia usada para cerrar uniones",
        float(snap_tolerance),
    )
    set_prop(
        sketch,
        "App::PropertyFloat",
        "FA_MinRoomAreaM2",
        "FacilArquitectura",
        "Area minima considerada recinto",
        float(minimum_room_area_m2),
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_ParametricConstraintCount",
        "FacilArquitectura",
        "Restricciones parametricas agregadas",
        constraint_count,
    )
    try:
        sketch.ViewObject.LineColor = (0.15, 0.78, 0.48)
        sketch.ViewObject.PointColor = (1.0, 0.75, 0.15)
        sketch.ViewObject.LineWidth = 3.0
    except Exception:
        pass
    doc.recompute()
    msg(
        "Sketch de recintos creado: %s | recintos=%d | bordes=%d | restricciones=%d"
        % (sketch.Label, len(topology["faces"]), len(topology["edges"]), constraint_count)
    )
    return sketch, topology


def build_room_topology(
    segments,
    snap_tolerance=DEFAULT_SNAP_TOLERANCE_MM,
    minimum_room_area_mm2=DEFAULT_MIN_ROOM_AREA_M2 * 1000000.0,
):
    """Snap, split and polygonize a planar line network."""
    cleaned = [_normalize_segment(segment) for segment in segments]
    cleaned = [segment for segment in cleaned if _segment_length(segment) > 1e-6]
    cleaned = _dedupe_segments(cleaned)
    if not cleaned:
        return {"edges": [], "faces": []}

    snapped = _snap_segment_endpoints(cleaned, float(snap_tolerance))
    snapped = _snap_endpoints_to_segments(snapped, float(snap_tolerance))
    split = _split_segments_at_intersections(snapped)
    graph = _graph_from_segments(split)
    faces = _bounded_faces(graph, float(minimum_room_area_mm2))
    room_edges = _edges_from_faces(faces, graph["points"])
    return {
        "edges": room_edges,
        "faces": [
            {
                "points": [graph["points"][node] for node in face],
                "area": abs(_polygon_area([graph["points"][node] for node in face])),
            }
            for face in faces
        ],
    }


def remove_previous_room_sketches(doc):
    candidates = [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == GENERATED_BY_ROOMS
    ]
    removed = 0
    for obj in candidates:
        try:
            if doc.getObject(obj.Name) is not None:
                doc.removeObject(obj.Name)
                removed += 1
        except Exception as exc:
            warn("No se pudo eliminar %s: %s" % (getattr(obj, "Label", obj.Name), exc))
    return removed


def _segments_from_sketches(sketches):
    result = []
    for sketch in sketches:
        shape = getattr(sketch, "Shape", None)
        try:
            edges = list(getattr(shape, "Edges", []) or [])
        except Exception:
            edges = []
        for edge in edges:
            try:
                vertices = list(getattr(edge, "Vertexes", []) or [])
                if len(vertices) >= 2:
                    first = vertices[0].Point
                    second = vertices[-1].Point
                else:
                    first = edge.valueAt(edge.FirstParameter)
                    second = edge.valueAt(edge.LastParameter)
                segment = (float(first.x), float(first.y), float(second.x), float(second.y))
            except Exception:
                continue
            if _segment_length(segment) > 1e-6:
                result.append(segment)
    return result


def _snap_segment_endpoints(segments, tolerance):
    points = []
    for segment in segments:
        points.extend(((segment[0], segment[1]), (segment[2], segment[3])))
    parent = list(range(len(points)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first, second):
        root_first, root_second = find(first), find(second)
        if root_first != root_second:
            parent[root_second] = root_first

    for first in range(len(points)):
        for second in range(first + 1, len(points)):
            if _distance(points[first], points[second]) <= tolerance:
                union(first, second)

    groups = {}
    for index, point in enumerate(points):
        groups.setdefault(find(index), []).append(point)
    centers = {
        root: (
            sum(point[0] for point in group) / len(group),
            sum(point[1] for point in group) / len(group),
        )
        for root, group in groups.items()
    }
    snapped_points = [centers[find(index)] for index in range(len(points))]
    return [
        (
            snapped_points[index * 2][0],
            snapped_points[index * 2][1],
            snapped_points[index * 2 + 1][0],
            snapped_points[index * 2 + 1][1],
        )
        for index in range(len(segments))
    ]


def _snap_endpoints_to_segments(segments, tolerance):
    result = [list(segment) for segment in segments]
    endpoints = [(index, endpoint) for index in range(len(result)) for endpoint in (0, 1)]
    for source_index, endpoint in endpoints:
        point = (
            result[source_index][0 if endpoint == 0 else 2],
            result[source_index][1 if endpoint == 0 else 3],
        )
        best = None
        for target_index, target in enumerate(result):
            if target_index == source_index:
                continue
            projected, parameter, distance = _project_point_to_segment(point, target)
            if parameter <= 1e-6 or parameter >= 1.0 - 1e-6 or distance > tolerance:
                continue
            if best is None or distance < best[0]:
                best = (distance, projected)
        if best is not None:
            if endpoint == 0:
                result[source_index][0], result[source_index][1] = best[1]
            else:
                result[source_index][2], result[source_index][3] = best[1]
    return _snap_segment_endpoints([tuple(segment) for segment in result], tolerance)


def _split_segments_at_intersections(segments):
    parameters = [[0.0, 1.0] for _segment in segments]
    for first_index, first in enumerate(segments):
        for second_index in range(first_index + 1, len(segments)):
            second = segments[second_index]
            intersections = _segment_intersection_parameters(first, second)
            for first_parameter, second_parameter in intersections:
                parameters[first_index].append(first_parameter)
                parameters[second_index].append(second_parameter)

    result = []
    for segment, values in zip(segments, parameters):
        unique = sorted({round(min(1.0, max(0.0, value)), 12) for value in values})
        for start, end in zip(unique, unique[1:]):
            if end - start <= 1e-9:
                continue
            first = _point_on_segment_parameter(segment, start)
            second = _point_on_segment_parameter(segment, end)
            candidate = (first[0], first[1], second[0], second[1])
            if _segment_length(candidate) > 1e-6:
                result.append(candidate)
    return _dedupe_segments(result)


def _segment_intersection_parameters(first, second):
    p = (first[0], first[1])
    r = (first[2] - first[0], first[3] - first[1])
    q = (second[0], second[1])
    s = (second[2] - second[0], second[3] - second[1])
    cross_rs = _cross(r, s)
    q_minus_p = (q[0] - p[0], q[1] - p[1])
    if abs(cross_rs) > 1e-9:
        first_parameter = _cross(q_minus_p, s) / cross_rs
        second_parameter = _cross(q_minus_p, r) / cross_rs
        if -1e-9 <= first_parameter <= 1.0 + 1e-9 and -1e-9 <= second_parameter <= 1.0 + 1e-9:
            return [(first_parameter, second_parameter)]
        return []

    if abs(_cross(q_minus_p, r)) > 1e-9:
        return []
    result = []
    for first_parameter, point in (
        (0.0, p),
        (1.0, (first[2], first[3])),
    ):
        second_parameter = _parameter_on_segment(point, second)
        if second_parameter is not None:
            result.append((first_parameter, second_parameter))
    for second_parameter, point in (
        (0.0, q),
        (1.0, (second[2], second[3])),
    ):
        first_parameter = _parameter_on_segment(point, first)
        if first_parameter is not None:
            result.append((first_parameter, second_parameter))
    return result


def _graph_from_segments(segments):
    points = {}
    edge_keys = set()
    adjacency = {}
    for segment in segments:
        first = (segment[0], segment[1])
        second = (segment[2], segment[3])
        first_key = _node_key(first)
        second_key = _node_key(second)
        if first_key == second_key:
            continue
        points.setdefault(first_key, first)
        points.setdefault(second_key, second)
        edge = tuple(sorted((first_key, second_key)))
        if edge in edge_keys:
            continue
        edge_keys.add(edge)
        adjacency.setdefault(first_key, set()).add(second_key)
        adjacency.setdefault(second_key, set()).add(first_key)
    return {"points": points, "edges": edge_keys, "adjacency": adjacency}


def _bounded_faces(graph, minimum_area):
    points = graph["points"]
    adjacency = {
        node: sorted(
            neighbors,
            key=lambda neighbor: math.atan2(
                points[neighbor][1] - points[node][1],
                points[neighbor][0] - points[node][0],
            ),
        )
        for node, neighbors in graph["adjacency"].items()
    }
    visited = set()
    faces = []
    for first, neighbors in adjacency.items():
        for second in neighbors:
            start = (first, second)
            if start in visited:
                continue
            cycle = []
            current = start
            for _step in range(max(4, len(graph["edges"]) * 2 + 4)):
                if current in visited:
                    break
                visited.add(current)
                source, target = current
                cycle.append(source)
                target_neighbors = adjacency.get(target, [])
                if source not in target_neighbors or not target_neighbors:
                    break
                reverse_index = target_neighbors.index(source)
                next_node = target_neighbors[(reverse_index - 1) % len(target_neighbors)]
                current = (target, next_node)
                if current == start:
                    if len(cycle) >= 3:
                        polygon = [points[node] for node in cycle]
                        area = _polygon_area(polygon)
                        if area >= minimum_area:
                            faces.append(cycle)
                    break
    return faces


def _edges_from_faces(faces, points):
    keys = set()
    result = []
    for face in faces:
        for first_node, second_node in zip(face, face[1:] + face[:1]):
            edge_key = tuple(sorted((first_node, second_node)))
            if edge_key in keys:
                continue
            keys.add(edge_key)
            first = points[first_node]
            second = points[second_node]
            result.append((first, second))
    return result


def _dedupe_segments(segments):
    result = []
    seen = set()
    for segment in segments:
        first = _node_key((segment[0], segment[1]))
        second = _node_key((segment[2], segment[3]))
        key = tuple(sorted((first, second)))
        if first == second or key in seen:
            continue
        seen.add(key)
        result.append(segment)
    return result


def _parameter_on_segment(point, segment):
    projected, parameter, distance = _project_point_to_segment(point, segment)
    if distance <= NODE_PRECISION_MM and -1e-9 <= parameter <= 1.0 + 1e-9:
        return parameter
    return None


def _project_point_to_segment(point, segment):
    dx = segment[2] - segment[0]
    dy = segment[3] - segment[1]
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-12:
        base = (segment[0], segment[1])
        return base, 0.0, _distance(point, base)
    parameter = ((point[0] - segment[0]) * dx + (point[1] - segment[1]) * dy) / length_squared
    projected = (segment[0] + parameter * dx, segment[1] + parameter * dy)
    return projected, parameter, _distance(point, projected)


def _point_on_segment_parameter(segment, parameter):
    return (
        segment[0] + (segment[2] - segment[0]) * parameter,
        segment[1] + (segment[3] - segment[1]) * parameter,
    )


def _polygon_area(points):
    return (
        sum(
            first[0] * second[1] - second[0] * first[1]
            for first, second in zip(points, points[1:] + points[:1])
        )
        / 2.0
    )


def _normalize_segment(segment):
    return tuple(float(value) for value in segment)


def _segment_length(segment):
    return math.hypot(segment[2] - segment[0], segment[3] - segment[1])


def _distance(first, second):
    return math.hypot(first[0] - second[0], first[1] - second[1])


def _cross(first, second):
    return first[0] * second[1] - first[1] * second[0]


def _node_key(point):
    return (
        int(round(float(point[0]) / NODE_PRECISION_MM)),
        int(round(float(point[1]) / NODE_PRECISION_MM)),
    )


def _unique_sources(sketches):
    result = []
    seen = set()
    for sketch in sketches or []:
        name = str(getattr(sketch, "Name", "") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(sketch)
    return result


def _unique_room_label(doc, current):
    base = ROOM_SKETCH_PREFIX
    labels = {
        str(getattr(obj, "Label", "") or "")
        for obj in list(getattr(doc, "Objects", []) or [])
        if obj is not current
    }
    if base not in labels:
        return base
    sequence = 2
    while "%s_%03d" % (base, sequence) in labels:
        sequence += 1
    return "%s_%03d" % (base, sequence)
