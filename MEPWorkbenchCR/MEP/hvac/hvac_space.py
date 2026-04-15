"""HVAC space object: cooling load belongs to the room/space."""

import os
import unicodedata

import FreeCAD as App
import Part

from ..utils import selection
from . import hvac_project

MEP_TYPE = "HVACSpace"
LOG_PREFIX = "[MEP-HVAC][Space] "
SPACE_DEBUG_REV = "2026-03-31-space-r1"
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "hvac.svg")
).replace(os.sep, "/")
AREA_GROUP_ALIASES = {
    "areas",
    "area",
    "areas_hvac",
    "subareas",
    "sub_areas",
    "subareas_hvac",
    "recintos",
    "espacios",
    "zonas",
}
KW_TO_BTUH = 3412.142
DEFAULT_OCCUPANCY_ACTIVITY = "Oficina"
OCCUPANCY_ACTIVITY_OPTIONS = [
    "Reposo",
    "Oficina",
    "Ligero",
    "Moderado",
    "Intenso",
]
OCCUPANCY_ACTIVITY_BTUH = {
    "Reposo": 450.0,
    "Oficina": 600.0,
    "Ligero": 750.0,
    "Moderado": 900.0,
    "Intenso": 1200.0,
}


def log(message):
    text = LOG_PREFIX + str(message)
    print(text)


def _to_float(value, default=0.0):
    try:
        if hasattr(value, "Value"):
            return float(value.Value)
        return float(value)
    except Exception:
        return float(default)


def _mep_type(obj):
    if obj is None:
        return ""
    try:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
            return str(getattr(obj, "MEPType", "") or "")
    except Exception:
        return ""
    return ""


def _is_hvac_object(obj):
    return _mep_type(obj).startswith("HVAC")


def _canonical_base_obj(base_obj):
    current = selection.unwrap_link(base_obj)
    visited = set()
    while current is not None and _is_hvac_object(current):
        key = str(getattr(current, "Name", "") or id(current))
        if key in visited:
            return None
        visited.add(key)
        linked = getattr(current, "BaseSpace", None)
        if linked is None:
            return None
        current = selection.unwrap_link(linked)
    return current


def _normalize_text(value):
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
    return text


def ensure_space_properties(obj):
    added_area = False
    added_height = False
    added_occupancy = False
    added_occupancy_activity = False
    added_equipment = False
    added_equipment_kw = False
    added_room_label = False
    added_label_text = False
    added_mode = False
    added_load = False

    if "MEPType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
    if str(getattr(obj, "MEPType", "")) != MEP_TYPE:
        obj.MEPType = MEP_TYPE

    if "BaseSpace" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyLink",
            "BaseSpace",
            "HVAC Space",
            "Linked Draft/Arch object that defines this room",
        )
    if "Project" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyLink",
            "Project",
            "HVAC Space",
            "HVAC project controlling climate factor",
        )
    if "RoomLabel" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyLink",
            "RoomLabel",
            "HVAC Space",
            "Linked HVAC label object for this room",
        )
        added_room_label = True
    if "LabelText" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyStringList",
            "LabelText",
            "HVAC Space",
            "Live label text lines shown over this room",
        )
        added_label_text = True
    if "Area" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Area", "HVAC Space", "Area in m2")
        added_area = True
    if "Height" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Height", "HVAC Space", "Height in meters")
        added_height = True
    if "Occupancy" not in obj.PropertiesList:
        obj.addProperty("App::PropertyInteger", "Occupancy", "HVAC Space", "Number of occupants")
        added_occupancy = True
    if "OccupancyActivity" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyEnumeration",
            "OccupancyActivity",
            "HVAC Space",
            "Occupancy activity level for people sensible load",
        )
        obj.OccupancyActivity = OCCUPANCY_ACTIVITY_OPTIONS
        added_occupancy_activity = True
    if "EquipmentLoad" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "EquipmentLoad",
            "HVAC Space",
            "Extra equipment load (BTU/h)",
        )
        added_equipment = True
    if "EquipmentLoadKW" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "EquipmentLoadKW",
            "HVAC Space",
            "Extra equipment load (kW)",
        )
        added_equipment_kw = True
    if "Mode" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyEnumeration",
            "Mode",
            "HVAC Space",
            "Load calculation mode",
        )
        obj.Mode = ["Rapido", "Preciso"]
        added_mode = True
    if "CoolingLoadBTU" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "CoolingLoadBTU",
            "HVAC Space",
            "Calculated cooling load (BTU/h)",
        )
        added_load = True

    if added_area:
        obj.Area = 20.0
    if added_height:
        obj.Height = 2.6
    if added_occupancy:
        obj.Occupancy = 0
    if "OccupancyActivity" in obj.PropertiesList:
        current_activity = str(getattr(obj, "OccupancyActivity", DEFAULT_OCCUPANCY_ACTIVITY) or DEFAULT_OCCUPANCY_ACTIVITY)
        try:
            obj.OccupancyActivity = OCCUPANCY_ACTIVITY_OPTIONS
        except Exception:
            pass
        if current_activity not in OCCUPANCY_ACTIVITY_OPTIONS:
            current_activity = DEFAULT_OCCUPANCY_ACTIVITY
        try:
            obj.OccupancyActivity = current_activity
        except Exception:
            pass
    if added_occupancy_activity:
        obj.OccupancyActivity = DEFAULT_OCCUPANCY_ACTIVITY
    if added_equipment:
        obj.EquipmentLoad = 0.0
    if added_equipment_kw:
        obj.EquipmentLoadKW = 0.0
    if added_mode:
        obj.Mode = "Rapido"
    if added_load:
        obj.CoolingLoadBTU = 0.0
    if added_room_label:
        obj.RoomLabel = None
    if added_label_text:
        obj.LabelText = []


def _normalize_area_value(raw_value):
    if raw_value is None:
        return None
    raw = _to_float(raw_value, 0.0)
    if raw <= 0:
        return None

    # Most FreeCAD geometric area values arrive in mm2.
    if raw > 100000.0:
        return raw / 1000000.0
    return raw


def _shape_planar_area_m2(shape):
    if shape is None:
        return None

    try:
        faces = list(getattr(shape, "Faces", []) or [])
    except Exception:
        faces = []

    # Planar face/solid support: use strongest horizontal footprint.
    if faces:
        horizontal_areas = []
        any_face_areas = []
        for face in faces:
            try:
                area_mm2 = _to_float(getattr(face, "Area", 0.0), 0.0)
                if area_mm2 <= 0:
                    continue
                any_face_areas.append(area_mm2)

                normal = None
                if hasattr(face, "Surface") and hasattr(face.Surface, "Axis"):
                    normal = face.Surface.Axis
                elif hasattr(face, "normalAt"):
                    # Typical param center for bounded surfaces.
                    u_mid = (face.ParameterRange[0] + face.ParameterRange[1]) * 0.5
                    v_mid = (face.ParameterRange[2] + face.ParameterRange[3]) * 0.5
                    normal = face.normalAt(u_mid, v_mid)
                if normal is not None and abs(float(getattr(normal, "z", 0.0))) >= 0.85:
                    horizontal_areas.append(area_mm2)
            except Exception:
                continue

        if horizontal_areas:
            return max(horizontal_areas) / 1000000.0
        if any_face_areas:
            # Fallback for 2D planar face with unknown normal retrieval.
            return max(any_face_areas) / 1000000.0

    # Closed planar wire support.
    try:
        wires = list(getattr(shape, "Wires", []) or [])
    except Exception:
        wires = []
    for wire in wires:
        try:
            if not wire.isClosed():
                continue
            face = Part.Face(wire)
            area_mm2 = _to_float(getattr(face, "Area", 0.0), 0.0)
            if area_mm2 > 0:
                return area_mm2 / 1000000.0
        except Exception:
            continue
    return None


def _shape_has_solids(shape):
    if shape is None:
        return False
    try:
        solids = list(getattr(shape, "Solids", []) or [])
        if solids:
            return True
    except Exception:
        pass
    try:
        volume = _to_float(getattr(shape, "Volume", 0.0), 0.0)
        if volume > 1e-6:
            return True
    except Exception:
        pass
    return False


def _is_embedded_model_element(base_obj):
    if base_obj is None:
        return False
    try:
        parent = base_obj.getParentGeoFeatureGroup()
    except Exception:
        parent = None
    if parent is None:
        return False
    parent_type = str(getattr(parent, "TypeId", "") or "")
    if parent_type.startswith("PartDesign::Body") or parent_type.startswith("App::Part"):
        return True
    return False


def _is_explicit_2d_area_type(base_obj):
    if base_obj is None:
        return False
    type_id = str(getattr(base_obj, "TypeId", "") or "")
    if "Part::Part2DObject" in type_id:
        return True
    if type_id.startswith("Sketcher::SketchObject"):
        return True
    return False


def _is_area_profile_candidate(base_obj, strict_2d=False):
    base_obj = _canonical_base_obj(base_obj)
    if base_obj is None:
        return False

    if bool(strict_2d):
        if not _is_explicit_2d_area_type(base_obj):
            return False
        if _is_embedded_model_element(base_obj):
            return False

    type_id = str(getattr(base_obj, "TypeId", "") or "")
    if "Part::Part2DObject" in type_id or type_id.startswith("Sketcher::SketchObject"):
        return True

    shape = getattr(base_obj, "Shape", None)
    if shape is not None:
        if _shape_has_solids(shape):
            return False
        area_from_shape = _shape_planar_area_m2(shape)
        if area_from_shape is not None and area_from_shape > 0:
            return True

    if hasattr(base_obj, "PropertiesList") and "Area" in base_obj.PropertiesList:
        area_prop = _normalize_area_value(getattr(base_obj, "Area", None))
        if area_prop is not None and area_prop > 0:
            return True
    return False


def detect_area_from_base(base_obj):
    base_obj = _canonical_base_obj(base_obj)
    if base_obj is None:
        return None
    if not _is_area_profile_candidate(base_obj, strict_2d=False):
        return None

    # Prefer explicit Area property from Draft/Arch objects.
    if hasattr(base_obj, "PropertiesList") and "Area" in base_obj.PropertiesList:
        normalized = _normalize_area_value(getattr(base_obj, "Area", None))
        if normalized is not None:
            return normalized

    # Prefer geometric area for polygons/faces/solids.
    if hasattr(base_obj, "Shape"):
        try:
            geometric_area = _shape_planar_area_m2(base_obj.Shape)
            if geometric_area is not None and geometric_area > 0:
                return geometric_area
        except Exception:
            pass
    return None


def _distance_point_to_segment_xy(px, py, ax, ay, bx, by):
    vx = float(bx) - float(ax)
    vy = float(by) - float(ay)
    wx = float(px) - float(ax)
    wy = float(py) - float(ay)
    seg_len2 = (vx * vx) + (vy * vy)
    if seg_len2 <= 1e-12:
        dx = float(px) - float(ax)
        dy = float(py) - float(ay)
        return (dx * dx + dy * dy) ** 0.5
    t = ((wx * vx) + (wy * vy)) / seg_len2
    t = max(0.0, min(1.0, t))
    cx = float(ax) + (t * vx)
    cy = float(ay) + (t * vy)
    dx = float(px) - cx
    dy = float(py) - cy
    return (dx * dx + dy * dy) ** 0.5


def _point_in_polygon_xy(px, py, vertices_xy, tol=1.0):
    vertices = list(vertices_xy or [])
    if len(vertices) < 3:
        return False

    # Boundary check first.
    for idx in range(len(vertices)):
        ax, ay = vertices[idx]
        bx, by = vertices[(idx + 1) % len(vertices)]
        if _distance_point_to_segment_xy(px, py, ax, ay, bx, by) <= float(tol):
            return True

    # Ray casting.
    inside = False
    j = len(vertices) - 1
    for i in range(len(vertices)):
        xi, yi = vertices[i]
        xj, yj = vertices[j]
        yi_gt = float(yi) > float(py)
        yj_gt = float(yj) > float(py)
        if yi_gt != yj_gt:
            denom = float(yj) - float(yi)
            if abs(denom) > 1e-12:
                x_intersect = float(xi) + ((float(py) - float(yi)) * (float(xj) - float(xi)) / denom)
                if float(px) < x_intersect:
                    inside = not inside
        j = i
    return inside


def _face_normal_z_abs(face):
    try:
        u_min, u_max, v_min, v_max = face.ParameterRange
        u_mid = (float(u_min) + float(u_max)) * 0.5
        v_mid = (float(v_min) + float(v_max)) * 0.5
        normal = face.normalAt(u_mid, v_mid)
        return abs(float(getattr(normal, "z", 0.0)))
    except Exception:
        try:
            axis = getattr(face.Surface, "Axis", None)
            return abs(float(getattr(axis, "z", 0.0)))
        except Exception:
            return 0.0


def _pick_plan_face(shape):
    if shape is None:
        return None
    try:
        faces = list(getattr(shape, "Faces", []) or [])
    except Exception:
        faces = []
    if not faces:
        return None

    horizontal = []
    for face in faces:
        try:
            area = _to_float(getattr(face, "Area", 0.0), 0.0)
            if area <= 0:
                continue
            nz = _face_normal_z_abs(face)
            if nz >= 0.7:
                horizontal.append((area, face))
        except Exception:
            continue
    if horizontal:
        horizontal.sort(key=lambda row: row[0], reverse=True)
        return horizontal[0][1]

    try:
        return max(faces, key=lambda f: _to_float(getattr(f, "Area", 0.0), 0.0))
    except Exception:
        return faces[0]


def _shape_plan_vertices_xy(shape):
    face = _pick_plan_face(shape)
    if face is None:
        return []
    try:
        wire = getattr(face, "OuterWire", None)
        if wire is None:
            return []
        ordered = list(getattr(wire, "OrderedVertexes", []) or [])
        vertices = ordered if ordered else list(getattr(wire, "Vertexes", []) or [])
        coords = []
        for vertex in vertices:
            point = getattr(vertex, "Point", None)
            if point is None:
                continue
            x = float(point.x)
            y = float(point.y)
            if coords and abs(coords[-1][0] - x) <= 1e-9 and abs(coords[-1][1] - y) <= 1e-9:
                continue
            coords.append((x, y))
        if len(coords) > 1:
            first = coords[0]
            last = coords[-1]
            if abs(first[0] - last[0]) <= 1e-9 and abs(first[1] - last[1]) <= 1e-9:
                coords = coords[:-1]
        return coords
    except Exception:
        return []


def contains_point_in_base(base_obj, point, tol=5.0):
    base_obj = _canonical_base_obj(base_obj)
    if base_obj is None or point is None or not hasattr(base_obj, "Shape"):
        return False

    try:
        shape = base_obj.Shape
        bbox = shape.BoundBox
    except Exception:
        return False

    x = float(getattr(point, "x", 0.0))
    y = float(getattr(point, "y", 0.0))
    tol = float(tol)
    if x < (float(bbox.XMin) - tol) or x > (float(bbox.XMax) + tol):
        return False
    if y < (float(bbox.YMin) - tol) or y > (float(bbox.YMax) + tol):
        return False

    vertices_xy = _shape_plan_vertices_xy(shape)
    if len(vertices_xy) >= 3:
        return _point_in_polygon_xy(x, y, vertices_xy, tol=tol)

    # Fallback when polygon extraction is not available.
    try:
        return shape.BoundBox.isInside(point)
    except Exception:
        return False


def space_contains_point(space_obj, point, tol=5.0):
    if space_obj is None:
        return False
    base_obj = getattr(space_obj, "BaseSpace", None)
    return contains_point_in_base(base_obj, point, tol=tol)


def find_spaces(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    spaces = []
    for obj in doc.Objects:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
            if str(obj.MEPType) == MEP_TYPE:
                base = getattr(obj, "BaseSpace", None)
                if _mep_type(base) == MEP_TYPE:
                    # Invalid nested space; ignore to avoid duplicated processing.
                    continue
                spaces.append(obj)
    return spaces


def _replace_space_with_part_feature(space_obj):
    doc = getattr(space_obj, "Document", None)
    if doc is None:
        return space_obj, False
    if str(getattr(space_obj, "TypeId", "") or "").startswith("Part::FeaturePython"):
        return space_obj, False

    old_name = str(getattr(space_obj, "Name", "") or "")
    old_label = str(getattr(space_obj, "Label", "") or old_name)
    old_placement = None
    try:
        old_placement = space_obj.Placement
    except Exception:
        old_placement = None
    old_values = {}
    copy_props = (
        "BaseSpace",
        "Project",
        "Area",
        "Height",
        "Occupancy",
        "OccupancyActivity",
        "EquipmentLoad",
        "EquipmentLoadKW",
        "Mode",
        "CoolingLoadBTU",
        "LabelText",
    )
    for prop_name in copy_props:
        if prop_name in getattr(space_obj, "PropertiesList", []):
            try:
                old_values[prop_name] = getattr(space_obj, prop_name)
            except Exception:
                continue

    new_obj = doc.addObject("Part::FeaturePython", "HVAC_Space")
    HVACSpaceProxy(new_obj)
    HVACSpaceViewProvider(new_obj.ViewObject)
    ensure_space_properties(new_obj)
    new_obj.Label = old_label
    if old_placement is not None:
        try:
            new_obj.Placement = old_placement
        except Exception:
            pass

    for prop_name in copy_props:
        if prop_name not in old_values:
            continue
        if prop_name not in getattr(new_obj, "PropertiesList", []):
            continue
        try:
            setattr(new_obj, prop_name, old_values[prop_name])
        except Exception:
            continue
    _sync_space_shape_from_base(new_obj)

    try:
        from . import hvac_equipment

        for equipment_obj in hvac_equipment.find_equipments(doc):
            if getattr(equipment_obj, "Space", None) == space_obj:
                try:
                    equipment_obj.Space = new_obj
                except Exception:
                    continue
    except Exception:
        pass

    try:
        from . import hvac_label

        for label_obj in hvac_label.find_labels(doc):
            if getattr(label_obj, "Space", None) == space_obj:
                try:
                    label_obj.Space = new_obj
                except Exception:
                    continue
    except Exception:
        pass

    try:
        doc.removeObject(old_name)
    except Exception:
        return new_obj, True
    log("HVACSpace migrado a Part::FeaturePython: {0} -> {1}".format(old_name, new_obj.Name))
    return new_obj, True


def upgrade_spaces_schema(doc=None, rebind_proxy=True, recalc=False):
    """Upgrade existing HVACSpace objects to latest schema/proxy in current runtime."""

    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return {"spaces": 0, "rebound": 0, "recalculated": 0}

    spaces = list(find_spaces(doc))
    rebound = 0
    migrated = 0
    recalculated = 0
    cleared_roomlabel = 0
    for idx, space_obj in enumerate(spaces):
        if space_obj is None:
            continue
        space_obj, was_migrated = _replace_space_with_part_feature(space_obj)
        if was_migrated:
            migrated += 1
            spaces[idx] = space_obj
        if rebind_proxy:
            proxy = getattr(space_obj, "Proxy", None)
            if type(proxy) is not HVACSpaceProxy:
                HVACSpaceProxy(space_obj)
                rebound += 1
            else:
                ensure_space_properties(space_obj)
        else:
            ensure_space_properties(space_obj)

        if "RoomLabel" in getattr(space_obj, "PropertiesList", []):
            try:
                if getattr(space_obj, "RoomLabel", None) is not None:
                    space_obj.RoomLabel = None
                    cleared_roomlabel += 1
            except Exception:
                pass

        if bool(recalc):
            calculate_space_load(space_obj)
            recalculated += 1

    if spaces:
        log(
            "Upgrade schema espacios: total={0}, rebound={1}, recalculated={2}, rev={3}".format(
                len(spaces),
                rebound,
                recalculated,
                SPACE_DEBUG_REV,
            )
        )
    if migrated > 0:
        log("Espacios migrados a Part::FeaturePython: {0}".format(migrated))
    if cleared_roomlabel > 0:
        log("Backlinks RoomLabel limpiados en espacios HVAC: {0}".format(cleared_roomlabel))
    return {"spaces": len(spaces), "rebound": rebound, "migrated": migrated, "recalculated": recalculated}


def find_nested_spaces(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    nested = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if _mep_type(obj) != MEP_TYPE:
            continue
        base = getattr(obj, "BaseSpace", None)
        if _mep_type(base) == MEP_TYPE:
            nested.append(obj)
    return nested


def cleanup_nested_spaces(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    nested = find_nested_spaces(doc)
    if not nested:
        return 0

    try:
        from . import hvac_label

        hvac_label.remove_labels_for_spaces(nested, doc=doc)
    except Exception:
        pass

    removed = 0
    for obj in nested:
        try:
            doc.removeObject(obj.Name)
            removed += 1
        except Exception:
            continue
    if removed > 0:
        log("Recintos HVAC anidados eliminados: {0}".format(removed))
    return removed


def cleanup_duplicate_spaces(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    spaces = list(find_spaces(doc))
    if len(spaces) < 2:
        return 0

    keep_by_base = {}
    duplicate_spaces = []
    replacement_map = {}

    for space_obj in spaces:
        linked_base = _canonical_base_obj(getattr(space_obj, "BaseSpace", None))
        base_name = str(getattr(linked_base, "Name", "") or "")
        if not base_name:
            continue

        keeper = keep_by_base.get(base_name)
        if keeper is None:
            keep_by_base[base_name] = space_obj
            continue

        duplicate_spaces.append(space_obj)
        replacement_map[space_obj] = keeper

    if not duplicate_spaces:
        return 0

    # Keep equipment assignments stable when duplicates are cleaned.
    try:
        from . import hvac_equipment

        for equipment_obj in hvac_equipment.find_equipments(doc):
            linked_space = getattr(equipment_obj, "Space", None)
            replacement = replacement_map.get(linked_space)
            if replacement is not None:
                try:
                    equipment_obj.Space = replacement
                except Exception:
                    continue
    except Exception:
        pass

    try:
        from . import hvac_label

        hvac_label.remove_labels_for_spaces(duplicate_spaces, doc=doc)
    except Exception:
        pass

    removed = 0
    for space_obj in duplicate_spaces:
        try:
            doc.removeObject(space_obj.Name)
            removed += 1
        except Exception:
            continue

    if removed > 0:
        log("Recintos HVAC duplicados eliminados: {0}".format(removed))
    return removed


def cleanup_non_area_spaces(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    invalid_spaces = []
    for space_obj in list(find_spaces(doc)):
        linked_base = _canonical_base_obj(getattr(space_obj, "BaseSpace", None))
        if linked_base is None:
            invalid_spaces.append(space_obj)
            continue
        if not _is_area_profile_candidate(linked_base, strict_2d=True):
            invalid_spaces.append(space_obj)

    if not invalid_spaces:
        return 0

    try:
        from . import hvac_label

        hvac_label.remove_labels_for_spaces(invalid_spaces, doc=doc)
    except Exception:
        pass

    removed = 0
    for space_obj in invalid_spaces:
        try:
            doc.removeObject(space_obj.Name)
            removed += 1
        except Exception:
            continue

    if removed > 0:
        log("Recintos HVAC no compatibles con Areas eliminados: {0}".format(removed))
    return removed


def cleanup_spaces_outside_bases(base_objects, doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    allowed = set()
    for base_obj in list(base_objects or []):
        canonical = _canonical_base_obj(base_obj)
        base_name = str(getattr(canonical, "Name", "") or "")
        if base_name:
            allowed.add(base_name)
    if not allowed:
        return 0

    obsolete_spaces = []
    for space_obj in list(find_spaces(doc)):
        linked_base = _canonical_base_obj(getattr(space_obj, "BaseSpace", None))
        linked_name = str(getattr(linked_base, "Name", "") or "")
        if not linked_name or linked_name not in allowed:
            obsolete_spaces.append(space_obj)

    if not obsolete_spaces:
        return 0

    try:
        from . import hvac_equipment

        for equipment_obj in hvac_equipment.find_equipments(doc):
            linked_space = getattr(equipment_obj, "Space", None)
            if linked_space in obsolete_spaces:
                try:
                    equipment_obj.Space = None
                except Exception:
                    continue
    except Exception:
        pass

    try:
        from . import hvac_label

        hvac_label.remove_labels_for_spaces(obsolete_spaces, doc=doc)
    except Exception:
        pass

    removed = 0
    for space_obj in obsolete_spaces:
        try:
            doc.removeObject(space_obj.Name)
            removed += 1
        except Exception:
            continue
    if removed > 0:
        log("Recintos HVAC fuera del conjunto Areas eliminados: {0}".format(removed))
    return removed


def _find_project_for_space(space_obj, explicit_project=None):
    if explicit_project is not None:
        return explicit_project
    if "Project" in space_obj.PropertiesList and getattr(space_obj, "Project", None):
        return space_obj.Project
    projects = hvac_project.find_projects(space_obj.Document)
    if projects:
        return projects[0]
    return None


def calculate_space_load(space_obj, project=None):
    """Calculate cooling load for one space."""

    if space_obj is None:
        return 0.0

    ensure_space_properties(space_obj)
    base_obj = getattr(space_obj, "BaseSpace", None)
    detected_area = detect_area_from_base(base_obj)
    if detected_area is not None and detected_area > 0:
        if abs(_to_float(space_obj.Area, 0.0) - float(detected_area)) > 0.001:
            space_obj.Area = round(detected_area, 3)

    project_obj = _find_project_for_space(space_obj, explicit_project=project)
    if project_obj and "Project" in space_obj.PropertiesList and space_obj.Project is None:
        space_obj.Project = project_obj

    factor = 400.0
    if project_obj is not None:
        factor = _to_float(project_obj.ClimateFactor, 400.0)

    area = max(0.0, _to_float(space_obj.Area, 0.0))
    occupancy = max(0, int(getattr(space_obj, "Occupancy", 0)))
    occupancy_activity = str(getattr(space_obj, "OccupancyActivity", DEFAULT_OCCUPANCY_ACTIVITY) or DEFAULT_OCCUPANCY_ACTIVITY)
    if occupancy_activity not in OCCUPANCY_ACTIVITY_BTUH:
        occupancy_activity = DEFAULT_OCCUPANCY_ACTIVITY
    equipment_btu = max(0.0, _to_float(getattr(space_obj, "EquipmentLoad", 0.0), 0.0))
    equipment_kw = max(0.0, _to_float(getattr(space_obj, "EquipmentLoadKW", 0.0), 0.0))
    equipment_kw_btu = equipment_kw * KW_TO_BTUH
    equipment_total = equipment_btu + equipment_kw_btu
    height = max(1.8, _to_float(space_obj.Height, 2.6))
    mode = str(space_obj.Mode)

    area_load = area * factor
    people_coeff = OCCUPANCY_ACTIVITY_BTUH.get(occupancy_activity, OCCUPANCY_ACTIVITY_BTUH[DEFAULT_OCCUPANCY_ACTIVITY])
    if mode == "Preciso":
        people_coeff = people_coeff * (650.0 / 600.0)
    people_load = occupancy * people_coeff
    total = area_load + people_load + equipment_total

    if mode == "Preciso":
        height_factor = max(0.85, min(1.40, height / 2.6))
        total = total * height_factor

    old_load = _to_float(space_obj.CoolingLoadBTU, 0.0)
    cooling_load = round(total, 2)
    space_obj.CoolingLoadBTU = cooling_load
    if abs(old_load - cooling_load) > 0.01:
        log(
            "Carga recinto {0}: area={1} m2, factor={2}, personas={3}({4}), equipos_btu={5}, equipos_kw={6}, total={7}".format(
                space_obj.Name,
                round(area, 2),
                round(factor, 2),
                occupancy,
                occupancy_activity,
                round(equipment_btu, 2),
                round(equipment_kw, 3),
                cooling_load,
            )
        )
    return cooling_load


def _is_group(obj):
    type_id = str(getattr(obj, "TypeId", "") or "")
    if type_id.startswith("App::DocumentObjectGroup"):
        return True
    return hasattr(obj, "Group") and hasattr(obj, "addObject")


def _iter_group_tree(root_group):
    stack = [root_group]
    seen = set()
    while stack:
        grp = stack.pop()
        gid = str(getattr(grp, "Name", "")) or str(id(grp))
        if gid in seen:
            continue
        seen.add(gid)
        yield grp
        for child in list(getattr(grp, "Group", []) or []):
            if _is_group(child):
                stack.append(child)


def _iter_doc_groups(doc):
    for obj in list(getattr(doc, "Objects", []) or []):
        if _is_group(obj):
            yield obj


def _area_object_candidates_from_group(group_obj):
    candidates = []
    for grp in _iter_group_tree(group_obj):
        for child in list(getattr(grp, "Group", []) or []):
            if _is_group(child):
                continue
            unwrapped = selection.unwrap_link(child)
            if _is_hvac_object(unwrapped):
                continue
            if _is_area_profile_candidate(unwrapped, strict_2d=True) and detect_area_from_base(unwrapped) is not None:
                candidates.append(unwrapped)
    return candidates


def _group_is_areas_like(group_obj):
    if group_obj is None:
        return False
    name_norm = _normalize_text(getattr(group_obj, "Name", ""))
    label_norm = _normalize_text(getattr(group_obj, "Label", ""))
    if name_norm in AREA_GROUP_ALIASES or label_norm in AREA_GROUP_ALIASES:
        return True
    tokens = ("area", "subarea", "recinto", "espacio", "zona")
    return any(token in name_norm for token in tokens) or any(token in label_norm for token in tokens)


def _find_areas_group(doc, selected_objects=None):
    selected_objects = list(selected_objects or [])

    # 1) Prioridad: grupo seleccionado con objetos de area.
    for obj in selected_objects:
        if _is_group(obj) and _group_is_areas_like(obj):
            candidates = _area_object_candidates_from_group(obj)
            if candidates:
                return obj

    # 2) Busqueda por Name exacto.
    for name in ("Areas", "areas", "Recintos", "Espacios", "Zonas"):
        grp = doc.getObject(name)
        if grp is not None and _is_group(grp):
            return grp

    # 3) Busqueda por Label normalizado.
    for grp in _iter_doc_groups(doc):
        if _group_is_areas_like(grp):
            return grp
    return None


def _deduplicate_objects(objects):
    unique = []
    seen = set()
    for obj in objects:
        if obj is None:
            continue
        name = str(getattr(obj, "Name", "") or "")
        key = name if name else str(id(obj))
        if key in seen:
            continue
        seen.add(key)
        unique.append(obj)
    return unique


def _space_for_base(doc, base_obj):
    target_base = _canonical_base_obj(base_obj)
    if target_base is None:
        return None
    target_name = str(getattr(target_base, "Name", "") or "")
    if not target_name:
        return None

    for space in find_spaces(doc):
        linked_base = _canonical_base_obj(getattr(space, "BaseSpace", None))
        linked_name = str(getattr(linked_base, "Name", "") or "")
        if linked_name and linked_name == target_name:
            return space
    return None


def _sync_space_shape_from_base(space_obj):
    if space_obj is None:
        return False
    props = list(getattr(space_obj, "PropertiesList", []) or [])
    if "Shape" not in props:
        try:
            space_obj.addProperty(
                "Part::PropertyPartShape",
                "Shape",
                "HVAC Space",
                "Visible room profile copied from BaseSpace",
            )
        except Exception:
            return False
    base_obj = _canonical_base_obj(getattr(space_obj, "BaseSpace", None))
    if base_obj is None or not hasattr(base_obj, "Shape"):
        return False
    try:
        copied = base_obj.Shape.copy()
    except Exception:
        try:
            copied = base_obj.Shape
        except Exception:
            return False
    try:
        space_obj.Shape = copied
    except Exception:
        return False
    return True


def _set_base_objects_visibility(space_objects, visible=False):
    changed = 0
    seen = set()
    target_visibility = bool(visible)
    for space_obj in list(space_objects or []):
        props = list(getattr(space_obj, "PropertiesList", []) or [])
        if "Shape" not in props:
            # Do not hide base if HVAC space has no drawable geometry yet.
            continue
        base_obj = _canonical_base_obj(getattr(space_obj, "BaseSpace", None))
        base_name = str(getattr(base_obj, "Name", "") or "")
        if not base_name or base_name in seen:
            continue
        seen.add(base_name)
        vobj = getattr(base_obj, "ViewObject", None)
        if vobj is None or not hasattr(vobj, "Visibility"):
            continue
        try:
            current = bool(getattr(vobj, "Visibility", True))
            if current != target_visibility:
                vobj.Visibility = target_visibility
                changed += 1
        except Exception:
            continue
    return changed


def _create_or_update_space(doc, base_obj, project_obj=None):
    base_obj = _canonical_base_obj(base_obj)
    if base_obj is None:
        return None, False
    if not _is_area_profile_candidate(base_obj, strict_2d=True):
        return None, False

    existing = _space_for_base(doc, base_obj)
    created = False
    if existing is None:
        obj = doc.addObject("Part::FeaturePython", "HVAC_Space")
        HVACSpaceProxy(obj)
        HVACSpaceViewProvider(obj.ViewObject)
        ensure_space_properties(obj)
        created = True
    else:
        obj = existing
        ensure_space_properties(obj)

    if base_obj is not None:
        obj.BaseSpace = base_obj
        base_label = str(getattr(base_obj, "Label", "") or getattr(base_obj, "Name", ""))
        if base_label.upper().startswith("HVAC_"):
            base_label = base_label[5:]
        if base_label:
            obj.Label = "HVAC_" + base_label
        detected_area = detect_area_from_base(base_obj)
        if detected_area is not None and detected_area > 0:
            obj.Area = round(detected_area, 3)
        _sync_space_shape_from_base(obj)

    if project_obj is not None and "Project" in obj.PropertiesList and getattr(obj, "Project", None) is None:
        obj.Project = project_obj

    calculate_space_load(obj, project=project_obj)
    hvac_project.add_object_to_hvac_group(doc, obj)
    return obj, created


def create_spaces_from_selection(doc=None):
    """Create/update HVAC spaces from selected polygons/area groups."""

    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return []

    cleanup_nested_spaces(doc)
    cleanup_non_area_spaces(doc)
    cleanup_duplicate_spaces(doc)

    selected = list(selection.get_selected_objects(resolve_links=True) or [])
    candidates = []
    source_from_areas_group = False

    for obj in selected:
        if _is_hvac_object(obj):
            linked_base = _canonical_base_obj(obj)
            if (
                linked_base is not None
                and _is_area_profile_candidate(linked_base, strict_2d=True)
                and detect_area_from_base(linked_base) is not None
            ):
                candidates.append(linked_base)
            continue
        if _is_group(obj):
            if _group_is_areas_like(obj):
                candidates.extend(_area_object_candidates_from_group(obj))
            continue
        if _is_area_profile_candidate(obj, strict_2d=True) and detect_area_from_base(obj) is not None:
            candidates.append(obj)

    if not candidates:
        auto_group = _find_areas_group(doc, selected_objects=selected)
        if auto_group is not None:
            candidates = _area_object_candidates_from_group(auto_group)
            source_from_areas_group = bool(candidates)
            log(
                "Grupo de areas detectado: {0} ({1} objetos)".format(
                    getattr(auto_group, "Label", getattr(auto_group, "Name", "?")),
                    len(candidates),
                )
            )

    normalized = []
    for obj in candidates:
        base = _canonical_base_obj(obj)
        if base is None:
            continue
        if not _is_area_profile_candidate(base, strict_2d=True):
            continue
        if detect_area_from_base(base) is None:
            continue
        normalized.append(base)
    candidates = _deduplicate_objects(normalized)
    if not candidates:
        log("Seleccione un poligono/recinto o un grupo Areas con geometria valida")
        return []

    if source_from_areas_group:
        cleanup_spaces_outside_bases(candidates, doc=doc)

    projects = hvac_project.find_projects(doc)
    project_obj = projects[0] if projects else hvac_project.get_or_create_project(doc)

    spaces = []
    created_count = 0
    updated_count = 0
    for base_obj in candidates:
        space_obj, created = _create_or_update_space(doc, base_obj, project_obj=project_obj)
        if space_obj is None:
            continue
        spaces.append(space_obj)
        if created:
            created_count += 1
            log("Recinto HVAC creado desde poligono: {0}".format(base_obj.Name))
        else:
            updated_count += 1
            log("Recinto HVAC actualizado desde poligono: {0}".format(base_obj.Name))

    log(
        "Recintos HVAC procesados: total={0}, creados={1}, actualizados={2}".format(
            len(spaces), created_count, updated_count
        )
    )
    hidden_count = _set_base_objects_visibility(spaces, visible=False)
    if hidden_count > 0:
        log("Poligonos base ocultados para priorizar recintos HVAC: {0}".format(hidden_count))
    return spaces


def has_area_selection():
    selected = list(selection.get_selected_objects(resolve_links=True) or [])
    for obj in selected:
        if _is_group(obj):
            if _area_object_candidates_from_group(obj):
                return True
            continue
        candidate = obj
        if _is_hvac_object(candidate):
            candidate = _canonical_base_obj(candidate)
        if _is_area_profile_candidate(candidate, strict_2d=True) and detect_area_from_base(candidate) is not None:
            return True
    return False


def prepare_spaces_from_selection_quick(doc=None):
    spaces = create_spaces_from_selection(doc=doc)
    for space_obj in spaces:
        if "Mode" in getattr(space_obj, "PropertiesList", []):
            try:
                space_obj.Mode = "Rapido"
            except Exception:
                pass
    return spaces


def create_space_from_selection(doc=None):
    """Backward-compatible wrapper for single-command behavior."""

    spaces = create_spaces_from_selection(doc=doc)
    if spaces:
        return spaces[0]
    return None


class HVACSpaceProxy:
    def __init__(self, obj):
        obj.Proxy = self
        self._busy = False
        ensure_space_properties(obj)

    def onChanged(self, obj, prop):  # noqa: N802
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        if prop in {
            "Area",
            "Height",
            "Occupancy",
            "OccupancyActivity",
            "EquipmentLoad",
            "EquipmentLoadKW",
            "Mode",
            "Project",
            "BaseSpace",
        }:
            self._busy = True
            try:
                if prop == "BaseSpace":
                    _sync_space_shape_from_base(obj)
                calculate_space_load(obj)
            finally:
                self._busy = False

    def execute(self, obj):
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        self._busy = True
        try:
            _sync_space_shape_from_base(obj)
            calculate_space_load(obj)
        finally:
            self._busy = False


class HVACSpaceViewProvider:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object

    def getIcon(self):  # noqa: N802
        return ICON_PATH

    def updateData(self, obj, prop):  # noqa: N802
        pass

    def onChanged(self, vobj, prop):  # noqa: N802
        if str(prop) != "Visibility":
            return
        try:
            space_obj = getattr(vobj, "Object", None)
            if space_obj is None:
                return
            from . import hvac_label

            hvac_label.sync_label_visibility_for_space(space_obj, visible=bool(getattr(vobj, "Visibility", True)))
        except Exception:
            return

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

