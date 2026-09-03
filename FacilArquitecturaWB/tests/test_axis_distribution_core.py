"""Pruebas focales de distribucion de Arch Axis para FA Techo.

Nombre: test_axis_distribution_core.py
Proposito: validar distribucion uniforme, nominal fija y nominal redondeada sin FreeCAD.
Version: 0.2.0
Fecha y hora: 2026-08-30 21:00 America/Costa_Rica
"""

import math
import pytest

from core.axis_distribution_core import (
    plan_fixed_axis_distribution,
    plan_rounded_axis_distribution,
    plan_uniform_axis_distribution,
)


def test_uniform_legacy_truss_axis_five_positions():
    plan = plan_uniform_axis_distribution(12000.0, 3000.0)
    assert plan["axis_count"] == 5
    assert plan["positions_mm"] == pytest.approx([0.0, 3000.0, 6000.0, 9000.0, 12000.0])
    assert plan["spacing_mm"] == pytest.approx(3000.0)


def test_fixed_keeps_nominal_interior_and_adjusts_only_extremes():
    slope = 4000.0 / math.cos(math.radians(20.0))
    plan = plan_fixed_axis_distribution(slope, 800.0, 200.0, 200.0)
    assert plan["axis_count"] == 6
    assert plan["intervals_mm"][1:-1] == pytest.approx([800.0, 800.0, 800.0])
    assert plan["first_interval_mm"] == pytest.approx(plan["last_interval_mm"])
    assert plan["max_interval_mm"] <= 800.0 + 1e-9
    assert plan["positions_mm"][0] == pytest.approx(200.0)
    assert plan["positions_mm"][-1] == pytest.approx(slope - 200.0)


def test_fixed_exact_module_needs_no_edge_exception():
    plan = plan_fixed_axis_distribution(3600.0, 800.0, 200.0, 200.0)
    assert plan["intervals_mm"] == pytest.approx([800.0, 800.0, 800.0, 800.0])
    assert plan["axis_count"] == 5


def test_rounded_50_uses_practical_nominal_without_exceeding_maximum():
    slope = 4000.0 / math.cos(math.radians(20.0))
    plan = plan_rounded_axis_distribution(slope, 800.0, 50.0, 200.0, 200.0)
    assert plan["mode"] == "rounded"
    assert plan["rounded_nominal_mm"] % 50.0 == pytest.approx(0.0)
    assert plan["rounded_nominal_mm"] <= 800.0
    assert plan["max_interval_mm"] <= 800.0 + 1e-9


def test_rounded_100_uses_practical_nominal_without_exceeding_maximum():
    plan = plan_rounded_axis_distribution(3900.0, 850.0, 100.0, 150.0, 150.0)
    assert plan["rounded_nominal_mm"] % 100.0 == pytest.approx(0.0)
    assert plan["rounded_nominal_mm"] <= 850.0
    assert plan["positions_mm"][0] == pytest.approx(150.0)
    assert plan["positions_mm"][-1] == pytest.approx(3750.0)


def test_rejects_impossible_offsets():
    with pytest.raises(ValueError):
        plan_fixed_axis_distribution(1000.0, 800.0, 600.0, 600.0)
