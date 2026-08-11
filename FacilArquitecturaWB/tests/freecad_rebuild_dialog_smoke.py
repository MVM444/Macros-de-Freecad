"""Headless Qt smoke test for the BIM reconstruction assistant.

Descripcion: valida creacion del dialogo, asignaciones automaticas y lectura manual.
Objetivo: detectar incompatibilidades PySide antes de cargar el Workbench en GUI.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 23:55 UTC-06:00.
Version: 0.1.0.
Instrucciones de mantenimiento: ejecutar con QT_QPA_PLATFORM=offscreen.
"""

from __future__ import annotations

import os
import sys

import FreeCAD
from PySide import QtWidgets


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.core.bim_rebuild_utils import suggest_rebuild_assignments  # noqa: E402
from FacilArquitecturaWB.ui.dialog_rebuild_bim_model import RebuildBIMModelDialog  # noqa: E402


def _sketch(doc, name, kind, element, thickness=0.0):
    obj = doc.addObject("Sketcher::SketchObject", name)
    obj.addProperty("App::PropertyString", "FA_CenterlineKind", "FacilArquitectura")
    obj.addProperty("App::PropertyString", "FA_ElementType", "FacilArquitectura")
    obj.addProperty("App::PropertyLength", "FA_WallThickness", "FacilArquitectura")
    obj.FA_CenterlineKind = kind
    obj.FA_ElementType = element
    obj.FA_WallThickness = thickness
    return obj


def main():
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = FreeCAD.newDocument("FA_Rebuild_Dialog_Smoke")
    wall = _sketch(doc, "FA_GridWallTrace", "walls", "Muros", 150.0)
    columns = _sketch(doc, "Sketch_Columnas", "columns", "Columnas")
    doors = _sketch(doc, "Sketch_Puertas", "doors", "Puertas")
    window = _sketch(doc, "Sketch_Ventanas", "walls", "Ventanas")
    analysis = suggest_rebuild_assignments(doc)
    dialog = RebuildBIMModelDialog(analysis)
    assignments, options = dialog.values()
    assert assignments["walls"] is wall
    assert assignments["columns"] is columns
    assert assignments["doors"] is doors
    assert assignments["windows"] == [window]
    assert options["wall_height_mm"] == 3000.0
    dialog.close()
    FreeCAD.closeDocument(doc.Name)
    application.processEvents()
    print("FA_REBUILD_DIALOG_OK assignments=ok parameters=ok")


if __name__ == "__main__":
    main()
