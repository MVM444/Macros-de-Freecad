"""Shared global toolbar support for FreeCAD workbench loader macros."""

from __future__ import annotations

import os


TOOLBAR_NAME = "Macros"


def install_global_loader_toolbar(app, gui, macro_file, icon_path, menu_text, tooltip, log_prefix):
    handle = _LoaderToolbarHandle(app, gui, macro_file, icon_path, menu_text, tooltip, log_prefix)
    handle.install()
    return handle


class _LoaderToolbarHandle:
    def __init__(self, app, gui, macro_file, icon_path, menu_text, tooltip, log_prefix):
        self.app = app
        self.gui = gui
        self.macro_file = os.path.normpath(os.path.abspath(macro_file))
        self.script_name = os.path.basename(self.macro_file)
        self.icon_path = os.path.abspath(icon_path).replace(os.sep, "/") if icon_path else ""
        self.menu_text = str(menu_text)
        self.tooltip = str(tooltip)
        self.log_prefix = str(log_prefix)
        self.command_name = None
        self._qtcore = None
        self._qtgui = None
        self._qtwidgets = None

    def info(self, message):
        self.app.Console.PrintMessage(self.log_prefix + str(message) + "\n")

    def error(self, message):
        self.app.Console.PrintError(self.log_prefix + str(message) + "\n")

    def install(self):
        self.command_name = self._register_macro_command()
        self._register_global_toolbar()
        self.ensure_runtime(log=True)
        self._install_persistence()
        return self

    def refresh(self):
        self.ensure_runtime(log=False)
        self._schedule_persistence(0)

    def _group_names(self, group):
        try:
            return list(group.GetGroups())
        except Exception:
            return []

    def _next_macro_name(self, macros_group):
        highest = -1
        for name in self._group_names(macros_group):
            if not str(name).startswith("Std_Macro_"):
                continue
            try:
                highest = max(highest, int(str(name).split("_")[-1]))
            except Exception:
                pass
        return "Std_Macro_" + str(highest + 1)

    def _register_macro_command(self):
        macros_group = self.app.ParamGet("User parameter:BaseApp/Macro/Macros")
        existing = None
        for command_name in self._group_names(macros_group):
            command_group = macros_group.GetGroup(command_name)
            try:
                script = command_group.GetString("Script", "")
            except Exception:
                script = ""
            if os.path.normcase(os.path.basename(script)) == os.path.normcase(self.script_name):
                existing = str(command_name)
                break

        command_name = existing or self._next_macro_name(macros_group)
        command_group = macros_group.GetGroup(command_name)
        command_group.SetString("Script", self.script_name)
        command_group.SetString("Menu", self.menu_text)
        command_group.SetString("Tooltip", self.tooltip)
        command_group.SetString("WhatsThis", "")
        command_group.SetString("Statustip", self.tooltip)
        command_group.SetString("Pixmap", self.icon_path)
        command_group.SetString("Accel", "")
        command_group.SetBool("System", False)
        self.info(("Macro command updated: " if existing else "Macro command registered: ") + command_name)
        return command_name

    def _register_global_toolbar(self):
        toolbar_root = self.app.ParamGet("User parameter:BaseApp/Workbench/Global/Toolbar")
        toolbar_group = None
        max_index = 0
        for group_name in self._group_names(toolbar_root):
            group = toolbar_root.GetGroup(group_name)
            try:
                if group.GetString("Name", "") == TOOLBAR_NAME:
                    toolbar_group = group
                    break
            except Exception:
                pass
            if str(group_name).startswith("Custom_"):
                try:
                    max_index = max(max_index, int(str(group_name).split("_")[-1]))
                except Exception:
                    pass
        if toolbar_group is None:
            toolbar_group = toolbar_root.GetGroup("Custom_" + str(max_index + 1))
            toolbar_group.SetString("Name", TOOLBAR_NAME)
        toolbar_group.SetBool("Active", True)
        toolbar_group.SetString(self.command_name, "FreeCAD")
        self.app.ParamGet("User parameter:BaseApp/Preferences/MainWindow/Toolbars").SetBool(TOOLBAR_NAME, True)
        try:
            if hasattr(self.app, "saveParameter"):
                self.app.saveParameter()
        except Exception:
            pass
        self.info("Loader registered in global toolbar: " + TOOLBAR_NAME)

    def _load_qt(self):
        if self._qtwidgets is not None:
            return True
        for binding in ("PySide6", "PySide2", "PySide"):
            try:
                if binding == "PySide":
                    from PySide import QtCore, QtGui

                    self._qtcore, self._qtgui, self._qtwidgets = QtCore, QtGui, QtGui
                else:
                    module = __import__(binding, fromlist=["QtCore", "QtGui", "QtWidgets"])
                    self._qtcore, self._qtgui, self._qtwidgets = module.QtCore, module.QtGui, module.QtWidgets
                return True
            except Exception:
                continue
        return False

    def _toolbars(self, main_window):
        if not self._load_qt():
            return []
        try:
            return [
                toolbar
                for toolbar in main_window.findChildren(self._qtwidgets.QToolBar)
                if toolbar.windowTitle() == TOOLBAR_NAME or toolbar.objectName() == TOOLBAR_NAME
            ]
        except Exception:
            return []

    def _show_toolbars(self, toolbars):
        self.app.ParamGet("User parameter:BaseApp/Preferences/MainWindow/Toolbars").SetBool(TOOLBAR_NAME, True)
        for toolbar in toolbars:
            try:
                toolbar.toggleViewAction().setChecked(True)
            except Exception:
                pass
            try:
                toolbar.show()
                toolbar.setVisible(True)
            except Exception:
                pass

    def _action_is_standard(self, action):
        try:
            action_name = str(action.objectName())
        except Exception:
            action_name = ""
        try:
            action_text = str(action.text()).replace("&", "").strip().lower()
        except Exception:
            action_text = ""
        expected_texts = {self.menu_text.lower(), os.path.splitext(self.script_name)[0].lower()}
        return action_name == self.command_name or action_text in expected_texts

    def _runtime_action_name(self):
        safe = "".join(char if char.isalnum() else "_" for char in self.script_name)
        return "GlobalLoader_" + safe

    def _bind_fresh_execution(self, action):
        try:
            action.triggered.disconnect()
        except Exception:
            pass
        action.triggered.connect(self.execute_fresh)

    def ensure_runtime(self, log=False):
        if not self._load_qt():
            self.error("Could not access Qt modules to update toolbar")
            return
        try:
            main_window = self.gui.getMainWindow()
        except Exception as exc:
            self.error("Could not access FreeCAD main window: " + str(exc))
            return
        toolbars = self._toolbars(main_window)
        if not toolbars:
            try:
                toolbar = self._qtwidgets.QToolBar(TOOLBAR_NAME, main_window)
                toolbar.setObjectName(TOOLBAR_NAME)
                toolbar.setWindowTitle(TOOLBAR_NAME)
                main_window.addToolBar(toolbar)
                toolbars = [toolbar]
            except Exception as exc:
                self.error("Could not create runtime toolbar: " + str(exc))
                return

        toolbar = next((candidate for candidate in toolbars if candidate.isVisible()), toolbars[0])
        runtime_name = self._runtime_action_name()
        for action in list(toolbar.actions()):
            if self._action_is_standard(action):
                try:
                    action.setIcon(self._qtgui.QIcon(self.icon_path))
                    action.setToolTip(self.tooltip)
                except Exception:
                    pass
                self._show_toolbars(toolbars)
                return
            try:
                is_runtime = str(action.objectName()) == runtime_name
            except Exception:
                is_runtime = False
            if is_runtime:
                self._bind_fresh_execution(action)
                self._show_toolbars(toolbars)
                return

        action = self._qtgui.QAction(self._qtgui.QIcon(self.icon_path), self.menu_text, main_window)
        action.setObjectName(runtime_name)
        action.setToolTip(self.tooltip)
        self._bind_fresh_execution(action)
        toolbar.addAction(action)
        self._show_toolbars(toolbars)
        if log:
            self.info("Runtime loader button added to toolbar: " + TOOLBAR_NAME)

    def execute_fresh(self, checked=False):
        del checked
        namespace = {"__file__": self.macro_file, "__name__": "__main__"}
        try:
            with open(self.macro_file, "r", encoding="utf-8-sig") as handle:
                code = compile(handle.read(), self.macro_file, "exec")
            exec(code, namespace, namespace)
        except Exception as exc:
            self.error("Could not execute fresh loader from disk: " + str(exc))
            raise

    def _controller_attr(self):
        safe = "".join(char if char.isalnum() else "_" for char in self.script_name)
        return "_global_loader_toolbar_controller_" + safe

    def _install_persistence(self):
        if not self._load_qt():
            return
        main_window = self.gui.getMainWindow()
        attr_name = self._controller_attr()
        existing = getattr(main_window, attr_name, None)
        if existing is not None and hasattr(existing, "set_handle"):
            existing.set_handle(self)
            existing.schedule_show(0)
            return

        QtCore = self._qtcore

        class _ToolbarController(QtCore.QObject):
            def __init__(self, parent, loader_handle):
                super().__init__(parent)
                self.handle = loader_handle
                self.timer = QtCore.QTimer(self)
                self.timer.setSingleShot(True)
                self.timer.timeout.connect(self.show_toolbar)

            def set_handle(self, loader_handle):
                self.handle = loader_handle

            def schedule_show(self, delay=350):
                self.timer.start(max(0, int(delay)))

            def on_workbench_activated(self, *args):
                del args
                self.schedule_show(350)

            def show_toolbar(self):
                self.handle.ensure_runtime(log=False)

        controller = _ToolbarController(main_window, self)
        try:
            main_window.workbenchActivated.connect(controller.on_workbench_activated)
        except Exception as exc:
            self.error("Could not connect toolbar to workbench changes: " + str(exc))
        setattr(main_window, attr_name, controller)
        controller.schedule_show(0)
        self.info("Global loader toolbar persistence installed")

    def _schedule_persistence(self, delay):
        try:
            controller = getattr(self.gui.getMainWindow(), self._controller_attr(), None)
            if controller is not None:
                controller.schedule_show(delay)
        except Exception:
            pass
