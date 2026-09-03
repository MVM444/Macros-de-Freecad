"""Parametric service-platform-front module.

Keep this package initializer FreeCAD-independent so the calculator can be tested
with a regular Python interpreter.
"""

from .calculator import calculate_layout, calculate_line_layout
from .frame import AxisFrame, build_axis_frame
from .model import PlatformLayout, PlatformOptions

__all__ = [
    "AxisFrame",
    "PlatformLayout",
    "PlatformOptions",
    "build_axis_frame",
    "calculate_layout",
    "calculate_line_layout",
]
