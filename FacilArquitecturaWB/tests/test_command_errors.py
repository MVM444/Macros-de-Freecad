"""Tests for command-level error reporting without propagated tracebacks."""

from __future__ import annotations

import sys
import types
import unittest


def _install_gui_stub():
    if "FreeCADGui" not in sys.modules:
        gui = types.ModuleType("FreeCADGui")
        gui.Selection = types.SimpleNamespace(getSelection=lambda: [])
        gui.addCommand = lambda _name, _command: None
        gui.getMainWindow = lambda: None
        sys.modules["FreeCADGui"] = gui


_install_gui_stub()

from FacilArquitecturaWB.commands import cmd_create_axes_columns_bim  # noqa: E402
from FacilArquitecturaWB.core import command_errors  # noqa: E402


class CommandErrorTests(unittest.TestCase):
    def test_user_error_is_classified_as_warning(self):
        messages = []
        original_warn = command_errors.warn
        original_show = command_errors._show_message
        command_errors.warn = lambda text: messages.append(text)
        command_errors._show_message = lambda title, message, critical=False: messages.append(
            (title, message, critical)
        )
        try:
            result = command_errors.handle_command_exception(
                "FA Prueba",
                command_errors.UserFacingError("Seleccione un objeto."),
            )
        finally:
            command_errors.warn = original_warn
            command_errors._show_message = original_show

        self.assertEqual("warning", result)
        self.assertIn("FA Prueba: Seleccione un objeto.", messages)
        self.assertIn(("Facil Arquitectura", "Seleccione un objeto.", False), messages)

    def test_axis_command_without_selection_does_not_propagate(self):
        reported = []
        original_handler = cmd_create_axes_columns_bim.handle_command_exception
        cmd_create_axes_columns_bim.handle_command_exception = lambda label, exception: reported.append(
            (label, exception)
        )
        try:
            cmd_create_axes_columns_bim.CommandClass().Activated()
        finally:
            cmd_create_axes_columns_bim.handle_command_exception = original_handler

        self.assertEqual(1, len(reported))
        self.assertEqual("FA Ejes y columnas BIM", reported[0][0])
        self.assertIsInstance(reported[0][1], command_errors.UserFacingError)


if __name__ == "__main__":
    unittest.main()
