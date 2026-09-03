"""FreeCAD smoke test for the deterministic FA CAD import profile.

FreeCAD objetivo: 1.1.3
Fecha: 2026-08-26
"""

from __future__ import annotations

import os
import tempfile

import FreeCAD as App


PREFERENCE_KINDS = {
    "dxfUseLegacyImporter": "Boolean",
    "dxfImportAsDraft": "Boolean",
    "dxfImportAsPrimitives": "Boolean",
    "dxfImportAsShapes": "Boolean",
    "dxfImportAsFused": "Boolean",
    "DxfImportMode": "Integer",
    "dxftext": "Boolean",
    "dxflayout": "Boolean",
    "dxfstarblocks": "Boolean",
    "dxfUseDraftVisGroups": "Boolean",
    "dxfScaling": "Float",
    "dxfShowDialog": "Boolean",
}


def _minimal_dxf():
    pairs = (
        (0, "SECTION"), (2, "HEADER"),
        (9, "$ACADVER"), (1, "AC1015"),
        (9, "$INSUNITS"), (70, 4),
        (9, "$MEASUREMENT"), (70, 1),
        (0, "ENDSEC"),
        (0, "SECTION"), (2, "TABLES"),
        (0, "TABLE"), (2, "LAYER"), (70, 1),
        (0, "LAYER"), (2, "Muros"), (70, 0), (62, 7), (6, "CONTINUOUS"),
        (0, "ENDTAB"),
        (0, "ENDSEC"),
        (0, "SECTION"), (2, "ENTITIES"),
        (0, "LINE"), (8, "Muros"), (10, 0), (20, 0), (30, 0),
        (11, 4000), (21, 0), (31, 0),
        (0, "TEXT"), (8, "Muros"), (10, 500), (20, 500), (30, 0),
        (40, 200), (1, "RECINTO PRUEBA"),
        (0, "ENDSEC"), (0, "EOF"),
    )
    return "\n".join(str(value) for pair in pairs for value in pair) + "\n"


def run():
    from FacilArquitecturaWB.core.cad_reference_import import (
        _preference_contents,
        _restore_preferences,
        _snapshot_preferences,
        import_cad_reference,
    )

    prefs = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft")
    original = _snapshot_preferences(prefs, PREFERENCE_KINDS)
    document_name = None
    try:
        prefs.SetBool("dxfUseLegacyImporter", False)
        prefs.SetBool("dxfImportAsDraft", False)
        prefs.SetBool("dxfImportAsPrimitives", False)
        prefs.SetBool("dxfImportAsShapes", True)
        prefs.SetBool("dxfImportAsFused", False)
        prefs.SetInt("DxfImportMode", 2)
        prefs.SetBool("dxftext", False)
        hostile = _snapshot_preferences(prefs, PREFERENCE_KINDS)

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "fa_import_profile_smoke.dxf")
            with open(path, "w", encoding="ascii") as stream:
                stream.write(_minimal_dxf())
            result = import_cad_reference(path, unit_key="mm", fit_view=False)

        doc = result["document"]
        document_name = doc.Name
        after = _snapshot_preferences(prefs, PREFERENCE_KINDS)
        assert after == hostile, "FA no restauro el perfil global hostil de prueba."
        assert result["imported_object_count"] >= 2
        assert not doc.FileName
        assert doc.getObject("FA_CADImportMetadata") is not None
        assert any(type(getattr(obj, "Proxy", None)).__name__ == "Text" for obj in doc.Objects)
        assert any(getattr(obj, "Shape", None) is not None for obj in doc.Objects)
        assert _preference_contents(prefs)["dxfImportAsShapes"] == ("Boolean", True)
        print(
            "[FACILARQ_TEST] PASS - perfil CAD rico/eficiente temporal y preferencias restauradas"
        )
        print(
            "[FACILARQ_TEST] objetos=%d documento_sin_guardar=%s"
            % (len(doc.Objects), not bool(doc.FileName))
        )
        return True
    finally:
        if document_name and document_name in App.listDocuments():
            App.closeDocument(document_name)
        _restore_preferences(prefs, original, PREFERENCE_KINDS)


if __name__ == "__main__":
    run()
