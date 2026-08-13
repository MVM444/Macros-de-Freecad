"""FA_CreateWallsFromSketch command.

Descripcion: genera muros BIM parametricos desde Sketches usando Arch.makeWall.
Objetivo: crear Wall nativo con Base Sketch directa dentro de un Building Storey.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 21:24 UTC-06:00.
Version: 0.4.0.
Instrucciones de mantenimiento: conservar FA_CreateWallsBIM como alias heredado y
no volver a introducir FA_Project ni bases Part::Feature intermedias.
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from ..core.bim_utils import (
    collect_any_sketches_from_selection,
    collect_master_wall_sketches,
    create_walls_from_centerline_sketches,
    prepare_sketches_as_wall_centerlines,
    sketches_requiring_wall_metadata,
)
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.bim_structure_utils import (
    collect_buildings,
    ensure_bim_structure,
    is_building,
    is_level,
    selected_level,
)
from ..core.project_structure import active_or_new_document, msg
from ..ui.dialog_wall_parameters import WallSketchParametersDialog

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "walls_from_centerlines.svg")
).replace(os.sep, "/")


class CommandClass:
    """FreeCAD command for creating BIM walls from selected centerline sketches."""

    CommandName = "FA_CreateWallsFromSketch"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Muros BIM desde Sketch",
            "ToolTip": "Crear Arch Walls nativos con Base Sketch directa dentro de un Level.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            selection = list(FreeCADGui.Selection.getSelection() or [])
            doc = active_or_new_document()
            target_level = selected_level(selection)
            source_selection = [
                obj for obj in selection if not is_level(obj) and not is_building(obj)
            ]
            sketches = collect_any_sketches_from_selection(source_selection) if source_selection else []
            if source_selection and not sketches:
                raise UserFacingError("La seleccion no contiene ningun Sketcher::SketchObject.")
            if not source_selection:
                sketches = collect_master_wall_sketches(doc)
                if sketches:
                    msg("Sin seleccion: usando sketches maestros de muro como compatibilidad.")
            if not sketches:
                raise UserFacingError("Seleccione al menos un Sketch con geometria para crear el muro BIM.")

            prefs = FreeCAD.ParamGet(
                "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/WallsBIM"
            )
            params = {
                "wall_height_mm": prefs.GetFloat("wall_height_mm", 3000.0),
                "int_wall_thickness_mm": prefs.GetFloat("wall_thickness_mm", 120.0),
                "ext_wall_thickness_mm": prefs.GetFloat("wall_thickness_mm", 200.0),
            }
            existing_buildings = collect_buildings(doc)
            chosen_building = None
            if target_level is not None:
                chosen_building = next(
                    (parent for parent in target_level.InList if is_building(parent)), None
                )
            if chosen_building is None and len(existing_buildings) == 1:
                chosen_building = existing_buildings[0]
            missing = sketches_requiring_wall_metadata(sketches)
            conversion_values = None
            if missing:
                dialog = WallSketchParametersDialog(missing, params, parent=FreeCADGui.getMainWindow())
                accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
                if accepted != QtWidgets.QDialog.Accepted:
                    return
                conversion_values = dialog.values()
            try:
                doc.openTransaction("FA Muros BIM desde centros")
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
            if conversion_values is not None:
                sketches = prepare_sketches_as_wall_centerlines(
                    sketches,
                    conversion_values["thickness"],
                    conversion_values["height"],
                    conversion_values["wall_type"],
                )
            created = create_walls_from_centerline_sketches(
                doc, target_level, sketches, params, target_level=target_level
            )
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
            msg(
                "FA_CreateWallsFromSketch completado. Muros: %d | Level: %s"
                % (len(created), target_level.Label)
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Muros BIM desde Sketch", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    FreeCADGui.addCommand("FA_CreateWallsBIM", command)
    return command
