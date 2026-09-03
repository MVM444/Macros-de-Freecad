"""
Nombre: documentation.py
Proposito: Representacion documental 2D neutral del sistema sanitario.
Funcionamiento: Convierte el resultado de calculo en primitivas de planta y seccion
  JSON-compatible y puede renderizarlas a SVG sin FreeCADGui ni Qt.
Modificaciones futuras: Adaptar estas primitivas a TechDraw/Draft y DXF sin cambiar
  el contrato del nucleo documental.
Version: 0.1.0
Fecha: 2026-08-26
"""
from html import escape
from .freecad_adapter import preview_plan


def _rect(x, y, w, h, label="", category=""):
    return {"kind": "rect", "x": x, "y": y, "width": w, "height": h, "label": label, "category": category}


def _line(x1, y1, x2, y2, label="", category=""):
    return {"kind": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": label, "category": category}


def _text(x, y, text, category="annotation"):
    return {"kind": "text", "x": x, "y": y, "text": str(text), "category": category}


def build_plan_documentation(system_result):
    """Planta esquematica en metros, derivada del mismo geometry_spec/site_layout."""
    primitives = []
    for op in preview_plan(system_result, origin_mm=(0, 0, 0)):
        ox, oy, _ = op["origin_mm"]
        sx, sy, _ = op["size_mm"]
        x, y, w, h = ox / 1000.0, oy / 1000.0, sx / 1000.0, sy / 1000.0
        primitives.append(_rect(x, y, w, h, op["name"], "component"))
        primitives.append(_text(x + w / 2.0, y + h / 2.0, op["name"]))
    return {
        "view": "PLAN",
        "units": "m",
        "project": system_result.get("project", ""),
        "primitives": primitives,
        "status": "DOCUMENTARY_PREVIEW",
    }


def build_section_documentation(system_result):
    """Seccion esquematica: tanque, FAFA y zanja con nivel freatico si existe."""
    spec = system_result.get("geometry_spec", {})
    primitives = []
    cursor = 0.0
    gap = 1.0

    septic = spec.get("septic_tank", {})
    L = septic.get("length_m") or 0.0
    Hliq = septic.get("liquid_depth_m") or 0.0
    Htot = septic.get("total_internal_height_m") or 0.0
    if L > 0 and Htot > 0:
        primitives.append(_rect(cursor, 0.0, L, Htot, "Tanque septico", "septic"))
        if Hliq > 0:
            primitives.append(_line(cursor, Htot - Hliq, cursor + L, Htot - Hliq, "Nivel liquido", "waterline"))
        primitives.append(_text(cursor + L/2.0, Htot/2.0, "TANQUE SEPTICO"))
        cursor += L + gap

    fafa = spec.get("fafa", {})
    area = fafa.get("required_plan_area_m2") or 0.0
    media_h = fafa.get("media_height_m") or 0.0
    if area > 0 and media_h > 0:
        # Mismo criterio de preview del adaptador: 2:1, explicitamente no constructivo.
        width = (area / 2.0) ** 0.5
        length = 2.0 * width
        primitives.append(_rect(cursor, 0.0, length, media_h, "FAFA", "fafa"))
        primitives.append(_text(cursor + length/2.0, media_h/2.0, "MEDIO FILTRANTE"))
        cursor += length + gap

    field = spec.get("infiltration_field", {})
    trench_w = field.get("width_m") or 0.0
    trench_d = field.get("gravel_depth_m") or 0.0
    if trench_w > 0 and trench_d > 0:
        primitives.append(_rect(cursor, -trench_d, trench_w, trench_d, "Zanja infiltracion", "infiltration"))
        primitives.append(_line(cursor, 0.0, cursor + trench_w, 0.0, "Terreno", "ground"))
        primitives.append(_text(cursor + trench_w/2.0, -trench_d/2.0, "DRENAJE"))
        inf_data = system_result.get("infiltration", {}).get("data", {})
        clearance = inf_data.get("groundwater_clearance_m")
        if clearance is not None and clearance >= 0:
            gw_y = -trench_d - float(clearance)
            primitives.append(_line(cursor - 0.5, gw_y, cursor + trench_w + 0.5, gw_y, "Nivel freatico", "groundwater"))
            primitives.append(_text(cursor + trench_w/2.0, gw_y, "NIVEL FREATICO"))

    return {
        "view": "SECTION",
        "units": "m",
        "project": system_result.get("project", ""),
        "primitives": primitives,
        "status": "DOCUMENTARY_PREVIEW",
        "notes": ["La geometria FAFA 2:1 es solo documental preliminar hasta seleccionar dimensiones constructivas."],
    }


def _bounds(primitives):
    xs, ys = [0.0], [0.0]
    for p in primitives:
        if p["kind"] == "rect":
            xs += [p["x"], p["x"] + p["width"]]
            ys += [p["y"], p["y"] + p["height"]]
        elif p["kind"] == "line":
            xs += [p["x1"], p["x2"]]
            ys += [p["y1"], p["y2"]]
        elif p["kind"] == "text":
            xs.append(p["x"]); ys.append(p["y"])
    return min(xs), min(ys), max(xs), max(ys)


def render_svg(documentation, scale_px_per_m=60.0, margin_px=30.0):
    """Render SVG simple. No usa colores especificos para mantener salida neutra."""
    prims = documentation.get("primitives", [])
    minx, miny, maxx, maxy = _bounds(prims)
    width = max(1.0, (maxx - minx) * scale_px_per_m + 2 * margin_px)
    height = max(1.0, (maxy - miny) * scale_px_per_m + 2 * margin_px)

    def X(x): return margin_px + (x - minx) * scale_px_per_m
    def Y(y): return height - margin_px - (y - miny) * scale_px_per_m

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.2f} {height:.2f}">']
    out.append('<g fill="none" stroke="currentColor" stroke-width="1">')
    for p in prims:
        if p["kind"] == "rect":
            out.append(f'<rect x="{X(p["x"]):.2f}" y="{Y(p["y"] + p["height"]):.2f}" width="{p["width"]*scale_px_per_m:.2f}" height="{p["height"]*scale_px_per_m:.2f}"/>')
        elif p["kind"] == "line":
            out.append(f'<line x1="{X(p["x1"]):.2f}" y1="{Y(p["y1"]):.2f}" x2="{X(p["x2"]):.2f}" y2="{Y(p["y2"]):.2f}"/>')
    out.append('</g>')
    out.append('<g fill="currentColor" stroke="none" font-family="sans-serif" font-size="11" text-anchor="middle">')
    for p in prims:
        if p["kind"] == "text":
            out.append(f'<text x="{X(p["x"]):.2f}" y="{Y(p["y"]):.2f}">{escape(p["text"])}</text>')
    out.append('</g></svg>')
    return "\n".join(out)
