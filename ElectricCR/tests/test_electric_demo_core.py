# -*- coding: utf-8 -*-
"""Pure tests for ElectricCR canonical demo specification.

Version: 0.1.0
Date/time: 2026-09-09 22:09 America/Costa_Rica
"""

import json
import os
import re
import sys
import uuid

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ElectricCR.electriccr.demo.electric_demo_core import build_fixed_demo_spec, demo_summary


def _space_contains(space, placement):
    return (
        space["x"] < placement["x"] < space["x"] + space["length"]
        and space["y"] < placement["y"] < space["y"] + space["width"]
        and space["z"] < placement["z"] < space["z"] + space["height"]
    )


def test_spec_is_deterministic_and_json_serializable():
    a = build_fixed_demo_spec()
    b = build_fixed_demo_spec()
    assert a == b
    assert json.loads(json.dumps(a, sort_keys=True)) == a


def test_canonical_counts_and_unique_identity():
    spec = build_fixed_demo_spec()
    assert len(spec["spaces"]) == 2
    assert len(spec["walls"]) == 5
    assert len(spec["devices"]) == 7
    ids = [item["id"] for item in spec["devices"]]
    uids = [item["element_uid"] for item in spec["devices"]]
    assert len(ids) == len(set(ids))
    assert len(uids) == len(set(uids))
    for value in uids:
        uuid.UUID(value)


def test_every_device_point_is_inside_declared_space():
    spec = build_fixed_demo_spec()
    spaces = {item["key"]: item for item in spec["spaces"]}
    for device in spec["devices"]:
        assert device["space_key"] in spaces
        assert _space_contains(spaces[device["space_key"]], device["placement"]), device["id"]


def test_host_keys_and_internal_names_are_valid():
    spec = build_fixed_demo_spec()
    wall_keys = {item["key"] for item in spec["walls"]}
    for device in spec["devices"]:
        if device["host_key"]:
            assert device["host_key"] in wall_keys
        assert re.fullmatch(r"[A-Za-z0-9_]+", device["internal_name"])


def test_registry_families_exercised():
    spec = build_fixed_demo_spec()
    keys = [item["key_registro"] for item in spec["devices"]]
    assert keys.count("Tomacorriente_120V") == 2
    assert keys.count("Apagador_Simple") == 2
    assert keys.count("Luminaria LED Redonda 1000lm") == 2
    assert keys.count("Sensor_Humo") == 1


def test_scope_is_explicitly_a1_only_v01():
    scope = build_fixed_demo_spec()["scope"]
    assert scope == {
        "ifc_export": False,
        "circuit_objects": False,
        "control_objects": False,
        "random_variants": False,
    }


def test_summary_matches_spec():
    summary = demo_summary()
    assert summary["spaces"] == 2
    assert summary["walls"] == 5
    assert summary["devices"] == 7
    assert len(summary["element_uids"]) == 7
