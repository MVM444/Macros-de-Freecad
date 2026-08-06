# -*- coding: utf-8 -*-
"""Module: ElectricCR.ui.mode_manager
Purpose: Manage manual work modes and toolbar visibility for ElectricCR.
Important: Modes must be selected only by the user; never switch modes from
object selection. Keep all macros available through menus and launchers.
Modified: 2026-07-08 00:00 Costa Rica.
Target: FreeCAD 1.1.1.
"""

import json
import os
import unicodedata

import FreeCAD as App
import FreeCADGui as Gui


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/ElectricCR"
PARAM_LAST_MODE = "last_work_mode"

INTERFACE_MODES_PROTOTYPE = "modes_prototype"
INTERFACE_LEGACY = "legacy"

MODE_DEFS = [
    ("deteccion", "Deteccion de incendios", "Deteccion de incendios"),
    ("areas", "Arquitectura y áreas", "Arquitectura y áreas"),
    ("iluminacion", "Iluminación", "Iluminación"),
    ("tomacorrientes", "Tomacorrientes", "Tomacorrientes"),
    ("conexiones", "Canalización y conexiones", "Canalización y conexiones"),
    ("tableros_calculo", "Tableros y cálculo", "Tableros y cálculo"),
    ("documentacion", "Documentación", "Documentación"),
    ("organizacion", "Organización del proyecto", "Organización del proyecto"),
    ("personalizado", "Personalizado", "Personalizado"),
]

DEFAULT_WORK_MODES = {
    "deteccion": ["Deteccion"],
    "areas": ["Areas"],
    "iluminacion": ["Iluminacion"],
    "tomacorrientes": ["Tomacorrientes"],
    "conexiones": ["Conectar", "Cajas"],
    "tableros_calculo": ["Tableros", "Configuracion del proyecto"],
    "documentacion": ["Importar y Exportar"],
    "organizacion": ["Configuracion del proyecto"],
    "personalizado": [
        "Areas", "Iluminacion", "Tomacorrientes", "Conectar", "Cajas", "Tableros",
        "Configuracion del proyecto", "Importar y Exportar",
    ],
}

DEFAULT_ALWAYS_VISIBLE_TOOLBARS = ["Objetos", "Draft compacto"]

_FALLBACK_LAST_MODE = "areas"


def print_mode(message):
    try:
        App.Console.PrintMessage("[ElectricCR][Mode] " + str(message) + "\n")
    except Exception:
        try:
            print("[ElectricCR][Mode] " + str(message))
        except Exception:
            pass


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    except Exception as exc:
        print_mode("config_read_error=" + str(exc))
    return {}


def normalize_name(text):
    value = str(text or "").strip().lower()
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("&", "")
    value = " ".join(value.split())
    return value


def cfg_bool(cfg, key, default):
    try:
        value = cfg.get(key, default)
    except Exception:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        txt = value.strip().lower()
        if txt in {"1", "true", "yes", "on", "si"}:
            return True
        if txt in {"0", "false", "no", "off"}:
            return False
    return bool(default)


def interface_mode(cfg=None):
    cfg = cfg or load_config()
    return str(cfg.get("interface_mode", INTERFACE_LEGACY)).strip().lower()


def is_enabled(cfg=None):
    cfg = cfg or load_config()
    return interface_mode(cfg) == INTERFACE_MODES_PROTOTYPE


def panel_enabled(cfg=None):
    cfg = cfg or load_config()
    return is_enabled(cfg) and cfg_bool(cfg, "mode_panel_enabled", True)


def mode_defs(cfg=None):
    cfg = cfg or load_config()
    work_modes = work_mode_map(cfg)
    return [item for item in MODE_DEFS if item[0] in work_modes]


def work_mode_map(cfg=None):
    cfg = cfg or load_config()
    raw = cfg.get("work_modes")
    if not isinstance(raw, dict):
        raw = DEFAULT_WORK_MODES
    out = {}
    for key, names in raw.items():
        mode_key = str(key).strip().lower()
        if mode_key not in dict((item[0], item) for item in MODE_DEFS):
            continue
        if isinstance(names, list):
            clean = [str(name).strip() for name in names if str(name).strip()]
        elif isinstance(names, str):
            clean = [name.strip() for name in names.split(",") if name.strip()]
        else:
            clean = []
        if mode_key == "personalizado":
            custom = cfg.get("custom_mode_toolbars")
            if isinstance(custom, list):
                clean = [str(name).strip() for name in custom if str(name).strip()]
            elif isinstance(custom, str):
                clean = [name.strip() for name in custom.split(",") if name.strip()]
        out[mode_key] = clean
    if not out:
        out = dict(DEFAULT_WORK_MODES)
    return out


def always_visible_toolbars(cfg=None):
    cfg = cfg or load_config()
    raw = cfg.get("always_visible_toolbars")
    if not isinstance(raw, list):
        raw = DEFAULT_ALWAYS_VISIBLE_TOOLBARS
    return [str(name).strip() for name in raw if str(name).strip()]


def mode_label(mode_key, cfg=None):
    for key, label, _log_name in mode_defs(cfg):
        if key == mode_key:
            return label
    return "Areas"


def mode_log_name(mode_key, cfg=None):
    for key, _label, log_name in mode_defs(cfg):
        if key == mode_key:
            return log_name
    return "Areas"


def mode_toolbar_names(cfg=None):
    cfg = cfg or load_config()
    configured = cfg.get("mode_toolbar_names")
    if isinstance(configured, list) and configured:
        names = []
        seen = set()
        for name in always_visible_toolbars(cfg) + configured:
            text = str(name).strip()
            norm = normalize_name(text)
            if text and norm not in seen:
                names.append(text)
                seen.add(norm)
        return names

    names = []
    seen = set()
    for name in always_visible_toolbars(cfg):
        norm = normalize_name(name)
        if norm and norm not in seen:
            names.append(name)
            seen.add(norm)
    for toolbar_list in work_mode_map(cfg).values():
        for name in toolbar_list:
            norm = normalize_name(name)
            if norm and norm not in seen:
                names.append(name)
                seen.add(norm)
    return names


def should_create_toolbar(title, cfg=None):
    cfg = cfg or load_config()
    if not is_enabled(cfg):
        return False
    wanted = normalize_name(title)
    return wanted in {normalize_name(name) for name in mode_toolbar_names(cfg)}


def _param_group():
    try:
        return App.ParamGet(PARAM_PATH)
    except Exception:
        return None


def get_last_mode(cfg=None):
    global _FALLBACK_LAST_MODE
    cfg = cfg or load_config()
    valid = {key for key, _label, _log_name in mode_defs(cfg)}
    param = _param_group()
    value = ""
    if param is not None:
        try:
            value = param.GetString(PARAM_LAST_MODE, "")
        except Exception:
            value = ""
    if not value:
        value = _FALLBACK_LAST_MODE
    value = str(value).strip().lower()
    if value not in valid:
        value = "areas"
    return value


def set_last_mode(mode_key):
    global _FALLBACK_LAST_MODE
    mode_key = str(mode_key or "areas").strip().lower()
    _FALLBACK_LAST_MODE = mode_key
    param = _param_group()
    if param is not None:
        try:
            param.SetString(PARAM_LAST_MODE, mode_key)
        except Exception:
            pass


def _qt_modules():
    for candidate in ("PySide6", "PySide2", "PySide"):
        try:
            if candidate == "PySide":
                from PySide import QtCore, QtGui
                return QtGui, QtCore
            module = __import__(candidate, fromlist=["QtCore", "QtWidgets"])
            return module.QtWidgets, module.QtCore
        except Exception:
            continue
    return None, None


def _main_window():
    try:
        return Gui.getMainWindow()
    except Exception:
        return None


def _toolbar_title(toolbar):
    for getter in ("windowTitle", "objectName"):
        try:
            value = getattr(toolbar, getter)()
        except Exception:
            value = ""
        if value:
            return str(value).replace("&", "").strip()
    try:
        action = toolbar.toggleViewAction()
        value = action.text()
        if value:
            return str(value).replace("&", "").strip()
    except Exception:
        pass
    return ""


def _find_toolbars_by_name(QtWidgets, names):
    mw = _main_window()
    found = {}
    if mw is None or QtWidgets is None:
        return found

    wanted = {normalize_name(name): str(name) for name in names}
    try:
        toolbars = mw.findChildren(QtWidgets.QToolBar)
    except Exception:
        toolbars = []

    for toolbar in toolbars:
        title = _toolbar_title(toolbar)
        key = normalize_name(title)
        if key in wanted:
            found.setdefault(wanted[key], []).append(toolbar)
    return found


def _set_toolbar_visible(toolbar, visible):
    try:
        toolbar.setVisible(bool(visible))
        return True
    except Exception:
        try:
            if visible:
                toolbar.show()
            else:
                toolbar.hide()
            return True
        except Exception:
            return False


def apply_mode(mode_key=None, cfg=None):
    cfg = cfg or load_config()
    if not is_enabled(cfg):
        print_mode("interface_mode=legacy")
        return {
            "selected": get_last_mode(cfg),
            "visible": [],
            "hidden": [],
            "missing": [],
        }

    work_modes = work_mode_map(cfg)
    selected = str(mode_key or get_last_mode(cfg)).strip().lower()
    if selected not in work_modes:
        selected = "areas"
    set_last_mode(selected)

    managed = mode_toolbar_names(cfg)
    always_visible = always_visible_toolbars(cfg)
    visible = list(always_visible) + list(work_modes.get(selected, []))
    visible_seen = set()
    visible = [
        name for name in visible
        if not (normalize_name(name) in visible_seen or visible_seen.add(normalize_name(name)))
    ]
    visible_names = ["ElectricCR"] + visible
    hidden = [name for name in managed if normalize_name(name) not in {normalize_name(v) for v in visible}]
    toolbar_map = _find_toolbars_by_name(_qt_modules()[0], managed + ["ElectricCR"])

    missing = []
    for name in managed:
        toolbars = toolbar_map.get(name, [])
        if not toolbars:
            missing.append(name)
            continue
        should_show = normalize_name(name) in {normalize_name(v) for v in visible}
        for toolbar in toolbars:
            _set_toolbar_visible(toolbar, should_show)

    for toolbar in toolbar_map.get("ElectricCR", []):
        _set_toolbar_visible(toolbar, True)

    print_mode("selected=" + mode_log_name(selected, cfg))
    print_mode("visible=" + ",".join(visible_names))
    print_mode("hidden=" + ",".join(hidden))
    if missing:
        print_mode("missing=" + ",".join(missing))

    return {
        "selected": selected,
        "visible": visible_names,
        "hidden": hidden,
        "missing": missing,
    }


def restore_legacy_visibility(cfg=None):
    cfg = cfg or load_config()
    managed = mode_toolbar_names(cfg)
    toolbar_map = _find_toolbars_by_name(_qt_modules()[0], managed + ["ElectricCR"])
    for name, toolbars in toolbar_map.items():
        for toolbar in toolbars:
            _set_toolbar_visible(toolbar, True)
    print_mode("interface_mode=legacy")


def select_mode(mode_key, cfg=None):
    return apply_mode(mode_key, cfg)
