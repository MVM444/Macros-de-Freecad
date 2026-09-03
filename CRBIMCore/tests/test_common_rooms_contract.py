from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_common_command_ids_are_registered_by_one_shared_helper():
    source = (ROOT / "CRBIMCore" / "commands" / "common_rooms.py").read_text(encoding="utf-8")
    for command_id in ("CRBIM_SelectRoom", "CRBIM_RoomInfo", "CRBIM_NameRoom", "CRBIM_RoomGuide"):
        assert command_id in source
    assert "if command_id in available" in source


def test_both_workbenches_import_same_common_registration_helper():
    fa = (ROOT / "FacilArquitecturaWB" / "InitGui.py").read_text(encoding="utf-8")
    electric = (ROOT / "ElectricCR" / "InitGui.py").read_text(encoding="utf-8")
    needle = "from CRBIMCore.commands.common_rooms import ensure_common_room_commands_registered"
    assert needle in fa
    assert needle in electric
    assert '"Espacios y Recintos"' in fa
    assert '"Espacios y Recintos"' in electric


def test_electric_toolbar_keeps_protected_polygonal_producer_visible():
    source = (ROOT / "ElectricCR" / "InitGui.py").read_text(encoding="utf-8")
    assert "ElectricCR_Areas_AreaPorClick" in source
    assert "ElectricCR_Areas_RectFromBoundaryLines" in source
    assert "ElectricCR_Areas_PoligonosRecintosDesdeArchWalls" in source
    producer = (ROOT / "Areas" / "PoligonosRecintosDesdeArchWalls.FCMacro").read_text(encoding="utf-8")
    assert "Draft.make_wire" in producer
    assert "MakeFace" in producer
    assert "FA_SourceWalls" in producer
