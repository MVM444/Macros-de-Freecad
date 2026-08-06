"""FreeCAD command that creates a parametric service platform front."""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import active_or_new_document
from ..modules.service_platform.builder import create_service_platform_front
from ..modules.service_platform.validation import PlatformValidationError
from ..ui.dialog_service_platform import ServicePlatformDialog


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "service_platform.svg")
).replace(os.sep, "/")


class CommandClass:
    CommandName = "FA_CreateServicePlatformFront"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Crear frente de plataforma",
            "ToolTip": "Crear un frente parametrico para puestos de atencion al publico.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            dialog = ServicePlatformDialog(parent=FreeCADGui.getMainWindow())
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            values = dialog.options()
            doc = active_or_new_document()
            doc.openTransaction("FA Crear frente de plataforma")
            transaction_open = True
            result = create_service_platform_front(doc, values)
            doc.recompute()
            doc.commitTransaction()
            transaction_open = False
            _select_and_fit(result["root"], axonometric=values.create_3d_furniture)
        except PlatformValidationError as exc:
            _abort(doc, transaction_open)
            handle_command_exception("FA Crear frente de plataforma", UserFacingError(str(exc)))
        except Exception as exc:
            _abort(doc, transaction_open)
            handle_command_exception("FA Crear frente de plataforma", exc)

    def IsActive(self):  # noqa: N802
        return True


def _select_and_fit(root, axonometric=True):
    FreeCADGui.Selection.clearSelection()
    FreeCADGui.Selection.addSelection(root)
    view = FreeCADGui.activeDocument().activeView()
    if axonometric:
        view.viewAxonometric()
    else:
        view.viewTop()
    view.fitAll()


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
