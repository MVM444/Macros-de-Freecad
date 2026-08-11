"""Data model for a parametric public-service platform front."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformOptions:
    """User-editable dimensions in millimetres."""

    total_width_mm: float = 3840.0
    service_positions: int = 2
    desk_depth_mm: float = 600.0
    desk_height_mm: float = 740.0
    desk_thickness_mm: float = 30.0
    side_margin_mm: float = 100.0
    divider_thickness_mm: float = 40.0
    divider_depth_mm: float = 600.0
    divider_height_mm: float = 450.0
    staff_zone_depth_mm: float = 1800.0
    public_zone_depth_mm: float = 1500.0
    origin_x_mm: float = 0.0
    front_offset_mm: float = 0.0
    minimum_position_width_mm: float = 1200.0
    create_3d_furniture: bool = True
    create_functional_zones: bool = True


@dataclass(frozen=True)
class PlatformLayout:
    """Derived geometry for the platform front."""

    divider_count: int
    usable_width_mm: float
    position_width_mm: float
    minimum_total_width_mm: float
    approximate_total_depth_mm: float
