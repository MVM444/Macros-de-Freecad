"""Command to open the export TaskPanel.

Descripcion rapida: comando para seleccionar objetos y exportar a X3D.
Fecha y hora: 2026-03-11 17:40 UTC.
Instrucciones clave:
- Registrar logs con prefijo [GAMEEXPORT].
- Abrir el panel de exportacion cuando exista documento activo.
- Mantener cadenas ASCII.
"""

import os

import FreeCAD
import FreeCADGui

from ..ui import panel_export

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "gameexport.svg")
).replace(os.sep, "/")


class CommandClass:
    """FreeCAD command wrapper for the export TaskPanel."""

    CommandName = "GameEngineExport_Export"

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
        FreeCADGui.Control.showDialog(panel_export.ExportTaskPanel())

    def IsActive(self):  # noqa: N802
        return FreeCAD.ActiveDocument is not None
