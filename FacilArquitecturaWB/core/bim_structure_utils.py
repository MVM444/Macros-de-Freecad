"""Native BIM spatial structure helpers for FacilArquitecturaWB.

Descripcion: crea y reutiliza Building y Building Storey nativos de FreeCAD.
Objetivo: organizar reconstrucciones desde Sketches sin crear una jerarquia FA paralela.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-09-01 14:35 America/Costa_Rica.
Version: 0.4.0.
Instrucciones de mantenimiento: conservar Arch.makeBuilding/makeFloor como autoridad
y no reemplazar objetos BIM manuales del usuario durante una reejecucion.
"""

from __future__ import annotations

import FreeCAD

from .command_errors import UserFacingError
from .constants import GROUPS, ROOT_GROUP_NAME
from .project_structure import ensure_project_support_structure, msg, set_prop, warn

try:
    import Arch
except Exception:  # pragma: no cover - depende del runtime de FreeCAD
    Arch = None


GENERATED_BY_STRUCTURE = "FA_CreateBIMStructure"
DEFAULT_BUILDING_NAME = "Edificio"
DEFAULT_LEVEL_NAME = "Nivel 00"
AUXILIARY_GROUP_PREFIX = "FA_Auxiliary"
DEFAULT_AUXILIARY_GROUP_LABEL = "Auxiliares FA"


def is_building(obj):
    """Return True for native Arch Building objects."""
    return str(getattr(obj, "IfcType", "") or "") == "Building"


def is_level(obj):
    """Return True for native Arch Building Storey objects."""
    return str(getattr(obj, "IfcType", "") or "") == "Building Storey"


def collect_buildings(doc):
    return [obj for obj in list(getattr(doc, "Objects", []) or []) if is_building(obj)]


def collect_levels(doc, building=None):
    levels = [obj for obj in list(getattr(doc, "Objects", []) or []) if is_level(obj)]
    if building is None:
        return levels
    members = list(getattr(building, "Group", []) or [])
    return [obj for obj in levels if obj in members]


def selected_level(selection):
    """Resolve one explicitly selected level, including a selected child object."""
    direct = [obj for obj in list(selection or []) if is_level(obj)]
    if len(direct) == 1:
        return direct[0]
    parents = []
    for obj in list(selection or []):
        for parent in list(getattr(obj, "InList", []) or []):
            if is_level(parent) and parent not in parents:
                parents.append(parent)
    return parents[0] if len(parents) == 1 else None


def ensure_bim_structure(
    doc,
    building_name=DEFAULT_BUILDING_NAME,
    level_name=DEFAULT_LEVEL_NAME,
    elevation_mm=0.0,
    building=None,
    level=None,
    update_existing=False,
):
    """Create or reuse one native Building and Level idempotently."""
    _require_arch_structure()
    building_label = str(building_name or DEFAULT_BUILDING_NAME).strip() or DEFAULT_BUILDING_NAME
    level_label = str(level_name or DEFAULT_LEVEL_NAME).strip() or DEFAULT_LEVEL_NAME
    elevation = float(elevation_mm)

    if building is not None and not is_building(building):
        raise UserFacingError("El objeto de edificio seleccionado no es un Building BIM nativo.")
    if level is not None and not is_level(level):
        raise UserFacingError("El objeto de nivel seleccionado no es un Building Storey BIM nativo.")

    created_building = False
    created_level = False
    if building is None:
        building = _best_existing_building(doc, building_label)
    if building is None:
        building = Arch.makeBuilding(name=building_label)
        if building is None:
            raise UserFacingError("Arch.makeBuilding no pudo crear el edificio BIM.")
        created_building = True
        msg("Building creado: %s" % building_label)

    if level is None:
        level = _best_existing_level(doc, building, level_label)
    if level is None:
        level = Arch.makeFloor(name=level_label)
        if level is None:
            raise UserFacingError("Arch.makeFloor no pudo crear el nivel BIM.")
        created_level = True
        msg("Level creado: %s" % level_label)

    if created_building or _is_fa_generated(building) or update_existing:
        building.Label = building_label
    if created_level or _is_fa_generated(level) or update_existing:
        level.Label = level_label
        _set_level_elevation(level, elevation)

    _tag_structure(building, "building")
    _tag_structure(level, "level")
    add_to_container(building, level)
    # Once a native Level exists, generated FA support branches must no longer
    # remain as a parallel project tree. The migration changes containment only.
    migrate_legacy_support_to_level(doc, level)
    doc.recompute()
    return {
        "building": building,
        "level": level,
        "created_building": created_building,
        "created_level": created_level,
    }


def tag_target_level(level, obj):
    """Record the intended BIM Level without adding a second tree membership.

    Hosted objects such as doors and windows already belong visually to their
    host wall through FreeCAD's native Hosts relation. Adding them again to
    Level.Group makes the same object appear twice in the tree.
    """
    if not is_level(level):
        raise UserFacingError("El contenedor destino no es un Level BIM nativo.")
    set_prop(
        obj,
        "App::PropertyString",
        "FA_TargetLevel",
        "FacilArquitectura",
        "Clave del nivel BIM destino; la contencion visible puede venir del host",
        str(getattr(level, "Name", "") or ""),
    )
    return obj


def add_to_level(level, obj, source_sketch=None):
    """Place a non-hosted architectural object in a native Level."""
    if not is_level(level):
        raise UserFacingError("El contenedor destino no es un Level BIM nativo.")
    add_to_container(level, obj)
    tag_target_level(level, obj)
    # Do not create reverse PropertyLinks to a native container. BuildingPart
    # Group is the authoritative containment relation for direct Level members;
    # hosted openings are instead shown through the host wall.
    del source_sketch
    return obj


def ensure_level_auxiliary_group(
    doc,
    level,
    label=DEFAULT_AUXILIARY_GROUP_LABEL,
):
    """Create/reuse one auxiliary group inside a native Level.

    The group is for construction/reference/diagnostic outputs only. Permanent
    architectural elements must remain direct members of the native Level.
    """
    if not is_level(level):
        raise UserFacingError("El contenedor destino no es un Level BIM nativo.")
    level_name = str(getattr(level, "Name", "Level") or "Level")
    safe_level_name = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in level_name)
    group_name = "%s_%s" % (AUXILIARY_GROUP_PREFIX, safe_level_name)
    group = doc.getObject(group_name) if hasattr(doc, "getObject") else None
    created = False
    if group is None:
        group = doc.addObject("App::DocumentObjectGroup", group_name)
        group.Label = str(label or DEFAULT_AUXILIARY_GROUP_LABEL)
        created = True
        msg("Grupo auxiliar de Level creado: %s" % group.Label)
    add_to_container(level, group)
    set_prop(
        group,
        "App::PropertyString",
        "FA_GeneratedBy",
        "FacilArquitectura",
        "Generador o adaptador",
        "FA_AuxiliaryStructure",
    )
    set_prop(
        group,
        "App::PropertyString",
        "FA_Role",
        "FacilArquitectura",
        "Rol de trazabilidad",
        "auxiliary_group",
    )
    set_prop(
        group,
        "App::PropertyString",
        "FA_TargetLevel",
        "FacilArquitectura",
        "Clave del nivel BIM destino",
        level_name,
    )
    if not created:
        msg("Grupo auxiliar de Level reutilizado: %s" % getattr(group, "Label", group_name))
    return group


def resolve_level_context(doc, objects=None):
    """Resolve the unique native Level associated with objects or the document.

    This is intentionally conservative: an explicit Level wins, then recursive
    dependency ancestry and FA_TargetLevel metadata are inspected, and finally
    a document with exactly one Level is accepted.
    """
    candidates = []
    for obj in list(objects or []):
        if is_level(obj) and obj not in candidates:
            candidates.append(obj)
    if len(candidates) == 1:
        return candidates[0]

    pending = list(objects or [])
    seen = set()
    while pending:
        obj = pending.pop(0)
        if obj is None:
            continue
        identity = id(obj)
        if identity in seen:
            continue
        seen.add(identity)
        if is_level(obj):
            if obj not in candidates:
                candidates.append(obj)
            continue
        target_name = str(getattr(obj, "FA_TargetLevel", "") or "").strip()
        if target_name and hasattr(doc, "getObject"):
            target = doc.getObject(target_name)
            if target is not None and is_level(target) and target not in candidates:
                candidates.append(target)
        pending.extend(list(getattr(obj, "InList", []) or []))
    if len(candidates) == 1:
        return candidates[0]
    levels = collect_levels(doc)
    return levels[0] if len(levels) == 1 else None


def ensure_auxiliary_parent(doc, objects=None, legacy_key="master_sketches"):
    """Return the preferred support parent and its Level when available.

    New workflows use ``Level -> Auxiliares FA``. Only documents without an
    unambiguous BIM Level fall back to the old FA_Project support branch.
    """
    level = resolve_level_context(doc, objects=objects)
    if level is not None:
        migrate_legacy_support_to_level(doc, level)
        return ensure_level_auxiliary_group(doc, level), level
    _doc, _root, groups = ensure_project_support_structure(doc, keys=(legacy_key,))
    return groups[legacy_key], None


def adopt_auxiliary_sources(doc, level, objects, allow_any_type=False):
    """Adopt safe source objects into ``Auxiliares FA`` without visual duplicates.

    Root/legacy/direct-Level Sketches and spreadsheets are moved to the Level
    auxiliary group. Objects already used as a native ``Base`` are removed from
    redundant explicit groups but are *not* added to Auxiliares, because the
    Base relation already gives them their natural tree parent. Objects inside
    an unrelated user group are left untouched.
    """
    if level is None or not is_level(level):
        return []
    candidates = []
    for obj in list(objects or []):
        if obj is None or obj is level or is_building(obj) or is_level(obj):
            continue
        type_id = str(getattr(obj, "TypeId", "") or "")
        is_support_type = type_id.startswith("Sketcher::") or type_id.startswith("Spreadsheet::")
        if not (allow_any_type or is_support_type):
            continue
        if obj not in candidates:
            candidates.append(obj)
    if not candidates:
        return []

    aux = ensure_level_auxiliary_group(doc, level)
    moved = []
    for obj in candidates:
        group_parents = _explicit_group_parents(obj)
        unsafe = [parent for parent in group_parents if not _is_safe_support_parent(parent, level, aux)]
        if unsafe:
            continue

        # Remove obsolete support/direct-Level membership first.
        for parent in list(group_parents):
            if _is_safe_support_parent(parent, level, aux) and parent is not aux:
                _remove_from_container(parent, obj)

        if _has_native_base_parent(obj):
            # The Base relationship is the canonical visible parent.
            moved.append(obj)
            continue

        add_to_container(aux, obj)
        tag_target_level(level, obj)
        moved.append(obj)
    return moved


def migrate_legacy_support_to_level(
    doc,
    level,
    keys=("parameters", "master_sketches", "areas", "tables"),
):
    """Collapse generated FA_Project support branches into one Level auxiliary group.

    Geometry and semantic BIM objects are not changed. Only explicit group
    membership is normalized. Unknown/user groups are never migrated.
    """
    if level is None or not is_level(level):
        return {"moved": 0, "removed_groups": 0, "removed_root": False}
    legacy_groups = []
    for key in tuple(keys or ()):
        if key not in GROUPS:
            continue
        name, _label = GROUPS[key]
        group = doc.getObject(name) if hasattr(doc, "getObject") else None
        if group is not None:
            legacy_groups.append(group)
    root = doc.getObject(ROOT_GROUP_NAME) if hasattr(doc, "getObject") else None
    if not legacy_groups and root is None:
        return {"moved": 0, "removed_groups": 0, "removed_root": False}

    aux = None
    moved = 0
    removed_groups = 0
    for group in legacy_groups:
        for child in list(getattr(group, "Group", []) or []):
            _remove_from_container(group, child)
            if _has_native_base_parent(child):
                moved += 1
                continue
            if aux is None:
                aux = ensure_level_auxiliary_group(doc, level)
            add_to_container(aux, child)
            try:
                tag_target_level(level, child)
            except Exception:
                pass
            moved += 1
        if not list(getattr(group, "Group", []) or []):
            if root is not None:
                _remove_from_container(root, group)
            try:
                if hasattr(doc, "getObject") and doc.getObject(group.Name) is not None:
                    doc.removeObject(group.Name)
                    removed_groups += 1
            except Exception as exc:
                warn("No se pudo retirar grupo legacy %s: %s" % (getattr(group, "Label", group.Name), exc))

    removed_root = False
    if root is not None and bool(getattr(root, "FA_Workbench", False)):
        if not list(getattr(root, "Group", []) or []):
            try:
                if doc.getObject(root.Name) is not None:
                    doc.removeObject(root.Name)
                    removed_root = True
            except Exception as exc:
                warn("No se pudo retirar FA_Project vacio: %s" % exc)
    if moved:
        msg("Arbol BIM normalizado: auxiliares migrados=%d" % moved)
    return {"moved": moved, "removed_groups": removed_groups, "removed_root": removed_root}


def _explicit_group_parents(obj):
    result = []
    for parent in list(getattr(obj, "InList", []) or []):
        try:
            if obj in list(getattr(parent, "Group", []) or []):
                result.append(parent)
        except Exception:
            continue
    return result


def _has_native_base_parent(obj):
    for parent in list(getattr(obj, "InList", []) or []):
        try:
            base = getattr(parent, "Base", None)
        except Exception:
            base = None
        if base is obj:
            return True
        if isinstance(base, (tuple, list)) and base and base[0] is obj:
            return True
    return False


def _is_safe_support_parent(parent, level, aux):
    if parent is level or parent is aux:
        return True
    name = str(getattr(parent, "Name", "") or "")
    if name == ROOT_GROUP_NAME:
        return True
    return name in {value[0] for value in GROUPS.values()}


def _remove_from_container(container, obj):
    try:
        members = list(getattr(container, "Group", []) or [])
    except Exception:
        members = []
    if obj not in members:
        return
    try:
        if hasattr(container, "removeObject"):
            container.removeObject(obj)
        else:
            container.Group = [member for member in members if member is not obj]
    except Exception as exc:
        warn("No se pudo retirar %s de %s: %s" % (
            getattr(obj, "Label", getattr(obj, "Name", obj)),
            getattr(container, "Label", getattr(container, "Name", container)),
            exc,
        ))


def add_to_container(container, obj):
    """Use the native GroupExtension API exposed by BuildingPart."""
    if obj not in list(getattr(container, "Group", []) or []):
        if hasattr(container, "addObject"):
            container.addObject(obj)
        elif hasattr(container, "addObjects"):
            container.addObjects([obj])
        else:
            group = list(getattr(container, "Group", []) or [])
            group.append(obj)
            container.Group = group


def _best_existing_building(doc, requested_label):
    buildings = collect_buildings(doc)
    exact = [obj for obj in buildings if _matches_label(obj, requested_label)]
    if len(exact) == 1:
        return exact[0]
    generated = [obj for obj in buildings if _is_fa_generated(obj)]
    if len(generated) == 1:
        return generated[0]
    return buildings[0] if len(buildings) == 1 else None


def _best_existing_level(doc, building, requested_label):
    contained = collect_levels(doc, building)
    exact = [obj for obj in contained if _matches_label(obj, requested_label)]
    if len(exact) == 1:
        return exact[0]
    generated = [obj for obj in contained if _is_fa_generated(obj)]
    if len(generated) == 1:
        return generated[0]
    if len(contained) == 1:
        return contained[0]
    all_levels = collect_levels(doc)
    exact = [obj for obj in all_levels if _matches_label(obj, requested_label)]
    if len(exact) == 1:
        add_to_container(building, exact[0])
        return exact[0]
    return None


def _set_level_elevation(level, elevation):
    if hasattr(level, "LevelOffset"):
        try:
            level.LevelOffset = elevation
        except Exception:
            pass
    try:
        placement = FreeCAD.Placement(level.Placement)
        placement.Base.z = elevation
        level.Placement = placement
    except Exception:
        pass


def _tag_structure(obj, role):
    set_prop(
        obj,
        "App::PropertyString",
        "FA_GeneratedBy",
        "FacilArquitectura",
        "Generador o adaptador",
        GENERATED_BY_STRUCTURE,
    )
    set_prop(
        obj,
        "App::PropertyString",
        "FA_Role",
        "FacilArquitectura",
        "Rol de trazabilidad",
        role,
    )


def _is_fa_generated(obj):
    return str(getattr(obj, "FA_GeneratedBy", "") or "") == GENERATED_BY_STRUCTURE


def _matches_label(obj, requested):
    value = str(requested or "").strip().casefold()
    return value in {
        str(getattr(obj, "Name", "") or "").strip().casefold(),
        str(getattr(obj, "Label", "") or "").strip().casefold(),
    }


def _require_arch_structure():
    required = ("makeBuilding", "makeFloor")
    if Arch is None or any(not hasattr(Arch, name) for name in required):
        raise UserFacingError(
            "Arch/BIM no ofrece makeBuilding y makeFloor en esta instalacion de FreeCAD."
        )
