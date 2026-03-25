# -*- coding: utf-8 -*-
"""
electriccr.features.caja_emt_octogonal

Caja EMT octogonal basada en STEP:
- Reusa un master oculto en libreria.
- Inserta instancias ligeras App::Link.
- Publica 9 puertos EMT en PuertosJSON (coordenadas locales del objeto).
"""

import json
import math
from pathlib import Path

import FreeCAD as App
import Part


GUI_UP = False
try:
    import FreeCADGui as Gui  # noqa: F401
    GUI_UP = True
except Exception:
    GUI_UP = False


BOX_KEY = "EMT_Octagon_Box"
BOX_CATEGORY = "Caja"
CONDUIT_TYPE = "EMT"
MASTER_NAME = "Master_EMT_Octagon_Box"
MASTER_LABEL = "Master EMT Octagon Box"
STEP_FILENAME = "Caja_octogonal.step"
DEFAULT_DIAMETER = 22.2

SIDE_PORT_TARGETS = {
    "East": 0.0,
    "NorthEast": 45.0,
    "North": 90.0,
    "NorthWest": 135.0,
    "West": 180.0,
    "SouthWest": -135.0,
    "South": -90.0,
    "SouthEast": -45.0,
}

PORT_OUTPUT_ORDER = [
    "North",
    "South",
    "East",
    "West",
    "NorthEast",
    "NorthWest",
    "SouthEast",
    "SouthWest",
    "Bottom",
]


def _ts():
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_i(msg):
    App.Console.PrintMessage(f"[{_ts()}][CAJA_EMT][INFO] {msg}\n")


def log_w(msg):
    App.Console.PrintWarning(f"[{_ts()}][CAJA_EMT][WARN] {msg}\n")


def log_e(msg):
    App.Console.PrintError(f"[{_ts()}][CAJA_EMT][ERROR] {msg}\n")


def _safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _safe_name_token(value, fallback="Caja_EMT_Octogonal"):
    txt = _safe_text(value).strip()
    if not txt:
        return fallback
    out = []
    for ch in txt:
        out.append(ch if (ch.isalnum() or ch == "_") else "_")
    token = "".join(out).strip("_")
    while "__" in token:
        token = token.replace("__", "_")
    return token or fallback


def _vlen(vec):
    return math.sqrt((vec.x * vec.x) + (vec.y * vec.y) + (vec.z * vec.z))


def _normalize(vec):
    n = _vlen(vec)
    if n <= 1e-12:
        return App.Vector(0.0, 0.0, 0.0)
    return App.Vector(vec.x / n, vec.y / n, vec.z / n)


def _dot(a, b):
    return (a.x * b.x) + (a.y * b.y) + (a.z * b.z)


def _angle_deg(vec):
    return math.degrees(math.atan2(vec.y, vec.x))


def _circular_distance_deg(a, b):
    d = abs(a - b) % 360.0
    return 360.0 - d if d > 180.0 else d


def _ensure_property(obj, ptype, pname, pgroup, pdesc):
    try:
        if pname not in obj.PropertiesList:
            obj.addProperty(ptype, pname, pgroup, pdesc)
    except Exception:
        pass


def _ensure_common_properties(obj, model_path=""):
    _ensure_property(obj, "App::PropertyString", "Tipo", "ElectricCR", "Tipo logico")
    _ensure_property(obj, "App::PropertyString", "Categoria", "ElectricCR", "Categoria logica")
    _ensure_property(obj, "App::PropertyString", "ConduitType", "ElectricCR", "Tipo de tuberia")
    _ensure_property(obj, "App::PropertyFloat", "DiametroEMT", "Puertos", "Diametro EMT en mm")
    _ensure_property(obj, "App::PropertyString", "PuertosJSON", "Puertos", "Puertos EMT (local)")
    _ensure_property(obj, "App::PropertyString", "ModeloSTEP", "Registro", "Archivo STEP fuente")

    try:
        if not _safe_text(getattr(obj, "Tipo", "")):
            obj.Tipo = BOX_KEY
    except Exception:
        pass
    try:
        if not _safe_text(getattr(obj, "Categoria", "")):
            obj.Categoria = BOX_CATEGORY
    except Exception:
        pass
    try:
        if not _safe_text(getattr(obj, "ConduitType", "")):
            obj.ConduitType = CONDUIT_TYPE
    except Exception:
        pass
    try:
        current = float(getattr(obj, "DiametroEMT", 0.0) or 0.0)
        if current <= 0.0:
            obj.DiametroEMT = float(DEFAULT_DIAMETER)
    except Exception:
        pass
    try:
        if model_path and not _safe_text(getattr(obj, "ModeloSTEP", "")):
            obj.ModeloSTEP = model_path
    except Exception:
        pass


def _candidate_step_paths():
    cands = []
    here = Path(__file__).resolve()

    for anc in [here.parent, *here.parents[:8]]:
        if anc is None:
            continue
        p = anc / "Resources" / "prototypes" / "3d" / STEP_FILENAME
        if p.exists():
            try:
                cands.append(p.resolve())
            except Exception:
                cands.append(p)

    try:
        user_dir = Path(App.getUserAppDataDir())
    except Exception:
        user_dir = Path.home() / "AppData" / "Roaming" / "FreeCAD"

    for folder_name in ("Macro", "Macros"):
        p = user_dir / folder_name / "Resources" / "prototypes" / "3d" / STEP_FILENAME
        if p.exists():
            try:
                cands.append(p.resolve())
            except Exception:
                cands.append(p)

    uniq = []
    seen = set()
    for p in cands:
        s = str(p)
        if s not in seen:
            seen.add(s)
            uniq.append(p)
    return uniq


def resolve_step_path():
    cands = _candidate_step_paths()
    if cands:
        return str(cands[0])
    raise FileNotFoundError(
        f"No se encontro {STEP_FILENAME} en Resources/prototypes/3d (ni en ruta de usuario)."
    )


def _read_step_shape(path):
    shape = Part.read(path)
    if shape is None or shape.isNull():
        raise ValueError(f"Shape nula al leer STEP: {path}")
    return shape


def _ensure_group(doc, name, parent=None):
    if doc is None:
        return None
    grp = doc.getObject(name)
    if grp is None:
        try:
            grp = doc.addObject("App::DocumentObjectGroup", name)
        except Exception:
            return doc.getObject(name)
    if parent is not None and grp is not None:
        try:
            if grp not in (parent.Group or []):
                parent.addObject(grp)
        except Exception:
            pass
    return grp


def _add_to_group(group, obj):
    if group is None or obj is None:
        return
    try:
        if obj not in (group.Group or []):
            group.addObject(obj)
    except Exception:
        pass


def _ensure_master_group(doc):
    g_elec = _ensure_group(doc, "electrico", parent=None)
    g_lib = _ensure_group(doc, "_lib", parent=g_elec)
    g_boxes_lib = _ensure_group(doc, "_lib_cajas", parent=(g_lib or g_elec))
    return g_boxes_lib


def _ensure_boxes_group(doc):
    g_elec = _ensure_group(doc, "electrico", parent=None)
    return _ensure_group(doc, "Cajas", parent=g_elec)


def _face_normal(face):
    normal = None
    try:
        u0, u1, v0, v1 = face.ParameterRange
        u = 0.5 * (u0 + u1)
        v = 0.5 * (v0 + v1)
        normal = face.normalAt(u, v)
    except Exception:
        normal = None

    if normal is None:
        try:
            surf = getattr(face, "Surface", None)
            axis = getattr(surf, "Axis", None)
            if axis is not None:
                normal = App.Vector(axis.x, axis.y, axis.z)
        except Exception:
            normal = None

    if normal is None:
        return None
    return _normalize(normal)


def _orient_outward(normal, center, ref_center):
    vec = App.Vector(center.x - ref_center.x, center.y - ref_center.y, center.z - ref_center.z)
    if _vlen(vec) <= 1e-9:
        return normal
    if _dot(normal, vec) < 0.0:
        return App.Vector(-normal.x, -normal.y, -normal.z)
    return normal


def _extract_face_infos(shape):
    infos = []
    if shape is None or shape.isNull():
        return infos

    bb = shape.BoundBox
    bb_center = App.Vector(
        0.5 * (bb.XMin + bb.XMax),
        0.5 * (bb.YMin + bb.YMax),
        0.5 * (bb.ZMin + bb.ZMax),
    )

    for face in shape.Faces:
        try:
            center = face.CenterOfMass
        except Exception:
            continue
        normal = _face_normal(face)
        if normal is None:
            continue
        normal = _orient_outward(normal, center, bb_center)
        infos.append(
            {
                "face": face,
                "center": center,
                "normal": normal,
                "angle": _angle_deg(normal),
                "area": float(getattr(face, "Area", 0.0) or 0.0),
                "radial": math.hypot(center.x, center.y),
            }
        )
    return infos


def _select_lateral_pool(face_infos):
    lateral = [fi for fi in face_infos if abs(fi["normal"].z) < 0.75]
    if not lateral:
        return []

    outward = []
    for fi in lateral:
        c = fi["center"]
        n = fi["normal"]
        if (c.x * n.x + c.y * n.y) > 0.0:
            outward.append(fi)

    pool = outward if len(outward) >= 8 else lateral
    pool.sort(key=lambda fi: (fi["radial"], fi["area"]), reverse=True)
    return pool[:24]


def _assign_side_ports(face_infos):
    pool = _select_lateral_pool(face_infos)
    if not pool:
        return {}

    # Greedy assignment by nearest target angle; larger radial/area wins tie.
    remaining = list(pool)
    assigned = {}
    for label, target in SIDE_PORT_TARGETS.items():
        if not remaining:
            break
        best = min(
            remaining,
            key=lambda fi: (
                _circular_distance_deg(fi["angle"], target),
                -fi["radial"],
                -fi["area"],
            ),
        )
        assigned[label] = best
        remaining.remove(best)

    # Fill missing labels only if geometry was unusual.
    if len(assigned) < len(SIDE_PORT_TARGETS):
        fallback = pool[0]
        for label in SIDE_PORT_TARGETS.keys():
            if label not in assigned:
                assigned[label] = fallback
                log_w(f"Puerto lateral '{label}' en fallback por geometria no estandar.")

    return assigned


def _select_bottom_face(face_infos):
    horizontal = [fi for fi in face_infos if abs(fi["normal"].z) >= 0.75]
    if not horizontal:
        return None
    horizontal.sort(key=lambda fi: (fi["center"].z, -fi["area"]))
    return horizontal[0]


def _pack_port(name, center, normal, diameter):
    return {
        "name": name,
        "position": [float(center.x), float(center.y), float(center.z)],
        "direction": [float(normal.x), float(normal.y), float(normal.z)],
        "diameter": float(diameter),
        "conduitType": CONDUIT_TYPE,
    }


def build_ports_from_shape(shape, diameter):
    if shape is None or shape.isNull():
        return []

    face_infos = _extract_face_infos(shape)
    side_map = _assign_side_ports(face_infos)
    bottom = _select_bottom_face(face_infos)

    ports = {}
    for name, info in side_map.items():
        ports[name] = _pack_port(name, info["center"], info["normal"], diameter)

    if bottom is not None:
        bn = bottom["normal"]
        if bn.z > 0.0:
            bn = App.Vector(-bn.x, -bn.y, -bn.z)
        ports["Bottom"] = _pack_port("Bottom", bottom["center"], bn, diameter)
    else:
        bb = shape.BoundBox
        fallback_center = App.Vector(
            0.5 * (bb.XMin + bb.XMax),
            0.5 * (bb.YMin + bb.YMax),
            bb.ZMin,
        )
        ports["Bottom"] = _pack_port("Bottom", fallback_center, App.Vector(0.0, 0.0, -1.0), diameter)
        log_w("No se detecto cara inferior plana; se uso fallback en BoundBox.")

    ordered = []
    for name in PORT_OUTPUT_ORDER:
        port = ports.get(name)
        if port is not None:
            ordered.append(port)
    return ordered


def _ports_to_json(ports):
    try:
        return json.dumps(ports, ensure_ascii=True, separators=(",", ":"))
    except Exception:
        return "[]"


def _ports_from_json(raw):
    try:
        data = json.loads(_safe_text(raw))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _with_diameter(ports, diameter):
    out = []
    for p in ports:
        if not isinstance(p, dict):
            continue
        item = dict(p)
        item["diameter"] = float(diameter)
        item["conduitType"] = CONDUIT_TYPE
        out.append(item)
    return out


def _update_ports_property(obj, shape, diameter):
    ports = build_ports_from_shape(shape, diameter)
    try:
        obj.PuertosJSON = _ports_to_json(ports)
    except Exception:
        pass
    return ports


def _build_ports_for_link(master, diameter):
    ports = _ports_from_json(getattr(master, "PuertosJSON", ""))
    if not ports:
        ports = build_ports_from_shape(master.Shape, diameter)
    return _with_diameter(ports, diameter)


def _hide_object(obj):
    if not GUI_UP or obj is None or not hasattr(obj, "ViewObject"):
        return
    try:
        obj.ViewObject.Visibility = False
    except Exception:
        pass


def _get_or_create_master(doc, step_path, hide_master=True):
    master = doc.getObject(MASTER_NAME)
    if master is not None and master.TypeId != "Part::Feature":
        log_w(f"Existe objeto '{MASTER_NAME}' pero no es Part::Feature. Se creara otro master.")
        master = None

    if master is None:
        try:
            master = doc.addObject("Part::Feature", MASTER_NAME)
        except Exception:
            master = doc.addObject("Part::Feature")
        try:
            master.Label = MASTER_LABEL
        except Exception:
            pass

    _ensure_common_properties(master, step_path)

    try:
        if not hasattr(master, "Shape") or master.Shape.isNull():
            master.Shape = _read_step_shape(step_path)
        master.Placement = App.Placement()
    except Exception as ex:
        raise RuntimeError(f"No se pudo cargar shape master desde STEP: {ex}") from ex

    try:
        diam = float(getattr(master, "DiametroEMT", DEFAULT_DIAMETER) or DEFAULT_DIAMETER)
    except Exception:
        diam = float(DEFAULT_DIAMETER)
    _update_ports_property(master, master.Shape, diam)

    g_lib_boxes = _ensure_master_group(doc)
    _add_to_group(g_lib_boxes, master)

    if hide_master:
        _hide_object(master)

    return master


def actualizar_puertos_caja_emt(obj, diametro_emt=None, recompute=True):
    """
    Recalcula PuertosJSON para una caja EMT (master o link).
    """
    if obj is None:
        raise ValueError("obj no puede ser None")

    try:
        diameter = float(diametro_emt if diametro_emt is not None else getattr(obj, "DiametroEMT", DEFAULT_DIAMETER))
    except Exception:
        diameter = float(DEFAULT_DIAMETER)

    shape_source = None
    if getattr(obj, "TypeId", "") == "App::Link":
        linked = getattr(obj, "LinkedObject", None)
        if linked is None or not hasattr(linked, "Shape") or linked.Shape.isNull():
            raise RuntimeError("Link sin LinkedObject valido para recalcular puertos.")
        shape_source = linked.Shape
    else:
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            raise RuntimeError("Objeto sin Shape valido para recalcular puertos.")
        shape_source = obj.Shape

    _ensure_common_properties(obj, _safe_text(getattr(obj, "ModeloSTEP", "")))
    try:
        obj.DiametroEMT = diameter
    except Exception:
        pass
    ports = _update_ports_property(obj, shape_source, diameter)

    if recompute:
        try:
            obj.Document.recompute()
        except Exception:
            pass
    return ports


def insertar_caja_emt_octogonal_link(
    doc=None,
    name_prefix="Caja EMT Octogonal",
    placement=None,
    diametro_emt=DEFAULT_DIAMETER,
    recompute=True,
    hide_master=True,
):
    """
    Inserta una caja EMT octogonal como App::Link y retorna el objeto link.
    """
    doc = doc or App.ActiveDocument or App.newDocument("Electrico")
    step_path = resolve_step_path()
    master = _get_or_create_master(doc, step_path=step_path, hide_master=hide_master)

    internal_name = f"Link_{_safe_name_token(name_prefix)}"
    try:
        link = doc.addObject("App::Link", internal_name)
    except Exception:
        link = doc.addObject("App::Link")

    link.LinkedObject = master
    try:
        link.LinkTransform = False
    except Exception:
        pass
    if placement is not None:
        try:
            link.Placement = placement
        except Exception:
            pass
    try:
        link.Label = _safe_text(name_prefix) or "Caja EMT Octogonal"
    except Exception:
        pass

    _ensure_common_properties(link, step_path)
    try:
        link.Tipo = BOX_KEY
        link.Categoria = BOX_CATEGORY
        link.ConduitType = CONDUIT_TYPE
    except Exception:
        pass

    try:
        diameter = float(diametro_emt or DEFAULT_DIAMETER)
    except Exception:
        diameter = float(DEFAULT_DIAMETER)
    try:
        link.DiametroEMT = diameter
    except Exception:
        pass

    ports = _build_ports_for_link(master, diameter)
    try:
        link.PuertosJSON = _ports_to_json(ports)
    except Exception:
        pass

    g_boxes = _ensure_boxes_group(doc)
    _add_to_group(g_boxes, link)

    if recompute:
        try:
            doc.recompute()
        except Exception:
            pass

    log_i(
        "Caja EMT octogonal insertada: "
        f"{link.Name} | puertos={len(ports)} | diametro={diameter:.2f} mm"
    )
    return link


def crear_caja_emt_octogonal_master(doc=None, hide_master=True):
    """
    Crea o devuelve el master Part::Feature de la caja.
    """
    doc = doc or App.ActiveDocument or App.newDocument("Electrico")
    step_path = resolve_step_path()
    return _get_or_create_master(doc, step_path=step_path, hide_master=hide_master)


__all__ = [
    "BOX_KEY",
    "CONDUIT_TYPE",
    "DEFAULT_DIAMETER",
    "resolve_step_path",
    "build_ports_from_shape",
    "crear_caja_emt_octogonal_master",
    "insertar_caja_emt_octogonal_link",
    "actualizar_puertos_caja_emt",
]
