# -*- coding: utf-8 -*-
"""FreeCAD 1.1 smoke test for RectFromBoundaryLines BIM wall face support."""

import importlib.machinery
import os
import tempfile

import Arch
import Draft
import FreeCAD as App
import Part


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MACRO_PATH = os.path.join(ROOT, "Areas", "RectFromBoundaryLines.FCMacro")


class SelectionEntry(object):
    def __init__(self, obj, name, subobject, picked_point=None):
        self.Object = obj
        self.SubElementNames = [name]
        self.SubObjects = [subobject]
        self.PickedPoints = [] if picked_point is None else [picked_point]


def load_macro():
    loader = importlib.machinery.SourceFileLoader("rect_from_boundary_bim_faces", MACRO_PATH)
    return loader.load_module()


def make_wall(doc, name, p1, p2, width=200.0, height=3000.0):
    base = Draft.makeLine(App.Vector(*p1), App.Vector(*p2))
    base.Label = "Eje " + name
    wall = Arch.makeWall(base, width=width, height=height)
    wall.Label = name
    doc.recompute()
    return wall


def side_face_near(wall, axis, value):
    candidates = []
    for index, face in enumerate(wall.Shape.Faces, 1):
        normal = face.normalAt(0.0, 0.0)
        if abs(normal.z) > 0.2:
            continue
        coordinate = getattr(face.CenterOfMass, axis)
        candidates.append((abs(coordinate - value), index, face))
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1], candidates[0][2]


def top_face(wall):
    candidates = []
    for index, face in enumerate(wall.Shape.Faces, 1):
        normal = face.normalAt(0.0, 0.0)
        if normal.z > 0.8:
            candidates.append((face.CenterOfMass.z, index, face))
    candidates.sort(reverse=True)
    return candidates[0][1], candidates[0][2]


def assert_close(actual, expected, tolerance=0.05, message=""):
    if abs(float(actual) - float(expected)) > tolerance:
        raise AssertionError("{}: {} != {}".format(message, actual, expected))


def main():
    macro = load_macro()
    doc = App.newDocument("RectBoundaryBIMSmoke")
    doc.UndoMode = 1

    bottom = make_wall(doc, "Muro Sur", (0, 0, 0), (4000, 0, 0))
    top = make_wall(doc, "Muro Norte", (0, 3000, 0), (4000, 3000, 0))
    left = make_wall(doc, "Muro Oeste", (0, 0, 0), (0, 3000, 0))
    right = make_wall(doc, "Muro Este", (4000, 0, 0), (4000, 3000, 0))

    entries = []
    for wall, axis, value in (
        (bottom, "y", 100.0),
        (top, "y", 2900.0),
        (left, "x", 100.0),
        (right, "x", 3900.0),
    ):
        index, face = side_face_near(wall, axis, value)
        entries.append(SelectionEntry(wall, "Face{}".format(index), face, face.CenterOfMass))

    boundaries, source_walls, method = macro.get_selected_boundaries(entries)
    if len(boundaries) != 4 or len(source_walls) != 4:
        raise AssertionError("Expected four BIM face boundaries and four source walls")
    if "cara_vertical" not in method:
        raise AssertionError("Vertical BIM face method was not recorded")

    rectangle = macro.RectFromBoundaryLines(entries)
    if rectangle is None:
        raise AssertionError("The BIM face selection did not create a rectangle")
    name = rectangle.Name
    doc.recompute()
    assert_close(rectangle.AreaM2, 10.64, 0.001, "Room area")
    assert_close(rectangle.Shape.BoundBox.XMin, 100.0, message="XMin")
    assert_close(rectangle.Shape.BoundBox.XMax, 3900.0, message="XMax")
    assert_close(rectangle.Shape.BoundBox.YMin, 100.0, message="YMin")
    assert_close(rectangle.Shape.BoundBox.YMax, 2900.0, message="YMax")
    if len(rectangle.FA_SourceWalls) != 4:
        raise AssertionError("The rectangle did not retain its four source-wall links")

    # Horizontal face: the click near the inner edge must choose y=100, not y=-100.
    face_index, face = top_face(bottom)
    horizontal_entry = SelectionEntry(
        bottom,
        "Face{}".format(face_index),
        face,
        App.Vector(2000.0, 95.0, 3000.0),
    )
    horizontal_edges, unused_walls, horizontal_method = macro.get_selected_boundaries([horizontal_entry])
    endpoints = [vertex.Point for vertex in horizontal_edges[0].Vertexes]
    assert_close(endpoints[0].y, 100.0, message="Nearest top-face boundary Y")
    assert_close(endpoints[-1].y, 100.0, message="Nearest top-face boundary Y")
    if horizontal_method != "borde_cara_horizontal":
        raise AssertionError("Horizontal face method was not recorded")

    # Legacy explicit edges still produce the same 4 x 3 m rectangle.
    legacy_edges = [
        Part.makeLine(App.Vector(0, 0, 0), App.Vector(4000, 0, 0)),
        Part.makeLine(App.Vector(0, 3000, 0), App.Vector(4000, 3000, 0)),
        Part.makeLine(App.Vector(0, 0, 0), App.Vector(0, 3000, 0)),
        Part.makeLine(App.Vector(4000, 0, 0), App.Vector(4000, 3000, 0)),
    ]
    points = macro.rectangle_points_from_edges(legacy_edges)
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    assert_close(min(xs), 0.0, message="Legacy XMin")
    assert_close(max(xs), 4000.0, message="Legacy XMax")
    assert_close(min(ys), 0.0, message="Legacy YMin")
    assert_close(max(ys), 3000.0, message="Legacy YMax")

    doc.undo()
    doc.recompute()
    if doc.getObject(name) is not None:
        raise AssertionError("Undo did not remove the created rectangle")
    doc.redo()
    doc.recompute()
    rectangle = doc.getObject(name)
    if rectangle is None:
        raise AssertionError("Redo did not restore the created rectangle")

    handle, saved_path = tempfile.mkstemp(suffix=".FCStd")
    os.close(handle)
    try:
        doc.saveAs(saved_path)
        App.closeDocument(doc.Name)
        reopened = App.openDocument(saved_path)
        restored = reopened.getObject(name)
        if restored is None:
            raise AssertionError("Saved rectangle was not restored")
        assert_close(restored.AreaM2, 10.64, 0.001, "Restored room area")
        if len(restored.FA_SourceWalls) != 4:
            raise AssertionError("Source-wall links were not restored")
        App.closeDocument(reopened.Name)
    finally:
        try:
            os.remove(saved_path)
        except OSError:
            pass

    print("PASS: RectFromBoundaryLines supports BIM wall faces and preserves legacy edges")


if __name__ == "__main__":
    main()
