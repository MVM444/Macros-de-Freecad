"""FA_CreateWindowsFromSketch command.

Descripcion: crea ventanas Arch nativas desde Sketches y las aloja en muros.
Objetivo: admitir seleccion explicita y contener los objetos en un Level BIM nativo.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 22:35 UTC-06:00.
Version: 0.2.0.
Instrucciones de mantenimiento: conservar FA_CreateWindowsBIM como alias heredado.
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.opening_utils import (
    collect_bim_walls,
    collect_opening_sketches_from_document,
    collect_opening_sketches_from_selection,
    create_openings_from_centerlines,
    opening_source_assessment,
    selection_description,
)
from ..core.bim_structure_utils import (
    collect_buildings,
    ensure_bim_structure,
    is_building,
    is_level,
    selected_level,
)
from ..core.project_structure import active_or_new_document, msg
from ..ui.dialog_opening_parameters import OpeningParametersDialog


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "window_centerlines.svg")
).replace(os.sep, "/")


class CommandClass:
    """Create hosted native BIM windows from selected source sketches."""

    CommandName = "FA_CreateWindowsFromSketch"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Ventanas BIM",
            "ToolTip": "Crear ventanas BIM nativas y huecos reales desde ejes seleccionados.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            msg("FA_CreateWindowsFromSketch iniciado")
            selection = list(FreeCADGui.Selection.getSelection() or [])
            msg("Seleccion recibida: %s" % selection_description(selection))
            doc = active_or_new_document()
            target_level = selected_level(selection)
            source_selection = [
                obj for obj in selection if not is_level(obj) and not is_building(obj)
            ]
            for obj in source_selection:
                if str(getattr(obj, "TypeId", "") or "").startswith("Sketcher::"):
                    accepted, reason = opening_source_assessment(obj, "window", explicit=True)
                    msg("Fuente %s: %s" % (obj.Label, reason))
            sources = collect_opening_sketches_from_selection(source_selection, "window")
            if not sources:
                sources = collect_opening_sketches_from_document(doc, "window")
                if len(sources) > 1:
                    raise UserFacingError(
                        "Se encontraron varios Sketches de centros de ventanas: %s. "
                        "Seleccione explicitamente el Sketch que desea usar."
                        % ", ".join(str(obj.Label) for obj in sources)
                    )
                if sources:
                    msg(
                        "Sin Sketch de ventana explicito; se usara automaticamente: %s"
                        % ", ".join(str(obj.Label) for obj in sources)
                    )
            if not sources:
                raise UserFacingError(
                    "No se encontro un Sketch de centros de ventanas en la seleccion "
                    "ni en el documento. Seleccione el Sketch o genere primero "
                    "Sketch_Centros_Ventanas con FA Centros de ventanas."
                )
            walls = collect_bim_walls(doc, selection=selection)
            if not walls:
                raise UserFacingError("No se encontraron muros BIM con Sketch Base utilizable.")
            chosen_building = None
            if target_level is not None:
                chosen_building = next(
                    (parent for parent in target_level.InList if is_building(parent)), None
                )
            buildings = collect_buildings(doc)
            if chosen_building is None and len(buildings) == 1:
                chosen_building = buildings[0]
            params = {
                "window_height_mm": 1200.0,
                "window_sill_mm": 900.0,
            }
            msg("Sketches fuente: %d" % len(sources))
            msg("Muros BIM candidatos: %d" % len(walls))
            dialog = OpeningParametersDialog(
                "window", len(sources), len(walls), params, parent=FreeCADGui.getMainWindow()
            )
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            options = dialog.values()
            doc.openTransaction("FA Ventanas BIM")
            transaction_open = True
            structure = ensure_bim_structure(
                doc,
                building=chosen_building,
                level=target_level,
                elevation_mm=(target_level.Placement.Base.z if target_level is not None else 0.0),
            )
            target_level = structure["level"]
            created, summary = create_openings_from_centerlines(
                doc,
                target_level,
                sources,
                walls,
                "window",
                height_mm=options["height_mm"],
                sill_mm=options["sill_mm"],
                host_tolerance_mm=options["host_tolerance_mm"],
                replace_existing=options["replace_existing"],
            )
            doc.recompute()
            doc.commitTransaction()
            transaction_open = False
            try:
                FreeCADGui.Selection.clearSelection()
                for obj in created:
                    FreeCADGui.Selection.addSelection(obj)
            except Exception:
                pass
            msg(
                "Ventanas BIM creadas: %d | existentes: %d | rechazadas: %d | Level: %s"
                % (
                    summary["created_count"],
                    summary["skipped_existing_count"],
                    summary["rejected_count"],
                    target_level.Label,
                )
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Ventanas BIM", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    FreeCADGui.addCommand("FA_CreateWindowsBIM", command)
    return command
