# -*- coding: utf-8 -*-
"""Module: ElectricCR.InitGui
Purpose: Register the ElectricCR workbench, menus, toolbars, and mode panel.
Important: Keep ElectricCR as one workbench. Manual modes must not switch from
object selection. Keep all macros reachable through menus and launchers.
Modified: 2026-07-07 09:18 Costa Rica.
Target: FreeCAD 1.1.1.
"""

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
import unicodedata
import FreeCAD as App
import FreeCADGui as Gui

from . import usage_log

BASE_DIR = os.path.dirname(__file__)
ICONS_DIR = os.path.join(BASE_DIR, "icons")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def icon_path(basename: str) -> str:
    for candidate in (f"{basename}.svg", f"{basename}.png", basename):
        p = os.path.join(ICONS_DIR, candidate)
        if os.path.exists(p):
            return p
    return ""


def _register_icon_path() -> None:
    try:
        Gui.addIconPath(ICONS_DIR.replace(os.sep, "/"))
    except Exception:
        pass


def load_config():
    try:
        import json
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        App.Console.PrintWarning(f"ElectricCR: no se pudo leer config.json: {e}\n")
    return {}


def _cfg_bool(cfg: dict, key: str, default: bool) -> bool:
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


def _cfg_str(cfg: dict, key: str, default: str) -> str:
    try:
        value = cfg.get(key, default)
    except Exception:
        return str(default)
    if value is None:
        return str(default)
    return str(value).strip()


def _cfg_list(cfg: dict, key: str, default: list) -> list:
    try:
        value = cfg.get(key, default)
    except Exception:
        value = default
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in default if str(item).strip()]


def _normalize_toolbar_key(text: str) -> str:
    s = str(text or "").strip().lower()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = " ".join(s.split())
    return s


def _group_name_in(title: str, names: list) -> bool:
    wanted = _normalize_toolbar_key(title)
    if not wanted:
        return False
    return any(_normalize_toolbar_key(name) == wanted for name in names)


def _merge_command_groups(groups: list) -> list:
    merged = []
    index_by_key = {}
    for title, cmds in groups or []:
        key = _normalize_toolbar_key(title)
        if not key:
            continue
        clean_cmds = [cmd for cmd in (cmds or []) if cmd]
        if not clean_cmds:
            continue
        if key in index_by_key:
            idx = index_by_key[key]
            group_title, group_cmds = merged[idx]
            seen = set(group_cmds)
            for cmd in clean_cmds:
                if cmd not in seen:
                    group_cmds.append(cmd)
                    seen.add(cmd)
            merged[idx] = (group_title, group_cmds)
        else:
            index_by_key[key] = len(merged)
            merged.append((title, clean_cmds))
    return merged


def _should_show_macro_toolbar(title: str, cfg: dict) -> bool:
    mode = _cfg_str(cfg, "macro_toolbar_mode", "compact").lower()
    if mode in {"full", "all", "todos"}:
        return True
    if mode in {"off", "none", "menu_only", "menu-only", "solo_menu", "solo-menu"}:
        return False
    visible_groups = _cfg_list(cfg, "macro_toolbar_groups", [])
    return _group_name_in(title, visible_groups)


_WRAPPED_COMMANDS = {}
_LOG_ENABLED = False
_CONNECTED_TOOLBARS = set()
_QT_MSG_FILTER_INSTALLED = False
_QT_PREV_MSG_HANDLER = None
_QT_EFFECTS_DISABLED = False


def _sanitize_id(text: str) -> str:
    import re
    base = re.sub(r"[^0-9A-Za-z_]+", "_", text or "")
    base = re.sub(r"_+", "_", base).strip("_")
    return base or "Cmd"


def _get_cmd_obj(cmd_name: str):
    try:
        if hasattr(Gui, "Command") and hasattr(Gui.Command, "getCommand"):
            return Gui.Command.getCommand(cmd_name)
    except Exception:
        pass
    try:
        if hasattr(Gui, "getCommand"):
            return Gui.getCommand(cmd_name)
    except Exception:
        pass
    return None


def _get_cmd_resources(cmd_name: str) -> dict:
    cmd = _get_cmd_obj(cmd_name)
    if cmd:
        for attr in ("GetResources", "getResources"):
            if hasattr(cmd, attr):
                try:
                    res = getattr(cmd, attr)()
                    if isinstance(res, dict):
                        return res
                except Exception:
                    pass
    return {}


def _resolve_pixmap(pixmap: str) -> str:
    if not pixmap:
        return ""
    try:
        p = str(pixmap)
    except Exception:
        return ""
    if not p:
        return ""
    if p.startswith(":/") or os.path.isabs(p):
        return p
    # Dejar que FreeCAD resuelva nombres de iconos relativos
    return p


def _wrap_command(cmd_name: str) -> str:
    if not cmd_name or cmd_name.startswith("ElectricCR_"):
        return cmd_name
    if cmd_name in _WRAPPED_COMMANDS:
        wrapper_name = _WRAPPED_COMMANDS[cmd_name]
    else:
        wrapper_name = f"ElectricCR_Track_{_sanitize_id(cmd_name)}"

    class _WrapCmd:
        def GetResources(self):
            res = _get_cmd_resources(cmd_name)
            if not res:
                res = {"MenuText": cmd_name, "ToolTip": cmd_name}
            try:
                res = dict(res)
            except Exception:
                res = {"MenuText": cmd_name, "ToolTip": cmd_name}
            if not res.get("MenuText"):
                res["MenuText"] = cmd_name
            if not res.get("ToolTip"):
                res["ToolTip"] = res.get("MenuText", cmd_name)
            pix = res.get("Pixmap") or res.get("PixmapPath") or ""
            if isinstance(pix, str):
                pix = _resolve_pixmap(pix)
                if pix:
                    res["Pixmap"] = pix
            return res

        def Activated(self):
            try:
                res = _get_cmd_resources(cmd_name)
                menu_text = ""
                try:
                    if isinstance(res, dict):
                        menu_text = str(res.get("MenuText") or "")
                except Exception:
                    menu_text = ""
                usage_log.log_tool(cmd_name, {"source": "toolbar", "menu": menu_text, "usage_kind": "real"})
            except Exception:
                pass
            try:
                Gui.runCommand(cmd_name)
            except Exception as e:
                App.Console.PrintError(f"ElectricCR: no se pudo ejecutar {cmd_name}: {e}\n")

        def IsActive(self):
            try:
                cmd = _get_cmd_obj(cmd_name)
                if cmd and hasattr(cmd, "IsActive"):
                    return cmd.IsActive()
            except Exception:
                pass
            return True

    try:
        Gui.addCommand(wrapper_name, _WrapCmd())
        _WRAPPED_COMMANDS[cmd_name] = wrapper_name
        return wrapper_name
    except Exception:
        return cmd_name


def _wrap_cmds(cmds: list[str], available: set[str]) -> list[str]:
    out = []
    for cmd_name in cmds:
        if cmd_name not in available:
            continue
        out.append(_wrap_command(cmd_name))
    return out


def _qmods():
    try:
        from PySide2 import QtWidgets
        return QtWidgets
    except Exception:
        try:
            from PySide import QtGui as QtWidgets
            return QtWidgets
        except Exception:
            return None


def _qmods_with_core():
    try:
        from PySide2 import QtWidgets, QtCore
        return QtWidgets, QtCore
    except Exception:
        try:
            from PySide import QtGui as QtWidgets
            from PySide import QtCore
            return QtWidgets, QtCore
        except Exception:
            return None, None


def _qt_message_filter(*args):
    msg = ""
    try:
        if args:
            msg = str(args[-1])
    except Exception:
        msg = ""
    if "UpdateLayeredWindowIndirect failed" in msg:
        return

    prev = _QT_PREV_MSG_HANDLER
    if prev is not None:
        try:
            prev(*args)
            return
        except Exception:
            pass


def _install_windows_qt_layered_filter(cfg: dict) -> None:
    global _QT_MSG_FILTER_INSTALLED, _QT_PREV_MSG_HANDLER
    if os.name != "nt":
        return
    if not _cfg_bool(cfg, "suppress_qt_layered_warnings", True):
        return
    if _QT_MSG_FILTER_INSTALLED:
        return

    _QtWidgets, QtCore = _qmods_with_core()
    if QtCore is None:
        return
    try:
        if hasattr(QtCore, "qInstallMessageHandler"):
            _QT_PREV_MSG_HANDLER = QtCore.qInstallMessageHandler(_qt_message_filter)
            _QT_MSG_FILTER_INSTALLED = True
        elif hasattr(QtCore, "qInstallMsgHandler"):
            _QT_PREV_MSG_HANDLER = QtCore.qInstallMsgHandler(_qt_message_filter)
            _QT_MSG_FILTER_INSTALLED = True
    except Exception:
        return

    if _QT_MSG_FILTER_INSTALLED:
        try:
            App.Console.PrintMessage(
                "ElectricCR: filtro Qt activado para UpdateLayeredWindowIndirect en Windows.\n"
            )
        except Exception:
            pass


def _disable_windows_qt_ui_effects(cfg: dict) -> None:
    global _QT_EFFECTS_DISABLED
    if os.name != "nt":
        return
    if not _cfg_bool(cfg, "disable_qt_ui_effects", True):
        return
    if _QT_EFFECTS_DISABLED:
        return

    QtWidgets, QtCore = _qmods_with_core()
    if QtWidgets is None or QtCore is None:
        return
    try:
        app = QtWidgets.QApplication.instance()
    except Exception:
        app = None
    if app is None:
        return

    changed = 0
    for effect_name in (
        "UI_AnimateMenu",
        "UI_FadeMenu",
        "UI_AnimateCombo",
        "UI_AnimateTooltip",
        "UI_FadeTooltip",
    ):
        try:
            effect = getattr(QtCore.Qt, effect_name, None)
            if effect is None:
                continue
            app.setEffectEnabled(effect, False)
            changed += 1
        except Exception:
            continue

    if changed > 0:
        _QT_EFFECTS_DISABLED = True
        try:
            App.Console.PrintMessage(
                "ElectricCR: efectos UI de Qt desactivados en Windows (mitigacion layered windows).\n"
            )
        except Exception:
            pass


def _action_command_id(action) -> str:
    try:
        name = action.objectName()
    except Exception:
        name = ""
    if not name:
        try:
            data = action.data()
            if isinstance(data, str):
                name = data
        except Exception:
            pass
    if not name:
        try:
            name = action.text()
        except Exception:
            name = ""
    return (name or "").replace("&", "").strip()


def _should_log_cmd(cmd_name: str) -> bool:
    if not cmd_name:
        return False
    if cmd_name.startswith("ElectricCR_"):
        return False
    return cmd_name.startswith(("CRBIM_", "Draft_", "BIM_", "Arch_"))


def _on_toolbar_action(action) -> None:
    if not _LOG_ENABLED:
        return
    try:
        cmd_name = _action_command_id(action)
        if not _should_log_cmd(cmd_name):
            return
        meta = {}
        try:
            meta["text"] = action.text()
        except Exception:
            pass
        usage_log.log_tool(cmd_name, {"source": "toolbar_action", "usage_kind": "real", **meta})
    except Exception:
        pass


def _connect_toolbar_logger() -> None:
    QtWidgets = _qmods()
    if QtWidgets is None:
        return
    try:
        mw = Gui.getMainWindow()
    except Exception:
        mw = None
    if mw is None:
        return
    try:
        for tb in mw.findChildren(QtWidgets.QToolBar):
            try:
                key = int(tb.winId())
            except Exception:
                key = id(tb)
            if key in _CONNECTED_TOOLBARS:
                continue
            try:
                tb.actionTriggered.connect(_on_toolbar_action)
                _CONNECTED_TOOLBARS.add(key)
            except Exception:
                continue
    except Exception:
        pass


class ElectricCRWorkbench(Gui.Workbench):
    """Workbench personalizado ElectricCR."""

    MenuText = "Eléctrico CR"
    ToolTip = "Workbench para diseñar instalaciones eléctricas"
    Icon = icon_path("Rayo")

    def Initialize(self):
        # Evitar duplicados si se recarga el módulo
        if getattr(self, "_built", False):
            return
        _register_icon_path()

        # Comandos contextuales propios de objetos ElectricCR.
        wall_side_cmd = None
        try:
            from .commands import wall_side as _wall_side
            wall_side_cmd = _wall_side.register_command()
        except Exception as e:
            App.Console.PrintWarning(f"[ElectricCR][Context] wall_side_warning={e}\n")

        # Asegurar que Draft registre sus comandos si está disponible
        try:
            import Draft  # noqa: F401
            import DraftGui  # noqa: F401
        except Exception:
            pass

        # Intentar registrar comandos de Arch/BIM para que aparezcan en listCommands
        try:
            import Arch  # noqa: F401
            import ArchGui  # noqa: F401
        except Exception:
            pass
        try:
            import BIM  # noqa: F401  # Módulo del WB BIM si está instalado
        except Exception:
            pass

        available = set(Gui.listCommands())
        common_room_commands = []
        try:
            from CRBIMCore.commands.common_rooms import ensure_common_room_commands_registered

            common_room_commands = ensure_common_room_commands_registered()
        except Exception as e:
            App.Console.PrintWarning(f"[ElectricCR][Rooms] command_warning={e}\n")
        cfg = load_config()
        show_bim_toolbar = _cfg_bool(cfg, "show_bim_toolbar", False)
        show_draft_toolbars = _cfg_bool(cfg, "show_draft_toolbars", False)
        mode_manager = None
        mode_panel = None
        modes_enabled = False
        try:
            from .ui import mode_manager as _mode_manager
            from .ui import mode_panel as _mode_panel
            mode_manager = _mode_manager
            mode_panel = _mode_panel
            modes_enabled = mode_manager.is_enabled(cfg)
        except Exception as e:
            App.Console.PrintWarning(f"[ElectricCR][Mode] import_warning={e}\n")

        # BIM/Arch tools (e.g., Wall/Muro)
        try:
            bim_wall_candidates = ["BIM_Wall", "Arch_Wall"]
            bim_cmds = [c for c in bim_wall_candidates if c in available]
            if bim_cmds:
                if show_bim_toolbar:
                    self.appendToolbar("BIM", bim_cmds)
                self.appendMenu("BIM", bim_cmds)
        except Exception:
            pass

        # Categorías Draft
        esbozar = [
            "Draft_Line", "Draft_Wire", "Draft_Fillet",
            "Draft_Arc", "Draft_Circle", "Draft_Ellipse", "Draft_Rectangle",
            "Draft_Polygon", "Draft_BSpline", "Draft_BezCurve",
            "Draft_Point", "Draft_Facebinder", "Draft_TextShape", "Draft_Hatch",
        ]
        # Draft_AnnotationStyleEditor can emit "Cannot find icon: SpreadsheetAlignLeft"
        # on some installations; keep core annotation tools in this WB toolbar.
        anotacion = ["Draft_Text", "Draft_Dimension", "Draft_Label"]
        modificacion = [
            "Draft_Move", "Draft_Rotate", "Draft_Scale", "Draft_Mirror",
            "Draft_Offset", "Draft_Trimex", "Draft_Stretch", "Draft_Edit",
            "Draft_Join", "Draft_Split", "Draft_Upgrade", "Draft_Downgrade",
            "Draft_Clone", "Draft_Array", "Draft_PathArray", "Draft_PolarArray",
            "Draft_Shape2DView",
        ]
        utilidades = [
            "Draft_SetStyle", "Draft_ApplyStyle", "Draft_Layer",
            "Draft_ToggleConstructionMode", "Draft_ToggleGrid", "Draft_SelectPlane",
            "Draft_AddToGroup", "Draft_MoveToGroup", "Draft_SelectGroup",
        ]
        try:
            if show_draft_toolbars:
                from draftutils import init_tools as _draft_tools
                snap_cmds = [c for c in _draft_tools.get_draft_snap_commands() if c in available]
                if snap_cmds:
                    _draft_tools.init_toolbar(self, "Draft snap", snap_cmds)
        except Exception:
            pass

        groups = [
            ("Esbozar", [c for c in esbozar if c in available]),
            ("Anotación", [c for c in anotacion if c in available]),
            ("Modificación", [c for c in modificacion if c in available]),
            ("Utilidades", [c for c in utilidades if c in available]),
        ]

        for title, cmds in groups:
            if cmds:
                if show_draft_toolbars:
                    self.appendToolbar(title, cmds)
                self.appendMenu(title, cmds)

        draft_compact = [
            "Draft_Line",
            "Draft_Wire",
            "Draft_Rectangle",
            "Draft_Circle",
            "Draft_Polygon",
            "Draft_Move",
            "Draft_Rotate",
            "Draft_AddToGroup",
            "Draft_SelectGroup",
            "Draft_Snap_Endpoint",
            "Draft_Snap_Midpoint",
            "Draft_Snap_Center",
            "Draft_Snap_Intersection",
            "Draft_Snap_Perpendicular",
            "Draft_Snap_Ortho",
        ]
        try:
            show_draft_compact = _cfg_bool(cfg, "show_draft_compact_toolbar", True)
            draft_compact_cmds = [c for c in draft_compact if c in available]
            if show_draft_compact and draft_compact_cmds:
                self.appendToolbar("Draft compacto", draft_compact_cmds)
        except Exception:
            pass

        # Grupos de macros ElectricCR
        primary_toolbar_cmds = []
        try:
            from .commands.macros import register_predefined_macros
            macro_groups = register_predefined_macros(BASE_DIR)
            macro_groups = _merge_command_groups(macro_groups)
            # Orden personalizado desde config
            cfg = load_config()
            order = cfg.get('toolbar_order', [])
            if order and isinstance(order, list):
                # ordenar según 'order', dejando el resto al final
                order_index = {_normalize_toolbar_key(name): i for i, name in enumerate(order)}
                macro_groups.sort(key=lambda g: order_index.get(_normalize_toolbar_key(g[0]), 10_000))
            try:
                from .commands import macro_launcher as _launcher
                launcher_cmd = _launcher.register_macro_launcher(macro_groups)
                primary_toolbar_cmds.append(launcher_cmd)
                self.appendMenu("ElectricCR", [launcher_cmd])
            except Exception:
                pass
            for title, cmds in macro_groups:
                if cmds:
                    if modes_enabled and mode_manager is not None:
                        show_toolbar = mode_manager.should_create_toolbar(title, cfg)
                    else:
                        show_toolbar = _should_show_macro_toolbar(title, cfg)
                    # La antigua barra Areas se conserva en menu, pero su acceso
                    # principal pasa a la barra comun Espacios y Recintos.
                    if show_toolbar and _normalize_toolbar_key(title) != "areas":
                        self.appendToolbar(title, cmds)
                    self.appendMenu(title, cmds)

            producer_commands = [
                "ElectricCR_Areas_AreaPorClick",
                "ElectricCR_Areas_RectFromBoundaryLines",
                "ElectricCR_Areas_PoligonosRecintosDesdeArchWalls",
            ]
            producer_commands = [cmd for cmd in producer_commands if cmd in set(Gui.listCommands())]
            if common_room_commands:
                room_toolbar = (
                    common_room_commands[:3]
                    + ["Separator"]
                    + producer_commands
                    + ["Separator", common_room_commands[3]]
                )
                self.appendToolbar("Espacios y Recintos", room_toolbar)
                self.appendMenu("Espacios y Recintos", room_toolbar)

            # Mantener el acceso principal al flujo de deteccion junto al
            # selector de modos. En algunas sesiones de FreeCAD las barras
            # creadas dinamicamente despues de recargar quedan registradas,
            # pero Qt no llega a dibujarlas.
            detector_prefixes = (
                "ElectricCR_Deteccion_ColocarDetectores_NFPA_",
                "ElectricCR_Deteccion_ColocarDetectores_Poligonos_NFPA_",
            )
            for prefix in detector_prefixes:
                detector_cmds = [
                    name for name in Gui.listCommands() if name.startswith(prefix)
                ]
                if not detector_cmds:
                    continue
                detector_cmds.sort(
                    key=lambda name: int(name.rsplit("_", 1)[-1])
                    if name.rsplit("_", 1)[-1].isdigit() else 0
                )
                primary_toolbar_cmds.append(detector_cmds[-1])
        except Exception as e:
            App.Console.PrintError(f"ElectricCR: error registrando macros: {e}\n")

        # Manual mode panel command
        try:
            if modes_enabled and mode_panel is not None and mode_manager.panel_enabled(cfg):
                mode_panel_cmd = mode_panel.register_mode_panel_command()
                self.appendMenu("ElectricCR", [mode_panel_cmd])
        except Exception as e:
            App.Console.PrintWarning(f"[ElectricCR][Mode] command_warning={e}\n")

        # Comandos de chat/log
        try:
            from .commands import chatlog_cmds as _chat
            if _cfg_bool(cfg, "show_chat_toolbar", False):
                self.appendToolbar("Chat", [_chat.SAVE_CMD, _chat.OPEN_CMD, _chat.PRINT_CMD])
            self.appendMenu("Chat", [_chat.SAVE_CMD, _chat.OPEN_CMD, _chat.PRINT_CMD])
        except Exception:
            pass

        # Estadisticas de uso
        try:
            from .commands import usage_stats_cmds as _stats
            if _cfg_bool(cfg, "show_usage_stats_on_toolbar", False):
                primary_toolbar_cmds.append(_stats.STATS_CMD)
            self.appendMenu("ElectricCR", [_stats.STATS_CMD])
        except Exception:
            pass

        # Comando para recargar el workbench sin reiniciar FreeCAD
        try:
            from .commands.reload import COMMAND_NAME as RELOAD_CMD
            primary_toolbar_cmds.append(RELOAD_CMD)
            self.appendMenu("ElectricCR", [RELOAD_CMD])
        except Exception:
            pass

        if wall_side_cmd:
            self.appendMenu("ElectricCR", [wall_side_cmd])

        if primary_toolbar_cmds and _cfg_bool(cfg, "show_primary_toolbar", True):
            self.appendToolbar("ElectricCR", primary_toolbar_cmds)

        self._built = True

    def ContextMenu(self, recipient):
        """Keep object actions visible; FreeCAD may update selection after popup creation."""
        try:
            from .commands import wall_side as _wall_side
            self.appendContextMenu("ElectricCR", [_wall_side.COMMAND_NAME])
        except Exception as e:
            App.Console.PrintWarning(f"[ElectricCR][Context] menu_warning={e}\n")

    def Activated(self):
        global _LOG_ENABLED
        _LOG_ENABLED = True
        _connect_toolbar_logger()
        cfg = load_config()
        _install_windows_qt_layered_filter(cfg)
        _disable_windows_qt_ui_effects(cfg)
        try:
            from .ui import mode_manager as _mode_manager
            from .ui import mode_combo as _mode_combo
            from .ui import mode_panel as _mode_panel
            if _mode_manager.is_enabled(cfg):
                _mode_combo.ensure_mode_combo(cfg)
                if _mode_manager.panel_enabled(cfg):
                    _mode_panel.ensure_panel(show=False, cfg=cfg)
                _mode_manager.apply_mode(None, cfg)
            else:
                _mode_panel.hide_panel()
                _mode_manager.restore_legacy_visibility(cfg)
        except Exception as e:
            App.Console.PrintWarning(f"[ElectricCR][Mode] activate_warning={e}\n")
        # En Windows, el overlay de Snapper puede disparar spam de
        # UpdateLayeredWindowIndirect en ciertas combinaciones Qt/GPU.
        snapper_default = False if os.name == "nt" else True
        toolbar_default = False if os.name == "nt" else True
        enable_draft_toolbar = _cfg_bool(cfg, "draft_toolbar_autoload", toolbar_default)
        enable_snapper_overlay = _cfg_bool(cfg, "draft_snapper_overlay", snapper_default)
        enable_statusbar = _cfg_bool(cfg, "draft_statusbar", True)
        # Habilitar snap y barra de estado de Draft al entrar al WB
        try:
            import DraftTools  # noqa: F401
        except Exception:
            pass
        try:
            if hasattr(Gui, "draftToolBar"):
                if enable_draft_toolbar:
                    Gui.draftToolBar.Activated()
                else:
                    Gui.draftToolBar.Deactivated()
                    if os.name == "nt":
                        App.Console.PrintMessage(
                            "ElectricCR: autoactivacion de Draft toolbar desactivada "
                            "(config 'draft_toolbar_autoload': true para reactivarla).\n"
                        )
            if hasattr(Gui, "Snapper"):
                if enable_snapper_overlay:
                    Gui.Snapper.show()
                else:
                    Gui.Snapper.hide()
                    if os.name == "nt":
                        App.Console.PrintMessage(
                            "ElectricCR: overlay de Snapper desactivado en Windows "
                            "(config 'draft_snapper_overlay': true para reactivarlo).\n"
                        )
            if enable_statusbar:
                from draftutils import init_draft_statusbar
                init_draft_statusbar.show_draft_statusbar()
        except Exception:
            pass
        try:
            from CRBIMCore.commands.common_rooms import schedule_room_toolbar_layout

            schedule_room_toolbar_layout(
                [
                    "CRBIM_SelectRoom", "CRBIM_RoomInfo", "CRBIM_NameRoom",
                    "Separator",
                    "ElectricCR_Areas_AreaPorClick",
                    "ElectricCR_Areas_RectFromBoundaryLines",
                    "ElectricCR_Areas_PoligonosRecintosDesdeArchWalls",
                    "Separator", "CRBIM_RoomGuide",
                ],
                label_overrides={
                    "ElectricCR_Areas_AreaPorClick": "Recinto por click",
                    "ElectricCR_Areas_RectFromBoundaryLines": "Rectangulo desde limites",
                    "ElectricCR_Areas_PoligonosRecintosDesdeArchWalls": "Recintos desde muros BIM",
                },
            )
        except Exception as e:
            App.Console.PrintWarning(f"[ElectricCR][Rooms] toolbar_warning={e}\n")

    def Deactivated(self):
        global _LOG_ENABLED
        _LOG_ENABLED = False
        cfg = load_config()
        enable_statusbar = _cfg_bool(cfg, "draft_statusbar", True)
        try:
            from .ui import mode_panel as _mode_panel
            _mode_panel.hide_panel()
        except Exception:
            pass
        # Ocultar snap/estado cuando se sale del WB
        try:
            if hasattr(Gui, "draftToolBar"):
                Gui.draftToolBar.Deactivated()
            if hasattr(Gui, "Snapper"):
                Gui.Snapper.hide()
            if enable_statusbar:
                try:
                    from PySide2 import QtCore
                except Exception:
                    from PySide import QtCore
                from draftutils import init_draft_statusbar
                t = QtCore.QTimer()
                t.singleShot(700, init_draft_statusbar.hide_draft_statusbar)
        except Exception:
            pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


try:
    existing = set()
    try:
        wb_map = Gui.listWorkbenches()
        existing = set(wb_map.keys()) if isinstance(wb_map, dict) else set(wb_map)
    except Exception:
        existing = set()
    if 'ElectricCRWorkbench' not in existing:
        Gui.addWorkbench(ElectricCRWorkbench())
except Exception:
    pass
