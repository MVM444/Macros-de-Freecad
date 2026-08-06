"""FA_CreateSampleGeometry command.

Descripcion: agrega geometria simple de muestra a sketches maestros vacios.
Fecha: 2026-07-13
Version: 0.1.0
Instrucciones: este comando es demostrativo; no debe ejecutarse sobre trabajo real salvo que el usuario lo quiera.
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from ..core.parameters import ensure_parameter_sheet, read_parameters
from ..core.command_errors import handle_command_exception
from ..core.project_structure import ensure_project_structure, msg
from ..core.sketch_utils import add_sample_geometry_to_master_sketches

ICON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "facilarq.svg")).replace(
    os.sep, "/"
)
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """FreeCAD command for adding sample geometry to empty master sketches."""

    CommandName = "FA_CreateSampleGeometry_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Crear geometria de muestra",
            "ToolTip": "Agregar geometria simple a sketches maestros vacios para pruebas.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            doc, _root, groups = ensure_project_structure()
            sheet = ensure_parameter_sheet(doc, groups["parameters"])
            params = read_parameters(sheet)
            add_sample_geometry_to_master_sketches(doc, groups["master_sketches"], params)
            doc.recompute()
            msg("FA_CreateSampleGeometry completado.")
        except Exception as exc:
            handle_command_exception("FA Crear geometria de muestra", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
