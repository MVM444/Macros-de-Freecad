"""Smoke test for the self-contained rectangular BIM-wall area engine.

Run with the Python bundled by FreeCAD 1.1.3 or through FreeCAD MCP.
Only a temporary document and a temporary FCStd copy are used.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import os
import sys
import tempfile

import FreeCAD as App

FREECAD_MOD_DIR = os.path.join(App.getHomePath(), "Mod")
if FREECAD_MOD_DIR not in sys.path:
    sys.path.insert(0, FREECAD_MOD_DIR)

import Draft
import FreeCADGui as Gui
import Part
import Sketcher


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
ARCHIVED_WRAPPER_PATH = os.path.join(
    REPO_ROOT,
    "Xcluidos",
    "Areas",
    "AnalizarAreasRectangularesDesdeMurosBIM.FCMacro",
)
ENGINE_PATH = os.path.join(REPO_ROOT, "FacilArquitecturaWB", "core", "rectangular_area_analysis.py")
OUTLET_PATH = os.path.join(REPO_ROOT, "Tomacorrientes", "CrearCircuitosGeneralesPorParedYRecinto.FCMacro")
LIGHTING_PATH = os.path.join(REPO_ROOT, "Iluminacion", "Actualizar_Iluminacion_Completa.FCMacro")
if not os.path.isfile(LIGHTING_PATH):
    LIGHTING_PATH = os.path.join(REPO_ROOT, "Iluminación", "Actualizar_Iluminacion_Completa.FCMacro")


def _load_module(name, path):
    if str(path).lower().endswith(".fcmacro"):
        spec = importlib.util.spec_from_loader(name, SourceFileLoader(name, path))
    else:
        spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError("Cannot load module: %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _line(sketch, x1, y1, x2, y2):
    sketch.addGeometry(
        Part.LineSegment(App.Vector(x1, y1, 0), App.Vector(x2, y2, 0)),
        False,
    )


def _wall(doc, name, sketch, shape):
    wall = doc.addObject("Part::Feature", name)
    wall.Label = name
    wall.Shape = shape
    wall.addProperty("App::PropertyString", "FA_Role", "FacilArquitectura")
    wall.addProperty("App::PropertyLink", "Base", "FacilArquitectura")
    wall.addProperty("App::PropertyLength", "Width", "FacilArquitectura")
    wall.FA_Role = "wall"
    wall.Base = sketch
    wall.Width = 120.0
    return wall


def _label(name, point, area_m2):
    obj = Draft.make_text([name, "%.2f m2" % area_m2], placement=point, screen=False)
    obj.Label = "Etiqueta_" + name.replace(" ", "_")
    return obj


def _rectangles(doc):
    group = doc.getObject("FA_RectangularAreas")
    if group is None:
        return []
    return [
        obj
        for obj in list(group.Group or [])
        if str(getattr(obj, "ElectricCRTipo", "") or "").lower() == "area"
    ]


def _run_rectangular_engine(walls):
    # The visible launcher is intentionally archived. Test the preserved,
    # reusable engine directly and verify the archived entry point remains.
    assert os.path.isfile(ARCHIVED_WRAPPER_PATH)
    engine = _load_module("facilarq_rectangular_area_analysis_headless", ENGINE_PATH)
    return engine.generate_rectangular_areas(doc=App.ActiveDocument, walls=walls)


def _lighting_helpers():
    with open(LIGHTING_PATH, "r", encoding="utf-8") as handle:
        source = handle.read()
    cutoff = source.index("\ndef run(")
    namespace = {"__name__": "electriccr_lighting_helpers_test", "__file__": LIGHTING_PATH}
    exec(compile(source[:cutoff], LIGHTING_PATH, "exec"), namespace)
    return namespace


def run():
    doc_name = "ECR_RectangularAreasSmoke"
    old = App.listDocuments().get(doc_name)
    if old is not None:
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    doc.UndoMode = 1
    temp_path = os.path.join(tempfile.gettempdir(), doc_name + ".FCStd")
    if os.path.exists(temp_path):
        os.remove(temp_path)

    try:
        areas_parent = doc.addObject("App::DocumentObjectGroup", "FA_Areas")
        areas_parent.Label = "04_Areas"

        left_source = doc.addObject("Sketcher::SketchObject", "WallAxesA")
        _line(left_source, 0, 0, 0, 4000)
        _line(left_source, 0, 0, 8000, 0)
        _line(left_source, 0, 4000, 8000, 4000)

        right_source = doc.addObject("Sketcher::SketchObject", "WallAxesB")
        _line(right_source, 4000, 0, 4000, 4000)
        _line(right_source, 8000, 0, 8000, 4000)

        wall_a = _wall(
            doc,
            "WallA",
            left_source,
            Part.makeCompound(
                [Part.makeBox(120, 4000, 3000), Part.makeBox(8000, 120, 3000)]
            ),
        )
        wall_b = _wall(
            doc,
            "WallB",
            right_source,
            Part.makeCompound(
                [
                    Part.makeBox(120, 4000, 3000, App.Vector(3940, 0, 0)),
                    Part.makeBox(120, 4000, 3000, App.Vector(7880, 0, 0)),
                    Part.makeBox(8000, 120, 3000, App.Vector(0, 3880, 0)),
                ]
            ),
        )
        _label("RECINTO A", App.Vector(2000, 2000, 0), 15.05)
        _label("RECINTO B", App.Vector(6000, 2000, 0), 15.05)
        doc.recompute()

        result = _run_rectangular_engine([wall_a, wall_b])
        rectangles = _rectangles(doc)
        assert len(rectangles) == 2
        assert len(result["walls"]) == 2
        assert doc.getObject("Spreadsheet_Analisis_Areas") is not None
        assert int(result["group"].FA_RoomCount) == 2
        assert len(list(result["group"].FA_SourceBIMWalls or [])) == 2
        assert len(list(result["group"].FA_SourceCenterlines or [])) == 2
        for obj in rectangles:
            assert obj.TypeId == "Part::Part2DObjectPython"
            assert str(getattr(getattr(obj, "Proxy", None), "Type", "")) == "Rectangle"
            assert bool(obj.MakeFace)
            assert len(obj.Shape.Faces) == 1
            assert abs(float(obj.Placement.Base.z) - 20.0) < 0.01
            assert str(obj.GeneratedBy) == "FA_RectangularAreaAnalysis"
            assert str(obj.FA_GeneratedBy) == "FA_RectangularAreaAnalysis"
            assert str(obj.ElectricCRTipo) == "Area"
            assert float(obj.Length.Value) > 500.0
            assert float(obj.Height.Value) > 500.0
            assert float(obj.AreaM2) > 1.0
            assert obj.FA_SourceBIMWall is wall_a
            assert obj.FA_SourceCenterline is left_source

        doc.undo()
        assert doc.getObject("FA_RectangularAreas") is None
        doc.redo()
        assert len(_rectangles(doc)) == 2

        result2 = _run_rectangular_engine([wall_a, wall_b])
        assert len(_rectangles(doc)) == 2
        assert len([obj for obj in doc.Objects if obj.Name == "Spreadsheet_Analisis_Areas"]) == 1
        assert result2["group"].Name == "FA_RectangularAreas"

        single_source = doc.addObject("Sketcher::SketchObject", "WallAxesSingle")
        _line(single_source, 0, 0, 0, 4000)
        _line(single_source, 4000, 0, 4000, 4000)
        _line(single_source, 8000, 0, 8000, 4000)
        _line(single_source, 0, 0, 8000, 0)
        _line(single_source, 0, 4000, 8000, 4000)
        single_wall = _wall(
            doc,
            "WallSingle",
            single_source,
            Part.makeCompound(list(wall_a.Shape.Solids) + list(wall_b.Shape.Solids)),
        )
        single_result = _run_rectangular_engine([single_wall])
        assert len(single_result["walls"]) == 1
        assert len(_rectangles(doc)) == 2

        from FacilArquitecturaWB.core import ceiling_utils

        ceiling_rooms = ceiling_utils.collect_rooms(doc, selection=[])
        assert len(ceiling_rooms) == 2

        outlets = _load_module("ecr_outlet_room_test", OUTLET_PATH)
        outlet_records = outlets.area_records(doc)
        assert len(outlet_records) == 2
        assert outlets.point_rooms(App.Vector(2000, 2000, 0), outlet_records) == ["RECINTO A"]

        lighting = _lighting_helpers()
        lighting_rows, _stats = lighting["_collect_area_rows"](
            doc.getObject("FA_RectangularAreas"), {}
        )
        assert len(lighting_rows) == 2
        assert all(row["filas"] >= 1 and row["columnas"] >= 1 for row in lighting_rows)
        assert all(hasattr(obj, "Rows") and hasattr(obj, "Columns") for obj in _rectangles(doc))

        doc.recompute()
        doc.saveAs(temp_path)
        App.closeDocument(doc.Name)
        doc = App.openDocument(temp_path)
        doc.recompute()
        reopened = _rectangles(doc)
        assert len(reopened) == 2
        assert doc.getObject("Spreadsheet_Analisis_Areas") is not None
        assert all(obj.TypeId == "Part::Part2DObjectPython" for obj in reopened)
        assert all(bool(obj.MakeFace) and len(obj.Shape.Faces) == 1 for obj in reopened)

        print(
            "PASS: rectangular BIM-wall engine remains repository-contained; single/multi-wall input, "
            "metadata, spreadsheet, rerun, Undo/Redo, persistence, ceilings, outlets "
            "and lighting consumers verified"
        )
    finally:
        if hasattr(Gui, "Selection"):
            Gui.Selection.clearSelection()
        current = App.listDocuments().get(doc_name)
        if current is not None:
            App.closeDocument(doc_name)
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    run()
