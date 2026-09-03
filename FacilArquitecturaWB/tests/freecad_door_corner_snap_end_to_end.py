"""FreeCAD 1.1.3 end-to-end matrix for FA door corner snapping.

Validates physical Mode1/Mode2 selection, START/END direction invariance,
NO_FIT, jamb-only crossing behavior, native Host/cut, idempotence, Undo/Redo
and save/reopen without touching user documents.
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
from FacilArquitecturaWB.core.opening_utils import (
    create_openings_from_centerlines,
    native_door_opening_mode,
)

DOC = "FADoorCornerSnapE2E"


def _line_sketch(doc, name, segments):
    sketch = doc.addObject("Sketcher::SketchObject", name)
    for first, second in segments:
        sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(*first), FreeCAD.Vector(*second)), False)
    return sketch


def _native_doors(doc):
    return [obj for obj in doc.Objects if str(getattr(obj, "IfcType", "") or "") == "Door"]


def _actual_leaf_vector(door):
    """Measure the opened leaf from the largest door solid, not FA metadata."""
    solids = list(door.Shape.Solids)
    assert len(solids) >= 2, door.Name
    leaf = max(solids, key=lambda solid: float(solid.Volume))
    center = leaf.BoundBox.Center
    hinge = door.FA_HingePoint
    dx, dy = float(center.x - hinge.x), float(center.y - hinge.y)
    length = math.hypot(dx, dy)
    assert length > 100.0, (door.Name, dx, dy)
    return (dx / length, dy / length)


def _assert_vector(actual, expected, tolerance=0.12):
    dot = actual[0] * expected[0] + actual[1] * expected[1]
    assert dot >= 1.0 - tolerance, (actual, expected, dot)


def _door_report(door):
    hinge = getattr(door, "FA_HingePoint", FreeCAD.Vector())
    actual = _actual_leaf_vector(door) if door.FA_HingeEndpoint in ("START", "END") else None
    return {
        "index": int(door.FA_SourceGeometryIndex),
        "jambs": [
            [float(door.FA_ProjectedFirst.x), float(door.FA_ProjectedFirst.y)],
            [float(door.FA_ProjectedSecond.x), float(door.FA_ProjectedSecond.y)],
        ],
        "width": float(door.Width.Value),
        "hinge": door.FA_HingeEndpoint,
        "hinge_point": [float(hinge.x), float(hinge.y)],
        "side": door.FA_OpeningSide,
        "mode": native_door_opening_mode(door),
        "leaf_vector": list(actual) if actual else None,
        "corner_status": getattr(door, "FA_CornerStatus", ""),
    }


def main():
    repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(repo_dir, ".codex_tmp")
    os.makedirs(output_dir, exist_ok=True)
    fcstd_path = os.path.join(output_dir, "fa_door_corner_snap_end_to_end.FCStd")
    active_before = getattr(FreeCAD.ActiveDocument, "Name", None)
    if DOC in FreeCAD.listDocuments():
        FreeCAD.closeDocument(DOC)
    try:
        doc = FreeCAD.newDocument(DOC)
        level = ensure_bim_structure(doc)["level"]

        # One multisegment Arch Wall reproduces the topology of the 1416 model.
        wall_segments = []
        for y in (0, 4000, 8000, 12000, 16000, 20000, 24000, 28000, 32000):
            wall_segments.append(((-1000, y, 0), (3000, y, 0)))
        wall_segments.extend(
            [
                ((0, 0, 0), (0, 2000, 0)),
                ((0, 4000, 0), (0, 6000, 0)),
                ((1000, 8000, 0), (1000, 10000, 0)),
                ((1000, 12000, 0), (1000, 14000, 0)),
                ((0, 16000, 0), (0, 18000, 0)),
                ((930, 16000, 0), (930, 18000, 0)),
                ((0, 19000, 0), (0, 21000, 0)),
                ((0, 28000, 0), (0, 30000, 0)),
                ((1000, 28000, 0), (1000, 30000, 0)),
                ((0, 32000, 0), (0, 34000, 0)),
                ((930, 32000, 0), (930, 34000, 0)),
            ]
        )
        host_sketch = _line_sketch(doc, "Sketch_Host", wall_segments)
        host = Arch.makeWall(host_sketch, width=100.0, height=3000.0)
        host.Label = "Muro anfitrion multisegmento"
        add_to_level(level, host, source_sketch=host_sketch)

        doors_sketch = _line_sketch(
            doc,
            "Sketch_Centros_Puertas",
            [
                ((80, 0, 0), (980, 0, 0)),
                ((980, 4000, 0), (80, 4000, 0)),
                ((20, 8000, 0), (920, 8000, 0)),
                ((920, 12000, 0), (20, 12000, 0)),
                ((51.499, 16000, 0), (954.535, 16000, 0)),
                ((80, 20000, 0), (980, 20000, 0)),
                ((300, 24000, 0), (1200, 24000, 0)),
                ((80, 28000, 0), (920, 28000, 0)),
                ((80, 32000, 0), (743.850602, 32000, 0)),
            ],
        )
        add_to_level(level, doors_sketch, source_sketch=doors_sketch)
        doc.recompute()

        before_volume = float(host.Shape.Volume)
        doc.openTransaction("FA E2E door corner phase 2")
        created, summary = create_openings_from_centerlines(
            doc, level, [doors_sketch], [host], "door", height_mm=2100.0,
            host_tolerance_mm=250.0, replace_existing=True,
            door_corner_snap_tolerance_mm=180.0,
        )
        doc.recompute()
        doc.commitTransaction()

        assert len(created) == 9, summary
        by_index = {int(obj.FA_SourceGeometryIndex): obj for obj in created}
        a, b, c, d = (by_index[index] for index in range(4))
        assert (a.FA_HingeEndpoint, a.FA_OpeningSide, native_door_opening_mode(a)) == ("START", "LEFT", "Mode1")
        assert (b.FA_HingeEndpoint, b.FA_OpeningSide, native_door_opening_mode(b)) == ("END", "RIGHT", "Mode1")
        assert (c.FA_HingeEndpoint, c.FA_OpeningSide, native_door_opening_mode(c)) == ("END", "LEFT", "Mode2")
        assert (d.FA_HingeEndpoint, d.FA_OpeningSide, native_door_opening_mode(d)) == ("START", "RIGHT", "Mode2")
        for door in (a, b, c, d):
            _assert_vector(_actual_leaf_vector(door), (0.0, 1.0))
            assert abs(float(door.Width.Value) - 900.0) <= 0.01
            assert list(door.Hosts or []) == [host]
        assert abs(float(a.FA_HingePoint.x) - 50.0) <= 0.5
        assert abs(float(b.FA_HingePoint.x) - 50.0) <= 0.5
        assert abs(float(c.FA_HingePoint.x) - 950.0) <= 0.5
        assert abs(float(d.FA_HingePoint.x) - 950.0) <= 0.5

        no_fit = by_index[4]
        assert no_fit.FA_CornerStatus == "NO_FIT"
        assert bool(no_fit.FA_CornerNoFit) is True
        assert bool(no_fit.FA_CornerSnapped) is False
        assert abs(float(no_fit.Width.Value) - 903.036) <= 0.01
        assert abs(float(no_fit.FA_AvailableWidth_mm.Value) - 830.0) <= 0.01
        assert abs(float(no_fit.FA_CornerPenetration_mm.Value) - 73.036) <= 0.01

        crossing = by_index[5]
        assert crossing.FA_CornerStatus == "JAMB_ONLY"
        assert bool(crossing.FA_CornerSnapped) is True
        assert bool(crossing.FA_CornerSwingResolved) is False
        assert crossing.FA_JambEndpoint == "START"
        assert crossing.FA_HingeEndpoint == "AUTO"
        assert crossing.FA_OpeningSide == "AUTO"
        assert abs(float(crossing.FA_ProjectedFirst.x) - 50.0) <= 0.5

        no_side = by_index[6]
        assert bool(no_side.FA_CornerSnapped) is False
        assert no_side.FA_CornerStatus == "NO_CANDIDATE"
        ambiguous = by_index[7]
        assert bool(ambiguous.FA_CornerSnapped) is False
        assert ambiguous.FA_CornerStatus == "AMBIGUOUS"
        bounded = by_index[8]
        assert bool(bounded.FA_CornerSnapped) is False
        assert bounded.FA_CornerStatus == "BOUNDED"
        assert bounded.FA_BaseAlignmentMode == "bounded_leaf_authoritative"
        assert abs(float(bounded.Width.Value) - 663.850602) <= 0.01
        assert abs(float(bounded.FA_BaseOuterWidth_mm.Value) - 763.850602) <= 0.01
        inner_first = bounded.Base.Placement.multVec(bounded.Base.Geometry[4].StartPoint)
        inner_second = bounded.Base.Placement.multVec(bounded.Base.Geometry[4].EndPoint)
        axis = bounded.FA_ProjectedSecond.sub(bounded.FA_ProjectedFirst)
        axis.normalize()
        inner_t = sorted(
            point.sub(bounded.FA_ProjectedFirst).dot(axis)
            for point in (inner_first, inner_second)
        )
        assert abs(inner_t[0]) <= 0.01
        assert abs(inner_t[1] - float(bounded.Width.Value)) <= 0.01
        assert summary["corner_snapped_count"] == 5, summary
        assert summary["corner_no_fit_count"] == 1, summary
        assert summary["corner_jamb_only_count"] == 1, summary
        assert summary["corner_ambiguous_count"] == 1, summary
        assert float(host.Shape.Volume) < before_volume - 1.0

        for door in created:
            subvolume = door.Proxy.getSubVolume(door, host=host)
            assert subvolume is not None and float(subvolume.Volume) > 1.0

        doc.undo()
        doc.recompute()
        assert len(_native_doors(doc)) == 0
        doc.redo()
        doc.recompute()
        assert len(_native_doors(doc)) == 9

        doc.openTransaction("FA E2E door corner rerun")
        rerun, summary2 = create_openings_from_centerlines(
            doc, level, [doors_sketch], [host], "door", height_mm=2100.0,
            host_tolerance_mm=250.0, replace_existing=True,
            door_corner_snap_tolerance_mm=180.0,
        )
        doc.recompute()
        doc.commitTransaction()
        assert len(rerun) == 9
        assert summary2["removed_count"] == 9, summary2
        assert len(_native_doors(doc)) == 9

        doc.saveAs(fcstd_path)
        FreeCAD.closeDocument(doc.Name)
        reopened = FreeCAD.openDocument(fcstd_path)
        reopened.recompute()
        restored = _native_doors(reopened)
        assert len(restored) == 9
        restored_by_index = {int(obj.FA_SourceGeometryIndex): obj for obj in restored}
        assert native_door_opening_mode(restored_by_index[0]) == "Mode1"
        assert native_door_opening_mode(restored_by_index[2]) == "Mode2"
        assert restored_by_index[4].FA_CornerStatus == "NO_FIT"
        assert restored_by_index[8].FA_CornerStatus == "BOUNDED"
        assert restored_by_index[8].FA_BaseAlignmentMode == "bounded_leaf_authoritative"
        result = {
            "created": len(created),
            "summary": summary,
            "rerun_removed": summary2["removed_count"],
            "cases": [_door_report(restored_by_index[index]) for index in range(9)],
            "saved": fcstd_path,
        }
        FreeCAD.closeDocument(reopened.Name)
        print("FA_DOOR_CORNER_E2E_OK", json.dumps(result, sort_keys=True))
    finally:
        if DOC in FreeCAD.listDocuments():
            FreeCAD.closeDocument(DOC)
        if active_before and active_before in FreeCAD.listDocuments():
            FreeCAD.setActiveDocument(active_before)


if __name__ == "__main__":
    main()
