"""FreeCAD GUI regression test for line/edge evaporator insertion.

Run from FreeCAD's Python console or MCP with::

    from MEPWorkbenchCR.tests.test_hvac_evaporator_edge_midpoint import run
    run()
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
import Part

from MEPWorkbenchCR.MEP.hvac import hvac_equipment
from MEPWorkbenchCR.MEP.hvac import hvac_space
from MEPWorkbenchCR.MEP.utils import selection


DOC_NAME = "Test_HVACEvaporator_EdgeMidpoint"


def _edge_midpoint(edge):
    parameter = edge.getParameterByLength(float(edge.Length) * 0.5)
    return App.Vector(edge.valueAt(parameter))


def _assert_same_xy(first, second, tol=0.01):
    assert abs(float(first.x) - float(second.x)) <= tol
    assert abs(float(first.y) - float(second.y)) <= tol


def _assert_x_axis_parallel(equipment_obj, tangent, tol=1e-6):
    local_x = equipment_obj.Placement.Rotation.multVec(App.Vector(1.0, 0.0, 0.0))
    first = App.Vector(float(local_x.x), float(local_x.y), 0.0)
    second = App.Vector(float(tangent.x), float(tangent.y), 0.0)
    first.normalize()
    second.normalize()
    cross_z = float(first.x) * float(second.y) - float(first.y) * float(second.x)
    assert abs(cross_z) <= tol


def run():
    previous_doc_name = App.ActiveDocument.Name if App.ActiveDocument is not None else ""
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)

    temp_path = os.path.join(tempfile.gettempdir(), DOC_NAME + ".FCStd")
    if os.path.exists(temp_path):
        os.remove(temp_path)

    doc = App.newDocument(DOC_NAME)
    try:
        area = doc.addObject("Part::Part2DObject", "AreaServidor")
        area.Label = "Servidor"
        area.Shape = Part.makePlane(4000.0, 3000.0, App.Vector(0.0, 0.0, 0.0))
        spaces = hvac_space.create_spaces_from_objects(
            [area],
            doc=doc,
            source_mode=hvac_space.SOURCE_MODE_COPY,
        )
        assert len(spaces) == 1
        space_obj = spaces[0]
        doc.recompute()

        # Explicit subedge of the source geometry is recognized directly.
        edge = area.Shape.Edges[0]
        expected_edge_point = _edge_midpoint(edge)
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, area.Name, "Edge1")
        edge_reference = selection.get_selected_linear_reference()
        assert edge_reference is not None
        assert edge_reference["source"] == "subedge"
        _assert_same_xy(edge_reference["point"], expected_edge_point)

        # In common display modes a click at the visual border is delivered as
        # Face1 plus PickedPoints.  It must resolve to the nearest real edge.
        expected_wall_point = App.Vector(4000.0, 1500.0, 0.0)
        expected_wall_tangent = App.Vector(0.0, 1.0, 0.0)
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, area.Name, "Face1", 3995.0, 1400.0, 0.0)
        face_reference = selection.get_selected_linear_reference()
        assert face_reference is not None
        assert face_reference["source"] == "picked-boundary-edge"
        _assert_same_xy(face_reference["point"], expected_wall_point)

        wall_unit = hvac_equipment.insert_evaporator_from_selection(
            doc=doc,
            model_name="Pared_12000",
        )
        assert wall_unit is not None
        assert str(wall_unit.Type) == "Wall"
        _assert_same_xy(wall_unit.Placement.Base, expected_wall_point)
        _assert_x_axis_parallel(wall_unit, expected_wall_tangent)
        assert wall_unit.Space == space_obj

        # A complete Part/Draft-like single-edge object must work without Edge1.
        line = doc.addObject("Part::Feature", "LineaPisoCielo")
        line.Label = "Linea piso-cielo"
        line.Shape = Part.makeLine(
            App.Vector(1000.0, 1000.0, 0.0),
            App.Vector(3000.0, 2000.0, 0.0),
        )
        doc.recompute()
        expected_floor_point = _edge_midpoint(line.Shape.Edges[0])
        expected_floor_tangent = line.Shape.Edges[0].tangentAt(
            line.Shape.Edges[0].getParameterByLength(float(line.Shape.Edges[0].Length) * 0.5)
        )
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, line.Name)
        line_reference = selection.get_selected_linear_reference()
        assert line_reference is not None
        assert line_reference["source"] == "single-edge-object"
        _assert_same_xy(line_reference["point"], expected_floor_point)

        floor_unit = hvac_equipment.insert_evaporator_from_selection(
            doc=doc,
            model_name="PisoCielo_60000",
        )
        assert floor_unit is not None
        assert str(floor_unit.Type) == "FloorCeiling"
        _assert_same_xy(floor_unit.Placement.Base, expected_floor_point)
        _assert_x_axis_parallel(floor_unit, expected_floor_tangent)
        assert floor_unit.Space == space_obj

        wall_name = wall_unit.Name
        floor_name = floor_unit.Name
        space_name = space_obj.Name
        doc.recompute()
        Gui.Selection.clearSelection()
        doc.saveAs(temp_path)
        App.closeDocument(DOC_NAME)

        reopened = App.openDocument(temp_path)
        reopened.recompute()
        persisted_wall = reopened.getObject(wall_name)
        persisted_floor = reopened.getObject(floor_name)
        persisted_space = reopened.getObject(space_name)
        assert persisted_wall is not None
        assert persisted_floor is not None
        assert persisted_space is not None
        _assert_same_xy(persisted_wall.Placement.Base, expected_wall_point)
        _assert_same_xy(persisted_floor.Placement.Base, expected_floor_point)
        assert persisted_wall.Space == persisted_space
        assert persisted_floor.Space == persisted_space
        App.closeDocument(reopened.Name)
    finally:
        Gui.Selection.clearSelection()
        if DOC_NAME in App.listDocuments():
            App.closeDocument(DOC_NAME)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if previous_doc_name and previous_doc_name in App.listDocuments():
            App.setActiveDocument(previous_doc_name)

    return {
        "selected_subedge": True,
        "selected_face_border": True,
        "selected_whole_line": True,
        "wall_midpoint": True,
        "floor_ceiling_midpoint": True,
        "space_link": True,
        "orientation": True,
        "persisted": True,
    }


if __name__ == "__main__":
    print(run())
