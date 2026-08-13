"""GameEngineExportWB GUI bootstrap."""

import os

import FreeCAD
import FreeCADGui

from .commands import cmd_add_light_properties
from .commands import cmd_bim_doors_windows
from .commands import cmd_export_and_launch
from .commands import cmd_import_json_example
from .commands import cmd_open_panel
from .commands import cmd_quick_examples
from .commands import cmd_reload_workbench
from .commands import cmd_roof_quick_example

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

    def Initialize(self):  # noqa: N802
        """Register commands and set up menus and toolbars."""
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Initializing workbench menus\n")
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Workbench source: " + os.path.dirname(__file__) + "\n"
        )
        export_command = cmd_open_panel.CommandClass()
        export_launch_command = cmd_export_and_launch.CommandClass()
        light_command = cmd_add_light_properties.CommandClass()
        quick_example_command = cmd_quick_examples.CommandClass()
        import_json_command = cmd_import_json_example.CommandClass()
        bim_doors_windows_command = cmd_bim_doors_windows.CommandClass()
        roof_command = cmd_roof_quick_example.CommandClass()
        reload_command = cmd_reload_workbench.CommandClass()

        registered = (
            export_command,
            export_launch_command,
            light_command,
            quick_example_command,
            import_json_command,
            bim_doors_windows_command,
            roof_command,
            reload_command,
        )
        for command in registered:
            FreeCADGui.addCommand(command.CommandName, command)

        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Registered export command: " + export_command.CommandName + "\n"
        )
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX
            + "Registered one-click export command: "
            + export_launch_command.CommandName
            + "\n"
        )
        commands = [command.CommandName for command in registered]
        self.appendToolbar("Game Engine Export", commands)
        self.appendMenu("Game Engine Export", commands)

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
            try:
                FreeCADGui.activateWorkbench("StartWorkbench")
            except Exception:
                pass
            FreeCADGui.removeWorkbench(WORKBENCH_ID)
            FreeCAD.Console.PrintMessage(
                LOG_PREFIX + "Removed previous workbench registration\n"
            )
        except Exception as exc:  # pragma: no cover
            FreeCAD.Console.PrintWarning(
                LOG_PREFIX
                + "Could not remove previous workbench registration: "
                + str(exc)
                + "\n"
            )


_ensure_clean_registration()
FreeCADGui.addWorkbench(GameEngineExportWorkbench())
