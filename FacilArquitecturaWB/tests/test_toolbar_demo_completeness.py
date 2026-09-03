from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_guided_fa_capabilities_are_identified_as_real_tools_or_native_steps():
    core = (ROOT / "core" / "demo_guided_core.py").read_text(encoding="utf-8")
    init = (ROOT / "InitGui.py").read_text(encoding="utf-8")
    assert "FA Detectar recintos 2D" in core
    assert "FA Crear espacios BIM" in core
    assert "Draft Rectangle" in core
    assert "Sketcher / FA Centros de ejes" in core
    assert "cmd_detect_rooms_2d" in init
    assert "cmd_create_bim_spaces" in init
