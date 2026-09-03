"""Validation and input normalization for service platform fronts."""

from __future__ import annotations

from dataclasses import fields

from .model import PlatformOptions


class PlatformValidationError(ValueError):
    """Actionable invalid user input."""


def normalize_options(values=None) -> PlatformOptions:
    """Return a typed, normalized options object."""
    if values is None:
        return PlatformOptions()
    if isinstance(values, PlatformOptions):
        return values
    source = dict(values)
    defaults = PlatformOptions()
    normalized = {}
    bool_names = {
        "create_3d_furniture",
        "create_functional_zones",
        "invert_direction",
        "show_service_areas",
        "glass_opening_enabled",
    }
    int_names = {"service_positions"}
    string_names = {"staff_side"}
    for item in fields(PlatformOptions):
        name = item.name
        raw = source.get(name, getattr(defaults, name))
        try:
            if name in bool_names:
                normalized[name] = _as_bool(raw)
            elif name in int_names:
                normalized[name] = int(raw)
            elif name in string_names:
                normalized[name] = str(raw).strip().lower()
            else:
                normalized[name] = float(raw)
        except (TypeError, ValueError) as exc:
            raise PlatformValidationError("Valor no valido para %s: %s" % (name, raw)) from exc
    return PlatformOptions(**normalized)


def validate_options(options: PlatformOptions) -> None:
    """Validate non-derived constraints."""
    if options.service_positions < 1:
        raise PlatformValidationError("La cantidad de puestos debe ser al menos 1.")
    if options.total_width_mm <= 0.0:
        raise PlatformValidationError("El ancho total debe ser mayor que cero.")
    non_negative = (
        ("margen lateral", options.side_margin_mm),
        ("espesor de division", options.divider_thickness_mm),
    )
    for label, value in non_negative:
        if value < 0.0:
            raise PlatformValidationError("El %s no puede ser negativo." % label)
    positive = (
        ("profundidad del escritorio", options.desk_depth_mm),
        ("altura del escritorio", options.desk_height_mm),
        ("espesor del escritorio", options.desk_thickness_mm),
        ("profundidad de division", options.divider_depth_mm),
        ("altura de division", options.divider_height_mm),
        ("profundidad del mostrador", options.counter_depth_mm),
        ("espesor del panel frontal", options.front_panel_thickness_mm),
        ("espesor del vidrio", options.glass_thickness_mm),
        ("cota superior del vidrio", options.glass_top_mm),
        ("ancho de parante", options.mullion_width_mm),
        ("profundidad de parante", options.mullion_depth_mm),
        ("profundidad del area de funcionario", options.staff_zone_depth_mm),
        ("profundidad del area publica", options.public_zone_depth_mm),
        ("ancho minimo por puesto", options.minimum_position_width_mm),
    )
    for label, value in positive:
        if value <= 0.0:
            raise PlatformValidationError("La %s debe ser mayor que cero." % label)
    if options.desk_thickness_mm > options.desk_height_mm:
        raise PlatformValidationError("El espesor del escritorio no puede superar su altura.")
    if options.glass_top_mm <= options.desk_height_mm:
        raise PlatformValidationError(
            "La cota superior del vidrio debe superar la altura del mostrador."
        )
    if options.staff_side not in ("left", "right"):
        raise PlatformValidationError("El lado de funcionario debe ser left o right.")


def validate_glass_opening(options: PlatformOptions) -> None:
    """Validate opening rules only for the compact line-driven workflow."""
    opening_dimensions = (
        ("ancho de la abertura del vidrio", options.glass_opening_width_mm),
        ("alto de la abertura del vidrio", options.glass_opening_height_mm),
        ("altura inferior de la abertura del vidrio", options.glass_opening_bottom_mm),
    )
    for label, value in opening_dimensions:
        if value < 0.0:
            raise PlatformValidationError("El %s no puede ser negativo." % label)
    if not options.glass_opening_enabled:
        return
    if options.glass_opening_width_mm <= 0.0:
        raise PlatformValidationError(
            "El ancho de la abertura del vidrio debe ser mayor que cero."
        )
    if options.glass_opening_height_mm <= 0.0:
        raise PlatformValidationError(
            "El alto de la abertura del vidrio debe ser mayor que cero."
        )
    if options.glass_opening_bottom_mm < options.desk_height_mm:
        raise PlatformValidationError(
            "La altura inferior de la abertura del vidrio debe ser igual o superior "
            "a la altura del mostrador."
        )
    opening_top = options.glass_opening_bottom_mm + options.glass_opening_height_mm
    if opening_top >= options.glass_top_mm:
        raise PlatformValidationError(
            "La abertura del vidrio termina a %.1f mm y debe quedar por debajo de la "
            "cota superior del vidrio de %.1f mm." % (opening_top, options.glass_top_mm)
        )


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "off")
    return bool(value)
