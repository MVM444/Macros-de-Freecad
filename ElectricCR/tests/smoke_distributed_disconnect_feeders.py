"""Smoke test headless de alimentadores distribuidos en la cara del tablero."""

import os
import runpy

import FreeCAD as App
import Part


def _string(obj, name, value):
    obj.addProperty("App::PropertyString", name, "Test")
    setattr(obj, name, value)


def _link(obj, name, value):
    obj.addProperty("App::PropertyLink", name, "Test")
    setattr(obj, name, value)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    macro = os.path.abspath(
        os.path.join(here, "..", "..", "Conectar", "Conectar_Desconectores_HVAC_a_TP.FCMacro")
    )
    namespace = runpy.run_path(macro, run_name="electriccr_test_distributed_disconnects")

    doc = App.newDocument("TestDistributedDisconnectFeeders")
    panel = doc.addObject("Part::Feature", "PanelTP")
    panel.Label = "Tablero principal"
    panel.Shape = Part.makeBox(900.0, 300.0, 1200.0)
    _string(panel, "ClaseEquipo", "Tablero")
    _string(panel, "Codigo", "TP")

    disconnectors = []
    for index, circuit in enumerate(("TP-021", "TP-022", "TP-023"), start=1):
        obj = doc.addObject("Part::Feature", "Disconnect%02d" % index)
        obj.Label = "Desconector %02d" % index
        obj.Shape = Part.makeBox(100.0, 100.0, 100.0, App.Vector(2000.0 * index, 3000.0, 8000.0))
        _string(obj, "ClaseEquipo", "Desconector HVAC")
        _string(obj, "Codigo", "DS-%02d" % index)
        _string(obj, "CircuitoID", circuit)
        _link(obj, "Panel", panel)
        disconnectors.append(obj)

    doc.recompute()
    records = namespace["analyze_assignments"](doc, disconnectors)
    plan = namespace["_slot_plan"](doc)
    if [plan[obj.Name][:2] for obj in disconnectors] != [(0, 3), (1, 3), (2, 3)]:
        raise RuntimeError("El plan de ranuras no es estable: %r" % plan)

    routes = []
    for record in records:
        routes.append(namespace["_run_connection"](record, plan[record["object"].Name]))
    doc.recompute()

    starts = [(round(route.PuntoOrigen.x, 6), round(route.PuntoOrigen.y, 6)) for route in routes]
    if len(set(starts)) != 3:
        raise RuntimeError("Las rutas comparten el mismo punto superior: %r" % starts)
    for index, route in enumerate(routes, start=1):
        if abs(float(route.PuntoOrigen.z) - 1200.0) > 0.01:
            raise RuntimeError("Punto fuera de la cara superior: %s" % route.PuntoOrigen)
        if int(route.RanuraTableroOrigen) != index:
            raise RuntimeError("Numero de ranura incorrecto")
        if int(route.CantidadRanurasTableroOrigen) != 3:
            raise RuntimeError("Cantidad de ranuras incorrecta")

    route_count = len([obj for obj in doc.Objects if getattr(obj, "Tipo", "") == "AlimentadorEntreTableros"])
    original_start = App.Vector(routes[1].PuntoOrigen)
    updated = namespace["_run_connection"](records[1], plan[disconnectors[1].Name])
    doc.recompute()
    new_count = len([obj for obj in doc.Objects if getattr(obj, "Tipo", "") == "AlimentadorEntreTableros"])
    if new_count != route_count or updated.PuntoOrigen.distanceToPoint(original_start) > 0.001:
        raise RuntimeError("La actualizacion no fue idempotente")

    App.closeDocument(doc.Name)
    print("SMOKE DISTRIBUTED DISCONNECT FEEDERS OK starts=%r" % starts)


if __name__ == "__main__":
    main()
