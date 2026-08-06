"""Regression test for semantic height and composed plan rotation.

Run with FreeCAD's bundled Python from the repository root::

    python ElectricCR/tests/test_cambiar_altura_rotacion_semantica.py
"""

import os
import runpy
import sys
import tempfile

import FreeCAD as App


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ElectricCR.electriccr.features import objeto_toma_uno
from MEPWorkbenchCR.MEP.hvac import hvac_equipment


DOC_NAME = "Test_Altura_Rotacion_Semantica"
MACRO_PATH = os.path.join(ROOT, "Objetos", "cambiar_altura_y_rotacion_objetos.FCMacro")
NFPA_MACRO_PATH = os.path.join(ROOT, "Deteccion", "ColocarDetectores_NFPA.FCMacro")


def _near(value, expected, tolerance=0.01):
    return abs(float(value) - float(expected)) <= float(tolerance)


def _euler(obj):
    return tuple(float(value) for value in obj.Placement.Rotation.toEuler())


def _assert_rotation(obj, yaw, pitch, roll):
    actual = _euler(obj)
    assert _near(actual[0], yaw, 0.001), actual
    assert _near(actual[1], pitch, 0.001), actual
    assert _near(actual[2], roll, 0.001), actual


def _legacy_luminaire_link(doc, height_mm):
    master = objeto_toma_uno.crear_toma_uno(
        doc=doc,
        name_prefix="Legacy luminaire master",
        key_registro="Luminaria_Legacy_Test",
        tipo_logico="Luminaria",
        internal_name="LegacyLuminaireMaster",
        recompute=False,
    )
    master.ModoVisual = "Ambos"
    master.AlturaRel = float(height_mm)
    master.addProperty("App::PropertyString", "LnkMasterKey", "Link")
    master.addProperty("App::PropertyFloat", "LnkMasterAltura", "Link")
    master.addProperty("App::PropertyString", "LnkMasterMode", "Link")
    master.LnkMasterKey = "Luminaria_Legacy_Test"
    master.LnkMasterAltura = float(height_mm)
    master.LnkMasterMode = "Ambos"

    link = doc.addObject("App::Link", "LegacyLuminaireLink")
    link.Label = "Luminaria legacy App::Link"
    link.LinkedObject = master
    link.LinkTransform = True
    link.Placement = App.Placement(App.Vector(300.0, 400.0, 0.0), App.Rotation(15.0, 25.0, 35.0))
    return link, master


def run():
    macro = runpy.run_path(MACRO_PATH, run_name="electriccr_height_rotation_test")
    apply_changes = macro["cambiar_altura_y_rotacion_objetos"]
    nfpa_macro = runpy.run_path(NFPA_MACRO_PATH, run_name="electriccr_nfpa_sensor_test")

    previous_doc_name = App.ActiveDocument.Name if App.ActiveDocument is not None else ""
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)
    temp_path = os.path.join(tempfile.gettempdir(), DOC_NAME + ".FCStd")
    if os.path.exists(temp_path):
        os.remove(temp_path)

    doc = App.newDocument(DOC_NAME)
    doc.UndoMode = 1
    try:
        room = doc.addObject("Part::Feature", "TestRoom")
        room.Label = "Recinto de prueba"
        sensor = nfpa_macro["insert_sensor"](
            doc,
            objeto_toma_uno.crear_toma_uno,
            "Sensor_Humo",
            "Sensor directo ",
            room,
            App.Vector(0.0, 0.0, 0.0),
            App.Rotation(),
            100.0,
            200.0,
            1,
            altura_rel=2500.0,
            modo_visual="Ambos",
        )
        assert sensor is not None
        sensor.ModoVisual = "Ambos"
        sensor.AlturaRel = 2500.0
        sensor.Placement = App.Placement(App.Vector(100.0, 200.0, 0.0), App.Rotation(10.0, 20.0, 30.0))

        luminaire, old_luminaire_master = _legacy_luminaire_link(doc, 2800.0)
        circuit_group = doc.addObject("App::DocumentObjectGroup", "LightingCircuitTest")
        circuit_group.addObject(luminaire)
        luminaire_label_before = luminaire.Label
        sibling_link = doc.addObject("App::Link", "SiblingLuminaireLink")
        sibling_link.LinkedObject = old_luminaire_master
        sibling_link.LinkTransform = True

        simple = doc.addObject("Part::Feature", "SimpleObject")
        simple.Placement = App.Placement(App.Vector(0.0, 0.0, 100.0), App.Rotation())

        equipment = hvac_equipment.insert_evaporator_safe(
            doc=doc,
            point=App.Vector(1200.0, 800.0, 0.0),
            model_name="Pared_12000",
        )
        assert equipment is not None
        equipment.Placement = App.Placement(equipment.Placement.Base, App.Rotation(5.0, 10.0, 15.0))
        symbol = equipment.Symbol2D
        assert symbol is not None
        symbol_z_before = float(symbol.Placement.Base.z)
        hvac_height_before = hvac_equipment.installation_elevation_mm(equipment)

        doc.recompute()
        doc.clearUndos()

        assert apply_changes(
            True,
            "abs",
            3100.0,
            True,
            "abs",
            90.0,
            objects=[sensor, luminaire, symbol, simple],
        )

        assert _near(sensor.AlturaRel.Value, 3100.0)
        assert _near(sensor.Placement.Base.z, 0.0)
        _assert_rotation(sensor, 90.0, 20.0, 30.0)

        assert luminaire.LinkedObject is not old_luminaire_master
        assert sibling_link.LinkedObject is old_luminaire_master
        assert _near(luminaire.AlturaRel, 3100.0)
        assert luminaire.Label == luminaire_label_before
        assert luminaire in list(circuit_group.Group or [])
        assert str(luminaire.KeyRegistro) == "Luminaria_Legacy_Test"
        assert _near(luminaire.Placement.Base.x, 300.0)
        assert _near(luminaire.Placement.Base.y, 400.0)
        assert _near(luminaire.Placement.Base.z, 0.0)
        _assert_rotation(luminaire, 90.0, 25.0, 35.0)

        assert _near(hvac_equipment.installation_elevation_mm(equipment), 3100.0)
        assert _near(equipment.Placement.Base.z, 0.0)
        assert _near(symbol.Placement.Base.z, symbol_z_before)
        _assert_rotation(equipment, 90.0, 10.0, 15.0)

        assert _near(simple.Placement.Base.z, 3100.0)
        _assert_rotation(simple, 90.0, 0.0, 0.0)

        doc.undo()
        doc.recompute()
        sensor = doc.getObject("Part2DObject") or doc.getObject(sensor.Name)
        luminaire = doc.getObject("LegacyLuminaireLink")
        simple = doc.getObject("SimpleObject")
        equipment = doc.getObject(equipment.Name)
        assert _near(sensor.AlturaRel.Value, 2500.0)
        assert luminaire.LinkedObject is old_luminaire_master
        assert _near(simple.Placement.Base.z, 100.0)
        assert _near(hvac_equipment.installation_elevation_mm(equipment), hvac_height_before)

        doc.redo()
        doc.recompute()
        sensor = doc.getObject(sensor.Name)
        luminaire = doc.getObject("LegacyLuminaireLink")
        simple = doc.getObject("SimpleObject")
        equipment = doc.getObject(equipment.Name)
        assert _near(sensor.AlturaRel.Value, 3100.0)
        assert _near(luminaire.AlturaRel, 3100.0)
        assert _near(simple.Placement.Base.z, 3100.0)
        assert _near(hvac_equipment.installation_elevation_mm(equipment), 3100.0)

        assert apply_changes(
            True,
            "delta",
            100.0,
            True,
            "delta",
            15.0,
            objects=[sensor, luminaire, equipment, simple],
        )
        assert _near(sensor.AlturaRel.Value, 3200.0)
        assert _near(luminaire.AlturaRel, 3200.0)
        assert _near(hvac_equipment.installation_elevation_mm(equipment), 3200.0)
        assert _near(simple.Placement.Base.z, 3200.0)
        _assert_rotation(sensor, 105.0, 20.0, 30.0)

        names = {
            "sensor": sensor.Name,
            "luminaire": luminaire.Name,
            "equipment": equipment.Name,
            "symbol": equipment.Symbol2D.Name,
            "simple": simple.Name,
            "group": circuit_group.Name,
        }
        doc.saveAs(temp_path)
        App.closeDocument(DOC_NAME)

        reopened = App.openDocument(temp_path)
        reopened.recompute()
        sensor = reopened.getObject(names["sensor"])
        luminaire = reopened.getObject(names["luminaire"])
        equipment = reopened.getObject(names["equipment"])
        symbol = reopened.getObject(names["symbol"])
        simple = reopened.getObject(names["simple"])
        circuit_group = reopened.getObject(names["group"])
        assert _near(sensor.AlturaRel.Value, 3200.0)
        assert _near(sensor.Placement.Base.z, 0.0)
        assert _near(luminaire.AlturaRel, 3200.0)
        assert luminaire.Label == luminaire_label_before
        assert luminaire in list(circuit_group.Group or [])
        assert _near(luminaire.Placement.Base.z, 0.0)
        assert _near(hvac_equipment.installation_elevation_mm(equipment), 3200.0)
        assert _near(symbol.Placement.Base.z, symbol_z_before)
        assert _near(simple.Placement.Base.z, 3200.0)
        App.closeDocument(reopened.Name)
    finally:
        if DOC_NAME in App.listDocuments():
            App.closeDocument(DOC_NAME)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if previous_doc_name and previous_doc_name in App.listDocuments():
            App.setActiveDocument(previous_doc_name)

    return {
        "sensor_direct": True,
        "legacy_luminaire_link": True,
        "shared_master_isolated": True,
        "hvac_symbol_2d_plane": True,
        "simple_fallback": True,
        "absolute_and_delta": True,
        "technical_rotation_preserved": True,
        "undo_redo": True,
        "save_reopen": True,
    }


if __name__ == "__main__":
    print(run())
