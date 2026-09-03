"""FA_ImportCADReference command.

Descripcion: selecciona DWG/DXF, solicita la unidad real e importa en documento nuevo.
Fecha: 2026-09-02
Version: 0.2.0
Instrucciones: conservar el ultimo directorio y unidad para acelerar usos repetidos.
"""

from __future__ import annotations

import os
import time

import FreeCAD
import FreeCADGui

from .. import i18n
from ..core.cad_reference_import import _import_log, import_cad_reference
from ..core.command_errors import handle_command_exception


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "import_cad_reference.svg")
).replace(os.sep, "/")
PREFS_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/ImportCAD"
def _unit_options():
    return (
        ("auto", i18n.bi("Automatico desde cabecera", "Automatic from header")),
        ("m", i18n.bi("Metros (1 unidad = 1 m)", "Meters (1 unit = 1 m)")),
        ("mm", i18n.bi("Milimetros (1 unidad = 1 mm)", "Millimeters (1 unit = 1 mm)")),
        ("cm", i18n.bi("Centimetros (1 unidad = 1 cm)", "Centimeters (1 unit = 1 cm)")),
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


def _qt_core():
    for binding in ("PySide6", "PySide2"):
        try:
            module = __import__(binding, fromlist=["QtCore"])
            return module.QtCore
        except Exception:
            continue
    from PySide import QtCore

    return QtCore


def _schedule_event_loop_probes(origin):
    QtCore = _qt_core()
    for delay in (0, 100, 500, 1000):
        QtCore.QTimer.singleShot(
            delay,
            lambda value=delay: _import_log(
                "QTimer despues del retorno",
                origin=origin,
                delay_ms=value,
            ),
        )


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
            i18n.bi("Importar referencia CAD en documento nuevo", "Import CAD reference into a new document"),
            last_directory,
            i18n.bi("Planos CAD (*.dwg *.dxf);;DWG (*.dwg);;DXF (*.dxf)", "CAD drawings (*.dwg *.dxf);;DWG (*.dwg);;DXF (*.dxf)"),
        )
    )
    if not source:
        return None

    unit_options = _unit_options()
    keys = [item[0] for item in unit_options]
    labels = [item[1] for item in unit_options]
    last_unit = prefs.GetString("LastUnit", "auto")
    current = keys.index(last_unit) if last_unit in keys else 0
    selected_label, accepted = QtWidgets.QInputDialog.getItem(
        parent,
        i18n.bi("Unidad real del dibujo", "Actual drawing unit"),
        i18n.bi(
            "Seleccione la unidad usada por las coordenadas del archivo:\n(esta eleccion corrige cabeceras DWG/DXF incorrectas)",
            "Select the unit used by the file coordinates:\n(this choice corrects incorrect DWG/DXF headers)",
        ),
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
    operation_started = time.perf_counter()
    _import_log("run_import_dialog inicio")
    selection = _choose_source_and_unit()
    if not selection:
        _import_log("run_import_dialog cancelado", operation_started)
        return None
    source, unit_key = selection
    try:
        result = import_cad_reference(source, unit_key=unit_key, fit_view=True)
    except RuntimeError as exc:
        if str(source).lower().endswith(".dwg") and "convert" in str(exc).lower():
            QtWidgets = _qt_widgets()
            QtWidgets.QMessageBox.warning(
                FreeCADGui.getMainWindow(),
                i18n.bi("No se pudo convertir el DWG", "DWG conversion failed"),
                i18n.bi(
                    "FreeCAD necesita un convertidor DWG externo configurado (normalmente ODA File Converter). Configure el convertidor en FreeCAD o convierta el archivo previamente a DXF y vuelva a intentarlo.",
                    "FreeCAD needs a configured external DWG converter (commonly ODA File Converter). Configure the converter in FreeCAD, or convert the file to DXF first and try again.",
                ),
            )
            return None
        raise
    _import_log("import_cad_reference retorno a dialogo", operation_started)

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
    _import_log("QMessageBox final aparicion")
    english_bounds = ""
    if minimum and maximum:
        english_bounds = (
            "\nInsertion range: %.2f to %.2f m in X; %.2f to %.2f m in Y."
            % (minimum[0] / 1000.0, maximum[0] / 1000.0, minimum[1] / 1000.0, maximum[1] / 1000.0)
        )
    spanish_message = (
        "Se creo el documento nuevo '%s'.\nObjetos importados: %d.\nEscala efectiva: 1 unidad CAD = %.6g mm.%s\n\nEl documento permanece sin guardar."
        % (result["document"].Label, result["imported_object_count"], result["resolved_mm_per_unit"], bounds_text)
    )
    english_message = (
        "New document '%s' created.\nImported objects: %d.\nEffective scale: 1 CAD unit = %.6g mm.%s\n\nThe document remains unsaved."
        % (result["document"].Label, result["imported_object_count"], result["resolved_mm_per_unit"], english_bounds)
    )
    QtWidgets.QMessageBox.information(
        FreeCADGui.getMainWindow(),
        i18n.bi("Importacion CAD completada", "CAD import completed"),
        i18n.bi(spanish_message, english_message),
    )
    _import_log("QMessageBox final cierre")
    _schedule_event_loop_probes("run_import_dialog")
    _import_log("run_import_dialog retorno", operation_started)
    return result


class CommandClass:
    """FreeCAD command for importing a CAD reference safely."""

    CommandName = "FA_ImportCADReference"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Importar referencia DWG/DXF", "FA Import DWG/DXF reference"),
            "ToolTip": i18n.bi("Importar DWG o DXF en un documento nuevo, con unidad real controlada.", "Import DWG or DXF into a new document with controlled real units."),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        operation_started = time.perf_counter()
        _import_log("Command.Activated inicio")
        try:
            run_import_dialog()
        except Exception as exc:
            handle_command_exception(i18n.bi("FA Importar referencia DWG/DXF", "FA Import DWG/DXF reference"), exc)
        finally:
            _schedule_event_loop_probes("Command.Activated")
            _import_log("Command.Activated retorno", operation_started)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
