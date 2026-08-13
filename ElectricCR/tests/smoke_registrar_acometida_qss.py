# -*- coding: utf-8 -*-
"""Render and validate the Registrar acometida panel under light/dark themes."""

from pathlib import Path
import runpy
import sys
import tempfile

import FreeCAD as App
import Part


REPO_ROOT = Path(__file__).resolve().parents[2]
MACRO_PATH = REPO_ROOT / "Configuracion del proyecto" / "Registrar_Acometida_y_Ruta.FCMacro"
ARTIFACT_DIR = Path(tempfile.gettempdir()) / "electriccr_acometida_qss_validation"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

namespace = runpy.run_path(str(MACRO_PATH), run_name="electriccr_acometida_qss_test")
Dialog = namespace["_AcometidaDialog"]
QtCore = namespace["QtCore"]
QtWidgets = namespace["QtWidgets"]
popup_qss = namespace["_acometida_combo_popup_qss"]()


class _Selection(object):
    @staticmethod
    def getSelection():
        return []

    @staticmethod
    def getSelectionEx():
        return []


class _HeadlessGui(object):
    Selection = _Selection()


Dialog.__init__.__globals__["Gui"] = _HeadlessGui

app = QtWidgets.QApplication.instance()
if app is None:
    app = QtWidgets.QApplication(sys.argv)

doc = App.newDocument("SmokeAcometidaQSS")
medidor = doc.addObject("Part::Feature", "MedidorPrueba")
medidor.Label = "Medidor prueba"
medidor.Shape = Part.makeBox(200.0, 150.0, 300.0)
tablero = doc.addObject("Part::Feature", "TableroPrueba")
tablero.Label = "Tablero principal prueba"
tablero.Shape = Part.makeBox(400.0, 150.0, 600.0)
wire = doc.addObject("Part::Feature", "WirePrueba")
wire.Label = "Wire manual prueba"
wire.Shape = Part.makePolygon([App.Vector(0, 0, 0), App.Vector(1000, 0, 0)])
area = doc.addObject("Part::Feature", "AreaPrueba")
area.Label = "Area proyecto prueba"
area.Shape = Part.Face(Part.makePolygon([
    App.Vector(0, 0, 0),
    App.Vector(5000, 0, 0),
    App.Vector(5000, 4000, 0),
    App.Vector(0, 4000, 0),
    App.Vector(0, 0, 0),
]))
doc.recompute()

dark_theme = """
QWidget { background: #20242b; color: #f2f2f2; }
QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit { background: #252a33; color: #f2f2f2; }
QTabBar::tab { background: #303743; color: #dce3ec; }
"""
light_theme = """
QWidget { background: #eeeeee; color: #202020; }
QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit { background: #ffffff; color: #202020; }
QTabBar::tab { background: #e5e5e5; color: #202020; }
"""

required_qss = (
    "QWidget#AcometidaTabPage {",
    "QCheckBox {",
    "QCheckBox:disabled {",
    "QTabBar::tab {",
    "QTabBar::tab:selected {",
    "QTabBar::tab:disabled {",
    "QComboBox QAbstractItemView {",
    "QComboBox QAbstractItemView::item:selected {",
    "QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QLineEdit:disabled {",
    "selection-background-color: #2d6fb8;",
    "selection-color: #ffffff;",
)

required_direct_popup_qss = (
    "QAbstractItemView#AcometidaComboPopup {",
    "QAbstractItemView#AcometidaComboPopup::item {",
    "QAbstractItemView#AcometidaComboPopup::item:selected {",
    "background-color: #ffffff;",
    "color: #1f2d3d;",
    "selection-background-color: #2d6fb8;",
    "selection-color: #ffffff;",
)


def _save_widget(widget, filename):
    widget.repaint()
    app.processEvents()
    path = ARTIFACT_DIR / filename
    if not widget.grab().save(str(path), "PNG"):
        raise AssertionError("No se pudo guardar {}".format(path))
    return path


def _validate_and_render(theme_name, theme_qss):
    app.setStyleSheet(theme_qss)
    form = Dialog(doc, parent=None)
    form.sp_zroute.setValue(2500.0)
    form.sp_area_total.setValue(20.0)
    form.sp_vln.setEnabled(False)
    form.resize(760, 650)
    # Gui.Control reparents the form into FreeCAD's Tasks dock. Reproduce that
    # topology because the combo popup is a separate top-level Qt window.
    host = QtWidgets.QMainWindow()
    host.resize(900, 720)
    dock = QtWidgets.QDockWidget("Tareas", host)
    dock.setWidget(form)
    qt = QtCore.Qt
    dock_enum = getattr(qt, "DockWidgetArea", qt)
    right_area = getattr(dock_enum, "RightDockWidgetArea")
    host.addDockWidget(right_area, dock)
    host.show()
    app.processEvents()

    qss = form.styleSheet()
    for token in required_qss:
        if token not in qss:
            raise AssertionError("Falta regla QSS: {}".format(token))
    if not form.sp_zroute.text().strip() or abs(form.sp_zroute.value() - 2500.0) > 0.01:
        raise AssertionError("Altura ruta Z no muestra correctamente 2500.0")
    if not form.sp_area_total.text().strip() or abs(form.sp_area_total.value() - 20.0) > 0.001:
        raise AssertionError("Area total no muestra su valor")
    for combo in (
        form.cb_medidor,
        form.cb_tablero,
        form.cb_wire_manual,
        form.cb_area_obj,
        form.cb_system,
        form.cb_norma,
        form.cb_demanda_metodo,
        form.cb_material,
        form.cb_awg,
    ):
        if not combo.currentText().strip():
            raise AssertionError("Combo sin texto visible")
        direct_qss = combo.view().styleSheet()
        for token in required_direct_popup_qss:
            if token not in direct_qss:
                raise AssertionError("Popup sin regla QSS directa: {}".format(token))
        if direct_qss != popup_qss:
            raise AssertionError("El popup no usa el QSS directo canonico")
        if combo.view().viewport().styleSheet() != "background-color: #ffffff; color: #1f2d3d;":
            raise AssertionError("El viewport del popup no tiene fondo y texto explicitos")
    expected_checks = (
        "Usar wire manual para longitud/calculo",
        "Crear/usar grupo Proyecto_Acometida",
        "Reemplazar wire anterior de esta misma acometida",
    )
    actual_checks = tuple(box.text() for box in form.findChildren(QtWidgets.QCheckBox))
    for expected in expected_checks:
        if expected not in actual_checks:
            raise AssertionError("Falta checkbox: {}".format(expected))

    tabs = form.findChild(QtWidgets.QTabWidget)
    if tabs is None:
        raise AssertionError("No se encontro QTabWidget")
    expected_tabs = ("Datos Basicos", "Demanda Auto", "Seleccion Final")
    actual_tabs = tuple(tabs.tabText(i) for i in range(tabs.count()))
    if actual_tabs != expected_tabs:
        raise AssertionError("Pestanas inesperadas: {}".format(actual_tabs))

    paths = []
    for index, suffix in enumerate(("basicos", "demanda", "seleccion")):
        tabs.setCurrentIndex(index)
        app.processEvents()
        paths.append(_save_widget(form, "{}_{}.png".format(theme_name, suffix)))

    if form.cb_medidor.count() > 1:
        form.cb_medidor.setCurrentIndex(1)
    form.cb_medidor.showPopup()
    app.processEvents()
    form.cb_medidor.view().setFocus()
    form.cb_medidor.view().setCurrentIndex(form.cb_medidor.model().index(form.cb_medidor.currentIndex(), 0))
    app.processEvents()
    popup = form.cb_medidor.view().window()
    paths.append(_save_widget(popup, "{}_combo_popup.png".format(theme_name)))
    form.cb_medidor.hidePopup()
    host.close()
    host.deleteLater()
    app.processEvents()
    return paths


old_qss = app.styleSheet()
artifacts = []
try:
    artifacts.extend(_validate_and_render("dark", dark_theme))
    artifacts.extend(_validate_and_render("light", light_theme))
finally:
    app.setStyleSheet(old_qss)

print("PASS Registrar_Acometida_y_Ruta QSS")
for artifact in artifacts:
    print("ARTIFACT {}".format(artifact))

App.closeDocument(doc.Name)
