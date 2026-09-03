from __future__ import annotations

import json

import pytest

from core.demo_guided_core import (
    guided_progress_text,
    guided_step,
    guided_steps,
    guided_total_steps,
)


def test_guided_plan_is_stable_json_compatible_and_complete():
    steps = guided_steps()
    assert guided_total_steps() == 14
    assert [item["id"] for item in steps] == [
        "project",
        "wall_sources",
        "floor",
        "walls",
        "door_sources",
        "doors",
        "window_sources",
        "windows",
        "rooms",
        "spaces",
        "ceiling",
        "roof_source",
        "roof",
        "finalize",
    ]
    assert all(item["camera"] in {"top", "axon"} for item in steps)
    assert all(item["icon"].endswith(".svg") for item in steps)
    assert all(item.get("tool") for item in steps)
    assert guided_step(9)["icon"] == "detect_rooms.svg"
    assert guided_step(10)["icon"] == "bim_spaces.svg"
    for number in (6, 8, 13):
        step = guided_step(number)
        assert step["long_process"] is True
        assert "varios segundos" in step["duration_note"]
    assert guided_step(3)["icon"] == "site_floor_bim.svg"
    assert "jardin" in guided_step(3)["title"].lower()
    assert guided_step(5)["icon"] == "door_centerlines.svg"
    assert guided_step(7)["icon"] == "window_centerlines.svg"
    assert guided_step(11)["icon"] == "modular_ceiling.svg"
    assert guided_step(13)["icon"] == "roof_from_rectangle.svg"
    json.dumps(steps, sort_keys=True)


def test_guided_step_is_one_based_and_defensive():
    first = guided_step(1)
    assert first["id"] == "project"
    first["id"] = "changed"
    assert guided_step(1)["id"] == "project"
    with pytest.raises(ValueError):
        guided_step(0)
    with pytest.raises(ValueError):
        guided_step(15)


def test_guided_progress_text_tracks_start_middle_and_finish():
    assert guided_progress_text(0).startswith("Listo para iniciar")
    assert "Paso 4 de 14" in guided_progress_text(4)
    assert guided_progress_text(14) == "Demostracion completada | 14/14"
