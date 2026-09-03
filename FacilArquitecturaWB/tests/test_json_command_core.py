import json
import pytest
from json_command_core import SCHEMA_NAME, example_command, parse_command_text, validate_command


def test_example_is_valid():
    data = validate_command(example_command())
    assert data["schema"] == SCHEMA_NAME
    assert data["operations"][0]["op"] == "create_site_object"
    assert len(data["operations"]) == 3


def test_parse_rejects_snapshot_schema():
    with pytest.raises(ValueError):
        parse_command_text(json.dumps({"schema": "facil-arquitectura.snapshot", "schema_version": 1, "operations": []}))


def test_apply_elements_valid():
    payload = {
        "schema": SCHEMA_NAME,
        "schema_version": 1,
        "operations": [{"op": "apply_elements", "category": "windows", "records": [{"ElementID": "V-001"}]}],
    }
    assert validate_command(payload)["operations"][0]["category"] == "windows"


def test_create_demo_must_be_alone():
    payload = {
        "schema": SCHEMA_NAME,
        "schema_version": 1,
        "operations": [
            {"op": "create_demo", "specification": {"seed": 1}},
            {"op": "set_properties", "target": "Roof", "values": {"FA_Pitch": 30}},
        ],
    }
    with pytest.raises(ValueError):
        validate_command(payload)


def test_create_site_object_tree_valid():
    payload = {
        "schema": "facil-arquitectura.command",
        "schema_version": 1,
        "operations": [
            {
                "op": "create_site_object",
                "object_type": "tree",
                "name": "Tree_01",
                "label": "Arbol demo",
                "placement": {"x_mm": 1000, "y_mm": 2000, "z_mm": 0},
                "geometry": {
                    "height_mm": 4200,
                    "crown_diameter_mm": 2400,
                    "trunk_diameter_mm": 220,
                },
            }
        ],
    }
    data = validate_command(payload)
    op = data["operations"][0]
    assert op["op"] == "create_site_object"
    assert op["object_type"] == "tree"
    assert op["placement"]["x_mm"] == 1000.0
    assert op["plan_symbol"] is True


def test_create_site_object_rejects_bad_name():
    payload = {
        "schema": "facil-arquitectura.command",
        "schema_version": 1,
        "operations": [
            {
                "op": "create_site_object",
                "object_type": "tree",
                "name": "Árbol 01",
                "placement": {},
                "geometry": {
                    "height_mm": 4200,
                    "crown_diameter_mm": 2400,
                    "trunk_diameter_mm": 220,
                },
            }
        ],
    }
    import pytest
    with pytest.raises(ValueError):
        validate_command(payload)
