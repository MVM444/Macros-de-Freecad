"""FA_CenterlinesFromSelection command.

Descripcion: crea Sketches de centros desde shapes, layers o Part::Feature Compound seleccionados.
Funcion principal: delega al nucleo la extraccion no destructiva, incluida la descomposicion virtual de Compound/CompSolid.
Mantenimiento: no exigir Part Explode como paso previo; conservar intacto el objeto fuente y registrar mensajes FACILARQ utiles.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-09-01 14:35 America/Costa_Rica.
Version: 0.6.0.
"""

from __future__ import annotations

import os
import time

import FreeCADGui

from ..core.centerline_utils import create_centerline_sketch_from_objects
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.bim_structure_utils import adopt_auxiliary_sources, ensure_auxiliary_parent
from ..core.project_structure import active_or_new_document, msg

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
            "ToolTip": "Crear Sketches parametricos de centros desde shapes, grupos o Compound sin explotar la fuente.",
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
            doc = active_or_new_document()
            support_parent, target_level = ensure_auxiliary_parent(doc, selection, legacy_key="master_sketches")
            try:
                doc.openTransaction("FA Centros desde seleccion")
                transaction_open = True
            except Exception:
                transaction_open = False
            sketch, segments = create_centerline_sketch_from_objects(doc, support_parent, selection)
            if target_level is not None:
                adopt_auxiliary_sources(doc, target_level, [sketch] + selection)
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
