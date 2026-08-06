"""FreeCAD regression test for 3D-only evaporator elevation changes.

Run from FreeCAD's Python console or MCP with::

    from MEPWorkbenchCR.tests.test_hvac_evaporator_installation_elevation import run
    run()
"""

import os
import tempfile

import FreeCAD as App

from MEPWorkbenchCR.MEP.hvac import hvac_equipment


DOC_NAME = "Test_HVACEvaporator_InstallationElevation"


def _placement_signature(obj):
    placement = obj.Placement
    rotation = placement.Rotation
    return (
        round(float(placement.Base.x), 6),
        round(float(placement.Base.y), 6),
        round(float(placement.Base.z), 6),
        tuple(round(float(value), 9) for value in rotation.Q),
    )


def _shape_signature(obj):
    shape = obj.Shape
    bbox = shape.BoundBox
    try:
        shape_hash = int(shape.hashCode())
    except Exception:
        shape_hash = 0
    return (
        shape_hash,
        round(float(bbox.XMin), 6),
        round(float(bbox.YMin), 6),
        round(float(bbox.ZMin), 6),
        round(float(bbox.XMax), 6),
        round(float(bbox.YMax), 6),
        round(float(bbox.ZMax), 6),
        len(shape.Edges),
        len(shape.Faces),
    )


def run():
    previous_doc_name = App.ActiveDocument.Name if App.ActiveDocument is not None else ""
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)

    temp_path = os.path.join(tempfile.gettempdir(), DOC_NAME + ".FCStd")
    if os.path.exists(temp_path):
        os.remove(temp_path)

    doc = App.newDocument(DOC_NAME)
    try:
        equipment = hvac_equipment.insert_evaporator_safe(
            doc=doc,
            point=App.Vector(1250.0, 850.0, 0.0),
            model_name="Pared_12000",
        )
        assert equipment is not None
        symbol = equipment.Symbol2D
        info = equipment.Info2D
        assert symbol is not None
        assert info is not None
        assert hvac_equipment.resolve_equipment_owner(symbol, doc=doc) is equipment
        assert hvac_equipment.equipment_owners_from_objects([symbol, equipment], doc=doc) == [equipment]

        symbol_name = symbol.Name
        equipment_name = equipment.Name
        symbol_placement_before = _placement_signature(symbol)
        symbol_shape_before = _shape_signature(symbol)
        info_placement_before = _placement_signature(info)
        master_before = equipment.LinkedObject

        applied = hvac_equipment.set_installation_elevation(equipment, 3100.0)
        doc.recompute()

        assert abs(float(applied) - 3100.0) <= 0.01
        assert abs(float(equipment.InstallationElevation.Value) - 3100.0) <= 0.01
        assert abs(float(equipment.Height) - 3.1) <= 0.0001
        assert equipment.LinkedObject is not master_before
        assert abs(float(equipment.LinkedObject.Height) - 3.1) <= 0.0001
        assert equipment.Symbol2D is symbol
        assert equipment.Info2D is info
        assert _placement_signature(symbol) == symbol_placement_before
        assert _shape_signature(symbol) == symbol_shape_before
        assert _placement_signature(info) == info_placement_before

        doc.saveAs(temp_path)
        App.closeDocument(DOC_NAME)

        reopened = App.openDocument(temp_path)
        reopened.recompute()
        persisted_equipment = reopened.getObject(equipment_name)
        persisted_symbol = reopened.getObject(symbol_name)
        assert persisted_equipment is not None
        assert persisted_symbol is not None
        assert abs(float(persisted_equipment.InstallationElevation.Value) - 3100.0) <= 0.01
        assert abs(float(persisted_equipment.Height) - 3.1) <= 0.0001
        assert _placement_signature(persisted_symbol) == symbol_placement_before
        # OCCT's in-memory shape hash may change after reopening; compare the
        # persisted vector geometry (bounds and topology counts) instead.
        assert _shape_signature(persisted_symbol)[1:] == symbol_shape_before[1:]
        App.closeDocument(reopened.Name)
    finally:
        if DOC_NAME in App.listDocuments():
            App.closeDocument(DOC_NAME)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if previous_doc_name and previous_doc_name in App.listDocuments():
            App.setActiveDocument(previous_doc_name)

    return {
        "canonical_property_mm": True,
        "legacy_height_m": True,
        "model_3d_changed": True,
        "symbol_2d_placement_preserved": True,
        "symbol_2d_shape_preserved": True,
        "info_2d_placement_preserved": True,
        "selection_from_symbol": True,
        "persisted": True,
    }


if __name__ == "__main__":
    print(run())
