"""Helpers to compute and persist default export folder/name values."""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Optional, Tuple

LAST_DOC_PATH_KEY = "last_doc_path"


def _strip_to_ascii(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _normalize_base_name(candidate: str, fallback: str = "Scene") -> str:
    candidate = candidate.strip()
    candidate = _strip_to_ascii(candidate)
    candidate = re.sub(r"\s+", "_", candidate)
    candidate = re.sub(r"[^0-9A-Za-z_-]", "", candidate)
    candidate = candidate.strip("_-")
    return candidate or fallback


def _sanitize_doc_base(doc_path: Path) -> str:
    """Normalize the stem so it can safely become a base filename."""
    return _normalize_base_name(doc_path.stem)


def compute_output_defaults(params, doc_path: Optional[Path]) -> Tuple[str, str, str]:
    """Return the directory/base defaults plus the active document key."""
    stored_dir = params.GetString("output_dir", "")
    stored_base = params.GetString("base_name", "")
    last_doc = params.GetString(LAST_DOC_PATH_KEY, "")

    doc_key = str(doc_path) if doc_path else ""
    doc_dir = str(doc_path.parent) if doc_path else ""
    doc_base = _sanitize_doc_base(doc_path) if doc_path else ""

    if doc_key:
        if doc_key != last_doc:
            return doc_dir, doc_base, doc_key
        return stored_dir or doc_dir, stored_base or doc_base, doc_key

    return stored_dir, stored_base, ""


def ensure_output_directory(value: str) -> Tuple[str, bool]:
    """Return a normalized output folder and create it only when missing."""
    raw_value = str(value or "").strip()
    if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {'"', "'"}:
        raw_value = raw_value[1:-1].strip()
    if not raw_value:
        raise ValueError("Output folder is empty")

    normalized = os.path.normpath(os.path.expandvars(os.path.expanduser(raw_value)))
    output_path = Path(normalized)

    # Do not call mkdir for an existing OneDrive/reparse-point directory.
    # Windows may return Access Denied instead of File Exists for that call.
    if output_path.is_dir():
        return str(output_path), False
    if output_path.exists():
        raise NotADirectoryError("Output path exists but is not a directory: " + str(output_path))

    try:
        output_path.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        # Another process may have created the directory after the first check.
        if output_path.is_dir():
            return str(output_path), False
        raise
    return str(output_path), True


def persist_output_settings(
    params, output_dir: str, base_name: str, doc_path: Optional[Path]
) -> None:
    """Store output prefs and register the active document key when available."""
    params.SetString("output_dir", output_dir or "")
    params.SetString("base_name", base_name or "")
    if doc_path:
        params.SetString(LAST_DOC_PATH_KEY, str(doc_path))


def normalize_base_name(value: str, fallback: str = "Scene") -> str:
    return _normalize_base_name(value, fallback)
