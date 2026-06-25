"""GameStart helpers for Game Engine Export WB.

Descripcion rapida: API minima compatible con panel_export.
Fecha y hora: 2026-03-11 17:40 UTC.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional


LOG_PREFIX = "[GAMEEXPORT] "


def ensure_gamestart(doc, label: str = "GameStart"):
    """Return existing GameStart object if present (no forced creation in safe mode)."""
    return find_gamestart(doc, label)


def find_gamestart(doc, label: str = "GameStart"):
    """Find GameStart by marker flag, then by label."""
    if doc is None:
        return None
    for obj in getattr(doc, "Objects", []):
        if getattr(obj, "IsGameStartMarker", False):
            return obj
    for obj in getattr(doc, "Objects", []):
        if getattr(obj, "Label", "") == label:
            return obj
    return None


def get_metadata(obj) -> Optional[Dict[str, object]]:
    """Extract lightweight viewpoint metadata from GameStart object."""
    if obj is None:
        return None
    FreeCAD = __import__("FreeCAD")

    placement = getattr(obj, "Placement", None)
    base = getattr(placement, "Base", None) if placement is not None else None
    position_mm = (
        float(getattr(base, "x", 0.0)),
        float(getattr(base, "y", 0.0)),
        float(getattr(base, "z", 0.0)),
    )
    return {
        "position_mm": position_mm,
        "orientation": (0.0, 1.0, 0.0, 0.0),
        "fov_rad": math.radians(float(getattr(obj, "FieldOfView", 60.0) or 60.0)),
        "description": getattr(obj, "Label", "") or getattr(obj, "Name", "") or "GameStart",
        "source_doc": getattr(getattr(obj, "Document", None), "Name", ""),
        "freecad_version": getattr(FreeCAD, "Version", lambda: [])(),
    }


__all__: List[str] = ["ensure_gamestart", "find_gamestart", "get_metadata"]
