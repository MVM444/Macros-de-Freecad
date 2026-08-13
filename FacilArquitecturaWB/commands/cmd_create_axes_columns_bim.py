"""FA_CreateColumnsFromSketch command.

Descripcion: crea Arch Axis, AxisSystem y columnas Arch Structure desde un Sketch.
Objetivo: generar columnas nativas directamente dentro de un Building Storey.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 22:10 UTC-06:00.
Version: 0.2.0.
Instrucciones de mantenimiento: conservar FA_CreateAxesColumnsBIM como alias
heredado y no reintroducir FA_Project ni grupos esteticos de columnas.
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui

from ..core.axis_utils import create_bim_axes_and_columns_from_sketch, find_axis_sketch_from_selection
from ..core.command_errors import handle_command_exception
from ..core.bim_structure_utils import (
    collect_buildings,
    ensure_bim_structure,
    is_building,
    is_level,
    selected_level,
)
from ..core.project_structure import active_or_new_document, msg

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "axes_columns_bim.svg")
).replace(os.sep, "/")
class CommandClass:
    """Create a native BIM axis system and replicated columns from one sketch."""

    CommandName = "FA_CreateColumnsFromSketch"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Columnas BIM desde Sketch",
            "ToolTip": "Crear ejes y columnas Arch Structure dentro de un Level BIM nativo.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            selection = list(FreeCADGui.Selection.getSelection() or [])
            target_level = selected_level(selection)
            sketch = find_axis_sketch_from_selection(
                [obj for obj in selection if not is_level(obj) and not is_building(obj)]
            )
            doc = active_or_new_document()
            chosen_building = None
            if target_level is not None:
                chosen_building = next(
                    (parent for parent in target_level.InList if is_building(parent)), None
                )
            buildings = collect_buildings(doc)
            if chosen_building is None and len(buildings) == 1:
                chosen_building = buildings[0]
            prefs = FreeCAD.ParamGet(
                "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/ColumnsBIM"
            )
            params = {
                "axis_extension_mm": prefs.GetFloat("axis_extension_mm", 1000.0),
                "axis_cluster_tolerance_mm": prefs.GetFloat("axis_cluster_tolerance_mm", 10.0),
                "column_width_mm": prefs.GetFloat("column_width_mm", 400.0),
                "column_depth_mm": prefs.GetFloat("column_depth_mm", 400.0),
                "column_height_mm": prefs.GetFloat("column_height_mm", 3000.0),
            }
            try:
                doc.openTransaction("FA Ejes y columnas BIM")
                transaction_open = True
            except Exception:
                transaction_open = False
            structure = ensure_bim_structure(
                doc,
                building=chosen_building,
                level=target_level,
                elevation_mm=(target_level.Placement.Base.z if target_level is not None else 0.0),
            )
            target_level = structure["level"]
            result = create_bim_axes_and_columns_from_sketch(doc, target_level, sketch, params)
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
                "FA_CreateColumnsFromSketch completado. Ejes: %d | Columnas: %d | Level: %s"
                % (
                    sum(len(axis.Distances) for axis in result["axes"]),
                    len(result["points"]),
                    target_level.Label,
                )
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
    FreeCADGui.addCommand("FA_CreateAxesColumnsBIM", command)
    return command
