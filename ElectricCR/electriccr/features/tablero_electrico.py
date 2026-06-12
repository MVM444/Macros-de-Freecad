# -*- coding: utf-8 -*-
"""
electriccr.features.tablero_electrico

Insercion de tableros electricos como App::Link.
Cada instancia apunta a un master oculto por variante geometrica.
"""

import math
import re

import FreeCAD as App
import Part

GUI_UP = False
try:
    import FreeCADGui as Gui  # noqa: F401
    GUI_UP = True
except Exception:
    Gui = None
    GUI_UP = False

try:
    import Draft
except Exception:
    Draft = None


TABLERO_SIZE_GROUPS_M = [
    {"key": "2-4", "min": 2, "max": 4, "MLO": (0.30, 0.20, 0.10), "MB": (0.35, 0.25, 0.12)},
    {"key": "6-8", "min": 6, "max": 8, "MLO": (0.45, 0.30, 0.12), "MB": (0.50, 0.35, 0.12)},
    {"key": "12-18", "min": 12, "max": 18, "MLO": (0.65, 0.40, 0.12), "MB": (0.75, 0.45, 0.15)},
    {"key": "24-30", "min": 24, "max": 30, "MLO": (0.85, 0.50, 0.15), "MB": (0.95, 0.55, 0.15)},
    {"key": "42", "min": 42, "max": 42, "MLO": (1.00, 0.50, 0.15), "MB": (1.10, 0.60, 0.20)},
    {"key": "54", "min": 54, "max": 54, "MLO": (1.20, 0.60, 0.20), "MB": (1.30, 0.65, 0.20)},
    {"key": "72-84", "min": 72, "max": 84, "MLO": (1.50, 0.75, 0.25), "MB": (1.80, 0.90, 0.30)},
]

MONTAJE_CHOICES = ("Empotrado", "Sobrepuesto")
LINK_MODE_CHOICES = ("Ambos", "Solo2D", "Solo3D")
EQUIPO_CHOICES = ("Tablero", "Desconector", "Interruptor")
DIMENSION_PROFILE_CHOICES = ("Generico", "Eaton_CH_PlugOnNeutral")
EATON_CONFIG_CHOICES = ("Auto", "Convertible")
EATON_BOX_CHOICES = ("Auto", "X0", "X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8", "X9")
EATON_AMP_CHOICES = (100, 125, 150, 200, 225)
DEFAULT_MODE = "Ambos"
MASTER_KIND_TOKEN = "TableroMaster"
DEFAULT_ALTURA_SUPERIOR_MM = 1800.0
SYMBOL_FRONT_OFFSET_MM = 25.0
TEXT_FRONT_OFFSET_MM = 80.0
WORKSPACE_FRONT_MM = 1200.0
WORKSPACE_MIN_WIDTH_MM = 800.0
WORKSPACE_HEIGHT_MM = 2000.0
WORKSPACE_SIDE_RECOMMENDED_MM = 300.0
TABLERO_OBSERVER_ATTR = "_electriccr_tablero_observer"
TABLERO_GEOM_VERSION_CURRENT = 2

EATON_CH_BOX_SIZES_MM = {
    # X0 se toma de la tabla de box sizes general del mismo catalogo (pag. 29), ya que la tabla puntual de pag. 30 inicia en X1.
    "X0": (425.5, 363.2, 79.4),
    "X1": (480.1, 363.2, 96.5),
    "X2": (535.9, 363.2, 96.5),
    "X3": (586.7, 363.2, 96.5),
    "X4": (688.3, 363.2, 96.5),
    "X5": (741.7, 363.2, 96.5),
    "X6": (868.7, 363.2, 96.5),
    "X7": (942.3, 363.2, 96.5),
    "X8": (993.1, 363.2, 96.5),
    "X9": (1145.5, 363.2, 96.5),
}

EATON_CH_AUTO_BOX_RULES = {
    "MainBreaker": {
        100: {14: "X1", 18: "X2", 22: "X2", 30: "X5"},
        125: {22: "X2", 30: "X5"},
        150: {24: "X5", 32: "X6"},
        200: {24: "X5", 32: "X6", 42: "X7", 60: "X9"},
        225: {42: "X7", 60: "X9"},
    },
    "MainLug": {
        125: {12: "X0", 16: "X1", 20: "X2", 24: "X2"},
        150: {24: "X5", 32: "X5"},
        200: {16: "X5"},
        225: {24: "X5", 32: "X5", 42: "X6"},
    },
    "Convertible": {
        125: {22: "X2"},
        225: {32: "X6", 42: "X7", 60: "X9"},
    },
}


def log_i(msg):
    App.Console.PrintMessage("[TABLERO][INFO] {}\n".format(msg))


def log_w(msg):
    App.Console.PrintWarning("[TABLERO][WARN] {}\n".format(msg))


def log_e(msg):
    App.Console.PrintError("[TABLERO][ERROR] {}\n".format(msg))


def _safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _safe_name_token(value, fallback="Obj"):
    token = re.sub(r"[^0-9A-Za-z_]+", "_", _safe_text(value))
    token = re.sub(r"_+", "_", token).strip("_")
    if not token:
        token = fallback
    if token[0].isdigit():
        token = "{}_{}".format(fallback, token)
    return token


def _unique_name(doc, base):
    root = _safe_name_token(base, "Obj")
    candidate = root
    idx = 1
    while doc.getObject(candidate) is not None:
        candidate = "{}_{:02d}".format(root, idx)
        idx += 1
    return candidate


def _ensure_property(obj, ptype, pname, pgroup, pdesc):
    try:
        if pname not in obj.PropertiesList:
            obj.addProperty(ptype, pname, pgroup, pdesc)
    except Exception:
        pass


def _mm(value_m):
    return float(value_m) * 1000.0


def _copy_vector(vec, z=None):
    if vec is None:
        return App.Vector(0.0, 0.0, 0.0 if z is None else float(z))
    return App.Vector(
        float(getattr(vec, "x", 0.0) or 0.0),
        float(getattr(vec, "y", 0.0) or 0.0),
        float(getattr(vec, "z", 0.0) if z is None else z),
    )


def _vector_add(v1, v2):
    return App.Vector(float(v1.x) + float(v2.x), float(v1.y) + float(v2.y), float(v1.z) + float(v2.z))


def _vector_sub(v1, v2):
    return App.Vector(float(v1.x) - float(v2.x), float(v1.y) - float(v2.y), float(v1.z) - float(v2.z))


def _vector_mul(v, scalar):
    scale = float(scalar)
    return App.Vector(float(v.x) * scale, float(v.y) * scale, float(v.z) * scale)


def _vector_dot(v1, v2):
    return float(v1.x) * float(v2.x) + float(v1.y) * float(v2.y) + float(v1.z) * float(v2.z)


def _vector_length(v):
    return math.sqrt(_vector_dot(v, v))


def _vector_plan(v):
    return App.Vector(float(getattr(v, "x", 0.0) or 0.0), float(getattr(v, "y", 0.0) or 0.0), 0.0)


def _normalize_vector(v, fallback=None, tol=1.0e-6):
    vec = _copy_vector(v)
    length = _vector_length(vec)
    if length <= float(tol):
        if fallback is None:
            return App.Vector(0.0, 0.0, 0.0)
        return _copy_vector(fallback)
    return _vector_mul(vec, 1.0 / length)


def _bbox_center(bb):
    if bb is None:
        return App.Vector(0.0, 0.0, 0.0)
    try:
        return App.Vector(
            0.5 * (float(bb.XMin) + float(bb.XMax)),
            0.5 * (float(bb.YMin) + float(bb.YMax)),
            0.5 * (float(bb.ZMin) + float(bb.ZMax)),
        )
    except Exception:
        return App.Vector(0.0, 0.0, 0.0)


def _shape_center(shape):
    if shape is None:
        return App.Vector(0.0, 0.0, 0.0)
    try:
        center = getattr(shape, "CenterOfMass", None)
        if center is not None:
            return _copy_vector(center)
    except Exception:
        pass
    try:
        return _bbox_center(getattr(shape, "BoundBox", None))
    except Exception:
        return App.Vector(0.0, 0.0, 0.0)


def _shape_from_object(obj):
    if obj is None:
        return None
    try:
        shape = getattr(obj, "Shape", None)
        if shape is not None:
            return shape
    except Exception:
        return None
    return None


def _midpoint(v1, v2):
    return App.Vector(
        0.5 * (float(v1.x) + float(v2.x)),
        0.5 * (float(v1.y) + float(v2.y)),
        0.5 * (float(v1.z) + float(v2.z)),
    )


def _collect_unique_points(points, tol=1.0e-3):
    unique = []
    for point in (points or []):
        vec = _copy_vector(point)
        if any(_vector_distance(vec, other) <= float(tol) for other in unique):
            continue
        unique.append(vec)
    return unique


def _project_point_to_segment(point, start, end):
    p = _copy_vector(point)
    a = _copy_vector(start)
    b = _copy_vector(end)
    ab = _vector_sub(b, a)
    denom = _vector_dot(ab, ab)
    if denom <= 1.0e-9:
        return a
    t = _vector_dot(_vector_sub(p, a), ab) / denom
    t = max(0.0, min(1.0, t))
    return _vector_add(a, _vector_mul(ab, t))


def _rectangle_polygon_area(points):
    if len(points or []) < 3:
        return 0.0
    area = 0.0
    count = len(points)
    for idx in range(count):
        p1 = points[idx]
        p2 = points[(idx + 1) % count]
        area += float(p1.x) * float(p2.y) - float(p2.x) * float(p1.y)
    return 0.5 * area


def _extract_horizontal_rectangle_points(shape):
    if shape is None:
        return None
    vertexes = list(getattr(shape, "Vertexes", []) or [])
    if not vertexes:
        return None
    points = _collect_unique_points([getattr(vx, "Point", None) for vx in vertexes], tol=1.0e-3)
    if len(points) != 4:
        return None

    z_values = [float(pt.z) for pt in points]
    if (max(z_values) - min(z_values)) > 1.0e-3:
        return None

    centroid = App.Vector(
        sum(float(pt.x) for pt in points) / 4.0,
        sum(float(pt.y) for pt in points) / 4.0,
        sum(float(pt.z) for pt in points) / 4.0,
    )
    ordered = sorted(points, key=lambda pt: math.atan2(float(pt.y) - float(centroid.y), float(pt.x) - float(centroid.x)))
    if abs(_rectangle_polygon_area(ordered)) <= 1.0e-6:
        return None

    edges = []
    for idx in range(4):
        p1 = ordered[idx]
        p2 = ordered[(idx + 1) % 4]
        edge_vec = _vector_plan(_vector_sub(p2, p1))
        length = _vector_length(edge_vec)
        if length <= 1.0e-6:
            return None
        edges.append((p1, p2, _normalize_vector(edge_vec)))

    lengths = [_vector_length(_vector_plan(_vector_sub(edge[1], edge[0]))) for edge in edges]
    if abs(lengths[0] - lengths[2]) > 2.0 or abs(lengths[1] - lengths[3]) > 2.0:
        return None

    for idx in range(4):
        dir_a = edges[idx][2]
        dir_b = edges[(idx + 1) % 4][2]
        if abs(_vector_dot(dir_a, dir_b)) > 0.2:
            return None
    return ordered


def _rotation_from_front_vector(front_dir):
    front = _normalize_vector(_vector_plan(front_dir), fallback=App.Vector(1.0, 0.0, 0.0))
    angle_deg = math.degrees(math.atan2(float(front.y), float(front.x)))
    return App.Rotation(App.Vector(0.0, 0.0, 1.0), angle_deg)


def _make_insertion_context(kind="origin", point=None, anchor=None, front_dir=None, side_dir=None, base_z=0.0, source=None):
    point_vec = _copy_vector(point, z=(float(getattr(point, "z", 0.0) or 0.0) if point is not None else float(base_z or 0.0)))
    anchor_vec = _copy_vector(anchor if anchor is not None else point_vec, z=float(base_z or 0.0))
    front = _normalize_vector(_vector_plan(front_dir), fallback=App.Vector(1.0, 0.0, 0.0))
    side = _normalize_vector(_vector_plan(side_dir), fallback=App.Vector(-front.y, front.x, 0.0))
    return {
        "kind": _safe_text(kind) or "origin",
        "point": point_vec,
        "anchor": anchor_vec,
        "front_dir": front,
        "side_dir": side,
        "base_z": float(base_z or 0.0),
        "source": _safe_text(source),
    }


def clear_step_cache():
    return None


def buscar_step(*_args, **_kwargs):
    return None


def get_or_create_doc(default_name="Electrico"):
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument(_safe_name_token(default_name, "Electrico"))
    return doc


def _find_row_for_key(key):
    for row in TABLERO_SIZE_GROUPS_M:
        if row["key"] == key:
            return row
    raise ValueError("Rango no encontrado: {}".format(key))


def _normalize_range_key(espacios):
    n = int(espacios)
    if n < 2:
        log_w("Espacios={} no valido; se usa 2.".format(n))
        n = 2
    if n <= 4:
        key = "2-4"
    elif n <= 8:
        key = "6-8"
    elif n <= 18:
        key = "12-18"
    elif n <= 30:
        key = "24-30"
    elif n <= 42:
        key = "42"
    elif n <= 54:
        key = "54"
    elif n <= 84:
        key = "72-84"
    else:
        key = "72-84"
        log_w("Espacios={} supera 84; se usa rango 72-84.".format(n))

    row = _find_row_for_key(key)
    if not (row["min"] <= n <= row["max"]):
        log_w("Espacios={} normalizado al rango {}.".format(n, key))
    return key, n


def _normalize_link_mode(value):
    txt = _safe_text(value).strip().lower()
    if txt in ("solo2d", "2d", "plano"):
        return "Solo2D"
    if txt in ("solo3d", "3d", "volumen"):
        return "Solo3D"
    if txt in ("ambos", "both", "mixto"):
        return "Ambos"
    return "Ambos"


def _normalize_clase_equipo(value):
    txt = _safe_text(value).strip().lower()
    if txt in ("tablero", "panel"):
        return "Tablero"
    if txt in ("desconector", "disconnect", "switch_disconnect"):
        return "Desconector"
    if txt in ("interruptor", "breaker", "switch"):
        return "Interruptor"
    return "Tablero"


def _normalize_dimension_profile(value):
    txt = _safe_text(value).strip().lower()
    if txt in ("eaton", "eaton_ch", "eaton ch", "eaton_ch_plugonneutral", "eaton ch plug-on neutral", "eaton ch plug on neutral"):
        return "Eaton_CH_PlugOnNeutral"
    return "Generico"


def _normalize_eaton_config(value, main_breaker=False):
    txt = _safe_text(value).strip().lower()
    if txt in ("", "auto", "automatico", "automático"):
        if bool(main_breaker):
            return "MainBreaker"
        return "MainLug"
    if txt in ("mainbreaker", "main_breaker", "mb", "principal"):
        return "MainBreaker"
    if txt in ("mainlug", "main_lug", "mlo"):
        return "MainLug"
    if txt in ("convertible", "combo", "base"):
        return "Convertible"
    if bool(main_breaker):
        return "MainBreaker"
    return "MainLug"


def _normalize_eaton_box(value):
    txt = _safe_text(value).strip().upper().replace("-", "")
    if not txt or txt == "AUTO":
        return "Auto"
    if txt in EATON_CH_BOX_SIZES_MM:
        return txt
    return "Auto"


def _normalize_eaton_amp(value, default=225):
    try:
        amp_value = int(value)
    except Exception:
        amp_value = int(default)
    if amp_value in EATON_AMP_CHOICES:
        return amp_value
    nearest = min(EATON_AMP_CHOICES, key=lambda candidate: abs(int(candidate) - int(amp_value)))
    return int(nearest)


def _safe_spaces_value(espacios):
    try:
        n = int(espacios)
    except Exception:
        n = 2
    if n < 2:
        log_w("Espacios={} no valido; se usa 2.".format(espacios))
        n = 2
    return n


def _resolve_insert_defaults(clase_equipo, espacios, main_breaker):
    clase = _normalize_clase_equipo(clase_equipo)
    spaces_value = int(espacios)
    mb_value = bool(main_breaker)
    if clase in ("Desconector", "Interruptor"):
        spaces_value = 2
        mb_value = False
    return clase, spaces_value, mb_value


def _bool_value(value, default=False):
    try:
        return bool(value)
    except Exception:
        return bool(default)


def _int_value(value, default=0):
    try:
        return int(value)
    except Exception:
        return int(default)


def _resolve_eaton_box_auto(espacios, amp=None, main_breaker=False, eaton_config="Auto"):
    spaces_value = _safe_spaces_value(espacios)
    amp_value = _normalize_eaton_amp(amp, default=225)
    config_value = _normalize_eaton_config(eaton_config, main_breaker=main_breaker)
    box = (((EATON_CH_AUTO_BOX_RULES.get(config_value) or {}).get(amp_value) or {}).get(spaces_value))
    if box:
        return box, config_value, amp_value
    return None, config_value, amp_value


def calcular_dimensiones(espacios, amp=None, main_breaker=False, dimension_profile="Generico", eaton_config="Auto", eaton_box="Auto"):
    profile_value = _normalize_dimension_profile(dimension_profile)
    if profile_value == "Eaton_CH_PlugOnNeutral":
        spaces_value = _safe_spaces_value(espacios)
        amp_value = _normalize_eaton_amp(amp, default=225)
        config_value = _normalize_eaton_config(eaton_config, main_breaker=main_breaker)
        box_value = _normalize_eaton_box(eaton_box)
        if box_value == "Auto":
            box_value, config_value, amp_value = _resolve_eaton_box_auto(
                espacios=spaces_value,
                amp=amp_value,
                main_breaker=main_breaker,
                eaton_config=config_value,
            )
            if not box_value:
                raise ValueError(
                    "Eaton CH sin caja automatica para amp={}A, espacios={}, configuracion={}.".format(
                        amp_value,
                        spaces_value,
                        config_value,
                    )
                )
        dims_mm = EATON_CH_BOX_SIZES_MM.get(box_value)
        if not dims_mm:
            raise ValueError("Caja Eaton no soportada: {}".format(box_value))
        return {
            "rango": box_value,
            "espacios": int(spaces_value),
            "alto_mm": float(dims_mm[0]),
            "ancho_mm": float(dims_mm[1]),
            "fondo_mm": float(dims_mm[2]),
            "amp": int(amp_value),
            "perfil_dimensiones": profile_value,
            "configuracion_catalogo": config_value,
            "caja_modelo": box_value,
            "caja_eaton": _normalize_eaton_box(eaton_box),
        }

    key, spaces_value = _normalize_range_key(espacios)
    row = _find_row_for_key(key)
    dims_m = row["MB"] if bool(main_breaker) else row["MLO"]
    return {
        "rango": key,
        "espacios": int(spaces_value),
        "alto_mm": _mm(dims_m[0]),
        "ancho_mm": _mm(dims_m[1]),
        "fondo_mm": _mm(dims_m[2]),
        "amp": amp,
        "perfil_dimensiones": "Generico",
        "configuracion_catalogo": _normalize_eaton_config(eaton_config, main_breaker=main_breaker),
        "caja_modelo": key,
        "caja_eaton": _normalize_eaton_box(eaton_box),
    }


def _is_group(obj):
    if obj is None:
        return False
    try:
        if obj.isDerivedFrom("App::DocumentObjectGroup"):
            return True
    except Exception:
        pass
    return bool(hasattr(obj, "Group"))


def _group_matches(obj, aliases):
    if not _is_group(obj):
        return False
    alias_keys = set(_safe_name_token(x, "").lower() for x in aliases if _safe_text(x))
    name_key = _safe_name_token(getattr(obj, "Name", ""), "").lower()
    label_key = _safe_name_token(getattr(obj, "Label", ""), "").lower()
    return bool(name_key in alias_keys or label_key in alias_keys)


def _add_to_group(group_obj, child_obj):
    if group_obj is None or child_obj is None:
        return
    try:
        if child_obj not in (group_obj.Group or []):
            group_obj.addObject(child_obj)
    except Exception:
        pass


def _ensure_child_group(doc, parent, aliases, default_name, default_label, search_doc_fallback=True):
    if parent is not None and _is_group(parent):
        for obj in (getattr(parent, "Group", []) or []):
            if _group_matches(obj, aliases):
                return obj

    if search_doc_fallback:
        for obj in (doc.Objects or []):
            if _group_matches(obj, aliases):
                _add_to_group(parent, obj)
                return obj

    name = default_name if doc.getObject(default_name) is None else _unique_name(doc, default_name)
    grp = doc.addObject("App::DocumentObjectGroup", name)
    try:
        grp.Label = default_label
    except Exception:
        pass
    _add_to_group(parent, grp)
    return grp


def _ensure_main_electrico_group(doc):
    for obj in (doc.Objects or []):
        if _group_matches(obj, ("electrico", "electricidad", "electrico")):
            return obj
    grp = doc.getObject("electrico")
    if grp is None:
        grp = doc.addObject("App::DocumentObjectGroup", "electrico")
    try:
        grp.Label = "electrico"
    except Exception:
        pass
    return grp


def _ensure_tableros_group(doc, main_group):
    return _ensure_child_group(
        doc,
        main_group,
        ("Tableros", "Tableros Electricos", "Tableros Electricricos", "Paneles"),
        "Tableros",
        "Tableros",
        search_doc_fallback=False,
    )


def _ensure_lib_root_group(doc, main_group):
    return _ensure_child_group(
        doc,
        main_group,
        ("_lib", "_Libreria", "Libreria", "Library"),
        "_lib",
        "_lib",
    )


def _ensure_tablero_masters_group(doc, lib_group):
    return _ensure_child_group(
        doc,
        lib_group,
        ("_lib_tableros", "Tableros_Link_Masters", "Tableros Masters"),
        "_lib_tableros",
        "_lib_tableros",
        search_doc_fallback=False,
    )


def _hide_in_view(obj):
    if not GUI_UP or obj is None or not hasattr(obj, "ViewObject"):
        return
    try:
        obj.ViewObject.Visibility = False
    except Exception:
        pass
    try:
        if hasattr(obj.ViewObject, "Selectable"):
            obj.ViewObject.Selectable = False
    except Exception:
        pass
    try:
        if hasattr(obj.ViewObject, "Pickable"):
            obj.ViewObject.Pickable = False
    except Exception:
        pass


def _show_in_view(obj):
    if not GUI_UP or obj is None or not hasattr(obj, "ViewObject"):
        return
    try:
        obj.ViewObject.Visibility = True
    except Exception:
        pass
    try:
        if hasattr(obj.ViewObject, "Selectable"):
            obj.ViewObject.Selectable = True
    except Exception:
        pass
    try:
        if hasattr(obj.ViewObject, "Pickable"):
            obj.ViewObject.Pickable = True
    except Exception:
        pass


def _set_display_mode(vobj, candidates):
    if vobj is None:
        return
    for mode in (candidates or []):
        try:
            vobj.DisplayMode = mode
            return
        except Exception:
            continue


def _build_rectangle_edges(x0, y0, x1, y1, z0=0.0):
    p1 = App.Vector(float(x0), float(y0), float(z0))
    p2 = App.Vector(float(x1), float(y0), float(z0))
    p3 = App.Vector(float(x1), float(y1), float(z0))
    p4 = App.Vector(float(x0), float(y1), float(z0))
    return [
        Part.makeLine(p1, p2),
        Part.makeLine(p2, p3),
        Part.makeLine(p3, p4),
        Part.makeLine(p4, p1),
    ]


def _workspace_width_mm(ancho_mm):
    return max(float(ancho_mm), float(WORKSPACE_MIN_WIDTH_MM))


def _board_x_limits(montaje, fondo_mm, geom_version=TABLERO_GEOM_VERSION_CURRENT):
    depth = float(fondo_mm)
    if _int_value(geom_version, 1) >= 2 and _safe_text(montaje) == "Empotrado":
        return -depth, 0.0
    return 0.0, depth


def _front_plane_x(montaje, fondo_mm, geom_version=TABLERO_GEOM_VERSION_CURRENT):
    if _int_value(geom_version, 1) >= 2 and _safe_text(montaje) == "Empotrado":
        return 0.0
    return float(fondo_mm)


def _build_2d_shape(ancho_mm, fondo_mm, montaje="Sobrepuesto", geom_version=TABLERO_GEOM_VERSION_CURRENT):
    x0, x1 = _board_x_limits(montaje, fondo_mm, geom_version=geom_version)
    p1 = App.Vector(float(x0), 0.0, 0.0)
    p2 = App.Vector(float(x1), 0.0, 0.0)
    p3 = App.Vector(float(x1), float(ancho_mm), 0.0)
    p4 = App.Vector(float(x0), float(ancho_mm), 0.0)
    shapes = _build_rectangle_edges(float(x0), 0.0, float(x1), float(ancho_mm), 0.0)
    shapes.append(Part.makeLine(p1, p3))
    shapes.append(Part.makeLine(p2, p4))
    return Part.makeCompound(shapes)


def _build_workspace_2d_shape(ancho_mm, fondo_mm, montaje="Sobrepuesto", geom_version=TABLERO_GEOM_VERSION_CURRENT):
    work_width = _workspace_width_mm(ancho_mm)
    y0 = 0.5 * float(ancho_mm) - 0.5 * float(work_width)
    y1 = y0 + float(work_width)
    x0 = _front_plane_x(montaje, fondo_mm, geom_version=geom_version)
    x1 = x0 + float(WORKSPACE_FRONT_MM)
    shapes = _build_rectangle_edges(x0, y0, x1, y1, 0.0)
    return Part.makeCompound(shapes)


def _build_workspace_3d_shape(ancho_mm, fondo_mm, montaje="Sobrepuesto", geom_version=TABLERO_GEOM_VERSION_CURRENT):
    work_width = _workspace_width_mm(ancho_mm)
    y0 = 0.5 * float(ancho_mm) - 0.5 * float(work_width)
    x0 = _front_plane_x(montaje, fondo_mm, geom_version=geom_version)
    box = Part.makeBox(
        float(WORKSPACE_FRONT_MM),
        float(work_width),
        float(WORKSPACE_HEIGHT_MM),
        App.Vector(float(x0), float(y0), 0.0),
    )
    try:
        return Part.makeCompound(list(getattr(box, "Edges", []) or []))
    except Exception:
        return box


def _build_3d_shape(alto_mm, ancho_mm, fondo_mm, cota_inferior_mm, montaje="Sobrepuesto", geom_version=TABLERO_GEOM_VERSION_CURRENT):
    x0, _x1 = _board_x_limits(montaje, fondo_mm, geom_version=geom_version)
    return Part.makeBox(
        float(fondo_mm),
        float(ancho_mm),
        float(alto_mm),
        App.Vector(float(x0), 0.0, float(cota_inferior_mm)),
    )


def _build_master_shape(
    modo_visual,
    alto_mm,
    ancho_mm,
    fondo_mm,
    cota_inferior_mm,
    montaje="Sobrepuesto",
    show_workspace=False,
    geom_version=TABLERO_GEOM_VERSION_CURRENT,
):
    modo = _normalize_link_mode(modo_visual)
    shapes = []
    if modo in ("Ambos", "Solo3D"):
        shapes.append(_build_3d_shape(alto_mm, ancho_mm, fondo_mm, cota_inferior_mm, montaje=montaje, geom_version=geom_version))
        if _bool_value(show_workspace, False):
            shapes.append(_build_workspace_3d_shape(ancho_mm, fondo_mm, montaje=montaje, geom_version=geom_version))
    if modo in ("Ambos", "Solo2D"):
        shapes.append(_build_2d_shape(ancho_mm, fondo_mm, montaje=montaje, geom_version=geom_version))
        if _bool_value(show_workspace, False):
            shapes.append(_build_workspace_2d_shape(ancho_mm, fondo_mm, montaje=montaje, geom_version=geom_version))
    if not shapes:
        return _build_3d_shape(alto_mm, ancho_mm, fondo_mm, cota_inferior_mm, montaje=montaje, geom_version=geom_version)
    if len(shapes) == 1:
        return shapes[0]
    return Part.makeCompound(shapes)


def _montaje_token(montaje):
    return "EMP" if _safe_text(montaje) == "Empotrado" else "SUP"


def _tipo_tablero_token(main_breaker):
    return "MB" if bool(main_breaker) else "MLO"


def _clase_equipo_token(clase_equipo):
    clase = _normalize_clase_equipo(clase_equipo)
    if clase == "Desconector":
        return "DSC"
    if clase == "Interruptor":
        return "INT"
    return "TAB"


def _master_name_for(range_key, main_breaker, montaje, modo_visual, cota_inferior_mm, show_workspace=False, geom_version=1):
    base = "Master_Tablero_{}_{}_{}_{}_CI{}_AW{}".format(
        _safe_name_token(range_key, "R"),
        _tipo_tablero_token(main_breaker),
        _montaje_token(montaje),
        _safe_name_token(_normalize_link_mode(modo_visual), "Modo"),
        int(round(float(cota_inferior_mm or 0.0))),
        "1" if _bool_value(show_workspace, False) else "0",
    )
    if _int_value(geom_version, 1) >= 2:
        return "{}_GV{}".format(base, _int_value(geom_version, 2))
    return base


def _ensure_master_properties(obj, range_key, main_breaker, montaje, modo_visual, alto_mm, ancho_mm, fondo_mm, cota_inferior_mm, show_workspace=False, geom_version=1):
    _ensure_property(obj, "App::PropertyString", "Tipo", "ElectricCR", "Tipo logico")
    _ensure_property(obj, "App::PropertyString", "Categoria", "ElectricCR", "Categoria logica")
    _ensure_property(obj, "App::PropertyString", "TableroMasterKind", "ElectricCR", "Marca de master")
    _ensure_property(obj, "App::PropertyString", "RangoEspacios", "ElectricCR", "Rango normalizado")
    _ensure_property(obj, "App::PropertyBool", "MainBreaker", "ElectricCR", "True=MB, False=MLO")
    _ensure_property(obj, "App::PropertyFloat", "Alto", "ElectricCR", "Alto del tablero")
    _ensure_property(obj, "App::PropertyFloat", "Ancho", "ElectricCR", "Ancho del tablero")
    _ensure_property(obj, "App::PropertyFloat", "Profundidad", "ElectricCR", "Profundidad del tablero")
    _ensure_property(obj, "App::PropertyFloat", "CotaInferior", "ElectricCR", "Cota inferior del tablero")
    _ensure_property(obj, "App::PropertyBool", "MostrarAreaTrabajo", "ElectricCR", "Mostrar area de trabajo")
    _ensure_property(obj, "App::PropertyInteger", "GeometriaMontajeVersion", "ElectricCR", "Version geometrica del montaje")

    if "Montaje" not in obj.PropertiesList:
        try:
            obj.addProperty("App::PropertyEnumeration", "Montaje", "ElectricCR", "Tipo de montaje").Montaje = list(MONTAJE_CHOICES)
        except Exception:
            pass
    if "ModoVisual" not in obj.PropertiesList:
        try:
            obj.addProperty("App::PropertyEnumeration", "ModoVisual", "ElectricCR", "Modo visual").ModoVisual = list(LINK_MODE_CHOICES)
        except Exception:
            pass

    try:
        obj.Tipo = "Tablero"
    except Exception:
        pass
    try:
        obj.Categoria = "Tablero"
    except Exception:
        pass
    try:
        obj.TableroMasterKind = MASTER_KIND_TOKEN
    except Exception:
        pass
    try:
        obj.RangoEspacios = _safe_text(range_key)
    except Exception:
        pass
    try:
        obj.MainBreaker = bool(main_breaker)
    except Exception:
        pass
    try:
        obj.Alto = float(alto_mm)
    except Exception:
        pass
    try:
        obj.Ancho = float(ancho_mm)
    except Exception:
        pass
    try:
        obj.Profundidad = float(fondo_mm)
    except Exception:
        pass
    try:
        obj.CotaInferior = float(cota_inferior_mm)
    except Exception:
        pass
    try:
        obj.MostrarAreaTrabajo = _bool_value(show_workspace, False)
    except Exception:
        pass
    try:
        obj.GeometriaMontajeVersion = _int_value(geom_version, 1)
    except Exception:
        pass
    try:
        obj.Montaje = _safe_text(montaje) if _safe_text(montaje) in MONTAJE_CHOICES else MONTAJE_CHOICES[1]
    except Exception:
        pass
    try:
        obj.ModoVisual = _normalize_link_mode(modo_visual)
    except Exception:
        pass


def _update_master_shape(obj):
    if obj is None:
        return
    try:
        modo = _normalize_link_mode(getattr(obj, "ModoVisual", DEFAULT_MODE))
        alto_mm = float(getattr(obj, "Alto", 600.0) or 600.0)
        ancho_mm = float(getattr(obj, "Ancho", 400.0) or 400.0)
        fondo_mm = float(getattr(obj, "Profundidad", 150.0) or 150.0)
        cota_inferior_mm = float(getattr(obj, "CotaInferior", 0.0) or 0.0)
        show_workspace = _bool_value(getattr(obj, "MostrarAreaTrabajo", False), False)
        montaje = _safe_text(getattr(obj, "Montaje", "Sobrepuesto"))
        if montaje not in MONTAJE_CHOICES:
            montaje = "Sobrepuesto"
        geom_version = _int_value(getattr(obj, "GeometriaMontajeVersion", 1), 1)
        obj.Shape = _build_master_shape(
            modo,
            alto_mm,
            ancho_mm,
            fondo_mm,
            cota_inferior_mm,
            montaje=montaje,
            show_workspace=show_workspace,
            geom_version=geom_version,
        )
        if GUI_UP and hasattr(obj, "ViewObject") and obj.ViewObject is not None:
            _set_display_mode(obj.ViewObject, ("Flat Lines", "Wireframe", "Shaded"))
    except Exception as ex:
        log_e("No se pudo regenerar Shape del master tablero: {}".format(ex))


class _VP_TableroMaster:
    def __init__(self, vobj):
        self.Object = getattr(vobj, "Object", None)
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = getattr(vobj, "Object", None)
        try:
            vobj.DisplayModes = ("Flat Lines",)
        except Exception:
            pass
        _set_display_mode(vobj, ("Flat Lines", "Wireframe", "Shaded"))
        try:
            vobj.Visibility = False
            vobj.Transparency = 0
            vobj.LineWidth = 1.0
            vobj.PointSize = 3.0
        except Exception:
            pass
        try:
            if hasattr(vobj, "Selectable"):
                vobj.Selectable = False
        except Exception:
            pass
        try:
            if hasattr(vobj, "Pickable"):
                vobj.Pickable = False
        except Exception:
            pass

    def getDisplayModes(self, _vobj):
        return ["Flat Lines"]

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, _mode):
        return "Flat Lines"

    def updateData(self, _fp, _prop):
        return

    def onChanged(self, _vp, _prop):
        return

    def __getstate__(self):
        return None

    def __setstate__(self, _state):
        return


class _TableroMasterProxy(object):
    def __init__(self):
        self.Type = "TableroMasterProxy"

    def __getstate__(self):
        return {"Type": _safe_text(getattr(self, "Type", "TableroMasterProxy")) or "TableroMasterProxy"}

    def __setstate__(self, state):
        type_name = "TableroMasterProxy"
        try:
            if isinstance(state, dict):
                type_name = _safe_text(state.get("Type", type_name)) or type_name
        except Exception:
            pass
        self.Type = type_name

    def attach(self, obj):
        obj.Proxy = self

    def onDocumentRestored(self, obj):
        self.attach(obj)
        try:
            _ensure_master_properties(
                obj,
                _safe_text(getattr(obj, "RangoEspacios", "")),
                _bool_value(getattr(obj, "MainBreaker", False), False),
                _safe_text(getattr(obj, "Montaje", "Sobrepuesto")),
                _normalize_link_mode(getattr(obj, "ModoVisual", DEFAULT_MODE)),
                float(getattr(obj, "Alto", 600.0) or 600.0),
                float(getattr(obj, "Ancho", 400.0) or 400.0),
                float(getattr(obj, "Profundidad", 150.0) or 150.0),
                float(getattr(obj, "CotaInferior", 0.0) or 0.0),
                show_workspace=_bool_value(getattr(obj, "MostrarAreaTrabajo", False), False),
                geom_version=_int_value(getattr(obj, "GeometriaMontajeVersion", 1), 1),
            )
        except Exception:
            pass
        try:
            _setup_master_view(obj)
        except Exception:
            pass
        try:
            _update_master_shape(obj)
        except Exception as ex:
            log_w(
                "No se pudo restaurar master tablero {}: {}".format(
                    _safe_text(getattr(obj, "Name", "")),
                    ex,
                )
            )
        try:
            _ensure_tablero_observer(force_refresh=False)
        except Exception:
            pass
        try:
            obj.touch()
        except Exception:
            pass

    def execute(self, obj):
        _update_master_shape(obj)

    def onChanged(self, obj, prop):
        if prop in ("ModoVisual", "Alto", "Ancho", "Profundidad", "Montaje", "MostrarAreaTrabajo", "CotaInferior", "GeometriaMontajeVersion"):
            _update_master_shape(obj)


def _setup_master_view(master):
    if not GUI_UP or master is None or not hasattr(master, "ViewObject") or master.ViewObject is None:
        return
    try:
        _VP_TableroMaster(master.ViewObject)
    except Exception:
        pass
    try:
        _set_display_mode(master.ViewObject, ("Flat Lines", "Wireframe", "Shaded"))
    except Exception:
        pass
    _hide_in_view(master)


def _is_tablero_master(obj):
    if obj is None:
        return False
    if _safe_text(getattr(obj, "TypeId", "")) != "Part::FeaturePython":
        return False
    return _safe_text(getattr(obj, "TableroMasterKind", "")) == MASTER_KIND_TOKEN


def _create_master_featurepython(doc, internal_name, range_key, main_breaker, montaje, modo_visual, alto_mm, ancho_mm, fondo_mm, cota_inferior_mm, show_workspace=False, geom_version=1):
    try:
        master = doc.addObject("Part::FeaturePython", internal_name)
    except Exception:
        master = doc.addObject("Part::FeaturePython")
    try:
        master.Label = internal_name
    except Exception:
        pass
    proxy = _TableroMasterProxy()
    proxy.attach(master)
    _ensure_master_properties(
        master,
        range_key,
        main_breaker,
        montaje,
        modo_visual,
        alto_mm,
        ancho_mm,
        fondo_mm,
        cota_inferior_mm,
        show_workspace=show_workspace,
        geom_version=geom_version,
    )
    _update_master_shape(master)
    _setup_master_view(master)
    return master


def _get_or_create_master_tablero(doc, range_key, main_breaker, montaje, modo_visual, alto_mm, ancho_mm, fondo_mm, cota_inferior_mm, lib_group, hide_master=True, show_workspace=False, geom_version=1):
    master_name = _master_name_for(
        range_key,
        main_breaker,
        montaje,
        modo_visual,
        cota_inferior_mm,
        show_workspace=show_workspace,
        geom_version=geom_version,
    )
    master = doc.getObject(master_name)
    if master is None or not _is_tablero_master(master):
        master = _create_master_featurepython(
            doc,
            master_name,
            range_key,
            main_breaker,
            montaje,
            modo_visual,
            alto_mm,
            ancho_mm,
            fondo_mm,
            cota_inferior_mm,
            show_workspace,
            geom_version,
        )
    else:
        _ensure_master_properties(
            master,
            range_key,
            main_breaker,
            montaje,
            modo_visual,
            alto_mm,
            ancho_mm,
            fondo_mm,
            cota_inferior_mm,
            show_workspace=show_workspace,
            geom_version=geom_version,
        )
        _update_master_shape(master)
        _setup_master_view(master)
    _add_to_group(lib_group, master)
    if hide_master:
        _hide_in_view(master)
    return master


def _compose_codigo_interno(clase_equipo, espacios, main_breaker, montaje):
    return "{}_E{}_{}_{}".format(
        _clase_equipo_token(clase_equipo),
        int(espacios),
        _tipo_tablero_token(main_breaker),
        _montaje_token(montaje),
    )


def _build_link_label(codigo, nombre_tablero, codigo_interno):
    codigo_txt = _safe_text(codigo).strip()
    nombre_txt = _safe_text(nombre_tablero).strip()
    if codigo_txt and nombre_txt:
        return "{} - {}".format(codigo_txt, nombre_txt)
    if codigo_txt:
        return codigo_txt
    if nombre_txt:
        return nombre_txt
    return codigo_interno


def _is_tablero_link(obj):
    if obj is None:
        return False
    if _safe_text(getattr(obj, "TypeId", "")) != "App::Link":
        return False
    tipo = _safe_text(getattr(obj, "Tipo", ""))
    categoria = _safe_text(getattr(obj, "Categoria", ""))
    return tipo in EQUIPO_CHOICES or categoria in EQUIPO_CHOICES


def _plan_rotation_from_placement(placement):
    try:
        rot = getattr(placement, "Rotation", App.Rotation())
    except Exception:
        return App.Rotation()
    try:
        x_axis = rot.multVec(App.Vector(1.0, 0.0, 0.0))
        x_plan = App.Vector(float(x_axis.x), float(x_axis.y), 0.0)
        if x_plan.Length <= 1e-6:
            return App.Rotation()
        angle_deg = math.degrees(math.atan2(float(x_plan.y), float(x_plan.x)))
        return App.Rotation(App.Vector(0.0, 0.0, 1.0), angle_deg)
    except Exception:
        return App.Rotation()


def _vector_distance(v1, v2):
    try:
        dx = float(v1.x) - float(v2.x)
        dy = float(v1.y) - float(v2.y)
        dz = float(v1.z) - float(v2.z)
        return math.sqrt(dx * dx + dy * dy + dz * dz)
    except Exception:
        return 1.0e9


def _placements_match(pl_a, pl_b, pos_tol=1.0e-3, dir_tol=1.0e-6):
    try:
        if _vector_distance(pl_a.Base, pl_b.Base) > float(pos_tol):
            return False
        ax_a = pl_a.Rotation.multVec(App.Vector(1.0, 0.0, 0.0))
        ax_b = pl_b.Rotation.multVec(App.Vector(1.0, 0.0, 0.0))
        ay_a = pl_a.Rotation.multVec(App.Vector(0.0, 1.0, 0.0))
        ay_b = pl_b.Rotation.multVec(App.Vector(0.0, 1.0, 0.0))
        return _vector_distance(ax_a, ax_b) <= float(dir_tol) and _vector_distance(ay_a, ay_b) <= float(dir_tol)
    except Exception:
        return False


def _placement_is_identity(pl, pos_tol=1.0e-3, dir_tol=1.0e-6):
    return _placements_match(pl, App.Placement(), pos_tol=pos_tol, dir_tol=dir_tol)


def _effective_link_placement(link_obj):
    if link_obj is None:
        return App.Placement()
    try:
        if hasattr(link_obj, "getGlobalPlacement"):
            gp = link_obj.getGlobalPlacement()
            if gp is not None:
                return App.Placement(gp)
    except Exception:
        pass
    try:
        placement = App.Placement(getattr(link_obj, "Placement", App.Placement()))
    except Exception:
        placement = App.Placement()
    link_placement = App.Placement()
    try:
        if hasattr(link_obj, "LinkPlacement"):
            link_placement = App.Placement(getattr(link_obj, "LinkPlacement", App.Placement()))
    except Exception:
        link_placement = App.Placement()
    if _placement_is_identity(link_placement):
        return placement
    if _placement_is_identity(placement):
        return link_placement
    if _placements_match(placement, link_placement):
        return placement
    try:
        return placement.multiply(link_placement)
    except Exception:
        return placement


def _compute_text_placement(link_obj):
    try:
        ancho_mm = float(getattr(link_obj, "Ancho", 0.0) or 0.0)
    except Exception:
        ancho_mm = 0.0
    try:
        profundidad_mm = float(getattr(link_obj, "Profundidad", 0.0) or 0.0)
    except Exception:
        profundidad_mm = 0.0
    montaje_value = _safe_text(getattr(link_obj, "Montaje", "Sobrepuesto"))
    if montaje_value not in MONTAJE_CHOICES:
        montaje_value = "Sobrepuesto"
    geom_version = _int_value(getattr(link_obj, "GeometriaMontajeVersion", 1), 1)
    front_gap_mm = max(float(TEXT_FRONT_OFFSET_MM), 180.0)
    front_x = _front_plane_x(montaje_value, profundidad_mm, geom_version=geom_version)
    local = App.Vector(
        float(front_x) + front_gap_mm,
        0.5 * float(ancho_mm),
        0.0,
    )
    try:
        placement = _effective_link_placement(link_obj)
        rot_plan = _plan_rotation_from_placement(placement)
        text_rot = rot_plan.multiply(App.Rotation(App.Vector(0.0, 0.0, 1.0), 90.0))
        base = placement.Base + rot_plan.multVec(local)
        base = App.Vector(float(base.x), float(base.y), 0.0)
        return App.Placement(base, text_rot)
    except Exception:
        return App.Placement(local, App.Rotation())


def _rectangle_context_from_shape(shape, pick_point, source="rectangle"):
    if shape is None or pick_point is None:
        return None
    rect_points = _extract_horizontal_rectangle_points(shape)
    if not rect_points:
        return None
    centroid = App.Vector(
        sum(float(pt.x) for pt in rect_points) / 4.0,
        sum(float(pt.y) for pt in rect_points) / 4.0,
        sum(float(pt.z) for pt in rect_points) / 4.0,
    )
    best = None
    for idx in range(4):
        start = rect_points[idx]
        end = rect_points[(idx + 1) % 4]
        proj = _project_point_to_segment(pick_point, start, end)
        dist = _vector_distance(proj, pick_point)
        edge_dir = _normalize_vector(_vector_plan(_vector_sub(end, start)))
        inward = _normalize_vector(App.Vector(-float(edge_dir.y), float(edge_dir.x), 0.0))
        if _vector_dot(_vector_plan(_vector_sub(centroid, proj)), inward) < 0.0:
            inward = _vector_mul(inward, -1.0)
        candidate = (dist, proj, inward, edge_dir, _midpoint(start, end))
        if best is None or candidate[0] < best[0]:
            best = candidate
    if best is None:
        return None
    _, proj, inward, edge_dir, edge_mid = best
    base_z = float(sum(float(pt.z) for pt in rect_points) / 4.0)
    anchor = App.Vector(float(proj.x), float(proj.y), base_z)
    return _make_insertion_context(
        kind="rectangle",
        point=_copy_vector(pick_point),
        anchor=anchor,
        front_dir=inward,
        side_dir=edge_dir,
        base_z=base_z,
        source="{}@({:.1f},{:.1f})".format(_safe_text(source) or "rectangle", float(edge_mid.x), float(edge_mid.y)),
    )


def _face_mid_normal(face):
    if face is None:
        return None
    try:
        u0, u1, v0, v1 = getattr(face, "ParameterRange", (0.0, 1.0, 0.0, 1.0))
        normal = face.normalAt(0.5 * (float(u0) + float(u1)), 0.5 * (float(v0) + float(v1)))
        return _copy_vector(normal)
    except Exception:
        return None


def _active_view_out_vector(gui_module=None):
    if not GUI_UP:
        return None
    gui_ref = gui_module or Gui
    if gui_ref is None:
        return None
    try:
        view = getattr(getattr(gui_ref, "ActiveDocument", None), "ActiveView", None)
        if view is None:
            return None
    except Exception:
        return None

    try:
        from pivy import coin  # type: ignore

        cam = view.getCameraNode()
        if cam is not None:
            rot = cam.orientation.getValue()
            out = rot.multVec(coin.SbVec3f(0.0, 0.0, 1.0))
            vals = out.getValue() if hasattr(out, "getValue") else out
            vec = App.Vector(float(vals[0]), float(vals[1]), float(vals[2]))
            plan = _vector_plan(vec)
            if _vector_length(plan) > 1.0e-6:
                return _normalize_vector(plan)
    except Exception:
        pass

    try:
        view_dir = _copy_vector(view.getViewDirection())
        plan = _vector_plan(view_dir)
        if _vector_length(plan) > 1.0e-6:
            return _normalize_vector(_vector_mul(plan, -1.0))
    except Exception:
        pass
    return None


def _face_context_from_face(face, owner_obj=None, pick_point=None, source="face", gui_module=None):
    if face is None:
        return None
    face_center = _shape_center(face)
    owner_shape = _shape_from_object(owner_obj)
    outward = App.Vector(0.0, 0.0, 0.0)
    if owner_shape is not None:
        outward = _vector_plan(_vector_sub(face_center, _shape_center(owner_shape)))
    normal = _vector_plan(_face_mid_normal(face))
    if _vector_length(outward) > 1.0e-6:
        front_dir = _normalize_vector(outward)
    elif _vector_length(normal) > 1.0e-6:
        front_dir = _normalize_vector(normal)
    else:
        return None
    if _vector_length(_vector_plan(front_dir)) <= 1.0e-6:
        return None
    view_out = _active_view_out_vector(gui_module=gui_module)
    if view_out is not None and _vector_dot(front_dir, view_out) < 0.0:
        front_dir = _vector_mul(front_dir, -1.0)
    base_point = _copy_vector(pick_point if pick_point is not None else face_center)
    try:
        base_z = float(getattr(face, "BoundBox", None).ZMin)
    except Exception:
        base_z = float(base_point.z)
    anchor = App.Vector(float(base_point.x), float(base_point.y), base_z)
    side_dir = App.Vector(-float(front_dir.y), float(front_dir.x), 0.0)
    return _make_insertion_context(
        kind="face",
        point=base_point,
        anchor=anchor,
        front_dir=front_dir,
        side_dir=side_dir,
        base_z=base_z,
        source=source,
    )


def pick_insertion_context_from_gui(gui_module=None):
    origin = _make_insertion_context(kind="origin", point=App.Vector(0.0, 0.0, 0.0), source="origin")
    if not GUI_UP:
        return origin

    gui_ref = gui_module or Gui
    if gui_ref is None:
        return origin

    try:
        selection_ex = list(gui_ref.Selection.getSelectionEx() or [])
    except Exception:
        return origin
    if not selection_ex:
        return origin

    for sx in selection_ex:
        obj = getattr(sx, "Object", None)
        picked_points = list(getattr(sx, "PickedPoints", []) or [])
        pick_point = _copy_vector(picked_points[0]) if picked_points else None
        for sub in (getattr(sx, "SubObjects", []) or []):
            if _safe_text(getattr(sub, "ShapeType", "")) != "Face":
                continue
            ctx = _face_context_from_face(sub, owner_obj=obj, pick_point=pick_point, source="face", gui_module=gui_ref)
            if ctx is not None:
                return ctx

    for sx in selection_ex:
        obj = getattr(sx, "Object", None)
        picked_points = list(getattr(sx, "PickedPoints", []) or [])
        pick_point = _copy_vector(picked_points[0]) if picked_points else None
        if pick_point is None:
            continue
        for sub in (getattr(sx, "SubObjects", []) or []):
            ctx = _rectangle_context_from_shape(sub, pick_point, source="subshape")
            if ctx is not None:
                return ctx
        ctx = _rectangle_context_from_shape(_shape_from_object(obj), pick_point, source=getattr(obj, "Name", "object"))
        if ctx is not None:
            return ctx

    for sx in selection_ex:
        picked_points = list(getattr(sx, "PickedPoints", []) or [])
        if picked_points:
            picked = _copy_vector(picked_points[0])
            return _make_insertion_context(kind="point", point=picked, anchor=picked, base_z=float(picked.z), source="point")
        for sub in (getattr(sx, "SubObjects", []) or []):
            if _safe_text(getattr(sub, "ShapeType", "")) == "Vertex" and hasattr(sub, "Point"):
                picked = _copy_vector(sub.Point)
                return _make_insertion_context(kind="point", point=picked, anchor=picked, base_z=float(picked.z), source="vertex")

    for sx in selection_ex:
        obj = getattr(sx, "Object", None)
        if obj is None or not hasattr(obj, "Placement"):
            continue
        try:
            base = _copy_vector(obj.Placement.Base)
            return _make_insertion_context(kind="point", point=base, anchor=base, base_z=float(base.z), source=getattr(obj, "Name", "placement"))
        except Exception:
            continue
    return origin


def pick_insertion_point_from_gui(gui_module=None):
    context = pick_insertion_context_from_gui(gui_module=gui_module)
    return _copy_vector((context or {}).get("point", App.Vector(0.0, 0.0, 0.0)))


def _placement_from_insertion_context(context, montaje, ancho_mm, fondo_mm, fallback_point=None):
    ctx = context or {}
    kind = _safe_text(ctx.get("kind", "point")) or "point"
    if kind in ("face", "rectangle"):
        anchor = _copy_vector(ctx.get("anchor", fallback_point or App.Vector(0.0, 0.0, 0.0)), z=float(ctx.get("base_z", 0.0)))
        front_dir = _normalize_vector(_vector_plan(ctx.get("front_dir", App.Vector(1.0, 0.0, 0.0))), fallback=App.Vector(1.0, 0.0, 0.0))
        side_dir = _normalize_vector(_vector_plan(ctx.get("side_dir", App.Vector(0.0, 1.0, 0.0))), fallback=App.Vector(-front_dir.y, front_dir.x, 0.0))
        base = _vector_sub(anchor, _vector_mul(side_dir, 0.5 * float(ancho_mm)))
        base = App.Vector(float(base.x), float(base.y), float(ctx.get("base_z", 0.0)))
        return App.Placement(base, _rotation_from_front_vector(front_dir))

    base_point = _copy_vector(fallback_point if fallback_point is not None else ctx.get("point", App.Vector(0.0, 0.0, 0.0)))
    return App.Placement(base_point, App.Rotation())


def _sync_text_with_link(link_obj):
    if link_obj is None:
        return
    text_obj = getattr(link_obj, "EtiquetaTexto", None)
    if text_obj is None:
        return
    codigo_texto = _safe_text(getattr(link_obj, "Codigo", "")).strip() or _safe_text(getattr(link_obj, "Label", "")).strip() or "TAB"
    try:
        text_obj.Text = [codigo_texto]
    except Exception:
        pass
    try:
        text_obj.Placement = _compute_text_placement(link_obj)
    except Exception:
        pass
    try:
        text_obj.Label = "{}_Texto".format(_safe_name_token(codigo_texto, "Tablero"))
    except Exception:
        pass
    try:
        text_obj.ViewObject.FontSize = 200.0
    except Exception:
        pass
    _show_in_view(text_obj)
    try:
        text_obj.Justification = "Middle-Center"
    except Exception:
        pass


def sync_tablero_texts(doc=None):
    target_doc = doc or App.ActiveDocument
    if target_doc is None:
        return 0
    synced = 0
    for obj in (getattr(target_doc, "Objects", []) or []):
        if not _is_tablero_link(obj):
            continue
        try:
            _sync_text_with_link(obj)
            synced += 1
        except Exception:
            continue
    return synced


def refresh_tablero_geometry(doc=None):
    target_doc = doc or App.ActiveDocument
    if target_doc is None:
        return {"masters": 0, "texts": 0}
    masters = 0
    links = 0
    for obj in (getattr(target_doc, "Objects", []) or []):
        if not _is_tablero_link(obj):
            continue
        try:
            _retarget_link_to_master(obj)
            links += 1
        except Exception:
            continue
    for obj in (getattr(target_doc, "Objects", []) or []):
        if not _is_tablero_master(obj):
            continue
        try:
            _update_master_shape(obj)
            masters += 1
        except Exception:
            continue
    texts = sync_tablero_texts(target_doc)
    try:
        target_doc.recompute()
    except Exception:
        pass
    return {"masters": masters, "texts": texts, "links": links}


class _TableroDocumentObserver:
    def __init__(self):
        self._busy = False

    def slotChangedObject(self, obj, prop):  # noqa: N802 (FreeCAD callback)
        if self._busy or not _is_tablero_link(obj):
            return
        prop_name = _safe_text(prop)
        if prop_name not in (
            "Placement",
            "LinkPlacement",
            "Codigo",
            "Label",
            "Ancho",
            "Alto",
            "Profundidad",
            "EtiquetaTexto",
            "Espacios",
            "MainBreaker",
            "Montaje",
            "ModoVisual",
            "MostrarAreaTrabajo",
            "GeometriaMontajeVersion",
            "AlturaSuperiorInstalacion",
            "CotaInferior",
            "ClaseEquipo",
            "PerfilDimensiones",
            "ConfiguracionCatalogo",
            "AmperajeNominal",
            "CajaEaton",
        ):
            return
        self._busy = True
        try:
            if prop_name in (
                "Espacios",
                "MainBreaker",
                "Montaje",
                "ModoVisual",
                "MostrarAreaTrabajo",
                "GeometriaMontajeVersion",
                "AlturaSuperiorInstalacion",
                "CotaInferior",
                "ClaseEquipo",
                "PerfilDimensiones",
                "ConfiguracionCatalogo",
                "AmperajeNominal",
                "CajaEaton",
            ):
                _retarget_link_to_master(obj)
            _sync_text_with_link(obj)
        finally:
            self._busy = False

    def slotDeletedObject(self, obj):  # noqa: N802 (FreeCAD callback)
        if self._busy or not _is_tablero_link(obj):
            return
        self._busy = True
        try:
            text_obj = getattr(obj, "EtiquetaTexto", None)
            doc = getattr(obj, "Document", None)
            if text_obj is not None and doc is not None:
                text_name = _safe_text(getattr(text_obj, "Name", ""))
                if text_name and doc.getObject(text_name) is not None:
                    try:
                        doc.removeObject(text_name)
                    except Exception:
                        pass
        finally:
            self._busy = False


def _remove_tablero_observer():
    existing = getattr(App, TABLERO_OBSERVER_ATTR, None)
    if existing is None:
        return
    try:
        App.removeDocumentObserver(existing)
    except Exception:
        pass
    try:
        delattr(App, TABLERO_OBSERVER_ATTR)
    except Exception:
        pass


def _ensure_tablero_observer(force_refresh=True):
    existing = getattr(App, TABLERO_OBSERVER_ATTR, None)
    if existing is not None and force_refresh:
        _remove_tablero_observer()
        existing = None
    if existing is not None:
        return existing
    observer = _TableroDocumentObserver()
    try:
        App.addDocumentObserver(observer)
        setattr(App, TABLERO_OBSERVER_ATTR, observer)
        return observer
    except Exception as ex:
        log_w("No se pudo registrar observer de tablero: {}".format(ex))
        return None


def _create_tablero_link(doc, master, tableros_group, internal_name):
    try:
        link = doc.addObject("App::Link", internal_name)
    except Exception:
        link = doc.addObject("App::Link")

    link.LinkedObject = master
    try:
        link.LinkTransform = True
    except Exception:
        pass
    try:
        link.setEditorMode("Placement", 0)
    except Exception:
        pass
    try:
        link.setEditorMode("LinkPlacement", 0)
    except Exception:
        pass
    try:
        link.setPropertyStatus("Placement", [])
    except Exception:
        pass
    try:
        link.setPropertyStatus("LinkPlacement", [])
    except Exception:
        pass
    try:
        if hasattr(link, "LinkPlacement"):
            link.LinkPlacement = App.Placement()
    except Exception:
        pass
    _show_in_view(link)
    if GUI_UP and hasattr(link, "ViewObject") and link.ViewObject is not None:
        _set_display_mode(link.ViewObject, ("Flat Lines", "Wireframe", "Shaded"))
        try:
            link.ViewObject.LineWidth = 1.0
        except Exception:
            pass
        try:
            link.ViewObject.Transparency = 0
        except Exception:
            pass
    _add_to_group(tableros_group, link)
    return link


def _ensure_link_properties(
    obj,
    clase_equipo,
    codigo,
    nombre_tablero,
    conectado_a,
    codigo_interno,
    espacios,
    main_breaker,
    montaje,
    modo_visual,
    rango_key,
    alto_mm,
    ancho_mm,
    fondo_mm,
    perfil_dimensiones="Generico",
    configuracion_catalogo="Auto",
    amperaje_nominal=225,
    caja_eaton="Auto",
    caja_modelo="",
    show_workspace=False,
    geom_version=1,
):
    _ensure_property(obj, "App::PropertyString", "Tipo", "ElectricCR", "Tipo logico")
    _ensure_property(obj, "App::PropertyString", "Categoria", "ElectricCR", "Categoria logica")
    _ensure_property(obj, "App::PropertyString", "ClaseEquipo", "ElectricCR", "Clase de equipo")
    _ensure_property(obj, "App::PropertyString", "Codigo", "Tablero", "Codigo manual")
    _ensure_property(obj, "App::PropertyString", "NombreTablero", "Tablero", "Nombre manual")
    _ensure_property(obj, "App::PropertyString", "ConectadoA", "Tablero", "Tablero o fuente aguas arriba")
    _ensure_property(obj, "App::PropertyString", "CodigoInterno", "Tablero", "Codigo interno")
    _ensure_property(obj, "App::PropertyInteger", "Espacios", "Tablero", "Cantidad de espacios")
    _ensure_property(obj, "App::PropertyBool", "MainBreaker", "Tablero", "True=MB, False=MLO")
    _ensure_property(obj, "App::PropertyString", "RangoEspacios", "Tablero", "Rango normalizado")
    _ensure_property(obj, "App::PropertyFloat", "Alto", "Tablero", "Alto del tablero")
    _ensure_property(obj, "App::PropertyFloat", "Ancho", "Tablero", "Ancho del tablero")
    _ensure_property(obj, "App::PropertyFloat", "Profundidad", "Tablero", "Profundidad del tablero")
    _ensure_property(obj, "App::PropertyString", "TipoTablero", "Tablero", "MB o MLO")
    _ensure_property(obj, "App::PropertyString", "PerfilDimensiones", "Tablero", "Perfil de dimensiones del tablero")
    _ensure_property(obj, "App::PropertyString", "ConfiguracionCatalogo", "Tablero", "Configuracion de catalogo para perfiles de fabricante")
    _ensure_property(obj, "App::PropertyInteger", "AmperajeNominal", "Tablero", "Amperaje nominal de referencia")
    _ensure_property(obj, "App::PropertyString", "CajaEaton", "Tablero", "Caja Eaton seleccionada manualmente o Auto")
    _ensure_property(obj, "App::PropertyString", "CajaModelo", "Tablero", "Caja o rango realmente usado")
    _ensure_property(obj, "App::PropertyFloat", "AlturaSuperiorInstalacion", "Tablero", "Cota superior de instalacion (mm)")
    _ensure_property(obj, "App::PropertyFloat", "CotaInferior", "Tablero", "Cota inferior del tablero (mm)")
    _ensure_property(obj, "App::PropertyBool", "MostrarAreaTrabajo", "Visual", "Mostrar area de trabajo")
    _ensure_property(obj, "App::PropertyInteger", "GeometriaMontajeVersion", "Visual", "Version geometrica del montaje")
    _ensure_property(obj, "App::PropertyLink", "EtiquetaTexto", "Visual", "Texto Draft asociado")

    if "Montaje" not in obj.PropertiesList:
        try:
            obj.addProperty("App::PropertyEnumeration", "Montaje", "Tablero", "Tipo de montaje").Montaje = list(MONTAJE_CHOICES)
        except Exception:
            pass
    if "ModoVisual" not in obj.PropertiesList:
        try:
            obj.addProperty("App::PropertyEnumeration", "ModoVisual", "Visual", "Modo visual").ModoVisual = list(LINK_MODE_CHOICES)
        except Exception:
            pass

    try:
        obj.Tipo = _normalize_clase_equipo(clase_equipo)
    except Exception:
        pass
    try:
        obj.Categoria = _normalize_clase_equipo(clase_equipo)
    except Exception:
        pass
    try:
        obj.ClaseEquipo = _normalize_clase_equipo(clase_equipo)
    except Exception:
        pass
    try:
        obj.Codigo = _safe_text(codigo)
    except Exception:
        pass
    try:
        obj.NombreTablero = _safe_text(nombre_tablero)
    except Exception:
        pass
    try:
        obj.ConectadoA = _safe_text(conectado_a)
    except Exception:
        pass
    try:
        obj.CodigoInterno = _safe_text(codigo_interno)
    except Exception:
        pass
    try:
        obj.Espacios = int(espacios)
    except Exception:
        pass
    try:
        obj.MainBreaker = bool(main_breaker)
    except Exception:
        pass
    try:
        obj.Montaje = _safe_text(montaje) if _safe_text(montaje) in MONTAJE_CHOICES else MONTAJE_CHOICES[1]
    except Exception:
        pass
    try:
        obj.ModoVisual = _normalize_link_mode(modo_visual)
    except Exception:
        pass
    try:
        obj.MostrarAreaTrabajo = _bool_value(show_workspace, False)
    except Exception:
        pass
    try:
        obj.GeometriaMontajeVersion = _int_value(geom_version, 1)
    except Exception:
        pass
    try:
        obj.RangoEspacios = _safe_text(rango_key)
    except Exception:
        pass
    try:
        obj.Alto = float(alto_mm)
    except Exception:
        pass
    try:
        obj.Ancho = float(ancho_mm)
    except Exception:
        pass
    try:
        obj.Profundidad = float(fondo_mm)
    except Exception:
        pass
    try:
        obj.TipoTablero = _tipo_tablero_token(main_breaker)
    except Exception:
        pass
    try:
        obj.PerfilDimensiones = _normalize_dimension_profile(perfil_dimensiones)
    except Exception:
        pass
    try:
        obj.ConfiguracionCatalogo = _normalize_eaton_config(configuracion_catalogo, main_breaker=main_breaker)
    except Exception:
        pass
    try:
        obj.AmperajeNominal = _normalize_eaton_amp(amperaje_nominal, default=225)
    except Exception:
        pass
    try:
        obj.CajaEaton = _normalize_eaton_box(caja_eaton)
    except Exception:
        pass
    try:
        obj.CajaModelo = _safe_text(caja_modelo or rango_key)
    except Exception:
        pass
    try:
        obj.setEditorMode("CodigoInterno", 1)
    except Exception:
        pass


def _retarget_link_to_master(link_obj):
    if link_obj is None:
        return None
    doc = getattr(link_obj, "Document", None)
    if doc is None:
        return None
    clase_equipo_value, espacios_value, main_breaker_value = _resolve_insert_defaults(
        getattr(link_obj, "ClaseEquipo", getattr(link_obj, "Tipo", "Tablero")),
        getattr(link_obj, "Espacios", 42),
        getattr(link_obj, "MainBreaker", False),
    )
    perfil_dimensiones = _normalize_dimension_profile(getattr(link_obj, "PerfilDimensiones", "Generico"))
    configuracion_catalogo = _safe_text(getattr(link_obj, "ConfiguracionCatalogo", "Auto"))
    amperaje_nominal = _int_value(getattr(link_obj, "AmperajeNominal", 225), 225)
    caja_eaton = _safe_text(getattr(link_obj, "CajaEaton", "Auto"))
    try:
        dims = calcular_dimensiones(
            espacios_value,
            amp=amperaje_nominal,
            main_breaker=main_breaker_value,
            dimension_profile=perfil_dimensiones,
            eaton_config=configuracion_catalogo,
            eaton_box=caja_eaton,
        )
    except Exception as ex:
        log_w("No se pudo recalcular tablero {}: {}".format(_safe_text(getattr(link_obj, "Name", "")), ex))
        return None
    montaje_value = _safe_text(getattr(link_obj, "Montaje", "Sobrepuesto"))
    if montaje_value not in MONTAJE_CHOICES:
        montaje_value = "Sobrepuesto"
    modo_visual = _normalize_link_mode(getattr(link_obj, "ModoVisual", DEFAULT_MODE))
    show_workspace = _bool_value(getattr(link_obj, "MostrarAreaTrabajo", False), False)
    geom_version = _int_value(getattr(link_obj, "GeometriaMontajeVersion", 1), 1)
    try:
        altura_sup = float(getattr(link_obj, "AlturaSuperiorInstalacion", DEFAULT_ALTURA_SUPERIOR_MM) or DEFAULT_ALTURA_SUPERIOR_MM)
    except Exception:
        altura_sup = float(DEFAULT_ALTURA_SUPERIOR_MM)
    cota_inferior = float(altura_sup) - float(dims["alto_mm"])
    g_electrico = _ensure_main_electrico_group(doc)
    g_lib = _ensure_lib_root_group(doc, g_electrico)
    g_lib_tableros = _ensure_tablero_masters_group(doc, g_lib)
    master = _get_or_create_master_tablero(
        doc=doc,
        range_key=dims["rango"],
        main_breaker=bool(main_breaker_value),
        montaje=montaje_value,
        modo_visual=modo_visual,
        alto_mm=dims["alto_mm"],
        ancho_mm=dims["ancho_mm"],
        fondo_mm=dims["fondo_mm"],
        cota_inferior_mm=cota_inferior,
        lib_group=g_lib_tableros,
        hide_master=True,
        show_workspace=show_workspace,
        geom_version=geom_version,
    )
    try:
        if hasattr(link_obj, "setLink"):
            link_obj.setLink(master)
        else:
            link_obj.LinkedObject = master
    except Exception:
        try:
            link_obj.LinkedObject = master
        except Exception:
            pass
    _ensure_link_properties(
        obj=link_obj,
        clase_equipo=clase_equipo_value,
        codigo=getattr(link_obj, "Codigo", ""),
        nombre_tablero=getattr(link_obj, "NombreTablero", ""),
        conectado_a=getattr(link_obj, "ConectadoA", ""),
        codigo_interno=getattr(link_obj, "CodigoInterno", ""),
        espacios=dims["espacios"],
        main_breaker=main_breaker_value,
        montaje=montaje_value,
        modo_visual=modo_visual,
        rango_key=dims["rango"],
        alto_mm=dims["alto_mm"],
        ancho_mm=dims["ancho_mm"],
        fondo_mm=dims["fondo_mm"],
        perfil_dimensiones=dims.get("perfil_dimensiones", perfil_dimensiones),
        configuracion_catalogo=dims.get("configuracion_catalogo", configuracion_catalogo),
        amperaje_nominal=dims.get("amp", amperaje_nominal),
        caja_eaton=dims.get("caja_eaton", caja_eaton),
        caja_modelo=dims.get("caja_modelo", dims["rango"]),
        show_workspace=show_workspace,
        geom_version=geom_version,
    )
    try:
        link_obj.AlturaSuperiorInstalacion = altura_sup
    except Exception:
        pass
    try:
        link_obj.CotaInferior = cota_inferior
    except Exception:
        pass
    return master


def _create_instance_text(doc, parent_group, link_obj, codigo_texto):
    if Draft is None or link_obj is None:
        return None

    lines = [_safe_text(codigo_texto).strip() or "TAB"]
    placement = _compute_text_placement(link_obj)
    p = placement.Base
    txt = None
    factories = []
    make_text = getattr(Draft, "make_text", None)
    makeText = getattr(Draft, "makeText", None)
    if callable(make_text):
        factories.extend(
            [
                lambda: make_text(lines, point=p),
                lambda: make_text("\n".join(lines), point=p),
                lambda: make_text(lines, p),
                lambda: make_text("\n".join(lines), p),
                lambda: make_text(lines, placement=placement),
                lambda: make_text("\n".join(lines), placement=placement),
                lambda: make_text(lines, placement),
                lambda: make_text("\n".join(lines), placement),
                lambda: make_text(lines),
                lambda: make_text("\n".join(lines)),
            ]
        )
    if callable(makeText):
        factories.extend(
            [
                lambda: makeText(lines, point=p),
                lambda: makeText("\n".join(lines), point=p),
                lambda: makeText(lines, p),
                lambda: makeText("\n".join(lines), p),
                lambda: makeText(lines),
                lambda: makeText("\n".join(lines)),
            ]
        )
    for factory in factories:
        try:
            txt = factory()
            if txt is not None:
                break
        except Exception:
            continue

    if txt is None:
        log_w("No se pudo crear el texto Draft del tablero.")
        return None

    try:
        txt.Label = "{}_Texto".format(_safe_name_token(lines[0], "Tablero"))
    except Exception:
        pass
    try:
        txt.Text = lines
    except Exception:
        pass
    try:
        txt.Placement = placement
    except Exception:
        pass
    try:
        txt.ViewObject.FontSize = 200.0
    except Exception:
        pass
    _show_in_view(txt)
    try:
        txt.Justification = "Middle-Center"
    except Exception:
        pass
    _add_to_group(parent_group, txt)
    return txt


def insertar_tablero(
    doc=None,
    clase_equipo="Tablero",
    codigo="",
    espacios=42,
    amp=None,
    amperaje_nominal=225,
    main_breaker=False,
    modo=DEFAULT_MODE,
    usar_step=False,
    crear_area_nfpa=False,
    montage=None,
    montaje="Sobrepuesto",
    nombre_tablero="",
    conectado_a="",
    perfil_dimensiones="Generico",
    configuracion_catalogo="Auto",
    caja_eaton="Auto",
    altura_superior_mm=DEFAULT_ALTURA_SUPERIOR_MM,
    mostrar_area_trabajo=False,
    position=None,
    insertion_point=None,
    insertion_context=None,
    recompute=True,
    create_text=True,
    hide_master=True,
):
    del usar_step, crear_area_nfpa

    doc = doc or get_or_create_doc("Electrico")
    montaje_value = _safe_text(montaje or montage or "Sobrepuesto")
    if montaje_value not in MONTAJE_CHOICES:
        montaje_value = "Sobrepuesto"
    clase_equipo_value, espacios_value, main_breaker_value = _resolve_insert_defaults(clase_equipo, espacios, main_breaker)
    modo_visual = _normalize_link_mode(modo)
    if amp is not None:
        amperaje_nominal = amp
    dims = calcular_dimensiones(
        espacios_value,
        amp=amperaje_nominal,
        main_breaker=main_breaker_value,
        dimension_profile=perfil_dimensiones,
        eaton_config=configuracion_catalogo,
        eaton_box=caja_eaton,
    )

    g_electrico = _ensure_main_electrico_group(doc)
    g_tableros = _ensure_tableros_group(doc, g_electrico)
    g_lib = _ensure_lib_root_group(doc, g_electrico)
    g_lib_tableros = _ensure_tablero_masters_group(doc, g_lib)
    _show_in_view(g_electrico)
    _show_in_view(g_tableros)
    _hide_in_view(g_lib)
    _hide_in_view(g_lib_tableros)
    _ensure_tablero_observer()
    try:
        altura_sup = float(altura_superior_mm if altura_superior_mm is not None else DEFAULT_ALTURA_SUPERIOR_MM)
    except Exception:
        altura_sup = float(DEFAULT_ALTURA_SUPERIOR_MM)
    cota_inferior = float(altura_sup) - float(dims["alto_mm"])
    geom_version = int(TABLERO_GEOM_VERSION_CURRENT)

    master = _get_or_create_master_tablero(
        doc=doc,
        range_key=dims["rango"],
        main_breaker=bool(main_breaker_value),
        montaje=montaje_value,
        modo_visual=modo_visual,
        alto_mm=dims["alto_mm"],
        ancho_mm=dims["ancho_mm"],
        fondo_mm=dims["fondo_mm"],
        cota_inferior_mm=cota_inferior,
        lib_group=g_lib_tableros,
        hide_master=hide_master,
        show_workspace=mostrar_area_trabajo,
        geom_version=geom_version,
    )

    codigo_interno = _compose_codigo_interno(clase_equipo_value, dims["espacios"], main_breaker_value, montaje_value)
    link_name = _unique_name(doc, "Link_{}".format(codigo_interno))
    link = _create_tablero_link(doc, master, g_tableros, link_name)

    label = _build_link_label(codigo, nombre_tablero, codigo_interno)
    try:
        link.Label = label
    except Exception:
        pass

    _ensure_link_properties(
        obj=link,
        clase_equipo=clase_equipo_value,
        codigo=codigo,
        nombre_tablero=nombre_tablero,
        conectado_a=conectado_a,
        codigo_interno=codigo_interno,
        espacios=dims["espacios"],
        main_breaker=main_breaker_value,
        montaje=montaje_value,
        modo_visual=modo_visual,
        rango_key=dims["rango"],
        alto_mm=dims["alto_mm"],
        ancho_mm=dims["ancho_mm"],
        fondo_mm=dims["fondo_mm"],
        perfil_dimensiones=dims.get("perfil_dimensiones", perfil_dimensiones),
        configuracion_catalogo=dims.get("configuracion_catalogo", configuracion_catalogo),
        amperaje_nominal=dims.get("amp", amperaje_nominal),
        caja_eaton=dims.get("caja_eaton", caja_eaton),
        caja_modelo=dims.get("caja_modelo", dims["rango"]),
        show_workspace=mostrar_area_trabajo,
        geom_version=geom_version,
    )
    try:
        link.AlturaSuperiorInstalacion = altura_sup
    except Exception:
        pass
    try:
        link.CotaInferior = cota_inferior
        link.setEditorMode("CotaInferior", 1)
    except Exception:
        pass

    base_point = insertion_point if isinstance(insertion_point, App.Vector) else position
    if not isinstance(base_point, App.Vector):
        base_point = App.Vector(0.0, 0.0, 0.0)
    context_kind = _safe_text((insertion_context or {}).get("kind", "point")) or "point"
    placement = _placement_from_insertion_context(
        insertion_context,
        montaje=montaje_value,
        ancho_mm=dims["ancho_mm"],
        fondo_mm=dims["fondo_mm"],
        fallback_point=base_point,
    )
    try:
        link.Placement = placement
    except Exception:
        pass

    text_obj = None
    if create_text:
        text_obj = _create_instance_text(doc, g_tableros, link, _safe_text(codigo).strip() or codigo_interno)
        if text_obj is not None:
            try:
                link.EtiquetaTexto = text_obj
            except Exception:
                pass
            _sync_text_with_link(link)

    if recompute:
        try:
            doc.recompute()
        except Exception:
            pass

    log_i(
        "{} link creado: {} -> {} | rango={} | tipo={} | modo={} | perfil={} | caja={} | insercion={} | conectado_a={}".format(
            clase_equipo_value,
            _safe_text(getattr(link, "Name", "")),
            _safe_text(getattr(master, "Name", "")),
            dims["rango"],
            _tipo_tablero_token(main_breaker_value),
            modo_visual,
            dims.get("perfil_dimensiones", "Generico"),
            dims.get("caja_modelo", dims["rango"]),
            context_kind,
            _safe_text(conectado_a),
        )
    )
    return link


__all__ = [
    "MONTAJE_CHOICES",
    "LINK_MODE_CHOICES",
    "get_or_create_doc",
    "calcular_dimensiones",
    "buscar_step",
    "clear_step_cache",
    "pick_insertion_context_from_gui",
    "pick_insertion_point_from_gui",
    "sync_tablero_texts",
    "refresh_tablero_geometry",
    "insertar_tablero",
]
