"""Smoke test headless para Asignar_Luminarias_Apagadores.FCMacro.

Uso:
    FreeCADCmd.exe smoke_asignar_luminarias_apagadores.py entrada.FCStd salida.FCStd
"""

import os
import sys

import FreeCAD as App


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Faltan archivo de entrada y salida")
    source = os.path.abspath(sys.argv[-2])
    target = os.path.abspath(sys.argv[-1])
    here = os.path.dirname(os.path.abspath(__file__))
    macro = os.path.abspath(os.path.join(here, "..", "..", "Iluminación", "Asignar_Luminarias_Apagadores.FCMacro"))
    doc = App.openDocument(source)
    namespace = {"__name__": "electriccr_smoke", "__file__": macro}
    with open(macro, "r", encoding="utf-8-sig") as handle:
        exec(compile(handle.read(), macro, "exec"), namespace, namespace)
    luminaires = namespace["_physical_objects"](doc, namespace["_is_luminaire"])
    switches = namespace["_physical_objects"](doc, namespace["_is_switch"])
    print("SMOKE devices luminaires=%d switches=%d" % (len(luminaires), len(switches)))
    if len(luminaires) < 8 or len(switches) < 3:
        raise RuntimeError("El documento no contiene ocho luminarias y tres apagadores de prueba")
    result = namespace["assign_manual"](doc, luminaires[:2], switches[:2], 90.0, 140.0)
    print("SMOKE result=%s" % result)
    if not result.get("triway") or result.get("luminarias") != 2:
        raise RuntimeError("Resultado tri-way inesperado")
    control = namespace["_control_by_id"](doc, result["id"])
    if control is None or len(control.Luminarias) != 2 or len(control.Apagadores) != 2:
        raise RuntimeError("Los enlaces centrales no quedaron guardados")
    namespace["assign_manual"](doc, luminaires[2:4], [switches[2]], 90.0, 140.0)
    namespace["assign_manual"](doc, luminaires[4:6], [switches[2]], 90.0, 140.0)
    if switches[2].ECR_NumeroTeclas != 2 or switches[2].ECR_TipoControl != "Doble":
        raise RuntimeError("No se genero el apagador doble")
    namespace["assign_manual"](doc, luminaires[6:8], [switches[2]], 90.0, 140.0)
    if switches[2].ECR_NumeroTeclas != 3 or switches[2].ECR_TipoControl != "Triple":
        raise RuntimeError("No se genero el apagador triple")
    marker = doc.getObject("ECR_ControlMarker_" + switches[2].Name)
    if marker is None or marker.TextoPlano != "3" or marker.Shape.isNull():
        raise RuntimeError("El indicador 2D triple no se genero")
    doc.recompute()
    doc.saveAs(target)
    App.closeDocument(doc.Name)
    print("SMOKE OK " + target)


if __name__ == "__main__":
    main()
