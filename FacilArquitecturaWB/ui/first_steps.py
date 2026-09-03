"""Welcome and Getting Started dialog for Facil Arquitectura.

Name: ui/first_steps.py
Purpose: offer a short first-use introduction while keeping the full manual in
ui.help_dialog.
Main behavior: show once per session unless disabled; present Demo, CAD and manual
Sketch entry paths; never create or modify documents by itself.
Maintenance notes:
- Keep this dialog short and route detailed explanations to FA Help.
- Use "buque/buques" in Spanish user-facing text.
- Keep CAD limitations and the DWG converter requirement visible.
- Use the Workbench i18n adapter for every user-visible string.
Version: 0.3.0
Date and time: 2026-09-02 15:35 America/Costa_Rica
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

from .. import i18n

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/FirstSteps"
SESSION_FLAG = "_FA_FirstStepsShownThisSession"
ICON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons"))


def _icon(name):
    return os.path.join(ICON_DIR, str(name)).replace(os.sep, "/")


def _exec_dialog(dialog):
    return dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()


def _add_step(layout, number, title, description, icon_name):
    row = QtWidgets.QHBoxLayout()
    icon = QtWidgets.QLabel()
    icon.setFixedSize(54, 54)
    icon.setPixmap(QtGui.QIcon(_icon(icon_name)).pixmap(48, 48))
    row.addWidget(icon)
    texts = QtWidgets.QVBoxLayout()
    heading = QtWidgets.QLabel("%d. %s" % (number, title))
    font = heading.font()
    font.setBold(True)
    heading.setFont(font)
    texts.addWidget(heading)
    body = QtWidgets.QLabel(description)
    body.setWordWrap(True)
    texts.addWidget(body)
    row.addLayout(texts, 1)
    layout.addLayout(row)


def show_startup_tips(force=False):
    if not getattr(FreeCAD, "GuiUp", False):
        return False
    params = FreeCAD.ParamGet(PARAM_PATH)
    if not force:
        if params.GetBool("dont_show_again", False):
            return False
        if bool(getattr(FreeCAD, SESSION_FLAG, False)):
            return False
    setattr(FreeCAD, SESSION_FLAG, True)

    dialog = QtWidgets.QDialog(FreeCADGui.getMainWindow())
    dialog.setWindowTitle(i18n.bi("Facil Arquitectura - Primeros pasos", "Facil Arquitectura - Getting Started"))
    dialog.setWindowIcon(QtGui.QIcon(_icon("fa_help.svg")))
    dialog.setMinimumWidth(680)
    layout = QtWidgets.QVBoxLayout(dialog)

    title = QtWidgets.QLabel(i18n.bi("Elija como quiere comenzar", "Choose how you want to start"))
    font = title.font()
    font.setBold(True)
    font.setPointSize(max(font.pointSize() + 2, 11))
    title.setFont(font)
    layout.addWidget(title)

    _add_step(
        layout,
        1,
        i18n.bi("Demo edificio", "Building Demo"),
        i18n.bi(
            "La forma recomendada de conocer el Workbench. Crea una casa de prueba en un documento nuevo y puede ejecutarse completa o guiada paso a paso.",
            "The recommended way to learn the Workbench. It creates a test house in a new document and can run as a complete or guided step-by-step build.",
        ),
        "demo_building.svg",
    )
    _add_step(
        layout,
        2,
        i18n.bi("Importar DWG/DXF", "Import DWG/DXF"),
        i18n.bi(
            "Para un plano existente: seleccione escala/unidad y capas utiles; prepare centros de paredes, ventanas y puertas; cierre buques que correspondan y luego genere los objetos BIM.",
            "For an existing drawing: select the correct scale/unit and useful layers; prepare wall, window, and door centerlines; close valid openings as needed; then generate BIM objects.",
        ),
        "import_cad_reference.svg",
    )
    _add_step(
        layout,
        3,
        i18n.bi("Dibujar o corregir Sketches", "Draw or correct Sketches"),
        i18n.bi(
            "Tambien puede empezar manualmente con Sketcher/Draft y continuar con paredes, puertas, ventanas, Recintos/Espacios BIM, techo y cielorraso.",
            "You can also start manually with Sketcher/Draft and continue with walls, doors, windows, Rooms/BIM Spaces, roof, and ceiling.",
        ),
        "walls_from_centerlines.svg",
    )

    warning = QtWidgets.QLabel(i18n.bi(
        "DWG requiere un convertidor externo configurado en FreeCAD (normalmente ODA File Converter); DXF se importa directamente. El flujo CAD ha sido probado con pocos ejemplos y puede requerir limpieza manual.",
        "DWG requires an external converter configured in FreeCAD (commonly ODA File Converter); DXF imports directly. The CAD workflow has been tested with a limited number of examples and may require manual cleanup.",
    ))
    warning.setWordWrap(True)
    warning_font = warning.font()
    warning_font.setBold(True)
    warning.setFont(warning_font)
    layout.addWidget(warning)

    purpose = QtWidgets.QLabel(i18n.bi(
        "FA no sustituye el trabajo arquitectonico profesional. Su objetivo es facilitar un modelo rapido y util como base para FreeCAD, ElectricCR, MEP y otros flujos de ingenieria. Recintos/Espacios BIM sigue siendo experimental, pero es esencial para esa integracion.",
        "FA does not replace professional architectural work. Its purpose is to facilitate a quick, useful model as a base for FreeCAD, ElectricCR, MEP, and other engineering workflows. Rooms/BIM Spaces remain experimental, but are essential for that integration.",
    ))
    purpose.setWordWrap(True)
    layout.addWidget(purpose)

    check = QtWidgets.QCheckBox(i18n.bi("No volver a mostrar este mensaje", "Do not show this message again"))
    check.setChecked(params.GetBool("dont_show_again", False))
    layout.addWidget(check)

    buttons = QtWidgets.QDialogButtonBox()
    help_button = buttons.addButton(i18n.bi("Ayuda", "Help"), QtWidgets.QDialogButtonBox.HelpRole)
    close_button = buttons.addButton(i18n.bi("Cerrar", "Close"), QtWidgets.QDialogButtonBox.RejectRole)
    layout.addWidget(buttons)

    def _help():
        from .help_dialog import show_help_dialog
        show_help_dialog(parent=dialog)

    help_button.clicked.connect(_help)
    close_button.clicked.connect(dialog.reject)
    _exec_dialog(dialog)
    params.SetBool("dont_show_again", bool(check.isChecked()))
    return True


def maybe_show_startup_tips():
    return show_startup_tips(force=False)


def schedule_startup_tips(delay_ms=350):
    try:
        QtCore.QTimer.singleShot(int(delay_ms), maybe_show_startup_tips)
        return True
    except Exception:
        return False
