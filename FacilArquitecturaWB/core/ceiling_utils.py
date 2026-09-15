"""Suspended modular ceiling helpers for FacilArquitecturaWB.

Descripcion: genera cielos de 600x600 rectangulares o poligonales y reserva luminarias ElectricCR.
Funcion principal: conservar la logica modular existente e integrar la salida dentro del Level BIM.
Mantenimiento: la reticula es auxiliar; el cielo conserva semantica IFC Covering/CEILING hasta validar Covering nativo.
Las zonas de exclusion entran como poligonos XY del mundo. Por defecto recortan paneles al generarlos; de forma opt-in pueden materializarse como un Part::Cut paramétrico ligado al Placement de su propietario.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-09-15 15:20 America/Costa_Rica.
Version: 0.7.3.
"""

from __future__ import annotations

import json
import math
import re

import FreeCAD
import Part

from .command_errors import UserFacingError
from .project_structure import ensure_group, set_prop, warn


GENERATED_BY_CEILING = "FA_CreateModularCeiling"
CEILING_GROUP_NAME = "FA_Ceilings"
CEILING_SHEET_NAME = "Spreadsheet_CielosSuspendidos"
EPSILON = 1.0e-6
MIN_CLIPPED_FACE_AREA_MM2 = 1.0


def axis_segments(length, module=600.0, phase=0.0):
    """Partition an axis using a repeating module and clipped perimeter cells."""
    length = float(length)
    module = float(module)
    if length <= EPSILON or module <= EPSILON:
        raise ValueError("La longitud y el modulo deben ser mayores que cero.")
    phase = float(phase) % module
    boundaries = [0.0]
    value = phase
    if value <= EPSILON:
        value = module
    while value < length - EPSILON:
        boundaries.append(value)
        value += module
    boundaries.append(length)
    boundaries = sorted({round(max(0.0, min(length, value)), 6) for value in boundaries})
    return [(boundaries[index], boundaries[index + 1]) for index in range(len(boundaries) - 1)]


def balanced_phase(length, module=600.0):
    """Return a grid phase that balances the two perimeter cuts."""
    length = float(length)
    module = float(module)
    remainder = length % module
    if remainder <= EPSILON or module - remainder <= EPSILON:
        return 0.0
    return remainder / 2.0


def wrapped_distance(value, target, period):
    """Shortest signed distance between two periodic values."""
    period = float(period)
    return ((float(value) - float(target) + period / 2.0) % period) - period / 2.0


def choose_axis_phase(length, positions, module=600.0, align_lights=True):
    """Choose a grid phase, prioritizing luminaire centres and then balanced cuts."""
    module = float(module)
    base = balanced_phase(length, module)
    usable = [float(value) for value in positions or [] if 0.0 <= float(value) <= float(length)]
    if not align_lights or not usable:
        return base
    candidates = [base]
    candidates.extend((value - module / 2.0) % module for value in usable)
    best_phase = base
    best_score = None
    for phase in candidates:
        alignment = sum(
            wrapped_distance(value, phase + module / 2.0, module) ** 2 for value in usable
        )
        balance = wrapped_distance(phase, base, module) ** 2
        score = alignment + balance * 0.02
        if best_score is None or score < best_score:
            best_score = score
            best_phase = phase
    return float(best_phase)


def plan_modular_ceiling(
    length,
    depth,
    luminaires=None,
    module=600.0,
    alignment_tolerance=50.0,
    align_lights=True,
):
    """Build a pure-data ceiling plan and reserve cells occupied by luminaires.

    Luminaires are dictionaries containing at least ``x`` and ``y`` in room-local
    coordinates. Existing positions are never modified.
    """
    length = float(length)
    depth = float(depth)
    module = float(module)
    tolerance = max(0.0, float(alignment_tolerance))
    if min(length, depth, module) <= EPSILON:
        raise ValueError("Las dimensiones del recinto y el modulo deben ser positivas.")
    lights = list(luminaires or [])
    inside = [
        light
        for light in lights
        if -EPSILON <= float(light["x"]) <= length + EPSILON
        and -EPSILON <= float(light["y"]) <= depth + EPSILON
    ]
    outside = [light for light in lights if light not in inside]
    phase_x = choose_axis_phase(length, [light["x"] for light in inside], module, align_lights)
    phase_y = choose_axis_phase(depth, [light["y"] for light in inside], module, align_lights)
    x_segments = axis_segments(length, module, phase_x)
    y_segments = axis_segments(depth, module, phase_y)

    cells = []
    for row, (y0, y1) in enumerate(y_segments):
        for column, (x0, x1) in enumerate(x_segments):
            cells.append(
                {
                    "row": row,
                    "column": column,
                    "x0": x0,
                    "x1": x1,
                    "y0": y0,
                    "y1": y1,
                    "width": x1 - x0,
                    "depth": y1 - y0,
                    "full": abs((x1 - x0) - module) <= 0.01
                    and abs((y1 - y0) - module) <= 0.01,
                }
            )

    reserved = set()
    assignments = []
    cell_by_index = {(cell["row"], cell["column"]): cell for cell in cells}
    for light in inside:
        x = min(length - EPSILON, max(0.0, float(light["x"])))
        y = min(depth - EPSILON, max(0.0, float(light["y"])))
        column = _segment_index(x_segments, x)
        row = _segment_index(y_segments, y)
        cell = cell_by_index[(row, column)]
        centre_x = (cell["x0"] + cell["x1"]) / 2.0
        centre_y = (cell["y0"] + cell["y1"]) / 2.0
        error = math.hypot(x - centre_x, y - centre_y)
        collision = (row, column) in reserved
        reserved.add((row, column))
        assignments.append(
            {
                "light": light,
                "row": row,
                "column": column,
                "centre_x": centre_x,
                "centre_y": centre_y,
                "error": error,
                "full_cell": bool(cell["full"]),
                "collision": collision,
                "aligned": bool(error <= tolerance and cell["full"] and not collision),
            }
        )

    panel_cells = [cell for cell in cells if (cell["row"], cell["column"]) not in reserved]
    full_panels = sum(1 for cell in panel_cells if cell["full"])
    partial_panels = len(panel_cells) - full_panels
    incompatible = sum(1 for assignment in assignments if not assignment["aligned"]) + len(outside)
    return {
        "length": length,
        "depth": depth,
        "module": module,
        "phase_x": phase_x,
        "phase_y": phase_y,
        "x_segments": x_segments,
        "y_segments": y_segments,
        "cells": cells,
        "panel_cells": panel_cells,
        "reserved_cells": sorted(reserved),
        "assignments": assignments,
        "outside_luminaires": outside,
        "rows": len(y_segments),
        "columns": len(x_segments),
        "full_panels": full_panels,
        "partial_panels": partial_panels,
        "reserved_count": len(reserved),
        "incompatible_luminaires": incompatible,
    }


def collect_rooms(doc, selection=None):
    """Collect selected room faces, preferring polygonal wall-derived rooms."""
    selected = list(selection or [])
    candidates = _flatten_selection(selected) if selected else list(getattr(doc, "Objects", []) or [])
    spaces = [obj for obj in candidates if _is_bim_space(obj)]
    polygons = [obj for obj in candidates if _is_room_polygon(obj, selected=bool(selected))]
    rectangles = [obj for obj in candidates if _is_room_rectangle(obj, selected=bool(selected))]
    if not selected:
        if spaces:
            rooms = spaces
        elif polygons:
            rooms = polygons
        else:
            rooms = rectangles
        generated = [
            obj
            for obj in rooms
            if str(getattr(obj, "FA_GeneratedBy", "") or "") == "FA_RectangularAreaAnalysis"
        ]
        if generated and not polygons:
            rooms = generated
    else:
        rooms = spaces + [obj for obj in polygons if obj not in spaces]
        rooms += [obj for obj in rectangles if obj not in rooms]
    result = []
    seen = set()
    for room in rooms:
        name = str(getattr(room, "Name", "") or "")
        if name and name not in seen:
            seen.add(name)
            result.append(room)
    return result


def collect_room_rectangles(doc, selection=None):
    """Backward-compatible alias; now also returns polygonal room faces."""
    return collect_rooms(doc, selection)


def collect_electriccr_luminaires(doc):
    """Collect ElectricCR luminaires, including App::Link instances."""
    return [obj for obj in list(getattr(doc, "Objects", []) or []) if _is_luminaire(obj)]


def create_modular_ceilings(
    doc, bim_group, rooms, luminaires, options, level=None, schedule_group=None
):
    """Create one clipped compound ceiling per room inside the BIM Level.

    The grid remains part of the calculation contract, but its permanent 2D
    object is optional/documentary and disabled by default to keep the model
    tree compact.
    """
    rooms = list(rooms or [])
    if not rooms:
        raise UserFacingError("No hay recintos rectangulares o poligonales para crear cielos.")
    module = float(options.get("module_mm", 600.0))
    elevation = float(options.get("ceiling_elevation_mm", 2700.0))
    thickness = float(options.get("panel_thickness_mm", 15.0))
    gap = max(0.0, float(options.get("joint_gap_mm", 5.0)))
    tolerance = max(0.0, float(options.get("alignment_tolerance_mm", 50.0)))
    create_documentary_grid = bool(options.get("create_documentary_grid", False))
    exclusion_zones = _normalize_exclusion_zones(options.get("exclusion_zones_world_mm", []))
    exclusion_owner = options.get("exclusion_owner")
    exclusion_reason = str(options.get("exclusion_reason") or "")
    dynamic_exclusion_source = options.get("dynamic_exclusion_source")
    dynamic_exclusion_mode = str(options.get("dynamic_exclusion_mode") or "").strip().lower()
    group_name = str(options.get("group_name") or CEILING_GROUP_NAME)
    sheet_name = str(options.get("sheet_name") or CEILING_SHEET_NAME)
    group_label = str(options.get("group_label") or "Cielos suspendidos")
    if module <= 0.0 or thickness <= 0.0:
        raise UserFacingError("El modulo y el espesor del panel deben ser mayores que cero.")
    if bool(options.get("replace_previous", True)):
        remove_previous_ceilings(doc)

    target_parent = level if level is not None else bim_group
    ceiling_group = ensure_group(doc, group_name, group_label, target_parent)
    _move_generated_group_to_parent(ceiling_group, target_parent)
    if level is not None:
        set_prop(
            ceiling_group,
            "App::PropertyString",
            "FA_TargetLevel",
            "FacilArquitectura",
            "Nivel BIM que contiene los cielos",
            str(getattr(level, "Name", "") or ""),
        )
    plans = []
    created_objects = []
    all_lights = list(luminaires or [])
    for room in rooms:
        spec = _room_spec(room)
        local_lights = []
        source_lights = []
        for light in all_lights:
            point = _luminaire_world_point(light)
            local = _world_to_room_local(spec, point)
            if _point_inside_room(spec, local):
                local_lights.append(
                    {"x": local[0], "y": local[1], "name": _object_label(light), "object": light}
                )
                source_lights.append(light)
        plan = plan_modular_ceiling(
            spec["length"],
            spec["depth"],
            luminaires=local_lights,
            module=module,
            alignment_tolerance=tolerance,
            align_lights=bool(options.get("align_to_luminaires", True)),
        )
        if spec["geometry"] == "polygon":
            _clip_plan_to_polygon(spec, plan)
        plan["room"] = room
        plan["room_label"] = _room_name(room)
        plan["geometry"] = spec["geometry"]
        panels = _create_room_panels(
            doc,
            ceiling_group,
            spec,
            plan,
            elevation,
            thickness,
            gap,
            exclusion_zones_world_mm=exclusion_zones,
            dynamic_exclusion_source=(
                dynamic_exclusion_source if dynamic_exclusion_mode == "follow_placement" else None
            ),
        )
        _set_common_ceiling_properties(panels, room, source_lights, plan, elevation, thickness)
        if int(plan.get("exclusion_zone_count", 0)) > 0:
            set_prop(panels, "App::PropertyInteger", "FA_ExclusionZoneCount", "FacilArquitectura", "Cantidad de zonas de exclusion", int(plan.get("exclusion_zone_count", 0)))
            set_prop(panels, "App::PropertyString", "FA_ExclusionZonesJSON", "FacilArquitectura", "Zonas de exclusion XY", json.dumps(exclusion_zones, sort_keys=True, separators=(",", ":")))
            set_prop(panels, "App::PropertyString", "FA_ExclusionReason", "FacilArquitectura", "Motivo de exclusion", exclusion_reason)
            if exclusion_owner is not None:
                # The stair master links back to these panels. Store only the
                # owner name here to keep the dependency graph acyclic.
                set_prop(panels, "App::PropertyString", "FA_ExclusionOwnerName", "FacilArquitectura", "Elemento que solicita la exclusion", str(getattr(exclusion_owner, "Name", "") or ""))
        set_prop(panels, "App::PropertyString", "IfcType", "IFC", "Clase IFC", "Covering")
        set_prop(panels, "App::PropertyString", "PredefinedType", "IFC", "Tipo IFC", "CEILING")
        _set_view(panels, color=(0.92, 0.92, 0.88), transparency=0)
        created_objects.append(panels)
        if create_documentary_grid:
            grid = _create_room_grid(doc, schedule_group or ceiling_group, spec, plan, elevation)
            _set_common_ceiling_properties(grid, room, source_lights, plan, elevation, 0.0)
            set_prop(
                grid,
                "App::PropertyBool",
                "FA_DocumentaryOnly",
                "FacilArquitectura",
                "Objeto auxiliar de documentacion 2D",
                True,
            )
            _set_view(grid, color=(0.35, 0.35, 0.35), transparency=0)
            created_objects.append(grid)
        plans.append(plan)

    sheet = _write_ceiling_schedule(doc, plans, schedule_group or ceiling_group, options, sheet_name=sheet_name)
    created_objects.append(sheet)
    doc.recompute()
    exclusion_objects = [
        obj
        for obj in created_objects
        if int(getattr(obj, "FA_ExclusionZoneCount", 0) or 0) > 0
    ]
    return {
        "group": ceiling_group,
        "plans": plans,
        "objects": created_objects,
        "sheet": sheet,
        "documentary_grid": create_documentary_grid,
        "exclusion_objects": exclusion_objects,
        "exclusion_zone_count": sum(int(plan.get("exclusion_zone_count", 0)) for plan in plans),
    }


def _move_generated_group_to_parent(group, parent):
    """Keep FA_Ceilings in only one explicit container to avoid duplicated tree branches."""
    if group is None or parent is None:
        return
    for container in list(getattr(group, "InList", []) or []):
        if container is parent:
            continue
        members = list(getattr(container, "Group", []) or [])
        if group not in members:
            continue
        try:
            if hasattr(container, "removeObject"):
                container.removeObject(group)
            else:
                container.Group = [obj for obj in members if obj is not group]
        except Exception as exc:
            warn("No se pudo retirar Cielos suspendidos de %s: %s" % (_object_label(container), exc))
    try:
        if group not in list(getattr(parent, "Group", []) or []):
            parent.addObject(group)
    except Exception as exc:
        warn("No se pudo integrar Cielos suspendidos al contenedor BIM: %s" % exc)


def remove_previous_ceilings(doc):
    """Remove only generated ceiling geometry and its generated schedule."""
    tagged = [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == GENERATED_BY_CEILING
    ]
    removed = 0
    for obj in tagged:
        if str(getattr(obj, "Name", "") or "") == CEILING_GROUP_NAME:
            continue
        try:
            if doc.getObject(obj.Name) is not None:
                doc.removeObject(obj.Name)
                removed += 1
        except Exception as exc:
            warn("No se pudo eliminar %s: %s" % (_object_label(obj), exc))
    if removed:
        doc.recompute()
    return removed


def _segment_index(segments, value):
    for index, (start, end) in enumerate(segments):
        if start - EPSILON <= value < end - EPSILON or index == len(segments) - 1:
            return index
    return len(segments) - 1


def _flatten_selection(selection):
    pending = list(selection or [])
    result = []
    seen = set()
    while pending:
        obj = pending.pop(0)
        identity = str(getattr(obj, "Name", "") or id(obj))
        if identity in seen:
            continue
        seen.add(identity)
        result.append(obj)
        for attr in ("Group", "Objects"):
            try:
                pending.extend(list(getattr(obj, attr, []) or []))
            except Exception:
                pass
    return result


def _is_bim_space(obj):
    """Return True for native Arch/BIM Space objects, including FA-tagged Spaces."""
    role = str(getattr(obj, "FA_Role", "") or "").strip().lower()
    ifc_type = str(getattr(obj, "IfcType", "") or "").strip().lower()
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "").strip().lower()
    return bool(role == "bim_space" or ifc_type == "space" or proxy_type == "space")


def _space_polygon_spec(room):
    """Return an exact polygon spec when a Space exposes FA_FloorPolygonJSON."""
    raw = str(getattr(room, "FA_FloorPolygonJSON", "") or "").strip()
    if not raw:
        return None
    try:
        points = json.loads(raw)
        points = [(float(point[0]), float(point[1])) for point in points]
        if len(points) < 3:
            return None
        origin_x = min(point[0] for point in points)
        origin_y = min(point[1] for point in points)
        local = [(x - origin_x, y - origin_y) for x, y in points]
        vectors = [FreeCAD.Vector(x, y, 0.0) for x, y in local]
        wire = Part.makePolygon(vectors + [vectors[0]])
        face = Part.Face(wire)
        bounds = face.BoundBox
        if float(face.Area) <= EPSILON or bounds.XLength <= EPSILON or bounds.YLength <= EPSILON:
            return None
        return {
            "room": room,
            "geometry": "polygon",
            "length": float(bounds.XLength),
            "depth": float(bounds.YLength),
            "base": FreeCAD.Vector(origin_x, origin_y, 0.0),
            "rotation": FreeCAD.Rotation(),
            "face": face,
            "room_area_mm2": float(face.Area),
        }
    except Exception:
        return None


def _is_room_rectangle(obj, selected=False):
    try:
        length = _quantity_value(obj.Length)
        depth = _quantity_value(obj.Height)
    except Exception:
        return False
    if length < 200.0 or depth < 200.0:
        return False
    text = (str(getattr(obj, "Name", "")) + " " + _object_label(obj)).lower()
    excluded = ("puerta", "door", "ventana", "window", "lumin", "grid", "cuadricula")
    if any(token in text for token in excluded):
        return False
    generated = str(getattr(obj, "FA_GeneratedBy", "") or "")
    role = str(getattr(obj, "FA_Role", "") or "").lower()
    type_id = str(getattr(obj, "TypeId", "") or "")
    return bool(
        generated == "FA_RectangularAreaAnalysis"
        or role in ("room", "area", "room_area")
        or (selected and ("Part2DObject" in type_id or "Rectangle" in text))
    )


def _is_room_polygon(obj, selected=False):
    generated = str(getattr(obj, "FA_GeneratedBy", "") or "")
    role = str(getattr(obj, "FA_Role", "") or "").lower()
    electric_type = str(getattr(obj, "ElectricCRTipo", "") or "").lower()
    try:
        faces = list(obj.Shape.Faces)
    except Exception:
        return False
    if not faces:
        return False
    return bool(
        generated == "FA_PolygonalRoomsFromArchWalls"
        or role == "room_polygon"
        or (selected and electric_type == "area" and not hasattr(obj, "Length"))
    )


def _is_luminaire(obj):
    type_id = str(getattr(obj, "TypeId", "") or "")
    label_text = (str(getattr(obj, "Name", "")) + " " + _object_label(obj)).strip().lower()
    if type_id != "App::Link" and (
        hasattr(obj, "LnkMasterKey") or label_text.startswith("master")
    ):
        return False
    candidates = [obj]
    for attr in ("LinkedObject", "Link"):
        linked = getattr(obj, attr, None)
        if linked is not None:
            candidates.append(linked)
    for candidate in candidates:
        tipo = str(getattr(candidate, "Tipo", "") or "").strip().lower()
        if tipo == "luminaria" or "luminaria" in tipo:
            return True
    if type_id in ("Spreadsheet::Sheet", "App::DocumentObjectGroup"):
        return False
    return "luminaria" in label_text


def _room_spec(room):
    if _is_bim_space(room):
        exact = _space_polygon_spec(room)
        if exact is not None:
            return exact
        try:
            bounds = room.Shape.BoundBox
            length = float(bounds.XLength)
            depth = float(bounds.YLength)
            if length <= EPSILON or depth <= EPSILON:
                raise ValueError("Space sin huella util")
            return {
                "room": room,
                "geometry": "rectangle",
                "length": length,
                "depth": depth,
                "base": FreeCAD.Vector(float(bounds.XMin), float(bounds.YMin), 0.0),
                "rotation": FreeCAD.Rotation(),
                "face": None,
                "room_area_mm2": length * depth,
            }
        except Exception as exc:
            raise UserFacingError("El Espacio BIM %s no tiene huella valida: %s" % (_object_label(room), exc))
    if _is_room_polygon(room, selected=True):
        try:
            source_face = max(list(room.Shape.Faces), key=lambda face: float(face.Area))
            face = source_face.copy()
            bounds = face.BoundBox
            origin_x = float(bounds.XMin)
            origin_y = float(bounds.YMin)
            origin_z = float(bounds.ZMin)
            face.translate(FreeCAD.Vector(-origin_x, -origin_y, -origin_z))
            local_bounds = face.BoundBox
            length = float(local_bounds.XLength)
            depth = float(local_bounds.YLength)
            if length <= EPSILON or depth <= EPSILON or float(face.Area) <= EPSILON:
                raise ValueError("cara sin dimensiones")
            return {
                "room": room,
                "geometry": "polygon",
                "length": length,
                "depth": depth,
                "base": FreeCAD.Vector(origin_x, origin_y, 0.0),
                "rotation": FreeCAD.Rotation(),
                "face": face,
                "room_area_mm2": float(face.Area),
            }
        except Exception as exc:
            raise UserFacingError(
                "El recinto poligonal %s no tiene una cara valida: %s" % (_object_label(room), exc)
            )
    try:
        length = _quantity_value(room.Length)
        depth = _quantity_value(room.Height)
    except Exception as exc:
        raise UserFacingError("El recinto %s no tiene Length/Height validos: %s" % (_object_label(room), exc))
    placement = getattr(room, "Placement", FreeCAD.Placement())
    base = getattr(placement, "Base", FreeCAD.Vector(0.0, 0.0, 0.0))
    rotation = getattr(placement, "Rotation", FreeCAD.Rotation())
    return {
        "room": room,
        "geometry": "rectangle",
        "length": length,
        "depth": depth,
        "base": base,
        "rotation": rotation,
        "face": None,
        "room_area_mm2": length * depth,
    }


def _luminaire_world_point(light):
    try:
        return light.getGlobalPlacement().Base
    except Exception:
        pass
    try:
        return light.Placement.Base
    except Exception:
        return FreeCAD.Vector(0.0, 0.0, 0.0)


def _world_to_room_local(spec, point):
    delta = FreeCAD.Vector(float(point.x - spec["base"].x), float(point.y - spec["base"].y), 0.0)
    try:
        local = spec["rotation"].inverted().multVec(delta)
        return float(local.x), float(local.y)
    except Exception:
        return float(delta.x), float(delta.y)


def _point_inside_room(spec, local):
    x, y = float(local[0]), float(local[1])
    if not (-EPSILON <= x <= spec["length"] + EPSILON and -EPSILON <= y <= spec["depth"] + EPSILON):
        return False
    if spec.get("geometry") != "polygon":
        return True
    try:
        return bool(spec["face"].isInside(FreeCAD.Vector(x, y, 0.0), 0.1, True))
    except Exception:
        return False


def _local_to_world(spec, x, y, z):
    vector = FreeCAD.Vector(float(x), float(y), 0.0)
    try:
        vector = spec["rotation"].multVec(vector)
    except Exception:
        pass
    return FreeCAD.Vector(vector.x + spec["base"].x, vector.y + spec["base"].y, float(z))


def _place_local_shape(shape, spec, z):
    """Compose the room transform without discarding an OCCT subshape placement."""
    placed = shape.copy()
    room_placement = FreeCAD.Placement(
        FreeCAD.Vector(spec["base"].x, spec["base"].y, float(z)), spec["rotation"]
    )
    try:
        placed.Placement = room_placement.multiply(placed.Placement)
    except Exception:
        placed.Placement = room_placement
    return placed


def _local_rectangle_face(x0, y0, x1, y1):
    points = [
        FreeCAD.Vector(float(x0), float(y0), 0.0),
        FreeCAD.Vector(float(x1), float(y0), 0.0),
        FreeCAD.Vector(float(x1), float(y1), 0.0),
        FreeCAD.Vector(float(x0), float(y1), 0.0),
        FreeCAD.Vector(float(x0), float(y0), 0.0),
    ]
    return Part.Face(Part.makePolygon(points))


def _clip_plan_to_polygon(spec, plan):
    """Discard outside cells and attach exact polygon intersections to the plan."""
    clipped_cells = []
    for cell in list(plan["cells"]):
        cell_face = _local_rectangle_face(cell["x0"], cell["y0"], cell["x1"], cell["y1"])
        clipped = spec["face"].common(cell_face)
        clipped_area = sum(float(face.Area) for face in list(getattr(clipped, "Faces", []) or []))
        if clipped_area <= MIN_CLIPPED_FACE_AREA_MM2:
            continue
        item = dict(cell)
        item["clip_shape"] = clipped
        item["clip_area_mm2"] = clipped_area
        original_area = float(cell["width"]) * float(cell["depth"])
        item["boundary_clipped"] = clipped_area < original_area - max(1.0, original_area * 1.0e-7)
        item["full"] = bool(item["full"] and not item["boundary_clipped"])
        clipped_cells.append(item)

    reserved = set(tuple(value) for value in plan["reserved_cells"])
    plan["cells"] = clipped_cells
    plan["panel_cells"] = [
        cell for cell in clipped_cells if (cell["row"], cell["column"]) not in reserved
    ]
    plan["full_panels"] = sum(1 for cell in plan["panel_cells"] if cell["full"])
    plan["partial_panels"] = len(plan["panel_cells"]) - plan["full_panels"]
    plan["clipped_cell_count"] = sum(1 for cell in clipped_cells if cell["boundary_clipped"])
    plan["room_area_mm2"] = float(spec["room_area_mm2"])
    plan["planned_panel_area_mm2"] = sum(
        float(cell["clip_area_mm2"]) for cell in plan["panel_cells"]
    )


def _normalize_exclusion_zones(zones):
    """Return JSON-safe world-XY exclusion zones, ignoring malformed entries."""
    result = []
    for index, raw in enumerate(list(zones or [])):
        data = dict(raw) if isinstance(raw, dict) else {"polygon_mm": raw}
        polygon = []
        for point in list(data.get("polygon_mm", []) or []):
            try:
                polygon.append([float(point[0]), float(point[1])])
            except Exception:
                polygon = []
                break
        if len(polygon) < 3:
            continue
        result.append(
            {
                "id": str(data.get("id") or data.get("role") or "zone_%d" % index),
                "role": str(data.get("role") or "exclusion"),
                "polygon_mm": polygon,
            }
        )
    return result


def _world_exclusion_faces(spec, zones):
    """Convert world-XY exclusion polygons to room-local faces that overlap the room."""
    if not zones:
        return []
    if spec.get("geometry") == "polygon":
        room_face = spec["face"]
    else:
        room_face = _local_rectangle_face(0.0, 0.0, spec["length"], spec["depth"])
    result = []
    for zone in _normalize_exclusion_zones(zones):
        local_points = []
        for x, y in zone["polygon_mm"]:
            delta = FreeCAD.Vector(float(x) - spec["base"].x, float(y) - spec["base"].y, 0.0)
            try:
                local = spec["rotation"].inverted().multVec(delta)
            except Exception:
                local = delta
            local_points.append(FreeCAD.Vector(float(local.x), float(local.y), 0.0))
        try:
            wire = Part.makePolygon(local_points + [FreeCAD.Vector(local_points[0])])
            face = Part.Face(wire)
            overlap = room_face.common(face)
            area = sum(float(item.Area) for item in list(getattr(overlap, "Faces", []) or []))
            if area > MIN_CLIPPED_FACE_AREA_MM2:
                result.append(overlap)
        except Exception as exc:
            warn("No se pudo preparar una zona de exclusion de cielorraso: %s" % exc)
    return result



def _shape_bbox_xy(shape):
    if shape is None:
        return None
    try:
        if shape.isNull():
            return None
        bb = shape.BoundBox
        return (float(bb.XMin), float(bb.YMin), float(bb.XMax), float(bb.YMax))
    except Exception:
        return None


def _bbox_overlaps(a, b, tolerance=0.0):
    if a is None or b is None:
        return False
    tol = max(0.0, float(tolerance))
    return not (
        float(a[2]) < float(b[0]) - tol
        or float(a[0]) > float(b[2]) + tol
        or float(a[3]) < float(b[1]) - tol
        or float(a[1]) > float(b[3]) + tol
    )


def _fuse_exclusion_faces(faces):
    valid = []
    for face in list(faces or []):
        try:
            if face is None or face.isNull():
                continue
        except Exception:
            continue
        valid.append(face)
    if not valid:
        return Part.Shape()
    result = valid[0]
    for face in valid[1:]:
        result = result.fuse(face)
    try:
        result = result.removeSplitter()
    except Exception:
        pass
    return result

def _cut_face_by_exclusions(face, exclusions):
    result = face
    for exclusion in list(exclusions or []):
        try:
            if result is None or result.isNull():
                break
            if exclusion is None or exclusion.isNull():
                continue
            result = result.cut(exclusion)
            # A previous exclusion may remove the complete panel. In that case
            # there is nothing left to cut; continuing would ask OCCT to operate
            # on a Null shape and emit a misleading warning.
            if result is None or result.isNull():
                break
        except Exception as exc:
            warn("No se pudo recortar un panel por zona de exclusion: %s" % exc)
    return result


def _global_placement(obj):
    """Return the current global Placement for a GeoFeature-like object."""
    if obj is None:
        return FreeCAD.Placement()
    try:
        return obj.getGlobalPlacement()
    except Exception:
        try:
            return FreeCAD.Placement(obj.Placement)
        except Exception:
            return FreeCAD.Placement()


def _dynamic_exclusion_solid(zones, placement_source, z_min, z_max):
    """Build one exclusion solid in ``placement_source`` local coordinates.

    The returned Shape stays geometrically local; a caller can therefore drive a
    normal Part::Feature Placement from the stair master without regenerating the
    ceiling grid. This path is deliberately opt-in for the minimal stair demo.
    """
    normalized = _normalize_exclusion_zones(zones)
    if not normalized or placement_source is None:
        return Part.Shape(), []
    inv = _global_placement(placement_source).inverse()
    solids = []
    local_zones = []
    for zone in normalized:
        polygon = list(zone.get("polygon_mm", []) or [])
        if len(polygon) < 3:
            continue
        local_points = [
            inv.multVec(FreeCAD.Vector(float(x), float(y), float(z_min)))
            for x, y in polygon
        ]
        if len(local_points) < 3:
            continue
        try:
            wire = Part.makePolygon(local_points + [FreeCAD.Vector(local_points[0])])
            face = Part.Face(wire)
            probe = inv.multVec(FreeCAD.Vector(float(polygon[0][0]), float(polygon[0][1]), float(z_max)))
            direction = probe.sub(local_points[0])
            solid = face.extrude(direction)
            if solid is not None and not solid.isNull():
                solids.append(solid)
                local_zone = dict(zone)
                local_zone["polygon_mm"] = [[float(point.x), float(point.y)] for point in local_points]
                local_zones.append(local_zone)
        except Exception as exc:
            warn("No se pudo preparar una zona dinamica de cielorraso: %s" % exc)
    if not solids:
        return Part.Shape(), local_zones
    result = solids[0]
    for solid in solids[1:]:
        try:
            result = result.fuse(solid)
        except Exception:
            result = Part.makeCompound([result, solid])
    try:
        result = result.removeSplitter()
    except Exception:
        pass
    return result, local_zones


def _make_dynamic_ceiling_cut(doc, group, base_shape, zones, elevation, thickness, placement_source, room_label):
    """Return a native Part::Cut whose opening follows ``placement_source``.

    The full modular ceiling remains fixed in building coordinates. Only the
    hidden cutter is expressed against the stair Placement, so translating or
    rotating the stair moves the opening while the ceiling itself stays put.
    """
    margin = max(5.0, float(thickness))
    z_min = float(elevation) - float(thickness) - margin
    z_max = float(elevation) + margin
    cutter_shape, local_zones = _dynamic_exclusion_solid(
        zones, placement_source, z_min, z_max
    )
    if cutter_shape is None or cutter_shape.isNull():
        raise RuntimeError("No se pudo construir el buque dinamico del cielorraso.")

    base = doc.addObject("Part::Feature", "FA_CeilingPanelsBase")
    base.Label = "Base cielo 600x600 - %s" % room_label
    base.Shape = base_shape
    _tag_generated(base, "ceiling_panels_base")
    set_prop(base, "App::PropertyBool", "FA_ConstructionOnly", "FacilArquitectura", "Geometria auxiliar", True)
    set_prop(base, "App::PropertyBool", "GameExportExclude", "FacilArquitectura", "Excluir de exportacion de juego", True)

    cutter = doc.addObject("Part::Feature", "FA_CeilingDynamicOpening")
    cutter.Label = "Buque cielorraso escalera - dinamico"
    cutter.Shape = cutter_shape
    _tag_generated(cutter, "ceiling_dynamic_opening")
    set_prop(cutter, "App::PropertyLink", "FA_PlacementSource", "FacilArquitectura", "Fuente de Placement", placement_source)
    set_prop(cutter, "App::PropertyString", "FA_LocalExclusionZonesJSON", "FacilArquitectura", "Zonas locales JSON", json.dumps(local_zones, sort_keys=True, separators=(",", ":")))
    set_prop(cutter, "App::PropertyBool", "FA_ConstructionOnly", "FacilArquitectura", "Volumen auxiliar de construccion", True)
    set_prop(cutter, "App::PropertyBool", "GameExportExclude", "FacilArquitectura", "Excluir de exportacion de juego", True)
    try:
        cutter.setExpression("Placement", "%s.Placement" % placement_source.Name)
    except Exception as exc:
        raise RuntimeError("No se pudo enlazar el buque del cielorraso al Placement de la escalera: %s" % exc)

    cut = doc.addObject("Part::Cut", "FA_CeilingPanels")
    cut.Label = "Cielo 600x600 - %s" % room_label
    cut.Base = base
    cut.Tool = cutter
    try:
        cut.Refine = True
    except Exception:
        pass
    group.addObject(cut)
    _tag_generated(cut, "ceiling_panels")
    set_prop(cut, "App::PropertyBool", "FA_DynamicExclusion", "FacilArquitectura", "Abertura ligada a Placement", True)
    set_prop(cut, "App::PropertyString", "FA_ExclusionPlacementSourceName", "FacilArquitectura", "Elemento que mueve la abertura", str(getattr(placement_source, "Name", "") or ""))
    try:
        base.ViewObject.Visibility = False
        cutter.ViewObject.Visibility = False
    except Exception:
        pass
    return cut


def _create_room_panels(
    doc,
    group,
    spec,
    plan,
    elevation,
    thickness,
    gap,
    exclusion_zones_world_mm=None,
    dynamic_exclusion_source=None,
):
    normalized_zones = _normalize_exclusion_zones(exclusion_zones_world_mm or [])
    dynamic = bool(dynamic_exclusion_source is not None and normalized_zones)
    # A dynamic opening must keep a complete, fixed ceiling as the Boolean Base.
    # The historical/static path continues clipping panel faces during generation.
    exclusion_faces = [] if dynamic else _world_exclusion_faces(spec, normalized_zones)
    exclusion_union = _fuse_exclusion_faces(exclusion_faces) if exclusion_faces else Part.Shape()
    exclusion_bbox = _shape_bbox_xy(exclusion_union)
    plan["exclusion_zone_count"] = len(normalized_zones) if dynamic else len(exclusion_faces)
    plan["exclusion_boolean_candidate_count"] = 0
    shapes = []
    for cell in plan["panel_cells"]:
        inset_x = min(gap / 2.0, cell["width"] / 4.0)
        inset_y = min(gap / 2.0, cell["depth"] / 4.0)
        width = max(0.1, cell["width"] - 2.0 * inset_x)
        depth = max(0.1, cell["depth"] - 2.0 * inset_y)
        cell_bbox = (
            float(cell["x0"] + inset_x),
            float(cell["y0"] + inset_y),
            float(cell["x1"] - inset_x),
            float(cell["y1"] - inset_y),
        )
        touches_exclusion = (not dynamic) and _bbox_overlaps(cell_bbox, exclusion_bbox, tolerance=EPSILON)

        # Fast path: untouched rectangular panel (also used for every panel when
        # the opening is a downstream parametric Part::Cut).
        if spec["geometry"] != "polygon" and not touches_exclusion:
            shape = Part.makeBox(
                width,
                depth,
                thickness,
                FreeCAD.Vector(cell["x0"] + inset_x, cell["y0"] + inset_y, elevation - thickness),
            )
            try:
                shape.Placement = FreeCAD.Placement(
                    FreeCAD.Vector(spec["base"].x, spec["base"].y, 0.0), spec["rotation"]
                )
            except Exception:
                pass
            shapes.append(shape)
            continue

        inset_face = _local_rectangle_face(
            cell["x0"] + inset_x,
            cell["y0"] + inset_y,
            cell["x1"] - inset_x,
            cell["y1"] - inset_y,
        )
        working = spec["face"].common(inset_face) if spec["geometry"] == "polygon" else inset_face
        if touches_exclusion and exclusion_bbox is not None:
            plan["exclusion_boolean_candidate_count"] += 1
            working = _cut_face_by_exclusions(working, [exclusion_union])
        for face in list(getattr(working, "Faces", []) or []):
            if float(face.Area) <= MIN_CLIPPED_FACE_AREA_MM2:
                continue
            placed = _place_local_shape(face, spec, elevation - thickness)
            shapes.append(placed.extrude(FreeCAD.Vector(0.0, 0.0, thickness)))

    compound = Part.makeCompound(shapes) if shapes else Part.Shape()
    if dynamic:
        obj = _make_dynamic_ceiling_cut(
            doc,
            group,
            compound,
            normalized_zones,
            elevation,
            thickness,
            dynamic_exclusion_source,
            _room_name(spec["room"]),
        )
    else:
        obj = doc.addObject("Part::Feature", "FA_CeilingPanels")
        obj.Label = "Cielo 600x600 - %s" % _room_name(spec["room"])
        obj.Shape = compound
        group.addObject(obj)
        _tag_generated(obj, "ceiling_panels")
    return obj

def _create_room_grid(doc, group, spec, plan, elevation):
    edges = []
    if spec["geometry"] == "polygon":
        for cell in plan["cells"]:
            for edge in list(getattr(cell.get("clip_shape"), "Edges", []) or []):
                edges.append(_place_local_shape(edge, spec, elevation))
    else:
        x_values = [0.0] + [segment[1] for segment in plan["x_segments"]]
        y_values = [0.0] + [segment[1] for segment in plan["y_segments"]]
        for x in sorted(set(x_values)):
            edges.append(Part.makeLine(_local_to_world(spec, x, 0.0, elevation), _local_to_world(spec, x, spec["depth"], elevation)))
        for y in sorted(set(y_values)):
            edges.append(Part.makeLine(_local_to_world(spec, 0.0, y, elevation), _local_to_world(spec, spec["length"], y, elevation)))
    obj = doc.addObject("Part::Feature", "FA_CeilingGrid")
    obj.Label = "Reticula cielo - %s" % _room_name(spec["room"])
    obj.Shape = Part.makeCompound(edges) if edges else Part.Shape()
    group.addObject(obj)
    _tag_generated(obj, "ceiling_grid")
    return obj


def _set_common_ceiling_properties(obj, room, luminaires, plan, elevation, thickness):
    set_prop(obj, "App::PropertyLink", "FA_SourceRoom", "FacilArquitectura", "Recinto fuente", room)
    set_prop(obj, "App::PropertyLinkList", "FA_SourceLuminaires", "ElectricCR", "Luminarias reservadas", list(luminaires))
    set_prop(obj, "App::PropertyLength", "FA_ModuleSize", "FacilArquitectura", "Modulo nominal", plan["module"])
    set_prop(obj, "App::PropertyLength", "FA_CeilingElevation", "FacilArquitectura", "Cota inferior", elevation)
    set_prop(obj, "App::PropertyLength", "FA_PanelThickness", "FacilArquitectura", "Espesor", thickness)
    set_prop(obj, "App::PropertyInteger", "FA_GridRows", "FacilArquitectura", "Filas de celdas", plan["rows"])
    set_prop(obj, "App::PropertyInteger", "FA_GridColumns", "FacilArquitectura", "Columnas de celdas", plan["columns"])
    set_prop(obj, "App::PropertyInteger", "FA_FullPanelCount", "FacilArquitectura", "Paneles completos", plan["full_panels"])
    set_prop(obj, "App::PropertyInteger", "FA_PartialPanelCount", "FacilArquitectura", "Paneles recortados", plan["partial_panels"])
    set_prop(obj, "App::PropertyInteger", "FA_LuminaireCellCount", "ElectricCR", "Celdas reservadas", plan["reserved_count"])
    set_prop(obj, "App::PropertyInteger", "FA_IncompatibleLuminaireCount", "ElectricCR", "Luminarias fuera de modulo", plan["incompatible_luminaires"])
    set_prop(obj, "App::PropertyString", "FA_RoomGeometry", "FacilArquitectura", "Geometria del recinto", plan.get("geometry", "rectangle"))
    set_prop(obj, "App::PropertyArea", "FA_SourceRoomArea", "FacilArquitectura", "Area del recinto fuente", plan.get("room_area_mm2", plan["length"] * plan["depth"]))
    set_prop(obj, "App::PropertyInteger", "FA_ClippedCellCount", "FacilArquitectura", "Celdas recortadas por perimetro", plan.get("clipped_cell_count", plan["partial_panels"]))


def _write_ceiling_schedule(doc, plans, parent_group, options, sheet_name=CEILING_SHEET_NAME):
    sheet_name = str(sheet_name or CEILING_SHEET_NAME)
    old = doc.getObject(sheet_name)
    if old is not None:
        doc.removeObject(old.Name)
    sheet = doc.addObject("Spreadsheet::Sheet", sheet_name)
    sheet.Label = "Cuadro de cielos suspendidos"
    headers = [
        "Recinto", "Geometria", "Area_recinto_m2", "Modulo_mm", "Cota_mm", "Filas", "Columnas",
        "Paneles completos", "Paneles recortados", "Celdas luminaria", "Luminarias incompatibles",
        "Fase_X_mm", "Fase_Y_mm",
    ]
    for index, value in enumerate(headers, start=1):
        sheet.set("%s1" % _column_name(index), value)
    for row, plan in enumerate(plans, start=2):
        values = [
            plan["room_label"], plan.get("geometry", "rectangle"),
            plan.get("room_area_mm2", plan["length"] * plan["depth"]) / 1000000.0,
            plan["module"], float(options.get("ceiling_elevation_mm", 2700.0)),
            plan["rows"], plan["columns"], plan["full_panels"], plan["partial_panels"],
            plan["reserved_count"], plan["incompatible_luminaires"], plan["phase_x"], plan["phase_y"],
        ]
        for index, value in enumerate(values, start=1):
            sheet.set("%s%d" % (_column_name(index), row), str(value))
    if parent_group is not None:
        parent_group.addObject(sheet)
    _tag_generated(sheet, "ceiling_schedule")
    return sheet


def _column_name(index):
    result = ""
    index = int(index)
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _tag_generated(obj, role):
    set_prop(obj, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Comando generador", GENERATED_BY_CEILING)
    set_prop(obj, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", role)


def _set_view(obj, color=None, transparency=None):
    view = getattr(obj, "ViewObject", None)
    if view is None:
        return
    try:
        if color is not None:
            view.ShapeColor = tuple(float(value) for value in color)
            view.LineColor = tuple(float(value) for value in color)
        if transparency is not None:
            view.Transparency = int(transparency)
    except Exception:
        pass


def _quantity_value(value):
    try:
        return float(value.Value)
    except Exception:
        return float(value)


def _room_name(room):
    for prop in ("FA_RoomName", "RoomName", "NombreRecinto"):
        value = str(getattr(room, prop, "") or "").strip()
        if value:
            return value
    label = _object_label(room)
    return re.sub(r"(?<=\D)00\d$", "", label).strip() or str(getattr(room, "Name", "Recinto"))


def _object_label(obj):
    return str(getattr(obj, "Label", getattr(obj, "Name", "")) or "")
