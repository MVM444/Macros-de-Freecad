"""FA_CenterlinesFromSelection command.

Descripcion: crea un sketch generico de centros desde shapes seleccionados o un layer seleccionado.
Fecha: 2026-07-14
Version: 0.4.0
Instrucciones: usar como asistente desde DXF; no pretende detectar BIM completo automaticamente.
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from ..core.centerline_utils import create_centerline_sketch_from_objects
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import ensure_project_structure, msg

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "centerlines_from_selection.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """FreeCAD command for extracting generic centerlines from selection."""

    CommandName = "FA_CenterlinesFromSelection_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Centros desde seleccion",
            "ToolTip": "Crear Sketches parametricos de centros, separados por espesor detectado.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            selection = list(FreeCADGui.Selection.getSelection() or [])
            if not selection:
                raise UserFacingError("Seleccione un layer, grupo o shapes antes de ejecutar el comando.")
            generated = [
                obj
                for obj in selection
                if str(getattr(obj, "FA_Role", "") or "").strip().lower() == "centerlines"
                or str(getattr(obj, "Label", getattr(obj, "Name", "")) or "").startswith("Sketch_Centros")
            ]
            if generated:
                selection = [obj for obj in selection if obj not in generated]
                msg("Sketches de centros removidos de la seleccion de entrada: %d" % len(generated))
            if not selection:
                raise UserFacingError(
                    "No use Sketch_Centros como entrada de FA Centros. Seleccione el layer o los Shapes originales."
                )
            doc, _root, groups = ensure_project_structure()
            try:
                doc.openTransaction("FA Centros desde seleccion")
                transaction_open = True
            except Exception:
                transaction_open = False
            sketch, segments = create_centerline_sketch_from_objects(doc, groups["master_sketches"], selection)
            doc.recompute()
            if transaction_open:
                doc.commitTransaction()
                transaction_open = False
            related = [sketch] + list(getattr(sketch, "FA_RelatedCenterlineSketches", []) or [])
            try:
                FreeCADGui.Selection.clearSelection()
                for related_sketch in related:
                    FreeCADGui.Selection.addSelection(related_sketch)
            except Exception:
                pass
            msg(
                "FA_CenterlinesFromSelection completado. Sketches: %d | lineas: %d"
                % (len(related), len(segments))
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Centros desde seleccion", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
