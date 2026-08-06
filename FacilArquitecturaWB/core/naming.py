"""Naming helpers for FacilArquitecturaWB.

Descripcion: utilidades para nombres seguros en FreeCAD.
Fecha: 2026-07-13
Version: 0.1.0
Instrucciones: mantener salida ASCII y sin espacios para Name; Label puede ser legible.
"""

from __future__ import annotations


def safe_name(value: str, fallback: str = "FA_Object") -> str:
    """Return an ASCII-ish object name accepted by FreeCAD."""
    text = str(value or "").strip()
    replacements = {
        " ": "_",
        "-": "_",
        "/": "_",
        "\\": "_",
        ".": "_",
        "(": "",
        ")": "",
        "[": "",
        "]": "",
        "{": "",
        "}": "",
        ":": "_",
        ";": "_",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = "".join(ch for ch in text if ch.isalnum() or ch == "_")
    return text or fallback
