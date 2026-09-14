# -*- coding: utf-8 -*-
"""FreeCAD adapter/orchestrator for the canonical ElectricCR A1 demo.

Purpose:
- Materialize the pure demo specification in a NEW FreeCAD document.
- Reuse native BIM Space/Wall and the approved ElectricCR A1 factory/services.

Main behavior:
- Never mutates the user's active production document.
- Creates a deterministic two-space architectural scaffold and seven A1 devices.
- Uses one outer transaction; failures close the newly-created demo document.

Future modification guidance:
- Keep domain decisions in electric_demo_core.py.
- Reuse ElectricCR/FreeCAD services; do not duplicate A1 creation or RoomResolver logic.
- IFC export belongs to a later adapter phase, not this module's v0.1 contract.

Version: 0.1.1
Date/time: 2026-09-09 23:14 America/Costa_Rica
Target: FreeCAD 1.1.3.
"""

from __future__ import annotations

import math

import FreeCAD as App
import Part
import Arch

from ..features import objeto_toma_uno
from ..semantic import freecad_adapter
from .electric_demo_core import build_fixed_demo_spec


TRANSACTION_NAME = "ElectricCR: crear demo A1"
DEMO_PROPERTY_GROUP = "ElectricCR Demo"


def _text(value):
    try:
        return str(value or "").strip()
    except Exception:
        return ""


def _next_document_name(prefix):
    base = _text(prefix) or "ElectricCR_Demo_A1"
    opened = set(App.listDocuments().keys())
    if base not in opened:
        return base
    index = 2
    while "%s_%03d" % (base, index) in opened:
        index += 1
    return "%s_%03d" % (base, index)


def _add_demo_key(obj, key):
    if obj is None:
        return
    props = set(getattr(obj, "PropertiesList", []) or [])
    if "ECR_DemoKey" not in props:
        obj.addProperty(
            "App::PropertyString",
            "ECR_DemoKey",
            DEMO_PROPERTY_GROUP,
            "Clave estable dentro de la demo canonica ElectricCR",
        )
    obj.ECR_DemoKey = _text(key)


def _add_to_container(container, obj):
    if container is None or obj is None:
        return
    for method_name in ("addObject", "addObjects"):
        method = getattr(container, method_name, None)
        if not callable(method):
            continue
        try:
            if method_name == "addObjects":
                method([obj])
            else:
                method(obj)
            return
        except Exception:
            continue


def _ensure_group(doc, internal_name, label, parent=None):
    group = doc.getObject(internal_name)
    if group is None:
        group = doc.addObject("App::DocumentObjectGroup", internal_name)
    group.Label = label
    _add_demo_key(group, internal_name)
    _add_to_container(parent, group)
    return group


def _create_metadata(doc, spec):
    obj = doc.addObject("App::FeaturePython", "ECR_Demo_Metadata")
    obj.Label = "ElectricCR Demo - Metadata"
    for ptype, name, value in (
        ("App::PropertyString", "ECR_DemoId", spec["demo_id"]),
        ("App::PropertyInteger", "ECR_DemoSchemaVersion", int(spec["schema_version"])),
        ("App::PropertyString", "ECR_DemoGeneratorVersion", "0.1.0"),
    ):
        obj.addProperty(ptype, name, DEMO_PROPERTY_GROUP)
        setattr(obj, name, value)
    _add_demo_key(obj, "metadata")
    return obj


def _create_floor(doc, spec, level):
    item = spec["floor"]
    floor = doc.addObject("Part::Box", "ECR_Demo_Floor")
    floor.Label = item["label"]
    floor.Length = item["length"]
    floor.Width = item["width"]
    floor.Height = item["height"]
    floor.Placement.Base = App.Vector(item["x"], item["y"], item["z"])
    _add_demo_key(floor, item["key"])
    _add_to_container(level, floor)
    return floor


def _create_wall(doc, item, defaults, level):
    key_token = _text(item["key"]).replace("-", "_")
    base = doc.addObject("Part::Feature", "ECR_Demo_WallAxis_%s" % key_token)
    start = item["start"]
    end = item["end"]
    base.Shape = Part.makeLine(
        App.Vector(float(start[0]), float(start[1]), 0.0),
        App.Vector(float(end[0]), float(end[1]), 0.0),
    )
    base.Label = "%s - eje" % item["label"]
    _add_demo_key(base, "%s_axis" % item["key"])
    wall = Arch.makeWall(
        baseobj=base,
        height=float(defaults["height"]),
        width=float(defaults["width"]),
        align=_text(defaults["align"]),
        name=item["label"],
    )
    wall.Label = item["label"]
    _add_demo_key(wall, item["key"])
    _add_to_container(level, wall)
    try:
        base.ViewObject.Visibility = False
    except Exception:
        pass
    return wall


def _create_space(doc, item, level):
    base = doc.addObject("Part::Box", item["base_name"])
    base.Label = "%s - volumen base" % item["label"]
    base.Length = float(item["length"])
    base.Width = float(item["width"])
    base.Height = float(item["height"])
    base.Placement.Base = App.Vector(float(item["x"]), float(item["y"]), float(item["z"]))
    _add_demo_key(base, "%s_base" % item["key"])

    space = Arch.makeSpace(base, name=item["label"])
    space.Label = item["label"]
    _add_demo_key(space, item["key"])
    if hasattr(space, "LongName"):
        try:
            space.LongName = item["label"]
        except Exception:
            pass
    _add_to_container(level, space)
    try:
        space.ViewObject.DisplayMode = "Wireframe"
    except Exception:
        pass
    try:
        space.ViewObject.Transparency = 85
    except Exception:
        pass
    return space


def _rotation_z(yaw_deg):
    return App.Rotation(App.Vector(0.0, 0.0, 1.0), float(yaw_deg))


def _preflight_registry_resources(spec):
    """Fail before document creation if the canonical demo would use fallback cubes."""
    missing = []
    registry = getattr(objeto_toma_uno, "REGISTRY", {}) or {}
    types = registry.get("types", {}) or {}
    resolver = getattr(objeto_toma_uno, "_find_resource", None)
    if not callable(resolver):
        raise RuntimeError("ElectricCR no expone el resolver interno de recursos requerido por la demo")
    for key in sorted({item["key_registro"] for item in spec["devices"]}):
        entry = types.get(key) or {}
        if not entry:
            missing.append("registro:%s" % key)
            continue
        for field, kind in (("symbol2D", "2d"), ("model3D", "3d")):
            resource = _text(entry.get(field, ""))
            if not resource:
                missing.append("%s:%s:vacio" % (key, field))
                continue
            if not resolver(resource, kind):
                missing.append("%s:%s:%s" % (key, field, resource))
    if missing:
        raise RuntimeError("Recursos demo faltantes; no usar cubos fallback: %s" % ", ".join(missing))
    return {"status": "PASS", "checked_type_keys": sorted({item["key_registro"] for item in spec["devices"]})}


def _create_device(doc, item, target_group, host):
    placement = App.Placement(
        App.Vector(
            float(item["placement"]["x"]),
            float(item["placement"]["y"]),
            float(item["placement"]["z"]),
        ),
        _rotation_z(item["placement"]["yaw_deg"]),
    )
    owner = objeto_toma_uno.crear_toma_link(
        doc=doc,
        name_prefix=item["label"],
        key_registro=item["key_registro"],
        tipo_logico=item["tipo_logico"],
        placement=placement,
        modo_visual=item["modo_visual"],
        altura_rel=float(item["altura_rel"]),
        orientacion_pared=item["orientacion_pared"],
        internal_name=item["internal_name"],
        recompute=False,
        target_group=target_group,
        hide_master=True,
        separate_documentation=True,
    )

    # Reuse the existing semantic adapter. The injected factory makes the demo
    # reproducible while preserving the production rule that ElementUID lives
    # on the Owner, never on PLAN/master.
    uid_value = item["element_uid"]
    semantic = freecad_adapter.ensure_device_semantics(
        owner,
        dry_run=False,
        uid_factory=lambda value=uid_value: value,
        host=host,
        manage_transaction=False,
    )
    if _text(getattr(owner, "ElementUID", "")) != uid_value:
        raise RuntimeError("ElementUID demo inesperado en %s" % owner.Name)

    if "CircuitoID" not in set(getattr(owner, "PropertiesList", []) or []):
        owner.addProperty(
            "App::PropertyString",
            "CircuitoID",
            DEMO_PROPERTY_GROUP,
            "Identificador de circuito de demostracion; no constituye objeto Circuit",
        )
    owner.CircuitoID = item["circuit_id"]

    return owner, semantic


def create_validated_scaffold(spec=None):
    """Create only the manually validated architectural scaffold through five walls.

    This regression stage deliberately stops before Arch Spaces and A1 devices.
    It reuses the same helpers as ``create_fixed_demo`` so the test exercises the
    production demo path instead of a parallel hand-built implementation.
    """
    data = spec or build_fixed_demo_spec()
    doc_name = _next_document_name("ElectricCR_Demo_A1_Scaffold")
    doc = App.newDocument(doc_name)
    doc.Label = "ElectricCR Demo A1 - Prueba arquitectura"
    try:
        doc.UndoMode = 1
    except Exception:
        pass

    created = {
        "document": doc,
        "metadata": None,
        "building": None,
        "level": None,
        "floor": None,
        "walls": {},
        "spec": data,
    }

    doc.openTransaction("ElectricCR: prueba demo A1 hasta muros")
    try:
        created["metadata"] = _create_metadata(doc, data)

        building = Arch.makeBuilding(name=data["building"]["label"])
        building.Label = data["building"]["label"]
        _add_demo_key(building, data["building"]["key"])
        created["building"] = building

        level = Arch.makeFloor(name=data["level"]["label"])
        level.Label = data["level"]["label"]
        try:
            level.Placement.Base.z = float(data["level"]["elevation_mm"])
        except Exception:
            pass
        _add_demo_key(level, data["level"]["key"])
        _add_to_container(building, level)
        created["level"] = level

        created["floor"] = _create_floor(doc, data, level)

        for wall_spec in data["walls"]:
            wall = _create_wall(doc, wall_spec, data["wall_defaults"], level)
            created["walls"][wall_spec["key"]] = wall

        doc.recompute()
        doc.commitTransaction()
    except Exception:
        try:
            doc.abortTransaction()
        except Exception:
            pass
        name = doc.Name
        try:
            App.closeDocument(name)
        except Exception:
            pass
        raise

    App.Console.PrintMessage(
        "[ElectricCR][Demo] scaffold validado creado %s: losa + %d muros; se detiene antes de Spaces/A1.\n"
        % (doc.Label, len(created["walls"]))
    )
    return created


def create_fixed_demo(spec=None):
    """Create the canonical demo in a new document and return created objects.

    This function never writes into the previously active document.
    """
    data = spec or build_fixed_demo_spec()
    preflight = _preflight_registry_resources(data)
    doc_name = _next_document_name(data["document"]["name_prefix"])
    doc = App.newDocument(doc_name)
    doc.Label = data["document"]["label"]
    try:
        doc.UndoMode = 1
    except Exception:
        pass

    created = {
        "document": doc,
        "metadata": None,
        "building": None,
        "level": None,
        "floor": None,
        "spaces": {},
        "walls": {},
        "owners": {},
        "semantic_results": {},
        "resource_preflight": preflight,
        "spec": data,
    }

    doc.openTransaction(TRANSACTION_NAME)
    try:
        created["metadata"] = _create_metadata(doc, data)

        building = Arch.makeBuilding(name=data["building"]["label"])
        building.Label = data["building"]["label"]
        _add_demo_key(building, data["building"]["key"])
        created["building"] = building

        level = Arch.makeFloor(name=data["level"]["label"])
        level.Label = data["level"]["label"]
        try:
            level.Placement.Base.z = float(data["level"]["elevation_mm"])
        except Exception:
            pass
        _add_demo_key(level, data["level"]["key"])
        _add_to_container(building, level)
        created["level"] = level

        created["floor"] = _create_floor(doc, data, level)

        for wall_spec in data["walls"]:
            wall = _create_wall(doc, wall_spec, data["wall_defaults"], level)
            created["walls"][wall_spec["key"]] = wall

        for space_spec in data["spaces"]:
            space = _create_space(doc, space_spec, level)
            created["spaces"][space_spec["key"]] = space

        # Give Arch objects a valid Shape before RoomResolver is asked to resolve
        # device points.
        doc.recompute()

        electric_root = _ensure_group(doc, "electrico", "electrico")
        demo_root = _ensure_group(doc, "ECR_Demo_Devices", "Demo ElectricCR A1", electric_root)
        type_groups = {
            "Toma": _ensure_group(doc, "ECR_Demo_Outlets", "Tomacorrientes", demo_root),
            "Apagador": _ensure_group(doc, "ECR_Demo_Switches", "Apagadores", demo_root),
            "Luminaria": _ensure_group(doc, "ECR_Demo_Lights", "Luminarias", demo_root),
            "Sensor": _ensure_group(doc, "ECR_Demo_Sensors", "Sensores", demo_root),
        }

        for device_spec in data["devices"]:
            host = created["walls"].get(device_spec["host_key"])
            owner, semantic = _create_device(
                doc,
                device_spec,
                type_groups.get(device_spec["tipo_logico"], demo_root),
                host,
            )
            created["owners"][device_spec["id"]] = owner
            created["semantic_results"][device_spec["id"]] = semantic

        # Physical masters are now available. Materialize all PLANs explicitly
        # inside the same outer transaction and then perform one final recompute.
        for device_spec in data["devices"]:
            owner = created["owners"][device_spec["id"]]
            objeto_toma_uno.sync_plan_representation(
                owner,
                dry_run=False,
                manage_transaction=False,
            )

        doc.recompute()
        doc.commitTransaction()
    except Exception:
        try:
            doc.abortTransaction()
        except Exception:
            pass
        name = doc.Name
        try:
            App.closeDocument(name)
        except Exception:
            pass
        raise

    App.Console.PrintMessage(
        "[ElectricCR][Demo] creada %s: %d espacios, %d dispositivos A1.\n"
        % (doc.Label, len(created["spaces"]), len(created["owners"]))
    )
    return created


__all__ = ["TRANSACTION_NAME", "create_fixed_demo", "create_validated_scaffold"]
