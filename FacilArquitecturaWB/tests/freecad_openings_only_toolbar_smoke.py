"""GUI smoke for the FA Opening Elements command and toolbar."""

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
        command = "FA_CreateOpeningsFromSketch"
        assert command in set(Gui.listCommands())
        assert command in set(InitGui.REGISTERED_COMMANDS)
        assert InitGui.REGISTERED_COMMANDS.count(command) == 1
        toolbars = [
            toolbar
            for toolbar in Gui.getMainWindow().findChildren(QtWidgets.QToolBar)
            if str(toolbar.windowTitle()) == "FA Aberturas BIM"
        ]
        assert len(toolbars) == 1
        actions = [str(action.objectName()) for action in toolbars[0].actions()]
        assert command in actions
        App.Console.PrintMessage(
            "FA_OPENINGS_ONLY_TOOLBAR_SMOKE_OK command=%s toolbar_count=%d\n"
            % (command, len(toolbars))
        )
    except Exception as exc:
        App.Console.PrintError("FA_OPENINGS_ONLY_TOOLBAR_SMOKE_FAILED %s\n" % exc)
    finally:
        QtWidgets.QApplication.instance().quit()


QtCore.QTimer.singleShot(1000, validate)
