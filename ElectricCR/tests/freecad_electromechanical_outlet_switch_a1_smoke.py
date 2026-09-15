"""MCP smoke for exactly one outlet and one switch under the A1 contract.

Revision: 2026-09-03, FreeCAD 1.1.3.  The document and DXF are temporary and
are removed even if an assertion fails.  No productive object is inspected or
mutated by this test.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import Arch
import Draft
import FreeCAD as App
import FreeCADGui as Gui
import Part


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ElectricCR.electriccr.features import objeto_toma_uno
from ElectricCR.electriccr.semantic.freecad_adapter import (
    ensure_device_semantics,
    is_semantic_device_candidate,
)


DOC_NAME = "ECR_OutletSwitch_A1_MCP"
FIXTURE_GROUP = "ElectricCR A1 MCP Test"


def _rect_face(x, y, width, depth):
    points = [
        App.Vector(x, y, 0.0),
        App.Vector(x + width, y, 0.0),
        App.Vector(x + width, y + depth, 0.0),
        App.Vector(x, y + depth, 0.0),
        App.Vector(x, y, 0.0),
    ]
    return Part.Face(Part.makePolygon(points))


def _add_bool(obj, name, value=True):
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyBool", name, FIXTURE_GROUP)
    setattr(obj, name, bool(value))


def _metrics(shape):
    box = shape.BoundBox
    return {
        "volume": round(float(shape.Volume), 6),
        "bound_box": [
            round(float(box.XMin), 6),
            round(float(box.YMin), 6),
            round(float(box.ZMin), 6),
            round(float(box.XMax), 6),
            round(float(box.YMax), 6),
            round(float(box.ZMax), 6),
        ],
        "solids": len(shape.Solids),
        "faces": len(shape.Faces),
    }


def _placement(obj):
    value = obj.Placement
    return {
        "base": [
            round(float(value.Base.x), 6),
            round(float(value.Base.y), 6),
            round(float(value.Base.z), 6),
        ],
        "rotation_q": [round(float(item), 12) for item in value.Rotation.Q],
    }


def _remove_temp(path):
    if path and os.path.isfile(path):
        os.remove(path)


def _make_context(doc):
    building = Arch.makeBuilding(name="ECR A1 Test Building")
    level = Arch.makeBuildingPart(name="Ground Floor")
    level.IfcType = "Building Storey"
    building.addObject(level)

    boundary = doc.addObject("Part::Feature", "ECR_A1_SpaceBoundary")
    boundary.Shape = _rect_face(0.0, 0.0, 4000.0, 3000.0)
    _add_bool(boundary, "ECR_TestFixture")
    space = Arch.makeSpace(boundary, name="ECR A1 Test Space")
    space.Label = "ECR A1 Test Space"
    space.LongName = "ECR A1 Test Space"
    level.addObject(space)

    axis = Draft.make_line(App.Vector(0.0, 0.0, 0.0), App.Vector(4000.0, 0.0, 0.0))
    axis.Label = "ECR A1 Host Axis"
    _add_bool(axis, "ECR_TestFixture")
    host = Arch.makeWall(axis, width=200.0, height=3000.0, name="ECR A1 Host Wall")
    host.Label = "ECR A1 Host Wall"
    level.addObject(host)
    return level, space, host


def _assert_a1_device(owner, expected_space, expected_host, min_z):
    plan = objeto_toma_uno.get_plan_representation(owner)
    assert str(owner.RepresentationContract) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1
    assert str(owner.LinkedObject.RepresentationContract) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1
    assert str(owner.RepresentationContract) != objeto_toma_uno.REPRESENTATION_CONTRACT_LEGACY
    assert str(owner.LinkedObject.RepresentationContract) != objeto_toma_uno.REPRESENTATION_CONTRACT_LEGACY
    assert owner.TypeId == "App::Link" and owner.LinkedObject is not None
    assert owner.Space is expected_space and owner.Host is expected_host
    assert str(owner.ElementUID).strip()
    assert plan is not None and plan.Owner is owner
    assert plan.DocumentationOnly is True and str(plan.RepresentationRole) == "PLAN"
    assert "ElementUID" not in plan.PropertiesList
    physical = _metrics(owner.Shape)
    documentation = _metrics(plan.Shape)
    assert physical["volume"] > 0.0 and physical["solids"] > 0
    assert physical["bound_box"][2] > float(min_z)
    assert documentation["volume"] == 0.0 and documentation["solids"] == 0
    assert documentation["bound_box"][2] == 0.0
    assert documentation["bound_box"][5] == 0.0
    return plan, physical, documentation


def run():
    previous_document = App.ActiveDocument.Name if App.ActiveDocument is not None else ""
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)
    temp_fcstd = os.path.join(tempfile.gettempdir(), DOC_NAME + ".FCStd")
    temp_dxf = os.path.join(tempfile.gettempdir(), DOC_NAME + ".dxf")
    _remove_temp(temp_fcstd)
    _remove_temp(temp_dxf)
    doc = App.newDocument(DOC_NAME)
    doc.UndoMode = 1
    try:
        level, space, host = _make_context(doc)
        staging = doc.addObject("App::DocumentObjectGroup", "ECR_A1_Devices")
        level.addObject(staging)
        doc.recompute()

        initial_count = len(doc.Objects)
        doc.clearUndos()
        doc.openTransaction("ElectricCR A1 create outlet and switch")
        outlet = objeto_toma_uno.crear_toma_link(
            doc=doc,
            name_prefix="Tomacorriente A1",
            key_registro="Tomacorriente_120V",
            tipo_logico="Toma",
            placement=App.Placement(App.Vector(1000.0, 100.0, 0.0), App.Rotation()),
            altura_rel=300.0,
            orientacion_pared="Vertical",
            internal_name="ECR_A1_Outlet",
            recompute=False,
            target_group=staging,
            separate_documentation=True,
        )
        switch = objeto_toma_uno.crear_toma_link(
            doc=doc,
            name_prefix="Apagador A1",
            key_registro="Apagador_Simple",
            tipo_logico="Apagador",
            placement=App.Placement(
                App.Vector(2000.0, 100.0, 0.0),
                App.Rotation(App.Vector(0.0, 0.0, 1.0), 12.0),
            ),
            altura_rel=1200.0,
            orientacion_pared="Vertical",
            internal_name="ECR_A1_Switch",
            recompute=False,
            target_group=staging,
            separate_documentation=True,
        )
        doc.recompute()
        objeto_toma_uno.sync_plan_representation(outlet, dry_run=False, manage_transaction=False)
        objeto_toma_uno.sync_plan_representation(switch, dry_run=False, manage_transaction=False)
        doc.commitTransaction()

        identities = [obj for obj in doc.Objects if is_semantic_device_candidate(obj)]
        assert identities == [outlet, switch]
        electriccr_masters = [
            obj for obj in doc.Objects
            if obj.TypeId == "Part::FeaturePython" and objeto_toma_uno.is_electriccr_device(obj)
        ]
        assert electriccr_masters
        assert all(
            str(master.RepresentationContract) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1
            for master in electriccr_masters
        )

        owner_names = [outlet.Name, switch.Name]
        plan_names = [
            objeto_toma_uno.get_plan_representation(outlet).Name,
            objeto_toma_uno.get_plan_representation(switch).Name,
        ]
        master_names = [outlet.LinkedObject.Name, switch.LinkedObject.Name]
        after_create_count = len(doc.Objects)
        doc.undo()
        doc.recompute()
        assert all(doc.getObject(name) is None for name in owner_names + plan_names)
        doc.redo()
        doc.recompute()
        outlet, switch = [doc.getObject(name) for name in owner_names]
        assert all((outlet, switch)) and len(doc.Objects) == after_create_count

        outlet_semantics = ensure_device_semantics(
            outlet,
            dry_run=False,
            uid_factory=lambda: "a1e00000-0000-4000-8000-000000000001",
            host=host,
        )
        switch_semantics = ensure_device_semantics(
            switch,
            dry_run=False,
            uid_factory=lambda: "a1e00000-0000-4000-8000-000000000002",
            host=host,
        )
        assert outlet_semantics["status"] == "RESOLVED"
        assert switch_semantics["status"] == "RESOLVED"
        assert outlet.ElementUID != switch.ElementUID

        outlet_plan, outlet_physical_300, outlet_plan_before = _assert_a1_device(
            outlet, space, host, 250.0
        )
        switch_plan, switch_physical_1200, switch_plan_before = _assert_a1_device(
            switch, space, host, 1100.0
        )
        placements_before = {outlet.Name: _placement(outlet), switch.Name: _placement(switch)}
        uids = {outlet.Name: str(outlet.ElementUID), switch.Name: str(switch.ElementUID)}

        # PLAN changes independently; the physical metrics must be byte-for-byte stable.
        outlet.PlanSymbolScale = 1.25
        switch.PlanSymbolScale = 0.80
        objeto_toma_uno.sync_plan_representation(outlet, dry_run=False)
        objeto_toma_uno.sync_plan_representation(switch, dry_run=False)
        assert _metrics(outlet.Shape) == outlet_physical_300
        assert _metrics(switch.Shape) == switch_physical_1200
        assert _metrics(outlet_plan.Shape) != outlet_plan_before
        assert _metrics(switch_plan.Shape) != switch_plan_before
        idempotent_counts = len(doc.Objects)
        assert objeto_toma_uno.sync_plan_representation(outlet, dry_run=False)["material_changes"] == 0
        assert objeto_toma_uno.sync_plan_representation(switch, dry_run=False)["material_changes"] == 0
        assert len(doc.Objects) == idempotent_counts

        doc.openTransaction("ElectricCR A1 visibility")
        objeto_toma_uno.set_representation_visibility(outlet, False, True)
        objeto_toma_uno.set_representation_visibility(switch, True, False)
        doc.commitTransaction()
        doc.undo()
        doc.recompute()
        doc.redo()
        doc.recompute()
        assert not bool(outlet.MostrarModelo3D) and bool(outlet.MostrarSimboloPlano)
        assert bool(switch.MostrarModelo3D) and not bool(switch.MostrarSimboloPlano)
        objeto_toma_uno.set_representation_visibility(outlet, True, True)
        objeto_toma_uno.set_representation_visibility(switch, True, True)

        doc.openTransaction("ElectricCR A1 installation heights")
        objeto_toma_uno.set_installation_elevation(outlet, 450.0)
        objeto_toma_uno.set_installation_elevation(switch, 1350.0)
        doc.recompute()
        doc.commitTransaction()
        masters_after_height = [outlet.LinkedObject.Name, switch.LinkedObject.Name]
        outlet_physical_450 = _metrics(outlet.Shape)
        switch_physical_1350 = _metrics(switch.Shape)
        assert outlet_physical_450["bound_box"][2] > outlet_physical_300["bound_box"][2]
        assert switch_physical_1350["bound_box"][2] > switch_physical_1200["bound_box"][2]
        for owner in (outlet, switch):
            assert owner.Space is space and owner.Host is host
            assert _placement(owner) == placements_before[owner.Name]
            assert str(owner.ElementUID) == uids[owner.Name]
            assert str(owner.RepresentationContract) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1
        doc.undo()
        doc.recompute()
        assert [outlet.LinkedObject.Name, switch.LinkedObject.Name] == master_names
        doc.redo()
        doc.recompute()
        assert [outlet.LinkedObject.Name, switch.LinkedObject.Name] == masters_after_height

        exported = objeto_toma_uno.export_plan_dxf([outlet, switch], temp_dxf)
        assert [obj.Name for obj in exported] == plan_names
        assert os.path.isfile(temp_dxf) and os.path.getsize(temp_dxf) > 0
        dxf_size = os.path.getsize(temp_dxf)

        doc.recompute()
        context_names = [level.Name, space.Name, host.Name, staging.Name]
        doc.saveAs(temp_fcstd)
        App.closeDocument(DOC_NAME)
        doc = App.openDocument(temp_fcstd)
        doc.recompute()
        level, space, host, staging = [doc.getObject(name) for name in context_names]
        outlet, switch = [doc.getObject(name) for name in owner_names]
        assert all((level, space, host, staging, outlet, switch))
        assert [obj for obj in doc.Objects if is_semantic_device_candidate(obj)] == [outlet, switch]
        for owner in (outlet, switch):
            assert owner.TypeId == "App::Link" and owner.LinkedObject is not None
            assert owner.Space is space and owner.Host is host
            assert _placement(owner) == placements_before[owner.Name]
            assert str(owner.ElementUID) == uids[owner.Name]
            assert str(owner.RepresentationContract) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1
            assert str(owner.LinkedObject.RepresentationContract) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1
            plan = objeto_toma_uno.get_plan_representation(owner)
            assert plan is not None and plan.Owner is owner and plan.DocumentationOnly
            assert "ElementUID" not in plan.PropertiesList
        assert objeto_toma_uno.cleanup_orphan_documentation(doc, dry_run=True) == []

        final_metrics = {
            outlet.Name: {
                "shape": _metrics(outlet.Shape),
                "plan": _metrics(objeto_toma_uno.get_plan_representation(outlet).Shape),
            },
            switch.Name: {
                "shape": _metrics(switch.Shape),
                "plan": _metrics(objeto_toma_uno.get_plan_representation(switch).Shape),
            },
        }
        result = {
            "freecad_version": ".".join(App.Version()[:3]),
            "document": DOC_NAME,
            "device_identity_count": 2,
            "outlet_count": 1,
            "switch_count": 1,
            "initial_object_count": initial_count,
            "representation_contract": objeto_toma_uno.REPRESENTATION_CONTRACT_A1,
            "owners": owner_names,
            "masters": masters_after_height,
            "plan_objects": plan_names,
            "element_uids": uids,
            "space": space.Name,
            "host": host.Name,
            "placements": placements_before,
            "metrics": final_metrics,
            "dxf_size_bytes": dxf_size,
            "undo_redo": {"creation": True, "visibility": True, "height": True},
            "save_reopen": True,
            "projection_idempotent": True,
            "orphan_documentation": 0,
            "productive_documents_touched": False,
        }
        print("ECR_OUTLET_SWITCH_A1_OK " + json.dumps(result, sort_keys=True))

        for owner in (outlet, switch):
            objeto_toma_uno.remove_device_with_documentation(owner)
        assert all(doc.getObject(name) is None for name in owner_names + plan_names)
        assert objeto_toma_uno.cleanup_orphan_documentation(doc, dry_run=True) == []
        return result
    finally:
        try:
            Gui.Selection.clearSelection()
        except Exception:
            pass
        if DOC_NAME in App.listDocuments():
            App.closeDocument(DOC_NAME)
        _remove_temp(temp_fcstd)
        _remove_temp(temp_dxf)
        if previous_document and previous_document in App.listDocuments():
            App.setActiveDocument(previous_document)


if __name__ == "__main__":
    run()
