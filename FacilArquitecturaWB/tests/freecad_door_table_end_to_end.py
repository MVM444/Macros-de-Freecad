"""FreeCAD 1.1.3 end-to-end smoke for ElementDataCore + door table.

Validates a user-named native preset door and the FA double door, table grouping,
hinge/swing transfer, dry-run, replacement, undo/redo and reopen.
"""

from __future__ import annotations

import json
import math
import os

import Arch
import FreeCAD
import Part
import Sketcher  # noqa: F401

from FacilArquitecturaWB.core.bim_structure_utils import add_to_level, ensure_bim_structure
from FacilArquitecturaWB.core.door_table_utils import (
    apply_door_records,
    ensure_door_table,
    extract_door_records,
    is_native_door,
    read_door_records,
    validate_door_records,
    write_door_records,
)
from FacilArquitecturaWB.core.opening_utils import native_door_opening_mode

DOC = "FADoorTableTarget"


def _line_sketch(doc, name, segments):
    sketch = doc.addObject("Sketcher::SketchObject", name)
    for first, second in segments:
        sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(*first), FreeCAD.Vector(*second)), False)
    return sketch


def _model(doc):
    structure = ensure_bim_structure(doc)
    level = structure["level"]
    wall_sketch = _line_sketch(
        doc,
        "Sketch_Muro",
        [((0, 0, 0), (7000, 0, 0)), ((2850, 0, 0), (2850, 2500, 0))],
    )
    wall = Arch.makeWall(wall_sketch, width=200.0, height=3000.0)
    wall.Label = "Muro prueba puertas"
    add_to_level(level, wall, source_sketch=wall_sketch)
    doors = _line_sketch(
        doc,
        "Sketch_Centros_Puertas",
        [((600, 0, 0), (1500, 0, 0)), ((3000, 0, 0), (4800, 0, 0))],
    )
    add_to_level(level, doors, source_sketch=doors)
    doc.recompute()
    return level, wall, doors


def _doors(doc):
    return [obj for obj in doc.Objects if is_native_door(obj)]


def _leaf_vector(door):
    leaf = max(list(door.Shape.Solids), key=lambda solid: float(solid.Volume))
    center = leaf.BoundBox.Center
    hinge = door.FA_HingePoint
    dx, dy = float(center.x - hinge.x), float(center.y - hinge.y)
    length = math.hypot(dx, dy)
    return (dx / length, dy / length)


def _records():
    return [
        {
            "ElementID": "P-001",
            "SourceSketch": "Sketch_Centros_Puertas",
            "GeometryIndex": 0,
            "CenterX": 1050.0,
            "CenterY": 0.0,
            "Length": 900.0,
            "AngleDeg": 0.0,
            "Height": 2100.0,
            "DoorType": "Puerta Oficina",
            "TypeSource": "native_preset",
            "TypeRef": "Simple door",
            "Preset": "Simple door",
            "LeafCount": 1,
            "HingeEndpoint": "END",
            "OpeningSide": "RIGHT",
            "OpensInward": True,
            "Opening": 100.0,
            "IfcType": "Door",
        },
        {
            "ElementID": "P-002",
            "SourceSketch": "Sketch_Centros_Puertas",
            "GeometryIndex": 1,
            "CenterX": 3900.0,
            "CenterY": 0.0,
            "Length": 1800.0,
            "AngleDeg": 0.0,
            "Height": 2200.0,
            "DoorType": "DoubleDoor",
            "TypeSource": "fa_double",
            "TypeRef": "architecture.door.double_leaf.glazed.europa",
            "Preset": "Double leaf glazed Europa",
            "LeafCount": 2,
            "HingeEndpoint": "BOTH",
            "OpeningSide": "AUTO",
            "OpensInward": None,
            "Opening": 50.0,
            "IfcType": "Door",
        },
    ]


def main():
    repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(repo_dir, ".codex_tmp")
    os.makedirs(output_dir, exist_ok=True)
    fcstd_path = os.path.join(output_dir, "fa_door_table_end_to_end.FCStd")
    active_before = getattr(FreeCAD.ActiveDocument, "Name", None)
    if DOC in FreeCAD.listDocuments():
        FreeCAD.closeDocument(DOC)
    result = {}
    try:
        doc = FreeCAD.newDocument(DOC)
        level, wall, sketch = _model(doc)
        sheet = ensure_door_table(doc)
        write_door_records(sheet, _records())
        table_group = doc.getObject("FA_Tables")
        assert table_group is not None and sheet in list(table_group.Group or [])
        records = read_door_records(sheet)
        validation = validate_door_records(records, [sketch])
        assert validation["counts"]["MATCH"] == 2, validation
        preview = apply_door_records(doc, level, records, [sketch], [wall], dry_run=True)
        assert preview["action_counts"]["CREATE"] == 2, preview
        applied = apply_door_records(doc, level, records, [sketch], [wall], dry_run=False)
        doors = _doors(doc)
        assert len(doors) == 2, [obj.Label for obj in doors]
        assert sorted(round(float(obj.Width.Value)) for obj in doors) == [900, 1800]
        by_id = {str(obj.FA_ElementID): obj for obj in doors}
        assert by_id["P-001"].FA_HingeEndpoint == "END"
        assert by_id["P-001"].FA_OpeningSide == "RIGHT"
        assert native_door_opening_mode(by_id["P-001"]) == "Mode1"
        assert _leaf_vector(by_id["P-001"])[1] < -0.9
        assert bool(by_id["P-001"].FA_OpensInward) is True
        assert by_id["P-001"].FA_DoorType == "Puerta Oficina"
        assert by_id["P-002"].FA_HingeEndpoint == "BOTH"
        assert by_id["P-002"].FA_DoorTypeSource == "fa_double"
        assert by_id["P-002"].FA_OpeningSide == "LEFT"
        assert bool(by_id["P-002"].FA_OpensInward) is True
        assert bool(by_id["P-002"].FA_CornerSnapped) is True
        assert abs(float(by_id["P-002"].FA_CornerShift_mm) - (-50.0)) <= 0.5
        assert all(list(obj.Hosts or []) == [wall] for obj in doors)

        extracted = extract_door_records(doc)
        assert {r["ElementID"] for r in extracted} == {"P-001", "P-002"}
        extracted_by_id = {r["ElementID"]: r for r in extracted}
        assert extracted_by_id["P-001"]["HingeEndpoint"] == "END"
        assert extracted_by_id["P-001"]["OpeningSide"] == "RIGHT"
        assert extracted_by_id["P-002"]["LeafCount"] >= 2

        second = apply_door_records(doc, level, records, [sketch], [wall], dry_run=False)
        assert second["action_counts"]["KEEP"] == 2, second
        sheet.set("H2", "2300")
        sheet.set("Q2", "LEFT")
        doc.recompute()
        changed = read_door_records(sheet)
        updated = apply_door_records(doc, level, changed, [sketch], [wall], dry_run=False)
        assert updated["action_counts"]["REPLACE"] == 1, updated
        assert updated["action_counts"]["KEEP"] == 1, updated
        assert len(_doors(doc)) == 2
        doc.undo()
        assert round(float({obj.FA_ElementID: obj for obj in _doors(doc)}["P-001"].Height.Value)) == 2100
        doc.redo()
        p1 = {obj.FA_ElementID: obj for obj in _doors(doc)}["P-001"]
        assert round(float(p1.Height.Value)) == 2300
        assert p1.FA_OpeningSide == "LEFT"
        assert native_door_opening_mode(p1) == "Mode2"
        assert _leaf_vector(p1)[1] > 0.9

        doc.saveAs(fcstd_path)
        FreeCAD.closeDocument(doc.Name)
        reopened = FreeCAD.openDocument(fcstd_path)
        reopened.recompute()
        assert len(_doors(reopened)) == 2
        assert reopened.getObject("Spreadsheet_Puertas") is not None
        assert reopened.getObject("FA_Tables") is not None
        result = {
            "validation": validation["counts"],
            "preview": preview["action_counts"],
            "applied": applied["action_counts"],
            "rerun": second["action_counts"],
            "updated": updated["action_counts"],
            "saved": fcstd_path,
        }
        FreeCAD.closeDocument(reopened.Name)
        print("FA_DOOR_TABLE_E2E_OK", json.dumps(result, sort_keys=True))
    finally:
        if DOC in FreeCAD.listDocuments():
            FreeCAD.closeDocument(DOC)
        if active_before and active_before in FreeCAD.listDocuments():
            FreeCAD.setActiveDocument(active_before)


if __name__ == "__main__":
    main()
