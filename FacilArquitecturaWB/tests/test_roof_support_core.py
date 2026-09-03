"""Pruebas puras para resolucion de apoyos extremos de FA Techo."""

from FacilArquitecturaWB.core.roof_support_core import (
    apply_symmetric_support_adjust,
    select_end_support_axes,
)


def test_selects_end_walls_and_ignores_interior():
    data = select_end_support_axes([100.0, 4200.0, 11266.0], 11366.0, 1000.0)
    assert data["start_axis_mm"] == 100.0
    assert data["end_axis_mm"] == 11266.0


def test_requires_both_end_supports():
    assert select_end_support_axes([100.0, 4200.0], 11366.0, 1000.0) is None


def test_symmetric_adjust_moves_inward():
    data = apply_symmetric_support_adjust(100.0, 11266.0, 50.0)
    assert data["start_axis_mm"] == 150.0
    assert data["end_axis_mm"] == 11216.0
    assert data["support_length_mm"] == 11066.0


def test_negative_adjust_moves_outward():
    data = apply_symmetric_support_adjust(100.0, 11266.0, -25.0)
    assert data["start_axis_mm"] == 75.0
    assert data["end_axis_mm"] == 11291.0
