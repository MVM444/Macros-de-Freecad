"""Lights management helpers for Game Engine Export WB.

Descripcion rapida: API compatible con panel_export para manejo de luces.
Fecha y hora: 2026-03-11 17:40 UTC.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence


LOG_PREFIX = "[GAMEEXPORT] "


@dataclass
class PointLightData:
    name: str
    label: str
    position_mm: tuple[float, float, float]
    intensity: float
    color_rgb: tuple[float, float, float]
    radius: float


def _log(message: str) -> None:
    FreeCAD = __import__("FreeCAD")
    FreeCAD.Console.PrintMessage(LOG_PREFIX + message + "\n")


def list_point_lights(doc) -> List[object]:
    """Return objects flagged as lights (best effort)."""
    if doc is None:
        return []
    return [obj for obj in getattr(doc, "Objects", []) if getattr(obj, "IsGameExportLight", False)]


def tag_selection_as_light(doc, selection: Sequence[object]) -> List[str]:
    if doc is None or not selection:
        return []
    names = []
    for obj in selection:
        if obj is None or getattr(obj, "Document", None) is not doc:
            continue
        if hasattr(obj, "PropertiesList") and "IsGameExportLight" not in obj.PropertiesList:
            obj.addProperty("App::PropertyBool", "IsGameExportLight", "GameEngineExport", "Mark as PointLight")
        setattr(obj, "IsGameExportLight", True)
        names.append(obj.Name)
    if names:
        _log("Tagged as lights: " + ", ".join(names))
    return names


def untag_selection_as_light(doc, selection: Sequence[object]) -> List[str]:
    if doc is None or not selection:
        return []
    names = []
    for obj in selection:
        if obj is None or getattr(obj, "Document", None) is not doc:
            continue
        if hasattr(obj, "IsGameExportLight"):
            setattr(obj, "IsGameExportLight", False)
            names.append(obj.Name)
    if names:
        _log("Un-tagged lights: " + ", ".join(names))
    return names


def apply_light_names(doc, names: Iterable[str]) -> None:
    if doc is None:
        return
    wanted = set(names or [])
    for obj in getattr(doc, "Objects", []):
        if hasattr(obj, "PropertiesList") and "IsGameExportLight" not in obj.PropertiesList:
            continue
        if hasattr(obj, "IsGameExportLight"):
            obj.IsGameExportLight = obj.Name in wanted or getattr(obj, "Label", "") in wanted


def get_light_properties(obj) -> dict:
    return {
        "intensity": float(getattr(obj, "GameExportLightIntensity", 1.2)),
        "radius": float(getattr(obj, "GameExportLightRadius", 12.0)),
        "color": (1.0, 1.0, 1.0),
    }


def set_light_properties(
    doc,
    objects: Sequence[object],
    intensity: Optional[float] = None,
    radius: Optional[float] = None,
    color: Optional[Iterable[float]] = None,
) -> List[str]:
    if doc is None or not objects:
        return []
    updated = []
    for obj in objects:
        if obj is None or getattr(obj, "Document", None) is not doc:
            continue
        if hasattr(obj, "PropertiesList") and "GameExportLightIntensity" not in obj.PropertiesList:
            obj.addProperty("App::PropertyFloat", "GameExportLightIntensity", "GameEngineExport", "Light intensity")
        if hasattr(obj, "PropertiesList") and "GameExportLightRadius" not in obj.PropertiesList:
            obj.addProperty("App::PropertyFloat", "GameExportLightRadius", "GameEngineExport", "Light radius")
        if intensity is not None:
            setattr(obj, "GameExportLightIntensity", float(intensity))
        if radius is not None:
            setattr(obj, "GameExportLightRadius", float(radius))
        updated.append(obj.Name)
    return updated


def gather_point_light_data(doc, names: Iterable[str] | None = None) -> List[PointLightData]:
    if doc is None:
        return []
    allowed = set(names) if names is not None else None
    entries: List[PointLightData] = []
    for obj in list_point_lights(doc):
        if allowed is not None and obj.Name not in allowed and getattr(obj, "Label", "") not in allowed:
            continue
        base = getattr(getattr(obj, "Placement", None), "Base", None)
        position = (
            float(getattr(base, "x", 0.0)),
            float(getattr(base, "y", 0.0)),
            float(getattr(base, "z", 0.0)),
        )
        props = get_light_properties(obj)
        entries.append(
            PointLightData(
                name=obj.Name,
                label=getattr(obj, "Label", obj.Name),
                position_mm=position,
                intensity=float(props["intensity"]),
                color_rgb=tuple(props["color"]),
                radius=float(props["radius"]),
            )
        )
    return entries


__all__: List[str] = [
    "PointLightData",
    "list_point_lights",
    "tag_selection_as_light",
    "untag_selection_as_light",
    "apply_light_names",
    "set_light_properties",
    "get_light_properties",
    "gather_point_light_data",
]
