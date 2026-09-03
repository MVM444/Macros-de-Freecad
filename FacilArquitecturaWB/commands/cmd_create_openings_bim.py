"""FA_CreateOpeningsFromSketch command.

Descripcion: crea vanos Arch nativos sin hoja, marco ni vidrio desde Sketches.
Objetivo: usar el preset Opening only de FreeCAD y alojarlo en el Wall correcto.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-12 18:10 UTC-06:00.
Version: 0.1.0.
Mantenimiento: conservar delgado; la geometria vive en core.opening_utils.
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from ..core.bim_structure_utils import (
    adopt_auxiliary_sources,
    collect_buildings,
    ensure_bim_structure,
    is_building,
    is_level,
    selected_level,
)
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.opening_utils import (
    collect_bim_walls,
    collect_opening_sketches_from_document,
    collect_opening_sketches_from_selection,
    create_openings_from_centerlines,
    opening_source_assessment,
    selection_description,
    sketch_segments,
)
from ..core.project_structure import active_or_new_document
from ..ui.dialog_opening_parameters import OpeningParametersDialog


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "opening_only.svg")
).replace(os.sep, "/")


def _log(message, warning=False):
    printer = FreeCAD.Console.PrintWarning if warning else FreeCAD.Console.PrintMessage
    printer("[FACILARQ][ABERTURAS] " + str(message) + "\n")


class CommandClass:
    """Create hosted native BIM Opening Elements from selected Sketch lines."""

    CommandName = "FA_CreateOpeningsFromSketch"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Aberturas BIM desde Sketch",
            "ToolTip": "Crear solo vanos BIM reales desde las lineas de uno o varios Sketches.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            _log("FA_CreateOpeningsFromSketch iniciado")
            selection = list(FreeCADGui.Selection.getSelection() or [])
            _log("Seleccion recibida: %s" % selection_description(selection))
            doc = active_or_new_document()
            target_level = selected_level(selection)
            source_selection = [
                obj for obj in selection if not is_level(obj) and not is_building(obj)
            ]
            for obj in source_selection:
                if str(getattr(obj, "TypeId", "") or "").startswith("Sketcher::"):
                    _accepted, reason = opening_source_assessment(obj, "opening", explicit=True)
                    _log("Fuente %s: %s" % (obj.Label, reason))
            sources = collect_opening_sketches_from_selection(source_selection, "opening")
            if not sources:
                sources = collect_opening_sketches_from_document(doc, "opening")
                if len(sources) > 1:
                    raise UserFacingError(
                        "Se encontraron varios Sketches de aberturas. Seleccione explicitamente "
                        "uno o varios Sketches fuente."
                    )
            if not sources:
                raise UserFacingError(
                    "Seleccione uno o varios Sketches cuyas lineas representen vanos."
                )
            line_count = sum(len(sketch_segments(source)) for source in sources)
            if not line_count:
                raise UserFacingError("Los Sketches seleccionados no contienen lineas rectas utiles.")
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

            _log("Sketches fuente: %d" % len(sources))
            _log("Lineas detectadas: %d" % line_count)
            _log("Muros BIM candidatos: %d" % len(walls))
            dialog = OpeningParametersDialog(
                "opening",
                len(sources),
                len(walls),
                {"opening_height_mm": 2100.0, "opening_sill_mm": 0.0},
                parent=FreeCADGui.getMainWindow(),
            )
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            options = dialog.values()

            doc.openTransaction("FA Aberturas BIM desde Sketch")
            transaction_open = True
            structure = ensure_bim_structure(
                doc,
                building=chosen_building,
                level=target_level,
                elevation_mm=(target_level.Placement.Base.z if target_level is not None else 0.0),
            )
            target_level = structure["level"]
            adopt_auxiliary_sources(doc, target_level, sources)
            created, summary = create_openings_from_centerlines(
                doc,
                target_level,
                sources,
                walls,
                "opening",
                height_mm=options["height_mm"],
                sill_mm=options["sill_mm"],
                host_tolerance_mm=options["host_tolerance_mm"],
                replace_existing=options["replace_existing"],
            )
            doc.commitTransaction()
            transaction_open = False
            try:
                FreeCADGui.Selection.clearSelection()
                for obj in created:
                    FreeCADGui.Selection.addSelection(obj)
            except Exception:
                pass
            _log(
                "Resultado: creadas=%d omitidas=%d existentes=%d Level=%s"
                % (
                    summary["created_count"],
                    summary["rejected_count"],
                    summary["skipped_existing_count"],
                    target_level.Label,
                )
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            _log(str(exc), warning=True)
            handle_command_exception("FA Aberturas BIM desde Sketch", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
