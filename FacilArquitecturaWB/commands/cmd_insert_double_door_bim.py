"""FA_InsertDoubleDoorBIM command.

Descripcion: inserta una puerta Arch/BIM de dos hojas en Placement libre o en
un muro seleccionado.
Objetivo: exponer la puerta Europa validada como herramienta reutilizable del
Workbench, no como macro especifica de Puriscal.
FreeCAD objetivo: 1.1.3.
Fecha: 2026-08-12.
Version: 0.1.0.
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from ..core.bim_structure_utils import is_level, selected_level
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.double_door_bim import (
    create_double_door_bim,
    host_insertion_for_wall,
    validate_host_opening,
)
from ..core.opening_utils import ensure_opening_group, is_bim_wall
from ..core.project_structure import active_or_new_document, ensure_project_structure, msg
from ..ui.dialog_double_door_bim import DoubleDoorBIMDialog


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "double_door_bim.svg")
).replace(os.sep, "/")


class CommandClass:
    """Insert one reusable native double BIM door."""

    CommandName = "FA_InsertDoubleDoorBIM"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Insertar puerta doble BIM",
            "ToolTip": (
                "Insertar una puerta Arch/BIM Europa de dos hojas. Seleccione un muro "
                "y, preferiblemente, pulse el punto de insercion antes de ejecutar."
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            msg("FA_InsertDoubleDoorBIM iniciado")
            doc = active_or_new_document()
            selection = list(FreeCADGui.Selection.getSelection() or [])
            wall = _selected_wall(selection)
            picked_point = _picked_point_for_wall(wall)
            dialog = DoubleDoorBIMDialog(
                host_label=_label(wall) if wall is not None else "",
                picked_on_host=picked_point is not None,
                parent=FreeCADGui.getMainWindow(),
            )
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            options = dialog.values()
            use_host = bool(options["use_host"] and wall is not None)
            host_context = None
            if use_host:
                host_context = host_insertion_for_wall(
                    wall, options["width_mm"], picked_point
                )
                placement = host_context["placement"]
                msg("Host seleccionado: %s" % _label(wall))
                msg("Punto insercion: %s" % _vector_text(placement.Base))
                msg(
                    "Normal calculada: %s | tramo: %d"
                    % (
                        _vector_text(host_context["normal"]),
                        host_context["segment_index"],
                    )
                )
            else:
                placement = FreeCAD.Placement(
                    FreeCAD.Vector(options["x_mm"], options["y_mm"], options["z_mm"]),
                    FreeCAD.Rotation(
                        FreeCAD.Vector(0.0, 0.0, 1.0), options["rotation_deg"]
                    ),
                )

            wall_shape_before = wall.Shape.copy() if use_host else None
            wall_volume_before = float(wall.Shape.Volume) if use_host else 0.0
            doc.openTransaction("FA Insertar puerta doble BIM")
            transaction_open = True
            _structured_doc, _project_root, project_groups = ensure_project_structure(doc)
            target_level = selected_level(selection)
            if target_level is None and wall is not None:
                target_level = next(
                    (parent for parent in list(getattr(wall, "InList", []) or []) if is_level(parent)),
                    None,
                )
            target_container = target_level or project_groups["bim"]
            opening_container = ensure_opening_group(doc, target_container, "door")
            door, profile = create_double_door_bim(
                doc,
                placement=placement,
                host=wall if use_host else None,
                target_container=opening_container,
                parameters={
                    "width_mm": options["width_mm"],
                    "height_mm": options["height_mm"],
                },
                opening=options["opening_percent"],
                host_context=host_context,
            )
            if use_host:
                wall.touch()
            doc.recompute()
            cut_volume = 0.0
            cut_status = "free"
            if use_host:
                msg("Hosts asignados: %s" % ", ".join(_label(item) for item in door.Hosts))
                msg("MoveWithHost: %s" % bool(door.MoveWithHost))
                msg(
                    "Hole/Subvolume: wire=%s | depth=%.1f mm | custom=%s"
                    % (
                        getattr(door, "HoleWire", ""),
                        float(door.HoleDepth.Value),
                        _label(getattr(door, "Subvolume", None)) or "automatico",
                    )
                )
                cut_result = validate_host_opening(
                    door,
                    wall,
                    wall_shape_before=wall_shape_before,
                    host_context=host_context,
                )
                cut_volume = cut_result["cut_volume_mm3"]
                cut_status = cut_result["cut_status"]
                msg(
                    "Interseccion hueco/muro: antes=%.0f | despues=%.0f | delta muro=%.0f mm3"
                    % (
                        cut_result["intersection_before_mm3"],
                        cut_result["intersection_after_mm3"],
                        wall_volume_before - float(wall.Shape.Volume),
                    )
                )
                msg("Corte BIM confirmado: %s" % cut_status)
            doc.commitTransaction()
            transaction_open = False
            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(door)
                FreeCADGui.activeDocument().activeView().fitAll()
            except Exception:
                pass
            msg(
                "Puerta doble BIM creada: %s | %.0f x %.0f mm | host: %s | corte: %.0f mm3 | estado: %s"
                % (
                    door.Label,
                    door.Width.Value,
                    door.Height.Value,
                    _label(wall) if use_host else "sin muro",
                    cut_volume,
                    cut_status,
                )
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Insertar puerta doble BIM", exc)

    def IsActive(self):  # noqa: N802
        return True


def _selected_wall(selection):
    walls = []
    for obj in selection or []:
        candidate = _linked_object(obj)
        if is_bim_wall(candidate) and candidate not in walls:
            walls.append(candidate)
    if len(walls) > 1:
        raise UserFacingError("Seleccione un solo muro BIM para insertar la puerta doble.")
    return walls[0] if walls else None


def _picked_point_for_wall(wall):
    if wall is None:
        return None
    try:
        extended = list(FreeCADGui.Selection.getSelectionEx() or [])
    except Exception:
        extended = []
    for item in extended:
        if _linked_object(getattr(item, "Object", None)) is not wall:
            continue
        points = list(getattr(item, "PickedPoints", []) or [])
        if points:
            return points[0]
    return None


def _linked_object(obj):
    if obj is None:
        return None
    try:
        linked = obj.getLinkedObject(True)
        return linked or obj
    except Exception:
        return obj


def _label(obj):
    return str(getattr(obj, "Label", getattr(obj, "Name", "")) or "")


def _vector_text(value):
    try:
        return "(%.1f, %.1f, %.1f)" % (value.x, value.y, value.z)
    except Exception:
        try:
            return "(%.1f, %.1f, %.1f)" % (
                float(value[0]),
                float(value[1]),
                float(value[2]),
            )
        except Exception:
            return str(value)


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
