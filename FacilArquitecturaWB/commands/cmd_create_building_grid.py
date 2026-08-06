"""FA_CreateBuildingGrid command.

Descripcion: crea una reticula BIM inferida desde centros de muros, puertas y ventanas.
Fecha: 2026-07-25
Version: 0.4.9
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from ..core.building_grid_utils import collect_building_grid_sources, create_inferred_building_grid
from ..core.command_errors import handle_command_exception
from ..core.parameters import ensure_parameter_sheet, read_parameters
from ..core.project_structure import ensure_project_structure, msg


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "building_grid.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """Infer and create one native ArchGrid architectural grid."""

    CommandName = "FA_CreateBuildingGrid_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Cuadricula ArchGrid para reconstruir paredes",
            "ToolTip": "Crear ArchGrid desde centros de paredes, prefiriendo copias sin huecos de puertas y ventanas.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            doc, _root, groups = ensure_project_structure()
            selection = list(FreeCADGui.Selection.getSelection() or [])
            sources = collect_building_grid_sources(doc, selection)
            sheet = ensure_parameter_sheet(doc, groups["parameters"])
            params = read_parameters(sheet)
            try:
                doc.openTransaction("FA Crear reticula desde edificio")
                transaction_open = True
            except Exception:
                transaction_open = False
            result = create_inferred_building_grid(doc, groups["bim"], sources, params)
            doc.recompute()
            if transaction_open:
                doc.commitTransaction()
                transaction_open = False
            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(result.get("display", result["grid"]))
            except Exception:
                pass
            model = result["model"]
            msg(
                "FA_CreateBuildingGrid completado. ArchGrid: columnas=%d filas=%d | lineas base=%d | segmentos visibles=%d | solidos de muro reconstruidos=%d"
                % (
                    len(model["column_sizes"]),
                    len(model["row_sizes"]),
                    len(model["wall_x_lines"]) + len(model["wall_y_lines"]),
                    int(getattr(result.get("display"), "FA_ClippedSegmentCount", 0) or 0),
                    len(getattr(getattr(result.get("wall"), "Shape", None), "Solids", []) or []),
                )
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Crear reticula desde edificio", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
