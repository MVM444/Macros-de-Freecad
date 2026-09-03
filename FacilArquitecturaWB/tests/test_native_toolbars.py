"""Pruebas de contrato para las barras nativas de FacilArquitecturaWB.

Version: 1.0
Fecha y hora: 2026-09-01 12:12 America/Costa_Rica.
"""

import ast
from pathlib import Path


def _source():
    return (Path(__file__).resolve().parents[1] / "InitGui.py").read_text(encoding="utf-8")


def test_native_toolbar_contract_is_present():
    source = _source()
    tree = ast.parse(source)
    strings = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    for expected in {
        "FA Dibujo 2D",
        "FA Snaps",
        "FA Auxiliares BIM",
        "BIM_Sketch",
        "Sketcher_NewSketch",
        "Draft_Line",
        "Draft_Wire",
        "Draft_Rectangle",
        "Draft_Move",
        "Draft_Trimex",
        "Draft_Draft2Sketch",
        "Draft_Snap_Endpoint",
        "Draft_Snap_Midpoint",
        "Arch_SectionPlane",
        "BIM_Create2DViews",
    }:
        assert expected in strings
    assert "all_toolbar_specs = tuple(toolbar_specs) + tuple(native_toolbar_specs)" in source
    assert "_ensure_native_freecad_commands()" in source
