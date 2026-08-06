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
    bool_names = {"create_3d_furniture", "create_functional_zones"}
    int_names = {"service_positions"}
    for item in fields(PlatformOptions):
        name = item.name
        raw = source.get(name, getattr(defaults, name))
        try:
            if name in bool_names:
                normalized[name] = _as_bool(raw)
            elif name in int_names:
                normalized[name] = int(raw)
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
        ("profundidad del area de funcionario", options.staff_zone_depth_mm),
        ("profundidad del area publica", options.public_zone_depth_mm),
        ("ancho minimo por puesto", options.minimum_position_width_mm),
    )
    for label, value in positive:
        if value <= 0.0:
            raise PlatformValidationError("La %s debe ser mayor que cero." % label)
    if options.desk_thickness_mm > options.desk_height_mm:
        raise PlatformValidationError("El espesor del escritorio no puede superar su altura.")


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "off")
    return bool(value)
