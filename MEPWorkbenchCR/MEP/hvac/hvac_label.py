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
        return
    if hasattr(label_obj, "PropertiesList") and "LabelText" in label_obj.PropertiesList:
        label_obj.LabelText = lines
        return
    label_obj.Label = " | ".join(lines)


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
            bbox = base.Shape.BoundBox
            return App.Vector(bbox.Center.x, bbox.Center.y, bbox.ZMax + 800.0)
        except Exception:
            pass
    if hasattr(space_obj, "Placement"):
        return App.Vector(space_obj.Placement.Base).add(App.Vector(0, 0, 800))
    return App.Vector(0, 0, 800)


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

    if hasattr(label_obj, "Placement"):
        placement = label_obj.Placement
        placement.Base = _label_position(space_obj)
        label_obj.Placement = placement
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
