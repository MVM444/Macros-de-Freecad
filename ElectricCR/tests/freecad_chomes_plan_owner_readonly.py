"""Read-only diagnosis for an A1 Owner/PLAN pair in a supplied FCStd.

Revision: 2026-09-05, FreeCAD 1.1.3.
Set ``ECR_PLAN_OWNER_SOURCE`` and optionally ``ECR_PLAN_OWNER_NAME``.
The source document is never saved.
"""

from __future__ import annotations

import json
import os

import FreeCAD as App


def _placement(obj):
    value = obj.Placement
    return {
        "base": [round(float(item), 9) for item in value.Base],
        "rotation_q": [round(float(item), 12) for item in value.Rotation.Q],
    }


def _global_placement(obj):
    try:
        return _placement(type("Global", (), {"Placement": obj.getGlobalPlacement()})())
    except Exception:
        return _placement(obj)


def run():
    source = os.environ.get("ECR_PLAN_OWNER_SOURCE", "").strip()
    owner_name = os.environ.get("ECR_PLAN_OWNER_NAME", "Link_TomaBIM_011").strip()
    if not source or not os.path.isfile(source):
        raise RuntimeError("ECR_PLAN_OWNER_SOURCE must identify an existing FCStd")
    before = set(App.listDocuments())
    doc = App.openDocument(source)
    try:
        owner = doc.getObject(owner_name)
        if owner is None:
            raise RuntimeError("Owner not found: " + owner_name)
        plan_name = str(getattr(owner, "DocumentationRepresentationName", "") or "")
        plan = doc.getObject(plan_name)
        if plan is None:
            raise RuntimeError("PLAN not found from DocumentationRepresentationName")
        doc.recompute()
        result = {
            "freecad": ".".join(App.Version()[:3]),
            "document": doc.Label,
            "object_count": len(doc.Objects),
            "owner": {
                "name": owner.Name,
                "type_id": owner.TypeId,
                "contract": str(getattr(owner, "RepresentationContract", "")),
                "uid": str(getattr(owner, "ElementUID", "")),
                "placement": _placement(owner),
                "global_placement": _global_placement(owner),
                "out_list": [obj.Name for obj in owner.OutList],
                "in_list": [obj.Name for obj in owner.InList],
            },
            "plan": {
                "name": plan.Name,
                "type_id": plan.TypeId,
                "owner": getattr(getattr(plan, "Owner", None), "Name", ""),
                "placement": _placement(plan),
                "expression_engine": [(str(path), str(value)) for path, value in plan.ExpressionEngine],
                "signature": str(getattr(plan, "RepresentationSignature", "")),
                "state": [str(item) for item in plan.State],
                "out_list": [obj.Name for obj in plan.OutList],
                "in_list": [obj.Name for obj in plan.InList],
            },
        }
        a1_devices = [
            obj for obj in doc.Objects
            if str(getattr(obj, "RepresentationContract", "")) == "PhysicalDocumentationA1"
            and obj.TypeId == "App::Link"
        ]
        result["a1_summary"] = {
            "count": len(a1_devices),
            "outlets": [
                obj.Name for obj in a1_devices
                if str(getattr(obj, "Tipo", "")) == "Toma"
            ][:10],
            "switches": [
                obj.Name for obj in a1_devices
                if str(getattr(obj, "Tipo", "")) == "Apagador"
            ][:10],
        }
        result["delta_xy"] = [
            round(result["owner"]["placement"]["base"][0] - result["plan"]["placement"]["base"][0], 9),
            round(result["owner"]["placement"]["base"][1] - result["plan"]["placement"]["base"][1], 9),
        ]
        print("ECR_CHOMES_PLAN_OWNER_DIAGNOSIS " + json.dumps(result, sort_keys=True))
        return result
    finally:
        App.closeDocument(doc.Name)
        assert set(App.listDocuments()) == before


if __name__ == "__main__":
    run()
