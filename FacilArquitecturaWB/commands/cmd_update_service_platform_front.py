"""FreeCAD command that rebuilds a selected service platform front."""

from __future__ import annotations

import os

import FreeCADGui

from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import msg
from ..modules.service_platform.builder import find_platform_root, update_service_platform_front
from ..modules.service_platform.validation import PlatformValidationError


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "update_service_platform.svg")
).replace(os.sep, "/")


class CommandClass:
    CommandName = "FA_UpdateServicePlatformFront"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Actualizar frente de plataforma",
            "ToolTip": "Releer la linea fuente y actualizar la plataforma sin duplicar objetos.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            selection = list(FreeCADGui.Selection.getSelection() or [])
            if len(selection) != 1:
                raise UserFacingError("Seleccione un frente de plataforma o uno de sus objetos.")
            root = find_platform_root(selection[0])
            if root is None:
                raise UserFacingError("La seleccion no pertenece a un FA_ServicePlatformFront.")
            doc = root.Document
            doc.openTransaction("FA Actualizar frente de plataforma")
            transaction_open = True
            result = update_service_platform_front(doc, root)
            doc.recompute()
            doc.commitTransaction()
            transaction_open = False
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(result["root"])
            FreeCADGui.activeDocument().activeView().fitAll()
            msg("FA_UpdateServicePlatformFront completado sin duplicados.")
        except PlatformValidationError as exc:
            _abort(doc, transaction_open)
            handle_command_exception("FA Actualizar frente de plataforma", UserFacingError(str(exc)))
        except Exception as exc:
            _abort(doc, transaction_open)
            handle_command_exception("FA Actualizar frente de plataforma", exc)

    def IsActive(self):  # noqa: N802
        return bool(FreeCADGui.ActiveDocument)


def _abort(doc, transaction_open):
    if transaction_open and doc is not None:
        try:
            doc.abortTransaction()
        except Exception:
            pass


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
