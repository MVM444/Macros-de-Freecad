"""Suspended modular ceiling helpers for FacilArquitecturaWB.

Descripcion: genera cielos de 600x600 rectangulares o poligonales y reserva luminarias ElectricCR.
Fecha: 2026-07-26
Version: 0.2.0
"""

from __future__ import annotations

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
    polygons = [obj for obj in candidates if _is_room_polygon(obj, selected=bool(selected))]
    rectangles = [obj for obj in candidates if _is_room_rectangle(obj, selected=bool(selected))]
    if not selected:
        if polygons:
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
        rooms = polygons + [obj for obj in rectangles if obj not in polygons]
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


def create_modular_ceilings(doc, bim_group, rooms, luminaires, options):
    """Create one clipped compound ceiling and grid per room face."""
    rooms = list(rooms or [])
    if not rooms:
        raise UserFacingError("No hay recintos rectangulares o poligonales para crear cielos.")
    module = float(options.get("module_mm", 600.0))
    elevation = float(options.get("ceiling_elevation_mm", 2700.0))
    thickness = float(options.get("panel_thickness_mm", 15.0))
    gap = max(0.0, float(options.get("joint_gap_mm", 5.0)))
    tolerance = max(0.0, float(options.get("alignment_tolerance_mm", 50.0)))
    if module <= 0.0 or thickness <= 0.0:
        raise UserFacingError("El modulo y el espesor del panel deben ser mayores que cero.")
    if bool(options.get("replace_previous", True)):
        remove_previous_ceilings(doc)

    ceiling_group = ensure_group(doc, CEILING_GROUP_NAME, "Cielos suspendidos", bim_group)
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
        panels = _create_room_panels(doc, ceiling_group, spec, plan, elevation, thickness, gap)
        grid = _create_room_grid(doc, ceiling_group, spec, plan, elevation)
        _set_common_ceiling_properties(panels, room, source_lights, plan, elevation, thickness)
        _set_common_ceiling_properties(grid, room, source_lights, plan, elevation, 0.0)
        set_prop(panels, "App::PropertyString", "IfcType", "IFC", "Clase IFC", "Covering")
        set_prop(panels, "App::PropertyString", "PredefinedType", "IFC", "Tipo IFC", "CEILING")
        _set_view(panels, color=(0.92, 0.92, 0.88), transparency=0)
        _set_view(grid, color=(0.35, 0.35, 0.35), transparency=0)
        created_objects.extend([panels, grid])
        plans.append(plan)

    sheet = _write_ceiling_schedule(doc, plans, ceiling_group, options)
    created_objects.append(sheet)
    doc.recompute()
    return {"group": ceiling_group, "plans": plans, "objects": created_objects, "sheet": sheet}


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


def _create_room_panels(doc, group, spec, plan, elevation, thickness, gap):
    shapes = []
    for cell in plan["panel_cells"]:
        inset_x = min(gap / 2.0, cell["width"] / 4.0)
        inset_y = min(gap / 2.0, cell["depth"] / 4.0)
        width = max(0.1, cell["width"] - 2.0 * inset_x)
        depth = max(0.1, cell["depth"] - 2.0 * inset_y)
        if spec["geometry"] == "polygon":
            inset_face = _local_rectangle_face(
                cell["x0"] + inset_x,
                cell["y0"] + inset_y,
                cell["x1"] - inset_x,
                cell["y1"] - inset_y,
            )
            clipped = spec["face"].common(inset_face)
            for face in list(getattr(clipped, "Faces", []) or []):
                if float(face.Area) <= MIN_CLIPPED_FACE_AREA_MM2:
                    continue
                placed = _place_local_shape(face, spec, elevation - thickness)
                shapes.append(placed.extrude(FreeCAD.Vector(0.0, 0.0, thickness)))
        else:
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
    obj = doc.addObject("Part::Feature", "FA_CeilingPanels")
    obj.Label = "Cielo 600x600 - %s" % _room_name(spec["room"])
    obj.Shape = Part.makeCompound(shapes) if shapes else Part.Shape()
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


def _write_ceiling_schedule(doc, plans, parent_group, options):
    old = doc.getObject(CEILING_SHEET_NAME)
    if old is not None:
        doc.removeObject(old.Name)
    sheet = doc.addObject("Spreadsheet::Sheet", CEILING_SHEET_NAME)
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
