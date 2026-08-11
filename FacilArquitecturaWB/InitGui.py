"""FacilArquitecturaWB GUI bootstrap.

Descripcion: registra el workbench Facil Arquitectura y sus comandos iniciales.
Objetivo: exponer comandos independientes y el asistente de reconstruccion BIM nativa.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 23:40 UTC-06:00.
Version: 0.9.0.
Instrucciones de mantenimiento: mantener comandos pequenos y cargar modulos del
workbench de forma explicita.
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui

from .commands import cmd_centerlines_from_selection
from .commands import cmd_collect_room_labels
from .commands import cmd_create_building_grid
from .commands import cmd_create_bim_structure
from .commands import cmd_create_closed_rooms
from .commands import cmd_create_doors_bim
from .commands import cmd_create_axes_columns_bim
from .commands import cmd_create_master_sketches
from .commands import cmd_create_modular_ceiling
from .commands import cmd_create_project
from .commands import cmd_rebuild_bim_model
from .commands import cmd_create_sample_geometry
from .commands import cmd_create_site_floor_bim
from .commands import cmd_create_service_platform_front
from .commands import cmd_create_walls_bim
from .commands import cmd_create_windows_bim
from .commands import cmd_door_centerlines_from_selection
from .commands import cmd_import_cad_reference
from .commands import cmd_window_centerlines_from_selection
from .commands import cmd_update_service_platform_front
from .commands import cmd_add_cashier_service_window
from .core.constants import BUILD_ID, LOG_PREFIX, VERSION, WORKBENCH_ID, WORKBENCH_NAME


REGISTERED_COMMANDS = []


class FacilArquitecturaWorkbench(FreeCADGui.Workbench):
    """Workbench definition for Facil Arquitectura."""

    MenuText = WORKBENCH_NAME
    ToolTip = "Organizar planos y crear base arquitectonica BIM editable | v%s build %s" % (VERSION, BUILD_ID)
    Icon = os.path.abspath(os.path.join(os.path.dirname(__file__), "resources", "icons", "facilarq.svg")).replace(
        os.sep, "/"
    )

    def Initialize(self):  # noqa: N802
        global REGISTERED_COMMANDS
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "VERSION CARGADA: v%s | build %s\n" % (VERSION, BUILD_ID)
        )
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Inicializando workbench Facil Arquitectura\n")
        commands = [
            cmd_import_cad_reference.register().CommandName,
            cmd_create_bim_structure.register().CommandName,
            cmd_rebuild_bim_model.register().CommandName,
            cmd_create_project.register().CommandName,
            cmd_create_master_sketches.register().CommandName,
            cmd_centerlines_from_selection.register().CommandName,
            cmd_window_centerlines_from_selection.register().CommandName,
            cmd_door_centerlines_from_selection.register().CommandName,
            cmd_create_doors_bim.register().CommandName,
            cmd_create_windows_bim.register().CommandName,
            cmd_create_closed_rooms.register().CommandName,
            cmd_collect_room_labels.register().CommandName,
            cmd_create_sample_geometry.register().CommandName,
            cmd_create_axes_columns_bim.register().CommandName,
            cmd_create_building_grid.register().CommandName,
            cmd_create_walls_bim.register().CommandName,
            cmd_create_site_floor_bim.register().CommandName,
            cmd_create_modular_ceiling.register().CommandName,
            cmd_create_service_platform_front.register().CommandName,
            cmd_update_service_platform_front.register().CommandName,
            cmd_add_cashier_service_window.register().CommandName,
        ]
        REGISTERED_COMMANDS = list(commands)
        self.appendToolbar("Facil Arquitectura", commands)
        self.appendMenu("Facil Arquitectura", commands)
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Comandos registrados: " + ", ".join(commands) + "\n")

    def Activated(self):  # noqa: N802
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Workbench activado | v%s build %s\n" % (VERSION, BUILD_ID)
        )

    def Deactivated(self):  # noqa: N802
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Workbench desactivado\n")


def _ensure_clean_registration():
    """Try to remove a previous registration during development reloads."""
    try:
        workbenches = dict(getattr(FreeCADGui, "listWorkbenches", lambda: {})() or {})
    except Exception:
        workbenches = {}
    if WORKBENCH_ID in workbenches and hasattr(FreeCADGui, "removeWorkbench"):
        try:
            FreeCADGui.removeWorkbench(WORKBENCH_ID)
        except Exception:
            pass


_ensure_clean_registration()
FreeCADGui.addWorkbench(FacilArquitecturaWorkbench())
