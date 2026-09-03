"""FreeCAD 1.1.3 end-to-end smoke for ElementDataCore + window table."""

from __future__ import annotations

import json
import os

import Arch
import FreeCAD
import Part
import Sketcher  # noqa: F401

from FacilArquitecturaWB.core.bim_structure_utils import add_to_level, ensure_bim_structure
from FacilArquitecturaWB.core.opening_utils import create_openings_from_centerlines
from FacilArquitecturaWB.core.window_table_utils import (
    _find_manual_element_id_conflict,
    apply_window_records,
    ensure_window_table,
    export_table_native,
    extract_window_records,
    import_table_native,
    is_native_window,
    read_window_records,
    validate_window_records,
    window_sill_height,
    write_window_records,
)


SOURCE = "FAWindowTableSource"
TARGET = "FAWindowTableTarget"
MANUAL = "FAWindowTableManualConflict"


def _line_sketch(doc, name, segments):
    sketch = doc.addObject("Sketcher::SketchObject", name)
    for first, second in segments:
        sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(*first), FreeCAD.Vector(*second)), False)
    return sketch


def _model(doc, window_segments):
    structure = ensure_bim_structure(doc)
    level = structure["level"]
    wall_sketch = _line_sketch(doc, "Sketch_Muro", [((0, 0, 0), (6000, 0, 0))])
    wall = Arch.makeWall(wall_sketch, width=200.0, height=3000.0)
    wall.Label = "Muro destino"
    add_to_level(level, wall, source_sketch=wall_sketch)
    windows = _line_sketch(doc, "Sketch_Centros_Ventanas", window_segments)
    add_to_level(level, windows, source_sketch=windows)
    doc.recompute()
    return level, wall, windows


def _windows(doc):
    return [obj for obj in doc.Objects if is_native_window(obj)]


def main():
    repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(repo_dir, ".codex_tmp")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "Spreadsheet_Ventanas_roundtrip.csv")
    fcstd_path = os.path.join(output_dir, "fa_window_table_end_to_end.FCStd")
    active_before = getattr(FreeCAD.ActiveDocument, "Name", None)
    for name in (SOURCE, TARGET, MANUAL):
        if name in FreeCAD.listDocuments():
            FreeCAD.closeDocument(name)
    result = {}
    try:
        source_doc = FreeCAD.newDocument(SOURCE)
        source_level, source_wall, source_sketch = _model(
            source_doc,
            [((500, 0, 0), (1500, 0, 0)), ((2500, 0, 0), (3700, 0, 0))],
        )
        source_doc.openTransaction("Create source windows")
        created, _summary = create_openings_from_centerlines(
            source_doc,
            source_level,
            [source_sketch],
            [source_wall],
            "window",
            height_mm=1250.0,
            sill_mm=850.0,
            replace_existing=True,
        )
        source_doc.commitTransaction()
        assert len(created) == 2
        records = extract_window_records(source_doc)
        assert len(records) == 2
        sheet = ensure_window_table(source_doc)
        write_window_records(sheet, records)
        export_table_native(sheet, csv_path)

        target_doc = FreeCAD.newDocument(TARGET)
        target_level, target_wall, target_sketch = _model(
            target_doc,
            [((2450, 0, 0), (3750, 0, 0)), ((450, 0, 0), (1550, 0, 0))],
        )
        copied = target_doc.copyObject(sheet, True)
        target_doc.recompute()
        assert copied.TypeId == "Spreadsheet::Sheet"
        assert copied.get("A2") == "V-001"
        target_doc.removeObject(copied.Name)
        imported = import_table_native(target_doc, csv_path)
        imported.set("H2", "1400")
        imported.set("I2", "800")
        target_doc.recompute()
        target_records = read_window_records(imported)
        validation = validate_window_records(target_records, [target_sketch])
        assert validation["counts"]["CAMBIO"] == 2, validation
        preview = apply_window_records(
            target_doc,
            target_level,
            target_records,
            [target_sketch],
            [target_wall],
            dry_run=True,
        )
        assert preview["action_counts"]["CREATE"] == 2, preview
        assert len(_windows(target_doc)) == 0
        applied = apply_window_records(
            target_doc,
            target_level,
            target_records,
            [target_sketch],
            [target_wall],
            dry_run=False,
        )
        target_windows = _windows(target_doc)
        assert len(target_windows) == 2
        assert sorted(round(float(obj.Width.Value)) for obj in target_windows) == [1100, 1300]
        assert sorted(round(float(obj.Height.Value)) for obj in target_windows) == [1250, 1400]
        assert sorted(round(window_sill_height(obj)) for obj in target_windows) == [800, 850]
        assert all(obj.Hosts == [target_wall] for obj in target_windows)
        second = apply_window_records(
            target_doc,
            target_level,
            target_records,
            [target_sketch],
            [target_wall],
            dry_run=False,
        )
        assert second["action_counts"]["KEEP"] == 2, second
        assert len(_windows(target_doc)) == 2
        imported.set("H2", "1500")
        target_doc.recompute()
        changed_records = read_window_records(imported)
        updated = apply_window_records(
            target_doc,
            target_level,
            changed_records,
            [target_sketch],
            [target_wall],
            dry_run=False,
        )
        assert updated["action_counts"]["REPLACE"] == 1, updated
        assert updated["action_counts"]["KEEP"] == 1, updated
        assert len(_windows(target_doc)) == 2
        target_doc.undo()
        assert sorted(round(float(obj.Height.Value)) for obj in _windows(target_doc)) == [1250, 1400]
        target_doc.redo()
        assert len(_windows(target_doc)) == 2
        assert sorted(round(float(obj.Height.Value)) for obj in _windows(target_doc)) == [1250, 1500]
        target_doc.recompute()
        target_doc.saveAs(fcstd_path)
        target_name = target_doc.Name
        FreeCAD.closeDocument(target_name)
        reopened = FreeCAD.openDocument(fcstd_path)
        reopened.recompute()
        reopened_windows = _windows(reopened)
        assert len(reopened_windows) == 2
        assert reopened.getObject("Spreadsheet_Ventanas") is not None
        assert all(list(obj.Hosts or []) for obj in reopened_windows)
        reopened_widths = sorted(float(obj.Width.Value) for obj in reopened_windows)
        reopened_heights = sorted(float(obj.Height.Value) for obj in reopened_windows)
        reopened_sills = sorted(window_sill_height(obj) for obj in reopened_windows)
        FreeCAD.closeDocument(reopened.Name)

        manual_doc = FreeCAD.newDocument(MANUAL)
        manual_level, manual_wall, manual_sketch = _model(
            manual_doc,
            [((1000, 0, 0), (2000, 0, 0))],
        )
        manual_created, _manual_summary = create_openings_from_centerlines(
            manual_doc,
            manual_level,
            [manual_sketch],
            [manual_wall],
            "window",
            height_mm=1200.0,
            sill_mm=900.0,
            replace_existing=True,
        )
        assert len(manual_created) == 1
        manual_window = manual_created[0]
        manual_window.FA_GeneratedBy = "Manual"
        if "FA_ElementID" not in manual_window.PropertiesList:
            manual_window.addProperty("App::PropertyString", "FA_ElementID", "FacilArquitectura")
        manual_window.FA_ElementID = "V-MANUAL-001"
        manual_doc.recompute()
        manual_records = extract_window_records(manual_doc)
        assert manual_window.FA_GeneratedBy == "Manual"
        assert manual_records[0]["ElementID"] == "V-MANUAL-001", manual_records
        assert _find_manual_element_id_conflict(manual_doc, "V-MANUAL-001") is manual_window
        manual_name = manual_window.Name
        manual_conflict = apply_window_records(
            manual_doc,
            manual_level,
            manual_records,
            [manual_sketch],
            [manual_wall],
            dry_run=False,
        )
        assert manual_conflict["action_counts"]["SKIP"] == 1, manual_conflict
        assert len(_windows(manual_doc)) == 1
        assert manual_doc.getObject(manual_name) is manual_window
        result = {
            "source_records": len(records),
            "validation": validation["counts"],
            "preview": preview["action_counts"],
            "applied": applied["action_counts"],
            "rerun": second["action_counts"],
            "updated": updated["action_counts"],
            "widths": reopened_widths,
            "heights": reopened_heights,
            "sills": reopened_sills,
            "manual_conflict": manual_conflict["action_counts"],
            "saved": fcstd_path,
        }
        FreeCAD.closeDocument(manual_doc.Name)
        print("FA_WINDOW_TABLE_E2E_OK", json.dumps(result, sort_keys=True))
    finally:
        for name in (SOURCE, TARGET, MANUAL):
            if name in FreeCAD.listDocuments():
                FreeCAD.closeDocument(name)
        if active_before and active_before in FreeCAD.listDocuments():
            FreeCAD.setActiveDocument(active_before)


if __name__ == "__main__":
    main()
