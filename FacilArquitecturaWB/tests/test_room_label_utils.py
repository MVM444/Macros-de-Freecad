"""Tests for room-label collection and spreadsheet output."""

from __future__ import annotations

import sys
import types
import unittest


if "FreeCAD" not in sys.modules:
    freecad = types.ModuleType("FreeCAD")
    freecad.Console = types.SimpleNamespace(
        PrintMessage=lambda _message: None,
        PrintWarning=lambda _message: None,
        PrintError=lambda _message: None,
    )
    sys.modules["FreeCAD"] = freecad

from FacilArquitecturaWB.core import room_label_utils  # noqa: E402


class Point:
    def __init__(self, x, y, z=0.0):
        self.x, self.y, self.z = x, y, z


class Placement:
    def __init__(self, point):
        self.Base = point


class TextObject:
    TypeId = "App::FeaturePython"

    def __init__(self, name, text, point):
        self.Name = name
        self.Label = "Etiqueta_" + name
        self.Text = text
        self.Placement = Placement(point)


class Document:
    def __init__(self, objects):
        self.Objects = objects


class RoomLabelUtilsTests(unittest.TestCase):
    def test_collects_structured_labels_and_consolidates_duplicates(self):
        doc = Document(
            [
                TextObject("Caja1", ["CAJA", "8.20 m2", "Oficina", "55%"], Point(10, 20)),
                TextObject("Caja2", ["  caja  ", "8,20 m\u00b2", "Oficina", "55%"], Point(30, 40)),
                TextObject("Archivo", ["ARCHIVO", "56.41 m2", "Archivo", "0%"], Point(50, 60)),
            ]
        )
        records = room_label_utils.collect_room_labels(doc)
        self.assertEqual(["ARCHIVO", "CAJA"], [record["name"] for record in records])
        caja = records[1]
        self.assertEqual(2, caja["count"])
        self.assertAlmostEqual(8.2, caja["area"])
        self.assertEqual("Oficina", caja["type"])
        self.assertEqual((10.0, 20.0, 0.0), (caja["x"], caja["y"], caja["z"]))

    def test_ignores_non_text_objects(self):
        doc = Document([types.SimpleNamespace(Name="Wall", Label="Wall")])
        self.assertEqual([], room_label_utils.collect_room_labels(doc))

    def test_reads_square_metre_symbol_without_encoding_dependency(self):
        self.assertAlmostEqual(8.2, room_label_utils.area_value(["CAJA", "8,20 m\u00b2"]))


if __name__ == "__main__":
    unittest.main()
