"""Pure geometry plan for the compact line-driven service platform."""

from __future__ import annotations

from dataclasses import dataclass

from .calculator import calculate_line_layout
from .validation import PlatformValidationError, normalize_options


@dataclass(frozen=True)
class BoxSpec:
    role: str
    index: int
    x: float
    y: float
    z: float
    length: float
    depth: float
    height: float


@dataclass(frozen=True)
class CompactPlatformPlan:
    position_width_mm: float
    glass_opening_count: int
    body: tuple[BoxSpec, ...]
    glass: tuple[BoxSpec, ...]
    staff_areas: tuple[BoxSpec, ...]
    public_areas: tuple[BoxSpec, ...]


def plan_compact_platform(values=None) -> CompactPlatformPlan:
    """Plan opaque and glass solids in the canonical left-hand local frame."""
    options = normalize_options(values)
    layout = calculate_line_layout(options)
    width = float(options.total_width_mm)
    module = layout.position_width_mm
    clear_glass_width = module - options.mullion_width_mm
    if options.glass_opening_enabled and options.glass_opening_width_mm >= clear_glass_width:
        raise PlatformValidationError(
            "El ancho de la abertura del vidrio (%.1f mm) debe ser menor que el ancho "
            "util del pano de cada puesto (%.1f mm)."
            % (options.glass_opening_width_mm, clear_glass_width)
        )
    staff_sign = 1.0 if options.staff_side == "left" else -1.0
    staff_y = 0.0 if staff_sign > 0.0 else -options.desk_depth_mm
    public_y = -options.counter_depth_mm if staff_sign > 0.0 else 0.0
    divider_y = 0.0 if staff_sign > 0.0 else -options.divider_depth_mm

    body = [
        BoxSpec(
            "front_panel",
            0,
            0.0,
            -options.front_panel_thickness_mm * 0.5,
            0.0,
            width,
            options.front_panel_thickness_mm,
            options.desk_height_mm,
        ),
        BoxSpec(
            "service_counter",
            0,
            0.0,
            public_y,
            options.desk_height_mm - options.desk_thickness_mm,
            width,
            options.counter_depth_mm,
            options.desk_thickness_mm,
        ),
    ]
    glass = []
    staff_areas = []
    public_areas = []
    for index in range(options.service_positions):
        x = index * module
        body.append(
            BoxSpec(
                "employee_desk",
                index + 1,
                x,
                staff_y,
                options.desk_height_mm - options.desk_thickness_mm,
                module,
                options.desk_depth_mm,
                options.desk_thickness_mm,
            )
        )
        glass_start = x + options.mullion_width_mm * 0.5
        glass_length = max(1.0, module - options.mullion_width_mm)
        if options.glass_opening_enabled:
            opening_start = x + module * 0.5 - options.glass_opening_width_mm * 0.5
            opening_end = opening_start + options.glass_opening_width_mm
            opening_bottom = options.glass_opening_bottom_mm
            opening_top = opening_bottom + options.glass_opening_height_mm
            lower_height = opening_bottom - options.desk_height_mm
            if lower_height > 0.0:
                glass.append(
                    BoxSpec(
                        "glass_below_opening",
                        index + 1,
                        glass_start,
                        -options.glass_thickness_mm * 0.5,
                        options.desk_height_mm,
                        glass_length,
                        options.glass_thickness_mm,
                        lower_height,
                    )
                )
            side_height = opening_top - opening_bottom
            glass.extend(
                (
                    BoxSpec(
                        "glass_left_of_opening",
                        index + 1,
                        glass_start,
                        -options.glass_thickness_mm * 0.5,
                        opening_bottom,
                        opening_start - glass_start,
                        options.glass_thickness_mm,
                        side_height,
                    ),
                    BoxSpec(
                        "glass_right_of_opening",
                        index + 1,
                        opening_end,
                        -options.glass_thickness_mm * 0.5,
                        opening_bottom,
                        glass_start + glass_length - opening_end,
                        options.glass_thickness_mm,
                        side_height,
                    ),
                    BoxSpec(
                        "glass_above_opening",
                        index + 1,
                        glass_start,
                        -options.glass_thickness_mm * 0.5,
                        opening_top,
                        glass_length,
                        options.glass_thickness_mm,
                        options.glass_top_mm - opening_top,
                    ),
                )
            )
        else:
            glass.append(
                BoxSpec(
                    "glass_pane",
                    index + 1,
                    glass_start,
                    -options.glass_thickness_mm * 0.5,
                    options.desk_height_mm,
                    glass_length,
                    options.glass_thickness_mm,
                    options.glass_top_mm - options.desk_height_mm,
                )
            )
        staff_area_y = options.desk_depth_mm if staff_sign > 0.0 else (
            -options.desk_depth_mm - options.staff_zone_depth_mm
        )
        public_area_y = -options.public_zone_depth_mm if staff_sign > 0.0 else options.counter_depth_mm
        staff_areas.append(
            BoxSpec("staff_area", index + 1, x, staff_area_y, 0.0, module, options.staff_zone_depth_mm, 10.0)
        )
        public_areas.append(
            BoxSpec("public_area", index + 1, x, public_area_y, 0.0, module, options.public_zone_depth_mm, 10.0)
        )

    for index in range(1, options.service_positions):
        body.append(
            BoxSpec(
                "lateral_divider",
                index,
                index * module - options.divider_thickness_mm * 0.5,
                divider_y,
                options.desk_height_mm,
                options.divider_thickness_mm,
                options.divider_depth_mm,
                options.divider_height_mm,
            )
        )
    for index in range(options.service_positions + 1):
        x = min(max(index * module - options.mullion_width_mm * 0.5, 0.0), max(0.0, width - options.mullion_width_mm))
        body.append(
            BoxSpec(
                "mullion",
                index + 1,
                x,
                -options.mullion_depth_mm * 0.5,
                options.desk_height_mm,
                options.mullion_width_mm,
                options.mullion_depth_mm,
                options.glass_top_mm - options.desk_height_mm,
            )
        )
    return CompactPlatformPlan(
        position_width_mm=module,
        glass_opening_count=(options.service_positions if options.glass_opening_enabled else 0),
        body=tuple(body),
        glass=tuple(glass),
        staff_areas=tuple(staff_areas),
        public_areas=tuple(public_areas),
    )
