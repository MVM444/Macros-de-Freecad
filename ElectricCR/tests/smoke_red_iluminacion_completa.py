"""Smoke test headless de cajas, ramales y alimentadores de iluminacion."""

import os
import sys

import FreeCAD as App


def main():
    source = os.path.abspath(sys.argv[-2])
    target = os.path.abspath(sys.argv[-1])
    here = os.path.dirname(os.path.abspath(__file__))
    macro = os.path.abspath(os.path.join(here, "..", "..", "Conectar", "Preparar_Red_Iluminacion_Completa.FCMacro"))
    doc = App.openDocument(source)
    namespace = {"__name__": "electriccr_smoke_red_luz", "__file__": macro}
    with open(macro, "r", encoding="utf-8-sig") as handle:
        exec(compile(handle.read(), macro, "exec"), namespace, namespace)
    groups = namespace["_lighting_groups"](doc)
    print("SMOKE RED groups=%s" % [namespace["_group_circuit_id"](group) for group in groups])
    result = namespace["run"](
        doc_override=doc,
        groups_override=groups,
        cfg_override={
            "box_z": 3300.0,
            "route_z": 3300.0,
            "panel_route_z": 3400.0,
            "bend_radius": 100.0,
            "rebuild": True,
            "luminaire_boxes": True,
            "switch_boxes": True,
            "branches": True,
            "panel_feeders": True,
        },
    )
    print("SMOKE RED result=%s" % result)
    if result is None:
        raise RuntimeError("El orquestador no termino")
    for group in groups:
        boxes = list(getattr(group, "CajasOctogonalesAsignadas", []) or [])
        if not boxes:
            raise RuntimeError("Circuito sin cajas: " + group.CircuitoID)
    circuit_ids = set(group.CircuitoID for group in groups)
    feeders = [obj for obj in doc.Objects
               if str(getattr(obj, "GeneradoPor", "")) == "Conectar_Circuitos_TP_a_Cara_Superior_Tablero"
               and str(getattr(obj, "CircuitoID", "")) in circuit_ids]
    if len(feeders) != len(groups):
        raise RuntimeError("Faltan alimentadores al TP")
    doc.recompute()
    doc.saveAs(target)
    App.closeDocument(doc.Name)
    print("SMOKE RED OK " + target)


if __name__ == "__main__":
    main()
