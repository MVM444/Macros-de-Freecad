"""GUI smoke test for Facil Arquitectura toolbar organization."""

from __future__ import annotations

import os
import sys

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def validate():
    try:
        from FacilArquitecturaWB import InitGui

        Gui.activateWorkbench("FacilArquitecturaWorkbench")
        Gui.updateGui()
        commands = set(Gui.listCommands())
        required_command = "FA_InsertDoubleDoorBIM"
        if required_command not in commands:
            raise AssertionError("Comando no registrado: " + required_command)
        if required_command not in set(InitGui.REGISTERED_COMMANDS):
            raise AssertionError("Comando ausente de REGISTERED_COMMANDS")
        titles = [
            str(toolbar.windowTitle())
            for toolbar in Gui.getMainWindow().findChildren(QtWidgets.QToolBar)
        ]
        required_toolbars = {
            "FA Proyecto BIM",
            "FA Estructura BIM",
            "FA Aberturas BIM",
            "FA Recintos y cielos",
            "FA Plataforma",
        }
        missing = sorted(required_toolbars - set(titles))
        if missing:
            raise AssertionError("Barras ausentes: " + ", ".join(missing))
        duplicated = sorted(
            title for title in required_toolbars if titles.count(title) != 1
        )
        if duplicated:
            raise AssertionError(
                "Barras con conteo distinto de uno: "
                + ", ".join(
                    "%s=%d" % (title, titles.count(title)) for title in duplicated
                )
            )
        App.Console.PrintMessage(
            "FA_DOUBLE_DOOR_TOOLBAR_SMOKE_OK command=%s toolbars=%s\n"
            % (required_command, ", ".join(sorted(required_toolbars)))
        )
    except Exception as exc:
        App.Console.PrintError("FA_DOUBLE_DOOR_TOOLBAR_SMOKE_FAILED %s\n" % exc)
    finally:
        QtWidgets.QApplication.instance().quit()


QtCore.QTimer.singleShot(750, validate)
