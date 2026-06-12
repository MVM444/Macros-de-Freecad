#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
import FreeCADGui as Gui

from .. import usage_log


ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons")


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


def _icon(name):
    for candidate in (f"{name}.svg", f"{name}.png", name):
        p = os.path.join(ICONS_DIR, candidate)
        if os.path.exists(p):
            return p
    return ""


def _load_rows():
    data = usage_log.get_stats()
    tools = data.get("tools", {})
    rows = []
    if isinstance(tools, dict):
        for tool_id, rec in tools.items():
            if not isinstance(rec, dict):
                continue
            count = rec.get("count", 0)
            last_ts = rec.get("last_ts", "")
            try:
                count = int(count)
            except Exception:
                count = 0
            rows.append((count, str(tool_id), str(last_ts)))
    rows.sort(key=lambda r: r[0], reverse=True)
    return rows


class UsageStatsCmd:
    def GetResources(self):
        return {
            'Pixmap': _icon('Rayo'),
            'MenuText': 'Estadisticas de uso',
            'ToolTip': 'Muestra estadisticas de uso de herramientas.',
        }

    def IsActive(self):
        return True

    def Activated(self):
        QtWidgets = _qmods()
        rows = _load_rows()
        if QtWidgets is None:
            App.Console.PrintMessage("ElectricCR: estadisticas de uso\n")
            for count, tool_id, last_ts in rows[:50]:
                App.Console.PrintMessage(f"{count}\t{tool_id}\t{last_ts}\n")
            return

        dlg = QtWidgets.QDialog()
        dlg.setWindowTitle("Estadisticas de uso")
        layout = QtWidgets.QVBoxLayout(dlg)

        info = QtWidgets.QLabel(dlg)
        info.setText("Ranking de herramientas usadas (top 100).")
        layout.addWidget(info)

        table = QtWidgets.QTableWidget(dlg)
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Uso", "Herramienta", "Ultimo"])
        table.setRowCount(min(len(rows), 100))
        for i, (count, tool_id, last_ts) in enumerate(rows[:100]):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(count)))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(tool_id))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(last_ts))
        try:
            table.horizontalHeader().setStretchLastSection(True)
            table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        except Exception:
            pass
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout.addWidget(table)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)

        dlg.resize(820, 480)
        dlg.exec_()


STATS_CMD = 'ElectricCR_UsageStats'
Gui.addCommand(STATS_CMD, UsageStatsCmd())
