# -*- coding: utf-8 -*-
"""Usage logging for ElectricCR.

Writes per-tool usage counts to ElectricCR/logs/tool_usage.json.
"""

import os
import json
import datetime as _dt

BASE_DIR = os.path.dirname(__file__)
LOGS_DIR = os.path.join(BASE_DIR, "logs")
STATS_PATH = os.path.join(LOGS_DIR, "tool_usage.json")


def _ensure_logs_dir() -> str:
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
    except Exception:
        pass
    return LOGS_DIR


def _now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _load_stats() -> dict:
    try:
        if os.path.exists(STATS_PATH):
            with open(STATS_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _save_stats(data: dict) -> None:
    try:
        _ensure_logs_dir()
        with open(STATS_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=True, indent=2)
    except Exception:
        pass


def log_tool(tool_id: str, meta: dict | None = None) -> None:
    if not tool_id:
        return
    try:
        data = _load_stats()
        tools = data.get("tools")
        if not isinstance(tools, dict):
            tools = {}
        rec = tools.get(tool_id)
        if not isinstance(rec, dict):
            rec = {"count": 0}
        try:
            rec["count"] = int(rec.get("count", 0)) + 1
        except Exception:
            rec["count"] = 1
        rec["last_ts"] = _now_iso()
        if meta:
            try:
                rec["last_meta"] = meta
            except Exception:
                pass
        tools[tool_id] = rec
        data["version"] = 1
        data["updated"] = rec["last_ts"]
        data["tools"] = tools
        _save_stats(data)
    except Exception:
        pass


def get_stats() -> dict:
    return _load_stats()
