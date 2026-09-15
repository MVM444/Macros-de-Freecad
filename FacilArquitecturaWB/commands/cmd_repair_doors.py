"""FA_RepairDoors command.

Nombre: cmd_repair_doors.py
Proposito: reparar de forma guiada puertas BIM FA mal posicionadas respecto al
buque, usando una jamba seleccionada por el usuario como referencia fisica.
Funcionamiento principal: el usuario selecciona una puerta y una jamba vertical,
o selecciona primero la puerta y el comando queda esperando la jamba. El marco
exterior mas cercano a la jamba se traslada hasta ella, conservando Width. Antes
de escribir muestra diagnostico y pide confirmacion; despues de recompute verifica
la misma jamba y cancela la transaccion si no coincide.
Mantenimiento: no modificar aqui FA Puertas BIM. Mantener nucleo independiente,
Undo/Redo, verificacion posterior, mensajes de consola e idempotencia. Los modos
automaticos historicos permanecen en el nucleo solo para diagnostico/migracion,
pero no forman parte del flujo visible guiado.
Version: 0.6.0
Fecha y hora: 2026-09-03 15:05 America/Costa_Rica
"""

from __future__ import annotations

import math
import os

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtWidgets

from .. import i18n
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.door_repair_core import (
    CORE_VERSION,
    DEFAULT_TOLERANCE_MM,
    plan_jamb_alignment,
)
from ..core.project_structure import msg, set_prop
from ..core.reloadable_command import ReloadableCommandProxy

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "repair_doors.svg")
).replace(os.sep, "/")

_GENERATORS = {"FA_CreateDoorsFromSketch", "FA_CreateDoorsBIM"}
_PENDING_JAMB_OBSERVER = None


def _is_fa_door(obj):
    role = str(getattr(obj, "FA_Role", "") or "").strip().lower()
    ifc = str(getattr(obj, "IfcType", "") or "").strip().lower()
    generator = str(getattr(obj, "FA_GeneratedBy", "") or "").strip()
    return role == "door" and (ifc == "door" or generator in _GENERATORS)


def _named_constraint(sketch, name):
    for index, constraint in enumerate(list(getattr(sketch, "Constraints", []) or [])):
        if str(getattr(constraint, "Name", "") or "") == str(name):
            return index, float(getattr(constraint, "Value", 0.0) or 0.0)
    return None, None


def _xy(vector):
    return (float(vector.x), float(vector.y))


def _door_record(obj):
    base = getattr(obj, "Base", None)
    if base is None:
        raise ValueError("door has no native Base")
    width_index, outer_width = _named_constraint(base, "Width")
    _frame_start_index, frame_start = _named_constraint(base, "Frame2")
    _frame_end_index, frame_end = _named_constraint(base, "Frame3")
    if None in (width_index, outer_width, frame_start, frame_end):
        raise ValueError("native Base lacks Width/Frame2/Frame3")

    frame_first = base.Placement.multVec(FreeCAD.Vector(0.0, 0.0, 0.0))
    frame_second = base.Placement.multVec(FreeCAD.Vector(float(outer_width), 0.0, 0.0))
    return {
        "door_name": str(getattr(obj, "Name", "") or ""),
        "door_label": str(getattr(obj, "Label", "") or ""),
        "frame_first": _xy(frame_first),
        "frame_second": _xy(frame_second),
        "frame_start_mm": float(frame_start),
        "frame_end_mm": float(frame_end),
        "outer_width_mm": float(outer_width),
        "width_constraint_index": int(width_index),
    }


def _status_message(text, timeout_ms=0):
    try:
        status = FreeCADGui.getMainWindow().statusBar()
        if timeout_ms:
            status.showMessage(text, int(timeout_ms))
        else:
            status.showMessage(text)
    except Exception:
        pass


def _clear_status_message():
    try:
        FreeCADGui.getMainWindow().statusBar().clearMessage()
    except Exception:
        pass


def _vertical_jamb_info(obj, subelement, subshape=None, picked_point=None):
    """Return a JSON-compatible jamb reference from a vertical Edge or Vertex."""
    if obj is None:
        raise ValueError("jamb object is missing")
    name = str(subelement or "")
    if not name:
        raise ValueError("select a jamb edge or vertex, not only the wall object")
    if subshape is None:
        try:
            subshape = obj.getSubObject(name)
        except Exception:
            subshape = None
    shape_type = str(getattr(subshape, "ShapeType", "") or "")

    if shape_type == "Vertex" or name.startswith("Vertex"):
        point = getattr(subshape, "Point", None)
        if point is None:
            point = picked_point
        if point is None:
            raise ValueError("selected jamb vertex has no point")
        x, y = float(point.x), float(point.y)
        kind = "Vertex"
    elif shape_type == "Edge" or name.startswith("Edge"):
        vertices = list(getattr(subshape, "Vertexes", []) or [])
        if len(vertices) < 2:
            raise ValueError("selected jamb edge has insufficient vertices")
        points = [vertex.Point for vertex in vertices]
        xs = [float(p.x) for p in points]
        ys = [float(p.y) for p in points]
        zs = [float(p.z) for p in points]
        xy_span = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
        z_span = max(zs) - min(zs)
        # A jamb is expected to be essentially vertical in the building model.
        # Allow small modeling noise but reject horizontal/slanted wall edges.
        if z_span <= 1e-6 or xy_span > max(2.0, 0.02 * z_span):
            raise ValueError("selected edge is not a vertical jamb")
        x = sum(xs) / len(xs)
        y = sum(ys) / len(ys)
        kind = "Edge"
    else:
        raise ValueError("select a vertical jamb Edge or Vertex")

    return {
        "point_xy_mm": (x, y),
        "object_name": str(getattr(obj, "Name", "") or ""),
        "object_label": str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or ""),
        "subelement": name,
        "kind": kind,
    }


def _selected_door(selection_ex):
    doors = []
    for entry in selection_ex:
        obj = getattr(entry, "Object", None)
        if obj is not None and _is_fa_door(obj) and obj not in doors:
            doors.append(obj)
    if len(doors) == 1:
        return doors[0]
    if not doors:
        raise UserFacingError(i18n.bi(
            "Seleccione una puerta BIM generada por FA.",
            "Select one FA-generated BIM door.",
        ))
    raise UserFacingError(i18n.bi(
        "Seleccione solamente una puerta para la reparacion guiada.",
        "Select only one door for guided repair.",
    ))


def _jamb_from_selection_ex(selection_ex, door):
    base = getattr(door, "Base", None)
    for entry in selection_ex:
        obj = getattr(entry, "Object", None)
        if obj is None or obj is door or obj is base:
            continue
        names = list(getattr(entry, "SubElementNames", []) or [])
        shapes = list(getattr(entry, "SubObjects", []) or [])
        picked = list(getattr(entry, "PickedPoints", []) or [])
        for index, name in enumerate(names):
            shape = shapes[index] if index < len(shapes) else None
            point = picked[index] if index < len(picked) else (picked[0] if picked else None)
            try:
                return _vertical_jamb_info(obj, name, subshape=shape, picked_point=point)
            except ValueError:
                continue
    return None


def _cancel_pending_jamb_selection(reason=""):
    global _PENDING_JAMB_OBSERVER
    observer = _PENDING_JAMB_OBSERVER
    _PENDING_JAMB_OBSERVER = None
    if observer is not None:
        try:
            FreeCADGui.Selection.removeObserver(observer)
        except Exception:
            pass
    _clear_status_message()
    if reason:
        msg("FA Reparar puertas seleccion jamba cancelada | %s" % reason)


def _apply_guided_move(obj, plan, jamb_info):
    action = dict(plan.get("action") or {})
    if not action or action.get("mode") != "align_to_jamb":
        return False
    base = getattr(obj, "Base", None)
    if base is None:
        return False
    shift_x, shift_y = action["shift_vector_xy_mm"]
    before = base.Placement.Base
    placement = base.Placement
    placement.Base = FreeCAD.Vector(
        float(before.x) + float(shift_x),
        float(before.y) + float(shift_y),
        float(before.z),
    )
    base.Placement = placement

    set_prop(obj, "App::PropertyString", "FA_DoorRepairStatus", "FacilArquitectura", "Estado de reparacion de puerta", "REPAIRED_TO_JAMB")
    set_prop(obj, "App::PropertyString", "FA_DoorRepairCoreVersion", "FacilArquitectura", "Version del reparador", CORE_VERSION)
    set_prop(obj, "App::PropertyFloat", "FA_DoorRepairBeforeError_mm", "FacilArquitectura", "Error antes de reparar", float(plan.get("error_mm") or 0.0))
    set_prop(obj, "App::PropertyString", "FA_BaseAlignmentMode", "FacilArquitectura", "Adaptacion del Base nativo", "align_to_jamb")
    set_prop(obj, "App::PropertyString", "FA_DoorRepairJambObject", "FacilArquitectura", "Objeto que contiene la jamba seleccionada", str(jamb_info.get("object_name") or ""))
    set_prop(obj, "App::PropertyString", "FA_DoorRepairJambSubelement", "FacilArquitectura", "Subelemento de jamba seleccionado", str(jamb_info.get("subelement") or ""))
    set_prop(obj, "App::PropertyString", "FA_DoorRepairFrameEndpoint", "FacilArquitectura", "Extremo del marco alineado a la jamba", str(action.get("frame_endpoint") or ""))
    return True


def _guided_summary(door, jamb_info, plan):
    action = dict(plan.get("action") or {})
    endpoint = str(action.get("frame_endpoint") or plan.get("frame_endpoint") or "-")
    endpoint_label = i18n.bi("primero", "first") if endpoint == "first" else i18n.bi("segundo", "second")
    shift = action.get("shift_vector_xy_mm") or (0.0, 0.0)
    width = float(action.get("current_outer_width_mm") or 0.0)
    return i18n.bi(
        "Puerta: %s\nJamba: %s.%s\nExtremo del marco: %s\nCorreccion: %.2f mm (dx=%.2f, dy=%.2f)\nAncho actual: %.2f mm\nAncho: se conserva"
        % (
            getattr(door, "Label", getattr(door, "Name", "Door")),
            jamb_info.get("object_label") or jamb_info.get("object_name") or "",
            jamb_info.get("subelement") or "",
            endpoint_label,
            float(plan.get("error_mm") or 0.0),
            float(shift[0]),
            float(shift[1]),
            width,
        ),
        "Door: %s\nJamb: %s.%s\nFrame endpoint: %s\nCorrection: %.2f mm (dx=%.2f, dy=%.2f)\nCurrent width: %.2f mm\nWidth: preserved"
        % (
            getattr(door, "Label", getattr(door, "Name", "Door")),
            jamb_info.get("object_label") or jamb_info.get("object_name") or "",
            jamb_info.get("subelement") or "",
            endpoint_label,
            float(plan.get("error_mm") or 0.0),
            float(shift[0]),
            float(shift[1]),
            width,
        ),
    )


def _run_guided_repair(doc, door, jamb_info):
    transaction_open = False
    try:
        record = _door_record(door)
        plan = plan_jamb_alignment(record, jamb_info["point_xy_mm"], tolerance_mm=DEFAULT_TOLERANCE_MM)
        summary = _guided_summary(door, jamb_info, plan)
        msg(
            "FA Reparar puertas jamba diagnostico | %s | jamb=%s.%s | endpoint=%s | error=%.3f mm | width=%.3f mm"
            % (
                getattr(door, "Label", getattr(door, "Name", "Door")),
                jamb_info.get("object_name") or "",
                jamb_info.get("subelement") or "",
                plan.get("frame_endpoint") or "",
                float(plan.get("error_mm") or 0.0),
                float(record.get("outer_width_mm") or 0.0),
            )
        )
        if plan.get("status") == "OK":
            QtWidgets.QMessageBox.information(
                FreeCADGui.getMainWindow(),
                i18n.bi("FA Reparar puertas", "FA Repair doors"),
                summary + "\n\n" + i18n.bi(
                    "El marco ya coincide con la jamba seleccionada.",
                    "The frame already coincides with the selected jamb.",
                ),
            )
            return
        if not plan.get("repairable"):
            raise UserFacingError(summary + "\n\n" + str(plan.get("reason") or ""))

        answer = QtWidgets.QMessageBox.question(
            FreeCADGui.getMainWindow(),
            i18n.bi("FA Reparar puertas - jamba", "FA Repair doors - jamb"),
            summary + "\n\n" + i18n.bi(
                "¿Mover la puerta hasta esta jamba?",
                "Move the door to this jamb?",
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if answer != QtWidgets.QMessageBox.Yes:
            msg("FA Reparar puertas jamba cancelado por usuario")
            return

        action = dict(plan["action"])
        shift = action["shift_vector_xy_mm"]
        base = getattr(door, "Base", None)
        before_base = getattr(getattr(base, "Placement", None), "Base", None)
        before_xyz = (
            float(before_base.x), float(before_base.y), float(before_base.z)
        ) if before_base is not None else (0.0, 0.0, 0.0)
        doc.openTransaction("FA Reparar puerta a jamba")
        transaction_open = True
        if not _apply_guided_move(door, plan, jamb_info):
            raise UserFacingError(i18n.bi("No se pudo mover el Base de la puerta.", "The door Base could not be moved."))
        doc.recompute()

        after_record = _door_record(door)
        verify = plan_jamb_alignment(
            after_record,
            jamb_info["point_xy_mm"],
            tolerance_mm=DEFAULT_TOLERANCE_MM,
            frame_endpoint=action["frame_endpoint"],
        )
        after_base = getattr(getattr(base, "Placement", None), "Base", None)
        after_xyz = (
            float(after_base.x), float(after_base.y), float(after_base.z)
        ) if after_base is not None else (0.0, 0.0, 0.0)
        msg(
            "FA Reparar puertas jamba aplicar | %s | jamb=%s.%s | endpoint=%s | shift=(%.3f, %.3f) mm | width=%.3f -> %.3f mm | Base=(%.3f, %.3f, %.3f)->(%.3f, %.3f, %.3f) | verify=%.3f mm"
            % (
                getattr(door, "Label", getattr(door, "Name", "Door")),
                jamb_info.get("object_name") or "",
                jamb_info.get("subelement") or "",
                action.get("frame_endpoint") or "",
                float(shift[0]), float(shift[1]),
                float(action.get("current_outer_width_mm") or 0.0),
                float(action.get("target_outer_width_mm") or 0.0),
                before_xyz[0], before_xyz[1], before_xyz[2],
                after_xyz[0], after_xyz[1], after_xyz[2],
                float(verify.get("error_mm") or 0.0),
            )
        )
        if verify.get("status") != "OK":
            raise UserFacingError(i18n.bi(
                "La comprobacion posterior no logro alinear el marco con la jamba (error %.3f mm); se cancela la transaccion." % float(verify.get("error_mm") or 0.0),
                "Post-repair verification did not align the frame with the jamb (error %.3f mm); the transaction is being cancelled." % float(verify.get("error_mm") or 0.0),
            ))
        set_prop(door, "App::PropertyFloat", "FA_DoorRepairAfterError_mm", "FacilArquitectura", "Error despues de reparar", float(verify.get("error_mm") or 0.0))
        doc.commitTransaction()
        transaction_open = False
        QtWidgets.QMessageBox.information(
            FreeCADGui.getMainWindow(),
            i18n.bi("FA Reparar puertas", "FA Repair doors"),
            i18n.bi(
                "Puerta alineada con la jamba. El ancho se conservo. Puede usar Deshacer para revertir el cambio.",
                "Door aligned with the jamb. Width was preserved. You can use Undo to revert the change.",
            ),
        )
        msg("FA Reparar puertas jamba completado | reparadas: 1")
    except Exception as exc:
        if transaction_open:
            try:
                doc.abortTransaction()
            except Exception:
                pass
        handle_command_exception(i18n.bi("FA Reparar puertas", "FA Repair doors"), exc)


class _JambSelectionObserver:
    """One-shot FreeCAD selection observer used only while waiting for a jamb."""

    def __init__(self, document_name, door_name):
        self.document_name = str(document_name)
        self.door_name = str(door_name)
        self.finished = False

    def addSelection(self, document, object_name, element, position):  # noqa: N802
        if self.finished or str(document) != self.document_name:
            return
        try:
            doc = FreeCAD.getDocument(self.document_name)
        except Exception:
            _cancel_pending_jamb_selection("documento ya no disponible")
            return
        door = doc.getObject(self.door_name)
        obj = doc.getObject(str(object_name))
        if door is None or obj is None:
            return
        if obj is door or obj is getattr(door, "Base", None):
            _status_message(i18n.bi(
                "Seleccione una jamba vertical de la pared, no la puerta.",
                "Select a vertical wall jamb, not the door.",
            ), 5000)
            return
        try:
            subshape = obj.getSubObject(str(element)) if element else None
            jamb_info = _vertical_jamb_info(obj, element, subshape=subshape, picked_point=position)
        except Exception as exc:
            _status_message(i18n.bi(
                "Seleccion no valida: %s. Seleccione una arista vertical de la jamba." % exc,
                "Invalid selection: %s. Select a vertical jamb edge." % exc,
            ), 6000)
            return

        self.finished = True
        _cancel_pending_jamb_selection()
        msg(
            "FA Reparar puertas jamba seleccionada | door=%s | jamb=%s.%s | point=(%.3f, %.3f)"
            % (
                self.door_name,
                jamb_info.get("object_name") or "",
                jamb_info.get("subelement") or "",
                float(jamb_info["point_xy_mm"][0]),
                float(jamb_info["point_xy_mm"][1]),
            )
        )
        QtCore.QTimer.singleShot(0, lambda: _run_guided_repair(doc, door, jamb_info))


class CommandClass:
    """Align one selected FA door to one user-selected wall jamb."""

    CommandName = "FA_RepairDoors"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Reparar puertas", "FA Repair doors"),
            "ToolTip": i18n.bi(
                "Reparacion guiada: seleccione una puerta y una jamba vertical para alinear el marco conservando el ancho.",
                "Guided repair: select a door and a vertical jamb to align the frame while preserving width.",
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = FreeCAD.ActiveDocument
        if doc is None:
            handle_command_exception(
                i18n.bi("FA Reparar puertas", "FA Repair doors"),
                UserFacingError(i18n.bi("No hay documento activo.", "There is no active document.")),
            )
            return
        try:
            # Invoking the command again cancels any stale one-shot observer first.
            _cancel_pending_jamb_selection()
            selection_ex = list(FreeCADGui.Selection.getSelectionEx() or [])
            door = _selected_door(selection_ex)
            jamb_info = _jamb_from_selection_ex(selection_ex, door)
            if jamb_info is not None:
                msg("FA Reparar puertas flujo | puerta+jamba preseleccionadas")
                _run_guided_repair(doc, door, jamb_info)
                return

            global _PENDING_JAMB_OBSERVER
            observer = _JambSelectionObserver(doc.Name, door.Name)
            _PENDING_JAMB_OBSERVER = observer
            FreeCADGui.Selection.addObserver(observer)
            instruction = i18n.bi(
                "Puerta seleccionada: %s\n\nAhora seleccione una jamba vertical de la pared.\nLa herramienta usara esa jamba para mover el marco y conservara el ancho de la puerta."
                % getattr(door, "Label", door.Name),
                "Selected door: %s\n\nNow select a vertical wall jamb.\nThe tool will use that jamb to move the frame and will preserve the door width."
                % getattr(door, "Label", door.Name),
            )
            _status_message(i18n.bi(
                "FA Reparar puertas: seleccione la jamba vertical de la pared.",
                "FA Repair doors: select the vertical wall jamb.",
            ))
            msg("FA Reparar puertas esperando jamba | door=%s" % door.Name)
            QtWidgets.QMessageBox.information(
                FreeCADGui.getMainWindow(),
                i18n.bi("FA Reparar puertas - seleccionar jamba", "FA Repair doors - select jamb"),
                instruction,
            )
        except Exception as exc:
            _cancel_pending_jamb_selection()
            handle_command_exception(i18n.bi("FA Reparar puertas", "FA Repair doors"), exc)

    def IsActive(self):  # noqa: N802
        return FreeCAD.ActiveDocument is not None


def register():
    command = ReloadableCommandProxy(
        __name__, class_name="CommandClass", command_name=CommandClass.CommandName
    )
    FreeCADGui.addCommand(command.CommandName, command)
    return command
