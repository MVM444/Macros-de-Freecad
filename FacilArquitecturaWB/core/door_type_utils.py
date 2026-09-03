"""Native BIM door preset changes for Facil Arquitectura.

Descripcion: cambia el preset de puertas Arch existentes reutilizando
ArchWindowPresets y conservando la identidad del objeto, su host y trazabilidad.
FreeCAD objetivo: 1.1.3.
Fecha: 2026-08-13.
Version: 0.2.0.
"""

from __future__ import annotations

import json

import FreeCAD

from .command_errors import UserFacingError
from .project_structure import set_prop


LOG_PREFIX = "[FACILARQ][PUERTAS] "
SOURCE_OVERRIDES_PROPERTY = "FA_DoorTypeOverrides"
DOUBLE_DOOR_GENERATOR = "FA_InsertDoubleDoorBIM"
DOUBLE_DOOR_SPEC_ID = "architecture.door.double_leaf.glazed.europa"
TYPE_SOURCE_NATIVE = "native_preset"
TYPE_SOURCE_DOUBLE = "fa_double"


def log(message, warning=False):
    printer = FreeCAD.Console.PrintWarning if warning else FreeCAD.Console.PrintMessage
    printer(LOG_PREFIX + str(message) + "\n")


def native_door_presets(preset_module=None):
    """Return the installed built-in Arch presets whose native name is a door."""
    if preset_module is None:
        try:
            import ArchWindowPresets as preset_module
        except Exception as exc:
            raise UserFacingError(
                "No se pudo cargar ArchWindowPresets de FreeCAD: %s" % exc
            )
    result = []
    for entry in list(getattr(preset_module, "WindowPresets", []) or []):
        name = entry[0] if isinstance(entry, (tuple, list)) and entry else entry
        text = str(name or "").strip()
        if text and "door" in text.lower() and text not in result:
            result.append(text)
    if not result:
        raise UserFacingError(
            "La instalacion de FreeCAD no publico presets BIM nativos de puerta."
        )
    return result


def door_type_catalog(preset_module=None):
    """Return JSON-compatible door type definitions available in this installation.

    Native and user-installed ArchWindow presets are discovered dynamically.  The
    FA double-leaf door remains an explicit factory because it uses custom
    ``WindowParts`` rather than a simple preset swap.
    """
    result = [
        {
            "DoorType": "DoubleDoor",
            "TypeSource": TYPE_SOURCE_DOUBLE,
            "TypeRef": DOUBLE_DOOR_SPEC_ID,
            "Preset": "Double leaf glazed Europa",
            "LeafCount": 2,
        }
    ]
    for preset in native_door_presets(preset_module=preset_module):
        result.append(
            {
                "DoorType": preset,
                "TypeSource": TYPE_SOURCE_NATIVE,
                "TypeRef": preset,
                "Preset": preset,
                "LeafCount": 1,
            }
        )
    return result


def resolve_door_type(door_type="", type_source="", type_ref="", preset="", leaf_count=None, preset_module=None):
    """Resolve one table definition to a supported native/factory door type.

    This deliberately accepts newly installed FreeCAD door presets without code
    changes: put the preset name in ``Preset`` or ``TypeRef`` and it becomes a
    valid ``native_preset`` type. Unknown factories remain rejected instead of
    silently substituting a different geometry.
    """
    door_type = str(door_type or "").strip()
    source = str(type_source or "").strip().lower()
    ref = str(type_ref or "").strip()
    preset = str(preset or "").strip()
    try:
        leaves = int(leaf_count) if leaf_count is not None else None
    except Exception:
        leaves = None
    double_aliases = {
        "doubledoor",
        "double door",
        "puerta doble",
        "double leaf glazed europa",
        DOUBLE_DOOR_SPEC_ID.lower(),
    }
    if source == TYPE_SOURCE_DOUBLE or ref.lower() == DOUBLE_DOOR_SPEC_ID.lower() or door_type.lower() in double_aliases or (leaves is not None and leaves > 1 and not preset):
        return {
            "DoorType": door_type or "DoubleDoor",
            "TypeSource": TYPE_SOURCE_DOUBLE,
            "TypeRef": DOUBLE_DOOR_SPEC_ID,
            "Preset": preset or "Double leaf glazed Europa",
            "LeafCount": max(2, leaves or 2),
        }

    available = native_door_presets(preset_module=preset_module)
    candidate = ref or preset or door_type
    if candidate in available:
        return {
            "DoorType": door_type or candidate,
            "TypeSource": TYPE_SOURCE_NATIVE,
            "TypeRef": candidate,
            "Preset": candidate,
            "LeafCount": max(1, leaves or 1),
        }
    raise UserFacingError(
        "Tipo de puerta no disponible: %s. Use un preset de puerta instalado en FreeCAD "
        "o TypeSource=fa_double para la puerta doble FA." % (candidate or door_type or "(vacio)")
    )


def is_special_fa_double_door(obj):
    return bool(
        str(getattr(obj, "FA_GeneratedBy", "") or "") == DOUBLE_DOOR_GENERATOR
        or str(getattr(obj, "SpecId", "") or "") in (DOUBLE_DOOR_SPEC_ID, "FA-DOOR-DOUBLE-GLAZED-EUROPA")
        or _integer(getattr(obj, "LeafCount", 0)) > 1
    )


def door_compatibility(obj):
    """Return ``(accepted, reason)`` for one identity-preserving preset change."""
    if obj is None:
        return False, "objeto inexistente"
    if is_special_fa_double_door(obj):
        return False, (
            "es una puerta doble especial de FA; su Base y WindowParts no son "
            "compatibles con los presets simples de ArchWindowPresets"
        )
    ifc_type = str(getattr(obj, "IfcType", "") or "").strip().lower()
    if ifc_type != "door":
        if ifc_type == "window":
            return False, "es una ventana BIM, no una puerta"
        if ifc_type == "opening element":
            return False, "es un Opening Element, no una puerta"
        return False, "IfcType no es Door"
    proxy = getattr(obj, "Proxy", None)
    proxy_type = str(getattr(proxy, "Type", "") or "").lower()
    proxy_module = str(getattr(getattr(proxy, "__class__", None), "__module__", "") or "")
    if proxy_type != "window" and "ArchWindow" not in proxy_module:
        return False, "no es un objeto ArchWindow/Window compatible"
    required = ("Base", "WindowParts", "Preset", "Width", "Height", "Hosts")
    missing = [name for name in required if not hasattr(obj, name)]
    if missing:
        return False, "le faltan propiedades Arch: %s" % ", ".join(missing)
    if getattr(obj, "Base", None) is None:
        return False, "no tiene Base BIM transferible"
    return True, "puerta Arch/BIM compatible"


def collect_compatible_doors(selection):
    """Collect unique compatible doors and report every rejected selection."""
    doors = []
    rejected = []
    seen = set()
    for selected in list(selection or []):
        obj = _resolved_selection_object(selected)
        key = _object_key(obj)
        if key in seen:
            continue
        seen.add(key)
        accepted, reason = door_compatibility(obj)
        if accepted:
            doors.append(obj)
        else:
            rejected.append((obj, reason))
    return doors, rejected


def door_preset_name(obj, presets=None):
    """Resolve the semantic preset name from FA metadata or native Preset index."""
    available = list(presets or native_door_presets())
    for attr in ("FA_DoorPresetName", "FA_PresetName"):
        value = str(getattr(obj, attr, "") or "").strip()
        if value in available:
            return value
    try:
        import ArchWindowPresets

        all_presets = list(getattr(ArchWindowPresets, "WindowPresets", []) or [])
        index = int(getattr(obj, "Preset", 0)) - 1
        if 0 <= index < len(all_presets):
            value = str(all_presets[index] or "").strip()
            if value in available:
                return value
    except Exception:
        pass
    return "Desconocido"


def common_preset_name(doors, presets=None):
    names = {door_preset_name(obj, presets=presets) for obj in list(doors or [])}
    return names.pop() if len(names) == 1 else "Varios"


def source_door_type_overrides(source):
    """Read the source-Sketch mapping ``geometry index -> native preset``."""
    raw = str(getattr(source, SOURCE_OVERRIDES_PROPERTY, "") or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    result = {}
    for key, value in data.items():
        try:
            normalized_key = str(int(key))
        except Exception:
            continue
        text = str(value or "").strip()
        if text:
            result[normalized_key] = text
    return result


def door_preset_override(source, geometry_index, presets=None):
    if source is None:
        return ""
    value = source_door_type_overrides(source).get(str(int(geometry_index)), "")
    available = list(presets or native_door_presets())
    return value if value in available else ""


def record_source_door_override(door, preset_name):
    """Persist one manual per-instance exception on its authoritative Sketch."""
    source = getattr(door, "FA_SourceSketch", None)
    try:
        index = int(getattr(door, "FA_SourceGeometryIndex", -1))
    except Exception:
        index = -1
    if source is None or index < 0:
        return False
    overrides = source_door_type_overrides(source)
    overrides[str(index)] = str(preset_name)
    set_prop(
        source,
        "App::PropertyString",
        SOURCE_OVERRIDES_PROPERTY,
        "FacilArquitectura",
        "Overrides manuales de preset por indice geometrico (JSON)",
        json.dumps(overrides, sort_keys=True, separators=(",", ":")),
    )
    return True


def change_door_types(
    doc,
    doors,
    target_preset,
    preserve_dimensions=True,
    preserve_opening=True,
):
    """Change native door presets in place and validate hosted wall cuts.

    The caller owns the FreeCAD transaction. All doors are validated before any
    mutation. Native temporary doors are removed only after the transferred
    objects pass geometry and host-cut validation.
    """
    selected = _unique_objects(doors)
    if not selected:
        raise UserFacingError("Seleccione una o varias puertas Arch/BIM existentes.")
    presets = native_door_presets()
    target = str(target_preset or "").strip()
    if target not in presets:
        raise UserFacingError(
            "El preset %s no existe entre las puertas BIM nativas instaladas."
            % (target or "(vacio)")
        )
    for obj in selected:
        accepted, reason = door_compatibility(obj)
        if not accepted:
            raise UserFacingError("%s: %s." % (_label(obj), reason))

    log("Cambiar tipo - seleccionadas: %d" % len(selected))
    log("Preset destino: %s" % target)
    states = [_capture_state(obj) for obj in selected]
    temporary_doors = []
    for state in states:
        template = _make_native_template(doc, state, target)
        temporary_doors.append(template)
        _transfer_template(state, template, preserve_dimensions, preserve_opening)

    for state in states:
        for host in state["hosts"]:
            try:
                host.touch()
            except Exception:
                pass
    doc.recompute()
    validation = [_validate_transferred_state(state, target) for state in states]

    # Only validated doors may become authoritative and release temporaries.
    for state in states:
        obj = state["door"]
        previous = state["preset_name"]
        set_prop(obj, "App::PropertyString", "FA_DoorPresetName", "FacilArquitectura", "Preset BIM nativo actual", target)
        set_prop(obj, "App::PropertyString", "FA_PreviousDoorPreset", "FacilArquitectura", "Preset anterior", previous)
        set_prop(obj, "App::PropertyBool", "FA_TypeOverride", "FacilArquitectura", "Tipo modificado manualmente", True)
        set_prop(obj, "App::PropertyString", "FA_TypeOverrideSource", "FacilArquitectura", "Herramienta que fijo el override", "FA_ChangeDoorType")
        if hasattr(obj, "FA_PresetName"):
            obj.FA_PresetName = target
        record_source_door_override(obj, target)

    for template in temporary_doors:
        name = str(getattr(template, "Name", "") or "")
        try:
            template.Hosts = []
        except Exception:
            pass
        if name and doc.getObject(name) is not None:
            doc.removeObject(name)
    for state in states:
        _retire_old_base_if_unreferenced(doc, state)
    doc.recompute()
    for state in states:
        _validate_transferred_state(state, target)

    for state in states:
        obj = state["door"]
        host_text = ", ".join(_label(host) for host in state["hosts"]) or "sin host"
        log("%s host preservado: %s" % (obj.Name, host_text))
        log("%s dimensiones: %.0f x %.0f mm" % (obj.Name, _length(obj.Width), _length(obj.Height)))
        log("%s corte validado" % obj.Name if state["hosts"] else "%s puerta libre validada" % obj.Name)
    log("Cambio completado: %d/%d" % (len(states), len(states)))
    return selected, {
        "changed_count": len(states),
        "target_preset": target,
        "identity_preserved": True,
        "validated_host_count": sum(item["validated_host_count"] for item in validation),
    }


def _capture_state(obj):
    base = obj.Base
    hosts = list(getattr(obj, "Hosts", []) or [])
    host_checks = []
    for host in hosts:
        old_subvolume = obj.Proxy.getSubVolume(obj, host=host)
        before_shape = host.Shape.copy()
        host_checks.append(
            {
                "host": host,
                "before_shape": before_shape,
                "before_volume": float(before_shape.Volume),
                "support_shape": before_shape.fuse(old_subvolume),
            }
        )
    return {
        "door": obj,
        "name": obj.Name,
        "label": obj.Label,
        "base": base,
        "base_name": base.Name,
        "base_label": base.Label,
        "base_placement": FreeCAD.Placement(base.Placement),
        "base_parents": _group_parents(base),
        "base_visibility": _visibility(base),
        "door_parents": _group_parents(obj),
        "placement": FreeCAD.Placement(obj.Placement),
        "width": _length(obj.Width),
        "height": _length(obj.Height),
        "hosts": hosts,
        "normal": _copy_vector(getattr(obj, "Normal", None)),
        "hole_depth": _length(getattr(obj, "HoleDepth", 0.0)),
        "opening": _number(getattr(obj, "Opening", 0.0)),
        "symbol_plan": getattr(obj, "SymbolPlan", None),
        "symbol_elevation": getattr(obj, "SymbolElevation", None),
        "ifc_type": str(getattr(obj, "IfcType", "Door") or "Door"),
        "move_with_host": getattr(obj, "MoveWithHost", None),
        "preset_name": door_preset_name(obj),
        "host_checks": host_checks,
    }


def _make_native_template(doc, state, target):
    try:
        import ArchWindowPresets
    except Exception as exc:
        raise UserFacingError("No se pudo cargar ArchWindowPresets: %s" % exc)
    width = state["width"]
    height = state["height"]
    if width <= 0.0 or height <= 0.0:
        raise UserFacingError("%s tiene dimensiones no validas." % state["label"])
    wall_width = _host_width(state["hosts"][0]) if state["hosts"] else 100.0
    frame = max(5.0, min(50.0, width * 0.20, height * 0.20))
    panel_depth = min(40.0, max(10.0, wall_width * 0.5))
    template = ArchWindowPresets.makeWindowPreset(
        target,
        width,
        height,
        frame,
        frame,
        frame,
        wall_width,
        panel_depth,
        0.0,
        (wall_width - panel_depth) * 0.5,
        FreeCAD.Placement(state["base_placement"]),
    )
    if template is None or getattr(template, "Base", None) is None:
        raise UserFacingError("FreeCAD no pudo generar el preset nativo %s." % target)
    template.Hosts = []
    try:
        template.ViewObject.Visibility = False
        template.Base.ViewObject.Visibility = False
    except Exception:
        pass
    return template


def _transfer_template(state, template, preserve_dimensions, preserve_opening):
    obj = state["door"]
    new_base = template.Base
    _copy_base_metadata(state["base"], new_base)
    new_base.Label = state["base_label"]
    _transfer_base_containment(state["base"], new_base, state["base_parents"])
    obj.Base = new_base
    obj.WindowParts = list(template.WindowParts)
    obj.Preset = int(template.Preset)
    if hasattr(obj, "Frame") and hasattr(template, "Frame"):
        obj.Frame = _length(template.Frame)
    if hasattr(obj, "Offset") and hasattr(template, "Offset"):
        obj.Offset = _length(template.Offset)
    if preserve_dimensions:
        obj.Width = state["width"]
        obj.Height = state["height"]
    obj.Placement = FreeCAD.Placement(state["placement"])
    obj.Hosts = list(state["hosts"])
    if state["normal"] is not None and hasattr(obj, "Normal"):
        obj.Normal = _copy_vector(state["normal"])
    if hasattr(obj, "HoleDepth"):
        obj.HoleDepth = state["hole_depth"]
    if hasattr(obj, "Opening"):
        obj.Opening = int(
            round(state["opening"] if preserve_opening else _number(template.Opening))
        )
    if state["symbol_plan"] is not None and hasattr(obj, "SymbolPlan"):
        obj.SymbolPlan = state["symbol_plan"]
    if state["symbol_elevation"] is not None and hasattr(obj, "SymbolElevation"):
        obj.SymbolElevation = state["symbol_elevation"]
    if state["move_with_host"] is not None and hasattr(obj, "MoveWithHost"):
        obj.MoveWithHost = state["move_with_host"]
    obj.IfcType = "Door"
    obj.Label = state["label"]
    try:
        new_base.ViewObject.Visibility = state["base_visibility"]
    except Exception:
        pass


def _validate_transferred_state(state, target):
    obj = state["door"]
    if obj.Document.getObject(state["name"]) is not obj:
        raise UserFacingError("%s perdio su identidad durante el cambio." % state["label"])
    if getattr(obj, "Base", None) is None or obj.Shape.isNull() or not obj.Shape.Solids:
        raise UserFacingError("%s no genero una forma BIM valida para %s." % (state["label"], target))
    if list(getattr(obj, "Hosts", []) or []) != state["hosts"]:
        raise UserFacingError("%s perdio su muro anfitrion." % state["label"])
    if str(getattr(obj, "IfcType", "") or "") != "Door":
        raise UserFacingError("%s dejo de ser IfcType Door." % state["label"])
    if abs(_length(obj.Width) - state["width"]) > 0.01 or abs(_length(obj.Height) - state["height"]) > 0.01:
        raise UserFacingError("%s cambio su ancho o alto exterior." % state["label"])
    if not _same_placement(obj.Placement, state["placement"]):
        raise UserFacingError("%s cambio su Placement." % state["label"])
    if state["normal"] is not None and not _same_vector(getattr(obj, "Normal", None), state["normal"]):
        raise UserFacingError("%s cambio su Normal." % state["label"])
    for parent in state["door_parents"]:
        if obj not in list(getattr(parent, "Group", []) or []):
            raise UserFacingError("%s perdio su contenedor BIM." % state["label"])
    for parent in state["base_parents"]:
        if obj.Base not in list(getattr(parent, "Group", []) or []):
            raise UserFacingError("%s perdio el contenedor de su Base BIM." % state["label"])
    validated = 0
    for check in state["host_checks"]:
        host = check["host"]
        subvolume = obj.Proxy.getSubVolume(obj, host=host)
        support_intersection = float(check["support_shape"].common(subvolume).Volume)
        residual = float(host.Shape.common(subvolume).Volume)
        volume_delta = abs(float(host.Shape.Volume) - check["before_volume"])
        volume_tolerance = max(1.0, check["before_volume"] * 1e-7)
        if support_intersection <= 1.0:
            raise UserFacingError("%s ya no intersecta el soporte del muro %s." % (state["label"], _label(host)))
        if residual > max(1.0, float(subvolume.Volume) * 1e-7):
            raise UserFacingError("%s no mantiene perforado el muro %s." % (state["label"], _label(host)))
        if volume_delta > volume_tolerance:
            raise UserFacingError("%s cambio el volumen cortado del muro %s." % (state["label"], _label(host)))
        validated += 1
    return {"validated_host_count": validated}


def _copy_base_metadata(source, target):
    for name in list(getattr(source, "PropertiesList", []) or []):
        if not str(name).startswith("FA_"):
            continue
        try:
            if not hasattr(target, name):
                target.addProperty(
                    source.getTypeIdOfProperty(name),
                    name,
                    source.getGroupOfProperty(name),
                    source.getDocumentationOfProperty(name),
                )
            setattr(target, name, getattr(source, name))
        except Exception:
            pass


def _transfer_base_containment(old_base, new_base, parents):
    for parent in parents:
        try:
            parent.addObject(new_base)
        except Exception:
            try:
                parent.addObjects([new_base])
            except Exception:
                pass
        try:
            parent.removeObject(old_base)
        except Exception:
            pass


def _retire_old_base_if_unreferenced(doc, state):
    old_base = state["base"]
    if doc.getObject(state["base_name"]) is not old_base:
        return
    dependents = [
        item
        for item in list(getattr(old_base, "InList", []) or [])
        if item not in state["base_parents"]
    ]
    if not dependents:
        doc.removeObject(state["base_name"])


def _group_parents(obj):
    result = []
    for parent in list(getattr(obj, "InList", []) or []):
        try:
            if obj in list(getattr(parent, "Group", []) or []):
                result.append(parent)
        except Exception:
            pass
    return result


def _host_width(host):
    for attr in ("Width", "FA_Thickness_mm", "FA_WallThickness"):
        try:
            value = _length(getattr(host, attr))
            if value > 0.0:
                return value
        except Exception:
            pass
    return 100.0


def _visibility(obj):
    try:
        return bool(obj.ViewObject.Visibility)
    except Exception:
        return False


def _length(value):
    return float(getattr(value, "Value", value))


def _number(value):
    return float(getattr(value, "Value", value))


def _integer(value):
    try:
        return int(round(_number(value)))
    except Exception:
        return 0


def _copy_vector(value):
    if value is None:
        return None
    try:
        return FreeCAD.Vector(value)
    except Exception:
        return FreeCAD.Vector(float(value.x), float(value.y), float(value.z))


def _same_vector(first, second, tolerance=1e-7):
    try:
        return (FreeCAD.Vector(first) - FreeCAD.Vector(second)).Length <= tolerance
    except Exception:
        return False


def _same_placement(first, second, tolerance=1e-7):
    try:
        return all(abs(float(a) - float(b)) <= tolerance for a, b in zip(first.Matrix.A, second.Matrix.A))
    except Exception:
        return False


def _resolved_selection_object(obj):
    try:
        return obj.getLinkedObject(True) or obj
    except Exception:
        return obj


def _object_key(obj):
    name = str(getattr(obj, "Name", "") or "")
    document = getattr(obj, "Document", None)
    return (id(document), name) if name else (None, id(obj))


def _unique_objects(objects):
    result = []
    seen = set()
    for obj in list(objects or []):
        key = _object_key(obj)
        if key not in seen:
            seen.add(key)
            result.append(obj)
    return result


def _label(obj):
    return str(getattr(obj, "Label", getattr(obj, "Name", "Objeto")) or "Objeto")
