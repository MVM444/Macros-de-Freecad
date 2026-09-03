"""FA_CreateMasterSketches command.

Descripcion: crea sketches maestros editables y vacios en plano XY.
Fecha y hora: 2026-08-27 16:28 UTC-06:00
Version: 0.2.0
Instrucciones: conservar sketches existentes; no generar geometria de ejemplo en este comando.
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from ..core.parameters import ensure_parameter_sheet, read_parameters
from ..core.command_errors import handle_command_exception
from ..core.project_structure import ensure_project_support_structure, msg
from ..core.sketch_utils import ensure_master_sketches

ICON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "facilarq.svg")).replace(
    os.sep, "/"
)
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """FreeCAD command for creating master sketches."""

    CommandName = "FA_CreateMasterSketches_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Crear sketches maestros",
            "ToolTip": "Crear sketches maestros vacios para terreno, ejes, muros, puertas, ventanas y losa.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            doc, _root, groups = ensure_project_support_structure(
                keys=("parameters", "master_sketches")
            )
            sheet = ensure_parameter_sheet(doc, groups["parameters"])
            params = read_parameters(sheet)
            ensure_master_sketches(doc, groups["master_sketches"], params)
            doc.recompute()
            msg("FA_CreateMasterSketches completado.")
        except Exception as exc:
            handle_command_exception("FA Crear sketches maestros", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
