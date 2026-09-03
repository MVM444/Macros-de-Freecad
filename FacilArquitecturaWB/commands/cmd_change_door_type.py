"""FA_ChangeDoorType command.

Descripcion: cambia el preset BIM nativo de puertas Arch ya creadas sin perder
identidad, dimensiones, Placement, host ni trazabilidad.
FreeCAD objetivo: 1.1.3.
Fecha: 2026-08-13.
Version: 0.1.0.
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.door_type_utils import (
    change_door_types,
    collect_compatible_doors,
    common_preset_name,
    log,
    native_door_presets,
)
from ..core.project_structure import active_or_new_document
from ..ui.dialog_change_door_type import ChangeDoorTypeDialog


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "change_door_type.svg")
).replace(os.sep, "/")


class CommandClass:
    """Change one or more compatible Arch/BIM doors to an installed preset."""

    CommandName = "FA_ChangeDoorType"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Cambiar tipo de puerta",
            "ToolTip": (
                "Cambiar el preset BIM nativo de las puertas seleccionadas, "
                "conservando dimensiones, Placement, host y hueco."
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            doc = active_or_new_document()
            selection = list(FreeCADGui.Selection.getSelection() or [])
            doors, rejected = collect_compatible_doors(selection)
            if rejected:
                details = "; ".join(
                    "%s: %s"
                    % (str(getattr(obj, "Label", getattr(obj, "Name", "Objeto"))), reason)
                    for obj, reason in rejected
                )
                raise UserFacingError("La seleccion contiene objetos incompatibles: %s." % details)
            if not doors:
                raise UserFacingError(
                    "Seleccione una o varias puertas Arch/BIM existentes."
                )
            presets = native_door_presets()
            current = common_preset_name(doors, presets=presets)
            dialog = ChangeDoorTypeDialog(
                len(doors), current, presets, parent=FreeCADGui.getMainWindow()
            )
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            options = dialog.values()
            doc.openTransaction("FA Cambiar tipo de puerta")
            transaction_open = True
            changed, summary = change_door_types(
                doc,
                doors,
                options["target_preset"],
                preserve_dimensions=options["preserve_dimensions"],
                preserve_opening=options["preserve_opening"],
            )
            doc.commitTransaction()
            transaction_open = False
            try:
                FreeCADGui.Selection.clearSelection()
                for obj in changed:
                    FreeCADGui.Selection.addSelection(obj)
                FreeCADGui.activeDocument().activeView().fitAll()
            except Exception:
                pass
            log(
                "Resultado: %d puerta(s) -> %s | identidad=%s | hosts validados=%d"
                % (
                    summary["changed_count"],
                    summary["target_preset"],
                    "conservada" if summary["identity_preserved"] else "reemplazada",
                    summary["validated_host_count"],
                )
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            log(str(exc), warning=True)
            handle_command_exception("FA Cambiar tipo de puerta", exc)

    def IsActive(self):  # noqa: N802
        return FreeCAD.ActiveDocument is not None


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
