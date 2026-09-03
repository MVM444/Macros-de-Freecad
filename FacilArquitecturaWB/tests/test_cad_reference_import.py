"""Tests for CAD reference unit handling without a FreeCAD GUI."""

from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from FacilArquitecturaWB.core import cad_reference_import


class CadReferenceImportTests(unittest.TestCase):
    def test_insert_consumes_compatibility_layer_once(self):
        calls = []

        class FakeImportDXF:
            @staticmethod
            def insert(filename, document_name):
                calls.append(("insert", filename, document_name))
                return "ok"

        @contextmanager
        def fake_compat(**kwargs):
            calls.append(("enter", kwargs["import_dxf_module"]))
            yield
            calls.append(("exit",))

        with mock.patch.object(cad_reference_import, "dxf_waitcursor_workaround", fake_compat):
            result = cad_reference_import._insert_dxf_with_compat(
                FakeImportDXF,
                Path("sample.dxf"),
                "Document",
            )

        self.assertEqual("ok", result)
        self.assertEqual("enter", calls[0][0])
        self.assertIs(FakeImportDXF, calls[0][1])
        self.assertEqual(("insert", "sample.dxf", "Document"), calls[1])
        self.assertEqual(("exit",), calls[2])

    def test_manual_scale_overrides_incorrect_mm_header_for_metre_drawing(self):
        self.assertEqual(1000.0, cad_reference_import.manual_scaling_for("m", insunits=4))
        self.assertEqual(1000.0, cad_reference_import.resolved_mm_per_unit("m", insunits=4))

    def test_metre_header_needs_no_extra_manual_scale(self):
        self.assertEqual(1.0, cad_reference_import.manual_scaling_for("m", insunits=6))

    def test_auto_uses_header_without_extra_scale(self):
        self.assertEqual(1.0, cad_reference_import.manual_scaling_for("auto", insunits=6))
        self.assertEqual(1000.0, cad_reference_import.resolved_mm_per_unit("auto", insunits=6))

    def test_read_dxf_header_units(self):
        content = "\n".join(
            (
                "0", "SECTION", "2", "HEADER",
                "9", "$INSUNITS", "70", "4",
                "9", "$MEASUREMENT", "70", "1",
                "0", "ENDSEC", "0", "EOF", "",
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.dxf"
            path.write_text(content, encoding="ascii")
            result = cad_reference_import.read_dxf_header_units(path)
        self.assertEqual({"insunits": 4, "measurement": 1}, result)

    def test_safe_document_name_does_not_use_visible_label_syntax(self):
        self.assertEqual("Puriscal_Aire_Acondicionado", cad_reference_import.safe_document_name("Puriscal Aire Acondicionado"))
        self.assertEqual("CAD_2026_Plano", cad_reference_import.safe_document_name("2026 Plano"))

    def test_repeated_import_gets_a_unique_internal_document_name(self):
        existing = {"Puriscal_Aire_Acondicionado", "Puriscal_Aire_Acondicionado_002"}
        self.assertEqual(
            "Puriscal_Aire_Acondicionado_003",
            cad_reference_import.unique_document_name("Puriscal Aire Acondicionado", existing),
        )

    def test_fa_profile_is_rich_and_uses_efficient_fused_mode(self):
        profile = cad_reference_import.IMPORT_PROFILE
        self.assertEqual(("Boolean", False), profile["dxfUseLegacyImporter"])
        self.assertEqual(("Boolean", True), profile["dxfImportAsFused"])
        self.assertEqual(("Integer", 3), profile["DxfImportMode"])
        self.assertEqual(("Boolean", True), profile["dxftext"])
        self.assertEqual(("Boolean", True), profile["dxflayout"])
        self.assertEqual(("Boolean", True), profile["dxfstarblocks"])
        self.assertEqual(("Boolean", True), profile["dxfUseDraftVisGroups"])

    def test_temporary_profile_restores_values_and_removes_new_keys(self):
        class FakePrefs:
            def __init__(self):
                self.values = {
                    "dxfImportAsShapes": ("Boolean", True),
                    "DxfImportMode": ("Integer", 2),
                    "dxfScaling": ("Float", 1000.0),
                }

            def GetContents(self):
                return [(kind, name, value) for name, (kind, value) in self.values.items()]

            def _set(self, kind, name, value):
                self.values[name] = (kind, value)

            def SetBool(self, name, value):
                self._set("Boolean", name, bool(value))

            def SetInt(self, name, value):
                self._set("Integer", name, int(value))

            def SetFloat(self, name, value):
                self._set("Float", name, float(value))

            def SetString(self, name, value):
                self._set("String", name, str(value))

            def _remove(self, name):
                self.values.pop(name, None)

            RemBool = RemInt = RemFloat = RemString = _remove

        prefs = FakePrefs()
        kinds = {name: kind for name, (kind, _value) in cad_reference_import.IMPORT_PROFILE.items()}
        kinds.update({"dxfScaling": "Float", "dxfShowDialog": "Boolean"})
        snapshot = cad_reference_import._snapshot_preferences(prefs, kinds)
        profile = cad_reference_import._apply_import_profile(prefs, 1.0)

        self.assertEqual(("Boolean", True), prefs.values["dxfImportAsFused"])
        self.assertEqual(("Integer", 3), prefs.values["DxfImportMode"])
        self.assertEqual(("Float", 1.0), prefs.values["dxfScaling"])

        cad_reference_import._restore_preferences(prefs, snapshot, kinds)
        self.assertEqual(("Boolean", True), prefs.values["dxfImportAsShapes"])
        self.assertEqual(("Integer", 2), prefs.values["DxfImportMode"])
        self.assertEqual(("Float", 1000.0), prefs.values["dxfScaling"])
        self.assertNotIn("dxfImportAsFused", prefs.values)
        self.assertNotIn("dxfShowDialog", prefs.values)
        self.assertTrue(profile)


if __name__ == "__main__":
    unittest.main()
