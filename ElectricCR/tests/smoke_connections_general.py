"""Prueba headless del motor general de conexiones ElectricCR.

Ejecutar con FreeCADCmd 1.1.3 y una ruta temporal de salida como ultimo
argumento. No abre ni modifica el modelo original de Puriscal.
"""

import json
import os
import runpy
import sys

import FreeCAD as App
import Part


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from ElectricCR.electriccr.connections import assignments, backbone, feeders, panels


def _string(obj, name, value):
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", name, "Test")
    setattr(obj, name, value)


def _link(obj, name, value):
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", name, "Test")
    setattr(obj, name, value)


def _panel(doc, code, x, y):
    obj = doc.addObject("Part::Feature", "Panel_" + code)
    obj.Label = "Tablero " + code
    obj.Shape = Part.makeBox(900.0, 300.0, 1200.0, App.Vector(x, y, 0.0))
    _string(obj, "ClaseEquipo", "Tablero")
    _string(obj, "Codigo", code)
    return obj


def _port_json(x, y, z=3000.0):
    return json.dumps(
        [
            {"name": "East", "position": [x + 100.0, y, z + 50.0], "direction": [1.0, 0.0, 0.0]},
            {"name": "West", "position": [x - 100.0, y, z + 50.0], "direction": [-1.0, 0.0, 0.0]},
            {"name": "North", "position": [x, y + 100.0, z + 50.0], "direction": [0.0, 1.0, 0.0]},
            {"name": "South", "position": [x, y - 100.0, z + 50.0], "direction": [0.0, -1.0, 0.0]},
            {"name": "Bottom", "position": [x, y, z], "direction": [0.0, 0.0, -1.0]},
        ]
    )


def _box(doc, name, x, y):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = "Caja EMT Octogonal " + name
    obj.Shape = Part.makeBox(200.0, 200.0, 100.0, App.Vector(x - 100.0, y - 100.0, 3000.0))
    _string(obj, "Tipo", "EMT_Octagon_Box")
    _string(obj, "PuertosJSON", _port_json(x, y))
    return obj


def _circuit(doc, cid, panel, coordinates):
    group = doc.addObject("App::DocumentObjectGroup", "Circuit_" + cid.replace("-", "_"))
    group.Label = cid + " | circuito de prueba"
    _string(group, "CircuitoID", cid)
    _link(group, "Panel", panel)
    group.addProperty("App::PropertyLinkList", "CajasOctogonalesAsignadas", "Test")
    boxes = []
    for index, (x, y) in enumerate(coordinates, start=1):
        box = _box(doc, "Box_{}_{}".format(cid.replace("-", "_"), index), x, y)
        group.addObject(box)
        boxes.append(box)
    group.CajasOctogonalesAsignadas = boxes
    return group, boxes


def _guide(doc, name, points):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = "Ruta guia " + name
    obj.addProperty("App::PropertyVectorList", "Points", "Test")
    obj.Points = points
    obj.Shape = Part.makePolygon(points)
    _string(obj, "Tipo", "RutaGuia")
    return obj


def _route_for(doc, cid, generator):
    matches = [
        obj for obj in doc.Objects
        if str(getattr(obj, "GeneradoPor", "")) == generator
        and str(getattr(obj, "CircuitoID", "")) == cid
        and not hasattr(obj, "Group")
    ]
    if len(matches) != 1:
        raise RuntimeError("Se esperaba una ruta {} para {} y hay {}".format(generator, cid, len(matches)))
    return matches[0]


def _assert_face_point(panel, point, face_index):
    face = panel.Shape.getElement("Face{}".format(int(face_index)))
    distance = float(face.distToShape(Part.Vertex(App.Vector(point)))[0])
    if distance > 0.01:
        raise RuntimeError("Punto fuera de cara real: {} mm".format(distance))


def main():
    target = os.path.abspath(sys.argv[-1])
    doc = App.newDocument("ElectricCRConnectionsGeneral")
    # FreeCAD 1.1 expone UndoMode como propiedad del documento.
    doc.UndoMode = 1

    tp = _panel(doc, "TP", 10000.0, 0.0)
    tcom = _panel(doc, "TCOM", 10000.0, 10000.0)
    ts = _panel(doc, "TS", 10000.0, 20000.0)
    taa = _panel(doc, "TAA", 10000.0, 30000.0)

    tp1, tp1_boxes = _circuit(doc, "TP-001", tp, [(1000.0, 1000.0), (3500.0, 1000.0)])
    tp2, tp2_boxes = _circuit(doc, "TP-002", tp, [(1000.0, 2500.0), (3500.0, 2500.0)])
    tp3, tp3_boxes = _circuit(doc, "TP-003", tp, [(1000.0, 4000.0), (3500.0, 4000.0)])
    tcom1, _tcom_boxes = _circuit(doc, "TCOM-01", tcom, [(1000.0, 11000.0), (3500.0, 11000.0)])
    ts1, ts1_boxes = _circuit(doc, "TS-01", ts, [(1000.0, 21000.0), (3500.0, 21000.0)])
    guide = _guide(
        doc,
        "Guide_TCOM",
        [App.Vector(1500.0, 11500.0, 3400.0), App.Vector(7000.0, 11500.0, 3400.0), App.Vector(7000.0, 10150.0, 3400.0)],
    )
    doc.recompute()

    direct_tp = feeders.connect_circuit_feeders(doc, [tp1])
    guided_tcom = feeders.connect_circuit_feeders(doc, [tcom1], guides=[guide])
    direct_ts = feeders.connect_circuit_feeders(doc, [ts1])
    if direct_tp["errors"] or guided_tcom["errors"] or direct_ts["errors"]:
        raise RuntimeError("Fallo inicial: {} {} {}".format(direct_tp, guided_tcom, direct_ts))
    if _route_for(doc, "TP-001", feeders.GENERATED_BY).ModoRuteo != "DIRECTO":
        raise RuntimeError("TP no quedo en modo DIRECTO")
    tcom_route = _route_for(doc, "TCOM-01", feeders.GENERATED_BY)
    if tcom_route.ModoRuteo != "GUIADO" or tcom_route.RutaGuia is not guide:
        raise RuntimeError("TCOM no uso la guia seleccionada")
    if _route_for(doc, "TS-01", feeders.GENERATED_BY).ModoRuteo != "DIRECTO":
        raise RuntimeError("TS requirio codigo especializado")

    # Varias llegadas en el mismo tablero y puntos pertenecientes a la cara.
    multi = feeders.connect_circuit_feeders(doc, [tp1, tp2, tp3])
    if multi["errors"] or len(multi["routes"]) != 3:
        raise RuntimeError("No se generaron las tres llegadas TP")
    destinations = set()
    names_before = set()
    for cid in ("TP-001", "TP-002", "TP-003"):
        route = _route_for(doc, cid, feeders.GENERATED_BY)
        destinations.add((round(route.PuntoDestino.x, 4), round(route.PuntoDestino.y, 4), round(route.PuntoDestino.z, 4)))
        names_before.add(route.Name)
        _assert_face_point(tp, route.PuntoDestino, route.FaceIndexTablero)
        if int(route.CantidadSlotsTablero) != 3:
            raise RuntimeError("Cantidad de slots incorrecta")
    if len(destinations) != 3:
        raise RuntimeError("Las llegadas comparten un punto: {}".format(destinations))

    # Reserva: East queda ocupado manualmente en la caja fuente de TP-002.
    blocker = doc.addObject("Part::Feature", "ManualPortReservation")
    blocker.Shape = Part.makeLine(App.Vector(0, 0, 0), App.Vector(1, 0, 0))
    tp2_source = _route_for(doc, "TP-002", feeders.GENERATED_BY).CajaOrigen
    _link(blocker, "CajaOrigen", tp2_source)
    _string(blocker, "PuertoOrigen", "East")
    rerun = feeders.connect_circuit_feeders(doc, [tp1, tp2, tp3])
    if rerun["errors"]:
        raise RuntimeError("Fallo en actualizacion: {}".format(rerun))
    if set(route.Name for route in rerun["routes"]) != names_before:
        raise RuntimeError("La segunda ejecucion duplico alimentadores")
    if _route_for(doc, "TP-002", feeders.GENERATED_BY).PuertoOrigen == "East":
        raise RuntimeError("Se reutilizo un puerto ocupado con alternativas disponibles")

    # Movimiento de caja y tablero seguido de regeneracion.
    tp1_route = _route_for(doc, "TP-001", feeders.GENERATED_BY)
    old_start = App.Vector(tp1_route.PuntoOrigen)
    moved = tp1_route.CajaOrigen
    moved.Shape = Part.makeBox(200.0, 200.0, 100.0, App.Vector(1900.0, 4900.0, 3000.0))
    moved.PuertosJSON = _port_json(2000.0, 5000.0)
    feeders.connect_circuit_feeders(doc, [tp1, tp2, tp3])
    if _route_for(doc, "TP-001", feeders.GENERATED_BY).PuntoOrigen.distanceToPoint(old_start) < 100.0:
        raise RuntimeError("Mover la caja no actualizo la ruta")
    old_ts_end = App.Vector(_route_for(doc, "TS-01", feeders.GENERATED_BY).PuntoDestino)
    ts.Shape = Part.makeBox(900.0, 300.0, 1200.0, App.Vector(12000.0, 20000.0, 0.0))
    feeders.connect_circuit_feeders(doc, [ts1])
    if _route_for(doc, "TS-01", feeders.GENERATED_BY).PuntoDestino.distanceToPoint(old_ts_end) < 100.0:
        raise RuntimeError("Mover el tablero no actualizo el destino")

    # Un solo motor de backbone para prefijos distintos e idempotencia.
    back_tp = backbone.connect_backbone(doc, [tp1, tp2])
    back_tcom = backbone.connect_backbone(doc, [tcom1])
    if back_tp["errors"] or back_tcom["errors"]:
        raise RuntimeError("Fallo de backbone")
    expected_backbone = (len(tp1_boxes) - 1) + (len(tp2_boxes) - 1) + (len(_tcom_boxes) - 1)
    backbone_routes = [obj for obj in doc.Objects if str(getattr(obj, "GeneradoPor", "")) == backbone.GENERATED_BY]
    if len(backbone_routes) != expected_backbone:
        raise RuntimeError("Conteo de backbone incorrecto: {}".format(len(backbone_routes)))
    names_backbone = {obj.Name for obj in backbone_routes}
    backbone.connect_backbone(doc, [tp1, tp2])
    if {obj.Name for obj in doc.Objects if str(getattr(obj, "GeneradoPor", "")) == backbone.GENERATED_BY} != names_backbone:
        raise RuntimeError("La segunda ejecucion duplico backbone")

    # Equipos y desconectores usan el mismo motor y distribuyen cara superior.
    equipment = []
    for index, cid in enumerate(("TAA-01", "TAA-02"), start=1):
        obj = doc.addObject("Part::Feature", "Disconnect_{}".format(index))
        obj.Label = "Desconector {}".format(index)
        obj.Shape = Part.makeBox(150.0, 150.0, 150.0, App.Vector(2000.0 * index, 33000.0, 8000.0))
        _string(obj, "ClaseEquipo", "Desconector HVAC")
        _string(obj, "CircuitoID", cid)
        _link(obj, "Panel", taa)
        equipment.append(obj)
    records = assignments.analyze_equipment(doc, equipment)
    equipment_result = feeders.connect_equipment_feeders(doc, records)
    if equipment_result["errors"] or len(equipment_result["routes"]) != 2:
        raise RuntimeError("Fallo en alimentadores de equipos")
    starts = {(round(route.PuntoOrigen.x, 4), round(route.PuntoOrigen.y, 4)) for route in equipment_result["routes"]}
    if len(starts) != 2:
        raise RuntimeError("Los equipos comparten entrada al tablero")
    if any(panels.is_panel(route) for route in equipment_result["routes"]):
        raise RuntimeError("Un alimentador fue clasificado como tablero")

    # Undo/Redo sobre un circuito nuevo.
    tp4, _tp4_boxes = _circuit(doc, "TP-004", tp, [(1000.0, 5500.0), (3500.0, 5500.0)])
    doc.recompute()
    before_undo = len([obj for obj in doc.Objects if str(getattr(obj, "GeneradoPor", "")) == feeders.GENERATED_BY])
    feeders.connect_circuit_feeders(doc, [tp4])
    after_create = len([obj for obj in doc.Objects if str(getattr(obj, "GeneradoPor", "")) == feeders.GENERATED_BY])
    if after_create != before_undo + 1:
        raise RuntimeError("No se creo la ruta para probar Undo")
    doc.undo()
    after_undo = len([obj for obj in doc.Objects if str(getattr(obj, "GeneradoPor", "")) == feeders.GENERATED_BY])
    if after_undo != before_undo:
        raise RuntimeError("Undo no revirtio el alimentador")
    doc.redo()
    after_redo = len([obj for obj in doc.Objects if str(getattr(obj, "GeneradoPor", "")) == feeders.GENERATED_BY])
    if after_redo != after_create:
        raise RuntimeError("Redo no restauro el alimentador")

    # Los dos comandos visibles deben ser adaptadores ejecutables del nucleo.
    feeder_macro = os.path.join(REPO, "Conectar", "Conectar_Alimentadores_a_Tablero_Auto.FCMacro")
    feeder_command = runpy.run_path(feeder_macro, run_name="electriccr_test_feeder_command")
    command_result = feeder_command["run"](
        doc_override=doc,
        cfg_override=dict(feeders.DEFAULT_CONFIG),
        selection_override=[tp1],
    )
    if command_result["circuits"]["errors"]:
        raise RuntimeError("Fallo del comando visible de alimentadores")
    backbone_macro = os.path.join(REPO, "Conectar", "Conectar_Octogonales_por_Circuito.FCMacro")
    backbone_command = runpy.run_path(backbone_macro, run_name="electriccr_test_backbone_command")
    command_backbone = backbone_command["run"](
        doc_override=doc,
        cfg_override=dict(backbone.DEFAULT_CONFIG),
        groups_override=[tp1],
    )
    if command_backbone["errors"]:
        raise RuntimeError("Fallo del comando visible de backbone")

    doc.recompute()
    expected_feeders = len([obj for obj in doc.Objects if str(getattr(obj, "GeneradoPor", "")) == feeders.GENERATED_BY])
    expected_backbones = len([obj for obj in doc.Objects if str(getattr(obj, "GeneradoPor", "")) == backbone.GENERATED_BY])
    doc.saveAs(target)
    App.closeDocument(doc.Name)

    reopened = App.openDocument(target)
    reopened.recompute()
    reopened.recompute()
    actual_feeders = len([obj for obj in reopened.Objects if str(getattr(obj, "GeneradoPor", "")) == feeders.GENERATED_BY])
    actual_backbones = len([obj for obj in reopened.Objects if str(getattr(obj, "GeneradoPor", "")) == backbone.GENERATED_BY])
    if (actual_feeders, actual_backbones) != (expected_feeders, expected_backbones):
        raise RuntimeError("Guardar/reabrir cambio conteos: {} != {}".format((actual_feeders, actual_backbones), (expected_feeders, expected_backbones)))
    App.closeDocument(reopened.Name)
    print(
        "SMOKE CONNECTIONS GENERAL OK feeders={} backbone={} guide=GUIADO panels=TP,TCOM,TS,TAA".format(
            actual_feeders, actual_backbones
        )
    )


if __name__ == "__main__":
    main()
