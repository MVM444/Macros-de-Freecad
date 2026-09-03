"""FreeCAD 1.1.3 smoke for ElectricCR RoomResolver phase 2A.

The smoke creates only temporary documents and a temporary FCStd file.  It
does not create luminaires or modify any user model.
"""

from __future__ import annotations

import os
import sys
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
import Part


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MACRO_PATH = os.path.join(REPO_ROOT, "Iluminación", "Actualizar_Iluminacion_Completa.FCMacro")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _load_helpers():
    with open(MACRO_PATH, "r", encoding="utf-8") as handle:
        source = handle.read()
    cutoff = source.index("\ntry:\n    run()", source.index("\ndef run("))
    namespace = {"__name__": "electriccr_roomresolver_phase2a", "__file__": MACRO_PATH}
    exec(compile(source[:cutoff], MACRO_PATH, "exec"), namespace)
    return namespace


def _face(x, y, width=4000.0, depth=3000.0):
    wire = Part.makePolygon(
        [
            App.Vector(x, y, 0),
            App.Vector(x + width, y, 0),
            App.Vector(x + width, y + depth, 0),
            App.Vector(x, y + depth, 0),
            App.Vector(x, y, 0),
        ]
    )
    return Part.Face(wire)


def _space(doc, name, label, x=0.0, y=0.0):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = _face(x, y)
    obj.addProperty("App::PropertyString", "IfcType", "BIM")
    obj.addProperty("App::PropertyString", "FA_RoomUID", "FacilArquitectura")
    obj.IfcType = "Space"
    obj.FA_RoomUID = "UID-" + name
    return obj


def _area(doc, group, name, label, x=0.0, y=0.0):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = _face(x, y)
    obj.addProperty("App::PropertyString", "ElectricCRTipo", "ElectricCR")
    obj.addProperty("App::PropertyLength", "Length", "Draft")
    obj.addProperty("App::PropertyLength", "Height", "Draft")
    obj.ElectricCRTipo = "Area"
    obj.Length = 4000.0
    obj.Height = 3000.0
    group.addObject(obj)
    return obj


def _physical_signature(obj):
    placement = obj.Placement
    shape = obj.Shape
    return {
        "name": obj.Name,
        "type": obj.TypeId,
        "placement": (
            placement.Base.x,
            placement.Base.y,
            placement.Base.z,
            placement.Rotation.Q,
        ),
        "shape_hash": int(shape.hashCode()),
        "properties": tuple(sorted(obj.PropertiesList)),
    }


def _new_doc(name):
    if App.listDocuments().get(name) is not None:
        App.closeDocument(name)
    doc = App.newDocument(name)
    doc.UndoMode = 1
    return doc


def _close(name):
    if App.listDocuments().get(name) is not None:
        App.closeDocument(name)


def run():
    helpers = _load_helpers()
    created = []
    temp_path = os.path.join(tempfile.gettempdir(), "ECR_RoomResolver_Phase2A.FCStd")
    if os.path.exists(temp_path):
        os.remove(temp_path)
    try:
        # Space only: calculation is read-only for the architectural object.
        doc = _new_doc("ECR_Phase2A_SpaceOnly")
        created.append(doc.Name)
        space = _space(doc, "SpaceOnly", "Oficina Space")
        doc.recompute()
        before = _physical_signature(space)
        rows, _stats, audit = helpers["_collect_resolved_room_rows"](doc, None, {})
        assert len(rows) == 1 and rows[0]["room_source"] == "NATIVE_SPACE"
        assert rows[0]["area"] == 12.0 and rows[0]["filas"] >= 1 and rows[0]["columnas"] >= 1
        assert audit["candidate_count"] == 1
        assert _physical_signature(space) == before
        assert "Rows" not in space.PropertiesList and "Columns" not in space.PropertiesList

        calc = helpers["_ensure_calculation_group"](doc)
        sheet, first_rows = helpers["update_datos_recintos"](doc, None, calc, "DatosRecintos", False)
        count_after_first = len(doc.Objects)
        sheet2, second_rows = helpers["update_datos_recintos"](doc, None, calc, "DatosRecintos", False)
        assert sheet2 is sheet and len(first_rows) == len(second_rows) == 1
        assert len(doc.Objects) == count_after_first
        assert [sheet.get("%s1" % chr(65 + index)) for index in range(12)] == [
            "Recinto", "Area (m^2)", "Largo (m)", "Ancho (m)", "Altura (m)",
            "Filas", "Columnas", "Descripcion", "Cantidad Luminarias", "Tipo Luminaria",
            "Lumens Unitarios", "Potencia Unitaria (W)",
        ]
        assert not any("luminaria" in str(getattr(obj, "Label", "")).lower() for obj in doc.Objects)
        assert _physical_signature(space) == before

        doc.recompute()
        doc.saveAs(temp_path)
        saved_doc_name = doc.Name
        saved_sheet_name = sheet.Name
        App.closeDocument(saved_doc_name)
        created.remove(saved_doc_name)
        reopened = App.openDocument(temp_path)
        created.append(reopened.Name)
        assert reopened.getObject("SpaceOnly") is not None
        assert reopened.getObject(saved_sheet_name) is not None
        assert "Rows" not in reopened.getObject("SpaceOnly").PropertiesList
        reopened_name = reopened.Name
        App.closeDocument(reopened_name)
        created.remove(reopened_name)

        # Legacy only: preserve the established Rows/Columns property contract.
        doc = _new_doc("ECR_Phase2A_LegacyOnly")
        created.append(doc.Name)
        group = doc.addObject("App::DocumentObjectGroup", "Areas")
        area = _area(doc, group, "AreaLegacy", "Oficina Legacy")
        doc.recompute()
        old_rows, _old_stats = helpers["_collect_area_rows"](group, {})
        new_rows, _new_stats, audit = helpers["_collect_resolved_room_rows"](doc, group, {})
        assert len(old_rows) == len(new_rows) == 1
        for key in ("recinto", "area", "largo", "ancho", "filas", "columnas", "cantidad"):
            assert old_rows[0][key] == new_rows[0][key]
        assert new_rows[0]["room_source"] == "LEGACY_AREA"
        assert hasattr(area, "Rows") and hasattr(area, "Columns")
        assert audit["room_count"] == 1

        # Space + legacy overlap: Space is the sole calculation identity.
        doc = _new_doc("ECR_Phase2A_Overlap")
        created.append(doc.Name)
        group = doc.addObject("App::DocumentObjectGroup", "Areas")
        area = _area(doc, group, "AreaOverlap", "Oficina Duplicada")
        space = _space(doc, "SpaceOverlap", "Oficina Autoritativa")
        doc.recompute()
        before_space = _physical_signature(space)
        before_area_shape = int(area.Shape.hashCode())
        rows, _stats, audit = helpers["_collect_resolved_room_rows"](doc, group, {})
        assert len(rows) == 1 and rows[0]["obj"] is space
        assert rows[0]["room_source"] == "NATIVE_SPACE"
        assert any(item.get("status") == "SUPPRESSED" for item in audit["diagnostics"])
        assert _physical_signature(space) == before_space
        assert int(area.Shape.hashCode()) == before_area_shape

        # Full calculation command path without a GUI dialog or physical devices.
        doc = _new_doc("ECR_Phase2A_FullRun")
        created.append(doc.Name)
        space = _space(doc, "SpaceFullRun", "Sala de Espera")
        doc.recompute()
        full_run_signature = _physical_signature(space)
        original_qtwidgets = helpers["QtWidgets"]
        helpers["QtWidgets"] = None
        try:
            helpers["run"]()
            full_run_count = len(doc.Objects)
            helpers["run"]()
        finally:
            helpers["QtWidgets"] = original_qtwidgets
        assert len(doc.Objects) == full_run_count
        full_run_sheets = [obj for obj in doc.Objects if obj.TypeId == "Spreadsheet::Sheet"]
        assert len(full_run_sheets) == 2
        assert any(sheet.get("A1") == "Recinto" for sheet in full_run_sheets)
        assert _physical_signature(space) == full_run_signature
        assert not any("luminaria" in str(getattr(obj, "Label", "")).lower() for obj in doc.Objects)

        # Ambiguous and NOT_FOUND are explicit safe outcomes.
        doc = _new_doc("ECR_Phase2A_Ambiguous")
        created.append(doc.Name)
        first = _space(doc, "SpaceA", "Space A")
        second = _space(doc, "SpaceB", "Space B")
        doc.recompute()
        before_pair = (_physical_signature(first), _physical_signature(second))
        rows, _stats, audit = helpers["_collect_resolved_room_rows"](doc, None, {})
        assert rows == []
        assert any(item.get("status") == "AMBIGUOUS" for item in audit["diagnostics"])
        from CRBIMCore.freecad_room_adapter import resolve_room_for_point

        outside = resolve_room_for_point(doc, [10000.0, 10000.0, 0.0])
        assert outside["status"] == "NOT_FOUND"
        assert (_physical_signature(first), _physical_signature(second)) == before_pair

        print(
            "ECR_ROOMRESOLVER_PHASE2A_OK "
            "space_only=1 legacy_only=1 overlap_space_wins=1 ambiguous_safe=1 "
            "not_found_safe=1 datos_contract=12 idempotent=1 physical_signature_unchanged=1"
        )
    finally:
        Gui.Selection.clearSelection()
        for name in list(created):
            _close(name)
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    run()
