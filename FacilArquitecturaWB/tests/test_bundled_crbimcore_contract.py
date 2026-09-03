"""Static release contract for the self-contained CRBIMCore mirror."""

from pathlib import Path


def test_bundled_crbimcore_runtime_is_present():
    root = Path(__file__).resolve().parents[1]
    required = [
        "_bundled/__init__.py",
        "_bundled/CRBIMCore/__init__.py",
        "_bundled/CRBIMCore/room_resolver_core.py",
        "_bundled/CRBIMCore/room_operations_core.py",
        "_bundled/CRBIMCore/freecad_room_adapter.py",
        "_bundled/CRBIMCore/freecad_room_operations.py",
        "_bundled/CRBIMCore/commands/__init__.py",
        "_bundled/CRBIMCore/commands/common_rooms.py",
        "_bundled/CRBIMCore/resources/icons/CRBIM_SelectRoom.svg",
        "_bundled/CRBIMCore/resources/icons/CRBIM_RoomInfo.svg",
        "_bundled/CRBIMCore/resources/icons/CRBIM_NameRoom.svg",
        "_bundled/CRBIMCore/resources/icons/CRBIM_RoomGuide.svg",
    ]
    missing = [item for item in required if not (root / item).exists()]
    assert not missing, "Missing bundled runtime: " + ", ".join(missing)


def test_initgui_has_external_then_bundled_fallback():
    root = Path(__file__).resolve().parents[1]
    text = (root / "InitGui.py").read_text(encoding="utf-8")
    assert 'importlib.import_module("CRBIMCore.commands.common_rooms")' in text
    assert '._bundled.CRBIMCore.commands.common_rooms' in text
