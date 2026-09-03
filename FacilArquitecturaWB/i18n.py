"""Localization helpers for FacilArquitecturaWB.

Name: i18n.py
Purpose: provide one small language adapter for visible Workbench text.
Main behavior: follow the active FreeCAD language, prefer Qt translation catalogs,
and keep an explicit Spanish/English fallback while migration to .ts/.qm is completed.
Maintenance notes:
- Keep internal command ids, property names and JSON keys language independent.
- New visible UI strings must use tr() or bi().
- Translation catalogs under translations/ take precedence over the fallback.
Version: 0.1.0
Date and time: 2026-09-02 12:05 America/Costa_Rica
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui

CONTEXT = "FacilArquitecturaWB"
WORKBENCH_CONTEXT = "Workbench"


def current_language() -> str:
    """Return ``es`` or ``en`` from FreeCAD's active language preference."""
    try:
        language = FreeCAD.ParamGet(
            "User parameter:BaseApp/Preferences/General"
        ).GetString("Language", "")
    except Exception:
        language = ""
    normalized = str(language or "").strip().lower().replace("-", "_")
    if normalized.startswith("spanish") or normalized.startswith("espa") or normalized in {
        "es",
        "es_es",
        "es_cr",
        "spanish",
    }:
        return "es"
    return "en"


def tr(text: str, context: str = CONTEXT) -> str:
    """Translate one source string through FreeCAD/Qt when a catalog is installed."""
    source = str(text)
    try:
        translated = FreeCAD.Qt.translate(context, source)
    except Exception:
        translated = source
    return str(translated or source)


def bi(spanish: str, english: str, context: str = CONTEXT) -> str:
    """Return a localized ES/EN string, preferring any loaded Qt catalog."""
    source = str(english)
    translated = tr(source, context=context)
    if translated != source:
        return translated
    return str(spanish) if current_language() == "es" else source


def install_translation_path() -> str:
    """Register the Workbench translations directory with FreeCAD."""
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "translations"))
    if not os.path.isdir(path):
        return path
    try:
        FreeCADGui.addLanguagePath(path)
        FreeCADGui.updateLocale()
    except Exception:
        pass
    return path


__all__ = ["CONTEXT", "WORKBENCH_CONTEXT", "bi", "current_language", "install_translation_path", "tr"]
