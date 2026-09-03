"""Regression tests for the self-disabling FreeCAD DXF compatibility layer."""

from __future__ import annotations

import unittest

from FacilArquitecturaWB.core import freecad_compat


class FakeApp:
    @staticmethod
    def Version():
        return ["1", "1", "3", "20260725 (Git shallow)", "Unknown", "2026/07/25"]


class FutureApp:
    @staticmethod
    def Version():
        return ["1", "2", "0", "future", "Unknown", "future-build"]


class RecordingConsole:
    messages = []
    warnings = []

    @classmethod
    def PrintMessage(cls, message):
        cls.messages.append(message)

    @classmethod
    def PrintWarning(cls, message):
        cls.warnings.append(message)


class LoggingApp(FakeApp):
    Console = RecordingConsole


class FakeGui:
    @staticmethod
    def suspendWaitCursor():
        return "suspend-native"

    @staticmethod
    def resumeWaitCursor():
        return "resume-native"


class ExternallyPatchedGui(FakeGui):
    __name__ = "FreeCADGui"


class FakeFreeCADGuiReference:
    def suspendWaitCursor(self):
        pass

    def resumeWaitCursor(self):
        pass

    def suspendCursor(self):
        pass

    def resumeCursor(self):
        pass


FreeCADGui = FakeFreeCADGuiReference()


def affected_importer(_filename, _doc_name=None):
    FreeCADGui.suspendWaitCursor()
    FreeCADGui.resumeWaitCursor()


def fixed_importer(_filename, _doc_name=None):
    FreeCADGui.suspendCursor()
    FreeCADGui.resumeCursor()


def mixed_importer(_filename, _doc_name=None):
    FreeCADGui.suspendWaitCursor()


class FakeImportDXF:
    def __init__(self, implementation):
        self._import_dxf_file = implementation
        self.insert_calls = []

    def insert(self, filename, document_name):
        self.insert_calls.append((filename, document_name))
        return "inserted"


class FreeCADCompatTests(unittest.TestCase):
    def setUp(self):
        self.gui = FakeGui()
        self.original_suspend = self.gui.suspendWaitCursor
        self.original_resume = self.gui.resumeWaitCursor
        RecordingConsole.messages = []
        RecordingConsole.warnings = []

    def assert_gui_restored(self):
        self.assertIs(self.gui.suspendWaitCursor, self.original_suspend)
        self.assertIs(self.gui.resumeWaitCursor, self.original_resume)

    def test_structural_old_pattern_is_affected(self):
        importer = FakeImportDXF(affected_importer)
        assessment = freecad_compat.detect_dxf_waitcursor_bug(FakeApp, self.gui, importer)
        self.assertEqual(freecad_compat.AFFECTED, assessment.state)
        self.assertEqual("ast", assessment.inspection_method)
        self.assertTrue(
            freecad_compat.needs_dxf_waitcursor_workaround(FakeApp, self.gui, importer)
        )

    def test_affected_context_is_temporary_and_exactly_restored(self):
        importer = FakeImportDXF(affected_importer)
        with freecad_compat.dxf_waitcursor_workaround(FakeApp, self.gui, importer) as session:
            self.assertTrue(session.applied)
            self.assertIs(self.gui.suspendWaitCursor, freecad_compat._noop_waitcursor)
            self.assertIs(self.gui.resumeWaitCursor, freecad_compat._noop_waitcursor)
            self.assertEqual("inserted", importer.insert("sample.dxf", "Doc"))
        self.assertTrue(session.restored)
        self.assert_gui_restored()
        self.assertEqual([("sample.dxf", "Doc")], importer.insert_calls)

    def test_required_diagnostic_messages_are_emitted(self):
        importer = FakeImportDXF(affected_importer)
        with freecad_compat.dxf_waitcursor_workaround(LoggingApp, self.gui, importer):
            pass
        output = "".join(RecordingConsole.messages)
        self.assertIn("[FACILARQ][COMPAT] FreeCAD version: 1.1.3", output)
        self.assertIn("DXF WaitCursor bug #31637: affected", output)
        self.assertIn(
            "[FACILARQ][IMPORT] Workaround #31637 aplicado temporalmente",
            output,
        )

    def test_exception_inside_context_still_restores_exact_functions(self):
        importer = FakeImportDXF(affected_importer)
        with self.assertRaisesRegex(RuntimeError, "controlled failure"):
            with freecad_compat.dxf_waitcursor_workaround(FakeApp, self.gui, importer):
                raise RuntimeError("controlled failure")
        self.assert_gui_restored()

    def test_fixed_importer_disables_workaround_and_inserts_normally(self):
        importer = FakeImportDXF(fixed_importer)
        assessment = freecad_compat.detect_dxf_waitcursor_bug(FutureApp, self.gui, importer)
        self.assertEqual(freecad_compat.NOT_AFFECTED, assessment.state)
        self.assertFalse(
            freecad_compat.needs_dxf_waitcursor_workaround(FutureApp, self.gui, importer)
        )
        with freecad_compat.dxf_waitcursor_workaround(FutureApp, self.gui, importer) as session:
            self.assertFalse(session.applied)
            self.assertIs(self.gui.suspendWaitCursor, self.original_suspend)
            self.assertEqual("inserted", importer.insert("future.dxf", "FutureDoc"))
        self.assert_gui_restored()
        self.assertEqual([("future.dxf", "FutureDoc")], importer.insert_calls)

    def test_mixed_pattern_is_unknown_and_does_not_patch(self):
        importer = FakeImportDXF(mixed_importer)
        assessment = freecad_compat.detect_dxf_waitcursor_bug(FutureApp, self.gui, importer)
        self.assertEqual(freecad_compat.UNKNOWN, assessment.state)
        with freecad_compat.dxf_waitcursor_workaround(FutureApp, self.gui, importer) as session:
            self.assertFalse(session.applied)
            self.assertIs(self.gui.suspendWaitCursor, self.original_suspend)
        self.assert_gui_restored()

    def test_externally_patched_native_gui_is_unknown_and_is_not_overwritten(self):
        importer = FakeImportDXF(affected_importer)
        gui = ExternallyPatchedGui()
        original_suspend = gui.suspendWaitCursor
        original_resume = gui.resumeWaitCursor
        assessment = freecad_compat.detect_dxf_waitcursor_bug(FakeApp, gui, importer)
        self.assertEqual(freecad_compat.UNKNOWN, assessment.state)
        with freecad_compat.dxf_waitcursor_workaround(FakeApp, gui, importer) as session:
            self.assertFalse(session.applied)
            self.assertIs(gui.suspendWaitCursor, original_suspend)
            self.assertIs(gui.resumeWaitCursor, original_resume)

    def test_fixed_pattern_wins_over_113_version_fallback(self):
        importer = FakeImportDXF(fixed_importer)
        assessment = freecad_compat.detect_dxf_waitcursor_bug(FakeApp, self.gui, importer)
        self.assertEqual(freecad_compat.NOT_AFFECTED, assessment.state)
        self.assertFalse(
            freecad_compat.needs_dxf_waitcursor_workaround(FakeApp, self.gui, importer)
        )


if __name__ == "__main__":
    unittest.main()
