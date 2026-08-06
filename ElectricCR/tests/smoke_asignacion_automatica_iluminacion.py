"""Smoke test headless de asignacion automatica por recinto."""

import os
import sys

import FreeCAD as App


def main():
    source = os.path.abspath(sys.argv[-2])
    target = os.path.abspath(sys.argv[-1])
    here = os.path.dirname(os.path.abspath(__file__))
    macro = os.path.abspath(os.path.join(here, "..", "..", "Iluminación", "Asignar_Luminarias_Apagadores.FCMacro"))
    doc = App.openDocument(source)
    namespace = {"__name__": "electriccr_smoke_auto", "__file__": macro}
    with open(macro, "r", encoding="utf-8-sig") as handle:
        exec(compile(handle.read(), macro, "exec"), namespace, namespace)
    result = namespace["assign_automatic"](doc, True, 90.0, 140.0)
    print("SMOKE AUTO result=%s" % result)
    if result.get("controles", 0) <= 0 or result.get("luminarias", 0) <= 0:
        raise RuntimeError("La asignacion automatica no produjo controles")
    for control in namespace["_control_objects"](doc):
        if not control.Luminarias or len(control.Apagadores) not in (1, 2):
            raise RuntimeError("Control automatico incompleto: " + control.Name)
    doc.recompute()
    doc.saveAs(target)
    App.closeDocument(doc.Name)
    print("SMOKE AUTO OK " + target)


if __name__ == "__main__":
    main()
