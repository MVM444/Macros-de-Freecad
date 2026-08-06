"""FA_CreateWallsBIM command.

Descripcion: genera muros BIM parametricos desde sketches de centros usando Arch.makeWall.
Fecha: 2026-07-15
Version: 0.2.0
Instrucciones: no crear objetos muro propios; usar Arch/BIM si esta disponible.
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from ..core.bim_utils import (
    collect_master_wall_sketches,
    collect_wall_sketches_from_selection,
    create_walls_from_centerline_sketches,
)
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.parameters import ensure_parameter_sheet, read_parameters
from ..core.project_structure import ensure_project_structure, msg

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "walls_from_centerlines.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """FreeCAD command for creating BIM walls from selected centerline sketches."""

    CommandName = "FA_CreateWallsBIM_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Muros BIM desde centros",
            "ToolTip": "Crear un Arch Wall por Sketch_Centros usando su espesor y altura parametricos.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            doc, _root, groups = ensure_project_structure()
            sheet = ensure_parameter_sheet(doc, groups["parameters"])
            params = read_parameters(sheet)
            selection = list(FreeCADGui.Selection.getSelection() or [])
            sketches = collect_wall_sketches_from_selection(selection)
            if selection and not sketches:
                raise UserFacingError(
                    "La seleccion no contiene Sketches de centros con FA_WallThickness. "
                    "Seleccione uno o varios sketches de espesor."
                )
            if not sketches:
                sketches = collect_master_wall_sketches(doc)
                if sketches:
                    msg("Sin seleccion: usando sketches maestros de muro como compatibilidad.")
            if not sketches:
                raise UserFacingError("Seleccione al menos un Sketch_Centros de muro con espesor detectado.")
            try:
                doc.openTransaction("FA Muros BIM desde centros")
                transaction_open = True
            except Exception:
                transaction_open = False
            created = create_walls_from_centerline_sketches(doc, groups["bim"], sketches, params)
            doc.recompute()
            if transaction_open:
                doc.commitTransaction()
                transaction_open = False
            try:
                FreeCADGui.Selection.clearSelection()
                for wall in created:
                    FreeCADGui.Selection.addSelection(wall)
            except Exception:
                pass
            msg("FA_CreateWallsBIM completado. Muros creados: %d" % len(created))
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Muros BIM desde centros", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
