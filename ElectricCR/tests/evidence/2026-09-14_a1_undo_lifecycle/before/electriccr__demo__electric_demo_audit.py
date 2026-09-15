# -*- coding: utf-8 -*-
"""Read-only audit for the canonical ElectricCR A1 demo.

Purpose:
- Verify that a generated demo still satisfies the approved A1 contract.
- Return JSON-compatible evidence without modifying or recomputing the document.

Main behavior:
- Resolves demo objects by stable demo keys / deterministic ElementUID values.
- Checks Owner/PLAN 1:1, master, Placement, Space, Host, schema and orphan state.

Future modification guidance:
- Keep this module read-only by default.
- Add new checks when the demo scope grows; never repair from the auditor.

Version: 0.1.0
Date/time: 2026-09-09 22:09 America/Costa_Rica
Target: FreeCAD 1.1.3.
"""

from __future__ import annotations

import math

from ..features import objeto_toma_uno
from .electric_demo_core import build_fixed_demo_spec


TOL_MM = 1.0e-5
TOL_ROT = 1.0e-8


def _text(value):
    try:
        return str(value or "").strip()
    except Exception:
        return ""


def _props(obj):
    return set(getattr(obj, "PropertiesList", []) or []) if obj is not None else set()


def _demo_key(obj):
    return _text(getattr(obj, "ECR_DemoKey", "")) if "ECR_DemoKey" in _props(obj) else ""


def _rotation_close(a, b):
    try:
        qa = tuple(float(v) for v in a.Q)
        qb = tuple(float(v) for v in b.Q)
    except Exception:
        return False
    direct = max(abs(x - y) for x, y in zip(qa, qb))
    negated = max(abs(x + y) for x, y in zip(qa, qb))
    return min(direct, negated) <= TOL_ROT


def _rotation_matches_yaw(rotation, yaw_deg):
    try:
        q = tuple(float(v) for v in rotation.Q)
        half = math.radians(float(yaw_deg)) * 0.5
        expected = (0.0, 0.0, math.sin(half), math.cos(half))
    except Exception:
        return False
    direct = max(abs(x - y) for x, y in zip(q, expected))
    negated = max(abs(x + y) for x, y in zip(q, expected))
    return min(direct, negated) <= TOL_ROT


def _placement_payload(obj):
    p = obj.Placement
    return {
        "x": float(p.Base.x),
        "y": float(p.Base.y),
        "z": float(p.Base.z),
        "q": [float(v) for v in p.Rotation.Q],
    }


def _find_by_demo_key(doc, key):
    return [obj for obj in list(doc.Objects or []) if _demo_key(obj) == key]


def _find_owner_by_uid(doc, uid):
    result = []
    for obj in list(doc.Objects or []):
        if "ElementUID" in _props(obj) and _text(getattr(obj, "ElementUID", "")) == uid:
            result.append(obj)
    return result


def _plan_candidates(doc):
    result = []
    for obj in list(doc.Objects or []):
        if _text(getattr(obj, "RepresentationRole", "")) == objeto_toma_uno.REPRESENTATION_ROLE_PLAN:
            result.append(obj)
    return result


def _check(checks, code, ok, message, severity="ERROR", data=None):
    checks.append(
        {
            "code": code,
            "status": "PASS" if ok else severity,
            "message": message,
            "data": data or {},
        }
    )
    return bool(ok)


def audit_demo(doc, spec=None):
    """Audit *doc* without writing properties, recomputing or repairing it."""
    data = spec or build_fixed_demo_spec()
    checks = []
    devices = []

    metadata = doc.getObject("ECR_Demo_Metadata")
    _check(
        checks,
        "DEMO_ID",
        metadata is not None and _text(getattr(metadata, "ECR_DemoId", "")) == data["demo_id"],
        "Documento identificado como demo canonica ElectricCR.",
    )

    space_by_key = {}
    for space_spec in data["spaces"]:
        matches = _find_by_demo_key(doc, space_spec["key"])
        ok = len(matches) == 1
        _check(
            checks,
            "SPACE_%s" % space_spec["key"].upper(),
            ok,
            "Space %s unico." % space_spec["label"],
            data={"matches": [obj.Name for obj in matches]},
        )
        if ok:
            space_by_key[space_spec["key"]] = matches[0]

    wall_by_key = {}
    for wall_spec in data["walls"]:
        matches = _find_by_demo_key(doc, wall_spec["key"])
        ok = len(matches) == 1
        _check(
            checks,
            "WALL_%s" % wall_spec["key"].upper(),
            ok,
            "Host %s unico." % wall_spec["label"],
            data={"matches": [obj.Name for obj in matches]},
        )
        if ok:
            wall_by_key[wall_spec["key"]] = matches[0]

    seen_uids = set()
    seen_plan_names = set()
    for device_spec in data["devices"]:
        uid = device_spec["element_uid"]
        matches = _find_owner_by_uid(doc, uid)
        owner_ok = len(matches) == 1
        _check(
            checks,
            "OWNER_%s" % device_spec["id"].upper().replace("-", "_"),
            owner_ok,
            "Owner unico para %s." % device_spec["label"],
            data={"matches": [obj.Name for obj in matches], "uid": uid},
        )
        if not owner_ok:
            continue
        owner = matches[0]
        owner_checks = {
            "type": _text(getattr(owner, "TypeId", "")) == "App::Link",
            "a1": _text(getattr(owner, "RepresentationContract", "")) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1,
            "key": _text(getattr(owner, "KeyRegistro", "")) == device_spec["key_registro"],
            "uid_unique": uid not in seen_uids,
            "master": getattr(owner, "LinkedObject", None) is not None,
        }
        seen_uids.add(uid)
        master = getattr(owner, "LinkedObject", None)
        try:
            owner_checks["master_shape"] = bool(master and hasattr(master, "Shape") and not master.Shape.isNull())
        except Exception:
            owner_checks["master_shape"] = False

        expected_space = space_by_key.get(device_spec["space_key"])
        current_space = getattr(owner, "Space", None)
        owner_checks["space"] = bool(
            expected_space is not None
            and current_space is not None
            and _text(getattr(current_space, "Name", "")) == _text(getattr(expected_space, "Name", ""))
        )
        expected_host = wall_by_key.get(device_spec["host_key"]) if device_spec["host_key"] else None
        current_host = getattr(owner, "Host", None)
        if expected_host is None:
            owner_checks["host"] = current_host is None
        else:
            owner_checks["host"] = bool(
                current_host is not None
                and _text(getattr(current_host, "Name", "")) == _text(getattr(expected_host, "Name", ""))
            )

        expected_p = device_spec["placement"]
        p = owner.Placement
        owner_checks["placement_xyz"] = (
            abs(float(p.Base.x) - float(expected_p["x"])) <= TOL_MM
            and abs(float(p.Base.y) - float(expected_p["y"])) <= TOL_MM
            and abs(float(p.Base.z) - float(expected_p["z"])) <= TOL_MM
        )
        owner_checks["placement_rotation"] = _rotation_matches_yaw(
            owner.Placement.Rotation, device_spec["placement"]["yaw_deg"]
        )
        owner_checks["circuit"] = _text(getattr(owner, "CircuitoID", "")) == device_spec["circuit_id"]

        plan_name = _text(getattr(owner, "DocumentationRepresentationName", ""))
        plan = doc.getObject(plan_name) if plan_name else None
        plan_ok = plan is not None
        owner_checks["plan_exists"] = plan_ok
        if plan is not None:
            owner_checks["plan_unique_name"] = plan_name not in seen_plan_names
            seen_plan_names.add(plan_name)
            owner_checks["plan_role"] = _text(getattr(plan, "RepresentationRole", "")) == objeto_toma_uno.REPRESENTATION_ROLE_PLAN
            owner_checks["plan_schema"] = int(getattr(plan, "RepresentationSchemaVersion", 0)) == int(objeto_toma_uno.REPRESENTATION_SCHEMA_VERSION)
            owner_checks["plan_documentation_only"] = bool(getattr(plan, "DocumentationOnly", False))
            plan_owner = getattr(plan, "Owner", None)
            owner_checks["plan_owner"] = bool(
                plan_owner is not None
                and _text(getattr(plan_owner, "Name", "")) == _text(getattr(owner, "Name", ""))
            )
            owner_checks["plan_xy"] = (
                abs(float(plan.Placement.Base.x) - float(owner.Placement.Base.x)) <= TOL_MM
                and abs(float(plan.Placement.Base.y) - float(owner.Placement.Base.y)) <= TOL_MM
            )
            owner_checks["plan_z"] = abs(
                float(plan.Placement.Base.z) - float(getattr(owner, "DocumentationPlaneZ", 0.0))
            ) <= TOL_MM
            owner_checks["plan_rotation"] = _rotation_close(plan.Placement.Rotation, owner.Placement.Rotation)
            snaps = list(getattr(plan, "SnapPoints", []) or [])
            owner_checks["snap_origin"] = bool(
                snaps
                and abs(float(snaps[0].x)) <= TOL_MM
                and abs(float(snaps[0].y)) <= TOL_MM
                and abs(float(snaps[0].z)) <= TOL_MM
            )
        else:
            owner_checks["plan_unique_name"] = False
            owner_checks["plan_role"] = False
            owner_checks["plan_schema"] = False
            owner_checks["plan_documentation_only"] = False
            owner_checks["plan_owner"] = False
            owner_checks["plan_xy"] = False
            owner_checks["plan_z"] = False
            owner_checks["plan_rotation"] = False
            owner_checks["snap_origin"] = False

        all_ok = all(owner_checks.values())
        _check(
            checks,
            "DEVICE_CONTRACT_%s" % device_spec["id"].upper().replace("-", "_"),
            all_ok,
            "Contrato A1 de %s." % device_spec["label"],
            data=owner_checks,
        )
        devices.append(
            {
                "id": device_spec["id"],
                "owner_name": owner.Name,
                "owner_label": owner.Label,
                "uid": uid,
                "plan_name": plan_name,
                "space_name": _text(getattr(getattr(owner, "Space", None), "Name", "")),
                "host_name": _text(getattr(getattr(owner, "Host", None), "Name", "")),
                "placement": _placement_payload(owner),
                "checks": owner_checks,
            }
        )

    plans = _plan_candidates(doc)
    orphan_plans = [plan.Name for plan in plans if getattr(plan, "Owner", None) is None]
    _check(checks, "NO_ORPHAN_PLAN", not orphan_plans, "No existen PLAN huerfanos.", data={"orphans": orphan_plans})

    a1_owners = [
        obj for obj in list(doc.Objects or [])
        if _text(getattr(obj, "RepresentationContract", "")) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1
        and _text(getattr(obj, "TypeId", "")) == "App::Link"
    ]
    expected = data["expected"]
    counts = {
        "spaces": len([obj for obj in list(doc.Objects or []) if _demo_key(obj) in {s["key"] for s in data["spaces"]}]),
        "walls": len([obj for obj in list(doc.Objects or []) if _demo_key(obj) in {w["key"] for w in data["walls"]}]),
        "owners": len(a1_owners),
        "plans": len(plans),
        "physical_masters": len({getattr(obj, "LinkedObject", None).Name for obj in a1_owners if getattr(obj, "LinkedObject", None)}),
    }
    _check(checks, "EXPECTED_COUNTS", counts == expected, "Conteos canonicos de la demo.", data={"actual": counts, "expected": expected})

    errors = [item for item in checks if item["status"] == "ERROR"]
    warnings = [item for item in checks if item["status"] == "WARN"]
    return {
        "demo_id": data["demo_id"],
        "document_name": doc.Name,
        "document_label": doc.Label,
        "status": "PASS" if not errors else "FAIL",
        "read_only": True,
        "counts": counts,
        "checks": checks,
        "devices": devices,
        "errors": len(errors),
        "warnings": len(warnings),
    }


def format_console_summary(report):
    return (
        "[ElectricCR][Demo Audit] status=%s owners=%d plans=%d spaces=%d walls=%d errors=%d warnings=%d"
        % (
            report["status"],
            report["counts"].get("owners", 0),
            report["counts"].get("plans", 0),
            report["counts"].get("spaces", 0),
            report["counts"].get("walls", 0),
            report["errors"],
            report["warnings"],
        )
    )


__all__ = ["audit_demo", "format_console_summary"]
