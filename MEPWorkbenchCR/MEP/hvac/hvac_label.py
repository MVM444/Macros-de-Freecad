"""HVAC labels linked to spaces with live load and coverage summary."""

import os

import FreeCAD as App

from . import hvac_equipment
from . import hvac_project
from . import hvac_space

MEP_TYPE = "HVACLabel"
LOG_PREFIX = "[MEP-HVAC][Label] "
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "hvac.svg")
).replace(os.sep, "/")
DEFAULT_LABEL_SIZE = 200.0
DEBUG_LABEL_POSITION = True


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


def ensure_label_properties(obj):
    added_auto = False
    if "MEPType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
    if str(getattr(obj, "MEPType", "")) != MEP_TYPE:
        obj.MEPType = MEP_TYPE

    if "Space" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "Space", "HVAC Label", "Linked HVAC space")
    if "AutoUpdate" not in obj.PropertiesList:
        obj.addProperty("App::PropertyBool", "AutoUpdate", "HVAC Label", "Auto refresh text values")
        added_auto = True
    if added_auto:
        obj.AutoUpdate = True


def _space_name(space_obj):
    def _clean_name(raw):
        text = str(raw or "").strip()
        if text.upper().startswith("HVAC_"):
            text = text[5:]
        return text

    base = getattr(space_obj, "BaseSpace", None)
    if base is not None and getattr(base, "Label", ""):
        return _clean_name(base.Label).upper()
    if getattr(space_obj, "Label", ""):
        return _clean_name(space_obj.Label).upper()
    return str(space_obj.Name).upper()


def _space_equipment_capacity(doc, space_obj):
    capacity = 0.0
    for equipment in hvac_equipment.find_equipments(doc):
        if getattr(equipment, "Space", None) == space_obj:
            capacity += _to_float(equipment.CapacityBTU, 0.0)
    return round(capacity, 2)


def _build_label_lines(doc, space_obj):
    space_name = _space_name(space_obj)
    load = _to_float(space_obj.CoolingLoadBTU, 0.0)
    capacity = _space_equipment_capacity(doc, space_obj)
    coverage = 0.0
    if load > 0:
        coverage = (capacity / load) * 100.0

    line_1 = "{0}".format(space_name)
    line_2 = "{0:.0f} BTU/h".format(load)
    line_3 = "EQ: {0:.0f} ({1:.0f}%)".format(capacity, coverage)
    return [line_1, line_2, line_3]


def _set_label_text(label_obj, lines):
    if hasattr(label_obj, "PropertiesList") and "Text" in label_obj.PropertiesList:
        label_obj.Text = lines
    elif hasattr(label_obj, "PropertiesList") and "LabelText" in label_obj.PropertiesList:
        label_obj.LabelText = lines
    elif hasattr(label_obj, "PropertiesList") and "Strings" in label_obj.PropertiesList:
        label_obj.Strings = lines
    elif hasattr(label_obj, "PropertiesList") and "String" in label_obj.PropertiesList:
        label_obj.String = "\n".join(lines)
    label_obj.Label = "HVAC_Label_" + str(lines[0] if lines else getattr(label_obj, "Name", ""))


def _world_point_from_base(base_obj, point_local):
    point = App.Vector(point_local)
    placement = None
    try:
        if hasattr(base_obj, "getGlobalPlacement"):
            placement = base_obj.getGlobalPlacement()
    except Exception:
        placement = None
    if placement is None and hasattr(base_obj, "Placement"):
        try:
            placement = base_obj.Placement
        except Exception:
            placement = None
    if placement is None:
        return point
    try:
        return placement.multVec(point)
    except Exception:
        return point


def _base_reference_point(base_obj):
    if base_obj is None:
        return App.Vector(0.0, 0.0, 0.0)
    try:
        if hasattr(base_obj, "getGlobalPlacement"):
            gp = base_obj.getGlobalPlacement()
            if gp is not None:
                return App.Vector(gp.Base)
    except Exception:
        pass
    try:
        if hasattr(base_obj, "Placement"):
            return App.Vector(base_obj.Placement.Base)
    except Exception:
        pass
    return App.Vector(0.0, 0.0, 0.0)


def _fmt_vec(vec):
    try:
        v = App.Vector(vec)
        return "({0:.1f},{1:.1f},{2:.1f})".format(float(v.x), float(v.y), float(v.z))
    except Exception:
        return "(?, ?, ?)"


def _log_position_debug(space_obj, base_obj, bbox, raw_point, transformed_point, final_point, mode):
    if not DEBUG_LABEL_POSITION:
        return
    try:
        ref = _base_reference_point(base_obj)
        msg = (
            "PosDebug space={0} base={1} mode={2} ref={3} bbox_center={4} raw={5} transformed={6} final={7}"
        ).format(
            str(getattr(space_obj, "Name", "?")),
            str(getattr(base_obj, "Name", "?")),
            str(mode),
            _fmt_vec(ref),
            _fmt_vec(getattr(bbox, "Center", App.Vector(0.0, 0.0, 0.0))),
            _fmt_vec(raw_point),
            _fmt_vec(transformed_point),
            _fmt_vec(final_point),
        )
        log(msg)
    except Exception:
        pass


def _point_is_already_global(base_obj, bbox, point):
    """Heuristic: detect when Draft shape points already include object placement."""

    if base_obj is None:
        return True
    try:
        base_pos = _base_reference_point(base_obj)
        test = App.Vector(point)
        dx = abs(float(test.x) - float(base_pos.x))
        dy = abs(float(test.y) - float(base_pos.y))
        limit_x = max(100.0, float(getattr(bbox, "XLength", 0.0)) * 1.6)
        limit_y = max(100.0, float(getattr(bbox, "YLength", 0.0)) * 1.6)
        return dx <= limit_x and dy <= limit_y
    except Exception:
        return True


def _set_label_style(label_obj):
    if label_obj is None:
        return

    for prop_name in ("FontSize", "Size", "TextSize"):
        try:
            if hasattr(label_obj, "PropertiesList") and prop_name in label_obj.PropertiesList:
                setattr(label_obj, prop_name, DEFAULT_LABEL_SIZE)
        except Exception:
            continue
    _set_center_justification(label_obj)

    vobj = getattr(label_obj, "ViewObject", None)
    if vobj is not None:
        for view_prop in ("FontSize", "TextSize", "PointSize"):
            try:
                if hasattr(vobj, view_prop):
                    setattr(vobj, view_prop, DEFAULT_LABEL_SIZE)
            except Exception:
                continue
        _set_center_justification(vobj)
        try:
            if hasattr(vobj, "ShowInTree"):
                vobj.ShowInTree = False
        except Exception:
            pass


def _enum_values(obj, prop_name):
    try:
        getter = getattr(obj, "getEnumerationsOfProperty", None)
        if getter is None:
            return []
        values = getter(prop_name)
        return [str(value) for value in list(values or [])]
    except Exception:
        return []


def _pick_center_value(options):
    if not options:
        return "Center"

    normalized = [(opt, str(opt).strip().lower()) for opt in options]
    middle_center_tokens = (
        "middlecenter",
        "middle center",
        "mid center",
        "midcenter",
        "middle-centre",
        "middle centre",
        "medio centro",
        "centro medio",
    )
    for original, key in normalized:
        compact = key.replace("_", " ").replace("-", " ")
        compact = " ".join(compact.split())
        if "center" in compact or "centre" in compact or "centro" in compact:
            if "middle" in compact or "mid" in compact or "medio" in compact:
                return original
        joined = compact.replace(" ", "")
        if joined in middle_center_tokens:
            return original

    exact_targets = {"center", "centre", "centro", "middle", "medio", "centrado"}
    for original, key in normalized:
        if key in exact_targets:
            return original

    contains_targets = ("center", "centre", "middle", "medio", "centr")
    for original, key in normalized:
        if any(token in key for token in contains_targets):
            return original

    for original, key in normalized:
        if "left" not in key and "right" not in key and "izq" not in key and "der" not in key:
            return original
    return options[0]


def _set_center_justification(target_obj):
    if target_obj is None:
        return

    candidates = ("Justification", "TextAlign", "HorizontalAlignment")
    for prop_name in candidates:
        has_prop = False
        try:
            if hasattr(target_obj, "PropertiesList") and prop_name in target_obj.PropertiesList:
                has_prop = True
            elif hasattr(target_obj, prop_name):
                has_prop = True
        except Exception:
            has_prop = False
        if not has_prop:
            continue

        options = _enum_values(target_obj, prop_name)
        preferred = _pick_center_value(options)
        try:
            setattr(target_obj, prop_name, preferred)
        except Exception:
            try:
                setattr(target_obj, prop_name, "Center")
            except Exception:
                continue


def _make_annotation_text(doc, lines, point):
    if doc is None:
        return None
    label_obj = doc.addObject("App::AnnotationLabel", "HVAC_Label")
    if label_obj is None:
        return None

    try:
        if hasattr(label_obj, "PropertiesList") and "LabelText" in label_obj.PropertiesList:
            label_obj.LabelText = list(lines)
    except Exception:
        pass
    try:
        if hasattr(label_obj, "PropertiesList") and "Text" in label_obj.PropertiesList:
            label_obj.Text = list(lines)
    except Exception:
        pass
    try:
        if hasattr(label_obj, "PropertiesList") and "BasePosition" in label_obj.PropertiesList:
            label_obj.BasePosition = App.Vector(point)
        elif hasattr(label_obj, "PropertiesList") and "Position" in label_obj.PropertiesList:
            label_obj.Position = App.Vector(point)
        elif hasattr(label_obj, "Placement"):
            placement = label_obj.Placement
            placement.Base = App.Vector(point)
            label_obj.Placement = placement
    except Exception:
        pass
    return label_obj


def _make_draft_text(doc, lines, point):
    import Draft

    call_attempts = []
    if hasattr(Draft, "make_text"):
        call_attempts.extend(
            [
                lambda: Draft.make_text(lines, point=point),
                lambda: Draft.make_text("\n".join(lines), point=point),
                lambda: Draft.make_text(lines, point),
                lambda: Draft.make_text("\n".join(lines), point),
                lambda: Draft.make_text(lines),
                lambda: Draft.make_text("\n".join(lines)),
            ]
        )
    if hasattr(Draft, "makeText"):
        call_attempts.extend(
            [
                lambda: Draft.makeText(lines, point=point),
                lambda: Draft.makeText("\n".join(lines), point=point),
                lambda: Draft.makeText(lines, point),
                lambda: Draft.makeText("\n".join(lines), point),
                lambda: Draft.makeText(lines),
                lambda: Draft.makeText("\n".join(lines)),
            ]
        )

    last_error = None
    for call in call_attempts:
        try:
            obj = call()
            if obj is not None:
                return obj
        except Exception as exc:
            last_error = exc
            continue

    fallback = _make_annotation_text(doc, lines, point)
    if fallback is not None:
        log("Fallback etiqueta App::AnnotationLabel por incompatibilidad Draft: {0}".format(last_error))
        return fallback

    raise RuntimeError("No se pudo crear texto HVAC: {0}".format(last_error))


def _label_position(space_obj):
    base = getattr(space_obj, "BaseSpace", None)
    if base is not None and hasattr(base, "Shape"):
        try:
            shape = base.Shape
            # Use geometric centroid from the largest face for better centering on irregular polygons.
            faces = list(getattr(shape, "Faces", []) or [])
            if faces:
                largest = None
                max_area = -1.0
                for face in faces:
                    try:
                        area = _to_float(getattr(face, "Area", 0.0), 0.0)
                    except Exception:
                        area = 0.0
                    if area > max_area:
                        max_area = area
                        largest = face
                if largest is not None:
                    com = largest.CenterOfMass
                    z_plane = _to_float(getattr(largest.BoundBox, "ZMin", com.z), com.z)
                    point = App.Vector(com.x, com.y, z_plane)
                    transformed = _world_point_from_base(base, point)
                    if _point_is_already_global(base, shape.BoundBox, point):
                        _log_position_debug(space_obj, base, shape.BoundBox, point, transformed, point, "raw")
                        return point
                    _log_position_debug(space_obj, base, shape.BoundBox, point, transformed, transformed, "transformed")
                    return transformed

            com = shape.CenterOfMass
            bbox = shape.BoundBox
            point = App.Vector(com.x, com.y, bbox.ZMin)
            transformed = _world_point_from_base(base, point)
            if _point_is_already_global(base, bbox, point):
                _log_position_debug(space_obj, base, bbox, point, transformed, point, "raw")
                return point
            _log_position_debug(space_obj, base, bbox, point, transformed, transformed, "transformed")
            return transformed
        except Exception:
            pass
    if hasattr(space_obj, "Placement"):
        base_point = App.Vector(space_obj.Placement.Base)
        return App.Vector(base_point.x, base_point.y, base_point.z)
    return App.Vector(0, 0, 0)


def find_labels(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    labels = []
    for obj in doc.Objects:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == MEP_TYPE:
            labels.append(obj)
    return labels


def _find_label_for_space(doc, space_obj):
    for label in find_labels(doc):
        if getattr(label, "Space", None) == space_obj:
            return label
    return None


def remove_labels_for_spaces(space_objects, doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0
    targets = set()
    for space in list(space_objects or []):
        if space is None:
            continue
        targets.add(str(getattr(space, "Name", "") or ""))

    removed = 0
    if not targets:
        return removed

    for label in list(find_labels(doc)):
        linked_space = getattr(label, "Space", None)
        linked_name = str(getattr(linked_space, "Name", "") or "")
        if linked_name not in targets:
            continue
        try:
            doc.removeObject(label.Name)
            removed += 1
        except Exception:
            continue
    if removed > 0:
        log("Etiquetas HVAC eliminadas por limpieza: {0}".format(removed))
    return removed


def create_or_update_label(space_obj, doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None or space_obj is None:
        return None

    lines = _build_label_lines(doc, space_obj)
    label_obj = _find_label_for_space(doc, space_obj)
    if label_obj is None:
        label_obj = _make_draft_text(doc, lines, _label_position(space_obj))
        ensure_label_properties(label_obj)
        label_obj.Space = space_obj
        label_obj.Label = "HVAC_Label_{0}".format(space_obj.Name)
        log("Etiqueta creada para recinto: {0}".format(space_obj.Name))
    else:
        ensure_label_properties(label_obj)

    _set_label_text(label_obj, lines)
    _set_label_style(label_obj)

    if hasattr(label_obj, "Placement"):
        placement = label_obj.Placement
        placement.Base = _label_position(space_obj)
        label_obj.Placement = placement
    if hasattr(label_obj, "ViewObject"):
        try:
            label_obj.ViewObject.Visibility = True
        except Exception:
            pass
    hvac_project.add_object_to_hvac_group(doc, label_obj)

    return label_obj


def update_all_labels(doc=None, ensure_visible=False):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return
    for space_obj in hvac_space.find_spaces(doc):
        label_obj = create_or_update_label(space_obj, doc)
        if ensure_visible and label_obj is not None and hasattr(label_obj, "ViewObject"):
            label_obj.ViewObject.Visibility = True


def toggle_labels(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return

    labels = find_labels(doc)
    if not labels:
        update_all_labels(doc)
        labels = find_labels(doc)
        for label in labels:
            if hasattr(label, "ViewObject"):
                label.ViewObject.Visibility = True
        log("Etiquetas HVAC creadas y visibles")
        return

    visible_any = False
    for label in labels:
        if hasattr(label, "ViewObject") and bool(getattr(label.ViewObject, "Visibility", False)):
            visible_any = True
            break

    target_visibility = not visible_any
    for label in labels:
        if hasattr(label, "ViewObject"):
            label.ViewObject.Visibility = target_visibility

    state = "visible" if target_visibility else "ocultas"
    log("Etiquetas HVAC ahora estan {0}".format(state))


class HVACLabelViewProvider:
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
