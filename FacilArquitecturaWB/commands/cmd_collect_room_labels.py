"""FA_CollectRoomLabels command.

Descripcion: recopila nombres de recintos y sus metadatos en Spreadsheet_Rotulos_Recintos.
Fecha: 2026-07-25
Version: 0.3.0
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import ensure_project_structure, msg
from ..core.room_label_utils import collect_room_labels, write_room_label_spreadsheet


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "room_labels.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """FreeCAD command that consolidates room labels into a spreadsheet."""

    CommandName = "FA_CollectRoomLabels_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Recopilar rotulos de recintos",
            "ToolTip": "Recopilar nombres, areas, tipos y coordenadas de rotulos en una hoja.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            doc, _root, groups = ensure_project_structure()
            records = collect_room_labels(doc)
            if not records:
                raise UserFacingError(
                    "No se encontraron rotulos de recintos con propiedad Text."
                )
            try:
                doc.openTransaction("FA Recopilar rotulos de recintos")
                transaction_open = True
            except Exception:
                transaction_open = False
            sheet = write_room_label_spreadsheet(doc, records, groups["parameters"])
            doc.recompute()
            if transaction_open:
                doc.commitTransaction()
                transaction_open = False
            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(sheet)
            except Exception:
                pass
            msg("FA_CollectRoomLabels completado.")
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Recopilar rotulos de recintos", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
