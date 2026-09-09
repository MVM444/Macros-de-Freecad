"""Probe native FreeCAD Placement expressions through a PropertyLink Owner.

Revision: 2026-09-05, FreeCAD 1.1.3.
This diagnostic creates and removes only temporary data.
"""

from __future__ import annotations

import json
import os
import tempfile

import FreeCAD as App
import Part


DOC_NAME = "ECR_PlanOwnerExpressionProbe"


def _placement_data(obj):
    placement = obj.Placement
    return {
        "base": [round(float(value), 9) for value in placement.Base],
        "rotation_q": [round(float(value), 12) for value in placement.Rotation.Q],
    }


def _assert_plan_follows(owner, plan, expected_z):
    assert abs(plan.Placement.Base.x - owner.Placement.Base.x) < 1.0e-7
    assert abs(plan.Placement.Base.y - owner.Placement.Base.y) < 1.0e-7
    assert abs(plan.Placement.Base.z - expected_z) < 1.0e-7
    assert plan.Placement.Rotation.isSame(owner.Placement.Rotation, 1.0e-9)


def run():
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)
    temp_fcstd = os.path.join(tempfile.gettempdir(), DOC_NAME + ".FCStd")
    if os.path.isfile(temp_fcstd):
        os.remove(temp_fcstd)
    doc = App.newDocument(DOC_NAME)
    doc.UndoMode = 1
    try:
        master = doc.addObject("Part::Feature", "Master")
        master.Shape = Part.makeBox(10.0, 10.0, 10.0)
        owner = doc.addObject("App::Link", "OwnerDevice")
        owner.LinkedObject = master
        owner.addProperty("App::PropertyFloat", "DocumentationPlaneZ", "Representations")
        owner.DocumentationPlaneZ = 0.0
        owner.Placement = App.Placement(
            App.Vector(100.0, 200.0, 30.0),
            App.Rotation(App.Vector(0.0, 0.0, 1.0), 15.0),
        )
        plan = doc.addObject("Part::Feature", "Plan")
        plan.Shape = Part.makePolygon([App.Vector(), App.Vector(20.0, 0.0, 0.0)])
        plan.addProperty("App::PropertyLink", "Owner", "Representations")
        plan.Owner = owner
        expression = (
            "placement(vector(Owner.Placement.Base.x; Owner.Placement.Base.y; "
            "Owner.DocumentationPlaneZ); Owner.Placement.Rotation)"
        )
        plan.setExpression("Placement", expression)
        doc.recompute()
        _assert_plan_follows(owner, plan, 0.0)

        doc.openTransaction("Move and rotate owner")
        owner.Placement = App.Placement(
            App.Vector(600.0, -75.0, 30.0),
            App.Rotation(App.Vector(0.0, 0.0, 1.0), 105.0),
        )
        doc.commitTransaction()
        doc.recompute()
        _assert_plan_follows(owner, plan, 0.0)
        moved = _placement_data(plan)

        doc.openTransaction("Change documentation plane")
        owner.DocumentationPlaneZ = 125.0
        doc.commitTransaction()
        doc.recompute()
        _assert_plan_follows(owner, plan, 125.0)

        doc.undo()
        doc.recompute()
        _assert_plan_follows(owner, plan, 0.0)
        doc.redo()
        doc.recompute()
        _assert_plan_follows(owner, plan, 125.0)

        doc.saveAs(temp_fcstd)
        App.closeDocument(DOC_NAME)
        doc = App.openDocument(temp_fcstd)
        owner = doc.getObject("OwnerDevice")
        plan = doc.getObject("Plan")
        doc.recompute()
        _assert_plan_follows(owner, plan, 125.0)
        expression_engine = [(str(path), str(value)) for path, value in plan.ExpressionEngine]
        assert expression_engine
        result = {
            "freecad": ".".join(App.Version()[:3]),
            "expression": expression,
            "expression_engine": expression_engine,
            "moved": moved,
            "reopened": _placement_data(plan),
            "owner_dependency": owner.Name in [obj.Name for obj in plan.OutList],
            "save_reopen": True,
            "undo_redo": True,
        }
        print("ECR_PLAN_OWNER_EXPRESSION_OK " + json.dumps(result, sort_keys=True))
        return result
    finally:
        if DOC_NAME in App.listDocuments():
            App.closeDocument(DOC_NAME)
        if os.path.isfile(temp_fcstd):
            os.remove(temp_fcstd)


if __name__ == "__main__":
    run()
