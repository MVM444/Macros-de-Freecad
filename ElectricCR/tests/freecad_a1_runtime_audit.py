"""Read-only ElectricCR A1 Owner/PLAN runtime audit.

Revision: 2026-09-08. Target: FreeCAD 1.1.3.
Adapted from the current-model diagnostic prepared for the A1 audit.

Call ``audit(document)`` in FreeCAD with an already open document. Import and
audit never open, save, recompute, repair, select, or change document objects.
The caller must perform any requested recompute on a verified temporary copy
before calling this helper; reported error states describe that existing state.
No model location or output location is assumed and no files are written.
Native expression evaluation can mark Link dependencies Touched in FreeCAD 1.1.3;
this transient state is reported separately from Invalid/Error and stored values.
"""

from collections import defaultdict
from datetime import datetime, timezone

import FreeCAD as App


CONTRACT = "PhysicalDocumentationA1"
CANONICAL_PLACEMENT_EXPRESSION = (
    "placement(vector(Owner.Placement.Base.x; Owner.Placement.Base.y; "
    "Owner.DocumentationPlaneZ); Owner.Placement.Rotation)"
)


def placement_data(placement):
    return {
        "base": list(placement.Base),
        "rotation_q": list(placement.Rotation.Q),
    }


def follows(owner, plan):
    """Compare actual placements without forcing expression recomputation."""
    physical, documentation = owner.Placement, plan.Placement
    return (
        abs(physical.Base.x - documentation.Base.x) < 1e-6
        and abs(physical.Base.y - documentation.Base.y) < 1e-6
        and abs(documentation.Base.z - float(owner.DocumentationPlaneZ)) < 1e-6
        and physical.Rotation.isSame(documentation.Rotation, 1e-9)
    )


def _normalize_expression(expression):
    # FreeCAD may serialize relative property paths with a leading dot.
    return "".join(str(expression).split()).replace(".Owner.", "Owner.")


def _reference(obj):
    if obj is None:
        return None
    return {
        "name": obj.Name,
        "document": getattr(getattr(obj, "Document", None), "Name", None),
        "TypeId": obj.TypeId,
    }


def _context(obj, objects):
    return {
        "PropertiesList": list(obj.PropertiesList),
        "InList": [_reference(item) for item in obj.InList],
        "OutList": [_reference(item) for item in obj.OutList],
        "groups": [
            group.Name for group in objects
            if "Group" in group.PropertiesList and obj in group.Group
        ],
        "State": list(obj.State),
        "status": obj.getStatusString(),
    }


def audit(doc):
    """Return a JSON-compatible inventory and explicit A1 inconsistencies."""
    errors, owners, plans = [], [], []
    uid_names, claims, owner_plans = defaultdict(list), defaultdict(list), defaultdict(list)
    objects = list(doc.Objects)
    names = {obj.Name: obj for obj in objects}

    def err(kind, name, detail):
        errors.append({"kind": kind, "object": name, "detail": str(detail)})

    # A1 masters also declare RepresentationContract, but are not placed Owners.
    # Include App::Link instances and objects carrying their own identity/claim;
    # this also exposes malformed Owners whose TypeId was changed.
    candidates = [
        obj for obj in objects
        if str(getattr(obj, "RepresentationContract", "")) == CONTRACT
        and (
            obj.TypeId == "App::Link"
            or "ElementUID" in obj.PropertiesList
            or "DocumentationRepresentationName" in obj.PropertiesList
        )
    ]
    plan_objects = [
        obj for obj in objects
        if str(getattr(obj, "RepresentationRole", "")) == "PLAN"
        or obj.Name.startswith("ECR_DocPlan_")
        or (
            bool(getattr(obj, "DocumentationOnly", False))
            and not str(getattr(obj, "RepresentationRole", ""))
        )
    ]
    owner_names = {obj.Name for obj in candidates}
    plan_names = {obj.Name for obj in plan_objects}

    for owner in candidates:
        row = {
            "name": owner.Name, "label": owner.Label, "TypeId": owner.TypeId,
            "RepresentationContract": str(getattr(owner, "RepresentationContract", "")),
        }
        try:
            row.update(_context(owner, objects))
            uid = str(getattr(owner, "ElementUID", "") or "").strip()
            claim = str(getattr(owner, "DocumentationRepresentationName", "") or "").strip()
            row.update(
                ElementUID=uid, DocumentationRepresentationName=claim,
                Placement=placement_data(owner.Placement),
                DocumentationPlaneZ=float(owner.DocumentationPlaneZ),
            )
            if owner.TypeId != "App::Link":
                err("owner_type", owner.Name, owner.TypeId)
            if not uid:
                err("empty_uid", owner.Name, "ElementUID empty/missing")
            else:
                uid_names[uid].append(owner.Name)
            if not claim or claim not in names:
                err("owner_without_plan", owner.Name, claim or "empty name")
            elif claim not in plan_names:
                err("owner_claims_non_plan", owner.Name, claim)
            if claim:
                claims[claim].append(owner.Name)
            master = getattr(owner, "LinkedObject", None)
            row["master"] = _reference(master)
            if (
                master is None or getattr(master, "Document", None) is None
                or master.Document.getObject(master.Name) is not master
            ):
                err("invalid_master", owner.Name, row["master"])
            elif not hasattr(master, "Shape") or master.Shape.isNull():
                err("invalid_master_shape", owner.Name, master.Name)
            if claim in names and getattr(names[claim], "Owner", None) is not owner:
                err("crossed_owner_plan", owner.Name, claim)
        except Exception as exc:
            err("owner_read_failure", owner.Name, repr(exc))
        owners.append(row)

    for plan in plan_objects:
        row = {"name": plan.Name, "label": plan.Label, "TypeId": plan.TypeId}
        try:
            row.update(_context(plan, objects))
            role = str(getattr(plan, "RepresentationRole", ""))
            schema = getattr(plan, "RepresentationSchemaVersion", None)
            only = getattr(plan, "DocumentationOnly", None)
            row.update(
                RepresentationRole=role, RepresentationSchemaVersion=schema,
                DocumentationOnly=only, Placement=placement_data(plan.Placement),
                ExpressionEngine=[(str(key), str(value)) for key, value in plan.ExpressionEngine],
                ShowInTree=plan.ViewObject.ShowInTree,
            )
            if plan.TypeId != "Part::Feature":
                err("plan_type", plan.Name, plan.TypeId)
            if role != "PLAN":
                err("plan_role", plan.Name, role)
            if schema != 2:
                err("plan_schema", plan.Name, schema)
            if only is not True:
                err("documentation_only", plan.Name, only)
            if "ElementUID" in plan.PropertiesList:
                err("second_identity", plan.Name, "PLAN carries ElementUID")
            if row["ShowInTree"]:
                err("plan_in_tree", plan.Name, "ShowInTree=True")
            if row["groups"]:
                err("plan_in_groups", plan.Name, row["groups"])
            owner = getattr(plan, "Owner", None)
            row["Owner"] = getattr(owner, "Name", None)
            row["OwnerReference"] = _reference(owner)
            row["OwnerPropertyType"] = (
                plan.getTypeIdOfProperty("Owner") if "Owner" in plan.PropertiesList else None
            )
            if row["OwnerPropertyType"] != "App::PropertyLinkHidden":
                err("owner_property_type", plan.Name, row["OwnerPropertyType"])
            if owner is None or owner.Document is not doc or names.get(owner.Name) is not owner:
                err("orphan_plan", plan.Name, row["OwnerReference"])
            else:
                owner_plans[owner.Name].append(plan.Name)
                if owner.Name not in owner_names:
                    err("invalid_plan_owner", plan.Name, owner.Name)
                if str(getattr(owner, "DocumentationRepresentationName", "")) != plan.Name:
                    err("crossed_plan_owner", plan.Name, owner.Name)
                if not follows(owner, plan):
                    err("plan_not_following", plan.Name, owner.Name)
            snaps = list(getattr(plan, "SnapPoints", []))
            row["SnapPoints"] = [list(vector) for vector in snaps]
            if len(snaps) != 1 or snaps[0].Length > 1e-9:
                err("insertion_snap", plan.Name, row["SnapPoints"])
            bindings = [
                (key, value) for key, value in row["ExpressionEngine"]
                if key.lstrip(".") == "Placement"
            ]
            components = [
                key for key, _ in row["ExpressionEngine"]
                if key.lstrip(".").startswith("Placement.")
            ]
            if components:
                err("placement_component_expressions", plan.Name, components)
            if len(bindings) != 1:
                err("placement_expression", plan.Name, bindings)
            else:
                expression = bindings[0][1]
                if _normalize_expression(expression) != _normalize_expression(CANONICAL_PLACEMENT_EXPRESSION):
                    err("noncanonical_placement_expression", plan.Name, expression)
                value = plan.evalExpression(expression)
                row["evaluatedPlacement"] = placement_data(value)
                if (
                    (value.Base - plan.Placement.Base).Length > 1e-6
                    or not value.Rotation.isSame(plan.Placement.Rotation, 1e-9)
                ):
                    err("expression_value_mismatch", plan.Name, bindings[0])
        except Exception as exc:
            err("plan_read_or_expression_failure", plan.Name, repr(exc))
        plans.append(row)

    for uid, matching_names in uid_names.items():
        if len(matching_names) > 1:
            err("duplicate_uid", ",".join(matching_names), uid)
    for name, matching_names in claims.items():
        if len(matching_names) > 1:
            err("multiply_claimed_plan", name, matching_names)
    for owner_name, matching_names in owner_plans.items():
        if len(matching_names) > 1:
            err("duplicate_plan_for_owner", owner_name, matching_names)
    for owner_name in sorted(owner_names):
        if not owner_plans[owner_name]:
            err("owner_without_linked_plan", owner_name, "no PLAN.Owner references this identity")

    # Read existing native status after the caller's recompute. Touched alone
    # means recompute is pending, not that recompute failed.
    document_error_objects, touched_objects = [], []
    for obj in objects:
        try:
            state = list(obj.State)
            if "Touched" in state:
                touched_objects.append(obj.Name)
            if any(str(item).lower() in ("invalid", "error") for item in state):
                item = {"name": obj.Name, "State": state, "status": obj.getStatusString()}
                document_error_objects.append(item)
                err("document_error_state", obj.Name, item)
        except Exception as exc:
            err("document_status_read_failure", obj.Name, repr(exc))

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "freecad": ".".join(str(item) for item in App.Version()[:3]),
        "document": doc.Name, "file": doc.FileName, "object_count": len(objects),
        "owner_count": len(owners), "plan_count": len(plans),
        "owners": owners, "plans": plans,
        "recompute_performed": False, "touched_objects": touched_objects,
        "document_error_objects": document_error_objects,
        "errors": errors, "ok": not errors,
    }
