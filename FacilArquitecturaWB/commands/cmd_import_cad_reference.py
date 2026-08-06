"""FA_ImportCADReference command.

Descripcion: selecciona DWG/DXF, solicita la unidad real e importa en documento nuevo.
Fecha: 2026-07-31
Version: 0.1.0
Instrucciones: conservar el ultimo directorio y unidad para acelerar usos repetidos.
"""

from __future__ import annotations

import os
import time

import FreeCAD
import FreeCADGui

from ..core.cad_reference_import import import_cad_reference
from ..core.command_errors import handle_command_exception


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "import_cad_reference.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))
PREFS_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/ImportCAD"
UNIT_OPTIONS = (
    ("auto", "Automatico desde cabecera"),
    ("m", "Metros (1 unidad = 1 m)"),
    ("mm", "Milimetros (1 unidad = 1 mm)"),
    ("cm", "Centimetros (1 unidad = 1 cm)"),
)


def _qt_widgets():
    for binding in ("PySide6", "PySide2"):
        try:
            module = __import__(binding, fromlist=["QtWidgets"])
            return module.QtWidgets
        except Exception:
            continue
    from PySide import QtGui

    return QtGui


def _dialog_value(value):
    if isinstance(value, (tuple, list)):
        return value[0] if value else ""
    return value or ""


def _choose_source_and_unit():
    QtWidgets = _qt_widgets()
    parent = FreeCADGui.getMainWindow()
    prefs = FreeCAD.ParamGet(PREFS_PATH)
    last_directory = prefs.GetString("LastDirectory", "")
    if not last_directory or not os.path.isdir(last_directory):
        last_directory = os.path.expanduser("~")

    source = _dialog_value(
        QtWidgets.QFileDialog.getOpenFileName(
            parent,
            "Importar referencia CAD en documento nuevo",
            last_directory,
            "Planos CAD (*.dwg *.dxf);;DWG (*.dwg);;DXF (*.dxf)",
        )
    )
    if not source:
        return None

    keys = [item[0] for item in UNIT_OPTIONS]
    labels = [item[1] for item in UNIT_OPTIONS]
    last_unit = prefs.GetString("LastUnit", "auto")
    current = keys.index(last_unit) if last_unit in keys else 0
    selected_label, accepted = QtWidgets.QInputDialog.getItem(
        parent,
        "Unidad real del dibujo",
        "Seleccione la unidad usada por las coordenadas del archivo:\n"
        "(esta eleccion corrige cabeceras DWG/DXF incorrectas)",
        labels,
        current,
        False,
    )
    if not accepted:
        return None
    selected_index = labels.index(str(selected_label))
    unit_key = keys[selected_index]
    prefs.SetString("LastDirectory", os.path.dirname(os.path.abspath(source)))
    prefs.SetString("LastUnit", unit_key)
    return source, unit_key


def run_import_dialog():
    selection = _choose_source_and_unit()
    if not selection:
        return None
    source, unit_key = selection
    result = import_cad_reference(source, unit_key=unit_key, fit_view=True)

    QtWidgets = _qt_widgets()
    bounds = result.get("placement_bounds") or {}
    minimum = bounds.get("min_mm")
    maximum = bounds.get("max_mm")
    bounds_text = ""
    if minimum and maximum:
        bounds_text = (
            "\nRango de inserciones: %.2f a %.2f m en X; %.2f a %.2f m en Y."
            % (minimum[0] / 1000.0, maximum[0] / 1000.0, minimum[1] / 1000.0, maximum[1] / 1000.0)
        )
    QtWidgets.QMessageBox.information(
        FreeCADGui.getMainWindow(),
        "Importacion CAD completada",
        (
            "Se creo el documento nuevo '%s'.\n"
            "Objetos importados: %d.\n"
            "Escala efectiva: 1 unidad CAD = %.6g mm.%s\n\n"
            "El documento permanece sin guardar."
        )
        % (
            result["document"].Label,
            result["imported_object_count"],
            result["resolved_mm_per_unit"],
            bounds_text,
        ),
    )
    return result


class CommandClass:
    """FreeCAD command for importing a CAD reference safely."""

    CommandName = "FA_ImportCADReference_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Importar referencia DWG/DXF",
            "ToolTip": "Importar DWG o DXF en un documento nuevo, con unidad real controlada.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            run_import_dialog()
        except Exception as exc:
            handle_command_exception("FA Importar referencia DWG/DXF", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
