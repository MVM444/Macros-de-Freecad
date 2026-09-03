"""Regression contracts for FA Techo desde rectangulo.

These tests do not import FreeCAD. They protect ordering requirements that are
needed by FreeCAD BIM 1.1.3 and are verified geometrically in the real smoke test.
"""

from pathlib import Path


def _command_source():
    root = Path(__file__).resolve().parents[1]
    return (root / "commands" / "cmd_roof_axis_prototype.py").read_text(encoding="utf-8")


def test_roof_base_is_recomputed_before_arch_make_roof():
    source = _command_source()
    start = source.index("def _make_roof")
    end = source.index("def _shape_ok", start)
    body = source[start:end]
    assert "base.recompute()" in body
    assert body.index("base.recompute()") < body.index("Arch.makeRoof(")
    assert "base.Shape.Wires[0].isClosed()" in body
