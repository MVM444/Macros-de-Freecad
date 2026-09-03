"""FA_CollectRoomLabels command.

Descripcion: recopila nombres de recintos y sus metadatos en Spreadsheet_Rotulos_Recintos.
Funcionamiento principal: con una o mas capas Draft seleccionadas usa exactamente
sus textos como alcance; sin capas seleccionadas ejecuta deteccion automatica.
Mantenimiento: conservar la prioridad de seleccion explicita sobre heuristicas.
Version: 0.7.0
Fecha y hora: 2026-09-02 12:35 America/Costa_Rica
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from .. import i18n

from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.bim_structure_utils import ensure_auxiliary_parent
from ..core.project_structure import active_or_new_document, msg
from ..core.room_label_utils import (
    collect_room_labels,
    layer_objects,
    selected_draft_layers,
    write_room_label_spreadsheet,
)


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "room_labels.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """FreeCAD command that consolidates room labels into a spreadsheet."""

    CommandName = "FA_CollectRoomLabels_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Recopilar rotulos de recintos", "FA Collect room labels"),
            "ToolTip": i18n.bi(
                "Recopilar rotulos desde las capas seleccionadas; sin capas, detectar automaticamente nombres de recintos.",
                "Collect labels from selected layers; with no layers selected, automatically detect room names.",
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            # Capture user intent before resolving the auxiliary BIM parent.
            try:
                selection = list(FreeCADGui.Selection.getSelection() or [])
            except Exception:
                selection = []
            selected_layers = selected_draft_layers(selection)

            doc = active_or_new_document()

            if selected_layers:
                objects = layer_objects(selected_layers)
                layer_labels = [str(getattr(layer, "Label", "") or layer.Name) for layer in selected_layers]
                msg(
                    "FA Recopilar rotulos: alcance explicito por capa(s): %s | objetos=%d"
                    % (", ".join(layer_labels), len(objects))
                )
                records = collect_room_labels(doc, objects=objects, explicit_scope=True)
                if not records:
                    raise UserFacingError(
                        i18n.bi("Las capas seleccionadas no contienen objetos Draft Text con propiedad Text.", "The selected layers do not contain Draft Text objects with a Text property.")
                    )
            else:
                msg("FA Recopilar rotulos: sin capa seleccionada; modo automatico.")
                records = collect_room_labels(doc)
                if not records:
                    raise UserFacingError(
                        i18n.bi("Se encontraron cero rotulos de recinto con los criterios automaticos. Puede seleccionar la capa que contiene los nombres y ejecutar de nuevo.", "No room labels were found using the automatic criteria. You can select the layer containing the room names and run the command again.")
                    )

            support_parent, _level = ensure_auxiliary_parent(
                doc, selection, legacy_key="parameters"
            )
            try:
                doc.openTransaction("FA Recopilar rotulos de recintos")
                transaction_open = True
            except Exception:
                transaction_open = False
            sheet = write_room_label_spreadsheet(doc, records, support_parent)
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
            handle_command_exception(i18n.bi("FA Recopilar rotulos de recintos", "FA Collect room labels"), exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
