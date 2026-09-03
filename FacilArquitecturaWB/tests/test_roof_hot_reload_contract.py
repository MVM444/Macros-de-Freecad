from pathlib import Path


def test_roof_command_uses_reloadable_proxy_and_roof_base_recompute():
    root = Path(__file__).resolve().parents[1]
    source = (root / "commands" / "cmd_roof_axis_prototype.py").read_text(encoding="utf-8")
    assert "ReloadableCommandProxy" in source
    assert "command = ReloadableCommandProxy(" in source
    assert source.index("base.recompute()") < source.index("Arch.makeRoof(")
    assert "base_wires[0].isClosed()" in source
