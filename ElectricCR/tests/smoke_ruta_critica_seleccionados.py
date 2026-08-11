"""FreeCAD 1.1.3 smoke tests for RutaCritica_Seleccionados.

Run with:
    freecadcmd.exe -c "import runpy; runpy.run_path(<this file>, run_name='__main__')"
"""

import importlib.machinery
import importlib.util
import math
import os
import sys
import tempfile

import FreeCAD as App
import Part


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONNECT_DIR = os.path.join(ROOT, "Conectar")
if CONNECT_DIR not in sys.path:
    sys.path.insert(0, CONNECT_DIR)

import selection_geometry as selection


def _load_macro(filename, module_name):
    path = os.path.join(CONNECT_DIR, filename)
    loader = importlib.machinery.SourceFileLoader(module_name, path)
    spec = importlib.util.spec_from_loader(module_name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


base = _load_macro("medir_distancia_y_dibujar_ruta.FCMacro", "ruta_base_smoke")
route_macro = _load_macro("RutaCritica_Seleccionados.FCMacro", "ruta_selected_smoke")
adjust_macro = _load_macro("Ajustar_Alimentador_o_Ramal_Manual.FCMacro", "ruta_adjust_smoke")


class SelectionExFake:
    def __init__(self, obj, subobjects=None, names=None, picked=None):
        self.Object = obj
        self.SubObjects = tuple(subobjects or [])
        self.SubElementNames = tuple(names or [])
        self.PickedPoints = tuple(picked or [])
        self.HasSubObjects = bool(self.SubObjects)


def _close(name):
    try:
        App.closeDocument(name)
    except Exception:
        pass


def _assert_close(actual, expected, tolerance=1e-6, message=""):
    if abs(float(actual) - float(expected)) > float(tolerance):
        raise AssertionError(message or "{} != {}".format(actual, expected))


def _assert_vector(actual, expected, tolerance=1e-6):
    if actual is None or actual.distanceToPoint(expected) > tolerance:
        raise AssertionError("vector {} != {}".format(actual, expected))


def _has_curve(wire):
    return route_macro._wire_has_curved_edge(wire)


def test_selection_semantics():
    doc = App.newDocument("RutaSelectionSemantics")
    try:
        box_a = doc.addObject("Part::Box", "BoxA")
        box_a.Length = 1000
        box_a.Width = 800
        box_a.Height = 600
        box_b = doc.addObject("Part::Box", "BoxB")
        box_b.Length = 500
        box_b.Width = 400
        box_b.Height = 300
        box_b.Placement.Base = App.Vector(2000, 1000, 200)
        doc.recompute()

        # Whole object fallback preserves existing get_connection_point behavior.
        box_a.addProperty("App::PropertyLength", "AlturaRel")
        box_a.AlturaRel = 250
        records = selection.resolve_selection_ex_list(
            [SelectionExFake(box_a), SelectionExFake(box_b)],
            fallback_resolver=base.get_connection_point,
        )
        assert [item["selection_type"] for item in records] == ["OBJECT", "OBJECT"]
        _assert_vector(records[0]["point"], App.Vector(0, 0, 250))
        _assert_vector(records[1]["point"], App.Vector(2000, 1000, 200))

        # Face -> face and two different faces of the same object remain distinct.
        same_object = SelectionExFake(
            box_a,
            [box_a.Shape.Faces[0], box_a.Shape.Faces[1]],
            ["Face1", "Face2"],
            [App.Vector(0, 0, 0), App.Vector(0, 0, 0)],
        )
        face_records = selection.resolve_selection_ex_list(
            [same_object],
            fallback_resolver=base.get_connection_point,
        )
        assert len(face_records) == 2
        assert [item["subelement"] for item in face_records] == ["Face1", "Face2"]
        assert all(item["selection_type"] == "FACE" for item in face_records)
        _assert_vector(face_records[0]["point"], box_a.Shape.Faces[0].CenterOfMass)
        _assert_vector(face_records[1]["point"], box_a.Shape.Faces[1].CenterOfMass)

        # Vertex -> face keeps exact vertex and face center.
        mixed = selection.resolve_selection_ex_list(
            [
                SelectionExFake(box_a, [box_a.Shape.Vertexes[0]], ["Vertex1"]),
                SelectionExFake(box_b, [box_b.Shape.Faces[2]], ["Face3"]),
            ],
            fallback_resolver=base.get_connection_point,
        )
        assert [item["selection_type"] for item in mixed] == ["VERTEX", "FACE"]
        _assert_vector(mixed[0]["point"], box_a.Shape.Vertexes[0].Point)
        _assert_vector(mixed[1]["point"], box_b.Shape.Faces[2].CenterOfMass)

        # A reliable picked point on an edge wins; an unrelated hit does not.
        edge = Part.makeLine(App.Vector(0, 0, 0), App.Vector(1000, 0, 0))
        edge_obj = doc.addObject("Part::Feature", "EdgeObject")
        edge_obj.Shape = edge
        reliable = selection.resolve_selection_ex_list(
            [SelectionExFake(edge_obj, [edge], ["Edge1"], [App.Vector(125, 0, 0)])],
            fallback_resolver=base.get_connection_point,
        )[0]
        assert reliable["selection_type"] == "PICKEDPOINT"
        _assert_vector(reliable["point"], App.Vector(125, 0, 0))

        fallback = selection.resolve_selection_ex_list(
            [SelectionExFake(edge_obj, [edge], ["Edge1"], [App.Vector(125, 25, 0)])],
            fallback_resolver=base.get_connection_point,
        )[0]
        assert fallback["selection_type"] == "EDGE"
        _assert_vector(fallback["point"], App.Vector(500, 0, 0))

        # A real GUI selection includes a picked point on the circumference;
        # the endpoint must still be the geometric center of the circle.
        circle = Part.makeCircle(200, App.Vector(50, 60, 70))
        circle_point, circle_kind = selection.point_from_edge(
            circle,
            picked_point=App.Vector(250, 60, 70),
        )
        assert circle_kind == "CIRCLE_CENTER"
        _assert_vector(circle_point, App.Vector(50, 60, 70))

        circle_obj = doc.addObject("Part::Feature", "CircleEndpoint")
        circle_obj.Shape = circle
        doc.recompute()
        circle_record = selection.resolve_selection_ex_list(
            [
                SelectionExFake(
                    circle_obj,
                    [circle],
                    ["Edge1"],
                    [App.Vector(250, 60, 70)],
                )
            ],
            fallback_resolver=base.get_connection_point,
        )[0]
        assert circle_record["selection_type"] == "CIRCLE_CENTER"
        assert circle_record["subelement"] == "Edge1"
        _assert_vector(circle_record["point"], App.Vector(50, 60, 70))

        # Order is the SelectionEx order, then subelement order within an entry.
        ordered = selection.resolve_selection_ex_list(
            [
                SelectionExFake(box_a, [box_a.Shape.Faces[0], box_a.Shape.Faces[1]], ["Face1", "Face2"]),
                SelectionExFake(box_b),
            ],
            fallback_resolver=base.get_connection_point,
        )
        assert [item["subelement"] for item in ordered] == ["Face1", "Face2", ""]
    finally:
        _close(doc.Name)


def test_route_height_and_radius_math():
    low = base.ortho_points_path(App.Vector(0, 0, 2500), App.Vector(1000, 1000, 5000), 3000)
    assert all(point.z >= 2500 for point in low)
    _assert_close(max(point.z for point in low), 5000)

    high = base.ortho_points_path(App.Vector(0, 0, 2500), App.Vector(1000, 1000, 2000), 6000)
    _assert_close(max(point.z for point in high), 6000)

    roomy = [App.Vector(0, 0, 0), App.Vector(1000, 0, 0), App.Vector(1000, 1000, 0)]
    effective, capacity = selection.effective_fillet_radius(roomy, 235)
    _assert_close(effective, 235)
    _assert_close(capacity, 1000)

    effective_other, _capacity = selection.effective_fillet_radius(roomy, 175)
    _assert_close(effective_other, 175)

    effective_zero, _capacity = selection.effective_fillet_radius(roomy, 0)
    _assert_close(effective_zero, 0)

    short = [App.Vector(0, 0, 0), App.Vector(100, 0, 0), App.Vector(100, 100, 0)]
    effective_short, capacity_short = selection.effective_fillet_radius(short, 235)
    _assert_close(capacity_short, 100)
    assert 0 < effective_short < 100

    double_corner = [
        App.Vector(0, 0, 0),
        App.Vector(1000, 0, 0),
        App.Vector(1000, 200, 0),
        App.Vector(2000, 200, 0),
    ]
    _assert_close(selection.max_uniform_fillet_radius(double_corner), 100)


def test_adjust_manual_shared_helper():
    doc = App.newDocument("RutaAdjustSharedHelper")
    try:
        edge = Part.makeLine(App.Vector(0, 0, 0), App.Vector(1000, 0, 0))
        obj = doc.addObject("Part::Feature", "EdgeTarget")
        obj.Shape = edge
        doc.recompute()
        info = adjust_macro._target_info_from_selection_ex(
            SelectionExFake(obj, [edge], ["Edge1"], [App.Vector(275, 0, 0)])
        )
        _assert_vector(info["point"], App.Vector(275, 0, 0))
        assert info["selection_type"] == "PICKEDPOINT"
        assert info["subelement"] == "Edge1"

        points = [App.Vector(0, 0, 0), App.Vector(1000, 0, 0), App.Vector(1000, 200, 0), App.Vector(2000, 200, 0)]
        _assert_close(adjust_macro._max_fillet_radius(points), 100)
    finally:
        _close(doc.Name)


def test_draft_geometry():
    doc = App.newDocument("RutaDraftGeometry")
    try:
        points = base.ortho_points_path(
            App.Vector(0, 0, 0),
            App.Vector(2000, 1800, 0),
            3000,
        )
        effective, capacity = selection.effective_fillet_radius(points, 235)
        assert capacity >= effective > 0
        wire = base.create_draft_wire(points)
        wire.FilletRadius = effective
        doc.recompute()
        _assert_close(wire.FilletRadius.Value, effective)
        assert len(wire.Shape.Edges) >= 4
        assert _has_curve(wire)

        no_curve = base.create_draft_wire(points)
        no_curve.FilletRadius = 0
        doc.recompute()
        assert not _has_curve(no_curve)

        short_points = [
            App.Vector(0, 0, 0),
            App.Vector(100, 0, 0),
            App.Vector(100, 100, 0),
        ]
        short_effective, _short_capacity = selection.effective_fillet_radius(short_points, 235)
        short_wire = base.create_draft_wire(short_points)
        short_wire.FilletRadius = short_effective
        doc.recompute()
        assert _has_curve(short_wire)
    finally:
        _close(doc.Name)


def test_circle_center_route_endpoint():
    doc = App.newDocument("RutaCircleCenterEndpoint")
    try:
        origin_obj = doc.addObject("Part::Feature", "CircleRouteOrigin")
        origin_obj.Shape = Part.Vertex(App.Vector(0, 0, 0))
        circle_obj = doc.addObject("Part::Feature", "CircleRouteDestination")
        circle = Part.makeCircle(250, App.Vector(4000, 1800, 600))
        circle_obj.Shape = circle
        doc.recompute()

        origin = selection.resolve_selection_ex_list(
            [SelectionExFake(origin_obj, [origin_obj.Shape.Vertexes[0]], ["Vertex1"])],
            fallback_resolver=base.get_connection_point,
        )[0]
        destination = selection.resolve_selection_ex_list(
            [
                SelectionExFake(
                    circle_obj,
                    [circle_obj.Shape.Edges[0]],
                    ["Edge1"],
                    [App.Vector(4250, 1800, 600)],
                )
            ],
            fallback_resolver=base.get_connection_point,
        )[0]

        assert destination["selection_type"] == "CIRCLE_CENTER"
        _assert_vector(destination["point"], App.Vector(4000, 1800, 600))
        route_macro._selected_endpoints = lambda _base: [origin, destination]
        route_macro._route_settings_dialog = lambda: (3000.0, 0.0)
        route_macro.ruta_critica_solo_seleccionados()

        routes = _route_objects(doc)
        assert len(routes) == 1
        assert routes[0].ECR_TipoSeleccionDestino == "CIRCLE_CENTER"
        assert routes[0].ECR_SubElementoDestino == "Edge1"
        _assert_vector(routes[0].ECR_PuntoDestino, App.Vector(4000, 1800, 600))
        assert min(
            vertex.Point.distanceToPoint(App.Vector(4000, 1800, 600))
            for vertex in routes[0].Shape.Vertexes
        ) <= 1e-6
    finally:
        _close(doc.Name)


def _route_objects(doc):
    return [
        obj for obj in doc.Objects
        if str(getattr(obj, "Label", "") or "").startswith("Ruta Critica hacia")
    ]


def test_macro_end_to_end_save_reopen_undo_redo():
    doc = App.newDocument("RutaMacroEndToEnd")
    path = os.path.join(tempfile.gettempdir(), "ElectricCR_RutaCritica_Seleccionados_smoke.FCStd")
    try:
        doc.UndoMode = 1

        box = doc.addObject("Part::Box", "SharedBox")
        box.Length = 3000
        box.Width = 2000
        box.Height = 1000
        other = doc.addObject("Part::Box", "OtherBox")
        other.Length = 500
        other.Width = 500
        other.Height = 500
        other.Placement.Base = App.Vector(6000, 2500, 0)
        doc.recompute()

        origin = {
            "object": box,
            "subobject": box.Shape.Faces[0],
            "subelement": "Face1",
            "point": App.Vector(box.Shape.Faces[0].CenterOfMass),
            "selection_type": "FACE",
            "source": "subobject",
            "ordinal": 0,
        }
        same_object_destination = {
            "object": box,
            "subobject": box.Shape.Faces[1],
            "subelement": "Face2",
            "point": App.Vector(box.Shape.Faces[1].CenterOfMass),
            "selection_type": "FACE",
            "source": "subobject",
            "ordinal": 1,
        }
        object_destination = {
            "object": other,
            "subobject": None,
            "subelement": "",
            "point": base.get_connection_point(other),
            "selection_type": "OBJECT",
            "source": "object",
            "ordinal": 2,
        }

        route_macro._selected_endpoints = lambda _base: [origin, same_object_destination, object_destination]
        route_macro._route_settings_dialog = lambda: (3500.0, 235.0)
        route_macro.ruta_critica_solo_seleccionados()

        routes = _route_objects(doc)
        assert len(routes) == 2
        same_route = [obj for obj in routes if obj.ECR_ObjetoDestino == box.Name][0]
        assert same_route.ECR_SubElementoOrigen == "Face1"
        assert same_route.ECR_SubElementoDestino == "Face2"
        assert same_route.ECR_TipoSeleccionOrigen == "FACE"
        assert same_route.ECR_TipoSeleccionDestino == "FACE"
        _assert_vector(same_route.ECR_PuntoOrigen, origin["point"])
        _assert_vector(same_route.ECR_PuntoDestino, same_object_destination["point"])
        _assert_close(same_route.ECR_AlturaRuta.Value, 3500)
        _assert_close(same_route.ECR_RadioSolicitado.Value, 235)

        # Repeated execution remains valid and creates another independent pair.
        route_macro._route_settings_dialog = lambda: (3500.0, 0.0)
        route_macro.ruta_critica_solo_seleccionados()
        assert len(_route_objects(doc)) == 4
        assert any(math.isclose(obj.ECR_RadioEfectivo.Value, 0.0) for obj in _route_objects(doc))

        try:
            doc.undo()
            doc.recompute()
            assert len(_route_objects(doc)) == 2
            doc.redo()
            doc.recompute()
            assert len(_route_objects(doc)) == 4
        except Exception as exc:
            raise AssertionError("Undo/Redo failed: {}".format(exc))

        doc.recompute()
        doc.saveAs(path)
        name = doc.Name
        App.closeDocument(name)
        reopened = App.openDocument(path)
        reopened.recompute()
        routes_reopened = _route_objects(reopened)
        assert len(routes_reopened) == 4
        assert all("ECR_PuntoOrigen" in obj.PropertiesList for obj in routes_reopened)
        assert all("ECR_RadioSolicitado" in obj.PropertiesList for obj in routes_reopened)
        App.closeDocument(reopened.Name)
    finally:
        if App.ActiveDocument is not None and App.ActiveDocument.Name == doc.Name:
            _close(doc.Name)
        if os.path.isfile(path):
            os.remove(path)


def main():
    version = ".".join(App.Version()[:3])
    print("[RUTA-SEL-TEST] FreeCAD {}".format(version))
    test_selection_semantics()
    print("[RUTA-SEL-TEST] selection semantics OK")
    test_route_height_and_radius_math()
    print("[RUTA-SEL-TEST] route height and radius math OK")
    test_adjust_manual_shared_helper()
    print("[RUTA-SEL-TEST] shared manual-adjust helper OK")
    test_draft_geometry()
    print("[RUTA-SEL-TEST] Draft geometry OK")
    test_circle_center_route_endpoint()
    print("[RUTA-SEL-TEST] circle center route endpoint OK")
    test_macro_end_to_end_save_reopen_undo_redo()
    print("[RUTA-SEL-TEST] macro/save/reopen/undo/redo OK")
    print("[RUTA-SEL-TEST] ALL_OK")


if __name__ == "__main__":
    main()
