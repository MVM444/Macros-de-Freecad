"""Parametric service-platform-front module.

Keep this package initializer FreeCAD-independent so the calculator can be tested
with a regular Python interpreter.
"""

from .calculator import calculate_layout
from .model import PlatformLayout, PlatformOptions

__all__ = ["PlatformLayout", "PlatformOptions", "calculate_layout"]
