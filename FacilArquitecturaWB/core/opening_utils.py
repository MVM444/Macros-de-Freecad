"""Native BIM door, window and opening-only creation from centerline Sketches.

Descripcion: resuelve muros anfitriones y crea Arch Window/Doors con cortes reales.
Objetivo: crear aberturas alojadas en su muro anfitrion sin duplicarlas como miembros
directos del Building Storey, aceptando Sketches explicitamente seleccionados aunque
conserven metadatos historicos incorrectos.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-30 14:30 UTC-06:00.
Version: 0.7.0.
Instrucciones de mantenimiento: la seleccion explicita tiene prioridad si el Sketch
no es una base generada ni posee espesor de muro; conservar diagnosticos de rechazo.
"""

from __future__ import annotations

import math
import re

import FreeCAD

from .bim_utils import make_arch_window, make_arch_window_preset, wall_thickness_from_sketch
from .bim_structure_utils import is_level, tag_target_level
from .command_errors import UserFacingError
from .door_type_utils import door_preset_override, native_door_presets
from .door_corner_utils import (
    DEFAULT_CORNER_SNAP_TOLERANCE_MM,
    desired_open_leaf_vector,
    plan_door_corner_snap,
    resolve_native_opening_mode,
)
from .project_structure import ensure_group, msg, set_prop, warn


GENERATED_BY_DOORS = "FA_CreateDoorsFromSketch"
GENERATED_BY_WINDOWS = "FA_CreateWindowsFromSketch"
GENERATED_BY_OPENINGS = "FA_CreateOpeningsFromSketch"
LEGACY_GENERATORS = {
    "door": ("FA_CreateDoorsBIM", "FA_InsertDoorsBIM"),
    "window": ("FA_CreateWindowsBIM", "FA_InsertWindowsBIM"),
    "opening": (),
}
REPLACEABLE_GENERATORS = {
    "door": (GENERATED_BY_DOORS, "FA_CreateDoorsBIM"),
    "window": (GENERATED_BY_WINDOWS, "FA_CreateWindowsBIM"),
    "opening": (GENERATED_BY_OPENINGS,),
}
GROUP_SPECS = {
    "door": ("FA_Doors", "FA Doors"),
    "window": ("FA_Windows", "FA Windows"),
    "opening": ("FA_Openings", "FA Openings"),
}
MIN_OPENING_WIDTH_MM = 50.0
DEFAULT_ANGLE_TOLERANCE_DEG = 15.0
DEFAULT_COLLINEAR_TOLERANCE_MM = 80.0


def segment_length(segment):
    """Return the XY length of a six-value 3D segment tuple."""
    values = _segment_values(segment)
    return math.hypot(values[3] - values[0], values[4] - values[1])


def project_point_to_line(point, segment):
    """Project a 3D point to the infinite XY line of a segment."""
    values = _segment_values(segment)
    px, py, pz = _point_values(point)
    dx = values[3] - values[0]
    dy = values[4] - values[1]
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return float("inf"), (values[0], values[1], values[2]), 0.0
    parameter = ((px - values[0]) * dx + (py - values[1]) * dy) / length_sq
    projected = (
        values[0] + parameter * dx,
        values[1] + parameter * dy,
        values[2] + parameter * (values[5] - values[2]),
    )
    return math.hypot(px - projected[0], py - projected[1]), projected, parameter


def evaluate_wall_candidate(
    opening_segment,
    wall_segments,
    max_distance_mm,
    angle_tolerance_deg=DEFAULT_ANGLE_TOLERANCE_DEG,
    max_overhang_mm=None,
    collinear_tolerance_mm=DEFAULT_COLLINEAR_TOLERANCE_MM,
):
    """Return the best geometric match between one opening and one wall."""
    opening = _segment_values(opening_segment)
    opening_length = segment_length(opening)
    if opening_length <= 1e-9:
        return None
    oux = (opening[3] - opening[0]) / opening_length
    ouy = (opening[4] - opening[1]) / opening_length
    minimum_dot = math.cos(math.radians(float(angle_tolerance_deg)))
    max_distance = float(max_distance_mm)
    max_overhang = (
        max(500.0, max_distance * 2.0)
        if max_overhang_mm is None
        else float(max_overhang_mm)
    )
    walls = [_segment_values(segment) for segment in wall_segments or []]
    matches = []
    for reference_index, reference in enumerate(walls):
        wall_length = segment_length(reference)
        if wall_length <= 1e-9:
            continue
        wux = (reference[3] - reference[0]) / wall_length
        wuy = (reference[4] - reference[1]) / wall_length
        parallel = abs(oux * wux + ouy * wuy)
        if parallel < minimum_dot:
            continue
        distance_a, projected_a, _ = project_point_to_line(opening[:3], reference)
        distance_b, projected_b, _ = project_point_to_line(opening[3:], reference)
        offset = (distance_a + distance_b) * 0.5
        if offset > max_distance or max(distance_a, distance_b) > max_distance * 1.5:
            continue

        support = []
        for peer in walls:
            peer_length = segment_length(peer)
            if peer_length <= 1e-9:
                continue
            pux = (peer[3] - peer[0]) / peer_length
            puy = (peer[4] - peer[1]) / peer_length
            if abs(wux * pux + wuy * puy) < minimum_dot:
                continue
            peer_distance_a, _, _ = project_point_to_line(peer[:3], reference)
            peer_distance_b, _, _ = project_point_to_line(peer[3:], reference)
            if max(peer_distance_a, peer_distance_b) > float(collinear_tolerance_mm):
                continue
            support.extend(
                (
                    _scalar_on_axis(peer[:3], reference[:3], (wux, wuy)),
                    _scalar_on_axis(peer[3:], reference[:3], (wux, wuy)),
                )
            )
        if not support:
            continue
        axis_values = (
            _scalar_on_axis(projected_a, reference[:3], (wux, wuy)),
            _scalar_on_axis(projected_b, reference[:3], (wux, wuy)),
        )
        support_min, support_max = min(support), max(support)
        axis_min, axis_max = min(axis_values), max(axis_values)
        overhang = max(0.0, support_min - axis_min, axis_max - support_max)
        if overhang > max_overhang:
            continue
        angle_error = math.degrees(math.acos(max(-1.0, min(1.0, parallel))))
        wall_z = (projected_a[2] + projected_b[2]) * 0.5
        opening_z = (opening[2] + opening[5]) * 0.5
        z_offset = abs(opening_z - wall_z)
        if z_offset > max_distance:
            continue
        score = offset + overhang * 5.0 + angle_error * 2.0 + z_offset
        matches.append(
            {
                "score": score,
                "distance": offset,
                "overhang": overhang,
                "angle_error_deg": angle_error,
                "z_offset": z_offset,
                "projected_first": projected_a,
                "projected_second": projected_b,
                "wall_z": wall_z,
                "reference_segment_index": reference_index,
            }
        )
    return min(matches, key=lambda item: item["score"]) if matches else None


def select_best_host(
    opening_segment,
    wall_records,
    max_distance_mm,
    angle_tolerance_deg=DEFAULT_ANGLE_TOLERANCE_DEG,
    ambiguity_margin_mm=None,
):
    """Select one compatible host or report ambiguity between distinct walls."""
    candidates = []
    for record in wall_records or []:
        match = evaluate_wall_candidate(
            opening_segment,
            record.get("segments", []),
            max_distance_mm=max_distance_mm,
            angle_tolerance_deg=angle_tolerance_deg,
        )
        if match is None:
            continue
        candidate = dict(match)
        candidate["wall"] = record.get("wall")
        candidates.append(candidate)
    candidates.sort(key=lambda item: item["score"])
    if not candidates:
        return {"match": None, "ambiguous": False, "candidates": []}
    margin = (
        max(5.0, float(max_distance_mm) * 0.10)
        if ambiguity_margin_mm is None
        else float(ambiguity_margin_mm)
    )
    ambiguous = False
    if len(candidates) > 1:
        first = candidates[0]
        second = candidates[1]
        ambiguous = (
            first.get("wall") is not second.get("wall")
            and second["score"] - first["score"] <= margin
        )
    return {
        "match": None if ambiguous else candidates[0],
        "ambiguous": ambiguous,
        "candidates": candidates,
    }


def resolve_door_corner_snap(
    match,
    wall_records,
    tolerance_mm=DEFAULT_CORNER_SNAP_TOLERANCE_MM,
):
    """Adapt FreeCAD wall records to the pure door-corner snap planner.

    The returned ``match`` is a shallow copy with translated projected endpoints
    when one unique side wall is close enough. The opening length is preserved.
    """
    if match is None or match.get("wall") is None:
        return {"applied": False, "ambiguous": False, "match": match, "reason": "sin host"}
    host = match["wall"]
    host_key = _wall_record_key(host)
    host_segment_index = int(match.get("reference_segment_index", -1))
    pure_records = []
    object_map = {}
    for record in list(wall_records or []):
        wall = record.get("wall")
        if wall is None:
            continue
        key = _wall_record_key(wall)
        label = _object_label(wall)
        width = _wall_width(wall)
        segments = list(record.get("segments") or [])
        if wall is host:
            # A single Arch Wall can be based on a network Sketch containing the
            # host run and all perpendicular room walls.  Excluding the complete
            # object would hide every valid lateral segment.  Give only the actual
            # host segment its object key (the pure planner excludes that key) and
            # expose the remaining runs as virtual records that still resolve to
            # the same BIM Wall object.
            for segment_index, segment in enumerate(segments):
                virtual_key = (
                    key
                    if segment_index == host_segment_index
                    else "%s::segment:%d" % (key, segment_index)
                )
                object_map[virtual_key] = wall
                pure_records.append(
                    {
                        "wall_key": virtual_key,
                        "label": label,
                        "width_mm": width,
                        "segments": [segment],
                    }
                )
            continue
        object_map[key] = wall
        pure_records.append(
            {
                "wall_key": key,
                "label": label,
                "width_mm": width,
                "segments": segments,
            }
        )
    first = tuple(match["projected_first"])
    second = tuple(match["projected_second"])
    plan = plan_door_corner_snap(
        first + second,
        host_key,
        pure_records,
        tolerance_mm=float(tolerance_mm),
    )
    result = dict(plan)
    result["match"] = dict(match)
    if plan.get("applied"):
        result["match"]["projected_first"] = tuple(plan["projected_first"])
        result["match"]["projected_second"] = tuple(plan["projected_second"])
    candidate = plan.get("jamb_face_candidate") or {}
    side_key = str(plan.get("side_wall_key") or candidate.get("side_wall_key") or "")
    result["side_wall"] = object_map.get(side_key)
    return result


def apply_door_corner_metadata(obj, corner_plan):
    """Persist traceability for a previously resolved door corner snap."""
    plan = dict(corner_plan or {})
    applied = bool(plan.get("applied"))
    set_prop(obj, "App::PropertyBool", "FA_CornerSnapped", "FacilArquitectura", "Jamba ajustada a pared lateral", applied)
    set_prop(obj, "App::PropertyString", "FA_CornerStatus", "FacilArquitectura", "Estado del analisis de esquina", str(plan.get("status") or "NO_CANDIDATE"))
    set_prop(obj, "App::PropertyBool", "FA_CornerNoFit", "FacilArquitectura", "El ancho no cabe entre caras laterales", bool(plan.get("no_fit")))
    set_prop(obj, "App::PropertyBool", "FA_CornerSwingResolved", "FacilArquitectura", "La geometria resolvio el cuadrante de giro", bool(plan.get("swing_resolved")))
    set_prop(obj, "App::PropertyString", "FA_JambEndpoint", "FacilArquitectura", "Jamba alineada respecto al Sketch", str(plan.get("jamb_endpoint") or "AUTO"))
    set_prop(obj, "App::PropertyString", "FA_CornerSnapReason", "FacilArquitectura", "Motivo del ajuste de esquina", str(plan.get("reason") or ""))
    if plan.get("no_fit"):
        set_prop(obj, "App::PropertyLength", "FA_OpeningWidthChecked_mm", "FacilArquitectura", "Ancho autoritativo comprobado", float(plan.get("opening_width_mm") or 0.0))
        set_prop(obj, "App::PropertyLength", "FA_AvailableWidth_mm", "FacilArquitectura", "Luz util entre caras laterales", float(plan.get("available_width_mm") or 0.0))
        set_prop(obj, "App::PropertyLength", "FA_CornerPenetration_mm", "FacilArquitectura", "Penetracion que produciria el snap", float(plan.get("penetration_mm") or 0.0))
    if not applied:
        return obj
    side_wall = plan.get("side_wall")
    if side_wall is not None:
        # This is traceability, not a second host relation.  In FreeCAD 1.1.3
        # every PropertyLink back to the host participates in MoveWithHost and
        # can multiply the displacement of the opening.
        set_prop(
            obj,
            "App::PropertyString",
            "FA_CornerWall",
            "FacilArquitectura",
            "Nombre estable de la pared lateral usada para snap",
            str(getattr(side_wall, "Name", "") or ""),
        )
    set_prop(obj, "App::PropertyLength", "FA_CornerGapBefore_mm", "FacilArquitectura", "Separacion previa entre jamba y cara lateral", float(plan.get("snap_distance_mm") or 0.0))
    set_prop(obj, "App::PropertyFloat", "FA_CornerShift_mm", "FacilArquitectura", "Desplazamiento longitudinal aplicado", float(plan.get("shift_mm") or 0.0))
    return obj


def collect_opening_sketches_from_selection(selection, opening_kind):
    """Collect source sketches from explicit objects, groups and App links.

    A selected BIM wall never contributes its Base sketch: its source represents
    the wall axis, not an opening.  Link-like objects do preserve the explicit
    selection flag so a linked generic Sketch can be used intentionally.
    """
    kind = _normalize_kind(opening_kind)
    result = []
    seen = set()
    pending = [(obj, True) for obj in list(selection or [])]
    while pending:
        obj, explicit = pending.pop(0)
        key = _object_key(obj)
        if key in seen:
            continue
        seen.add(key)
        if _is_sketch(obj):
            accepted, _reason = opening_source_assessment(obj, kind, explicit=explicit)
            if accepted:
                result.append(obj)
            continue
        for attr in ("Group", "Objects"):
            try:
                pending.extend((child, False) for child in list(getattr(obj, attr, []) or []))
            except Exception:
                pass
        if is_bim_wall(obj):
            continue
        for attr in ("LinkedObject", "Link", "SourceObject", "FA_SourceSketch"):
            try:
                pending.extend(
                    (child, explicit)
                    for child in _linked_selection_objects(getattr(obj, attr, None))
                )
            except Exception:
                pass
    return result


def collect_opening_sketches_from_document(doc, opening_kind):
    """Find explicitly identified opening-center Sketches in a document.

    This is the safe fallback for the toolbar workflow: it accepts only sketches
    whose name, label or FA metadata identifies the requested opening type.  It
    never treats an arbitrary document sketch as an opening source.
    """
    kind = _normalize_kind(opening_kind)
    result = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_sketch(obj):
            continue
        accepted, _reason = opening_source_assessment(obj, kind, explicit=False)
        if accepted:
            result.append(obj)
    candidates = _unique_objects(result)
    if len(candidates) <= 1:
        return candidates

    reference_counts = {
        _object_key(source): _existing_source_reference_count(doc, source, kind)
        for source in candidates
    }
    maximum_references = max(reference_counts.values())
    if maximum_references > 0:
        candidates = [
            source
            for source in candidates
            if reference_counts[_object_key(source)] == maximum_references
        ]
        if len(candidates) == 1:
            return candidates

    canonical_name = {
        "door": "Sketch_Centros_Puertas",
        "window": "Sketch_Centros_Ventanas",
        "opening": "Sketch_Centros_Aberturas",
    }[kind]
    canonical = [
        source
        for source in candidates
        if str(getattr(source, "Name", "") or "") == canonical_name
        or str(getattr(source, "Label", "") or "") == canonical_name
    ]
    return canonical if len(canonical) == 1 else candidates


def opening_source_assessment(sketch, opening_kind, explicit=False):
    """Return ``(accepted, reason)`` for one possible opening-center Sketch.

    Explicit selection is authoritative for generic or historically mislabeled
    zero-thickness Sketches. Automatic discovery remains conservative.
    """
    kind = _normalize_kind(opening_kind)
    if not _is_sketch(sketch):
        return False, "no es un Sketcher::SketchObject"
    thickness = wall_thickness_from_sketch(sketch)
    if thickness > 0.0:
        return False, "posee espesor de muro %.1f mm" % thickness
    role = str(getattr(sketch, "FA_Role", "") or "").strip().lower()
    generated_by = str(getattr(sketch, "FA_GeneratedBy", "") or "")
    if role in ("door_base", "window_base", "opening_base"):
        return False, "es una base BIM generada, no un Sketch fuente"
    all_generators = {
        GENERATED_BY_DOORS,
        GENERATED_BY_WINDOWS,
        GENERATED_BY_OPENINGS,
        "FA_CreateDoorsBIM",
        "FA_CreateWindowsBIM",
    }
    if generated_by in all_generators:
        return False, "fue generado por %s" % generated_by

    centerline_kind = str(getattr(sketch, "FA_CenterlineKind", "") or "").lower()
    element_type = str(getattr(sketch, "FA_ElementType", "") or "").lower()
    text = " ".join(
        str(getattr(sketch, attr, "") or "")
        for attr in ("Name", "Label", "FA_Role", "FA_CenterlineKind", "FA_ElementType")
    ).lower()
    words_by_kind = {
        "door": ("door", "doors", "puerta", "puertas"),
        "window": ("window", "windows", "ventana", "ventanas"),
        "opening": ("opening", "openings", "abertura", "aberturas", "vano", "vanos", "buque", "buques"),
    }
    own_words = words_by_kind[kind]
    other_words = tuple(
        word for peer, words in words_by_kind.items() if peer != kind for word in words
    )
    if any(word in text for word in other_words):
        return False, "sus metadatos o nombre corresponden al otro tipo de abertura"
    if any(word in text for word in own_words):
        if centerline_kind in ("walls", "columns"):
            return True, "aceptado por nombre/tipo; FA_CenterlineKind historico=%s" % centerline_kind
        return True, "identificado por nombre o metadatos"
    if explicit:
        return True, "aceptado por seleccion explicita como Sketch generico sin espesor"
    if centerline_kind in ("walls", "columns") or element_type in (
        "wall",
        "walls",
        "muro",
        "muros",
        "column",
        "columns",
        "columna",
        "columnas",
    ):
        return False, "sus metadatos lo clasifican como muro o columna"
    return False, "no contiene nombre ni metadatos de %s" % (
        {"door": "puerta", "window": "ventana", "opening": "abertura"}[kind]
    )


def selection_description(selection):
    """Return a concise diagnostic description of the GUI selection."""
    objects = list(selection or [])
    if not objects:
        return "ninguna"
    return ", ".join(
        "%s [%s]"
        % (
            _object_label(obj),
            str(getattr(obj, "TypeId", "sin TypeId") or "sin TypeId"),
        )
        for obj in objects
    )


def collect_bim_walls(doc, selection=None):
    """Return selected BIM walls, or all document walls when none were selected."""
    selected = _collect_wall_objects(selection)
    objects = selected if selected else list(getattr(doc, "Objects", []) or [])
    result = []
    seen = set()
    for obj in objects:
        if not is_bim_wall(obj):
            continue
        key = _object_key(obj)
        if key in seen:
            continue
        seen.add(key)
        if wall_source_segments(obj):
            result.append(obj)
    return result


def is_bim_wall(obj):
    """Recognize native Arch walls, including FA-generated walls."""
    if obj is None:
        return False
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "").lower()
    ifc_type = str(getattr(obj, "IfcType", "") or "").lower()
    role = str(getattr(obj, "FA_Role", "") or "").lower()
    generated_by = str(getattr(obj, "FA_GeneratedBy", "") or "")
    is_wall_semantic = (
        proxy_type == "wall"
        or ifc_type in ("wall", "wall standard case")
        or role in ("wall", "reconstructed_wall")
        or generated_by in ("FA_CreateWallsBIM", "FA_CreateBuildingGrid")
    )
    shape = getattr(obj, "Shape", None)
    has_solid = bool(list(getattr(shape, "Solids", []) or []))
    return bool(is_wall_semantic and has_solid)


def wall_source_segments(wall):
    """Return global centerline segments from the authoritative wall source."""
    for attr in ("FA_SourceSketch", "Base", "FA_SourceGridTrace", "FA_SourceCenterline"):
        source = _linked_object(getattr(wall, attr, None))
        if source is None:
            continue
        segments = sketch_segments(source)
        if segments:
            return segments
    return []


def sketch_segments(sketch):
    """Return non-construction line geometry in global coordinates."""
    result = []
    placement = _global_placement(sketch)
    for index, geometry in enumerate(list(getattr(sketch, "Geometry", []) or [])):
        try:
            if bool(sketch.getConstruction(index)):
                continue
        except Exception:
            pass
        if not hasattr(geometry, "StartPoint") or not hasattr(geometry, "EndPoint"):
            continue
        try:
            first = placement.multVec(geometry.StartPoint)
            second = placement.multVec(geometry.EndPoint)
            segment = (
                float(first.x),
                float(first.y),
                float(first.z),
                float(second.x),
                float(second.y),
                float(second.z),
            )
        except Exception:
            continue
        if segment_length(segment) < MIN_OPENING_WIDTH_MM:
            continue
        result.append({"index": index, "segment": segment})
    return result


def create_openings_from_centerlines(
    doc,
    target_container,
    source_sketches,
    walls,
    opening_kind,
    height_mm,
    sill_mm=0.0,
    host_tolerance_mm=250.0,
    replace_existing=True,
    door_corner_snap_tolerance_mm=DEFAULT_CORNER_SNAP_TOLERANCE_MM,
):
    """Create hosted native Arch door, window or opening-only objects from axes."""
    kind = _normalize_kind(opening_kind)
    sources = _unique_objects(source_sketches)
    if not sources:
        raise UserFacingError("Seleccione al menos un Sketch de centros de aberturas.")
    wall_records = [
        {"wall": wall, "segments": [item["segment"] for item in wall_source_segments(wall)]}
        for wall in _unique_objects(walls)
        if is_bim_wall(wall)
    ]
    wall_records = [record for record in wall_records if record["segments"]]
    if not wall_records:
        raise UserFacingError("No se encontraron muros BIM con Sketch Base utilizable.")
    height = float(height_mm)
    sill = float(sill_mm)
    tolerance = float(host_tolerance_mm)
    if height <= 0.0:
        raise UserFacingError("La altura de la abertura debe ser mayor que cero.")
    if sill < 0.0:
        raise UserFacingError("El antepecho no puede ser negativo.")
    if tolerance <= 0.0:
        raise UserFacingError("La tolerancia de muro debe ser mayor que cero.")

    if kind == "opening":
        _kind_log(kind, "Sketches fuente: %d" % len(sources))
        _kind_log(kind, "Lineas detectadas: %d" % sum(len(sketch_segments(item)) for item in sources))
        _kind_log(kind, "Muros BIM candidatos: %d" % len(wall_records))

    generator = _generator_for_kind(kind)
    removed = 0
    if replace_existing:
        removed = remove_generated_openings(doc, sources, kind)
        if removed:
            doc.recompute()
            _kind_log(kind, "Aberturas FA anteriores reemplazadas: %d" % removed)
    existing = existing_opening_keys(doc, sources, kind)
    plans = []
    rejected = []
    skipped = 0
    for source in sources:
        segments = sketch_segments(source)
        for item in segments:
            key = (_object_key(source), int(item["index"]))
            if key in existing:
                skipped += 1
                continue
            selection = select_best_host(
                item["segment"], wall_records, max_distance_mm=tolerance
            )
            for candidate in selection["candidates"]:
                _kind_log(
                    kind,
                    "%s %02d -> host candidate %s | distance %.1f mm | score %.1f"
                    % (
                        kind.capitalize(),
                        item["index"] + 1,
                        _object_label(candidate["wall"]),
                        candidate["distance"],
                        candidate["score"],
                    )
                )
            if selection["ambiguous"]:
                rejected.append((source, item["index"], "host ambiguo"))
                _kind_log(
                    kind,
                    "%s %02d omitida: dos muros son geometricamente equivalentes."
                    % (kind.capitalize(), item["index"] + 1),
                    warning=True,
                )
                if kind == "opening":
                    _kind_log(kind, "Host ambiguo para geometria %d" % item["index"], warning=True)
                continue
            match = selection["match"]
            if match is None:
                rejected.append((source, item["index"], "sin host compatible"))
                _kind_log(
                    kind,
                    "%s %02d omitida: no hay muro compatible dentro de %.1f mm."
                    % (kind.capitalize(), item["index"] + 1, tolerance),
                    warning=True,
                )
                continue
            _kind_log(
                kind,
                "%s %02d -> selected host %s"
                % (kind.capitalize(), item["index"] + 1, _object_label(match["wall"]))
            )
            door_options = None
            corner_plan = None
            if kind == "door":
                corner_plan = resolve_door_corner_snap(
                    match, wall_records, tolerance_mm=door_corner_snap_tolerance_mm
                )
                door_options = {"corner_snap": corner_plan}
                if corner_plan.get("ambiguous"):
                    _kind_log(
                        kind,
                        "Puerta %02d: snap de esquina ambiguo; se conserva posicion del Sketch." % (item["index"] + 1),
                        warning=True,
                    )
                elif corner_plan.get("no_fit"):
                    _kind_log(
                        kind,
                        "Puerta %02d: NO_FIT; ancho %.1f mm > luz util %.1f mm. Se conserva posicion y ancho del Sketch."
                        % (
                            item["index"] + 1,
                            float(corner_plan.get("opening_width_mm") or 0.0),
                            float(corner_plan.get("available_width_mm") or 0.0),
                        ),
                        warning=True,
                    )
                elif corner_plan.get("applied") or corner_plan.get("swing_resolved"):
                    if corner_plan.get("applied"):
                        match = corner_plan["match"]
                    if corner_plan.get("swing_resolved"):
                        door_options.update({
                            "hinge_endpoint": corner_plan["hinge_endpoint"],
                            "opening_side": corner_plan["opening_side"],
                            "opens_inward": corner_plan.get("opens_inward"),
                        })
                    if corner_plan.get("position_preserved"):
                        _kind_log(
                            kind,
                            "Puerta %02d: dos caras opuestas acotan el vano; se conserva posicion del Sketch | bisagra %s | apertura %s"
                            % (
                                item["index"] + 1,
                                corner_plan["hinge_endpoint"],
                                corner_plan["opening_side"],
                            ),
                            warning=True,
                        )
                    elif corner_plan.get("applied"):
                        if corner_plan.get("swing_resolved"):
                            _kind_log(
                                kind,
                                "Puerta %02d: jamba ajustada %.1f mm a %s | bisagra %s | apertura %s"
                                % (
                                    item["index"] + 1,
                                    float(corner_plan.get("snap_distance_mm") or 0.0),
                                    str(corner_plan.get("side_wall_label") or "pared lateral"),
                                    corner_plan["hinge_endpoint"],
                                    corner_plan["opening_side"],
                                ),
                            )
                        else:
                            _kind_log(
                                kind,
                                "Puerta %02d: jamba alineada %.1f mm; cruce/T inversa sin autoridad para giro, apertura AUTO."
                                % (
                                    item["index"] + 1,
                                    float(corner_plan.get("snap_distance_mm") or 0.0),
                                ),
                                warning=True,
                            )
            plans.append({"source": source, "axis": item, "match": match, "door_options": door_options, "corner_plan": corner_plan})

    if not plans and not skipped:
        raise UserFacingError(
            "Ningun eje de %s encontro un muro BIM anfitrion no ambiguo."
            % ({"door": "puerta", "window": "ventana", "opening": "abertura"}[kind])
        )
    container = ensure_opening_group(doc, target_container, kind)
    host_shapes_before = {}
    host_volumes_before = {}
    for plan in plans:
        wall = plan["match"]["wall"]
        if wall in host_shapes_before:
            continue
        host_shapes_before[wall] = wall.Shape.copy()
        host_volumes_before[wall] = float(wall.Shape.Volume)

    created = []
    for plan in plans:
        obj = _create_native_opening(
            doc,
            container,
            plan["source"],
            plan["axis"],
            plan["match"],
            kind,
            height,
            sill,
            generator,
            options=plan.get("door_options"),
        )
        created.append(obj)
    for wall in host_shapes_before:
        wall.touch()
    doc.recompute()

    cut_volume = 0.0
    for obj in created:
        wall = obj.FA_HostWall
        if wall not in list(getattr(obj, "Hosts", []) or []):
            raise UserFacingError("La abertura %s no conservo su muro anfitrion." % obj.Label)
        if getattr(obj, "Base", None) is None:
            raise UserFacingError("La abertura %s no tiene Sketch Base nativo." % obj.Label)
        try:
            subvolume = obj.Proxy.getSubVolume(obj, host=wall)
            intersection = float(host_shapes_before[wall].common(subvolume).Volume)
        except Exception:
            intersection = 0.0
        if intersection <= 1.0:
            raise UserFacingError(
                "La abertura %s no intersecta realmente el muro anfitrion." % obj.Label
            )
        set_prop(
            obj,
            "App::PropertyFloat",
            "FA_CutVolume_mm3",
            "FacilArquitectura",
            "Volumen de muro intersectado durante validacion",
            intersection,
        )
        cut_volume += intersection
    for wall, before in host_volumes_before.items():
        hosted_created = [obj for obj in created if obj.FA_HostWall is wall]
        if hosted_created and float(wall.Shape.Volume) >= before - 1.0:
            raise UserFacingError(
                "Las aberturas alojadas en %s no produjeron un corte real." % _object_label(wall)
            )
    summary = {
        "created_count": len(created),
        "rejected_count": len(rejected),
        "skipped_existing_count": skipped,
        "removed_count": removed,
        "candidate_wall_count": len(wall_records),
        "cut_volume_mm3": cut_volume,
        "corner_snapped_count": sum(1 for item in plans if item.get("corner_plan") and item["corner_plan"].get("applied")),
        "corner_ambiguous_count": sum(1 for item in plans if item.get("corner_plan") and item["corner_plan"].get("ambiguous")),
        "corner_no_fit_count": sum(1 for item in plans if item.get("corner_plan") and item["corner_plan"].get("no_fit")),
        "corner_jamb_only_count": sum(1 for item in plans if item.get("corner_plan") and item["corner_plan"].get("status") == "JAMB_ONLY"),
        "rejected": rejected,
    }
    if kind == "opening":
        _kind_log(kind, "Aberturas creadas: %d" % summary["created_count"])
        _kind_log(kind, "Lineas omitidas: %d" % summary["rejected_count"])
    return created, summary


def ensure_opening_group(doc, target_container, opening_kind):
    """Return a native Level directly, or a legacy opening group when needed."""
    if is_level(target_container):
        return target_container
    kind = _normalize_kind(opening_kind)
    name, label = GROUP_SPECS[kind]
    group = ensure_group(doc, name, label, target_container)
    set_prop(
        group,
        "App::PropertyString",
        "FA_Role",
        "FacilArquitectura",
        "Rol",
        {"door": "doors", "window": "windows", "opening": "openings"}[kind],
    )
    return group


def place_hosted_opening_in_tree(target_container, obj, base):
    """Keep one visible tree residence for a hosted opening and its Base."""
    if is_level(target_container):
        tag_target_level(target_container, obj)
        tag_target_level(target_container, base)
    else:
        target_container.addObject(obj)
    return obj


def existing_opening_keys(doc, sources, opening_kind):
    """Return source/index keys, including compatible legacy Puriscal objects."""
    kind = _normalize_kind(opening_kind)
    source_keys = {_object_key(source) for source in sources or []}
    generators = {_generator_for_kind(kind)} | set(LEGACY_GENERATORS[kind])
    result = set()
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "FA_GeneratedBy", "") or "") not in generators:
            continue
        if str(getattr(obj, "FA_Role", "") or "") != kind:
            continue
        source = _opening_source(obj, kind)
        if source is None or _object_key(source) not in source_keys:
            continue
        for index in _opening_indices(obj):
            result.add((_object_key(source), index))
    return result


def remove_generated_openings(doc, sources, opening_kind):
    """Remove only objects generated by the current command for these sources."""
    kind = _normalize_kind(opening_kind)
    generators = set(REPLACEABLE_GENERATORS[kind])
    source_keys = {_object_key(source) for source in sources or []}
    opening_names = []
    base_names = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "FA_GeneratedBy", "") or "") not in generators:
            continue
        source = _opening_source(obj, kind)
        if source is None or _object_key(source) not in source_keys:
            continue
        role = str(getattr(obj, "FA_Role", "") or "")
        if role == kind:
            opening_names.append(obj.Name)
            base = getattr(obj, "Base", None)
            if base is not None:
                base_names.append(base.Name)
        elif role == kind + "_base":
            base_names.append(obj.Name)
    for name in opening_names:
        obj = doc.getObject(name)
        if obj is None:
            continue
        try:
            obj.Hosts = []
        except Exception:
            pass
        doc.removeObject(name)
    for name in dict.fromkeys(base_names):
        if doc.getObject(name) is not None:
            doc.removeObject(name)
    return len(opening_names)


def native_door_opening_mode(obj):
    """Return the unique Mode1/Mode2 token used by a native single door."""
    modes = []
    for value in list(getattr(obj, "WindowParts", []) or []):
        if isinstance(value, str):
            modes.extend(re.findall(r"\bMode[12]\b", value))
    unique = list(dict.fromkeys(modes))
    return unique[0] if len(unique) == 1 else ""


def set_native_door_opening_mode(obj, mode):
    """Change only the native swing token of a single-leaf Arch door preset."""
    requested = str(mode or "").strip()
    if requested not in ("Mode1", "Mode2"):
        raise UserFacingError("Modo nativo de puerta invalido: %s" % requested)
    original = list(getattr(obj, "WindowParts", []) or [])
    updated = []
    replacements = 0
    for value in original:
        if isinstance(value, str) and re.search(r"\bMode[12]\b", value):
            new_value, count = re.subn(r"\bMode[12]\b", requested, value)
            updated.append(new_value)
            replacements += count
        else:
            updated.append(value)
    if replacements != 1:
        raise UserFacingError(
            "El preset BIM no tiene un unico componente abatible Mode1/Mode2; no se modifica."
        )
    if updated != original:
        obj.WindowParts = updated
    return replacements


def resolve_door_native_mode(opening_segment, hinge_point, opening_side):
    """Resolve native swing using the physical axis, hinge coordinate and leaf vector."""
    desired = desired_open_leaf_vector(opening_segment, opening_side)
    if desired is None:
        return {"resolved": False, "mode": "", "reason": "bisagra o lado de apertura AUTO"}
    return resolve_native_opening_mode(opening_segment, hinge_point, desired)


def bounded_door_base_adjustment(width_mm, frame_start_mm, frame_end_mm, corner_plan):
    """Plan the Base-only adapter for a BOUNDED native door preset.

    ``FA_ProjectedFirst/Second`` describe the authoritative leaf segment.  The
    native ``Simple door`` preset, however, builds the visible leaf from its
    inner ``Wire1`` and interprets the supplied width as the outer ``Wire0``.
    For a BOUNDED opening there is no longitudinal snap to absorb the two frame
    margins, so the outer Base must grow around the leaf while the public door
    width remains the Sketch length.
    """
    plan = dict(corner_plan or {})
    if str(plan.get("status") or "").strip().upper() != "BOUNDED":
        return None
    if bool(plan.get("applied")):
        return None
    width = float(width_mm)
    frame_start = float(frame_start_mm)
    frame_end = float(frame_end_mm)
    if width <= 0.0 or frame_start < 0.0 or frame_end < 0.0:
        return None
    return {
        "mode": "bounded_leaf_authoritative",
        "origin_shift_mm": -frame_start,
        "outer_width_mm": width + frame_start + frame_end,
        "frame_start_mm": frame_start,
        "frame_end_mm": frame_end,
    }


def _named_sketch_constraint(sketch, name):
    for index, constraint in enumerate(list(getattr(sketch, "Constraints", []) or [])):
        if str(getattr(constraint, "Name", "") or "") == str(name):
            return index, float(getattr(constraint, "Value", 0.0) or 0.0)
    return None, None


def _align_bounded_door_base(obj, unit, authoritative_width_mm, corner_plan):
    """Make native Wire1 coincide with the authoritative BOUNDED leaf axis."""
    base = getattr(obj, "Base", None)
    if base is None:
        return None
    width_index, _current_width = _named_sketch_constraint(base, "Width")
    frame_start_index, frame_start = _named_sketch_constraint(base, "Frame2")
    frame_end_index, frame_end = _named_sketch_constraint(base, "Frame3")
    if None in (width_index, frame_start_index, frame_end_index):
        return None
    adjustment = bounded_door_base_adjustment(
        authoritative_width_mm,
        frame_start,
        frame_end,
        corner_plan,
    )
    if adjustment is None:
        return None
    placement = base.Placement
    placement.Base = FreeCAD.Vector(
        float(placement.Base.x) + float(unit[0]) * adjustment["origin_shift_mm"],
        float(placement.Base.y) + float(unit[1]) * adjustment["origin_shift_mm"],
        float(placement.Base.z),
    )
    base.Placement = placement
    base.setDatum(
        int(width_index),
        FreeCAD.Units.Quantity(float(adjustment["outer_width_mm"]), FreeCAD.Units.Length),
    )
    return adjustment


def _create_native_opening(
    doc,
    target_container,
    source,
    axis,
    match,
    kind,
    height,
    sill,
    generator,
    options=None,
):
    options = dict(options or {})
    wall = match["wall"]
    first = tuple(match["projected_first"])
    second = tuple(match["projected_second"])
    raw_first = first
    raw_second = second
    hinge_endpoint = str(options.get("hinge_endpoint") or "AUTO").strip().upper()
    if kind == "door" and hinge_endpoint == "END":
        first, second = second, first
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    width = math.hypot(dx, dy)
    if width < MIN_OPENING_WIDTH_MM:
        raise UserFacingError("El eje de abertura es demasiado corto para crear un objeto BIM.")
    unit = (dx / width, dy / width)
    normal = (-unit[1], unit[0])
    wall_width = _wall_width(wall)
    wall_base_z = _wall_base_z(wall, match.get("wall_z", 0.0))
    base_z = wall_base_z if kind == "door" else wall_base_z + sill
    origin = FreeCAD.Vector(
        first[0] - normal[0] * wall_width * 0.5,
        first[1] - normal[1] * wall_width * 0.5,
        base_z,
    )
    angle = math.degrees(math.atan2(unit[1], unit[0]))
    rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), angle).multiply(
        FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90)
    )
    placement = FreeCAD.Placement(origin, rotation)
    default_panel_depth = min(40.0, max(10.0, wall_width * 0.5))
    panel_depth = float(options.get("frame_mm") or default_panel_depth)
    panel_depth = min(max(1.0, panel_depth), max(1.0, wall_width))
    preset = str(options.get("preset") or "").strip() or {
        "door": "Simple door",
        "opening": "Opening only",
    }.get(kind, "Open 1-pane" if width < 900.0 else "Sliding 2-pane")
    type_override = ""
    if kind == "door" and not bool(options.get("preset_authoritative", False)):
        type_override = door_preset_override(
            source, int(axis["index"]), presets=native_door_presets()
        )
        if type_override:
            preset = type_override
    if kind == "opening":
        base = _create_opening_only_profile(doc, width, height, placement)
        obj = make_arch_window(
            baseobj=base,
            width=width,
            height=height,
            parts=[],
            name="Opening",
        )
    else:
        obj = make_arch_window_preset(
            preset,
            width=width,
            height=height,
            h1=50.0 if kind == "door" else 60.0,
            h2=50.0 if kind == "door" else 60.0,
            h3=0.0,
            w1=wall_width,
            w2=panel_depth,
            o1=float(options.get("offset_mm") or 0.0),
            o2=(wall_width - panel_depth) * 0.5,
            placement=placement,
        )
    if obj is None:
        raise UserFacingError("Arch no pudo crear el preset BIM %s." % preset)
    base_adjustment = None
    if kind == "door":
        base_adjustment = _align_bounded_door_base(
            obj,
            unit,
            width,
            options.get("corner_snap"),
        )
    index = int(axis["index"])
    visible_kind = {"door": "Puerta", "window": "Ventana", "opening": "Abertura"}[kind]
    obj.Label = "%s BIM - %s - %02d" % (
        visible_kind,
        _object_label(source),
        index + 1,
    )
    obj.IfcType = {"door": "Door", "window": "Window", "opening": "Opening Element"}[kind]
    default_opening = 100.0 if kind == "door" else 0.0
    obj.Opening = int(round(float(options.get("opening_percent", default_opening))))
    obj.SymbolPlan = kind != "opening"
    if hasattr(obj, "SymbolElevation") and kind == "opening":
        obj.SymbolElevation = False
    obj.HoleDepth = 0
    obj.MoveWithHost = True
    obj.Hosts = [wall]
    if kind == "door":
        raw_dx = raw_second[0] - raw_first[0]
        raw_dy = raw_second[1] - raw_first[1]
        raw_len = math.hypot(raw_dx, raw_dy)
        opening_side = str(options.get("opening_side") or "AUTO").strip().upper() or "AUTO"
        if raw_len > 1e-9 and hasattr(obj, "Normal"):
            left_normal = FreeCAD.Vector(-raw_dy / raw_len, raw_dx / raw_len, 0.0)
            if opening_side == "RIGHT":
                left_normal = left_normal.negative()
            if opening_side in ("LEFT", "RIGHT"):
                obj.Normal = left_normal
        hinge_point = raw_second if hinge_endpoint == "END" else raw_first
        mode_plan = resolve_door_native_mode(
            raw_first + raw_second,
            hinge_point,
            opening_side if hinge_endpoint in ("START", "END") else "AUTO",
        )
        if mode_plan.get("resolved"):
            set_native_door_opening_mode(obj, mode_plan["mode"])
            set_prop(obj, "App::PropertyString", "FA_NativeOpeningMode", "FacilArquitectura", "Modo nativo de giro FreeCAD", mode_plan["mode"])
            desired_vector = mode_plan.get("desired_leaf_vector") or (0.0, 0.0)
            set_prop(obj, "App::PropertyVector", "FA_DesiredLeafVector", "FacilArquitectura", "Vector fisico deseado de hoja abierta", FreeCAD.Vector(float(desired_vector[0]), float(desired_vector[1]), 0.0))
        else:
            detected_mode = native_door_opening_mode(obj)
            if detected_mode:
                set_prop(obj, "App::PropertyString", "FA_NativeOpeningMode", "FacilArquitectura", "Modo nativo de giro FreeCAD", detected_mode)
        set_prop(obj, "App::PropertyString", "FA_HingeEndpoint", "FacilArquitectura", "Extremo de bisagra transferible", hinge_endpoint or "AUTO")
        set_prop(obj, "App::PropertyVector", "FA_HingePoint", "FacilArquitectura", "Punto global de bisagra", FreeCAD.Vector(float(hinge_point[0]), float(hinge_point[1]), float(base_z)))
        set_prop(obj, "App::PropertyString", "FA_OpeningSide", "FacilArquitectura", "Lado de apertura respecto al eje", opening_side)
        opens_inward = options.get("opens_inward")
        if opens_inward is not None:
            set_prop(obj, "App::PropertyBool", "FA_OpensInward", "FacilArquitectura", "Abre hacia el recinto", bool(opens_inward))
    _tag_opening(
        obj,
        source,
        index,
        wall,
        kind,
        width,
        height,
        sill if kind in ("window", "opening") else 0.0,
        preset,
        match,
        generator,
    )
    if kind == "door":
        apply_door_corner_metadata(obj, options.get("corner_snap"))
        if base_adjustment:
            set_prop(obj, "App::PropertyString", "FA_BaseAlignmentMode", "FacilArquitectura", "Adaptacion del Base nativo", base_adjustment["mode"])
            set_prop(obj, "App::PropertyLength", "FA_BaseOuterWidth_mm", "FacilArquitectura", "Ancho exterior del Base ArchWindow", base_adjustment["outer_width_mm"])
            set_prop(obj, "App::PropertyLength", "FA_BaseFrameStart_mm", "FacilArquitectura", "Marco previo al segmento de hoja", base_adjustment["frame_start_mm"])
            set_prop(obj, "App::PropertyLength", "FA_BaseFrameEnd_mm", "FacilArquitectura", "Marco posterior al segmento de hoja", base_adjustment["frame_end_mm"])
    element_id = str(options.get("element_id") or "").strip()
    if element_id:
        set_prop(
            obj,
            "App::PropertyString",
            "FA_ElementID",
            "FacilArquitectura",
            "Identificador transferible del elemento",
            element_id,
        )
    if kind == "door" and type_override:
        set_prop(
            obj,
            "App::PropertyBool",
            "FA_TypeOverride",
            "FacilArquitectura",
            "Tipo modificado manualmente",
            True,
        )
        set_prop(
            obj,
            "App::PropertyString",
            "FA_DoorPresetName",
            "FacilArquitectura",
            "Preset BIM nativo actual",
            type_override,
        )
        set_prop(
            obj,
            "App::PropertyString",
            "FA_TypeOverrideSource",
            "FacilArquitectura",
            "Herramienta que fijo el override",
            "FA_ChangeDoorType",
        )
    base = obj.Base
    _tag_opening_base(base, source, index, wall, kind, generator)
    try:
        # The Hosts relation already places the opening under its wall in the
        # FreeCAD tree. Keep only level traceability here; adding obj/base to
        # Level.Group would show the same objects a second time.
        place_hosted_opening_in_tree(target_container, obj, base)
    except Exception:
        pass
    try:
        if kind == "door":
            obj.ViewObject.ShapeColor = (0.72, 0.48, 0.20)
            obj.ViewObject.LineColor = (0.22, 0.12, 0.05)
        else:
            obj.ViewObject.ShapeColor = (0.18, 0.64, 0.88)
            obj.ViewObject.LineColor = (0.03, 0.20, 0.34)
            obj.ViewObject.Transparency = 15
    except Exception:
        pass
    return obj


def create_native_door_from_axis_plan(
    doc,
    target_container,
    source,
    axis,
    match,
    height_mm,
    preset="",
    opening_percent=100.0,
    frame_mm=None,
    offset_mm=None,
    element_id="",
    hinge_endpoint="AUTO",
    opening_side="AUTO",
    opens_inward=None,
):
    """Create one hosted native Arch door from an already validated axis plan.

    ``HingeEndpoint`` is START/END relative to the authoritative Sketch segment.
    ``OpeningSide`` is LEFT/RIGHT relative to that same segment direction.  The
    metadata is persisted so table transfers remain deterministic.
    """
    return _create_native_opening(
        doc,
        target_container,
        source,
        axis,
        match,
        "door",
        float(height_mm),
        0.0,
        GENERATED_BY_DOORS,
        options={
            "preset": preset,
            "opening_percent": opening_percent,
            "frame_mm": frame_mm,
            "offset_mm": offset_mm,
            "element_id": element_id,
            "hinge_endpoint": hinge_endpoint,
            "opening_side": opening_side,
            "opens_inward": opens_inward,
            # The table is the authority for the transferred door type.  The
            # historical per-Sketch FA_DoorTypeOverrides remain active for the
            # regular FA Puertas BIM command, but must not silently replace a
            # type explicitly stored in Spreadsheet_Puertas.
            "preset_authoritative": True,
        },
    )


def create_native_window_from_axis_plan(
    doc,
    target_container,
    source,
    axis,
    match,
    height_mm,
    sill_mm,
    preset="",
    opening_percent=0.0,
    frame_mm=None,
    offset_mm=None,
    element_id="",
):
    """Create one hosted native Arch window from an already validated axis plan.

    This small public adapter lets table-driven workflows reuse the exact host,
    Placement, metadata and tree-residence logic of ``FA Ventanas BIM``.
    """
    return _create_native_opening(
        doc,
        target_container,
        source,
        axis,
        match,
        "window",
        float(height_mm),
        float(sill_mm),
        GENERATED_BY_WINDOWS,
        options={
            "preset": preset,
            "opening_percent": opening_percent,
            "frame_mm": frame_mm,
            "offset_mm": offset_mm,
            "element_id": element_id,
        },
    )


def _create_opening_only_profile(doc, width, height, placement):
    """Create the closed profile used by FreeCAD's native Opening only preset."""
    import Part

    profile = doc.addObject("Part::Feature", "FA_OpeningProfile")
    points = [
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(float(width), 0.0, 0.0),
        FreeCAD.Vector(float(width), float(height), 0.0),
        FreeCAD.Vector(0.0, float(height), 0.0),
        FreeCAD.Vector(0.0, 0.0, 0.0),
    ]
    profile.Shape = Part.makePolygon(points)
    profile.Placement = placement
    profile.Label = "Perfil de abertura BIM"
    try:
        profile.ViewObject.Visibility = False
    except Exception:
        pass
    return profile


def _tag_opening(
    obj,
    source,
    index,
    wall,
    kind,
    width,
    height,
    sill,
    preset,
    match,
    generator,
):
    values = (
        ("App::PropertyString", "FA_GeneratedBy", "Generador", generator),
        ("App::PropertyString", "FA_Role", "Rol", kind),
        ("App::PropertyString", "FA_ElementType", "Tipo de elemento", kind),
        ("App::PropertyLink", "FA_SourceSketch", "Sketch fuente", source),
        ("App::PropertyInteger", "FA_SourceGeometryIndex", "Indice geometrico fuente", index),
        (
            "App::PropertyString",
            "FA_SourceGeometryKey",
            "Clave estable fuente e indice",
            "%s:%d" % (getattr(source, "Name", "Sketch"), index),
        ),
        ("App::PropertyLink", "FA_HostWall", "Muro BIM anfitrion", wall),
        ("App::PropertyLength", "FA_Width_mm", "Ancho derivado del eje", width),
        ("App::PropertyLength", "FA_Height_mm", "Altura BIM", height),
        ("App::PropertyLength", "FA_Sill_mm", "Antepecho", sill),
        ("App::PropertyString", "FA_PresetName", "Preset BIM nativo", preset),
        ("App::PropertyLength", "FA_WallOffset", "Distancia al eje de muro", match["distance"]),
        ("App::PropertyFloat", "FA_HostScore", "Puntuacion del anfitrion", match["score"]),
        (
            "App::PropertyFloat",
            "FA_HostAngleError_deg",
            "Diferencia angular con el muro",
            match["angle_error_deg"],
        ),
        ("App::PropertyLength", "FA_HostOverhang", "Sobrepaso al soporte del muro", match["overhang"]),
    )
    for prop_type, name, description, value in values:
        set_prop(obj, prop_type, name, "FacilArquitectura", description, value)
    if kind == "door":
        set_prop(
            obj,
            "App::PropertyVector",
            "FA_ProjectedFirst",
            "FacilArquitectura",
            "Primera jamba proyectada sobre el host",
            FreeCAD.Vector(*match["projected_first"]),
        )
        set_prop(
            obj,
            "App::PropertyVector",
            "FA_ProjectedSecond",
            "FacilArquitectura",
            "Segunda jamba proyectada sobre el host",
            FreeCAD.Vector(*match["projected_second"]),
        )
        set_prop(
            obj,
            "App::PropertyString",
            "FA_OpenDirection",
            "FacilArquitectura",
            "Direccion de apertura inicial",
            "default",
        )
        set_prop(
            obj,
            "App::PropertyFloat",
            "FA_OpenAngle_deg",
            "FacilArquitectura",
            "Angulo de apertura",
            90.0,
        )


def _tag_opening_base(base, source, index, wall, kind, generator):
    if base is None:
        return
    set_prop(base, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", generator)
    set_prop(base, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", kind + "_base")
    set_prop(base, "App::PropertyLink", "FA_SourceSketch", "FacilArquitectura", "Sketch fuente", source)
    set_prop(
        base,
        "App::PropertyInteger",
        "FA_SourceGeometryIndex",
        "FacilArquitectura",
        "Indice geometrico fuente",
        index,
    )
    set_prop(base, "App::PropertyLink", "FA_HostWall", "FacilArquitectura", "Muro anfitrion", wall)


def _opening_source(obj, kind):
    source = getattr(obj, "FA_SourceSketch", None)
    if source is not None:
        return source
    alias = "FA_SourceDoorAxes" if kind == "door" else "FA_SourceWindowAxes"
    return getattr(obj, alias, None)


def _opening_indices(obj):
    result = set()
    try:
        value = int(getattr(obj, "FA_SourceGeometryIndex", -1))
        if value >= 0:
            result.add(value)
    except Exception:
        pass
    text = str(getattr(obj, "FA_SourceGeometryIndices", "") or "")
    for token in text.replace(";", ",").split(","):
        try:
            value = int(token.strip())
            if value >= 0:
                result.add(value)
        except Exception:
            pass
    return result


def _existing_source_reference_count(doc, source, kind):
    """Count native or legacy openings that authoritatively reference a source."""
    count = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "FA_Role", "") or "").strip().lower() != kind:
            continue
        if _opening_source(obj, kind) is source:
            count += 1
    return count


def _collect_wall_objects(selection):
    result = []
    seen = set()
    pending = list(selection or [])
    while pending:
        obj = pending.pop(0)
        key = _object_key(obj)
        if key in seen:
            continue
        seen.add(key)
        if is_bim_wall(obj):
            result.append(obj)
            continue
        for attr in ("Group", "Objects"):
            try:
                pending.extend(list(getattr(obj, attr, []) or []))
            except Exception:
                pass
    return result


def _is_opening_source(sketch, kind, allow_generic=False):
    """Compatibility wrapper retained for external macros and older tests."""
    return opening_source_assessment(sketch, kind, explicit=allow_generic)[0]


def _is_sketch(obj):
    type_id = str(getattr(obj, "TypeId", "") or "")
    return type_id.startswith("Sketcher::") or (not type_id and hasattr(obj, "Geometry"))


def _wall_width(wall):
    for attr in ("Width", "FA_Thickness_mm", "FA_WallThickness"):
        try:
            value = float(getattr(getattr(wall, attr), "Value", getattr(wall, attr)))
            if value > 0.0:
                return value
        except Exception:
            pass
    source = _linked_object(getattr(wall, "Base", None))
    value = wall_thickness_from_sketch(source) if source is not None else 0.0
    return value if value > 0.0 else 100.0


def _wall_base_z(wall, fallback):
    try:
        box = wall.Shape.BoundBox
        if float(box.ZLength) > 0.0:
            return float(box.ZMin)
    except Exception:
        pass
    return float(fallback)


def _global_placement(obj):
    try:
        return obj.getGlobalPlacement()
    except Exception:
        return getattr(obj, "Placement", FreeCAD.Placement())


def _linked_object(value):
    if isinstance(value, tuple) and value:
        return value[0]
    return value


def _linked_selection_objects(value):
    """Normalize App links and LinkSub values while traversing a selection."""
    if value is None:
        return []
    if isinstance(value, tuple):
        if value and (hasattr(value[0], "TypeId") or hasattr(value[0], "Geometry")):
            return [value[0]]
        result = []
        for item in value:
            result.extend(_linked_selection_objects(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_linked_selection_objects(item))
        return result
    if hasattr(value, "TypeId") or hasattr(value, "Geometry"):
        return [value]
    return []


def _unique_objects(objects):
    result = []
    seen = set()
    for obj in objects or []:
        key = _object_key(obj)
        if key in seen:
            continue
        seen.add(key)
        result.append(obj)
    return result


def _wall_record_key(obj):
    name = str(getattr(obj, "Name", "") or "")
    return name if name else "id:%d" % id(obj)


def _object_key(obj):
    name = str(getattr(obj, "Name", "") or "")
    return ("name", name) if name else ("id", id(obj))


def _object_label(obj):
    return str(getattr(obj, "Label", getattr(obj, "Name", "Object")) or "Object")


def _generator_for_kind(kind):
    return {
        "door": GENERATED_BY_DOORS,
        "window": GENERATED_BY_WINDOWS,
        "opening": GENERATED_BY_OPENINGS,
    }[kind]


def _normalize_kind(value):
    text = str(value or "").strip().lower()
    if text in ("door", "doors", "puerta", "puertas"):
        return "door"
    if text in ("window", "windows", "ventana", "ventanas"):
        return "window"
    if text in ("opening", "openings", "abertura", "aberturas", "vano", "vanos", "buque", "buques"):
        return "opening"
    raise ValueError("opening_kind debe ser door, window u opening")


def _kind_log(kind, message, warning=False):
    """Use the dedicated opening-only console prefix without changing legacy logs."""
    if kind == "opening":
        prefix = "[FACILARQ][ABERTURAS] "
        printer = FreeCAD.Console.PrintWarning if warning else FreeCAD.Console.PrintMessage
        printer(prefix + str(message) + "\n")
    elif warning:
        warn(message)
    else:
        msg(message)


def _segment_values(segment):
    values = tuple(float(value) for value in segment)
    if len(values) == 4:
        return values[0], values[1], 0.0, values[2], values[3], 0.0
    if len(values) != 6:
        raise ValueError("Un segmento debe contener cuatro o seis valores.")
    return values


def _point_values(point):
    if hasattr(point, "x"):
        return float(point.x), float(point.y), float(getattr(point, "z", 0.0))
    values = tuple(float(value) for value in point)
    if len(values) == 2:
        return values[0], values[1], 0.0
    return values[0], values[1], values[2]


def _scalar_on_axis(point, origin, unit):
    values = _point_values(point)
    base = _point_values(origin)
    return (values[0] - base[0]) * unit[0] + (values[1] - base[1]) * unit[1]
