"""Pure calculations for service platform fronts."""

from __future__ import annotations

from .model import PlatformLayout, PlatformOptions
from .validation import PlatformValidationError, normalize_options, validate_options


def calculate_layout(values=None) -> PlatformLayout:
    """Validate the input and calculate the modular widths."""
    options = normalize_options(values)
    validate_options(options)
    divider_count = max(options.service_positions - 1, 0)
    usable_width = (
        options.total_width_mm
        - 2.0 * options.side_margin_mm
        - divider_count * options.divider_thickness_mm
    )
    minimum_total = (
        2.0 * options.side_margin_mm
        + options.service_positions * options.minimum_position_width_mm
        + divider_count * options.divider_thickness_mm
    )
    if usable_width <= 0.0:
        raise PlatformValidationError(
            "No queda ancho util despues de descontar margenes y divisiones. "
            "Ancho total minimo recomendado: %.1f mm." % minimum_total
        )
    position_width = usable_width / float(options.service_positions)
    if position_width < options.minimum_position_width_mm:
        raise PlatformValidationError(
            "El ancho calculado por puesto es %.1f mm, menor que el minimo de %.1f mm. "
            "Use un ancho total de al menos %.1f mm para %d puestos."
            % (
                position_width,
                options.minimum_position_width_mm,
                minimum_total,
                options.service_positions,
            )
        )
    return PlatformLayout(
        divider_count=divider_count,
        usable_width_mm=usable_width,
        position_width_mm=position_width,
        minimum_total_width_mm=minimum_total,
        approximate_total_depth_mm=(
            options.public_zone_depth_mm + options.desk_depth_mm + options.staff_zone_depth_mm
        ),
    )


def position_origins(options: PlatformOptions, layout: PlatformLayout):
    """Return the left X coordinate of each service position."""
    x = options.origin_x_mm + options.side_margin_mm
    result = []
    for index in range(options.service_positions):
        result.append(x)
        x += layout.position_width_mm
        if index < layout.divider_count:
            x += options.divider_thickness_mm
    return result
