# -*- coding: utf-8 -*-
"""Real-FreeCAD smoke/regression for ElectricCR canonical A1 demo.

Purpose:
- Exercise the self-contained demo in FreeCAD 1.1.3 without touching user models.
- Verify create/audit, Owner->PLAN movement, Undo/Redo, Delete lifecycle and save/reopen.

Main behavior:
- Creates only a new temporary demo document and a temporary FCStd file.
- Restores the canonical state before final save/reopen.
- Deletes the temporary FCStd at the end when possible.

Future modification guidance:
- Keep this script focused on demo regression; do not repair failures.
- Extend only after the demo contract itself is deliberately expanded.

Version: 0.1.0
Date/time: 2026-09-09 22:09 America/Costa_Rica
Target: FreeCAD 1.1.3.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

from ElectricCR.electriccr.demo.electric_demo_freecad import create_fixed_demo
from ElectricCR.electriccr.demo.electric_demo_audit import audit_demo
from ElectricCR.electriccr.demo.electric_demo_core import build_fixed_demo_spec


def _assert_version():
    version = list(App.Version()[:3])
    assert version == ["1", "1", "3"], App.Version()


def _plan_for(owner):
    name = str(getattr(owner, "DocumentationRepresentationName", "") or "")
    plan = owner.Document.getObject(name) if name else None
    assert plan is not None, owner.Name
    return plan


def _assert_plan_follows(owner, plan, tol=1.0e-5):
    assert abs(float(owner.Placement.Base.x) - float(plan.Placement.Base.x)) <= tol
    assert abs(float(owner.Placement.Base.y) - float(plan.Placement.Base.y)) <= tol
    assert abs(float(plan.Placement.Base.z) - float(owner.DocumentationPlaneZ)) <= tol
    qa = tuple(float(v) for v in owner.Placement.Rotation.Q)
    qb = tuple(float(v) for v in plan.Placement.Rotation.Q)
    direct = max(abs(a - b) for a, b in zip(qa, qb))
    negated = max(abs(a + b) for a, b in zip(qa, qb))
    assert min(direct, negated) <= 1.0e-8


def run():
    _assert_version()
    spec = build_fixed_demo_spec()
    result = create_fixed_demo(spec)
    doc = result["document"]
    owner = result["owners"]["outlet-office-01"]
    owner_name = owner.Name
    plan = _plan_for(owner)
    plan_name = plan.Name

    stages = []

    initial = audit_demo(doc, spec)
    stages.append({"stage": "initial", "status": initial["status"], "counts": initial["counts"]})
    assert initial["status"] == "PASS", initial

    # Move only the Owner. PLAN must follow through the approved A1 contract.
    doc.openTransaction("ElectricCR demo smoke move")
    moved = owner.Placement
    moved.Base.x += 250.0
    moved.Base.y += 125.0
    owner.Placement = moved
    doc.commitTransaction()
    doc.recompute()
    plan = doc.getObject(plan_name)
    _assert_plan_follows(owner, plan)
    stages.append({"stage": "moved", "owner_x": float(owner.Placement.Base.x), "plan_x": float(plan.Placement.Base.x)})

    doc.undo()
    doc.recompute()
    owner = doc.getObject(owner_name)
    plan = doc.getObject(plan_name)
    assert owner is not None and plan is not None
    _assert_plan_follows(owner, plan)
    after_undo = audit_demo(doc, spec)
    stages.append({"stage": "move_undo", "status": after_undo["status"]})
    assert after_undo["status"] == "PASS", after_undo

    doc.redo()
    doc.recompute()
    owner = doc.getObject(owner_name)
    plan = doc.getObject(plan_name)
    _assert_plan_follows(owner, plan)
    stages.append({"stage": "move_redo", "ok": True})

    doc.undo()
    doc.recompute()
    owner = doc.getObject(owner_name)
    plan = doc.getObject(plan_name)
    assert audit_demo(doc, spec)["status"] == "PASS"

    # Exercise the same Std_Delete path used by the GUI. A1 lifecycle should
    # remove both Owner and its PLAN; Undo must restore the canonical pair.
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(owner)
    Gui.runCommand("Std_Delete")
    Gui.updateGui()
    assert doc.getObject(owner_name) is None
    assert doc.getObject(plan_name) is None
    stages.append({"stage": "delete", "owner_exists": False, "plan_exists": False})

    doc.undo()
    doc.recompute()
    owner = doc.getObject(owner_name)
    plan = doc.getObject(plan_name)
    assert owner is not None and plan is not None
    _assert_plan_follows(owner, plan)
    after_delete_undo = audit_demo(doc, spec)
    stages.append({"stage": "delete_undo", "status": after_delete_undo["status"]})
    assert after_delete_undo["status"] == "PASS", after_delete_undo

    # Save/reopen the generated demo only; no production file is involved.
    tmpdir = Path(tempfile.mkdtemp(prefix="electriccr_demo_a1_"))
    fcstd = tmpdir / "ElectricCR_Demo_A1.FCStd"
    doc.recompute()
    doc.saveAs(str(fcstd))
    saved_name = doc.Name
    App.closeDocument(saved_name)

    reopened = App.openDocument(str(fcstd))
    reopened_report = audit_demo(reopened, spec)
    stages.append({"stage": "reopen", "status": reopened_report["status"], "counts": reopened_report["counts"]})
    assert reopened_report["status"] == "PASS", reopened_report

    App.closeDocument(reopened.Name)
    try:
        fcstd.unlink()
        tmpdir.rmdir()
    except Exception:
        pass

    report = {
        "status": "PASS",
        "freecad_version": App.Version(),
        "demo_id": spec["demo_id"],
        "stages": stages,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    App.Console.PrintMessage("[ElectricCR][Demo Smoke] PASS\n")
    return report


if __name__ == "__main__":
    run()
