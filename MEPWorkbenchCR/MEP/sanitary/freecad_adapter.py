"""
Nombre: freecad_adapter.py
Proposito: Adaptador experimental entre el nucleo sanitario y objetos de FreeCAD.
Funcionamiento: Consume geometry_spec JSON-compatible; dry_run no modifica documentos. En modo escritura crea una previsualizacion 3D trazable.
Modificaciones futuras: Sustituir geometria provisional por objetos Part::FeaturePython parametricos 2D/3D y puertos tecnicos despues de validar en FreeCAD real.
Version: 0.2.0
Fecha: 2026-08-26

IMPORTANTE: este modulo no importa FreeCADGui ni Qt. La geometria de FAFA y zanjas
es una previsualizacion cuando no se han definido emplazamientos constructivos finales.
"""


def preview_plan(system_result, origin_mm=(0.0, 0.0, 0.0)):
    """Devuelve operaciones geometricas sin tocar FreeCAD."""
    spec = system_result.get("geometry_spec", {})
    x0, y0, z0 = origin_mm
    ops = []

    septic = spec.get("septic_tank", {})
    if all(septic.get(k) for k in ("length_m", "width_m", "total_internal_height_m")):
        ops.append({
            "name": "MEP_SepticTank",
            "kind": "box_preview",
            "origin_mm": [x0, y0, z0],
            "size_mm": [
                septic["length_m"] * 1000.0,
                septic["width_m"] * 1000.0,
                septic["total_internal_height_m"] * 1000.0,
            ],
            "provisional": False,
        })
        x0 += septic["length_m"] * 1000.0 + 1000.0

    fafa = spec.get("fafa", {})
    area = fafa.get("required_plan_area_m2")
    media_h = fafa.get("media_height_m")
    if area and media_h:
        # Solo preview: aspecto 2:1 para visualizar el area requerida; no es dimension final.
        width_m = (area / 2.0) ** 0.5
        length_m = 2.0 * width_m
        ops.append({
            "name": "MEP_FAFA",
            "kind": "box_preview",
            "origin_mm": [x0, y0, z0],
            "size_mm": [length_m * 1000.0, width_m * 1000.0, media_h * 1000.0],
            "provisional": True,
            "note": "Aspecto 2:1 usado solo para previsualizacion; requiere geometria seleccionada.",
        })
        x0 += length_m * 1000.0 + 1000.0

    field = spec.get("infiltration_field", {})
    width_m = field.get("width_m") or 0.5
    depth_m = field.get("gravel_depth_m") or 0.3

    site_layout = system_result.get("site_layout", {})
    layout_data = site_layout.get("data", {}) if site_layout.get("ok") else {}
    layout_trenches = layout_data.get("trenches") or []
    if layout_trenches:
        # Coordinates returned by layout.py are neutral local meters. Shift them
        # after the treatment units while preserving their calculated positions.
        for trench in layout_trenches:
            sx, sy = trench["start_m"]
            ex, _ = trench["end_m"]
            ops.append({
                "name": f"MEP_InfiltrationTrench_{trench['index']:02d}",
                "kind": "box_preview",
                "origin_mm": [x0 + sx * 1000.0, y0 + sy * 1000.0, z0 - depth_m * 1000.0],
                "size_mm": [(ex - sx) * 1000.0, width_m * 1000.0, depth_m * 1000.0],
                "provisional": True,
                "note": "Posicion calculada dentro del rectangulo disponible; falta validar poligono/obstaculos reales.",
            })
    else:
        count = int(field.get("trench_count") or 0)
        length_m = field.get("equal_trench_length_m") or 0.0
        spacing_m = field.get("center_spacing_m") or 1.8
        for idx in range(count):
            ops.append({
                "name": f"MEP_InfiltrationTrench_{idx + 1:02d}",
                "kind": "box_preview",
                "origin_mm": [x0, y0 + idx * spacing_m * 1000.0, z0 - depth_m * 1000.0],
                "size_mm": [length_m * 1000.0, width_m * 1000.0, depth_m * 1000.0],
                "provisional": True,
                "note": "Ubicacion paralela preliminar; debe ajustarse al area real del terreno.",
            })
    return ops


def create_preview_objects(doc, system_result, origin_mm=(0.0, 0.0, 0.0), dry_run=True):
    """Crea una previsualizacion. Por defecto es lectura/dry-run."""
    ops = preview_plan(system_result, origin_mm=origin_mm)
    if dry_run:
        return {"dry_run": True, "operations": ops}

    import FreeCAD as App
    import Part

    if doc is None:
        raise ValueError("Se requiere un documento FreeCAD")

    doc.openTransaction("MEP Sanitary Preview")
    created = []
    try:
        group = doc.getObject("MEP_Sanitary_Preview")
        if group is None:
            group = doc.addObject("App::DocumentObjectGroup", "MEP_Sanitary_Preview")
            group.Label = "MEP Sanitary Preview"
        for op in ops:
            obj = doc.getObject(op["name"])
            if obj is None:
                obj = doc.addObject("Part::Feature", op["name"])
                group.addObject(obj)
            sx, sy, sz = op["size_mm"]
            ox, oy, oz = op["origin_mm"]
            obj.Shape = Part.makeBox(sx, sy, sz, App.Vector(ox, oy, oz))
            if "MEPProvisional" not in obj.PropertiesList:
                obj.addProperty("App::PropertyBool", "MEPProvisional", "MEP Sanitary")
            obj.MEPProvisional = bool(op.get("provisional"))
            if "MEPSource" not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", "MEPSource", "MEP Sanitary")
            obj.MEPSource = "MEP.sanitary.system.geometry_spec"
            created.append(obj.Name)
        doc.recompute()
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    return {"dry_run": False, "created": created, "operations": ops}
