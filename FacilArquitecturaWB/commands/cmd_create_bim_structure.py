"""FA_CreateBIMStructure command.

Descripcion: crea o reutiliza Building y Building Storey nativos.
Objetivo: preparar la jerarquia BIM visible sin crear FA_Project.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 21:24 UTC-06:00.
Version: 0.1.0.
Instrucciones de mantenimiento: conservar CommandName estable y una sola transaccion.
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from ..core.bim_structure_utils import ensure_bim_structure
from ..core.command_errors import handle_command_exception
from ..core.project_structure import active_or_new_document, msg
from ..ui.dialog_bim_structure import BIMStructureDialog


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "bim_structure.svg")
).replace(os.sep, "/")
PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/BIMStructure"


class CommandClass:
    CommandName = "FA_CreateBIMStructure"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Crear estructura BIM",
            "ToolTip": "Crear o reutilizar Building y Level nativos de FreeCAD.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            doc = active_or_new_document()
            prefs = FreeCAD.ParamGet(PREFERENCES_PATH)
            dialog = BIMStructureDialog(
                prefs.GetString("building_name", "Edificio"),
                prefs.GetString("level_name", "Nivel 00"),
                prefs.GetFloat("elevation_mm", 0.0),
                parent=FreeCADGui.getMainWindow(),
            )
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            values = dialog.values()
            prefs.SetString("building_name", values["building_name"])
            prefs.SetString("level_name", values["level_name"])
            prefs.SetFloat("elevation_mm", values["elevation_mm"])
            doc.openTransaction("FA Crear estructura BIM")
            transaction_open = True
            result = ensure_bim_structure(doc, update_existing=True, **values)
            doc.recompute()
            doc.commitTransaction()
            transaction_open = False
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(result["level"])
            msg(
                "Estructura BIM lista: %s > %s"
                % (result["building"].Label, result["level"].Label)
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Crear estructura BIM", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
