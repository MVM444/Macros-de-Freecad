"""Pruebas focales del editor FA de ejes de cerchas.

Nombre: test_edit_truss_axes_contract.py
Proposito: proteger el contrato del editor amigable sobre Arch Axis nativo.
Version: 0.1.0
Fecha y hora: 2026-08-31 12:55 America/Costa_Rica
"""

from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
CMD = ROOT / "commands" / "cmd_edit_truss_axes.py"
CORE = ROOT / "core" / "axis_distribution_core.py"


def _load_core():
    spec = importlib.util.spec_from_file_location("axis_distribution_core_test", CORE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_editor_reuses_native_axis_contract():
    text = CMD.read_text(encoding="utf-8")
    assert 'COMMAND_NAME = "FA_EditTrussAxes"' in text
    assert "axis.Distances =" in text
    assert "axis.Angles =" in text
    assert "Arch.makeAxis" not in text
    assert "ReloadableCommandProxy" in text


def test_all_editor_modes_keep_requested_end_retiros():
    core = _load_core()
    total = 11166.0
    maximum = 3000.0
    start = 100.0
    end = 100.0
    planners = [
        core.plan_fixed_axis_distribution(total, maximum, start, end),
        core.plan_uniform_axis_distribution(total, maximum, start, end),
        core.plan_rounded_axis_distribution(total, maximum, 50.0, start, end),
        core.plan_rounded_axis_distribution(total, maximum, 100.0, start, end),
    ]
    for result in planners:
        assert result["axis_count"] >= 2
        assert abs(result["positions_mm"][0] - start) < 1e-9
        assert abs(result["positions_mm"][-1] - (total - end)) < 1e-9
        assert result["max_interval_mm"] <= maximum + 1e-9
