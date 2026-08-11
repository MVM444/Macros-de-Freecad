# -*- coding: utf-8 -*-
"""Deteccion y geometria de tableros para ElectricCR.

Reemplaza la deteccion repetida de cara superior en las macros TP, TCOM y
tablero-tablero. No contiene reglas para codigos concretos de tablero.
Compatible con FreeCAD 1.1.3. Creado: 2026-08-08 18:01 CST.
Advertencia: excluir rutas que contienen la palabra tablero en su Tipo.
"""

import math
import unicodedata

import FreeCAD as App


EPS = 1.0e-7


def text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def normalized(value):
    raw = unicodedata.normalize("NFKD", text(value).strip().lower())
    return "".join(ch for ch in raw if not unicodedata.combining(ch) and ch.isalnum())


def is_group(obj):
    return obj is not None and hasattr(obj, "Group")


def is_library_object(obj):
    probe = normalized("{} {}".format(getattr(obj, "Name", ""), getattr(obj, "Label", "")))
    return any(token in probe for token in ("master", "template", "plantilla", "prototype", "libtableros"))


def is_panel(obj):
    if obj is None or is_group(obj) or is_library_object(obj):
        return False
    props = set(getattr(obj, "PropertiesList", []) or [])
    kind = normalized(
        "{} {}".format(getattr(obj, "ClaseEquipo", ""), getattr(obj, "Tipo", ""))
    )
    # Un alimentador entre tableros contiene la palabra "tablero", pero no es
    # equipo. Esta firma geometrica evita usar rutas existentes como destino.
    if any(marker in kind for marker in ("alimentador", "conexion", "ramal", "ruta")):
        return False
    if {"PuntoOrigen", "PuntoDestino", "RutaJSON"}.issubset(props):
        return False
    blob = normalized(
        "{} {} {} {} {}".format(
            getattr(obj, "ClaseEquipo", ""),
            getattr(obj, "Tipo", ""),
            getattr(obj, "ElementType", ""),
            getattr(obj, "Subtype", ""),
            getattr(obj, "IfcType", ""),
        )
    )
    return any(marker in blob for marker in ("tablero", "distributionboard", "panelboard"))


def panel_code(panel):
    for name in ("Codigo", "PanelId", "NombreTablero", "CodigoInterno"):
        value = text(getattr(panel, name, "")).strip()
        if value:
            return value.upper()
    return text(getattr(panel, "Label", getattr(panel, "Name", "TABLERO"))).strip()


def panel_tokens(panel):
    return [
        panel_code(panel),
        text(getattr(panel, "Name", "")),
        text(getattr(panel, "Label", "")),
        text(getattr(panel, "NombreTablero", "")),
        text(getattr(panel, "CodigoInterno", "")),
    ]


def find_panel_by_token(doc, token):
    wanted = normalized(token)
    if not wanted:
        return None
    exact = []
    contained = []
    for obj in list(doc.Objects):
        if not is_panel(obj):
            continue
        keys = [normalized(value) for value in panel_tokens(obj) if text(value)]
        if wanted in keys:
            exact.append(obj)
        elif any(wanted in key or key in wanted for key in keys if key):
            contained.append(obj)
    if len(exact) == 1:
        return exact[0]
    if not exact and len(contained) == 1:
        return contained[0]
    return None


def top_center(panel):
    try:
        bb = panel.Shape.BoundBox
        if not bool(getattr(bb, "IsVoid", False)):
            return App.Vector(float(bb.Center.x), float(bb.Center.y), float(bb.ZMax))
    except Exception:
        pass
    try:
        placement = panel.getGlobalPlacement()
    except Exception:
        placement = getattr(panel, "Placement", App.Placement())
    return App.Vector(placement.Base)


def _face_mid_parameter(face):
    umin, umax, vmin, vmax = face.ParameterRange
    return 0.5 * (umin + umax), 0.5 * (vmin + vmax)


def top_face(panel):
    """Devuelve (indice, cara, centro, normal) para la cara superior real."""
    try:
        shape = panel.Shape
        if shape is None or shape.isNull():
            raise ValueError("Shape vacio")
        top_z = float(shape.BoundBox.ZMax)
    except Exception as exc:
        raise RuntimeError("El tablero no tiene Shape utilizable: {}".format(exc))

    candidates = []
    for index, face in enumerate(list(getattr(shape, "Faces", []) or []), start=1):
        try:
            u, v = _face_mid_parameter(face)
            normal = face.normalAt(u, v)
            center = face.valueAt(u, v)
            bb = face.BoundBox
        except Exception:
            continue
        if float(normal.z) < 0.70:
            continue
        if abs(float(bb.ZMax) - float(bb.ZMin)) > 0.1:
            continue
        if abs(float(center.z) - top_z) > 0.5:
            continue
        candidates.append((float(face.Area), index, face, center, normal))
    if not candidates:
        raise RuntimeError("No se encontro una cara superior horizontal real en el tablero.")
    candidates.sort(key=lambda item: item[0], reverse=True)
    _area, index, face, center, normal = candidates[0]
    return index, face, App.Vector(center), App.Vector(normal)


def _axis_lengths(face):
    umin, umax, vmin, vmax = face.ParameterRange
    umid = 0.5 * (umin + umax)
    vmid = 0.5 * (vmin + vmax)
    try:
        u_length = face.valueAt(umin, vmid).distanceToPoint(face.valueAt(umax, vmid))
        v_length = face.valueAt(umid, vmin).distanceToPoint(face.valueAt(umid, vmax))
    except Exception:
        u_length = v_length = 1.0
    return max(float(u_length), EPS), max(float(v_length), EPS)


def distributed_top_points(panel, count):
    """Distribuye ``count`` puntos dentro de la cara superior real.

    La malla se deriva del numero real de conexiones y de la proporcion fisica
    de la cara. No existen limites codificados para TP, TCOM u otro tablero.
    """
    count = max(1, int(count or 1))
    try:
        face_index, face, _center, _normal = top_face(panel)
    except Exception:
        center = top_center(panel)
        return [(App.Vector(center), 0) for _index in range(count)]

    umin, umax, vmin, vmax = face.ParameterRange
    u_length, v_length = _axis_lengths(face)
    columns = max(1, int(math.ceil(math.sqrt(float(count) * u_length / v_length))))
    rows = max(1, int(math.ceil(float(count) / float(columns))))
    while columns > 1 and (columns - 1) * rows >= count:
        columns -= 1

    points = []
    for index in range(count):
        row = index // columns
        column = index % columns
        items_this_row = min(columns, count - row * columns)
        u_fraction = float(column + 1) / float(items_this_row + 1)
        v_fraction = float(row + 1) / float(rows + 1)
        u = umin + u_fraction * (umax - umin)
        v = vmin + v_fraction * (vmax - vmin)
        point = App.Vector(face.valueAt(u, v))
        try:
            import Part

            distance = float(face.distToShape(Part.Vertex(point))[0])
        except Exception:
            distance = 0.0
        if distance > 0.01:
            raise RuntimeError("El punto distribuido no pertenece a la cara superior real.")
        points.append((point, int(face_index)))
    return points
