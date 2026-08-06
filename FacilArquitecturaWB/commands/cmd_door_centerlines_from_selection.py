"""FA_DoorCenterlinesFromSelection command.

Descripcion: crea un Sketch_Centros con el eje cerrado de cada simbolo de puerta.
Fecha: 2026-07-14
Version: 0.1.0
Instrucciones: seleccionar un layer, grupo o shapes que representen puertas antes de ejecutar.
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from ..core.centerline_utils import create_centerline_sketch_from_objects
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import ensure_project_structure, msg

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "door_centerlines.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """FreeCAD command for extracting closed-opening axes from door symbols."""

    CommandName = "FA_DoorCenterlinesFromSelection_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Centros de puertas",
            "ToolTip": "Crear un nuevo Sketch_Centros con el eje cerrado de cada simbolo de puerta.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            selection = list(FreeCADGui.Selection.getSelection() or [])
            if not selection:
                raise UserFacingError("Seleccione un layer, grupo o shapes de puertas antes de ejecutar el comando.")
            doc, _root, groups = ensure_project_structure()
            sketch, segments = create_centerline_sketch_from_objects(
                doc,
                groups["master_sketches"],
                selection,
                extraction_strategy="door_swing",
            )
            doc.recompute()
            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(sketch)
            except Exception:
                pass
            msg("FA_DoorCenterlinesFromSelection completado. Lineas creadas: %d" % len(segments))
        except Exception as exc:
            handle_command_exception("FA Centros de puertas", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
