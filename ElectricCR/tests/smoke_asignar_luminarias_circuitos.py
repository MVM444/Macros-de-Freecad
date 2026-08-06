"""Smoke test headless para Asignar_Luminarias_Circuitos.FCMacro."""

import os
import sys

import FreeCAD as App


def load_macro():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.abspath(os.path.join(here, "..", "..", "Iluminación", "Asignar_Luminarias_Circuitos.FCMacro"))
    namespace = {"__name__": "electriccr_smoke_circuits", "__file__": path}
    with open(path, "r", encoding="utf-8-sig") as handle:
        exec(compile(handle.read(), path, "exec"), namespace, namespace)
    return namespace


def main():
    source = os.path.abspath(sys.argv[-2])
    target = os.path.abspath(sys.argv[-1])
    doc = App.openDocument(source)
    macro = load_macro()
    luminaires = macro["_physical_luminaires"](doc)
    print("SMOKE CIRCUITS luminaires=%d" % len(luminaires))
    if len(luminaires) < 8:
        raise RuntimeError("No hay suficientes luminarias")
    result = macro["assign_automatic"](doc, "TP", 1, 4, True)
    print("SMOKE CIRCUITS automatic=%s" % result)
    if sum(result["cantidades"].values()) != len(luminaires):
        raise RuntimeError("No se asignaron todas las luminarias")
    groups = [macro["_find_circuit_group"](doc, "TP-%03d" % number) for number in range(1, 5)]
    if any(group is None for group in groups):
        raise RuntimeError("Faltan grupos TP-001 a TP-004")
    if sum(group.CantidadLuminarias for group in groups) != len(luminaires):
        raise RuntimeError("Los totales centrales no coinciden")
    if any(list(group.Group or []) for group in groups):
        raise RuntimeError("Los circuitos duplicaron objetos dentro de Group")
    manual = macro["assign_manual"](doc, luminaires[:2], groups[0], True)
    print("SMOKE CIRCUITS manual=%s" % manual)
    if any(lum.CircuitoID != "TP-001" for lum in luminaires[:2]):
        raise RuntimeError("La asignacion manual no actualizo CircuitoID")
    doc.recompute()
    doc.saveAs(target)
    App.closeDocument(doc.Name)
    print("SMOKE CIRCUITS OK " + target)


if __name__ == "__main__":
    main()
