"""Core independiente para techo, cerchas y clavadores de FacilArquitecturaWB.

Nombre: roof_system_core.py
Proposito: normalizar y planificar, sin FreeCADGui ni Qt, un sistema de techo
basado en Sketches: ejes de cerchas, clavadores/correas y contorno de cubierta.
Funcion principal: recibe geometria simple JSON-compatible y produce un plan
validado que el adaptador FreeCAD puede materializar con objetos BIM nativos.
FreeCAD objetivo: 1.1.3 (el nucleo no importa FreeCAD).
Version: 0.4.1
Fecha y hora: 2026-08-30 16:05 America/Costa_Rica

Instrucciones de mantenimiento:
- Mantener este modulo independiente de FreeCAD, FreeCADGui y Qt.
- Mantener entradas y salidas compatibles con JSON cuando sea razonable.
- Separar geometria/documentacion de calculo estructural. Este modulo NO dimensiona
  perfiles ni certifica capacidad estructural.
- No convertir automaticamente ambiguedades geometricas en decisiones de diseno.
- La geometria BIM nativa se resuelve en roof_bim_utils.py; este archivo solo
  describe intencion, relaciones y parametros verificables sin FreeCAD.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable, Mapping, Sequence

SCHEMA = "facil_arquitectura.roof_system"
SCHEMA_VERSION = 4
MIN_SEGMENT_MM = 20.0
MIN_CLOSED_AREA_MM2 = 10000.0
MAX_TRUSS_AXIS_DZ_MM = 1.0
ANGLE_TOLERANCE_DEG = 4.0
TRUSS_AXIS_SPREAD_TOLERANCE_MM = 1.0
TRUSS_AXIS_SPREAD_ANGLE_TOLERANCE_DEG = 0.1
RECTANGLE_ANGLE_TOLERANCE_DEG = 2.0
RECTANGLE_LENGTH_TOLERANCE_RATIO = 0.01
SQUARE_AMBIGUITY_RATIO = 0.02
TRUSS_SLANT_TYPES = ("Simple", "Double")
TRUSS_ROD_TYPES = ("Round", "Square")
TRUSS_ROD_DIRECTIONS = ("Forward", "Backward")
TRUSS_ROD_MODES = ("/|/|/|", "/\\/\\/\\", "/|\\|/|\\")
SUPPORTED_PURLIN_PROFILES = ("C", "RECT")
SUPPORTED_PURLIN_LAYOUT_MODES = ("source_3d", "project_plan_to_gable")
PURLIN_RIDGE_PARALLEL_TOLERANCE_DEG = 4.0
PURLIN_ROOF_BAND_TOLERANCE_MM = 2.0
SYSTEM_LEVEL_TOLERANCE_MM = 2.0
SYSTEM_PITCH_TOLERANCE_DEG = 0.05
SYSTEM_SPAN_TOLERANCE_MM = 5.0
SUPPORTED_ROOF_TYPES = ("gable",)


class RoofPlanError(ValueError):
    """Error de entrada o geometria entendible por la interfaz de FA."""


@dataclass(frozen=True)
class Point3:
    x: float
    y: float
    z: float = 0.0

    def as_list(self):
        return [float(self.x), float(self.y), float(self.z)]


@dataclass(frozen=True)
class Segment3:
    start: Point3
    end: Point3
    source_index: int = -1

    @property
    def length(self) -> float:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        dz = self.end.z - self.start.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @property
    def length_xy(self) -> float:
        return math.hypot(self.end.x - self.start.x, self.end.y - self.start.y)

    @property
    def midpoint(self) -> Point3:
        return Point3(
            (self.start.x + self.end.x) * 0.5,
            (self.start.y + self.end.y) * 0.5,
            (self.start.z + self.end.z) * 0.5,
        )

    def as_dict(self):
        return {
            "source_index": int(self.source_index),
            "start": self.start.as_list(),
            "end": self.end.as_list(),
            "length_mm": self.length,
            "length_xy_mm": self.length_xy,
        }


@dataclass(frozen=True)
class TrussDefaults:
    """Parametros geometricos para Arch Truss, no calculo estructural."""

    slant_type: str = "Double"
    pitch_deg: float = 20.0
    height_start_mm: float = 150.0
    height_end_mm: float | None = None
    derive_height_end_from_pitch: bool = True
    strut_start_offset_mm: float = 0.0
    strut_end_offset_mm: float = 0.0
    strut_height_mm: float = 50.0
    strut_width_mm: float = 50.0
    rod_type: str = "Square"
    rod_direction: str = "Forward"
    rod_size_mm: float = 25.0
    rod_sections: int = 6
    rod_end: bool = True
    rod_mode: str = "/|\\|/|\\"
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0)


@dataclass(frozen=True)
class PurlinDefaults:
    """Perfil, orientacion y modo geometrico de clavadores/correas."""

    profile_type: str = "C"
    profile_width_mm: float = 50.0
    profile_height_mm: float = 100.0
    profile_thickness_mm: float = 2.0
    layout_mode: str = "source_3d"
    align: bool = True
    rotation_deg: float = 0.0
    fuse: bool = False
    ifc_type: str = "Beam"


@dataclass(frozen=True)
class RoofDefaults:
    """Parametros geometricos iniciales para una cubierta a dos aguas."""

    roof_type: str = "gable"
    slope_deg: float = 20.0
    thickness_mm: float = 50.0
    overhang_mm: float = 600.0
    gable_edge_indices: tuple[int, int] | None = None


def _point(value) -> Point3:
    if isinstance(value, Point3):
        return value
    if isinstance(value, Mapping):
        return Point3(float(value["x"]), float(value["y"]), float(value.get("z", 0.0)))
    if not isinstance(value, Sequence) or len(value) not in (2, 3):
        raise RoofPlanError("Cada punto debe tener [x, y] o [x, y, z].")
    return Point3(float(value[0]), float(value[1]), float(value[2]) if len(value) == 3 else 0.0)


def normalize_segments(values: Iterable) -> list[Segment3]:
    """Normaliza segmentos JSON y rechaza lineas degeneradas."""
    result: list[Segment3] = []
    for index, value in enumerate(values or []):
        if isinstance(value, Segment3):
            seg = value
        elif isinstance(value, Mapping):
            seg = Segment3(_point(value["start"]), _point(value["end"]), int(value.get("source_index", index)))
        elif isinstance(value, Sequence) and len(value) == 2:
            seg = Segment3(_point(value[0]), _point(value[1]), index)
        else:
            raise RoofPlanError("Segmento invalido en indice %d." % index)
        if seg.length < MIN_SEGMENT_MM:
            raise RoofPlanError("El segmento %d mide menos de %.1f mm." % (index, MIN_SEGMENT_MM))
        result.append(seg)
    if not result:
        raise RoofPlanError("No hay segmentos utilizables.")
    return result


def _unit_xy(segment: Segment3) -> tuple[float, float]:
    dx = segment.end.x - segment.start.x
    dy = segment.end.y - segment.start.y
    length = math.hypot(dx, dy)
    if length < MIN_SEGMENT_MM:
        raise RoofPlanError("La proyeccion XY de un eje es demasiado corta.")
    return dx / length, dy / length


def _angle_delta_undirected(a: Segment3, b: Segment3) -> float:
    ax, ay = _unit_xy(a)
    bx, by = _unit_xy(b)
    dot = max(-1.0, min(1.0, abs(ax * bx + ay * by)))
    return math.degrees(math.acos(dot))


def validate_parallel_family(segments: Iterable, angle_tolerance_deg: float = ANGLE_TOLERANCE_DEG) -> list[Segment3]:
    """Valida que los ejes de cerchas constituyan una sola familia paralela y horizontal."""
    normalized = normalize_segments(segments)
    reference = normalized[0]
    for seg in normalized:
        if abs(seg.end.z - seg.start.z) > MAX_TRUSS_AXIS_DZ_MM:
            raise RoofPlanError(
                "El eje de cercha %d cambia %.2f mm en Z; debe ser una base horizontal."
                % (seg.source_index, abs(seg.end.z - seg.start.z))
            )
    for seg in normalized[1:]:
        delta = _angle_delta_undirected(reference, seg)
        if delta > float(angle_tolerance_deg):
            raise RoofPlanError(
                "Los ejes de cercha no forman una sola familia paralela; diferencia %.2f grados." % delta
            )
    return normalized


def _canonical_to_reference(segment: Segment3, reference: Segment3) -> Segment3:
    """Orienta un segmento en el mismo sentido XY que el segmento de referencia."""
    rx = reference.end.x - reference.start.x
    ry = reference.end.y - reference.start.y
    sx = segment.end.x - segment.start.x
    sy = segment.end.y - segment.start.y
    if rx * sx + ry * sy >= 0.0:
        return segment
    return Segment3(segment.end, segment.start, segment.source_index)


def validate_truss_axis_spread_family(
    segments: Iterable,
    tolerance_mm: float = TRUSS_AXIS_SPREAD_TOLERANCE_MM,
    angle_tolerance_deg: float = TRUSS_AXIS_SPREAD_ANGLE_TOLERANCE_DEG,
) -> list[Segment3]:
    """Valida que una sola cercha pueda repetirse por traslacion mediante Arch Axis.

    ArchComponent.spread() solo traslada la Shape maestra a los puntos del Axis; no
    cambia luz, nivel ni orientacion por instancia. Por ello todos los ejes deben ser
    copias por traslacion perpendicular de una misma linea base.
    """
    normalized = validate_parallel_family(segments)
    reference = normalized[0]
    result = [_canonical_to_reference(reference, reference)]
    ref = result[0]
    rdx = ref.end.x - ref.start.x
    rdy = ref.end.y - ref.start.y
    rlen = math.hypot(rdx, rdy)
    ux, uy = rdx / rlen, rdy / rlen

    for seg in normalized[1:]:
        current = _canonical_to_reference(seg, ref)
        delta = _angle_delta_undirected(ref, current)
        if delta > float(angle_tolerance_deg):
            raise RoofPlanError(
                "Los ejes de cercha no son compatibles con una sola cercha repetida por Axis; "
                "diferencia angular %.3f grados." % delta
            )
        if abs(current.length_xy - ref.length_xy) > float(tolerance_mm):
            raise RoofPlanError(
                "Los ejes de cercha no tienen la misma luz; una sola cercha maestra no puede repetirlos."
            )
        if abs(current.start.z - ref.start.z) > float(tolerance_mm) or abs(current.end.z - ref.end.z) > float(tolerance_mm):
            raise RoofPlanError(
                "Los ejes de cercha no estan al mismo nivel Z; un solo Arch Axis no puede repetir esa familia."
            )
        off_start = (current.start.x - ref.start.x, current.start.y - ref.start.y)
        off_end = (current.end.x - ref.end.x, current.end.y - ref.end.y)
        if math.hypot(off_start[0] - off_end[0], off_start[1] - off_end[1]) > float(tolerance_mm):
            raise RoofPlanError(
                "Los ejes de cercha no son traslaciones congruentes de una misma linea base."
            )
        longitudinal = off_start[0] * ux + off_start[1] * uy
        if abs(longitudinal) > float(tolerance_mm):
            raise RoofPlanError(
                "Los ejes de cercha estan escalonados longitudinalmente; Arch Axis solo debe gobernar su separacion transversal."
            )
        result.append(current)
    return result


def _normalized_truss_defaults(defaults: TrussDefaults | Mapping | None) -> TrussDefaults:
    cfg = defaults if isinstance(defaults, TrussDefaults) else TrussDefaults(**dict(defaults or {}))
    if cfg.slant_type not in TRUSS_SLANT_TYPES:
        raise RoofPlanError("slant_type debe ser Simple o Double.")
    if not 0.0 <= float(cfg.pitch_deg) < 89.0:
        raise RoofPlanError("La pendiente de cercha debe estar entre 0 y 89 grados.")
    if float(cfg.height_start_mm) <= 0:
        raise RoofPlanError("height_start_mm debe ser positivo.")
    if cfg.height_end_mm is not None and float(cfg.height_end_mm) <= 0:
        raise RoofPlanError("height_end_mm debe ser positivo cuando se especifica.")
    if int(cfg.rod_sections) < 1:
        raise RoofPlanError("rod_sections debe ser al menos 1.")
    if cfg.rod_type not in TRUSS_ROD_TYPES:
        raise RoofPlanError("rod_type invalido.")
    if cfg.rod_direction not in TRUSS_ROD_DIRECTIONS:
        raise RoofPlanError("rod_direction invalido.")
    if cfg.rod_mode not in TRUSS_ROD_MODES:
        raise RoofPlanError("rod_mode invalido.")
    if min(float(cfg.strut_height_mm), float(cfg.strut_width_mm), float(cfg.rod_size_mm)) <= 0:
        raise RoofPlanError("Las dimensiones de cordones y barras deben ser positivas.")
    normal = tuple(float(v) for v in cfg.normal)
    if len(normal) != 3 or math.sqrt(sum(v * v for v in normal)) <= 1e-9:
        raise RoofPlanError("normal debe ser un vector 3D no nulo.")
    return cfg


def _unit_vector3(values) -> tuple[float, float, float]:
    vals = tuple(float(v) for v in values)
    length = math.sqrt(sum(v * v for v in vals))
    if len(vals) != 3 or length <= 1e-9:
        raise RoofPlanError("Se requiere un vector normal 3D no nulo.")
    return tuple(v / length for v in vals)


def _shift_segment(segment: Segment3, vector: tuple[float, float, float], distance_mm: float) -> Segment3:
    dx, dy, dz = (float(v) * float(distance_mm) for v in vector)
    return Segment3(
        Point3(segment.start.x + dx, segment.start.y + dy, segment.start.z + dz),
        Point3(segment.end.x + dx, segment.end.y + dy, segment.end.z + dz),
        segment.source_index,
    )


def _resolved_truss_parameters(segment: Segment3, cfg: TrussDefaults) -> dict:
    params = asdict(cfg)
    run = segment.length_xy * (0.5 if cfg.slant_type == "Double" else 1.0)
    if cfg.height_end_mm is not None:
        height_end = float(cfg.height_end_mm)
        height_mode = "explicit"
    elif cfg.derive_height_end_from_pitch:
        height_end = float(cfg.height_start_mm) + run * math.tan(math.radians(float(cfg.pitch_deg)))
        height_mode = "pitch"
    else:
        raise RoofPlanError(
            "Debe indicar height_end_mm o activar derive_height_end_from_pitch para la cercha %d."
            % segment.source_index
        )
    params["height_start_mm"] = float(cfg.height_start_mm)
    params["height_end_mm"] = float(height_end)
    params["resolved_run_mm"] = float(run)
    params["height_end_mode"] = height_mode
    params["normal"] = [float(v) for v in cfg.normal]
    return params


def plan_trusses(segments: Iterable, defaults: TrussDefaults | Mapping | None = None) -> dict:
    """Planifica una cercha maestra repetida por un unico Arch Axis.

    Cada linea fuente sigue representando una posicion logica de cercha, pero la
    materializacion BIM prevista es ONE_TRUSS_AXIS_SPREAD: una sola Base nativa,
    un solo Arch Truss y un Arch Axis con tantas posiciones como cerchas.

    En Arch Truss, HeightStart/HeightEnd llegan hasta la cara superior del cordon
    superior. Por eso la linea dibujada por el usuario se interpreta como linea de
    apoyo superior (contacto cercha-clavador), y la Base nativa se desplaza hacia
    abajo exactamente HeightStart.
    """
    segments = validate_truss_axis_spread_family(segments)
    cfg = _normalized_truss_defaults(defaults)
    normal = _unit_vector3(cfg.normal)
    items = []
    for number, seg in enumerate(segments, start=1):
        params = _resolved_truss_parameters(seg, cfg)
        native_baseline = _shift_segment(seg, normal, -float(params["height_start_mm"]))
        items.append(
            {
                "id": "TRUSS-%03d" % number,
                "source_index": seg.source_index,
                "baseline": seg.as_dict(),
                "support_line": seg.as_dict(),
                "native_baseline": native_baseline.as_dict(),
                "parameters": params,
            }
        )
    return {
        "count": len(items),
        "family_parallel": True,
        "axis_spread_compatible": True,
        "representation": "ONE_TRUSS_AXIS_SPREAD",
        "materialized_truss_objects": 1,
        "slant_type": cfg.slant_type,
        "reference_role": "TRUSS_TOP_SUPPORT",
        "items": items,
    }


def _normalized_purlin_defaults(defaults: PurlinDefaults | Mapping | None) -> PurlinDefaults:
    cfg = defaults if isinstance(defaults, PurlinDefaults) else PurlinDefaults(**dict(defaults or {}))
    profile_type = str(cfg.profile_type or "").upper()
    if profile_type not in SUPPORTED_PURLIN_PROFILES:
        raise RoofPlanError("profile_type debe ser uno de: %s." % ", ".join(SUPPORTED_PURLIN_PROFILES))
    if str(cfg.layout_mode) not in SUPPORTED_PURLIN_LAYOUT_MODES:
        raise RoofPlanError("layout_mode debe ser source_3d o project_plan_to_gable.")
    if min(float(cfg.profile_width_mm), float(cfg.profile_height_mm), float(cfg.profile_thickness_mm)) <= 0:
        raise RoofPlanError("Las dimensiones del perfil de clavador deben ser positivas.")
    if profile_type == "C":
        if 2.0 * float(cfg.profile_thickness_mm) >= min(float(cfg.profile_width_mm), float(cfg.profile_height_mm)):
            raise RoofPlanError("El espesor del perfil C es demasiado grande para sus dimensiones.")
    return cfg


def plan_purlins(segments: Iterable, defaults: PurlinDefaults | Mapping | None = None) -> dict:
    """Produce un plan para clavadores/correas definidos explicitamente por Sketch."""
    segments = normalize_segments(segments)
    cfg = _normalized_purlin_defaults(defaults)
    profile = asdict(cfg)
    profile["profile_type"] = str(cfg.profile_type).upper()
    profile["layout_mode"] = str(cfg.layout_mode)
    items = []
    for number, seg in enumerate(segments, start=1):
        items.append(
            {
                "id": "PURLIN-%03d" % number,
                "source_index": seg.source_index,
                "path": seg.as_dict(),
            }
        )
    return {
        "count": len(items),
        "items": items,
        "profile": profile,
        "layout_mode": str(cfg.layout_mode),
        "representation": "ONE_FRAME_MULTIPLE_EDGES",
    }


def _signed_area_xy(points: Sequence[Point3]) -> float:
    total = 0.0
    for a, b in zip(points, points[1:] + points[:1]):
        total += a.x * b.y - b.x * a.y
    return 0.5 * total


def normalize_closed_outline(points: Iterable) -> list[Point3]:
    """Normaliza un contorno de cubierta, eliminando cierre duplicado si existe."""
    pts = [_point(p) for p in (points or [])]
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        raise RoofPlanError("La cubierta necesita un contorno cerrado de al menos tres vertices.")
    area = abs(_signed_area_xy(pts))
    if area < MIN_CLOSED_AREA_MM2:
        raise RoofPlanError("El contorno de cubierta tiene un area demasiado pequena o degenerada.")
    return pts


def _edge_segment(points: Sequence[Point3], index: int) -> Segment3:
    return Segment3(points[index], points[(index + 1) % len(points)], index)


def _edge_lengths_xy(points: Sequence[Point3]) -> list[float]:
    return [_edge_segment(points, i).length_xy for i in range(len(points))]


def _vector_xy(a: Point3, b: Point3) -> tuple[float, float]:
    return (b.x - a.x, b.y - a.y)


def _angle_between_xy(first: tuple[float, float], second: tuple[float, float]) -> float:
    l1 = math.hypot(*first)
    l2 = math.hypot(*second)
    if l1 <= 1e-9 or l2 <= 1e-9:
        raise RoofPlanError("El contorno contiene un borde degenerado.")
    dot = max(-1.0, min(1.0, (first[0] * second[0] + first[1] * second[1]) / (l1 * l2)))
    return math.degrees(math.acos(dot))


def _validate_rectangle(points: Sequence[Point3]) -> list[float]:
    if len(points) != 4:
        raise RoofPlanError("La cubierta a dos aguas automatica requiere por ahora un contorno rectangular de 4 bordes.")
    lengths = _edge_lengths_xy(points)
    for index in range(4):
        current = _vector_xy(points[index], points[(index + 1) % 4])
        nxt = _vector_xy(points[(index + 1) % 4], points[(index + 2) % 4])
        angle = _angle_between_xy(current, nxt)
        if abs(angle - 90.0) > RECTANGLE_ANGLE_TOLERANCE_DEG:
            raise RoofPlanError("El contorno de cubierta no es rectangular; angulo %.2f grados." % angle)
    for a, b in ((0, 2), (1, 3)):
        scale = max(lengths[a], lengths[b], 1.0)
        if abs(lengths[a] - lengths[b]) / scale > RECTANGLE_LENGTH_TOLERANCE_RATIO:
            raise RoofPlanError("Los bordes opuestos del contorno no tienen longitudes compatibles.")
    return lengths


def _normalize_gable_indices(value) -> tuple[int, int] | None:
    if value is None:
        return None
    if not isinstance(value, Sequence) or len(value) != 2:
        raise RoofPlanError("gable_edge_indices debe contener exactamente dos indices.")
    result = tuple(sorted(int(v) for v in value))
    if result not in ((0, 2), (1, 3)):
        raise RoofPlanError("Los bordes de hastial deben ser opuestos: (0,2) o (1,3).")
    return result


def _resolve_gable_edges(points: Sequence[Point3], cfg: RoofDefaults) -> tuple[tuple[int, int], list[float]]:
    lengths = _validate_rectangle(points)
    explicit = _normalize_gable_indices(cfg.gable_edge_indices)
    if explicit is not None:
        return explicit, lengths
    pair_02 = (lengths[0] + lengths[2]) * 0.5
    pair_13 = (lengths[1] + lengths[3]) * 0.5
    scale = max(pair_02, pair_13, 1.0)
    if abs(pair_02 - pair_13) / scale <= SQUARE_AMBIGUITY_RATIO:
        raise RoofPlanError(
            "La huella es casi cuadrada y la direccion de cumbrera es ambigua; indique gable_edge_indices."
        )
    # En una cubierta convencional la cumbrera se orienta segun el lado largo;
    # por tanto los hastiales corresponden al par de bordes mas cortos.
    return ((0, 2) if pair_02 < pair_13 else (1, 3)), lengths


def _point_to_infinite_line_distance_xy(point: Point3, line_start: Point3, line_end: Point3) -> float:
    vx = line_end.x - line_start.x
    vy = line_end.y - line_start.y
    length = math.hypot(vx, vy)
    if length <= 1e-9:
        raise RoofPlanError("Borde degenerado al calcular recorrido de cubierta.")
    return abs(vy * point.x - vx * point.y + line_end.x * line_start.y - line_end.y * line_start.x) / length


def _gable_native_data(points: Sequence[Point3], cfg: RoofDefaults) -> dict:
    gable_edges, lengths = _resolve_gable_edges(points, cfg)
    eave_edges = tuple(i for i in range(4) if i not in gable_edges)
    eave0 = _edge_segment(points, eave_edges[0])
    distance_between_eaves = _point_to_infinite_line_distance_xy(
        eave0.midpoint,
        points[eave_edges[1]],
        points[(eave_edges[1] + 1) % 4],
    )
    run = distance_between_eaves * 0.5
    if run <= MIN_SEGMENT_MM:
        raise RoofPlanError("El semivano de cubierta es demasiado pequeno.")
    angles = [90.0 if i in gable_edges else float(cfg.slope_deg) for i in range(4)]
    runs = [0.0 if i in gable_edges else float(run) for i in range(4)]
    thickness = [float(cfg.thickness_mm)] * 4
    overhang = [float(cfg.overhang_mm)] * 4

    # La cumbrera geometrica de un rectangulo une los puntos medios de los hastiales.
    g0 = _edge_segment(points, gable_edges[0]).midpoint
    g1 = _edge_segment(points, gable_edges[1]).midpoint
    base_z = sum(p.z for p in points) / len(points)
    rise = run * math.tan(math.radians(float(cfg.slope_deg)))
    ridge_z = base_z + rise
    ridge = {
        "start": [g0.x, g0.y, ridge_z],
        "end": [g1.x, g1.y, ridge_z],
        "elevation_mm": ridge_z,
        "rise_mm": rise,
    }
    return {
        "angles": angles,
        "runs": runs,
        "thickness": thickness,
        "overhang": overhang,
        "gable_edge_indices": list(gable_edges),
        "eave_edge_indices": list(eave_edges),
        "edge_lengths_mm": lengths,
        "half_span_mm": run,
        "ridge": ridge,
    }



def _segment_angle_to_vector_undirected(segment: Segment3, vector_xy: tuple[float, float]) -> float:
    """Devuelve diferencia angular 0..90 entre un segmento y una direccion XY."""
    sx, sy = _unit_xy(segment)
    vx, vy = vector_xy
    length = math.hypot(vx, vy)
    if length <= 1e-9:
        raise RoofPlanError("La direccion de referencia para clavadores es nula.")
    vx, vy = vx / length, vy / length
    dot = max(-1.0, min(1.0, abs(sx * vx + sy * vy)))
    return math.degrees(math.acos(dot))


def _canonicalize_segment_to_vector(segment: Segment3, vector_xy: tuple[float, float]) -> Segment3:
    """Orienta un segmento en el mismo sentido XY que una direccion de referencia."""
    vx, vy = vector_xy
    sx = segment.end.x - segment.start.x
    sy = segment.end.y - segment.start.y
    if sx * vx + sy * vy >= 0.0:
        return segment
    return Segment3(segment.end, segment.start, segment.source_index)


def _plane_normal_for_roof_side(roof_plan: Mapping, side: str) -> list[float]:
    """Normal unitaria hacia arriba del faldon asociado a EAVE-n."""
    if str(side) == "RIDGE":
        return [0.0, 0.0, 1.0]
    try:
        edge_index = int(str(side).split("-", 1)[1])
    except Exception as exc:
        raise RoofPlanError("Identificador de faldon invalido: %s" % side) from exc
    outline = [_point(v) for v in roof_plan.get("outline", [])]
    ridge = roof_plan.get("native", {}).get("ridge", {})
    rs = _point(ridge.get("start", []))
    re = _point(ridge.get("end", []))
    rm = Point3((rs.x + re.x) * 0.5, (rs.y + re.y) * 0.5, (rs.z + re.z) * 0.5)
    a = outline[edge_index]
    b = outline[(edge_index + 1) % len(outline)]
    em = Point3((a.x + b.x) * 0.5, (a.y + b.y) * 0.5, (a.z + b.z) * 0.5)
    ux, uy, uz = b.x - a.x, b.y - a.y, b.z - a.z
    vx, vy, vz = rm.x - em.x, rm.y - em.y, rm.z - em.z
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length <= 1e-9:
        raise RoofPlanError("No se pudo obtener la normal del faldon %s." % side)
    nx, ny, nz = nx / length, ny / length, nz / length
    if nz < 0.0:
        nx, ny, nz = -nx, -ny, -nz
    return [nx, ny, nz]


def _distance_to_line_signed_xy(point: Point3, line_start: Point3, line_end: Point3) -> float:
    """Distancia firmada a una recta XY; el signo depende del sentido del borde."""
    vx = line_end.x - line_start.x
    vy = line_end.y - line_start.y
    length = math.hypot(vx, vy)
    if length <= 1e-9:
        raise RoofPlanError("Borde degenerado al proyectar clavadores.")
    return (vx * (point.y - line_start.y) - vy * (point.x - line_start.x)) / length


def _project_point_to_gable_height(point: Point3, roof_plan: Mapping) -> tuple[Point3, dict]:
    """Proyecta Z de un punto en planta sobre uno de los dos faldones de un techo a dos aguas."""
    if str(roof_plan.get("roof_type", "")) != "gable":
        raise RoofPlanError("La proyeccion automatica de clavadores solo admite roof_type=gable.")
    outline = [_point(v) for v in roof_plan.get("outline", [])]
    if len(outline) != 4:
        raise RoofPlanError("La proyeccion de clavadores requiere una cubierta rectangular de 4 bordes.")
    native = roof_plan.get("native", {})
    eave_indices = [int(v) for v in native.get("eave_edge_indices", [])]
    if len(eave_indices) != 2:
        raise RoofPlanError("La cubierta no define exactamente dos bordes de alero.")
    half_span = float(native.get("half_span_mm", 0.0))
    if half_span <= MIN_SEGMENT_MM:
        raise RoofPlanError("La cubierta no tiene un semivano util para proyectar clavadores.")
    slope = float(roof_plan.get("parameters", {}).get("slope_deg", 0.0))
    base_z = sum(p.z for p in outline) / len(outline)

    distances = []
    signed = []
    for edge_index in eave_indices:
        a = outline[edge_index]
        b = outline[(edge_index + 1) % 4]
        signed_value = _distance_to_line_signed_xy(point, a, b)
        signed.append(signed_value)
        distances.append(abs(signed_value))

    full_span = 2.0 * half_span
    # Dentro de la franja entre dos aleros paralelos, la suma de las distancias
    # perpendiculares a ambas rectas coincide con el vano completo.
    if abs(sum(distances) - full_span) > max(PURLIN_ROOF_BAND_TOLERANCE_MM, full_span * 1e-6):
        raise RoofPlanError(
            "El clavador en planta queda fuera de la franja entre aleros; distancias %.2f + %.2f mm, vano %.2f mm."
            % (distances[0], distances[1], full_span)
        )
    nearest = 0 if distances[0] <= distances[1] else 1
    distance_to_eave = min(distances[nearest], half_span)
    rise = distance_to_eave * math.tan(math.radians(slope))
    projected = Point3(point.x, point.y, base_z + rise)
    if abs(distances[0] - distances[1]) <= PURLIN_ROOF_BAND_TOLERANCE_MM:
        side = "RIDGE"
    else:
        side = "EAVE-%d" % eave_indices[nearest]
    return projected, {
        "side": side,
        "distance_to_eave_mm": distance_to_eave,
        "rise_mm": rise,
        "signed_eave_distances_mm": signed,
    }


def plan_projected_purlins(
    segments: Iterable,
    roof_plan: Mapping,
    defaults: PurlinDefaults | Mapping | None = None,
    parallel_tolerance_deg: float = PURLIN_RIDGE_PARALLEL_TOLERANCE_DEG,
) -> dict:
    """Proyecta lineas 2D de clavadores sobre los faldones de una cubierta a dos aguas.

    El Sketch fuente sigue siendo 2D y editable. El adaptador FreeCAD materializa
    posteriormente un layout 3D auxiliar para Arch Frame. Las lineas deben ser
    paralelas a la cumbrera; una linea coincidente con la cumbrera se admite.
    """
    cfg = _normalized_purlin_defaults(defaults)
    if str(cfg.layout_mode) != "project_plan_to_gable":
        cfg = PurlinDefaults(**{**asdict(cfg), "layout_mode": "project_plan_to_gable"})
    normalized = normalize_segments(segments)
    ridge = roof_plan.get("native", {}).get("ridge", {})
    ridge_start = _point(ridge.get("start", []))
    ridge_end = _point(ridge.get("end", []))
    ridge_vector = (ridge_end.x - ridge_start.x, ridge_end.y - ridge_start.y)
    if math.hypot(*ridge_vector) <= MIN_SEGMENT_MM:
        raise RoofPlanError("La cubierta no define una cumbrera util para proyectar clavadores.")

    profile = asdict(cfg)
    profile["profile_type"] = str(cfg.profile_type).upper()
    profile["layout_mode"] = "project_plan_to_gable"
    items = []
    for number, seg in enumerate(normalized, start=1):
        delta = _segment_angle_to_vector_undirected(seg, ridge_vector)
        if delta > float(parallel_tolerance_deg):
            raise RoofPlanError(
                "El clavador %d no es paralelo a la cumbrera; diferencia %.2f grados."
                % (seg.source_index, delta)
            )
        start, start_meta = _project_point_to_gable_height(seg.start, roof_plan)
        end, end_meta = _project_point_to_gable_height(seg.end, roof_plan)
        if abs(start.z - end.z) > PURLIN_ROOF_BAND_TOLERANCE_MM:
            raise RoofPlanError(
                "El clavador %d cruza niveles distintos del techo; divida la linea por faldon."
                % seg.source_index
            )
        sides = {start_meta["side"], end_meta["side"]}
        if len(sides) > 1 and "RIDGE" not in sides:
            raise RoofPlanError(
                "El clavador %d cruza la cumbrera; use una linea independiente por faldon."
                % seg.source_index
            )
        side = "RIDGE" if "RIDGE" in sides else start_meta["side"]
        projected = _canonicalize_segment_to_vector(Segment3(start, end, seg.source_index), ridge_vector)
        plane_normal = _plane_normal_for_roof_side(roof_plan, side)
        items.append(
            {
                "id": "PURLIN-%03d" % number,
                "source_index": seg.source_index,
                "source_path": seg.as_dict(),
                "path": projected.as_dict(),
                "support_path": projected.as_dict(),
                "roof_side": side,
                "plane_normal": plane_normal,
                "profile_base_point": "BOTTOM_CENTER",
                "elevation_mm": (projected.start.z + projected.end.z) * 0.5,
                "requires_ridge_detail": side == "RIDGE",
            }
        )
    return {
        "count": len(items),
        "items": items,
        "profile": profile,
        "layout_mode": "project_plan_to_gable",
        "representation": "PROJECTED_GABLE_LAYOUT",
        "frame_strategy": "ONE_FRAME_PER_ROOF_SIDE",
        "roof_sides": sorted({item["roof_side"] for item in items}),
        "roof_dependency": {
            "roof_type": roof_plan.get("roof_type"),
            "ridge": ridge,
            "gable_edge_indices": list(roof_plan.get("native", {}).get("gable_edge_indices", [])),
            "eave_edge_indices": list(roof_plan.get("native", {}).get("eave_edge_indices", [])),
        },
    }

def plan_roof(outline_points: Iterable, defaults: RoofDefaults | Mapping | None = None) -> dict:
    """Produce parametros por borde compatibles con Arch Roof para una cubierta inicial."""
    pts = normalize_closed_outline(outline_points)
    cfg = defaults if isinstance(defaults, RoofDefaults) else RoofDefaults(**dict(defaults or {}))
    roof_type = str(cfg.roof_type or "").lower()
    if roof_type not in SUPPORTED_ROOF_TYPES:
        raise RoofPlanError("roof_type soportado en esta fase: gable.")
    if not 0.1 <= float(cfg.slope_deg) < 89.0:
        raise RoofPlanError("La pendiente debe estar entre 0.1 y 89 grados.")
    if float(cfg.thickness_mm) <= 0 or float(cfg.overhang_mm) < 0:
        raise RoofPlanError("Espesor debe ser positivo y alero no negativo.")
    native = _gable_native_data(pts, cfg)
    return {
        "roof_type": roof_type,
        "outline": [p.as_list() for p in pts],
        "edge_count": len(pts),
        "parameters": {
            "slope_deg": float(cfg.slope_deg),
            "thickness_mm": float(cfg.thickness_mm),
            "overhang_mm": float(cfg.overhang_mm),
        },
        "native": native,
        "documentation": {
            "ridge": native["ridge"],
            "gable_edge_indices": native["gable_edge_indices"],
            "eave_edge_indices": native["eave_edge_indices"],
        },
    }


def _roof_surface_z(point: Point3, roof_plan: Mapping) -> float:
    projected, _ = _project_point_to_gable_height(point, roof_plan)
    return float(projected.z)


def _couple_trusses_to_roof(truss_plan: dict, roof_plan: Mapping) -> dict:
    """Valida que las caras superiores de cerchas coincidan con la superficie maestra."""
    slope = float(roof_plan.get("parameters", {}).get("slope_deg", 0.0))
    full_span = 2.0 * float(roof_plan.get("native", {}).get("half_span_mm", 0.0))
    for item in truss_plan.get("items", []):
        params = item.get("parameters", {})
        if abs(float(params.get("pitch_deg", 0.0)) - slope) > SYSTEM_PITCH_TOLERANCE_DEG:
            raise RoofPlanError(
                "La pendiente de cercha %.3f no coincide con la cubierta %.3f grados."
                % (float(params.get("pitch_deg", 0.0)), slope)
            )
        support = item.get("support_line", item.get("baseline", {}))
        seg = Segment3(_point(support["start"]), _point(support["end"]), int(item.get("source_index", -1)))
        if abs(seg.length_xy - full_span) > SYSTEM_SPAN_TOLERANCE_MM:
            raise RoofPlanError(
                "La cercha %s mide %.2f mm y el vano entre aleros es %.2f mm."
                % (item.get("id"), seg.length_xy, full_span)
            )
        for point in (seg.start, seg.end):
            expected_z = _roof_surface_z(point, roof_plan)
            if abs(point.z - expected_z) > SYSTEM_LEVEL_TOLERANCE_MM:
                raise RoofPlanError(
                    "La cara superior de %s no coincide con la superficie maestra: Z %.2f vs %.2f mm."
                    % (item.get("id"), point.z, expected_z)
                )
    truss_plan["roof_coupled"] = True
    truss_plan["support_surface_role"] = "TRUSS_TOP_SUPPORT"
    return truss_plan


def _apply_purlin_roof_stack(roof_plan: dict, purlin_plan: Mapping) -> dict:
    """Desplaza la base de Roof hasta la cara superior de los clavadores.

    Los paths proyectados de clavadores son lineas de contacto sobre la cara
    superior de las cerchas. El perfil crece normal al faldon desde ese path.
    FreeCAD Arch Roof usa el contorno base como cara inferior del faldon; para
    obtener una separacion normal h, el contorno debe elevarse h/cos(pendiente).
    """
    if purlin_plan.get("representation") != "PROJECTED_GABLE_LAYOUT":
        roof_plan["stacking"] = {
            "mode": "EXTERNAL_3D_PURLINS",
            "reference_role": "ROOF_SOURCE_OUTLINE",
            "roof_base_vertical_offset_mm": 0.0,
            "roof_base_outline": list(roof_plan.get("outline", [])),
        }
        return roof_plan
    profile = purlin_plan.get("profile", {})
    height = float(profile.get("profile_height_mm", 0.0))
    slope = float(roof_plan.get("parameters", {}).get("slope_deg", 0.0))
    cosv = math.cos(math.radians(slope))
    if height <= 0.0 or cosv <= 1e-9:
        raise RoofPlanError("No se puede calcular el apilado cubierta-clavador.")
    vertical_offset = height / cosv
    base_outline = []
    for value in roof_plan.get("outline", []):
        pt = _point(value)
        base_outline.append([pt.x, pt.y, pt.z + vertical_offset])
    ridge = dict(roof_plan.get("native", {}).get("ridge", {}))
    roof_plan["stacking"] = {
        "mode": "TRUSS_PURLIN_ROOF",
        "reference_role": "TRUSS_TOP_SUPPORT",
        "purlin_contact_role": "PURLIN_BOTTOM_CONTACT",
        "purlin_height_normal_mm": height,
        "roof_base_vertical_offset_mm": vertical_offset,
        "roof_base_outline": base_outline,
        "roof_base_ridge_elevation_mm": float(ridge.get("elevation_mm", 0.0)) + vertical_offset,
        "roof_base_role": "PURLIN_TOP_SUPPORT",
    }
    return roof_plan


def build_roof_system_plan(
    *,
    truss_segments: Iterable,
    purlin_segments: Iterable,
    roof_outline: Iterable,
    truss_defaults: TrussDefaults | Mapping | None = None,
    purlin_defaults: PurlinDefaults | Mapping | None = None,
    roof_defaults: RoofDefaults | Mapping | None = None,
    source_names: Mapping | None = None,
) -> dict:
    """Construye el contrato completo Sketch -> ejes -> cerchas -> clavadores -> cubierta."""
    roof_plan = plan_roof(roof_outline, roof_defaults)
    truss_plan = _couple_trusses_to_roof(plan_trusses(truss_segments, truss_defaults), roof_plan)
    purlin_cfg = _normalized_purlin_defaults(purlin_defaults)
    if purlin_cfg.layout_mode == "project_plan_to_gable":
        purlin_plan = plan_projected_purlins(purlin_segments, roof_plan, purlin_cfg)
    else:
        purlin_plan = plan_purlins(purlin_segments, purlin_cfg)
    roof_plan = _apply_purlin_roof_stack(roof_plan, purlin_plan)
    plan = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "units": "mm",
        "structural_design_status": "GEOMETRIC_ONLY",
        "validation_status": "PENDING_FREECAD_MCP",
        "sources": dict(source_names or {}),
        "system_reference": {
            "role": "TRUSS_TOP_SUPPORT",
            "stacking_mode": roof_plan.get("stacking", {}).get("mode"),
        },
        "trusses": truss_plan,
        "purlins": purlin_plan,
        "roof": roof_plan,
    }
    return plan


__all__ = [
    "RoofPlanError",
    "Point3",
    "Segment3",
    "TrussDefaults",
    "PurlinDefaults",
    "RoofDefaults",
    "normalize_segments",
    "validate_parallel_family",
    "plan_trusses",
    "plan_purlins",
    "plan_projected_purlins",
    "normalize_closed_outline",
    "plan_roof",
    "build_roof_system_plan",
]
