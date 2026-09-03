"""Helpers GUI para comandos FA Techo de Facil Arquitectura.

Nombre: roof_command_common.py
Proposito: resolver seleccion y Level BIM para comandos de cerchas, clavadores y cubierta.
Funcion principal: mantener fuera del nucleo independiente la pequena logica que depende de FreeCADGui.
FreeCAD objetivo: 1.1.3.
Version: 0.2.0
Fecha y hora: 2026-08-30 16:55 America/Costa_Rica

Instrucciones de mantenimiento:
- Este modulo pertenece a commands/ y puede depender de FreeCADGui.
- No mover esta logica al nucleo roof_system_core.py.
- El grupo Techo BIM debe contener solo objetos principales; las Bases/Perfiles quedan como hijos nativos.
"""

from __future__ import annotations

import FreeCAD
import FreeCADGui

from ..core.bim_structure_utils import (
    collect_buildings,
    ensure_bim_structure,
    is_building,
    is_level,
    selected_level,
)
from ..core.command_errors import UserFacingError
from ..core.project_structure import active_or_new_document


def is_sketch(obj):
    return bool(obj) and str(getattr(obj, "TypeId", "") or "") == "Sketcher::SketchObject"


def current_selection():
    return list(FreeCADGui.Selection.getSelection() or [])


def selected_sketches(selection=None):
    return [obj for obj in list(selection if selection is not None else current_selection()) if is_sketch(obj)]


def require_single_sketch(selection=None, purpose="fuente"):
    sketches = selected_sketches(selection)
    if len(sketches) != 1:
        raise UserFacingError(
            "Seleccione exactamente un Sketch para %s. Seleccion actual: %d Sketches."
            % (purpose, len(sketches))
        )
    return sketches[0]


def document_for_source(source):
    doc = getattr(source, "Document", None)
    return doc if doc is not None else active_or_new_document()


def ensure_target_level(doc, selection=None):
    """Reutiliza Level seleccionado/ancestral o crea estructura BIM nativa minima."""
    selection = list(selection if selection is not None else current_selection())
    target_level = selected_level(selection)
    chosen_building = None
    if target_level is not None:
        chosen_building = next(
            (parent for parent in list(getattr(target_level, "InList", []) or []) if is_building(parent)),
            None,
        )
    buildings = collect_buildings(doc)
    if chosen_building is None and len(buildings) == 1:
        chosen_building = buildings[0]
    structure = ensure_bim_structure(
        doc,
        building=chosen_building,
        level=target_level,
        elevation_mm=(float(target_level.Placement.Base.z) if target_level is not None else 0.0),
    )
    return structure["level"]


def ensure_roof_container(level):
    """Reutiliza o crea el grupo visual Techo BIM dentro del Level objetivo."""
    if level is None:
        raise UserFacingError("No se pudo resolver el Level BIM para el techo.")
    doc = getattr(level, "Document", None)
    if doc is None:
        raise UserFacingError("El Level seleccionado no pertenece a un documento.")
    for child in list(getattr(level, "Group", []) or []) + list(getattr(level, "OutList", []) or []):
        if bool(getattr(child, "FA_IsRoofContainer", False)):
            return child
    safe_level = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(getattr(level, "Name", "Level")))
    group = doc.addObject("App::DocumentObjectGroup", "FA_RoofSystem_%s" % safe_level)
    group.Label = "Techo BIM"
    if "FA_IsRoofContainer" not in list(getattr(group, "PropertiesList", []) or []):
        group.addProperty("App::PropertyBool", "FA_IsRoofContainer", "FacilArquitectura", "Contenedor visual de FA Techo")
    group.FA_IsRoofContainer = True
    try:
        level.addObject(group)
    except Exception as exc:
        try:
            doc.removeObject(group.Name)
        except Exception:
            pass
        raise UserFacingError("No se pudo agregar Techo BIM al Level: %s" % exc)
    return group


def open_transaction(doc, label):
    try:
        doc.openTransaction(str(label))
        return True
    except Exception:
        return False


def finish_transaction(doc, opened, commit=True):
    if not opened:
        return
    try:
        if commit:
            doc.commitTransaction()
        else:
            doc.abortTransaction()
    except Exception:
        pass


def select_results(objects):
    try:
        FreeCADGui.Selection.clearSelection()
        for obj in list(objects or []):
            if obj is not None:
                FreeCADGui.Selection.addSelection(obj)
    except Exception:
        pass


def parse_gable_edge_indices(text):
    value = str(text or "").strip()
    if not value:
        return None
    parts = [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
    if len(parts) != 2:
        raise UserFacingError("GableEdgeIndices debe ser, por ejemplo, 0,2 o 1,3.")
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        raise UserFacingError("GableEdgeIndices debe contener dos enteros.")


__all__ = [
    "current_selection",
    "selected_sketches",
    "require_single_sketch",
    "document_for_source",
    "ensure_target_level",
    "ensure_roof_container",
    "open_transaction",
    "finish_transaction",
    "select_results",
    "parse_gable_edge_indices",
]
