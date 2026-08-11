"""Wall-gap closing helpers for FacilArquitecturaWB.

Descripcion: copia sketches de muros y extiende sus lineas sobre buques detectados.
Fecha: 2026-07-23
Version: 0.2.0
Instrucciones: conservar posicion, orientacion y propiedades BIM del sketch fuente.
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
DEFAULT_MAX_GAP_MM = 3000.0
DEFAULT_ALIGNMENT_TOLERANCE_MM = 5.0
DEFAULT_ANGLE_TOLERANCE_DEG = 2.0
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


def create_closed_wall_sketches(
    doc,
    parent_group,
    wall_sketches,
    opening_sketches,
    max_gap_mm=DEFAULT_MAX_GAP_MM,
    alignment_tolerance_mm=DEFAULT_ALIGNMENT_TOLERANCE_MM,
    angle_tolerance_deg=DEFAULT_ANGLE_TOLERANCE_DEG,
    close_unmarked_gaps=False,
    replace_previous=True,
):
    """Copy wall sketches and close only collinear gaps represented by openings."""
    walls = _unique_sources(wall_sketches)
    if not walls:
        raise UserFacingError("Seleccione al menos un sketch de centros de paredes.")
    openings = [
        sketch
        for sketch in _unique_sources(opening_sketches)
        if sketch not in walls and _is_opening_sketch(sketch)
    ]

    if replace_previous:
        removed = remove_previous_closed_wall_sketches(doc, walls)
        if removed:
            msg("Sketches cerrados anteriores reemplazados: %d" % removed)

    created = []
    total_bridges = 0
    used_openings = set()
    for source in walls:
        records = _geometry_records_from_sketch(source)
        line_records = [record for record in records if record["kind"] == "line"]
        if not line_records:
            warn("Sketch omitido porque no contiene lineas: %s" % _object_label(source))
            continue

        opening_records = _opening_segments_in_target(openings, source)
        adjusted, bridges = bridge_wall_gaps(
            [record["segment"] for record in line_records],
            [record["segment"] for record in opening_records],
            max_gap_mm=float(max_gap_mm),
            alignment_tolerance_mm=float(alignment_tolerance_mm),
            angle_tolerance_deg=float(angle_tolerance_deg),
            allow_unmarked=bool(close_unmarked_gaps),
        )
        for bridge in bridges:
            opening_index = bridge.get("opening_index")
            if opening_index is not None and 0 <= opening_index < len(opening_records):
                used_openings.add(opening_records[opening_index]["source"])

        sketch, constraint_count = _create_wall_sketch_copy(
            doc,
            parent_group,
            source,
            records,
            adjusted,
            bridges,
            opening_records,
            max_gap_mm=float(max_gap_mm),
            alignment_tolerance_mm=float(alignment_tolerance_mm),
            angle_tolerance_deg=float(angle_tolerance_deg),
        )
        created.append(sketch)
        total_bridges += len(bridges)
        msg(
            "Sketch de pared copiado: %s | lineas=%d | huecos_cerrados=%d | restricciones=%d"
            % (sketch.Label, len(line_records), len(bridges), constraint_count)
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
        "closed_gap_count": total_bridges,
        "used_opening_sketch_count": len(used_openings),
    }


def bridge_wall_gaps(
    wall_segments,
    opening_segments,
    max_gap_mm=DEFAULT_MAX_GAP_MM,
    alignment_tolerance_mm=DEFAULT_ALIGNMENT_TOLERANCE_MM,
    angle_tolerance_deg=DEFAULT_ANGLE_TOLERANCE_DEG,
    allow_unmarked=False,
):
    """Extend facing endpoints of collinear wall segments to a shared midpoint."""
    adjusted = [tuple(float(value) for value in segment) for segment in wall_segments]
    openings = [tuple(float(value) for value in segment) for segment in opening_segments]
    candidates = []
    for first_index in range(len(adjusted)):
        for second_index in range(first_index + 1, len(adjusted)):
            candidate = _wall_gap_candidate(
                adjusted[first_index],
                adjusted[second_index],
                first_index,
                second_index,
                max_gap_mm=float(max_gap_mm),
                alignment_tolerance_mm=float(alignment_tolerance_mm),
                angle_tolerance_deg=float(angle_tolerance_deg),
            )
            if candidate is not None:
                candidates.append(candidate)

    matches = []
    if openings:
        for opening_index, opening in enumerate(openings):
            for candidate in candidates:
                score = _opening_match_score(
                    candidate,
                    opening,
                    alignment_tolerance_mm=float(alignment_tolerance_mm),
                    angle_tolerance_deg=float(angle_tolerance_deg),
                )
                if score is not None:
                    matches.append((score, opening_index, candidate))
        matches.sort(key=lambda item: item[0])
    elif allow_unmarked:
        matches = [
            (candidate["gap_length"], None, candidate)
            for candidate in sorted(candidates, key=lambda item: item["gap_length"])
        ]

    bridges = []
    used_opening_indices = set()
    used_endpoints = set()
    used_pairs = set()
    for _score, opening_index, candidate in matches:
        if opening_index is not None and opening_index in used_opening_indices:
            continue
        endpoint_a = (candidate["first_index"], candidate["first_endpoint"])
        endpoint_b = (candidate["second_index"], candidate["second_endpoint"])
        pair = tuple(sorted((candidate["first_index"], candidate["second_index"])))
        if endpoint_a in used_endpoints or endpoint_b in used_endpoints or pair in used_pairs:
            continue

        join_point = candidate["join_point"]
        adjusted[candidate["first_index"]] = _replace_segment_endpoint(
            adjusted[candidate["first_index"]],
            candidate["first_endpoint"],
            join_point,
        )
        adjusted[candidate["second_index"]] = _replace_segment_endpoint(
            adjusted[candidate["second_index"]],
            candidate["second_endpoint"],
            join_point,
        )
        bridge = dict(candidate)
        bridge["opening_index"] = opening_index
        bridges.append(bridge)
        used_endpoints.update((endpoint_a, endpoint_b))
        used_pairs.add(pair)
        if opening_index is not None:
            used_opening_indices.add(opening_index)
    return adjusted, bridges


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
    adjusted_segments,
    bridges,
    opening_records,
    max_gap_mm,
    alignment_tolerance_mm,
    angle_tolerance_deg,
):
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

    line_indices = []
    line_segments = []
    line_cursor = 0
    for record in geometry_records:
        if record["kind"] == "line":
            segment = adjusted_segments[line_cursor]
            geometry = Part.LineSegment(
                FreeCAD.Vector(segment[0], segment[1], 0.0),
                FreeCAD.Vector(segment[2], segment[3], 0.0),
            )
            line_cursor += 1
            line_segments.append(segment)
        else:
            geometry = _clone_geometry(record["geometry"])
        try:
            geometry_index = sketch.addGeometry(geometry, bool(record.get("construction", False)))
        except TypeError:
            geometry_index = sketch.addGeometry(geometry)
            if record.get("construction"):
                try:
                    sketch.toggleConstruction(geometry_index)
                except Exception:
                    pass
        if record["kind"] == "line":
            line_indices.append(int(geometry_index))

    constraint_count = _add_copy_constraints(sketch, line_indices, line_segments)
    _copy_wall_properties(source, sketch)
    opening_sources = []
    for bridge in bridges:
        opening_index = bridge.get("opening_index")
        if opening_index is None or not (0 <= opening_index < len(opening_records)):
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
        "App::PropertyLinkList",
        "FA_SourceOpeningSketches",
        "FacilArquitectura",
        "Sketches de puertas o ventanas que cerraron huecos",
        opening_sources,
    )
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_ClosedGapCount",
        "FacilArquitectura",
        "Cantidad de huecos cerrados",
        len(bridges),
    )
    set_prop(
        sketch,
        "App::PropertyLength",
        "FA_MaxClosingGap",
        "FacilArquitectura",
        "Longitud maxima de hueco permitida",
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
        for record in _geometry_records_from_sketch(opening):
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
    }


def _opening_match_score(candidate, opening, alignment_tolerance_mm, angle_tolerance_deg):
    first = (opening[0], opening[1])
    second = (opening[2], opening[3])
    vector = _subtract(second, first)
    length = math.hypot(vector[0], vector[1])
    if length <= 1e-9:
        return None
    opening_axis = (vector[0] / length, vector[1] / length)
    axis = candidate["axis"]
    opening_angle_tolerance = max(float(angle_tolerance_deg), 5.0)
    if abs(_cross2(axis, opening_axis)) > math.sin(math.radians(opening_angle_tolerance)):
        return None

    midpoint = ((first[0] + second[0]) * 0.5, (first[1] + second[1]) * 0.5)
    offset = abs(_cross2(axis, _subtract(midpoint, candidate["origin"])))
    opening_alignment = max(10.0, float(alignment_tolerance_mm) * 2.0)
    if offset > opening_alignment:
        return None

    projections = [
        _dot2(_subtract(point, candidate["origin"]), axis)
        for point in (first, second)
    ]
    opening_start, opening_end = min(projections), max(projections)
    overlap = max(
        0.0,
        min(candidate["gap_end"], opening_end) - max(candidate["gap_start"], opening_start),
    )
    minimum_overlap = min(candidate["gap_length"], opening_end - opening_start) * 0.5
    if overlap + 1e-6 < minimum_overlap:
        return None
    opening_center = (opening_start + opening_end) * 0.5
    gap_center = (candidate["gap_start"] + candidate["gap_end"]) * 0.5
    if abs(opening_center - gap_center) > max(200.0, candidate["gap_length"] * 0.35):
        return None
    return (
        offset
        + abs(candidate["gap_length"] - (opening_end - opening_start)) * 0.1
        + abs(opening_center - gap_center) * 0.25
    )


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
    if kind in ("walls", "columns"):
        return False
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

    if replace_previous:
        removed = remove_previous_room_sketches(doc)
        if removed:
            msg("Sketches de recintos anteriores reemplazados: %d" % removed)

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
