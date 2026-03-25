# -*- coding: utf-8 -*-
"""Utilidad de registro de chat para ElectricCR.

Guarda entradas del chat (rol + texto) en JSONL por día y permite listar y
restaurar sesiones. Ubicación: ElectricCR/logs.
"""

import os
import json
import datetime as _dt


BASE_DIR = os.path.dirname(__file__)
LOGS_DIR = os.path.join(BASE_DIR, "logs")


def _ensure_logs_dir() -> str:
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
    except Exception:
        pass
    return LOGS_DIR


def _today_name() -> str:
    return _dt.datetime.now().strftime("chat_%Y%m%d.jsonl")


def current_session_path() -> str:
    _ensure_logs_dir()
    return os.path.join(LOGS_DIR, _today_name())


def append_entry(role: str, text: str, meta: dict | None = None) -> str:
    """Agregar una entrada al archivo de sesión actual. Devuelve la ruta."""
    _ensure_logs_dir()
    entry = {
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "role": (role or "user").strip(),
        "text": text or "",
        "meta": meta or {},
    }
    path = current_session_path()
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def list_sessions() -> list[str]:
    _ensure_logs_dir()
    try:
        files = [f for f in os.listdir(LOGS_DIR) if f.lower().endswith(".jsonl")]
        files.sort()
        return [os.path.join(LOGS_DIR, f) for f in files]
    except Exception:
        return []


def load_session(path: str) -> list[dict]:
    out: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def export_session(src_path: str, dst_path: str) -> bool:
    try:
        with open(src_path, "rb") as s, open(dst_path, "wb") as d:
            d.write(s.read())
        return True
    except Exception:
        return False

