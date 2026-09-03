"""FA_RebuildBIMModel command.

Descripcion: asistente unico para reconstruir BIM nativo desde Sketches existentes.
Objetivo: clasificar, confirmar y coordinar Building, Level, muros, columnas y aberturas.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-09-01 13:55 America/Costa_Rica.
Version: 0.1.0.
Instrucciones de mantenimiento: conservar CommandName estable y una sola transaccion.
"""

from __future__ import annotations

import os

import FreeCADGui
from PySide import QtWidgets

from ..core.bim_rebuild_utils import rebuild_bim_model, suggest_rebuild_assignments
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import active_or_new_document, msg
from ..ui.dialog_rebuild_bim_model import RebuildBIMModelDialog


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "rebuild_bim.svg")
).replace(os.sep, "/")


class CommandClass:
    """Analyze a document and rebuild its native BIM model after confirmation."""

    CommandName = "FA_RebuildBIMModel"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Reconstruir modelo BIM",
            "ToolTip": "Clasificar Sketches y crear Building, Level, muros, columnas, puertas y ventanas BIM.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            doc = active_or_new_document()
            analysis = suggest_rebuild_assignments(doc)
            if not analysis["records"]:
                raise UserFacingError("El documento no contiene Sketches para reconstruir.")
            for record in analysis["records"]:
                msg(
                    "Clasificacion %s -> %s (%s)"
                    % (
                        record["sketch"].Label,
                        record["suggested_role"] or "manual",
                        record["reason"],
                    )
                )
            dialog = RebuildBIMModelDialog(analysis, parent=FreeCADGui.getMainWindow())
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            assignments, options = dialog.values()
            doc.openTransaction("FA Reconstruir modelo BIM")
            transaction_open = True
            result = rebuild_bim_model(doc, assignments, options)
            doc.recompute()
            doc.commitTransaction()
            transaction_open = False
            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(result["building"])
                FreeCADGui.Selection.addSelection(result["level"])
            except Exception:
                pass
            column_count = len(result["columns"]["points"]) if result["columns"] else 0
            msg(
                "Reconstruccion BIM completada: muros=%d | columnas=%d | puertas=%d | "
                "ventanas=%d | losa=diferida"
                % (
                    len(result["walls"]),
                    column_count,
                    len(result["doors"]),
                    len(result["windows"]),
                )
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Reconstruir modelo BIM desde Sketches", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
