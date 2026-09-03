# -*- coding: utf-8 -*-
"""Catalogo estructurado de macros ElectricCR.

Revision: 2026-08-12 16:35 America/Costa_Rica
FreeCAD: 1.1.3

The catalog is informational only. It never moves, deletes or executes a
macro. Manual review fields are preserved when the active registry is rebuilt.
"""

from __future__ import annotations

import ast
import datetime as _dt
import json
import os
import re
import tempfile


SCHEMA_VERSION = 1
PACKAGE_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(PACKAGE_DIR, os.pardir))
DATA_DIR = os.path.join(PACKAGE_DIR, "data")
CATALOG_PATH = os.path.join(DATA_DIR, "macros_catalog.json")
MARKDOWN_PATH = os.path.join(PACKAGE_DIR, "MACROS_CATALOGO.md")
GPT_DESCRIPTIONS_PATH = os.path.join(REPO_ROOT, "ElectricCR", "MACROS_DESCRIPCIONES_GPT.json")

MANUAL_STATUSES = ("SIN_REVISAR", "REVISAR", "REVISADA")
DECISIONS = ("SIN_DECISION", "MANTENER", "MEJORAR", "MOVER", "FUSIONAR", "OCULTAR", "ARCHIVAR")


def _now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _text(value) -> str:
    return str(value or "").strip()


def _description_is_generic(value: str, entry: dict, path: str) -> bool:
    text = _text(value)
    if not text or text.casefold() == "sin descripcion":
        return True
    stem = os.path.splitext(os.path.basename(path))[0]
    name = _text(entry.get("name"))
    generic = {stem.casefold(), os.path.basename(path).casefold(), name.casefold()}
    if text.casefold() in generic:
        return True
    # Header fragments such as "Macro: X Description:" are metadata, not a
    # useful functional explanation; the supplied GPT description can replace
    # them while preserving the original in the audit fields.
    lowered = text.casefold()
    return lowered.startswith("macro:") and ("description:" in lowered or len(text) < 120)


def relative_path(path: str) -> str:
    """Return the stable slash-separated path below Macros-de-Freecad."""
    value = _text(path).replace("\\", "/")
    marker = "Macros-de-Freecad/"
    if marker in value:
        return value.split(marker, 1)[1].strip("/")
    if not os.path.isabs(value) and value and not value.startswith("../") and not value.startswith("./"):
        return value.strip("/")
    try:
        return os.path.relpath(os.path.abspath(path), REPO_ROOT).replace("\\", "/")
    except Exception:
        return os.path.basename(value)


def _literal_metadata(text: str) -> dict:
    """Read official FreeCAD macro metadata without executing the macro."""
    result = {}
    keys = ("Name", "Comment", "Help", "Status", "Requires", "Icon", "Author", "Version", "Date")
    pattern = re.compile(r"^\s*__([A-Za-z]+)__\s*=\s*(['\"])(.*?)\2\s*(?:#.*)?$")
    for line in str(text or "").splitlines()[:80]:
        match = pattern.match(line)
        if match and match.group(1) in keys:
            result[match.group(1)] = match.group(3).strip()
    return result


def read_macro_metadata(path: str) -> dict:
    """Read official metadata and safe header/docstring descriptions."""
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as fh:
            source = fh.read()
    except Exception:
        return {}
    result = _literal_metadata(source)
    lines = source.splitlines()
    header = {}
    for line in lines[:80]:
        match = re.match(r"^\s*#\s*(Description|Comment|Help|MenuText|Label)\s*:\s*(.*?)\s*$", line, re.I)
        if match:
            header[match.group(1).lower()] = match.group(2).strip()
    result["header"] = header
    if not result.get("Comment"):
        result["Comment"] = header.get("description") or header.get("comment") or header.get("help") or ""
    if not result.get("Help"):
        result["Help"] = header.get("help") or ""
    if not result.get("Name"):
        result["Name"] = header.get("menutext") or header.get("label") or os.path.splitext(os.path.basename(path))[0]
    if not result.get("Comment"):
        try:
            tree = ast.parse(source, filename=path)
            result["Comment"] = (ast.get_docstring(tree) or "").strip().split("\n\n", 1)[0].strip()
        except Exception:
            pass
    return result


def description_for_path(path: str) -> tuple[str, str]:
    metadata = read_macro_metadata(path)
    if metadata.get("Comment"):
        return _text(metadata["Comment"]), "macro_metadata"
    if metadata.get("Help"):
        return _text(metadata["Help"]), "macro_metadata"
    if metadata.get("header", {}).get("description"):
        return _text(metadata["header"]["description"]), "header"
    return "", ""


def _default_entry(path: str, group: str = "") -> dict:
    abs_path = os.path.join(REPO_ROOT, path.replace("/", os.sep))
    metadata = read_macro_metadata(abs_path) if os.path.isfile(abs_path) else {}
    description, source = description_for_path(abs_path) if os.path.isfile(abs_path) else ("", "")
    name = _text(metadata.get("Name")) or os.path.splitext(os.path.basename(path))[0]
    return {
        "path": path,
        "name": name,
        "group": _text(group) or (path.split("/", 1)[0] if "/" in path else "Macros"),
        "description": description,
        "description_source": source,
        "comment": "",
        "manual_status": "SIN_REVISAR",
        "decision": "SIN_DECISION",
        "role": "",
        "maturity": "",
        "verified_result": "",
        "recommended_visibility": "",
        "priority": "",
        "retirement_risk": "",
        "dependencies": [],
        "recommended_action": "",
        "confidence": "",
        "technical_note": "",
        "source": "auto_scan",
        "last_reviewed": "",
        "active": False,
    }


def _iter_macro_paths():
    ignored = {".git", "__pycache__", ".qodo", ".codex"}
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [name for name in dirs if name not in ignored]
        for name in sorted(files):
            if name.lower().endswith(".fcmacro"):
                yield os.path.join(root, name)


def _normalize_entry(entry: dict, path: str) -> dict:
    # Existing entries already contain their description/manual fields. Avoid
    # reparsing every macro file whenever the Panel refreshes its tree.
    base = _default_entry(path) if not entry else {
        "path": path,
        "name": os.path.splitext(os.path.basename(path))[0],
        "group": path.split("/", 1)[0] if "/" in path else "Macros",
        "description": "",
        "description_source": "",
        "comment": "",
        "manual_status": "SIN_REVISAR",
        "decision": "SIN_DECISION",
        "role": "",
        "maturity": "",
        "verified_result": "",
        "recommended_visibility": "",
        "priority": "",
        "retirement_risk": "",
        "dependencies": [],
        "recommended_action": "",
        "confidence": "",
        "technical_note": "",
        "source": "auto_scan",
        "last_reviewed": "",
        "active": False,
    }
    if isinstance(entry, dict):
        base.update(entry)
    base["path"] = path
    if not isinstance(base.get("dependencies"), list):
        base["dependencies"] = []
    if base.get("manual_status") not in MANUAL_STATUSES:
        base["manual_status"] = "SIN_REVISAR"
    if base.get("decision") not in DECISIONS:
        base["decision"] = "SIN_DECISION"
    base["active"] = bool(base.get("active"))
    return base


def load_catalog() -> dict:
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        entries = data.get("entries", {}) if isinstance(data, dict) else {}
        if not isinstance(entries, dict):
            entries = {}
        normalized = {_text(key).replace("\\", "/"): value for key, value in entries.items() if _text(key)}
        result = {"schema_version": int(data.get("schema_version", SCHEMA_VERSION)),
                  "updated": _text(data.get("updated")), "entries": normalized}
        for key, value in data.items():
            if key not in {"schema_version", "updated", "entries"}:
                result[key] = value
        return result
    except Exception:
        return {"schema_version": SCHEMA_VERSION, "updated": "", "entries": {}}


def _active_index(active_rows) -> dict:
    result = {}
    for meta in active_rows or []:
        path = relative_path(meta.get("macro") or meta.get("macro_rel") or "")
        if path:
            result[path] = meta
    return result


def merge_active_metadata(data: dict, active_rows=None) -> tuple[dict, bool]:
    """Reconcile scanned files and currently registered commands idempotently."""
    result = {"schema_version": SCHEMA_VERSION, "updated": data.get("updated", ""),
              "entries": dict(data.get("entries", {}))}
    changed = False
    for path_abs in _iter_macro_paths():
        path = relative_path(path_abs)
        old = result["entries"].get(path, {})
        entry = _normalize_entry(old, path)
        if not old:
            changed = True
        if not old and not entry.get("description"):
            desc, source = description_for_path(path_abs)
            if desc:
                entry["description"] = desc
                entry["description_source"] = source
                changed = True
        result["entries"][path] = entry

    for path, meta in _active_index(active_rows).items():
        entry = _normalize_entry(result["entries"].get(path, {}), path)
        group = _text(meta.get("toolbar") or meta.get("group"))
        label = _text(meta.get("label"))
        if group and entry.get("group") != group and entry.get("source") == "auto_scan":
            entry["group"] = group
            changed = True
        if label and (not entry.get("name") or entry.get("name") == os.path.splitext(os.path.basename(path))[0]):
            if entry.get("name") != label:
                entry["name"] = label
                changed = True
        if not result["entries"].get(path) and not entry.get("description"):
            desc, source = description_for_path(os.path.join(REPO_ROOT, path.replace("/", os.sep)))
            if desc:
                entry["description"] = desc
                entry["description_source"] = source
                changed = True
        if not entry.get("source") or entry.get("source") == "auto_scan":
            entry["source"] = "registry" if meta else entry.get("source", "auto_scan")
        if not entry.get("active"):
            entry["active"] = True
            changed = True
        result["entries"][path] = entry
    if changed:
        result["updated"] = _now_iso()
    return result, changed


def _atomic_write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".electriccr_", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass


def save_catalog(data: dict) -> None:
    payload = {"schema_version": SCHEMA_VERSION, "updated": _text(data.get("updated")) or _now_iso(),
               "entries": {key: _normalize_entry(value, key) for key, value in sorted(data.get("entries", {}).items())}}
    for key, value in data.items():
        if key not in {"schema_version", "updated", "entries"}:
            payload[key] = value
    _atomic_write(CATALOG_PATH, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    data.clear()
    data.update(payload)


def integrate_gpt_descriptions(source_path: str | None = None) -> dict:
    """Merge supplied functional descriptions without touching review data.

    The route is the only identity key. Concrete local descriptions remain
    authoritative; a differing GPT text is retained as an alternative and
    marked for review instead of being silently replaced.
    """
    source_path = source_path or GPT_DESCRIPTIONS_PATH
    with open(source_path, "r", encoding="utf-8") as fh:
        source = json.load(fh)
    items = source.get("items", []) if isinstance(source, dict) else []
    data = load_catalog()
    entries = data.setdefault("entries", {})
    stats = {"source_items": len(items), "matched": 0, "updated": 0,
             "preserved_local": 0, "discrepancies": 0, "missing_local": 0}
    for item in items:
        if not isinstance(item, dict):
            continue
        path = _text(item.get("ruta") or item.get("path")).replace("\\", "/")
        description = _text(item.get("descripcion") or item.get("description"))
        if not path or not description:
            continue
        local = entries.get(path)
        if not isinstance(local, dict):
            local = _default_entry(path, _text(item.get("grupo")))
            entries[path] = local
        stats["matched"] += 1
        old_description = _text(local.get("description"))
        local_is_generic = _description_is_generic(old_description, local, path)
        gpt_source = _text(item.get("fuente_descripcion")) or "codigo_revisado_gpt"
        gpt_confidence = _text(item.get("confianza_descripcion")) or "media"
        # Always preserve the supplied provenance, even when a newer local
        # description remains authoritative.
        local["fuente_descripcion"] = gpt_source
        local["confianza_descripcion"] = gpt_confidence
        local["gpt_description"] = description
        local["gpt_description_original"] = _text(item.get("descripcion_original"))
        if local_is_generic:
            if old_description != description or local.get("description_source") != gpt_source:
                stats["updated"] += 1
            local["description"] = description
            local["description_source"] = gpt_source
            local["description_confidence"] = gpt_confidence
            local.pop("description_alternative", None)
            local.pop("description_discrepancy", None)
            stats["missing_local"] += 1
        elif old_description == description:
            # Existing concrete text agrees with the supplied description.
            local.setdefault("description_confidence", gpt_confidence)
            stats["preserved_local"] += 1
        else:
            # A concrete local description wins; preserve the GPT proposal as
            # an explicit alternative for later human review.
            local["description_alternative"] = description
            local["description_alternative_source"] = gpt_source
            local["description_alternative_confidence"] = gpt_confidence
            local["description_discrepancy"] = True
            local["description_discrepancy_note"] = "Descripcion local concreta conservada; alternativa GPT pendiente de revision."
            stats["preserved_local"] += 1
            stats["discrepancies"] += 1
    data["description_source_file"] = relative_path(source_path)
    data["description_source_generated"] = _text(source.get("generado")) if isinstance(source, dict) else ""
    data["description_integration"] = {**stats, "updated": _now_iso()}
    data["updated"] = _now_iso()
    save_catalog(data)
    regenerate_markdown(data)
    return stats


def markdown_for_catalog(data: dict) -> str:
    lines = ["# Catalogo de macros ElectricCR", "", f"Esquema JSON: {SCHEMA_VERSION}",
             f"Actualizado: {data.get('updated') or 'sin fecha'}", "",
             "Fuente de verdad: `ElectricCR/data/macros_catalog.json`.",
             "Este archivo se genera automaticamente; los comentarios manuales se editan en el JSON desde el Panel.", ""]
    entries = data.get("entries", {})
    groups = {}
    for path, entry in sorted(entries.items(), key=lambda item: (_text(item[1].get("group")), _text(item[1].get("name")), item[0])):
        groups.setdefault(_text(entry.get("group")) or "Macros", []).append((path, entry))
    for group, values in sorted(groups.items(), key=lambda item: item[0].casefold()):
        lines.extend([f"## {group}", "", "| Herramienta | Ruta | Descripcion | Fuente/confianza | Comentario | Estado | Decision | Rol / madurez | Observacion |", "|---|---|---|---|---|---|---|---|---|"])
        for path, entry in values:
            def cell(value):
                return _text(value).replace("|", "\\|").replace("\n", " ")
            role = "/".join(filter(None, [_text(entry.get("role")), _text(entry.get("maturity"))]))
            source = "/".join(filter(None, [cell(entry.get("description_source")), cell(entry.get("description_confidence") or entry.get("confianza_descripcion"))]))
            if entry.get("description_discrepancy"):
                note = (cell(entry.get("description_discrepancy_note")) or "Discrepancia")
            else:
                note = cell(entry.get("technical_note") or entry.get("recommended_action"))
            lines.append("| {name} | `{path}` | {desc} | {source} | {comment} | {status} | {decision} | {role} | {note} |".format(
                name=cell(entry.get("name")), path=cell(path), desc=cell(entry.get("description")) or "Sin descripcion",
                source=source, comment=cell(entry.get("comment")), status=cell(entry.get("manual_status")), decision=cell(entry.get("decision")),
                role=cell(role), note=note))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def regenerate_markdown(data: dict | None = None) -> None:
    if data is None:
        data = load_catalog()
    _atomic_write(MARKDOWN_PATH, markdown_for_catalog(data))


def ensure_catalog(active_rows=None) -> dict:
    data = load_catalog()
    merged, changed = merge_active_metadata(data, active_rows)
    if changed or not os.path.isfile(CATALOG_PATH):
        save_catalog(merged)
    else:
        merged = data
    if not os.path.isfile(MARKDOWN_PATH) or changed:
        regenerate_markdown(merged)
    return merged


def update_entry(path: str, updates: dict) -> dict:
    data = load_catalog()
    key = relative_path(path)
    entry = _normalize_entry(data.get("entries", {}).get(key, {}), key)
    for name, value in (updates or {}).items():
        if name in entry and name not in {"path", "active"}:
            entry[name] = value
    entry["last_reviewed"] = _now_iso()
    data.setdefault("entries", {})[key] = entry
    data["updated"] = _now_iso()
    save_catalog(data)
    regenerate_markdown(data)
    return entry


def entry_for_meta(meta: dict, data: dict | None = None) -> dict:
    if data is None:
        data = load_catalog()
    key = relative_path(meta.get("macro") or meta.get("macro_rel") or "")
    return _normalize_entry(data.get("entries", {}).get(key, {}), key) if key else _default_entry("", "Macros")
