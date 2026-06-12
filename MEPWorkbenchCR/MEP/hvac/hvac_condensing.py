"""HVAC condenser object and capacity validation."""

# Qt compatibility for FreeCAD 1.x (PySide6) and older builds.
def _ensure_qt_compat():
    import sys
    import types

    QtCore = QtGui = QtWidgets = None
    binding_name = None

    for candidate in ("PySide6", "PySide2", "PySide"):
        try:
            if candidate == "PySide":
                from PySide import QtCore as _QtCore, QtGui as _QtGui
                _QtWidgets = _QtGui
            else:
                module = __import__(candidate, fromlist=["QtCore", "QtGui", "QtWidgets"])
                _QtCore = module.QtCore
                _QtGui = module.QtGui
                _QtWidgets = module.QtWidgets
            QtCore, QtGui, QtWidgets = _QtCore, _QtGui, _QtWidgets
            binding_name = candidate
            break
        except Exception:
            continue

    if QtCore is None:
        return

    qtgui_compat = types.ModuleType("QtGui")
    qtgui_compat.__dict__.update(getattr(QtGui, "__dict__", {}))
    qtgui_compat.__dict__.update(getattr(QtWidgets, "__dict__", {}))

    qtsvg_compat = None
    for module_name in ("QtSvg", "QtSvgWidgets"):
        try:
            module = __import__(binding_name, fromlist=[module_name])
            qt_module = getattr(module, module_name)
        except Exception:
            continue
        if qtsvg_compat is None:
            qtsvg_compat = types.ModuleType("QtSvg")
        qtsvg_compat.__dict__.update(getattr(qt_module, "__dict__", {}))

    qtuitools_compat = None
    try:
        module = __import__(binding_name, fromlist=["QtUiTools"])
        qtuitools_compat = module.QtUiTools
    except Exception:
        pass

    for package_name in ("PySide2", "PySide"):
        package = sys.modules.get(package_name)
        if package is None:
            package = types.ModuleType(package_name)
            sys.modules[package_name] = package
        package.QtCore = QtCore
        package.QtGui = qtgui_compat
        package.QtWidgets = QtWidgets
        sys.modules[package_name + ".QtCore"] = QtCore
        sys.modules[package_name + ".QtGui"] = qtgui_compat
        sys.modules[package_name + ".QtWidgets"] = QtWidgets
        if qtsvg_compat is not None:
            package.QtSvg = qtsvg_compat
            sys.modules[package_name + ".QtSvg"] = qtsvg_compat
        if qtuitools_compat is not None:
            package.QtUiTools = qtuitools_compat
            sys.modules[package_name + ".QtUiTools"] = qtuitools_compat


_ensure_qt_compat()

import os

import FreeCAD as App
import Part

from ..utils import selection
from . import hvac_equipment
from . import hvac_project

MEP_TYPE = "HVACCondenser"
MASTER_MEP_TYPE = "HVACCondenserMaster"
SYMBOL2D_MEP_TYPE = "HVACCondenser2D"
INFO2D_MEP_TYPE = "HVACCondenserInfo2D"
INFO2D_DEBUG_ENABLED = True
LOG_PREFIX = "[MEP-HVAC][Condenser] "
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "hvac.svg")
).replace(os.sep, "/")
MASTER_PREFIX = "HVAC_CondMaster_"
DEFAULT_SYMBOL_SIZE = 650.0
VISUAL_MODE_OPTIONS = ["Ambos", "Solo2D", "Solo3D", "Ninguno"]
DEFAULT_VISUAL_MODE = "Ambos"
DEFAULT_INFO2D_SIZE = 95.0
MIN_INFO2D_SIZE = 20.0
MAX_INFO2D_SIZE = 700.0

DISCHARGE_OPTIONS = ["Horizontal", "Vertical"]
STEP_EXTENSIONS = (".step", ".stp", ".stpz")

# Practical baseline:
# - Mini-split small capacities typically use horizontal (side) discharge.
# - Vertical discharge is offered from larger capacities.
CONDENSER_LIBRARY = {
    "MiniSplit_12000_Horizontal": {
        "CapacityBTU": 12000.0,
        "Discharge": "Horizontal",
        "Size": (820.0, 320.0, 600.0),
        "StepFile": "Condenser_12000_Horizontal.step",
        "Step2DFile": "MiniSplit_12000_Horizontal_2D.step",
    },
    "MiniSplit_18000_Horizontal": {
        "CapacityBTU": 18000.0,
        "Discharge": "Horizontal",
        "Size": (860.0, 340.0, 620.0),
        "StepFile": "Condenser_18000_Horizontal.step",
        "Step2DFile": "MiniSplit_18000_Horizontal_2D.step",
    },
    "MiniSplit_24000_Horizontal": {
        "CapacityBTU": 24000.0,
        "Discharge": "Horizontal",
        "Size": (900.0, 360.0, 680.0),
        "StepFile": "Condenser_24000_Horizontal.step",
        "Step2DFile": "MiniSplit_24000_Horizontal_2D.step",
    },
    "Condenser_36000_Vertical": {
        "CapacityBTU": 36000.0,
        "Discharge": "Vertical",
        "Size": (900.0, 900.0, 920.0),
        "StepFile": "Condenser_36000_Vertical.step",
        "Step2DFile": "Condenser_36000_Vertical_2D.step",
    },
    "Condenser_48000_Vertical": {
        "CapacityBTU": 48000.0,
        "Discharge": "Vertical",
        "Size": (980.0, 980.0, 980.0),
        "StepFile": "Condenser_48000_Vertical.step",
        "Step2DFile": "Condenser_48000_Vertical_2D.step",
    },
    "Condenser_60000_Vertical": {
        "CapacityBTU": 60000.0,
        "Discharge": "Vertical",
        "Size": (1080.0, 1080.0, 1100.0),
        "StepFile": "Condenser_60000_Vertical.step",
        "Step2DFile": "Condenser_60000_Vertical_2D.step",
    },
}
DEFAULT_CONDENSER_MODEL = "MiniSplit_12000_Horizontal"
_STEP_SHAPE_CACHE = {}
_STEP_FILE_INDEX_CACHE = None
_SYMBOL2D_FILE_INDEX_CACHE = None
MASTER_SHAPE_SCHEMA_REV = "2026-04-13-r1"
STEP_MASTER_AUTO_RELOAD = False


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


def _clamp(value, vmin, vmax):
    return max(float(vmin), min(float(vmax), float(value)))


def _normalized_info2d_size(value):
    size = _to_float(value, DEFAULT_INFO2D_SIZE)
    if size <= 0.0:
        return float(DEFAULT_INFO2D_SIZE)
    return _clamp(size, MIN_INFO2D_SIZE, MAX_INFO2D_SIZE)


def _normalized_visual_mode(value):
    mode = str(value or DEFAULT_VISUAL_MODE).strip()
    if mode not in VISUAL_MODE_OPTIONS:
        return DEFAULT_VISUAL_MODE
    return mode


def _safe_obj_name(obj):
    if obj is None:
        return ""
    try:
        return str(getattr(obj, "Name", "") or "")
    except Exception:
        return ""


def _safe_obj_label(obj):
    if obj is None:
        return ""
    try:
        return str(getattr(obj, "Label", "") or "")
    except Exception:
        return ""


def _view_visibility(obj):
    if obj is None:
        return None
    try:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return None
        return bool(getattr(vobj, "Visibility", False))
    except Exception:
        return None


def _is_group(obj):
    type_id = str(getattr(obj, "TypeId", "") or "")
    if type_id.startswith("App::DocumentObjectGroup"):
        return True
    return hasattr(obj, "Group") and hasattr(obj, "addObject")


def _group_memberships(obj):
    if obj is None:
        return []
    doc = getattr(obj, "Document", None)
    if doc is None:
        return []
    memberships = []
    for candidate in list(getattr(doc, "Objects", []) or []):
        if candidate is None or not _is_group(candidate):
            continue
        try:
            children = list(getattr(candidate, "Group", []) or [])
            if obj in children:
                memberships.append(str(getattr(candidate, "Name", "") or getattr(candidate, "Label", "") or "?"))
        except Exception:
            continue
    return memberships


def _symbol_size_mm(condenser_obj):
    return max(100.0, _to_float(getattr(condenser_obj, "Symbol2DSize", DEFAULT_SYMBOL_SIZE), DEFAULT_SYMBOL_SIZE))


def _format_btu_label(value):
    try:
        number = int(round(_to_float(value, 0.0)))
    except Exception:
        number = 0
    text = "{0:,}".format(max(0, number))
    return text.replace(",", " ")


def _labelize_token(value):
    text = str(value or "").strip().upper()
    text = text.replace("-", " ")
    return " ".join(text.split())


def _normalize_discharge(value):
    raw = str(value or "").strip().lower()
    if raw in {"vertical", "top", "upflow"}:
        return "Vertical"
    if raw in {"horizontal", "side", "sidedischarge", "side_discharge"}:
        return "Horizontal"
    return "Horizontal"


def _sanitize_model_token(model_name):
    token = str(model_name or "").strip()
    if not token:
        return "Default"
    chars = []
    for char in token:
        if char.isalnum():
            chars.append(char)
        else:
            chars.append("_")
    normalized = "".join(chars).strip("_")
    return normalized or "Default"


def _master_internal_name(model_name):
    return "{0}{1}".format(MASTER_PREFIX, _sanitize_model_token(model_name))


def _is_link_condenser(obj):
    if obj is None:
        return False
    return str(getattr(obj, "TypeId", "") or "") == "App::Link"


def _is_master_condenser_obj(obj):
    if obj is None:
        return False
    try:
        props = list(getattr(obj, "PropertiesList", []) or [])
        if "MEPType" not in props:
            return False
        return str(getattr(obj, "MEPType", "") or "") == MASTER_MEP_TYPE
    except Exception:
        return False


def _configure_link_for_transform(link_obj):
    if link_obj is None or not _is_link_condenser(link_obj):
        return
    try:
        link_obj.LinkTransform = True
    except Exception:
        pass
    try:
        link_obj.setEditorMode("Placement", 0)
    except Exception:
        pass
    try:
        link_obj.setEditorMode("LinkPlacement", 0)
    except Exception:
        pass
    try:
        link_obj.setPropertyStatus("Placement", [])
    except Exception:
        pass
    try:
        link_obj.setPropertyStatus("LinkPlacement", [])
    except Exception:
        pass
    try:
        if hasattr(link_obj, "ViewObject") and link_obj.ViewObject is not None:
            if hasattr(link_obj.ViewObject, "Selectable"):
                link_obj.ViewObject.Selectable = True
    except Exception:
        pass


def _condenser_spec(model_name):
    return CONDENSER_LIBRARY.get(str(model_name), CONDENSER_LIBRARY[DEFAULT_CONDENSER_MODEL])


def _available_models_for_discharge(discharge):
    target = _normalize_discharge(discharge)
    models = []
    for model_name, spec in CONDENSER_LIBRARY.items():
        if _normalize_discharge(spec.get("Discharge", "Horizontal")) == target:
            models.append(model_name)
    return sorted(models, key=lambda name: (_to_float(_condenser_spec(name).get("CapacityBTU", 0.0), 0.0), name))


def _guess_model_from_capacity(capacity_btu, discharge=None):
    cap = max(0.0, _to_float(capacity_btu, 0.0))
    if discharge is None or str(discharge).strip() == "":
        discharge = "Vertical" if cap >= 36000.0 else "Horizontal"
    discharge = _normalize_discharge(discharge)

    candidates = _available_models_for_discharge(discharge)
    if not candidates:
        return DEFAULT_CONDENSER_MODEL

    best_model = candidates[0]
    best_delta = abs(_to_float(_condenser_spec(best_model).get("CapacityBTU", 0.0), 0.0) - cap)
    for model_name in candidates[1:]:
        model_cap = _to_float(_condenser_spec(model_name).get("CapacityBTU", 0.0), 0.0)
        delta = abs(model_cap - cap)
        if delta < best_delta:
            best_model = model_name
            best_delta = delta
    return best_model


def _condensers_library_dir():
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "resources",
            "libraries",
            "hvac",
            "condensers",
        )
    )


def _symbol2d_library_dir():
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "resources",
            "libraries",
            "hvac",
            "symbols2d",
            "condensers",
        )
    )


def _step_file_index():
    global _STEP_FILE_INDEX_CACHE
    cached = _STEP_FILE_INDEX_CACHE
    if isinstance(cached, dict) and cached:
        return cached

    index = {}
    library_dir = _condensers_library_dir()
    if not os.path.isdir(library_dir):
        return index
    try:
        for root_dir, _dirs, files in os.walk(library_dir):
            for entry in files:
                ext = os.path.splitext(entry)[1].lower()
                if ext not in STEP_EXTENSIONS:
                    continue
                base = os.path.splitext(entry)[0].strip().lower()
                if not base:
                    continue
                path = os.path.join(root_dir, entry)
                previous = index.get(base, "")
                if not previous:
                    index[base] = path
                    continue
                # Prefer file located directly in condensers root.
                prev_dir = os.path.abspath(os.path.dirname(previous))
                curr_dir = os.path.abspath(root_dir)
                root_abs = os.path.abspath(library_dir)
                if prev_dir != root_abs and curr_dir == root_abs:
                    index[base] = path
    except Exception:
        return index
    _STEP_FILE_INDEX_CACHE = index
    return index


def _symbol2d_file_index():
    global _SYMBOL2D_FILE_INDEX_CACHE
    cached = _SYMBOL2D_FILE_INDEX_CACHE
    if isinstance(cached, dict) and cached:
        return cached

    index = {}
    library_dir = _symbol2d_library_dir()
    if not os.path.isdir(library_dir):
        return index
    try:
        for root_dir, _dirs, files in os.walk(library_dir):
            for entry in files:
                ext = os.path.splitext(entry)[1].lower()
                if ext not in STEP_EXTENSIONS:
                    continue
                base = os.path.splitext(entry)[0].strip().lower()
                if not base:
                    continue
                path = os.path.join(root_dir, entry)
                previous = index.get(base, "")
                if not previous:
                    index[base] = path
                    continue
                prev_dir = os.path.abspath(os.path.dirname(previous))
                curr_dir = os.path.abspath(root_dir)
                root_abs = os.path.abspath(library_dir)
                if prev_dir != root_abs and curr_dir == root_abs:
                    index[base] = path
    except Exception:
        return index
    _SYMBOL2D_FILE_INDEX_CACHE = index
    return index


def _resolve_symbol2d_step_for_model(model_name):
    model = str(model_name or "").strip()
    if not model:
        return ""
    spec = _condenser_spec(model)
    candidates = []
    configured = str(spec.get("Step2DFile", "") or spec.get("Symbol2DStepFile", "")).strip()
    if configured:
        candidates.append(os.path.splitext(configured)[0].lower())

    base = os.path.splitext(model)[0].strip()
    if base:
        candidates.extend(
            [
                "{0}_2D".format(base).lower(),
                "{0}_2d".format(base).lower(),
                base.lower(),
            ]
        )

    index = _symbol2d_file_index()
    for key in candidates:
        path = index.get(str(key).strip().lower(), "")
        if path and os.path.isfile(path):
            return path
    return ""


def _resolve_step_file_for_model(model_name):
    model = str(model_name or "").strip()
    if not model:
        return ""
    spec = _condenser_spec(model)
    candidates = []
    step_file = str(spec.get("StepFile", "")).strip()
    if step_file:
        candidates.append(os.path.splitext(step_file)[0].lower())
    model_base = os.path.splitext(model)[0].strip().lower()
    if model_base:
        candidates.append(model_base)
        candidates.append(model_base.replace(" ", "_"))
        candidates.append(model_base.replace("-", "_"))

    index = _step_file_index()
    for key in candidates:
        path = index.get(key, "")
        if path and os.path.isfile(path):
            return path
    return ""


def _scale_symbol_shape_xy(shape, target_size_mm, allow_downscale=False):
    if shape is None or shape.isNull():
        return shape
    try:
        bbox = shape.BoundBox
        current_span = max(float(bbox.XLength), float(bbox.YLength))
    except Exception:
        return shape
    if current_span <= 0.1:
        return shape

    target_span = max(100.0, float(target_size_mm))
    factor = target_span / current_span
    if not bool(allow_downscale) and factor < 1.0:
        try:
            return shape.copy()
        except Exception:
            return shape

    if abs(factor - 1.0) <= 0.02:
        try:
            return shape.copy()
        except Exception:
            return shape

    try:
        matrix = App.Matrix()
        matrix.scale(float(factor), float(factor), 1.0)
        scaled = shape.copy()
        scaled.transformShape(matrix, True)
        return scaled
    except Exception:
        return shape


def _step_cache_key(step_path):
    try:
        st = os.stat(step_path)
        return (os.path.abspath(step_path), int(st.st_mtime_ns), int(st.st_size))
    except Exception:
        return (os.path.abspath(step_path), 0, 0)


def _normalize_shape_to_origin(shape):
    if shape is None:
        return None
    try:
        result = shape.copy()
        bbox = result.BoundBox
        result.translate(App.Vector(-float(bbox.Center.x), -float(bbox.Center.y), -float(bbox.ZMin)))
        return result
    except Exception:
        return None


def _get_cached_step_shape(step_path):
    key = _step_cache_key(step_path)
    cached = _STEP_SHAPE_CACHE.get(key)
    if cached is None:
        return None
    try:
        return cached.copy()
    except Exception:
        return None


def _put_cached_step_shape(step_path, shape):
    if shape is None:
        return
    key = _step_cache_key(step_path)
    path_abs = key[0]
    stale_keys = [k for k in list(_STEP_SHAPE_CACHE.keys()) if isinstance(k, tuple) and len(k) >= 1 and k[0] == path_abs and k != key]
    for stale in stale_keys:
        _STEP_SHAPE_CACHE.pop(stale, None)
    try:
        _STEP_SHAPE_CACHE[key] = shape.copy()
    except Exception:
        pass


def _load_step_shape(step_path):
    if not step_path or not os.path.isfile(step_path):
        return None
    cached = _get_cached_step_shape(step_path)
    if cached is not None:
        return cached
    try:
        if hasattr(Part, "read"):
            direct_shape = Part.read(step_path)
            if direct_shape is not None and not direct_shape.isNull():
                normalized = _normalize_shape_to_origin(direct_shape)
                if normalized is not None and not normalized.isNull():
                    _put_cached_step_shape(step_path, normalized)
                    return normalized
    except Exception:
        pass
    return None


def _model_source_tag(model_name):
    if _resolve_step_file_for_model(model_name):
        return "STEP"
    return "PRIMITIVE"


def _primitive_condenser_shape(model_name):
    spec = _condenser_spec(model_name)
    sx, sy, sz = tuple(spec.get("Size", (1200.0, 500.0, 900.0)))
    discharge = _normalize_discharge(spec.get("Discharge", "Horizontal"))

    body = Part.makeBox(float(sx), float(sy), float(sz))
    body.translate(App.Vector(-float(sx) * 0.5, -float(sy) * 0.5, 0.0))
    components = [body]

    # Optional visual cue to differentiate top discharge units.
    if discharge == "Vertical":
        radius = max(100.0, min(float(sx), float(sy)) * 0.28)
        fan_h = max(10.0, float(sz) * 0.05)
        fan = Part.makeCylinder(radius, fan_h, App.Vector(0.0, 0.0, float(sz) - fan_h), App.Vector(0, 0, 1))
        components.append(fan)

    if len(components) == 1:
        return components[0]
    return Part.Compound(components)


def _build_symbol_shape(size_mm, condenser_obj=None):
    model_name = str(getattr(condenser_obj, "Model", "") or "")
    symbol_step = _resolve_symbol2d_step_for_model(model_name)
    if symbol_step:
        loaded = _load_step_shape(symbol_step)
        if loaded is not None:
            # For explicit STEP 2D symbols, preserve native size by default.
            # Only upscale to the minimum target symbol size when needed.
            return _scale_symbol_shape_xy(loaded, size_mm, allow_downscale=False)

    width = max(240.0, float(size_mm) * 1.25)
    depth = max(140.0, float(size_mm) * 0.72)
    x0 = -width * 0.5
    x1 = width * 0.5
    y0 = -depth * 0.5
    y1 = depth * 0.5
    p1 = App.Vector(x0, y0, 0.0)
    p2 = App.Vector(x1, y0, 0.0)
    p3 = App.Vector(x1, y1, 0.0)
    p4 = App.Vector(x0, y1, 0.0)
    border = [
        Part.makeLine(p1, p2),
        Part.makeLine(p2, p3),
        Part.makeLine(p3, p4),
        Part.makeLine(p4, p1),
    ]
    cross = [
        Part.makeLine(p1, p3),
        Part.makeLine(p2, p4),
    ]
    fan = Part.makeCircle(min(width, depth) * 0.22, App.Vector(0.0, 0.0, 0.0), App.Vector(0, 0, 1))
    return Part.Compound(border + cross + [fan])


def _bbox_size_nearly_equal(shape_a, shape_b, tol=0.1):
    try:
        if shape_a is None or shape_b is None or shape_a.isNull() or shape_b.isNull():
            return False
        a = shape_a.BoundBox
        b = shape_b.BoundBox
        return (
            abs(float(a.XLength) - float(b.XLength)) <= tol
            and abs(float(a.YLength) - float(b.YLength)) <= tol
            and abs(float(a.ZLength) - float(b.ZLength)) <= tol
        )
    except Exception:
        return False


def _clone_placement(value):
    if value is None:
        return None
    try:
        clone = App.Placement()
        clone.Base = App.Vector(float(value.Base.x), float(value.Base.y), float(value.Base.z))
        clone.Rotation = App.Rotation(value.Rotation)
        return clone
    except Exception:
        return None


def _placement_is_identity(value, tol=1e-9):
    if value is None:
        return True
    try:
        base = getattr(value, "Base", App.Vector())
        rot = getattr(value, "Rotation", App.Rotation())
        return (
            abs(float(base.x)) <= tol
            and abs(float(base.y)) <= tol
            and abs(float(base.z)) <= tol
            and abs(float(rot.Angle)) <= tol
        )
    except Exception:
        return False


def _set_condenser_placement(condenser_obj, base_vec=None, rotation=None):
    if condenser_obj is None:
        return
    current = getattr(condenser_obj, "Placement", App.Placement())
    target = App.Vector(base_vec if base_vec is not None else current.Base)
    target_rot = rotation if rotation is not None else current.Rotation

    placement = getattr(condenser_obj, "Placement", App.Placement())
    placement.Base = target
    if rotation is not None:
        placement.Rotation = target_rot
    condenser_obj.Placement = placement

    if _is_link_condenser(condenser_obj):
        try:
            condenser_obj.LinkPlacement = App.Placement()
        except Exception:
            pass


def _global_placement_of(condenser_obj):
    helper = getattr(hvac_equipment, "_global_placement_of", None)
    if callable(helper):
        try:
            return helper(condenser_obj)
        except Exception:
            pass
    if condenser_obj is None:
        return App.Placement()
    try:
        if hasattr(condenser_obj, "getGlobalPlacement"):
            placement = condenser_obj.getGlobalPlacement()
            if placement is not None:
                return App.Placement(placement)
    except Exception:
        pass
    try:
        return App.Placement(getattr(condenser_obj, "Placement", App.Placement()))
    except Exception:
        return App.Placement()


def _build_condenser_shape_signature(condenser_obj):
    if condenser_obj is None:
        return "none"
    model = str(getattr(condenser_obj, "Model", DEFAULT_CONDENSER_MODEL) or DEFAULT_CONDENSER_MODEL)
    discharge = _normalize_discharge(getattr(condenser_obj, "Discharge", "Horizontal"))
    capacity = int(round(_to_float(getattr(condenser_obj, "CapacityBTU", 0.0), 0)))
    step_path = _resolve_step_file_for_model(model)
    if step_path:
        key = _step_cache_key(step_path)
        src = "{0}:{1}:{2}".format(os.path.basename(str(key[0])), int(key[1]), int(key[2]))
    else:
        src = "builtin"
    return "model={0};dis={1};cap={2};src={3}".format(model, discharge, capacity, src)


def _build_condenser_shape_for_model(model_name):
    model = str(model_name or DEFAULT_CONDENSER_MODEL)
    if model not in CONDENSER_LIBRARY:
        model = DEFAULT_CONDENSER_MODEL
    step_path = _resolve_step_file_for_model(model)
    if step_path:
        cached_shape = _get_cached_step_shape(step_path)
        if cached_shape is not None:
            return cached_shape
        step_shape = _load_step_shape(step_path)
        if step_shape is not None:
            log("Geometria condensadora cargada desde STEP para modelo {0}: {1}".format(model, os.path.basename(step_path)))
            return step_shape
    return _primitive_condenser_shape(model)


def _build_condenser_shape(condenser_obj=None):
    model = DEFAULT_CONDENSER_MODEL
    if condenser_obj is not None:
        model = str(getattr(condenser_obj, "Model", DEFAULT_CONDENSER_MODEL) or DEFAULT_CONDENSER_MODEL)
    if model not in CONDENSER_LIBRARY:
        model = _guess_model_from_capacity(
            _to_float(getattr(condenser_obj, "CapacityBTU", 0.0), 0.0) if condenser_obj is not None else 12000.0,
            getattr(condenser_obj, "Discharge", "Horizontal") if condenser_obj is not None else "Horizontal",
        )
    return _build_condenser_shape_for_model(model)


def _master_shape_signature(model_name):
    model = str(model_name or DEFAULT_CONDENSER_MODEL)
    if model not in CONDENSER_LIBRARY:
        model = DEFAULT_CONDENSER_MODEL
    discharge = _normalize_discharge(_condenser_spec(model).get("Discharge", "Horizontal"))
    step_path = _resolve_step_file_for_model(model)
    if step_path:
        src = str(os.path.basename(step_path) or "").strip()
        if bool(STEP_MASTER_AUTO_RELOAD):
            key = _step_cache_key(step_path)
            src = "{0}:{1}:{2}".format(os.path.basename(str(key[0])), int(key[1]), int(key[2]))
    else:
        src = "builtin"
    return "schema={0};model={1};dis={2};src={3}".format(MASTER_SHAPE_SCHEMA_REV, model, discharge, src)


def _ensure_master_condenser(doc, model_name):
    if doc is None:
        return None
    model = str(model_name or DEFAULT_CONDENSER_MODEL)
    if model not in CONDENSER_LIBRARY:
        model = DEFAULT_CONDENSER_MODEL
    internal_name = _master_internal_name(model)
    master = doc.getObject(internal_name)
    if master is None:
        master = doc.addObject("Part::Feature", internal_name)
        master.Label = "MASTER_COND_{0}".format(model)

    if hasattr(master, "PropertiesList"):
        if "MEPType" not in master.PropertiesList:
            master.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
        if str(getattr(master, "MEPType", "")) != MASTER_MEP_TYPE:
            master.MEPType = MASTER_MEP_TYPE
        if "Model" not in master.PropertiesList:
            master.addProperty("App::PropertyString", "Model", "HVAC Condenser", "Condenser model")
        if str(getattr(master, "Model", "")) != model:
            master.Model = model
        if "Discharge" not in master.PropertiesList:
            master.addProperty("App::PropertyString", "Discharge", "HVAC Condenser", "Condenser discharge type")
        expected_discharge = _normalize_discharge(_condenser_spec(model).get("Discharge", "Horizontal"))
        if str(getattr(master, "Discharge", "")) != expected_discharge:
            master.Discharge = expected_discharge
        if "ShapeSignature" not in master.PropertiesList:
            master.addProperty("App::PropertyString", "ShapeSignature", "HVAC Condenser", "Internal shape signature")

    expected_signature = _master_shape_signature(model)
    current_signature = str(getattr(master, "ShapeSignature", "") or "")
    signature_changed = current_signature != expected_signature
    current_shape = None
    shape_missing = True
    try:
        current_shape = getattr(master, "Shape", None)
        shape_missing = current_shape is None or current_shape.isNull()
    except Exception:
        current_shape = None
        shape_missing = True
    needs_rebuild = bool(signature_changed or shape_missing)

    if needs_rebuild:
        expected_shape = _build_condenser_shape_for_model(model)
    else:
        expected_shape = None

    try:
        if needs_rebuild and expected_shape is not None:
            master.Shape = expected_shape
    except Exception:
        pass
    try:
        if "ShapeSignature" in getattr(master, "PropertiesList", []):
            master.ShapeSignature = expected_signature
    except Exception:
        pass

    if hasattr(master, "ViewObject"):
        try:
            master.ViewObject.Visibility = False
        except Exception:
            pass
        try:
            if hasattr(master.ViewObject, "ShowInTree"):
                master.ViewObject.ShowInTree = False
        except Exception:
            pass
    hvac_project.add_object_to_hvac_group(doc, master)
    return master


def _is_symbol2d_obj(obj):
    if obj is None:
        return False
    try:
        props = list(getattr(obj, "PropertiesList", []) or [])
        if "MEPType" in props and str(getattr(obj, "MEPType", "") or "") == SYMBOL2D_MEP_TYPE:
            return True
    except Exception:
        pass
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    return name.startswith("HVAC_Cond2D") or label.startswith("HVAC_2D_COND_")


def _ensure_symbol2d_properties(symbol_obj, condenser_obj=None):
    if symbol_obj is None:
        return
    try:
        if "MEPType" not in symbol_obj.PropertiesList:
            symbol_obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
        if str(getattr(symbol_obj, "MEPType", "") or "") != SYMBOL2D_MEP_TYPE:
            symbol_obj.MEPType = SYMBOL2D_MEP_TYPE
        # Avoid document dependency cycles (DAG) by ensuring there is no back link
        # from the 2D symbol to the parent 3D condenser.
        if "ParentCondenser" in symbol_obj.PropertiesList:
            try:
                if getattr(symbol_obj, "ParentCondenser", None) is not None:
                    symbol_obj.ParentCondenser = None
            except Exception:
                pass
        if "VisualMode" not in symbol_obj.PropertiesList:
            symbol_obj.addProperty("App::PropertyEnumeration", "VisualMode", "HVAC Condenser", "View mode controller")
        try:
            symbol_obj.VisualMode = list(VISUAL_MODE_OPTIONS)
        except Exception:
            pass
        if condenser_obj is not None:
            target_mode = _normalized_visual_mode(getattr(condenser_obj, "VisualMode", DEFAULT_VISUAL_MODE))
            try:
                symbol_obj.VisualMode = target_mode
            except Exception:
                pass
        if "CondenserName" not in symbol_obj.PropertiesList:
            symbol_obj.addProperty("App::PropertyString", "CondenserName", "HVAC Condenser", "Parent condenser name")
        if condenser_obj is not None:
            symbol_obj.CondenserName = str(getattr(condenser_obj, "Label", "") or getattr(condenser_obj, "Name", "") or "")
    except Exception:
        pass


def _ensure_symbol2d_object(condenser_obj):
    if condenser_obj is None:
        return None
    doc = getattr(condenser_obj, "Document", None)
    if doc is None:
        return None
    if "Symbol2D" not in getattr(condenser_obj, "PropertiesList", []):
        return None

    symbol_obj = getattr(condenser_obj, "Symbol2D", None)
    if symbol_obj is not None:
        try:
            if doc.getObject(str(getattr(symbol_obj, "Name", "") or "")) is None:
                symbol_obj = None
        except Exception:
            symbol_obj = None

    if symbol_obj is not None and not _is_symbol2d_obj(symbol_obj):
        symbol_obj = None
        try:
            condenser_obj.Symbol2D = None
        except Exception:
            pass

    if symbol_obj is None:
        try:
            symbol_obj = doc.addObject("Part::Feature", "HVAC_Cond2D")
        except Exception:
            return None
        try:
            condenser_obj.Symbol2D = symbol_obj
        except Exception:
            pass

    _ensure_symbol2d_properties(symbol_obj, condenser_obj=condenser_obj)
    try:
        base_label = str(getattr(condenser_obj, "Label", "") or getattr(condenser_obj, "Name", "") or "COND")
        symbol_obj.Label = "HVAC_2D_COND_{0}".format(base_label)
    except Exception:
        pass
    try:
        if hasattr(symbol_obj, "ViewObject") and symbol_obj.ViewObject is not None:
            if hasattr(symbol_obj.ViewObject, "Selectable"):
                symbol_obj.ViewObject.Selectable = True
            if hasattr(symbol_obj.ViewObject, "ShowInTree"):
                symbol_obj.ViewObject.ShowInTree = True
    except Exception:
        pass
    try:
        hvac_project.add_object_to_hvac_group(doc, symbol_obj)
    except Exception:
        pass
    return symbol_obj


def _cleanup_orphan_symbol2d_objects(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    linked_names = set()
    for condenser_obj in list(find_condensers(doc) or []):
        if condenser_obj is None:
            continue
        try:
            if "Symbol2D" not in getattr(condenser_obj, "PropertiesList", []):
                continue
            symbol_obj = getattr(condenser_obj, "Symbol2D", None)
            symbol_name = str(getattr(symbol_obj, "Name", "") or "")
            if symbol_name and doc.getObject(symbol_name) is not None:
                linked_names.add(symbol_name)
        except Exception:
            continue

    removed = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if obj is None or not _is_symbol2d_obj(obj):
            continue
        obj_name = str(getattr(obj, "Name", "") or "")
        if not obj_name or obj_name in linked_names:
            continue
        try:
            if doc.getObject(obj_name) is not None:
                doc.removeObject(obj_name)
                removed += 1
        except Exception:
            continue

    if removed > 0:
        log("Limpieza simbolos 2D condensadora: huerfanos_eliminados={0}".format(removed))
    return removed


def _symbol2d_placement_for_condenser(condenser_obj):
    placement = _global_placement_of(condenser_obj)
    try:
        base = App.Vector(float(placement.Base.x), float(placement.Base.y), 0.0)
        rot = App.Rotation(placement.Rotation)
        return App.Placement(base, rot)
    except Exception:
        return App.Placement()


def _sync_symbol2d_for_condenser(condenser_obj):
    symbol_obj = _ensure_symbol2d_object(condenser_obj)
    if symbol_obj is None:
        return
    try:
        symbol_obj.Shape = _build_symbol_shape(_symbol_size_mm(condenser_obj), condenser_obj=condenser_obj)
    except Exception:
        return
    try:
        symbol_obj.Placement = _symbol2d_placement_for_condenser(condenser_obj)
    except Exception:
        pass


def _condenser_system_label(condenser_obj):
    model = _labelize_token(getattr(condenser_obj, "Model", ""))
    model_token = model.replace(" ", "")
    if "VRF" in model_token:
        return "VRF"
    if "MULTISPLIT" in model_token:
        return "MULTI SPLIT"
    if "MINISPLIT" in model_token:
        return "MINI SPLIT"
    try:
        linked_units = list(getattr(condenser_obj, "ConnectedUnits", []) or [])
    except Exception:
        linked_units = []
    return "MULTI SPLIT" if len(linked_units) >= 2 else "MINI SPLIT"


def _condenser_type_label(condenser_obj):
    discharge = _normalize_discharge(getattr(condenser_obj, "Discharge", "Horizontal"))
    return "HORIZONTAL" if discharge == "Horizontal" else "VERTICAL"


def _build_info2d_lines(condenser_obj):
    if condenser_obj is None:
        return ["CONDENSADORA", "SISTEMA MINI SPLIT", "0 BTU/H"]
    type_label = _condenser_type_label(condenser_obj)
    system_label = _condenser_system_label(condenser_obj)
    capacity = _format_btu_label(getattr(condenser_obj, "CapacityBTU", 0.0))
    return [
        "CONDENSADORA TIPO {0}".format(type_label),
        "SISTEMA {0}".format(system_label),
        "{0} BTU/H".format(capacity),
    ]


def _is_info2d_obj(obj):
    if obj is None:
        return False
    try:
        props = list(getattr(obj, "PropertiesList", []) or [])
        if "MEPType" in props and str(getattr(obj, "MEPType", "") or "") == INFO2D_MEP_TYPE:
            return True
    except Exception:
        pass
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    return name.startswith("HVAC_CondInfo2D") or label.startswith("HVAC_INFO2D_COND_")


def _ensure_info2d_properties(info_obj, condenser_obj=None):
    if info_obj is None:
        return
    try:
        props = list(getattr(info_obj, "PropertiesList", []) or [])
        if "MEPType" not in props:
            info_obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
        if str(getattr(info_obj, "MEPType", "") or "") != INFO2D_MEP_TYPE:
            info_obj.MEPType = INFO2D_MEP_TYPE
        if "CondenserName" not in props:
            info_obj.addProperty("App::PropertyString", "CondenserName", "HVAC Condenser", "Parent condenser name")
        if condenser_obj is not None:
            info_obj.CondenserName = str(
                getattr(condenser_obj, "Label", "")
                or getattr(condenser_obj, "Name", "")
                or ""
            )
    except Exception:
        pass


def _info2d_offset_local(condenser_obj):
    symbol_size = max(120.0, _symbol_size_mm(condenser_obj))
    text_size = _normalized_info2d_size(getattr(condenser_obj, "Info2DSize", DEFAULT_INFO2D_SIZE))
    clearance = max(180.0, symbol_size * 0.9, text_size * 1.6)
    return App.Vector(0.0, clearance, 0.0)


def _info2d_point_for_condenser(condenser_obj, symbol_obj=None):
    if condenser_obj is None:
        return App.Vector(0.0, 0.0, 0.0)

    get_global_placement = getattr(hvac_equipment, "_global_placement_of", None)
    get_bbox_local = getattr(hvac_equipment, "_shape_boundbox_local", None)
    estimate_text_block = getattr(hvac_equipment, "_estimate_text_block_mm", None)

    anchor_obj = symbol_obj if symbol_obj is not None else condenser_obj
    if callable(get_global_placement):
        placement = get_global_placement(anchor_obj)
    else:
        placement = getattr(anchor_obj, "Placement", App.Placement())
    if (
        symbol_obj is not None
        and abs(float(getattr(placement.Base, "x", 0.0))) < 0.001
        and abs(float(getattr(placement.Base, "y", 0.0))) < 0.001
        and abs(float(getattr(placement.Base, "z", 0.0))) < 0.001
    ):
        if callable(get_global_placement):
            placement = get_global_placement(condenser_obj)
        else:
            placement = getattr(condenser_obj, "Placement", App.Placement())

    try:
        base = App.Vector(placement.Base)
    except Exception:
        base = App.Vector(0.0, 0.0, 0.0)
    try:
        rot = App.Rotation(placement.Rotation)
    except Exception:
        rot = App.Rotation()

    local_anchor = _info2d_offset_local(condenser_obj)
    bbox = get_bbox_local(symbol_obj) if callable(get_bbox_local) and symbol_obj is not None else None
    if bbox is None and callable(get_bbox_local):
        bbox = get_bbox_local(condenser_obj)

    lines = _build_info2d_lines(condenser_obj)
    text_size = _normalized_info2d_size(getattr(condenser_obj, "Info2DSize", DEFAULT_INFO2D_SIZE))
    if callable(estimate_text_block):
        text_w, text_h = estimate_text_block(lines, text_size)
    else:
        text_w = max(120.0, max(len(v) for v in lines) * text_size * 0.56)
        text_h = max(text_size, len(lines) * text_size * 1.25)

    if bbox is not None:
        try:
            bbox_y = max(0.0, float(getattr(bbox, "YLength", 0.0)))
            front_extent = max(
                0.5 * bbox_y,
                max(100.0, _symbol_size_mm(condenser_obj) * 0.25),
            )
            margin = max(90.0, text_size * 0.8)
            text_push = max(text_h * 1.05, text_size * 2.4)
            local_anchor = App.Vector(
                0.0,
                front_extent + margin + text_push,
                float(getattr(local_anchor, "z", 0.0)),
            )
        except Exception:
            pass
    else:
        text_push = max(text_h * 1.05, text_size * 2.4)
        local_anchor = App.Vector(
            float(local_anchor.x),
            float(local_anchor.y) + max(90.0, text_push),
            float(local_anchor.z),
        )

    return base + rot.multVec(local_anchor)


def _ensure_info2d_object(condenser_obj, symbol_obj=None):
    if condenser_obj is None:
        return None
    doc = getattr(condenser_obj, "Document", None)
    if doc is None:
        return None
    if "Info2D" not in getattr(condenser_obj, "PropertiesList", []):
        return None

    info_obj = getattr(condenser_obj, "Info2D", None)
    if info_obj is not None:
        try:
            info_name = str(getattr(info_obj, "Name", "") or "")
            if not info_name or doc.getObject(info_name) is None:
                info_obj = None
        except Exception:
            info_obj = None

    if info_obj is not None and not _is_info2d_obj(info_obj):
        info_obj = None
        try:
            condenser_obj.Info2D = None
        except Exception:
            pass

    is_draft_text = getattr(hvac_equipment, "_is_draft_text_obj", None)
    if info_obj is not None and callable(is_draft_text) and not is_draft_text(info_obj):
        old_name = str(getattr(info_obj, "Name", "") or "")
        old_type = str(getattr(info_obj, "TypeId", "") or "")
        log("Migrando Info2D condensadora a Draft: {0} ({1})".format(old_name or "?", old_type or "?"))
        info_obj = None
        try:
            condenser_obj.Info2D = None
        except Exception:
            pass
        try:
            if old_name and doc.getObject(old_name) is not None:
                doc.removeObject(old_name)
        except Exception:
            pass

    if info_obj is None:
        lines = _build_info2d_lines(condenser_obj)
        point = _info2d_point_for_condenser(condenser_obj, symbol_obj=symbol_obj)
        make_text = getattr(hvac_equipment, "_make_info2d_text", None)
        if not callable(make_text):
            log("Texto 2D condensadora omitido: helper Draft no disponible")
            return None
        try:
            info_obj = make_text(doc, lines, point)
        except Exception as exc:
            log("Texto 2D condensadora omitido: {0}".format(exc))
            return None
        try:
            condenser_obj.Info2D = info_obj
        except Exception:
            pass

    _ensure_info2d_properties(info_obj, condenser_obj=condenser_obj)
    try:
        base_label = str(getattr(condenser_obj, "Label", "") or getattr(condenser_obj, "Name", "") or "COND")
        info_obj.Label = "HVAC_INFO2D_COND_{0}".format(base_label)
    except Exception:
        pass
    assigned_group = None
    try:
        assigned_group = hvac_project.add_object_to_hvac_group(doc, info_obj)
    except Exception as exc:
        if INFO2D_DEBUG_ENABLED:
            log(
                "Info2D route error condensadora: unidad={0} info={1} error={2}".format(
                    _safe_obj_name(condenser_obj) or "?",
                    _safe_obj_name(info_obj) or "?",
                    str(exc),
                )
            )
    if INFO2D_DEBUG_ENABLED:
        group_name = str(getattr(assigned_group, "Name", "") or "") if assigned_group is not None else ""
        if not group_name:
            memberships = _group_memberships(info_obj)
            group_name = memberships[0] if memberships else "-"
        log(
            "Info2D route condensadora: unidad={0} info={1} grupo={2}".format(
                _safe_obj_name(condenser_obj) or "?",
                _safe_obj_name(info_obj) or "?",
                group_name or "-",
            )
        )
    return info_obj


def _sync_info2d_for_condenser(condenser_obj, symbol_obj=None):
    if condenser_obj is None:
        return
    info_obj = _ensure_info2d_object(condenser_obj, symbol_obj=symbol_obj)
    if info_obj is None:
        return

    set_text_lines = getattr(hvac_equipment, "_set_text_lines", None)
    set_text_size = getattr(hvac_equipment, "_set_text_size", None)
    set_text_centered = getattr(hvac_equipment, "_set_text_centered", None)
    set_text_point = getattr(hvac_equipment, "_set_text_point", None)
    set_text_visibility = getattr(hvac_equipment, "_set_text_visibility", None)

    lines = _build_info2d_lines(condenser_obj)
    raw_size = _to_float(getattr(condenser_obj, "Info2DSize", DEFAULT_INFO2D_SIZE), DEFAULT_INFO2D_SIZE)
    effective_size = _normalized_info2d_size(raw_size)
    if raw_size < MIN_INFO2D_SIZE:
        effective_size = DEFAULT_INFO2D_SIZE
        try:
            condenser_obj.Info2DSize = effective_size
        except Exception:
            pass

    if callable(set_text_lines):
        set_text_lines(info_obj, lines)
    if callable(set_text_size):
        set_text_size(info_obj, effective_size)
    if callable(set_text_centered):
        set_text_centered(info_obj)
    info_point = _info2d_point_for_condenser(condenser_obj, symbol_obj=symbol_obj)
    if callable(set_text_point):
        set_text_point(info_obj, info_point)

    mode = _normalized_visual_mode(getattr(condenser_obj, "VisualMode", DEFAULT_VISUAL_MODE))
    show_3d = mode in {"Ambos", "Solo3D"}
    show_2d = mode in {"Ambos", "Solo2D"}
    if mode == "Ninguno":
        show_3d = False
        show_2d = False
    show_info2d = bool(show_2d) and bool(getattr(condenser_obj, "ShowInfo2D", True))
    if callable(set_text_visibility):
        set_text_visibility(info_obj, show_info2d)
    if INFO2D_DEBUG_ENABLED:
        groups = ",".join(_group_memberships(info_obj) or [])
        if not groups:
            groups = "-"
        log(
            "Info2D sync condensadora: cond={0} ({1}) mode={2} show3d={3} show2d={4} showInfo2D={5} -> text={6} vis(owner/sym/text)={7}/{8}/{9} point=({10:.1f},{11:.1f},{12:.1f}) groups={13}".format(
                _safe_obj_name(condenser_obj) or "?",
                _safe_obj_label(condenser_obj) or "?",
                mode,
                int(bool(show_3d)),
                int(bool(show_2d)),
                int(bool(getattr(condenser_obj, "ShowInfo2D", True))),
                int(bool(show_info2d)),
                _view_visibility(condenser_obj),
                _view_visibility(symbol_obj),
                _view_visibility(info_obj),
                float(getattr(info_point, "x", 0.0)),
                float(getattr(info_point, "y", 0.0)),
                float(getattr(info_point, "z", 0.0)),
                groups,
            )
        )


def _cleanup_orphan_info2d_objects(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    linked_names = set()
    for condenser_obj in list(find_condensers(doc) or []):
        if condenser_obj is None:
            continue
        try:
            if "Info2D" not in getattr(condenser_obj, "PropertiesList", []):
                continue
            info_obj = getattr(condenser_obj, "Info2D", None)
            info_name = str(getattr(info_obj, "Name", "") or "")
            if info_name and doc.getObject(info_name) is not None:
                linked_names.add(info_name)
        except Exception:
            continue

    is_probable_info2d = getattr(hvac_equipment, "_is_probable_info2d_draft_text", None)
    removed = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if obj is None:
            continue
        if _is_info2d_obj(obj):
            pass
        elif callable(is_probable_info2d) and is_probable_info2d(obj):
            pass
        else:
            continue
        obj_name = str(getattr(obj, "Name", "") or "")
        if not obj_name or obj_name in linked_names:
            continue
        try:
            if doc.getObject(obj_name) is not None:
                doc.removeObject(obj_name)
                removed += 1
        except Exception:
            continue

    if removed > 0:
        log("Limpieza texto 2D condensadora: huerfanos_eliminados={0}".format(removed))
    return removed


def _sync_visual_mode_visibility(condenser_obj):
    if condenser_obj is None:
        return
    mode = _normalized_visual_mode(getattr(condenser_obj, "VisualMode", DEFAULT_VISUAL_MODE))
    show_3d = mode in {"Ambos", "Solo3D"}
    show_2d = mode in {"Ambos", "Solo2D"}
    if mode == "Ninguno":
        show_3d = False
        show_2d = False

    try:
        if hasattr(condenser_obj, "ViewObject") and condenser_obj.ViewObject is not None:
            condenser_obj.ViewObject.Visibility = bool(show_3d)
    except Exception:
        pass

    symbol_obj = getattr(condenser_obj, "Symbol2D", None) if "Symbol2D" in getattr(condenser_obj, "PropertiesList", []) else None
    if symbol_obj is not None:
        try:
            if hasattr(symbol_obj, "ViewObject") and symbol_obj.ViewObject is not None:
                symbol_obj.ViewObject.Visibility = bool(show_2d)
        except Exception:
            pass
    info_obj = getattr(condenser_obj, "Info2D", None) if "Info2D" in getattr(condenser_obj, "PropertiesList", []) else None
    if info_obj is not None:
        try:
            if hasattr(info_obj, "ViewObject") and info_obj.ViewObject is not None:
                info_obj.ViewObject.Visibility = bool(show_2d) and bool(getattr(condenser_obj, "ShowInfo2D", True))
        except Exception:
            pass


def _apply_condenser_shape(condenser_obj, force=False):
    if condenser_obj is None:
        return
    ensure_condenser_properties(condenser_obj)

    if _is_link_condenser(condenser_obj):
        placement_before = _clone_placement(getattr(condenser_obj, "Placement", None))
        link_placement_before = _clone_placement(getattr(condenser_obj, "LinkPlacement", None))
        master = _ensure_master_condenser(
            getattr(condenser_obj, "Document", None),
            getattr(condenser_obj, "Model", DEFAULT_CONDENSER_MODEL),
        )
        if master is not None and getattr(condenser_obj, "LinkedObject", None) != master:
            condenser_obj.LinkedObject = master
        _configure_link_for_transform(condenser_obj)
        has_placement = placement_before is not None and not _placement_is_identity(placement_before)
        has_link_placement = link_placement_before is not None and not _placement_is_identity(link_placement_before)
        # Keep the runtime transform in Placement, matching evaporadoras and the
        # route/symbol code. Older condensadoras may still carry LinkPlacement;
        # migrate that value once so new refreshes do not double-offset links.
        if has_link_placement and not has_placement:
            try:
                condenser_obj.Placement = link_placement_before
            except Exception:
                pass
        elif placement_before is not None:
            try:
                condenser_obj.Placement = placement_before
            except Exception:
                pass
        try:
            condenser_obj.LinkPlacement = App.Placement()
        except Exception:
            pass
        if "ShapeSignature" in getattr(condenser_obj, "PropertiesList", []):
            try:
                condenser_obj.ShapeSignature = _master_shape_signature(getattr(condenser_obj, "Model", DEFAULT_CONDENSER_MODEL))
            except Exception:
                pass
        _sync_symbol2d_for_condenser(condenser_obj)
        _sync_info2d_for_condenser(condenser_obj, symbol_obj=getattr(condenser_obj, "Symbol2D", None))
        _sync_visual_mode_visibility(condenser_obj)
        return

    signature = _build_condenser_shape_signature(condenser_obj)
    current_signature = str(getattr(condenser_obj, "ShapeSignature", "") or "")
    shape_current = getattr(condenser_obj, "Shape", None)

    # Legacy safety: if object already has a valid shape but no signature, avoid relocating it.
    if not bool(force) and current_signature == "":
        try:
            if shape_current is not None and not shape_current.isNull():
                if "ShapeSignature" in condenser_obj.PropertiesList:
                    condenser_obj.ShapeSignature = signature
                _sync_symbol2d_for_condenser(condenser_obj)
                _sync_info2d_for_condenser(condenser_obj, symbol_obj=getattr(condenser_obj, "Symbol2D", None))
                _sync_visual_mode_visibility(condenser_obj)
                return
        except Exception:
            pass

    needs = bool(force) or signature != current_signature
    if not needs:
        try:
            needs = shape_current is None or shape_current.isNull()
        except Exception:
            needs = True
    if not needs:
        _sync_symbol2d_for_condenser(condenser_obj)
        _sync_info2d_for_condenser(condenser_obj, symbol_obj=getattr(condenser_obj, "Symbol2D", None))
        _sync_visual_mode_visibility(condenser_obj)
        return

    placement_before = _clone_placement(getattr(condenser_obj, "Placement", None))
    condenser_obj.Shape = _build_condenser_shape(condenser_obj)
    if placement_before is not None:
        try:
            condenser_obj.Placement = placement_before
        except Exception:
            pass

    if "ShapeSignature" in condenser_obj.PropertiesList:
        condenser_obj.ShapeSignature = signature
    _sync_symbol2d_for_condenser(condenser_obj)
    _sync_info2d_for_condenser(condenser_obj, symbol_obj=getattr(condenser_obj, "Symbol2D", None))
    _sync_visual_mode_visibility(condenser_obj)


def ensure_condenser_properties(obj):
    added_capacity = False
    added_load = False
    added_coverage = False
    added_auto = False
    added_model = False
    added_discharge = False
    added_signature = False
    added_symbol_size = False
    added_visual_mode = False
    added_show_info2d = False
    added_info2d_size = False

    if "MEPType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
    if str(getattr(obj, "MEPType", "")) != MEP_TYPE:
        try:
            obj.MEPType = MEP_TYPE
        except Exception:
            if "MEPType" not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
            obj.MEPType = MEP_TYPE

    if "Model" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "Model", "HVAC Condenser", "Condenser model")
        added_model = True
    if "Discharge" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "Discharge", "HVAC Condenser", "Condenser discharge type")
        added_discharge = True
    if "CapacityBTU" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "CapacityBTU", "HVAC Condenser", "Condenser capacity")
        added_capacity = True
    if "ConnectedUnits" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyLinkList",
            "ConnectedUnits",
            "HVAC Condenser",
            "Evaporator units connected to this condenser",
        )
    if "ConnectedLoadBTU" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "ConnectedLoadBTU",
            "HVAC Condenser",
            "Sum of connected evaporator capacities",
        )
        added_load = True
    if "CoveragePct" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "CoveragePct",
            "HVAC Condenser",
            "Condenser coverage over connected load",
        )
        added_coverage = True
    if "AutoCollect" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyBool",
            "AutoCollect",
            "HVAC Condenser",
            "Legacy flag (auto collect disabled by default)",
        )
        added_auto = True
    if "ShapeSignature" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "ShapeSignature", "HVAC Condenser", "Internal shape signature")
        added_signature = True
    if "Symbol2DSize" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Symbol2DSize", "HVAC Condenser", "2D symbol size (mm)")
        added_symbol_size = True
    if "VisualMode" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "VisualMode", "HVAC Condenser", "Visual representation mode")
        added_visual_mode = True
    if "Symbol2D" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "Symbol2D", "HVAC Condenser", "Linked 2D symbol object")
    if "ShowInfo2D" not in obj.PropertiesList:
        obj.addProperty("App::PropertyBool", "ShowInfo2D", "HVAC Condenser", "Show 2D plan text near condenser symbol")
        added_show_info2d = True
    if "Info2DSize" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Info2DSize", "HVAC Condenser", "2D plan text size")
        added_info2d_size = True
    if "Info2D" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "Info2D", "HVAC Condenser", "Linked 2D text object")

    if "Model" in obj.PropertiesList:
        current_model = str(getattr(obj, "Model", "") or "")
        capacity_for_guess = _to_float(getattr(obj, "CapacityBTU", 0.0), 0.0)
        discharge_for_guess = str(getattr(obj, "Discharge", "") or "")
        if current_model not in CONDENSER_LIBRARY:
            current_model = _guess_model_from_capacity(capacity_for_guess, discharge_for_guess)
        try:
            obj.Model = list(CONDENSER_LIBRARY.keys())
        except Exception:
            pass
        try:
            obj.Model = current_model
        except Exception:
            pass

    if "Discharge" in obj.PropertiesList:
        current_discharge = _normalize_discharge(getattr(obj, "Discharge", "Horizontal"))
        try:
            obj.Discharge = list(DISCHARGE_OPTIONS)
        except Exception:
            pass
        try:
            obj.Discharge = current_discharge
        except Exception:
            pass

    if added_capacity:
        obj.CapacityBTU = _condenser_spec(DEFAULT_CONDENSER_MODEL).get("CapacityBTU", 12000.0)
    if added_load:
        obj.ConnectedLoadBTU = 0.0
    if added_coverage:
        obj.CoveragePct = 0.0
    if added_auto:
        obj.AutoCollect = False
    if added_signature:
        obj.ShapeSignature = ""
    if "VisualMode" in obj.PropertiesList:
        try:
            obj.VisualMode = VISUAL_MODE_OPTIONS
        except Exception:
            pass
        mode = _normalized_visual_mode(getattr(obj, "VisualMode", DEFAULT_VISUAL_MODE))
        if added_visual_mode:
            mode = DEFAULT_VISUAL_MODE
        try:
            obj.VisualMode = mode
        except Exception:
            pass
    if added_symbol_size:
        obj.Symbol2DSize = DEFAULT_SYMBOL_SIZE
    if added_show_info2d:
        obj.ShowInfo2D = True
    if added_info2d_size:
        obj.Info2DSize = DEFAULT_INFO2D_SIZE


def _initialize_condenser_defaults(obj):
    ensure_condenser_properties(obj)

    model = str(getattr(obj, "Model", "") or "")
    capacity = _to_float(getattr(obj, "CapacityBTU", 0.0), 0.0)
    discharge = _normalize_discharge(getattr(obj, "Discharge", "Horizontal"))

    if model not in CONDENSER_LIBRARY:
        model = _guess_model_from_capacity(capacity, discharge)
        try:
            obj.Model = model
        except Exception:
            pass
    spec = _condenser_spec(model)

    model_discharge = _normalize_discharge(spec.get("Discharge", "Horizontal"))
    if discharge != model_discharge:
        discharge = model_discharge
    try:
        obj.Discharge = discharge
    except Exception:
        pass

    if capacity <= 0.0:
        obj.CapacityBTU = _to_float(spec.get("CapacityBTU", 12000.0), 12000.0)
    if _to_float(obj.ConnectedLoadBTU, 0.0) < 0:
        obj.ConnectedLoadBTU = 0.0
    if _to_float(obj.CoveragePct, 0.0) < 0:
        obj.CoveragePct = 0.0
    if not isinstance(getattr(obj, "AutoCollect", False), bool):
        obj.AutoCollect = False
    if bool(getattr(obj, "AutoCollect", False)):
        obj.AutoCollect = False
    if _to_float(getattr(obj, "Symbol2DSize", 0.0), 0.0) <= 0.0:
        obj.Symbol2DSize = DEFAULT_SYMBOL_SIZE
    if not isinstance(getattr(obj, "ShowInfo2D", True), bool):
        obj.ShowInfo2D = True
    current_info2d_size = _to_float(getattr(obj, "Info2DSize", 0.0), 0.0)
    if current_info2d_size <= 0.0:
        obj.Info2DSize = DEFAULT_INFO2D_SIZE
    else:
        normalized_size = _normalized_info2d_size(current_info2d_size)
        if abs(float(current_info2d_size) - float(normalized_size)) > 0.01:
            obj.Info2DSize = normalized_size
    if "VisualMode" in getattr(obj, "PropertiesList", []):
        try:
            obj.VisualMode = VISUAL_MODE_OPTIONS
        except Exception:
            pass
        try:
            obj.VisualMode = _normalized_visual_mode(getattr(obj, "VisualMode", DEFAULT_VISUAL_MODE))
        except Exception:
            obj.VisualMode = DEFAULT_VISUAL_MODE


def set_condenser_model(condenser_obj, model_name, force=False):
    if condenser_obj is None:
        return
    ensure_condenser_properties(condenser_obj)
    model = str(model_name or "").strip()
    if model not in CONDENSER_LIBRARY:
        model = _guess_model_from_capacity(
            _to_float(getattr(condenser_obj, "CapacityBTU", 0.0), 0.0),
            getattr(condenser_obj, "Discharge", "Horizontal"),
        )
    spec = _condenser_spec(model)
    try:
        condenser_obj.Model = model
    except Exception:
        pass
    try:
        condenser_obj.Discharge = _normalize_discharge(spec.get("Discharge", "Horizontal"))
    except Exception:
        pass
    if force or _to_float(getattr(condenser_obj, "CapacityBTU", 0.0), 0.0) <= 0.0:
        condenser_obj.CapacityBTU = _to_float(spec.get("CapacityBTU", 12000.0), 12000.0)


def _switch_model_by_discharge(condenser_obj, discharge):
    if condenser_obj is None:
        return
    target_discharge = _normalize_discharge(discharge)
    current_capacity = _to_float(getattr(condenser_obj, "CapacityBTU", 0.0), 0.0)
    target_model = _guess_model_from_capacity(current_capacity, target_discharge)
    set_condenser_model(condenser_obj, target_model, force=False)


def find_condensers(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    condensers = []
    for obj in doc.Objects:
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == MEP_TYPE:
            condensers.append(obj)
    return condensers


def _selected_equipments(doc):
    picked = []
    for obj in selection.get_selected_objects(resolve_links=False):
        candidate = obj
        linked = selection.unwrap_link(obj)
        for current in (candidate, linked):
            if current is None:
                continue
            if hasattr(current, "PropertiesList") and "MEPType" in current.PropertiesList:
                if str(getattr(current, "MEPType", "")) == hvac_equipment.MEP_TYPE:
                    picked.append(current)
                    break
    return _deduplicate_units(picked)


def _selected_condensers(doc):
    picked = []
    for obj in selection.get_selected_objects(resolve_links=False):
        candidate = obj
        linked = selection.unwrap_link(obj)
        for current in (candidate, linked):
            if current is None:
                continue
            if hasattr(current, "PropertiesList") and "MEPType" in current.PropertiesList:
                if str(getattr(current, "MEPType", "")) == MEP_TYPE:
                    picked.append(current)
                    break
    if picked:
        return picked

    existing = list(find_condensers(doc))
    if len(existing) == 1:
        log("No se selecciono condensadora. Se usa la unica disponible: {0}".format(existing[0].Name))
        return existing
    return []


def _deduplicate_units(units):
    unique = []
    seen = set()
    for unit in units:
        if unit is None:
            continue
        if not hasattr(unit, "PropertiesList") or "MEPType" not in unit.PropertiesList:
            continue
        if str(getattr(unit, "MEPType", "")) != hvac_equipment.MEP_TYPE:
            continue
        key = str(getattr(unit, "Name", ""))
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(unit)
    return unique


def assign_units_to_condenser(condenser_obj, units, append=True):
    if condenser_obj is None:
        return 0
    ensure_condenser_properties(condenser_obj)
    _initialize_condenser_defaults(condenser_obj)

    selected_units = _deduplicate_units(list(units or []))
    if append:
        current_units = _deduplicate_units(list(getattr(condenser_obj, "ConnectedUnits", []) or []))
        by_name = {str(unit.Name): unit for unit in current_units}
        for unit in selected_units:
            by_name[str(unit.Name)] = unit
        final_units = list(by_name.values())
    else:
        final_units = selected_units

    condenser_obj.ConnectedUnits = final_units
    condenser_obj.AutoCollect = False
    recalculate_condenser(condenser_obj)
    log(
        "Condenser {0}: evaporadoras asignadas={1} (append={2})".format(
            condenser_obj.Name, len(final_units), bool(append)
        )
    )
    return len(final_units)


def assign_selected_units_to_selected_condenser(doc=None, append=True):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return None

    condensers = _selected_condensers(doc)
    if not condensers:
        log("Seleccione una condensadora para asignar evaporadoras")
        return None
    if len(condensers) > 1:
        log("Se detectaron multiples condensadoras. Se usa la primera seleccionada")
    condenser = condensers[0]

    units = _selected_equipments(doc)
    if not units:
        log("Seleccione una o mas evaporadoras para asignar")
        return condenser

    assign_units_to_condenser(condenser, units, append=append)
    return condenser


def recalculate_condenser(condenser_obj):
    if condenser_obj is None:
        return 0.0
    ensure_condenser_properties(condenser_obj)
    _initialize_condenser_defaults(condenser_obj)

    old_connected = _to_float(getattr(condenser_obj, "ConnectedLoadBTU", 0.0), 0.0)
    old_coverage = _to_float(getattr(condenser_obj, "CoveragePct", 0.0), 0.0)

    units = list(getattr(condenser_obj, "ConnectedUnits", []) or [])
    connected_load = 0.0
    for unit in units:
        connected_load += _to_float(getattr(unit, "CapacityBTU", 0.0), 0.0)
    condenser_obj.ConnectedLoadBTU = round(connected_load, 2)

    capacity = _to_float(condenser_obj.CapacityBTU, 0.0)
    if connected_load > 0:
        condenser_obj.CoveragePct = round((capacity / connected_load) * 100.0, 2)
    else:
        condenser_obj.CoveragePct = 0.0

    if abs(old_connected - condenser_obj.ConnectedLoadBTU) > 0.01 or abs(old_coverage - condenser_obj.CoveragePct) > 0.01:
        log(
            "Condenser {0}: capacidad={1}, conectada={2}, cobertura={3}%".format(
                condenser_obj.Name,
                round(capacity, 2),
                round(connected_load, 2),
                round(_to_float(condenser_obj.CoveragePct, 0.0), 2),
            )
        )
    return condenser_obj.CoveragePct


def _condenser_has_valid_shape(condenser_obj):
    if condenser_obj is None:
        return False
    try:
        shape = getattr(condenser_obj, "Shape", None)
        return shape is not None and not shape.isNull()
    except Exception:
        return False


def sanitize_all_condensers(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0
    repaired = 0
    for condenser_obj in list(find_condensers(doc)):
        if condenser_obj is None:
            continue
        try:
            ensure_condenser_properties(condenser_obj)
            _initialize_condenser_defaults(condenser_obj)
            was_link = _is_link_condenser(condenser_obj)
            if was_link:
                linked_obj = getattr(condenser_obj, "LinkedObject", None)
                linked_ok = _is_master_condenser_obj(linked_obj)
                if linked_ok:
                    model_expected = str(getattr(condenser_obj, "Model", DEFAULT_CONDENSER_MODEL) or DEFAULT_CONDENSER_MODEL)
                    model_linked = str(getattr(linked_obj, "Model", "") or "")
                    if model_linked and model_linked != model_expected:
                        linked_ok = False
                if linked_ok:
                    if not bool(getattr(condenser_obj, "LinkTransform", False)):
                        _configure_link_for_transform(condenser_obj)
                else:
                    previous_target = linked_obj
                    _apply_condenser_shape(condenser_obj, force=False)
                    if getattr(condenser_obj, "LinkedObject", None) != previous_target:
                        repaired += 1
            else:
                if not _condenser_has_valid_shape(condenser_obj):
                    _apply_condenser_shape(condenser_obj, force=False)
                    if _condenser_has_valid_shape(condenser_obj):
                        repaired += 1
            recalculate_condenser(condenser_obj)
        except Exception as exc:
            log("Sanitize condensadora omitida: {0} -> {1}".format(getattr(condenser_obj, "Name", "?"), exc))
    if repaired > 0:
        log("Sanitize condensadoras aplicado: reparadas={0}".format(repaired))
    return repaired


def refresh_step_models(doc=None):
    """Manual refresh for condenser STEP models and dependent links."""
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    masters_reset = 0
    refreshed = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_master_condenser_obj(obj):
            continue
        try:
            if "ShapeSignature" in getattr(obj, "PropertiesList", []):
                obj.ShapeSignature = ""
                masters_reset += 1
        except Exception:
            pass

    for condenser_obj in list(find_condensers(doc) or []):
        if condenser_obj is None:
            continue
        try:
            ensure_condenser_properties(condenser_obj)
            _initialize_condenser_defaults(condenser_obj)
            if "ShapeSignature" in getattr(condenser_obj, "PropertiesList", []):
                condenser_obj.ShapeSignature = ""
            _apply_condenser_shape(condenser_obj, force=False)
            recalculate_condenser(condenser_obj)
            refreshed += 1
        except Exception as exc:
            log("Refresh condensadora omitida: {0} -> {1}".format(getattr(condenser_obj, "Name", "?"), exc))

    removed_orphans = 0
    try:
        removed_orphans = _cleanup_orphan_symbol2d_objects(doc)
    except Exception:
        removed_orphans = 0
    removed_info_orphans = 0
    try:
        removed_info_orphans = _cleanup_orphan_info2d_objects(doc)
    except Exception:
        removed_info_orphans = 0

    log(
        "Refresh modelos condensadora manual: masters={0}, condensadoras={1}, simbolos2d_huerfanos={2}, textos2d_huerfanos={3}".format(
            masters_reset,
            refreshed,
            removed_orphans,
            removed_info_orphans,
        )
    )
    return refreshed


def refresh_condenser(condenser_obj):
    if condenser_obj is None:
        return
    ensure_condenser_properties(condenser_obj)
    _initialize_condenser_defaults(condenser_obj)
    _apply_condenser_shape(condenser_obj, force=False)
    recalculate_condenser(condenser_obj)


def find_symbol2d_objects(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    symbols = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if _is_symbol2d_obj(obj):
            symbols.append(obj)
    return symbols


def find_info2d_objects(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    infos = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if _is_info2d_obj(obj):
            infos.append(obj)
    return infos


def _pick_condenser_model_for_insert():
    if not App.GuiUp:
        return DEFAULT_CONDENSER_MODEL
    try:
        from PySide2 import QtWidgets
    except Exception:
        try:
            from PySide import QtGui as QtWidgets  # FreeCAD legacy fallback
        except Exception:
            return DEFAULT_CONDENSER_MODEL

    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("Insertar Condensadora HVAC")
    dialog.setMinimumWidth(560)

    cmb_discharge = QtWidgets.QComboBox()
    cmb_discharge.addItems(DISCHARGE_OPTIONS)
    cmb_discharge.setCurrentText(_normalize_discharge(_condenser_spec(DEFAULT_CONDENSER_MODEL).get("Discharge", "Horizontal")))

    cmb_model = QtWidgets.QComboBox()
    lbl_info = QtWidgets.QLabel("")

    def refresh_models():
        discharge = _normalize_discharge(cmb_discharge.currentText())
        models = _available_models_for_discharge(discharge)
        cmb_model.clear()
        for model_name in models:
            spec = _condenser_spec(model_name)
            capacity = int(round(_to_float(spec.get("CapacityBTU", 0.0), 0)))
            source = _model_source_tag(model_name)
            text = "{0} BTU/h | {1} | {2}".format(capacity, model_name, source)
            cmb_model.addItem(text, model_name)
        if cmb_model.count() <= 0:
            lbl_info.setText("No hay modelos para esta descarga")
        else:
            selected_model = str(cmb_model.currentData() or "")
            lbl_info.setText("Modelo seleccionado: {0}".format(selected_model))

    def on_model_change():
        selected_model = str(cmb_model.currentData() or "")
        if selected_model:
            lbl_info.setText("Modelo seleccionado: {0}".format(selected_model))

    cmb_discharge.currentIndexChanged.connect(refresh_models)
    cmb_model.currentIndexChanged.connect(on_model_change)
    refresh_models()

    form = QtWidgets.QFormLayout()
    form.addRow("Descarga:", cmb_discharge)
    form.addRow("Modelo:", cmb_model)
    form.addRow("Info:", lbl_info)

    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addLayout(form)
    layout.addWidget(buttons)

    result = dialog.exec_()
    if result == QtWidgets.QDialog.Accepted and cmb_model.count() > 0:
        selected = str(cmb_model.currentData() or DEFAULT_CONDENSER_MODEL)
        spec = _condenser_spec(selected)
        log(
            "Picker condensadora seleccionado: descarga={0}, modelo={1}, capacidad={2}, fuente={3}".format(
                _normalize_discharge(spec.get("Discharge", "Horizontal")),
                selected,
                int(round(_to_float(spec.get("CapacityBTU", 0.0), 0))),
                _model_source_tag(selected),
            )
        )
        return selected

    if result != QtWidgets.QDialog.Accepted:
        log("Insercion condensadora cancelada por usuario")
        return None
    log("Insercion condensadora cancelada: sin modelo disponible")
    return None


def insert_condenser_from_selection(doc=None, model_name=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return None

    selected_model = str(model_name or "")
    if not selected_model:
        selected_model = _pick_condenser_model_for_insert()
    if not selected_model:
        log("Insercion condensadora cancelada")
        return None
    if selected_model not in CONDENSER_LIBRARY:
        selected_model = DEFAULT_CONDENSER_MODEL

    try:
        obj = doc.addObject("App::Link", "HVAC_Condenser")
        log("InsertDebug condensadora creada como App::Link")
    except Exception as exc:
        log("InsertDebug fallback a Part::FeaturePython (App::Link no disponible): {0}".format(exc))
        obj = doc.addObject("Part::FeaturePython", "HVAC_Condenser")
        HVACCondenserProxy(obj)
        if getattr(obj, "ViewObject", None) is not None:
            HVACCondenserViewProvider(obj.ViewObject)
    ensure_condenser_properties(obj)
    _initialize_condenser_defaults(obj)
    set_condenser_model(obj, selected_model, force=True)
    if "VisualMode" in getattr(obj, "PropertiesList", []):
        try:
            obj.VisualMode = DEFAULT_VISUAL_MODE
            log("VisualMode default condensadora aplicado: {0}".format(str(getattr(obj, "VisualMode", ""))))
        except Exception:
            pass
    obj.AutoCollect = False
    obj.ConnectedUnits = []
    _apply_condenser_shape(obj, force=True)

    points = selection.get_selected_points()
    if points:
        point = App.Vector(points[0])
        _set_condenser_placement(obj, base_vec=point)
        _apply_condenser_shape(obj, force=False)
        log("Condenser ubicada en punto seleccionado")
    else:
        log("Condenser creada sin evaporadoras asignadas. Asigne manualmente.")

    recalculate_condenser(obj)
    hvac_project.add_object_to_hvac_group(doc, obj)
    try:
        doc.recompute()
    except Exception as exc:
        log("Recompute omitido tras insertar condensadora: {0}".format(exc))

    spec = _condenser_spec(selected_model)
    log(
        "Condenser insertada: modelo={0}, descarga={1}, capacidad={2} BTU/h".format(
            selected_model,
            _normalize_discharge(spec.get("Discharge", "Horizontal")),
            int(round(_to_float(obj.CapacityBTU, 0.0), 0)),
        )
    )
    return obj


class HVACCondenserProxy:
    def __init__(self, obj):
        obj.Proxy = self
        self._busy = False
        ensure_condenser_properties(obj)
        _initialize_condenser_defaults(obj)

    def onChanged(self, obj, prop):  # noqa: N802
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        if prop in {
            "CapacityBTU",
            "ConnectedUnits",
            "AutoCollect",
            "Model",
            "Discharge",
            "VisualMode",
            "Symbol2DSize",
            "ShowInfo2D",
            "Info2DSize",
            "Placement",
        }:
            self._busy = True
            try:
                ensure_condenser_properties(obj)
                _initialize_condenser_defaults(obj)
                if prop == "Discharge":
                    _switch_model_by_discharge(obj, getattr(obj, "Discharge", "Horizontal"))
                elif prop == "Model":
                    set_condenser_model(obj, getattr(obj, "Model", DEFAULT_CONDENSER_MODEL), force=False)
                _apply_condenser_shape(obj, force=(prop in {"Model", "Discharge"}))
                recalculate_condenser(obj)
            finally:
                self._busy = False

    def execute(self, obj):
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        self._busy = True
        try:
            ensure_condenser_properties(obj)
            _initialize_condenser_defaults(obj)
            _apply_condenser_shape(obj, force=False)
            recalculate_condenser(obj)
        finally:
            self._busy = False


class HVACCondenserViewProvider:
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
