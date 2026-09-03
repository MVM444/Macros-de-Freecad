"""Centerline extraction helpers for FacilArquitecturaWB.

Descripcion: genera lineas de centro desde shapes importados de distintos sistemas, incluidos Part::Feature con Shape Compound.
Funcion principal: extrae ejes y espesores sin modificar ni explotar destructivamente la geometria fuente.
Mantenimiento: conservar la descomposicion virtual de Compound/CompSolid antes de aplicar heuristicas de eje principal; no convertir el contenedor completo en un unico muro.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-23 11:31 America/Costa_Rica.
Version: 0.22.0.
"""

from __future__ import annotations

import json
import math
import os

import FreeCAD
import Part
import Sketcher

from .command_errors import UserFacingError
from .constants import BUILD_ID, VERSION
from .naming import safe_name
from .project_structure import msg, set_prop, warn


CENTERLINE_SKETCH_PREFIX = "Sketch_Centros"
MAX_SOURCE_DESCRIPTOR_LENGTH = 48
MIN_WALL_LENGTH_MM = 250.0
MIN_WALL_THICKNESS_MM = 20.0
MAX_WALL_THICKNESS_MM = 800.0
DUPLICATE_TOLERANCE_MM = 1.0
ANGLE_TOLERANCE_DEG = 4.0
MIN_OVERLAP_RATIO = 0.35
MIN_UNCOVERED_RATIO = 0.45
COLUMN_MAX_SIZE_MM = 1000.0
COLUMN_MIN_SIZE_MM = 250.0
COLUMN_MAX_ASPECT_RATIO = 1.80
COLUMN_MIN_FILL_RATIO = 0.82
STRUCTURAL_COLUMN_MIN_SIZE_MM = 100.0
CLOSED_TOLERANCE_MM = 2.0
MERGE_ANGLE_TOLERANCE_DEG = 2.0
MERGE_OFFSET_TOLERANCE_MM = 10.0
MERGE_GAP_TOLERANCE_MM = 50.0
THICKNESS_CLUSTER_TOLERANCE_MM = 10.0
DEFAULT_TOPOLOGY_THICKNESS_MM = 150.0
TOPOLOGY_JOIN_MARGIN_MM = 25.0
TOPOLOGY_MIN_JOIN_MM = 75.0
TOPOLOGY_MAX_JOIN_MM = 600.0
TOPOLOGY_COLLINEAR_GAP_FACTOR = 2.0
PARAMETRIC_POINT_TOLERANCE_MM = 1.0
PARAMETRIC_AXIS_TOLERANCE_DEG = 0.25
PROFILE_BOUNDARY_TOLERANCE_MM = 1.0
END_CAP_TOLERANCE_MM = 5.0
COMPLEX_PROFILE_MIN_EDGES = 3
COMPLEX_PROFILE_MIN_ASPECT_RATIO = 1.35
COMPLEX_PROFILE_MAX_DEPTH_MM = 1500.0
OPENING_PROFILE_MIN_ASPECT_RATIO = 1.0
PROFILE_COMPONENT_GAP_MM = 250.0
FRAGMENT_PROFILE_MIN_AXIS_MM = 1.0
FRAGMENT_PROFILE_MAX_GAP_MM = 5.0
BLOCK_RECTANGLE_MIN_FILL_RATIO = 0.70
BLOCK_BOUNDS_MIN_ASPECT_RATIO = 1.35
BLOCK_EDGE_DIRECTION_TOLERANCE_DEG = 10.0
BLOCK_STATION_CLUSTER_TOLERANCE_MM = 5.0
GEOMETRY_SCALE_CANDIDATES = (
    0.001,
    0.01,
    0.1,
    10.0,
    25.4,
    100.0,
    1000.0,
    10000.0,
    100000.0,
    1000000.0,
)
COMMON_WALL_THICKNESSES_MM = (50.0, 75.0, 100.0, 120.0, 125.0, 150.0, 200.0, 250.0, 300.0, 400.0, 600.0)
DOOR_COMPONENT_GAP_MM = 300.0
DOOR_LEAF_MATCH_TOLERANCE_MM = 120.0
OPENING_KEYWORDS = ("ventana", "window", "puerta", "door", "opening", "buque", "vano", "abertura")


def create_centerline_sketch_from_objects(doc, parent_group, objects, extraction_strategy="auto"):
    """Create a new centerline sketch from selected CAD/layer objects."""
    selected_objects = list(objects or [])
    source_labels = _selection_labels(selected_objects)
    prefer_opening_profile = extraction_strategy == "profile_axis" or (
        extraction_strategy == "auto" and _selection_prefers_opening_profile(source_labels)
    )
    prefer_column_profile = extraction_strategy == "auto" and _selection_prefers_column_profile(source_labels)
    source_objects = _collect_leaf_objects(objects)
    if not source_objects:
        raise UserFacingError("No hay objetos utiles en la seleccion.")
    document_source_objects = list(source_objects)
    source_objects = _virtual_edge_sources_for_auto_compounds(
        source_objects,
        extraction_strategy,
    )
    source_ids = [_source_object_id(obj, index) for index, obj in enumerate(source_objects)]
    topology_context = _source_topology_context(source_objects, source_ids)
    topology_edge_records = _topology_edge_records(source_objects, source_ids)
    _augment_topology_context_from_edges(topology_context, topology_edge_records)
    topology_segments = [record["segment"] for record in topology_edge_records]
    closed_profile_count = sum(len(profiles) for profiles in topology_context["profiles_by_source"].values())
    compact_blocker_count = len(topology_context["compact_profiles"])
    if closed_profile_count or compact_blocker_count:
        msg(
            "Perfiles para validar uniones: paredes=%d bloqueadores_compactos=%d"
            % (closed_profile_count, compact_blocker_count)
        )

    scale_diagnostic = {"status": "not_applicable"}
    if _should_validate_geometry_scale(extraction_strategy, prefer_column_profile):
        scale_diagnostic = _geometry_scale_diagnostic(topology_context)
    if scale_diagnostic.get("status") == "invalid":
        warn(
            "Escala geometrica no adecuada: espesor tipico medido=%.9g unidades | "
            "factor sugerido x%.9g | espesor estimado=%.1f mm | perfiles compatibles=%d/%d"
            % (
                scale_diagnostic["measured_thickness"],
                scale_diagnostic["suggested_factor"],
                scale_diagnostic["estimated_thickness_mm"],
                scale_diagnostic["compatible_profile_count"],
                scale_diagnostic["profile_count"],
            )
        )
        diagnostic_path = _write_centerline_geometry_diagnostic(
            source_objects,
            source_ids,
            topology_context,
            scale_diagnostic=scale_diagnostic,
        )
        if diagnostic_path:
            msg("Diagnostico geometrico guardado en: %s" % diagnostic_path)
        raise UserFacingError(
            "La geometria seleccionada no esta en milimetros. Corrija la escala de importacion "
            "o aplique el factor x%.9g antes de crear los centros."
            % scale_diagnostic["suggested_factor"]
        )

    body_records = []
    raw_edge_records = []
    ignored_compact_profiles = 0
    profile_axis_count = 0
    if extraction_strategy == "profile_axis":
        profile_segments, profile_axis_count, ignored_compact_profiles = _profile_centerlines_from_objects(source_objects)
        body_records = [_centerline_record(segment) for segment in profile_segments]
    elif extraction_strategy == "door_swing":
        door_segments, profile_axis_count, ignored_compact_profiles = _door_centerlines_from_objects(source_objects)
        body_records = [_centerline_record(segment) for segment in door_segments]
    else:
        for obj, source_id in zip(source_objects, source_ids):
            obj_body_records, obj_edges, obj_ignored_compact, obj_profile_axis_count = _segments_from_object(
                obj, prefer_opening_profile, source_id=source_id
            )
            body_records.extend(obj_body_records)
            raw_edge_records.extend(_centerline_record(segment, source_ids=(source_id,)) for segment in obj_edges)
            ignored_compact_profiles += obj_ignored_compact
            profile_axis_count += obj_profile_axis_count

    if (
        not body_records
        and not raw_edge_records
        and closed_profile_count
        and extraction_strategy != "door_swing"
    ):
        recovered_records = _centerline_records_from_closed_profiles(
            topology_context,
            prefer_opening_profile=prefer_opening_profile,
        )
        if recovered_records:
            body_records.extend(recovered_records)
            profile_axis_count += len(recovered_records)
            msg(
                "Centros recuperados perfil por perfil desde geometria compuesta o enlazada: %d"
                % len(recovered_records)
            )

    compact_source_ids = set(topology_context.get("compact_source_ids", ()))
    if compact_source_ids:
        raw_edge_records = [
            record
            for record in raw_edge_records
            if not frozenset(record.get("source_ids", ())).issubset(compact_source_ids)
        ]

    raw_edge_count = len(raw_edge_records)
    raw_edge_records = _merge_source_edge_records(
        raw_edge_records,
        topology_context=topology_context,
        topology_segments=topology_segments,
    )
    raw_edges = [record["segment"] for record in raw_edge_records]
    if len(raw_edge_records) < raw_edge_count:
        msg("Bordes fuente duplicados o solapados consolidados: %d -> %d" % (raw_edge_count, len(raw_edge_records)))
    paired_records = _centerline_records_from_parallel_edges(
        raw_edge_records,
        topology_segments=topology_segments,
    )
    if paired_records:
        msg("Centros creados por pares de bordes paralelos: %d" % len(paired_records))
    if profile_axis_count:
        msg("Centros creados desde el eje principal de shapes complejos: %d" % profile_axis_count)
    if ignored_compact_profiles:
        msg("Contornos compactos ambiguos omitidos: %d" % ignored_compact_profiles)
    unmerged_center_count = len(body_records) + len(paired_records)
    records = _dedupe_centerline_records(body_records + paired_records)
    if not records and raw_edges:
        warn("No se encontraron pares de bordes; usando lineas sueltas como respaldo.")
        records = [
            _centerline_record(record["segment"], source_ids=record.get("source_ids"))
            for record in raw_edge_records
        ]

    column_method = "compact_profile"
    column_records = []
    if prefer_column_profile:
        column_records = _column_centerline_records_from_source_profiles(topology_context)
        if column_records:
            column_method = "structural_profile"
    if not column_records:
        column_records = _column_centerline_records(topology_context)

    if not records and not column_records:
        diagnostic_path = _write_centerline_geometry_diagnostic(
            source_objects,
            source_ids,
            topology_context,
            scale_diagnostic=scale_diagnostic,
        )
        if diagnostic_path:
            msg("Diagnostico geometrico guardado en: %s" % diagnostic_path)
        raise UserFacingError("No se detectaron lineas de centro. Seleccione shapes o un layer que contenga geometria util.")

    separate_by_thickness = extraction_strategy == "auto" and any(
        record.get("thickness") is not None for record in records
    )
    if records:
        groups, joined_endpoint_count = _prepare_centerline_groups(
            records,
            separate_by_thickness,
            topology_context=topology_context,
        )
    else:
        groups, joined_endpoint_count = [], 0
    if column_records:
        groups.append({"thickness": None, "kind": "columns", "records": column_records})
        if column_method == "structural_profile":
            msg("Ejes de columnas leidos desde perfiles estructurales: %d" % (len(column_records) // 2))
        else:
            msg("Ejes de columnas compactas restaurados como cruces: %d" % (len(column_records) // 2))
    segments = [record["segment"] for group in groups for record in group["records"]]
    if len(segments) < unmerged_center_count:
        msg("Lineas de centro colineales consolidadas: %d -> %d" % (unmerged_center_count, len(segments)))
    if joined_endpoint_count:
        msg("Extremos llevados a esquinas o intersecciones: %d" % joined_endpoint_count)

    extraction_mode = _extraction_mode(profile_axis_count, bool(paired_records), extraction_strategy)
    _remove_previous_matching_centerlines(
        doc,
        parent_group,
        document_source_objects,
        extraction_strategy,
    )
    sketches = []
    for group_index, group in enumerate(groups):
        thickness = group.get("thickness")
        group_kind = _centerline_kind_for_strategy(
            group.get("kind", "walls"),
            extraction_strategy,
        )
        suffix = "Columnas" if group_kind == "columns" else (_thickness_label_suffix(thickness) if separate_by_thickness else "")
        sketch = _create_centerline_sketch(
            doc,
            parent_group,
            source_labels,
            extraction_mode,
            suffix=suffix,
            thickness=thickness,
            color_index=2 if group_kind == "columns" else group_index,
        )
        group_segments = [record["segment"] for record in group["records"]]
        constraint_count = _populate_parametric_sketch(sketch, group_segments)
        _set_centerline_properties(
            sketch,
            document_source_objects,
            raw_edges,
            ignored_compact_profiles,
            group_segments,
            extraction_strategy,
            thickness,
            constraint_count,
            joined_endpoint_count,
        )
        set_prop(
            sketch,
            "App::PropertyString",
            "FA_CenterlineKind",
            "FacilArquitectura",
            "Tipo de ejes contenido en el sketch",
            group_kind,
        )
        if group_kind == "columns":
            set_prop(
                sketch,
                "App::PropertyString",
                "FA_ElementType",
                "FacilArquitectura",
                "Tipo de elemento representado",
                "Columnas",
            )
        sketches.append(sketch)

    primary_sketch = sketches[0]
    set_prop(
        primary_sketch,
        "App::PropertyLinkList",
        "FA_RelatedCenterlineSketches",
        "FacilArquitectura",
        "Sketches adicionales creados en la misma extraccion",
        sketches[1:],
    )
    msg(
        "Sketches de centros creados: %d | lineas: %d | objetos fuente: %d"
        % (len(sketches), len(segments), len(document_source_objects))
    )
    return primary_sketch, segments


def _selection_labels(objects):
    labels = []
    for obj in objects or []:
        label = str(getattr(obj, "Label", getattr(obj, "Name", "")) or "").strip()
        if label and label not in labels:
            labels.append(label)
    return labels


def _source_descriptor(source_labels):
    if len(source_labels) == 1:
        descriptor = safe_name(source_labels[0], "Seleccion")
    elif source_labels:
        descriptor = "Seleccion_%d_objetos" % len(source_labels)
    else:
        descriptor = "Seleccion"
    return descriptor[:MAX_SOURCE_DESCRIPTOR_LENGTH].rstrip("_") or "Seleccion"


def _selection_prefers_opening_profile(source_labels):
    text = " ".join(str(label).lower() for label in source_labels)
    return any(keyword in text for keyword in OPENING_KEYWORDS)


def _selection_prefers_column_profile(source_labels):
    text = " ".join(str(label).lower() for label in source_labels)
    return any(keyword in text for keyword in ("columna", "column", "pilar"))


def _should_validate_geometry_scale(extraction_strategy, prefer_column_profile=False):
    return extraction_strategy == "auto" and not prefer_column_profile


def _extraction_mode(profile_axis_count, has_parallel_pairs, extraction_strategy="auto"):
    modes = []
    if profile_axis_count:
        modes.append("door_swing" if extraction_strategy == "door_swing" else "profile_axis")
    if has_parallel_pairs:
        modes.append("parallel_edges")
    return "+".join(modes) or "direct_edges"


def _centerline_kind_for_strategy(group_kind, extraction_strategy):
    """Classify specialized opening extractions for downstream room tools."""
    if str(group_kind or "").strip().lower() == "columns":
        return "columns"
    if extraction_strategy == "door_swing":
        return "doors"
    if extraction_strategy == "profile_axis":
        return "windows"
    return "walls"


def _unique_sketch_label(doc, source_labels, suffix=""):
    base_label = "%s_%s" % (CENTERLINE_SKETCH_PREFIX, _source_descriptor(source_labels))
    if suffix:
        base_label += "_" + safe_name(suffix, "Grupo")
    existing_labels = {str(getattr(obj, "Label", "")) for obj in list(getattr(doc, "Objects", []) or [])}
    if base_label not in existing_labels:
        return base_label
    sequence = 2
    while True:
        candidate = "%s_%03d" % (base_label, sequence)
        if candidate not in existing_labels:
            return candidate
        sequence += 1


def _collect_leaf_objects(objects):
    """Traverse selected layers/groups and return objects that may contain geometry."""
    result = []
    pending = list(objects or [])
    seen = set()
    ignored_centerlines = 0
    while pending:
        obj = pending.pop(0)
        name = str(getattr(obj, "Name", ""))
        if not name or name in seen:
            continue
        seen.add(name)

        if _is_generated_centerline_object(obj):
            ignored_centerlines += 1
            continue

        # App::Link forwards properties such as Group from its target. Treating
        # it as a normal container loses the placement of every link instance.
        if _is_link_object(obj):
            shape = getattr(obj, "Shape", None)
            if _shape_has_edges(shape):
                result.append(obj)
            else:
                warn(
                    "Link sin geometria util omitido: %s"
                    % str(getattr(obj, "Label", getattr(obj, "Name", "Link")))
                )
            continue

        container_children = []
        for attr in ("Group", "Objects"):
            try:
                container_children.extend(list(getattr(obj, attr, []) or []))
            except Exception:
                pass
        if container_children:
            pending.extend(container_children)
            continue

        try:
            pending.extend(list(getattr(obj, "OutList", []) or []))
        except Exception:
            pass

        if _shape_has_edges(getattr(obj, "Shape", None)):
            result.append(obj)
    if ignored_centerlines:
        warn("Sketches de centros omitidos como fuente para evitar una extraccion recursiva: %d" % ignored_centerlines)
    return result


class _VirtualEdgeShape:
    """Minimal in-memory shape wrapper equivalent to one Draft split edge."""

    ShapeType = "Edge"

    def __init__(self, edge):
        self.Edges = [edge]
        self.Wires = []
        self.BoundBox = getattr(edge, "BoundBox", None)


class _VirtualEdgeSource:
    """Expose one Compound edge without creating an object in the document tree."""

    def __init__(self, source, edge, index):
        self._source = source
        source_name = str(getattr(source, "Name", "Compound") or "Compound")
        self.Name = "%s__edge_%04d" % (source_name, int(index))
        self.Label = str(getattr(source, "Label", source_name) or source_name)
        self.TypeId = "Part::Feature"
        self.Shape = _VirtualEdgeShape(edge)

    def __getattr__(self, name):
        return getattr(self._source, name)


def _virtual_edge_sources_for_auto_compounds(source_objects, extraction_strategy):
    """Virtually reproduce Draft ``splitWires`` for plain Part::Feature Compounds.

    The stable reference path for reconstructed wall networks is one source object
    per edge.  Keeping every Compound child Wire intact lets the complex-profile
    heuristic invent axes and also assigns one source id to unrelated walls and a
    compact column.  Edge proxies give the existing topology, pairing, compact
    profile and thickness logic the same inputs as the user's successful manual
    Downgrade/Explode workflow, while leaving the document tree untouched.

    Specialized door/window strategies, App::Link instances, non-Compound shapes
    and derived Part feature types retain their previous paths.
    """
    if extraction_strategy != "auto":
        return list(source_objects or [])

    result = []
    for obj in source_objects or []:
        shape = getattr(obj, "Shape", None)
        type_id = str(getattr(obj, "TypeId", "") or "")
        if (
            _is_link_object(obj)
            or type_id != "Part::Feature"
            or _shape_type_name(shape) != "Compound"
        ):
            result.append(obj)
            continue

        try:
            edges = list(getattr(shape, "Edges", []) or [])
        except Exception:
            edges = []
        if not edges:
            result.append(obj)
            continue

        result.extend(
            _VirtualEdgeSource(obj, edge, index)
            for index, edge in enumerate(edges, start=1)
        )
        msg(
            "Compound descompuesto virtualmente como bordes: %s | bordes=%d | fuente intacta"
            % (
                str(getattr(obj, "Label", getattr(obj, "Name", "Objeto"))),
                len(edges),
            )
        )
    return result


def _is_link_object(obj):
    type_id = str(getattr(obj, "TypeId", "") or "")
    return type_id == "App::Link" or type_id.startswith("App::Link")


def _shape_has_edges(shape):
    if shape is None:
        return False
    try:
        if hasattr(shape, "isNull") and shape.isNull():
            return False
        return bool(list(getattr(shape, "Edges", []) or []))
    except Exception:
        return False


def _is_generated_centerline_object(obj):
    role = str(getattr(obj, "FA_Role", "") or "").strip().lower()
    label = str(getattr(obj, "Label", getattr(obj, "Name", "")) or "").strip()
    return role == "centerlines" or label.startswith(CENTERLINE_SKETCH_PREFIX)


def _source_object_id(obj, index):
    name = str(getattr(obj, "Name", "") or "").strip()
    return name or "source_%d" % int(index)


def _source_object_names(objects):
    return sorted(
        str(getattr(obj, "Name", "") or "").strip()
        for obj in objects or []
        if str(getattr(obj, "Name", "") or "").strip()
    )


def _remove_previous_matching_centerlines(doc, parent_group, source_objects, extraction_strategy):
    """Replace only FA outputs previously generated from the exact same sources."""
    source_names = _source_object_names(source_objects)
    if not source_names or doc is None or not hasattr(doc, "removeObject"):
        return 0

    try:
        candidates = list(getattr(parent_group, "Group", []) or [])
    except Exception:
        candidates = []
    matches = []
    for obj in candidates:
        role = str(getattr(obj, "FA_Role", "") or "").strip().lower()
        strategy = str(getattr(obj, "FA_ExtractionStrategy", "") or "").strip()
        stored_names = sorted(
            str(value or "").strip()
            for value in list(getattr(obj, "FA_SourceObjectNames", []) or [])
            if str(value or "").strip()
        )
        if role == "centerlines" and strategy == str(extraction_strategy) and stored_names == source_names:
            matches.append(obj)

    for obj in reversed(matches):
        doc.removeObject(obj.Name)
    if matches:
        msg("Sketches FA previos reemplazados para la misma fuente: %d" % len(matches))
    return len(matches)


def _write_centerline_geometry_diagnostic(
    source_objects,
    source_ids,
    topology_context,
    scale_diagnostic=None,
):
    """Write representative source geometry so unsupported DXF blocks can be inspected."""
    try:
        base_dir = str(FreeCAD.getUserAppDataDir())
    except Exception:
        base_dir = os.getcwd()
    path = os.path.join(base_dir, "FacilArquitectura_DiagnosticoCentros.json")
    try:
        objects = [
            _source_object_geometry_diagnostic(obj, source_id)
            for obj, source_id in list(zip(source_objects, source_ids))[:3]
        ]
        profiles_by_source = (topology_context or {}).get("profiles_by_source", {})
        data = {
            "workbench_version": VERSION,
            "build_id": BUILD_ID,
            "units_expected": "mm",
            "source_object_count": len(source_objects),
            "profile_count": sum(len(profiles) for profiles in profiles_by_source.values()),
            "scale_diagnostic": scale_diagnostic or {},
            "thresholds": {
                "minimum_wall_length_mm": MIN_WALL_LENGTH_MM,
                "minimum_wall_thickness_mm": MIN_WALL_THICKNESS_MM,
                "maximum_wall_thickness_mm": MAX_WALL_THICKNESS_MM,
            },
            "objects": objects,
            "profiles": {
                source_id: [
                    _polygon_geometry_diagnostic(polygon)
                    for polygon in profiles_by_source.get(source_id, [])
                ]
                for source_id in source_ids[:3]
            },
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        if objects:
            sample = objects[0]
            bbox = sample.get("bounding_box", {})
            lengths = sample.get("edge_length_summary", {})
            msg(
                "Muestra diagnostica: %s | bbox=(%.6g, %.6g, %.6g) | "
                "bordes=%d wires=%d | largo_borde min=%.6g max=%.6g"
                % (
                    sample.get("label", sample.get("name", "Objeto")),
                    float(bbox.get("x_length", 0.0)),
                    float(bbox.get("y_length", 0.0)),
                    float(bbox.get("z_length", 0.0)),
                    int(sample.get("edge_count", 0)),
                    int(sample.get("wire_count", 0)),
                    float(lengths.get("minimum", 0.0)),
                    float(lengths.get("maximum", 0.0)),
                )
            )
        return path
    except Exception as exc:
        warn("No se pudo escribir el diagnostico geometrico: %s" % exc)
        return None


def _source_object_geometry_diagnostic(obj, source_id):
    shape = getattr(obj, "Shape", None)
    try:
        edges = list(getattr(shape, "Edges", []) or [])
    except Exception:
        edges = []
    try:
        wires = list(getattr(shape, "Wires", []) or [])
    except Exception:
        wires = []
    try:
        vertices = list(getattr(shape, "Vertexes", []) or [])
    except Exception:
        vertices = []
    edge_lengths = []
    edge_data = []
    for index, edge in enumerate(edges):
        try:
            length = float(edge.Length)
        except Exception:
            segment = _segment_from_edge(edge, min_length=0.0)
            length = _segment_length(segment) if segment is not None else 0.0
        edge_lengths.append(length)
        if index < 100:
            segment = _segment_from_edge(edge, min_length=0.0)
            edge_data.append(
                {
                    "index": index,
                    "length": length,
                    "curve_type": type(getattr(edge, "Curve", None)).__name__,
                    "segment_xy": list(segment) if segment is not None else None,
                }
            )
    linked = getattr(obj, "LinkedObject", None) if _is_link_object(obj) else None
    return {
        "source_id": source_id,
        "name": str(getattr(obj, "Name", "")),
        "label": str(getattr(obj, "Label", "")),
        "type_id": str(getattr(obj, "TypeId", "")),
        "linked_object": {
            "name": str(getattr(linked, "Name", "")),
            "label": str(getattr(linked, "Label", "")),
            "type_id": str(getattr(linked, "TypeId", "")),
            "children": _linked_shape_children_diagnostic(linked),
        }
        if linked is not None
        else None,
        "link_transform": bool(getattr(obj, "LinkTransform", False)) if _is_link_object(obj) else None,
        "scale": float(getattr(obj, "Scale", 1.0)) if _is_link_object(obj) else None,
        "placement": _placement_diagnostic(getattr(obj, "Placement", None)),
        "link_placement": _placement_diagnostic(getattr(obj, "LinkPlacement", None))
        if _is_link_object(obj)
        else None,
        "bounding_box": _shape_bounding_box_diagnostic(shape),
        "edge_count": len(edges),
        "wire_count": len(wires),
        "vertex_count": len(vertices),
        "edge_length_summary": {
            "minimum": min(edge_lengths) if edge_lengths else 0.0,
            "maximum": max(edge_lengths) if edge_lengths else 0.0,
            "average": sum(edge_lengths) / len(edge_lengths) if edge_lengths else 0.0,
        },
        "edges": edge_data,
        "wires": [
            {
                "index": index,
                "edge_count": len(list(getattr(wire, "Edges", []) or [])),
                "vertex_count": len(list(getattr(wire, "Vertexes", []) or [])),
                "is_closed": _wire_is_closed(
                    wire,
                    _segments_from_edges(getattr(wire, "Edges", []) or [], min_length=0.0),
                ),
            }
            for index, wire in enumerate(wires[:20])
        ],
    }


def _linked_shape_children_diagnostic(linked):
    if linked is None:
        return []
    try:
        children = list(getattr(linked, "Group", []) or [])
    except Exception:
        children = []
    if not children:
        try:
            children = list(getattr(linked, "OutList", []) or [])
        except Exception:
            children = []
    result = []
    seen = set()
    for child in children:
        name = str(getattr(child, "Name", "") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        shape = getattr(child, "Shape", None)
        try:
            edge_count = len(list(getattr(shape, "Edges", []) or []))
        except Exception:
            edge_count = 0
        try:
            wire_count = len(list(getattr(shape, "Wires", []) or []))
        except Exception:
            wire_count = 0
        result.append(
            {
                "name": name,
                "label": str(getattr(child, "Label", "")),
                "type_id": str(getattr(child, "TypeId", "")),
                "edge_count": edge_count,
                "wire_count": wire_count,
                "bounding_box": _shape_bounding_box_diagnostic(shape),
                "placement": _placement_diagnostic(getattr(child, "Placement", None)),
            }
        )
        if len(result) >= 20:
            break
    return result


def _placement_diagnostic(placement):
    if placement is None:
        return None
    try:
        base = placement.Base
        position = [float(base.x), float(base.y), float(base.z)]
    except Exception:
        position = []
    try:
        quaternion = [float(value) for value in placement.Rotation.Q]
    except Exception:
        quaternion = []
    return {
        "position": position,
        "quaternion_xyzw": quaternion,
    }


def _shape_bounding_box_diagnostic(shape):
    bbox = getattr(shape, "BoundBox", None)
    if bbox is None:
        return {}
    result = {}
    for source_name, target_name in (
        ("XMin", "x_min"),
        ("YMin", "y_min"),
        ("ZMin", "z_min"),
        ("XMax", "x_max"),
        ("YMax", "y_max"),
        ("ZMax", "z_max"),
        ("XLength", "x_length"),
        ("YLength", "y_length"),
        ("ZLength", "z_length"),
    ):
        try:
            result[target_name] = float(getattr(bbox, source_name))
        except Exception:
            result[target_name] = 0.0
    return result


def _polygon_geometry_diagnostic(polygon):
    metrics = _oriented_polygon_metrics(polygon)
    xs = [float(point[0]) for point in polygon] if polygon else []
    ys = [float(point[1]) for point in polygon] if polygon else []
    return {
        "point_count": len(polygon),
        "area": _polygon_area(polygon),
        "bounds_xy": {
            "x_min": min(xs) if xs else 0.0,
            "x_max": max(xs) if xs else 0.0,
            "y_min": min(ys) if ys else 0.0,
            "y_max": max(ys) if ys else 0.0,
        },
        "metrics": {
            "short_len": float(metrics["short_len"]),
            "long_len": float(metrics["long_len"]),
            "fill_ratio": float(metrics["fill_ratio"]),
            "u": list(metrics["u"]),
            "n": list(metrics["n"]),
        }
        if metrics is not None
        else None,
        "points_xy": [[float(point[0]), float(point[1])] for point in polygon[:200]],
    }


def _source_topology_context(source_objects, source_ids):
    profiles_by_source = {}
    compact_profiles = []
    compact_source_ids = set()
    for obj, source_id in zip(source_objects, source_ids):
        shape = getattr(obj, "Shape", None)
        polygons = _closed_profile_polygons(shape)
        for polygon in polygons:
            if _polygon_is_compact_profile(polygon):
                compact_profiles.append(polygon)
                compact_source_ids.add(source_id)
            else:
                profiles_by_source.setdefault(source_id, []).append(polygon)
    return {
        "profiles_by_source": profiles_by_source,
        "compact_profiles": compact_profiles,
        "compact_source_ids": compact_source_ids,
    }


def _geometry_scale_diagnostic(topology_context):
    """Detect an unambiguous unit mismatch without changing source geometry."""
    samples = []
    profiles_by_source = (topology_context or {}).get("profiles_by_source", {})
    for polygons in profiles_by_source.values():
        for polygon in polygons:
            metrics = _oriented_polygon_metrics(polygon)
            if metrics is None or metrics["fill_ratio"] < BLOCK_RECTANGLE_MIN_FILL_RATIO:
                continue
            short_len = float(metrics["short_len"])
            long_len = float(metrics["long_len"])
            if short_len <= 1e-12 or long_len / short_len < COMPLEX_PROFILE_MIN_ASPECT_RATIO:
                continue
            samples.append((short_len, long_len))

    if not samples:
        return {"status": "unknown", "profile_count": 0}

    current_count = _plausible_scaled_profile_count(samples, 1.0)
    if current_count:
        return {
            "status": "ok",
            "profile_count": len(samples),
            "compatible_profile_count": current_count,
            "suggested_factor": 1.0,
        }

    candidates = []
    for factor in GEOMETRY_SCALE_CANDIDATES:
        compatible = [
            (short_len * factor, long_len * factor)
            for short_len, long_len in samples
            if _scaled_profile_is_plausible(short_len, long_len, factor)
        ]
        if not compatible:
            continue
        thickness_penalty = sum(
            min(abs(thickness - common) for common in COMMON_WALL_THICKNESSES_MM)
            for thickness, _length in compatible
        ) / len(compatible)
        candidates.append(
            {
                "factor": factor,
                "compatible": compatible,
                "count": len(compatible),
                "penalty": thickness_penalty,
            }
        )

    minimum_count = max(1, int(math.ceil(len(samples) * 0.5)))
    viable = [candidate for candidate in candidates if candidate["count"] >= minimum_count]
    if not viable:
        return {
            "status": "unknown",
            "profile_count": len(samples),
            "compatible_profile_count": 0,
        }

    best = min(viable, key=lambda candidate: (-candidate["count"], candidate["penalty"]))
    measured = sorted(short_len for short_len, _long_len in samples)
    estimated = sorted(thickness for thickness, _length in best["compatible"])
    return {
        "status": "invalid",
        "profile_count": len(samples),
        "compatible_profile_count": best["count"],
        "measured_thickness": _median(measured),
        "suggested_factor": float(best["factor"]),
        "estimated_thickness_mm": _median(estimated),
    }


def _plausible_scaled_profile_count(samples, factor):
    return sum(
        1
        for short_len, long_len in samples
        if _scaled_profile_is_plausible(short_len, long_len, factor)
    )


def _scaled_profile_is_plausible(short_len, long_len, factor):
    thickness = float(short_len) * float(factor)
    length = float(long_len) * float(factor)
    return (
        MIN_WALL_THICKNESS_MM <= thickness <= MAX_WALL_THICKNESS_MM
        and length >= MIN_WALL_LENGTH_MM
    )


def _median(values):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _topology_edge_records(source_objects, source_ids):
    records = []
    for obj, source_id in zip(source_objects, source_ids):
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        try:
            edges = list(getattr(shape, "Edges", []) or [])
        except Exception:
            edges = []
        for segment in _segments_from_edges(edges, min_length=1.0):
            records.append(_centerline_record(segment, source_ids=(source_id,)))
    return records


def _augment_topology_context_from_edges(topology_context, edge_records):
    """Recover closed profiles when a DXF imported every boundary edge as a separate Shape."""
    existing_keys = {
        _polygon_key(polygon)
        for profiles in topology_context.get("profiles_by_source", {}).values()
        for polygon in profiles
    }
    existing_keys.update(_polygon_key(polygon) for polygon in topology_context.get("compact_profiles", []))
    for component in _edge_record_components(edge_records):
        segments = [record["segment"] for record in component]
        if not _segments_form_closed_loop(segments):
            continue
        polygon = _ordered_polygon_from_segments(segments)
        if not polygon:
            continue
        polygon_key = _polygon_key(polygon)
        if polygon_key in existing_keys:
            continue
        existing_keys.add(polygon_key)
        if _polygon_is_compact_profile(polygon):
            topology_context.setdefault("compact_profiles", []).append(polygon)
            for record in component:
                topology_context.setdefault("compact_source_ids", set()).update(record.get("source_ids", ()))
            continue
        source_ids = set()
        for record in component:
            source_ids.update(record.get("source_ids", ()))
        for source_id in source_ids:
            topology_context.setdefault("profiles_by_source", {}).setdefault(source_id, []).append(polygon)


def _edge_record_components(edge_records):
    if not edge_records:
        return []
    parent = list(range(len(edge_records)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first, second):
        first_root = find(first)
        second_root = find(second)
        if first_root != second_root:
            parent[second_root] = first_root

    endpoints = [
        ((record["segment"][0], record["segment"][1]), (record["segment"][2], record["segment"][3]))
        for record in edge_records
    ]
    for first_index, first_endpoints in enumerate(endpoints):
        for second_index in range(first_index + 1, len(endpoints)):
            if any(
                _point_distance(first, second) <= CLOSED_TOLERANCE_MM
                for first in first_endpoints
                for second in endpoints[second_index]
            ):
                union(first_index, second_index)
    grouped = {}
    for index, record in enumerate(edge_records):
        grouped.setdefault(find(index), []).append(record)
    return list(grouped.values())


def _polygon_key(polygon):
    points = sorted((_closed_key(point[0]), _closed_key(point[1])) for point in polygon)
    return tuple(points)


def _column_centerline_records(topology_context):
    records = []
    seen = set()
    for polygon in topology_context.get("compact_profiles", []):
        polygon_key = _polygon_key(polygon)
        if polygon_key in seen:
            continue
        seen.add(polygon_key)
        crosses = _column_cross_segments(polygon)
        records.extend(_centerline_record(segment) for segment in crosses)
    return records


def _column_centerline_records_from_source_profiles(topology_context):
    """Create one cross per linked column from its central structural section."""
    records = []
    profiles_by_source = (topology_context or {}).get("profiles_by_source", {})
    for source_id, polygons in profiles_by_source.items():
        candidates = []
        for polygon in polygons:
            metrics = _oriented_polygon_metrics(polygon)
            if metrics is None:
                continue
            short_len = float(metrics["short_len"])
            long_len = float(metrics["long_len"])
            if (
                short_len < STRUCTURAL_COLUMN_MIN_SIZE_MM
                or long_len > COLUMN_MAX_SIZE_MM
                or long_len / max(short_len, 1e-9) > COLUMN_MAX_ASPECT_RATIO
            ):
                continue
            candidates.append((long_len, abs(long_len - short_len), -_polygon_area(polygon), polygon))
        if not candidates:
            continue
        _long_len, _aspect_delta, _negative_area, polygon = min(candidates, key=lambda item: item[:3])
        records.extend(
            _centerline_record(segment, source_ids=(source_id,))
            for segment in _column_cross_segments(polygon)
        )
    return _dedupe_centerline_records(records)


def _column_cross_segments(polygon):
    if len(polygon) < 3:
        return []
    edges = []
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        length = _point_distance(first, second)
        if length > 1e-9:
            edges.append((length, first, second))
    if not edges:
        return []
    _length, first, second = max(edges, key=lambda item: item[0])
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    axis_length = math.hypot(dx, dy)
    u = (dx / axis_length, dy / axis_length)
    n = (-u[1], u[0])
    along = [_dot(point, u) for point in polygon]
    across = [_dot(point, n) for point in polygon]
    along_min, along_max = min(along), max(along)
    across_min, across_max = min(across), max(across)
    along_center = (along_min + along_max) / 2.0
    across_center = (across_min + across_max) / 2.0
    return [
        (
            u[0] * along_min + n[0] * across_center,
            u[1] * along_min + n[1] * across_center,
            u[0] * along_max + n[0] * across_center,
            u[1] * along_max + n[1] * across_center,
        ),
        (
            u[0] * along_center + n[0] * across_min,
            u[1] * along_center + n[1] * across_min,
            u[0] * along_center + n[0] * across_max,
            u[1] * along_center + n[1] * across_max,
        ),
    ]


def _closed_profile_polygons(shape):
    if shape is None:
        return []
    try:
        wires = list(getattr(shape, "Wires", []) or [])
    except Exception:
        wires = []
    polygons = []
    for wire in wires:
        polygon = _wire_polygon_points(wire)
        if polygon:
            polygons.append(polygon)
    if polygons:
        return polygons

    try:
        segments = _segments_from_edges(getattr(shape, "Edges", []) or [], min_length=1.0)
    except Exception:
        segments = []
    if _segments_form_closed_loop(segments):
        polygon = _ordered_polygon_from_segments(segments)
        if polygon:
            polygons.append(polygon)
    return polygons


def _centerline_records_from_closed_profiles(topology_context, prefer_opening_profile=False):
    """Recover axes when a compound link contains many independent closed profiles."""
    records = []
    fragment_records = []
    aggregate_count = 0
    profile_count = 0
    provisional_axis_count = 0
    paired_profile_count = 0
    concentric_pair_count = 0
    block_profile_pair_count = 0
    bounding_rectangle_pair_count = 0
    rectangular_profile_count = 0
    concentric_axis_count = 0
    no_axis_count = 0
    non_wall_depth_count = 0
    profiles_by_source = (topology_context or {}).get("profiles_by_source", {})
    for source_id, polygons in profiles_by_source.items():
        profile_count += len(polygons)
        (
            concentric_records,
            nested_pairs,
            block_pairs,
            bounding_pairs,
            rectangular_profiles,
        ) = _centerline_records_from_concentric_profiles(
            polygons,
            source_id,
        )
        concentric_pair_count += nested_pairs
        block_profile_pair_count += block_pairs
        bounding_rectangle_pair_count += bounding_pairs
        rectangular_profile_count += rectangular_profiles
        concentric_axis_count += len(concentric_records)
        if concentric_records:
            records.extend(concentric_records)
            continue

        source_records = []
        source_fragments = []
        source_profile_axes = []
        source_segments = []
        for polygon in polygons:
            segments = [
                (
                    float(first[0]),
                    float(first[1]),
                    float(second[0]),
                    float(second[1]),
                )
                for first, second in zip(polygon, polygon[1:] + polygon[:1])
                if _point_distance(first, second) > 1e-9
            ]
            source_segments.extend(segments)
            profile_axis = _centerline_from_segments(
                segments,
                prefer_opening_profile=prefer_opening_profile,
                minimum_edges=COMPLEX_PROFILE_MIN_EDGES,
                minimum_axis_length=FRAGMENT_PROFILE_MIN_AXIS_MM,
            )
            if profile_axis is None:
                no_axis_count += 1
                continue

            provisional_axis_count += 1
            profile_depth = _profile_depth_from_segments(segments, profile_axis)
            source_profile_axes.append(
                {
                    "segment": profile_axis,
                    "profile_depth": profile_depth,
                    "source_ids": frozenset((source_id,)),
                }
            )
            thickness = _valid_wall_thickness(profile_depth)
            if thickness is None:
                non_wall_depth_count += 1
            if _segment_length(profile_axis) >= MIN_WALL_LENGTH_MM:
                source_records.append(
                    _centerline_record(
                        profile_axis,
                        thickness,
                        source_ids=(source_id,),
                        closed_endpoints=(1, 2),
                    )
                )
                continue
            if thickness is not None:
                source_fragments.append(
                    _centerline_record(
                        profile_axis,
                        thickness,
                        source_ids=(source_id,),
                    )
                )

        paired_records = _centerline_records_from_profile_pairs(source_profile_axes)
        if paired_records:
            paired_profile_count += len(paired_records)
            for record in paired_records:
                if _segment_length(record["segment"]) >= MIN_WALL_LENGTH_MM:
                    records.append(record)
                else:
                    fragment_records.append(record)
            continue

        if source_records:
            records.extend(source_records)
            continue

        connected_components = _group_segments_by_proximity(
            source_segments,
            FRAGMENT_PROFILE_MAX_GAP_MM,
        )
        aggregate_axis = None
        if len(polygons) > 1 and len(connected_components) == 1:
            aggregate_axis = _centerline_from_segments(
                source_segments,
                prefer_opening_profile=prefer_opening_profile,
                minimum_edges=COMPLEX_PROFILE_MIN_EDGES,
            )
        if aggregate_axis is not None:
            records.append(
                _centerline_record(
                    aggregate_axis,
                    _profile_thickness_from_segments(source_segments, aggregate_axis),
                    source_ids=(source_id,),
                    closed_endpoints=(1, 2),
                )
            )
            aggregate_count += 1
            continue
        fragment_records.extend(source_fragments)

    merged_fragments = _merge_fragment_centerline_records(fragment_records)
    records.extend(merged_fragments)
    msg(
        "Analisis perfiles cerrados: total=%d fuentes=%d max_por_fuente=%d "
        "rectangulares=%d concentricos=%d pares_bloque=%d pares_bbox=%d ejes_contorno=%d "
        "ejes=%d pares_capas=%d compuestos=%d fragmentos=%d consolidados=%d "
        "sin_eje=%d espesor_fuera_rango=%d"
        % (
            profile_count,
            len(profiles_by_source),
            max((len(polygons) for polygons in profiles_by_source.values()), default=0),
            rectangular_profile_count,
            concentric_pair_count,
            block_profile_pair_count,
            bounding_rectangle_pair_count,
            concentric_axis_count,
            provisional_axis_count,
            paired_profile_count,
            aggregate_count,
            len(fragment_records),
            len(merged_fragments),
            no_axis_count,
            non_wall_depth_count,
        )
    )
    return _dedupe_centerline_records(records)


def _centerline_records_from_concentric_profiles(polygons, source_id):
    """Create perimeter centerlines between nested outer and inner contours."""
    if len(polygons) < 2:
        return [], 0, 0, 0, 0

    profile_data = []
    for polygon_index, polygon in enumerate(polygons):
        segments = _merge_profile_boundary_segments(
            [
                (
                    float(first[0]),
                    float(first[1]),
                    float(second[0]),
                    float(second[1]),
                )
                for first, second in zip(polygon, polygon[1:] + polygon[:1])
                if _point_distance(first, second) > 1e-9
            ]
        )
        if len(segments) < COMPLEX_PROFILE_MIN_EDGES:
            continue
        metrics = _oriented_polygon_metrics(polygon)
        rectangle_segments = []
        if metrics is not None and metrics["fill_ratio"] >= BLOCK_RECTANGLE_MIN_FILL_RATIO:
            rectangle_segments = _oriented_rectangle_segments(metrics)
        profile_data.append(
            {
                "index": polygon_index,
                "polygon": polygon,
                "segments": segments,
                "area": _polygon_area(polygon),
                "reference_point": _polygon_mean_point(polygon),
                "rectangle_segments": rectangle_segments,
            }
        )
    rectangular_profile_count = sum(bool(profile["rectangle_segments"]) for profile in profile_data)

    nested_pairs = []
    for inner in profile_data:
        containers = [
            outer
            for outer in profile_data
            if outer["area"] > inner["area"] + 1e-6
            and _point_in_polygon(
                inner["reference_point"],
                outer["polygon"],
                include_boundary=False,
            )
        ]
        if containers:
            nested_pairs.append((min(containers, key=lambda item: item["area"]), inner))

    records = []
    valid_pair_count = 0
    for outer, inner in nested_pairs:
        topology_segments = outer["segments"] + inner["segments"]
        outer_infos = [
            info
            for index, segment in enumerate(outer["segments"])
            for info in (
                _edge_info_with_min_length(
                    segment,
                    FRAGMENT_PROFILE_MIN_AXIS_MM,
                    index=index,
                ),
            )
            if info is not None
        ]
        inner_infos = [
            info
            for index, segment in enumerate(inner["segments"])
            for info in (
                _edge_info_with_min_length(
                    segment,
                    FRAGMENT_PROFILE_MIN_AXIS_MM,
                    index=index,
                ),
            )
            if info is not None
        ]
        candidates = []
        for outer_index, outer_info in enumerate(outer_infos):
            outer_info["source_ids"] = frozenset((source_id,))
            for inner_index, inner_info in enumerate(inner_infos):
                inner_info["source_ids"] = frozenset((source_id,))
                candidate = _pair_candidate(
                    outer_info,
                    inner_info,
                    topology_segments=topology_segments,
                )
                if candidate is not None:
                    candidate["segment"] = _concentric_pair_segment(
                        outer_info,
                        inner_info,
                        candidate["thickness"],
                    )
                    candidate["closed_endpoints"] = frozenset()
                    candidates.append((candidate["score"], outer_index, inner_index, candidate))

        pair_records = []
        used_outer = set()
        used_inner = set()
        for _score, outer_index, inner_index, candidate in sorted(candidates, key=lambda item: item[0]):
            if outer_index in used_outer or inner_index in used_inner:
                continue
            pair_records.append(
                _centerline_record(
                    candidate["segment"],
                    candidate["thickness"],
                    source_ids=(source_id,),
                    closed_endpoints=candidate.get("closed_endpoints"),
                )
            )
            used_outer.add(outer_index)
            used_inner.add(inner_index)
        if pair_records:
            records.extend(pair_records)
            valid_pair_count += 1
    if records:
        return _dedupe_centerline_records(records), valid_pair_count, 0, 0, rectangular_profile_count

    # Some CAD blocks contain two nearly concentric rectangles that overlap or
    # are slightly displaced, so strict polygon containment is not reliable.
    block_candidates = []
    for first_index, first in enumerate(profile_data):
        for second in profile_data[first_index + 1 :]:
            pair_records = _centerline_records_between_profile_boundaries(
                first,
                second,
                source_id,
            )
            used_bounding_rectangles = False
            if (
                (len(pair_records) < 3 or not _records_span_multiple_directions(pair_records))
                and first["rectangle_segments"]
                and second["rectangle_segments"]
            ):
                first_rectangle = dict(first, segments=first["rectangle_segments"])
                second_rectangle = dict(second, segments=second["rectangle_segments"])
                pair_records = _centerline_records_between_profile_boundaries(
                    first_rectangle,
                    second_rectangle,
                    source_id,
                )
                used_bounding_rectangles = True
            if len(pair_records) < 3 or not _records_span_multiple_directions(pair_records):
                continue
            average_thickness = sum(float(record["thickness"]) for record in pair_records) / len(pair_records)
            block_candidates.append(
                (-len(pair_records), average_thickness, used_bounding_rectangles, pair_records)
            )
    if not block_candidates:
        return [], 0, 0, 0, rectangular_profile_count
    _negative_count, _average_thickness, used_bounding_rectangles, best_records = min(
        block_candidates,
        key=lambda item: (item[0], item[1]),
    )
    return (
        _dedupe_centerline_records(best_records),
        0,
        1,
        int(used_bounding_rectangles),
        rectangular_profile_count,
    )


def _centerline_records_between_profile_boundaries(first, second, source_id):
    topology_segments = first["segments"] + second["segments"]
    first_infos = [
        info
        for index, segment in enumerate(first["segments"])
        for info in (
            _edge_info_with_min_length(
                segment,
                FRAGMENT_PROFILE_MIN_AXIS_MM,
                index=index,
            ),
        )
        if info is not None
    ]
    second_infos = [
        info
        for index, segment in enumerate(second["segments"])
        for info in (
            _edge_info_with_min_length(
                segment,
                FRAGMENT_PROFILE_MIN_AXIS_MM,
                index=index,
            ),
        )
        if info is not None
    ]
    candidates = []
    for first_index, first_info in enumerate(first_infos):
        first_info["source_ids"] = frozenset((source_id,))
        for second_index, second_info in enumerate(second_infos):
            second_info["source_ids"] = frozenset((source_id,))
            candidate = _pair_candidate(
                first_info,
                second_info,
                topology_segments=topology_segments,
            )
            if candidate is None:
                continue
            candidate["segment"] = _concentric_pair_segment(
                first_info,
                second_info,
                candidate["thickness"],
            )
            candidates.append((candidate["score"], first_index, second_index, candidate))

    result = []
    used_first = set()
    used_second = set()
    for _score, first_index, second_index, candidate in sorted(candidates, key=lambda item: item[0]):
        if first_index in used_first or second_index in used_second:
            continue
        result.append(
            _centerline_record(
                candidate["segment"],
                candidate["thickness"],
                source_ids=(source_id,),
            )
        )
        used_first.add(first_index)
        used_second.add(second_index)
    return _dedupe_centerline_records(result)


def _records_span_multiple_directions(records):
    angles = []
    for record in records:
        info = _edge_info(record["segment"])
        if info is None:
            continue
        if all(
            _angle_difference(info["angle"], existing) > math.radians(ANGLE_TOLERANCE_DEG)
            for existing in angles
        ):
            angles.append(info["angle"])
    return len(angles) >= 2


def _oriented_rectangle_segments(metrics):
    u = metrics["u"]
    n = metrics["n"]
    along_min = metrics["along_min"]
    along_max = metrics["along_max"]
    across_min = metrics["across_min"]
    across_max = metrics["across_max"]

    def point(along, across):
        return (
            u[0] * along + n[0] * across,
            u[1] * along + n[1] * across,
        )

    corners = [
        point(along_min, across_min),
        point(along_max, across_min),
        point(along_max, across_max),
        point(along_min, across_max),
    ]
    return [
        (
            corners[index][0],
            corners[index][1],
            corners[(index + 1) % 4][0],
            corners[(index + 1) % 4][1],
        )
        for index in range(4)
    ]


def _merge_profile_boundary_segments(segments):
    """Rebuild long contour sides imported as many short collinear edges."""
    result = []
    for segment in segments:
        normalized = tuple(float(value) for value in segment)
        if _segment_length(normalized) < FRAGMENT_PROFILE_MIN_AXIS_MM:
            continue
        if result:
            merged = _try_merge_segments(
                result[-1],
                normalized,
                gap_tolerance=FRAGMENT_PROFILE_MAX_GAP_MM,
                minimum_length=FRAGMENT_PROFILE_MIN_AXIS_MM,
            )
            if merged is not None:
                result[-1] = merged
                continue
        result.append(normalized)

    # A closed wire may split one straight side between the end and beginning
    # of its ordered vertex list.
    if len(result) > 1:
        merged = _try_merge_segments(
            result[-1],
            result[0],
            gap_tolerance=FRAGMENT_PROFILE_MAX_GAP_MM,
            minimum_length=FRAGMENT_PROFILE_MIN_AXIS_MM,
        )
        if merged is not None:
            result[0] = merged
            result.pop()
    return result


def _concentric_pair_segment(first, second, thickness):
    u = first["u"]
    n = (-u[1], u[0])
    first_range = _projection_range(first, u)
    second_range = _projection_range(second, u)
    overlap_start = max(first_range[0], second_range[0])
    overlap_end = min(first_range[1], second_range[1])
    union_start = min(first_range[0], second_range[0])
    union_end = max(first_range[1], second_range[1])
    extension = float(thickness) / 2.0
    selected_start = max(union_start, overlap_start - extension)
    selected_end = min(union_end, overlap_end + extension)
    first_axis = (_dot(first["p1"], n) + _dot(first["p2"], n)) / 2.0
    second_axis = (_dot(second["p1"], n) + _dot(second["p2"], n)) / 2.0
    center_axis = (first_axis + second_axis) / 2.0
    return (
        u[0] * selected_start + n[0] * center_axis,
        u[1] * selected_start + n[1] * center_axis,
        u[0] * selected_end + n[0] * center_axis,
        u[1] * selected_end + n[1] * center_axis,
    )


def _polygon_area(polygon):
    if not polygon or len(polygon) < 3:
        return 0.0
    return abs(
        sum(
            first[0] * second[1] - second[0] * first[1]
            for first, second in zip(polygon, polygon[1:] + polygon[:1])
        )
    ) / 2.0


def _polygon_mean_point(polygon):
    if not polygon:
        return (0.0, 0.0)
    count = float(len(polygon))
    return (
        sum(float(point[0]) for point in polygon) / count,
        sum(float(point[1]) for point in polygon) / count,
    )


def _centerline_records_from_profile_pairs(profile_axes):
    """Create wall axes between two thin, parallel profile layers."""
    candidates = []
    for first_index, first_record in enumerate(profile_axes):
        first = _edge_info_with_min_length(
            first_record["segment"],
            FRAGMENT_PROFILE_MIN_AXIS_MM,
            index=first_index,
        )
        if first is None:
            continue
        for second_index in range(first_index + 1, len(profile_axes)):
            second_record = profile_axes[second_index]
            second = _edge_info_with_min_length(
                second_record["segment"],
                FRAGMENT_PROFILE_MIN_AXIS_MM,
                index=second_index,
            )
            if second is None:
                continue
            angle_delta = _angle_difference(first["angle"], second["angle"])
            if angle_delta > math.radians(ANGLE_TOLERANCE_DEG):
                continue

            u = first["u"]
            n = (-u[1], u[0])
            first_range = _projection_range(first, u)
            second_range = _projection_range(second, u)
            overlap_start = max(first_range[0], second_range[0])
            overlap_end = min(first_range[1], second_range[1])
            overlap = overlap_end - overlap_start
            minimum_length = min(
                first_range[1] - first_range[0],
                second_range[1] - second_range[0],
            )
            if overlap < FRAGMENT_PROFILE_MIN_AXIS_MM or minimum_length <= 1e-9:
                continue
            overlap_ratio = overlap / minimum_length
            if overlap_ratio < MIN_OVERLAP_RATIO:
                continue

            first_axis = (_dot(first["p1"], n) + _dot(first["p2"], n)) / 2.0
            second_axis = (_dot(second["p1"], n) + _dot(second["p2"], n)) / 2.0
            axis_distance = abs(second_axis - first_axis)
            first_depth = max(0.0, float(first_record.get("profile_depth") or 0.0))
            second_depth = max(0.0, float(second_record.get("profile_depth") or 0.0))
            envelope_thickness = axis_distance + 0.5 * (first_depth + second_depth)
            thickness = _valid_wall_thickness(envelope_thickness)
            if thickness is None or axis_distance <= DUPLICATE_TOLERANCE_MM:
                continue

            center_axis = (first_axis + second_axis) / 2.0
            segment = (
                u[0] * overlap_start + n[0] * center_axis,
                u[1] * overlap_start + n[1] * center_axis,
                u[0] * overlap_end + n[0] * center_axis,
                u[1] * overlap_end + n[1] * center_axis,
            )
            candidates.append(
                {
                    "first_index": first_index,
                    "second_index": second_index,
                    "record": _centerline_record(
                        segment,
                        thickness,
                        source_ids=frozenset(first_record.get("source_ids", ()))
                        | frozenset(second_record.get("source_ids", ())),
                    ),
                    "score": (axis_distance, angle_delta, -overlap_ratio, -overlap),
                }
            )

    result = []
    used = set()
    for candidate in sorted(candidates, key=lambda item: item["score"]):
        if candidate["first_index"] in used or candidate["second_index"] in used:
            continue
        result.append(candidate["record"])
        used.add(candidate["first_index"])
        used.add(candidate["second_index"])
    return result


def _merge_fragment_centerline_records(records):
    """Join short profile axes before applying the minimum wall-length filter."""
    result = [
        _centerline_record(
            record["segment"],
            record.get("thickness"),
            source_ids=record.get("source_ids"),
        )
        for record in records
        if _segment_length(record["segment"]) >= FRAGMENT_PROFILE_MIN_AXIS_MM
        and record.get("thickness") is not None
    ]
    changed = True
    while changed:
        changed = False
        for first_index, first in enumerate(result):
            first_thickness = float(first["thickness"])
            for second_index in range(first_index + 1, len(result)):
                second = result[second_index]
                second_thickness = float(second["thickness"])
                if abs(first_thickness - second_thickness) > THICKNESS_CLUSTER_TOLERANCE_MM:
                    continue
                merged = _try_merge_segments(
                    first["segment"],
                    second["segment"],
                    gap_tolerance=FRAGMENT_PROFILE_MAX_GAP_MM,
                    minimum_length=FRAGMENT_PROFILE_MIN_AXIS_MM,
                )
                if merged is None:
                    continue
                first_length = _segment_length(first["segment"])
                second_length = _segment_length(second["segment"])
                total_length = max(first_length + second_length, 1e-9)
                thickness = (
                    first_thickness * first_length + second_thickness * second_length
                ) / total_length
                source_ids = frozenset(first.get("source_ids", ())) | frozenset(
                    second.get("source_ids", ())
                )
                result[first_index] = _centerline_record(
                    merged,
                    thickness,
                    source_ids=source_ids,
                )
                del result[second_index]
                changed = True
                break
            if changed:
                break
    return _dedupe_centerline_records(result)


def _wire_polygon_points(wire):
    try:
        if hasattr(wire, "isClosed") and not bool(wire.isClosed()):
            return None
    except Exception:
        pass
    try:
        segments = _segments_from_edges(getattr(wire, "Edges", []) or [], min_length=1.0)
    except Exception:
        segments = []
    if _segments_form_closed_loop(segments):
        polygon = _ordered_polygon_from_segments(segments)
        if polygon:
            return polygon

    # Vertexes from imported block wires are not guaranteed to follow the wire
    # traversal order. Keep them only as a fallback when edge topology is absent.
    try:
        vertices = list(getattr(wire, "Vertexes", []) or [])
        points = [(float(vertex.Point.x), float(vertex.Point.y)) for vertex in vertices]
    except Exception:
        points = []
    if len(points) >= 3:
        return points
    return None


def _ordered_polygon_from_segments(segments):
    if len(segments) < 3:
        return None
    remaining = [tuple(float(value) for value in segment) for segment in segments]
    first = remaining.pop(0)
    start = (first[0], first[1])
    current = (first[2], first[3])
    polygon = [start, current]
    while remaining:
        match_index = None
        next_point = None
        for index, segment in enumerate(remaining):
            first_point = (segment[0], segment[1])
            second_point = (segment[2], segment[3])
            if _point_distance(current, first_point) <= CLOSED_TOLERANCE_MM:
                match_index, next_point = index, second_point
                break
            if _point_distance(current, second_point) <= CLOSED_TOLERANCE_MM:
                match_index, next_point = index, first_point
                break
        if match_index is None:
            return None
        del remaining[match_index]
        current = next_point
        if _point_distance(current, start) <= CLOSED_TOLERANCE_MM:
            return polygon if not remaining else None
        polygon.append(current)
    return polygon if _point_distance(current, start) <= CLOSED_TOLERANCE_MM else None


def _polygon_is_compact_profile(polygon):
    metrics = _oriented_polygon_metrics(polygon)
    if metrics is None:
        return False
    short_len = metrics["short_len"]
    long_len = metrics["long_len"]
    if short_len < COLUMN_MIN_SIZE_MM or long_len > COLUMN_MAX_SIZE_MM:
        return False
    if long_len / max(short_len, 1e-9) > COLUMN_MAX_ASPECT_RATIO:
        return False
    return metrics["fill_ratio"] >= COLUMN_MIN_FILL_RATIO


def _oriented_polygon_metrics(polygon):
    """Measure compactness in the polygon orientation so rotated columns remain valid."""
    if not polygon or len(polygon) < 3:
        return None
    edges = []
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        length = _point_distance(first, second)
        if length > 1e-9:
            edges.append((length, first, second))
    if not edges:
        return None
    _length, first, second = max(edges, key=lambda item: item[0])
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    direction_length = math.hypot(dx, dy)
    u = (dx / direction_length, dy / direction_length)
    n = (-u[1], u[0])
    along = [_dot(point, u) for point in polygon]
    across = [_dot(point, n) for point in polygon]
    first_extent = max(along) - min(along)
    second_extent = max(across) - min(across)
    short_len = min(first_extent, second_extent)
    long_len = max(first_extent, second_extent)
    oriented_area = first_extent * second_extent
    if short_len <= 1e-9 or oriented_area <= 1e-9:
        return None
    area = abs(
        sum(
            first[0] * second[1] - second[0] * first[1]
            for first, second in zip(polygon, polygon[1:] + polygon[:1])
        )
    ) / 2.0
    return {
        "short_len": short_len,
        "long_len": long_len,
        "fill_ratio": min(1.0, area / oriented_area),
        "u": u,
        "n": n,
        "along_min": min(along),
        "along_max": max(along),
        "across_min": min(across),
        "across_max": max(across),
    }


def _record_supports_profile_point(record, point, topology_context, include_boundary=False):
    if not topology_context:
        return True
    source_ids = frozenset(record.get("source_ids", ()))
    if not source_ids:
        return True
    profiles_by_source = topology_context.get("profiles_by_source", {})
    has_closed_profile = False
    for source_id in source_ids:
        profiles = profiles_by_source.get(source_id, [])
        if profiles:
            has_closed_profile = True
        if any(_point_in_polygon(point, polygon, include_boundary=include_boundary) for polygon in profiles):
            return True
    return not has_closed_profile


def _point_is_blocked_by_compact_profile(point, topology_context):
    if not topology_context:
        return False
    return any(
        _point_in_polygon(point, polygon, include_boundary=True)
        for polygon in topology_context.get("compact_profiles", [])
    )


def _point_in_polygon(point, polygon, include_boundary=False):
    if len(polygon) < 3:
        return False
    x, y = float(point[0]), float(point[1])
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if _point_on_segment((x, y), previous, current, PROFILE_BOUNDARY_TOLERANCE_MM):
            return bool(include_boundary)
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y):
            crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing_x:
                inside = not inside
        previous = current
    return inside


def _point_on_segment(point, first, second, tolerance):
    dx = float(second[0]) - float(first[0])
    dy = float(second[1]) - float(first[1])
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-12:
        return _point_distance(point, first) <= tolerance
    parameter = (
        (float(point[0]) - float(first[0])) * dx + (float(point[1]) - float(first[1])) * dy
    ) / length_squared
    if parameter < 0.0 or parameter > 1.0:
        return False
    projected = (float(first[0]) + parameter * dx, float(first[1]) + parameter * dy)
    return _point_distance(point, projected) <= tolerance


def _segments_from_object(obj, prefer_opening_profile=False, source_id=None):
    """Read one source object, virtually decomposing topological compounds when needed.

    A Part::Feature may expose an entire CAD layer or reconstructed wall set as one
    ``Part::TopoShape`` Compound. Running the dominant-axis heuristic on that aggregate
    can incorrectly collapse several independent walls into one long centerline.
    FreeCAD exposes direct compound children through ``TopoShape.childShapes()``; use
    those children in memory and keep the document object untouched.
    """
    shape = getattr(obj, "Shape", None)
    if shape is None:
        return [], [], 0, 0

    is_link = _is_link_object(obj)
    # Preserve the already validated App::Link/block path. This change targets
    # plain Part::Feature-style containers such as Pared_Concreto001.
    components = [shape] if is_link else _shape_extraction_components(shape)
    if len(components) > 1 or (components and components[0] is not shape):
        label = str(getattr(obj, "Label", getattr(obj, "Name", "Objeto")))
        msg(
            "Compound descompuesto virtualmente: %s | componentes=%d | fuente intacta"
            % (label, len(components))
        )
        body_records = []
        raw_edges = []
        ignored_compact_profiles = 0
        profile_axis_count = 0
        for component in components:
            (
                component_body,
                component_edges,
                component_ignored,
                component_profile_count,
            ) = _segments_from_shape(
                component,
                prefer_opening_profile=prefer_opening_profile,
                source_id=source_id,
                allow_block_heuristics=False,
            )
            body_records.extend(component_body)
            raw_edges.extend(component_edges)
            ignored_compact_profiles += component_ignored
            profile_axis_count += component_profile_count
        return body_records, raw_edges, ignored_compact_profiles, profile_axis_count

    return _segments_from_shape(
        shape,
        prefer_opening_profile=prefer_opening_profile,
        source_id=source_id,
        allow_block_heuristics=is_link,
        source_label=str(getattr(obj, "Label", getattr(obj, "Name", ""))),
    )


def _shape_extraction_components(shape):
    """Return meaningful topological children for Compound/CompSolid shapes.

    Only compound containers are flattened. Wires, faces and solids remain intact so
    their local closed-profile information is preserved. ``childShapes()`` defaults
    to cumulative orientation and location in FreeCAD, which is what extraction needs.
    """
    if shape is None or _shape_type_name(shape) not in ("Compound", "CompSolid"):
        return [shape] if shape is not None else []

    result = []
    pending = [shape]
    while pending:
        current = pending.pop(0)
        current_type = _shape_type_name(current)
        if current_type in ("Compound", "CompSolid"):
            try:
                children = list(current.childShapes() or [])
            except Exception:
                children = []
            if children:
                pending[0:0] = children
                continue
        if _shape_has_edges(current):
            result.append(current)

    # Defensive fallback: never discard a usable source solely because an importer
    # exposes a Compound without childShapes().
    if not result and _shape_has_edges(shape):
        return [shape]
    return result


def _shape_type_name(shape):
    try:
        return str(getattr(shape, "ShapeType", "") or "")
    except Exception:
        return ""


def _segments_from_shape(
    shape,
    prefer_opening_profile=False,
    source_id=None,
    allow_block_heuristics=False,
    source_label="",
):
    """Extract wall/profile candidates from one non-container topological shape."""
    if shape is None:
        return [], [], 0, 0

    body_records = []
    try:
        edges = list(getattr(shape, "Edges", []) or [])
    except Exception:
        edges = []

    profile_record = _centerline_record_from_complex_shape(
        shape,
        prefer_opening_profile,
        source_ids=(source_id,) if source_id is not None else (),
    )
    if profile_record is not None:
        if source_label:
            msg("Eje principal leido en shape complejo: %s" % source_label)
        return [profile_record], [], 0, 1

    if allow_block_heuristics:
        block_record = _centerline_record_from_block_shape(
            shape,
            source_ids=(source_id,) if source_id is not None else (),
        )
        if block_record is not None:
            msg(
                "Eje de bloque leido desde envolvente principal: %s | largo=%.1f mm | espesor=%.1f mm"
                % (
                    source_label or "Link",
                    _segment_length(block_record["segment"]),
                    float(block_record["thickness"]),
                )
            )
            return [block_record], [], 0, 1

        perimeter_records = _centerline_records_from_block_perimeter(
            shape,
            source_ids=(source_id,) if source_id is not None else (),
        )
        if perimeter_records:
            msg(
                "Ejes perimetrales leidos desde bloque completo: %s | lineas=%d"
                % (source_label or "Link", len(perimeter_records))
            )
            return perimeter_records, [], 0, len(perimeter_records)

    ignored_edge_keys, ignored_compact_profiles = _compact_closed_edge_keys(shape)
    raw_edges = [segment for segment in _segments_from_edges(edges) if _segment_key(*segment) not in ignored_edge_keys]

    # Shapes without usable edges are unusual, but their bounding box remains a
    # useful last resort. Closed wall outlines are handled by edge pairing so
    # diagonal walls keep their real direction.
    if not raw_edges and not edges and not ignored_compact_profiles:
        shape_segment = _centerline_from_bbox(getattr(shape, "BoundBox", None))
        if shape_segment is not None:
            body_records.append(
                _centerline_record(
                    shape_segment,
                    _bbox_wall_thickness(getattr(shape, "BoundBox", None)),
                    source_ids=(source_id,) if source_id is not None else (),
                )
            )

    return body_records, raw_edges, ignored_compact_profiles, 0

def _profile_centerlines_from_objects(objects):
    """Group nearby shape edges and create one dominant axis per component."""
    segments = []
    for obj in objects:
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        try:
            edges = list(getattr(shape, "Edges", []) or [])
        except Exception:
            edges = []
        obj_segments = _segments_from_edges(edges, min_length=1.0)
        if obj_segments:
            segments.extend(obj_segments)
            msg(
                "Geometria de perfil leida en %s: bordes=%d"
                % (str(getattr(obj, "Label", getattr(obj, "Name", ""))), len(obj_segments))
            )

    components = _group_segments_by_proximity(segments, PROFILE_COMPONENT_GAP_MM)
    result = []
    ignored = 0
    for component in components:
        centerline = _centerline_from_segments(component, prefer_opening_profile=True, minimum_edges=1)
        if centerline is None:
            ignored += 1
            continue
        result.append(centerline)
    msg("Perfiles complejos agrupados: %d | ejes validos: %d" % (len(components), len(result)))
    return result, len(result), ignored


def _door_centerlines_from_objects(objects):
    """Create the closed-opening axis from door swing symbols when possible."""
    records = []
    for obj in objects:
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        try:
            edges = list(getattr(shape, "Edges", []) or [])
        except Exception:
            edges = []
        obj_records = [record for record in (_door_edge_record(edge) for edge in edges) if record is not None]
        if obj_records:
            records.extend(obj_records)
            msg(
                "Geometria de puerta leida en %s: bordes=%d"
                % (str(getattr(obj, "Label", getattr(obj, "Name", ""))), len(obj_records))
            )

    components = _group_items_by_proximity(records, lambda record: record["segment"], DOOR_COMPONENT_GAP_MM)
    result = []
    ignored = 0
    arc_count = 0
    fallback_count = 0
    for component in components:
        centerline, method = _door_centerline_from_component(component)
        if centerline is None:
            ignored += 1
            continue
        result.append(centerline)
        if method == "swing_arc":
            arc_count += 1
        else:
            fallback_count += 1
    msg(
        "Puertas agrupadas: %d | ejes por arco: %d | ejes de respaldo: %d"
        % (len(components), arc_count, fallback_count)
    )
    return result, len(result), ignored


def _door_edge_record(edge):
    segment = _segment_from_edge(edge, min_length=1.0)
    if segment is None:
        return None
    curve = getattr(edge, "Curve", None)
    curve_name = type(curve).__name__.lower() if curve is not None else ""
    is_line = "line" in curve_name or curve is None
    center = None
    if not is_line and curve is not None:
        raw_center = getattr(curve, "Center", None)
        if raw_center is not None:
            try:
                center = (float(raw_center.x), float(raw_center.y))
            except Exception:
                center = None
    return {"segment": segment, "is_line": is_line, "arc_center": center}


def _door_centerline_from_component(records):
    linear_segments = [record["segment"] for record in records if record["is_line"]]
    arc_records = [record for record in records if record["arc_center"] is not None]
    arc_records.sort(key=lambda record: -_segment_length(record["segment"]))

    for record in arc_records:
        center = record["arc_center"]
        x1, y1, x2, y2 = record["segment"]
        candidates = [
            (center[0], center[1], x1, y1),
            (center[0], center[1], x2, y2),
        ]
        if any(_segment_length(candidate) < MIN_WALL_LENGTH_MM for candidate in candidates):
            continue
        scores = [_radial_leaf_match_score(candidate, linear_segments) for candidate in candidates]
        if scores[0] > scores[1] + 1e-6:
            return candidates[1], "swing_arc"
        if scores[1] > scores[0] + 1e-6:
            return candidates[0], "swing_arc"

    fallback_segments = linear_segments or [record["segment"] for record in records]
    fallback = _centerline_from_segments(fallback_segments, prefer_opening_profile=True, minimum_edges=1)
    return fallback, "dominant_axis" if fallback is not None else "none"


def _radial_leaf_match_score(radial, linear_segments):
    radial_length = _segment_length(radial)
    if radial_length <= 1e-9:
        return 0.0
    best = 0.0
    for segment in linear_segments:
        segment_length = _segment_length(segment)
        if segment_length < radial_length * 0.65 or segment_length > radial_length * 1.35:
            continue
        endpoint_error = min(
            _point_distance((radial[0], radial[1]), (segment[0], segment[1]))
            + _point_distance((radial[2], radial[3]), (segment[2], segment[3])),
            _point_distance((radial[0], radial[1]), (segment[2], segment[3]))
            + _point_distance((radial[2], radial[3]), (segment[0], segment[1])),
        )
        if endpoint_error > 2.0 * DOOR_LEAF_MATCH_TOLERANCE_MM:
            continue
        score = 1.0 - endpoint_error / (2.0 * DOOR_LEAF_MATCH_TOLERANCE_MM)
        best = max(best, score)
    return best


def _segment_length(segment):
    return math.hypot(float(segment[2]) - float(segment[0]), float(segment[3]) - float(segment[1]))


def _point_distance(first, second):
    return math.hypot(float(second[0]) - float(first[0]), float(second[1]) - float(first[1]))


def _group_segments_by_proximity(segments, gap):
    """Build connected components from touching or nearby projected segments."""
    return _group_items_by_proximity(segments, lambda segment: segment, gap)


def _group_items_by_proximity(items, segment_getter, gap):
    if not items:
        return []
    parent = list(range(len(items)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first, second):
        first_root = find(first)
        second_root = find(second)
        if first_root != second_root:
            parent[second_root] = first_root

    boxes = [_segment_box(segment_getter(item)) for item in items]
    for i, first_box in enumerate(boxes):
        for j in range(i + 1, len(boxes)):
            if _box_distance(first_box, boxes[j]) <= float(gap):
                union(i, j)

    grouped = {}
    for index, item in enumerate(items):
        grouped.setdefault(find(index), []).append(item)
    return list(grouped.values())


def _segment_box(segment):
    x1, y1, x2, y2 = segment
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def _box_distance(first, second):
    dx = max(0.0, first[0] - second[2], second[0] - first[2])
    dy = max(0.0, first[1] - second[3], second[1] - first[3])
    return math.hypot(dx, dy)


def _centerline_from_complex_shape(shape, prefer_opening_profile=False):
    """Create one dominant axis for an elongated closed or multi-edge shape."""
    record = _centerline_record_from_complex_shape(shape, prefer_opening_profile)
    return record["segment"] if record is not None else None


def _centerline_record_from_complex_shape(shape, prefer_opening_profile=False, source_ids=()):
    """Create a centerline record and retain the profile depth as wall thickness."""
    try:
        edges = list(getattr(shape, "Edges", []) or [])
    except Exception:
        return None
    segments = _segments_from_edges(edges, min_length=1.0)
    centerline = _centerline_from_segments(
        segments,
        prefer_opening_profile=prefer_opening_profile,
        minimum_edges=COMPLEX_PROFILE_MIN_EDGES,
    )
    if centerline is None:
        return None
    return _centerline_record(
        centerline,
        _profile_thickness_from_segments(segments, centerline),
        source_ids=source_ids,
        closed_endpoints=(1, 2) if _closed_profile_polygons(shape) else (),
    )


def _centerline_record_from_block_shape(shape, source_ids=()):
    """Infer one wall axis from the unordered point cloud of a legacy block."""
    points = []
    try:
        vertices = list(getattr(shape, "Vertexes", []) or [])
    except Exception:
        vertices = []
    for vertex in vertices:
        try:
            points.append((float(vertex.Point.x), float(vertex.Point.y)))
        except Exception:
            continue
    if len(points) < 2:
        try:
            edges = list(getattr(shape, "Edges", []) or [])
        except Exception:
            edges = []
        for segment in _segments_from_edges(edges, min_length=FRAGMENT_PROFILE_MIN_AXIS_MM):
            points.extend(((segment[0], segment[1]), (segment[2], segment[3])))

    unique_points = {}
    for point in points:
        key = (_round_key(point[0]), _round_key(point[1]))
        unique_points.setdefault(key, point)
    points = list(unique_points.values())
    if len(points) < 3:
        return None

    center_x = sum(point[0] for point in points) / len(points)
    center_y = sum(point[1] for point in points) / len(points)
    covariance_xx = sum((point[0] - center_x) ** 2 for point in points) / len(points)
    covariance_xy = sum(
        (point[0] - center_x) * (point[1] - center_y)
        for point in points
    ) / len(points)
    covariance_yy = sum((point[1] - center_y) ** 2 for point in points) / len(points)
    if max(covariance_xx, covariance_yy) <= 1e-9:
        return None

    angle = 0.5 * math.atan2(
        2.0 * covariance_xy,
        covariance_xx - covariance_yy,
    )
    u = (math.cos(angle), math.sin(angle))
    n = (-u[1], u[0])
    along = [_dot(point, u) for point in points]
    across = [_dot(point, n) for point in points]
    along_min, along_max = min(along), max(along)
    across_min, across_max = min(across), max(across)
    long_extent = along_max - along_min
    depth = across_max - across_min
    if depth > long_extent:
        u, n = n, (-u[0], -u[1])
        along, across = across, [-value for value in along]
        along_min, along_max = min(along), max(along)
        across_min, across_max = min(across), max(across)
        long_extent = along_max - along_min
        depth = across_max - across_min

    thickness = _valid_wall_thickness(depth)
    if (
        long_extent < MIN_WALL_LENGTH_MM
        or thickness is None
        or long_extent / max(depth, 1e-9) < BLOCK_BOUNDS_MIN_ASPECT_RATIO
    ):
        return None

    center_axis = (across_min + across_max) / 2.0
    segment = (
        u[0] * along_min + n[0] * center_axis,
        u[1] * along_min + n[1] * center_axis,
        u[0] * along_max + n[0] * center_axis,
        u[1] * along_max + n[1] * center_axis,
    )
    return _centerline_record(
        segment,
        thickness,
        source_ids=source_ids,
        closed_endpoints=(1, 2),
    )


def _centerline_records_from_block_perimeter(shape, source_ids=()):
    """Create a rectangular centerline loop from edge stations of a legacy block."""
    try:
        edges = list(getattr(shape, "Edges", []) or [])
    except Exception:
        edges = []
    segments = _segments_from_edges(edges, min_length=FRAGMENT_PROFILE_MIN_AXIS_MM)
    infos = [
        info
        for index, segment in enumerate(segments)
        for info in (
            _edge_info_with_min_length(
                segment,
                FRAGMENT_PROFILE_MIN_AXIS_MM,
                index=index,
            ),
        )
        if info is not None
    ]
    if len(infos) < 8:
        return []

    reference = max(infos, key=lambda info: info["length"])
    u = reference["u"]
    n = (-u[1], u[0])
    direction_limit = math.cos(math.radians(BLOCK_EDGE_DIRECTION_TOLERANCE_DEG))
    along_stations = []
    across_stations = []
    for info in infos:
        midpoint = (
            (info["p1"][0] + info["p2"][0]) / 2.0,
            (info["p1"][1] + info["p2"][1]) / 2.0,
        )
        if abs(_dot(info["u"], u)) >= direction_limit:
            across_stations.append((_dot(midpoint, n), info["length"]))
        elif abs(_dot(info["u"], n)) >= direction_limit:
            along_stations.append((_dot(midpoint, u), info["length"]))

    along = _dominant_block_stations(along_stations)
    across = _dominant_block_stations(across_stations)
    if len(along) != 4 or len(across) != 4:
        return []

    outer_along = along[-1] - along[0]
    outer_across = across[-1] - across[0]
    if max(outer_along, outer_across) <= COLUMN_MAX_SIZE_MM:
        return []

    left_thickness = _valid_wall_thickness(along[1] - along[0])
    right_thickness = _valid_wall_thickness(along[3] - along[2])
    bottom_thickness = _valid_wall_thickness(across[1] - across[0])
    top_thickness = _valid_wall_thickness(across[3] - across[2])
    if None in (left_thickness, right_thickness, bottom_thickness, top_thickness):
        return []

    left_axis = (along[0] + along[1]) / 2.0
    right_axis = (along[2] + along[3]) / 2.0
    bottom_axis = (across[0] + across[1]) / 2.0
    top_axis = (across[2] + across[3]) / 2.0
    if (
        right_axis - left_axis < MIN_WALL_LENGTH_MM
        or top_axis - bottom_axis < MIN_WALL_LENGTH_MM
    ):
        return []

    def point(along_value, across_value):
        return (
            u[0] * along_value + n[0] * across_value,
            u[1] * along_value + n[1] * across_value,
        )

    bottom_left = point(left_axis, bottom_axis)
    bottom_right = point(right_axis, bottom_axis)
    top_right = point(right_axis, top_axis)
    top_left = point(left_axis, top_axis)
    return [
        _centerline_record(
            (bottom_left[0], bottom_left[1], bottom_right[0], bottom_right[1]),
            bottom_thickness,
            source_ids=source_ids,
        ),
        _centerline_record(
            (bottom_right[0], bottom_right[1], top_right[0], top_right[1]),
            right_thickness,
            source_ids=source_ids,
        ),
        _centerline_record(
            (top_right[0], top_right[1], top_left[0], top_left[1]),
            top_thickness,
            source_ids=source_ids,
        ),
        _centerline_record(
            (top_left[0], top_left[1], bottom_left[0], bottom_left[1]),
            left_thickness,
            source_ids=source_ids,
        ),
    ]


def _dominant_block_stations(weighted_stations):
    if not weighted_stations:
        return []
    clusters = []
    for station, weight in sorted(weighted_stations, key=lambda item: item[0]):
        if (
            clusters
            and abs(station - clusters[-1]["station"]) <= BLOCK_STATION_CLUSTER_TOLERANCE_MM
        ):
            total_weight = clusters[-1]["weight"] + weight
            clusters[-1]["station"] = (
                clusters[-1]["station"] * clusters[-1]["weight"] + station * weight
            ) / max(total_weight, 1e-9)
            clusters[-1]["weight"] = total_weight
        else:
            clusters.append({"station": float(station), "weight": float(weight)})
    if len(clusters) < 4:
        return []
    dominant = sorted(clusters, key=lambda item: item["weight"], reverse=True)[:4]
    return sorted(cluster["station"] for cluster in dominant)


def _profile_thickness_from_segments(segments, centerline):
    return _valid_wall_thickness(_profile_depth_from_segments(segments, centerline))


def _profile_depth_from_segments(segments, centerline):
    length = _segment_length(centerline)
    if length <= 1e-9:
        return None
    u = ((centerline[2] - centerline[0]) / length, (centerline[3] - centerline[1]) / length)
    n = (-u[1], u[0])
    points = []
    for x1, y1, x2, y2 in segments:
        points.extend(((x1, y1), (x2, y2)))
    if not points:
        return None
    across = [_dot(point, n) for point in points]
    return max(across) - min(across)


def _bbox_wall_thickness(bbox):
    if bbox is None:
        return None
    try:
        return _valid_wall_thickness(min(abs(float(bbox.XLength)), abs(float(bbox.YLength))))
    except Exception:
        return None


def _valid_wall_thickness(value):
    if value is None:
        return None
    thickness = abs(float(value))
    if thickness < MIN_WALL_THICKNESS_MM or thickness > MAX_WALL_THICKNESS_MM:
        return None
    return thickness


def _centerline_from_segments(
    segments,
    prefer_opening_profile=False,
    minimum_edges=COMPLEX_PROFILE_MIN_EDGES,
    minimum_axis_length=MIN_WALL_LENGTH_MM,
):
    if len(segments) < int(minimum_edges):
        return None

    sum_cos = 0.0
    sum_sin = 0.0
    longest_segment = None
    longest_length = 0.0
    for segment in segments:
        x1, y1, x2, y2 = segment
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            continue
        angle = math.atan2(dy, dx)
        sum_cos += length * math.cos(2.0 * angle)
        sum_sin += length * math.sin(2.0 * angle)
        if length > longest_length:
            longest_segment = segment
            longest_length = length
    if longest_segment is None:
        return None

    if math.hypot(sum_cos, sum_sin) <= 1e-6:
        angle = math.atan2(longest_segment[3] - longest_segment[1], longest_segment[2] - longest_segment[0])
    else:
        angle = 0.5 * math.atan2(sum_sin, sum_cos)
    u = (math.cos(angle), math.sin(angle))
    n = (-u[1], u[0])

    points = []
    for x1, y1, x2, y2 in segments:
        points.extend(((x1, y1), (x2, y2)))
    along = [_dot(point, u) for point in points]
    across = [_dot(point, n) for point in points]
    along_min = min(along)
    along_max = max(along)
    across_min = min(across)
    across_max = max(across)
    long_extent = along_max - along_min
    depth = across_max - across_min
    if long_extent < float(minimum_axis_length):
        return None
    if depth <= 1e-6:
        return tuple(float(value) for value in longest_segment) if prefer_opening_profile else None
    if depth > COMPLEX_PROFILE_MAX_DEPTH_MM:
        return None
    minimum_aspect = OPENING_PROFILE_MIN_ASPECT_RATIO if prefer_opening_profile else COMPLEX_PROFILE_MIN_ASPECT_RATIO
    if long_extent / depth < minimum_aspect:
        return None

    center_axis = (across_min + across_max) / 2.0
    return (
        u[0] * along_min + n[0] * center_axis,
        u[1] * along_min + n[1] * center_axis,
        u[0] * along_max + n[0] * center_axis,
        u[1] * along_max + n[1] * center_axis,
    )


def _compact_closed_edge_keys(shape):
    """Return projected edge keys belonging to ambiguous compact outlines."""
    try:
        wires = list(getattr(shape, "Wires", []) or [])
    except Exception:
        wires = []

    ignored = set()
    count = 0
    for wire in wires:
        try:
            wire_edges = list(getattr(wire, "Edges", []) or [])
        except Exception:
            wire_edges = []
        segments = _segments_from_edges(wire_edges)
        if not segments or not _wire_is_closed(wire, segments):
            continue
        polygon = _ordered_polygon_from_segments(segments)
        if not _polygon_is_compact_profile(polygon):
            continue
        ignored.update(_segment_key(*segment) for segment in segments)
        count += 1

    # Some importers expose a closed polygon without a Wire collection.
    if not wires:
        segments = _segments_from_edges(getattr(shape, "Edges", []) or [])
        polygon = _ordered_polygon_from_segments(segments) if _segments_form_closed_loop(segments) else None
        if _polygon_is_compact_profile(polygon):
            ignored.update(_segment_key(*segment) for segment in segments)
            count = 1
    return ignored, count


def _wire_is_closed(wire, segments):
    try:
        return bool(wire.isClosed())
    except Exception:
        return _segments_form_closed_loop(segments)


def _segments_form_closed_loop(segments):
    if len(segments) < 3:
        return False
    degree = {}
    for x1, y1, x2, y2 in segments:
        for point in ((_closed_key(x1), _closed_key(y1)), (_closed_key(x2), _closed_key(y2))):
            degree[point] = degree.get(point, 0) + 1
    return bool(degree) and all(value == 2 for value in degree.values())


def _closed_key(value):
    return int(round(float(value) / CLOSED_TOLERANCE_MM))


def _bbox_is_compact_column(bbox):
    if bbox is None:
        return False
    try:
        x_len = abs(float(bbox.XLength))
        y_len = abs(float(bbox.YLength))
    except Exception:
        return False
    short_len = min(x_len, y_len)
    long_len = max(x_len, y_len)
    if short_len < COLUMN_MIN_SIZE_MM or long_len > COLUMN_MAX_SIZE_MM:
        return False
    return long_len / short_len <= COLUMN_MAX_ASPECT_RATIO


def _centerline_from_bbox(bbox):
    """Infer wall centerline from an axis-aligned bounding box."""
    if bbox is None:
        return None
    try:
        x_len = float(bbox.XLength)
        y_len = float(bbox.YLength)
        x_min = float(bbox.XMin)
        x_max = float(bbox.XMax)
        y_min = float(bbox.YMin)
        y_max = float(bbox.YMax)
    except Exception:
        return None

    long_len = max(x_len, y_len)
    short_len = min(x_len, y_len)
    if long_len < MIN_WALL_LENGTH_MM:
        return None

    # For thin imported wall polygons this bbox represents the wall body.
    # For single CAD lines, one dimension may be zero; in that case the line itself is acceptable.
    if short_len > MAX_WALL_THICKNESS_MM:
        return None
    if short_len > 0.0 and short_len < MIN_WALL_THICKNESS_MM and long_len > MIN_WALL_LENGTH_MM:
        pass

    if x_len >= y_len:
        y = (y_min + y_max) / 2.0
        return (x_min, y, x_max, y)
    x = (x_min + x_max) / 2.0
    return (x, y_min, x, y_max)


def _segments_from_edges(edges, min_length=MIN_WALL_LENGTH_MM):
    result = []
    for edge in edges:
        segment = _segment_from_edge(edge, min_length)
        if segment is not None:
            result.append(segment)
    return result


def _segment_from_edge(edge, min_length=MIN_WALL_LENGTH_MM):
    try:
        vertices = list(getattr(edge, "Vertexes", []) or [])
        if len(vertices) >= 2:
            p1 = vertices[0].Point
            p2 = vertices[-1].Point
        else:
            p1 = edge.valueAt(edge.FirstParameter)
            p2 = edge.valueAt(edge.LastParameter)
        length = math.hypot(float(p2.x - p1.x), float(p2.y - p1.y))
        if length < float(min_length):
            return None
        return float(p1.x), float(p1.y), float(p2.x), float(p2.y)
    except Exception:
        return None


def _edge_info(segment, index=0):
    return _edge_info_with_min_length(segment, MIN_WALL_LENGTH_MM, index=index)


def _edge_info_with_min_length(segment, min_length, index=0):
    x1, y1, x2, y2 = [float(v) for v in segment]
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length < float(min_length):
        return None
    ux = dx / length
    uy = dy / length
    if ux < -1e-9 or (abs(ux) <= 1e-9 and uy < 0.0):
        ux = -ux
        uy = -uy
    angle = math.atan2(uy, ux)
    if angle < 0.0:
        angle += math.pi
    return {
        "index": index,
        "p1": (x1, y1),
        "p2": (x2, y2),
        "u": (ux, uy),
        "angle": angle,
        "segment": (x1, y1, x2, y2),
        "length": length,
    }


def _centerlines_from_parallel_edges(edges):
    """Compatibility wrapper returning only segment tuples."""
    return [record["segment"] for record in _centerline_records_from_parallel_edges(edges)]


def _centerline_records_from_parallel_edges(edges, topology_segments=None):
    infos = [info for info in (_edge_record_info(edge, index) for index, edge in enumerate(edges)) if info is not None]
    if not infos:
        return []

    candidates = []
    for i, first in enumerate(infos):
        for second in infos[i + 1 :]:
            candidate = _pair_candidate(first, second, topology_segments=topology_segments)
            if candidate is not None:
                candidates.append(candidate)
    candidates.sort(key=lambda item: item["score"])

    result = []
    covered = {}
    for candidate in candidates:
        first_index = candidate["first_index"]
        second_index = candidate["second_index"]
        first_fraction = _uncovered_fraction(candidate["first_interval"], covered.get(first_index, []))
        second_fraction = _uncovered_fraction(candidate["second_interval"], covered.get(second_index, []))
        if first_fraction < MIN_UNCOVERED_RATIO or second_fraction < MIN_UNCOVERED_RATIO:
            continue
        result.append(
            _centerline_record(
                candidate["segment"],
                candidate["thickness"],
                source_ids=candidate.get("source_ids"),
                closed_endpoints=candidate.get("closed_endpoints"),
            )
        )
        covered.setdefault(first_index, []).append(candidate["first_interval"])
        covered.setdefault(second_index, []).append(candidate["second_interval"])
    return result


def _edge_record_info(edge, index):
    if isinstance(edge, dict):
        segment = edge.get("segment")
        source_ids = edge.get("source_ids", ())
    else:
        segment = edge
        source_ids = ()
    info = _edge_info(segment, index)
    if info is not None:
        info["source_ids"] = frozenset(source_ids or ())
    return info


def _pair_candidate(first, second, topology_segments=None):
    angle_delta = _angle_difference(first["angle"], second["angle"])
    if angle_delta > math.radians(ANGLE_TOLERANCE_DEG):
        return None

    u1 = first["u"]
    u2 = second["u"]
    if _dot(u1, u2) < 0.0:
        u2 = (-u2[0], -u2[1])
    ux = u1[0] + u2[0]
    uy = u1[1] + u2[1]
    u_length = math.hypot(ux, uy)
    if u_length <= 1e-9:
        return None
    u = (ux / u_length, uy / u_length)
    n = (-u[1], u[0])

    first_range = _projection_range(first, u)
    second_range = _projection_range(second, u)
    overlap_start = max(first_range[0], second_range[0])
    overlap_end = min(first_range[1], second_range[1])
    overlap = overlap_end - overlap_start
    if overlap < MIN_WALL_LENGTH_MM:
        return None
    min_length = min(first_range[1] - first_range[0], second_range[1] - second_range[0])
    if min_length <= 0.0:
        return None
    overlap_ratio = overlap / min_length
    if overlap_ratio < MIN_OVERLAP_RATIO:
        return None

    first_axis = (_dot(first["p1"], n) + _dot(first["p2"], n)) / 2.0
    second_axis = (_dot(second["p1"], n) + _dot(second["p2"], n)) / 2.0
    distance = abs(second_axis - first_axis)
    if distance < MIN_WALL_THICKNESS_MM or distance > MAX_WALL_THICKNESS_MM:
        return None

    selected_start = overlap_start
    selected_end = overlap_end
    union_start = min(first_range[0], second_range[0])
    union_end = max(first_range[1], second_range[1])
    if overlap_start - union_start <= MAX_WALL_THICKNESS_MM and _pair_has_end_cap(
        u, n, union_start, first_axis, second_axis, topology_segments
    ):
        selected_start = union_start
    if union_end - overlap_end <= MAX_WALL_THICKNESS_MM and _pair_has_end_cap(
        u, n, union_end, first_axis, second_axis, topology_segments
    ):
        selected_end = union_end

    center_axis = (first_axis + second_axis) / 2.0
    p_start = (u[0] * selected_start + n[0] * center_axis, u[1] * selected_start + n[1] * center_axis)
    p_end = (u[0] * selected_end + n[0] * center_axis, u[1] * selected_end + n[1] * center_axis)
    first_interval = sorted((_dot(p_start, first["u"]), _dot(p_end, first["u"])))
    second_interval = sorted((_dot(p_start, second["u"]), _dot(p_end, second["u"])))
    closed_endpoints = set()
    if _pair_has_end_cap(u, n, selected_start, first_axis, second_axis, topology_segments):
        closed_endpoints.add(1)
    if _pair_has_end_cap(u, n, selected_end, first_axis, second_axis, topology_segments):
        closed_endpoints.add(2)
    return {
        "first_index": first["index"],
        "second_index": second["index"],
        "first_interval": tuple(first_interval),
        "second_interval": tuple(second_interval),
        "segment": (p_start[0], p_start[1], p_end[0], p_end[1]),
        "thickness": distance,
        "source_ids": frozenset(first.get("source_ids", ())) | frozenset(second.get("source_ids", ())),
        "closed_endpoints": frozenset(closed_endpoints),
        # The nearest parallel edge is normally the opposite face of the same wall.
        "score": (distance, angle_delta, -overlap_ratio, -overlap),
    }


def _pair_has_end_cap(direction, normal, station, first_axis, second_axis, topology_segments):
    if not topology_segments:
        return False
    first_point = (
        direction[0] * station + normal[0] * first_axis,
        direction[1] * station + normal[1] * first_axis,
    )
    second_point = (
        direction[0] * station + normal[0] * second_axis,
        direction[1] * station + normal[1] * second_axis,
    )
    for segment in topology_segments:
        info = _edge_info_with_min_length(segment, 1.0)
        if info is None:
            continue
        if abs(_dot(info["u"], direction)) > math.sin(math.radians(ANGLE_TOLERANCE_DEG)):
            continue
        if _point_to_segment_projection(first_point, segment)[0] > END_CAP_TOLERANCE_MM:
            continue
        if _point_to_segment_projection(second_point, segment)[0] <= END_CAP_TOLERANCE_MM:
            return True
    return False


def _projection_range(info, direction):
    values = (_dot(info["p1"], direction), _dot(info["p2"], direction))
    return min(values), max(values)


def _dot(first, second):
    return float(first[0]) * float(second[0]) + float(first[1]) * float(second[1])


def _angle_difference(first, second):
    delta = abs(float(first) - float(second)) % math.pi
    return min(delta, math.pi - delta)


def _uncovered_fraction(interval, covered_intervals):
    start, end = sorted((float(interval[0]), float(interval[1])))
    length = end - start
    if length <= 1e-9:
        return 0.0
    intersections = []
    for covered_start, covered_end in covered_intervals:
        overlap_start = max(start, min(covered_start, covered_end))
        overlap_end = min(end, max(covered_start, covered_end))
        if overlap_end > overlap_start:
            intersections.append((overlap_start, overlap_end))
    if not intersections:
        return 1.0
    intersections.sort()
    merged = [list(intersections[0])]
    for overlap_start, overlap_end in intersections[1:]:
        if overlap_start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], overlap_end)
        else:
            merged.append([overlap_start, overlap_end])
    covered_length = sum(overlap_end - overlap_start for overlap_start, overlap_end in merged)
    return max(0.0, 1.0 - covered_length / length)


def _centerline_record(segment, thickness=None, source_ids=(), closed_endpoints=()):
    return {
        "segment": tuple(float(value) for value in segment),
        "thickness": _valid_wall_thickness(thickness),
        "source_ids": frozenset(source_ids or ()),
        "closed_endpoints": frozenset(int(position) for position in (closed_endpoints or ())),
    }


def _closed_endpoint_points(record):
    segment = record["segment"]
    points = []
    if 1 in record.get("closed_endpoints", ()):
        points.append((segment[0], segment[1]))
    if 2 in record.get("closed_endpoints", ()):
        points.append((segment[2], segment[3]))
    return points


def _closed_endpoints_for_segment(segment, points):
    result = set()
    for point in points:
        if _point_distance((segment[0], segment[1]), point) <= END_CAP_TOLERANCE_MM:
            result.add(1)
        if _point_distance((segment[2], segment[3]), point) <= END_CAP_TOLERANCE_MM:
            result.add(2)
    return frozenset(result)


def _dedupe_centerline_records(records):
    """Deduplicate axes while preferring records that retain a detected thickness."""
    by_key = {}
    order = []
    for record in records:
        segment = tuple(float(value) for value in record["segment"])
        if _segment_length(segment) < MIN_WALL_LENGTH_MM:
            continue
        key = _segment_key(*segment)
        existing = by_key.get(key)
        normalized = _centerline_record(
            segment,
            record.get("thickness"),
            record.get("source_ids"),
            record.get("closed_endpoints"),
        )
        if existing is None:
            by_key[key] = normalized
            order.append(key)
        else:
            source_ids = frozenset(existing.get("source_ids", ())) | frozenset(normalized.get("source_ids", ()))
            closed_points = _closed_endpoint_points(existing) + _closed_endpoint_points(normalized)
            if existing.get("thickness") is None and normalized.get("thickness") is not None:
                normalized["source_ids"] = source_ids
                normalized["closed_endpoints"] = _closed_endpoints_for_segment(normalized["segment"], closed_points)
                by_key[key] = normalized
            else:
                existing["source_ids"] = source_ids
                existing["closed_endpoints"] = _closed_endpoints_for_segment(existing["segment"], closed_points)
    return [by_key[key] for key in order]


def _merge_source_edge_records(records, topology_context=None, topology_segments=None):
    """Merge collinear DXF fragments unless a short perpendicular end cap separates them."""
    result = _dedupe_centerline_records(records)
    changed = True
    while changed:
        changed = False
        for i, first in enumerate(result):
            for j in range(i + 1, len(result)):
                second = result[j]
                first_sources = frozenset(first.get("source_ids", ()))
                second_sources = frozenset(second.get("source_ids", ()))
                merged = _try_merge_segments(first["segment"], second["segment"])
                if merged is None:
                    continue
                different_sources = first_sources and second_sources and not first_sources.intersection(second_sources)
                if different_sources and not _source_fragments_can_merge(first, second, topology_segments):
                    continue
                if not _collinear_bridge_supported(
                    first,
                    second,
                    topology_context,
                    include_boundary=True,
                ):
                    continue
                result[i] = _centerline_record(
                    merged,
                    source_ids=first_sources | second_sources,
                )
                del result[j]
                changed = True
                break
            if changed:
                break
    return _dedupe_centerline_records(result)


def _source_fragments_can_merge(first_record, second_record, topology_segments):
    first = _edge_info(first_record["segment"])
    second = _edge_info(second_record["segment"])
    if first is None or second is None:
        return False
    u = first["u"]
    n = (-u[1], u[0])
    first_range = _projection_range(first, u)
    second_range = _projection_range(second, u)
    overlap = min(first_range[1], second_range[1]) - max(first_range[0], second_range[0])
    if overlap > DUPLICATE_TOLERANCE_MM:
        return True
    join_projection = (
        min(first_range[1], second_range[1]) + max(first_range[0], second_range[0])
    ) / 2.0
    first_axis = (_dot(first["p1"], n) + _dot(first["p2"], n)) / 2.0
    second_axis = (_dot(second["p1"], n) + _dot(second["p2"], n)) / 2.0
    point = (
        u[0] * join_projection + n[0] * (first_axis + second_axis) / 2.0,
        u[1] * join_projection + n[1] * (first_axis + second_axis) / 2.0,
    )
    return not _short_perpendicular_cap_at_point(point, u, topology_segments)


def _short_perpendicular_cap_at_point(point, direction, topology_segments):
    for segment in topology_segments or ():
        info = _edge_info_with_min_length(segment, 1.0)
        if info is None:
            continue
        if info["length"] > MAX_WALL_THICKNESS_MM * 1.25:
            continue
        if abs(_dot(info["u"], direction)) > math.sin(math.radians(ANGLE_TOLERANCE_DEG)):
            continue
        if _point_to_segment_projection(point, segment)[0] <= END_CAP_TOLERANCE_MM:
            return True
    return False


def _cluster_centerline_records(records, separate_by_thickness):
    if not separate_by_thickness:
        return [{"thickness": None, "records": _dedupe_centerline_records(records)}]

    known = sorted(
        (record for record in records if record.get("thickness") is not None),
        key=lambda record: float(record["thickness"]),
    )
    groups = []
    for record in known:
        thickness = float(record["thickness"])
        target = None
        for group in groups:
            if abs(thickness - float(group["thickness"])) <= THICKNESS_CLUSTER_TOLERANCE_MM:
                target = group
                break
        if target is None:
            target = {"thickness": thickness, "records": []}
            groups.append(target)
        target["records"].append(record)
        weights = [_segment_length(item["segment"]) for item in target["records"]]
        target["thickness"] = sum(
            float(item["thickness"]) * weight for item, weight in zip(target["records"], weights)
        ) / max(sum(weights), 1e-9)

    unknown = [record for record in records if record.get("thickness") is None]
    if unknown:
        groups.append({"thickness": None, "records": unknown})
    return groups


def _prepare_centerline_groups(records, separate_by_thickness, topology_context=None):
    groups = _cluster_centerline_records(_dedupe_centerline_records(records), separate_by_thickness)
    for group in groups:
        thickness = group.get("thickness")
        reference_thickness = thickness if thickness is not None else DEFAULT_TOPOLOGY_THICKNESS_MM
        gap_tolerance = min(
            TOPOLOGY_MAX_JOIN_MM,
            max(MERGE_GAP_TOLERANCE_MM, reference_thickness * TOPOLOGY_COLLINEAR_GAP_FACTOR + TOPOLOGY_JOIN_MARGIN_MM),
        )
        group["records"] = _merge_centerline_record_group(
            group["records"],
            gap_tolerance=gap_tolerance,
            topology_context=topology_context,
            group_thickness=thickness,
        )

    joined_endpoint_count = _join_centerline_group_network(groups, topology_context=topology_context)
    for group in groups:
        group["records"] = _dedupe_centerline_records(group["records"])
    groups = [group for group in groups if group["records"]]
    groups.sort(key=lambda group: (group.get("thickness") is None, float(group.get("thickness") or 0.0)))
    return groups, joined_endpoint_count


def _merge_centerline_record_group(records, gap_tolerance, topology_context, group_thickness):
    result = _dedupe_centerline_records(records)
    changed = True
    while changed:
        changed = False
        for i, first in enumerate(result):
            for j in range(i + 1, len(result)):
                second = result[j]
                merged = _try_merge_segments(
                    first["segment"],
                    second["segment"],
                    gap_tolerance=gap_tolerance,
                )
                if merged is None:
                    continue
                if not _collinear_bridge_supported(first, second, topology_context):
                    continue
                source_ids = frozenset(first.get("source_ids", ())) | frozenset(second.get("source_ids", ()))
                closed_points = _closed_endpoint_points(first) + _closed_endpoint_points(second)
                result[i] = _centerline_record(
                    merged,
                    group_thickness,
                    source_ids=source_ids,
                    closed_endpoints=_closed_endpoints_for_segment(merged, closed_points),
                )
                del result[j]
                changed = True
                break
            if changed:
                break
    return _dedupe_centerline_records(result)


def _collinear_bridge_supported(first_record, second_record, topology_context, include_boundary=False):
    first = _edge_info(first_record["segment"])
    second = _edge_info(second_record["segment"])
    if first is None or second is None:
        return False
    u = first["u"]
    n = (-u[1], u[0])
    first_range = _projection_range(first, u)
    second_range = _projection_range(second, u)
    overlap = min(first_range[1], second_range[1]) - max(first_range[0], second_range[0])
    if overlap > DUPLICATE_TOLERANCE_MM:
        return True
    bridge_projection = (
        min(first_range[1], second_range[1]) + max(first_range[0], second_range[0])
    ) / 2.0
    first_axis = (_dot(first["p1"], n) + _dot(first["p2"], n)) / 2.0
    second_axis = (_dot(second["p1"], n) + _dot(second["p2"], n)) / 2.0
    bridge_axis = (first_axis + second_axis) / 2.0
    point = (
        u[0] * bridge_projection + n[0] * bridge_axis,
        u[1] * bridge_projection + n[1] * bridge_axis,
    )
    first_near = _near_endpoint(first_record["segment"], point, float("inf"))
    second_near = _near_endpoint(second_record["segment"], point, float("inf"))
    if first_near is not None and first_near[0] in first_record.get("closed_endpoints", ()):
        return False
    if second_near is not None and second_near[0] in second_record.get("closed_endpoints", ()):
        return False
    return _record_supports_profile_point(
        first_record,
        point,
        topology_context,
        include_boundary=include_boundary,
    ) and _record_supports_profile_point(
        second_record,
        point,
        topology_context,
        include_boundary=include_boundary,
    )


def _join_centerline_group_network(groups, topology_context=None):
    """Snap nearby endpoints to real non-parallel intersections without splitting crossing axes."""
    flattened = []
    for group_index, group in enumerate(groups):
        for record_index, record in enumerate(group["records"]):
            flattened.append((group_index, record_index, record))

    proposals = {}
    for first_index, first_ref in enumerate(flattened):
        first_group, first_record_index, first_record = first_ref
        for second_group, second_record_index, second_record in flattened[first_index + 1 :]:
            first_segment = first_record["segment"]
            second_segment = second_record["segment"]
            intersection = _line_intersection(first_segment, second_segment)
            if intersection is None:
                continue
            point, first_parameter, second_parameter = intersection
            tolerance = _network_join_tolerance(first_record.get("thickness"), second_record.get("thickness"))
            if _parameter_extension_distance(first_segment, first_parameter) > tolerance:
                continue
            if _parameter_extension_distance(second_segment, second_parameter) > tolerance:
                continue

            if _point_is_blocked_by_compact_profile(point, topology_context):
                continue
            first_endpoint = _validated_network_endpoint(
                first_record,
                point,
                first_parameter,
                tolerance,
                topology_context,
            )
            second_endpoint = _validated_network_endpoint(
                second_record,
                point,
                second_parameter,
                tolerance,
                topology_context,
            )
            first_reaches_intersection = 0.0 <= first_parameter <= 1.0 or first_endpoint is not None
            second_reaches_intersection = 0.0 <= second_parameter <= 1.0 or second_endpoint is not None
            if not first_reaches_intersection or not second_reaches_intersection:
                continue
            if first_endpoint is None and second_endpoint is None:
                continue
            if first_endpoint is not None:
                _store_snap_proposal(
                    proposals,
                    (first_group, first_record_index, first_endpoint[0]),
                    first_endpoint[1],
                    point,
                )
            if second_endpoint is not None:
                _store_snap_proposal(
                    proposals,
                    (second_group, second_record_index, second_endpoint[0]),
                    second_endpoint[1],
                    point,
                )

    changed = 0
    for (group_index, record_index, endpoint), (_distance, point) in proposals.items():
        record = groups[group_index]["records"][record_index]
        segment = list(record["segment"])
        offset = 0 if endpoint == 1 else 2
        if _point_distance((segment[offset], segment[offset + 1]), point) > 1e-7:
            segment[offset], segment[offset + 1] = point
            record["segment"] = tuple(segment)
            record["closed_endpoints"] = frozenset(
                position for position in record.get("closed_endpoints", ()) if position != endpoint
            )
            changed += 1
    return changed


def _validated_network_endpoint(record, point, parameter, tolerance, topology_context):
    endpoint = _near_endpoint(record["segment"], point, tolerance)
    if endpoint is None or endpoint[1] <= 1e-7:
        return endpoint

    endpoint_index = endpoint[0]
    is_closed = endpoint_index in record.get("closed_endpoints", ())
    if not is_closed:
        return endpoint if _record_supports_profile_point(record, point, topology_context) else None

    if _endpoint_snap_shortens_segment(parameter, endpoint_index):
        return endpoint if _record_supports_profile_point(record, point, topology_context, include_boundary=True) else None

    # An explicit end cap is a real wall boundary. It may be trimmed inward when
    # the generated axis overshoots a corner, but it must never enter another wall.
    return None


def _endpoint_snap_shortens_segment(parameter, endpoint_index):
    parameter = float(parameter)
    if endpoint_index == 1:
        return 1e-9 < parameter <= 1.0 + 1e-9
    return -1e-9 <= parameter < 1.0 - 1e-9


def _line_intersection(first, second):
    p = (float(first[0]), float(first[1]))
    q = (float(second[0]), float(second[1]))
    r = (float(first[2]) - p[0], float(first[3]) - p[1])
    s = (float(second[2]) - q[0], float(second[3]) - q[1])
    denominator = r[0] * s[1] - r[1] * s[0]
    scale = max(math.hypot(*r) * math.hypot(*s), 1e-9)
    if abs(denominator) / scale <= math.sin(math.radians(ANGLE_TOLERANCE_DEG)):
        return None
    q_minus_p = (q[0] - p[0], q[1] - p[1])
    first_parameter = (q_minus_p[0] * s[1] - q_minus_p[1] * s[0]) / denominator
    second_parameter = (q_minus_p[0] * r[1] - q_minus_p[1] * r[0]) / denominator
    point = (p[0] + first_parameter * r[0], p[1] + first_parameter * r[1])
    return point, first_parameter, second_parameter


def _parameter_extension_distance(segment, parameter):
    if 0.0 <= parameter <= 1.0:
        return 0.0
    multiplier = -parameter if parameter < 0.0 else parameter - 1.0
    return multiplier * _segment_length(segment)


def _network_join_tolerance(first_thickness, second_thickness):
    first = float(first_thickness or DEFAULT_TOPOLOGY_THICKNESS_MM)
    second = float(second_thickness or DEFAULT_TOPOLOGY_THICKNESS_MM)
    return min(
        TOPOLOGY_MAX_JOIN_MM,
        max(TOPOLOGY_MIN_JOIN_MM, 0.75 * (first + second) + TOPOLOGY_JOIN_MARGIN_MM),
    )


def _near_endpoint(segment, point, tolerance):
    distances = (
        _point_distance((segment[0], segment[1]), point),
        _point_distance((segment[2], segment[3]), point),
    )
    endpoint_index = 1 if distances[0] <= distances[1] else 2
    distance = min(distances)
    return (endpoint_index, distance) if distance <= tolerance else None


def _store_snap_proposal(proposals, key, distance, point):
    existing = proposals.get(key)
    if existing is None or distance < existing[0]:
        proposals[key] = (distance, point)


def _merge_collinear_segments(segments, gap_tolerance=MERGE_GAP_TOLERANCE_MM):
    result = _dedupe_segments(segments)
    changed = True
    while changed:
        changed = False
        for i, first in enumerate(result):
            for j in range(i + 1, len(result)):
                merged = _try_merge_segments(first, result[j], gap_tolerance=gap_tolerance)
                if merged is None:
                    continue
                result[i] = merged
                del result[j]
                changed = True
                break
            if changed:
                break
    return _dedupe_segments(result)


def _try_merge_segments(
    first_segment,
    second_segment,
    gap_tolerance=MERGE_GAP_TOLERANCE_MM,
    minimum_length=MIN_WALL_LENGTH_MM,
):
    first = _edge_info_with_min_length(first_segment, minimum_length)
    second = _edge_info_with_min_length(second_segment, minimum_length)
    if first is None or second is None:
        return None
    if _angle_difference(first["angle"], second["angle"]) > math.radians(MERGE_ANGLE_TOLERANCE_DEG):
        return None

    u = first["u"]
    n = (-u[1], u[0])
    first_axis = (_dot(first["p1"], n) + _dot(first["p2"], n)) / 2.0
    second_axis = (_dot(second["p1"], n) + _dot(second["p2"], n)) / 2.0
    if abs(second_axis - first_axis) > MERGE_OFFSET_TOLERANCE_MM:
        return None
    first_range = _projection_range(first, u)
    second_range = _projection_range(second, u)
    gap = max(first_range[0], second_range[0]) - min(first_range[1], second_range[1])
    if gap > float(gap_tolerance):
        return None
    start = min(first_range[0], second_range[0])
    end = max(first_range[1], second_range[1])
    center_axis = (first_axis + second_axis) / 2.0
    return (
        u[0] * start + n[0] * center_axis,
        u[1] * start + n[1] * center_axis,
        u[0] * end + n[0] * center_axis,
        u[1] * end + n[1] * center_axis,
    )


def _dedupe_segments(segments):
    seen = set()
    result = []
    for segment in segments:
        x1, y1, x2, y2 = [float(v) for v in segment]
        if math.hypot(x2 - x1, y2 - y1) < MIN_WALL_LENGTH_MM:
            continue
        key = _segment_key(x1, y1, x2, y2)
        if key in seen:
            continue
        seen.add(key)
        result.append((x1, y1, x2, y2))
    return result


def _round_key(value):
    return int(round(float(value) / DUPLICATE_TOLERANCE_MM))


def _segment_key(x1, y1, x2, y2):
    a = (_round_key(x1), _round_key(y1))
    b = (_round_key(x2), _round_key(y2))
    return (a, b) if a <= b else (b, a)


def _thickness_label_suffix(thickness):
    if thickness is None:
        return "Espesor_NoDetectado"
    rounded = int(round(float(thickness)))
    return "Espesor_%dmm" % rounded


def _create_centerline_sketch(
    doc,
    parent_group,
    source_labels,
    extraction_mode,
    suffix="",
    thickness=None,
    color_index=0,
):
    label = _unique_sketch_label(doc, source_labels, suffix)
    sketch = doc.addObject("Sketcher::SketchObject", safe_name(label))
    sketch.Label = label
    msg("Sketch creado: %s" % label)
    try:
        sketch.Placement = FreeCAD.Placement()
    except Exception:
        pass
    try:
        if sketch not in list(getattr(parent_group, "Group", []) or []):
            parent_group.addObject(sketch)
    except Exception:
        pass
    source_text = ", ".join(source_labels) if source_labels else "Seleccion"
    element_type = source_labels[0] if len(source_labels) == 1 else "Por definir"
    set_prop(sketch, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "centerlines")
    set_prop(sketch, "App::PropertyString", "FA_System", "FacilArquitectura", "Sistema", "reference_geometry")
    set_prop(
        sketch,
        "App::PropertyString",
        "FA_SourceSelection",
        "FacilArquitectura",
        "Layer, grupo u objetos seleccionados",
        source_text,
    )
    set_prop(
        sketch,
        "App::PropertyString",
        "FA_ElementType",
        "FacilArquitectura",
        "Tipo de elemento representado",
        element_type,
    )
    set_prop(
        sketch,
        "App::PropertyString",
        "FA_ExtractionMode",
        "FacilArquitectura",
        "Metodo usado para obtener los centros",
        extraction_mode,
    )
    colors = (
        (0.90, 0.10, 0.10),
        (0.10, 0.45, 0.85),
        (0.15, 0.65, 0.30),
        (0.90, 0.55, 0.08),
        (0.55, 0.25, 0.75),
    )
    color = colors[int(color_index) % len(colors)]
    try:
        sketch.ViewObject.LineColor = color
        sketch.ViewObject.ShapeColor = color
        sketch.ViewObject.LineWidth = 3.0
    except Exception:
        pass
    set_prop(
        sketch,
        "App::PropertyBool",
        "FA_ThicknessDetected",
        "FacilArquitectura",
        "El espesor fue detectado en la geometria fuente",
        thickness is not None,
    )
    set_prop(
        sketch,
        "App::PropertyLength",
        "FA_WallThickness",
        "FacilArquitectura",
        "Espesor representativo del grupo",
        float(thickness or 0.0),
    )
    return sketch


def _add_line(sketch, x1, y1, x2, y2):
    line = Part.LineSegment(FreeCAD.Vector(float(x1), float(y1), 0.0), FreeCAD.Vector(float(x2), float(y2), 0.0))
    try:
        return sketch.addGeometry(line, False)
    except TypeError:
        return sketch.addGeometry(line)


def _set_centerline_properties(
    sketch,
    source_objects,
    raw_edges,
    ignored_compact_profiles,
    segments,
    extraction_strategy,
    thickness,
    constraint_count,
    joined_endpoint_count,
):
    set_prop(
        sketch,
        "App::PropertyString",
        "FA_ExtractionStrategy",
        "FacilArquitectura",
        "Estrategia que genero estos centros",
        str(extraction_strategy),
    )
    set_prop(
        sketch,
        "App::PropertyStringList",
        "FA_SourceObjectNames",
        "FacilArquitectura",
        "Nombres internos de los objetos fuente para reejecucion segura",
        _source_object_names(source_objects),
    )
    set_prop(sketch, "App::PropertyInteger", "FA_SourceObjectCount", "FacilArquitectura", "Objetos fuente", len(source_objects))
    set_prop(sketch, "App::PropertyInteger", "FA_RawEdgeCount", "FacilArquitectura", "Bordes analizados", len(raw_edges))
    set_prop(
        sketch,
        "App::PropertyInteger",
        "FA_IgnoredCompactCount",
        "FacilArquitectura",
        "Contornos compactos ambiguos omitidos",
        ignored_compact_profiles,
    )
    set_prop(sketch, "App::PropertyInteger", "FA_CenterlineCount", "FacilArquitectura", "Lineas de centro", len(segments))
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
        "FA_JoinedEndpointCount",
        "FacilArquitectura",
        "Extremos ajustados en toda la red extraida",
        joined_endpoint_count,
    )
    set_prop(
        sketch,
        "App::PropertyLength",
        "FA_ThicknessClusterTolerance",
        "FacilArquitectura",
        "Tolerancia para agrupar espesores similares",
        THICKNESS_CLUSTER_TOLERANCE_MM,
    )
    if extraction_strategy == "profile_axis":
        set_prop(
            sketch,
            "App::PropertyLength",
            "FA_ProfileGroupingGap",
            "FacilArquitectura",
            "Distancia usada para agrupar detalles del mismo perfil",
            PROFILE_COMPONENT_GAP_MM,
        )
    elif extraction_strategy == "door_swing":
        set_prop(
            sketch,
            "App::PropertyLength",
            "FA_DoorGroupingGap",
            "FacilArquitectura",
            "Distancia usada para agrupar detalles de la misma puerta",
            DOOR_COMPONENT_GAP_MM,
        )
    if thickness is not None:
        msg("Grupo de espesor detectado: %.1f mm | lineas: %d" % (float(thickness), len(segments)))


def _populate_parametric_sketch(sketch, segments):
    geometry_indices = []
    clean_segments = []
    for segment in segments:
        index = _add_line(sketch, *segment)
        if index is None:
            index = len(geometry_indices)
        geometry_indices.append(int(index))
        clean_segments.append(tuple(float(value) for value in segment))

    constraint_count = 0
    axis_limit = math.sin(math.radians(PARAMETRIC_AXIS_TOLERANCE_DEG))
    for geometry_index, segment in zip(geometry_indices, clean_segments):
        dx = segment[2] - segment[0]
        dy = segment[3] - segment[1]
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            continue
        if abs(dy) / length <= axis_limit:
            constraint_count += _add_constraint(sketch, Sketcher.Constraint("Horizontal", geometry_index))
        elif abs(dx) / length <= axis_limit:
            constraint_count += _add_constraint(sketch, Sketcher.Constraint("Vertical", geometry_index))

    endpoints = []
    for geometry_index, segment in zip(geometry_indices, clean_segments):
        endpoints.append((geometry_index, 1, (segment[0], segment[1])))
        endpoints.append((geometry_index, 2, (segment[2], segment[3])))
    endpoint_groups = _group_coincident_endpoints(endpoints)
    endpoints_with_coincident = set()
    for endpoint_group in endpoint_groups:
        if len(endpoint_group) < 2:
            continue
        anchor = endpoint_group[0]
        for endpoint in endpoint_group[1:]:
            if anchor[0] == endpoint[0]:
                continue
            constraint_count += _add_constraint(
                sketch,
                Sketcher.Constraint("Coincident", anchor[0], anchor[1], endpoint[0], endpoint[1]),
            )
            endpoints_with_coincident.add((anchor[0], anchor[1]))
            endpoints_with_coincident.add((endpoint[0], endpoint[1]))

    for geometry_index, position, point in endpoints:
        if (geometry_index, position) in endpoints_with_coincident:
            continue
        best = None
        for other_index, other_segment in zip(geometry_indices, clean_segments):
            if other_index == geometry_index:
                continue
            distance, parameter = _point_to_segment_projection(point, other_segment)
            if distance > PARAMETRIC_POINT_TOLERANCE_MM or parameter <= 1e-6 or parameter >= 1.0 - 1e-6:
                continue
            if best is None or distance < best[0]:
                best = (distance, other_index)
        if best is not None:
            constraint_count += _add_constraint(
                sketch,
                Sketcher.Constraint("PointOnObject", geometry_index, position, best[1]),
            )
    return constraint_count


def _group_coincident_endpoints(endpoints):
    groups = []
    for endpoint in endpoints:
        matching = None
        for group in groups:
            if _point_distance(endpoint[2], group[0][2]) <= PARAMETRIC_POINT_TOLERANCE_MM:
                matching = group
                break
        if matching is None:
            groups.append([endpoint])
        else:
            matching.append(endpoint)
    return groups


def _point_to_segment_projection(point, segment):
    dx = float(segment[2]) - float(segment[0])
    dy = float(segment[3]) - float(segment[1])
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-12:
        return _point_distance(point, (segment[0], segment[1])), 0.0
    parameter = ((float(point[0]) - float(segment[0])) * dx + (float(point[1]) - float(segment[1])) * dy) / length_squared
    clamped = max(0.0, min(1.0, parameter))
    projected = (float(segment[0]) + clamped * dx, float(segment[1]) + clamped * dy)
    return _point_distance(point, projected), parameter


def _add_constraint(sketch, constraint):
    try:
        result = sketch.addConstraint(constraint)
        return 0 if isinstance(result, int) and result < 0 else 1
    except Exception as exc:
        warn("Restriccion omitida para evitar sobrerrestriccion: %s" % exc)
        return 0
