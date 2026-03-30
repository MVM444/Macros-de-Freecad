"""HVAC space object: cooling load belongs to the room/space."""

import os
import unicodedata

import FreeCAD as App
import Part

from ..utils import selection
from . import hvac_project

MEP_TYPE = "HVACSpace"
LOG_PREFIX = "[MEP-HVAC][Space] "
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "hvac.svg")
).replace(os.sep, "/")
AREA_GROUP_ALIASES = {"areas", "area", "recintos", "espacios", "zonas"}


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
    added_equipment = False
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
    if "Area" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Area", "HVAC Space", "Area in m2")
        added_area = True
    if "Height" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Height", "HVAC Space", "Height in meters")
        added_height = True
    if "Occupancy" not in obj.PropertiesList:
        obj.addProperty("App::PropertyInteger", "Occupancy", "HVAC Space", "Number of occupants")
        added_occupancy = True
    if "EquipmentLoad" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "EquipmentLoad",
            "HVAC Space",
            "Extra equipment load (BTU/h)",
        )
        added_equipment = True
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
    if added_equipment:
        obj.EquipmentLoad = 0.0
    if added_mode:
        obj.Mode = "Rapido"
    if added_load:
        obj.CoolingLoadBTU = 0.0


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


def detect_area_from_base(base_obj):
    if base_obj is None:
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

    # Fallback using footprint from bounding box.
    if hasattr(base_obj, "Shape"):
        try:
            bbox = base_obj.Shape.BoundBox
            area_m2 = (bbox.XLength * bbox.YLength) / 1000000.0
            if area_m2 > 0:
                return area_m2
        except Exception:
            pass
    return None


def find_spaces(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    spaces = []
    for obj in doc.Objects:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
            if str(obj.MEPType) == MEP_TYPE:
                spaces.append(obj)
    return spaces


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
    equipment = max(0.0, _to_float(space_obj.EquipmentLoad, 0.0))
    height = max(1.8, _to_float(space_obj.Height, 2.6))
    mode = str(space_obj.Mode)

    area_load = area * factor
    people_coeff = 600.0 if mode == "Rapido" else 650.0
    people_load = occupancy * people_coeff
    total = area_load + people_load + equipment

    if mode == "Preciso":
        height_factor = max(0.85, min(1.40, height / 2.6))
        total = total * height_factor

    old_load = _to_float(space_obj.CoolingLoadBTU, 0.0)
    cooling_load = round(total, 2)
    space_obj.CoolingLoadBTU = cooling_load
    if abs(old_load - cooling_load) > 0.01:
        log(
            "Carga recinto {0}: area={1} m2, factor={2}, personas={3}, equipos={4}, total={5}".format(
                space_obj.Name, round(area, 2), round(factor, 2), occupancy, round(equipment, 2), cooling_load
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
            if detect_area_from_base(unwrapped) is not None:
                candidates.append(unwrapped)
    return candidates


def _find_areas_group(doc, selected_objects=None):
    selected_objects = list(selected_objects or [])

    # 1) Prioridad: grupo seleccionado con objetos de area.
    for obj in selected_objects:
        if _is_group(obj):
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
        label_norm = _normalize_text(getattr(grp, "Label", ""))
        if label_norm in AREA_GROUP_ALIASES:
            return grp

    # 4) Heuristica: grupo con mas objetos geometricos de area.
    best_group = None
    best_count = 0
    for grp in _iter_doc_groups(doc):
        count = len(_area_object_candidates_from_group(grp))
        if count > best_count:
            best_group = grp
            best_count = count
    if best_group is not None and best_count > 0:
        return best_group
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
    for space in find_spaces(doc):
        if getattr(space, "BaseSpace", None) == base_obj:
            return space
    return None


def _create_or_update_space(doc, base_obj, project_obj=None):
    existing = _space_for_base(doc, base_obj)
    created = False
    if existing is None:
        obj = doc.addObject("App::FeaturePython", "HVAC_Space")
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
        if base_label:
            obj.Label = "HVAC_" + base_label
        detected_area = detect_area_from_base(base_obj)
        if detected_area is not None and detected_area > 0:
            obj.Area = round(detected_area, 3)

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

    selected = list(selection.get_selected_objects(resolve_links=True) or [])
    candidates = []

    for obj in selected:
        if _is_group(obj):
            candidates.extend(_area_object_candidates_from_group(obj))
            continue
        if detect_area_from_base(obj) is not None:
            candidates.append(obj)

    if not candidates:
        auto_group = _find_areas_group(doc, selected_objects=selected)
        if auto_group is not None:
            candidates = _area_object_candidates_from_group(auto_group)
            log(
                "Grupo de areas detectado: {0} ({1} objetos)".format(
                    getattr(auto_group, "Label", getattr(auto_group, "Name", "?")),
                    len(candidates),
                )
            )

    candidates = _deduplicate_objects(candidates)
    if not candidates:
        log("Seleccione un poligono/recinto o un grupo Areas con geometria valida")
        return []

    projects = hvac_project.find_projects(doc)
    project_obj = projects[0] if projects else hvac_project.get_or_create_project(doc)

    spaces = []
    created_count = 0
    updated_count = 0
    for base_obj in candidates:
        space_obj, created = _create_or_update_space(doc, base_obj, project_obj=project_obj)
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
    return spaces


def has_area_selection():
    selected = list(selection.get_selected_objects(resolve_links=True) or [])
    for obj in selected:
        if _is_group(obj):
            return True
        if detect_area_from_base(obj) is not None:
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
        if prop in {"Area", "Height", "Occupancy", "EquipmentLoad", "Mode", "Project", "BaseSpace"}:
            self._busy = True
            try:
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
        pass

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

