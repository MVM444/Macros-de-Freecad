"""Command to reopen Facil Arquitectura Getting Started tips.

Name: commands/cmd_first_steps.py
Purpose: allow the user to reopen the initial guidance even after disabling its
automatic appearance.
Main behavior: invoke ``ui.first_steps.show_startup_tips(force=True)``.
Maintenance notes: keep detailed Help content in ui.help_dialog, not here.
Version: 0.2.0
Date and time: 2026-09-02 12:10 America/Costa_Rica
"""

from __future__ import annotations

import os

import FreeCADGui

from .. import i18n
from ..ui.first_steps import show_startup_tips

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "fa_help.svg")
).replace(os.sep, "/")


class CommandClass:
    CommandName = "FA_FirstSteps"

    def GetResources(self):
        return {
            "MenuText": i18n.bi("FA Primeros pasos", "FA Getting Started"),
            "ToolTip": i18n.bi(
                "Mostrar nuevamente la ventana de bienvenida y flujo inicial.",
                "Show the welcome and initial-workflow window again.",
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):
        show_startup_tips(force=True)

    def IsActive(self):
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
