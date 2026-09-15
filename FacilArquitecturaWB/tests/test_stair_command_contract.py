"""Contract tests for FA Stair Between Slabs integration.

Fecha y hora: 2026-09-14 20:00 America/Costa_Rica
FreeCAD objetivo: 1.1.3
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_stair_command_uses_native_arch_and_separated_layers():
    command = (ROOT / "commands" / "cmd_stair_between_slabs.py").read_text(encoding="utf-8")
    adapter = (ROOT / "core" / "stair_freecad_adapter.py").read_text(encoding="utf-8")
    pure = (ROOT / "core" / "fa_stair_core.py").read_text(encoding="utf-8")
    assert "plan_angled_stair" in command
    assert "create_native_stair" in command
    assert "Arch.makeStairs(" in adapter
    assert "Part.makeBox" not in adapter
    assert "FreeCADGui" not in adapter
    assert "import FreeCAD" not in pure
    assert "import FreeCADGui" not in pure
    assert "DocumentationOnly" in adapter
    assert 'RepresentationRole", "Documentacion", "Rol documental", "PLAN"' in adapter
    assert "FA_LowerSlab" in adapter
    assert "FA_UpperSlab" in adapter
    assert "FA_LowerLevel" in adapter
    assert "FA_UpperLevel" in adapter
    assert "def create_native_slab_opening(" in adapter
    assert "Arch.removeComponents" not in adapter or "removeComponents" in adapter
    assert "Subtractions" in adapter
    assert "FA_SlabOpeningStatus" in adapter
    assert "def create_stair_opening_liner(" in adapter
    assert "FA_StairOpeningLiner" in adapter
    assert "Tapichel lateral - buque escalera" in adapter
    assert "FA_OpeningLinerStatus" in adapter
    assert "stair_opening_liner" in adapter
    assert "def _building_parent_for_level(" in adapter
    assert "add_to_container(building, master)" in adapter
    assert "add_to_level(lower_level, master)" not in adapter
    assert "ceiling_plane_id=None" in adapter
    assert "target_container=None" in adapter
    assert '== "l_union_v2"' in adapter
    assert "unified = _fused_clearance_face" in adapter
    assert "def _edge_matches_open_end(" in adapter
    assert "FA_LinerOpenEndsJSON" in adapter
    assert "FA_LinerSkippedOpenEnds" in adapter
    assert "shape = shape.cut(clear_void)" in adapter
    assert '"applied_open_ends"' in adapter


def test_initgui_registers_stair_in_structure_toolbar():
    init_gui = (ROOT / "InitGui.py").read_text(encoding="utf-8")
    assert "cmd_stair_between_slabs" in init_gui
    assert '"stair_between_slabs": cmd_stair_between_slabs.register().CommandName' in init_gui
    structure = init_gui.split('_toolbar_title("structure")', 1)[1].split('),', 1)[0]
    assert 'registered["stair_between_slabs"]' in structure
