# -*- coding: utf-8 -*-
"""Panel searchable para ejecutar macros ElectricCR registradas."""

import os
import unicodedata

import FreeCAD as App
import FreeCADGui as Gui

from .. import usage_log


COMMAND_NAME = "ElectricCR_MacroLauncher"
_MACRO_GROUPS = []
ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons")


def _icon(name):
    for candidate in (f"{name}.svg", f"{name}.png", name):
        path = os.path.join(ICONS_DIR, candidate)
        if os.path.exists(path):
            return path
    return ""


def _qmods():
    for candidate in ("PySide6", "PySide2", "PySide"):
        try:
            if candidate == "PySide":
                from PySide import QtCore, QtGui
                return QtGui, QtCore, QtGui
            module = __import__(candidate, fromlist=["QtCore", "QtGui", "QtWidgets"])
            return module.QtWidgets, module.QtCore, module.QtGui
        except Exception:
            continue
    return None, None, None


def _user_role(QtCore):
    try:
        return QtCore.Qt.ItemDataRole.UserRole
    except Exception:
        return QtCore.Qt.UserRole


def _normalize(text):
    s = str(text or "").strip().lower()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _command_obj(cmd_name):
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


def _command_resources(cmd_name):
    cmd = _command_obj(cmd_name)
    if cmd:
        for attr in ("GetResources", "getResources"):
            if hasattr(cmd, attr):
                try:
                    resources = getattr(cmd, attr)()
                    if isinstance(resources, dict):
                        return resources
                except Exception:
                    pass
    return {}


def _command_label(cmd_name):
    resources = _command_resources(cmd_name)
    label = resources.get("MenuText") or resources.get("ToolTip") or cmd_name
    return str(label).replace("&", "").strip() or cmd_name


def _command_icon(cmd_name):
    resources = _command_resources(cmd_name)
    pixmap = resources.get("Pixmap") or resources.get("PixmapPath") or ""
    try:
        return str(pixmap or "")
    except Exception:
        return ""


def _iter_macro_rows():
    for group_title, cmds in _MACRO_GROUPS:
        rows = []
        for cmd_name in cmds:
            if not cmd_name:
                continue
            rows.append((cmd_name, _command_label(cmd_name), _command_icon(cmd_name)))
        if rows:
            yield str(group_title or "Macros"), rows


def register_macro_launcher(macro_groups):
    global _MACRO_GROUPS
    clean_groups = []
    try:
        for title, cmds in macro_groups or []:
            clean_cmds = [str(cmd) for cmd in (cmds or []) if str(cmd or "").strip()]
            if clean_cmds:
                clean_groups.append((str(title or "Macros"), clean_cmds))
    except Exception:
        clean_groups = []
    _MACRO_GROUPS = clean_groups

    try:
        Gui.addCommand(COMMAND_NAME, MacroLauncherCmd())
    except Exception:
        pass
    return COMMAND_NAME


class MacroLauncherCmd:
    def GetResources(self):
        return {
            "Pixmap": _icon("Rayo"),
            "MenuText": "Panel de macros ElectricCR",
            "ToolTip": "Buscar y ejecutar macros ElectricCR por grupo o nombre.",
        }

    def IsActive(self):
        return True

    def Activated(self):
        try:
            usage_log.log_tool(COMMAND_NAME, {"source": "toolbar"})
        except Exception:
            pass

        QtWidgets, QtCore, QtGui = _qmods()
        if QtWidgets is None or QtCore is None or QtGui is None:
            App.Console.PrintMessage("ElectricCR: macros disponibles\n")
            for group_title, rows in _iter_macro_rows():
                App.Console.PrintMessage(f"[{group_title}]\n")
                for _cmd_name, label, _icon_path in rows:
                    App.Console.PrintMessage(f"  - {label}\n")
            return

        role = _user_role(QtCore)
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Panel de macros ElectricCR")
        dialog.resize(720, 520)

        layout = QtWidgets.QVBoxLayout(dialog)

        search = QtWidgets.QLineEdit(dialog)
        search.setPlaceholderText("Buscar por grupo o nombre...")
        layout.addWidget(search)

        tree = QtWidgets.QTreeWidget(dialog)
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Macro", "Grupo"])
        tree.setRootIsDecorated(True)
        tree.setAlternatingRowColors(True)
        try:
            tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        except Exception:
            tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(tree)

        status = QtWidgets.QLabel(dialog)
        layout.addWidget(status)

        button_row = QtWidgets.QHBoxLayout()
        run_button = QtWidgets.QPushButton("Ejecutar", dialog)
        close_button = QtWidgets.QPushButton("Cerrar", dialog)
        button_row.addStretch(1)
        button_row.addWidget(run_button)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        def item_command(item):
            if item is None:
                return ""
            try:
                value = item.data(0, role)
                return str(value or "")
            except Exception:
                return ""

        def populate():
            query = _normalize(search.text())
            tokens = [token for token in query.split() if token]
            tree.clear()
            total = 0

            for group_title, rows in _iter_macro_rows():
                group_key = _normalize(group_title)
                matching_rows = []
                for cmd_name, label, icon_path in rows:
                    haystack = _normalize(f"{group_title} {label} {cmd_name}")
                    if tokens and not all(token in haystack for token in tokens):
                        continue
                    matching_rows.append((cmd_name, label, icon_path))

                if tokens and not matching_rows and not all(token in group_key for token in tokens):
                    continue
                if not matching_rows and tokens:
                    matching_rows = rows

                group_item = QtWidgets.QTreeWidgetItem([group_title, ""])
                tree.addTopLevelItem(group_item)
                for cmd_name, label, icon_path in matching_rows:
                    child = QtWidgets.QTreeWidgetItem([label, group_title])
                    try:
                        child.setData(0, role, cmd_name)
                    except Exception:
                        pass
                    if icon_path:
                        try:
                            child.setIcon(0, QtGui.QIcon(icon_path))
                        except Exception:
                            pass
                    group_item.addChild(child)
                    total += 1
                group_item.setExpanded(True)

            status.setText(f"{total} macros")
            if tree.topLevelItemCount() > 0:
                first = tree.topLevelItem(0)
                if first and first.childCount() > 0:
                    tree.setCurrentItem(first.child(0))

        def run_current():
            item = tree.currentItem()
            cmd_name = item_command(item)
            if not cmd_name and item is not None and item.childCount() > 0:
                tree.setCurrentItem(item.child(0))
                cmd_name = item_command(item.child(0))
            if not cmd_name:
                return
            try:
                Gui.runCommand(cmd_name)
            except Exception as exc:
                App.Console.PrintError(f"ElectricCR: no se pudo ejecutar {cmd_name}: {exc}\n")

        search.textChanged.connect(populate)
        run_button.clicked.connect(run_current)
        close_button.clicked.connect(dialog.reject)
        tree.itemDoubleClicked.connect(lambda _item, _column: run_current())

        populate()
        search.setFocus()
        try:
            dialog.exec()
        except AttributeError:
            dialog.exec_()
