"""FA_WindowCenterlinesFromSelection command.

Descripcion: crea un Sketch_Centros con un eje principal por shape complejo de ventana.
Fecha: 2026-07-14
Version: 0.1.0
Instrucciones: seleccionar un layer, grupo o shapes que representen ventanas antes de ejecutar.
"""

from __future__ import annotations

import os
import FreeCADGui

from ..core.centerline_utils import create_centerline_sketch_from_objects
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import ensure_project_structure, msg

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "window_centerlines.svg")
).replace(os.sep, "/")


class CommandClass:
    """FreeCAD command for extracting one dominant centerline per window shape."""

    CommandName = "FA_WindowCenterlinesFromSelection"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Centros de ventanas",
            "ToolTip": "Crear un nuevo Sketch_Centros con un eje principal por shape complejo de ventana.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            selection = list(FreeCADGui.Selection.getSelection() or [])
            if not selection:
                raise UserFacingError("Seleccione un layer, grupo o shapes de ventanas antes de ejecutar el comando.")
            doc, _root, groups = ensure_project_structure()
            sketch, segments = create_centerline_sketch_from_objects(
                doc,
                groups["master_sketches"],
                selection,
                extraction_strategy="profile_axis",
            )
            doc.recompute()
            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(sketch)
            except Exception:
                pass
            msg("FA_WindowCenterlinesFromSelection completado. Lineas creadas: %d" % len(segments))
        except Exception as exc:
            handle_command_exception("FA Centros de ventanas", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
