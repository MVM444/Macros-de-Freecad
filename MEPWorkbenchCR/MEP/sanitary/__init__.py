"""
Nombre: MEP.sanitary
Proposito: Nucleo sanitario de MEPWorkbenchCR.
Version: 0.5.0
Fecha: 2026-08-26
"""
from .system import calculate_system
from .infiltration import (
    infiltration_rate_min_cm,
    application_rate_from_test,
    select_design_infiltration_test,
    size_from_infiltration_tests,
    evaluate_field_infiltration_test,
)
from .freecad_adapter import preview_plan, create_preview_objects
from .layout import layout_parallel_trenches
from .freecad_objects import create_septic_tank, create_fafa, create_infiltration_trench
from .documentation import build_plan_documentation, build_section_documentation, render_svg
from .case import validate_case_input, calculate_case
from .boundary import Boundary2D
from .spatial import validate_spatial_references

__all__ = [
    "calculate_system",
    "infiltration_rate_min_cm",
    "application_rate_from_test",
    "select_design_infiltration_test",
    "size_from_infiltration_tests",
    "evaluate_field_infiltration_test",
    "preview_plan",
    "create_preview_objects",
    "layout_parallel_trenches",
    "create_septic_tank",
    "create_fafa",
    "create_infiltration_trench",
    "build_plan_documentation",
    "build_section_documentation",
    "render_svg",
    "validate_case_input",
    "calculate_case",
    "Boundary2D",
    "validate_spatial_references",
]
