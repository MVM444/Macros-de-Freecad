"""Facil Arquitectura integrated Help command.

Name: commands/cmd_help.py
Purpose: open the canonical bilingual Help dialog.
Main behavior: thin GUI command; all Help content lives in ui.help_dialog.
Maintenance notes: keep this command small and do not duplicate Help text here.
Version: 0.2.0
Date and time: 2026-09-02 15:35 America/Costa_Rica
"""

from __future__ import annotations

import importlib
import os

import FreeCADGui

from .. import i18n

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "fa_help.svg")
).replace(os.sep, "/")


class CommandClass:
    CommandName = "FA_Help"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Ayuda", "FA Help"),
            "ToolTip": i18n.bi(
                "Abrir Primeros pasos, flujo DWG/DXF, flujo de trabajo, barras, Demo e Informacion.",
                "Open Getting Started, DWG/DXF workflow, full workflow, toolbars, Demo, and Information.",
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        module = importlib.import_module("FacilArquitecturaWB.ui.help_dialog")
        module.show_help_dialog()

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
