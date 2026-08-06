"""Properties and Spreadsheet persistence for service platform fronts."""

from __future__ import annotations

from dataclasses import fields

from ...core.project_structure import set_prop, warn
from .model import PlatformLayout, PlatformOptions
from .validation import normalize_options


GENERATED_BY = "FA_CreateServicePlatformFront"
MODULE_TYPE = "service_platform_front"
MODULE_VERSION = "0.1"
PROPERTY_GROUP = "FacilArquitectura - Plataforma"
PARAMETER_ROWS = (
    ("total_width_mm", "Ancho total", "mm"),
    ("service_positions", "Cantidad de puestos", ""),
    ("desk_depth_mm", "Profundidad del escritorio", "mm"),
    ("desk_height_mm", "Altura del escritorio", "mm"),
    ("desk_thickness_mm", "Espesor del escritorio", "mm"),
    ("side_margin_mm", "Margen lateral", "mm"),
    ("divider_thickness_mm", "Espesor de division", "mm"),
    ("divider_depth_mm", "Profundidad de division", "mm"),
    ("divider_height_mm", "Altura de division", "mm"),
    ("staff_zone_depth_mm", "Profundidad area funcionario", "mm"),
    ("public_zone_depth_mm", "Profundidad area publica", "mm"),
    ("front_offset_mm", "Desfase frontal", "mm"),
    ("minimum_position_width_mm", "Ancho minimo por puesto", "mm"),
    ("create_3d_furniture", "Crear mobiliario 3D", "boolean"),
    ("create_functional_zones", "Crear zonas funcionales", "boolean"),
)


def write_parameter_sheet(sheet, options: PlatformOptions) -> None:
    """Write a stable parameter table and aliases."""
    headers = ("Parametro", "Valor", "Unidad", "Descripcion")
    for column, value in zip(("A", "B", "C", "D"), headers):
        sheet.set(column + "1", value)
    for row, (name, description, unit) in enumerate(PARAMETER_ROWS, start=2):
        value = getattr(options, name)
        if isinstance(value, bool):
            value = 1 if value else 0
        sheet.set("A%d" % row, name)
        sheet.set("B%d" % row, str(value))
        sheet.set("C%d" % row, unit)
        sheet.set("D%d" % row, description)
        try:
            sheet.setAlias("B%d" % row, name)
        except Exception as exc:
            warn("No se pudo crear alias %s: %s" % (name, exc))
    try:
        sheet.setColumnWidth("A", 210)
        sheet.setColumnWidth("B", 110)
        sheet.setColumnWidth("C", 80)
        sheet.setColumnWidth("D", 240)
    except Exception:
        pass
    set_prop(sheet, "App::PropertyString", "FA_ModuleType", PROPERTY_GROUP, "Tipo de modulo", MODULE_TYPE)
    set_prop(sheet, "App::PropertyString", "FA_ModuleVersion", PROPERTY_GROUP, "Version", MODULE_VERSION)


def read_parameter_sheet(sheet) -> PlatformOptions:
    """Read aliases first and retain defaults for missing values."""
    values = {}
    defaults = PlatformOptions()
    bool_names = {"create_3d_furniture", "create_functional_zones"}
    int_names = {"service_positions"}
    for item in fields(PlatformOptions):
        name = item.name
        raw = None
        try:
            raw = sheet.get(name)
        except Exception:
            pass
        if raw in (None, ""):
            for row, (row_name, _description, _unit) in enumerate(PARAMETER_ROWS, start=2):
                if row_name == name:
                    try:
                        raw = sheet.get("B%d" % row)
                    except Exception:
                        raw = None
                    break
        if raw in (None, ""):
            raw = getattr(defaults, name)
        if name in bool_names:
            values[name] = str(raw).strip().lower() not in ("", "0", "false", "no", "off")
        elif name in int_names:
            values[name] = int(float(raw))
        else:
            values[name] = float(getattr(raw, "Value", raw))
    return normalize_options(values)


def set_root_properties(root, options: PlatformOptions, layout: PlatformLayout, sheet=None) -> None:
    """Store the public module contract on its semantic owner."""
    values = (
        ("App::PropertyString", "FA_ModuleType", "Tipo de modulo", MODULE_TYPE),
        ("App::PropertyString", "FA_ModuleVersion", "Version del modulo", MODULE_VERSION),
        ("App::PropertyLength", "FA_TotalWidth_mm", "Ancho total", options.total_width_mm),
        ("App::PropertyInteger", "FA_ServicePositions", "Cantidad de puestos", options.service_positions),
        ("App::PropertyLength", "FA_PositionWidth_mm", "Ancho por puesto", layout.position_width_mm),
        ("App::PropertyLength", "FA_DeskDepth_mm", "Profundidad escritorio", options.desk_depth_mm),
        ("App::PropertyLength", "FA_DeskHeight_mm", "Altura escritorio", options.desk_height_mm),
        ("App::PropertyLength", "FA_StaffZoneDepth_mm", "Profundidad funcionario", options.staff_zone_depth_mm),
        ("App::PropertyLength", "FA_PublicZoneDepth_mm", "Profundidad publica", options.public_zone_depth_mm),
        ("App::PropertyString", "FA_GeneratedBy", "Generador", GENERATED_BY),
        ("App::PropertyString", "FA_SourceStandard", "Referencia", "CCSS_PL-01_reference"),
        ("App::PropertyString", "FA_ReferenceDocument", "Documento", "Guia Estandarizacion 050626 2"),
        ("App::PropertyString", "FA_ReferencePages", "Paginas", "33-34"),
    )
    for prop_type, name, description, value in values:
        set_prop(root, prop_type, name, PROPERTY_GROUP, description, value)
    _set_initial_property(root, "App::PropertyBool", "FA_IncludeCashier", "Incluye caja", False)
    _set_initial_property(root, "App::PropertyBool", "FA_Reviewed", "Revisado", False)
    if sheet is not None:
        set_prop(root, "App::PropertyLink", "FA_ParameterSheet", PROPERTY_GROUP, "Hoja de parametros", sheet)


def _set_initial_property(obj, prop_type, name, description, value):
    """Set review-state defaults only once so updates preserve user decisions."""
    if hasattr(obj, name):
        return
    set_prop(obj, prop_type, name, PROPERTY_GROUP, description, value)


def tag_representation(obj, owner, role: str, part: str) -> None:
    """Link every generated representation to the semantic owner."""
    set_prop(obj, "App::PropertyString", "FA_GeneratedBy", PROPERTY_GROUP, "Generador", GENERATED_BY)
    set_prop(obj, "App::PropertyString", "FA_ModuleType", PROPERTY_GROUP, "Tipo de modulo", MODULE_TYPE)
    set_prop(obj, "App::PropertyString", "FA_ModulePart", PROPERTY_GROUP, "Parte del modulo", part)
    # The owner already contains this object through a DocumentObjectGroup. A
    # regular PropertyLink in the opposite direction would make FreeCAD's
    # recompute graph cyclic. PropertyLinkHidden retains a real document link
    # while intentionally excluding it from dependency traversal.
    set_prop(obj, "App::PropertyLinkHidden", "Owner", PROPERTY_GROUP, "Propietario semantico", owner)
    set_prop(obj, "App::PropertyString", "RepresentationRole", PROPERTY_GROUP, "Rol de representacion", role)
