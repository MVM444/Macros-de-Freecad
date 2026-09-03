"""Coordinator services for rebuilding a native BIM model from Sketches.

Descripcion: clasifica Sketches y coordina estructura, muros, columnas, puertas y
ventanas reutilizando los servicios especializados de FacilArquitecturaWB.
Objetivo: reconstruccion BIM reproducible sin copiar geometria ni crear FA_Project.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-09-01 14:35 America/Costa_Rica.
Version: 0.2.0.
Instrucciones de mantenimiento: este modulo solo coordina; no duplicar algoritmos
de muros, columnas o aberturas. El comando GUI administra la transaccion.
"""

from __future__ import annotations

import unicodedata

from .axis_utils import create_bim_axes_and_columns_from_sketch
from .bim_structure_utils import adopt_auxiliary_sources, ensure_bim_structure
from .bim_utils import (
    create_walls_from_centerline_sketches,
    prepare_sketches_as_wall_centerlines,
    sketches_requiring_wall_metadata,
    wall_thickness_from_sketch,
)
from .command_errors import UserFacingError
from .opening_utils import create_openings_from_centerlines, remove_generated_openings


ROLES = ("walls", "columns", "doors", "windows", "slab", "reference")


def collect_document_sketches(doc):
    """Return every real Sketcher object, excluding generated opening bases."""
    result = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_sketch(obj):
            continue
        role = _text(getattr(obj, "FA_Role", ""))
        if role in ("door_base", "window_base"):
            continue
        result.append(obj)
    return result


def classify_sketch(sketch):
    """Return scored role candidates with evidence, ordered by confidence."""
    fields = {
        "name": _text(getattr(sketch, "Name", "")),
        "label": _text(getattr(sketch, "Label", "")),
        "role": _text(getattr(sketch, "FA_Role", "")),
        "kind": _text(getattr(sketch, "FA_CenterlineKind", "")),
        "element": _text(getattr(sketch, "FA_ElementType", "")),
    }
    combined = " ".join(fields.values())
    scores = {role: 0 for role in ROLES}
    evidence = {role: [] for role in ROLES}

    def add(role, points, reason):
        scores[role] += int(points)
        evidence[role].append(str(reason))

    metadata_words = {
        "walls": ("wall", "walls", "muro", "muros", "pared", "paredes"),
        "columns": ("column", "columns", "columna", "columnas"),
        "doors": ("door", "doors", "puerta", "puertas"),
        "windows": ("window", "windows", "ventana", "ventanas", "ventanal", "ventanales"),
        "slab": ("slab", "losa", "piso", "floor"),
        "reference": ("reference", "referencia", "plataforma"),
    }
    for role, words in metadata_words.items():
        if any(word in fields["element"] for word in words):
            add(role, 500, "FA_ElementType")
        if any(word in fields["role"] for word in words):
            add(role, 450, "FA_Role")
        if any(word in fields["kind"] for word in words):
            add(role, 300, "FA_CenterlineKind")
        if any(word in (fields["name"] + " " + fields["label"]) for word in words):
            add(role, 350, "Name/Label")

    thickness = wall_thickness_from_sketch(sketch)
    if thickness > 0.0:
        add("walls", 650, "FA_WallThickness=%.1f mm" % thickness)
        scores["doors"] -= 800
        scores["windows"] -= 800
    compact = combined.replace("_", "").replace("-", "").replace(" ", "")
    if "gridwalltrace" in compact:
        add("walls", 900, "traza maestra FA_GridWallTrace")
    if "cerrado" in combined:
        add("walls", 120, "Sketch cerrado de muro")
    if "centro" in combined and "columna" in combined:
        add("columns", 300, "centros de columnas")
    if "seleccion" in combined and max(scores.values()) <= 300:
        for role in ROLES:
            scores[role] = min(scores[role], 40)
        evidence["reference"].append("nombre generico: requiere asignacion manual")

    ordered = sorted(
        (
            {"role": role, "score": score, "evidence": tuple(evidence[role])}
            for role, score in scores.items()
            if score > 0
        ),
        key=lambda item: (-item["score"], ROLES.index(item["role"])),
    )
    suggested = ordered[0]["role"] if ordered and ordered[0]["score"] >= 100 else None
    return {
        "sketch": sketch,
        "suggested_role": suggested,
        "candidates": ordered,
        "reason": ", ".join(ordered[0]["evidence"]) if suggested else "sin evidencia suficiente",
    }


def suggest_rebuild_assignments(doc):
    """Suggest one primary Sketch per role and every confident window Sketch."""
    records = [classify_sketch(sketch) for sketch in collect_document_sketches(doc)]
    by_role = {role: [] for role in ROLES}
    for record in records:
        for candidate in record["candidates"]:
            by_role[candidate["role"]].append((candidate["score"], record["sketch"], candidate))
    for role in ROLES:
        by_role[role].sort(key=lambda item: (-item[0], _label(item[1]).casefold()))

    assignments = {
        "walls": _first_confident(by_role["walls"]),
        "columns": _first_confident(by_role["columns"]),
        "doors": _first_confident(by_role["doors"]),
        "windows": [item[1] for item in by_role["windows"] if item[0] >= 300],
        "slab": _first_confident(by_role["slab"]),
        "references": [item[1] for item in by_role["reference"] if item[0] >= 300],
    }
    return {"records": records, "by_role": by_role, "assignments": assignments}


def rebuild_bim_model(doc, assignments, options):
    """Run the complete native BIM rebuild using existing specialized services."""
    walls_source = _one_or_none(assignments.get("walls"))
    if walls_source is None:
        raise UserFacingError("Asigne un Sketch fuente para los muros.")
    columns_source = _one_or_none(assignments.get("columns"))
    doors_source = _one_or_none(assignments.get("doors"))
    window_sources = _unique(assignments.get("windows") or [])
    reference_sources = _unique(assignments.get("references") or [])

    # Openings depend on their Wall host. Remove only rebuild-generated openings
    # before replacing the Wall, then recreate them later in the same transaction.
    if doors_source is not None:
        remove_generated_openings(doc, [doors_source], "door")
    if window_sources:
        remove_generated_openings(doc, window_sources, "window")

    structure = ensure_bim_structure(
        doc,
        building_name=options.get("building_name", "Edificio"),
        level_name=options.get("level_name", "Nivel 00"),
        elevation_mm=float(options.get("elevation_mm", 0.0)),
        building=options.get("building"),
        level=options.get("level"),
        update_existing=bool(options.get("update_structure", False)),
    )
    level = structure["level"]
    wall_params = {
        "wall_height_mm": float(options.get("wall_height_mm", 3000.0)),
        "int_wall_thickness_mm": float(options.get("wall_thickness_mm", 150.0)),
        "ext_wall_thickness_mm": float(options.get("wall_thickness_mm", 150.0)),
    }
    if sketches_requiring_wall_metadata([walls_source]):
        prepare_sketches_as_wall_centerlines(
            [walls_source],
            float(options.get("wall_thickness_mm", 150.0)),
            float(options.get("wall_height_mm", 3000.0)),
            str(options.get("wall_type", "interior")),
        )
    walls = create_walls_from_centerline_sketches(
        doc, level, [walls_source], wall_params, target_level=level
    )

    columns_result = None
    if columns_source is not None:
        column_params = {
            "axis_extension_mm": float(options.get("axis_extension_mm", 1000.0)),
            "axis_cluster_tolerance_mm": float(options.get("axis_cluster_tolerance_mm", 10.0)),
            "column_width_mm": float(options.get("column_width_mm", 400.0)),
            "column_depth_mm": float(options.get("column_depth_mm", 400.0)),
            "column_height_mm": float(options.get("column_height_mm", 3000.0)),
        }
        columns_result = create_bim_axes_and_columns_from_sketch(
            doc, level, columns_source, column_params
        )

    doors = []
    door_summary = None
    if doors_source is not None:
        doors, door_summary = create_openings_from_centerlines(
            doc,
            level,
            [doors_source],
            walls,
            "door",
            height_mm=float(options.get("door_height_mm", 2100.0)),
            host_tolerance_mm=float(options.get("host_tolerance_mm", 250.0)),
            replace_existing=True,
        )

    windows = []
    window_summary = None
    if window_sources:
        windows, window_summary = create_openings_from_centerlines(
            doc,
            level,
            window_sources,
            walls,
            "window",
            height_mm=float(options.get("window_height_mm", 1200.0)),
            sill_mm=float(options.get("window_sill_mm", 900.0)),
            host_tolerance_mm=float(options.get("host_tolerance_mm", 250.0)),
            replace_existing=True,
        )

    organized_sources = _unique(
        [walls_source, columns_source, doors_source] + window_sources + reference_sources
    )
    adopt_auxiliary_sources(doc, level, organized_sources, allow_any_type=True)
    doc.recompute()
    return {
        "building": structure["building"],
        "level": level,
        "walls": walls,
        "columns": columns_result,
        "doors": doors,
        "windows": windows,
        "door_summary": door_summary,
        "window_summary": window_summary,
        "organized_sources": organized_sources,
        "slab_status": "deferred",
    }


def _first_confident(items):
    return items[0][1] if items and items[0][0] >= 100 else None


def _one_or_none(value):
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def _unique(objects):
    result = []
    seen = set()
    for obj in objects or []:
        if obj is None:
            continue
        key = str(getattr(obj, "Name", "") or id(obj))
        if key not in seen:
            seen.add(key)
            result.append(obj)
    return result


def _is_sketch(obj):
    return str(getattr(obj, "TypeId", "") or "").startswith("Sketcher::")


def _label(obj):
    return str(getattr(obj, "Label", getattr(obj, "Name", "Sketch")) or "Sketch")


def _text(value):
    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))
