"""FA_CreateAxesColumnsBIM command.

Descripcion: crea Arch Axis, AxisSystem y columnas Arch Structure desde un sketch seleccionado.
Fecha: 2026-07-15
Version: 0.1.0
Instrucciones: seleccionar un unico sketch con dos familias de lineas de ejes.
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from ..core.axis_utils import create_bim_axes_and_columns_from_sketch, find_axis_sketch_from_selection
from ..core.command_errors import handle_command_exception
from ..core.parameters import ensure_parameter_sheet, read_parameters
from ..core.project_structure import ensure_project_structure, msg

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "axes_columns_bim.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """Create a native BIM axis system and replicated columns from one sketch."""

    CommandName = "FA_CreateAxesColumnsBIM_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Ejes y columnas BIM",
            "ToolTip": "Crear Arch Axis, AxisSystem y columnas BIM desde el sketch de ejes seleccionado.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            selection = list(FreeCADGui.Selection.getSelection() or [])
            sketch = find_axis_sketch_from_selection(selection)
            doc, _root, groups = ensure_project_structure()
            sheet = ensure_parameter_sheet(doc, groups["parameters"])
            params = read_parameters(sheet)
            try:
                doc.openTransaction("FA Ejes y columnas BIM")
                transaction_open = True
            except Exception:
                transaction_open = False
            result = create_bim_axes_and_columns_from_sketch(doc, groups["bim"], sketch, params)
            doc.recompute()
            if transaction_open:
                doc.commitTransaction()
                transaction_open = False
            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(result["system"])
                FreeCADGui.Selection.addSelection(result["column"])
            except Exception:
                pass
            msg(
                "FA_CreateAxesColumnsBIM completado. Ejes: %d | Columnas: %d"
                % (sum(len(axis.Distances) for axis in result["axes"]), len(result["points"]))
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Ejes y columnas BIM", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
