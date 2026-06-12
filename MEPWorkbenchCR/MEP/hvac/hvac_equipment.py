"""HVAC evaporator equipment object."""

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
import re
import unicodedata

import FreeCAD as App
import Part

from ..utils import selection
from . import hvac_ports
from . import hvac_project
from . import hvac_space

MEP_TYPE = "HVACEquipment"
MASTER_MEP_TYPE = "HVACEvaporatorMaster"
SYMBOL2D_MEP_TYPE = "HVACEquipment2D"
LOG_PREFIX = "[MEP-HVAC][Equipment] "
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icons", "hvac.svg")
).replace(os.sep, "/")
EVAPORATOR_LIBRARY = {
    "Pared_9000": {
        "Type": "Wall",
        "CapacityBTU": 9000.0,
        "Size": (760.0, 230.0, 220.0),
        "StepFile": "Pared_9000.step",
        "Step2DFile": "Pared_9000_2D.step",
    },
    "Pared_12000": {
        "Type": "Wall",
        "CapacityBTU": 12000.0,
        "Size": (900.0, 260.0, 220.0),
        "StepFile": "Pared_12000.step",
        "Step2DFile": "Pared_12000_2D.step",
    },
    "Pared_18000": {
        "Type": "Wall",
        "CapacityBTU": 18000.0,
        "Size": (1040.0, 280.0, 240.0),
        "StepFile": "Pared_18000.step",
        "Step2DFile": "Pared_18000_2D.step",
    },
    "Pared_24000": {
        "Type": "Wall",
        "CapacityBTU": 24000.0,
        "Size": (1200.0, 300.0, 250.0),
        "StepFile": "Pared_24000.step",
        "Step2DFile": "Pared_24000_2D.step",
    },
    "Cassette_24000": {
        "Type": "Cassette",
        "CapacityBTU": 24000.0,
        "Size": (600.0, 600.0, 320.0),
        "StepFile": "Cassette_24000.step",
        "Step2DFile": "Cassette_24000_2D.step",
    },
    "Cassette_36000": {
        "Type": "Cassette",
        "CapacityBTU": 36000.0,
        "Size": (840.0, 840.0, 350.0),
        "StepFile": "Cassette_36000.step",
        "Step2DFile": "Cassette_36000_2D.step",
    },
    "Cassette_48000": {
        "Type": "Cassette",
        "CapacityBTU": 48000.0,
        "Size": (980.0, 980.0, 380.0),
        "StepFile": "Cassette_48000.step",
        "Step2DFile": "Cassette_48000_2D.step",
    },
    "Cassette_60000": {
        "Type": "Cassette",
        "CapacityBTU": 60000.0,
        "Size": (1100.0, 1100.0, 420.0),
        "StepFile": "Cassette_60000.step",
        "Step2DFile": "Cassette_60000_2D.step",
    },
    "PisoCielo_24000": {
        "Type": "FloorCeiling",
        "CapacityBTU": 24000.0,
        "Size": (1250.0, 235.0, 690.0),
        "StepFile": "PisoCielo_24000.step",
        "Step2DFile": "PisoCielo_24000_2D.step",
    },
    "PisoCielo_36000": {
        "Type": "FloorCeiling",
        "CapacityBTU": 36000.0,
        "Size": (1450.0, 250.0, 700.0),
        "StepFile": "PisoCielo_36000.step",
        "Step2DFile": "PisoCielo_36000_2D.step",
    },
    "PisoCielo_48000": {
        "Type": "FloorCeiling",
        "CapacityBTU": 48000.0,
        "Size": (1650.0, 280.0, 720.0),
        "StepFile": "PisoCielo_48000.step",
        "Step2DFile": "PisoCielo_48000_2D.step",
    },
    "Ducto_36000": {
        "Type": "Duct",
        "CapacityBTU": 36000.0,
        "Size": (1200.0, 360.0, 320.0),
        "StepFile": "Ducto_36000.step",
        "Step2DFile": "Ducto_36000_2D.step",
    },
    "Ducto_60000": {
        "Type": "Duct",
        "CapacityBTU": 60000.0,
        "Size": (1600.0, 450.0, 380.0),
        "StepFile": "Ducto_60000.step",
        "Step2DFile": "Ducto_60000_2D.step",
    },
}
DEFAULT_MODEL = "Pared_12000"
DEFAULT_SYMBOL_SIZE = 450.0
VISUAL_MODE_OPTIONS = ["Ambos", "Solo2D", "Solo3D", "Ninguno"]
DEFAULT_VISUAL_MODE = "Ambos"
MASTER_PREFIX = "HVAC_EvapMaster_"
EQUIP_DEBUG_REV = "2026-04-13-eq-r14"
MASTER_SHAPE_SCHEMA_REV = "2026-04-13-r2"
STEP_MASTER_AUTO_RELOAD = False
GROUP_MODEL_PREFIX = "Grupo::"
GROUP_MODEL_LABEL_ALIASES = {
    "modelos",
    "models",
    "model",
    "biblioteca",
    "hvac modelos",
    "hvac models",
}
STEP_EXTENSIONS = (".step", ".stp", ".stpz")
TYPE_UI_TO_INTERNAL = {
    "Pared": "Wall",
    "Cassette": "Cassette",
    "Piso-Cielo": "FloorCeiling",
    "Ducto": "Duct",
}
TYPE_INTERNAL_TO_UI = {value: key for key, value in TYPE_UI_TO_INTERNAL.items()}
EQUIPMENT_TYPE_OPTIONS = ["Wall", "Cassette", "FloorCeiling", "Duct"]
SYSTEM_TYPE_OPTIONS = ["Mini-split", "Multi-split", "VRF", "Otro"]
DEFAULT_SYSTEM_TYPE = "Mini-split"
DEFAULT_INFO2D_SIZE = 90.0
LEGACY_INFO2D_SIZE = 120.0
LEGACY_INFO2D_SIZE_SMALL = 14.0
MIN_INFO2D_SIZE = 20.0
MAX_INFO2D_SIZE = 600.0
INFO2D_MEP_TYPE = "HVACEquipmentInfo2D"
INFO2D_DEBUG_ENABLED = True
_STEP_SHAPE_CACHE = {}
_ACCESS_VIOLATION_TOKENS = (
    "access violation",
    "violacion de acceso",
    "link broken",
    "broken link",
    "link roto",
)


def log(message):
    text = LOG_PREFIX + str(message)
    print(text)


def _exc_text(exc):
    try:
        return str(exc or "").strip()
    except Exception:
        return ""


def _is_access_violation(exc):
    text = _exc_text(exc).lower()
    if not text:
        return False
    return any(token in text for token in _ACCESS_VIOLATION_TOKENS)


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


def _remove_broken_equipment(doc, equipment_obj, reason="", context="runtime"):
    if doc is None or equipment_obj is None:
        return False
    obj_name = _safe_obj_name(equipment_obj)
    if not obj_name:
        return False

    try:
        props = list(getattr(equipment_obj, "PropertiesList", []) or [])
    except Exception:
        props = []
    if "Space" in props:
        try:
            equipment_obj.Space = None
        except Exception:
            pass

    try:
        existing = doc.getObject(obj_name)
    except Exception:
        existing = None
    if existing is None:
        return False

    reason_text = _exc_text(reason) or "invalid object"
    try:
        doc.removeObject(obj_name)
        log(
            "Evaporadora invalida eliminada ({0}): {1} -> {2}".format(
                str(context or "runtime"),
                obj_name,
                reason_text,
            )
        )
        return True
    except Exception as exc:
        log(
            "No se pudo eliminar evaporadora invalida ({0}): {1} -> {2}".format(
                str(context or "runtime"),
                obj_name,
                _exc_text(exc) or exc,
            )
        )
        return False


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
    # Migrate old default from previous builds.
    if abs(float(size) - float(LEGACY_INFO2D_SIZE)) <= 0.5:
        size = DEFAULT_INFO2D_SIZE
    if abs(float(size) - float(LEGACY_INFO2D_SIZE_SMALL)) <= 0.5:
        size = DEFAULT_INFO2D_SIZE
    return _clamp(size, MIN_INFO2D_SIZE, MAX_INFO2D_SIZE)


def _normalize_text(value):
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))


def _is_group(obj):
    type_id = str(getattr(obj, "TypeId", "") or "")
    if type_id.startswith("App::DocumentObjectGroup"):
        return True
    return hasattr(obj, "Group") and hasattr(obj, "addObject")


def _shape_from_obj(obj, apply_placement=False):
    if obj is None or not hasattr(obj, "Shape"):
        return None
    try:
        shape = obj.Shape
        if shape is None or shape.isNull():
            return None
        if bool(apply_placement):
            shape = shape.copy()
            placement = getattr(obj, "Placement", None)
            if placement is not None:
                try:
                    shape.Placement = placement
                except Exception:
                    try:
                        shape.transformShape(placement.toMatrix(), True)
                    except Exception:
                        pass
        bbox = shape.BoundBox
        if float(bbox.XLength) <= 0.1 or float(bbox.YLength) <= 0.1 or float(bbox.ZLength) <= 0.1:
            return None
        return shape
    except Exception:
        return None


def _find_model_group(doc):
    if doc is None:
        return None

    selected = list(selection.get_selected_objects(resolve_links=True) or [])
    for obj in selected:
        if not _is_group(obj):
            continue
        label_norm = _normalize_text(getattr(obj, "Label", ""))
        name_norm = _normalize_text(getattr(obj, "Name", ""))
        if label_norm in GROUP_MODEL_LABEL_ALIASES or name_norm in GROUP_MODEL_LABEL_ALIASES:
            return obj

    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_group(obj):
            continue
        label_norm = _normalize_text(getattr(obj, "Label", ""))
        name_norm = _normalize_text(getattr(obj, "Name", ""))
        if label_norm in GROUP_MODEL_LABEL_ALIASES or name_norm in GROUP_MODEL_LABEL_ALIASES:
            return obj
    return None


def _group_model_map(doc):
    result = {}
    group = _find_model_group(doc)
    if group is None:
        return result

    for child in list(getattr(group, "Group", []) or []):
        candidate = selection.unwrap_link(child)
        if _shape_from_obj(candidate) is None:
            continue
        label = str(getattr(candidate, "Label", "") or getattr(candidate, "Name", "") or "").strip()
        if not label:
            continue
        key_base = GROUP_MODEL_PREFIX + label
        key = key_base
        idx = 2
        while key in result:
            key = "{0} ({1})".format(key_base, idx)
            idx += 1
        result[key] = candidate
    return result


def _is_group_model_name(model_name):
    return str(model_name or "").startswith(GROUP_MODEL_PREFIX)


def _model_capacity_guess(model_name):
    tokens = re.findall(r"\d{4,6}", str(model_name or ""))
    if not tokens:
        return 0.0
    try:
        return float(tokens[0])
    except Exception:
        return 0.0


def _group_model_object(doc, model_name):
    return _group_model_map(doc).get(str(model_name or ""))


def _group_model_shape(doc, model_name):
    source_obj = _group_model_object(doc, model_name)
    source_shape = _shape_from_obj(source_obj, apply_placement=True)
    if source_shape is None:
        return None
    try:
        shape_copy = source_shape.copy()
        bbox = shape_copy.BoundBox
        shape_copy.translate(App.Vector(-float(bbox.Center.x), -float(bbox.Center.y), -float(bbox.ZMin)))
        return shape_copy
    except Exception:
        return None


def _step_library_dir():
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "resources",
            "libraries",
            "hvac",
            "evaporators",
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
            "evaporators",
        )
    )


def _step_file_index():
    index = {}
    library_dir = _step_library_dir()
    if not os.path.isdir(library_dir):
        return index
    try:
        entries = list(os.listdir(library_dir))
    except Exception:
        return index
    for entry in entries:
        ext = os.path.splitext(entry)[1].lower()
        if ext not in STEP_EXTENSIONS:
            continue
        base = os.path.splitext(entry)[0].strip().lower()
        if not base:
            continue
        index[base] = os.path.join(library_dir, entry)
    return index


def _resolve_symbol2d_step_for_model(model_name):
    model = str(model_name or "").strip()
    if not model:
        return ""
    library_dir = _symbol2d_library_dir()
    if not os.path.isdir(library_dir):
        return ""

    candidates = []
    spec = EVAPORATOR_LIBRARY.get(model)
    if isinstance(spec, dict):
        configured = str(spec.get("Step2DFile", "") or spec.get("Symbol2DStepFile", "")).strip()
        if configured:
            candidates.append(configured)

    base = os.path.splitext(model)[0].strip()
    if base:
        candidates.extend(
            [
                "{0}_2D.step".format(base),
                "{0}_2d.step".format(base),
                "{0}.step".format(base),
                "{0}.stp".format(base),
            ]
        )

    seen = set()
    for candidate in candidates:
        key = str(candidate or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        symbol_path = os.path.join(library_dir, str(candidate))
        if os.path.isfile(symbol_path):
            return symbol_path
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


def _resolve_step_file_for_model(model_name):
    model = str(model_name or "").strip()
    if not model or _is_group_model_name(model):
        return ""

    spec = EVAPORATOR_LIBRARY.get(model)
    candidates = []
    if isinstance(spec, dict):
        step_file = str(spec.get("StepFile", "")).strip()
        if step_file:
            candidates.append(os.path.splitext(step_file)[0].lower())

    model_base = os.path.splitext(model)[0].strip()
    if model_base:
        candidates.append(model_base.lower())
        candidates.append(model_base.replace(" ", "_").lower())
        candidates.append(model_base.replace("-", "_").lower())

    index = _step_file_index()
    for key in candidates:
        path = index.get(str(key).strip().lower(), "")
        if path and os.path.isfile(path):
            return path
    return ""


def _normalize_shape_to_origin(shape, preserve_xy=False):
    if shape is None:
        return None
    try:
        result = shape.copy()
        bbox = result.BoundBox
        if bool(preserve_xy):
            result.translate(App.Vector(0.0, 0.0, -float(bbox.ZMin)))
        else:
            result.translate(App.Vector(-float(bbox.Center.x), -float(bbox.Center.y), -float(bbox.ZMin)))
        return result
    except Exception:
        return None


def _safe_shape_volume(shape):
    if shape is None or shape.isNull():
        return 0.0
    try:
        return max(0.0, float(getattr(shape, "Volume", 0.0) or 0.0))
    except Exception:
        return 0.0


def _sanitize_step_shape(shape, source_path=""):
    """Keep only useful solids from imported STEP to avoid visual artifacts and mesh warnings."""
    if shape is None or shape.isNull():
        return None

    kept_solids = []
    dropped_solids = 0
    try:
        raw_solids = list(getattr(shape, "Solids", []) or [])
    except Exception:
        raw_solids = []

    if raw_solids:
        largest_volume = 0.0
        for solid in raw_solids:
            largest_volume = max(largest_volume, _safe_shape_volume(solid))
        # Drop tiny sliver solids that come from dirty STEP exports.
        min_keep_volume = max(0.1, largest_volume * 1e-5)
        for solid in raw_solids:
            vol = _safe_shape_volume(solid)
            if vol >= min_keep_volume:
                try:
                    kept_solids.append(solid.copy())
                except Exception:
                    pass
            else:
                dropped_solids += 1

    if kept_solids:
        try:
            cleaned = kept_solids[0] if len(kept_solids) == 1 else Part.Compound(kept_solids)
        except Exception:
            cleaned = None
    else:
        # Fallback to original shape if no solids are available.
        cleaned = shape

    if cleaned is None or cleaned.isNull():
        return None

    try:
        refined = cleaned.removeSplitter()
        if refined is not None and not refined.isNull():
            cleaned = refined
    except Exception:
        pass

    if dropped_solids > 0:
        log(
            "STEP saneado ({0}): solidos_descartados={1}".format(
                os.path.basename(str(source_path or "")) or "sin_nombre",
                int(dropped_solids),
            )
        )
    return cleaned


def _step_cache_key(step_path, preserve_xy=False):
    try:
        st = os.stat(step_path)
        return (os.path.abspath(step_path), int(st.st_mtime_ns), int(st.st_size), int(bool(preserve_xy)))
    except Exception:
        return (os.path.abspath(step_path), 0, 0, int(bool(preserve_xy)))


def _master_shape_signature(model_name, height_m, symbol_size_mm, visual_mode=DEFAULT_VISUAL_MODE):
    model = str(model_name or DEFAULT_MODEL)
    h_token = int(round(max(0.0, float(height_m)) * 1000.0))
    s_token = int(round(max(100.0, float(symbol_size_mm))))
    v_token = _sanitize_model_token(_normalized_visual_mode(visual_mode))
    step_path = _resolve_step_file_for_model(model)
    if step_path:
        source_token = str(os.path.basename(step_path) or "").strip()
        if bool(STEP_MASTER_AUTO_RELOAD):
            key = _step_cache_key(step_path)
            source_token = "{0}:{1}:{2}".format(os.path.basename(str(key[0])), int(key[1]), int(key[2]))
    else:
        source_token = "builtin"
    return "schema={0};model={1};h={2};s={3};v={4};src={5}".format(
        MASTER_SHAPE_SCHEMA_REV,
        model,
        h_token,
        s_token,
        v_token,
        source_token,
    )


def _get_cached_step_shape(step_path, preserve_xy=False):
    key = _step_cache_key(step_path, preserve_xy=preserve_xy)
    cached = _STEP_SHAPE_CACHE.get(key)
    if cached is None:
        return None
    try:
        return cached.copy()
    except Exception:
        return None


def _put_cached_step_shape(step_path, shape, preserve_xy=False):
    if shape is None:
        return
    key = _step_cache_key(step_path, preserve_xy=preserve_xy)
    path_abs = key[0]
    stale_keys = [
        k
        for k in list(_STEP_SHAPE_CACHE.keys())
        if isinstance(k, tuple) and len(k) >= 1 and k[0] == path_abs and k != key
    ]
    for stale in stale_keys:
        _STEP_SHAPE_CACHE.pop(stale, None)
    try:
        _STEP_SHAPE_CACHE[key] = shape.copy()
    except Exception:
        pass


def _load_step_shape(step_path, preserve_xy=False):
    if not step_path or not os.path.isfile(step_path):
        return None

    cached = _get_cached_step_shape(step_path, preserve_xy=preserve_xy)
    if cached is not None:
        return cached

    # Preferred path: read STEP directly as one shape.
    try:
        direct_shape = None
        if hasattr(Part, "read"):
            direct_shape = Part.read(step_path)
        if direct_shape is not None and not direct_shape.isNull():
            sanitized = _sanitize_step_shape(direct_shape, source_path=step_path)
            normalized = _normalize_shape_to_origin(sanitized, preserve_xy=preserve_xy)
            if normalized is not None and not normalized.isNull():
                _put_cached_step_shape(step_path, normalized, preserve_xy=preserve_xy)
                return normalized
    except Exception:
        pass

    # Fallback path for environments where direct read is unavailable.
    temp_doc = None
    try:
        temp_doc = App.newDocument("HVAC_STEP_TMP")
    except Exception:
        temp_doc = None
    if temp_doc is None:
        return None

    try:
        loaded = False
        try:
            import Import  # noqa: F401
            import Import as ImportModule

            ImportModule.insert(step_path, temp_doc.Name)
            loaded = True
        except Exception:
            loaded = False

        if not loaded:
            try:
                Part.insert(step_path, temp_doc.Name)
                loaded = True
            except Exception:
                loaded = False
        if not loaded:
            return None

        shapes = []
        for obj in list(getattr(temp_doc, "Objects", []) or []):
            shape = _shape_from_obj(obj, apply_placement=True)
            if shape is not None:
                try:
                    shapes.append(shape.copy())
                except Exception:
                    pass
        if not shapes:
            return None
        compound = shapes[0] if len(shapes) == 1 else Part.Compound(shapes)
        sanitized = _sanitize_step_shape(compound, source_path=step_path)
        normalized = _normalize_shape_to_origin(sanitized, preserve_xy=preserve_xy)
        if normalized is not None and not normalized.isNull():
            _put_cached_step_shape(step_path, normalized, preserve_xy=preserve_xy)
            return normalized
        return None
    except Exception:
        return None
    finally:
        try:
            App.closeDocument(temp_doc.Name)
        except Exception:
            pass


def _model_source_tag(model_name):
    if _resolve_step_file_for_model(model_name):
        return "STEP"
    return "PRIMITIVE"


def _guess_ui_type_from_model_name(model_name):
    name = _normalize_text(model_name)
    if not name:
        return "Pared"
    if "cassette" in name or "casete" in name:
        return "Cassette"
    if "ducto" in name or "duct" in name or "conducto" in name:
        return "Ducto"
    if "piso" in name or "cielo" in name or "techo" in name:
        return "Piso-Cielo"
    return "Pared"


def _picker_models_by_type(doc=None):
    grouped = {key: [] for key in TYPE_UI_TO_INTERNAL.keys()}
    for model_name, spec in EVAPORATOR_LIBRARY.items():
        eq_type = str(spec.get("Type", "Wall") or "Wall")
        ui_type = TYPE_INTERNAL_TO_UI.get(eq_type, "Pared")
        capacity = _to_float(spec.get("CapacityBTU", 0.0), 0.0)
        grouped.setdefault(ui_type, []).append(
            {
                "Model": model_name,
                "Capacity": capacity,
                "Source": _model_source_tag(model_name),
            }
        )

    if doc is not None:
        for group_model_name in list(_group_model_map(doc).keys()):
            ui_type = _guess_ui_type_from_model_name(group_model_name)
            capacity = _model_capacity_guess(group_model_name)
            grouped.setdefault(ui_type, []).append(
                {
                    "Model": group_model_name,
                    "Capacity": capacity,
                    "Source": "GROUP",
                }
            )

    for ui_type in grouped:
        grouped[ui_type] = sorted(
            grouped[ui_type],
            key=lambda row: (_to_float(row.get("Capacity", 0.0), 0.0), str(row.get("Model", "")).lower()),
        )
    return grouped


def ensure_equipment_properties(obj):
    added_model = False
    added_type = False
    added_capacity = False
    added_height = False
    added_base_level = False
    added_symbol_size = False
    added_show_symbol = False
    added_visual_mode = False
    added_auto_detect = False
    added_use_ports = False
    added_coverage = False
    added_system_type = False
    added_show_info2d = False
    added_info2d_size = False

    if "MEPType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
    if str(getattr(obj, "MEPType", "")) != MEP_TYPE:
        obj.MEPType = MEP_TYPE

    model_added = False
    if "Model" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "Model", "HVAC Equipment", "Concrete evaporator model")
        obj.Model = list(EVAPORATOR_LIBRARY.keys())
        model_added = True
        added_model = True
    if "Type" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "Type", "HVAC Equipment", "Equipment type")
        obj.Type = EQUIPMENT_TYPE_OPTIONS
        added_type = True
    if "CapacityBTU" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "CapacityBTU", "HVAC Equipment", "Equipment capacity")
        added_capacity = True
    if "Space" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "Space", "HVAC Equipment", "Assigned HVAC space")
    if "Height" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Height", "HVAC Equipment", "Mounting height (m)")
        added_height = True
    if "BaseLevel" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "BaseLevel", "HVAC Equipment", "Base elevation reference (mm)")
        added_base_level = True
    if "Symbol2DSize" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Symbol2DSize", "HVAC Equipment", "2D symbol size (mm)")
        added_symbol_size = True
    if "ShowSymbol2D" not in obj.PropertiesList:
        obj.addProperty("App::PropertyBool", "ShowSymbol2D", "HVAC Equipment", "Show 2D symbol in plan")
        added_show_symbol = True
    if "VisualMode" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "VisualMode", "HVAC Equipment", "Visual representation mode")
        obj.VisualMode = VISUAL_MODE_OPTIONS
        added_visual_mode = True
    if "Symbol2D" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "Symbol2D", "HVAC Equipment", "Linked 2D symbol object")
    if "SystemType" not in obj.PropertiesList:
        obj.addProperty("App::PropertyEnumeration", "SystemType", "HVAC Equipment", "System class shown in 2D plan text")
        try:
            obj.SystemType = list(SYSTEM_TYPE_OPTIONS)
        except Exception:
            pass
        added_system_type = True
    if "ShowInfo2D" not in obj.PropertiesList:
        obj.addProperty("App::PropertyBool", "ShowInfo2D", "HVAC Equipment", "Show 2D plan text near evaporator symbol")
        added_show_info2d = True
    if "Info2DSize" not in obj.PropertiesList:
        obj.addProperty("App::PropertyFloat", "Info2DSize", "HVAC Equipment", "2D plan text size")
        added_info2d_size = True
    if "Info2D" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", "Info2D", "HVAC Equipment", "Linked 2D text object")
    if "CoveragePct" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyFloat",
            "CoveragePct",
            "HVAC Equipment",
            "Coverage percentage for assigned space",
        )
        added_coverage = True
    if "AutoDetectSpace" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyBool",
            "AutoDetectSpace",
            "HVAC Equipment",
            "Auto assign nearest/selected HVAC space",
        )
        added_auto_detect = True
    if "UsePorts" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyBool",
            "UsePorts",
            "HVAC Equipment",
            "Generate technical ports for routes/system flow",
        )
        added_use_ports = True
    if "Ports" not in obj.PropertiesList:
        obj.addProperty("App::PropertyLinkList", "Ports", "HVAC Equipment", "Equipment port objects")

    model_options = available_models(getattr(obj, "Document", None))
    if "Model" in obj.PropertiesList:
        current_model = str(getattr(obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
        try:
            obj.Model = model_options
        except Exception:
            pass
        if model_added:
            current_model = DEFAULT_MODEL
        if current_model not in model_options:
            current_model = DEFAULT_MODEL
        try:
            obj.Model = current_model
        except Exception:
            pass
    if "Type" in obj.PropertiesList:
        current_type = str(getattr(obj, "Type", "Wall") or "Wall")
        try:
            obj.Type = EQUIPMENT_TYPE_OPTIONS
        except Exception:
            pass
        if current_type not in EQUIPMENT_TYPE_OPTIONS:
            current_type = "Wall"
        try:
            obj.Type = current_type
        except Exception:
            pass
    if "SystemType" in obj.PropertiesList:
        current_system = str(getattr(obj, "SystemType", DEFAULT_SYSTEM_TYPE) or DEFAULT_SYSTEM_TYPE)
        try:
            obj.SystemType = list(SYSTEM_TYPE_OPTIONS)
        except Exception:
            pass
        if current_system not in SYSTEM_TYPE_OPTIONS:
            current_system = DEFAULT_SYSTEM_TYPE
        try:
            obj.SystemType = current_system
        except Exception:
            pass
    if added_type:
        obj.Type = EVAPORATOR_LIBRARY[DEFAULT_MODEL]["Type"]
    if added_capacity:
        obj.CapacityBTU = EVAPORATOR_LIBRARY[DEFAULT_MODEL]["CapacityBTU"]
    if added_height:
        obj.Height = 2.3
    if added_base_level:
        obj.BaseLevel = 0.0
    if added_symbol_size:
        obj.Symbol2DSize = DEFAULT_SYMBOL_SIZE
    if added_show_symbol:
        # Legacy property kept for compatibility; geometry now includes 2D in the same object.
        obj.ShowSymbol2D = False
    if "VisualMode" in obj.PropertiesList:
        try:
            obj.VisualMode = VISUAL_MODE_OPTIONS
        except Exception:
            pass
        if added_visual_mode:
            obj.VisualMode = DEFAULT_VISUAL_MODE
        else:
            try:
                obj.VisualMode = _normalized_visual_mode(getattr(obj, "VisualMode", DEFAULT_VISUAL_MODE))
            except Exception:
                obj.VisualMode = DEFAULT_VISUAL_MODE
    if added_coverage:
        obj.CoveragePct = 0.0
    if added_system_type:
        try:
            obj.SystemType = DEFAULT_SYSTEM_TYPE
        except Exception:
            pass
    if added_show_info2d:
        obj.ShowInfo2D = True
    if added_info2d_size:
        obj.Info2DSize = DEFAULT_INFO2D_SIZE
    if added_auto_detect:
        obj.AutoDetectSpace = True
    if added_use_ports:
        obj.UsePorts = False


def available_models(doc=None):
    models = list(EVAPORATOR_LIBRARY.keys())
    if doc is not None:
        models.extend(list(_group_model_map(doc).keys()))
    return models


def _model_spec(model_name):
    return EVAPORATOR_LIBRARY.get(str(model_name), EVAPORATOR_LIBRARY[DEFAULT_MODEL])


def set_equipment_model(equipment_obj, model_name, force=False):
    if equipment_obj is None:
        return
    ensure_equipment_properties(equipment_obj)
    doc = getattr(equipment_obj, "Document", None)
    model_options = available_models(doc)
    model = str(model_name or DEFAULT_MODEL)
    if model not in model_options:
        model = DEFAULT_MODEL
    if "Model" in equipment_obj.PropertiesList:
        equipment_obj.Model = model

    if _is_group_model_name(model):
        if force or str(getattr(equipment_obj, "Type", "")) not in EQUIPMENT_TYPE_OPTIONS:
            equipment_obj.Type = "Wall"
        if force or _to_float(getattr(equipment_obj, "CapacityBTU", 0.0), 0.0) <= 0.0:
            guessed_capacity = _model_capacity_guess(model)
            equipment_obj.CapacityBTU = guessed_capacity if guessed_capacity > 0 else 12000.0
        return

    spec = _model_spec(model)
    if force or str(getattr(equipment_obj, "Type", "")) not in EQUIPMENT_TYPE_OPTIONS:
        equipment_obj.Type = spec["Type"]
    if force or _to_float(getattr(equipment_obj, "CapacityBTU", 0.0), 0.0) <= 0.0:
        equipment_obj.CapacityBTU = float(spec["CapacityBTU"])


def _initialize_equipment_defaults(obj):
    doc = getattr(obj, "Document", None)
    model_options = available_models(doc)
    model = str(getattr(obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    if model not in model_options:
        model = DEFAULT_MODEL
    if "Model" in obj.PropertiesList:
        try:
            obj.Model = model_options
        except Exception:
            pass
        obj.Model = model

    if model in EVAPORATOR_LIBRARY:
        spec = _model_spec(model)
        if str(obj.Type) not in EQUIPMENT_TYPE_OPTIONS:
            obj.Type = spec["Type"]
        if _to_float(obj.CapacityBTU, 0) <= 0:
            obj.CapacityBTU = spec["CapacityBTU"]
    else:
        if str(obj.Type) not in EQUIPMENT_TYPE_OPTIONS:
            obj.Type = "Wall"
        if _to_float(obj.CapacityBTU, 0) <= 0:
            guessed_capacity = _model_capacity_guess(model)
            obj.CapacityBTU = guessed_capacity if guessed_capacity > 0 else 12000.0
    normalized_height = _sanitize_height_input_m(getattr(obj, "Height", 0.0))
    if normalized_height <= 0.0:
        obj.Height = 2.3
    elif abs(_to_float(getattr(obj, "Height", 0.0), 0.0) - normalized_height) > 0.0001:
        obj.Height = normalized_height
    if _to_float(getattr(obj, "Symbol2DSize", 0.0), 0.0) <= 0:
        obj.Symbol2DSize = DEFAULT_SYMBOL_SIZE
    if not isinstance(getattr(obj, "ShowSymbol2D", False), bool):
        obj.ShowSymbol2D = False
    if "VisualMode" in getattr(obj, "PropertiesList", []):
        try:
            obj.VisualMode = VISUAL_MODE_OPTIONS
        except Exception:
            pass
        mode = _normalized_visual_mode(getattr(obj, "VisualMode", DEFAULT_VISUAL_MODE))
        try:
            obj.VisualMode = mode
        except Exception:
            pass
    if "SystemType" in getattr(obj, "PropertiesList", []):
        current_system = str(getattr(obj, "SystemType", DEFAULT_SYSTEM_TYPE) or DEFAULT_SYSTEM_TYPE)
        try:
            obj.SystemType = list(SYSTEM_TYPE_OPTIONS)
        except Exception:
            pass
        if current_system not in SYSTEM_TYPE_OPTIONS:
            current_system = DEFAULT_SYSTEM_TYPE
        try:
            obj.SystemType = current_system
        except Exception:
            pass
    if not isinstance(getattr(obj, "ShowInfo2D", True), bool):
        obj.ShowInfo2D = True
    current_info2d_size = _to_float(getattr(obj, "Info2DSize", 0.0), 0.0)
    legacy_floor = max(MIN_INFO2D_SIZE, DEFAULT_INFO2D_SIZE * 0.45)
    if current_info2d_size <= 0.0 or current_info2d_size < legacy_floor:
        obj.Info2DSize = DEFAULT_INFO2D_SIZE
    else:
        normalized_info2d_size = _normalized_info2d_size(current_info2d_size)
        if abs(float(current_info2d_size) - float(normalized_info2d_size)) > 0.01:
            obj.Info2DSize = normalized_info2d_size
    if not isinstance(getattr(obj, "AutoDetectSpace", True), bool):
        obj.AutoDetectSpace = True
    if not isinstance(getattr(obj, "UsePorts", False), bool):
        obj.UsePorts = False
    if _to_float(obj.CoveragePct, 0) < 0:
        obj.CoveragePct = 0.0


def _equipment_size(equipment_obj):
    doc = getattr(equipment_obj, "Document", None)
    model = str(getattr(equipment_obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    if model in EVAPORATOR_LIBRARY:
        return tuple(EVAPORATOR_LIBRARY[model]["Size"])
    if _is_group_model_name(model):
        group_shape = _group_model_shape(doc, model)
        if group_shape is not None:
            bbox = group_shape.BoundBox
            return (
                max(100.0, float(bbox.XLength)),
                max(100.0, float(bbox.YLength)),
                max(100.0, float(bbox.ZLength)),
            )

    eq_type = str(getattr(equipment_obj, "Type", "Wall"))
    if eq_type == "Cassette":
        return (600.0, 600.0, 320.0)
    if eq_type == "Duct":
        return (1200.0, 360.0, 320.0)
    return (900.0, 260.0, 220.0)


def _is_link_equipment(equipment_obj):
    return str(getattr(equipment_obj, "TypeId", "") or "") == "App::Link"


def _height_value_m(equipment_obj):
    return _sanitize_height_input_m(getattr(equipment_obj, "Height", 0.0))


def _sanitize_height_input_m(value):
    """Normalize mount height input to meters.

    Practical rule:
    - normal input is meters (2.3, 3.0, ...)
    - if user enters very large numbers (>= 100), interpret as millimeters
      to avoid sending the object far away in Z.
    """
    raw = _to_float(value, 0.0)
    if raw >= 100.0:
        raw = raw / 1000.0
    return max(0.0, float(raw))


def _symbol_size_mm(equipment_obj):
    return max(100.0, _to_float(getattr(equipment_obj, "Symbol2DSize", DEFAULT_SYMBOL_SIZE), DEFAULT_SYMBOL_SIZE))


def _symbol2d_step_scale_enabled(equipment_obj):
    """Explicit STEP 2D scaling is opt-in per model.

    Default: disabled, to preserve exact STEP origin/alignment vs 3D model.
    """
    if equipment_obj is None:
        return False
    model = str(getattr(equipment_obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    spec = EVAPORATOR_LIBRARY.get(model, {}) if isinstance(EVAPORATOR_LIBRARY, dict) else {}
    if not isinstance(spec, dict):
        return False
    for key in ("Step2DAllowScale", "Symbol2DAllowScale", "Step2DAutoScale"):
        value = spec.get(key, None)
        if value is None:
            continue
        try:
            return bool(value)
        except Exception:
            return False
    return False


def _normalized_visual_mode(value):
    mode = str(value or DEFAULT_VISUAL_MODE).strip()
    if mode not in VISUAL_MODE_OPTIONS:
        return DEFAULT_VISUAL_MODE
    return mode


def _visual_mode_value(equipment_obj):
    if equipment_obj is None:
        return DEFAULT_VISUAL_MODE
    return _normalized_visual_mode(getattr(equipment_obj, "VisualMode", DEFAULT_VISUAL_MODE))


def _sanitize_model_token(model_name):
    raw = str(model_name or DEFAULT_MODEL)
    token = "".join(char if (char.isalnum() or char == "_") else "_" for char in raw)
    token = "_".join([part for part in token.split("_") if part])
    return token or DEFAULT_MODEL


def _master_internal_name(model_name, height_m=2.3, symbol_size_mm=DEFAULT_SYMBOL_SIZE, visual_mode=DEFAULT_VISUAL_MODE):
    height_token = int(round(max(0.0, float(height_m)) * 1000.0))
    symbol_token = int(round(max(100.0, float(symbol_size_mm))))
    mode_token = _sanitize_model_token(_normalized_visual_mode(visual_mode))
    return "{0}{1}_H{2}_S{3}_V{4}".format(
        MASTER_PREFIX,
        _sanitize_model_token(model_name),
        height_token,
        symbol_token,
        mode_token,
    )


def _build_symbol_shape(size_mm, equipment_obj=None):
    model_name = str(getattr(equipment_obj, "Model", "") or "")
    symbol_step = _resolve_symbol2d_step_for_model(model_name)
    if symbol_step:
        loaded = _load_step_shape(symbol_step, preserve_xy=True)
        if loaded is not None:
            # Keep explicit STEP 2D geometry exactly as authored by default.
            # This avoids XY drift when symbol origin and model origin must match.
            if not _symbol2d_step_scale_enabled(equipment_obj):
                try:
                    return loaded.copy()
                except Exception:
                    return loaded
            return _scale_symbol_shape_xy(loaded, size_mm, allow_downscale=False)

    radius = max(50.0, float(size_mm) * 0.5)
    p1 = App.Vector(-radius, -radius, 0.0)
    p2 = App.Vector(radius, radius, 0.0)
    p3 = App.Vector(-radius, radius, 0.0)
    p4 = App.Vector(radius, -radius, 0.0)
    line_1 = Part.makeLine(p1, p2)
    line_2 = Part.makeLine(p3, p4)
    circle = Part.makeCircle(radius * 0.9, App.Vector(0.0, 0.0, 0.0), App.Vector(0, 0, 1))
    return Part.Compound([line_1, line_2, circle])


def _centered_builtin_body_shape(model_name):
    model = str(model_name or DEFAULT_MODEL)
    if model in EVAPORATOR_LIBRARY:
        sx, sy, sz = tuple(EVAPORATOR_LIBRARY[model]["Size"])
    else:
        sx, sy, sz = tuple(EVAPORATOR_LIBRARY[DEFAULT_MODEL]["Size"])
    shape = Part.makeBox(float(sx), float(sy), float(sz))
    shape.translate(App.Vector(-float(sx) * 0.5, -float(sy) * 0.5, 0.0))
    return shape


def _body_shape_for_model(doc, model_name):
    model = str(model_name or DEFAULT_MODEL)
    if _is_group_model_name(model):
        group_shape = _group_model_shape(doc, model)
        if group_shape is not None:
            return group_shape
    step_path = _resolve_step_file_for_model(model)
    if step_path:
        step_shape = _load_step_shape(step_path, preserve_xy=True)
        if step_shape is not None:
            log("Geometria cargada desde STEP para modelo {0}: {1}".format(model, os.path.basename(step_path)))
            return step_shape
    return _centered_builtin_body_shape(model)


def _build_compound_shape(doc, model_name, height_m, symbol_size_mm, visual_mode=DEFAULT_VISUAL_MODE):
    components = []
    include_body = True

    if include_body:
        body_shape = _body_shape_for_model(doc, model_name)
        if body_shape is not None:
            body_copy = body_shape.copy()
            body_copy.translate(App.Vector(0.0, 0.0, max(0.0, float(height_m)) * 1000.0))
            components.append(body_copy)

    if not components:
        return Part.Shape()
    if len(components) == 1:
        return components[0]
    return Part.Compound(components)


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


def _ensure_master_equipment(
    doc,
    model_name,
    height_m=2.3,
    symbol_size_mm=DEFAULT_SYMBOL_SIZE,
    visual_mode=DEFAULT_VISUAL_MODE,
):
    if doc is None:
        return None
    model = str(model_name or DEFAULT_MODEL)
    height_m = max(0.0, float(height_m))
    symbol_size_mm = max(100.0, float(symbol_size_mm))
    visual_mode = _normalized_visual_mode(visual_mode)
    internal_name = _master_internal_name(
        model,
        height_m=height_m,
        symbol_size_mm=symbol_size_mm,
        visual_mode=visual_mode,
    )
    master = doc.getObject(internal_name)
    if master is None:
        master = doc.addObject("Part::Feature", internal_name)
        master.Label = "MASTER_EVAP_{0}".format(model)
    if hasattr(master, "PropertiesList"):
        if "MEPType" not in master.PropertiesList:
            master.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
        if str(getattr(master, "MEPType", "")) != MASTER_MEP_TYPE:
            master.MEPType = MASTER_MEP_TYPE
        if "Model" not in master.PropertiesList:
            master.addProperty("App::PropertyString", "Model", "HVAC Equipment", "Concrete evaporator model")
        if str(getattr(master, "Model", "")) != model:
            master.Model = model
        if "Height" not in master.PropertiesList:
            master.addProperty("App::PropertyFloat", "Height", "HVAC Equipment", "Mounting height (m)")
        if abs(_to_float(getattr(master, "Height", 0.0), 0.0) - height_m) > 0.0001:
            master.Height = height_m
        if "Symbol2DSize" not in master.PropertiesList:
            master.addProperty("App::PropertyFloat", "Symbol2DSize", "HVAC Equipment", "2D symbol size (mm)")
        if abs(_to_float(getattr(master, "Symbol2DSize", 0.0), 0.0) - symbol_size_mm) > 0.01:
            master.Symbol2DSize = symbol_size_mm
        if "ShapeSignature" not in master.PropertiesList:
            master.addProperty("App::PropertyString", "ShapeSignature", "HVAC Equipment", "Internal shape signature")
        if "HVACVisualMode" not in master.PropertiesList:
            master.addProperty("App::PropertyString", "HVACVisualMode", "HVAC Equipment", "Visual representation mode")
        if str(getattr(master, "HVACVisualMode", "") or "") != visual_mode:
            master.HVACVisualMode = visual_mode

    expected_signature = _master_shape_signature(
        model,
        height_m,
        symbol_size_mm,
        visual_mode=visual_mode,
    )
    current_signature = ""
    try:
        current_signature = str(getattr(master, "ShapeSignature", "") or "")
    except Exception:
        current_signature = ""
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
        shape_expected = _build_compound_shape(
            doc,
            model,
            height_m,
            symbol_size_mm,
            visual_mode=visual_mode,
        )
    else:
        shape_expected = None

    try:
        if needs_rebuild and shape_expected is not None:
            master.Shape = shape_expected
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


def _build_equipment_shape(equipment_obj):
    doc = getattr(equipment_obj, "Document", None)
    model = str(getattr(equipment_obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    return _build_compound_shape(
        doc,
        model,
        _height_value_m(equipment_obj),
        _symbol_size_mm(equipment_obj),
        visual_mode=_visual_mode_value(equipment_obj),
    )


def _is_evaporator_like_name(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    return raw.startswith("hvac_evaporator") or raw.startswith("evap_") or raw.startswith("cielo_")


def find_equipments(doc=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return []
    equipments = []
    seen = set()
    for obj in list(getattr(doc, "Objects", []) or []):
        obj_name = str(getattr(obj, "Name", "") or "")
        if obj_name in seen:
            continue

        try:
            props = list(getattr(obj, "PropertiesList", []) or [])
        except Exception:
            props = []

        try:
            if "MEPType" in props and str(getattr(obj, "MEPType", "") or "") == MEP_TYPE:
                equipments.append(obj)
                continue
        except Exception:
            pass

        try:
            type_id = str(getattr(obj, "TypeId", "") or "")
        except Exception:
            type_id = ""
        try:
            name = str(getattr(obj, "Name", "") or "")
        except Exception:
            name = ""
        try:
            label = str(getattr(obj, "Label", "") or "")
        except Exception:
            label = ""

        # Legacy fallback: include evaporator-like links even when MEPType is missing/corrupted.
        # Some broken objects lose custom properties, but keep EVAP_* names.
        if type_id == "App::Link" and (_is_evaporator_like_name(name) or _is_evaporator_like_name(label)):
            equipments.append(obj)
            seen.add(obj_name)
            continue

        # Include evaporator-like objects even if they are no longer links.
        if _is_evaporator_like_name(name) or _is_evaporator_like_name(label):
            if not _is_master_equipment_obj(obj):
                equipments.append(obj)
                seen.add(obj_name)
                continue

        try:
            if "Model" in props and "CapacityBTU" in props and "Space" in props:
                equipments.append(obj)
                seen.add(obj_name)
                continue
        except Exception:
            pass
    return equipments


def _preclean_broken_evaporator_links(doc):
    """Remove obviously broken legacy evaporator links before full sanitize."""
    if doc is None:
        return 0

    removed = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if obj is None:
            continue

        try:
            if _is_master_equipment_obj(obj):
                continue
        except Exception:
            pass

        try:
            name = str(getattr(obj, "Name", "") or "")
        except Exception:
            name = ""
        try:
            label = str(getattr(obj, "Label", "") or "")
        except Exception:
            label = ""
        try:
            type_id = str(getattr(obj, "TypeId", "") or "")
        except Exception:
            type_id = ""

        if not (_is_evaporator_like_name(name) or _is_evaporator_like_name(label)):
            continue

        should_remove = False
        if type_id == "App::Link":
            try:
                if getattr(obj, "LinkedObject", None) is None:
                    should_remove = True
            except Exception as exc:
                if _is_access_violation(exc):
                    should_remove = True

        if not should_remove:
            try:
                _ = getattr(obj, "Shape", None)
            except Exception as exc:
                if _is_access_violation(exc):
                    should_remove = True

        if not should_remove:
            continue

        if _remove_broken_equipment(doc, obj, reason="broken evaporator link", context="preclean"):
            removed += 1

    if removed > 0:
        log("Preclean evaporadoras rotas aplicado: eliminadas={0}".format(removed))
    return removed


def _is_master_equipment_obj(obj):
    if obj is None:
        return False
    try:
        return (
            hasattr(obj, "PropertiesList")
            and "MEPType" in obj.PropertiesList
            and str(getattr(obj, "MEPType", "") or "") == MASTER_MEP_TYPE
        )
    except Exception:
        return False


def sanitize_all_equipments(doc=None):
    """Repair common broken-link states in HVAC evaporators after legacy migrations."""

    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    repaired = 0
    removed = _preclean_broken_evaporator_links(doc)
    for equipment_obj in list(find_equipments(doc) or []):
        if doc.getObject(_safe_obj_name(equipment_obj)) is None:
            continue
        try:
            ensure_equipment_properties(equipment_obj)
            _initialize_equipment_defaults(equipment_obj)
        except Exception as exc:
            if _is_access_violation(exc):
                if _remove_broken_equipment(doc, equipment_obj, reason=exc, context="sanitize_props"):
                    removed += 1
                continue
            log("Sanitize evaporadora omitida (props): {0} -> {1}".format(getattr(equipment_obj, "Name", "?"), exc))
            continue

        if not _is_link_equipment(equipment_obj):
            try:
                if _geometry_needs_sync(equipment_obj):
                    _sync_equipment_geometry(equipment_obj)
                    repaired += 1
            except Exception as exc:
                if _is_access_violation(exc):
                    if _remove_broken_equipment(doc, equipment_obj, reason=exc, context="sanitize_shape"):
                        removed += 1
                    continue
                log("Sanitize evaporadora omitida (shape): {0} -> {1}".format(getattr(equipment_obj, "Name", "?"), exc))
            continue

        model = str(getattr(equipment_obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
        expected_master = None
        try:
            expected_master = _ensure_master_equipment(
                doc,
                model,
                height_m=_height_value_m(equipment_obj),
                symbol_size_mm=_symbol_size_mm(equipment_obj),
                visual_mode=_visual_mode_value(equipment_obj),
            )
        except Exception as exc:
            if _is_access_violation(exc):
                if _remove_broken_equipment(doc, equipment_obj, reason=exc, context="sanitize_master"):
                    removed += 1
                continue
            log("Sanitize evaporadora omitida (master): {0} -> {1}".format(getattr(equipment_obj, "Name", "?"), exc))
            continue

        if expected_master is None:
            continue

        linked_ok = False
        try:
            current_link = getattr(equipment_obj, "LinkedObject", None)
            linked_ok = current_link is not None and current_link == expected_master and _is_master_equipment_obj(current_link)
        except Exception:
            linked_ok = False

        if linked_ok:
            try:
                _configure_link_for_transform(equipment_obj)
            except Exception as exc:
                if _is_access_violation(exc):
                    if _remove_broken_equipment(doc, equipment_obj, reason=exc, context="sanitize_linkcfg"):
                        removed += 1
                    continue
            continue

        try:
            equipment_obj.LinkedObject = expected_master
            _configure_link_for_transform(equipment_obj)
            _cleanup_legacy_symbol2d(equipment_obj)
            repaired += 1
            log("Sanitize evaporadora reparada: {0}".format(getattr(equipment_obj, "Name", "?")))
        except Exception as exc:
            if _is_access_violation(exc):
                if _remove_broken_equipment(doc, equipment_obj, reason=exc, context="sanitize_relink"):
                    removed += 1
                continue
            log("Sanitize evaporadora fallo en re-link: {0} -> {1}".format(getattr(equipment_obj, "Name", "?"), exc))
            continue

    if repaired > 0 or removed > 0:
        log("Sanitize evaporadoras aplicado: reparadas={0}, eliminadas={1}".format(repaired, removed))
    return repaired + removed


def _space_from_selection(doc):
    selected = selection.get_selected_objects(resolve_links=True)
    non_space_markers = {
        MEP_TYPE,
        "HVACCondenser",
        "HVACRoute",
        "HVACPort",
        "HVACLabel",
        "HVACProject",
        "HVACRootGroup",
        "HVACSpacesGroup",
        "HVACEquipmentsGroup",
        "HVACLabelGroup",
        "HVACInternalGroup",
    }
    known_spaces = list(hvac_space.find_spaces(doc))
    for obj in selected:
        if obj is None:
            continue
        props = list(getattr(obj, "PropertiesList", []) or [])
        mep_type = ""
        if "MEPType" in props:
            try:
                mep_type = str(getattr(obj, "MEPType", "") or "")
            except Exception:
                mep_type = ""
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == hvac_space.MEP_TYPE:
            return obj
        if mep_type in non_space_markers:
            continue
        if "Space" in props:
            linked_space = getattr(obj, "Space", None)
            if linked_space is not None and str(getattr(linked_space, "MEPType", "") or "") == hvac_space.MEP_TYPE:
                return linked_space
        for space in known_spaces:
            if getattr(space, "BaseSpace", None) == obj:
                return space
    return None


def _dedupe_objects_by_name(objects):
    unique = []
    seen = set()
    for obj in list(objects or []):
        if obj is None:
            continue
        key = str(getattr(obj, "Name", "") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(obj)
    return unique


def _selected_spaces(doc):
    selected = selection.get_selected_objects(resolve_links=True)
    spaces = []
    known_spaces = list(hvac_space.find_spaces(doc))
    for obj in selected:
        if obj is None:
            continue
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == hvac_space.MEP_TYPE:
            spaces.append(obj)
            continue
        if hasattr(obj, "PropertiesList") and "Space" in obj.PropertiesList:
            linked = getattr(obj, "Space", None)
            if linked is not None:
                spaces.append(linked)
                continue
        for space in known_spaces:
            if getattr(space, "BaseSpace", None) == obj:
                spaces.append(space)
                break
    return _dedupe_objects_by_name(spaces)


def _selected_equipments(doc):
    picked = []
    for obj in selection.get_selected_objects(resolve_links=True):
        if obj is None:
            continue
        if hasattr(obj, "PropertiesList") and "MEPType" in obj.PropertiesList and str(obj.MEPType) == MEP_TYPE:
            picked.append(obj)
    return _dedupe_objects_by_name(picked)


def _space_from_position(doc, point):
    if point is None:
        return None
    spaces = list(hvac_space.find_spaces(doc))

    def _collect_candidates(tol):
        rows = []
        for space in spaces:
            try:
                if not hvac_space.space_contains_point(space, point, tol=float(tol)):
                    continue
            except Exception:
                continue

            area = _to_float(getattr(space, "Area", 0.0), 0.0)
            if area <= 0.0:
                base = getattr(space, "BaseSpace", None)
                detected = hvac_space.detect_area_from_base(base)
                if detected is not None:
                    area = _to_float(detected, 0.0)
            if area <= 0.0:
                area = 10**12

            center = _space_center_point(space)
            if center is None:
                dist2 = 10**18
            else:
                dx = float(point.x) - float(center.x)
                dy = float(point.y) - float(center.y)
                dist2 = dx * dx + dy * dy
            rows.append((float(dist2), float(area), space))
        return rows

    # Pass 1: strict interior check to avoid ambiguity when rooms share boundaries.
    strict_candidates = _collect_candidates(tol=0.5)
    if strict_candidates:
        strict_candidates.sort(key=lambda row: (row[0], row[1]))
        return strict_candidates[0][2]

    # Pass 2: relaxed tolerance for nearly-on-boundary points.
    relaxed_candidates = _collect_candidates(tol=8.0)
    if relaxed_candidates:
        relaxed_candidates.sort(key=lambda row: (row[0], row[1]))
        return relaxed_candidates[0][2]

    # Legacy fallback for unexpected shapes.
    for space in spaces:
        base = getattr(space, "BaseSpace", None)
        if base is None or not hasattr(base, "Shape"):
            continue
        try:
            if base.Shape.BoundBox.isInside(point):
                return space
        except Exception:
            continue
    return None


def _space_center_point(space_obj):
    if space_obj is None:
        return None
    base = getattr(space_obj, "BaseSpace", None)
    if base is None or not hasattr(base, "Shape"):
        return None
    try:
        bbox = base.Shape.BoundBox
        return App.Vector(float(bbox.Center.x), float(bbox.Center.y), float(bbox.ZMin))
    except Exception:
        return None


def _fallback_space_for_insert(doc=None):
    """Pick a deterministic visible HVAC space when insertion has no selection."""
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return None
    spaces = list(hvac_space.find_spaces(doc) or [])
    rows = []
    for space_obj in spaces:
        center = _space_center_point(space_obj)
        if center is None:
            continue
        area = _to_float(getattr(space_obj, "Area", 0.0), 0.0)
        if area <= 0.0:
            try:
                area = _to_float(hvac_space.detect_area_from_base(getattr(space_obj, "BaseSpace", None)), 0.0)
            except Exception:
                area = 0.0
        rows.append((float(area), str(getattr(space_obj, "Name", "") or ""), space_obj))
    if not rows:
        return None
    rows.sort(key=lambda row: (-row[0], row[1]))
    return rows[0][2]


def _equipment_needs_plan_fallback(equipment_obj):
    if equipment_obj is None:
        return False
    try:
        if getattr(equipment_obj, "Space", None) is not None:
            return False
    except Exception:
        pass
    try:
        base = _get_equipment_base(equipment_obj)
    except Exception:
        return False
    return abs(float(base.x)) <= 0.01 and abs(float(base.y)) <= 0.01


def _place_equipment_on_fallback_space(equipment_obj, reason=""):
    doc = getattr(equipment_obj, "Document", None)
    fallback_space = _fallback_space_for_insert(doc)
    if fallback_space is None:
        return False
    placed = _apply_insert_mount_logic(
        equipment_obj,
        selected_space=fallback_space,
        selected_point=_space_center_point(fallback_space),
    )
    if placed is None:
        return False
    try:
        equipment_obj.Space = fallback_space
    except Exception:
        pass
    suffix = " ({0})".format(reason) if reason else ""
    log(
        "Evaporadora ubicada en recinto fallback{0}: {1}".format(
            suffix,
            str(getattr(fallback_space, "Name", "") or getattr(fallback_space, "Label", "") or "?"),
        )
    )
    return True


def _space_bbox(space_obj):
    if space_obj is None:
        return None
    base = getattr(space_obj, "BaseSpace", None)
    if base is None or not hasattr(base, "Shape"):
        return None
    try:
        return base.Shape.BoundBox
    except Exception:
        return None


def _space_floor_z(space_obj, fallback=0.0):
    bbox = _space_bbox(space_obj)
    if bbox is None:
        return float(fallback)
    try:
        return float(bbox.ZMin)
    except Exception:
        return float(fallback)


def _space_height_mm(space_obj, fallback_mm=2600.0):
    if space_obj is not None:
        try:
            h_m = _to_float(getattr(space_obj, "Height", 0.0), 0.0)
            if h_m > 0.0:
                return float(h_m) * 1000.0
        except Exception:
            pass
    bbox = _space_bbox(space_obj)
    if bbox is not None:
        try:
            z_len = float(bbox.ZLength)
            if z_len > 0.1:
                return z_len
        except Exception:
            pass
    return float(fallback_mm)


def _space_ceiling_z(space_obj, floor_z=0.0):
    return float(floor_z) + _space_height_mm(space_obj)


def _get_equipment_base(equipment_obj):
    if equipment_obj is None:
        return App.Vector(0.0, 0.0, 0.0)
    try:
        return App.Vector(getattr(equipment_obj, "Placement", App.Placement()).Base)
    except Exception:
        return App.Vector(0.0, 0.0, 0.0)


def _set_equipment_base(equipment_obj, base_vec):
    _set_equipment_placement(equipment_obj, base_vec=base_vec)


def _set_equipment_placement(equipment_obj, base_vec=None, rotation=None):
    if equipment_obj is None:
        return
    current = getattr(equipment_obj, "Placement", App.Placement())
    target = App.Vector(base_vec if base_vec is not None else current.Base)
    target_rot = rotation if rotation is not None else current.Rotation

    # ElectricCR-style behavior: keep runtime transform in Placement.
    placement = getattr(equipment_obj, "Placement", App.Placement())
    placement.Base = target
    if rotation is not None:
        placement.Rotation = target_rot
    equipment_obj.Placement = placement


def _wall_mount_point_and_rotation(space_obj, equipment_obj, preferred_point=None):
    bbox = _space_bbox(space_obj)
    if bbox is None:
        return None, None

    room_w = max(1.0, float(bbox.XLength))
    room_d = max(1.0, float(bbox.YLength))
    _sx, sy, _sz = _equipment_size(equipment_obj)
    half_depth = max(20.0, float(sy) * 0.5)
    safe_depth = min(half_depth, max(20.0, min(room_w, room_d) * 0.45))

    anchor = App.Vector(float(bbox.Center.x), float(bbox.Center.y), float(bbox.ZMin))
    if preferred_point is not None:
        try:
            anchor = App.Vector(preferred_point)
        except Exception:
            pass

    side_distance = [
        ("xmin", abs(float(anchor.x) - float(bbox.XMin))),
        ("xmax", abs(float(anchor.x) - float(bbox.XMax))),
        ("ymin", abs(float(anchor.y) - float(bbox.YMin))),
        ("ymax", abs(float(anchor.y) - float(bbox.YMax))),
    ]
    side = sorted(side_distance, key=lambda item: item[1])[0][0]
    floor_z = float(bbox.ZMin)

    x_in_min = float(bbox.XMin) + safe_depth
    x_in_max = float(bbox.XMax) - safe_depth
    y_in_min = float(bbox.YMin) + safe_depth
    y_in_max = float(bbox.YMax) - safe_depth

    if x_in_min > x_in_max:
        x_in_min = x_in_max = float(bbox.Center.x)
    if y_in_min > y_in_max:
        y_in_min = y_in_max = float(bbox.Center.y)

    if side == "xmin":
        point = App.Vector(x_in_min, _clamp(anchor.y, y_in_min, y_in_max), floor_z)
        inward = App.Vector(1.0, 0.0, 0.0)
    elif side == "xmax":
        point = App.Vector(x_in_max, _clamp(anchor.y, y_in_min, y_in_max), floor_z)
        inward = App.Vector(-1.0, 0.0, 0.0)
    elif side == "ymin":
        point = App.Vector(_clamp(anchor.x, x_in_min, x_in_max), y_in_min, floor_z)
        inward = App.Vector(0.0, 1.0, 0.0)
    else:
        point = App.Vector(_clamp(anchor.x, x_in_min, x_in_max), y_in_max, floor_z)
        inward = App.Vector(0.0, -1.0, 0.0)

    try:
        rotation = App.Rotation(App.Vector(0.0, 1.0, 0.0), inward)
    except Exception:
        rotation = App.Rotation()
    return point, rotation


def _ceiling_mount_height_m(space_obj, equipment_obj, base_z=0.0):
    _sx, _sy, sz = _equipment_size(equipment_obj)
    ceiling_z = _space_ceiling_z(space_obj, floor_z=base_z)
    height_mm = max(0.0, float(ceiling_z) - float(base_z) - float(sz))
    return float(height_mm) / 1000.0


def _apply_insert_mount_logic(equipment_obj, selected_space=None, selected_point=None):
    if equipment_obj is None:
        return None

    eq_type = str(getattr(equipment_obj, "Type", "Wall") or "Wall")
    point = None
    rotation = None
    src_point = None
    if selected_point is not None:
        try:
            src_point = App.Vector(selected_point)
        except Exception:
            src_point = None

    mount_space = selected_space
    if mount_space is None and src_point is not None:
        try:
            mount_space = _space_from_position(getattr(equipment_obj, "Document", None), src_point)
        except Exception:
            mount_space = None

    if eq_type == "Wall":
        if mount_space is not None:
            point, rotation = _wall_mount_point_and_rotation(mount_space, equipment_obj, preferred_point=src_point)
            if point is not None:
                log("Evaporadora de pared orientada perpendicular hacia adentro del recinto")
        if point is None and src_point is not None:
            point = App.Vector(src_point)

    elif eq_type == "FloorCeiling":
        if mount_space is not None:
            point, rotation = _wall_mount_point_and_rotation(mount_space, equipment_obj, preferred_point=src_point)
            if point is not None:
                log("Evaporadora piso-cielo orientada perpendicular hacia adentro del recinto")
        if point is None and src_point is not None:
            point = App.Vector(src_point)

    elif eq_type == "Cassette":
        if src_point is not None:
            point = App.Vector(src_point)
        elif selected_space is not None:
            point = _space_center_point(selected_space)
            if point is not None:
                log("Cassette ubicado en centro de recinto (regla luminaria)")
        if point is not None and selected_space is not None:
            floor_z = _space_floor_z(selected_space, fallback=point.z)
            point.z = floor_z
            mount_h = _ceiling_mount_height_m(selected_space, equipment_obj, base_z=floor_z)
            equipment_obj.Height = mount_h
            log("Cassette ajustado al cielo del recinto")

    else:  # Duct
        if src_point is not None:
            point = App.Vector(src_point)
            if selected_space is not None:
                floor_z = _space_floor_z(selected_space, fallback=point.z)
                point.z = floor_z
                equipment_obj.Height = _ceiling_mount_height_m(selected_space, equipment_obj, base_z=floor_z)
                log("Ducto ubicado en punto seleccionado y ajustado al cielo del recinto")
            else:
                log("Ducto ubicado en punto seleccionado")
        elif selected_space is not None:
            point = _space_center_point(selected_space)
            if point is not None:
                floor_z = _space_floor_z(selected_space, fallback=point.z)
                point.z = floor_z
                equipment_obj.Height = _ceiling_mount_height_m(selected_space, equipment_obj, base_z=floor_z)
                log("Ducto ubicado en techo de recinto seleccionado")

    if point is None and selected_space is not None:
        point = _space_center_point(selected_space)

    if point is None:
        return None

    equipment_obj.BaseLevel = float(point.z)
    _set_equipment_placement(equipment_obj, base_vec=point, rotation=rotation)
    return point


def _link_transform_enabled(link_obj):
    if link_obj is None or not _is_link_equipment(link_obj):
        return False
    try:
        return bool(getattr(link_obj, "LinkTransform", False))
    except Exception:
        return False


def detect_space_for_equipment(equipment_obj):
    if equipment_obj is None:
        return None
    doc = equipment_obj.Document

    point = _get_equipment_base(equipment_obj)
    space = _space_from_position(doc, point)
    if space is not None:
        return space

    spaces = hvac_space.find_spaces(doc)
    eq_type = str(getattr(equipment_obj, "Type", "Wall") or "Wall")
    if len(spaces) == 1 and eq_type != "Duct":
        return spaces[0]
    return None


def update_equipment_coverage(equipment_obj):
    if equipment_obj is None:
        return 0.0
    load = 0.0
    try:
        linked_space = getattr(equipment_obj, "Space", None)
    except Exception:
        linked_space = None
    if linked_space is not None:
        try:
            load = _to_float(getattr(linked_space, "CoolingLoadBTU", 0.0), 0.0)
        except Exception:
            load = 0.0
    capacity = _to_float(equipment_obj.CapacityBTU, 0.0)
    if load > 0:
        equipment_obj.CoveragePct = round((capacity / load) * 100.0, 2)
    else:
        equipment_obj.CoveragePct = 0.0
    return equipment_obj.CoveragePct


def update_equipment_ports(equipment_obj):
    if equipment_obj is None:
        return []
    if not bool(getattr(equipment_obj, "UsePorts", False)):
        return list(getattr(equipment_obj, "Ports", []) or [])
    hvac_ports.update_equipment_ports(equipment_obj)


def _equipment_shape_changed(equipment_obj, tol=0.1):
    try:
        expected = _build_equipment_shape(equipment_obj)
        if expected is None or expected.isNull():
            return False
        shape_obj = getattr(equipment_obj, "Shape", None)
        if shape_obj is None or shape_obj.isNull():
            return True
        return not _bbox_size_nearly_equal(shape_obj, expected, tol=tol)
    except Exception:
        return True


def _master_link_changed(equipment_obj):
    if not _is_link_equipment(equipment_obj):
        return False
    expected_master = _ensure_master_equipment(
        equipment_obj.Document,
        getattr(equipment_obj, "Model", DEFAULT_MODEL),
        height_m=_height_value_m(equipment_obj),
        symbol_size_mm=_symbol_size_mm(equipment_obj),
        visual_mode=_visual_mode_value(equipment_obj),
    )
    if expected_master is None:
        return False
    return getattr(equipment_obj, "LinkedObject", None) != expected_master


def _geometry_needs_sync(equipment_obj):
    if equipment_obj is None:
        return False
    if _is_link_equipment(equipment_obj):
        if not _link_transform_enabled(equipment_obj):
            return True
        if _master_link_changed(equipment_obj):
            return True
    else:
        if _equipment_shape_changed(equipment_obj):
            return True

    base = _get_equipment_base(equipment_obj)
    target_z = _to_float(getattr(equipment_obj, "BaseLevel", 0.0), 0.0)
    if abs(float(base.z) - float(target_z)) > 0.01:
        return True
    return False


def _apply_equipment_elevation(equipment_obj):
    if equipment_obj is None:
        return
    base = _get_equipment_base(equipment_obj)
    base_level = _to_float(getattr(equipment_obj, "BaseLevel", 0.0), 0.0)
    target_z = base_level
    if abs(base.z - target_z) > 0.01:
        base.z = target_z
        _set_equipment_base(equipment_obj, base)


def _configure_link_for_transform(link_obj, reset_link_placement=False):
    if link_obj is None or not _is_link_equipment(link_obj):
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
    if reset_link_placement:
        try:
            if hasattr(link_obj, "LinkPlacement"):
                link_obj.LinkPlacement = App.Placement()
        except Exception:
            pass
    try:
        if hasattr(link_obj, "ViewObject") and link_obj.ViewObject is not None:
            if hasattr(link_obj.ViewObject, "Selectable"):
                link_obj.ViewObject.Selectable = True
    except Exception:
        pass


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
    label_upper = label.upper()
    # Important: do not match condenser symbols here.
    # Condenser labels typically include "HVAC_2D_COND_*".
    return (
        name.startswith("HVAC_Evap2D")
        or label.startswith("HVAC_2D_EVAP_")
        or (label.startswith("HVAC_2D_") and "_COND_" not in label_upper)
    )


def _ensure_symbol2d_properties(symbol_obj, equipment_obj=None):
    if symbol_obj is None:
        return
    try:
        if "MEPType" not in symbol_obj.PropertiesList:
            symbol_obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
        if str(getattr(symbol_obj, "MEPType", "") or "") != SYMBOL2D_MEP_TYPE:
            symbol_obj.MEPType = SYMBOL2D_MEP_TYPE
        # Avoid document dependency cycles (DAG) by ensuring there is no back link
        # from the 2D symbol to the parent 3D equipment.
        if "ParentEquipment" in symbol_obj.PropertiesList:
            try:
                if getattr(symbol_obj, "ParentEquipment", None) is not None:
                    symbol_obj.ParentEquipment = None
            except Exception:
                pass
        if "VisualMode" not in symbol_obj.PropertiesList:
            symbol_obj.addProperty("App::PropertyEnumeration", "VisualMode", "HVAC Equipment", "View mode controller")
        try:
            symbol_obj.VisualMode = list(VISUAL_MODE_OPTIONS)
        except Exception:
            pass
        if equipment_obj is not None:
            target_mode = _visual_mode_value(equipment_obj)
            try:
                symbol_obj.VisualMode = target_mode
            except Exception:
                pass
        if "EquipmentName" not in symbol_obj.PropertiesList:
            symbol_obj.addProperty("App::PropertyString", "EquipmentName", "HVAC Equipment", "Parent equipment name")
        if equipment_obj is not None:
            symbol_obj.EquipmentName = str(getattr(equipment_obj, "Label", "") or getattr(equipment_obj, "Name", "") or "")
    except Exception:
        pass


def _ensure_symbol2d_object(equipment_obj):
    if equipment_obj is None:
        return None
    doc = getattr(equipment_obj, "Document", None)
    if doc is None:
        return None
    if "Symbol2D" not in getattr(equipment_obj, "PropertiesList", []):
        return None

    symbol_obj = getattr(equipment_obj, "Symbol2D", None)
    if symbol_obj is not None:
        try:
            if doc.getObject(str(getattr(symbol_obj, "Name", "") or "")) is None:
                symbol_obj = None
        except Exception:
            symbol_obj = None

    if symbol_obj is not None and not _is_symbol2d_obj(symbol_obj):
        legacy_name = str(getattr(symbol_obj, "Name", "") or "")
        if legacy_name and (legacy_name.startswith("HVAC_Evaporator2D") or legacy_name.startswith("SYM2D_")):
            try:
                if doc.getObject(legacy_name) is not None:
                    doc.removeObject(legacy_name)
            except Exception:
                pass
        symbol_obj = None
        try:
            equipment_obj.Symbol2D = None
        except Exception:
            pass

    if symbol_obj is None:
        try:
            symbol_obj = doc.addObject("Part::Feature", "HVAC_Evap2D")
        except Exception:
            return None
        try:
            equipment_obj.Symbol2D = symbol_obj
        except Exception:
            pass
    _ensure_symbol2d_properties(symbol_obj, equipment_obj=equipment_obj)
    try:
        base_label = str(getattr(equipment_obj, "Label", "") or getattr(equipment_obj, "Name", "") or "EVAP")
        symbol_obj.Label = "HVAC_2D_EVAP_{0}".format(base_label)
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
    for equipment_obj in list(find_equipments(doc) or []):
        if equipment_obj is None:
            continue
        try:
            if "Symbol2D" not in getattr(equipment_obj, "PropertiesList", []):
                continue
            symbol_obj = getattr(equipment_obj, "Symbol2D", None)
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
        log("Limpieza simbolos 2D evaporadora: huerfanos_eliminados={0}".format(removed))
    return removed


def _cleanup_legacy_symbol2d(equipment_obj):
    doc = getattr(equipment_obj, "Document", None)
    if doc is None:
        return 0
    return _cleanup_orphan_symbol2d_objects(doc)


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
    if label.startswith("HVAC_INFO2D_COND_"):
        return False
    return name.startswith("HVAC_EvapInfo2D") or label.startswith("HVAC_INFO2D_")


def _is_probable_info2d_draft_text(obj):
    if obj is None:
        return False
    type_id = str(getattr(obj, "TypeId", "") or "")
    if "Draft" not in type_id or "Text" not in type_id:
        return False
    try:
        lines = _extract_text_lines(obj)
    except Exception:
        return False
    if not lines:
        return False
    joined = "\n".join(str(v or "").lower() for v in lines)
    is_field_style = ("sistema:" in joined) and ("capacidad:" in joined) and ("unidad:" in joined)
    is_plan_style = ("evaporadora" in joined) and ("sistema" in joined) and ("btu/h" in joined)
    return bool(is_field_style or is_plan_style)


def _is_condenser_info2d_obj(obj):
    if obj is None:
        return False
    try:
        props = list(getattr(obj, "PropertiesList", []) or [])
    except Exception:
        props = []
    try:
        mep = str(getattr(obj, "MEPType", "") or "")
    except Exception:
        mep = ""
    if mep == "HVACCondenserInfo2D":
        return True
    if "CondenserName" in props:
        return True
    name = str(getattr(obj, "Name", "") or "")
    label = str(getattr(obj, "Label", "") or "")
    if name.startswith("HVAC_CondInfo2D") or label.startswith("HVAC_INFO2D_COND_"):
        return True
    try:
        lines = _extract_text_lines(obj)
    except Exception:
        lines = []
    if lines:
        joined = "\n".join(str(v or "").upper() for v in lines)
        if "CONDENSADORA" in joined:
            return True
    return False


def _is_draft_text_obj(obj):
    if obj is None:
        return False
    type_id = str(getattr(obj, "TypeId", "") or "")
    if "Annotation" in type_id:
        return False
    if ("Draft" in type_id and "Text" in type_id) or type_id == "Part::Part2DObjectPython":
        return True
    try:
        import Draft

        if hasattr(Draft, "getType"):
            dtype = str(Draft.getType(obj) or "")
            if dtype.strip().lower() == "text" and "Annotation" not in type_id:
                return True
    except Exception:
        pass
    try:
        props = list(getattr(obj, "PropertiesList", []) or [])
    except Exception:
        props = []
    if "Text" in props and "Placement" in props and "LabelText" not in props:
        return True
    return False


def _extract_text_lines(text_obj):
    if text_obj is None:
        return []
    props = list(getattr(text_obj, "PropertiesList", []) or [])
    raw = None
    for key in ("Text", "LabelText", "Strings"):
        if key in props:
            try:
                raw = getattr(text_obj, key, None)
                break
            except Exception:
                raw = None
    if raw is None and "String" in props:
        try:
            raw = getattr(text_obj, "String", "")
        except Exception:
            raw = ""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(v or "") for v in raw]
    return str(raw or "").splitlines()


def _is_legacy_info2d_text_obj(obj):
    if obj is None:
        return False
    if _is_info2d_obj(obj):
        return True
    try:
        lines = [str(v).strip().lower() for v in _extract_text_lines(obj) if str(v).strip()]
    except Exception:
        lines = []
    if not lines:
        return False
    has_sistema = any(("sistema:" in line) or ("sistema " in line) for line in lines)
    has_capacidad = any(("capacidad:" in line and "btu/h" in line) or ("btu/h" in line) for line in lines)
    has_unidad = any(("unidad:" in line) or ("evaporadora" in line and "tipo" in line) for line in lines)
    return bool(has_sistema and has_capacidad and has_unidad)


def _set_text_lines(text_obj, lines):
    if text_obj is None:
        return
    values = list(lines or [])
    try:
        props = list(getattr(text_obj, "PropertiesList", []) or [])
        if "Text" in props:
            text_obj.Text = values
        elif "LabelText" in props:
            text_obj.LabelText = values
        elif "Strings" in props:
            text_obj.Strings = values
        elif "String" in props:
            text_obj.String = "\n".join(values)
    except Exception:
        pass


def _set_text_point(text_obj, point):
    if text_obj is None:
        return
    target = App.Vector(point)
    try:
        props = list(getattr(text_obj, "PropertiesList", []) or [])
    except Exception:
        props = []
    try:
        if "BasePosition" in props:
            text_obj.BasePosition = target
            return
    except Exception:
        pass
    try:
        if "Position" in props:
            text_obj.Position = target
            return
    except Exception:
        pass
    try:
        if hasattr(text_obj, "Placement"):
            placement = text_obj.Placement
            placement.Base = target
            text_obj.Placement = placement
    except Exception:
        pass


def _set_text_size(text_obj, size):
    value = _normalized_info2d_size(size)
    for prop_name in ("FontSize", "Size", "TextSize"):
        try:
            props = list(getattr(text_obj, "PropertiesList", []) or [])
            if prop_name in props:
                setattr(text_obj, prop_name, value)
        except Exception:
            continue
    vobj = getattr(text_obj, "ViewObject", None)
    if vobj is not None:
        for prop_name in ("FontSize", "TextSize", "PointSize"):
            try:
                if hasattr(vobj, prop_name):
                    setattr(vobj, prop_name, value)
            except Exception:
                continue


def _set_text_visibility(text_obj, visible):
    if text_obj is None:
        return
    try:
        vobj = getattr(text_obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = bool(visible)
    except Exception:
        pass


def _enum_values(target_obj, prop_name):
    if target_obj is None:
        return []
    try:
        if hasattr(target_obj, "getEnumerationsOfProperty"):
            values = target_obj.getEnumerationsOfProperty(prop_name)
            if isinstance(values, (list, tuple)):
                return [str(v) for v in values if str(v).strip()]
    except Exception:
        pass
    try:
        value = getattr(target_obj, prop_name, None)
        if hasattr(value, "values"):
            return [str(v) for v in list(value.values) if str(v).strip()]
    except Exception:
        pass
    return []


def _normalize_token(value):
    raw = str(value or "")
    return "".join(ch for ch in raw.lower() if ch.isalnum())


def _pick_center_value(options):
    if not options:
        return "Center"
    normalized = [(opt, _normalize_token(opt)) for opt in options]
    middle_center_tokens = {
        "center",
        "centre",
        "middlecenter",
        "centermiddle",
        "middle",
        "centro",
        "centrado",
    }
    for original, key in normalized:
        if key in middle_center_tokens:
            return original
    for original, key in normalized:
        if "center" in key or "centre" in key or "centr" in key or "middle" in key:
            return original
    return options[0]


def _set_center_justification(target_obj):
    if target_obj is None:
        return
    for prop_name in ("Justification", "TextAlign", "HorizontalAlignment"):
        has_prop = False
        try:
            props = list(getattr(target_obj, "PropertiesList", []) or [])
            if prop_name in props:
                has_prop = True
        except Exception:
            pass
        if not has_prop and hasattr(target_obj, prop_name):
            has_prop = True
        if not has_prop:
            continue
        preferred = _pick_center_value(_enum_values(target_obj, prop_name))
        try:
            setattr(target_obj, prop_name, preferred)
        except Exception:
            try:
                setattr(target_obj, prop_name, "Center")
            except Exception:
                pass


def _set_text_centered(text_obj):
    if text_obj is None:
        return
    _set_center_justification(text_obj)
    try:
        _set_center_justification(getattr(text_obj, "ViewObject", None))
    except Exception:
        pass


def _text_has_center_alignment(text_obj):
    if text_obj is None:
        return False
    for target in (text_obj, getattr(text_obj, "ViewObject", None)):
        if target is None:
            continue
        for prop_name in ("Justification", "TextAlign", "HorizontalAlignment"):
            try:
                has_prop = False
                props = list(getattr(target, "PropertiesList", []) or [])
                if prop_name in props or hasattr(target, prop_name):
                    has_prop = True
                if not has_prop:
                    continue
                token = _normalize_token(getattr(target, prop_name, ""))
                if "center" in token or "centre" in token or "centr" in token or "middle" in token:
                    return True
            except Exception:
                continue
    return False


def _is_annotation_text_obj(text_obj):
    if text_obj is None:
        return False
    type_id = str(getattr(text_obj, "TypeId", "") or "")
    if "Annotation" in type_id:
        return True
    name = str(getattr(text_obj, "Name", "") or "")
    return name.startswith("HVAC_EvapInfo2D") and "Annotation" in type_id


def _estimate_text_block_mm(lines, text_size):
    values = [str(v or "") for v in list(lines or [])]
    if not values:
        values = [""]
    longest = max(len(v) for v in values)
    size = _normalized_info2d_size(text_size)
    width = max(120.0, float(longest) * size * 0.56)
    height = max(size, float(len(values)) * size * 1.25)
    return width, height


def _shape_boundbox_local(obj):
    if obj is None:
        return None
    try:
        shape = getattr(obj, "Shape", None)
    except Exception:
        shape = None
    if shape is None:
        return None
    try:
        bbox = shape.BoundBox
    except Exception:
        return None
    try:
        if bool(getattr(bbox, "isValid", lambda: True)()):
            return bbox
    except Exception:
        pass
    try:
        if float(getattr(bbox, "XLength", 0.0)) > 0.0 or float(getattr(bbox, "YLength", 0.0)) > 0.0:
            return bbox
    except Exception:
        pass
    return None


def _world_point_from_base_obj(base_obj, point):
    if base_obj is None:
        return App.Vector(point)
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
        return App.Vector(point)
    try:
        return placement.multVec(App.Vector(point))
    except Exception:
        return App.Vector(point)


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


def _global_placement_of(base_obj):
    if base_obj is None:
        return App.Placement()
    try:
        if hasattr(base_obj, "getGlobalPlacement"):
            gp = base_obj.getGlobalPlacement()
            if gp is not None:
                return App.Placement(gp)
    except Exception:
        pass
    try:
        if hasattr(base_obj, "Placement"):
            return App.Placement(base_obj.Placement)
    except Exception:
        pass
    return App.Placement()


def _point_is_already_global(base_obj, bbox, point):
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


def _space_area_anchor_point(space_obj):
    if space_obj is None:
        return None
    base = getattr(space_obj, "BaseSpace", None)
    if base is not None and hasattr(base, "Shape"):
        try:
            shape = base.Shape
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
                    transformed = _world_point_from_base_obj(base, point)
                    if _point_is_already_global(base, shape.BoundBox, point):
                        return point
                    return transformed

            com = shape.CenterOfMass
            bbox = shape.BoundBox
            point = App.Vector(com.x, com.y, bbox.ZMin)
            transformed = _world_point_from_base_obj(base, point)
            if _point_is_already_global(base, bbox, point):
                return point
            return transformed
        except Exception:
            pass
    try:
        if hasattr(space_obj, "Placement"):
            p = App.Vector(space_obj.Placement.Base)
            return App.Vector(p.x, p.y, p.z)
    except Exception:
        pass
    return None


def _make_info2d_text(doc, lines, point):
    last_error = None
    try:
        import Draft

        creators = []
        if hasattr(Draft, "make_text"):
            creators.extend(
                [
                    lambda: Draft.make_text(list(lines), point=point),
                    lambda: Draft.make_text("\n".join(lines), point=point),
                    lambda: Draft.make_text(list(lines), point),
                    lambda: Draft.make_text("\n".join(lines), point),
                    lambda: Draft.make_text(list(lines)),
                    lambda: Draft.make_text("\n".join(lines)),
                ]
            )
        if hasattr(Draft, "makeText"):
            creators.extend(
                [
                    lambda: Draft.makeText(list(lines), point=point),
                    lambda: Draft.makeText("\n".join(lines), point=point),
                    lambda: Draft.makeText(list(lines), point),
                    lambda: Draft.makeText("\n".join(lines), point),
                    lambda: Draft.makeText(list(lines)),
                    lambda: Draft.makeText("\n".join(lines)),
                ]
            )
        for creator in creators:
            try:
                obj = creator()
                if obj is not None:
                    _set_text_point(obj, point)
                    if not _is_draft_text_obj(obj):
                        # Enforce Draft text only for 2D export reliability.
                        try:
                            bad_name = str(getattr(obj, "Name", "") or "")
                            if bad_name and doc.getObject(bad_name) is not None:
                                doc.removeObject(bad_name)
                        except Exception:
                            pass
                        continue
                    log("Etiqueta 2D creada como Draft: {0} ({1})".format(str(getattr(obj, "Name", "") or "?"), str(getattr(obj, "TypeId", "") or "?")))
                    return obj
            except Exception as exc:
                last_error = exc
    except Exception as exc:
        last_error = exc

    raise RuntimeError("No se pudo crear texto 2D HVAC Draft: {0}".format(last_error))


def _equipment_type_ui_name(equipment_obj):
    raw = str(getattr(equipment_obj, "Type", "Wall") or "Wall")
    return TYPE_INTERNAL_TO_UI.get(raw, raw)


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


def _build_info2d_lines(equipment_obj):
    system = str(getattr(equipment_obj, "SystemType", DEFAULT_SYSTEM_TYPE) or DEFAULT_SYSTEM_TYPE)
    if system not in SYSTEM_TYPE_OPTIONS:
        system = DEFAULT_SYSTEM_TYPE
    capacity = _format_btu_label(getattr(equipment_obj, "CapacityBTU", 0.0))
    unit_type = _labelize_token(_equipment_type_ui_name(equipment_obj))
    system_label = _labelize_token(system)
    return [
        "EVAPORADORA TIPO {0}".format(unit_type),
        "SISTEMA {0}".format(system_label),
        "{0} BTU/H".format(capacity),
    ]


def _ensure_info2d_properties(info_obj, equipment_obj=None):
    if info_obj is None:
        return
    try:
        props = list(getattr(info_obj, "PropertiesList", []) or [])
        if "MEPType" not in props:
            info_obj.addProperty("App::PropertyString", "MEPType", "MEP", "Internal MEP marker")
        if str(getattr(info_obj, "MEPType", "") or "") != INFO2D_MEP_TYPE:
            info_obj.MEPType = INFO2D_MEP_TYPE
        if "EquipmentName" not in props:
            info_obj.addProperty("App::PropertyString", "EquipmentName", "HVAC Equipment", "Parent equipment name")
        if equipment_obj is not None:
            info_obj.EquipmentName = str(
                getattr(equipment_obj, "Label", "")
                or getattr(equipment_obj, "Name", "")
                or ""
            )
    except Exception:
        pass


def _info2d_offset_local(equipment_obj):
    symbol_size = max(120.0, _symbol_size_mm(equipment_obj))
    text_size = _normalized_info2d_size(getattr(equipment_obj, "Info2DSize", DEFAULT_INFO2D_SIZE))
    clearance = max(140.0, symbol_size * 0.85, text_size * 1.4)
    # Front side convention for HVAC symbols/equipment is local +Y (room side).
    return App.Vector(0.0, clearance, 0.0)


def _info2d_point_for_equipment(equipment_obj, symbol_obj=None):
    if equipment_obj is None:
        return App.Vector(0.0, 0.0, 0.0)

    # Anchor on the 2D symbol when available; fallback to equipment.
    anchor_obj = symbol_obj if symbol_obj is not None else equipment_obj
    placement = _global_placement_of(anchor_obj)
    if (
        symbol_obj is not None
        and abs(float(getattr(placement.Base, "x", 0.0))) < 0.001
        and abs(float(getattr(placement.Base, "y", 0.0))) < 0.001
        and abs(float(getattr(placement.Base, "z", 0.0))) < 0.001
    ):
        placement = _global_placement_of(equipment_obj)
    try:
        base = App.Vector(placement.Base)
    except Exception:
        base = App.Vector(0.0, 0.0, 0.0)
    try:
        rot = App.Rotation(placement.Rotation)
    except Exception:
        rot = App.Rotation()

    local_anchor = _info2d_offset_local(equipment_obj)
    bbox = _shape_boundbox_local(symbol_obj) if symbol_obj is not None else None
    if bbox is None:
        bbox = _shape_boundbox_local(equipment_obj)

    lines = _build_info2d_lines(equipment_obj)
    text_size = _normalized_info2d_size(getattr(equipment_obj, "Info2DSize", DEFAULT_INFO2D_SIZE))
    text_w, text_h = _estimate_text_block_mm(lines, text_size)

    if bbox is not None:
        try:
            bbox_y = max(0.0, float(getattr(bbox, "YLength", 0.0)))
            front_extent = max(
                0.5 * bbox_y,
                max(80.0, _symbol_size_mm(equipment_obj) * 0.25),
            )
            margin = max(80.0, text_size * 0.8)
            text_push = max(text_h * 1.05, text_size * 2.4)
            local_anchor = App.Vector(
                0.0,
                front_extent + margin + text_push,
                float(getattr(local_anchor, "z", 0.0)),
            )
        except Exception:
            pass
    else:
        # Without bbox, still place text clearly in front of equipment.
        text_push = max(text_h * 1.05, text_size * 2.4)
        local_anchor = App.Vector(
            float(local_anchor.x),
            float(local_anchor.y) + max(80.0, text_push),
            float(local_anchor.z),
        )

    # Keep only a defensive correction for legacy annotation objects.
    info_obj = getattr(equipment_obj, "Info2D", None) if "Info2D" in getattr(equipment_obj, "PropertiesList", []) else None
    if _is_annotation_text_obj(info_obj) and not _text_has_center_alignment(info_obj):
        local_anchor = App.Vector(float(local_anchor.x) - (text_w * 0.5), float(local_anchor.y), float(local_anchor.z))

    return base + rot.multVec(local_anchor)


def _ensure_info2d_object(equipment_obj, symbol_obj=None):
    if equipment_obj is None:
        return None
    doc = getattr(equipment_obj, "Document", None)
    if doc is None:
        return None
    if "Info2D" not in getattr(equipment_obj, "PropertiesList", []):
        return None

    info_obj = getattr(equipment_obj, "Info2D", None)
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
            equipment_obj.Info2D = None
        except Exception:
            pass

    # Force migration to Draft Text so DXF export includes these labels consistently.
    if info_obj is not None and not _is_draft_text_obj(info_obj):
        old_name = str(getattr(info_obj, "Name", "") or "")
        old_type = str(getattr(info_obj, "TypeId", "") or "")
        log("Migrando Info2D a Draft: {0} ({1})".format(old_name or "?", old_type or "?"))
        info_obj = None
        try:
            equipment_obj.Info2D = None
        except Exception:
            pass
        try:
            if old_name and doc.getObject(old_name) is not None:
                doc.removeObject(old_name)
        except Exception:
            pass

    if info_obj is None:
        lines = _build_info2d_lines(equipment_obj)
        point = _info2d_point_for_equipment(equipment_obj, symbol_obj=symbol_obj)
        try:
            info_obj = _make_info2d_text(doc, lines, point)
        except Exception as exc:
            log("Texto 2D HVAC omitido: {0}".format(exc))
            return None
        try:
            equipment_obj.Info2D = info_obj
        except Exception:
            pass
    else:
        try:
            log("Info2D activo: {0} ({1})".format(str(getattr(info_obj, "Name", "") or "?"), str(getattr(info_obj, "TypeId", "") or "?")))
        except Exception:
            pass

    _ensure_info2d_properties(info_obj, equipment_obj=equipment_obj)
    try:
        base_label = str(getattr(equipment_obj, "Label", "") or getattr(equipment_obj, "Name", "") or "EVAP")
        info_obj.Label = "HVAC_INFO2D_{0}".format(base_label)
    except Exception:
        pass
    assigned_group = None
    try:
        assigned_group = hvac_project.add_object_to_hvac_group(doc, info_obj)
    except Exception as exc:
        if INFO2D_DEBUG_ENABLED:
            log(
                "Info2D route error evaporadora: equipo={0} info={1} error={2}".format(
                    _safe_obj_name(equipment_obj) or "?",
                    _safe_obj_name(info_obj) or "?",
                    _exc_text(exc) or exc,
                )
            )
    if INFO2D_DEBUG_ENABLED:
        group_name = str(getattr(assigned_group, "Name", "") or "") if assigned_group is not None else ""
        if not group_name:
            memberships = _group_memberships(info_obj)
            group_name = memberships[0] if memberships else "-"
        log(
            "Info2D route evaporadora: equipo={0} info={1} grupo={2}".format(
                _safe_obj_name(equipment_obj) or "?",
                _safe_obj_name(info_obj) or "?",
                group_name or "-",
            )
        )
    return info_obj


def _sync_info2d_for_equipment(equipment_obj, symbol_obj=None):
    if equipment_obj is None:
        return
    info_obj = _ensure_info2d_object(equipment_obj, symbol_obj=symbol_obj)
    if info_obj is None:
        return
    lines = _build_info2d_lines(equipment_obj)
    raw_size = _to_float(getattr(equipment_obj, "Info2DSize", DEFAULT_INFO2D_SIZE), DEFAULT_INFO2D_SIZE)
    effective_size = _normalized_info2d_size(raw_size)
    legacy_floor = max(MIN_INFO2D_SIZE, DEFAULT_INFO2D_SIZE * 0.45)
    if raw_size < legacy_floor:
        effective_size = DEFAULT_INFO2D_SIZE
        try:
            equipment_obj.Info2DSize = effective_size
        except Exception:
            pass
    _set_text_lines(info_obj, lines)
    _set_text_size(info_obj, effective_size)
    _set_text_centered(info_obj)
    info_point = _info2d_point_for_equipment(equipment_obj, symbol_obj=symbol_obj)
    _set_text_point(info_obj, info_point)
    mode = _visual_mode_value(equipment_obj)
    show_3d = mode in {"Ambos", "Solo3D"}
    show_2d = mode in {"Ambos", "Solo2D"}
    if mode == "Ninguno":
        show_3d = False
        show_2d = False
    show_info2d = bool(show_2d) and bool(getattr(equipment_obj, "ShowInfo2D", True))
    _set_text_visibility(info_obj, show_info2d)
    if INFO2D_DEBUG_ENABLED:
        groups = ",".join(_group_memberships(info_obj) or [])
        if not groups:
            groups = "-"
        log(
            "Info2D sync evaporadora: eq={0} ({1}) mode={2} show3d={3} show2d={4} showInfo2D={5} -> text={6} vis(owner/sym/text)={7}/{8}/{9} point=({10:.1f},{11:.1f},{12:.1f}) groups={13}".format(
                _safe_obj_name(equipment_obj) or "?",
                _safe_obj_label(equipment_obj) or "?",
                mode,
                int(bool(show_3d)),
                int(bool(show_2d)),
                int(bool(getattr(equipment_obj, "ShowInfo2D", True))),
                int(bool(show_info2d)),
                _view_visibility(equipment_obj),
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
    for equipment_obj in list(find_equipments(doc) or []):
        if equipment_obj is None:
            continue
        try:
            if "Info2D" not in getattr(equipment_obj, "PropertiesList", []):
                continue
            info_obj = getattr(equipment_obj, "Info2D", None)
            info_name = str(getattr(info_obj, "Name", "") or "")
            if info_name and doc.getObject(info_name) is not None:
                linked_names.add(info_name)
        except Exception:
            continue

    removed = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if _is_condenser_info2d_obj(obj):
            continue
        if obj is None or not (_is_info2d_obj(obj) or _is_probable_info2d_draft_text(obj)):
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
        log("Limpieza texto 2D evaporadora: huerfanos_eliminados={0}".format(removed))
    return removed


def _symbol2d_manual_offset_local(equipment_obj):
    if equipment_obj is None:
        return App.Vector(0.0, 0.0, 0.0)
    model = str(getattr(equipment_obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    spec = EVAPORATOR_LIBRARY.get(model, {}) if isinstance(EVAPORATOR_LIBRARY, dict) else {}
    raw = None
    if isinstance(spec, dict):
        raw = spec.get("Step2DOffset", spec.get("Step2DOffsetXYZ", None))
    if raw is None:
        return App.Vector(0.0, 0.0, 0.0)
    try:
        if isinstance(raw, (list, tuple)):
            if len(raw) == 2:
                return App.Vector(float(raw[0]), float(raw[1]), 0.0)
            if len(raw) >= 3:
                return App.Vector(float(raw[0]), float(raw[1]), float(raw[2]))
    except Exception:
        pass
    return App.Vector(0.0, 0.0, 0.0)


def _symbol2d_auto_offset_enabled(equipment_obj):
    """Depth auto-alignment is opt-in per model.

    Default is disabled to preserve exact STEP origin alignment between 3D/2D.
    """
    if equipment_obj is None:
        return False
    model = str(getattr(equipment_obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    spec = EVAPORATOR_LIBRARY.get(model, {}) if isinstance(EVAPORATOR_LIBRARY, dict) else {}
    if not isinstance(spec, dict):
        return False
    for key in (
        "Step2DAutoOffset",
        "Step2DAutoWallOffset",
        "Auto2DDepthAlign",
        "AutoWallOffset2D",
    ):
        value = spec.get(key, None)
        if value is None:
            continue
        try:
            return bool(value)
        except Exception:
            return False
    return False


def _symbol2d_auto_wall_offset_local(equipment_obj, symbol_obj):
    if equipment_obj is None or symbol_obj is None:
        return App.Vector(0.0, 0.0, 0.0)
    if not _symbol2d_auto_offset_enabled(equipment_obj):
        return App.Vector(0.0, 0.0, 0.0)

    eq_type = str(getattr(equipment_obj, "Type", "Wall") or "Wall")
    if eq_type not in {"Wall", "FloorCeiling"}:
        return App.Vector(0.0, 0.0, 0.0)

    model = str(getattr(equipment_obj, "Model", DEFAULT_MODEL) or DEFAULT_MODEL)
    if not _resolve_symbol2d_step_for_model(model):
        # Only auto-correct when using explicit STEP 2D symbols.
        return App.Vector(0.0, 0.0, 0.0)

    _sx, eq_depth, _sz = _equipment_size(equipment_obj)
    if float(eq_depth) <= 0.1:
        return App.Vector(0.0, 0.0, 0.0)

    sym_depth = float(eq_depth)
    try:
        shape = getattr(symbol_obj, "Shape", None)
        if shape is not None and not shape.isNull():
            sym_depth = max(0.1, float(shape.BoundBox.YLength))
    except Exception:
        sym_depth = float(eq_depth)

    delta = (float(eq_depth) - float(sym_depth)) * 0.5
    if abs(float(delta)) <= 0.01:
        return App.Vector(0.0, 0.0, 0.0)

    # Keep back face aligned with wall: shift symbol toward wall when it is shallower.
    return App.Vector(0.0, -float(delta), 0.0)


def _symbol2d_placement_for_equipment(equipment_obj, symbol_obj=None):
    placement = getattr(equipment_obj, "Placement", App.Placement())
    base_level = _to_float(getattr(equipment_obj, "BaseLevel", 0.0), 0.0)
    try:
        base = App.Vector(float(placement.Base.x), float(placement.Base.y), float(base_level))
        rot = App.Rotation(placement.Rotation)
        offset_local = _symbol2d_manual_offset_local(equipment_obj) + _symbol2d_auto_wall_offset_local(equipment_obj, symbol_obj)
        if abs(float(offset_local.x)) > 0.01 or abs(float(offset_local.y)) > 0.01 or abs(float(offset_local.z)) > 0.01:
            log(
                "Offset 2D aplicado {0}: dx={1:.2f}, dy={2:.2f}, dz={3:.2f}".format(
                    str(getattr(equipment_obj, "Label", "") or getattr(equipment_obj, "Name", "") or "equipo"),
                    float(offset_local.x),
                    float(offset_local.y),
                    float(offset_local.z),
                )
            )
        base = base + rot.multVec(offset_local)
        return App.Placement(base, rot)
    except Exception:
        return App.Placement()


def _sync_symbol2d_for_equipment(equipment_obj):
    symbol_obj = _ensure_symbol2d_object(equipment_obj)
    if symbol_obj is None:
        return None
    try:
        symbol_obj.Shape = _build_symbol_shape(_symbol_size_mm(equipment_obj), equipment_obj=equipment_obj)
    except Exception:
        return symbol_obj
    try:
        symbol_obj.Placement = _symbol2d_placement_for_equipment(equipment_obj, symbol_obj=symbol_obj)
    except Exception:
        pass
    return symbol_obj


def _sync_visual_mode_visibility(equipment_obj):
    if equipment_obj is None:
        return
    mode = _visual_mode_value(equipment_obj)
    show_3d = mode in {"Ambos", "Solo3D"}
    show_2d = mode in {"Ambos", "Solo2D"}

    if mode == "Ninguno":
        show_3d = False
        show_2d = False

    try:
        if hasattr(equipment_obj, "ViewObject") and equipment_obj.ViewObject is not None:
            equipment_obj.ViewObject.Visibility = bool(show_3d)
    except Exception:
        pass

    symbol_obj = getattr(equipment_obj, "Symbol2D", None) if "Symbol2D" in getattr(equipment_obj, "PropertiesList", []) else None
    if symbol_obj is not None:
        try:
            if hasattr(symbol_obj, "ViewObject") and symbol_obj.ViewObject is not None:
                symbol_obj.ViewObject.Visibility = bool(show_2d)
        except Exception:
            pass

    info_obj = getattr(equipment_obj, "Info2D", None) if "Info2D" in getattr(equipment_obj, "PropertiesList", []) else None
    show_info2d = bool(show_2d) and bool(getattr(equipment_obj, "ShowInfo2D", True))
    _set_text_visibility(info_obj, show_info2d)


def _sync_equipment_geometry(equipment_obj):
    if equipment_obj is None:
        return
    _apply_equipment_elevation(equipment_obj)
    if _is_link_equipment(equipment_obj):
        expected_master = _ensure_master_equipment(
            equipment_obj.Document,
            getattr(equipment_obj, "Model", DEFAULT_MODEL),
            height_m=_height_value_m(equipment_obj),
            symbol_size_mm=_symbol_size_mm(equipment_obj),
            visual_mode=_visual_mode_value(equipment_obj),
        )
        if expected_master is not None and getattr(equipment_obj, "LinkedObject", None) != expected_master:
            equipment_obj.LinkedObject = expected_master
        _configure_link_for_transform(equipment_obj)
    else:
        equipment_obj.Shape = _build_equipment_shape(equipment_obj)
    symbol_obj = _sync_symbol2d_for_equipment(equipment_obj)
    _sync_info2d_for_equipment(equipment_obj, symbol_obj=symbol_obj)
    _sync_visual_mode_visibility(equipment_obj)
    if bool(getattr(equipment_obj, "UsePorts", False)):
        update_equipment_ports(equipment_obj)


def _finalize_insert_visuals(equipment_obj):
    """Force freshly inserted equipment and plan objects into a visible state."""
    if equipment_obj is None:
        return
    mode = _visual_mode_value(equipment_obj)
    show_3d = mode in {"Ambos", "Solo3D"}
    show_2d = mode in {"Ambos", "Solo2D"}
    if mode == "Ninguno":
        show_3d = False
        show_2d = False

    try:
        vobj = getattr(equipment_obj, "ViewObject", None)
        if vobj is not None:
            vobj.Visibility = bool(show_3d)
            if hasattr(vobj, "ShowInTree"):
                vobj.ShowInTree = True
            if hasattr(vobj, "Selectable"):
                vobj.Selectable = True
            if hasattr(vobj, "Pickable"):
                vobj.Pickable = True
    except Exception:
        pass

    symbol_obj = None
    try:
        if "Symbol2D" in getattr(equipment_obj, "PropertiesList", []):
            symbol_obj = getattr(equipment_obj, "Symbol2D", None)
    except Exception:
        symbol_obj = None
    if symbol_obj is not None:
        try:
            vobj = getattr(symbol_obj, "ViewObject", None)
            if vobj is not None:
                vobj.Visibility = bool(show_2d)
                if hasattr(vobj, "ShowInTree"):
                    vobj.ShowInTree = True
                if hasattr(vobj, "Selectable"):
                    vobj.Selectable = True
        except Exception:
            pass

    info_obj = None
    try:
        if "Info2D" in getattr(equipment_obj, "PropertiesList", []):
            info_obj = getattr(equipment_obj, "Info2D", None)
    except Exception:
        info_obj = None
    _set_text_visibility(info_obj, bool(show_2d) and bool(getattr(equipment_obj, "ShowInfo2D", True)))

    try:
        linked = getattr(equipment_obj, "LinkedObject", None)
        linked_name = str(getattr(linked, "Name", "") or "-") if linked is not None else "-"
    except Exception:
        linked_name = "-"
    try:
        shape_obj = getattr(equipment_obj, "Shape", None)
        has_shape = shape_obj is not None and not shape_obj.isNull()
    except Exception:
        has_shape = False
    try:
        symbol_shape = getattr(symbol_obj, "Shape", None) if symbol_obj is not None else None
        has_symbol_shape = symbol_shape is not None and not symbol_shape.isNull()
    except Exception:
        has_symbol_shape = False
    log(
        "InsertVisual resumen: equipo={0}, modo={1}, link={2}, shape3d={3}, simbolo2d={4}, visible3d={5}, visible2d={6}".format(
            _safe_obj_name(equipment_obj) or "?",
            mode,
            linked_name,
            int(bool(has_shape)),
            int(bool(has_symbol_shape)),
            int(bool(show_3d)),
            int(bool(show_2d)),
        )
    )


def _pick_model_for_insert(doc=None):
    log(
        "PickerDebug enter rev={0} gui={1} module={2}".format(
            EQUIP_DEBUG_REV,
            bool(getattr(App, "GuiUp", False)),
            __file__,
        )
    )
    if not App.GuiUp:
        return DEFAULT_MODEL

    try:
        from PySide2 import QtWidgets
    except Exception:
        try:
            from PySide import QtGui as QtWidgets  # FreeCAD legacy fallback
        except Exception:
            return DEFAULT_MODEL

    grouped_models = _picker_models_by_type(doc=doc)
    group_models = [name for name in available_models(doc) if _is_group_model_name(name)]
    log(
        "Modelos disponibles para insercion: catalogo={0}, grupo={1}".format(
            sum(len(items) for items in grouped_models.values()),
            len(group_models),
        )
    )

    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("Insertar Evaporadora HVAC")
    dialog.setMinimumWidth(520)

    cmb_type = QtWidgets.QComboBox()
    cmb_type.addItems(["Pared", "Cassette", "Piso-Cielo", "Ducto"])
    cmb_type.setCurrentText("Pared")

    cmb_capacity = QtWidgets.QComboBox()
    lbl_info = QtWidgets.QLabel("")

    def refresh_capacity():
        ui_type = str(cmb_type.currentText() or "Pared")
        cmb_capacity.clear()
        rows = list(grouped_models.get(ui_type, []))
        for row in rows:
            cap = int(round(_to_float(row.get("Capacity", 0.0), 0.0)))
            source = str(row.get("Source", "PRIMITIVE"))
            text = "{0} BTU/h | {1} | {2}".format(cap, row["Model"], source)
            cmb_capacity.addItem(text, row["Model"])
        if cmb_capacity.count() <= 0:
            lbl_info.setText("No hay capacidades disponibles para este tipo")
        else:
            selected_model = str(cmb_capacity.currentData() or "")
            lbl_info.setText("Modelo seleccionado: {0}".format(selected_model))

    def on_capacity_changed():
        selected_model = str(cmb_capacity.currentData() or "")
        if selected_model:
            lbl_info.setText("Modelo seleccionado: {0}".format(selected_model))

    cmb_type.currentIndexChanged.connect(refresh_capacity)
    cmb_capacity.currentIndexChanged.connect(on_capacity_changed)
    refresh_capacity()

    if group_models:
        info_group = QtWidgets.QLabel(
            "Modelos de grupo detectados: {0} (disponibles con fuente GROUP)".format(len(group_models))
        )
    else:
        info_group = QtWidgets.QLabel("No se detectaron modelos externos en grupo")

    form = QtWidgets.QFormLayout()
    form.addRow("Tipo:", cmb_type)
    form.addRow("Capacidad/Modelo:", cmb_capacity)
    form.addRow("Info:", lbl_info)
    form.addRow("", info_group)

    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addLayout(form)
    layout.addWidget(buttons)

    result = dialog.exec_()
    if result == QtWidgets.QDialog.Accepted:
        if cmb_capacity.count() > 0:
            selected = str(cmb_capacity.currentData() or DEFAULT_MODEL)
            ui_type = str(cmb_type.currentText() or "Pared")
            source = _model_source_tag(selected)
            log("Picker seleccionado: tipo={0}, modelo={1}, fuente={2}".format(ui_type, selected, source))
            return selected

        try:
            if group_models:
                selected, ok = QtWidgets.QInputDialog.getItem(
                    None,
                    "Insertar Evaporadora HVAC (Grupo)",
                    "Modelo externo desde grupo:",
                    group_models,
                    0,
                    False,
                )
                if ok and selected:
                    return str(selected)
        except Exception:
            pass

        log("Insercion evaporadora cancelada: sin modelo disponible")
        return None

    log("Insercion evaporadora cancelada por usuario")
    return None


def _is_rectangle_like(obj):
    if obj is None:
        return False
    proxy = getattr(obj, "Proxy", None)
    if str(getattr(proxy, "Type", "") or "") == "Rectangle":
        return True
    type_id = str(getattr(obj, "TypeId", "") or "")
    if "Part2DObjectPython" in type_id and hasattr(obj, "Length") and hasattr(obj, "Height"):
        return True
    return False


def _is_hvac_space_obj(obj):
    if obj is None:
        return False
    try:
        return (
            hasattr(obj, "PropertiesList")
            and "MEPType" in obj.PropertiesList
            and str(getattr(obj, "MEPType", "") or "") == hvac_space.MEP_TYPE
        )
    except Exception:
        return False


def _collect_rectangles_from_selection(doc=None):
    selected = selection.get_selected_objects(resolve_links=True)
    rectangles = []
    for obj in list(selected or []):
        if obj is None:
            continue
        if _is_group(obj):
            for child in list(getattr(obj, "Group", []) or []):
                child_obj = selection.unwrap_link(child)
                if _is_rectangle_like(child_obj):
                    rectangles.append(child_obj)
            continue
        if _is_rectangle_like(obj):
            rectangles.append(obj)
    return _dedupe_objects_by_name(rectangles)


def _collect_spaces_from_selection(doc=None):
    selected = selection.get_selected_objects(resolve_links=True)
    spaces = []
    known_spaces = list(hvac_space.find_spaces(doc))

    def add_object(candidate):
        obj = selection.unwrap_link(candidate)
        if obj is None:
            return
        if _is_group(obj):
            for child in list(getattr(obj, "Group", []) or []):
                add_object(child)
            return
        if _is_hvac_space_obj(obj):
            spaces.append(obj)
            return
        for space_obj in known_spaces:
            if getattr(space_obj, "BaseSpace", None) == obj:
                spaces.append(space_obj)
                return

    for selected_obj in list(selected or []):
        add_object(selected_obj)
    return _dedupe_objects_by_name(spaces)


def _rect_dims_cols_rows(rect):
    if rect is None:
        return None
    try:
        width = _to_float(getattr(rect, "Length", 0.0), 0.0)
        height = _to_float(getattr(rect, "Height", 0.0), 0.0)
        cols = int(getattr(rect, "Columns", 1) or 1)
        rows = int(getattr(rect, "Rows", 1) or 1)
    except Exception:
        return None
    if width <= 0.0 or height <= 0.0:
        return None
    cols = max(1, cols)
    rows = max(1, rows)
    return float(width), float(height), cols, rows


def _pick_ceiling_model_for_insert(doc=None):
    if not App.GuiUp:
        if "Cassette_24000" in EVAPORATOR_LIBRARY:
            return "Cassette_24000"
        return DEFAULT_MODEL
    try:
        from PySide2 import QtWidgets
    except Exception:
        try:
            from PySide import QtGui as QtWidgets
        except Exception:
            if "Cassette_24000" in EVAPORATOR_LIBRARY:
                return "Cassette_24000"
            return DEFAULT_MODEL

    grouped_models = _picker_models_by_type(doc=doc)
    allowed_types = ["Cassette", "Ducto"]
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("Colocar Cassettes o Ductos en cielo")
    dialog.setMinimumWidth(520)

    cmb_type = QtWidgets.QComboBox()
    cmb_type.addItems(allowed_types)
    cmb_type.setCurrentText("Cassette")

    cmb_capacity = QtWidgets.QComboBox()
    lbl_info = QtWidgets.QLabel("")

    def refresh_capacity():
        ui_type = str(cmb_type.currentText() or "Cassette")
        cmb_capacity.clear()
        rows = list(grouped_models.get(ui_type, []))
        for row in rows:
            cap = int(round(_to_float(row.get("Capacity", 0.0), 0.0)))
            source = str(row.get("Source", "PRIMITIVE"))
            text = "{0} BTU/h | {1} | {2}".format(cap, row["Model"], source)
            cmb_capacity.addItem(text, row["Model"])
        if cmb_capacity.count() > 0:
            lbl_info.setText("Modelo seleccionado: {0}".format(str(cmb_capacity.currentData() or "")))
        else:
            lbl_info.setText("No hay modelos disponibles para este tipo")

    def on_capacity_changed():
        selected_model = str(cmb_capacity.currentData() or "")
        if selected_model:
            lbl_info.setText("Modelo seleccionado: {0}".format(selected_model))

    cmb_type.currentIndexChanged.connect(refresh_capacity)
    cmb_capacity.currentIndexChanged.connect(on_capacity_changed)
    refresh_capacity()

    form = QtWidgets.QFormLayout()
    form.addRow("Tipo:", cmb_type)
    form.addRow("Capacidad/Modelo:", cmb_capacity)
    form.addRow("Info:", lbl_info)

    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addLayout(form)
    layout.addWidget(buttons)

    result = dialog.exec_()
    if result == QtWidgets.QDialog.Accepted and cmb_capacity.count() > 0:
        selected = str(cmb_capacity.currentData() or DEFAULT_MODEL)
        log("Picker cielo seleccionado: tipo={0}, modelo={1}".format(str(cmb_type.currentText()), selected))
        return selected

    if result != QtWidgets.QDialog.Accepted:
        log("Insercion en cielo cancelada por usuario")
        return None
    log("Insercion en cielo cancelada: sin modelo disponible")
    return None


def _set_link_selectable(link_obj):
    if link_obj is None:
        return
    try:
        vo = getattr(link_obj, "ViewObject", None)
        if vo is not None:
            if hasattr(vo, "Selectable"):
                vo.Selectable = True
            if hasattr(vo, "Pickable"):
                vo.Pickable = True
    except Exception:
        pass


def _ensure_all_hvac_links_selectable(doc):
    if doc is None:
        return 0
    count = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "TypeId", "") or "") != "App::Link":
            continue
        if str(getattr(obj, "MEPType", "") or "") != MEP_TYPE:
            continue
        _set_link_selectable(obj)
        count += 1
    return count


def place_ceiling_units_from_selection(doc=None, model_name=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return []

    rectangles = _collect_rectangles_from_selection(doc)
    spaces = _collect_spaces_from_selection(doc)
    if spaces:
        selected_base_names = {
            str(getattr(selection.unwrap_link(getattr(space_obj, "BaseSpace", None)), "Name", "") or "")
            for space_obj in spaces
        }
        selected_base_names.discard("")
        if selected_base_names:
            rectangles = [
                rect
                for rect in rectangles
                if str(getattr(rect, "Name", "") or "") not in selected_base_names
            ]

    if not rectangles and not spaces:
        log("Seleccione uno o mas HVAC Space, rectangulos o grupo Areas para colocar equipos en cielo")
        return []

    selected_model = model_name if model_name is not None else _pick_ceiling_model_for_insert(doc)
    if not selected_model:
        log("Colocacion en cielo cancelada")
        return []
    selected_model = str(selected_model)
    selected_spec = _model_spec(selected_model)
    selected_type = str(selected_spec.get("Type", "Cassette") or "Cassette")
    if selected_type not in {"Cassette", "Duct"}:
        log("El modelo seleccionado no es de cielo (cassette/ducto): {0}".format(selected_model))
        return []

    created = []
    index = 1
    doc.openTransaction("HVAC: Colocar Cassettes/Ductos en cielo")
    try:
        for rect in rectangles:
            dims = _rect_dims_cols_rows(rect)
            if not dims:
                log("Rectangulo sin Length/Height/Columns/Rows validos: {0}".format(getattr(rect, "Label", rect.Name)))
                continue

            width, height, cols, rows = dims
            rect_pl = getattr(rect, "Placement", App.Placement())
            rect_pos = App.Vector(getattr(rect_pl, "Base", App.Vector()))
            rect_rot = getattr(rect_pl, "Rotation", App.Rotation())
            step_x = float(width) / float(cols)
            step_y = float(height) / float(rows)

            for row in range(rows):
                for col in range(cols):
                    local_x = (float(col) + 0.5) * step_x
                    local_y = (float(row) + 0.5) * step_y
                    base = rect_pos + rect_rot.multVec(App.Vector(local_x, local_y, 0.0))

                    obj = _create_evaporator_link(doc, selected_model)
                    obj.Label = "CIELO_{0}_{1:03d}".format(str(getattr(rect, "Label", rect.Name)), index)
                    _set_link_selectable(obj)

                    space = _space_from_position(doc, base)
                    _apply_insert_mount_logic(
                        obj,
                        selected_space=space,
                        selected_point=base,
                    )
                    if space is not None:
                        obj.Space = space
                    else:
                        _auto_assign_space(obj, warn_if_not_found=False)
                    _sync_equipment_geometry(obj)
                    update_equipment_coverage(obj)
                    hvac_project.add_object_to_hvac_group(doc, obj)
                    created.append(obj)
                    index += 1

        for space_obj in spaces:
            base_obj = selection.unwrap_link(getattr(space_obj, "BaseSpace", None))
            region_label = str(
                getattr(space_obj, "Label", "")
                or getattr(base_obj, "Label", "")
                or getattr(space_obj, "Name", "SPACE")
            )
            points = []

            if _is_rectangle_like(base_obj):
                dims = _rect_dims_cols_rows(base_obj)
                if dims:
                    width, height, cols, rows = dims
                    rect_pl = getattr(base_obj, "Placement", App.Placement())
                    rect_pos = App.Vector(getattr(rect_pl, "Base", App.Vector()))
                    rect_rot = getattr(rect_pl, "Rotation", App.Rotation())
                    step_x = float(width) / float(cols)
                    step_y = float(height) / float(rows)
                    for row in range(rows):
                        for col in range(cols):
                            local_x = (float(col) + 0.5) * step_x
                            local_y = (float(row) + 0.5) * step_y
                            points.append(rect_pos + rect_rot.multVec(App.Vector(local_x, local_y, 0.0)))

            if not points:
                center = _space_center_point(space_obj)
                if center is not None:
                    points.append(center)

            if not points:
                log(
                    "No fue posible obtener puntos para recinto HVAC seleccionado: {0}".format(
                        str(getattr(space_obj, "Name", "HVAC_Space"))
                    )
                )
                continue

            for point in points:
                obj = _create_evaporator_link(doc, selected_model)
                obj.Label = "CIELO_{0}_{1:03d}".format(region_label, index)
                _set_link_selectable(obj)

                _apply_insert_mount_logic(
                    obj,
                    selected_space=space_obj,
                    selected_point=point,
                )
                obj.Space = space_obj
                _sync_equipment_geometry(obj)
                update_equipment_coverage(obj)
                hvac_project.add_object_to_hvac_group(doc, obj)
                created.append(obj)
                index += 1

        try:
            from . import hvac_label

            hvac_label.update_all_labels(doc, ensure_visible=True)
        except Exception:
            pass

        _ensure_all_hvac_links_selectable(doc)
        doc.recompute()
        doc.commitTransaction()
    except Exception as exc:
        doc.abortTransaction()
        log("Error colocando equipos en cielo: {0}".format(exc))
        return []

    log(
        "Colocacion en cielo finalizada: modelo={0}, tipo={1}, rectangulos={2}, espacios={3}, creados={4}".format(
            selected_model,
            selected_type,
            len(rectangles),
            len(spaces),
            len(created),
        )
    )
    return created


def _auto_assign_space(equipment_obj, warn_if_not_found=False):
    if not bool(getattr(equipment_obj, "AutoDetectSpace", True)):
        return False
    space = detect_space_for_equipment(equipment_obj)
    if space is not None and space != getattr(equipment_obj, "Space", None):
        equipment_obj.Space = space
        log("Recinto detectado para {0}: {1}".format(equipment_obj.Name, space.Name))
        return True
    if space is not None:
        return True
    if warn_if_not_found:
        eq_type = str(getattr(equipment_obj, "Type", "Wall") or "Wall")
        if eq_type == "Duct":
            log("Ducto sin recinto detectado. Es valido para manejadora en techo general.")
        else:
            log("Evaporadora sin recinto detectado. Asignela manualmente si es necesario.")
    return False


def _fmt_point(point):
    try:
        vec = App.Vector(point)
        return "({0:.1f},{1:.1f},{2:.1f})".format(float(vec.x), float(vec.y), float(vec.z))
    except Exception:
        return "(?, ?, ?)"


def _coerce_point(point):
    if point is None:
        return None
    try:
        return App.Vector(point)
    except Exception:
        return None


def _selected_insert_point():
    try:
        points = list(selection.get_selected_points() or [])
    except Exception as exc:
        log("Diagnostico seleccion: no se pudieron leer puntos seleccionados: {0}".format(exc))
        return None
    if not points:
        return None
    point = _coerce_point(points[0])
    if point is None:
        log("Diagnostico seleccion: punto seleccionado invalido")
        return None
    return point


def _selected_object_count():
    try:
        return len(list(selection.get_selected_objects(resolve_links=True) or []))
    except Exception:
        return 0


def _has_hvac_root(doc):
    if doc is None:
        return False
    try:
        return bool(hvac_project.find_root_groups(doc))
    except Exception:
        return False


def _has_hvac_project(doc):
    if doc is None:
        return False
    try:
        return bool(hvac_project.find_projects(doc))
    except Exception:
        return False


def _ensure_hvac_insert_structure(doc):
    if doc is None:
        return None
    had_root = _has_hvac_root(doc)
    had_project = _has_hvac_project(doc)
    if not had_root or not had_project:
        log("Creando estructura HVAC...")
    try:
        root = hvac_project.ensure_hvac_root_group(doc)
        try:
            hvac_project.ensure_hvac_equipment_group(doc)
        except Exception as group_exc:
            log("No se pudo crear grupo HVAC de equipos: {0}".format(group_exc))
        if not had_project:
            log("Proyecto HVAC no existente; se omite creacion pesada durante insercion")
        return root
    except Exception as exc:
        log("No se pudo crear estructura HVAC minima: {0}".format(exc))
    return None


def diagnose_evaporator_insert_context(doc=None, point=None, space=None):
    """Return and print the minimum context used by robust evaporator insertion."""
    if doc is None:
        doc = App.ActiveDocument

    explicit_point = _coerce_point(point) is not None
    selected_point = None

    report = {
        "ok": False,
        "has_document": doc is not None,
        "has_hvac_root": False,
        "has_hvac_project": False,
        "space_count": 0,
        "has_space": False,
        "has_point": explicit_point,
        "selected_objects": 0,
        "free_mode": False,
    }

    if doc is None:
        log("Diagnostico insercion evaporadora: no hay documento activo")
        return report

    spaces = []
    try:
        spaces = list(hvac_space.find_spaces(doc) or [])
    except Exception as exc:
        log("Diagnostico HVAC Space: no se pudo consultar recintos: {0}".format(exc))

    report["has_hvac_root"] = _has_hvac_root(doc)
    report["has_hvac_project"] = _has_hvac_project(doc)
    report["space_count"] = len(spaces)
    report["has_space"] = bool(space is not None or spaces)
    report["selected_objects"] = _selected_object_count()
    if not explicit_point:
        selected_point = _selected_insert_point()
    report["has_point"] = bool(explicit_point or selected_point is not None)
    report["free_mode"] = not bool(report["has_space"])
    report["ok"] = True

    log(
        "Diagnostico insercion evaporadora: root={0}, proyecto={1}, spaces={2}, punto={3}, seleccion={4}".format(
            int(bool(report["has_hvac_root"])),
            int(bool(report["has_hvac_project"])),
            int(report["space_count"]),
            int(bool(report["has_point"])),
            int(report["selected_objects"]),
        )
    )
    if not report["has_hvac_root"] or not report["has_hvac_project"]:
        log("Contexto HVAC incompleto, se intentara crear automaticamente")
    if not spaces and space is None:
        log("No HVAC Space detectado, insertando en modo libre")
    if not report["has_point"] and space is None:
        log("No seleccion detectada, usando origen")
    return report


def _resolve_insert_space_and_point(doc, point=None, space=None):
    seed_point = _coerce_point(point)
    if seed_point is None:
        seed_point = _selected_insert_point()

    selected_space = space
    if selected_space is None and seed_point is not None:
        selected_space = _space_from_position(doc, seed_point)
    if selected_space is None:
        selected_space = _space_from_selection(doc)
    if seed_point is None and selected_space is None:
        selected_space = _fallback_space_for_insert(doc)
        if selected_space is not None:
            seed_point = _space_center_point(selected_space)
            log("Insercion sin seleccion: se usa recinto HVAC fallback para ubicar la evaporadora")

    if seed_point is None and selected_space is not None:
        seed_point = _space_center_point(selected_space)

    if seed_point is None:
        seed_point = App.Vector(0.0, 0.0, 0.0)
        log("No seleccion detectada, usando origen")

    return selected_space, seed_point


def _log_insert_geometry_source(model_name):
    model = str(model_name or DEFAULT_MODEL)
    if _is_group_model_name(model):
        log("Geometria desde grupo externo para modelo {0}".format(model))
        return
    if _resolve_step_file_for_model(model):
        log("Geometria STEP detectada para modelo {0}".format(model))
        return
    log("Geometria STEP no encontrada, usando primitivo")


def assign_selected_equipments_to_selected_space(doc=None, lock_manual=True):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return None

    equipments = _selected_equipments(doc)
    if not equipments:
        log("Seleccione una o mas evaporadoras para asignar al recinto")
        return None

    spaces = _selected_spaces(doc)
    if spaces:
        if len(spaces) > 1:
            log("Se detectaron multiples recintos HVAC. Se usa el primero seleccionado")
        target_space = spaces[0]
    else:
        target_space = None
        changed_auto = 0
        for equipment_obj in equipments:
            ensure_equipment_properties(equipment_obj)
            _initialize_equipment_defaults(equipment_obj)
            detected = detect_space_for_equipment(equipment_obj)
            if detected is None:
                continue
            previous = getattr(equipment_obj, "Space", None)
            equipment_obj.Space = detected
            update_equipment_coverage(equipment_obj)
            if previous != detected:
                changed_auto += 1
                log("Evaporadora autoasignada por ubicacion: {0} -> {1}".format(equipment_obj.Name, detected.Name))

        if changed_auto <= 0:
            log("No se detecto recinto automaticamente. Seleccione un HVAC Space y las evaporadoras.")
            return None

        log("Asignacion automatica completada por ubicacion: evaporadoras={0}".format(changed_auto))
        try:
            from . import hvac_label

            hvac_label.update_all_labels(doc, ensure_visible=True)
        except Exception:
            pass
        return None

    changed = 0
    for equipment_obj in equipments:
        ensure_equipment_properties(equipment_obj)
        _initialize_equipment_defaults(equipment_obj)
        previous = getattr(equipment_obj, "Space", None)
        equipment_obj.Space = target_space
        if bool(lock_manual) and hasattr(equipment_obj, "PropertiesList") and "AutoDetectSpace" in equipment_obj.PropertiesList:
            equipment_obj.AutoDetectSpace = False
        update_equipment_coverage(equipment_obj)
        if previous != target_space:
            changed += 1
            log("Evaporadora asignada manualmente: {0} -> {1}".format(equipment_obj.Name, target_space.Name))

    if changed <= 0:
        log("Las evaporadoras seleccionadas ya estaban asignadas al recinto {0}".format(target_space.Name))
    else:
        log("Asignacion agil completada: recinto={0}, evaporadoras={1}".format(target_space.Name, changed))

    try:
        from . import hvac_label

        hvac_label.update_all_labels(doc, ensure_visible=True)
    except Exception:
        pass
    return target_space


def _create_evaporator_link(doc, model_name):
    try:
        obj = doc.addObject("App::Link", "HVAC_Evaporator")
        log("InsertDebug evaporadora creada como App::Link")
    except Exception as exc:
        log("InsertDebug fallback a Part::FeaturePython (App::Link no disponible): {0}".format(exc))
        obj = doc.addObject("Part::FeaturePython", "HVAC_Evaporator")
        HVACEquipmentProxy(obj)
        if getattr(obj, "ViewObject", None) is not None:
            HVACEquipmentViewProvider(obj.ViewObject)
    ensure_equipment_properties(obj)
    _initialize_equipment_defaults(obj)
    set_equipment_model(obj, model_name, force=True)
    if "VisualMode" in getattr(obj, "PropertiesList", []):
        try:
            obj.VisualMode = DEFAULT_VISUAL_MODE
            log("VisualMode default evaporadora aplicado: {0}".format(str(getattr(obj, "VisualMode", ""))))
        except Exception:
            pass
    _configure_link_for_transform(obj, reset_link_placement=True)
    _set_link_selectable(obj)
    return obj


def insert_evaporator_safe(doc=None, point=None, space=None, model_name=None):
    """Insert an evaporator with minimum HVAC context, even in empty documents."""
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return None

    diagnose_evaporator_insert_context(doc=doc, point=point, space=space)
    _ensure_hvac_insert_structure(doc)

    selected_model = str(model_name or DEFAULT_MODEL)
    model_options = available_models(doc)
    if selected_model not in model_options:
        log("Modelo evaporadora no disponible: {0}. Usando {1}".format(selected_model, DEFAULT_MODEL))
        selected_model = DEFAULT_MODEL

    log(
        "InsertSafe rev={0} gui={1} module={2} model={3}".format(
            EQUIP_DEBUG_REV,
            bool(getattr(App, "GuiUp", False)),
            __file__,
            str(selected_model),
        )
    )

    transaction_open = False
    try:
        doc.openTransaction("HVAC: Insertar Evaporadora")
        transaction_open = True
    except Exception:
        transaction_open = False

    try:
        obj = _create_evaporator_link(doc, selected_model)
        obj.Label = "EVAP_{0}".format(str(getattr(obj, "Model", selected_model)))
        log(
            "Evaporadora concreta seleccionada: {0} ({1} BTU/h) fuente={2}".format(
                obj.Model,
                int(_to_float(obj.CapacityBTU, 0.0)),
                _model_source_tag(obj.Model),
            )
        )

        _log_insert_geometry_source(obj.Model)

        selected_space, seed_point = _resolve_insert_space_and_point(
            doc,
            point=point,
            space=space,
        )
        log("Insertando evaporadora en {0}".format(_fmt_point(seed_point)))

        placed = _apply_insert_mount_logic(
            obj,
            selected_space=selected_space,
            selected_point=seed_point,
        )
        if placed is None:
            obj.BaseLevel = float(seed_point.z)
            _set_equipment_base(obj, seed_point)
            log("Insercion libre aplicada sin recinto HVAC")
        elif selected_space is None:
            log("Insercion libre aplicada sin recinto HVAC")
        if placed is not None and selected_space is not None and str(getattr(obj, "Type", "")) == "Wall":
            log("Evaporadora de pared ajustada al muro para identificar recinto")

        if selected_space is not None:
            obj.Space = selected_space
            log("Evaporadora asociada a recinto: {0}".format(selected_space.Name))
        else:
            _auto_assign_space(obj, warn_if_not_found=True)

        _sync_equipment_geometry(obj)
        update_equipment_coverage(obj)
        hvac_project.add_object_to_hvac_group(doc, obj)
        _finalize_insert_visuals(obj)
        try:
            doc.recompute()
        except Exception as exc:
            log("Recompute omitido tras insertar evaporadora: {0}".format(exc))
        if transaction_open:
            try:
                doc.commitTransaction()
            except Exception:
                pass
        return obj
    except Exception as exc:
        log("Error insertando evaporadora segura: {0}".format(exc))
        if transaction_open:
            try:
                doc.abortTransaction()
            except Exception:
                pass
        raise


def insert_evaporator_from_selection(doc=None, model_name=None):
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        log("No hay documento activo")
        return None

    log(
        "InsertDebug rev={0} gui={1} module={2} model_arg={3}".format(
            EQUIP_DEBUG_REV,
            bool(getattr(App, "GuiUp", False)),
            __file__,
            str(model_name),
        )
    )

    selected_model = model_name if model_name is not None else _pick_model_for_insert(doc=doc)
    if not selected_model:
        log("Insercion evaporadora cancelada")
        return None
    return insert_evaporator_safe(doc=doc, model_name=str(selected_model))


def refresh_equipment(equipment_obj):
    if equipment_obj is None:
        return
    ensure_equipment_properties(equipment_obj)
    _initialize_equipment_defaults(equipment_obj)
    if _is_link_equipment(equipment_obj):
        _configure_link_for_transform(equipment_obj)
    if _geometry_needs_sync(equipment_obj):
        _sync_equipment_geometry(equipment_obj)
    _auto_assign_space(equipment_obj)
    update_equipment_coverage(equipment_obj)


def refresh_step_models(doc=None):
    """Manual refresh for evaporator STEP models and dependent links."""
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return 0

    masters_reset = 0
    refreshed = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_master_equipment_obj(obj):
            continue
        try:
            if "ShapeSignature" in getattr(obj, "PropertiesList", []):
                obj.ShapeSignature = ""
                masters_reset += 1
        except Exception:
            pass

    for equipment_obj in list(find_equipments(doc) or []):
        if equipment_obj is None:
            continue
        try:
            ensure_equipment_properties(equipment_obj)
            _initialize_equipment_defaults(equipment_obj)
            if _equipment_needs_plan_fallback(equipment_obj):
                _place_equipment_on_fallback_space(equipment_obj, reason="refresh")
            _sync_equipment_geometry(equipment_obj)
            _auto_assign_space(equipment_obj)
            update_equipment_coverage(equipment_obj)
            _finalize_insert_visuals(equipment_obj)
            refreshed += 1
        except Exception as exc:
            log("Refresh evaporadora omitida: {0} -> {1}".format(getattr(equipment_obj, "Name", "?"), exc))

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
        "Refresh modelos evaporadora manual: masters={0}, equipos={1}, simbolos2d_huerfanos={2}, textos2d_huerfanos={3}".format(
            masters_reset,
            refreshed,
            removed_orphans,
            removed_info_orphans,
        )
    )
    return refreshed


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
    info_objs = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if _is_info2d_obj(obj):
            info_objs.append(obj)
    return info_objs


class HVACEquipmentProxy:
    def __init__(self, obj):
        obj.Proxy = self
        self._busy = False
        ensure_equipment_properties(obj)
        _initialize_equipment_defaults(obj)

    def onChanged(self, obj, prop):  # noqa: N802
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        if prop in {
            "Model",
            "Type",
            "CapacityBTU",
            "SystemType",
            "Space",
            "Height",
            "BaseLevel",
            "Placement",
            "Symbol2DSize",
            "ShowSymbol2D",
            "ShowInfo2D",
            "Info2DSize",
            "AutoDetectSpace",
            "UsePorts",
        }:
            self._busy = True
            try:
                if prop == "Model":
                    set_equipment_model(obj, getattr(obj, "Model", DEFAULT_MODEL), force=True)
                if prop == "Height":
                    raw_h = _to_float(getattr(obj, "Height", 0.0), 0.0)
                    norm_h = _sanitize_height_input_m(raw_h)
                    if abs(raw_h - norm_h) > 0.0001:
                        obj.Height = norm_h
                        log(
                            "Altura normalizada para {0}: {1} -> {2} m".format(
                                _safe_obj_name(obj) or "?",
                                round(float(raw_h), 3),
                                round(float(norm_h), 3),
                            )
                        )
                if prop == "Placement":
                    placement = getattr(obj, "Placement", App.Placement())
                    inferred_base_level = float(placement.Base.z)
                    if abs(_to_float(getattr(obj, "BaseLevel", 0.0), 0.0) - inferred_base_level) > 0.01:
                        obj.BaseLevel = inferred_base_level
                if prop in {"Placement", "AutoDetectSpace"}:
                    _auto_assign_space(obj)
                if prop in {
                    "Model",
                    "Type",
                    "Placement",
                    "Height",
                    "BaseLevel",
                    "Symbol2DSize",
                    "ShowSymbol2D",
                    "ShowInfo2D",
                    "Info2DSize",
                    "SystemType",
                    "UsePorts",
                }:
                    _sync_equipment_geometry(obj)
                if prop in {"Model", "CapacityBTU", "Space", "Placement", "AutoDetectSpace", "Height", "BaseLevel"}:
                    update_equipment_coverage(obj)
            except Exception as exc:
                if _is_access_violation(exc):
                    _remove_broken_equipment(getattr(obj, "Document", None), obj, reason=exc, context="onChanged")
                else:
                    log("onChanged omitido por error en {0}: {1}".format(_safe_obj_name(obj) or "?", _exc_text(exc) or exc))
            finally:
                self._busy = False

    def execute(self, obj):
        if not hasattr(self, "_busy"):
            self._busy = False
        if self._busy:
            return
        self._busy = True
        try:
            ensure_equipment_properties(obj)
            _initialize_equipment_defaults(obj)
            if _geometry_needs_sync(obj):
                _sync_equipment_geometry(obj)
            _auto_assign_space(obj)
            update_equipment_coverage(obj)
        except Exception as exc:
            if _is_access_violation(exc):
                _remove_broken_equipment(getattr(obj, "Document", None), obj, reason=exc, context="execute")
            else:
                log("execute omitido por error en {0}: {1}".format(_safe_obj_name(obj) or "?", _exc_text(exc) or exc))
        finally:
            self._busy = False


class HVACEquipmentViewProvider:
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
