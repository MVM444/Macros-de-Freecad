"""Visible FA Tabla de puertas command.

Nombre: cmd_door_table.py
Proposito: conectar Spreadsheet_Puertas con ElementDataCore y puertas BIM nativas.
Funcionamiento: extrae, valida, previsualiza y aplica registros de puertas desde un Sketch.
FreeCAD objetivo: 1.1.3
Version: 0.1.0
Fecha y hora: 2026-08-28 17:42 UTC-06:00
Mantenimiento: mantener este comando delgado; no duplicar logica de core/door_table_utils.py.
"""

from __future__ import annotations

import json
import os

import FreeCADGui
from PySide import QtWidgets

from ..core.bim_structure_utils import collect_levels, selected_level
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.door_table_utils import (
    apply_door_records,
    ensure_door_table,
    export_table_native,
    extract_door_records,
    import_table_native,
    read_door_records,
    update_validation_statuses,
    validate_door_records,
    write_door_records,
)
from ..core.opening_utils import (
    collect_bim_walls,
    collect_opening_sketches_from_document,
    collect_opening_sketches_from_selection,
)
from ..core.project_structure import active_or_new_document, msg
from ..ui.dialog_door_table import DoorTableDialog


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "door_table.svg")
).replace(os.sep, "/")


class CommandClass:
    CommandName = "FA_DoorTable"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Tabla de puertas",
            "ToolTip": "Extraer, transferir, validar y aplicar datos de puertas BIM, incluidas dobles, bisagra y apertura.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            doc = active_or_new_document()
            selection = list(FreeCADGui.Selection.getSelection() or [])
            dialog = DoorTableDialog(parent=FreeCADGui.getMainWindow())
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted or not dialog.action_name:
                return
            action = dialog.action_name

            if action == "open":
                sheet = self._transaction(doc, "FA Crear tabla de puertas", lambda: ensure_door_table(doc))
                doc.recompute()
                self._open_sheet(sheet)
                msg("[PUERTAS][TABLA] Spreadsheet_Puertas lista para editar")
                return

            if action == "extract":
                records = extract_door_records(doc)
                sheet = self._transaction(
                    doc,
                    "FA Extraer tabla de puertas",
                    lambda: write_door_records(ensure_door_table(doc), records),
                    return_sheet=True,
                )
                msg("[PUERTAS][TABLA] Puertas extraidas a tabla: %d" % len(records))
                self._open_sheet(sheet)
                return

            if action == "import":
                filename = QtWidgets.QFileDialog.getOpenFileName(
                    FreeCADGui.getMainWindow(),
                    "Importar tabla de puertas",
                    "",
                    "CSV/TSV (*.csv *.tsv);;Todos (*.*)",
                )[0]
                if not filename:
                    return
                sheet = self._transaction(
                    doc,
                    "FA Importar tabla de puertas",
                    lambda: import_table_native(doc, filename),
                )
                msg("[PUERTAS][TABLA] Tabla importada: %s" % filename)
                self._open_sheet(sheet)
                return

            sheet = doc.getObject("Spreadsheet_Puertas")
            if sheet is None:
                sheet = self._transaction(doc, "FA Crear tabla de puertas", lambda: ensure_door_table(doc))

            if action == "export":
                filename = QtWidgets.QFileDialog.getSaveFileName(
                    FreeCADGui.getMainWindow(),
                    "Exportar tabla de puertas",
                    "Spreadsheet_Puertas.csv",
                    "CSV (*.csv);;TSV (*.tsv)",
                )[0]
                if filename:
                    export_table_native(sheet, filename)
                    msg("[PUERTAS][TABLA] Tabla exportada (UTF-8, separador tabulador): %s" % filename)
                return

            records = read_door_records(sheet)
            if not records:
                raise UserFacingError("Spreadsheet_Puertas no contiene filas de puertas.")
            sketches = collect_opening_sketches_from_selection(selection, "door")
            if not sketches:
                sketches = collect_opening_sketches_from_document(doc, "door")
            if not sketches:
                raise UserFacingError("Seleccione el Sketch actual de centros de puertas.")

            if action == "validate":
                report = validate_door_records(records, sketches)
                self._transaction(
                    doc,
                    "FA Estado tabla de puertas",
                    lambda: update_validation_statuses(sheet, report),
                )
                self._log_report(report)
                self._open_sheet(sheet)
                return

            if action == "apply":
                walls = collect_bim_walls(doc, selection=selection)
                if not walls:
                    raise UserFacingError("No se encontraron muros BIM anfitriones.")
                target_level = selected_level(selection)
                if target_level is None:
                    levels = collect_levels(doc)
                    if len(levels) == 1:
                        target_level = levels[0]
                preview = apply_door_records(doc, target_level, records, sketches, walls, dry_run=True)
                self._log_report(preview["validation"])
                executable = preview["action_counts"].get("CREATE", 0) + preview["action_counts"].get("REPLACE", 0)
                if executable == 0:
                    msg("[PUERTAS][TABLA] Aplicacion sin cambios; no hay filas nuevas o modificadas seguras")
                    return
                answer = QtWidgets.QMessageBox.question(
                    FreeCADGui.getMainWindow(),
                    "FA Tabla de puertas",
                    "Dry-run aprobado para %d cambio(s).\n\n"
                    "Se omitirán filas NO_MATCH, AMBIGUO o conflictos manuales. ¿Aplicar ahora?" % executable,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No,
                )
                if answer != QtWidgets.QMessageBox.Yes:
                    return
                result = apply_door_records(doc, target_level, records, sketches, walls, dry_run=False)
                msg("[PUERTAS][TABLA] Aplicacion completada: %s" % json.dumps(result["action_counts"], sort_keys=True))
        except Exception as exc:
            handle_command_exception("FA Tabla de puertas", exc)

    def IsActive(self):  # noqa: N802
        return True

    @staticmethod
    def _transaction(doc, label, callback, return_sheet=False):
        opened = False
        try:
            doc.openTransaction(label)
            opened = True
            result = callback()
            doc.recompute()
            doc.commitTransaction()
            opened = False
            if return_sheet:
                return doc.getObject("Spreadsheet_Puertas")
            return result
        except Exception:
            if opened:
                doc.abortTransaction()
            raise

    @staticmethod
    def _open_sheet(sheet):
        try:
            FreeCADGui.activeDocument().setEdit(sheet.Name)
        except Exception:
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(sheet)

    @staticmethod
    def _log_report(report):
        counts = report.get("counts", {})
        msg(
            "[PUERTAS][TABLA] Validacion: MATCH=%d | CAMBIO=%d | NO_MATCH=%d | AMBIGUO=%d"
            % tuple(int(counts.get(name, 0)) for name in ("MATCH", "CAMBIO", "NO_MATCH", "AMBIGUO"))
        )


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
