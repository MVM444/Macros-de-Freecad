"""Reload GameEngineExportWB commands and export modules without restarting."""

import importlib
import os

import FreeCAD
import FreeCADGui

from . import cmd_add_light_properties
from . import cmd_bim_doors_windows
from . import cmd_import_json_example
from . import cmd_open_panel
from . import cmd_quick_examples
from . import cmd_roof_quick_example


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "gameexport.svg")
).replace(os.sep, "/")


def reload_workbench_runtime():
    """Replace registered command handlers and reload the export runtime."""
    try:
        if hasattr(FreeCADGui.Control, "activeDialog") and FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
    except Exception as exc:
        FreeCAD.Console.PrintWarning(
            "[GAMEEXPORT][WARN] Could not close active dialog before reload: "
            + str(exc)
            + "\n"
        )

    importlib.invalidate_caches()
    command_modules = (
        cmd_open_panel,
        cmd_add_light_properties,
        cmd_quick_examples,
        cmd_import_json_example,
        cmd_bim_doors_windows,
        cmd_roof_quick_example,
    )
    for module in command_modules:
        current = importlib.reload(module)
        command = current.CommandClass()
        FreeCADGui.addCommand(command.CommandName, command)
        FreeCAD.Console.PrintMessage(
            "[GAMEEXPORT] Command reloaded: "
            + command.CommandName
            + " | path="
            + str(getattr(current, "__file__", "unknown"))
            + "\n"
        )

    current_open_panel = importlib.reload(cmd_open_panel)
    current_panel = current_open_panel._reload_export_runtime()
    FreeCAD.Console.PrintMessage(
        "[GAMEEXPORT] Workbench runtime reload complete: panel="
        + str(getattr(current_panel, "DEBUG_VERSION", "unversioned"))
        + "\n"
    )
    return True


class CommandClass:
    """FreeCAD command wrapper for a runtime-only Workbench reload."""

    CommandName = "GameEngineExport_ReloadWorkbench"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "Recargar Workbench / Reload Workbench",
            "ToolTip": "Reload GameEngineExportWB code without restarting FreeCAD",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        FreeCAD.Console.PrintMessage("[GAMEEXPORT] Workbench runtime reload requested\n")
        try:
            reload_workbench_runtime()
        except Exception as exc:
            FreeCAD.Console.PrintError(
                "[GAMEEXPORT] Workbench runtime reload failed: " + str(exc) + "\n"
            )

    def IsActive(self):  # noqa: N802
        return True
