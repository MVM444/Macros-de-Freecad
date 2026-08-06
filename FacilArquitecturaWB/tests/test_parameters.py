"""Regression tests for non-destructive parameter-sheet updates."""

from __future__ import annotations

import sys
import types
import unittest
from unittest import mock


if "FreeCAD" not in sys.modules:
    freecad = types.ModuleType("FreeCAD")
    freecad.Console = types.SimpleNamespace(
        PrintMessage=lambda _message: None,
        PrintWarning=lambda _message: None,
        PrintError=lambda _message: None,
    )
    sys.modules["FreeCAD"] = freecad

from FacilArquitecturaWB.core import parameters  # noqa: E402


class FakeSheet:
    Name = parameters.PARAM_SHEET_NAME
    Label = parameters.PARAM_SHEET_NAME

    def __init__(self):
        self.cells = {"A2": "existing", "B2": "9", "A3": "user_parameter", "B3": "77"}

    def get(self, address):
        return self.cells.get(address, "")

    def set(self, address, value):
        self.cells[address] = str(value)

    def setAlias(self, _address, _alias):
        return None

    def addProperty(self, _kind, name, _group, _description):
        setattr(self, name, None)


class FakeDocument:
    def __init__(self, sheet):
        self.Objects = [sheet]


class ParametersTests(unittest.TestCase):
    def test_missing_parameter_is_appended_after_unknown_user_rows(self):
        sheet = FakeSheet()
        doc = FakeDocument(sheet)
        defaults = [("existing", 1.0), ("new_parameter", 2.0)]

        with mock.patch.object(parameters, "DEFAULT_PARAMETERS", defaults):
            parameters.ensure_parameter_sheet(doc)

        self.assertEqual("user_parameter", sheet.cells["A3"])
        self.assertEqual("77", sheet.cells["B3"])
        self.assertEqual("new_parameter", sheet.cells["A4"])
        self.assertEqual("2.0", sheet.cells["B4"])


if __name__ == "__main__":
    unittest.main()
