"""Native BIM axis-system and column helpers for FacilArquitecturaWB.

Descripcion: convierte lineas de un Sketch en Arch Axis, AxisSystem y columnas
Arch Structure, contenidas directamente en un Building Storey nativo.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 22:10 UTC-06:00.
Version: 0.2.0.
Instrucciones de mantenimiento: no crear grupos FA intermedios para columnas;
conservar el Sketch como fuente trazable y el Level.Group como contencion.
"""

from __future__ import annotations

import math

import FreeCAD

from .command_errors import UserFacingError
from .bim_structure_utils import add_to_level, is_level
from .naming import safe_name
from .project_structure import msg, set_prop, warn

try:
    import Arch
except Exception:  # pragma: no cover - depende del runtime de FreeCAD
    Arch = None


GENERATED_BY_AXES_COLUMNS = "FA_CreateColumnsFromSketch"
LEGACY_GENERATORS = ("FA_CreateAxesColumnsBIM", GENERATED_BY_AXES_COLUMNS)
ANGLE_TOLERANCE_DEG = 4.0
MIN_AXIS_SEGMENT_MM = 20.0
MAX_COLUMN_INSTANCES = 2000


def find_axis_sketch_from_selection(objects):
    """Return the single selected sketch intended to define the BIM grid."""
    candidates = []
    pending = list(objects or [])
    seen = set()
    while pending:
        obj = pending.pop(0)
        identity = str(getattr(obj, "Name", "") or id(obj))
        if identity in seen:
            continue
        seen.add(identity)

        source = getattr(obj, "FA_SourceSketch", None)
        if source is not None:
            pending.append(source)
        if _is_sketch(obj) and _sketch_line_count(obj) > 0:
            candidates.append(obj)
            continue
        for attr in ("Group", "Objects"):
            try:
                pending.extend(list(getattr(obj, attr, []) or []))
            except Exception:
                pass

    candidates = _unique_objects(candidates)
    if len(candidates) == 1:
        return candidates[0]
    preferred = [sketch for sketch in candidates if _is_column_axis_sketch(sketch)]
    if len(preferred) == 1:
        return preferred[0]
    if not candidates:
        raise UserFacingError("Seleccione el sketch que contiene los ejes o las cruces de columnas.")
    raise UserFacingError("La seleccion contiene varios sketches de ejes. Seleccione solamente uno.")


def create_bim_axes_and_columns_from_sketch(doc, target_container, sketch, params):
    """Create two Arch Axis families, one AxisSystem and one replicated Arch column."""
    _require_bim_tools()
    settings = _ensure_sketch_parameters(sketch, params)
    segments = _segments_from_sketch(sketch)
    specs, omitted_family_count = axis_family_specs_from_segments(
        segments,
        angle_tolerance_deg=ANGLE_TOLERANCE_DEG,
        position_tolerance=settings["axis_tolerance"],
        extension=settings["axis_extension"],
    )
    if omitted_family_count:
        raise UserFacingError(
            "El sketch contiene mas de dos direcciones de ejes (%d adicionales). "
            "Separe cada sistema estructural en un sketch distinto." % omitted_family_count
        )
    system_point_count = len(specs[0]["positions"]) * len(specs[1]["positions"])
    source_points = source_cross_points_from_specs(
        specs,
        intersection_tolerance=settings["axis_tolerance"],
    )
    if not source_points:
        raise UserFacingError(
            "No se encontraron cruces reales entre las dos familias. "
            "El sketch debe contener lineas que se intersecten en cada columna."
        )
    if system_point_count > MAX_COLUMN_INSTANCES:
        raise UserFacingError(
            "El sistema produciria %d intersecciones; el limite de seguridad es %d."
            % (system_point_count, MAX_COLUMN_INSTANCES)
        )

    removed = remove_previous_axes_columns(doc, source_sketch=sketch)
    if removed:
        msg("Sistema BIM anterior reemplazado para %s: %d objetos" % (_object_label(sketch), removed))

    axes = []
    for family_index, spec in enumerate(specs, start=1):
        axis = _make_arch_axis(spec, sketch, family_index)
        axes.append(axis)

    system_name = safe_name("FA_AxisSystem_" + _object_label(sketch), "FA_AxisSystem")
    system = Arch.makeAxisSystem(axes, name=system_name)
    if system is None:
        raise RuntimeError("Arch.makeAxisSystem no pudo crear el sistema de ejes.")
    system.Label = "Sistema de ejes BIM - " + _object_label(sketch)
    _tag_generated_object(system, sketch, "axis_system")
    set_prop(
        system,
        "App::PropertyInteger",
        "FA_GridPointCount",
        "FacilArquitectura",
        "Cantidad de intersecciones del sistema",
        system_point_count,
    )
    set_prop(
        system,
        "App::PropertyInteger",
        "FA_SourceGridPointCount",
        "FacilArquitectura",
        "Cantidad de cruces realmente dibujados en el sketch",
        len(source_points),
    )
    _add_to_target(target_container, system, sketch)
    for axis in axes:
        _add_to_target(target_container, axis, sketch)

    doc.recompute()
    points = list(system.Proxy.getPoints(system) or [])
    if len(points) != system_point_count:
        raise UserFacingError(
            "El sistema BIM calculo %d intersecciones, pero se esperaban %d. Revise lineas paralelas o muy cortas."
            % (len(points), system_point_count)
        )

    column_rotation = _grid_rotation_deg(specs)
    use_axis_spread = len(source_points) == system_point_count and abs(column_rotation) <= 1e-6
    placement_mode = "axis_system" if use_axis_spread else "sketch_crosses"
    if len(source_points) == system_point_count and not use_axis_spread:
        placement_mode = "sketch_crosses_rotated"
    column_objects = []
    if use_axis_spread:
        column = _make_arch_column(
            sketch,
            settings,
            safe_name("FA_ColumnGrid_" + _object_label(sketch), "FA_ColumnGrid"),
            "Columnas en sistema de ejes - " + _object_label(sketch),
            (0.0, 0.0, 0.0),
            column_rotation,
            axis=system,
            role="columns",
            count=system_point_count,
        )
        _set_column_placement_mode(column, placement_mode)
        _add_to_target(target_container, column, sketch)
        column_objects.append(column)
    else:
        for index, point in enumerate(source_points, start=1):
            column = _make_arch_column(
                sketch,
                settings,
                safe_name("FA_Column_%03d_%s" % (index, _object_label(sketch)), "FA_Column"),
                "Columna BIM %03d - %s" % (index, _object_label(sketch)),
                point,
                column_rotation,
                role="column",
                count=1,
            )
            set_prop(
                column,
                "App::PropertyLink",
                "FA_AxisSystem",
                "FacilArquitectura",
                "Sistema de ejes BIM de referencia",
                system,
            )
            set_prop(
                column,
                "App::PropertyInteger",
                "FA_GridPointIndex",
                "FacilArquitectura",
                "Indice del cruce fuente",
                index,
            )
            _set_column_placement_mode(column, placement_mode)
            _add_to_target(target_container, column, sketch)
            column_objects.append(column)

    doc.recompute()
    solid_count = sum(
        len(list(getattr(getattr(column, "Shape", None), "Solids", []) or []))
        for column in column_objects
    )
    if solid_count != len(source_points):
        raise RuntimeError(
            "Las columnas BIM generaron %d solidos, pero el sketch contiene %d cruces."
            % (solid_count, len(source_points))
        )
    try:
        sketch.ViewObject.Visibility = False
    except Exception:
        pass
    msg(
        "Sistema BIM creado desde %s: familias=%d | ejes=%s | intersecciones=%d | columnas=%d | modo=%s"
        % (
            _object_label(sketch),
            len(axes),
            "+".join(str(len(spec["positions"])) for spec in specs),
            system_point_count,
            len(source_points),
            placement_mode,
        )
    )
    return {
        "sketch": sketch,
        "axes": axes,
        "system": system,
        "column": column_objects[0],
        "columns": column_objects,
        "points": source_points,
        "system_points": points,
    }


def axis_family_specs_from_segments(
    segments,
    angle_tolerance_deg=ANGLE_TOLERANCE_DEG,
    position_tolerance=10.0,
    extension=1000.0,
):
    """Analyze sketch lines and return two non-uniform BIM axis family specifications."""
    records = []
    for segment in segments or []:
        x1, y1, z1, x2, y2, z2 = [float(value) for value in segment]
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < MIN_AXIS_SEGMENT_MM:
            continue
        angle = math.atan2(dy, dx) % math.pi
        records.append(
            {
                "segment": (x1, y1, z1, x2, y2, z2),
                "length": length,
                "angle": angle,
            }
        )
    if not records:
        raise UserFacingError("El sketch no contiene segmentos lineales utilizables como ejes.")

    clusters = []
    tolerance = math.radians(float(angle_tolerance_deg))
    for record in sorted(records, key=lambda item: item["angle"]):
        target = None
        for cluster in clusters:
            if _axis_angle_difference(record["angle"], _cluster_angle(cluster)) <= tolerance:
                target = cluster
                break
        if target is None:
            target = []
            clusters.append(target)
        target.append(record)
    clusters.sort(key=lambda cluster: -sum(item["length"] for item in cluster))
    if len(clusters) < 2:
        raise UserFacingError("El sketch debe contener dos familias de ejes no paralelas.")

    selected = clusters[:2]
    specs = [_family_spec(cluster, float(position_tolerance)) for cluster in selected]
    determinant = abs(_cross_2d(specs[0]["right"], specs[1]["right"]))
    if determinant < math.sin(math.radians(10.0)):
        raise UserFacingError("Las dos familias detectadas son casi paralelas y no forman una reticula valida.")

    intersections = []
    for first_position in specs[0]["positions"]:
        for second_position in specs[1]["positions"]:
            intersections.append(_line_family_intersection(specs[0], first_position, specs[1], second_position))
    z_level = sum(
        value
        for record in records
        for value in (record["segment"][2], record["segment"][5])
    ) / (2.0 * len(records))
    for spec in specs:
        along_values = [_dot_2d(point, spec["direction"]) for point in intersections]
        for record in spec["records"]:
            segment = record["segment"]
            along_values.extend(
                (
                    _dot_2d((segment[0], segment[1]), spec["direction"]),
                    _dot_2d((segment[3], segment[4]), spec["direction"]),
                )
            )
        minimum = min(along_values) - float(extension)
        maximum = max(along_values) + float(extension)
        spec["length"] = maximum - minimum
        spec["z"] = z_level
        first_position = spec["positions"][0]
        spec["origin"] = (
            spec["right"][0] * first_position + spec["direction"][0] * minimum,
            spec["right"][1] * first_position + spec["direction"][1] * minimum,
            z_level,
        )
        spec["distances"] = [0.0] + [
            spec["positions"][index] - spec["positions"][index - 1]
            for index in range(1, len(spec["positions"]))
        ]
        spec["rotation_deg"] = math.degrees(
            math.atan2(-spec["direction"][0], spec["direction"][1])
        )
        spec["numbering"] = "1,2,3" if abs(spec["direction"][1]) >= abs(spec["direction"][0]) else "A,B,C"
    specs.sort(key=lambda spec: 0 if spec["numbering"] == "1,2,3" else 1)
    return specs, max(0, len(clusters) - 2)


def source_cross_points_from_specs(specs, intersection_tolerance=10.0):
    """Return only intersections that are physically drawn by both source families."""
    if len(specs or []) != 2:
        return []
    tolerance = max(0.01, float(intersection_tolerance))
    result = []
    first_spec, second_spec = specs
    for first_record in first_spec["records"]:
        for second_record in second_spec["records"]:
            point = _bounded_segment_intersection(
                first_record["segment"],
                second_record["segment"],
                tolerance,
            )
            if point is None:
                continue
            first_position = min(
                first_spec["positions"],
                key=lambda value: abs(value - _dot_2d(point, first_spec["right"])),
            )
            second_position = min(
                second_spec["positions"],
                key=lambda value: abs(value - _dot_2d(point, second_spec["right"])),
            )
            snapped = _line_family_intersection(
                first_spec,
                first_position,
                second_spec,
                second_position,
            )
            z_value = sum(
                (
                    first_record["segment"][2],
                    first_record["segment"][5],
                    second_record["segment"][2],
                    second_record["segment"][5],
                )
            ) / 4.0
            _append_unique_point(result, (snapped[0], snapped[1], z_value), tolerance)
    return sorted(result, key=lambda point: (round(point[1], 6), round(point[0], 6), round(point[2], 6)))


def remove_previous_axes_columns(doc, source_sketch=None):
    """Remove only axis/column objects generated by this command for one source sketch."""
    source_name = str(getattr(source_sketch, "Name", "") or "")
    candidates = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "FA_GeneratedBy", "") or "") not in LEGACY_GENERATORS:
            continue
        if source_name:
            source = getattr(obj, "FA_SourceSketch", None)
            if str(getattr(source, "Name", "") or "") != source_name:
                continue
        candidates.append(obj)
    priority = {
        "column": 0,
        "columns": 0,
        "columns_group": 1,
        "axis_system": 2,
        "axis_family": 3,
    }
    candidates.sort(key=lambda obj: priority.get(str(getattr(obj, "FA_Role", "") or ""), 3))
    removed = 0
    for obj in candidates:
        name = str(getattr(obj, "Name", "") or "")
        if not name:
            continue
        try:
            if doc.getObject(name) is not None:
                doc.removeObject(name)
                removed += 1
        except Exception:
            pass
    return removed


def _make_arch_axis(spec, sketch, family_index):
    count = len(spec["positions"])
    label_kind = "1-%d" % count if spec["numbering"] == "1,2,3" else "A-%s" % _alpha_label(count)
    name = safe_name("FA_Axes_%s_%s" % (_object_label(sketch), label_kind), "FA_Axes")
    axis = Arch.makeAxis(num=count, size=1.0, name=name)
    if axis is None:
        raise RuntimeError("Arch.makeAxis no pudo crear la familia %d." % family_index)
    axis.Label = "Ejes BIM %s - %s" % (label_kind, _object_label(sketch))
    axis.Distances = [float(value) for value in spec["distances"]]
    axis.Angles = [0.0] * count
    axis.Length = float(spec["length"])
    axis.Placement = FreeCAD.Placement(
        FreeCAD.Vector(*spec["origin"]),
        FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), float(spec["rotation_deg"])),
    )
    _tag_generated_object(axis, sketch, "axis_family")
    set_prop(
        axis,
        "App::PropertyInteger",
        "FA_AxisFamilyIndex",
        "FacilArquitectura",
        "Indice de familia de ejes",
        family_index,
    )
    try:
        axis.ViewObject.NumberingStyle = spec["numbering"]
        axis.ViewObject.BubblePosition = "Both"
        axis.ViewObject.LineWidth = 2.0
        axis.ViewObject.LineColor = (0.85, 0.42, 0.10)
    except Exception:
        pass
    return axis


def _make_arch_column(sketch, settings, name, label, center, rotation_deg, axis=None, role="column", count=1):
    column = Arch.makeStructure(
        None,
        length=settings["column_width"],
        width=settings["column_depth"],
        height=settings["column_height"],
        name=name,
    )
    if column is None:
        raise RuntimeError("Arch.makeStructure no pudo crear una columna BIM.")
    column.Label = label
    rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), float(rotation_deg))
    column.Placement = FreeCAD.Placement(
        FreeCAD.Vector(center[0], center[1], center[2]),
        rotation,
    )
    if axis is not None:
        column.Axis = axis
    try:
        column.IfcType = "Column"
    except Exception:
        pass
    _link_column_parameters(column, sketch)
    _tag_generated_object(column, sketch, role)
    set_prop(
        column,
        "App::PropertyInteger",
        "FA_ColumnCount",
        "FacilArquitectura",
        "Cantidad de columnas representadas por este objeto",
        int(count),
    )
    try:
        column.ViewObject.ShapeColor = (0.72, 0.72, 0.76)
        column.ViewObject.LineColor = (0.20, 0.22, 0.24)
    except Exception:
        pass
    return column


def _set_column_placement_mode(column, placement_mode):
    set_prop(
        column,
        "App::PropertyString",
        "FA_ColumnPlacementMode",
        "FacilArquitectura",
        "Metodo utilizado para colocar la columna",
        str(placement_mode),
    )


def _add_to_target(target_container, obj, source_sketch):
    """Add an object to a native Level, with legacy group compatibility."""
    if is_level(target_container):
        add_to_level(target_container, obj, source_sketch=source_sketch)
        return
    try:
        target_container.addObject(obj)
    except Exception:
        pass


def _family_spec(cluster, position_tolerance):
    angle = _cluster_angle(cluster)
    direction = (math.cos(angle), math.sin(angle))
    right = (direction[1], -direction[0])
    dominant = right[0] if abs(right[0]) >= abs(right[1]) else right[1]
    if dominant < 0.0:
        direction = (-direction[0], -direction[1])
        right = (-right[0], -right[1])
    raw_positions = []
    for record in cluster:
        segment = record["segment"]
        midpoint = ((segment[0] + segment[3]) / 2.0, (segment[1] + segment[4]) / 2.0)
        raw_positions.append(_dot_2d(midpoint, right))
    return {
        "records": cluster,
        "direction": direction,
        "right": right,
        "positions": _cluster_values(raw_positions, position_tolerance),
    }


def _cluster_values(values, tolerance):
    groups = []
    for value in sorted(float(item) for item in values):
        if groups and abs(value - sum(groups[-1]) / len(groups[-1])) <= float(tolerance):
            groups[-1].append(value)
        else:
            groups.append([value])
    return [sum(group) / len(group) for group in groups]


def _cluster_angle(cluster):
    cosine = sum(item["length"] * math.cos(2.0 * item["angle"]) for item in cluster)
    sine = sum(item["length"] * math.sin(2.0 * item["angle"]) for item in cluster)
    angle = 0.5 * math.atan2(sine, cosine)
    return angle % math.pi


def _line_family_intersection(first, first_position, second, second_position):
    r1 = first["right"]
    r2 = second["right"]
    determinant = _cross_2d(r1, r2)
    return (
        (first_position * r2[1] - r1[1] * second_position) / determinant,
        (r1[0] * second_position - first_position * r2[0]) / determinant,
    )


def _segments_from_sketch(sketch):
    segments = []
    placement = getattr(sketch, "Placement", FreeCAD.Placement())
    try:
        geometry = list(getattr(sketch, "Geometry", []) or [])
    except Exception:
        geometry = []
    for item in geometry:
        start = getattr(item, "StartPoint", None)
        end = getattr(item, "EndPoint", None)
        if start is None or end is None:
            continue
        try:
            first = placement.multVec(FreeCAD.Vector(start.x, start.y, start.z))
            second = placement.multVec(FreeCAD.Vector(end.x, end.y, end.z))
            segments.append((first.x, first.y, first.z, second.x, second.y, second.z))
        except Exception:
            continue
    if segments:
        return _dedupe_segments(segments)

    try:
        edges = list(getattr(getattr(sketch, "Shape", None), "Edges", []) or [])
    except Exception:
        edges = []
    for edge in edges:
        try:
            vertices = list(edge.Vertexes)
            first = vertices[0].Point
            second = vertices[-1].Point
            segments.append((first.x, first.y, first.z, second.x, second.y, second.z))
        except Exception:
            continue
    return _dedupe_segments(segments)


def _dedupe_segments(segments):
    result = []
    seen = set()
    for segment in segments:
        first = tuple(round(float(value), 4) for value in segment[:3])
        second = tuple(round(float(value), 4) for value in segment[3:])
        key = tuple(sorted((first, second)))
        if key not in seen:
            seen.add(key)
            result.append(tuple(float(value) for value in segment))
    return result


def _ensure_sketch_parameters(sketch, params):
    definitions = (
        ("FA_AxisExtension", "axis_extension_mm", 1000.0, "Extension de los ejes fuera de la reticula"),
        ("FA_AxisTolerance", "axis_cluster_tolerance_mm", 10.0, "Tolerancia para agrupar lineas colineales"),
        ("FA_ColumnWidth", "column_width_mm", 400.0, "Dimension X de cada columna"),
        ("FA_ColumnDepth", "column_depth_mm", 400.0, "Dimension Y de cada columna"),
        ("FA_ColumnHeight", "column_height_mm", 3000.0, "Altura de cada columna"),
    )
    values = {}
    for property_name, parameter_name, fallback, description in definitions:
        default = float(params.get(parameter_name, fallback))
        value = _quantity_value(getattr(sketch, property_name, 0.0))
        if not hasattr(sketch, property_name):
            set_prop(
                sketch,
                "App::PropertyLength",
                property_name,
                "FacilArquitectura",
                description,
                default,
            )
            value = default
        elif value <= 0.0:
            try:
                setattr(sketch, property_name, default)
                value = default
            except Exception:
                pass
        values[property_name] = value if value > 0.0 else default
    return {
        "axis_extension": values["FA_AxisExtension"],
        "axis_tolerance": values["FA_AxisTolerance"],
        "column_width": values["FA_ColumnWidth"],
        "column_depth": values["FA_ColumnDepth"],
        "column_height": values["FA_ColumnHeight"],
    }


def _link_column_parameters(column, sketch):
    if not hasattr(column, "setExpression"):
        return
    sketch_name = str(getattr(sketch, "Name", "") or "")
    for column_property, sketch_property in (
        ("Length", "FA_ColumnWidth"),
        ("Width", "FA_ColumnDepth"),
        ("Height", "FA_ColumnHeight"),
    ):
        try:
            column.setExpression(column_property, "%s.%s" % (sketch_name, sketch_property))
        except Exception as exc:
            warn("No se pudo vincular %s de las columnas BIM: %s" % (column_property, exc))


def _tag_generated_object(obj, sketch, role):
    set_prop(obj, "App::PropertyLink", "FA_SourceSketch", "FacilArquitectura", "Sketch fuente", sketch)
    set_prop(
        obj,
        "App::PropertyString",
        "FA_GeneratedBy",
        "FacilArquitectura",
        "Generado por",
        GENERATED_BY_AXES_COLUMNS,
    )
    set_prop(obj, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol", role)


def _require_bim_tools():
    required = ("makeAxis", "makeAxisSystem", "makeStructure")
    if Arch is None or any(not hasattr(Arch, name) for name in required):
        raise UserFacingError("Arch/BIM no ofrece makeAxis, makeAxisSystem y makeStructure en esta instalacion.")


def _sketch_line_count(sketch):
    try:
        return sum(
            1
            for item in list(getattr(sketch, "Geometry", []) or [])
            if getattr(item, "StartPoint", None) is not None and getattr(item, "EndPoint", None) is not None
        )
    except Exception:
        return 0


def _is_sketch(obj):
    return str(getattr(obj, "TypeId", "") or "").startswith("Sketcher::") or hasattr(obj, "Geometry")


def _is_column_axis_sketch(sketch):
    kind = str(getattr(sketch, "FA_CenterlineKind", "") or "").strip().lower()
    element_type = str(getattr(sketch, "FA_ElementType", "") or "").strip().lower()
    label = _object_label(sketch).lower()
    return kind == "columns" or element_type in ("columnas", "columns") or label.endswith("_columnas")


def _unique_objects(objects):
    result = []
    seen = set()
    for obj in objects:
        identity = str(getattr(obj, "Name", "") or id(obj))
        if identity not in seen:
            seen.add(identity)
            result.append(obj)
    return result


def _object_label(obj):
    return str(getattr(obj, "Label", getattr(obj, "Name", "Sketch_Ejes")) or "Sketch_Ejes")


def _quantity_value(value):
    try:
        return float(getattr(value, "Value", value))
    except Exception:
        return 0.0


def _alpha_label(number):
    number = max(1, int(number))
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def _axis_angle_difference(first, second):
    delta = abs(float(first) - float(second)) % math.pi
    return min(delta, math.pi - delta)


def _grid_rotation_deg(specs):
    horizontal_spec = min(specs, key=lambda spec: abs(float(spec["direction"][1])))
    direction = horizontal_spec["direction"]
    angle = math.degrees(math.atan2(float(direction[1]), float(direction[0])))
    while angle >= 90.0:
        angle -= 180.0
    while angle < -90.0:
        angle += 180.0
    return 0.0 if abs(angle) <= 1e-9 else angle


def _bounded_segment_intersection(first, second, tolerance):
    p = (float(first[0]), float(first[1]))
    q = (float(second[0]), float(second[1]))
    r = (float(first[3]) - p[0], float(first[4]) - p[1])
    s = (float(second[3]) - q[0], float(second[4]) - q[1])
    determinant = _cross_2d(r, s)
    first_length = math.hypot(r[0], r[1])
    second_length = math.hypot(s[0], s[1])
    if abs(determinant) <= 1e-9 or first_length <= 1e-9 or second_length <= 1e-9:
        return None
    delta = (q[0] - p[0], q[1] - p[1])
    first_parameter = _cross_2d(delta, s) / determinant
    second_parameter = _cross_2d(delta, r) / determinant
    first_margin = float(tolerance) / first_length
    second_margin = float(tolerance) / second_length
    if not (-first_margin <= first_parameter <= 1.0 + first_margin):
        return None
    if not (-second_margin <= second_parameter <= 1.0 + second_margin):
        return None
    return (p[0] + first_parameter * r[0], p[1] + first_parameter * r[1])


def _append_unique_point(points, point, tolerance):
    limit = max(0.01, float(tolerance))
    for current in points:
        if math.hypot(float(current[0]) - float(point[0]), float(current[1]) - float(point[1])) <= limit:
            return
    points.append(tuple(float(value) for value in point))


def _dot_2d(first, second):
    return float(first[0]) * float(second[0]) + float(first[1]) * float(second[1])


def _cross_2d(first, second):
    return float(first[0]) * float(second[1]) - float(first[1]) * float(second[0])
