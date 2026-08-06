# -*- coding: utf-8 -*-
"""Module: ElectricCR.tests.simulate_mode_interface
Purpose: Simulate the ElectricCR mode panel without launching FreeCAD.
Important: This is a lightweight stub test for reload safety and toolbar
visibility rules. It must not execute real macros.
Modified: 2026-07-08 00:00 Costa Rica.
Target: FreeCAD 1.1.1.
"""

import os
import sys
import types


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class Signal:
    def __init__(self):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)

    def disconnect(self):
        self._slots = []

    def emit(self, *args, **kwargs):
        for slot in list(self._slots):
            slot(*args, **kwargs)


class QWidget:
    def __init__(self, *args, **kwargs):
        self._object_name = ""
        self._visible = False

    def setObjectName(self, name):
        self._object_name = str(name)

    def objectName(self):
        return self._object_name

    def show(self):
        self._visible = True

    def hide(self):
        self._visible = False

    def isVisible(self):
        return self._visible


class QLabel(QWidget):
    def __init__(self, text="", *args, **kwargs):
        super().__init__()
        self.text_value = text

    def setText(self, text):
        self.text_value = str(text)

    def setStyleSheet(self, _style):
        pass


class QPushButton(QWidget):
    def __init__(self, text="", *args, **kwargs):
        super().__init__()
        self.text_value = text
        self.clicked = Signal()
        self.checked = False

    def setCheckable(self, _value):
        pass

    def setChecked(self, value):
        self.checked = bool(value)

    def setStyleSheet(self, _style):
        pass


class QComboBox(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.currentIndexChanged = Signal()
        self.items = []
        self.index = -1
        self._blocked = False

    def setMinimumWidth(self, _value):
        pass

    def setToolTip(self, _value):
        pass

    def addItem(self, text, data=None):
        self.items.append((str(text), data))
        if self.index < 0:
            self.index = 0

    def clear(self):
        self.items = []
        self.index = -1

    def count(self):
        return len(self.items)

    def itemData(self, index):
        return self.items[index][1]

    def itemText(self, index):
        return self.items[index][0]

    def setCurrentIndex(self, index):
        self.index = int(index)
        if not self._blocked:
            self.currentIndexChanged.emit(self.index)

    def currentIndex(self):
        return self.index

    def blockSignals(self, value):
        old = self._blocked
        self._blocked = bool(value)
        return old


class QVBoxLayout:
    def __init__(self, _parent=None):
        self.items = []

    def setContentsMargins(self, *_args):
        pass

    def setSpacing(self, _value):
        pass

    def addWidget(self, widget):
        self.items.append(widget)

    def addStretch(self, _value):
        pass


class ToggleAction:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class QToolBar(QWidget):
    def __init__(self, title):
        super().__init__()
        self._title = title
        self._visible = True
        self.actionTriggered = Signal()
        self.widgets = []

    def windowTitle(self):
        return self._title

    def setVisible(self, value):
        self._visible = bool(value)

    def toggleViewAction(self):
        return ToggleAction(self._title)

    def addWidget(self, widget):
        self.widgets.append(widget)
        return widget

    def findChild(self, cls, name):
        for child in self.findChildren(cls):
            if child.objectName() == name:
                return child
        return None

    def findChildren(self, cls):
        return [widget for widget in self.widgets if isinstance(widget, cls)]


class QDockWidget(QWidget):
    def __init__(self, title="", _parent=None):
        super().__init__()
        self._title = title
        self._widget = None
        self._visible = False

    def setAllowedAreas(self, _areas):
        pass

    def setWidget(self, widget):
        self._widget = widget

    def widget(self):
        return self._widget

    def raise_(self):
        pass


class MainWindow:
    def __init__(self):
        self.toolbars = []
        self.docks = []

    def addDockWidget(self, _area, dock):
        if dock not in self.docks:
            self.docks.append(dock)

    def findChild(self, cls, name):
        for child in self.findChildren(cls):
            if child.objectName() == name:
                return child
        return None

    def findChildren(self, cls):
        items = []
        if cls is QToolBar:
            items.extend(self.toolbars)
        if cls is QDockWidget:
            items.extend(self.docks)
        return items


class QtValues:
    LeftDockWidgetArea = 1
    RightDockWidgetArea = 2


class QtNamespace:
    DockWidgetArea = QtValues
    LeftDockWidgetArea = 1
    RightDockWidgetArea = 2


class ParamGroup:
    store = {}

    def GetString(self, key, default=""):
        return self.store.get(key, default)

    def SetString(self, key, value):
        self.store[key] = str(value)


class Console:
    @staticmethod
    def PrintMessage(message):
        print(str(message).rstrip())

    @staticmethod
    def PrintWarning(message):
        print(str(message).rstrip())

    @staticmethod
    def PrintError(message):
        print(str(message).rstrip())


main_window = MainWindow()
commands = {}
workbenches = {}


class Workbench:
    def appendToolbar(self, title, cmds):
        toolbar = QToolBar(title)
        toolbar.setObjectName(title)
        main_window.toolbars.append(toolbar)

    def appendMenu(self, _title, _cmds):
        pass


def install_stubs():
    freecad = types.ModuleType("FreeCAD")
    freecad.Console = Console
    freecad.ActiveDocument = None
    freecad.ParamGet = lambda _path: ParamGroup()
    sys.modules["FreeCAD"] = freecad

    freecadgui = types.ModuleType("FreeCADGui")
    freecadgui.Workbench = Workbench
    freecadgui.addIconPath = lambda _path: None
    freecadgui.addCommand = lambda name, obj: commands.setdefault(name, obj)
    freecadgui.listCommands = lambda: sorted(commands)
    freecadgui.runCommand = lambda _name: None
    freecadgui.listWorkbenches = lambda: workbenches
    freecadgui.addWorkbench = lambda wb: workbenches.setdefault("ElectricCRWorkbench", wb)
    freecadgui.getMainWindow = lambda: main_window
    freecadgui.activeWorkbench = lambda: workbenches.get("ElectricCRWorkbench")
    sys.modules["FreeCADGui"] = freecadgui

    qtcore = types.SimpleNamespace(Qt=QtNamespace)
    qtwidgets = types.SimpleNamespace(
        QWidget=QWidget,
        QLabel=QLabel,
        QPushButton=QPushButton,
        QComboBox=QComboBox,
        QVBoxLayout=QVBoxLayout,
        QToolBar=QToolBar,
        QDockWidget=QDockWidget,
    )
    for package_name in ("PySide6", "PySide2"):
        package = types.ModuleType(package_name)
        package.QtCore = qtcore
        package.QtWidgets = qtwidgets
        package.QtGui = types.SimpleNamespace()
        sys.modules[package_name] = package
        sys.modules[package_name + ".QtCore"] = qtcore
        sys.modules[package_name + ".QtWidgets"] = qtwidgets
        sys.modules[package_name + ".QtGui"] = package.QtGui

    for name in ("Draft", "DraftGui", "Arch", "ArchGui", "BIM", "DraftTools"):
        sys.modules[name] = types.ModuleType(name)

    for name in (
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
    ):
        commands.setdefault(name, object())


def normalize(text):
    import unicodedata

    value = str(text or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def visible_toolbar_names():
    return {normalize(tb.windowTitle()) for tb in main_window.toolbars if tb.isVisible()}


def assert_visible(expected):
    names = visible_toolbar_names()
    expected_norm = {normalize(name) for name in expected}
    expected_norm.update({"objetos", "draft compacto"})
    managed = {
        "areas",
        "objetos",
        "draft compacto",
        "iluminacion",
        "tomacorrientes",
        "conectar",
        "cajas",
        "tableros",
        "configuracion del proyecto",
        "importar y exportar",
    }
    assert "electriccr" in names
    assert names.intersection(managed) == expected_norm


def main():
    install_stubs()

    import ElectricCR.InitGui  # noqa: F401
    from ElectricCR.ui import mode_combo
    from ElectricCR.ui import mode_manager, mode_panel

    wb = workbenches["ElectricCRWorkbench"]
    wb.Initialize()
    wb.Activated()

    combo_a = mode_combo.ensure_mode_combo()
    combo_b = mode_combo.ensure_mode_combo()
    assert combo_a is combo_b
    assert combo_a.count() == 8

    panel_a = mode_panel.ensure_panel(show=True)
    panel_b = mode_panel.ensure_panel(show=False)
    assert panel_a is panel_b
    assert len(main_window.docks) == 1

    tests = [
        ("areas", ["Areas"]),
        ("iluminacion", ["Iluminacion"]),
        ("tomacorrientes", ["Tomacorrientes"]),
        ("conexiones", ["Conectar", "Cajas"]),
        ("tableros_calculo", ["Tableros", "Configuracion del proyecto"]),
        ("documentacion", ["Importar y Exportar"]),
        ("organizacion", ["Configuracion del proyecto"]),
        ("personalizado", [
            "Areas", "Iluminacion", "Tomacorrientes", "Conectar", "Cajas", "Tableros",
            "Configuracion del proyecto", "Importar y Exportar",
        ]),
    ]
    for mode_key, expected in tests:
        mode_manager.select_mode(mode_key)
        assert_visible(expected)

    combo_a.setCurrentIndex(1)
    assert mode_manager.get_last_mode() == "iluminacion"
    assert_visible(["Iluminacion"])

    main_window.toolbars = [
        tb for tb in main_window.toolbars if normalize(tb.windowTitle()) != "cajas"
    ]
    result = mode_manager.select_mode("conexiones")
    assert "Cajas" in result["missing"]

    print("simulate_mode_interface: PASS")


if __name__ == "__main__":
    main()
