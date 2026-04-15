# -*- coding: utf-8 -*-
"""InitGui del workbench ElectricCR.

Registra el WB “Eléctrico CR”, agrega barras/menús con comandos Draft
disponibles y agrupa macros del repositorio. Pensado para cargarse
desde la carpeta `Macros` mediante un macro loader.
"""

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


def _normalize_toolbar_key(text: str) -> str:
    s = str(text or "").strip().lower()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = " ".join(s.split())
    return s


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
                usage_log.log_tool(cmd_name, {"source": "toolbar", "menu": menu_text})
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
    return cmd_name.startswith("Draft_") or cmd_name.startswith("BIM_") or cmd_name.startswith("Arch_")


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
        usage_log.log_tool(cmd_name, {"source": "toolbar_action", **meta})
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

        # BIM/Arch tools (e.g., Wall/Muro)
        try:
            bim_wall_candidates = ["BIM_Wall", "Arch_Wall"]
            bim_cmds = [c for c in bim_wall_candidates if c in available]
            if bim_cmds:
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
                self.appendToolbar(title, cmds)
                self.appendMenu(title, cmds)

        # Grupos de macros ElectricCR
        try:
            from .commands.macros import register_predefined_macros
            macro_groups = register_predefined_macros(BASE_DIR)
            # Orden personalizado desde config
            cfg = load_config()
            order = cfg.get('toolbar_order', [])
            if order and isinstance(order, list):
                # ordenar según 'order', dejando el resto al final
                order_index = {_normalize_toolbar_key(name): i for i, name in enumerate(order)}
                macro_groups.sort(key=lambda g: order_index.get(_normalize_toolbar_key(g[0]), 10_000))
            for title, cmds in macro_groups:
                if cmds:
                    self.appendToolbar(title, cmds)
                    self.appendMenu(title, cmds)
        except Exception as e:
            App.Console.PrintError(f"ElectricCR: error registrando macros: {e}\n")

        # Comandos de chat/log
        try:
            from .commands import chatlog_cmds as _chat
            self.appendToolbar("Chat", [_chat.SAVE_CMD, _chat.OPEN_CMD, _chat.PRINT_CMD])
            self.appendMenu("Chat", [_chat.SAVE_CMD, _chat.OPEN_CMD, _chat.PRINT_CMD])
        except Exception:
            pass

        # Estadisticas de uso
        try:
            from .commands import usage_stats_cmds as _stats
            self.appendMenu("ElectricCR", [_stats.STATS_CMD])
        except Exception:
            pass

        # Comando para recargar el workbench sin reiniciar FreeCAD
        try:
            from .commands.reload import COMMAND_NAME as RELOAD_CMD
            self.appendToolbar("ElectricCR", [RELOAD_CMD])
            self.appendMenu("ElectricCR", [RELOAD_CMD])
        except Exception:
            pass

        self._built = True

    def Activated(self):
        global _LOG_ENABLED
        _LOG_ENABLED = True
        _connect_toolbar_logger()
        cfg = load_config()
        _install_windows_qt_layered_filter(cfg)
        _disable_windows_qt_ui_effects(cfg)
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

    def Deactivated(self):
        global _LOG_ENABLED
        _LOG_ENABLED = False
        cfg = load_config()
        enable_statusbar = _cfg_bool(cfg, "draft_statusbar", True)
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
