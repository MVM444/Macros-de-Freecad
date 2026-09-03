"""BIM floor and terrain helpers for FacilArquitecturaWB.

Descripcion: crea una losa BIM y un sitio/terreno desde sketches arquitectonicos.
Funcion principal: integrar Site -> Building -> Level -> Slab y evitar terreno superpuesto bajo la losa.
Mantenimiento: conservar Arch.makeStructure/Arch.makeSite y las dependencias nativas; no duplicar contencion.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-09-01 15:15 America/Costa_Rica.
Version: 0.3.0.
"""

from __future__ import annotations

import math
import random

import FreeCAD
import Part

from .command_errors import UserFacingError
from .bim_structure_utils import add_to_level, is_building, is_level
from .project_structure import msg, set_prop, warn

try:
    import Arch
except Exception:  # pragma: no cover - depende del runtime de FreeCAD
    Arch = None


GENERATED_BY_SITE_FLOOR = "FA_CreateSiteFloorBIM"
PLAN_KEYWORDS = ("muro", "pared", "wall", "puerta", "door", "ventana", "window")
EXCLUDED_KEYWORDS = ("terreno", "losa_piso", "losa piso", "ejes", "axis")
MIN_FLOOR_SIZE_MM = 500.0


def collect_plan_sketches(doc, selection=None):
    """Collect wall, door and window sketches from a selection or the document."""
    selected = list(selection or [])
    pending = selected if selected else list(getattr(doc, "Objects", []) or [])
    result = []
    seen = set()
    while pending:
        obj = pending.pop(0)
        name = str(getattr(obj, "Name", "") or "")
        identity = name or str(id(obj))
        if identity in seen:
            continue
        seen.add(identity)

        if _is_plan_source_sketch(obj):
            result.append(obj)
            continue

        if selected:
            for attr in ("Group", "Objects"):
                try:
                    pending.extend(list(getattr(obj, attr, []) or []))
                except Exception:
                    pass
    return result


def combined_sketch_bounds(sketches):
    """Return the XY bounds of all usable source sketches."""
    boxes = []
    for sketch in sketches or []:
        shape = getattr(sketch, "Shape", None)
        bbox = getattr(shape, "BoundBox", None)
        if bbox is None:
            continue
        try:
            values = (
                float(bbox.XMin),
                float(bbox.YMin),
                float(bbox.XMax),
                float(bbox.YMax),
            )
        except Exception:
            continue
        if all(math.isfinite(value) for value in values):
            boxes.append(values)
    if not boxes:
        raise UserFacingError("Los sketches seleccionados no tienen geometria util para definir el piso.")

    bounds = (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )
    if bounds[2] - bounds[0] < MIN_FLOOR_SIZE_MM or bounds[3] - bounds[1] < MIN_FLOOR_SIZE_MM:
        raise UserFacingError(
            "La envolvente de los sketches es demasiado pequena. Verifique que el dibujo este en milimetros."
        )
    return bounds


def create_site_floor_from_sketches(doc, bim_group, sketches, options, building=None, level=None):
    """Create a dynamic footprint, BIM slab and Site, preferring native spatial containment."""
    if Arch is None or not hasattr(Arch, "makeStructure") or not hasattr(Arch, "makeSite"):
        raise UserFacingError("Arch/BIM no esta disponible. Active o instale el Workbench BIM.")
    if building is not None and not is_building(building):
        raise UserFacingError("El contenedor de edificio no es un Building BIM nativo.")
    if level is not None and not is_level(level):
        raise UserFacingError("El contenedor de piso no es un Building Storey BIM nativo.")

    usable = _unique_plan_sketches(sketches)
    combined_sketch_bounds(usable)
    if bool(options.get("replace_previous", True)):
        removed = remove_previous_site_floor(doc)
        if removed:
            msg("Piso y terreno anteriores reemplazados: %d objetos" % removed)

    footprint = doc.addObject("Part::FeaturePython", "FA_FloorFootprint")
    footprint.Label = "Huella de piso desde sketches"
    FloorFootprintProxy(footprint)
    footprint.Sources = usable
    footprint.Overhang = float(options.get("floor_overhang_mm", 100.0))
    footprint.TopZ = float(options.get("floor_top_z_mm", 0.0))
    _tag_generated(footprint, "floor_footprint")
    # La huella es Base de la losa. En el flujo BIM nativo no se agrega tambien
    # al Level para evitar una segunda aparicion visual en el arbol.
    if level is None and bim_group is not None:
        try:
            bim_group.addObject(footprint)
        except Exception:
            pass
    doc.recompute()
    if getattr(footprint, "Shape", None) is None or footprint.Shape.isNull():
        raise UserFacingError("No fue posible construir la huella del piso desde los sketches.")

    slab = _make_bim_slab(footprint, float(options.get("floor_thickness_mm", 150.0)))
    slab.Label = "Losa BIM desde sketches"
    _tag_generated(slab, "floor_slab")
    _set_source_name_metadata(
        slab,
        usable,
        "Sketches usados para calcular la huella; la dependencia geometrica real reside en la Base",
    )
    if level is not None:
        add_to_level(level, slab)
    elif bim_group is not None:
        try:
            bim_group.addObject(slab)
        except Exception:
            pass

    terrain = None
    if bool(options.get("create_test_terrain", True)):
        terrain = doc.addObject("Part::FeaturePython", "FA_TestTerrain")
        terrain.Label = "Terreno irregular de prueba"
        TestTerrainProxy(terrain)
        terrain.Footprint = footprint
        terrain.Margin = float(options.get("terrain_margin_mm", 5000.0))
        terrain.PadMargin = float(options.get("pad_margin_mm", 1000.0))
        terrain.Variation = float(options.get("terrain_variation_mm", 500.0))
        terrain.SurfaceZ = float(options.get("floor_top_z_mm", 0.0)) - float(
            options.get("floor_thickness_mm", 150.0)
        )
        terrain.Seed = int(options.get("terrain_seed", 12345))
        terrain.CutUnderBuilding = bool(options.get("cut_terrain_under_building", True))
        _tag_generated(terrain, "terrain")
        set_prop(
            terrain,
            "App::PropertyBool",
            "CGE_GroundCandidate",
            "FacilArquitectura",
            "Puede usarse como suelo de prueba para exportacion",
            True,
        )
        doc.recompute()

    site_objects = [building] if building is not None else [slab]
    try:
        site = Arch.makeSite(objectslist=site_objects, baseobj=terrain, name="FA_Site")
    except TypeError:
        site = Arch.makeSite(site_objects, terrain, "FA_Site")
    if site is None:
        raise UserFacingError("Arch.makeSite no pudo crear el sitio BIM.")
    site.Label = "Sitio BIM"
    _tag_generated(site, "site")
    _set_source_name_metadata(
        site,
        usable,
        "Sketches arquitectonicos de referencia; se guardan por nombre para no reclamar hijos en el arbol",
    )
    if building is not None:
        set_prop(
            site,
            "App::PropertyString",
            "FA_BuildingName",
            "FacilArquitectura",
            "Building contenido por el Site",
            str(getattr(building, "Name", "") or ""),
        )
    if level is not None:
        set_prop(
            site,
            "App::PropertyString",
            "FA_LevelName",
            "FacilArquitectura",
            "Level que contiene la losa",
            str(getattr(level, "Name", "") or ""),
        )
    # En el flujo nativo el Site es raiz espacial y no se agrega tambien a 03_BIM.
    if building is None and bim_group is not None:
        try:
            bim_group.addObject(site)
        except Exception:
            pass

    _set_view(footprint, visible=False)
    _set_view(slab, color=(0.78, 0.72, 0.62), transparency=0)
    if terrain is not None:
        _set_view(terrain, color=(0.38, 0.53, 0.30), transparency=0)
    doc.recompute()
    msg(
        "Piso BIM creado desde %d sketches | espesor %.1f mm | terreno de prueba: %s"
        % (
            len(usable),
            float(options.get("floor_thickness_mm", 150.0)),
            "si" if terrain is not None else "no",
        )
    )
    return {"site": site, "slab": slab, "terrain": terrain, "footprint": footprint}




def _set_source_name_metadata(obj, sketches, description):
    """Store source names without creating extra dependency children in the tree.

    Earlier builds used ``App::PropertyLinkList FA_SourceSketches`` on Site and
    Slab only for traceability. Those links made the Sketches appear under Site
    even though their semantic parent is a Wall/Footprint/Auxiliares FA. New
    objects use names only; generated legacy properties are cleared on rerun.
    """
    names = [str(getattr(sketch, "Name", "") or "") for sketch in list(sketches or [])]
    names = [name for name in names if name]
    if hasattr(obj, "FA_SourceSketches"):
        try:
            obj.FA_SourceSketches = []
        except Exception:
            pass
    set_prop(
        obj,
        "App::PropertyStringList",
        "FA_SourceSketchNames",
        "FacilArquitectura",
        description,
        names,
    )

def remove_previous_site_floor(doc):
    """Remove only objects generated by this command, in dependency order."""
    tagged = [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == GENERATED_BY_SITE_FLOOR
    ]
    role_order = {"site": 0, "floor_slab": 1, "terrain": 2, "terrain_test": 2, "floor_footprint": 3}
    tagged.sort(key=lambda obj: role_order.get(str(getattr(obj, "FA_Role", "")), 99))
    removed = 0
    for obj in tagged:
        try:
            if doc.getObject(obj.Name) is not None:
                doc.removeObject(obj.Name)
                removed += 1
        except Exception as exc:
            warn("No se pudo eliminar %s: %s" % (_object_label(obj), exc))
    if removed:
        doc.recompute()
    return removed


class FloorFootprintProxy:
    """Parametric rectangular envelope driven by architectural sketches."""

    def __init__(self, obj=None):
        self.Type = "FacilArquitectura_FloorFootprint"
        if obj is not None:
            self.attach(obj)

    def attach(self, obj):
        set_prop(
            obj,
            "App::PropertyLinkList",
            "Sources",
            "FacilArquitectura",
            "Sketches que controlan la huella",
            [],
        )
        set_prop(
            obj,
            "App::PropertyLength",
            "Overhang",
            "FacilArquitectura",
            "Sobresaliente del piso alrededor de los sketches",
            100.0,
        )
        set_prop(
            obj,
            "App::PropertyLength",
            "TopZ",
            "FacilArquitectura",
            "Cota superior del piso",
            0.0,
        )
        obj.Proxy = self

    def execute(self, obj):
        try:
            x_min, y_min, x_max, y_max = combined_sketch_bounds(list(obj.Sources or []))
            margin = _quantity_value(obj.Overhang)
            z = _quantity_value(obj.TopZ)
            obj.Shape = _rectangle_face(
                x_min - margin,
                y_min - margin,
                x_max + margin,
                y_max + margin,
                z,
            )
        except Exception as exc:
            warn("No se pudo actualizar la huella del piso: %s" % exc)

    def onDocumentRestored(self, obj):  # noqa: N802
        obj.Proxy = self

    def __getstate__(self):
        return {"Type": self.Type}

    def __setstate__(self, state):
        self.Type = (state or {}).get("Type", "FacilArquitectura_FloorFootprint")


class TestTerrainProxy:
    """Simple deterministic terrain surface with a flat pad and optional building cutout."""

    def __init__(self, obj=None):
        self.Type = "FacilArquitectura_TestTerrain"
        if obj is not None:
            self.attach(obj)

    def attach(self, obj):
        set_prop(obj, "App::PropertyLink", "Footprint", "FacilArquitectura", "Huella del edificio", None)
        set_prop(obj, "App::PropertyLength", "Margin", "FacilArquitectura", "Margen total del terreno", 5000.0)
        set_prop(obj, "App::PropertyLength", "PadMargin", "FacilArquitectura", "Margen de plataforma plana", 1000.0)
        set_prop(obj, "App::PropertyLength", "Variation", "FacilArquitectura", "Variacion vertical maxima", 500.0)
        set_prop(obj, "App::PropertyLength", "SurfaceZ", "FacilArquitectura", "Cota de plataforma", -150.0)
        set_prop(obj, "App::PropertyInteger", "Seed", "FacilArquitectura", "Semilla del terreno", 12345)
        set_prop(
            obj,
            "App::PropertyBool",
            "CutUnderBuilding",
            "FacilArquitectura",
            "No generar caras de terreno bajo la huella de la losa",
            True,
        )
        obj.Proxy = self

    def execute(self, obj):
        footprint = getattr(obj, "Footprint", None)
        shape = getattr(footprint, "Shape", None)
        bbox = getattr(shape, "BoundBox", None)
        if bbox is None:
            return
        try:
            obj.Shape = _test_terrain_shape(
                float(bbox.XMin),
                float(bbox.YMin),
                float(bbox.XMax),
                float(bbox.YMax),
                _quantity_value(obj.Margin),
                _quantity_value(obj.PadMargin),
                _quantity_value(obj.Variation),
                _quantity_value(obj.SurfaceZ),
                int(obj.Seed),
                bool(getattr(obj, "CutUnderBuilding", True)),
            )
        except Exception as exc:
            warn("No se pudo actualizar el terreno de prueba: %s" % exc)

    def onDocumentRestored(self, obj):  # noqa: N802
        # Reaplica el esquema sin sobrescribir valores guardados. Esto agrega
        # CutUnderBuilding a terrenos creados por versiones anteriores.
        self.attach(obj)

    def __getstate__(self):
        return {"Type": self.Type}

    def __setstate__(self, state):
        self.Type = (state or {}).get("Type", "FacilArquitectura_TestTerrain")


def _make_bim_slab(base, thickness):
    if thickness <= 0.0:
        raise UserFacingError("El espesor del piso debe ser mayor que cero.")
    try:
        slab = Arch.makeStructure(base, height=float(thickness), name="FA_FloorSlab")
    except TypeError:
        slab = Arch.makeStructure(base, None, None, float(thickness), "FA_FloorSlab")
    if slab is None:
        raise UserFacingError("Arch.makeStructure no pudo crear la losa BIM.")
    slab.IfcType = "Slab"
    try:
        slab.Normal = FreeCAD.Vector(0.0, 0.0, -1.0)
    except Exception:
        pass
    return slab


def _test_terrain_shape(
    x_min, y_min, x_max, y_max, margin, pad_margin, variation, surface_z, seed, cut_under_building=True
):
    margin = max(500.0, float(margin))
    pad_margin = max(0.0, min(float(pad_margin), margin))
    x0, x1 = x_min - margin, x_max + margin
    y0, y1 = y_min - margin, y_max + margin
    xs = _terrain_coordinates(x0, x_min - pad_margin, x_min, x_max, x_max + pad_margin, x1)
    ys = _terrain_coordinates(y0, y_min - pad_margin, y_min, y_max, y_max + pad_margin, y1)
    points = []
    for row, y in enumerate(ys):
        row_points = []
        for column, x in enumerate(xs):
            inside_pad = (
                x_min - pad_margin <= x <= x_max + pad_margin
                and y_min - pad_margin <= y <= y_max + pad_margin
            )
            if inside_pad:
                z = surface_z
            else:
                rng = random.Random(int(seed) + row * 1009 + column * 9176)
                wave = math.sin(x / 4300.0) * 0.30 + math.cos(y / 5100.0) * 0.25
                z = surface_z + float(variation) * (wave + rng.uniform(-0.25, 0.25))
            row_points.append(FreeCAD.Vector(x, y, z))
        points.append(row_points)
    faces = []
    for row in range(len(ys) - 1):
        for column in range(len(xs) - 1):
            cell_cx = (xs[column] + xs[column + 1]) / 2.0
            cell_cy = (ys[row] + ys[row + 1]) / 2.0
            if bool(cut_under_building) and x_min <= cell_cx <= x_max and y_min <= cell_cy <= y_max:
                # La losa ocupa esta zona. Omitir estas caras evita superficies
                # coincidentes y el efecto visual de terreno atravesando el piso.
                continue
            p00 = points[row][column]
            p10 = points[row][column + 1]
            p01 = points[row + 1][column]
            p11 = points[row + 1][column + 1]
            faces.append(Part.Face(Part.makePolygon([p00, p10, p11, p00])))
            faces.append(Part.Face(Part.makePolygon([p00, p11, p01, p00])))
    return Part.makeCompound(faces)


def _terrain_coordinates(start, pad_start, core_start, core_end, pad_end, end):
    values = [
        start,
        (start + pad_start) / 2.0,
        pad_start,
        core_start,
        (core_start + core_end) / 2.0,
        core_end,
        pad_end,
        (pad_end + end) / 2.0,
        end,
    ]
    return sorted({round(min(max(value, start), end), 6) for value in values})


def _rectangle_face(x_min, y_min, x_max, y_max, z):
    points = [
        FreeCAD.Vector(x_min, y_min, z),
        FreeCAD.Vector(x_max, y_min, z),
        FreeCAD.Vector(x_max, y_max, z),
        FreeCAD.Vector(x_min, y_max, z),
        FreeCAD.Vector(x_min, y_min, z),
    ]
    return Part.Face(Part.makePolygon(points))


def _unique_plan_sketches(sketches):
    result = []
    seen = set()
    for sketch in sketches or []:
        name = str(getattr(sketch, "Name", "") or "")
        if not name or name in seen or not _is_plan_source_sketch(sketch):
            continue
        seen.add(name)
        result.append(sketch)
    if not result:
        raise UserFacingError("No hay sketches de muros, ventanas o puertas para calcular el piso.")
    return result


def _is_plan_source_sketch(obj):
    if obj is None:
        return False
    type_id = str(getattr(obj, "TypeId", "") or "")
    if not (type_id.startswith("Sketcher::") or hasattr(obj, "Geometry")):
        return False
    kind = str(getattr(obj, "FA_CenterlineKind", "") or "").strip().lower()
    element_type = str(getattr(obj, "FA_ElementType", "") or "").strip().lower()
    if kind == "columns" or element_type in ("columnas", "columns"):
        return False
    label = _object_label(obj)
    text = ("%s %s" % (str(getattr(obj, "Name", "")), label)).lower()
    if any(keyword in text for keyword in EXCLUDED_KEYWORDS):
        return False
    role = str(getattr(obj, "FA_Role", "") or "").strip().lower()
    relevant = role == "centerlines" or any(keyword in text for keyword in PLAN_KEYWORDS)
    return relevant and _geometry_count(obj) > 0


def _geometry_count(obj):
    try:
        geometry = list(getattr(obj, "Geometry", []) or [])
        if geometry:
            return len(geometry)
    except Exception:
        pass
    try:
        return len(list(getattr(getattr(obj, "Shape", None), "Edges", []) or []))
    except Exception:
        return 0


def _tag_generated(obj, role):
    set_prop(
        obj,
        "App::PropertyString",
        "FA_GeneratedBy",
        "FacilArquitectura",
        "Comando que genero el objeto",
        GENERATED_BY_SITE_FLOOR,
    )
    set_prop(obj, "App::PropertyString", "FA_Role", "FacilArquitectura", "Rol del objeto", role)


def _set_view(obj, color=None, transparency=None, visible=None):
    view = getattr(obj, "ViewObject", None)
    if view is None:
        return
    try:
        if color is not None:
            view.ShapeColor = tuple(float(value) for value in color)
            view.LineColor = tuple(float(value) for value in color)
        if transparency is not None:
            view.Transparency = int(transparency)
        if visible is not None:
            view.Visibility = bool(visible)
    except Exception:
        pass


def _quantity_value(value):
    try:
        return float(value.Value)
    except Exception:
        return float(value)


def _object_label(obj):
    return str(getattr(obj, "Label", getattr(obj, "Name", "")) or "")
