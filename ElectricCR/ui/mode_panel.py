# -*- coding: utf-8 -*-
"""Module: ElectricCR.ui.mode_panel
Purpose: Provide the dockable ElectricCR mode selector panel and command.
Important: Reuse the dock widget named ElectricCRModePanel. Do not create
multiple panels on reload. Mode changes must be manual only.
Modified: 2026-07-07 09:18 Costa Rica.
Target: FreeCAD 1.1.1.
"""

import FreeCAD as App
import FreeCADGui as Gui

from .. import usage_log
from . import mode_manager


COMMAND_NAME = "ElectricCR_ModePanel"
PANEL_OBJECT_NAME = "ElectricCRModePanel"
CONTENT_OBJECT_NAME = "ElectricCRModePanelContent"


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


def _right_dock_area(QtCore):
    try:
        return QtCore.Qt.DockWidgetArea.RightDockWidgetArea
    except Exception:
        return QtCore.Qt.RightDockWidgetArea


def _all_dock_areas(QtCore):
    try:
        return (
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
            | QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
    except Exception:
        return QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea


def _find_panel(QtWidgets):
    mw = _main_window()
    if mw is None or QtWidgets is None:
        return None
    try:
        panel = mw.findChild(QtWidgets.QDockWidget, PANEL_OBJECT_NAME)
        if panel is not None:
            return panel
    except Exception:
        pass
    try:
        for panel in mw.findChildren(QtWidgets.QDockWidget):
            try:
                if panel.objectName() == PANEL_OBJECT_NAME:
                    return panel
            except Exception:
                pass
    except Exception:
        pass
    return None


def _mode_button_style(active):
    if active:
        return (
            "QPushButton {"
            "font-weight: 600;"
            "background-color: #dbeafe;"
            "border: 1px solid #2563eb;"
            "padding: 6px;"
            "text-align: left;"
            "}"
        )
    return (
        "QPushButton {"
        "padding: 6px;"
        "text-align: left;"
        "}"
    )


def _make_content(QtWidgets, QtCore, dock, cfg):
    root = QtWidgets.QWidget()
    root.setObjectName(CONTENT_OBJECT_NAME)

    layout = QtWidgets.QVBoxLayout(root)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    title = QtWidgets.QLabel("ElectricCR Modos")
    try:
        title.setStyleSheet("font-weight: 600;")
    except Exception:
        pass
    layout.addWidget(title)

    current_label = QtWidgets.QLabel("")
    layout.addWidget(current_label)

    buttons = {}

    def refresh():
        active = mode_manager.get_last_mode(cfg)
        current_label.setText("Modo actual: " + mode_manager.mode_label(active, cfg))
        for key, button in buttons.items():
            checked = key == active
            try:
                button.setChecked(checked)
            except Exception:
                pass
            try:
                button.setStyleSheet(_mode_button_style(checked))
            except Exception:
                pass

    def select_mode(mode_key):
        mode_manager.select_mode(mode_key, cfg)
        refresh()

    for mode_key, label, _log_name in mode_manager.mode_defs(cfg):
        button = QtWidgets.QPushButton(label)
        try:
            button.setCheckable(True)
        except Exception:
            pass
        button.clicked.connect(lambda _checked=False, key=mode_key: select_mode(key))
        buttons[mode_key] = button
        layout.addWidget(button)

    try:
        layout.addStretch(1)
    except Exception:
        pass

    hide_button = QtWidgets.QPushButton("Ocultar panel")
    hide_button.clicked.connect(dock.hide)
    layout.addWidget(hide_button)

    root._electriccr_refresh_modes = refresh
    refresh()
    return root


def ensure_panel(show=False, cfg=None):
    cfg = cfg or mode_manager.load_config()
    if not mode_manager.panel_enabled(cfg):
        mode_manager.print_mode("panel_enabled=False")
        return None

    QtWidgets, QtCore = _qt_modules()
    mw = _main_window()
    if QtWidgets is None or QtCore is None or mw is None:
        mode_manager.print_mode("panel_unavailable=True")
        return None

    panel = _find_panel(QtWidgets)
    reused = panel is not None
    if panel is None:
        panel = QtWidgets.QDockWidget("ElectricCR Modos", mw)
        panel.setObjectName(PANEL_OBJECT_NAME)
        try:
            panel.setAllowedAreas(_all_dock_areas(QtCore))
        except Exception:
            pass
        try:
            mw.addDockWidget(_right_dock_area(QtCore), panel)
        except Exception:
            pass

    # Rebuild content on every ensure call. The dock is reused, but old button
    # signal connections are discarded with the previous child widget.
    new_content = _make_content(QtWidgets, QtCore, panel, cfg)
    try:
        panel.setWidget(new_content)
    except Exception:
        pass

    if show:
        try:
            panel.show()
            panel.raise_()
        except Exception:
            pass

    mode_manager.print_mode("panel_reused=" + str(bool(reused)))
    return panel


def toggle_panel(cfg=None):
    cfg = cfg or mode_manager.load_config()
    QtWidgets, _QtCore = _qt_modules()
    panel = _find_panel(QtWidgets)
    if panel is None:
        return ensure_panel(show=True, cfg=cfg)
    try:
        if panel.isVisible():
            panel.hide()
        else:
            ensure_panel(show=True, cfg=cfg)
    except Exception:
        ensure_panel(show=True, cfg=cfg)
    return panel


def hide_panel():
    QtWidgets, _QtCore = _qt_modules()
    panel = _find_panel(QtWidgets)
    if panel is None:
        return
    try:
        panel.hide()
    except Exception:
        pass


class ToggleModePanelCommand:
    def GetResources(self):
        return {
            "MenuText": "ElectricCR Modos",
            "ToolTip": "Mostrar u ocultar el panel ElectricCR Modos.",
        }

    def Activated(self):
        try:
            usage_log.log_tool(COMMAND_NAME, {"source": "mode_panel"})
        except Exception:
            pass
        toggle_panel()

    def IsActive(self):
        return True


def register_mode_panel_command():
    try:
        Gui.addCommand(COMMAND_NAME, ToggleModePanelCommand())
    except Exception as exc:
        try:
            App.Console.PrintWarning(
                "[ElectricCR][Mode] command_register_warning=" + str(exc) + "\n"
            )
        except Exception:
            pass
    return COMMAND_NAME
