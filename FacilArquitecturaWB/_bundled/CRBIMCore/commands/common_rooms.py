"""Register the common Espacios y Recintos commands exactly once."""

from __future__ import annotations

import os

import FreeCAD as App
import FreeCADGui as Gui

from .. import freecad_room_operations as adapter
from .. import room_operations_core as core
from .. import room_resolver_core as resolver


SELECT_ROOM = "CRBIM_SelectRoom"
ROOM_INFO = "CRBIM_RoomInfo"
NAME_ROOM = "CRBIM_NameRoom"
ROOM_GUIDE = "CRBIM_RoomGuide"
COMMAND_IDS = (SELECT_ROOM, ROOM_INFO, NAME_ROOM, ROOM_GUIDE)
LOG_PREFIX = "[CRBIMCore][ROOMS] "
_ACTIVE_PICKER = None


def _qt():
    for package in ("PySide6", "PySide2", "PySide"):
        try:
            module = __import__(package, fromlist=["QtCore", "QtWidgets", "QtGui"])
            widgets = getattr(module, "QtWidgets", None) or getattr(module, "QtGui", None)
            if widgets is not None:
                return getattr(module, "QtCore", None), widgets
        except Exception:
            continue
    raise RuntimeError("No se encontro una interfaz Qt compatible.")


def _icon(command_id):
    path = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons", command_id + ".svg")
    )
    return path.replace(os.sep, "/")


def _active_doc():
    return getattr(App, "ActiveDocument", None)


def _message(icon_name, title, text):
    _core, widgets = _qt()
    icon = getattr(widgets.QMessageBox, icon_name)
    box = widgets.QMessageBox()
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(str(text))
    box.setStandardButtons(widgets.QMessageBox.Ok)
    return box.exec() if hasattr(box, "exec") else box.exec_()


def _question(title, text):
    _core, widgets = _qt()
    answer = widgets.QMessageBox.question(
        None,
        title,
        str(text),
        widgets.QMessageBox.Yes | widgets.QMessageBox.No,
        widgets.QMessageBox.No,
    )
    return answer == widgets.QMessageBox.Yes


def _show_resolution(title, result, doc=None):
    info = adapter.room_info(doc, result) if doc is not None else core.room_info_record(result)
    icon = "Information" if result.get("status") == resolver.STATUS_RESOLVED else "Warning"
    _message(icon, title, core.format_room_info(info))


def _select_resolved(doc, result):
    if result.get("status") != resolver.STATUS_RESOLVED:
        return False
    obj = adapter.physical_object(doc, result)
    if obj is None:
        _message("Warning", "Seleccionar recinto", "El objeto fisico resuelto ya no existe.")
        return False
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, obj.Name)
    App.Console.PrintMessage(
        LOG_PREFIX + "RESOLVED source=%s object=%s label=%s\n"
        % (result.get("source_kind", ""), obj.Name, getattr(obj, "Label", ""))
    )
    return True


class _PointPicker:
    def __init__(self, doc):
        self.doc = doc
        self.view = Gui.activeDocument().activeView()
        self.callback = self.view.addEventCallback("SoMouseButtonEvent", self._event)
        try:
            Gui.getMainWindow().statusBar().showMessage("Haga clic dentro del recinto. Esc cancela.")
        except Exception:
            pass

    def close(self):
        global _ACTIVE_PICKER
        try:
            self.view.removeEventCallback("SoMouseButtonEvent", self.callback)
        except Exception:
            pass
        try:
            Gui.getMainWindow().statusBar().clearMessage()
        except Exception:
            pass
        if _ACTIVE_PICKER is self:
            _ACTIVE_PICKER = None

    def _event(self, event):
        if str(event.get("State", "")).upper() != "DOWN":
            return
        button = str(event.get("Button", "")).upper()
        if button not in {"BUTTON1", "1"}:
            return
        position = event.get("Position") or (0, 0)
        try:
            point = self.view.getPoint(int(position[0]), int(position[1]))
            result = adapter.resolve_clicked_point(self.doc, [point.x, point.y, point.z])
        except Exception as exc:
            self.close()
            _message("Critical", "Seleccionar recinto", str(exc))
            return
        self.close()
        if not _select_resolved(self.doc, result):
            _show_resolution("Seleccionar recinto", result, self.doc)


class _SelectRoomCommand:
    def GetResources(self):
        return {
            "Pixmap": _icon(SELECT_ROOM),
            "MenuText": "Seleccionar recinto",
            "ToolTip": "Resuelve y selecciona el Space o Area fisica del recinto",
        }

    def Activated(self):
        global _ACTIVE_PICKER
        doc = _active_doc()
        if doc is None:
            _message("Warning", "Seleccionar recinto", "No hay un documento activo.")
            return
        selection = list(Gui.Selection.getSelection() or [])
        if selection:
            result = adapter.resolve_selected_objects(doc, selection)
            if not _select_resolved(doc, result):
                _show_resolution("Seleccionar recinto", result, doc)
            return
        if _ACTIVE_PICKER is not None:
            _ACTIVE_PICKER.close()
        _ACTIVE_PICKER = _PointPicker(doc)
        App.Console.PrintMessage(LOG_PREFIX + "Esperando punto dentro del recinto.\n")

    def IsActive(self):
        return _active_doc() is not None


class _RoomInfoCommand:
    def GetResources(self):
        return {
            "Pixmap": _icon(ROOM_INFO),
            "MenuText": "Info recinto",
            "ToolTip": "Muestra identidad, area y fuente geometrica sin modificar el recinto",
        }

    def Activated(self):
        doc = _active_doc()
        selection = list(Gui.Selection.getSelection() or [])
        if doc is None or not selection:
            _message("Warning", "Info recinto", "Seleccione un recinto u objeto relacionado.")
            return
        result = adapter.resolve_selected_objects(doc, selection)
        _show_resolution("Info recinto", result, doc)

    def IsActive(self):
        return _active_doc() is not None


class _NameRoomCommand:
    def GetResources(self):
        return {
            "Pixmap": _icon(NAME_ROOM),
            "MenuText": "Nombrar recinto",
            "ToolTip": "Cambia solo Label en Spaces o Areas fisicas validas",
        }

    def Activated(self):
        doc = _active_doc()
        selection = list(Gui.Selection.getSelection() or [])
        if doc is None or not selection:
            _message("Warning", "Nombrar recinto", "Seleccione uno o varios Spaces o Areas validas.")
            return
        _qtcore, widgets = _qt()
        names = adapter.standard_room_names(doc)
        label, accepted = widgets.QInputDialog.getItem(
            None, "Nombrar recinto", "Nombre:", names, 0, True
        )
        if not accepted or not str(label).strip():
            return
        plan = adapter.apply_room_labels(doc, selection, str(label), dry_run=True)
        if not plan.get("accepted"):
            rejected = ", ".join(item.get("object_name") or "seleccion" for item in plan.get("rejected", []))
            _message("Warning", "Nombrar recinto", "No hay recintos fisicos validos. Rechazados: %s" % rejected)
            return
        if plan.get("rejected"):
            rejected = ", ".join(item.get("object_name") or "seleccion" for item in plan["rejected"])
            if not _question(
                "Nombrar recinto",
                "Se rechazaran objetos que no son recintos fisicos: %s\n\nContinuar con los validos?" % rejected,
            ):
                return
        result = adapter.apply_room_labels(doc, selection, str(label), dry_run=False)
        App.Console.PrintMessage(
            LOG_PREFIX + "Nombrar recinto label=%s applied=%d rejected=%d\n"
            % (result.get("new_label", ""), result.get("applied", 0), len(result.get("rejected", [])))
        )
        _message(
            "Information",
            "Nombrar recinto",
            "Recintos actualizados: %d\nObjetos rechazados: %d"
            % (result.get("applied", 0), len(result.get("rejected", []))),
        )

    def IsActive(self):
        return _active_doc() is not None


class _RoomGuideCommand:
    def GetResources(self):
        return {
            "Pixmap": _icon(ROOM_GUIDE),
            "MenuText": "Guia Espacios y Recintos",
            "ToolTip": "Explica el flujo comun de Spaces y Areas compatibles",
        }

    def Activated(self):
        _message("Information", "Guia Espacios y Recintos", core.guide_text())

    def IsActive(self):
        return True


def ensure_common_room_commands_registered():
    """Register one implementation per stable command ID and return its IDs."""
    available = set(Gui.listCommands())
    definitions = (
        (SELECT_ROOM, _SelectRoomCommand),
        (ROOM_INFO, _RoomInfoCommand),
        (NAME_ROOM, _NameRoomCommand),
        (ROOM_GUIDE, _RoomGuideCommand),
    )
    for command_id, command_type in definitions:
        if command_id in available:
            continue
        Gui.addCommand(command_id, command_type())
        available.add(command_id)
    return list(COMMAND_IDS)


def schedule_room_toolbar_layout(command_ids, title="Espacios y Recintos", label_overrides=None):
    """Reapply one toolbar layout after FreeCAD switches workbenches.

    FreeCAD reuses a QToolBar with the same title across workbenches and can
    retain the previous action order.  This function only arranges existing
    QActions; it does not register or copy commands.
    """
    qtcore, widgets = _qt()
    wanted = tuple(str(value or "") for value in list(command_ids or []))
    overrides = dict(label_overrides or {})

    def _apply():
        try:
            main_window = Gui.getMainWindow()
            toolbars = [
                toolbar
                for toolbar in main_window.findChildren(widgets.QToolBar)
                if str(toolbar.windowTitle() or "") == str(title)
            ]
            for toolbar in toolbars:
                toolbar.clear()
                for command_id in wanted:
                    if command_id == "Separator":
                        toolbar.addSeparator()
                        continue
                    command = Gui.Command.get(command_id)
                    actions = list(command.getAction() or []) if command is not None else []
                    if not actions:
                        continue
                    action = actions[0]
                    if command_id in overrides:
                        action.setText(str(overrides[command_id]))
                    toolbar.addAction(action)
        except Exception as exc:
            App.Console.PrintWarning(LOG_PREFIX + "No se pudo ordenar la barra: %s\n" % exc)

    qtcore.QTimer.singleShot(0, _apply)


__all__ = [
    "COMMAND_IDS",
    "NAME_ROOM",
    "ROOM_GUIDE",
    "ROOM_INFO",
    "SELECT_ROOM",
    "ensure_common_room_commands_registered",
    "schedule_room_toolbar_layout",
]
