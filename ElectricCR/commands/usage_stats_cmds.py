#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
