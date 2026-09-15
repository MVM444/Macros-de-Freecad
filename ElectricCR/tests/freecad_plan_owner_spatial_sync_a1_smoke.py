"""Regression for A1 PLAN spatial synchronization on a temporary Chomes copy.

Revision: 2026-09-05 14:35, FreeCAD 1.1.3.
The source FCStd is hashed before/after and is never saved.  The test repairs
one real A1 outlet in the copy and creates one temporary A1 switch.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import FreeCAD as App


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ELECTRICCR_ROOT = PROJECT_ROOT / "ElectricCR"
if str(ELECTRICCR_ROOT) not in sys.path:
    sys.path.insert(0, str(ELECTRICCR_ROOT))

from electriccr.features import objeto_toma_uno


OWNER_NAME = "Link_TomaBIM_011"
SWITCH_NAME = "ECR_A1_SpatialSyncSwitch"
EXPECTED_STALE_X = 19003.999751956
REPRODUCED_OWNER_X = 19263.0


def _hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _metrics(shape):
    box = shape.BoundBox
    return {
        "volume": round(float(shape.Volume), 9),
        "solids": len(shape.Solids),
        "bound_box": [
            round(float(value), 9)
            for value in (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)
        ],
    }


def _geometry_signature(shape):
    box = shape.BoundBox
    return {
        "volume": round(float(shape.Volume), 9),
        "solids": len(shape.Solids),
        "edges": len(shape.Edges),
        "size": [
            round(float(box.XLength), 9),
            round(float(box.YLength), 9),
            round(float(box.ZLength), 9),
        ],
    }


def _placement(obj):
    value = obj.Placement
    return {
        "base": [round(float(item), 9) for item in value.Base],
        "rotation_q": [round(float(item), 12) for item in value.Rotation.Q],
    }


def _expression(plan):
    values = []
    for path, expression in list(plan.ExpressionEngine or []):
        values.append([str(path), str(expression)])
    return values


def _assert_plan_follows(owner, plan, expected_z=None):
    z_value = float(owner.DocumentationPlaneZ) if expected_z is None else float(expected_z)
    assert plan.Owner is owner
    assert bool(plan.DocumentationOnly)
    assert str(plan.RepresentationRole) == "PLAN"
    assert plan.TypeId == "Part::Feature"
    assert abs(plan.Placement.Base.x - owner.Placement.Base.x) < 1.0e-6
    assert abs(plan.Placement.Base.y - owner.Placement.Base.y) < 1.0e-6
    assert abs(plan.Placement.Base.z - z_value) < 1.0e-6
    assert plan.Placement.Rotation.isSame(owner.Placement.Rotation, 1.0e-9)
    assert _expression(plan)
    assert "SnapPoints" in plan.PropertiesList
    snap_points = list(plan.SnapPoints or [])
    assert len(snap_points) == 1
    snap = snap_points[0]
    assert abs(float(snap.x)) < 1.0e-9
    assert abs(float(snap.y)) < 1.0e-9
    assert abs(float(snap.z)) < 1.0e-9
    world_snap = plan.Placement.multVec(snap)
    assert abs(float(world_snap.x) - float(plan.Placement.Base.x)) < 1.0e-6
    assert abs(float(world_snap.y) - float(plan.Placement.Base.y)) < 1.0e-6
    assert abs(float(world_snap.z) - float(plan.Placement.Base.z)) < 1.0e-6
    assert _metrics(plan.Shape)["volume"] == 0.0
    assert _metrics(plan.Shape)["solids"] == 0


def _ensure_link(obj, property_name, target, description):
    if property_name not in obj.PropertiesList:
        obj.addProperty("App::PropertyLink", property_name, "BIM", description)
    setattr(obj, property_name, target)


def _ensure_string(obj, property_name, value, description):
    if property_name not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", property_name, "Identity", description)
    setattr(obj, property_name, value)


def _first_door(doc):
    for candidate in doc.Objects:
        ifc_type = str(getattr(candidate, "IfcType", "") or "").casefold()
        if "door" in ifc_type or "window" in ifc_type:
            return candidate
    door = doc.addObject("Part::Feature", "ECR_A1_TestDoor")
    door.addProperty("App::PropertyBool", "ECR_TestFixture", "Tests")
    door.ECR_TestFixture = True
    return door


def run():
    source = Path(os.environ.get("ECR_PLAN_OWNER_SOURCE", ""))
    work_dir = Path(os.environ.get("ECR_PLAN_OWNER_WORK_DIR", ""))
    report_path = Path(os.environ.get("ECR_PLAN_OWNER_REPORT", ""))
    if not source.is_file():
        raise RuntimeError("ECR_PLAN_OWNER_SOURCE must identify Chomes FCStd")
    if not work_dir.is_dir():
        raise RuntimeError("ECR_PLAN_OWNER_WORK_DIR must identify a temporary directory")
    if not report_path.parent.is_dir():
        raise RuntimeError("ECR_PLAN_OWNER_REPORT parent must exist")

    source_hash_before = _hash(source)
    source_stat_before = (source.stat().st_size, source.stat().st_mtime_ns)
    copy_path = work_dir / "Chomes-Segundo Piso_A1_PLAN_OWNER_TEMP.FCStd"
    dxf_path = work_dir / "A1_PLAN_OWNER_TEMP.dxf"
    shutil.copy2(source, copy_path)
    before_documents = set(App.listDocuments())
    doc = None
    try:
        doc = App.openDocument(str(copy_path))
        doc.UndoMode = 1
        owner = doc.getObject(OWNER_NAME)
        assert owner is not None and owner.TypeId == "App::Link"
        assert str(owner.RepresentationContract) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1
        plan = objeto_toma_uno.get_plan_representation(owner)
        assert plan is not None and plan.Owner is owner
        assert plan.ExpressionEngine == []
        assert abs(plan.Placement.Base.x - EXPECTED_STALE_X) < 1.0e-6
        initial_object_count = len(doc.Objects)
        physical_initial = _metrics(owner.Shape)

        stale_placement = App.Placement(owner.Placement)
        stale_placement.Base.x = REPRODUCED_OWNER_X
        owner.Placement = stale_placement
        doc.recompute()
        physical_before_repair = _metrics(owner.Shape)
        stale_delta = round(owner.Placement.Base.x - plan.Placement.Base.x, 9)
        assert abs(stale_delta - (REPRODUCED_OWNER_X - EXPECTED_STALE_X)) < 1.0e-6
        assert not _expression(plan)

        repair_plan = objeto_toma_uno.sync_plan_representation(owner, dry_run=True)
        assert "BIND_PLAN_TO_OWNER_PLACEMENT" in repair_plan["actions"]
        assert "UPDATE_PLAN_REPRESENTATION" in repair_plan["actions"]
        repair = objeto_toma_uno.sync_plan_representation(owner, dry_run=False)
        plan = objeto_toma_uno.get_plan_representation(owner)
        _assert_plan_follows(owner, plan, 0.0)
        signature_after_repair = str(plan.RepresentationSignature)
        assert _metrics(owner.Shape) == physical_before_repair
        assert len(doc.Objects) == initial_object_count

        doc.clearUndos()
        before_move = _placement(owner)
        doc.openTransaction("A1 move and rotate outlet owner")
        moved = App.Placement(owner.Placement)
        moved.Base.x += 500.0
        moved.Base.y += 275.0
        moved.Rotation = App.Rotation(App.Vector(0.0, 0.0, 1.0), 90.0)
        owner.Placement = moved
        doc.commitTransaction()
        doc.recompute()
        _assert_plan_follows(owner, plan, 0.0)
        after_move = _placement(owner)
        assert str(plan.RepresentationSignature) == signature_after_repair
        doc.undo()
        doc.recompute()
        assert _placement(owner) == before_move
        _assert_plan_follows(owner, plan, 0.0)
        doc.redo()
        doc.recompute()
        assert _placement(owner) == after_move
        _assert_plan_follows(owner, plan, 0.0)

        owner_xy_rotation = _placement(owner)
        doc.openTransaction("A1 outlet installation elevation")
        elevation_result = objeto_toma_uno.set_installation_elevation(owner, 450.0)
        doc.commitTransaction()
        doc.recompute()
        assert _placement(owner) == owner_xy_rotation
        _assert_plan_follows(owner, plan, 0.0)
        physical_450 = _metrics(owner.Shape)
        assert physical_450["bound_box"][2] > physical_initial["bound_box"][2]
        assert str(plan.RepresentationSignature) == signature_after_repair

        plan_geometry_before = _geometry_signature(plan.Shape)
        physical_before_documentation = _metrics(owner.Shape)
        doc.openTransaction("A1 documentation plane")
        owner.DocumentationPlaneZ = 225.0
        doc.commitTransaction()
        doc.recompute()
        _assert_plan_follows(owner, plan, 225.0)
        assert _geometry_signature(plan.Shape) == plan_geometry_before
        assert _metrics(owner.Shape) == physical_before_documentation
        assert str(plan.RepresentationSignature) == signature_after_repair

        owner.PlanSymbolScale = 1.35
        scale_sync = objeto_toma_uno.sync_plan_representation(owner, dry_run=False)
        _assert_plan_follows(owner, plan, 225.0)
        assert "UPDATE_PLAN_REPRESENTATION" in scale_sync["actions"]
        assert _geometry_signature(plan.Shape) != plan_geometry_before
        assert _metrics(owner.Shape) == physical_before_documentation
        outlet_signature_scaled = str(plan.RepresentationSignature)

        host = getattr(owner, "Host", None)
        space = getattr(owner, "Space", None)
        door = _first_door(doc)
        switch = objeto_toma_uno.crear_toma_link(
            doc=doc,
            name_prefix="Apagador A1 PLAN Owner test",
            key_registro="Apagador_Simple",
            tipo_logico="Apagador",
            placement=App.Placement(
                App.Vector(owner.Placement.Base.x + 1000.0, owner.Placement.Base.y + 500.0, 0.0),
                App.Rotation(App.Vector(0.0, 0.0, 1.0), 37.0),
            ),
            altura_rel=1200.0,
            orientacion_pared="Vertical",
            internal_name=SWITCH_NAME,
            recompute=False,
            separate_documentation=True,
        )
        _ensure_string(
            switch,
            "ElementUID",
            "a1-plan-owner-switch-0001",
            "Stable identity for the temporary regression switch",
        )
        _ensure_link(switch, "Host", host, "Temporary host copied from outlet")
        _ensure_link(switch, "Space", space, "Temporary space copied from outlet")
        _ensure_link(switch, "PuertaOrigen", door, "Temporary door for yaw regression")
        doc.recompute()
        objeto_toma_uno.sync_plan_representation(switch, dry_run=False)
        switch_plan = objeto_toma_uno.get_plan_representation(switch)
        _assert_plan_follows(switch, switch_plan, 0.0)
        switch_physical_before = _metrics(switch.Shape)
        switch_plan_before = _geometry_signature(switch_plan.Shape)

        doc.openTransaction("A1 move and rotate switch owner")
        switch_moved = App.Placement(switch.Placement)
        switch_moved.Base.x += 250.0
        switch_moved.Base.y -= 125.0
        switch_moved.Rotation = App.Rotation(App.Vector(0.0, 0.0, 1.0), 83.0)
        switch.Placement = switch_moved
        doc.commitTransaction()
        doc.recompute()
        _assert_plan_follows(switch, switch_plan, 0.0)
        switch_after_move = _placement(switch)
        doc.undo()
        doc.recompute()
        _assert_plan_follows(switch, switch_plan, 0.0)
        doc.redo()
        doc.recompute()
        assert _placement(switch) == switch_after_move
        _assert_plan_follows(switch, switch_plan, 0.0)

        objeto_toma_uno.set_installation_elevation(switch, 1350.0)
        doc.recompute()
        _assert_plan_follows(switch, switch_plan, 0.0)
        assert _metrics(switch.Shape)["bound_box"][2] > switch_physical_before["bound_box"][2]
        switch.DocumentationPlaneZ = 75.0
        switch.PlanSymbolScale = 0.80
        objeto_toma_uno.sync_plan_representation(switch, dry_run=False)
        _assert_plan_follows(switch, switch_plan, 75.0)
        assert _geometry_signature(switch_plan.Shape) != switch_plan_before

        physical_before_dxf = {
            owner.Name: _metrics(owner.Shape),
            switch.Name: _metrics(switch.Shape),
        }
        exported = objeto_toma_uno.export_plan_dxf([owner, switch], str(dxf_path))
        assert [item.Name for item in exported] == [plan.Name, switch_plan.Name]
        assert dxf_path.is_file() and dxf_path.stat().st_size > 0
        assert _metrics(owner.Shape) == physical_before_dxf[owner.Name]
        assert _metrics(switch.Shape) == physical_before_dxf[switch.Name]
        assert objeto_toma_uno.cleanup_orphan_documentation(doc, dry_run=True) == []

        names = [owner.Name, plan.Name, switch.Name, switch_plan.Name]
        object_count_before_save = len(doc.Objects)
        placements_before_save = {name: _placement(doc.getObject(name)) for name in names}
        expressions_before_save = {
            plan.Name: _expression(plan),
            switch_plan.Name: _expression(switch_plan),
        }
        doc.save()
        copy_document_name = doc.Name
        App.closeDocument(copy_document_name)
        doc = App.openDocument(str(copy_path))
        doc.recompute()
        assert len(doc.Objects) == object_count_before_save
        owner, plan, switch, switch_plan = [doc.getObject(name) for name in names]
        assert all((owner, plan, switch, switch_plan))
        _assert_plan_follows(owner, plan, 225.0)
        _assert_plan_follows(switch, switch_plan, 75.0)
        assert {name: _placement(doc.getObject(name)) for name in names} == placements_before_save
        assert _expression(plan) == expressions_before_save[plan.Name]
        assert _expression(switch_plan) == expressions_before_save[switch_plan.Name]
        assert str(plan.RepresentationSignature) == outlet_signature_scaled
        assert switch.PuertaOrigen is not None
        assert objeto_toma_uno.cleanup_orphan_documentation(doc, dry_run=True) == []

        count_before_recompute = len(doc.Objects)
        placements_before_recompute = {name: _placement(doc.getObject(name)) for name in names}
        for _index in range(3):
            doc.recompute()
        assert len(doc.Objects) == count_before_recompute
        assert {name: _placement(doc.getObject(name)) for name in names} == placements_before_recompute
        assert objeto_toma_uno.sync_plan_representation(owner, dry_run=True)["material_changes"] == 0
        assert objeto_toma_uno.sync_plan_representation(switch, dry_run=True)["material_changes"] == 0

        result = {
            "status": "PASS",
            "freecad": ".".join(App.Version()[:3]),
            "source_hash_before": source_hash_before,
            "source_bytes": source_stat_before[0],
            "initial_object_count": initial_object_count,
            "object_count_after_reopen": len(doc.Objects),
            "reproduced_delta_x_mm": stale_delta,
            "repair_actions": repair["actions"],
            "spatial_mechanism": "native Placement expression through Owner PropertyLink",
            "representation_schema_version": objeto_toma_uno.REPRESENTATION_SCHEMA_VERSION,
            "outlet": {
                "name": owner.Name,
                "plan": plan.Name,
                "placement": _placement(owner),
                "plan_placement": _placement(plan),
                "expression_engine": _expression(plan),
                "physical": _metrics(owner.Shape),
                "documentation": _metrics(plan.Shape),
                "height_result": elevation_result,
            },
            "switch": {
                "name": switch.Name,
                "plan": switch_plan.Name,
                "placement": _placement(switch),
                "plan_placement": _placement(switch_plan),
                "expression_engine": _expression(switch_plan),
                "door": switch.PuertaOrigen.Name,
                "physical": _metrics(switch.Shape),
                "documentation": _metrics(switch_plan.Shape),
            },
            "undo_redo": {"outlet_move_rotation": True, "switch_move_rotation": True},
            "documentation_plane_z": {"outlet": 225.0, "switch": 75.0},
            "plan_symbol_scale": {"outlet": 1.35, "switch": 0.80},
            "save_reopen": True,
            "recompute_repetitions": 3,
            "orphan_plans": 0,
            "dxf_size_bytes": dxf_path.stat().st_size,
            "physical_invariant_after_dxf": True,
            "legacy_migrated": False,
        }
        report_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        print("ECR_PLAN_OWNER_SPATIAL_SYNC_OK " + json.dumps(result, sort_keys=True))
        return result
    finally:
        if doc is not None and doc.Name in App.listDocuments():
            App.closeDocument(doc.Name)
        if copy_path.is_file():
            copy_path.unlink()
        for backup_path in work_dir.glob(copy_path.stem + ".*.FCBak"):
            backup_path.unlink()
        assert set(App.listDocuments()) == before_documents
        assert _hash(source) == source_hash_before
        assert (source.stat().st_size, source.stat().st_mtime_ns) == source_stat_before


if __name__ == "__main__":
    run()
