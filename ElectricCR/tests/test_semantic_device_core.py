"""Pure regression tests for the semantic luminaire projection contract."""

import os
import sys


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ElectricCR.electriccr.semantic import device_core


def test_complete_projection_is_json_compatible_and_deterministic():
    first = device_core.build_lighting_projection(
        "78607af3-84af-4eed-bdc7-e3aaaf605ac2",
        "Sala de Espera",
        "IL-TEST",
        "S1",
    )
    second = device_core.build_lighting_projection(
        "78607af3-84af-4eed-bdc7-e3aaaf605ac2",
        "Sala de Espera",
        "IL-TEST",
        "S1",
    )
    assert first == second
    assert first["status"] == device_core.STATUS_READY
    assert first["path"] == [
        "electrico",
        "Iluminacion",
        "Circuitos",
        "IL-TEST",
        "Recintos",
        "Sala de Espera",
        "Apagadores",
        "S1",
        "Luminarias",
    ]
    assert len({node["key"] for node in first["nodes"]}) == 8


def test_incomplete_projection_does_not_guess_missing_authority():
    result = device_core.build_lighting_projection("uid", "", "IL-TEST", "")
    assert result["status"] == device_core.STATUS_INCOMPLETE
    assert result["path"] == [] and result["nodes"] == []
    assert result["missing"] == ["Space", "Apagador"]


if __name__ == "__main__":
    test_complete_projection_is_json_compatible_and_deterministic()
    test_incomplete_projection_does_not_guess_missing_authority()
    print("ECR_SEMANTIC_DEVICE_CORE_OK deterministic=1 incomplete_safe=1")
