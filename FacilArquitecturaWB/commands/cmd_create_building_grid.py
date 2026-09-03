"""FA_CreateBuildingGrid command.

Descripcion: crea una reticula ArchGrid auxiliar desde centros de muros, puertas y ventanas.
Funcion principal: generar referencia geometrica; nunca crea ni sustituye muros BIM.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-19 21:32 UTC-06:00.
Version: 0.5.0.
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from ..core.building_grid_utils import collect_building_grid_sources, create_inferred_building_grid
from ..core.bim_structure_utils import ensure_bim_structure, is_building, selected_level
from ..core.command_errors import handle_command_exception
from ..core.parameters import ensure_parameter_sheet, read_parameters
from ..core.project_structure import active_or_new_document, msg


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "building_grid.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))


def _building_parent(level):
    """Return the unique native Building parent of a Level when available."""
    if level is None:
        return None
    parents = [obj for obj in list(getattr(level, "InList", []) or []) if is_building(obj)]
    return parents[0] if len(parents) == 1 else None


class CommandClass:
    """Infer and create one native ArchGrid architectural grid."""

    CommandName = "FA_CreateBuildingGrid_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Cuadricula ArchGrid de referencia",
            "ToolTip": "Crear una ArchGrid auxiliar desde centros de paredes. No crea muros BIM.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            doc = active_or_new_document()
            selection = list(FreeCADGui.Selection.getSelection() or [])
            sources = collect_building_grid_sources(doc, selection)
            sheet = ensure_parameter_sheet(doc, doc.getObject("FA_Parameters"))
            params = read_parameters(sheet)
            preferred_level = selected_level(selection)
            try:
                doc.openTransaction("FA Crear reticula desde edificio")
                transaction_open = True
            except Exception:
                transaction_open = False
            spatial = ensure_bim_structure(
                doc,
                building=_building_parent(preferred_level),
                level=preferred_level,
            )
            result = create_inferred_building_grid(doc, spatial["level"], sources, params)
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
                "FA_CreateBuildingGrid completado. ArchGrid: columnas=%d filas=%d | lineas base=%d | segmentos visibles=%d | muros creados=0"
                % (
                    len(model["column_sizes"]),
                    len(model["row_sizes"]),
                    len(model["wall_x_lines"]) + len(model["wall_y_lines"]),
                    int(getattr(result.get("display"), "FA_ClippedSegmentCount", 0) or 0),
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
