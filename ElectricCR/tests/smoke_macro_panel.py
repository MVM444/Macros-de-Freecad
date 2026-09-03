"""Non-GUI smoke checks for the ElectricCR macro panel registry."""

import os
import sys


HERE = os.path.abspath(os.path.dirname(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import FreeCADGui as Gui


_registered = []
if not hasattr(Gui, "addCommand"):
    Gui.addCommand = lambda name, obj: _registered.append(str(name))
if not hasattr(Gui, "listCommands"):
    Gui.listCommands = lambda: list(_registered)

from ElectricCR.commands import macro_launcher, macros


def main():
    groups = macros.register_predefined_macros(REPO)
    macro_launcher.register_macro_launcher(groups)
    rows = macro_launcher._metadata_rows()
    assert rows, "no se registraron macros"
    assert any(row.get("icon_status") == "RAYO" for row in rows)
    assert any(row.get("icon_status") == "ESPECIFICO" for row in rows)
    rayo = next(row for row in rows if row.get("icon_status") == "RAYO")
    specific = next(row for row in rows if row.get("icon_status") == "ESPECIFICO")
    assert rayo.get("state") == "REVISAR"
    assert specific.get("state") == "OK"
    missing = dict(specific, file_exists=False)
    assert macro_launcher._state_for(missing) == "ERROR"
    assert all(row.get("macro_rel") for row in rows)
    assert all(row.get("toolbar") for row in rows)
    assert sum(1 for row in rows if macro_launcher._filter_match(row, "Todas")) == len(rows)
    assert sum(1 for row in rows if macro_launcher._filter_match(row, "Con Rayo")) > 0
    widgets, qtcore, _qtgui = macro_launcher._qmods()
    assert widgets is not None and qtcore is not None
    settings = macro_launcher._settings(qtcore)
    assert settings is not None
    key = "macro_panel/smoke_width"
    settings.setValue(key, 321)
    settings.sync()
    assert int(settings.value(key)) == 321
    settings.remove(key)
    settings.sync()
    print("PASS smoke_macro_panel groups=%d rows=%d" % (len(groups), len(rows)))


if __name__ == "__main__":
    main()
