"""Controlled Upala smoke for the real outlet/switch placement helpers.

The source document is copied before FreeCAD opens it.  Exactly one A1 outlet
and one A1 switch are created in that copy, then the copy and its DXF are
removed.  Existing devices, when present in the source snapshot, are audited
but never edited or migrated.
"""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

import Arch
import FreeCAD as App


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTLET_MACRO = PROJECT_ROOT / "Tomacorrientes" / "InstalarTomacorrientesEnParedesBIM.FCMacro"
SWITCH_MACRO = PROJECT_ROOT / "Iluminación" / "ColocarApagadoresEnPuertas.FCMacro"
A1_CONTRACT = "PhysicalDocumentationA1"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ElectricCR.electriccr.features import objeto_toma_uno


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _props(obj):
    return set(getattr(obj, "PropertiesList", []) or [])


def _device_kind(obj):
    props = _props(obj)
    if obj.TypeId != "App::Link":
        return ""
    tipo = _text(getattr(obj, "Tipo", "")) if "Tipo" in props else ""
    key = _text(getattr(obj, "KeyRegistro", "")) if "KeyRegistro" in props else ""
    if tipo == "Toma" or key == "Tomacorriente_120V":
        return "Toma"
    if tipo == "Apagador" or key == "Apagador_Simple":
        return "Apagador"
    return ""


def _legacy_snapshot(doc):
    result = {}
    for obj in doc.Objects:
        kind = _device_kind(obj)
        contract = _text(getattr(obj, "RepresentationContract", ""))
        if not kind or contract == A1_CONTRACT:
            continue
        linked = getattr(obj, "LinkedObject", None)
        result[obj.Name] = {
            "kind": kind,
            "label": _text(obj.Label),
            "contract": contract or "<missing>",
            "master": _text(getattr(linked, "Name", "")),
            "placement": _placement(obj),
        }
    return result


def _placement(obj):
    value = obj.Placement
    return {
        "base": [round(float(value.Base.x), 6), round(float(value.Base.y), 6), round(float(value.Base.z), 6)],
        "rotation_q": [round(float(item), 12) for item in value.Rotation.Q],
    }


def _metrics(shape):
    box = shape.BoundBox
    return {
        "volume": round(float(shape.Volume), 6),
        "bound_box": [round(float(value), 6) for value in (
            box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax
        )],
        "size": [round(float(value), 6) for value in (box.XLength, box.YLength, box.ZLength)],
        "solids": len(shape.Solids),
        "faces": len(shape.Faces),
    }


def _outlet_candidate(doc, macro):
    walls = [obj for obj in doc.Objects if macro["is_wall"](obj)]
    openings = macro["collect_openings"](doc, walls)
    area_faces = macro["collect_area_faces"](doc)
    for wall in walls:
        for p0, p1, length in macro["wall_segments"](wall):
            tangent = App.Vector((p1.x - p0.x) / length, (p1.y - p0.y) / length, 0.0)
            forbidden = macro["opening_intervals"](p0, p1, wall, openings, 0.0)
            for start, end in macro["usable_runs"](length, forbidden):
                positions = macro["positions_for_run"](start, end, 1800.0, 600.0)
                if not positions:
                    continue
                midpoint_s = (start + end) * 0.5
                midpoint = App.Vector(
                    p0.x + tangent.x * midpoint_s,
                    p0.y + tangent.y * midpoint_s,
                    0.0,
                )
                left_inside, right_inside = macro["side_states"](
                    midpoint, tangent, wall, area_faces
                )
                sides = ([1] if left_inside else []) + ([-1] if right_inside else [])
                if not sides:
                    continue
                distance = positions[0]
                point = App.Vector(
                    p0.x + tangent.x * distance,
                    p0.y + tangent.y * distance,
                    0.0,
                )
                return {
                    "wall": wall,
                    "point": point,
                    "tangent": tangent,
                    "side": sides[0],
                    "segment": [p0, p1],
                    "forbidden": forbidden,
                }
    raise RuntimeError("El algoritmo real no encontro una posicion de toma en Upala")


def _switch_candidate(doc, macro):
    cfg = macro["_default_cfg"]()
    cfg.update({"use_a1": True, "update_existing": False, "dry_run": False})
    diagnostics = []
    for door in macro["_collect_all_doors"](doc):
        plans, skipped = macro["_build_plans"](doc, [door], cfg)
        diagnostics.extend(
            {"door": item.Name, "reason": reason} for item, reason in skipped
        )
        if plans:
            return plans[0], cfg, diagnostics
    raise RuntimeError("El algoritmo real no encontro una posicion de apagador en Upala")


def _test_space(doc):
    source = next(
        (
            obj for obj in doc.Objects
            if obj.Name == "Rectangle006" or _text(obj.Label) == "Rectangle006"
        ),
        None,
    )
    if source is None or source.Shape.isNull():
        raise RuntimeError("Upala no contiene el Rectangle006 documental esperado")
    boundary = doc.addObject("Part::Feature", "ECR_A1_UpalaSpaceBoundary")
    boundary.Label = "ECR A1 Upala Space Boundary [TEMPORAL]"
    boundary.Shape = source.Shape.copy()
    space = Arch.makeSpace(boundary, name="ECR A1 Upala Test Space")
    space.Label = "ECR A1 Upala Test Space [TEMPORAL]"
    space.LongName = "ECR A1 Upala Test Space"
    doc.recompute()
    return space


def _assert_a1(owner, host, space, door=None):
    assert owner.TypeId == "App::Link"
    assert owner.RepresentationContract == A1_CONTRACT
    assert owner.LinkedObject is not None and owner.LinkedObject is not owner
    assert owner.Host is host
    assert owner.Space is space
    assert _text(owner.ElementUID)
    if door is not None:
        assert owner.PuertaOrigen is door
    physical = _metrics(owner.Shape)
    assert physical["volume"] > 0.0 and physical["solids"] > 0
    plan = objeto_toma_uno.get_plan_representation(owner)
    assert plan is not None and plan.Owner is owner
    assert plan.DocumentationOnly is True and plan.RepresentationRole == "PLAN"
    assert plan is not owner and "ElementUID" not in plan.PropertiesList
    plan_metrics = _metrics(plan.Shape)
    assert plan_metrics["volume"] == 0.0 and plan_metrics["solids"] == 0
    return plan, physical, plan_metrics


def run(source_path):
    source = Path(source_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    source_before = {"size": source.stat().st_size, "sha256": _sha256(source)}
    temp_root = Path(tempfile.gettempdir())
    token = uuid.uuid4().hex
    temp_fcstd = temp_root / ("ElectricCR_Upala_A1_Controlled_%s.FCStd" % token)
    temp_dxf = temp_root / ("ElectricCR_Upala_A1_Controlled_%s.dxf" % token)
    previous_document = _text(getattr(App.ActiveDocument, "Name", ""))
    shutil.copy2(source, temp_fcstd)
    doc = None
    reopened = None
    try:
        doc = App.openDocument(str(temp_fcstd))
        doc.UndoMode = 1
        outlet_macro = runpy.run_path(str(OUTLET_MACRO), run_name="ecr_upala_outlet_macro")
        switch_macro = runpy.run_path(str(SWITCH_MACRO), run_name="ecr_upala_switch_macro")
        baseline = _legacy_snapshot(doc)

        # Derive a temporary native Space from Upala's existing Rectangle006.
        # This also supplies the same real plan face to the outlet-side algorithm.
        space = _test_space(doc)
        outlet_data = _outlet_candidate(doc, outlet_macro)
        switch_plan, switch_cfg, switch_diagnostics = _switch_candidate(doc, switch_macro)

        toma_module = outlet_macro["load_toma_module"]()
        doc.openTransaction("ElectricCR Upala: una toma A1 controlada")
        try:
            outlet_group = outlet_macro["_ensure_group"](doc)
            outlet = outlet_macro["create_toma"](
                doc,
                toma_module,
                outlet_group,
                outlet_data["point"],
                outlet_data["tangent"],
                outlet_data["side"],
                outlet_data["wall"],
                49,
                {
                    "registry": "Tomacorriente_120V",
                    "height": 300.0,
                    "use_a1": True,
                },
            )
            doc.recompute()
            outlet_macro["finalize_a1_devices"](
                toma_module, [(outlet, outlet_data["wall"])]
            )
            doc.recompute()
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise

        doc.openTransaction("ElectricCR Upala: un apagador A1 controlado")
        try:
            switch_group = switch_macro["_ensure_group"](doc)
            switch = switch_macro["_create_switch"](
                toma_module, doc, switch_group, switch_plan, switch_cfg
            )
            doc.recompute()
            switch_macro["_finalize_a1_devices"](
                toma_module, [(switch, switch_plan["wall"])]
            )
            doc.recompute()
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise

        outlet_plan, outlet_metrics, outlet_plan_metrics = _assert_a1(
            outlet, outlet_data["wall"], space
        )
        switch_plan_obj, switch_metrics, switch_plan_metrics = _assert_a1(
            switch, switch_plan["wall"], space, switch_plan["door"]
        )
        legacy_after_create = _legacy_snapshot(doc)
        assert legacy_after_create == baseline

        placements = {outlet.Name: _placement(outlet), switch.Name: _placement(switch)}
        physical_before_sync = {outlet.Name: _metrics(outlet.Shape), switch.Name: _metrics(switch.Shape)}
        toma_module.sync_plan_representation(
            outlet, dry_run=False, manage_transaction=False
        )
        toma_module.sync_plan_representation(
            switch, dry_run=False, manage_transaction=False
        )
        physical_after_sync = {outlet.Name: _metrics(outlet.Shape), switch.Name: _metrics(switch.Shape)}
        assert physical_after_sync == physical_before_sync

        # Creation transactions are individually reversible and recoverable.
        switch_name, switch_plan_name = switch.Name, switch_plan_obj.Name
        doc.undo(); doc.recompute()
        assert doc.getObject(switch_name) is None and doc.getObject(switch_plan_name) is None
        assert _legacy_snapshot(doc) == baseline
        outlet_name, outlet_plan_name = outlet.Name, outlet_plan.Name
        doc.undo(); doc.recompute()
        assert doc.getObject(outlet_name) is None and doc.getObject(outlet_plan_name) is None
        assert _legacy_snapshot(doc) == baseline
        doc.redo(); doc.recompute()
        outlet = doc.getObject(outlet_name)
        outlet_plan = doc.getObject(outlet_plan_name)
        assert outlet is not None and outlet_plan is not None
        doc.redo(); doc.recompute()
        switch = doc.getObject(switch_name)
        switch_plan_obj = doc.getObject(switch_plan_name)
        assert switch is not None and switch_plan_obj is not None

        # Height changes relink each App::Link to an A1 master and preserve placement.
        height_results = {}
        for owner, height in ((outlet, 450.0), (switch, 1350.0)):
            before_placement = _placement(owner)
            before_shape = _metrics(owner.Shape)
            doc.openTransaction("ElectricCR Upala: altura A1")
            height_results[owner.Name] = toma_module.set_installation_elevation(owner, height)
            doc.recompute()
            toma_module.sync_plan_representation(owner, dry_run=False, manage_transaction=False)
            doc.commitTransaction()
            after_shape = _metrics(owner.Shape)
            assert _placement(owner) == before_placement
            assert after_shape["volume"] == before_shape["volume"]
            assert after_shape["size"] == before_shape["size"]
            assert after_shape["solids"] == before_shape["solids"]
            assert owner.LinkedObject.RepresentationContract == A1_CONTRACT

        toma_module.export_plan_dxf([outlet, switch], str(temp_dxf))
        assert temp_dxf.is_file() and temp_dxf.stat().st_size > 0
        pre_save = {outlet.Name: _metrics(outlet.Shape), switch.Name: _metrics(switch.Shape)}
        uids = {outlet.Name: outlet.ElementUID, switch.Name: switch.ElementUID}
        reopen_refs = {
            "outlet_wall": outlet.Host.Name,
            "switch_wall": switch.Host.Name,
            "space": outlet.Space.Name,
            "door": switch.PuertaOrigen.Name,
        }
        doc.save()
        App.closeDocument(doc.Name)
        doc = None

        reopened = App.openDocument(str(temp_fcstd))
        outlet = reopened.getObject(outlet_name)
        switch = reopened.getObject(switch_name)
        assert outlet is not None and switch is not None
        assert {outlet.Name: _metrics(outlet.Shape), switch.Name: _metrics(switch.Shape)} == pre_save
        assert {outlet.Name: outlet.ElementUID, switch.Name: switch.ElementUID} == uids
        assert _legacy_snapshot(reopened) == baseline
        _assert_a1(
            outlet,
            reopened.getObject(reopen_refs["outlet_wall"]),
            reopened.getObject(reopen_refs["space"]),
        )
        _assert_a1(
            switch,
            reopened.getObject(reopen_refs["switch_wall"]),
            reopened.getObject(reopen_refs["space"]),
            reopened.getObject(reopen_refs["door"]),
        )

        source_after = {"size": source.stat().st_size, "sha256": _sha256(source)}
        assert source_after == source_before
        result = {
            "freecad_version": ".".join(App.Version()[:3]),
            "source": str(source),
            "source_unchanged": True,
            "legacy_baseline_in_current_file": {
                "outlets": sum(1 for row in baseline.values() if row["kind"] == "Toma"),
                "switches": sum(1 for row in baseline.values() if row["kind"] == "Apagador"),
                "identities_unchanged": True,
            },
            "a1_created": {"outlets": 1, "switches": 1},
            "contracts": [outlet.RepresentationContract, switch.RepresentationContract],
            "owners": [outlet.Name, switch.Name],
            "plans": [
                toma_module.get_plan_representation(outlet).Name,
                toma_module.get_plan_representation(switch).Name,
            ],
            "uids": uids,
            "hosts": [outlet.Host.Name, switch.Host.Name],
            "spaces": [outlet.Space.Name, switch.Space.Name],
            "door": switch.PuertaOrigen.Name,
            "placements": placements,
            "physical": {outlet.Name: outlet_metrics, switch.Name: switch_metrics},
            "plan": {outlet.Name: outlet_plan_metrics, switch.Name: switch_plan_metrics},
            "height_relink": height_results,
            "physical_invariant_under_plan_sync": True,
            "undo_redo": True,
            "save_reopen": True,
            "dxf_size_bytes": temp_dxf.stat().st_size,
            "switch_algorithm_diagnostics": switch_diagnostics,
            "temporary_artifacts_removed": True,
        }
        print("ECR_UPALA_REAL_A1_OK " + json.dumps(result, ensure_ascii=False, sort_keys=True))
        return result
    finally:
        if reopened is not None and reopened.Name in App.listDocuments():
            App.closeDocument(reopened.Name)
        if doc is not None and doc.Name in App.listDocuments():
            App.closeDocument(doc.Name)
        for path in (temp_fcstd, temp_dxf):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
        for backup in temp_root.glob(
            "ElectricCR_Upala_A1_Controlled_%s.*.FCBak" % token
        ):
            try:
                os.remove(backup)
            except FileNotFoundError:
                pass
        if previous_document and previous_document in App.listDocuments():
            App.setActiveDocument(previous_document)


if __name__ == "__main__":
    run(sys.argv[1])
