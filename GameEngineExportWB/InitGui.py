"""GameEngineExportWB GUI bootstrap

Descripcion rapida: registro del workbench Game Engine Export WB y comando principal.
Fecha y hora: 2025-10-13 13:54 UTC.
Instrucciones clave:
- Registrar comandos sin cargar modulos pesados hasta ser necesarios.
- Mantener cadenas tecnicas en ASCII.
- Todos los logs deben usar prefijo [GAMEEXPORT].
- Priorizar comentarios claros para futuras ampliaciones.
"""

import FreeCAD
import FreeCADGui
import os

from .commands import cmd_open_panel

LOG_PREFIX = "[GAMEEXPORT] "
WORKBENCH_ID = "GameEngineExportWorkbench"


class GameEngineExportWorkbench(FreeCADGui.Workbench):
    """Workbench definition for Game Engine Export WB."""

    MenuText = "Game Engine Export WB"
    ToolTip = "Export FreeCAD scenes to Castle Game Engine"
    _icon_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "resources", "icons", "gameexport.svg")
    )
    Icon = _icon_path.replace(os.sep, "/")

    def Initialize(self):  # noqa: N802 (FreeCAD naming)
        """Register command and set up menus and toolbars."""
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Initializing workbench menus\n")
        command = cmd_open_panel.CommandClass()
        FreeCADGui.addCommand(command.CommandName, command)
        self.appendToolbar("Game Engine Export", [command.CommandName])
        self.appendMenu("Game Engine Export", [command.CommandName])

    def Activated(self):  # noqa: N802
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Workbench activated\n")

    def Deactivated(self):  # noqa: N802
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Workbench deactivated\n")


def _ensure_clean_registration():
    """Remove existing GameEngineExport registration before addWorkbench."""
    try:
        workbenches = dict(getattr(FreeCADGui, "listWorkbenches", lambda: {})() or {})
    except Exception:
        workbenches = {}

    if WORKBENCH_ID in workbenches and hasattr(FreeCADGui, "removeWorkbench"):
        try:
            # Some FreeCAD builds refuse removal while active.
            try:
                FreeCADGui.activateWorkbench("StartWorkbench")
            except Exception:
                pass
            FreeCADGui.removeWorkbench(WORKBENCH_ID)
            FreeCAD.Console.PrintMessage(LOG_PREFIX + "Removed previous workbench registration\n")
        except Exception as exc:  # pragma: no cover - runtime guard
            FreeCAD.Console.PrintWarning(
                LOG_PREFIX + "Could not remove previous workbench registration: " + str(exc) + "\n"
            )


_ensure_clean_registration()
FreeCADGui.addWorkbench(GameEngineExportWorkbench())
