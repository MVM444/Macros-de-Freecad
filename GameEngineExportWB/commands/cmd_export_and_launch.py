"""One-click X3D export followed by Castle Game Engine launch."""

import importlib
import os
import sys

import FreeCAD
import FreeCADGui


ICON_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "resources",
        "icons",
        "export_launch_x3d.svg",
    )
).replace(os.sep, "/")


def _get_open_panel_module():
    module_name = "GameEngineExportWB.commands.cmd_open_panel"
    return sys.modules.get(module_name) or importlib.import_module(module_name)


class CommandClass:
    """Export with current settings and launch Castle without showing the panel."""

    CommandName = "GameEngineExport_ExportAndLaunch"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "Exportar X3D y lanzar Castle",
            "ToolTip": (
                "Genera un X3D nuevo con la configuracion actual "
                "y lo abre en Castle Game Engine"
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        FreeCAD.Console.PrintMessage(
            "[GAMEEXPORT] One-click X3D export and Castle launch requested\n"
        )
        try:
            if (
                hasattr(FreeCADGui.Control, "activeDialog")
                and FreeCADGui.Control.activeDialog()
            ):
                FreeCADGui.Control.closeDialog()
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                "[GAMEEXPORT][WARN] Could not close active dialog: "
                + str(exc)
                + "\n"
            )

        try:
            open_panel = _get_open_panel_module()
            panel_module = open_panel._reload_export_runtime()
            panel = panel_module.ExportTaskPanel()
        except Exception as exc:
            FreeCAD.Console.PrintError(
                "[GAMEEXPORT] Could not prepare one-click export: "
                + str(exc)
                + "\n"
            )
            return

        cge_path = panel.cge_path_line.text().strip()
        if not cge_path or not os.path.isfile(cge_path):
            FreeCAD.Console.PrintError(
                "[GAMEEXPORT] Castle executable is not configured or does not exist. "
                "Open the export panel and configure it once.\n"
            )
            return

        panel.launch_checkbox.setChecked(True)
        if panel._export_scene():
            FreeCAD.Console.PrintMessage(
                "[GAMEEXPORT] One-click X3D export and Castle launch completed\n"
            )

    def IsActive(self):  # noqa: N802
        return FreeCAD.ActiveDocument is not None
