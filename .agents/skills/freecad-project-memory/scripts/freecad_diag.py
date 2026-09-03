# -*- coding: utf-8 -*-
"""
FreeCAD Project Memory - runtime diagnostic
Version: 0.1.0
Date: 2026-08-11 16:44 -06:00

Purpose:
- Read FreeCAD runtime state without modifying documents or preferences.
- Print one JSON record prefixed with [FREECAD-PROJECT-MEMORY].
- Intended to run inside FreeCAD, including through MCP execute_code.

Safety:
- Read-only.
- Does not save, close, create, delete, or modify document objects.
"""

from __future__ import print_function

import hashlib
import json
import os
import platform
import socket
import sys
from datetime import datetime

import FreeCAD as App

try:
    import FreeCADGui as Gui
except Exception:
    Gui = None


PREFIX = "[FREECAD-PROJECT-MEMORY] "
PACKAGE_PREFIXES = (
    "ElectricCR",
    "MEPWorkbenchCR",
    "GameEngineExportWB",
    "FacilArquitecturaWB",
)


def _safe_call(func, default=None):
    try:
        return func()
    except Exception:
        return default


def _sha256(path):
    try:
        if not path or not os.path.isfile(path):
            return ""
        h = hashlib.sha256()
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _detect_qt():
    result = {
        "binding": "",
        "qt_version": "",
        "binding_version": "",
    }
    for name in ("PySide6", "PySide2", "PySide"):
        try:
            mod = __import__(name)
            result["binding"] = name
            result["binding_version"] = str(getattr(mod, "__version__", "") or "")
            try:
                qtcore = __import__(name + ".QtCore", fromlist=["QtCore"])
                result["qt_version"] = str(
                    getattr(qtcore, "qVersion", lambda: "")() or ""
                )
            except Exception:
                pass
            break
        except Exception:
            continue
    return result


def _active_workbench():
    if Gui is None:
        return ""
    try:
        wb = Gui.activeWorkbench()
        if wb is None:
            return ""
        for attr in ("name", "objectName"):
            member = getattr(wb, attr, None)
            if callable(member):
                value = member()
                if value:
                    return str(value)
        return str(wb)
    except Exception:
        return ""


def _registered_workbenches():
    if Gui is None:
        return []
    try:
        value = Gui.listWorkbenches() or {}
        if isinstance(value, dict):
            return sorted([str(x) for x in value.keys()])
        return sorted([str(x) for x in value])
    except Exception:
        return []


def _registered_commands():
    if Gui is None:
        return []
    try:
        return sorted([str(x) for x in (Gui.listCommands() or [])])
    except Exception:
        return []


def _module_info():
    modules = {}
    key_files = {}
    for name, module in list(sys.modules.items()):
        if not name.startswith(PACKAGE_PREFIXES):
            continue
        path = str(getattr(module, "__file__", "") or "")
        if not path:
            continue
        norm = os.path.normpath(os.path.abspath(path))
        modules[name] = norm
        digest = _sha256(norm)
        if digest:
            key_files[norm] = {
                "sha256": digest,
                "size": _safe_call(lambda p=norm: os.path.getsize(p), None),
                "mtime": _safe_call(lambda p=norm: os.path.getmtime(p), None),
            }
    return modules, key_files


def _macro_path():
    try:
        raw = App.ParamGet(
            "User parameter:BaseApp/Preferences/Macro"
        ).GetString("MacroPath", "")
    except Exception:
        raw = ""
    return str(raw or "")


def build_diagnostic():
    modules, key_files = _module_info()
    commands = _registered_commands()

    freecad_version = _safe_call(lambda: list(App.Version()), [])
    active_doc = ""
    try:
        if App.ActiveDocument is not None:
            active_doc = str(App.ActiveDocument.Name)
    except Exception:
        pass

    user_app_data = _safe_call(lambda: App.getUserAppDataDir(), "")
    user_macro_dir = _safe_call(lambda: App.getUserMacroDir(), "")

    command_summary = {
        "total": len(commands),
        "electriccr": [c for c in commands if c.startswith("ElectricCR_")],
        "mep_hvac": [c for c in commands if c.startswith("MEP_HVAC_")],
        "gameexport": [c for c in commands if c.startswith("GameEngineExport_")],
        "facilarq": [c for c in commands if c.startswith("Facil") or c.startswith("FA_")],
    }

    paths_for_onedrive = list(modules.values()) + [
        str(user_app_data or ""),
        str(user_macro_dir or ""),
        _macro_path(),
    ]
    onedrive_detected = any(
        "onedrive" in str(path).lower() for path in paths_for_onedrive
    )

    return {
        "schema_version": 1,
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "user": os.environ.get("USERNAME") or os.environ.get("USER") or "",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "freecad": {
            "version_tuple": freecad_version,
            "version_text": ".".join(str(x) for x in freecad_version[:3]),
        },
        "python": {
            "version": sys.version,
            "executable": sys.executable,
        },
        "qt": _detect_qt(),
        "active_workbench": _active_workbench(),
        "active_document": active_doc,
        "paths": {
            "user_app_data_dir": str(user_app_data or ""),
            "user_macro_dir": str(user_macro_dir or ""),
            "macro_path": _macro_path(),
        },
        "workbenches": _registered_workbenches(),
        "commands": command_summary,
        "modules": modules,
        "key_files": key_files,
        "onedrive_detected": bool(onedrive_detected),
    }


def main():
    data = build_diagnostic()
    print(PREFIX + json.dumps(data, ensure_ascii=True, sort_keys=True))
    return data


if __name__ == "__main__":
    main()
