"""Command to open the export TaskPanel.

Descripcion rapida: comando para seleccionar objetos y exportar a X3D.
Fecha y hora: 2026-03-11 17:40 UTC.
Instrucciones clave:
- Registrar logs con prefijo [GAMEEXPORT].
- Abrir el panel de exportacion cuando exista documento activo.
- Mantener cadenas ASCII.
"""

import importlib
import os
import sys

import FreeCAD
import FreeCADGui

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "gameexport.svg")
).replace(os.sep, "/")

RUNTIME_MODULE_NAMES = (
    "GameEngineExportWB.core.persist",
    "GameEngineExportWB.core.gamestart",
    "GameEngineExportWB.core.lights",
    "GameEngineExportWB.core.exporter_x3d",
    "GameEngineExportWB.ui.output_defaults",
    "GameEngineExportWB.ui.panel_info",
    "GameEngineExportWB.ui.panel_export",
)


def _reload_or_import(module_name):
    """Reload a live module or import it again after a loader purge."""
    module = sys.modules.get(module_name)
    if module is None:
        return importlib.import_module(module_name), "imported"
    return importlib.reload(module), "reloaded"


def _reload_export_runtime():
    """Reload the export stack before constructing a new TaskPanel.

    FreeCAD keeps Python modules in memory for the complete application
    session. Reload the modules in dependency order so a new panel cannot use
    an updated UI with an older geometry or light implementation.
    """
    importlib.invalidate_caches()
    reloaded = []
    for module_name in RUNTIME_MODULE_NAMES:
        current, action = _reload_or_import(module_name)
        reloaded.append(current)
        FreeCAD.Console.PrintMessage(
            "[GAMEEXPORT] Runtime module "
            + action
            + ": "
            + str(getattr(current, "__name__", "unknown"))
            + " | version="
            + str(getattr(current, "DEBUG_VERSION", "unversioned"))
            + " | path="
            + str(getattr(current, "__file__", "unknown"))
            + "\n"
        )
    return reloaded[-1]


class CommandClass:
    """FreeCAD command wrapper for the export TaskPanel."""

    CommandName = "GameEngineExport_Export_Current"

    def GetResources(self):  # noqa: N802 (FreeCAD API)
        return {
            "MenuText": "Exportar X3D",
            "ToolTip": "Seleccionar objetos y exportar a X3D",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        FreeCAD.Console.PrintMessage("[GAMEEXPORT] Opening export panel\n")
        try:
            if hasattr(FreeCADGui.Control, "activeDialog") and FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        except Exception as exc:  # pragma: no cover - runtime guard
            FreeCAD.Console.PrintWarning(f"[GAMEEXPORT] Could not close active dialog: {exc}\n")
        try:
            current_panel = _reload_export_runtime()
        except Exception as exc:  # pragma: no cover - runtime guard
            FreeCAD.Console.PrintWarning(
                "[GAMEEXPORT][WARN] Runtime reload failed; importing panel directly: "
                + str(exc)
                + "\n"
            )
            current_panel = importlib.import_module("GameEngineExportWB.ui.panel_export")
        FreeCAD.Console.PrintMessage(
            "[GAMEEXPORT] Export panel module: "
            + str(getattr(current_panel, "__file__", "unknown"))
            + "\n"
        )
        FreeCADGui.Control.showDialog(current_panel.ExportTaskPanel())

    def IsActive(self):  # noqa: N802
        return FreeCAD.ActiveDocument is not None
