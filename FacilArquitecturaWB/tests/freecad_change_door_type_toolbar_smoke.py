"""GUI smoke test for FA_ChangeDoorType registration and toolbar placement."""

from __future__ import annotations

import os
import sys

import FreeCAD
import FreeCADGui as Gui
from PySide import QtWidgets


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)


def main():
    import FacilArquitecturaWB.InitGui  # noqa: F401

    Gui.activateWorkbench("FacilArquitecturaWorkbench")
    command = Gui.Command.get("FA_ChangeDoorType")
    assert command is not None
    toolbars = [
        item
        for item in Gui.getMainWindow().findChildren(QtWidgets.QToolBar)
        if str(item.windowTitle()) == "FA Aberturas BIM"
    ]
    assert len(toolbars) == 1
    actions = [str(action.objectName()) for action in toolbars[0].actions()]
    assert actions.count("FA_ChangeDoorType") == 1, actions
    assert "FA_CreateDoorsFromSketch" in actions
    assert "FA_InsertDoubleDoorBIM" in actions
    FreeCAD.Console.PrintMessage(
        "FA_CHANGE_DOOR_TYPE_TOOLBAR_OK command=FA_ChangeDoorType toolbar_count=1\n"
    )


if __name__ == "__main__":
    main()
