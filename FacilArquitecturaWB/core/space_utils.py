"""Utilidades reutilizables para crear y actualizar Espacios BIM nativos desde recintos 2D.

Nombre: space_utils.py
Proposito: convertir recintos cerrados documentales en ``Arch Space`` nativos
sin duplicar la logica dentro de la demostracion automatica.
Funcion principal: derivar registros de recinto desde un Sketch, planificar su
matching contra Espacios existentes y materializar o actualizar sus volumenes BIM
sin destruir la identidad de los objetos ya enlazados por otros Workbenches.
Instrucciones relevantes para futuras modificaciones:
- Mantener la deteccion de recintos en ``room_utils``; este modulo solo adapta
  esos recintos a Arch Space.
- Aceptar registros simples compatibles con JSON para permitir reutilizacion por
  la demo, comandos y MCP.
- No depender de FreeCADGui ni Qt.
- Las actualizaciones deben ser no destructivas por defecto: conservar ``Name`` y
  ``PropertyLink`` de un Space reconocido; los casos ambiguos no se modifican.
- Mantener ``dry_run`` para diagnostico previo y trazabilidad MATCH/CAMBIO/NO_MATCH/AMBIGUO.
- La unica integracion externa admitida aqui es el hint booleano `GameExportExclude`,
  sin importar ni depender de GameEngineExportWB. Debe aplicarse tanto al Space como
  a su Base solida para evitar geometria auxiliar duplicada en exportaciones.
Version: 0.3.1
Fecha y hora: 2026-09-01 America/Costa_Rica
"""

from __future__ import annotations

import json
import math
import uuid

import Arch
import FreeCAD as App
import Part

from .bim_structure_utils import add_to_level
from .project_structure import ensure_group, msg, set_prop, warn
from .room_utils import (
    DEFAULT_MIN_ROOM_AREA_M2,
    DEFAULT_SNAP_TOLERANCE_MM,
    build_room_topology,
)


SPACE_GENERATOR = "FA_CreateBIMSpaces"
SPACE_GROUP_NAME = "FA_BIMSpaces"
SPACE_GROUP_LABEL = "Espacios BIM"
SPACE_SCHEMA_VERSION = 3
MATCH_STATUS = ("MATCH", "CAMBIO", "NO_MATCH", "AMBIGUO")
DEFAULT_MIN_IOU = 0.55
DEFAULT_MIN_OVERLAP = 0.70
DEFAULT_AMBIGUITY_MARGIN = 0.08


def _quantity_value(value, default=0.0):
    if value is None:
        return float(default)
    try:
        return float(value.Value)
    except Exception:
        try:
            return float(value)
        except Exception:
            return float(default)


def is_closed_room_sketch(obj):
    """Return True for a room Sketch produced by the FA room detector."""
    if obj is None:
        return False
    if not str(getattr(obj, "TypeId", "") or "").startswith("Sketcher::"):
        return False
    role = str(getattr(obj, "FA_Role", "") or "")
    count = int(getattr(obj, "FA_RoomCount", 0) or 0)
    return role == "closed_rooms" or count > 0


def collect_closed_room_sketches(doc, selection=None):
    """Collect explicit room Sketches first, otherwise discover them in the document."""
    selected = [obj for obj in list(selection or []) if is_closed_room_sketch(obj)]
    if selected:
        return selected
    return [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if is_closed_room_sketch(obj)
    ]


def _sketch_segments_global(sketch):
    placement = getattr(sketch, "Placement", None)
    result = []
    z_values = []
    for geometry in list(getattr(sketch, "Geometry", []) or []):
        first = getattr(geometry, "StartPoint", None)
        second = getattr(geometry, "EndPoint", None)
        if first is None or second is None:
            continue
        first_vec = App.Vector(float(first.x), float(first.y), float(getattr(first, "z", 0.0)))
        second_vec = App.Vector(float(second.x), float(second.y), float(getattr(second, "z", 0.0)))
        if placement is not None:
            try:
                first_vec = placement.multVec(first_vec)
                second_vec = placement.multVec(second_vec)
            except Exception:
                pass
        result.append((first_vec.x, first_vec.y, second_vec.x, second_vec.y))
        z_values.extend([float(first_vec.z), float(second_vec.z)])
    base_z = sum(z_values) / float(len(z_values)) if z_values else 0.0
    return result, base_z


def _polygon_area_centroid(points):
    """Return absolute area (mm2) and XY centroid for a polygon without FreeCAD objects."""
    pts = [(float(p[0]), float(p[1])) for p in list(points or [])]
    if len(pts) < 3:
        return 0.0, (0.0, 0.0)
    cross_sum = 0.0
    cx_sum = 0.0
    cy_sum = 0.0
    for index, first in enumerate(pts):
        second = pts[(index + 1) % len(pts)]
        cross_value = first[0] * second[1] - second[0] * first[1]
        cross_sum += cross_value
        cx_sum += (first[0] + second[0]) * cross_value
        cy_sum += (first[1] + second[1]) * cross_value
    signed_area = cross_sum * 0.5
    if abs(signed_area) <= 1.0e-9:
        return 0.0, (
            sum(point[0] for point in pts) / float(len(pts)),
            sum(point[1] for point in pts) / float(len(pts)),
        )
    factor = 1.0 / (6.0 * signed_area)
    return abs(signed_area), (cx_sum * factor, cy_sum * factor)


def room_records_from_sketch(room_sketch, default_height_mm=2700.0):
    """Return JSON-compatible room records reconstructed from one room Sketch.

    ``id`` is intentionally provisional. Once a record matches an existing Space,
    the persistent ``FA_RoomID``/``FA_RoomUID`` of that Space remains authoritative.
    """
    segments, base_z = _sketch_segments_global(room_sketch)
    if not segments:
        raise RuntimeError("El Sketch de recintos no contiene segmentos lineales utilizables.")
    snap_tolerance = _quantity_value(
        getattr(room_sketch, "FA_SnapTolerance", None), DEFAULT_SNAP_TOLERANCE_MM
    )
    min_area_m2 = _quantity_value(
        getattr(room_sketch, "FA_MinRoomAreaM2", None), DEFAULT_MIN_ROOM_AREA_M2
    )
    topology = build_room_topology(
        segments,
        snap_tolerance=snap_tolerance,
        minimum_room_area_mm2=min_area_m2 * 1000000.0,
    )
    if not topology.get("faces"):
        raise RuntimeError("No se pudieron reconstruir recintos cerrados desde el Sketch seleccionado.")
    records = []
    for index, face in enumerate(topology["faces"], 1):
        points = [[float(x), float(y)] for x, y in face["points"]]
        area_mm2, centroid = _polygon_area_centroid(points)
        records.append(
            {
                "schema_version": SPACE_SCHEMA_VERSION,
                "id": "R%02d" % index,
                "name": "Recinto %02d" % index,
                "polygon_mm": points,
                "area_m2": float(face["area"]) / 1000000.0,
                "centroid_mm": [float(centroid[0]), float(centroid[1])],
                "perimeter_m": _polygon_perimeter_mm(points) / 1000.0,
                "space_height_mm": float(default_height_mm),
                "base_z_mm": float(base_z),
            }
        )
        if area_mm2 > 0.0:
            records[-1]["area_m2"] = area_mm2 / 1000000.0
    return records


def _polygon_perimeter_mm(points):
    pts = [(float(p[0]), float(p[1])) for p in list(points or [])]
    if len(pts) < 2:
        return 0.0
    return sum(
        math.hypot(
            pts[(index + 1) % len(pts)][0] - point[0],
            pts[(index + 1) % len(pts)][1] - point[1],
        )
        for index, point in enumerate(pts)
    )


def _face_from_points(points, base_z=0.0):
    pts = list(points or [])
    if len(pts) < 3:
        raise RuntimeError("Poligono con menos de tres vertices.")
    vectors = [App.Vector(float(x), float(y), float(base_z)) for x, y in pts]
    wire = Part.makePolygon(vectors + [vectors[0]])
    face = Part.Face(wire)
    if face.isNull() or float(face.Area) <= 1.0:
        raise RuntimeError("Poligono sin cara valida.")
    return face


def _face_from_record(record):
    points = list(record.get("polygon_mm") or [])
    if len(points) < 3:
        raise RuntimeError("Recinto sin poligono suficiente: %s" % record.get("name", "?"))
    return _face_from_points(points, float(record.get("base_z_mm", 0.0) or 0.0))


def _safe_polygon_json(obj):
    raw = str(getattr(obj, "FA_FloorPolygonJSON", "") or "")
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except Exception:
        return []
    result = []
    for point in list(value or []):
        try:
            result.append([float(point[0]), float(point[1])])
        except Exception:
            return []
    return result if len(result) >= 3 else []


def _source_matches(obj, source_room_sketch):
    target_name = str(getattr(source_room_sketch, "Name", "") or "")
    source = getattr(obj, "FA_SourceRoomSketch", None)
    source_name = str(getattr(source, "Name", "") or "")
    return not target_name or source_name == target_name


def _space_base(space, doc, source_room_sketch=None, generator=SPACE_GENERATOR):
    for prop_name in ("Base", "BaseGeometry"):
        base = getattr(space, prop_name, None)
        if base is not None:
            return base
    room_uid = str(getattr(space, "FA_RoomUID", "") or "")
    room_id = str(getattr(space, "FA_RoomID", "") or "")
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "FA_GeneratedBy", "") or "") != str(generator):
            continue
        if str(getattr(obj, "FA_Role", "") or "") != "space_base":
            continue
        if source_room_sketch is not None and not _source_matches(obj, source_room_sketch):
            continue
        if room_uid and str(getattr(obj, "FA_RoomUID", "") or "") == room_uid:
            return obj
        if room_id and str(getattr(obj, "FA_RoomID", "") or "") == room_id:
            return obj
    return None


def collect_existing_spaces(doc, source_room_sketch, generator=SPACE_GENERATOR):
    """Return versioned FA Space descriptors for one documentary room Sketch.

    The demo and the interactive command share this service but use different
    ``FA_GeneratedBy`` values.  Schema metadata plus the canonical role/source
    identify a compatible FA Space without admitting unrelated Arch Spaces.
    """
    result = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "FA_Role", "") or "") != "bim_space":
            continue
        object_generator = str(getattr(obj, "FA_GeneratedBy", "") or "")
        schema_version = int(getattr(obj, "FA_SpaceSchemaVersion", 0) or 0)
        if schema_version <= 0 and object_generator not in {str(generator), SPACE_GENERATOR}:
            continue
        if not _source_matches(obj, source_room_sketch):
            continue
        points = _safe_polygon_json(obj)
        if not points:
            base = _space_base(obj, doc, source_room_sketch, generator=generator)
            shape = getattr(base, "Shape", None) if base is not None else None
            try:
                footprint = min(
                    [face for face in list(shape.Faces or []) if abs(float(face.normalAt(0, 0).z)) > 0.9],
                    key=lambda face: float(face.CenterOfMass.z),
                )
                wire = footprint.OuterWire
                points = [[float(vertex.Point.x), float(vertex.Point.y)] for vertex in wire.Vertexes]
                if len(points) > 1 and points[0] == points[-1]:
                    points.pop()
            except Exception:
                points = []
        area_mm2, centroid = _polygon_area_centroid(points)
        result.append(
            {
                "space": obj,
                "base": _space_base(obj, doc, source_room_sketch, generator=generator),
                "room_id": str(getattr(obj, "FA_RoomID", "") or ""),
                "room_uid": str(getattr(obj, "FA_RoomUID", "") or ""),
                "room_name": str(getattr(obj, "FA_RoomName", "") or ""),
                "polygon_mm": points,
                "area_mm2": area_mm2,
                "centroid_mm": centroid,
                "height_mm": _quantity_value(getattr(obj, "FA_SpaceHeight", None), 0.0),
            }
        )
    return result


def _overlap_metrics(points_a, points_b):
    """Return geometric overlap metrics for two planar polygons."""
    if len(points_a or []) < 3 or len(points_b or []) < 3:
        return {"intersection_mm2": 0.0, "iou": 0.0, "overlap": 0.0}
    try:
        first = _face_from_points(points_a, 0.0)
        second = _face_from_points(points_b, 0.0)
        intersection = first.common(second)
        intersection_area = max(0.0, float(getattr(intersection, "Area", 0.0) or 0.0))
        first_area = max(0.0, float(first.Area))
        second_area = max(0.0, float(second.Area))
    except Exception:
        first_area, _ = _polygon_area_centroid(points_a)
        second_area, _ = _polygon_area_centroid(points_b)
        intersection_area = 0.0
    union = max(first_area + second_area - intersection_area, 0.0)
    smaller = min(first_area, second_area)
    return {
        "intersection_mm2": intersection_area,
        "iou": intersection_area / union if union > 1.0 else 0.0,
        "overlap": intersection_area / smaller if smaller > 1.0 else 0.0,
    }


def _match_candidate(record, existing):
    new_points = list(record.get("polygon_mm") or [])
    old_points = list(existing.get("polygon_mm") or [])
    overlap = _overlap_metrics(new_points, old_points)
    new_area, new_centroid = _polygon_area_centroid(new_points)
    old_area = float(existing.get("area_mm2") or 0.0)
    old_centroid = existing.get("centroid_mm") or (0.0, 0.0)
    area_ratio = min(new_area, old_area) / max(new_area, old_area) if new_area > 1.0 and old_area > 1.0 else 0.0
    centroid_distance = math.hypot(new_centroid[0] - old_centroid[0], new_centroid[1] - old_centroid[1])
    characteristic = max(math.sqrt(max(min(new_area, old_area), 1.0)), 500.0)
    centroid_score = max(0.0, 1.0 - centroid_distance / characteristic)
    id_bonus = 0.03 if str(record.get("id") or "") == str(existing.get("room_id") or "") and overlap["iou"] >= 0.20 else 0.0
    score = min(
        1.0,
        0.55 * overlap["iou"]
        + 0.30 * overlap["overlap"]
        + 0.10 * area_ratio
        + 0.05 * centroid_score
        + id_bonus,
    )
    return {
        "score": score,
        "iou": overlap["iou"],
        "overlap": overlap["overlap"],
        "area_ratio": area_ratio,
        "centroid_distance_mm": centroid_distance,
        "existing": existing,
    }


def _record_changed(record, candidate, default_height_mm):
    height = float(record.get("space_height_mm", default_height_mm) or default_height_mm)
    previous_height = float(candidate["existing"].get("height_mm") or 0.0)
    return (
        candidate["iou"] < 0.995
        or candidate["overlap"] < 0.995
        or candidate["area_ratio"] < 0.999
        or abs(height - previous_height) > 0.1
    )


def plan_bim_space_updates(
    doc,
    room_sketch,
    room_records,
    default_height_mm=2700.0,
    generator=SPACE_GENERATOR,
    min_iou=DEFAULT_MIN_IOU,
    min_overlap=DEFAULT_MIN_OVERLAP,
    ambiguity_margin=DEFAULT_AMBIGUITY_MARGIN,
):
    """Plan non-destructive Space synchronization without changing the document."""
    records = [dict(record) for record in list(room_records or [])]
    existing = collect_existing_spaces(doc, room_sketch, generator=generator)
    entries = []
    top_claims = {}
    for index, record in enumerate(records):
        candidates = [_match_candidate(record, item) for item in existing]
        candidates.sort(key=lambda item: item["score"], reverse=True)
        eligible = [
            item
            for item in candidates
            if item["iou"] >= float(min_iou) and item["overlap"] >= float(min_overlap)
        ]
        if not eligible:
            entries.append({"index": index, "record": record, "status": "NO_MATCH", "candidate": None, "candidates": candidates[:3]})
            continue
        first = eligible[0]
        if len(eligible) > 1 and first["score"] - eligible[1]["score"] < float(ambiguity_margin):
            entries.append({"index": index, "record": record, "status": "AMBIGUO", "candidate": first, "candidates": eligible[:3], "reason": "multiple_candidates"})
            continue
        entries.append({
            "index": index,
            "record": record,
            "status": "CAMBIO" if _record_changed(record, first, default_height_mm) else "MATCH",
            "candidate": first,
            "candidates": eligible[:3],
        })
        key = str(getattr(first["existing"]["space"], "Name", "") or id(first["existing"]["space"]))
        top_claims.setdefault(key, []).append(entries[-1])

    for claims in top_claims.values():
        if len(claims) <= 1:
            continue
        for entry in claims:
            entry["status"] = "AMBIGUO"
            entry["reason"] = "shared_candidate"

    matched_names = {
        str(getattr(entry["candidate"]["existing"]["space"], "Name", "") or "")
        for entry in entries
        if entry["status"] in {"MATCH", "CAMBIO"} and entry.get("candidate")
    }
    stale = [item for item in existing if str(getattr(item["space"], "Name", "") or "") not in matched_names]
    return {
        "schema_version": SPACE_SCHEMA_VERSION,
        "entries": entries,
        "existing": existing,
        "stale": stale,
        "counts": {status: sum(1 for entry in entries if entry["status"] == status) for status in MATCH_STATUS},
    }


def remove_previous_spaces(doc, source_room_sketch, generator=SPACE_GENERATOR):
    """Destructive legacy helper. Prefer ``create_bim_spaces(..., replace_existing=True)``.

    Kept for explicit migrations only. Normal synchronization updates matched
    Spaces in place so downstream PropertyLinks remain valid.
    """
    target_name = str(getattr(source_room_sketch, "Name", "") or "")
    spaces = []
    bases = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "FA_GeneratedBy", "") or "") != str(generator):
            continue
        source = getattr(obj, "FA_SourceRoomSketch", None)
        if target_name and str(getattr(source, "Name", "") or "") != target_name:
            continue
        role = str(getattr(obj, "FA_Role", "") or "")
        if role == "bim_space":
            spaces.append(obj)
        elif role == "space_base":
            bases.append(obj)
    removed = 0
    for obj in spaces + bases:
        try:
            if doc.getObject(obj.Name) is not None:
                doc.removeObject(obj.Name)
                removed += 1
        except Exception as exc:
            warn("No se pudo eliminar %s: %s" % (getattr(obj, "Label", obj.Name), exc))
    return removed


def _remove_empty_space_groups(doc):
    """Remove obsolete generated grouping shells after Spaces move to Level."""
    removed = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        name = str(getattr(obj, "Name", "") or "")
        if not (name.startswith("FA_BIMSpaces") or name.startswith("FA_DemoSpaces")):
            continue
        if list(getattr(obj, "Group", []) or []):
            continue
        try:
            if doc.getObject(name) is not None:
                doc.removeObject(name)
                removed += 1
        except Exception as exc:
            warn("No se pudo retirar grupo de Espacios vacio %s: %s" % (name, exc))
    return removed


def migrate_game_export_exclusions(doc, dry_run=True, generator=SPACE_GENERATOR):
    """Ensure FA-generated BIM Spaces and their bases are excluded from game export."""
    targets = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "FA_GeneratedBy", "") or "") != str(generator):
            continue
        role = str(getattr(obj, "FA_Role", "") or "")
        if role not in {"bim_space", "space_base"}:
            continue
        try:
            already_excluded = hasattr(obj, "GameExportExclude") and bool(obj.GameExportExclude)
        except Exception:
            already_excluded = False
        if not already_excluded:
            targets.append(obj)
    result = {
        "matched": len(targets),
        "changed": 0 if dry_run else len(targets),
        "dry_run": bool(dry_run),
        "objects": [str(getattr(obj, "Name", "") or "") for obj in targets],
    }
    if dry_run or not targets:
        return result
    opened = False
    try:
        if hasattr(doc, "openTransaction"):
            doc.openTransaction("FA migrar exclusiones GameExport")
            opened = True
        for obj in targets:
            set_prop(obj, "App::PropertyBool", "GameExportExclude", "Exportacion", "Excluir de GameEngineExport", True)
        if hasattr(doc, "recompute"):
            doc.recompute()
        if opened and hasattr(doc, "commitTransaction"):
            doc.commitTransaction()
    except Exception:
        if opened and hasattr(doc, "abortTransaction"):
            try:
                doc.abortTransaction()
            except Exception:
                pass
        raise
    return result


def _new_room_uid():
    return "FA-RM-" + uuid.uuid4().hex


def _allocate_room_id(preferred, used_ids):
    preferred = str(preferred or "").strip()
    if preferred and preferred not in used_ids:
        used_ids.add(preferred)
        return preferred
    index = 1
    while True:
        candidate = "R%03d" % index
        if candidate not in used_ids:
            used_ids.add(candidate)
            return candidate
        index += 1


def _set_common_metadata(obj, room_id, room_uid, room_sketch, generator):
    set_prop(obj, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", generator)
    set_prop(obj, "App::PropertyString", "FA_RoomID", "FacilArquitectura", "ID recinto", room_id)
    set_prop(obj, "App::PropertyString", "FA_RoomUID", "FacilArquitectura", "UID estable del recinto", room_uid)
    set_prop(obj, "App::PropertyLink", "FA_SourceRoomSketch", "FacilArquitectura", "Sketch documental de recintos", room_sketch)
    set_prop(obj, "App::PropertyInteger", "FA_SpaceSchemaVersion", "FacilArquitectura", "Version de esquema espacial", SPACE_SCHEMA_VERSION)
    set_prop(obj, "App::PropertyBool", "GameExportExclude", "Exportacion", "Excluir de GameEngineExport", True)


def _apply_record_to_pair(space, base, record, room_sketch, generator, default_height_mm, room_id, room_uid, status, score, label_suffix=""):
    face = _face_from_record(record)
    height = float(record.get("space_height_mm", default_height_mm) or default_height_mm)
    room_name = str(record.get("name") or room_id)
    area_m2 = float(record.get("area_m2") or (float(face.Area) / 1000000.0))
    suffix = str(label_suffix or "")
    base.Shape = face.extrude(App.Vector(0.0, 0.0, height))
    if str(getattr(base, "Label", "") or "").startswith("Base espacio - "):
        base.Label = "Base espacio - %s%s" % (room_name, suffix)
    _set_common_metadata(base, room_id, room_uid, room_sketch, generator)
    set_prop(base, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "space_base")
    try:
        base.ViewObject.Visibility = False
    except Exception:
        pass

    for prop_name in ("Base", "BaseGeometry"):
        if hasattr(space, prop_name):
            try:
                setattr(space, prop_name, base)
                break
            except Exception:
                pass
    if str(getattr(space, "Label", "") or "").startswith("Espacio BIM - "):
        space.Label = "Espacio BIM - %s%s" % (room_name, suffix)
    if hasattr(space, "IfcType"):
        space.IfcType = "Space"
    _set_common_metadata(space, room_id, room_uid, room_sketch, generator)
    set_prop(space, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "bim_space")
    set_prop(space, "App::PropertyString", "FA_RoomName", "FacilArquitectura", "Nombre recinto", room_name)
    set_prop(space, "App::PropertyArea", "FA_RoomArea", "FacilArquitectura", "Area util", area_m2 * 1000000.0)
    set_prop(space, "App::PropertyLength", "FA_SpaceHeight", "FacilArquitectura", "Altura del espacio", height)
    set_prop(space, "App::PropertyString", "FA_FloorPolygonJSON", "FacilArquitectura", "Poligono de piso JSON", json.dumps(record.get("polygon_mm") or [], separators=(",", ":")))
    set_prop(space, "App::PropertyString", "FA_SpaceMatchStatus", "FacilArquitectura", "Estado de sincronizacion", status)
    set_prop(space, "App::PropertyFloat", "FA_SpaceMatchScore", "FacilArquitectura", "Confianza de matching", float(score))
    try:
        space.ViewObject.ShapeColor = (0.70, 0.88, 0.96)
        space.ViewObject.Transparency = 80
    except Exception:
        pass
    return space, base


def _create_pair(doc, level_or_group, record, room_sketch, generator, default_height_mm, room_id, room_uid, index, label_suffix=""):
    face = _face_from_record(record)
    height = float(record.get("space_height_mm", default_height_mm) or default_height_mm)
    room_name = str(record.get("name") or room_id)
    suffix = str(label_suffix or "")
    base = doc.addObject("Part::Feature", "FA_SpaceBase%02d" % index)
    base.Label = "Base espacio - %s%s" % (room_name, suffix)
    base.Shape = face.extrude(App.Vector(0.0, 0.0, height))
    _set_common_metadata(base, room_id, room_uid, room_sketch, generator)
    set_prop(base, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "space_base")
    space = Arch.makeSpace(baseobj=base, name="FA_BIMSpace%02d" % index)
    if space is None:
        raise RuntimeError("Arch.makeSpace no pudo crear %s" % room_name)
    space.Label = "Espacio BIM - %s%s" % (room_name, suffix)
    _apply_record_to_pair(space, base, record, room_sketch, generator, default_height_mm, room_id, room_uid, "NO_MATCH", 1.0, label_suffix=label_suffix)
    if level_or_group is not None:
        try:
            if hasattr(level_or_group, "IfcType") or str(getattr(level_or_group, "TypeId", "") or "").startswith("App::Part"):
                add_to_level(level_or_group, space)
            else:
                level_or_group.addObject(space)
        except Exception:
            try:
                level_or_group.addObject(space)
            except Exception:
                pass
    return space, base


def create_bim_spaces(
    doc,
    level,
    room_sketch,
    room_records=None,
    default_height_mm=2700.0,
    replace_existing=True,
    generator=SPACE_GENERATOR,
    group_name=None,
    group_label=SPACE_GROUP_LABEL,
    label_suffix="",
    dry_run=False,
    min_iou=DEFAULT_MIN_IOU,
    min_overlap=DEFAULT_MIN_OVERLAP,
    ambiguity_margin=DEFAULT_AMBIGUITY_MARGIN,
):
    """Synchronize native Arch Spaces from JSON-compatible room records or a room Sketch.

    With ``replace_existing=True`` the operation is non-destructive: matched Spaces
    are updated in place, new rooms create new Spaces, ambiguous records are skipped,
    and unmatched old Spaces are reported as stale instead of being silently deleted.
    ``dry_run=True`` returns the same plan without modifying the document.
    """
    records = list(room_records or room_records_from_sketch(room_sketch, default_height_mm))
    if not records:
        raise RuntimeError("No hay recintos para convertir en Espacios BIM.")

    if replace_existing:
        plan = plan_bim_space_updates(
            doc,
            room_sketch,
            records,
            default_height_mm=default_height_mm,
            generator=generator,
            min_iou=min_iou,
            min_overlap=min_overlap,
            ambiguity_margin=ambiguity_margin,
        )
    else:
        plan = {
            "schema_version": SPACE_SCHEMA_VERSION,
            "entries": [{"index": index, "record": dict(record), "status": "NO_MATCH", "candidate": None, "candidates": []} for index, record in enumerate(records)],
            "existing": collect_existing_spaces(doc, room_sketch, generator=generator),
            "stale": [],
            "counts": {"MATCH": 0, "CAMBIO": 0, "NO_MATCH": len(records), "AMBIGUO": 0},
        }

    result = {
        "group": None,
        "spaces": [],
        "bases": [],
        "removed": 0,
        "updated": 0,
        "created": 0,
        "ambiguous": plan["counts"].get("AMBIGUO", 0),
        "stale": [str(getattr(item["space"], "Name", "") or "") for item in plan.get("stale", [])],
        "records": records,
        "plan": plan,
        "dry_run": bool(dry_run),
    }
    if dry_run:
        return result

    group = ensure_group(doc, group_name, group_label, level) if group_name else level
    result["group"] = group
    used_ids = {str(item.get("room_id") or "") for item in plan.get("existing", []) if str(item.get("room_id") or "")}
    used_names = {str(getattr(item["space"], "Name", "") or "") for item in plan.get("existing", [])}
    create_index = len(used_names) + 1

    for entry in plan["entries"]:
        record = entry["record"]
        status = entry["status"]
        if status == "AMBIGUO":
            warn("Espacio ambiguo sin modificar: %s" % str(record.get("name") or record.get("id") or "?"))
            continue
        if status in {"MATCH", "CAMBIO"}:
            existing = entry["candidate"]["existing"]
            space = existing["space"]
            base = existing.get("base")
            if base is None:
                create_index += 1
                face = _face_from_record(record)
                base = doc.addObject("Part::Feature", "FA_SpaceBase%02d" % create_index)
                base.Shape = face.extrude(App.Vector(0.0, 0.0, float(record.get("space_height_mm", default_height_mm) or default_height_mm)))
            room_id = str(existing.get("room_id") or "").strip() or _allocate_room_id(record.get("id"), used_ids)
            room_uid = str(existing.get("room_uid") or "").strip() or _new_room_uid()
            _apply_record_to_pair(
                space,
                base,
                record,
                room_sketch,
                generator,
                default_height_mm,
                room_id,
                room_uid,
                status,
                float(entry["candidate"]["score"]),
                label_suffix=label_suffix,
            )
            result["spaces"].append(space)
            result["bases"].append(base)
            if status == "CAMBIO":
                result["updated"] += 1
            continue

        room_id = _allocate_room_id(record.get("id"), used_ids)
        room_uid = _new_room_uid()
        create_index += 1
        space, base = _create_pair(
            doc,
            group,
            record,
            room_sketch,
            generator,
            default_height_mm,
            room_id,
            room_uid,
            create_index,
            label_suffix=label_suffix,
        )
        result["spaces"].append(space)
        result["bases"].append(base)
        result["created"] += 1

    _remove_empty_space_groups(doc)
    doc.recompute()
    for space in result["spaces"]:
        shape = getattr(space, "Shape", None)
        if shape is None or shape.isNull() or not list(getattr(shape, "Solids", []) or []):
            raise RuntimeError("Espacio BIM invalido despues de recomputar: %s" % space.Label)

    msg(
        "Espacios BIM sincronizados: %d | actualizados: %d | nuevos: %d | ambiguos: %d | stale: %d | fuente: %s"
        % (
            len(result["spaces"]),
            result["updated"],
            result["created"],
            result["ambiguous"],
            len(result["stale"]),
            getattr(room_sketch, "Label", getattr(room_sketch, "Name", "?")),
        )
    )
    return result
