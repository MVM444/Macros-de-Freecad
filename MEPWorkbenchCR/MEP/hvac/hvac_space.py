"""HVAC space object: cooling load belongs to the room/space."""

import os
import unicodedata

import FreeCAD as App
import Part

from ..utils import selection
from . import hvac_project

try:
    from ..i18n import tr
except Exception:
    from MEP.i18n import tr

MEP_TYPE = "HVACSpace"
LOG_PREFIX = "[MEP-HVAC][Space] "
SPACE_DEBUG_REV = "2026-08-01-space-r5"
SPACE_SCHEMA_VERSION = 2
SOURCE_MODE_COPY = "LinkedCopy"
SOURCE_MODE_CONVERT = "Converted"
SOURCE_MODE_OPTIONS = [SOURCE_MODE_COPY, SOURCE_MODE_CONVERT]
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
        # A converted HVAC space owns an independent Shape snapshot.  It has no
        # BaseSpace by design, so it is its own geometric source.
        if (
            _mep_type(current) == MEP_TYPE
            and str(getattr(current, "SourceMode", "") or "") == SOURCE_MODE_CONVERT
            and getattr(current, "BaseSpace", None) is None
        ):
            return current
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
    added_source_mode = False
    added_source_name = False
    added_source_label = False
    added_allow_overlap = False
    added_schema_version = False

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
    if "SourceMode" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyEnumeration",
            "SourceMode",
            "HVAC Source",
            "LinkedCopy preserves the source; Converted owns a geometry snapshot",
        )
        obj.SourceMode = SOURCE_MODE_OPTIONS
        added_source_mode = True
    if "SourceObjectName" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyString",
            "SourceObjectName",
            "HVAC Source",
            "Original FreeCAD object name used to create this HVAC space",
        )
        added_source_name = True
    if "SourceObjectLabel" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyString",
            "SourceObjectLabel",
            "HVAC Source",
            "Original object label used to create this HVAC space",
        )
        added_source_label = True
    if "AllowOverlap" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyBool",
            "AllowOverlap",
            "HVAC Space",
            "Allow this HVAC analysis region to overlap other HVAC spaces",
        )
        added_allow_overlap = True
    if "HVACSchemaVersion" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyInteger",
            "HVACSchemaVersion",
            "MEP",
            "HVAC space data schema version",
        )
        added_schema_version = True
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
    if "SourceMode" in obj.PropertiesList:
        current_source_mode = str(getattr(obj, "SourceMode", "") or "")
        if added_source_mode:
            current_source_mode = (
                SOURCE_MODE_COPY if getattr(obj, "BaseSpace", None) is not None else SOURCE_MODE_CONVERT
            )
        try:
            obj.SourceMode = SOURCE_MODE_OPTIONS
        except Exception:
            pass
        if current_source_mode not in SOURCE_MODE_OPTIONS:
            current_source_mode = (
                SOURCE_MODE_COPY if getattr(obj, "BaseSpace", None) is not None else SOURCE_MODE_CONVERT
            )
        try:
            obj.SourceMode = current_source_mode
        except Exception:
            pass
    if added_source_name:
        obj.SourceObjectName = ""
    if added_source_label:
        obj.SourceObjectLabel = ""
    if added_allow_overlap:
        obj.AllowOverlap = True
    if added_schema_version or int(getattr(obj, "HVACSchemaVersion", 0) or 0) < SPACE_SCHEMA_VERSION:
        obj.HVACSchemaVersion = SPACE_SCHEMA_VERSION

    linked_source = getattr(obj, "BaseSpace", None)
    if linked_source is not None:
        if "SourceObjectName" in obj.PropertiesList and not str(getattr(obj, "SourceObjectName", "") or ""):
            obj.SourceObjectName = str(getattr(linked_source, "Name", "") or "")
        if "SourceObjectLabel" in obj.PropertiesList and not str(getattr(obj, "SourceObjectLabel", "") or ""):
            obj.SourceObjectLabel = str(getattr(linked_source, "Label", "") or "")


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


def _points_polygon_area_m2(base_obj):
    """Return XY polygon area for a closed Draft Wire Points list."""

    if base_obj is None:
        return None
    try:
        props = list(getattr(base_obj, "PropertiesList", []) or [])
    except Exception:
        props = []
    if "Points" not in props:
        return None
    try:
        points = list(getattr(base_obj, "Points", []) or [])
    except Exception:
        return None
    if len(points) < 3:
        return None

    closed = False
    if "Closed" in props:
        try:
            closed = bool(getattr(base_obj, "Closed", False))
        except Exception:
            closed = False
    try:
        first = points[0]
        last = points[-1]
        dx = float(first.x) - float(last.x)
        dy = float(first.y) - float(last.y)
        dz = float(first.z) - float(last.z)
        if ((dx * dx) + (dy * dy) + (dz * dz)) ** 0.5 <= 0.01:
            closed = True
            points = points[:-1]
    except Exception:
        pass
    if not closed or len(points) < 3:
        return None

    try:
        twice_area = 0.0
        for idx, point in enumerate(points):
            following = points[(idx + 1) % len(points)]
            twice_area += (float(point.x) * float(following.y)) - (
                float(following.x) * float(point.y)
            )
        area_mm2 = abs(twice_area) * 0.5
    except Exception:
        return None
    if area_mm2 <= 1.0:
        return None
    return area_mm2 / 1000000.0


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

    # Some imported/Draft wires expose themselves directly as ShapeType=Wire
    # without populating Shape.Wires.
    try:
        if str(getattr(shape, "ShapeType", "") or "") == "Wire" and shape.isClosed():
            face = Part.Face(shape)
            area_mm2 = _to_float(getattr(face, "Area", 0.0), 0.0)
            if area_mm2 > 0:
                return area_mm2 / 1000000.0
    except Exception:
        pass

    # Last wire fallback for compounds whose ordered edges form one loop.
    try:
        edges = list(getattr(shape, "Edges", []) or [])
        if edges:
            wire = Part.Wire(edges)
            if wire.isClosed():
                face = Part.Face(wire)
                area_mm2 = _to_float(getattr(face, "Area", 0.0), 0.0)
                if area_mm2 > 0:
                    return area_mm2 / 1000000.0
    except Exception:
        pass
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


def _wire_profile_area_m2(base_obj):
    """Return area only when an object represents a closed wire profile."""

    point_area = _points_polygon_area_m2(base_obj)
    if point_area is not None and point_area > 0:
        return point_area
    try:
        shape = getattr(base_obj, "Shape", None)
    except Exception:
        shape = None
    if shape is None or _shape_has_solids(shape):
        return None
    try:
        if list(getattr(shape, "Faces", []) or []):
            return None
    except Exception:
        pass
    return _shape_planar_area_m2(shape)


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
        if not _is_explicit_2d_area_type(base_obj) and _wire_profile_area_m2(base_obj) is None:
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

    # Draft Wire can provide a valid polygon even when its TopoShape does not
    # expose a Wires collection yet.
    points_area = _points_polygon_area_m2(base_obj)
    if points_area is not None and points_area > 0:
        return points_area

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
    geometry_obj = space_geometry_source(space_obj)
    return contains_point_in_base(geometry_obj, point, tol=tol)


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
        geometry_obj = space_geometry_source(space_obj)
        if geometry_obj is None:
            invalid_spaces.append(space_obj)
            continue
        strict_2d = geometry_obj is not space_obj
        if not _is_area_profile_candidate(geometry_obj, strict_2d=strict_2d):
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


def calculate_space_load(
    space_obj,
    project=None,
    refresh_area=True,
    ensure_schema=True,
    update_project_link=True,
):
    """Calculate cooling load for one space."""

    if space_obj is None:
        return 0.0

    if bool(ensure_schema):
        ensure_space_properties(space_obj)

    if bool(refresh_area):
        geometry_obj = space_geometry_source(space_obj)
        detected_area = detect_area_from_base(geometry_obj)
        if detected_area is not None and detected_area > 0:
            if abs(_to_float(space_obj.Area, 0.0) - float(detected_area)) > 0.001:
                space_obj.Area = round(detected_area, 3)

    project_obj = _find_project_for_space(space_obj, explicit_project=project)
    if (
        bool(update_project_link)
        and project_obj
        and "Project" in space_obj.PropertiesList
        and space_obj.Project is None
    ):
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
    if abs(old_load - cooling_load) > 0.01:
        space_obj.CoolingLoadBTU = cooling_load
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
    """Return only an explicitly selected group containing valid area profiles."""

    selected_objects = list(selected_objects or [])

    # Group names are intentionally ignored. Projects may use several area
    # collections with arbitrary names; only the user's selection is authoritative.
    for obj in selected_objects:
        if _is_group(obj):
            candidates = _area_object_candidates_from_group(obj)
            if candidates:
                return obj
    return None


def space_geometry_source(space_obj):
    """Return the object that currently owns the plan geometry for a space."""

    if space_obj is None:
        return None
    linked_base = _canonical_base_obj(getattr(space_obj, "BaseSpace", None))
    if linked_base is not None:
        return linked_base
    if (
        _mep_type(space_obj) == MEP_TYPE
        and str(getattr(space_obj, "SourceMode", "") or "") == SOURCE_MODE_CONVERT
        and hasattr(space_obj, "Shape")
    ):
        try:
            if not space_obj.Shape.isNull():
                return space_obj
        except Exception:
            return space_obj
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


def _create_or_update_space(doc, base_obj, project_obj=None, source_mode=SOURCE_MODE_COPY):
    base_obj = _canonical_base_obj(base_obj)
    if base_obj is None:
        return None, False
    if not _is_area_profile_candidate(base_obj, strict_2d=True):
        return None, False
    if source_mode not in SOURCE_MODE_OPTIONS:
        raise ValueError("Modo de origen HVAC no valido: {0}".format(source_mode))

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

    source_name = str(getattr(base_obj, "Name", "") or "")
    source_label = str(getattr(base_obj, "Label", "") or source_name)
    obj.SourceObjectName = source_name
    obj.SourceObjectLabel = source_label
    obj.AllowOverlap = True
    obj.SourceMode = SOURCE_MODE_COPY
    obj.BaseSpace = base_obj

    base_label = source_label
    if base_label.upper().startswith("HVAC_"):
        base_label = base_label[5:]
    if base_label:
        obj.Label = "HVAC_" + base_label
    detected_area = detect_area_from_base(base_obj)
    if detected_area is not None and detected_area > 0:
        obj.Area = round(detected_area, 3)
    if not _sync_space_shape_from_base(obj):
        raise RuntimeError("No se pudo copiar la geometria del area {0}".format(source_label or source_name))

    if project_obj is not None and "Project" in obj.PropertiesList and getattr(obj, "Project", None) is None:
        obj.Project = project_obj

    if source_mode == SOURCE_MODE_CONVERT:
        # The copied Shape becomes authoritative before the source is removed.
        obj.SourceMode = SOURCE_MODE_CONVERT
        obj.BaseSpace = None

    calculate_space_load(obj, project=project_obj, refresh_area=True)
    hvac_project.add_object_to_hvac_group(doc, obj)

    if source_mode == SOURCE_MODE_CONVERT and source_name:
        doc.removeObject(source_name)
    return obj, created


def collect_area_candidates(objects, log_groups=True):
    """Expand selected objects/groups into valid planar HVAC source profiles."""

    candidates = []
    for selected_obj in list(objects or []):
        obj = selection.unwrap_link(selected_obj)
        if obj is None:
            continue
        if _is_hvac_object(obj):
            linked_base = _canonical_base_obj(obj)
            if (
                linked_base is not None
                and linked_base is not obj
                and _is_area_profile_candidate(linked_base, strict_2d=True)
                and detect_area_from_base(linked_base) is not None
            ):
                candidates.append(linked_base)
            continue
        if _is_group(obj):
            group_candidates = _area_object_candidates_from_group(obj)
            if group_candidates:
                candidates.extend(group_candidates)
                if log_groups:
                    log(
                        "Grupo de areas seleccionado: {0} ({1} objetos)".format(
                            str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "?"),
                            len(group_candidates),
                        )
                    )
            continue
        if _is_area_profile_candidate(obj, strict_2d=True) and detect_area_from_base(obj) is not None:
            candidates.append(obj)

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
    return _deduplicate_objects(normalized)


def _conversion_blockers(base_obj):
    """Return non-container dependents that make deleting a source unsafe."""

    base_name = str(getattr(base_obj, "Name", "") or "")
    blockers = []
    for dependent in list(getattr(base_obj, "InList", []) or []):
        if dependent is None or _is_group(dependent):
            continue
        if _mep_type(dependent) == MEP_TYPE:
            linked = _canonical_base_obj(getattr(dependent, "BaseSpace", None))
            if str(getattr(linked, "Name", "") or "") == base_name:
                # Existing HVAC wrappers are intentionally consolidated before conversion.
                continue
        blockers.append(dependent)
    return blockers


def conversion_blockers(base_objects):
    """Return a traceable map of sources that cannot be safely removed."""

    blocked = {}
    for base_obj in collect_area_candidates(base_objects, log_groups=False):
        dependents = _conversion_blockers(base_obj)
        if dependents:
            blocked[base_obj] = dependents
    return blocked


def _format_conversion_blockers(blocked):
    rows = []
    for base_obj, dependents in blocked.items():
        source_label = str(getattr(base_obj, "Label", "") or getattr(base_obj, "Name", "") or "?")
        dependent_labels = [
            str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "?")
            for obj in dependents
        ]
        rows.append("{0}: {1}".format(source_label, ", ".join(dependent_labels)))
    return "\n".join(rows)


def create_spaces_from_objects(base_objects, doc=None, source_mode=SOURCE_MODE_COPY):
    """Create/update HVAC spaces from explicit sources without geometric overlap filtering."""

    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return []

    if source_mode not in SOURCE_MODE_OPTIONS:
        raise ValueError("Modo de origen HVAC no valido: {0}".format(source_mode))

    candidates = collect_area_candidates(base_objects)
    if not candidates:
        log(
            "No se actualizaron recintos: seleccione explicitamente los poligonos "
            "o el grupo de areas HVAC que desea procesar"
        )
        return []

    if source_mode == SOURCE_MODE_CONVERT:
        blocked = conversion_blockers(candidates)
        if blocked:
            raise RuntimeError(
                "No se pueden eliminar objetos fuente que tienen dependencias:\n{0}".format(
                    _format_conversion_blockers(blocked)
                )
            )

    transaction_open = False
    try:
        if hasattr(doc, "openTransaction"):
            operation_label = "HVAC: convertir espacios" if source_mode == SOURCE_MODE_CONVERT else "HVAC: copiar espacios"
            doc.openTransaction(operation_label)
            transaction_open = True

        # Maintenance is delayed until an explicit, valid selection exists.
        # These checks remove legacy nesting/duplicates, never geometric overlaps.
        cleanup_nested_spaces(doc)
        cleanup_non_area_spaces(doc)
        cleanup_duplicate_spaces(doc)

        projects = hvac_project.find_projects(doc)
        project_obj = projects[0] if projects else hvac_project.get_or_create_project(doc)

        spaces = []
        created_count = 0
        updated_count = 0
        for base_obj in candidates:
            source_name = str(getattr(base_obj, "Name", "") or "?")
            space_obj, created = _create_or_update_space(
                doc,
                base_obj,
                project_obj=project_obj,
                source_mode=source_mode,
            )
            if space_obj is None:
                continue
            spaces.append(space_obj)
            if created:
                created_count += 1
                log("Recinto HVAC creado desde area: {0}".format(source_name))
            else:
                updated_count += 1
                log("Recinto HVAC actualizado desde area: {0}".format(source_name))

        if transaction_open and hasattr(doc, "commitTransaction"):
            doc.commitTransaction()
            transaction_open = False
    except Exception:
        if transaction_open and hasattr(doc, "abortTransaction"):
            doc.abortTransaction()
        raise

    log(
        "Recintos HVAC procesados: total={0}, creados={1}, actualizados={2}, origen={3}, superposicion=permitida".format(
            len(spaces), created_count, updated_count, source_mode
        )
    )
    return spaces


def create_spaces_from_selection(doc=None, source_mode=SOURCE_MODE_COPY):
    """Backward-compatible selection API; defaults to preserving source objects."""

    selected = list(selection.get_selected_objects(resolve_links=True) or [])
    return create_spaces_from_objects(selected, doc=doc, source_mode=source_mode)


def _qt_widgets_module():
    try:
        from PySide6 import QtWidgets

        return QtWidgets
    except Exception:
        try:
            from PySide2 import QtWidgets

            return QtWidgets
        except Exception:
            try:
                from PySide import QtGui as QtWidgets

                return QtWidgets
            except Exception:
                return None


def _pick_source_mode_dialog(candidates):
    QtWidgets = _qt_widgets_module()
    if QtWidgets is None:
        return SOURCE_MODE_COPY

    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle(tr("space.dialog.title"))
    dialog.setMinimumWidth(520)

    intro = QtWidgets.QLabel(tr("space.dialog.selection", count=len(candidates)))
    intro.setWordWrap(True)

    source_list = QtWidgets.QListWidget()
    source_list.setMaximumHeight(130)
    for obj in candidates:
        label = str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "?")
        name = str(getattr(obj, "Name", "") or "")
        source_list.addItem("{0}  [{1}]".format(label, name))

    copy_radio = QtWidgets.QRadioButton(tr("space.dialog.copy"))
    copy_radio.setChecked(True)
    copy_help = QtWidgets.QLabel(tr("space.dialog.copy_help"))
    copy_help.setWordWrap(True)

    convert_radio = QtWidgets.QRadioButton(tr("space.dialog.convert"))
    convert_help = QtWidgets.QLabel(tr("space.dialog.convert_help"))
    convert_help.setWordWrap(True)

    overlap_note = QtWidgets.QLabel(tr("space.dialog.overlap"))
    overlap_note.setWordWrap(True)

    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addWidget(intro)
    layout.addWidget(source_list)
    layout.addWidget(copy_radio)
    layout.addWidget(copy_help)
    layout.addSpacing(6)
    layout.addWidget(convert_radio)
    layout.addWidget(convert_help)
    layout.addSpacing(8)
    layout.addWidget(overlap_note)
    layout.addWidget(buttons)

    result = dialog.exec_()
    if result != QtWidgets.QDialog.Accepted:
        return None
    if convert_radio.isChecked():
        return SOURCE_MODE_CONVERT
    return SOURCE_MODE_COPY


def create_spaces_interactive(doc=None):
    """GUI flow for copy-vs-convert creation from the current selection."""

    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return []

    selected = list(selection.get_selected_objects(resolve_links=True) or [])
    candidates = collect_area_candidates(selected)
    QtWidgets = _qt_widgets_module()
    if not candidates:
        message = tr("space.dialog.no_selection")
        log(message)
        if QtWidgets is not None:
            QtWidgets.QMessageBox.warning(None, tr("space.dialog.title"), message)
        return []

    source_mode = _pick_source_mode_dialog(candidates)
    if source_mode is None:
        log(tr("space.dialog.cancelled"))
        return []

    if source_mode == SOURCE_MODE_CONVERT:
        blocked = conversion_blockers(candidates)
        if blocked:
            message = tr("space.dialog.blocked", details=_format_conversion_blockers(blocked))
            log(message)
            if QtWidgets is not None:
                QtWidgets.QMessageBox.warning(None, tr("space.dialog.title"), message)
            return []
        if QtWidgets is not None:
            answer = QtWidgets.QMessageBox.question(
                None,
                tr("space.dialog.confirm_title"),
                tr("space.dialog.confirm", count=len(candidates)),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                log(tr("space.dialog.cancelled"))
                return []

    return create_spaces_from_objects(candidates, doc=doc, source_mode=source_mode)


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
        self._busy = True
        try:
            ensure_space_properties(obj)
        finally:
            self._busy = False

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
                calculate_space_load(
                    obj,
                    refresh_area=(prop == "BaseSpace"),
                    ensure_schema=False,
                )
            except Exception as exc:
                log(
                    "onChanged seguro omitido para {0} ({1}): {2}".format(
                        str(getattr(obj, "Name", "") or "?"),
                        str(prop or "?"),
                        str(exc or "error"),
                    )
                )
            finally:
                self._busy = False

    def execute(self, obj):
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        self._busy = True
        try:
            # Shape synchronization is intentionally excluded from execute().
            # Mutating Part geometry or schema while FreeCAD is recomputing can
            # trigger native Access violation errors on otherwise valid spaces.
            calculate_space_load(
                obj,
                refresh_area=False,
                ensure_schema=False,
                update_project_link=False,
            )
            self._last_execute_error = ""
        except Exception as exc:
            error_text = str(exc or "error")
            if getattr(self, "_last_execute_error", "") != error_text:
                log(
                    "execute seguro omitido para {0}: {1}".format(
                        str(getattr(obj, "Name", "") or "?"),
                        error_text,
                    )
                )
            self._last_execute_error = error_text
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

