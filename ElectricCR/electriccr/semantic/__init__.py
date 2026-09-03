"""Semantic helpers for ElectricCR objects and reproducible tree projections.

The package initializer intentionally does not import the FreeCAD adapter so
the pure core remains usable from ordinary Python.
"""

from .device_core import (  # noqa: F401
    SCHEMA_VERSION,
    STATUS_INCOMPLETE,
    STATUS_READY,
    build_lighting_projection,
)

