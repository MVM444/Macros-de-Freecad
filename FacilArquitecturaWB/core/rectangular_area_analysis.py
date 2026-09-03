# -*- coding: utf-8 -*-
# Descripcion: Motor reutilizable para analisis rectangular desde muros BIM.
# Revision: 2026-08-11 20:18 America/Costa_Rica
# FreeCAD: 1.1.3

from __future__ import annotations

import math
import re

import FreeCAD as App
import Draft

try:
    import FreeCADGui as Gui
except Exception:
    Gui = None


GENERATED_BY = "FA_RectangularAreaAnalysis"
GROUP_NAME = "FA_RectangularAreas"
SHEET_NAME = "Spreadsheet_Analisis_Areas"
AREA_RE = re.compile(r"^\s*([0-9]+(?:[.,][0-9]+)?)\s*m(?:2|²)\s*$", re.IGNORECASE)
ANGLE_TOLERANCE_DEG = 3.0
WALL_HALF_WIDTH_MM = 60.0
RAY_EXTENSION_MM = 250.0
MIN_DIMENSION_MM = 500.0
MAX_GUIDE_DISTANCE_MM = 12000.0
DIRECT_AREA_TOLERANCE = 0.35


def add_prop(obj, prop_type, name, group, description):
    try:
        if name not in obj.PropertiesList:
            obj.addProperty(prop_type, name, group, description)
    except Exception:
        pass


def quantity_value(value, default=0.0):
    try:
        return float(getattr(value, "Value", value))
    except Exception:
        return float(default)


def is_bim_wall(obj):
    if obj is None:
        return False
    role = str(getattr(obj, "FA_Role", "") or "").strip().lower()
    generated_by = str(getattr(obj, "FA_GeneratedBy", "") or "")
    proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "").lower()
    has_solid = bool(list(getattr(getattr(obj, "Shape", None), "Solids", []) or []))
    return has_solid and (
        role in ("wall", "reconstructed_wall")
        or generated_by in ("FA_CreateWallsBIM", "FA_CreateBuildingGrid")
        or proxy_type == "wall"
    )


def wall_centerline(wall):
    for attr in ("FA_SourceSketch", "Base", "FA_SourceGridTrace"):
        source = getattr(wall, attr, None)
        if source is not None and (
            str(getattr(source, "TypeId", "") or "").startswith("Sketcher::")
            or bool(list(getattr(source, "Geometry", []) or []))
        ):
            return source
    return None


def find_bim_wall(doc):
    selected = list(Gui.Selection.getSelection() or []) if Gui is not None else []
    for obj in selected:
        if is_bim_wall(obj) and wall_centerline(obj) is not None:
            return obj
    candidates = []
    for obj in doc.Objects:
        if not is_bim_wall(obj):
            continue
        source = wall_centerline(obj)
        if source is None:
            continue
        source_role = str(getattr(source, "FA_Role", "") or "").lower()
        score = 0
        if source_role == "grid_clipped_lines":
            score += 100
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == "FA_CreateWallsBIM":
            score += 40
        try:
            if obj.ViewObject.Visibility:
                score += 20
        except Exception:
            pass
        score += len(list(getattr(getattr(obj, "Shape", None), "Solids", []) or []))
        candidates.append((score, obj))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def selected_bim_walls(doc):
    explicit = globals().get("ELECTRICCR_SELECTED_BIM_WALLS", None)
    selected = list(explicit if explicit is not None else (Gui.Selection.getSelection() or [])) if Gui is not None else []
    walls = [obj for obj in selected if is_bim_wall(obj) and wall_centerline(obj) is not None]
    if walls:
        return walls
    fallback = find_bim_wall(doc)
    return [fallback] if fallback is not None else []


def unique_centerlines(walls):
    result, seen = [], set()
    for wall in walls:
        source = wall_centerline(wall)
        key = getattr(source, "Name", id(source))
        if source is not None and key not in seen:
            seen.add(key)
            result.append(source)
    return result


def text_lines(obj):
    if not hasattr(obj, "Text"):
        return []
    try:
        value = obj.Text
    except Exception:
        return []
    if isinstance(value, (list, tuple)):
        lines = [str(item).strip() for item in value]
    else:
        lines = [part.strip() for part in str(value).replace("\r", "\n").split("\n")]
    return [line for line in lines if line]


def label_area(lines):
    for line in lines[1:]:
        match = AREA_RE.match(line)
        if match:
            return float(match.group(1).replace(",", "."))
    return None


def room_labels(doc):
    result = []
    for obj in doc.Objects:
        lines = text_lines(obj)
        area = label_area(lines)
        if not lines or area is None:
            continue
        label = str(getattr(obj, "Label", "") or "").lower()
        if not label.startswith("etiqueta_"):
            continue
        try:
            point = obj.getGlobalPlacement().Base
        except Exception:
            point = obj.Placement.Base
        result.append(
            {
                "object": obj,
                "name": " ".join(lines[0].split()).upper(),
                "program_area": area,
                "type": lines[2] if len(lines) > 2 else "",
                "point": App.Vector(float(point.x), float(point.y), 0.0),
            }
        )
    return result


def global_line_segments(sketch):
    result = []
    try:
        placement = sketch.getGlobalPlacement()
    except Exception:
        placement = sketch.Placement
    for geometry in list(getattr(sketch, "Geometry", []) or []):
        if not hasattr(geometry, "StartPoint") or not hasattr(geometry, "EndPoint"):
            continue
        first = placement.multVec(geometry.StartPoint)
        second = placement.multVec(geometry.EndPoint)
        dx, dy = float(second.x - first.x), float(second.y - first.y)
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        angle = abs(math.degrees(math.atan2(dy, dx))) % 180.0
        if min(angle, abs(angle - 180.0)) <= ANGLE_TOLERANCE_DEG:
            result.append(("horizontal", float(first.x), float(first.y), float(second.x), float(second.y)))
        elif abs(angle - 90.0) <= ANGLE_TOLERANCE_DEG:
            result.append(("vertical", float(first.x), float(first.y), float(second.x), float(second.y)))
    if result:
        return result
    for edge in list(getattr(getattr(sketch, "Shape", None), "Edges", []) or []):
        vertices = list(getattr(edge, "Vertexes", []) or [])
        if len(vertices) < 2:
            continue
        first = placement.multVec(vertices[0].Point)
        second = placement.multVec(vertices[-1].Point)
        dx, dy = float(second.x - first.x), float(second.y - first.y)
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        angle = abs(math.degrees(math.atan2(dy, dx))) % 180.0
        if min(angle, abs(angle - 180.0)) <= ANGLE_TOLERANCE_DEG:
            result.append(("horizontal", float(first.x), float(first.y), float(second.x), float(second.y)))
        elif abs(angle - 90.0) <= ANGLE_TOLERANCE_DEG:
            result.append(("vertical", float(first.x), float(first.y), float(second.x), float(second.y)))
    return result


def find_wall_sketch(doc):
    preferred = (
        "FA_ReconstructedWallBase",
        "Sketch_Cerrado_Sketch_Centros_Pared_Muro_Seco_Espesor_120mm",
        "Sketch_Centros_Pared_Muro_Seco_Espesor_120mm",
    )
    for name in preferred:
        obj = doc.getObject(name)
        if obj is not None:
            return obj
    for obj in doc.Objects:
        text = (str(getattr(obj, "Name", "")) + " " + str(getattr(obj, "Label", ""))).lower()
        if "sketch" in str(getattr(obj, "TypeId", "")).lower() and "centros" in text and ("muro" in text or "pared" in text):
            return obj
    return None


def nearest_rectangle(point, segments):
    x, y = float(point.x), float(point.y)
    left = right = bottom = top = None
    for kind, x1, y1, x2, y2 in segments:
        if kind == "vertical":
            wall_x = (x1 + x2) * 0.5
            low, high = sorted((y1, y2))
            if y < low - RAY_EXTENSION_MM or y > high + RAY_EXTENSION_MM:
                continue
            if wall_x < x and (left is None or wall_x > left):
                left = wall_x
            if wall_x > x and (right is None or wall_x < right):
                right = wall_x
        else:
            wall_y = (y1 + y2) * 0.5
            low, high = sorted((x1, x2))
            if x < low - RAY_EXTENSION_MM or x > high + RAY_EXTENSION_MM:
                continue
            if wall_y < y and (bottom is None or wall_y > bottom):
                bottom = wall_y
            if wall_y > y and (top is None or wall_y < top):
                top = wall_y
    if None in (left, right, bottom, top):
        return None
    left += WALL_HALF_WIDTH_MM
    right -= WALL_HALF_WIDTH_MM
    bottom += WALL_HALF_WIDTH_MM
    top -= WALL_HALF_WIDTH_MM
    width, height = right - left, top - bottom
    if width < MIN_DIMENSION_MM or height < MIN_DIMENSION_MM:
        return None
    return left, bottom, width, height


def area_ratio_error(rectangle, target_area_m2):
    area = rectangle[2] * rectangle[3] / 1000000.0
    return abs(area - target_area_m2) / max(target_area_m2, 0.01)


def _overlap_ratio(rectangle, other):
    ax1, ay1, aw, ah = rectangle
    bx1, by1, bw, bh = other
    overlap_w = max(0.0, min(ax1 + aw, bx1 + bw) - max(ax1, bx1))
    overlap_h = max(0.0, min(ay1 + ah, by1 + bh) - max(ay1, by1))
    overlap = overlap_w * overlap_h
    return overlap / max(min(aw * ah, bw * bh), 1.0)


def guided_rectangle(record, segments, trusted_rectangles, room_records=None):
    """Infer a room from extended wall/grid lines and trusted green rectangles."""
    point = record["point"]
    x, y = float(point.x), float(point.y)
    x_lines = set()
    y_lines = set()
    for kind, x1, y1, x2, y2 in segments:
        if kind == "vertical":
            wall_x = (x1 + x2) * 0.5
            x_lines.add(round(wall_x - WALL_HALF_WIDTH_MM, 4))
            x_lines.add(round(wall_x + WALL_HALF_WIDTH_MM, 4))
        else:
            wall_y = (y1 + y2) * 0.5
            y_lines.add(round(wall_y - WALL_HALF_WIDTH_MM, 4))
            y_lines.add(round(wall_y + WALL_HALF_WIDTH_MM, 4))
    for rectangle in trusted_rectangles:
        rx, ry, rw, rh = rectangle
        x_lines.update((round(rx, 4), round(rx + rw, 4)))
        y_lines.update((round(ry, 4), round(ry + rh, 4)))
    for other in list(room_records or []):
        if other is record:
            continue
        other_x = float(other["point"].x)
        other_y = float(other["point"].y)
        dx, dy = other_x - x, other_y - y
        if math.hypot(dx, dy) > MAX_GUIDE_DISTANCE_MM * 1.5:
            continue
        if abs(dx) >= abs(dy) * 1.5:
            boundary = round((x + other_x) * 0.5, 4)
            x_lines.add(boundary)
        elif abs(dy) >= abs(dx) * 1.5:
            boundary = round((y + other_y) * 0.5, 4)
            y_lines.add(boundary)

    lefts = sorted(
        (value for value in x_lines if 0.0 < x - value <= MAX_GUIDE_DISTANCE_MM),
        key=lambda value: x - value,
    )[:8]
    rights = sorted(
        (value for value in x_lines if 0.0 < value - x <= MAX_GUIDE_DISTANCE_MM),
        key=lambda value: value - x,
    )[:8]
    bottoms = sorted(
        (value for value in y_lines if 0.0 < y - value <= MAX_GUIDE_DISTANCE_MM),
        key=lambda value: y - value,
    )[:8]
    tops = sorted(
        (value for value in y_lines if 0.0 < value - y <= MAX_GUIDE_DISTANCE_MM),
        key=lambda value: value - y,
    )[:8]
    target_mm2 = max(record["program_area"], 0.01) * 1000000.0
    target_scale = math.sqrt(target_mm2)
    best = None
    for left in lefts:
        for right in rights:
            width = right - left
            if width < MIN_DIMENSION_MM:
                continue
            for bottom in bottoms:
                for top in tops:
                    height = top - bottom
                    if height < MIN_DIMENSION_MM:
                        continue
                    rectangle = (left, bottom, width, height)
                    area = width * height
                    area_error = abs(math.log(max(area, 1.0) / target_mm2))
                    center_x = left + width * 0.5
                    center_y = bottom + height * 0.5
                    center_error = math.hypot(center_x - x, center_y - y) / max(target_scale, 1.0)
                    aspect = max(width / height, height / width)
                    aspect_penalty = max(0.0, aspect - 6.0) * 0.15
                    overlap_penalty = sum(_overlap_ratio(rectangle, other) for other in trusted_rectangles) * 8.0
                    score = area_error * 10.0 + center_error * 0.35 + aspect_penalty + overlap_penalty
                    if best is None or score < best[0]:
                        best = (score, rectangle, area_error)
    if best is None:
        return None, 0.0
    confidence = max(0.55, min(0.88, 0.88 - best[2] * 0.35))
    return best[1], confidence


def fit_target_area_on_guides(record, rectangle, trusted_rectangles):
    """Keep one guided dimension and derive the other from the stated room area."""
    x, y, width, height = rectangle
    point = record["point"]
    target_mm2 = max(record["program_area"], 0.01) * 1000000.0
    candidates = []
    derived_height = target_mm2 / max(width, 1.0)
    if derived_height >= MIN_DIMENSION_MM:
        candidate = (x, float(point.y) - derived_height * 0.5, width, derived_height)
        overlap = sum(_overlap_ratio(candidate, other) for other in trusted_rectangles)
        candidates.append((overlap, candidate))
    derived_width = target_mm2 / max(height, 1.0)
    if derived_width >= MIN_DIMENSION_MM:
        candidate = (float(point.x) - derived_width * 0.5, y, derived_width, height)
        overlap = sum(_overlap_ratio(candidate, other) for other in trusted_rectangles)
        candidates.append((overlap, candidate))
    if not candidates:
        return rectangle
    return min(candidates, key=lambda item: item[0])[1]


def ensure_group(doc):
    old = doc.getObject(GROUP_NAME)
    if old is not None:
        for child in list(getattr(old, "Group", []) or []):
            try:
                doc.removeObject(child.Name)
            except Exception:
                pass
        try:
            doc.removeObject(old.Name)
        except Exception:
            pass
    group = doc.addObject("App::DocumentObjectGroup", GROUP_NAME)
    group.Label = "Análisis de áreas rectangulares"
    parent = doc.getObject("FA_Areas")
    if parent is not None:
        try:
            parent.addObject(group)
        except Exception:
            pass
    return group


def program_rectangle(record, aspect_ratio=1.5):
    area_mm2 = max(float(record["program_area"]), 0.01) * 1000000.0
    width = math.sqrt(area_mm2 * float(aspect_ratio))
    height = area_mm2 / width
    point = record["point"]
    return (float(point.x) - width * 0.5, float(point.y) - height * 0.5, width, height)


def create_rectangle(
    doc,
    group,
    record,
    rectangle,
    mode="geometric",
    confidence=None,
    source_wall=None,
    source_centerline=None,
):
    x, y, width, height = rectangle
    obj = Draft.makeRectangle(
        float(width),
        float(height),
        App.Placement(App.Vector(x, y, 20.0), App.Rotation()),
    )
    obj.Label = record["name"]
    if hasattr(obj, "MakeFace"):
        obj.MakeFace = True
    area_m2 = width * height / 1000000.0
    for prop_type, name, category, description in (
        ("App::PropertyString", "ElectricCRTipo", "ElectricCR", "Tipo lógico compatible con ElectricCR"),
        ("App::PropertyString", "GeneratedBy", "ElectricCR", "Macro generadora"),
        ("App::PropertyFloat", "AreaM2", "ElectricCR", "Área rectangular en m²"),
        ("App::PropertyString", "AreaID", "ElectricCR", "Identificador de área"),
        ("App::PropertyString", "Recinto", "ElectricCR", "Nombre del recinto"),
        ("App::PropertyString", "AreaNombre", "ElectricCR", "Nombre del área"),
        ("App::PropertyString", "Habitacion", "ElectricCR", "Nombre de habitación"),
        ("App::PropertyString", "Local", "ElectricCR", "Nombre de local"),
        ("App::PropertyString", "Espacio", "ElectricCR", "Nombre de espacio"),
        ("App::PropertyString", "Zona", "ElectricCR", "Zona o tipo de recinto"),
        ("App::PropertyInteger", "VirtualClosures", "ElectricCR", "Cierres virtuales utilizados"),
        ("App::PropertyFloat", "Confidence", "ElectricCR", "Confianza geométrica"),
        ("App::PropertyString", "FA_RoomName", "FacilArquitectura", "Nombre del recinto"),
        ("App::PropertyFloat", "FA_ProgramAreaM2", "FacilArquitectura", "Área indicada por el rótulo"),
        ("App::PropertyFloat", "FA_AreaDifferenceM2", "FacilArquitectura", "Diferencia entre rectángulo y rótulo"),
        ("App::PropertyLink", "FA_SourceLabel", "FacilArquitectura", "Rótulo fuente"),
        ("App::PropertyLink", "FA_SourceBIMWall", "FacilArquitectura", "Muro BIM fuente"),
        ("App::PropertyLink", "FA_SourceCenterline", "FacilArquitectura", "Sketch base del muro BIM"),
        ("App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador"),
        ("App::PropertyString", "FA_InferenceMethod", "FacilArquitectura", "Método usado para obtener los límites"),
    ):
        add_prop(obj, prop_type, name, category, description)
    obj.ElectricCRTipo = "Area"
    obj.GeneratedBy = GENERATED_BY
    obj.AreaM2 = area_m2
    obj.AreaID = "FA_%03d" % (len([child for child in group.Group if getattr(child, "ElectricCRTipo", "") == "Area"]) + 1)
    obj.Recinto = record["name"]
    obj.AreaNombre = record["name"]
    obj.Habitacion = record["name"]
    obj.Local = record["name"]
    obj.Espacio = record["name"]
    obj.Zona = record["type"]
    obj.VirtualClosures = {"geometric": 0, "guided": 2, "guided_fit": 2, "program": 4}.get(mode, 4)
    obj.Confidence = float(confidence if confidence is not None else {"geometric": 0.95, "guided": 0.75, "guided_fit": 0.72, "program": 0.50}.get(mode, 0.50))
    obj.FA_RoomName = record["name"]
    obj.FA_ProgramAreaM2 = record["program_area"]
    obj.FA_AreaDifferenceM2 = area_m2 - record["program_area"]
    obj.FA_SourceLabel = record["object"]
    obj.FA_SourceBIMWall = source_wall
    obj.FA_SourceCenterline = source_centerline
    obj.FA_GeneratedBy = GENERATED_BY
    obj.FA_InferenceMethod = {
        "geometric": "Cuatro límites locales de muro",
        "guided": "Muros y prolongación de rectángulos confiables",
        "guided_fit": "Dos límites guía y área indicada en el rótulo",
        "program": "Dimensiones derivadas únicamente del área del rótulo",
    }.get(mode, mode)
    group.addObject(obj)
    try:
        colors = {
            "geometric": ((0.0, 0.48, 0.42), (0.35, 0.80, 0.70)),
            "guided": ((0.10, 0.35, 0.82), (0.40, 0.62, 0.95)),
            "guided_fit": ((0.38, 0.20, 0.78), (0.67, 0.50, 0.93)),
            "program": ((0.85, 0.38, 0.05), (0.95, 0.66, 0.28)),
        }
        line_color, shape_color = colors.get(mode, colors["program"])
        obj.ViewObject.LineColor = line_color
        obj.ViewObject.ShapeColor = shape_color
        obj.ViewObject.Transparency = 68
        obj.ViewObject.LineWidth = 3.0
    except Exception:
        pass

    center = App.Vector(x + width * 0.5, y + height * 0.5, 35.0)
    strings = [record["name"], "%.2f m²" % area_m2]
    try:
        label = Draft.make_text(strings, point=center, screen=False)
    except Exception:
        try:
            label = Draft.makeText(strings, point=center, screen=False)
        except Exception:
            label = None
    if label is not None:
        label.Label = "Etiqueta área - " + record["name"]
        add_prop(label, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador")
        add_prop(label, "App::PropertyLink", "FA_AreaRectangle", "FacilArquitectura", "Rectángulo asociado")
        label.FA_GeneratedBy = GENERATED_BY
        label.FA_AreaRectangle = obj
        group.addObject(label)
        try:
            label.ViewObject.FontSize = 180.0
            label.ViewObject.TextColor = (0.08, 0.20, 0.16)
            label.ViewObject.Justification = "Center"
        except Exception:
            pass
    return obj, label, area_m2


def write_analysis_sheet(doc, rows, source_wall=None, source_centerline=None):
    sheet = doc.getObject(SHEET_NAME)
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", SHEET_NAME)
    sheet.Label = "Análisis de áreas rectangulares"
    try:
        sheet.clearAll()
    except Exception:
        pass
    headers = ("Recinto", "Área_rótulo_m2", "Área_rectángulo_m2", "Diferencia_m2", "Ancho_mm", "Fondo_mm", "Estado")
    for index, header in enumerate(headers):
        cell = "%s1" % chr(ord("A") + index)
        sheet.set(cell, header)
        sheet.setStyle(cell, "bold", "add")
    for row_index, row in enumerate(rows, 2):
        values = (
            row["name"],
            "%.3f" % row["program_area"],
            "" if row["area"] is None else "%.3f" % row["area"],
            "" if row["area"] is None else "%.3f" % (row["area"] - row["program_area"]),
            "" if row["rectangle"] is None else "%.2f" % row["rectangle"][2],
            "" if row["rectangle"] is None else "%.2f" % row["rectangle"][3],
            row["status"],
        )
        for index, value in enumerate(values):
            sheet.set("%s%d" % (chr(ord("A") + index), row_index), str(value))
    total_row = len(rows) + 2
    program_total = sum(float(row["program_area"]) for row in rows)
    calculated_total = sum(float(row["area"] or 0.0) for row in rows)
    for cell, value in (
        ("A%d" % total_row, "TOTAL"),
        ("B%d" % total_row, "%.3f" % program_total),
        ("C%d" % total_row, "%.3f" % calculated_total),
        ("D%d" % total_row, "%.3f" % (calculated_total - program_total)),
    ):
        sheet.set(cell, value)
        sheet.setStyle(cell, "bold", "add")
    source_name = str(getattr(source_wall, "Label", getattr(source_wall, "Name", "")) or "")
    centerline_name = str(
        getattr(source_centerline, "Label", getattr(source_centerline, "Name", "")) or ""
    )
    source_values = (
        ("H1", "Fuente muro BIM"),
        ("I1", source_name),
        ("H2", "Sketch base"),
        ("I2", centerline_name),
        ("H3", "Recintos"),
        ("I3", str(len(rows))),
        ("H4", "Diferencia total m2"),
        ("I4", "%.3f" % (calculated_total - program_total)),
    )
    for cell, value in source_values:
        sheet.set(cell, value)
    for cell in ("H1", "H2", "H3", "H4"):
        sheet.setStyle(cell, "bold", "add")
    for column, width in zip("ABCDEFGHI", (220, 110, 130, 110, 100, 100, 150, 145, 260)):
        try:
            sheet.setColumnWidth(column, width)
        except Exception:
            pass
    parent = doc.getObject("FA_Areas")
    if parent is not None:
        try:
            parent.addObject(sheet)
        except Exception:
            pass
    add_prop(sheet, "App::PropertyLink", "FA_SourceBIMWall", "FacilArquitectura", "Muro BIM analizado")
    add_prop(sheet, "App::PropertyLink", "FA_SourceCenterline", "FacilArquitectura", "Sketch base analizado")
    add_prop(sheet, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador")
    sheet.FA_SourceBIMWall = source_wall
    sheet.FA_SourceCenterline = source_centerline
    sheet.FA_GeneratedBy = GENERATED_BY
    return sheet


def generate_rectangular_areas(doc=None, walls=None):
    """Create the legacy-compatible rectangular room analysis.

    The caller may provide one or several BIM walls.  When omitted, the module
    keeps the historical selection/fallback behavior for compatibility.
    """
    global WALL_HALF_WIDTH_MM

    doc = doc or App.ActiveDocument
    if doc is None:
        raise RuntimeError("Abra un documento antes de ejecutar la macro.")

    source_walls = list(walls or selected_bim_walls(doc))
    source_walls = [
        wall
        for wall in source_walls
        if is_bim_wall(wall) and wall_centerline(wall) is not None
    ]
    if not source_walls:
        raise RuntimeError("No se encontraron muros BIM con eje/base utilizable.")

    unique_walls = []
    seen_walls = set()
    for wall in source_walls:
        key = str(getattr(wall, "Name", "") or id(wall))
        if key not in seen_walls:
            seen_walls.add(key)
            unique_walls.append(wall)
    source_walls = unique_walls

    wall_sketches = unique_centerlines(source_walls)
    source_wall = source_walls[0]
    wall_sketch = wall_sketches[0] if wall_sketches else None
    if wall_sketch is None:
        raise RuntimeError("No se encontro un sketch de centros de muros.")

    records = room_labels(doc)
    if not records:
        raise RuntimeError("No se encontraron rotulos de recintos con area.")

    segments = []
    for sketch in wall_sketches:
        segments.extend(global_line_segments(sketch))

    thicknesses = []
    for wall in source_walls:
        value = quantity_value(getattr(wall, "Width", 0.0))
        if value <= 0.0:
            value = quantity_value(getattr(wall, "FA_Thickness_mm", 0.0), 120.0)
        thicknesses.append(value)
    wall_thickness = sum(thicknesses) / len(thicknesses)
    WALL_HALF_WIDTH_MM = max(0.0, wall_thickness * 0.5)
    if not segments:
        raise RuntimeError("El sketch de muros no contiene lineas ortogonales utilizables.")

    transaction_open = False
    doc.openTransaction("FA Analisis de areas rectangulares")
    transaction_open = True
    try:
        group = ensure_group(doc)
        add_prop(group, "App::PropertyLink", "FA_SourceBIMWall", "FacilArquitectura", "Muro BIM analizado")
        add_prop(group, "App::PropertyLink", "FA_SourceCenterline", "FacilArquitectura", "Sketch base analizado")
        add_prop(group, "App::PropertyLinkList", "FA_SourceBIMWalls", "FacilArquitectura", "Muros BIM analizados")
        add_prop(group, "App::PropertyLinkList", "FA_SourceCenterlines", "FacilArquitectura", "Ejes base analizados")
        add_prop(group, "App::PropertyLength", "FA_WallThickness", "FacilArquitectura", "Espesor del muro analizado")
        add_prop(group, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador")
        group.FA_SourceBIMWall = source_wall
        group.FA_SourceCenterline = wall_sketch
        group.FA_SourceBIMWalls = source_walls
        group.FA_SourceCenterlines = wall_sketches
        group.FA_WallThickness = wall_thickness
        group.FA_GeneratedBy = GENERATED_BY

        rows = []
        created = []
        labels = []
        prepared = []
        trusted_rectangles = []
        for record in records:
            direct = nearest_rectangle(record["point"], segments)
            if direct is not None and area_ratio_error(direct, record["program_area"]) <= DIRECT_AREA_TOLERANCE:
                prepared.append((record, direct, "geometric", 0.95))
                trusted_rectangles.append(direct)
            else:
                prepared.append((record, direct, None, None))

        occupied_rectangles = list(trusted_rectangles)
        for record, direct, mode, confidence in prepared:
            rectangle = direct
            if mode is None:
                rectangle, confidence = guided_rectangle(
                    record, segments, occupied_rectangles, room_records=records
                )
                mode = "guided" if rectangle is not None else "program"
                if rectangle is not None and area_ratio_error(rectangle, record["program_area"]) > 0.10:
                    rectangle = fit_target_area_on_guides(record, rectangle, occupied_rectangles)
                    confidence = 0.72
                    mode = "guided_fit"
            if rectangle is None:
                rectangle = program_rectangle(record)
                confidence = 0.50

            row = dict(record)
            row["rectangle"] = rectangle
            row["area"] = None
            obj, label, area_m2 = create_rectangle(
                doc,
                group,
                record,
                rectangle,
                mode=mode,
                confidence=confidence,
                source_wall=source_wall,
                source_centerline=wall_sketch,
            )
            row["area"] = area_m2
            row["status"] = {
                "geometric": "Geometrico",
                "guided": "Inferido con guias",
                "guided_fit": "Dos guias + area",
                "program": "Programatico",
            }[mode]
            created.append(obj)
            if label is not None:
                labels.append(label)
            rows.append(row)
            if mode != "geometric":
                occupied_rectangles.append(rectangle)

        program_total = sum(float(row["program_area"]) for row in rows)
        calculated_total = sum(float(row["area"] or 0.0) for row in rows)
        add_prop(group, "App::PropertyInteger", "FA_RoomCount", "FacilArquitectura", "Cantidad de recintos")
        add_prop(group, "App::PropertyFloat", "FA_ProgramAreaTotalM2", "FacilArquitectura", "Area programada total")
        add_prop(group, "App::PropertyFloat", "FA_CalculatedAreaTotalM2", "FacilArquitectura", "Area rectangular total")
        add_prop(group, "App::PropertyFloat", "FA_TotalDifferenceM2", "FacilArquitectura", "Diferencia total")
        group.FA_RoomCount = len(rows)
        group.FA_ProgramAreaTotalM2 = program_total
        group.FA_CalculatedAreaTotalM2 = calculated_total
        group.FA_TotalDifferenceM2 = calculated_total - program_total

        sheet = write_analysis_sheet(
            doc,
            rows,
            source_wall=source_wall,
            source_centerline=wall_sketch,
        )
        doc.recompute()
        doc.commitTransaction()
        transaction_open = False
    except Exception:
        if transaction_open:
            try:
                doc.abortTransaction()
            except Exception:
                pass
        raise

    App.Console.PrintMessage(
        "[FACILARQ][AREAS RECTANGULARES] Completado: %d de %d recintos | "
        "muros=%d | ejes=%d | hoja=%s\n"
        % (len(created), len(records), len(source_walls), len(wall_sketches), sheet.Label)
    )
    return {
        "walls": source_walls,
        "centerlines": wall_sketches,
        "group": group,
        "areas": created,
        "labels": labels,
        "rows": rows,
        "sheet": sheet,
    }


if __name__ == "__main__":
    RECTANGULAR_AREA_RESULT = generate_rectangular_areas()
