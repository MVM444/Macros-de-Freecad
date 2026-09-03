"""Smoke test for the ElectricCR macro moves and icon resolution."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

import FreeCAD as App
import FreeCADGui as Gui
import Part


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
XY_PATH = os.path.join(REPO_ROOT, "Tomacorrientes", "Ordenar_Tomas_XY.FCMacro")
HOR_PATH = os.path.join(REPO_ROOT, "Tomacorrientes", "Ordenar_Tomas_XY_Horario.FCMacro")


def _exec_macro(path):
    namespace = {"__name__": "smoke_macro_reorganization", "__file__": path}
    with open(path, "rb") as handle:
        exec(compile(handle.read(), path, "exec"), namespace)
    return namespace


def _make_toma(doc, name, x, y):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = name
    obj.addProperty("App::PropertyString", "Tipo", "ElectricCR")
    obj.Tipo = "Toma"
    obj.Shape = Part.makeBox(20, 20, 20, App.Vector(x, y, 0))
    obj.Placement.Base = App.Vector(x, y, 0)
    return obj


def _run_one(path, function_name, expected):
    doc = App.newDocument("ECR_MacroReorganizationSmoke")
    try:
        group = doc.addObject("App::DocumentObjectGroup", "Tomas")
        a = _make_toma(doc, "TomaA", 100, 100)
        b = _make_toma(doc, "TomaB", 300, 300)
        c = _make_toma(doc, "TomaC", 200, 500)
        group.addObject(a)
        group.addObject(b)
        group.addObject(c)
        doc.recompute()

        module = _exec_macro(path)
        # FreeCADCmd has no interactive Selection object; exercise the same
        # reordering primitive used by each public command.
        assert module["_reorder_group"](group)
        doc.recompute()
        assert [obj.Name for obj in group.Group] == expected
    finally:
        if hasattr(Gui, "Selection"):
            Gui.Selection.clearSelection()
        App.closeDocument(doc.Name)


def run():
    assert os.path.isfile(XY_PATH)
    assert os.path.isfile(HOR_PATH)
    for archived in (
        ("Objetos", "HVAC_Etiqueta_Libre.FCMacro"),
        ("Areas", "actualizar_rectangulos_con_spreadsheet().FCMacro"),
        ("Areas", "AnalizarAreasRectangularesDesdeMurosBIM.FCMacro"),
        ("Cajas", "CajaEMT.FCMacro"),
    ):
        assert os.path.isfile(os.path.join(REPO_ROOT, "Xcluidos", *archived))

    for icon in (
        "Ordenar_Tomas_XY.svg",
        "Ordenar_Tomas_XY_Horario.svg",
        "Habilitar_Transform_en_Links_Dispositivos.svg",
        "Asignar_Tableros_y_Circuitos.svg",
    ):
        icon_path = os.path.join(REPO_ROOT, "ElectricCR", "icons", icon)
        ET.parse(icon_path)

    _run_one(XY_PATH, "ordenar_tomas_xy", ["TomaC", "TomaB", "TomaA"])
    _run_one(HOR_PATH, "ordenar_tomas_xy_horario", ["TomaC", "TomaB", "TomaA"])
    print("PASS: ElectricCR macro reorganization, moved macros and SVG icons")


if __name__ == "__main__":
    run()
