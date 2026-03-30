"""Selection helpers with App::Link awareness."""

import FreeCAD as App

try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - console mode
    Gui = None


def _safe_gui_selection():
    if Gui is None:
        return []
    try:
        return Gui.Selection.getSelectionEx() or []
    except Exception:
        return []


def unwrap_link(obj):
    """Return linked target when the input is App::Link, otherwise itself."""

    if obj is None:
        return None
    if hasattr(obj, "isDerivedFrom"):
        try:
            if obj.isDerivedFrom("App::Link") and getattr(obj, "LinkedObject", None):
                return obj.LinkedObject
        except Exception:
            pass
    return obj


def get_selected_objects(resolve_links=True):
    """Return current GUI selection as document objects."""

    objects = []
    for sel in _safe_gui_selection():
        obj = getattr(sel, "Object", None)
        if resolve_links:
            obj = unwrap_link(obj)
        if obj is not None:
            objects.append(obj)
    return objects


def first_selected_object(resolve_links=True):
    """Return first selected object or None."""

    objects = get_selected_objects(resolve_links=resolve_links)
    if objects:
        return objects[0]
    return None


def get_selected_points():
    """Collect point vectors from selected sub-elements when available."""

    points = []
    for sel in _safe_gui_selection():
        for sub in getattr(sel, "SubObjects", []) or []:
            if hasattr(sub, "Point"):
                points.append(App.Vector(sub.Point))
            elif hasattr(sub, "CenterOfMass"):
                points.append(App.Vector(sub.CenterOfMass))
    return points


def object_mep_type(obj):
    """Read MEPType property defensively."""

    if obj is None:
        return ""
    if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList:
        try:
            return str(obj.MEPType)
        except Exception:
            return ""
    return ""

