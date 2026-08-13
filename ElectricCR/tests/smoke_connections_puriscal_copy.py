"""Prueba del motor general sobre una COPIA temporal de Puriscal.

No copia ni guarda el archivo fuente. La ruta recibida debe ser ya una copia
de trabajo fuera de OneDrive. Compatible con FreeCAD 1.1.3.
"""

import os
import sys

import FreeCAD as App


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from ElectricCR.electriccr.connections import backbone, feeders, panels


def _generated(doc, marker):
    return [obj for obj in doc.Objects if str(getattr(obj, "GeneradoPor", "")) == marker]


def main():
    target = os.path.abspath(sys.argv[-1])
    doc = App.openDocument(target)
    real_panels = [obj for obj in doc.Objects if panels.is_panel(obj)]
    codes = {panels.panel_code(obj) for obj in real_panels}
    if not {"TP", "TCOM", "TAA"}.issubset(codes):
        raise RuntimeError("Tableros reales no detectados correctamente: {}".format(sorted(codes)))
    if any("Alimentador" in str(getattr(obj, "Label", "")) for obj in real_panels):
        raise RuntimeError("Una ruta historica fue clasificada como tablero")

    candidates = feeders.candidate_circuit_groups(doc)
    by_id = {cid: group for cid, group, _boxes in candidates}
    if not any(cid.startswith("TP-") for cid in by_id) or not any(cid.startswith("TCOM-") for cid in by_id):
        raise RuntimeError("No se detectaron circuitos TP y TCOM")

    result = feeders.connect_circuit_feeders(doc)
    if result["errors"]:
        raise RuntimeError("Alimentadores sobre copia: {}".format(result["errors"]))
    names = {obj.Name for obj in result["routes"]}
    second = feeders.connect_circuit_feeders(doc)
    if second["errors"] or {obj.Name for obj in second["routes"]} != names:
        raise RuntimeError("La segunda ejecucion duplico o fallo")

    # La cara superior debe distribuir realmente las llegadas por tablero.
    for panel in real_panels:
        routes = [route for route in result["routes"] if getattr(route, "Panel", None) is panel]
        if len(routes) < 2:
            continue
        destinations = {
            (round(route.PuntoDestino.x, 3), round(route.PuntoDestino.y, 3), round(route.PuntoDestino.z, 3))
            for route in routes
        }
        if len(destinations) != len(routes):
            raise RuntimeError("Llegadas superpuestas en {}".format(panels.panel_code(panel)))

    sample_groups = [by_id[cid] for cid in sorted(by_id) if cid in ("TP-005", "TCOM-01")]
    backbone_result = backbone.connect_backbone(doc, sample_groups)
    if backbone_result["errors"]:
        raise RuntimeError("Backbone sobre copia: {}".format(backbone_result["errors"]))
    backbone_names = {obj.Name for obj in backbone_result["routes"]}
    repeated_backbone = backbone.connect_backbone(doc, sample_groups)
    if repeated_backbone["errors"] or {obj.Name for obj in repeated_backbone["routes"]} != backbone_names:
        raise RuntimeError("Backbone no idempotente")

    doc.recompute()
    expected = (len(_generated(doc, feeders.GENERATED_BY)), len(_generated(doc, backbone.GENERATED_BY)))
    doc.save()
    App.closeDocument(doc.Name)

    reopened = App.openDocument(target)
    reopened.recompute()
    actual = (len(_generated(reopened, feeders.GENERATED_BY)), len(_generated(reopened, backbone.GENERATED_BY)))
    if actual != expected:
        raise RuntimeError("Conteos cambiaron al reabrir: {} != {}".format(actual, expected))
    App.closeDocument(reopened.Name)
    print(
        "SMOKE PURISCAL COPY OK panels={} circuits={} feeders={} backbone={}".format(
            sorted(codes), len(candidates), actual[0], actual[1]
        )
    )


if __name__ == "__main__":
    main()
