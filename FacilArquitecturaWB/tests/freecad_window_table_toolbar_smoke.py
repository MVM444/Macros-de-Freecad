"""GUI smoke for the single FA Tabla de ventanas command."""

import FreeCADGui
from PySide import QtWidgets

import FacilArquitecturaWB.InitGui as InitGui


def main():
    assert "FA_WindowTable" in set(FreeCADGui.listCommands())
    assert "FA_WindowTable" in set(InitGui.REGISTERED_COMMANDS)
    main_window = FreeCADGui.getMainWindow()
    toolbars = list(main_window.findChildren(QtWidgets.QToolBar))
    matching = [bar for bar in toolbars if bar.windowTitle() == "FA Aberturas BIM"]
    assert len(matching) == 1
    actions = [action.objectName() for action in matching[0].actions()]
    assert actions.count("FA_WindowTable") == 1, actions
    print("FA_WINDOW_TABLE_TOOLBAR_OK", actions)


if __name__ == "__main__":
    main()
