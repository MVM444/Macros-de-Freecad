# -*- coding: utf-8 -*-
from __future__ import annotations

"""Usage logging for ElectricCR.

Writes aggregate counts to ElectricCR/logs/tool_usage.json and an event stream
to ElectricCR/logs/tool_events.jsonl for future workflow analysis.
"""

import datetime as _dt
import json
import os
import socket
import uuid

BASE_DIR = os.path.dirname(__file__)
LOGS_DIR = os.path.join(BASE_DIR, "logs")
STATS_PATH = os.path.join(LOGS_DIR, "tool_usage.json")
EVENTS_PATH = os.path.join(LOGS_DIR, "tool_events.jsonl")

SESSION_ID = os.environ.get("ELECTRICCR_SESSION_ID") or uuid.uuid4().hex[:12]
SESSION_STARTED = _dt.datetime.now().isoformat(timespec="seconds")
HOSTNAME = socket.gethostname()

_EVENT_SEQ = 0
_LAST_EVENT = None


def _ensure_logs_dir() -> str:
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
    except Exception:
        pass
    return LOGS_DIR


def _now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _parse_iso(value: str):
    try:
        return _dt.datetime.fromisoformat(str(value))
    except Exception:
        return None


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


def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


def _clean_meta(meta) -> dict:
    if not isinstance(meta, dict):
        return {}
    return _jsonable(meta)


def _rel_macro_path(path: str) -> str:
    text = str(path or "").replace("\\", "/")
    marker = "Macros-de-Freecad/"
    if marker in text:
        return text.split(marker, 1)[1]
    return os.path.basename(text)


def _tool_context(tool_id: str, meta: dict) -> dict:
    context = {
        "kind": "other",
        "group": "Otros",
        "label": str(meta.get("label") or meta.get("text") or meta.get("menu") or tool_id),
        "command": str(meta.get("cmd") or tool_id),
    }

    if tool_id.startswith("macro:"):
        macro_path = str(meta.get("macro") or tool_id[len("macro:"):])
        rel_path = _rel_macro_path(macro_path)
        group = rel_path.split("/", 1)[0] if "/" in rel_path else "Raiz"
        label = str(meta.get("label") or os.path.splitext(os.path.basename(rel_path))[0])
        context.update({
            "kind": "macro",
            "group": group,
            "label": label,
            "macro": macro_path,
            "macro_rel": rel_path,
        })
    elif tool_id.startswith("Draft_"):
        context.update({"kind": "draft", "group": "Draft heredado"})
    elif tool_id.startswith("BIM_") or tool_id.startswith("Arch_"):
        context.update({"kind": "bim_arch", "group": "BIM/Arch heredado"})
    elif tool_id.startswith("ElectricCR_"):
        context.update({"kind": "electriccr", "group": "ElectricCR sistema"})

    source = meta.get("source")
    if source:
        context["source"] = str(source)
    return context


def _active_document_context() -> dict:
    try:
        import FreeCAD as App
    except Exception:
        return {}
    try:
        doc = getattr(App, "ActiveDocument", None)
    except Exception:
        doc = None
    if doc is None:
        return {}

    out = {}
    for attr, key in (("Name", "document_name"), ("Label", "document_label"), ("FileName", "document_file")):
        try:
            value = getattr(doc, attr, "")
        except Exception:
            value = ""
        if value:
            out[key] = str(value)
    return out


def _active_workbench_context() -> dict:
    try:
        import FreeCADGui as Gui
    except Exception:
        return {}
    try:
        wb = Gui.activeWorkbench()
    except Exception:
        wb = None
    if wb is None:
        return {}
    try:
        name = wb.__class__.__name__
    except Exception:
        name = ""
    try:
        menu_text = getattr(wb, "MenuText", "")
    except Exception:
        menu_text = ""
    out = {}
    if name:
        out["workbench_class"] = str(name)
    if menu_text:
        out["workbench_label"] = str(menu_text)
    return out


def _append_event(tool_id: str, meta: dict, ts: str) -> None:
    global _EVENT_SEQ, _LAST_EVENT

    try:
        _EVENT_SEQ += 1
        event = {
            "version": 1,
            "ts": ts,
            "session_id": SESSION_ID,
            "session_started": SESSION_STARTED,
            "sequence": _EVENT_SEQ,
            "host": HOSTNAME,
            "tool_id": tool_id,
            "meta": meta,
        }
        event.update(_tool_context(tool_id, meta))
        event.update(_active_document_context())
        event.update(_active_workbench_context())

        if _LAST_EVENT:
            previous_ts = _parse_iso(_LAST_EVENT.get("ts", ""))
            current_ts = _parse_iso(ts)
            seconds_since = None
            if previous_ts is not None and current_ts is not None:
                seconds_since = max(0.0, (current_ts - previous_ts).total_seconds())
            event["previous_tool_id"] = _LAST_EVENT.get("tool_id", "")
            event["previous_group"] = _LAST_EVENT.get("group", "")
            event["previous_label"] = _LAST_EVENT.get("label", "")
            if seconds_since is not None:
                event["seconds_since_previous"] = seconds_since

        _ensure_logs_dir()
        with open(EVENTS_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

        _LAST_EVENT = {
            "ts": ts,
            "tool_id": event.get("tool_id", ""),
            "group": event.get("group", ""),
            "label": event.get("label", ""),
        }
    except Exception:
        pass


def log_tool(tool_id: str, meta=None) -> None:
    if not tool_id:
        return

    tool_id = str(tool_id)
    clean_meta = _clean_meta(meta)
    ts = _now_iso()

    try:
        data = _load_stats()
        tools = data.get("tools")
        if not isinstance(tools, dict):
            tools = {}
        rec = tools.get(tool_id)
        if not isinstance(rec, dict):
            rec = {"count": 0, "first_ts": ts}
        if not rec.get("first_ts"):
            rec["first_ts"] = ts
        try:
            rec["count"] = int(rec.get("count", 0)) + 1
        except Exception:
            rec["count"] = 1
        rec["last_ts"] = ts
        rec["last_session_id"] = SESSION_ID
        if clean_meta:
            rec["last_meta"] = clean_meta
        tools[tool_id] = rec
        data["version"] = 2
        data["updated"] = ts
        data["event_log"] = os.path.basename(EVENTS_PATH)
        data["last_session_id"] = SESSION_ID
        data["tools"] = tools
        _save_stats(data)
    except Exception:
        pass

    _append_event(tool_id, clean_meta, ts)


def get_stats() -> dict:
    return _load_stats()


def get_events_path() -> str:
    return EVENTS_PATH
