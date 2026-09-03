"""FreeCAD smoke test for FA centerlines from a Part::Feature Compound.

Nombre: freecad_compound_centerlines_smoke.py
Proposito: validar en FreeCAD real que FA_CenterlinesFromSelection puede leer un
Part::Feature con Shape Compound sin ejecutar Part Explode ni crear objetos
intermedios de explosion.
Funcionamiento: crea dos perfiles rectangulares de muro separados dentro de un
Compound, llama al nucleo de FacilArquitecturaWB y verifica dos ejes independientes,
la conservacion del objeto fuente y la ausencia de geometria explotada en el arbol.
Instrucciones de mantenimiento: mantener este test centrado en la regresion de
Compound; no mezclar pruebas de App::Link, puertas o reconstruccion BIM completa.
FreeCAD objetivo: 1.1.3
Version: 0.1.0
Fecha y hora: 2026-08-23 11:31 America/Costa_Rica
"""

from __future__ import annotations

import math
import os
import sys

import FreeCAD
import Part


TEST_NAME = "FA_CompoundCenterlinesSmoke"
EXPECTED_LENGTH_MM = 4000.0
LENGTH_TOLERANCE_MM = 5.0


def _ensure_repo_on_path():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    wb_dir = os.path.dirname(test_dir)
    repo_root = os.path.dirname(wb_dir)
    if repo_root and repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _rectangle_wire(x0, y0, width, depth):
    points = [
        FreeCAD.Vector(x0, y0, 0.0),
        FreeCAD.Vector(x0 + width, y0, 0.0),
        FreeCAD.Vector(x0 + width, y0 + depth, 0.0),
        FreeCAD.Vector(x0, y0 + depth, 0.0),
    ]
    edges = [
        Part.makeLine(points[0], points[1]),
        Part.makeLine(points[1], points[2]),
        Part.makeLine(points[2], points[3]),
        Part.makeLine(points[3], points[0]),
    ]
    return Part.Wire(edges)


def _segment_length(segment):
    x1, y1, x2, y2 = [float(value) for value in segment]
    return math.hypot(x2 - x1, y2 - y1)


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def run():
    _ensure_repo_on_path()
    from FacilArquitecturaWB.core.centerline_utils import create_centerline_sketch_from_objects

    try:
        existing = FreeCAD.getDocument(TEST_NAME)
    except Exception:
        existing = None
    if existing is not None:
        FreeCAD.closeDocument(TEST_NAME)

    doc = FreeCAD.newDocument(TEST_NAME)
    try:
        group = doc.addObject("App::DocumentObjectGroup", "FA_TestOutput")
        source = doc.addObject("Part::Feature", "Pared_Concreto_Compound_Test")
        source.Label = "Pared Concreto Compound Test"
        try:
            source.addProperty("App::PropertyString", "OriginalLayer", "CAD")
            source.OriginalLayer = "Pared Concreto"
        except Exception:
            pass

        # Two independent 4.0 m long x 150 mm thick walls with a 1.0 m gap.
        wall_a = _rectangle_wire(0.0, 0.0, 4000.0, 150.0)
        wall_b = _rectangle_wire(5000.0, 0.0, 4000.0, 150.0)
        source.Shape = Part.makeCompound([wall_a, wall_b])
        doc.recompute()

        _assert(str(source.Shape.ShapeType) == "Compound", "La fuente de prueba no es Compound.")
        source_children_before = list(source.Shape.childShapes())
        _assert(len(source_children_before) == 2, "El Compound de prueba debe tener dos hijos directos.")
        objects_before = {obj.Name for obj in doc.Objects}

        primary_sketch, segments = create_centerline_sketch_from_objects(
            doc,
            group,
            [source],
            extraction_strategy="auto",
        )
        doc.recompute()

        _assert(primary_sketch is not None, "No se creo el Sketch de centros.")
        _assert(len(segments) == 2, "Se esperaban 2 ejes independientes y se obtuvieron %d." % len(segments))

        lengths = sorted(_segment_length(segment) for segment in segments)
        for length in lengths:
            _assert(
                abs(length - EXPECTED_LENGTH_MM) <= LENGTH_TOLERANCE_MM,
                "Longitud de eje inesperada: %.3f mm." % length,
            )

        # Regression guard: no centerline may bridge the 1.0 m void between walls.
        for segment in segments:
            xs = sorted((float(segment[0]), float(segment[2])))
            _assert(xs[1] - xs[0] < 4500.0, "Un eje atraveso el vacio entre muros: %r" % (segment,))

        _assert(doc.getObject(source.Name) is source, "El objeto fuente fue reemplazado o eliminado.")
        _assert(str(source.Shape.ShapeType) == "Compound", "La fuente dejo de ser Compound tras la extraccion.")
        _assert(len(list(source.Shape.childShapes())) == 2, "La topologia fuente fue alterada.")

        new_objects = [obj for obj in doc.Objects if obj.Name not in objects_before]
        unexpected = [
            obj
            for obj in new_objects
            if not str(getattr(obj, "TypeId", "")).startswith("Sketcher::")
        ]
        _assert(
            not unexpected,
            "Se crearon objetos intermedios no esperados: %s"
            % ", ".join("%s:%s" % (obj.Name, obj.TypeId) for obj in unexpected),
        )

        print("[FACILARQ_TEST] PASS - Compound leido sin Explode")
        print("[FACILARQ_TEST] ejes=%d longitudes_mm=%s" % (len(segments), [round(v, 3) for v in lengths]))
        print("[FACILARQ_TEST] fuente=%s ShapeType=%s hijos=%d" % (
            source.Name,
            source.Shape.ShapeType,
            len(list(source.Shape.childShapes())),
        ))
        return True
    finally:
        try:
            FreeCAD.closeDocument(TEST_NAME)
        except Exception:
            pass


if __name__ == "__main__":
    run()
