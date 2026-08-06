"""Documented placeholder for the future BIM cashier service window."""

from __future__ import annotations

import os

import FreeCADGui

from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.bim_utils import supports_arch_window


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "cashier_window.svg")
).replace(os.sep, "/")


class CommandClass:
    CommandName = "FA_AddCashierServiceWindow"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Ventanilla de caja (proxima etapa)",
            "ToolTip": "Comando previsto para alojar una ventanilla fija en un muro BIM seleccionado.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            selection = list(FreeCADGui.Selection.getSelection() or [])
            if len(selection) != 1:
                raise UserFacingError("Seleccione un unico muro BIM para la futura ventanilla de caja.")
            wall = selection[0]
            if not _looks_like_wall(wall):
                raise UserFacingError("El objeto seleccionado no parece ser un muro BIM/Arch.")
            if not supports_arch_window():
                raise UserFacingError("Arch.makeWindow no esta disponible en esta instalacion de FreeCAD.")
            raise UserFacingError(
                "La ventanilla de caja queda prevista, pero no se crea en esta primera entrega. "
                "Se implementara sobre el muro seleccionado en una etapa independiente."
            )
        except Exception as exc:
            handle_command_exception("FA Ventanilla de caja", exc)

    def IsActive(self):  # noqa: N802
        return bool(FreeCADGui.ActiveDocument)


def _looks_like_wall(obj):
    proxy = getattr(obj, "Proxy", None)
    proxy_name = proxy.__class__.__name__.lower() if proxy is not None else ""
    ifc_type = str(getattr(obj, "IfcType", "") or "").lower()
    role = str(getattr(obj, "FA_WallType", "") or "").lower()
    return "wall" in proxy_name or ifc_type == "wall" or bool(role)


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
