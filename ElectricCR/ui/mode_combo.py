# -*- coding: utf-8 -*-
"""Module: ElectricCR.ui.mode_combo
Purpose: Add a compact work-mode combo box to the ElectricCR toolbar.
Important: Reuse the widget named ElectricCRModeCombo. Do not create duplicate
combo boxes on reload. Mode changes must be manual only.
Modified: 2026-07-07 09:33 Costa Rica.
Target: FreeCAD 1.1.1.
"""

import FreeCADGui as Gui

from . import mode_manager


COMBO_OBJECT_NAME = "ElectricCRModeCombo"
TOOLBAR_NAME = "ElectricCR"


def _qt_modules():
    for candidate in ("PySide6", "PySide2", "PySide"):
        try:
            if candidate == "PySide":
                from PySide import QtGui
                return QtGui
            module = __import__(candidate, fromlist=["QtWidgets"])
            return module.QtWidgets
        except Exception:
            continue
    return None


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


def _find_toolbar(QtWidgets):
    mw = _main_window()
    if mw is None or QtWidgets is None:
        return None
    try:
        toolbars = mw.findChildren(QtWidgets.QToolBar)
    except Exception:
        toolbars = []
    for toolbar in toolbars:
        if mode_manager.normalize_name(_toolbar_title(toolbar)) == mode_manager.normalize_name(TOOLBAR_NAME):
            return toolbar
    return None


def _find_combo(QtWidgets, toolbar):
    if toolbar is None or QtWidgets is None:
        return None
    try:
        combo = toolbar.findChild(QtWidgets.QComboBox, COMBO_OBJECT_NAME)
        if combo is not None:
            return combo
    except Exception:
        pass
    try:
        for combo in toolbar.findChildren(QtWidgets.QComboBox):
            try:
                if combo.objectName() == COMBO_OBJECT_NAME:
                    return combo
            except Exception:
                pass
    except Exception:
        pass
    return None


def _item_data(combo, index):
    try:
        value = combo.itemData(index)
        if value:
            return str(value)
    except Exception:
        pass
    try:
        text = combo.itemText(index)
    except Exception:
        text = ""
    for key, label, _log_name in mode_manager.mode_defs():
        if label == text:
            return key
    return ""


def _disconnect_combo(combo):
    try:
        combo.currentIndexChanged.disconnect()
    except Exception:
        pass


def refresh_mode_combo(combo=None, cfg=None):
    cfg = cfg or mode_manager.load_config()
    QtWidgets = _qt_modules()
    if combo is None:
        combo = _find_combo(QtWidgets, _find_toolbar(QtWidgets))
    if combo is None:
        return None

    active = mode_manager.get_last_mode(cfg)
    target_index = 0
    try:
        count = combo.count()
    except Exception:
        count = 0
    for index in range(count):
        if _item_data(combo, index) == active:
            target_index = index
            break
    try:
        old_state = combo.blockSignals(True)
    except Exception:
        old_state = None
    try:
        combo.setCurrentIndex(target_index)
    except Exception:
        pass
    try:
        combo.blockSignals(bool(old_state))
    except Exception:
        pass
    return combo


def ensure_mode_combo(cfg=None):
    cfg = cfg or mode_manager.load_config()
    if not mode_manager.is_enabled(cfg):
        return None

    QtWidgets = _qt_modules()
    toolbar = _find_toolbar(QtWidgets)
    if toolbar is None:
        mode_manager.print_mode("mode_combo_toolbar_missing=ElectricCR")
        return None
    if QtWidgets is None or not hasattr(QtWidgets, "QComboBox"):
        mode_manager.print_mode("mode_combo_unavailable=True")
        return None

    combo = _find_combo(QtWidgets, toolbar)
    reused = combo is not None
    if combo is None:
        combo = QtWidgets.QComboBox(toolbar)
        combo.setObjectName(COMBO_OBJECT_NAME)
        try:
            combo.setMinimumWidth(170)
        except Exception:
            pass
        try:
            combo.setToolTip("ElectricCR modo de trabajo")
        except Exception:
            pass
        try:
            toolbar.addWidget(combo)
        except Exception as exc:
            mode_manager.print_mode("mode_combo_add_failed=" + str(exc))
            return None

    _disconnect_combo(combo)
    try:
        old_state = combo.blockSignals(True)
    except Exception:
        old_state = None
    try:
        combo.clear()
        for mode_key, label, _log_name in mode_manager.mode_defs(cfg):
            try:
                combo.addItem(label, mode_key)
            except TypeError:
                combo.addItem(label)
    except Exception as exc:
        mode_manager.print_mode("mode_combo_populate_failed=" + str(exc))
    try:
        combo.blockSignals(bool(old_state))
    except Exception:
        pass

    def on_mode_changed(index):
        mode_key = _item_data(combo, index)
        if not mode_key:
            return
        mode_manager.select_mode(mode_key, cfg)
        refresh_mode_combo(combo, cfg)

    try:
        combo.currentIndexChanged.connect(on_mode_changed)
    except Exception as exc:
        mode_manager.print_mode("mode_combo_connect_failed=" + str(exc))

    refresh_mode_combo(combo, cfg)
    mode_manager.print_mode("mode_combo_reused=" + str(bool(reused)))
    return combo
