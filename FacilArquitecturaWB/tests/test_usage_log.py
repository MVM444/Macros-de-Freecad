"""Pruebas del historial local de FacilArquitecturaWB.

Proposito: verificar acumulados, eventos secuenciales y clasificacion sin FreeCAD.
Version: 1.0
Fecha y hora: 2026-09-01 10:42 America/Costa_Rica.
"""

import importlib.util
import json
from pathlib import Path


def _load_module():
    source = Path(__file__).resolve().with_name("FA_usage_log.py")
    if not source.exists():
        source = Path(__file__).resolve().parents[1] / "usage_log.py"
    spec = importlib.util.spec_from_file_location("fa_usage_log_test_target", source)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_usage_log_aggregate_and_sequence(tmp_path):
    usage = _load_module()
    usage.LOGS_DIR = str(tmp_path / "logs")
    usage.STATS_PATH = str(tmp_path / "logs" / "tool_usage.json")
    usage.EVENTS_PATH = str(tmp_path / "logs" / "tool_events.jsonl")
    usage._EVENT_SEQ = 0
    usage._LAST_EVENT = None

    usage.log_tool("FA_CreateWallsFromSketch", {"group": "FA Estructura BIM", "source": "test"})
    usage.log_tool("Draft_Move", {"source": "test"})

    stats = usage.get_stats()
    assert stats["tools"]["FA_CreateWallsFromSketch"]["count"] == 1
    assert stats["tools"]["FA_CreateWallsFromSketch"]["kind"] == "fa_command"
    assert stats["tools"]["Draft_Move"]["kind"] == "draft"

    events = [json.loads(line) for line in Path(usage.EVENTS_PATH).read_text(encoding="utf-8").splitlines()]
    assert [event["sequence"] for event in events] == [1, 2]
    assert events[1]["previous_tool_id"] == "FA_CreateWallsFromSketch"
    assert events[0]["logger_workbench_id"] == "FacilArquitecturaWorkbench"
