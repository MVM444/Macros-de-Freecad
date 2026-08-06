"""Tests for CAD reference unit handling without a FreeCAD GUI."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from FacilArquitecturaWB.core import cad_reference_import


class CadReferenceImportTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
