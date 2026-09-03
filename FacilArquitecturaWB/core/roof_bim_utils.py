"""Adaptador FreeCAD/BIM para techo, cerchas y clavadores de FacilArquitecturaWB.

Nombre: roof_bim_utils.py
Proposito: traducir planes de roof_system_core a objetos nativos Arch/BIM.
Funcion principal: extraer geometria de Sketches y materializar Arch Axis/Truss,
Arch Frame y Arch Roof, conservando enlaces FA hacia los Sketches fuente.
FreeCAD objetivo: 1.1.3.
Version: 0.5.0
Fecha y hora: 2026-08-30 16:55 America/Costa_Rica

Instrucciones de mantenimiento:
- Mantener el comando de sistema completo como ruta publicada; validar cambios geometricos en FreeCAD real.
- No introducir FreeCADGui ni Qt en este modulo.
- Mantener dry_run=True como modo seguro de diagnostico/planificacion.
- No presentar dimensiones de perfiles como calculo estructural.
- Conservar Sketches fuente y enlaces FA_SourceSketch/FA_SourceGeometryIndex.
- La referencia maestra del sistema es la cara superior del cordon superior de cercha.
- Roof usa directamente el Sketch cerrado solo cuando no necesita apilado; con clavadores
  proyectados usa un contorno auxiliar elevado hasta la cara superior de los clavadores.
- Frame usa un Frame y un perfil propio por faldon para evitar padres visuales multiples y orientar correctamente cada lado.
- El perfil de clavador tiene origen en el centro de su cara inferior (BasePoint=0), de modo
  que el path 3D sea la linea real de contacto con la cercha.
- Truss nativo exige una Base de una sola arista; FA crea una sola Draft Line como Base maestra
  y una sola cercha BIM, y usa la propiedad nativa Axis del Arch Component para repetirla.
- La Base maestra se desplaza hacia abajo HeightStart para que la linea fuente represente
  exactamente la cara superior del cordon. Arch/BIM oculta la Base al asignarla al Truss.
"""

from __future__ import annotations

import json
import math

import FreeCAD

from .command_errors import UserFacingError
from .project_structure import msg, set_prop, warn
from .roof_system_core import (
    PurlinDefaults,
    RoofDefaults,
    RoofPlanError,
    TrussDefaults,
    build_roof_system_plan,
    plan_purlins,
    plan_projected_purlins,
    plan_roof,
    plan_trusses,
)

try:
    import Arch
except Exception:  # pragma: no cover
    Arch = None

try:
    import Part
except Exception:  # pragma: no cover
    Part = None

try:
    import Draft
except Exception:  # pragma: no cover
    Draft = None


GENERATOR = "FA_RoofSystem"
SCHEMA_VERSION = 4


def _is_sketch(obj) -> bool:
    return bool(obj) and (
        str(getattr(obj, "TypeId", "")) == "Sketcher::SketchObject"
        or hasattr(obj, "Geometry")
    )


def _vector_tuple(v):
    return (float(v.x), float(v.y), float(v.z))


def _global_point(sketch, point):
    vec = FreeCAD.Vector(float(point.x), float(point.y), float(getattr(point, "z", 0.0)))
    try:
        return sketch.Placement.multVec(vec)
    except Exception:
        return vec


def sketch_line_segments(sketch):
    """Extrae solamente lineas no constructivas de un Sketch en coordenadas globales."""
    if not _is_sketch(sketch):
        raise UserFacingError("La fuente debe ser un Sketch.")
    segments = []
    geometry = list(getattr(sketch, "Geometry", []) or [])
    for index, geo in enumerate(geometry):
        try:
            if bool(sketch.getConstruction(index)):
                continue
        except Exception:
            pass
        if not hasattr(geo, "StartPoint") or not hasattr(geo, "EndPoint"):
            continue
        start = _global_point(sketch, geo.StartPoint)
        end = _global_point(sketch, geo.EndPoint)
        segments.append(
            {
                "source_index": index,
                "start": list(_vector_tuple(start)),
                "end": list(_vector_tuple(end)),
            }
        )
    if not segments:
        raise UserFacingError("El Sketch no contiene lineas no constructivas utilizables.")
    return segments


def sketch_outline_points(sketch, tolerance_mm=0.1):
    """Ordena un unico lazo de lineas del Sketch para usarlo como contorno de Roof."""
    segments = sketch_line_segments(sketch)
    unused = list(segments)
    first = unused.pop(0)
    ordered = [first["start"], first["end"]]

    def close(a, b):
        return math.dist(a, b) <= float(tolerance_mm)

    while unused:
        tail = ordered[-1]
        match = None
        reverse = False
        for idx, seg in enumerate(unused):
            if close(tail, seg["start"]):
                match = idx
                break
            if close(tail, seg["end"]):
                match = idx
                reverse = True
                break
        if match is None:
            raise UserFacingError("El Sketch de cubierta debe formar un unico contorno lineal continuo.")
        seg = unused.pop(match)
        ordered.append(seg["start"] if reverse else seg["end"])
    if not close(ordered[0], ordered[-1]):
        raise UserFacingError("El Sketch de cubierta no esta cerrado.")
    return ordered[:-1]


def _core_error(callable_obj, *args, **kwargs):
    try:
        return callable_obj(*args, **kwargs)
    except RoofPlanError as exc:
        raise UserFacingError(str(exc))


def plan_trusses_from_sketch(sketch, params=None):
    return _core_error(
        plan_trusses,
        sketch_line_segments(sketch),
        TrussDefaults(**dict(params or {})),
    )


def plan_purlins_from_sketch(sketch, params=None):
    return _core_error(
        plan_purlins,
        sketch_line_segments(sketch),
        PurlinDefaults(**dict(params or {})),
    )



def plan_projected_purlins_from_sketch(purlin_sketch, roof_sketch, purlin_params=None, roof_params=None):
    """Planifica clavadores dibujados en planta y proyectados sobre una cubierta gable."""
    roof_plan = plan_roof_from_sketch(roof_sketch, params=roof_params)
    params = dict(purlin_params or {})
    params["layout_mode"] = "project_plan_to_gable"
    return _core_error(
        plan_projected_purlins,
        sketch_line_segments(purlin_sketch),
        roof_plan,
        PurlinDefaults(**params),
    )

def plan_roof_from_sketch(sketch, params=None):
    return _core_error(
        plan_roof,
        sketch_outline_points(sketch),
        RoofDefaults(**dict(params or {})),
    )


def plan_from_sketches(truss_sketch, purlin_sketch, roof_sketch, params=None):
    """Genera plan JSON-compatible sin modificar el documento."""
    params = dict(params or {})
    try:
        return build_roof_system_plan(
            truss_segments=sketch_line_segments(truss_sketch),
            purlin_segments=sketch_line_segments(purlin_sketch),
            roof_outline=sketch_outline_points(roof_sketch),
            truss_defaults=TrussDefaults(**dict(params.get("truss", {}))),
            purlin_defaults=PurlinDefaults(**dict(params.get("purlin", {}))),
            roof_defaults=RoofDefaults(**dict(params.get("roof", {}))),
            source_names={
                "trusses": getattr(truss_sketch, "Name", ""),
                "purlins": getattr(purlin_sketch, "Name", ""),
                "roof": getattr(roof_sketch, "Name", ""),
            },
        )
    except RoofPlanError as exc:
        raise UserFacingError(str(exc))


def _tag(obj, source_sketch, role, geometry_index=None, element_id=None):
    set_prop(obj, "App::PropertyString", "FA_GeneratedBy", "FacilArquitectura", "Generador FA", GENERATOR)
    set_prop(obj, "App::PropertyString", "FA_RoofRole", "FacilArquitectura", "Rol del sistema de techo", role)
    set_prop(obj, "App::PropertyInteger", "FA_RoofSchemaVersion", "FacilArquitectura", "Version de esquema FA Techo", SCHEMA_VERSION)
    if source_sketch is not None:
        set_prop(obj, "App::PropertyLink", "FA_SourceSketch", "FacilArquitectura", "Sketch fuente", source_sketch)
    if geometry_index is not None:
        set_prop(
            obj,
            "App::PropertyInteger",
            "FA_SourceGeometryIndex",
            "FacilArquitectura",
            "Indice geometrico en Sketch fuente",
            int(geometry_index),
        )
    if element_id:
        set_prop(obj, "App::PropertyString", "FA_ElementId", "FacilArquitectura", "Identificador estable FA", str(element_id))


def _set_json_prop(obj, name, value, label):
    set_prop(
        obj,
        "App::PropertyString",
        name,
        "FacilArquitectura",
        label,
        json.dumps(value, ensure_ascii=True, sort_keys=True),
    )


def _add_to_container(container, obj):
    if container is None or obj is None:
        return
    try:
        if hasattr(container, "addObject"):
            container.addObject(obj)
            return
    except Exception:
        pass
    try:
        group = list(getattr(container, "Group", []) or [])
        if obj not in group:
            container.addObject(obj)
    except Exception:
        pass


def _set_if_present(obj, name, value):
    if hasattr(obj, name):
        try:
            setattr(obj, name, value)
            return True
        except Exception as exc:
            warn("No se pudo asignar %s=%r en %s: %s" % (name, value, getattr(obj, "Name", "?"), exc))
    return False


def _truss_axis_family_spec(truss_plan, extension_mm=500.0):
    items = list(truss_plan.get("items", []) or [])
    if not items:
        raise UserFacingError("No hay ejes de cercha para crear el datum BIM.")
    first = items[0]["baseline"]
    x1, y1, z1 = [float(v) for v in first["start"]]
    x2, y2, z2 = [float(v) for v in first["end"]]
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        raise UserFacingError("El primer eje de cercha es degenerado.")
    direction = (dx / length, dy / length)
    right = (direction[1], -direction[0])
    dominant = right[0] if abs(right[0]) >= abs(right[1]) else right[1]
    if dominant < 0.0:
        direction = (-direction[0], -direction[1])
        right = (-right[0], -right[1])

    records = []
    along = []
    z_values = []
    for item in items:
        baseline = item["baseline"]
        start = baseline["start"]
        end = baseline["end"]
        midpoint = ((float(start[0]) + float(end[0])) * 0.5, (float(start[1]) + float(end[1])) * 0.5)
        position = midpoint[0] * right[0] + midpoint[1] * right[1]
        records.append((position, int(item["source_index"])))
        for point in (start, end):
            along.append(float(point[0]) * direction[0] + float(point[1]) * direction[1])
            z_values.append(float(point[2]))
    records.sort(key=lambda pair: pair[0])
    positions = [pair[0] for pair in records]
    minimum = min(along) - float(extension_mm)
    maximum = max(along) + float(extension_mm)
    first_position = positions[0]
    z_level = sum(z_values) / len(z_values)
    origin = (
        right[0] * first_position + direction[0] * minimum,
        right[1] * first_position + direction[1] * minimum,
        z_level,
    )
    distances = [0.0] + [positions[i] - positions[i - 1] for i in range(1, len(positions))]
    rotation_deg = math.degrees(math.atan2(-direction[0], direction[1]))
    return {
        "count": len(items),
        "origin": origin,
        "length": maximum - minimum,
        "distances": distances,
        "rotation_deg": rotation_deg,
        "source_indices": [pair[1] for pair in records],
    }


def create_truss_axis_family(doc, container, source_sketch, truss_plan, extension_mm=500.0):
    """Crea un Arch Axis persistente para documentar la familia de cerchas."""
    if Arch is None or not hasattr(Arch, "makeAxis"):
        raise RuntimeError("Arch.makeAxis no esta disponible.")
    spec = _truss_axis_family_spec(truss_plan, extension_mm=extension_mm)
    axis = Arch.makeAxis(num=spec["count"], size=1.0, name="FA_TrussAxes")
    if axis is None:
        raise RuntimeError("Arch.makeAxis no pudo crear los ejes de cerchas.")
    axis.Label = "Ejes"
    axis.Distances = [float(v) for v in spec["distances"]]
    axis.Angles = [0.0] * int(spec["count"])
    axis.Length = float(spec["length"])
    axis.Placement = FreeCAD.Placement(
        FreeCAD.Vector(*spec["origin"]),
        FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), float(spec["rotation_deg"])),
    )
    _tag(axis, source_sketch, "truss_axis_family", element_id="TRUSS-AXES")
    _set_json_prop(axis, "FA_SourceGeometryIndices", spec["source_indices"], "Indices fuente de los ejes")
    try:
        axis.ViewObject.NumberingStyle = "01,02,03"
        axis.ViewObject.BubblePosition = "Both"
        axis.ViewObject.LineWidth = 2.0
        axis.ViewObject.DrawStyle = "Dashdot"
    except Exception:
        pass
    _add_to_container(container, axis)
    return axis


def _axis_runtime_points(axis):
    """Obtiene los puntos que ArchComponent.spread() usara realmente para el Axis."""
    points = []
    try:
        proxy = getattr(axis, "Proxy", None)
        if proxy is not None and hasattr(proxy, "getPoints"):
            points = list(proxy.getPoints(axis) or [])
    except Exception:
        points = []
    if not points:
        try:
            points = [edge.Vertexes[0].Point for edge in axis.Shape.Edges]
        except Exception:
            points = []
    return [FreeCAD.Vector(float(p.x), float(p.y), float(p.z)) for p in points]


def _master_truss_materialization_spec(doc, axis_family, truss_plan, tolerance_mm=1.0):
    """Resuelve una Base local que, repetida por Axis, reconstruya todas las lineas nativas."""
    spec = _truss_axis_family_spec(truss_plan)
    try:
        doc.recompute()
    except Exception:
        pass
    points = _axis_runtime_points(axis_family)
    if len(points) != int(spec["count"]):
        raise RuntimeError(
            "El Arch Axis devuelve %d puntos para %d posiciones de cercha."
            % (len(points), int(spec["count"]))
        )

    by_source = {int(item["source_index"]): item for item in truss_plan.get("items", [])}
    ordered = []
    for source_index in spec["source_indices"]:
        if int(source_index) not in by_source:
            raise RuntimeError("No se encontro la posicion logica de cercha %s." % source_index)
        ordered.append(by_source[int(source_index)])

    first_item = ordered[0]
    first_native = first_item.get("native_baseline", first_item["baseline"])
    p0 = points[0]
    local_start = FreeCAD.Vector(*[float(v) for v in first_native["start"]]).sub(p0)
    local_end = FreeCAD.Vector(*[float(v) for v in first_native["end"]]).sub(p0)

    for point, item in zip(points, ordered):
        native = item.get("native_baseline", item["baseline"])
        expected_start = FreeCAD.Vector(*[float(v) for v in native["start"]])
        expected_end = FreeCAD.Vector(*[float(v) for v in native["end"]])
        rebuilt_start = local_start.add(point)
        rebuilt_end = local_end.add(point)
        if rebuilt_start.sub(expected_start).Length > float(tolerance_mm) or rebuilt_end.sub(expected_end).Length > float(tolerance_mm):
            raise RuntimeError(
                "La geometria del Arch Axis no reproduce por traslacion la posicion de cercha source_index=%d."
                % int(item["source_index"])
            )

    return {
        "local_start": local_start,
        "local_end": local_end,
        "ordered_items": ordered,
        "axis_points": points,
        "source_indices": [int(item["source_index"]) for item in ordered],
    }


def _make_master_baseline(doc, source_sketch, truss_plan, axis_family):
    """Crea la unica Draft Line requerida como Base de la cercha maestra.

    La linea se expresa en coordenadas locales respecto del primer punto del
    Arch Axis. ArchComponent.spread() traslada despues la Shape del Truss a
    cada punto del Axis. La propia relacion Base de Arch/BIM gestiona su
    ocultamiento; FA no la agrega por separado al contenedor visual.
    """
    if Draft is None:
        raise RuntimeError("Draft no esta disponible.")
    spec = _master_truss_materialization_spec(doc, axis_family, truss_plan)
    master_item = spec["ordered_items"][0]
    maker = getattr(Draft, "make_line", None) or getattr(Draft, "makeLine", None)
    if maker is None:
        raise RuntimeError("Draft.make_line no esta disponible.")
    obj = maker(spec["local_start"], spec["local_end"])
    if obj is None:
        raise RuntimeError("Draft.make_line no pudo crear la Base de la cercha.")
    obj.Label = "Base cercha"
    _tag(obj, source_sketch, "truss_baseline", master_item["source_index"], "TRUSS-MASTER-BASE")
    _set_json_prop(obj, "FA_SourceGeometryIndices", spec["source_indices"], "Indices fuente de la familia de cerchas")
    try:
        doc.recompute()
    except Exception:
        pass
    return obj, spec


def create_trusses_from_plan(doc, container, source_sketch, truss_plan, axis_family=None):
    """Materializa una sola cercha BIM maestra repetida nativamente por Arch Axis."""
    if Arch is None or Part is None or not hasattr(Arch, "makeTruss"):
        raise RuntimeError("Arch.makeTruss/Part no estan disponibles.")
    if str(truss_plan.get("representation", "")) not in ("", "ONE_TRUSS_AXIS_SPREAD"):
        raise UserFacingError("Representacion de cerchas no soportada por este adaptador.")
    if axis_family is None:
        axis_family = create_truss_axis_family(doc, container, source_sketch, truss_plan)

    baseline, material = _make_master_baseline(doc, source_sketch, truss_plan, axis_family)
    truss = Arch.makeTruss(baseline)
    if truss is None:
        raise RuntimeError("Arch.makeTruss no pudo crear la cercha maestra.")
    truss.Label = "Cerchas BIM"

    master_item = material["ordered_items"][0]
    p = master_item["parameters"]
    mapping = {
        "SlantType": p["slant_type"],
        "Normal": FreeCAD.Vector(*p["normal"]),
        "HeightStart": p["height_start_mm"],
        "HeightEnd": p["height_end_mm"],
        "StrutStartOffset": p["strut_start_offset_mm"],
        "StrutEndOffset": p["strut_end_offset_mm"],
        "StrutHeight": p["strut_height_mm"],
        "StrutWidth": p["strut_width_mm"],
        "RodType": p["rod_type"],
        "RodDirection": p["rod_direction"],
        "RodSize": p["rod_size_mm"],
        "RodSections": int(p["rod_sections"]),
        "RodEnd": bool(p["rod_end"]),
        "RodMode": p["rod_mode"],
        "Axis": axis_family,
    }
    for prop, value in mapping.items():
        _set_if_present(truss, prop, value)

    _tag(truss, source_sketch, "truss", master_item["source_index"], "TRUSS-FAMILY")
    set_prop(truss, "App::PropertyInteger", "FA_TrussCount", "FacilArquitectura", "Cantidad de cerchas repetidas por Axis", int(truss_plan["count"]))
    set_prop(truss, "App::PropertyString", "FA_TrussRepresentation", "FacilArquitectura", "Representacion nativa de familia", "ONE_TRUSS_AXIS_SPREAD")
    set_prop(truss, "App::PropertyFloat", "FA_Pitch_deg", "FacilArquitectura", "Pendiente geometrica objetivo", float(p["pitch_deg"]))
    set_prop(truss, "App::PropertyString", "FA_HeightEndMode", "FacilArquitectura", "Origen de altura de cumbrera", p["height_end_mode"])
    _set_json_prop(truss, "FA_SourceGeometryIndices", material["source_indices"], "Indices de posiciones logicas de cercha")
    _add_to_container(container, truss)
    try:
        doc.recompute()
    except Exception:
        pass
    return [truss]


def _closed_face(points):
    wire = Part.makePolygon(points + [points[0]])
    return Part.Face(wire)


def _profile_face(profile_data, bottom_origin=False):
    """Crea una seccion 2D cuyo origen es el centro de la cara inferior.

    Arch Frame usa BasePoint=0 como el origen de la seccion. Con esta convencion
    el path 3D coincide con la linea de contacto cercha-clavador y el perfil crece
    en la direccion normal positiva del faldon.
    """
    if Part is None:
        raise RuntimeError("Part no esta disponible.")
    profile_type = str(profile_data["profile_type"]).upper()
    width = float(profile_data["profile_width_mm"])
    height = float(profile_data["profile_height_mm"])
    thickness = float(profile_data["profile_thickness_mm"])
    y0 = 0.0 if bottom_origin else -height / 2.0
    y1 = height if bottom_origin else height / 2.0
    if profile_type == "RECT":
        points = [
            FreeCAD.Vector(-width / 2.0, y0, 0),
            FreeCAD.Vector(width / 2.0, y0, 0),
            FreeCAD.Vector(width / 2.0, y1, 0),
            FreeCAD.Vector(-width / 2.0, y1, 0),
        ]
        return _closed_face(points)
    if profile_type == "C":
        points = [
            FreeCAD.Vector(-width / 2.0, y0, 0),
            FreeCAD.Vector(width / 2.0, y0, 0),
            FreeCAD.Vector(width / 2.0, y0 + thickness, 0),
            FreeCAD.Vector(-width / 2.0 + thickness, y0 + thickness, 0),
            FreeCAD.Vector(-width / 2.0 + thickness, y1 - thickness, 0),
            FreeCAD.Vector(width / 2.0, y1 - thickness, 0),
            FreeCAD.Vector(width / 2.0, y1, 0),
            FreeCAD.Vector(-width / 2.0, y1, 0),
        ]
        return _closed_face(points)
    raise UserFacingError("Tipo de perfil de clavador no soportado: %s" % profile_type)



def _make_projected_purlin_layout(doc, source_sketch, purlin_plan, items, suffix):
    """Materializa paths 3D de un solo faldon para un Arch Frame independiente."""
    if Part is None:
        raise RuntimeError("Part no esta disponible.")
    wires = []
    for item in items:
        path = item.get("support_path", item.get("path", {}))
        start = path.get("start")
        end = path.get("end")
        if not start or not end:
            continue
        p0 = FreeCAD.Vector(float(start[0]), float(start[1]), float(start[2]))
        p1 = FreeCAD.Vector(float(end[0]), float(end[1]), float(end[2]))
        wires.append(Part.Wire([Part.makeLine(p0, p1)]))
    if not wires:
        raise UserFacingError("No hay paths 3D de clavadores para el faldon %s." % suffix)
    safe = str(suffix).replace("-", "_")
    layout = doc.addObject("Part::Feature", "FA_PurlinLayout_%s" % safe)
    layout.Label = "Base clavadores - %s" % _roof_side_label(suffix)
    layout.Shape = wires[0] if len(wires) == 1 else Part.makeCompound(wires)
    _tag(layout, source_sketch, "purlin_layout", element_id="PURLIN-LAYOUT-%s" % safe)
    _set_json_prop(layout, "FA_SourceGeometryIndices", [item.get("source_index") for item in items], "Indices de lineas 2D proyectadas")
    _set_json_prop(layout, "FA_RoofDependency", purlin_plan.get("roof_dependency", {}), "Dependencia geometrica de cubierta")
    set_prop(layout, "App::PropertyString", "FA_RoofSide", "FacilArquitectura", "Faldon de cubierta", str(suffix))
    try:
        layout.ViewObject.Visibility = False
    except Exception:
        pass
    return layout


def _frame_profile_rotation(item):
    """Rotacion que alinea local Y con la normal del faldon y local Z con el path."""
    path = item.get("support_path", item.get("path", {}))
    start = path.get("start")
    end = path.get("end")
    if not start or not end:
        raise UserFacingError("Path de clavador incompleto.")
    bvec = FreeCAD.Vector(float(end[0]) - float(start[0]), float(end[1]) - float(start[1]), float(end[2]) - float(start[2]))
    normal_data = item.get("plane_normal", [0.0, 0.0, 1.0])
    normal = FreeCAD.Vector(float(normal_data[0]), float(normal_data[1]), float(normal_data[2]))
    return FreeCAD.Rotation(FreeCAD.Vector(), normal, bvec, "ZYX")


def _configure_frame(frame, profile_data, item, layout_mode, source_sketch, roof_source_sketch, frame_base, item_count):
    if item.get("plane_normal"):
        # Align=False evita que un unico borde deje indeterminada la normal de la Base.
        _set_if_present(frame, "Align", False)
        if hasattr(frame, "ProfilePlacement"):
            frame.ProfilePlacement = FreeCAD.Placement(FreeCAD.Vector(), _frame_profile_rotation(item))
        _set_if_present(frame, "BasePoint", 0)
    else:
        _set_if_present(frame, "Align", bool(profile_data["align"]))
    _set_if_present(frame, "Rotation", float(profile_data["rotation_deg"]))
    _set_if_present(frame, "Fuse", bool(profile_data["fuse"]))
    _set_if_present(frame, "IfcType", str(profile_data["ifc_type"]))
    set_prop(frame, "App::PropertyString", "FA_PurlinLayoutMode", "FacilArquitectura", "Modo geometrico de clavadores", layout_mode)
    if roof_source_sketch is not None:
        set_prop(frame, "App::PropertyLink", "FA_RoofSourceSketch", "FacilArquitectura", "Sketch fuente de cubierta", roof_source_sketch)
    set_prop(frame, "App::PropertyInteger", "FA_PurlinCount", "FacilArquitectura", "Cantidad de clavadores", int(item_count))
    set_prop(frame, "App::PropertyString", "FA_ProfileType", "FacilArquitectura", "Tipo logico de perfil", profile_data["profile_type"])
    set_prop(frame, "App::PropertyFloat", "FA_ProfileWidth_mm", "FacilArquitectura", "Ancho nominal geometrico", float(profile_data["profile_width_mm"]))
    set_prop(frame, "App::PropertyFloat", "FA_ProfileHeight_mm", "FacilArquitectura", "Altura nominal geometrica", float(profile_data["profile_height_mm"]))
    set_prop(frame, "App::PropertyFloat", "FA_ProfileThickness_mm", "FacilArquitectura", "Espesor nominal geometrico", float(profile_data["profile_thickness_mm"]))


def _roof_side_label(side):
    value = str(side or "").upper()
    if value == "LEFT":
        return "faldon izquierdo"
    if value == "RIGHT":
        return "faldon derecho"
    return str(side or "sin definir").lower()


def _make_purlin_profile(doc, source_sketch, profile_data, projected_mode, side=None):
    safe = str(side or "GENERAL").replace("-", "_").upper()
    profile = doc.addObject("Part::Feature", "FA_PurlinProfile_%s" % safe)
    if side:
        profile.Label = "Perfil %s clavadores - %s" % (profile_data["profile_type"], _roof_side_label(side))
    else:
        profile.Label = "Perfil %s clavadores" % profile_data["profile_type"]
    profile.Shape = _profile_face(profile_data, bottom_origin=projected_mode)
    _tag(profile, source_sketch, "purlin_profile", element_id="PURLIN-PROFILE-%s" % safe)
    set_prop(profile, "App::PropertyString", "FA_ProfileType", "FacilArquitectura", "Tipo logico de perfil", profile_data["profile_type"])
    set_prop(profile, "App::PropertyFloat", "FA_ProfileWidth_mm", "FacilArquitectura", "Ancho nominal geometrico", float(profile_data["profile_width_mm"]))
    set_prop(profile, "App::PropertyFloat", "FA_ProfileHeight_mm", "FacilArquitectura", "Altura nominal geometrica", float(profile_data["profile_height_mm"]))
    set_prop(profile, "App::PropertyFloat", "FA_ProfileThickness_mm", "FacilArquitectura", "Espesor nominal geometrico", float(profile_data["profile_thickness_mm"]))
    try:
        profile.ViewObject.Visibility = False
    except Exception:
        pass
    return profile


def create_purlins_from_plan(doc, container, source_sketch, purlin_plan, roof_source_sketch=None):
    """Crea clavadores BIM con una rama visual limpia por faldon.

    En modo proyectado cada Arch Frame posee su propia Base y su propio perfil.
    Los auxiliares no se agregan tambien al grupo Techo BIM: aparecen solamente
    mediante las relaciones nativas Base/Profile del Frame.
    """
    if Arch is None or Part is None or not hasattr(Arch, "makeFrame"):
        raise RuntimeError("Arch.makeFrame/Part no estan disponibles.")
    profile_data = purlin_plan["profile"]
    layout_mode = str(purlin_plan.get("layout_mode", profile_data.get("layout_mode", "source_3d")))
    projected_mode = purlin_plan.get("representation") == "PROJECTED_GABLE_LAYOUT" or layout_mode == "project_plan_to_gable"

    frames = []
    if projected_mode:
        groups = {}
        for item in purlin_plan.get("items", []):
            groups.setdefault(str(item.get("roof_side", "UNKNOWN")), []).append(item)
        for side in sorted(groups):
            items = groups[side]
            frame_base = _make_projected_purlin_layout(doc, source_sketch, purlin_plan, items, side)
            profile = _make_purlin_profile(doc, source_sketch, profile_data, True, side=side)
            doc.recompute()
            frame = Arch.makeFrame(frame_base, profile, name="FA_Purlins_%s" % side.replace("-", "_"))
            if frame is None:
                raise RuntimeError("Arch.makeFrame no pudo crear clavadores del faldon %s." % side)
            frame.Label = "Clavadores BIM - %s" % _roof_side_label(side)
            _configure_frame(frame, profile_data, items[0], layout_mode, source_sketch, roof_source_sketch, frame_base, len(items))
            _tag(frame, source_sketch, "purlins", element_id="PURLINS-%s" % side.replace("-", "_"))
            set_prop(frame, "App::PropertyString", "FA_RoofSide", "FacilArquitectura", "Faldon de cubierta", side)
            _set_json_prop(frame, "FA_SourceGeometryIndices", [item["source_index"] for item in items], "Indices de lineas de clavadores")
            _set_json_prop(frame, "FA_ProfileData", profile_data, "Datos geometricos del perfil")
            _add_to_container(container, frame)
            frames.append(frame)
    else:
        profile = _make_purlin_profile(doc, source_sketch, profile_data, False)
        doc.recompute()
        frame = Arch.makeFrame(source_sketch, profile, name="FA_Purlins")
        if frame is None:
            raise RuntimeError("Arch.makeFrame no pudo crear los clavadores.")
        frame.Label = "Clavadores BIM"
        _tag(frame, source_sketch, "purlins", element_id="PURLINS")
        _configure_frame(frame, profile_data, purlin_plan["items"][0], layout_mode, source_sketch, roof_source_sketch, source_sketch, purlin_plan["count"])
        _set_json_prop(frame, "FA_SourceGeometryIndices", [item["source_index"] for item in purlin_plan["items"]], "Indices de lineas de clavadores")
        _set_json_prop(frame, "FA_ProfileData", profile_data, "Datos geometricos del perfil")
        _add_to_container(container, frame)
        frames.append(frame)

    return frames


def _make_roof_base_layout(doc, source_sketch, roof_plan):
    stacking = roof_plan.get("stacking", {})
    points = stacking.get("roof_base_outline")
    offset = float(stacking.get("roof_base_vertical_offset_mm", 0.0) or 0.0)
    if not points or abs(offset) <= 1e-9:
        return source_sketch
    vectors = [FreeCAD.Vector(float(p[0]), float(p[1]), float(p[2])) for p in points]
    wire = Part.makePolygon(vectors + [vectors[0]])
    base = doc.addObject("Part::Feature", "FA_RoofBaseLayout")
    base.Label = "Base cubierta"
    base.Shape = wire
    _tag(base, source_sketch, "roof_base", element_id="ROOF-BASE")
    set_prop(base, "App::PropertyLink", "FA_RoofSourceSketch", "FacilArquitectura", "Sketch fuente de cubierta", source_sketch)
    set_prop(base, "App::PropertyFloat", "FA_VerticalOffset_mm", "FacilArquitectura", "Elevacion por altura de clavadores", offset)
    try:
        base.ViewObject.Visibility = False
    except Exception:
        pass
    return base


def create_roof_from_plan(doc, container, source_sketch, roof_plan):
    """Crea Roof nativo sobre la cara superior de los clavadores cuando hay apilado."""
    if Arch is None or Part is None or not hasattr(Arch, "makeRoof"):
        raise RuntimeError("Arch.makeRoof/Part no estan disponibles.")
    native = roof_plan["native"]
    roof_base = _make_roof_base_layout(doc, source_sketch, roof_plan)
    doc.recompute()
    roof = Arch.makeRoof(
        roof_base,
        angles=[float(v) for v in native["angles"]],
        run=[float(v) for v in native["runs"]],
        thickness=[float(v) for v in native["thickness"]],
        overhang=[float(v) for v in native["overhang"]],
        name="FA_Roof",
    )
    if roof is None:
        raise RuntimeError("Arch.makeRoof no pudo crear la cubierta.")
    roof.Label = "Cubierta BIM"
    _tag(roof, source_sketch, "roof", element_id="ROOF-001")
    p = roof_plan["parameters"]
    set_prop(roof, "App::PropertyString", "FA_RoofType", "FacilArquitectura", "Tipologia logica FA", roof_plan["roof_type"])
    set_prop(roof, "App::PropertyFloat", "FA_DefaultSlope_deg", "FacilArquitectura", "Pendiente objetivo de FA", float(p["slope_deg"]))
    set_prop(roof, "App::PropertyFloat", "FA_DefaultOverhang_mm", "FacilArquitectura", "Alero objetivo de FA", float(p["overhang_mm"]))
    set_prop(roof, "App::PropertyFloat", "FA_StackVerticalOffset_mm", "FacilArquitectura", "Separacion vertical por clavadores", float(roof_plan.get("stacking", {}).get("roof_base_vertical_offset_mm", 0.0)))
    _set_json_prop(roof, "FA_GableEdgeIndices", native["gable_edge_indices"], "Bordes de hastial")
    _set_json_prop(roof, "FA_EaveEdgeIndices", native["eave_edge_indices"], "Bordes de alero")
    _set_json_prop(roof, "FA_RidgeData", native["ridge"], "Datos geometricos de cumbrera")
    _set_json_prop(roof, "FA_StackingData", roof_plan.get("stacking", {}), "Apilado cercha-clavador-cubierta")
    _add_to_container(container, roof)
    return roof


def previous_generated_objects(doc, source_sketches=None):
    """Devuelve solo objetos de este subsistema, opcionalmente filtrados por Sketch fuente."""
    allowed = None
    if source_sketches:
        allowed = {str(getattr(sketch, "Name", "") or "") for sketch in source_sketches if sketch is not None}
    result = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if str(getattr(obj, "FA_GeneratedBy", "") or "") != GENERATOR:
            continue
        if allowed is not None:
            source = getattr(obj, "FA_SourceSketch", None)
            if str(getattr(source, "Name", "") or "") not in allowed:
                continue
        result.append(obj)
    return result



def remove_previous_component(doc, source_sketch, component):
    """Elimina solo un componente FA Techo generado desde un Sketch fuente.

    Debe ejecutarse dentro de una transaccion FreeCAD. No toca objetos manuales.
    """
    roles = {
        "trusses": {"truss", "truss_baseline", "truss_axis_family"},
        "purlins": {"purlins", "purlin_profile", "purlin_layout"},
        "roof": {"roof", "roof_base"},
    }
    key = str(component or "").lower()
    if key not in roles:
        raise UserFacingError("Componente FA Techo invalido: %s" % component)
    objects = [
        obj
        for obj in previous_generated_objects(doc, source_sketches=[source_sketch])
        if str(getattr(obj, "FA_RoofRole", "") or "") in roles[key]
    ]
    priority = {
        "roof": 0,
        "truss": 0,
        "purlins": 0,
        "truss_baseline": 1,
        "purlin_profile": 1,
        "purlin_layout": 1,
        "roof_base": 1,
        "truss_axis_family": 2,
    }
    objects.sort(key=lambda obj: priority.get(str(getattr(obj, "FA_RoofRole", "") or ""), 1))
    removed = 0
    for obj in objects:
        name = str(getattr(obj, "Name", "") or "")
        if not name:
            continue
        try:
            if doc.getObject(name) is not None:
                doc.removeObject(name)
                removed += 1
        except Exception as exc:
            warn("No se pudo eliminar %s previo %s: %s" % (key, name, exc))
    return removed

def remove_previous_roof_system(doc, source_sketches=None):
    """Elimina resultados FA previos. Debe llamarse dentro de una transaccion FreeCAD."""
    priority = {
        "roof": 0,
        "truss": 0,
        "purlins": 0,
        "truss_baseline": 1,
        "purlin_profile": 1,
        "purlin_layout": 1,
        "roof_base": 1,
        "truss_axis_family": 2,
    }
    objects = previous_generated_objects(doc, source_sketches=source_sketches)
    objects.sort(key=lambda obj: priority.get(str(getattr(obj, "FA_RoofRole", "") or ""), 1))
    removed = 0
    for obj in objects:
        name = str(getattr(obj, "Name", "") or "")
        if not name:
            continue
        try:
            if doc.getObject(name) is not None:
                doc.removeObject(name)
                removed += 1
        except Exception as exc:
            warn("No se pudo eliminar resultado FA Techo previo %s: %s" % (name, exc))
    return removed


def create_roof_system_from_sketches(
    doc,
    container,
    truss_sketch,
    purlin_sketch,
    roof_sketch,
    params=None,
    dry_run=True,
    replace_existing=False,
):
    """Planifica o materializa el sistema completo de techo.

    dry_run=True no modifica el documento. La creacion real debe ejecutarse dentro
    de una transaccion FreeCAD. Si ya existen resultados, replace_existing=False
    evita duplicarlos; replace_existing=True elimina solo resultados de este
    subsistema y de los mismos Sketches, confiando en la transaccion para rollback.
    """
    plan = plan_from_sketches(truss_sketch, purlin_sketch, roof_sketch, params=params)
    sources = [truss_sketch, purlin_sketch, roof_sketch]
    previous = previous_generated_objects(doc, source_sketches=sources)
    if dry_run:
        return {
            "dry_run": True,
            "plan": plan,
            "existing_count": len(previous),
            "created": {"truss_axis_family": None, "trusses": [], "purlins": [], "roof": None},
        }
    if previous and not replace_existing:
        raise UserFacingError(
            "Ya existen %d objetos FA Techo para estos Sketches. Ejecute dentro de una transaccion con replace_existing=True."
            % len(previous)
        )
    if previous:
        remove_previous_roof_system(doc, source_sketches=sources)
        doc.recompute()

    axis_family = create_truss_axis_family(doc, container, truss_sketch, plan["trusses"])
    trusses = create_trusses_from_plan(doc, container, truss_sketch, plan["trusses"], axis_family=axis_family)
    purlins = create_purlins_from_plan(
        doc, container, purlin_sketch, plan["purlins"], roof_source_sketch=roof_sketch
    )
    roof = create_roof_from_plan(doc, container, roof_sketch, plan["roof"])
    doc.recompute()
    msg("FA RoofSystem: cerchas=%d (1 Truss + Axis) | clavadores=%d | cubierta=1" % (plan["trusses"]["count"], plan["purlins"]["count"]))
    return {
        "dry_run": False,
        "plan": plan,
        "existing_count": len(previous),
        "created": {
            "truss_axis_family": axis_family,
            "trusses": trusses,
            "purlins": purlins,
            "roof": roof,
        },
    }


__all__ = [
    "sketch_line_segments",
    "sketch_outline_points",
    "plan_trusses_from_sketch",
    "plan_purlins_from_sketch",
    "plan_projected_purlins_from_sketch",
    "plan_roof_from_sketch",
    "plan_from_sketches",
    "create_truss_axis_family",
    "create_trusses_from_plan",
    "create_purlins_from_plan",
    "create_roof_from_plan",
    "previous_generated_objects",
    "remove_previous_component",
    "remove_previous_roof_system",
    "create_roof_system_from_sketches",
]
