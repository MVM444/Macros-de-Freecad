"""FA_CreateProject command.

Descripcion: crea estructura base y hoja de parametros.
Fecha: 2026-07-13
Version: 0.1.0
Instrucciones: comando idempotente; no destruir trabajo del usuario.
"""

from __future__ import annotations

import os
import time

import FreeCAD
import FreeCADGui

from ..core.parameters import ensure_parameter_sheet
from ..core.command_errors import handle_command_exception
from ..core.project_structure import ensure_project_structure, msg

ICON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "facilarq.svg")).replace(
    os.sep, "/"
)
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """FreeCAD command for creating the base Facil Arquitectura project."""

    CommandName = "FA_CreateProject_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Crear proyecto",
            "ToolTip": "Crear estructura base y Spreadsheet_Parametros para Facil Arquitectura.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            doc, _root, groups = ensure_project_structure()
            ensure_parameter_sheet(doc, groups["parameters"])
            doc.recompute()
            msg("FA_CreateProject completado.")
        except Exception as exc:
            handle_command_exception("FA Crear proyecto", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
