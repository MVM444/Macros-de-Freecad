# -*- coding: utf-8 -*-
"""Small Qt dock lifecycle helpers for ElectricCR.

Revision: 2026-08-10

This module only manages ElectricCR-owned QDockWidget instances. It never
changes Combo View, Tasks, the central widget or the global MainWindow layout.
"""

import FreeCAD as App


def _qt_widgets():
    for binding in ("PySide6", "PySide2", "PySide"):
        try:
            if binding == "PySide":
                from PySide import QtGui
                return QtGui
            module = __import__(binding, fromlist=["QtWidgets"])
            return module.QtWidgets
        except Exception:
            continue
    return None


def _is_valid(widget):
    if widget is None:
        return False
    for name in ("shiboken6", "shiboken2"):
        try:
            shiboken = __import__(name)
            return bool(shiboken.isValid(widget))
        except ImportError:
            continue
        except Exception:
            return False
    try:
        widget.objectName()
        return True
    except Exception:
        return False


def find_docks(main_window, object_name):
    """Return every valid QDockWidget with the exact stable objectName."""
    QtWidgets = _qt_widgets()
    if main_window is None or QtWidgets is None or not object_name:
        return []
    try:
        docks = list(main_window.findChildren(QtWidgets.QDockWidget) or [])
    except Exception:
        return []
    result = []
    for dock in docks:
        if not _is_valid(dock):
            continue
        try:
            if str(dock.objectName()) == str(object_name):
                result.append(dock)
        except Exception:
            continue
    return result


def _log(prefix, event, object_name, count=None):
    suffix = ""
    if count is not None:
        suffix = " count={}".format(int(count))
    App.Console.PrintMessage(
        "{} {} name={}{}\n".format(prefix, event, object_name, suffix)
    )


def get_reusable_dock(main_window, object_name, log_prefix="[UI-DOCK][ElectricCR]"):
    """Return one existing dock and schedule historical duplicates for deletion.

    The first valid instance is retained. No new dock is created while
    duplicates are being cleaned, and the event loop is not forced.
    """
    docks = find_docks(main_window, object_name)
    if not docks:
        return None

    keeper = docks[0]
    if len(docks) > 1:
        _log(log_prefix, "duplicate_found", object_name, len(docks))
        for duplicate in docks[1:]:
            try:
                duplicate.close()
            except Exception:
                pass
            try:
                duplicate.deleteLater()
                _log(log_prefix, "duplicate_removed", object_name)
            except Exception:
                pass
    _log(log_prefix, "reusing", object_name)
    return keeper


def show_dock(dock, object_name, log_prefix="[UI-DOCK][ElectricCR]"):
    """Show and raise an owned dock without altering global dock topology."""
    if not _is_valid(dock):
        return False
    try:
        dock.show()
        dock.raise_()
    except Exception:
        return False
    _log(log_prefix, "shown", object_name)
    return True


def log_created(object_name, log_prefix="[UI-DOCK][ElectricCR]"):
    _log(log_prefix, "creating", object_name)


def is_current(widget, current_widget):
    """Identity-safe guard for destroyed callbacks."""
    return widget is not None and widget is current_widget


__all__ = [
    "find_docks",
    "get_reusable_dock",
    "show_dock",
    "log_created",
    "is_current",
]
