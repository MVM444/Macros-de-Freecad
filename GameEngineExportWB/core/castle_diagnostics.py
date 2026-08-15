"""Castle Model Viewer diagnostics reusable from FreeCAD, CLI or MCP.

The module deliberately has no FreeCAD or Qt imports.  User interfaces are
adapters around :func:`run_diagnostic`, which always treats the source X3D as
read-only and writes results under a separate ``_castle_debug`` directory.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional, Sequence


SCHEMA_VERSION = "1.0"
DIAGNOSTIC_VERSION = "2026-08-15-castle-diagnostics-v2"
VALID_MODES = {"analyze", "interactive", "capture"}


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _checked_file(path, label: str) -> Path:
    value = Path(str(path or "")).expanduser()
    if not value.is_file():
        raise FileNotFoundError(label + " not found: " + str(value))
    return value.resolve()


def _source_fingerprint(path: Path) -> Dict[str, int]:
    stat_result = path.stat()
    return {
        "size_bytes": int(stat_result.st_size),
        "mtime_ns": int(stat_result.st_mtime_ns),
    }


def _emit(log_callback, level: str, message: str) -> None:
    if log_callback is not None:
        log_callback(str(level), str(message))


def find_castle_converter(viewer_path) -> Optional[Path]:
    """Find ``castle-model-converter`` beside the configured viewer."""
    if not viewer_path:
        return None
    viewer = Path(str(viewer_path)).expanduser()
    suffix = viewer.suffix if viewer.suffix.lower() == ".exe" else ""
    names = ["castle-model-converter" + suffix, "castle-model-converter"]
    for name in names:
        candidate = viewer.parent / name
        if candidate.is_file():
            return candidate.resolve()
    return None


def diagnostic_paths(x3d_path, run_id: Optional[str] = None) -> Dict[str, Path]:
    """Return deterministic output paths without creating or changing files."""
    source = Path(x3d_path)
    stamp = str(run_id or _timestamp())
    prefix = source.stem + "_" + stamp
    folder = source.parent / "_castle_debug"
    return {
        "folder": folder,
        "analysis_base": folder / (prefix + ".x3d"),
        "manifest": folder / (prefix + ".diagnostic.json"),
        "summary": folder / (prefix + ".summary.md"),
        "validation": folder / (prefix + ".validation.txt"),
        "castle_log": folder / (prefix + ".castle.log"),
        "screenshot": folder / (prefix + ".png"),
    }


def build_viewer_command(
    viewer_path,
    x3d_path,
    mode: str = "interactive",
    viewpoint: str = "GameStart",
    width: int = 1600,
    height: int = 900,
    anti_alias: int = 4,
    shader_debug: bool = True,
    screenshot_path=None,
) -> list:
    """Build a Castle command using only documented command-line options."""
    if mode not in {"interactive", "capture"}:
        raise ValueError("Viewer mode must be interactive or capture")
    command = [str(viewer_path), str(x3d_path)]
    if shader_debug:
        command.append("--debug-log-shaders")
    if mode == "capture":
        if screenshot_path is None:
            raise ValueError("screenshot_path is required in capture mode")
        command.extend(
            [
                "--viewpoint",
                str(viewpoint or "GameStart"),
                "--geometry",
                str(max(320, int(width))) + "x" + str(max(240, int(height))),
                "--anti-alias",
                str(max(0, min(4, int(anti_alias)))),
                "--screenshot",
                "0",
                str(screenshot_path),
            ]
        )
    return command


def _run_validation(converter: Path, x3d: Path, output_path: Path, timeout: int) -> Dict[str, object]:
    command = [str(converter), str(x3d), "--validate"]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=max(10, int(timeout)),
            check=False,
        )
        text = completed.stdout or ""
        output_path.write_text(text, encoding="utf-8", errors="replace")
        return {
            "status": "completed",
            "return_code": int(completed.returncode),
            "command": command,
            "log": str(output_path),
        }
    except subprocess.TimeoutExpired as exc:
        text = str(getattr(exc, "stdout", "") or "") + "\nValidation timed out.\n"
        output_path.write_text(text, encoding="utf-8", errors="replace")
        return {"status": "timeout", "command": command, "log": str(output_path)}
    except Exception as exc:
        output_path.write_text(str(exc) + "\n", encoding="utf-8")
        return {"status": "failed", "error": str(exc), "command": command, "log": str(output_path)}


def default_castle_log_path(viewer_path) -> Optional[Path]:
    """Return the standard Castle GUI log path when it is predictable."""
    app_name = Path(str(viewer_path)).stem
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            return Path(local_app_data) / app_name / (app_name + ".log")
    home = Path.home()
    if home:
        return home / ".config" / app_name / (app_name + ".log")
    return None


def _mirror_castle_log(process, source: Optional[Path], destination: Path, old_mtime_ns) -> None:
    process.wait()
    if source is None or not source.is_file():
        return
    source_stat = source.stat()
    if old_mtime_ns is not None and source_stat.st_mtime_ns <= old_mtime_ns:
        return
    if source_stat.st_size > 0:
        shutil.copyfile(str(source), str(destination))


def _start_viewer(command: Sequence[str], log_path: Path) -> Dict[str, object]:
    fallback_log = default_castle_log_path(command[0])
    fallback_mtime = None
    if fallback_log is not None and fallback_log.is_file():
        fallback_mtime = fallback_log.stat().st_mtime_ns

    log_handle = log_path.open("w", encoding="utf-8", errors="replace")
    try:
        process = subprocess.Popen(
            list(command),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )
    finally:
        log_handle.close()

    monitor = threading.Thread(
        target=_mirror_castle_log,
        args=(process, fallback_log, log_path, fallback_mtime),
        name="GameExportCastleLog-" + str(process.pid),
        daemon=True,
    )
    monitor.start()
    return {
        "status": "started",
        "pid": int(process.pid),
        "command": list(command),
        "log": str(log_path),
        "native_log": str(fallback_log) if fallback_log is not None else "",
        "log_status": "pending_until_castle_exits",
    }


def _recommendations(analysis: Dict[str, object]) -> list:
    lights = analysis.get("lights", {}) if isinstance(analysis, dict) else {}
    counts = lights.get("counts", {}) if isinstance(lights, dict) else {}
    total_local = int(counts.get("PointLight", 0) or 0) + int(counts.get("SpotLight", 0) or 0)
    recommendations = []
    if total_local > 16:
        recommendations.append(
            {
                "code": "many_local_lights",
                "message": "Many local lights may affect the same shape.",
                "castle_test": "View -> Max Lights Per Shape -> 8",
                "suggested_value": 8,
            }
        )
    summary = analysis.get("summary", {}) if isinstance(analysis, dict) else {}
    if int(summary.get("duplicate_def_names", 0) or 0):
        recommendations.append(
            {
                "code": "duplicate_def_names",
                "message": "Duplicate DEF names should be made unique before final delivery.",
            }
        )
    return recommendations


def _write_summary(manifest: Dict[str, object], path: Path) -> None:
    analysis = manifest.get("analysis", {}) or {}
    summary = analysis.get("summary", {}) if isinstance(analysis, dict) else {}
    counts = (analysis.get("lights", {}) or {}).get("counts", {}) if isinstance(analysis, dict) else {}
    lines = [
        "# Diagnostico Castle",
        "",
        "- Schema: " + str(manifest.get("schema_version", "")),
        "- Version: " + str(manifest.get("diagnostic_version", "")),
        "- X3D: `" + str(manifest.get("x3d", "")) + "`",
        "- Modo: " + str(manifest.get("mode", "")),
        "- Validacion: " + str((manifest.get("validation", {}) or {}).get("status", "disabled")),
        "- Castle: " + str((manifest.get("castle", {}) or {}).get("status", "not_started")),
        "- Shapes: " + str(summary.get("shapes", 0)),
        "- Triangulos aproximados: " + str(summary.get("triangles_approx", 0)),
        "- PointLight: " + str(counts.get("PointLight", 0)),
        "- SpotLight: " + str(counts.get("SpotLight", 0)),
        "- DirectionalLight: " + str(counts.get("DirectionalLight", 0)),
        "- DEF duplicados: " + str(summary.get("duplicate_def_names", 0)),
        "",
        "## Recomendaciones",
        "",
    ]
    recommendations = manifest.get("recommendations", []) or []
    if recommendations:
        for item in recommendations:
            lines.append("- " + str(item.get("message", "")))
            if item.get("castle_test"):
                lines.append("  - Prueba Castle: `" + str(item["castle_test"]) + "`")
    else:
        lines.append("- No se generaron recomendaciones automaticas.")
    lines.extend(["", "El diagnostico no modifica el FCStd ni el X3D original.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run_diagnostic(
    x3d_path,
    viewer_path=None,
    mode: str = "interactive",
    validate: bool = True,
    shader_debug: bool = True,
    viewpoint: str = "GameStart",
    width: int = 1600,
    height: int = 900,
    anti_alias: int = 4,
    top_n: int = 20,
    progress_callback: Optional[Callable[[int, int], bool]] = None,
    analyzer_module=None,
    validation_timeout: int = 300,
    run_id: Optional[str] = None,
    document: Optional[str] = None,
    log_callback: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, object]:
    """Analyze an X3D and optionally validate or open it with Castle.

    This is the stable entry point intended for FreeCAD, tests and MCP.
    """
    if mode not in VALID_MODES:
        raise ValueError("Unsupported diagnostic mode: " + str(mode))
    x3d = _checked_file(x3d_path, "X3D")
    source_before = _source_fingerprint(x3d)
    warnings = []
    viewer = None
    if viewer_path:
        try:
            viewer = _checked_file(viewer_path, "Castle Model Viewer")
        except FileNotFoundError:
            if mode != "analyze":
                raise
            warnings.append("Configured Castle Model Viewer was not found; validation was skipped.")
    if mode != "analyze" and viewer is None:
        raise FileNotFoundError("Castle Model Viewer path is required")

    paths = diagnostic_paths(x3d, run_id=run_id)
    paths["folder"].mkdir(parents=True, exist_ok=True)
    _emit(log_callback, "INFO", "Castle diagnostics started: " + str(x3d))
    _emit(log_callback, "DEBUG", "Diagnostic mode: " + mode)
    _emit(log_callback, "DEBUG", "Diagnostic folder: " + str(paths["folder"]))

    if analyzer_module is None:
        from . import x3d_analyzer as analyzer_module

    analysis = analyzer_module.analyze_x3d(
        x3d,
        top_n=max(1, int(top_n)),
        progress_callback=progress_callback,
    )
    analysis_json, analysis_markdown = analyzer_module.write_reports(
        analysis, paths["analysis_base"]
    )
    analysis_json = Path(analysis_json).resolve()
    analysis_markdown = Path(analysis_markdown).resolve()
    debug_folder = paths["folder"].resolve()
    if analysis_json.parent != debug_folder or analysis_markdown.parent != debug_folder:
        raise RuntimeError("X3D analyzer reports must be written inside _castle_debug")
    _emit(log_callback, "INFO", "X3D analysis completed")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "success": True,
        "operation": "castle_diagnostics",
        "generated_utc": _utc_now(),
        "document": str(document or ""),
        "mode": mode,
        "x3d": str(x3d),
        "source_unchanged": True,
        "source": source_before,
        "analysis": analysis,
        "recommendations": _recommendations(analysis),
        "warnings": warnings,
        "settings": {
            "validate": bool(validate),
            "shader_debug": bool(shader_debug),
            "viewpoint": str(viewpoint or "GameStart"),
            "width": int(width),
            "height": int(height),
            "anti_alias": int(anti_alias),
        },
        "outputs": {
            "folder": str(paths["folder"]),
            "analysis_json": str(analysis_json),
            "analysis_markdown": str(analysis_markdown),
            "manifest": str(paths["manifest"]),
            "summary": str(paths["summary"]),
        },
    }

    converter = find_castle_converter(viewer) if viewer else None
    if validate:
        if converter is None:
            reason = "castle-model-converter not found beside the viewer"
            paths["validation"].write_text(reason + "\n", encoding="utf-8")
            manifest["validation"] = {
                "status": "skipped",
                "reason": reason,
                "log": str(paths["validation"]),
            }
            manifest["warnings"].append(reason)
            _emit(log_callback, "WARN", reason)
        else:
            _emit(log_callback, "INFO", "Validating with: " + str(converter))
            manifest["validation"] = _run_validation(
                converter, x3d, paths["validation"], validation_timeout
            )
            _emit(
                log_callback,
                "INFO",
                "Castle validation status: " + str(manifest["validation"].get("status", "")),
            )
        manifest["outputs"]["validation"] = str(paths["validation"])
    else:
        manifest["validation"] = {"status": "disabled"}

    if viewer is not None and mode != "analyze":
        command = build_viewer_command(
            viewer,
            x3d,
            mode=mode,
            viewpoint=viewpoint,
            width=width,
            height=height,
            anti_alias=anti_alias,
            shader_debug=shader_debug,
            screenshot_path=paths["screenshot"] if mode == "capture" else None,
        )
        _emit(log_callback, "INFO", "Launching Castle: " + " ".join(command))
        manifest["castle"] = _start_viewer(command, paths["castle_log"])
        manifest["outputs"]["castle_log"] = str(paths["castle_log"])
        if mode == "capture":
            manifest["outputs"]["screenshot"] = str(paths["screenshot"])
            _emit(log_callback, "INFO", "Capture requested: " + str(paths["screenshot"]))

    source_after = _source_fingerprint(x3d)
    manifest["source_unchanged"] = source_before == source_after
    if not manifest["source_unchanged"]:
        manifest["warnings"].append("The source X3D metadata changed during diagnostics.")
        _emit(log_callback, "WARN", "Source X3D metadata changed during diagnostics")

    _write_summary(manifest, paths["summary"])
    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True),
        encoding="utf-8",
    )
    _emit(log_callback, "INFO", "Castle diagnostic manifest: " + str(paths["manifest"]))
    return manifest


__all__ = [
    "DIAGNOSTIC_VERSION",
    "SCHEMA_VERSION",
    "build_viewer_command",
    "diagnostic_paths",
    "find_castle_converter",
    "run_diagnostic",
]
