# -*- coding: utf-8 -*-
"""FreeCAD 1.1.3 smoke test for editable BIM-derived polygonal rooms."""

import importlib.machinery
import os
import runpy
import sys
import tempfile

import FreeCAD as App
import Part


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MACRO_PATH = os.path.join(ROOT, "Areas", "PoligonosRecintosDesdeArchWalls.FCMacro")
TOMAS_PATH = os.path.join(
    ROOT,
    "Tomacorrientes",
    "CrearCircuitosGeneralesPorParedYRecinto.FCMacro",
)
TOLERANCE = 0.05


def assert_close(actual, expected, tolerance=TOLERANCE, message=""):
    if abs(float(actual) - float(expected)) > float(tolerance):
        raise AssertionError("{}: {} != {}".format(message, actual, expected))


def polygon_wire(points, z=0.0):
    vectors = [App.Vector(float(x), float(y), float(z)) for x, y in points]
    return Part.makePolygon(vectors + [vectors[0]])


def make_frame_wall(doc, name, outer_points, inner_points, height=3000.0):
    outer_face = Part.Face(polygon_wire(outer_points))
    inner_face = Part.Face(polygon_wire(inner_points, z=-1.0))
    outer_solid = outer_face.extrude(App.Vector(0.0, 0.0, float(height)))
    inner_solid = inner_face.extrude(App.Vector(0.0, 0.0, float(height) + 2.0))
    wall = doc.addObject("Part::Feature", name)
    wall.Label = name
    wall.Shape = outer_solid.cut(inner_solid)
    wall.addProperty("App::PropertyString", "FA_Role", "FacilArquitectura")
    wall.FA_Role = "wall"
    return wall


def room_objects(doc):
    return [
        obj
        for obj in list(doc.Objects)
        if str(getattr(obj, "FA_Role", "") or "") == "room_polygon"
    ]


def proxy_type(obj):
    return str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")


def verify_room(room, expected_walls):
    if room.TypeId == "Part::Feature":
        raise AssertionError("Room is still a static Part::Feature")
    if proxy_type(room) != "Wire":
        raise AssertionError("Unexpected Draft proxy: {!r}".format(room.Proxy))
    if not bool(room.Closed):
        raise AssertionError("Draft room is not closed")
    if not bool(room.MakeFace):
        raise AssertionError("Draft room does not create a face")
    if len(room.Shape.Faces) < 1:
        raise AssertionError("Draft room has no valid face")
    if len(room.Points) < 3:
        raise AssertionError("Draft room has fewer than three editable points")
    if room.Points[0].isEqual(room.Points[-1], 1e-7):
        raise AssertionError("Closed Draft room duplicates the first point at the end")
    for point in room.Points:
        assert_close(point.z, 0.0, 0.001, "Local point elevation")
    assert_close(room.Placement.Base.z, 20.0, 0.001, "Display placement elevation")
    assert_close(room.Shape.BoundBox.ZMin, 20.0, 0.001, "Shape ZMin")
    assert_close(room.Shape.BoundBox.ZMax, 20.0, 0.001, "Shape ZMax")
    shape_area = float(room.Shape.Faces[0].Area)
    assert_close(float(room.AreaM2), shape_area / 1000000.0, 0.001, "AreaM2")
    assert_close(float(room.FA_Area.Value), shape_area, 1.0, "FA_Area")
    assert_close(
        float(room.FA_Perimeter.Value),
        float(room.Shape.Faces[0].OuterWire.Length),
        1.0,
        "FA_Perimeter",
    )
    if int(room.FA_VertexCount) != len(room.Points):
        raise AssertionError("FA_VertexCount does not match editable Points")
    if len(room.FA_SourceWalls) != expected_walls:
        raise AssertionError("FA_SourceWalls was not preserved")
    if room.FA_GeometrySource != "AUTO_BIM":
        raise AssertionError("Missing FA_GeometrySource")
    if room.FA_GeometryType != "DraftWire":
        raise AssertionError("Missing FA_GeometryType")


def load_tomas_consumer():
    loader = importlib.machinery.SourceFileLoader("tomas_room_consumer_smoke", TOMAS_PATH)
    return loader.load_module()


def main():
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

    doc = App.newDocument("PolygonalRoomsDraftWireSmoke")
    doc.UndoMode = 1
    areas = doc.addObject("App::DocumentObjectGroup", "Areas")
    areas.Label = "Areas"

    walls = [
        make_frame_wall(
            doc,
            "WallRectangular",
            [(-200, -200), (5200, -200), (5200, 4200), (-200, 4200)],
            [(200, 200), (4800, 200), (4800, 3800), (200, 3800)],
        ),
        make_frame_wall(
            doc,
            "WallConcave",
            [(7800, -200), (13200, -200), (13200, 4600), (7800, 4600)],
            [(8200, 200), (12800, 200), (12800, 1800), (11000, 1800), (11000, 4200), (8200, 4200)],
        ),
        make_frame_wall(
            doc,
            "WallManyVertices",
            [(15800, -200), (21200, -200), (21200, 4600), (15800, 4600)],
            [
                (16200, 200),
                (20800, 200),
                (20800, 1300),
                (20700, 1300),
                (20700, 2600),
                (19500, 2600),
                (19500, 4200),
                (16200, 4200),
            ],
        ),
    ]
    doc.recompute()

    namespace = runpy.run_path(MACRO_PATH, run_name="polygonal_rooms_macro_smoke")
    result = namespace.get("FA_POLYGONAL_ROOMS_RESULT")
    if not result:
        # Re-run without main()'s error wrapper so the geometric cause is visible.
        result = namespace["generate_polygonal_rooms"](doc=doc, walls=walls)
    rooms = room_objects(doc)
    if len(rooms) != 3:
        raise AssertionError("Expected three polygonal rooms, got {}".format(len(rooms)))
    for room in rooms:
        verify_room(room, len(walls))

    point_counts = sorted(len(room.Points) for room in rooms)
    if point_counts != [4, 6, 8]:
        raise AssertionError("Unexpected preserved vertex counts: {}".format(point_counts))
    concave = [room for room in rooms if len(room.Points) == 6][0]
    bounds = concave.Shape.BoundBox
    if float(concave.Shape.Faces[0].Area) >= float(bounds.XLength * bounds.YLength) - 1.0:
        raise AssertionError("Concave room was simplified to its bounding box")

    # The macro transaction must remain undoable and redoable as one operation.
    doc.undo()
    doc.recompute()
    if room_objects(doc):
        raise AssertionError("Undo did not remove generated rooms")
    doc.redo()
    doc.recompute()
    rooms = room_objects(doc)
    if len(rooms) != 3:
        raise AssertionError("Redo did not restore generated rooms")

    rectangle = [room for room in rooms if len(room.Points) == 4][0]
    original_points = [App.Vector(point) for point in rectangle.Points]
    original_area = float(rectangle.Shape.Faces[0].Area)
    edited_points = [App.Vector(point) for point in rectangle.Points]
    edited_points[0] = edited_points[0].add(App.Vector(125.0, 0.0, 0.0))
    doc.openTransaction("Edit Draft room point")
    rectangle.Points = edited_points
    doc.recompute()
    doc.commitTransaction()
    edited_area = float(rectangle.Shape.Faces[0].Area)
    if abs(edited_area - original_area) < 1.0:
        raise AssertionError("Editing Points did not rebuild the room geometry")
    if not rectangle.Points[0].isEqual(edited_points[0], 1e-7):
        raise AssertionError("Edited point was not retained")
    doc.undo()
    doc.recompute()
    if not rectangle.Points[0].isEqual(original_points[0], 1e-7):
        raise AssertionError("Undo did not restore the room point")
    doc.redo()
    doc.recompute()
    if not rectangle.Points[0].isEqual(edited_points[0], 1e-7):
        raise AssertionError("Redo did not restore the edited room point")

    # Current regeneration policy intentionally replaces generated rooms.
    rerun = namespace["generate_polygonal_rooms"](doc=doc, walls=walls)
    rooms = list(rerun["rooms"])
    if len(rooms) != 3 or len(room_objects(doc)) != 3:
        raise AssertionError("Regeneration duplicated or lost rooms")
    rectangle = [room for room in rooms if len(room.Points) == 4][0]
    if rectangle.Points[0].isEqual(edited_points[0], 1e-7):
        raise AssertionError("Test expected regeneration to replace the manual edit")
    for room in rooms:
        verify_room(room, len(walls))

    handle, saved_path = tempfile.mkstemp(suffix=".FCStd")
    os.close(handle)
    try:
        doc.saveAs(saved_path)
        App.closeDocument(doc.Name)
        reopened = App.openDocument(saved_path)
        reopened.recompute()
        restored_rooms = room_objects(reopened)
        if len(restored_rooms) != 3:
            raise AssertionError("Saved Draft rooms were not restored")
        for room in restored_rooms:
            verify_room(room, len(walls))

        from FacilArquitecturaWB.core import ceiling_utils

        collected = ceiling_utils.collect_rooms(reopened)
        if len(collected) != 3:
            raise AssertionError("Ceiling consumer did not collect all Draft rooms")
        for room in collected:
            if ceiling_utils._room_spec(room)["geometry"] != "polygon":
                raise AssertionError("Ceiling consumer did not classify Draft room as polygon")
        bim_group = reopened.addObject("App::DocumentObjectGroup", "BIM_Test")
        ceiling_result = ceiling_utils.create_modular_ceilings(
            reopened,
            bim_group,
            collected,
            [],
            {
                "module_mm": 600.0,
                "ceiling_elevation_mm": 2700.0,
                "panel_thickness_mm": 15.0,
                "joint_gap_mm": 5.0,
                "alignment_tolerance_mm": 50.0,
                "align_to_luminaires": True,
                "replace_previous": True,
            },
        )
        if len(ceiling_result["plans"]) != 3:
            raise AssertionError("Ceiling creation did not process all Draft rooms")

        tomas = load_tomas_consumer()
        records = tomas.area_records(reopened)
        if len(records) != 3:
            raise AssertionError("Outlet consumer did not collect all Draft room faces")
        rectangular_record = [record for record in records if len(record[0].Points) == 4][0]
        probe = rectangular_record[2][0].CenterOfMass
        classified = tomas.point_rooms(probe, records)
        if not classified or rectangular_record[1] not in classified:
            raise AssertionError("Outlet point was not classified inside the Draft room")

        App.closeDocument(reopened.Name)
    finally:
        try:
            os.remove(saved_path)
        except OSError:
            pass

    print(
        "PASS: BIM room detection creates editable closed Draft Wires; "
        "persistence, ceilings, outlets, Undo/Redo and regeneration verified"
    )


if __name__ == "__main__":
    main()
