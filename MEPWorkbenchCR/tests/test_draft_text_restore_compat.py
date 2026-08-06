"""FreeCAD regression test for HVAC Draft Text restore compatibility.

Run from FreeCAD's Python console or MCP with::

    from MEPWorkbenchCR.tests.test_draft_text_restore_compat import run
    run()
"""

import os
import tempfile

import Draft
import FreeCAD as App

from MEPWorkbenchCR.MEP.utils import draft_text_compat


DOC_NAME = "Test_HVAC_DraftTextRestore"


def _make_text(point):
    last_error = None
    creators = (
        lambda: Draft.make_text(["HVAC TEST", "12000 BTU/H"], point),
        lambda: Draft.make_text(["HVAC TEST", "12000 BTU/H"]),
        lambda: Draft.makeText(["HVAC TEST", "12000 BTU/H"], point),
    )
    for creator in creators:
        try:
            obj = creator()
            if obj is not None:
                return obj
        except Exception as exc:
            last_error = exc
    raise RuntimeError("No se pudo crear Draft Text de prueba: {0}".format(last_error))


def run():
    previous_doc_name = App.ActiveDocument.Name if App.ActiveDocument is not None else ""
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)

    temp_path = os.path.join(tempfile.gettempdir(), DOC_NAME + ".FCStd")
    if os.path.exists(temp_path):
        os.remove(temp_path)

    doc = App.newDocument(DOC_NAME)
    try:
        assert draft_text_compat.patch_draft_text_class()
        text_obj = _make_text(App.Vector(100.0, 200.0, 0.0))
        text_obj.addProperty("App::PropertyString", "MEPType", "MEP")
        text_obj.MEPType = "HVACEquipmentInfo2D"

        draft_text_compat.ensure_text_proxy_state(text_obj)
        assert "stored_type" in text_obj.Proxy.__dict__

        # Reproduce the FreeCAD 1.1 ordering that previously raised:
        # onDocumentRestored ran before loads supplied instance state.
        del text_obj.Proxy.stored_type
        assert text_obj.Proxy.stored_type is None
        text_obj.Proxy.onDocumentRestored(text_obj)
        assert draft_text_compat.ensure_text_proxy_state(text_obj)

        doc.recompute()
        doc.saveAs(temp_path)
        App.closeDocument(DOC_NAME)

        reopened = App.openDocument(temp_path)
        reopened.recompute()
        reopened.recompute()
        texts = [
            obj
            for obj in reopened.Objects
            if str(getattr(obj, "MEPType", "") or "") == "HVACEquipmentInfo2D"
        ]
        assert len(texts) == 1
        assert "stored_type" in getattr(texts[0].Proxy, "__dict__", {})
        assert draft_text_compat.repair_document(reopened, mep_only=True) == 0
        assert len(reopened.Objects) == 1
        App.closeDocument(reopened.Name)
    finally:
        if DOC_NAME in App.listDocuments():
            App.closeDocument(DOC_NAME)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if previous_doc_name and previous_doc_name in App.listDocuments():
            App.setActiveDocument(previous_doc_name)

    return {
        "early_restore_callback": True,
        "stored_type_persisted": True,
        "no_duplicates": True,
        "temporary_document_closed": True,
    }


if __name__ == "__main__":
    print(run())
