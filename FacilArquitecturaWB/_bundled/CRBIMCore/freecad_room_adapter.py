"""Read-only FreeCAD adapter for :mod:`CRBIMCore.room_resolver_core`.

The adapter uses duck typing so it can be imported in ordinary Python tests.
It never imports FreeCADGui or Qt and never adds, removes, renames, or edits a
document object.
"""

from __future__ import annotations

import json
import math
import unicodedata

from . import room_resolver_core as core


NATIVE_SPACE = core.SOURCE_NATIVE_SPACE
LEGACY_AREA = core.SOURCE_LEGACY_AREA
KNOWN_LEGACY_GENERATORS = {
    "areaporclick",
    "poligonofromboundarylines",
    "rectfromboundarylines",
    "fa_rectangularareaanalysis",
    "fa_polygonalroomsfromarchwalls",
}
LEGACY_ROLES = {"area", "room", "room_area", "room_polygon"}
SUBAREA_MARKERS = {"subarea", "sub_area", "calculation_subarea"}


def _text(value):
    try:
        return str(value or "").strip()
    except Exception:
        return ""


def _normalized(value):
    text = unicodedata.normalize("NFKD", _text(value).lower())
    return "".join(char for char in text if not unicodedata.combining(char)).replace(" ", "_")


def _quantity(value, default=0.0):
    try:
        return float(value.Value)
    except Exception:
        try:
            return float(value)
        except Exception:
            return float(default)


def _object_name(obj):
    return _text(getattr(obj, "Name", ""))


def _object_label(obj):
    return _text(getattr(obj, "Label", "")) or _object_name(obj)


def _proxy_type(obj):
    return _text(getattr(getattr(obj, "Proxy", None), "Type", ""))


def _mep_type(obj):
    return _text(getattr(obj, "MEPType", "")) or _proxy_type(obj)


def _unwrap_link(obj):
    current = obj
    visited = set()
    while current is not None:
        identity = _object_name(current) or str(id(current))
        if identity in visited:
            return None
        visited.add(identity)
        type_id = _text(getattr(current, "TypeId", ""))
        if type_id != "App::Link":
            return current
        linked = getattr(current, "LinkedObject", None) or getattr(current, "Link", None)
        if linked is None:
            return current
        current = linked
    return None


def _is_hvac_space(obj):
    marker = _normalized(_mep_type(obj))
    return marker in {"hvacspace", "hvac_space"}


def _is_subarea(obj):
    markers = {
        _normalized(getattr(obj, name, ""))
        for name in ("ElectricCRTipo", "MEPType", "FA_Role", "ElementType", "ObjectType")
    }
    return bool(markers.intersection(SUBAREA_MARKERS))


def _is_native_space(obj):
    if obj is None or _is_hvac_space(obj) or _is_subarea(obj):
        return False
    type_id = _normalized(getattr(obj, "TypeId", ""))
    ifc_type = _normalized(getattr(obj, "IfcType", ""))
    proxy_type = _normalized(_proxy_type(obj))
    return bool(type_id == "arch::space" or ifc_type == "space" or proxy_type == "space")


def _legacy_area_reason(obj):
    if obj is None or _is_hvac_space(obj) or _is_subarea(obj) or _is_native_space(obj):
        return ""
    electric_type = _normalized(getattr(obj, "ElectricCRTipo", ""))
    if electric_type == "area":
        return "ElectricCRTipo=Area"
    generators = {
        _normalized(getattr(obj, "GeneratedBy", "")),
        _normalized(getattr(obj, "FA_GeneratedBy", "")),
    }
    known_generators = {_normalized(value) for value in KNOWN_LEGACY_GENERATORS}
    matched = sorted(generators.intersection(known_generators))
    if matched:
        return "generador=%s" % matched[0]
    role = _normalized(getattr(obj, "FA_Role", ""))
    if role in LEGACY_ROLES:
        return "FA_Role=%s" % role
    closed = bool(getattr(obj, "Closed", False))
    make_face = bool(getattr(obj, "MakeFace", False))
    metadata = any(
        _text(getattr(obj, name, ""))
        for name in ("AreaID", "FA_RoomName", "Recinto", "AreaNombre", "Habitacion", "Local", "Espacio")
    )
    has_area = _quantity(getattr(obj, "AreaM2", 0.0), 0.0) > 0.0
    if closed and make_face and metadata and has_area:
        return "Draft_cerrado_con_metadatos"
    return ""


def _safe_json_polygon(obj):
    raw = _text(getattr(obj, "FA_FloorPolygonJSON", ""))
    if not raw:
        return []
    try:
        values = json.loads(raw)
        return core.normalize_polygon(values)
    except Exception:
        return []


def _face_normal_z(face):
    try:
        u_min, u_max, v_min, v_max = face.ParameterRange
        normal = face.normalAt((u_min + u_max) * 0.5, (v_min + v_max) * 0.5)
        return abs(float(getattr(normal, "z", 0.0)))
    except Exception:
        try:
            return abs(float(getattr(getattr(face, "Surface", None).Axis, "z", 0.0)))
        except Exception:
            return 0.0


def _plan_face(shape):
    try:
        faces = [face for face in list(getattr(shape, "Faces", []) or []) if _quantity(face.Area) > 1.0]
    except Exception:
        faces = []
    if not faces:
        return None
    horizontal = [face for face in faces if _face_normal_z(face) >= 0.7]
    candidates = horizontal or faces
    return sorted(
        candidates,
        key=lambda face: (-_quantity(getattr(face, "Area", 0.0)), _quantity(getattr(face, "CenterOfMass", None).z if getattr(face, "CenterOfMass", None) is not None else 0.0)),
    )[0]


def _shape_polygon(obj):
    sources = [obj]
    for attr in ("Base", "BaseGeometry"):
        source = getattr(obj, attr, None)
        if source is not None and source not in sources:
            sources.append(source)
    for source in sources:
        shape = getattr(source, "Shape", None)
        face = _plan_face(shape)
        if face is None:
            continue
        try:
            wire = face.OuterWire
            vertices = list(getattr(wire, "OrderedVertexes", []) or [])
            if not vertices:
                vertices = list(getattr(wire, "Vertexes", []) or [])
            points = [[float(vertex.Point.x), float(vertex.Point.y)] for vertex in vertices]
            return core.normalize_polygon(points)
        except Exception:
            continue
    return []


def _polygon(obj):
    return _safe_json_polygon(obj) or _shape_polygon(obj)


def _linked_name(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return _text(value)
    return _object_name(value) or _object_label(value)


def _is_level_container(obj):
    if obj is None:
        return False
    ifc_type = _normalized(getattr(obj, "IfcType", ""))
    proxy_type = _normalized(_proxy_type(obj))
    return ifc_type in {"building_storey", "buildingstorey"} or proxy_type in {
        "buildingpart",
        "building_storey",
        "buildingstorey",
    }


def _level_name(obj):
    for property_name in ("BuildingStorey", "Level", "Storey"):
        value = getattr(obj, property_name, None)
        name = _linked_name(value)
        if name:
            return name
    pending = list(getattr(obj, "InList", []) or [])
    seen = set()
    while pending:
        parent = pending.pop(0)
        identity = _object_name(parent) or str(id(parent))
        if identity in seen:
            continue
        seen.add(identity)
        if _is_level_container(parent):
            return _object_name(parent) or _object_label(parent)
        pending.extend(list(getattr(parent, "InList", []) or []))
    return ""


def _first_text(obj, property_names, default=""):
    for name in property_names:
        value = _text(getattr(obj, name, ""))
        if value:
            return value
    return _text(default)


def _candidate_from_object(obj, source_kind, reason):
    polygon = _polygon(obj)
    if not polygon:
        raise ValueError("geometria_plana_no_disponible")
    name = _first_text(
        obj,
        ("FA_RoomName", "LongName", "AreaNombre", "Recinto", "Habitacion", "Local", "Espacio"),
        _object_label(obj),
    )
    room_uid = _first_text(obj, ("FA_RoomUID", "PersistentId", "GlobalId"))
    room_id = _first_text(obj, ("FA_RoomID", "AreaID", "Number", "SpaceNumber"))
    confidence = 1.0 if source_kind == NATIVE_SPACE else _quantity(getattr(obj, "Confidence", 0.5), 0.5)
    return core.normalize_candidate(
        {
            "source_kind": source_kind,
            "room_uid": room_uid,
            "room_id": room_id,
            "name": name,
            "object_name": _object_name(obj),
            "level": _level_name(obj),
            "polygon_mm": polygon,
            "confidence": confidence,
            "diagnostics": [reason],
        }
    )


def collect_room_candidates(doc, include_legacy=True):
    """Return a fully JSON-compatible read-only audit of physical room sources."""
    candidates = []
    diagnostics = []
    for obj in list(getattr(doc, "Objects", []) or []):
        object_name = _object_name(obj)
        if _text(getattr(obj, "TypeId", "")) == "App::Link":
            continue
        if _is_subarea(obj):
            diagnostics.append({"object_name": object_name, "status": "EXCLUDED", "reason": "SUBAREA"})
            continue
        if _is_hvac_space(obj):
            reason = "HVAC_BASESPACE_REFERENCE" if getattr(obj, "BaseSpace", None) is not None else "HVAC_WITHOUT_BASESPACE"
            diagnostics.append({"object_name": object_name, "status": "EXCLUDED", "reason": reason})
            continue
        source_kind = ""
        reason = ""
        if _is_native_space(obj):
            source_kind = NATIVE_SPACE
            reason = "Arch/BIM Space nativo"
        elif include_legacy:
            reason = _legacy_area_reason(obj)
            if reason:
                source_kind = LEGACY_AREA
        if not source_kind:
            continue
        try:
            candidates.append(_candidate_from_object(obj, source_kind, reason))
        except Exception as exc:
            diagnostics.append(
                {"object_name": object_name, "status": "REJECTED", "reason": _text(exc) or "candidato_invalido"}
            )
    return {
        "schema_version": core.SCHEMA_VERSION,
        "candidates": core.normalize_candidates(candidates),
        "diagnostics": diagnostics,
    }


def _not_found(reason):
    result = core.resolve_room_for_object([], {})
    result["diagnostics"] = [_text(reason)]
    return result


def resolve_room_for_point(doc, point_mm, level="", tolerance_mm=1.0):
    collection = collect_room_candidates(doc)
    result = core.resolve_room_for_point(
        collection["candidates"], point_mm, level=level, tolerance_mm=tolerance_mm
    )
    result["audit_diagnostics"] = collection["diagnostics"]
    return result


def resolve_room_reference(doc, reference):
    """Resolve an explicit FreeCAD reference, following HVACSpace.BaseSpace only."""
    current = _unwrap_link(reference)
    visited = set()
    while current is not None:
        identity = _object_name(current) or str(id(current))
        if identity in visited:
            return _not_found("REFERENCE_CYCLE")
        visited.add(identity)
        if _is_subarea(current):
            return _not_found("SUBAREA_EXCLUDED")
        if _is_hvac_space(current):
            base = _unwrap_link(getattr(current, "BaseSpace", None))
            if base is None:
                return _not_found("HVAC_WITHOUT_BASESPACE")
            current = base
            continue
        collection = collect_room_candidates(doc)
        result = core.resolve_room_reference(collection["candidates"], _object_name(current))
        result["audit_diagnostics"] = collection["diagnostics"]
        return result
    return _not_found("NULL_REFERENCE")


def _representative_point(obj):
    try:
        placement = obj.getGlobalPlacement()
        base = placement.Base
        return [float(base.x), float(base.y), float(base.z)]
    except Exception:
        pass
    try:
        base = obj.Placement.Base
        return [float(base.x), float(base.y), float(base.z)]
    except Exception:
        pass
    try:
        center = obj.Shape.CenterOfMass
        if all(math.isfinite(float(value)) for value in (center.x, center.y, center.z)):
            return [float(center.x), float(center.y), float(center.z)]
    except Exception:
        pass
    return None


def resolve_room_for_object(doc, obj, tolerance_mm=1.0):
    """Resolve a FreeCAD object by explicit links first, then by its placement."""
    subject = _unwrap_link(obj)
    if subject is None:
        return _not_found("NULL_OBJECT")
    if _is_subarea(subject) or _is_hvac_space(subject):
        return resolve_room_reference(doc, subject)
    for property_name in ("Space", "BaseSpace"):
        linked = _unwrap_link(getattr(subject, property_name, None))
        if linked is not None:
            return resolve_room_reference(doc, linked)
    collection = collect_room_candidates(doc)
    direct = core.resolve_room_reference(collection["candidates"], _object_name(subject))
    if direct["status"] == core.STATUS_RESOLVED:
        direct["audit_diagnostics"] = collection["diagnostics"]
        return direct
    point = _representative_point(subject)
    if point is None:
        return _not_found("OBJECT_WITHOUT_SPATIAL_POINT")
    result = core.resolve_room_for_point(
        collection["candidates"],
        point,
        level=_level_name(subject),
        tolerance_mm=tolerance_mm,
    )
    result["audit_diagnostics"] = collection["diagnostics"]
    return result


__all__ = [
    "collect_room_candidates",
    "resolve_room_for_point",
    "resolve_room_for_object",
    "resolve_room_reference",
]

