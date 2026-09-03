"""Compact platform generator driven by one selected source line."""

from __future__ import annotations

from dataclasses import replace

import FreeCAD
import Part

from ...core.bim_structure_utils import add_to_container, is_building, is_level
from ...core.naming import safe_name
from ...core.project_structure import set_prop
from .calculator import calculate_line_layout
from .planner import plan_compact_platform
from .properties import (
    GENERATED_BY,
    MODULE_TYPE,
    PROPERTY_GROUP,
    read_parameter_sheet,
    set_root_properties,
    tag_representation,
    write_parameter_sheet,
)
from .source import axis_reference_from_source, find_host_wall
from .validation import PlatformValidationError, normalize_options


COMPACT_MODE = "source_line_compact"
BODY_NAME = "Cuerpo_Plataforma"
GLASS_NAME = "Vidrios_Plataforma"
AREAS_NAME = "Areas_Atencion_Plataforma"


def create_compact_platform(doc, axis_reference, values=None):
    options = normalize_options(values)
    frame = axis_reference.frame(options.invert_direction)
    options = replace(
        options,
        total_width_mm=frame.length_mm,
        origin_x_mm=frame.p0[0],
        front_offset_mm=frame.p0[1],
        create_functional_zones=False,
    )
    layout = calculate_line_layout(options)
    host, ambiguous = find_host_wall(doc, axis_reference)
    _platform_log(
        "Fuente %s/%s | longitud %.1f mm | puestos %d | lado %s"
        % (
            getattr(axis_reference.source_object, "Name", "?"),
            axis_reference.source_subelement or "objeto",
            frame.length_mm,
            options.service_positions,
            options.staff_side,
        )
    )
    if ambiguous:
        _platform_log("Host BIM ambiguo; la plataforma se crea sin muro nuevo.", warning=True)
    elif host is not None:
        _platform_log("Muro BIM reutilizado como HostWall: %s" % host.Label)
    else:
        _platform_log("No se detecto HostWall; se construye solamente desde la linea.")

    root = doc.addObject("App::DocumentObjectGroup", _unique_name(doc, "FA_ServicePlatformFront"))
    root.Label = _unique_label(doc, "Plataforma de atencion", exclude=root)
    sheet = doc.addObject("Spreadsheet::Sheet", _unique_name(doc, "Spreadsheet_Platform"))
    sheet.Label = _unique_label(doc, "Parametros de plataforma", exclude=sheet)
    _hide_auxiliary(sheet)
    body = doc.addObject("Part::Feature", _unique_name(doc, BODY_NAME))
    body.Label = BODY_NAME
    glass = doc.addObject("Part::Feature", _unique_name(doc, GLASS_NAME))
    glass.Label = GLASS_NAME
    root.addObject(body)
    root.addObject(glass)
    _place_in_spatial_container(root, axis_reference.source_object)

    write_parameter_sheet(sheet, options)
    set_root_properties(root, options, layout, sheet)
    _set_compact_contract(root, axis_reference, options, host, body, glass)
    _set_representation_contract(body, root, axis_reference, host, "body")
    _set_representation_contract(glass, root, axis_reference, host, "glass")
    areas = _update_shapes(doc, root, body, glass, None, frame, options)
    doc.recompute()
    _platform_log("Creacion completada: 1 propietario, 2 geometrías visibles, 0 muros creados.")
    return {
        "root": root,
        "sheet": sheet,
        "body": body,
        "glass": glass,
        "areas": areas,
        "layout": layout,
        "host_wall": host,
        "axis": axis_reference,
        "compact": True,
    }


def update_compact_platform(doc, root):
    source = _linked(getattr(root, "SourceObject", None)) or _linked(
        getattr(root, "FA_SourceObject", None)
    )
    subelement = str(
        getattr(root, "SourceSubelement", "")
        or getattr(root, "FA_SourceSubelement", "")
        or ""
    )
    axis_reference = axis_reference_from_source(source, subelement)
    sheet = _linked(getattr(root, "FA_ParameterSheet", None))
    if sheet is None:
        raise PlatformValidationError("La plataforma no conserva Spreadsheet_Platform.")
    options = _read_compact_options(root, sheet)
    frame = axis_reference.frame(options.invert_direction)
    options = replace(
        options,
        total_width_mm=frame.length_mm,
        origin_x_mm=frame.p0[0],
        front_offset_mm=frame.p0[1],
        create_functional_zones=False,
    )
    layout = calculate_line_layout(options)
    current_host = _linked(getattr(root, "HostWall", None)) or _linked(
        getattr(root, "FA_HostWall", None)
    )
    host, ambiguous = find_host_wall(doc, axis_reference, existing=current_host)
    if ambiguous:
        _platform_log("Host BIM ambiguo durante actualizacion; se conserva el enlace anterior.", warning=True)
    body = _linked(getattr(root, "FA_BodyRepresentation", None)) or _child_by_role(root, "body")
    glass = _linked(getattr(root, "FA_GlassRepresentation", None)) or _child_by_role(root, "glass")
    if body is None:
        body = doc.addObject("Part::Feature", _unique_name(doc, BODY_NAME))
        body.Label = BODY_NAME
        root.addObject(body)
    if glass is None:
        glass = doc.addObject("Part::Feature", _unique_name(doc, GLASS_NAME))
        glass.Label = GLASS_NAME
        root.addObject(glass)
    areas = _linked(getattr(root, "FA_AreasRepresentation", None))
    write_parameter_sheet(sheet, options)
    set_root_properties(root, options, layout, sheet)
    _set_compact_contract(root, axis_reference, options, host, body, glass)
    _set_representation_contract(body, root, axis_reference, host, "body")
    _set_representation_contract(glass, root, axis_reference, host, "glass")
    areas = _update_shapes(doc, root, body, glass, areas, frame, options)
    doc.recompute()
    _platform_log(
        "Actualizacion completada | longitud %.1f mm | puestos %d | sin duplicados."
        % (frame.length_mm, options.service_positions)
    )
    return {
        "root": root,
        "sheet": sheet,
        "body": body,
        "glass": glass,
        "areas": areas,
        "layout": layout,
        "host_wall": host,
        "axis": axis_reference,
        "compact": True,
        "removed": 0,
    }


def _update_shapes(doc, root, body, glass, areas, frame, options):
    plan = plan_compact_platform(options)
    body.Shape = Part.makeCompound([_box_shape(spec, frame) for spec in plan.body])
    glass.Shape = Part.makeCompound([_box_shape(spec, frame) for spec in plan.glass])
    set_prop(
        root,
        "App::PropertyInteger",
        "FA_GlassOpeningCount",
        PROPERTY_GROUP,
        "Cantidad de aberturas reales en el vidrio",
        plan.glass_opening_count,
    )
    set_prop(
        glass,
        "App::PropertyInteger",
        "FA_GlassOpeningCount",
        PROPERTY_GROUP,
        "Cantidad de aberturas reales en el vidrio",
        plan.glass_opening_count,
    )
    if options.glass_opening_enabled:
        _platform_log("Glass openings enabled")
        _platform_log("Glass opening count: %d" % plan.glass_opening_count)
        _platform_log("Glass opening width: %.1f mm" % options.glass_opening_width_mm)
        _platform_log("Glass opening height: %.1f mm" % options.glass_opening_height_mm)
    try:
        body.ViewObject.ShapeColor = (0.72, 0.46, 0.24)
        glass.ViewObject.ShapeColor = (0.45, 0.75, 0.95)
        glass.ViewObject.Transparency = 70
    except Exception:
        pass
    if options.show_service_areas:
        if areas is None:
            areas = doc.addObject("Part::Feature", _unique_name(doc, AREAS_NAME))
            areas.Label = AREAS_NAME
            tag_representation(areas, root, "Analysis", "service_areas")
            set_prop(root, "App::PropertyLinkHidden", "FA_AreasRepresentation", PROPERTY_GROUP, "Areas opcionales", areas)
            _hide_in_tree(areas)
        specs = list(plan.staff_areas) + list(plan.public_areas)
        areas.Shape = Part.makeCompound([_box_shape(spec, frame) for spec in specs])
        try:
            areas.ViewObject.ShapeColor = (0.25, 0.65, 0.85)
            areas.ViewObject.Transparency = 85
            areas.ViewObject.Visibility = True
        except Exception:
            pass
    elif areas is not None and str(getattr(areas, "FA_GeneratedBy", "")) == GENERATED_BY:
        try:
            doc.removeObject(areas.Name)
        except Exception:
            pass
        areas = None
    return areas


def _box_shape(spec, frame):
    shape = Part.makeBox(float(spec.length), float(spec.depth), float(spec.height))
    local = FreeCAD.Placement(
        FreeCAD.Vector(float(spec.x), float(spec.y), float(spec.z)), FreeCAD.Rotation()
    )
    world = FreeCAD.Placement(
        FreeCAD.Vector(*frame.p0), FreeCAD.Rotation(FreeCAD.Vector(0.0, 0.0, 1.0), frame.angle_deg)
    )
    shape.Placement = world.multiply(local)
    return shape


def _set_compact_contract(root, axis, options, host, body, glass):
    pairs = (
        ("App::PropertyString", "FA_GenerationMode", "Modo de generacion", COMPACT_MODE),
        ("App::PropertyString", "IfcType", "Clasificacion BIM", "Furniture"),
        ("App::PropertyString", "PredefinedType", "Tipo IFC predefinido", "USERDEFINED"),
        ("App::PropertyString", "ObjectType", "Tipo de objeto", "Service Platform"),
        ("App::PropertyBool", "FA_CreateWall", "Crear muro automaticamente", False),
        ("App::PropertyLink", "FA_SourceObject", "Objeto fuente", axis.source_object),
        ("App::PropertyString", "FA_SourceKind", "Tipo de fuente", axis.source_kind),
        ("App::PropertyString", "FA_SourceSubelement", "Subelemento fuente", axis.source_subelement),
        ("App::PropertyLink", "FA_HostWall", "Muro BIM anfitrion", host),
        ("App::PropertyLink", "SourceObject", "Objeto fuente", axis.source_object),
        ("App::PropertyString", "SourceSubelement", "Subelemento fuente", axis.source_subelement),
        ("App::PropertyLink", "HostWall", "Muro BIM anfitrion", host),
        ("App::PropertyInteger", "NumeroPuestos", "Numero de puestos", options.service_positions),
        ("App::PropertyLength", "LongitudTotal", "Longitud derivada de la linea", options.total_width_mm),
        ("App::PropertyLength", "AlturaMostrador", "Altura del mostrador", options.desk_height_mm),
        ("App::PropertyLength", "CotaSuperiorVidrio", "Cota superior del vidrio", options.glass_top_mm),
        ("App::PropertyLength", "AnchoAberturaVidrio", "Ancho del hueco real en cada pano", options.glass_opening_width_mm),
        ("App::PropertyLength", "AltoAberturaVidrio", "Alto del hueco real en cada pano", options.glass_opening_height_mm),
        ("App::PropertyLength", "AlturaAberturaVidrio", "Cota inferior del hueco real", options.glass_opening_bottom_mm),
        ("App::PropertyBool", "MostrarAberturaVidrio", "Crear una abertura por puesto", options.glass_opening_enabled),
        ("App::PropertyString", "FA_GlassOpeningDimensionStatus", "Estado de las dimensiones del hueco", "PROVISIONAL_EDITABLE_NO_NORMATIVO"),
        ("App::PropertyLength", "ProfundidadEscritorio", "Profundidad del escritorio", options.desk_depth_mm),
        ("App::PropertyString", "LadoFuncionario", "Lado mirando P0 a P1", options.staff_side),
        ("App::PropertyBool", "InvertirDireccion", "Intercambiar P0 y P1", options.invert_direction),
        ("App::PropertyBool", "MostrarAreasAtencion", "Mostrar areas opcionales", options.show_service_areas),
        ("App::PropertyLink", "FA_BodyRepresentation", "Geometria opaca", body),
        ("App::PropertyLink", "FA_GlassRepresentation", "Geometria de vidrio", glass),
    )
    for prop_type, name, description, value in pairs:
        set_prop(root, prop_type, name, PROPERTY_GROUP, description, value)
    try:
        root.setEditorMode("LongitudTotal", 1)
        root.setEditorMode("FA_TotalWidth_mm", 1)
        root.setEditorMode("FA_CreateWall", 1)
        root.setEditorMode("FA_GlassOpeningDimensionStatus", 1)
    except Exception:
        pass


def _set_representation_contract(obj, root, axis, host, part):
    tag_representation(obj, root, "Model", part)
    set_prop(obj, "App::PropertyLink", "SourceObject", PROPERTY_GROUP, "Objeto fuente", axis.source_object)
    set_prop(obj, "App::PropertyString", "SourceSubelement", PROPERTY_GROUP, "Subelemento fuente", axis.source_subelement)
    set_prop(obj, "App::PropertyLink", "HostWall", PROPERTY_GROUP, "Muro BIM anfitrion", host)


def _read_compact_options(root, sheet):
    options = read_parameter_sheet(sheet)
    values = {field: getattr(options, field) for field in options.__dataclass_fields__}
    mapping = {
        "service_positions": "NumeroPuestos",
        "desk_height_mm": "AlturaMostrador",
        "glass_top_mm": "CotaSuperiorVidrio",
        "glass_opening_width_mm": "AnchoAberturaVidrio",
        "glass_opening_height_mm": "AltoAberturaVidrio",
        "glass_opening_bottom_mm": "AlturaAberturaVidrio",
        "glass_opening_enabled": "MostrarAberturaVidrio",
        "desk_depth_mm": "ProfundidadEscritorio",
        "staff_side": "LadoFuncionario",
        "invert_direction": "InvertirDireccion",
        "show_service_areas": "MostrarAreasAtencion",
    }
    for key, prop in mapping.items():
        if not hasattr(root, prop):
            continue
        raw = getattr(root, prop)
        if key in ("service_positions",):
            values[key] = int(raw)
        elif key in ("invert_direction", "show_service_areas", "glass_opening_enabled"):
            values[key] = bool(raw)
        elif key == "staff_side":
            values[key] = str(raw).strip().lower()
        else:
            values[key] = float(getattr(raw, "Value", raw))
    return normalize_options(values)


def _place_in_spatial_container(root, source):
    pending = list(getattr(source, "InList", []) or [])
    seen = set()
    fallback = None
    while pending:
        candidate = pending.pop(0)
        name = str(getattr(candidate, "Name", ""))
        if not name or name in seen:
            continue
        seen.add(name)
        if is_level(candidate):
            add_to_container(candidate, root)
            set_prop(root, "App::PropertyString", "FA_TargetLevel", PROPERTY_GROUP, "Nivel BIM", candidate.Name)
            return
        if is_building(candidate) and fallback is None:
            fallback = candidate
        pending.extend(list(getattr(candidate, "InList", []) or []))
    if fallback is not None:
        add_to_container(fallback, root)


def _child_by_role(root, role):
    return next(
        (
            obj
            for obj in list(getattr(root, "Group", []) or [])
            if str(getattr(obj, "FA_ModulePart", "")) == role
        ),
        None,
    )


def _hide_auxiliary(obj):
    try:
        obj.ViewObject.Visibility = False
    except Exception:
        pass
    _hide_in_tree(obj)


def _hide_in_tree(obj):
    try:
        obj.ViewObject.ShowInTree = False
    except Exception:
        pass


def _linked(value):
    if isinstance(value, tuple) and value:
        return value[0]
    return value


def _unique_name(doc, base):
    base = safe_name(base)
    if doc.getObject(base) is None:
        return base
    index = 2
    while doc.getObject("%s_%03d" % (base, index)) is not None:
        index += 1
    return "%s_%03d" % (base, index)


def _unique_label(doc, base, exclude=None):
    labels = {str(getattr(obj, "Label", "")) for obj in doc.Objects if obj is not exclude}
    if base not in labels:
        return base
    index = 2
    while "%s %d" % (base, index) in labels:
        index += 1
    return "%s %d" % (base, index)


def _platform_log(text, warning=False):
    line = "[FACILARQ][PLATAFORMA] " + str(text) + "\n"
    if warning:
        FreeCAD.Console.PrintWarning(line)
    else:
        FreeCAD.Console.PrintMessage(line)
