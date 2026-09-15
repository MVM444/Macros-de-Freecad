from __future__ import annotations

import json

from core.demo_building_core import CANONICAL_SEED, build_demo_spec, build_two_storey_demo_spec


def test_canonical_demo_contract():
    spec = build_demo_spec(CANONICAL_SEED, randomized=False)
    assert spec["footprint"] == {"width_mm": 6000.0, "depth_mm": 8000.0}
    assert spec["walls"]["height_mm"] == 3000.0
    assert len(spec["walls"]["exterior_segments"]) == 4
    assert len(spec["walls"]["interior_segments"]) == 1
    assert len(spec["openings"]["doors"]) == 2
    assert len(spec["openings"]["windows"]) == 6
    assert spec["roof"]["pitch_deg"] == 22.0
    json.dumps(spec, sort_keys=True)


def test_random_demo_is_reproducible_and_varies_by_seed():
    a = build_demo_spec(12345, randomized=True)
    b = build_demo_spec(12345, randomized=True)
    c = build_demo_spec(12346, randomized=True)
    assert a == b
    assert a != c
    assert a["randomized"] is True
    assert a["seed"] == 12345


def test_random_demo_openings_stay_inside_footprint():
    for seed in range(1, 250):
        spec = build_demo_spec(seed, randomized=True)
        width = spec["footprint"]["width_mm"]
        depth = spec["footprint"]["depth_mm"]
        for seg in spec["openings"]["doors"] + spec["openings"]["windows"]:
            for x, y in (seg["start_mm"], seg["end_mm"]):
                assert -1e-9 <= x <= width + 1e-9
                assert -1e-9 <= y <= depth + 1e-9


def test_demo_v2_has_spaces_and_600_ceiling_spec():
    spec = build_demo_spec()
    assert len(spec["rooms"]["items"]) == 2
    assert [room["name"] for room in spec["rooms"]["items"]] == ["Estar-comedor", "Dormitorio"]
    assert all(room["area_m2"] >= 2.0 for room in spec["rooms"]["items"])
    assert spec["ceiling"]["module_mm"] == 600.0
    assert spec["ceiling"]["elevation_mm"] == spec["rooms"]["items"][0]["space_height_mm"]


def test_demo_v2_random_rooms_are_reproducible():
    first = build_demo_spec(424242, True)
    second = build_demo_spec(424242, True)
    assert first["rooms"] == second["rooms"]
    assert first["ceiling"] == second["ceiling"]


def test_demo_site_garden_spec_is_stable_and_flat():
    spec = build_demo_spec(CANONICAL_SEED, randomized=False)
    assert spec["site"]["garden_enabled"] is True
    assert spec["site"]["terrain_margin_mm"] == 2500.0
    assert spec["site"]["terrain_variation_mm"] == 0.0
    assert spec["site"]["landscape_role"] == "garden"


def test_two_storey_demo_contract_is_json_compatible_and_has_two_native_level_specs():
    spec = build_two_storey_demo_spec()
    assert spec["building_mode"] == "two_storey"
    assert spec["storey_height_mm"] == 3000.0
    assert [item["level_name"] for item in spec["storeys"]] == ["Nivel 00", "Nivel 01"]
    assert [item["elevation_mm"] for item in spec["storeys"]] == [0.0, 3000.0]
    assert all(item["spec"]["footprint"] == {"width_mm": 6000.0, "depth_mm": 8000.0} for item in spec["storeys"])
    ground = spec["storeys"][0]["spec"]
    upper = spec["storeys"][1]["spec"]
    assert ground["site"]["garden_enabled"] is True
    assert upper["site"]["garden_enabled"] is False
    assert ground["walls"]["interior_segments"] != upper["walls"]["interior_segments"]
    assert len(upper["walls"]["interior_segments"]) == 2
    assert len(upper["rooms"]["items"]) == 3
    assert [room["name"] for room in upper["rooms"]["items"]] == [
        "Distribuidor y futura escalera",
        "Dormitorio principal",
        "Dormitorio secundario",
    ]
    assert len(upper["openings"]["doors"]) == 2
    assert all(door["start_mm"][1] == 3500.0 and door["end_mm"][1] == 3500.0 for door in upper["openings"]["doors"])
    assert all(not (door["start_mm"][1] == 0.0 and door["end_mm"][1] == 0.0) for door in upper["openings"]["doors"])
    assert len(upper["openings"]["windows"]) == 5
    assert upper["openings"]["windows"] != ground["openings"]["windows"]
    assert spec["stair"]["native_required"] is True
    assert spec["stair"]["reserved_zone"]["room_id"] == "R01"
    assert spec["stair"]["status"] == "canonical_demo"
    assert spec["stair"]["path_points_mm"] == [[5200.0, 4200.0], [5200.0, 1900.0], [2700.0, 1900.0]]
    assert spec["stair"]["width_mm"] == 1000.0
    assert spec["stair"]["railings_mode"] == "hidden_native_freecad_1_1_3_multisegment"
    assert spec["stair"]["cut_upper_slab"] is True
    assert spec["stair"]["layout_revision"] == "rearward_front_distributor_v2"
    assert spec["stair"]["headroom_mm"] == 2100.0
    assert spec["stair"]["clearance_preview"] is True
    assert spec["stair"]["apply_ceiling_exclusion"] is True
    assert spec["stair"]["clearance_geometry_revision"] == "l_union_v2"
    assert spec["stair"]["create_opening_liner"] is True
    assert spec["stair"]["opening_liner_mode"] == "side_walls_open_ends"
    assert spec["stair"]["opening_liner_thickness_mm"] == 100.0
    assert spec["stair"]["create_opening_liner"] is True
    assert spec["stair"]["opening_liner_thickness_mm"] == 100.0
    json.dumps(spec, sort_keys=True)

