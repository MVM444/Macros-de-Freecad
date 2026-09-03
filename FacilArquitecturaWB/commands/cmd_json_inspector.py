"""Interfaz JSON bidireccional para Facil Arquitectura.

Nombre: cmd_json_inspector.py
Proposito: exponer junto a FA Demo edificio una salida JSON reproducible y una
entrada JSON controlada para pruebas, diagnostico e integracion con ChatGPT/MCP.
Funcion principal: snapshot FA -> JSON y comando JSON -> validar -> dry-run -> aplicar.
Instrucciones relevantes para futuras modificaciones:
- La salida debe permanecer estrictamente read-only.
- La entrada solo admite operaciones declarativas del schema versionado; nunca
  ejecutar Python arbitrario recibido en JSON.
- Toda escritura debe pasar por validacion, dry-run y transacciones FreeCAD.
- Reutilizar ElementDataCore y los adaptadores existentes para puertas/ventanas.
- No serializar Shape, Geometry, Constraints ni mallas completas; usar resumenes.
- Mantener la logica pura en core/json_snapshot_core.py y json_command_core.py.
- El controlador FA_DemoBuilding es la fuente autoritativa de SpecificationJSON
  y StepPlanJSON cuando el documento proviene de la Demo.
Version: 0.3.0
Fecha y hora: 2026-09-02 17:18 America/Costa_Rica
"""

from __future__ import annotations

import json
import os

import FreeCAD as App
import FreeCADGui
import Part
from PySide import QtGui, QtWidgets

from .. import i18n
from ..core.command_errors import handle_command_exception
from ..core.constants import BUILD_ID, VERSION
from ..core.door_table_utils import apply_door_records, extract_door_records
from ..core.element_data_core import CATEGORY_DOORS, CATEGORY_WINDOWS, SCHEMA_VERSION as ELEMENT_SCHEMA_VERSION
from ..core.json_command_core import dumps_command, example_command, parse_command_text, validate_command
from ..core.json_snapshot_core import build_snapshot, dumps_snapshot
from ..core.opening_utils import is_bim_wall
from ..core.reloadable_command import ReloadableCommandProxy
from ..core.window_table_utils import apply_window_records, extract_window_records


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "json_inspector.svg")
).replace(os.sep, "/")
LOG = "[FA JSON] "

_HEAVY_PROPERTIES = {
    "Shape",
    "Geometry",
    "GeometryCount",
    "Constraints",
    "ExpressionEngine",
    "Mesh",
    "Proxy",
}


def _log(text):
    App.Console.PrintMessage(LOG + str(text) + "\n")


def _object_ref(value):
    if value is None:
        return None
    name = getattr(value, "Name", None)
    if name is not None:
        return {
            "name": str(name),
            "label": str(getattr(value, "Label", name) or name),
            "type_id": str(getattr(value, "TypeId", "") or ""),
        }
    return None


def _quantity_value(value):
    try:
        unit = str(getattr(value, "Unit", "") or "")
        numeric = float(value.Value)
    except Exception:
        return None
    result = {"value": numeric}
    if unit:
        result["unit"] = unit
    return result


def _vector_value(value):
    if not all(hasattr(value, axis) for axis in ("x", "y", "z")):
        return None
    try:
        return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}
    except Exception:
        return None


def _rotation_value(value):
    try:
        quat = value.Q
        return {"quaternion": [float(item) for item in quat]}
    except Exception:
        return None


def _placement_value(value):
    base = getattr(value, "Base", None)
    rotation = getattr(value, "Rotation", None)
    if base is None or rotation is None:
        return None
    base_data = _vector_value(base)
    rotation_data = _rotation_value(rotation)
    if base_data is None and rotation_data is None:
        return None
    return {"base": base_data, "rotation": rotation_data}


def _value_to_json(value, depth=0):
    if depth > 4:
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    ref = _object_ref(value)
    if ref is not None:
        return {"$ref": ref["name"], "label": ref["label"], "type_id": ref["type_id"]}
    quantity = _quantity_value(value)
    if quantity is not None:
        return quantity
    placement = _placement_value(value)
    if placement is not None:
        return placement
    vector = _vector_value(value)
    if vector is not None:
        return vector
    if isinstance(value, dict):
        return {str(key): _value_to_json(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        data = list(value)
        limit = 200
        result = [_value_to_json(item, depth + 1) for item in data[:limit]]
        if len(data) > limit:
            result.append({"_truncated": len(data) - limit})
        return result
    try:
        return str(value)
    except Exception:
        return "<unserializable>"


def _shape_summary(obj):
    try:
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull():
            return None
        bbox = shape.BoundBox
        return {
            "solids": int(len(getattr(shape, "Solids", []) or [])),
            "faces": int(len(getattr(shape, "Faces", []) or [])),
            "edges": int(len(getattr(shape, "Edges", []) or [])),
            "volume": float(getattr(shape, "Volume", 0.0) or 0.0),
            "area": float(getattr(shape, "Area", 0.0) or 0.0),
            "bbox": {
                "min": {"x": float(bbox.XMin), "y": float(bbox.YMin), "z": float(bbox.ZMin)},
                "max": {"x": float(bbox.XMax), "y": float(bbox.YMax), "z": float(bbox.ZMax)},
                "size": {"x": float(bbox.XLength), "y": float(bbox.YLength), "z": float(bbox.ZLength)},
            },
        }
    except Exception:
        return None


def _property_payload(obj):
    payload = {}
    for name in list(getattr(obj, "PropertiesList", []) or []):
        name = str(name)
        if name in _HEAVY_PROPERTIES:
            continue
        try:
            type_id = str(obj.getTypeIdOfProperty(name) or "")
        except Exception:
            type_id = ""
        # Avoid serializing large opaque Python/complex property containers.
        if type_id in ("App::PropertyPythonObject", "App::PropertyMatrix"):
            continue
        try:
            value = getattr(obj, name)
            converted = _value_to_json(value)
        except Exception as exc:
            converted = {"_error": str(exc)}
        payload[name] = {"type": type_id, "value": converted}
    return payload


def _object_payload(obj):
    row = {
        "name": str(getattr(obj, "Name", "") or ""),
        "label": str(getattr(obj, "Label", "") or ""),
        "type_id": str(getattr(obj, "TypeId", "") or ""),
        "parents": [str(item.Name) for item in list(getattr(obj, "InList", []) or []) if getattr(item, "Name", None)],
        "children": [str(item.Name) for item in list(getattr(obj, "OutList", []) or []) if getattr(item, "Name", None)],
        "properties": _property_payload(obj),
    }
    placement = _placement_value(getattr(obj, "Placement", None))
    if placement is not None:
        row["placement"] = placement
    shape = _shape_summary(obj)
    if shape is not None:
        row["shape"] = shape
    try:
        row["visibility"] = bool(obj.ViewObject.Visibility)
    except Exception:
        pass
    try:
        if str(getattr(obj, "TypeId", "")) == "Sketcher::SketchObject":
            row["sketch"] = {
                "geometry_count": int(getattr(obj, "GeometryCount", 0) or 0),
                "constraint_count": int(len(getattr(obj, "Constraints", []) or [])),
            }
    except Exception:
        pass
    return row


def _parse_json_property(obj, name):
    text = str(getattr(obj, name, "") or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception as exc:
        return {"_invalid_json": text, "_error": str(exc)}


def _link_names(obj, name):
    try:
        value = getattr(obj, name, None)
    except Exception:
        value = None
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item.Name) for item in value if getattr(item, "Name", None)]
    ref = _object_ref(value)
    return [ref["name"]] if ref else []


def _demo_payload(doc):
    controller = doc.getObject("FA_DemoBuilding") if doc is not None else None
    if controller is None:
        return {"present": False}
    return {
        "present": True,
        "controller": str(controller.Name),
        "seed": int(getattr(controller, "Seed", 0) or 0),
        "randomized": bool(getattr(controller, "Randomized", False)),
        "execution_mode": str(getattr(controller, "ExecutionMode", "") or ""),
        "current_step": int(getattr(controller, "CurrentStep", 0) or 0),
        "total_steps": int(getattr(controller, "TotalSteps", 0) or 0),
        "playback_state": str(getattr(controller, "PlaybackState", "") or ""),
        "last_completed_step": str(getattr(controller, "LastCompletedStep", "") or ""),
        "last_error": str(getattr(controller, "LastError", "") or ""),
        "specification": _parse_json_property(controller, "SpecificationJSON"),
        "step_plan": _parse_json_property(controller, "StepPlanJSON"),
        "sources": _link_names(controller, "Sources"),
        "spaces": _link_names(controller, "Spaces"),
        "ceiling_objects": _link_names(controller, "CeilingObjects"),
        "generated_objects": _link_names(controller, "GeneratedObjects"),
    }


def _element_data_payload(doc):
    errors = {}
    try:
        windows = extract_window_records(doc)
    except Exception as exc:
        windows = []
        errors[CATEGORY_WINDOWS] = str(exc)
    try:
        doors = extract_door_records(doc)
    except Exception as exc:
        doors = []
        errors[CATEGORY_DOORS] = str(exc)
    payload = {
        "schema_version": ELEMENT_SCHEMA_VERSION,
        "categories": {
            CATEGORY_WINDOWS: windows,
            CATEGORY_DOORS: doors,
        },
    }
    if errors:
        payload["errors"] = errors
    return payload


def build_document_snapshot(doc=None):
    """Build one semantic, read-only snapshot for the active FreeCAD document."""
    doc = doc or App.ActiveDocument
    if doc is None:
        raise RuntimeError(
            i18n.bi(
                "No hay un documento activo. Cree o abra un modelo; para la prueba puede usar FA Demo edificio.",
                "There is no active document. Create or open a model; for testing you can use FA Building Demo.",
            )
        )
    objects = [_object_payload(obj) for obj in list(doc.Objects)]
    selection = []
    try:
        selection = [str(obj.Name) for obj in FreeCADGui.Selection.getSelection() if getattr(obj, "Name", None)]
    except Exception:
        selection = []
    document_data = {
        "name": str(getattr(doc, "Name", "") or ""),
        "label": str(getattr(doc, "Label", "") or ""),
        "file_name": str(getattr(doc, "FileName", "") or ""),
        "object_count": len(objects),
    }
    workbench_data = {
        "id": "FacilArquitecturaWorkbench",
        "name": "Facil Arquitectura",
        "version": VERSION,
        "build": BUILD_ID,
        "snapshot_generator": "FA_JSONInspector",
    }
    snapshot = build_snapshot(
        workbench=workbench_data,
        document=document_data,
        objects=objects,
        demo=_demo_payload(doc),
        element_data=_element_data_payload(doc),
        selection=selection,
    )
    _log(
        "snapshot | doc=%s | objetos=%d | demo=%s | ventanas=%d | puertas=%d"
        % (
            document_data["name"],
            len(objects),
            bool(snapshot.get("demo", {}).get("present")),
            len(snapshot.get("element_data", {}).get("categories", {}).get(CATEGORY_WINDOWS, [])),
            len(snapshot.get("element_data", {}).get("categories", {}).get(CATEGORY_DOORS, [])),
        )
    )
    return snapshot



_INPUT_BLOCKED_PROPERTIES = {
    "Shape", "Proxy", "Geometry", "Constraints", "ExpressionEngine",
    "InternalShape", "Mesh", "Support", "AttachmentSupport",
}


def _input_ref_name(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("$ref") or value.get("name") or "")
    return ""


def _numeric_input(value):
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    return float(value)


def _convert_input_for_property(doc, obj, prop_name, value):
    type_id = str(obj.getTypeIdOfProperty(prop_name) or "")
    if prop_name in _INPUT_BLOCKED_PROPERTIES or type_id in (
        "Part::PropertyPartShape", "Part::PropertyGeometryList", "App::PropertyPythonObject"
    ):
        raise ValueError("Propiedad bloqueada para entrada JSON: %s.%s" % (obj.Name, prop_name))
    if type_id in ("App::PropertyString", "App::PropertyFile", "App::PropertyPath", "App::PropertyEnumeration"):
        return str(value)
    if type_id == "App::PropertyBool":
        if not isinstance(value, bool):
            raise ValueError("%s.%s requiere booleano" % (obj.Name, prop_name))
        return value
    if type_id in ("App::PropertyInteger", "App::PropertyIntegerConstraint"):
        return int(value)
    if type_id in ("App::PropertyFloat", "App::PropertyPercent", "App::PropertyPrecision"):
        return float(value)
    if type_id in (
        "App::PropertyLength", "App::PropertyDistance", "App::PropertyAngle",
        "App::PropertyArea", "App::PropertyVolume", "App::PropertyQuantity",
    ):
        return _numeric_input(value)
    if type_id in ("App::PropertyStringList",):
        if not isinstance(value, list):
            raise ValueError("%s.%s requiere lista" % (obj.Name, prop_name))
        return [str(item) for item in value]
    if type_id in ("App::PropertyFloatList",):
        if not isinstance(value, list):
            raise ValueError("%s.%s requiere lista" % (obj.Name, prop_name))
        return [float(item) for item in value]
    if type_id in ("App::PropertyIntegerList",):
        if not isinstance(value, list):
            raise ValueError("%s.%s requiere lista" % (obj.Name, prop_name))
        return [int(item) for item in value]
    if type_id in ("App::PropertyVector", "App::PropertyVectorDistance"):
        if not isinstance(value, dict):
            raise ValueError("%s.%s requiere {x,y,z}" % (obj.Name, prop_name))
        return App.Vector(float(value.get("x", 0.0)), float(value.get("y", 0.0)), float(value.get("z", 0.0)))
    if type_id == "App::PropertyLink":
        name = _input_ref_name(value)
        if not name:
            return None
        ref = doc.getObject(name)
        if ref is None:
            raise ValueError("Referencia inexistente para %s.%s: %s" % (obj.Name, prop_name, name))
        return ref
    if type_id in ("App::PropertyLinkList", "App::PropertyLinkListHidden"):
        if not isinstance(value, list):
            raise ValueError("%s.%s requiere lista de referencias" % (obj.Name, prop_name))
        refs = []
        for item in value:
            name = _input_ref_name(item)
            ref = doc.getObject(name) if name else None
            if ref is None:
                raise ValueError("Referencia inexistente para %s.%s: %s" % (obj.Name, prop_name, name))
            refs.append(ref)
        return refs
    raise ValueError("Tipo de propiedad no soportado por entrada JSON: %s (%s.%s)" % (type_id, obj.Name, prop_name))


def _document_for_command(command, require=True):
    doc = App.ActiveDocument
    if require and doc is None:
        raise RuntimeError("No hay documento activo para aplicar esta operacion")
    requested = str(command.get("document", "") or "").strip()
    if requested and doc is not None:
        if requested not in (str(doc.Name), str(getattr(doc, "Label", "") or "")):
            raise RuntimeError(
                "El JSON apunta al documento '%s', pero el documento activo es '%s'" %
                (requested, str(getattr(doc, "Label", "") or doc.Name))
            )
    return doc


def _plan_set_properties(doc, operation):
    obj = doc.getObject(str(operation["target"]))
    if obj is None:
        raise ValueError("Objeto no encontrado: %s" % operation["target"])
    changes = []
    properties = set(str(name) for name in list(getattr(obj, "PropertiesList", []) or []))
    for prop_name, requested in operation["values"].items():
        prop_name = str(prop_name)
        if prop_name not in properties:
            raise ValueError("La propiedad no existe: %s.%s" % (obj.Name, prop_name))
        converted = _convert_input_for_property(doc, obj, prop_name, requested)
        current = getattr(obj, prop_name)
        changes.append(
            {
                "property": prop_name,
                "type": str(obj.getTypeIdOfProperty(prop_name) or ""),
                "current": _value_to_json(current),
                "requested": _value_to_json(converted),
            }
        )
    return {"op": "set_properties", "target": obj.Name, "changes": changes}


def _apply_set_properties(doc, operation):
    plan = _plan_set_properties(doc, operation)
    transaction_open = False
    try:
        doc.openTransaction("FA JSON set_properties")
        transaction_open = True
        obj = doc.getObject(plan["target"])
        for prop_name, requested in operation["values"].items():
            setattr(obj, str(prop_name), _convert_input_for_property(doc, obj, str(prop_name), requested))
        try:
            obj.touch()
        except Exception:
            pass
        doc.recompute()
        doc.commitTransaction()
        transaction_open = False
    except Exception:
        if transaction_open:
            doc.abortTransaction()
        raise
    plan["applied"] = True
    return plan


def _element_context(doc, records):
    source_names = sorted({str(row.get("SourceSketch", "") or "") for row in records if str(row.get("SourceSketch", "") or "")})
    sketches = []
    missing = []
    for name in source_names:
        obj = doc.getObject(name)
        if obj is None:
            missing.append(name)
        else:
            sketches.append(obj)
    if missing:
        raise ValueError("SourceSketch no encontrado: %s" % ", ".join(missing))
    if not sketches:
        raise ValueError("Los records no identifican SourceSketch")
    walls = [obj for obj in list(doc.Objects) if is_bim_wall(obj)]
    if not walls:
        raise ValueError("No se encontraron muros BIM para resolver hosts")
    level_keys = sorted({str(row.get("LevelKey", "") or "") for row in records if str(row.get("LevelKey", "") or "")})
    if len(level_keys) > 1:
        raise ValueError("apply_elements no admite varios LevelKey en una misma operacion")
    target = doc.getObject(level_keys[0]) if level_keys else None
    if level_keys and target is None:
        raise ValueError("LevelKey no encontrado: %s" % level_keys[0])
    return target, sketches, walls


def _execute_apply_elements(doc, operation, dry_run):
    target, sketches, walls = _element_context(doc, operation["records"])
    kwargs = {"dry_run": bool(dry_run)}
    if operation.get("tolerance") is not None:
        kwargs["tolerance"] = operation["tolerance"]
    if operation.get("host_tolerance_mm") is not None:
        kwargs["host_tolerance_mm"] = float(operation["host_tolerance_mm"])
    if operation["category"] == CATEGORY_WINDOWS:
        result = apply_window_records(doc, target, operation["records"], sketches, walls, **kwargs)
    else:
        result = apply_door_records(doc, target, operation["records"], sketches, walls, **kwargs)
    return {"op": "apply_elements", "category": operation["category"], "result": result}



def _set_property(obj, type_id, name, group, description, value):
    """Create a simple FA property when missing and assign its value."""
    if name not in set(str(item) for item in list(getattr(obj, "PropertiesList", []) or [])):
        obj.addProperty(type_id, name, group, description)
    setattr(obj, name, value)


def _find_named_or_labeled(doc, key):
    key = str(key or "").strip()
    if not key:
        return None
    obj = doc.getObject(key)
    if obj is not None:
        return obj
    for candidate in list(getattr(doc, "Objects", []) or []):
        if str(getattr(candidate, "Label", "") or "") == key:
            return candidate
    return None


def _resolve_site_container(doc, requested="Site"):
    requested = str(requested or "Site").strip()
    container = _find_named_or_labeled(doc, requested)
    if container is None and requested.lower() == "site":
        for candidate in list(getattr(doc, "Objects", []) or []):
            if str(getattr(candidate, "FA_Role", "") or "").lower() == "site":
                container = candidate
                break
            if str(getattr(candidate, "IfcType", "") or "").lower() == "site":
                container = candidate
                break
    return container


def _site_objects_group(doc, requested="Site"):
    """Create/reuse one site-object group; attach it below Site when possible."""
    group = doc.getObject("FA_SiteObjects")
    if group is None:
        group = doc.addObject("App::DocumentObjectGroup", "FA_SiteObjects")
        group.Label = "Objetos de sitio - FA JSON"
        _set_property(group, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "site_objects")
        _set_property(group, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", "FA_JSON")
    container = _resolve_site_container(doc, requested)
    if container is not None and hasattr(container, "addObject"):
        try:
            container.addObject(group)
        except Exception:
            pass
    return group, container


def _plan_site_object(doc, operation):
    name = str(operation["name"])
    existing = doc.getObject(name)
    action = "CREATE"
    if existing is not None:
        generated_by = str(getattr(existing, "FA_GeneratedBy", "") or "")
        role = str(getattr(existing, "FA_Role", "") or "")
        if generated_by != "FA_JSON" or role != "site_tree":
            raise ValueError("Ya existe un objeto no administrado por FA JSON con name '%s'" % name)
        action = "UPDATE"
    return {
        "op": "create_site_object",
        "action": action,
        "object_type": operation["object_type"],
        "name": name,
        "label": operation["label"],
        "placement": dict(operation["placement"]),
        "geometry": dict(operation["geometry"]),
        "container": str(operation.get("container", "Site") or "Site"),
        "plan_symbol": bool(operation.get("plan_symbol", True)),
        "documentary_2d": "%s_Plan" % name,
    }


def _create_or_update_tree(doc, operation):
    """Materialize one lightweight landscape tree plus an explicit 2D plan symbol."""
    plan = _plan_site_object(doc, operation)
    name = plan["name"]
    placement = plan["placement"]
    geometry = plan["geometry"]
    height = float(geometry["height_mm"])
    crown_diameter = float(geometry["crown_diameter_mm"])
    trunk_diameter = float(geometry["trunk_diameter_mm"])
    crown_radius = crown_diameter / 2.0
    crown_center_z = height - crown_radius
    trunk_height = max(height * 0.45, crown_center_z + crown_radius * 0.15)

    site_group, site = _site_objects_group(doc, plan["container"])
    tree = doc.getObject(name)
    if tree is None:
        tree = doc.addObject("App::Part", name)
    tree.Label = str(plan["label"] or name)
    tree.Placement = App.Placement(
        App.Vector(float(placement["x_mm"]), float(placement["y_mm"]), float(placement["z_mm"])),
        App.Rotation(),
    )
    _set_property(tree, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", "site_tree")
    _set_property(tree, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", "FA_JSON")
    _set_property(tree, "App::PropertyLength", "FA_Height", "FacilArquitectura", "Altura", height)
    _set_property(tree, "App::PropertyLength", "FA_CrownDiameter", "FacilArquitectura", "Diametro de copa", crown_diameter)
    _set_property(tree, "App::PropertyLength", "FA_TrunkDiameter", "FacilArquitectura", "Diametro de tronco", trunk_diameter)
    _set_property(tree, "App::PropertyString", "FA_ObjectType", "FacilArquitectura", "Tipo de objeto de sitio", "tree")

    trunk_name = "%s_Trunk" % name
    crown_name = "%s_Crown" % name
    plan_name = "%s_Plan" % name
    def managed_child(child_name, role):
        child = doc.getObject(child_name)
        if child is None:
            return doc.addObject("Part::Feature", child_name)
        generated_by = str(getattr(child, "FA_GeneratedBy", "") or "")
        child_role = str(getattr(child, "FA_Role", "") or "")
        if generated_by != "FA_JSON" or child_role != role:
            raise ValueError("Ya existe un objeto no administrado por FA JSON con name '%s'" % child_name)
        return child

    trunk = managed_child(trunk_name, "site_tree_trunk")
    crown = managed_child(crown_name, "site_tree_crown")
    plan_obj = managed_child(plan_name, "site_tree_plan")
    trunk.Label = "Tronco - %s" % tree.Label
    crown.Label = "Copa - %s" % tree.Label
    plan_obj.Label = "Simbolo 2D - %s" % tree.Label

    trunk.Shape = Part.makeCylinder(trunk_diameter / 2.0, trunk_height)
    crown.Shape = Part.makeSphere(crown_radius, App.Vector(0.0, 0.0, crown_center_z))
    circle = Part.makeCircle(crown_radius, App.Vector(0.0, 0.0, 5.0), App.Vector(0.0, 0.0, 1.0))
    cross_x = Part.makeLine(App.Vector(-crown_radius, 0.0, 5.0), App.Vector(crown_radius, 0.0, 5.0))
    cross_y = Part.makeLine(App.Vector(0.0, -crown_radius, 5.0), App.Vector(0.0, crown_radius, 5.0))
    plan_obj.Shape = Part.makeCompound([circle, cross_x, cross_y])

    for child, role in ((trunk, "site_tree_trunk"), (crown, "site_tree_crown"), (plan_obj, "site_tree_plan")):
        _set_property(child, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", role)
        _set_property(child, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador", "FA_JSON")
        try:
            tree.addObject(child)
        except Exception:
            pass
    _set_property(plan_obj, "App::PropertyBool", "GameExportExclude", "FacilArquitectura", "Excluir geometria documental de exportacion 3D", True)

    try:
        trunk.ViewObject.ShapeColor = (0.45, 0.27, 0.10)
        crown.ViewObject.ShapeColor = (0.18, 0.55, 0.20)
        crown.ViewObject.LineColor = (0.10, 0.32, 0.12)
        plan_obj.ViewObject.LineColor = (0.08, 0.38, 0.10)
        plan_obj.ViewObject.LineWidth = 2.0
        plan_obj.ViewObject.Visibility = bool(plan["plan_symbol"])
    except Exception:
        pass
    try:
        site_group.addObject(tree)
    except Exception:
        pass
    doc.recompute()
    plan["created_objects"] = [tree.Name, trunk.Name, crown.Name, plan_obj.Name]
    plan["site"] = str(getattr(site, "Name", "") or "") if site is not None else ""
    plan["applied"] = True
    return plan


def _apply_site_object(doc, operation):
    transaction_open = False
    try:
        doc.openTransaction("FA JSON create_site_object")
        transaction_open = True
        result = _create_or_update_tree(doc, operation)
        doc.commitTransaction()
        transaction_open = False
        return result
    except Exception:
        if transaction_open:
            doc.abortTransaction()
        raise


def _error_result(stage, exc):
    return {
        "schema": "facil-arquitectura.command-result",
        "schema_version": 1,
        "ok": False,
        "stage": str(stage),
        "error": {
            "type": exc.__class__.__name__,
            "message": str(exc),
        },
    }


def _validate_demo_specification(spec):
    required = ("footprint", "walls", "openings", "rooms", "roof", "floor", "ceiling", "site")
    missing = [key for key in required if not isinstance(spec.get(key), dict)]
    if missing:
        raise ValueError("Especificacion Demo incompleta; faltan: %s" % ", ".join(missing))
    # Probar que realmente es serializable antes de entregar el plan.
    json.dumps(spec, ensure_ascii=False, sort_keys=True)
    return {
        "name": str(spec.get("name", "") or ""),
        "seed": int(spec.get("seed", 0) or 0),
        "randomized": bool(spec.get("randomized", False)),
        "footprint": spec.get("footprint", {}),
    }


def execute_command_envelope(payload, dry_run=True):
    """Validate, plan and optionally apply one inbound FA command envelope."""
    command = validate_command(payload)
    create_demo = command["operations"][0]["op"] == "create_demo"
    doc = _document_for_command(command, require=not create_demo)
    report = {
        "schema": "facil-arquitectura.command-result",
        "schema_version": 1,
        "ok": True,
        "dry_run": bool(dry_run),
        "document": str(getattr(doc, "Name", "") or "") if doc is not None else "",
        "operations": [],
    }
    for operation in command["operations"]:
        op = operation["op"]
        if op == "set_properties":
            result = _plan_set_properties(doc, operation) if dry_run else _apply_set_properties(doc, operation)
        elif op == "apply_elements":
            result = _execute_apply_elements(doc, operation, dry_run=dry_run)
        elif op == "create_site_object":
            result = _plan_site_object(doc, operation) if dry_run else _apply_site_object(doc, operation)
        elif op == "create_demo":
            summary = _validate_demo_specification(operation["specification"])
            if dry_run:
                result = {"op": op, "execution": operation["execution"], "specification": summary, "action": "CREATE_NEW_DOCUMENT"}
            else:
                from . import cmd_demo_building
                if operation["execution"] == "guided":
                    cmd_demo_building.start_guided_demo(operation["specification"])
                    result = {"op": op, "execution": "guided", "started": True, "specification": summary}
                else:
                    created = cmd_demo_building._materialize(operation["specification"])
                    result = {
                        "op": op,
                        "execution": "immediate",
                        "created": True,
                        "document": str(created.get("document", "") or "") if isinstance(created, dict) else "",
                        "specification": summary,
                    }
        else:  # pragma: no cover - core validator prevents this.
            raise ValueError("Operacion no soportada: %s" % op)
        report["operations"].append(result)
    return report


class JsonInspectorDialog(QtWidgets.QDialog):
    """Bidirectional FA JSON panel: snapshot output plus controlled command input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.bi("FA JSON", "FA JSON"))
        self.resize(980, 760)
        self.snapshot = None

        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel(
            i18n.bi(
                "Interfaz JSON de Facil Arquitectura. Salida genera un snapshot de diagnostico; Entrada recibe comandos JSON desde ChatGPT/MCP y obliga a validar/dry-run antes de aplicar.",
                "Facil Arquitectura JSON interface. Output generates a diagnostic snapshot; Input receives JSON commands from ChatGPT/MCP and requires validation/dry-run before applying.",
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.tabs = QtWidgets.QTabWidget(self)
        layout.addWidget(self.tabs, 1)
        self._build_output_tab()
        self._build_input_tab()
        self._build_result_tab()

        close_row = QtWidgets.QHBoxLayout()
        close_row.addStretch(1)
        close_button = QtWidgets.QPushButton(i18n.bi("Cerrar", "Close"))
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)
        self.refresh()

    def _fixed_font(self, widget):
        try:
            widget.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        except Exception:
            pass

    def _build_output_tab(self):
        page = QtWidgets.QWidget(self)
        page_layout = QtWidgets.QVBoxLayout(page)
        self.status = QtWidgets.QLabel("")
        page_layout.addWidget(self.status)
        self.editor = QtWidgets.QPlainTextEdit(page)
        self.editor.setReadOnly(True)
        self._fixed_font(self.editor)
        page_layout.addWidget(self.editor, 1)
        buttons = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton(i18n.bi("Actualizar", "Refresh"))
        self.copy_button = QtWidgets.QPushButton(i18n.bi("Copiar JSON", "Copy JSON"))
        self.save_button = QtWidgets.QPushButton(i18n.bi("Guardar JSON...", "Save JSON..."))
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.save_button)
        buttons.addStretch(1)
        page_layout.addLayout(buttons)
        self.refresh_button.clicked.connect(self.refresh)
        self.copy_button.clicked.connect(self.copy_json)
        self.save_button.clicked.connect(self.save_json)
        self.tabs.addTab(page, i18n.bi("Salida", "Output"))

    def _build_input_tab(self):
        page = QtWidgets.QWidget(self)
        page_layout = QtWidgets.QVBoxLayout(page)
        label = QtWidgets.QLabel(
            i18n.bi(
                "Pegue aqui un JSON schema 'facil-arquitectura.command'. El snapshot de Salida no se aplica directamente.",
                "Paste a 'facil-arquitectura.command' JSON schema here. The Output snapshot is not applied directly.",
            )
        )
        label.setWordWrap(True)
        page_layout.addWidget(label)
        self.input_editor = QtWidgets.QPlainTextEdit(page)
        self._fixed_font(self.input_editor)
        self.input_editor.setPlaceholderText(dumps_command(example_command(), pretty=True))
        page_layout.addWidget(self.input_editor, 1)
        self.input_status = QtWidgets.QLabel(i18n.bi("Sin validar.", "Not validated."))
        page_layout.addWidget(self.input_status)
        buttons = QtWidgets.QHBoxLayout()
        self.paste_button = QtWidgets.QPushButton(i18n.bi("Pegar", "Paste"))
        self.example_button = QtWidgets.QPushButton(i18n.bi("Ejemplo", "Example"))
        self.validate_button = QtWidgets.QPushButton(i18n.bi("Validar", "Validate"))
        self.dry_run_button = QtWidgets.QPushButton(i18n.bi("Dry-run", "Dry-run"))
        self.apply_button = QtWidgets.QPushButton(i18n.bi("Aplicar", "Apply"))
        for button in (self.paste_button, self.example_button, self.validate_button, self.dry_run_button, self.apply_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        page_layout.addLayout(buttons)
        self.paste_button.clicked.connect(self.paste_json)
        self.example_button.clicked.connect(self.insert_example)
        self.validate_button.clicked.connect(self.validate_input)
        self.dry_run_button.clicked.connect(self.dry_run_input)
        self.apply_button.clicked.connect(self.apply_input)
        self.tabs.addTab(page, i18n.bi("Entrada", "Input"))

    def _build_result_tab(self):
        page = QtWidgets.QWidget(self)
        page_layout = QtWidgets.QVBoxLayout(page)
        self.result_editor = QtWidgets.QPlainTextEdit(page)
        self.result_editor.setReadOnly(True)
        self._fixed_font(self.result_editor)
        page_layout.addWidget(self.result_editor, 1)
        buttons = QtWidgets.QHBoxLayout()
        self.copy_result_button = QtWidgets.QPushButton(i18n.bi("Copiar resultado/error", "Copy result/error"))
        buttons.addWidget(self.copy_result_button)
        buttons.addStretch(1)
        page_layout.addLayout(buttons)
        self.copy_result_button.clicked.connect(self.copy_result)
        self.result_page = page
        self.tabs.addTab(page, i18n.bi("Resultado", "Result"))

    def refresh(self):
        try:
            self.snapshot = build_document_snapshot(App.ActiveDocument)
        except Exception as exc:
            self.snapshot = None
            self.editor.setPlainText("")
            self.status.setText(i18n.bi("Sin documento activo. Entrada JSON sigue disponible: %s" % exc, "No active document. JSON Input is still available: %s" % exc))
            return
        text = dumps_snapshot(self.snapshot, pretty=True)
        self.editor.setPlainText(text)
        document = self.snapshot.get("document", {})
        demo = self.snapshot.get("demo", {})
        elements = self.snapshot.get("element_data", {}).get("categories", {})
        self.status.setText(
            i18n.bi(
                "Documento: %s | objetos: %d | Demo: %s | ventanas: %d | puertas: %d"
                % (
                    document.get("label") or document.get("name") or "-",
                    int(document.get("object_count", 0) or 0),
                    "si" if demo.get("present") else "no",
                    len(elements.get(CATEGORY_WINDOWS, [])),
                    len(elements.get(CATEGORY_DOORS, [])),
                ),
                "Document: %s | objects: %d | Demo: %s | windows: %d | doors: %d"
                % (
                    document.get("label") or document.get("name") or "-",
                    int(document.get("object_count", 0) or 0),
                    "yes" if demo.get("present") else "no",
                    len(elements.get(CATEGORY_WINDOWS, [])),
                    len(elements.get(CATEGORY_DOORS, [])),
                ),
            )
        )

    def copy_json(self):
        QtWidgets.QApplication.clipboard().setText(self.editor.toPlainText())
        self.status.setText(i18n.bi("JSON copiado al portapapeles.", "JSON copied to clipboard."))

    def save_json(self):
        doc = App.ActiveDocument
        if doc is None:
            self.status.setText(i18n.bi("No hay snapshot que guardar.", "There is no snapshot to save."))
            return
        base_name = str(getattr(doc, "Label", "FA_modelo") or "FA_modelo")
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in base_name).strip("_") or "FA_modelo"
        file_name, _selected = QtWidgets.QFileDialog.getSaveFileName(
            self,
            i18n.bi("Guardar snapshot JSON de Facil Arquitectura", "Save Facil Arquitectura JSON snapshot"),
            safe_name + ".fa.json",
            "JSON (*.json);;All files (*)",
        )
        if not file_name:
            return
        if not file_name.lower().endswith(".json"):
            file_name += ".json"
        with open(file_name, "w", encoding="utf-8") as handle:
            handle.write(self.editor.toPlainText())
            handle.write("\n")
        self.status.setText(i18n.bi("JSON guardado: %s" % file_name, "JSON saved: %s" % file_name))
        _log("guardado: %s" % file_name)

    def paste_json(self):
        self.input_editor.setPlainText(QtWidgets.QApplication.clipboard().text())
        self.input_status.setText(i18n.bi("JSON pegado. Falta validar.", "JSON pasted. Validation pending."))

    def insert_example(self):
        self.input_editor.setPlainText(dumps_command(example_command(), pretty=True))
        self.input_status.setText(i18n.bi("Ejemplo cargado. Falta validar.", "Example loaded. Validation pending."))

    def _parsed_input(self):
        return parse_command_text(self.input_editor.toPlainText())

    def _show_result(self, payload):
        self.result_editor.setPlainText(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str))
        self.tabs.setCurrentWidget(self.result_page)

    def _show_error(self, stage, exc):
        self._show_result(_error_result(stage, exc))

    def copy_result(self):
        text = self.result_editor.toPlainText()
        QtWidgets.QApplication.clipboard().setText(text)
        self.input_status.setText(i18n.bi("Resultado/error copiado al portapapeles.", "Result/error copied to clipboard."))

    def validate_input(self):
        try:
            command = self._parsed_input()
            self._show_result({"valid": True, "command": command})
            self.input_status.setText(i18n.bi("JSON valido. Ejecute Dry-run antes de aplicar.", "Valid JSON. Run Dry-run before applying."))
        except Exception as exc:
            self._show_error("validate", exc)
            self.input_status.setText(i18n.bi("JSON invalido: %s" % exc, "Invalid JSON: %s" % exc))

    def dry_run_input(self):
        try:
            command = self._parsed_input()
            report = execute_command_envelope(command, dry_run=True)
            self._show_result(report)
            self.input_status.setText(i18n.bi("Dry-run completado. Revise Resultado.", "Dry-run completed. Review Result."))
        except Exception as exc:
            self._show_error("dry-run", exc)
            self.input_status.setText(i18n.bi("Dry-run fallo: %s" % exc, "Dry-run failed: %s" % exc))

    def apply_input(self):
        try:
            command = self._parsed_input()
            plan = execute_command_envelope(command, dry_run=True)
            self._show_result(plan)
        except Exception as exc:
            self._show_error("apply-dry-run", exc)
            self.input_status.setText(i18n.bi("No se puede aplicar: %s" % exc, "Cannot apply: %s" % exc))
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            i18n.bi("Aplicar JSON en Facil Arquitectura", "Apply JSON in Facil Arquitectura"),
            i18n.bi(
                "El dry-run es valido. ¿Desea aplicar estas operaciones al modelo? Las modificaciones usan transacciones FreeCAD y pueden deshacerse con Undo.",
                "The dry-run is valid. Apply these operations to the model? Modifications use FreeCAD transactions and can be reverted with Undo.",
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if answer != QtWidgets.QMessageBox.Yes:
            self.input_status.setText(i18n.bi("Aplicacion cancelada; no se modifico el modelo.", "Apply cancelled; model unchanged."))
            return
        try:
            report = execute_command_envelope(command, dry_run=False)
            self._show_result(report)
            self.input_status.setText(i18n.bi("JSON aplicado. Revise Resultado y el modelo.", "JSON applied. Review Result and the model."))
            self.refresh()
            _log("comando JSON aplicado")
        except Exception as exc:
            self._show_error("apply", exc)
            self.input_status.setText(i18n.bi("Aplicacion fallo: %s" % exc, "Apply failed: %s" % exc))


class CommandClass:
    """Open the bidirectional JSON interface for Facil Arquitectura."""

    CommandName = "FA_JSONInspector"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA JSON", "FA JSON"),
            "ToolTip": i18n.bi(
                "Interfaz JSON bidireccional: inspecciona el modelo y permite pegar comandos JSON desde ChatGPT/MCP, validarlos, ejecutar dry-run y aplicarlos de forma controlada.",
                "Bidirectional JSON interface: inspect the model and paste JSON commands from ChatGPT/MCP, validate them, run dry-run, and apply them in a controlled way.",
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            dialog = JsonInspectorDialog(parent=FreeCADGui.getMainWindow())
            if hasattr(dialog, "exec"):
                dialog.exec()
            else:
                dialog.exec_()
        except Exception as exc:
            handle_command_exception(i18n.bi("FA JSON", "FA JSON"), exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = ReloadableCommandProxy(
        __name__, class_name="CommandClass", command_name=CommandClass.CommandName
    )
    FreeCADGui.addCommand(command.CommandName, command)
    return command
