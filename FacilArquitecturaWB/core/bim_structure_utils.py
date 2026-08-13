"""Native BIM spatial structure helpers for FacilArquitecturaWB.

Descripcion: crea y reutiliza Building y Building Storey nativos de FreeCAD.
Objetivo: organizar reconstrucciones desde Sketches sin crear una jerarquia FA paralela.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 21:24 UTC-06:00.
Version: 0.1.0.
Instrucciones de mantenimiento: conservar Arch.makeBuilding/makeFloor como autoridad
y no reemplazar objetos BIM manuales del usuario durante una reejecucion.
"""

from __future__ import annotations

import FreeCAD

from .command_errors import UserFacingError
from .project_structure import msg, set_prop

try:
    import Arch
except Exception:  # pragma: no cover - depende del runtime de FreeCAD
    Arch = None


GENERATED_BY_STRUCTURE = "FA_CreateBIMStructure"
DEFAULT_BUILDING_NAME = "Edificio"
DEFAULT_LEVEL_NAME = "Nivel 00"


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
    doc.recompute()
    return {
        "building": building,
        "level": level,
        "created_building": created_building,
        "created_level": created_level,
    }


def add_to_level(level, obj, source_sketch=None):
    """Place an architectural object in a native Level and add trace links."""
    if not is_level(level):
        raise UserFacingError("El contenedor destino no es un Level BIM nativo.")
    add_to_container(level, obj)
    set_prop(
        obj,
        "App::PropertyString",
        "FA_TargetLevel",
        "FacilArquitectura",
        "Clave del nivel BIM destino; la relacion autoritativa es Group",
        str(getattr(level, "Name", "") or ""),
    )
    # Do not create reverse PropertyLinks to a native container. BuildingPart
    # Group is the authoritative containment relation; reverse links create a
    # cyclic document graph in FreeCAD. Source traceability remains on the Wall.
    del source_sketch
    return obj


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
