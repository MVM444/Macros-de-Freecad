"""FA_DoorCenterlinesFromSelection command.

Descripcion: crea un Sketch_Centros con el eje cerrado de cada simbolo de puerta.
Fecha y hora: 2026-09-01 14:35 America/Costa_Rica
Version: 0.2.0
Instrucciones: seleccionar un layer, grupo o shapes que representen puertas antes de ejecutar.
"""

from __future__ import annotations

import os
import FreeCADGui

from ..core.centerline_utils import create_centerline_sketch_from_objects
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.bim_structure_utils import adopt_auxiliary_sources, ensure_auxiliary_parent
from ..core.project_structure import active_or_new_document, msg

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "door_centerlines.svg")
).replace(os.sep, "/")


class CommandClass:
    """FreeCAD command for extracting closed-opening axes from door symbols."""

    CommandName = "FA_DoorCenterlinesFromSelection"

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
            doc = active_or_new_document()
            support_parent, target_level = ensure_auxiliary_parent(doc, selection, legacy_key="master_sketches")
            sketch, segments = create_centerline_sketch_from_objects(
                doc,
                support_parent,
                selection,
                extraction_strategy="door_swing",
            )
            if target_level is not None:
                adopt_auxiliary_sources(doc, target_level, [sketch] + selection)
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
