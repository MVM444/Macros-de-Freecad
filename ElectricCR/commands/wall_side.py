# -*- coding: utf-8 -*-
"""Context command for moving ElectricCR devices to the opposite wall face."""

from __future__ import annotations

import math
import os
import unicodedata

import FreeCAD as App
import FreeCADGui as Gui


COMMAND_NAME = "ElectricCR_MoveToOppositeWallSide"
COMMAND_LABEL = "Mover al otro lado de la pared"
ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons")
MAX_WALL_DISTANCE_MM = 1000.0


def _text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _normalized(value):
    value = unicodedata.normalize("NFKD", _text(value).lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def _quantity(value, default=0.0):
    try:
        return float(getattr(value, "Value", value))
    except Exception:
        return float(default)


def _icon():
    for name in ("MoverAlOtroLadoPared.svg", "Rayo.svg", "Rayo.png"):
        path = os.path.join(ICONS_DIR, name)
        if os.path.exists(path):
            return path
    return ""


def _device_signature(obj):
    linked = getattr(obj, "LinkedObject", None)
    values = []
    for candidate in (obj, linked):
        if candidate is None:
            continue
        for name in ("Name", "Label", "Tipo", "TipoLogico", "KeyRegistro"):
            values.append(getattr(candidate, name, ""))
    return _normalized(" ".join(_text(value) for value in values))


def is_supported_device(obj):
    """Return True only for physical ElectricCR receptacles and switches."""
    if obj is None or not hasattr(obj, "Placement"):
        return False
    type_id = _text(getattr(obj, "TypeId", ""))
    if "DocumentObjectGroup" in type_id or "App::Part" in type_id:
        return False
    name = _normalized(getattr(obj, "Name", ""))
    if name.startswith(("master_", "proto", "biblioteca_")):
        return False
    signature = _device_signature(obj)
    tokens = (
        "toma", "tomacorriente", "receptacle", "outlet",
        "apagador", "interruptor", "switch",
    )
    return any(token in signature for token in tokens)


def selected_devices():
    result = []
    seen = set()
    for obj in Gui.Selection.getSelection() or []:
        if not is_supported_device(obj):
            continue
        key = (getattr(getattr(obj, "Document", None), "Name", ""), obj.Name)
        if key not in seen:
            seen.add(key)
            result.append(obj)
    return result


def has_applicable_selection():
    return bool(selected_devices())


def _is_wall(obj):
    if obj is None:
        return False
    ifc = _normalized(getattr(obj, "IfcType", ""))
    role = _normalized(getattr(obj, "FA_Role", ""))
    proxy_type = _normalized(getattr(getattr(obj, "Proxy", None), "Type", ""))
    type_id = _normalized(getattr(obj, "TypeId", ""))
    return (
        ifc in ("wall", "wallstandardcase")
        or role == "wall"
        or proxy_type == "wall"
        or "arch::wall" in type_id
    )


def _source_wall(obj):
    for name in ("ECR_SourceWall", "MuroReferencia", "SourceWall", "Wall"):
        try:
            wall = getattr(obj, name)
        except Exception:
            wall = None
        if _is_wall(wall):
            return wall
    return None


def _geometry_segments(source):
    result = []
    geometry = list(getattr(source, "Geometry", []) or [])
    placement = getattr(source, "Placement", App.Placement())
    for item in geometry:
        if not hasattr(item, "StartPoint") or not hasattr(item, "EndPoint"):
            continue
        try:
            start = placement.multVec(item.StartPoint)
            end = placement.multVec(item.EndPoint)
        except Exception:
            continue
        if math.hypot(end.x - start.x, end.y - start.y) > 1.0:
            result.append((start, end))
    return result


def _shape_segments(source):
    result = []
    shape = getattr(source, "Shape", None)
    for edge in list(getattr(shape, "Edges", []) or []):
        try:
            start = edge.Vertexes[0].Point
            end = edge.Vertexes[-1].Point
            xy_length = math.hypot(end.x - start.x, end.y - start.y)
            if xy_length <= 1.0:
                continue
            # Do not replace a curve by a chord that could cross the room.
            if abs(float(edge.Length) - xy_length) > max(2.0, xy_length * 0.002):
                continue
            result.append((start, end))
        except Exception:
            continue
    return result


def wall_segments(wall):
    base = getattr(wall, "Base", None)
    segments = _geometry_segments(base) if base is not None else []
    if not segments and base is not None:
        segments = _shape_segments(base)
    if not segments:
        segments = _shape_segments(wall)
    return segments


def _nearest_projection(point, segments):
    best = None
    for start, end in segments:
        dx, dy = end.x - start.x, end.y - start.y
        length2 = dx * dx + dy * dy
        if length2 <= 1.0:
            continue
        t = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length2
        t = max(0.0, min(1.0, t))
        projected = App.Vector(start.x + t * dx, start.y + t * dy, point.z)
        distance = math.hypot(point.x - projected.x, point.y - projected.y)
        if best is None or distance < best[0]:
            length = math.sqrt(length2)
            tangent = App.Vector(dx / length, dy / length, 0.0)
            best = (distance, projected, tangent)
    return best


def _wall_width(wall):
    base = getattr(wall, "Base", None)
    for owner, name in (
        (wall, "Width"), (wall, "FA_WallThickness"),
        (base, "FA_WallThickness"), (base, "Width"),
    ):
        if owner is None:
            continue
        value = _quantity(getattr(owner, name, 0.0), 0.0)
        if value > 1.0:
            return value
    return 120.0


def _candidate_walls(obj):
    wall = _source_wall(obj)
    if wall is not None:
        return [wall]
    doc = getattr(obj, "Document", None)
    return [candidate for candidate in getattr(doc, "Objects", []) if _is_wall(candidate)]


def _best_wall_axis(obj):
    point = obj.Placement.Base
    best = None
    for wall in _candidate_walls(obj):
        projection = _nearest_projection(point, wall_segments(wall))
        if projection is None:
            continue
        distance, projected, tangent = projection
        if best is None or distance < best[0]:
            best = (distance, projected, tangent, wall)
    if best is None:
        raise RuntimeError("no se encontro un eje de pared cercano")
    width = _wall_width(best[3])
    allowed = max(MAX_WALL_DISTANCE_MM, width * 3.0)
    if best[0] > allowed:
        raise RuntimeError(
            "la pared mas cercana esta a %.0f mm (limite %.0f mm)" % (best[0], allowed)
        )
    return best


def _opposite_placement(obj):
    old = App.Placement(obj.Placement)
    distance, axis_point, tangent, wall = _best_wall_axis(obj)
    dx = old.Base.x - axis_point.x
    dy = old.Base.y - axis_point.y

    if distance > 1.0:
        target = App.Vector(axis_point.x - dx, axis_point.y - dy, old.Base.z)
    else:
        # A device accidentally on the centerline has no geometric side. Infer
        # its current front from local +Y and place it on the opposite face.
        normal = App.Vector(-tangent.y, tangent.x, 0.0)
        front = old.Rotation.multVec(App.Vector(0.0, 1.0, 0.0))
        sign = 1.0 if front.x * normal.x + front.y * normal.y >= 0.0 else -1.0
        offset = _wall_width(wall) * 0.5
        target = App.Vector(
            axis_point.x - normal.x * sign * offset,
            axis_point.y - normal.y * sign * offset,
            old.Base.z,
        )

    turn = App.Rotation(App.Vector(0.0, 0.0, 1.0), 180.0)
    rotation = turn.multiply(old.Rotation)
    return App.Placement(target, rotation), wall, distance


def _record_flip(obj, wall):
    try:
        if "ECR_WallSideFlipCount" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyInteger", "ECR_WallSideFlipCount", "ElectricCR BIM",
                "Cantidad de cambios manuales de cara de pared",
            )
        obj.ECR_WallSideFlipCount = int(obj.ECR_WallSideFlipCount) + 1
    except Exception:
        pass
    if _source_wall(obj) is None:
        try:
            if "ECR_SourceWall" not in obj.PropertiesList:
                obj.addProperty(
                    "App::PropertyLink", "ECR_SourceWall", "ElectricCR BIM",
                    "Pared utilizada para la colocacion",
                )
            obj.ECR_SourceWall = wall
        except Exception:
            pass


def _area_room_name(obj):
    for name in ("FA_RoomName", "Recinto", "AreaNombre", "RoomName", "NombreRecinto"):
        value = _text(getattr(obj, name, "")).strip()
        if value:
            return value
    label = _text(getattr(obj, "Label", getattr(obj, "Name", ""))).strip()
    normalized = _normalized(label)
    for prefix in ("poligono - ", "poligono ", "etiqueta area - ", "etiqueta area "):
        if normalized.startswith(prefix):
            return label[len(prefix):].strip(" -")
    return label


def _room_at_device_front(obj):
    doc = getattr(obj, "Document", None)
    if doc is None:
        return None
    placement = obj.Placement
    front = placement.Rotation.multVec(App.Vector(0.0, 1.0, 0.0))
    probe = placement.Base + App.Vector(front.x, front.y, 0.0) * 250.0
    matches = []
    for candidate in doc.Objects:
        type_id = _text(getattr(candidate, "TypeId", ""))
        label = _normalized(getattr(candidate, "Label", ""))
        semantic = (
            candidate.Name.startswith("Rectangle")
            or candidate.Name.startswith("FA_PolygonalRoom")
            or label.startswith("poligono -")
            or "Part2DObject" in type_id
        )
        if not semantic:
            continue
        try:
            box = candidate.Shape.BoundBox
            if box.XLength <= 200.0 or box.YLength <= 200.0:
                continue
            if not (box.XMin - 2.0 <= probe.x <= box.XMax + 2.0 and box.YMin - 2.0 <= probe.y <= box.YMax + 2.0):
                continue
        except Exception:
            continue
        is_room_geometry = candidate.Name.startswith(("Rectangle", "FA_PolygonalRoom"))
        is_generic_2d = "Part2DObject" in type_id and not is_room_geometry
        rank = (0 if is_room_geometry else (2 if is_generic_2d else 1), box.XLength * box.YLength)
        matches.append((rank, candidate))
    return min(matches, key=lambda row: row[0])[1] if matches else None


def _toggle_switch_override(obj):
    if "ECR_SideOverride" not in getattr(obj, "PropertiesList", []):
        return
    current = _text(getattr(obj, "ECR_SideOverride", "")).strip()
    toggled = {
        "": "opposite_room",
        "opposite_room": "",
        "opening": "opposite_opening",
        "opposite_opening": "opening",
    }.get(current, "opposite_room")
    try:
        obj.ECR_SideOverride = toggled
    except Exception:
        pass
    if "ReglaCaraInterior" in getattr(obj, "PropertiesList", []):
        try:
            obj.ReglaCaraInterior = "cambio_contextual_otro_lado"
        except Exception:
            pass


def _update_room_after_flip(obj):
    room = _room_at_device_front(obj)
    if room is None:
        return
    room_name = _area_room_name(room)
    if "AreaRecinto" in getattr(obj, "PropertiesList", []):
        try:
            obj.AreaRecinto = room
        except Exception:
            pass
    if "Recinto" in getattr(obj, "PropertiesList", []):
        try:
            obj.Recinto = room_name
        except Exception:
            pass
    label = _text(getattr(obj, "Label", ""))
    if _normalized(label).startswith("apagador -"):
        try:
            obj.Label = "Apagador - " + room_name
        except Exception:
            pass


def flip_object(obj):
    if not is_supported_device(obj):
        raise RuntimeError("el objeto no es un tomacorriente o apagador ElectricCR")
    placement, wall, distance = _opposite_placement(obj)
    obj.Placement = placement
    _record_flip(obj, wall)
    _toggle_switch_override(obj)
    _update_room_after_flip(obj)
    return {
        "object": obj,
        "wall": wall,
        "previous_distance": distance,
        "placement": placement,
    }


def flip_objects(objects, use_transaction=True):
    devices = [obj for obj in objects or [] if is_supported_device(obj)]
    if not devices:
        return {"moved": [], "errors": []}
    doc = getattr(devices[0], "Document", None)
    moved, errors = [], []
    if use_transaction and doc is not None:
        doc.openTransaction(COMMAND_LABEL)
    try:
        for obj in devices:
            if getattr(obj, "Document", None) is not doc:
                errors.append((obj, "pertenece a otro documento"))
                continue
            try:
                moved.append(flip_object(obj))
            except Exception as exc:
                errors.append((obj, _text(exc)))
        if doc is not None:
            doc.recompute()
        if use_transaction and doc is not None:
            doc.commitTransaction()
    except Exception:
        if use_transaction and doc is not None:
            try:
                doc.abortTransaction()
            except Exception:
                pass
        raise
    return {"moved": moved, "errors": errors}


class MoveToOppositeWallSideCommand:
    def GetResources(self):
        return {
            "Pixmap": _icon(),
            "MenuText": COMMAND_LABEL,
            "ToolTip": (
                "Refleja los tomacorrientes y apagadores seleccionados a la cara "
                "opuesta del muro y los gira 180 grados."
            ),
        }

    def Activated(self):
        devices = selected_devices()
        if not devices:
            App.Console.PrintWarning(
                "[ElectricCR] Seleccione uno o varios tomacorrientes o apagadores.\n"
            )
            return
        result = flip_objects(devices, use_transaction=True)
        for item in result["moved"]:
            App.Console.PrintMessage(
                "[ElectricCR] %s movido al otro lado de %s.\n"
                % (item["object"].Label, item["wall"].Label)
            )
        for obj, reason in result["errors"]:
            App.Console.PrintWarning(
                "[ElectricCR] No se pudo mover %s: %s.\n"
                % (getattr(obj, "Label", obj.Name), reason)
            )
        if result["errors"]:
            App.Console.PrintWarning(
                "[ElectricCR] Resultado: %d movidos, %d omitidos.\n"
                % (len(result["moved"]), len(result["errors"]))
            )

    def IsActive(self):
        # Do not disable the popup action before FreeCAD has synchronized the
        # object under the right-click with Gui.Selection.
        return App.ActiveDocument is not None


def register_command():
    Gui.addCommand(COMMAND_NAME, MoveToOppositeWallSideCommand())
    return COMMAND_NAME
