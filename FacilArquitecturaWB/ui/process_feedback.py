"""Adaptador GUI reutilizable para feedback de operaciones largas.

Nombre: process_feedback.py
Proposito: mostrar de inmediato que FreeCAD recibio una operacion potencialmente
larga mediante cursor de espera, barra de estado, consola y tiempo total.
Funcion principal: ``LongOperationFeedback`` envuelve la fase costosa sin mover
la logica geometrica fuera del hilo normal de FreeCAD.
Instrucciones relevantes para futuras modificaciones:
- No ejecutar geometria FreeCAD en hilos secundarios desde este modulo.
- Restaurar siempre el cursor en ``finish`` aunque exista una excepcion.
- No mostrar porcentajes salvo que el comando disponga de progreso real.
- Pintar el aviso y procesar eventos GUI antes de entrar a la fase costosa.
- Mantener visible un indicador de actividad mientras dure la operacion.
Version: 0.2.0
Fecha y hora: 2026-09-01 09:50 America/Costa_Rica
"""

from __future__ import annotations

import time

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

from ..core.process_feedback import long_process_message, process_stage


LOG_PREFIX = "[FACILARQ] "


def _wait_cursor_enum():
    direct = getattr(QtCore.Qt, "WaitCursor", None)
    if direct is not None:
        return direct
    scope = getattr(QtCore.Qt, "CursorShape", None)
    if scope is not None:
        return getattr(scope, "WaitCursor")
    return None


def _status_bar():
    try:
        return FreeCADGui.getMainWindow().statusBar()
    except Exception:
        return None


def _exclude_user_input_flag():
    direct = getattr(QtCore.QEventLoop, "ExcludeUserInputEvents", None)
    if direct is not None:
        return direct
    scope = getattr(QtCore.QEventLoop, "ProcessEventsFlag", None)
    if scope is not None:
        return getattr(scope, "ExcludeUserInputEvents", None)
    return None


def _process_events(max_time_ms=80):
    """Force pending paint/status events before heavy synchronous work."""
    try:
        FreeCADGui.updateGui()
    except Exception:
        pass
    flag = _exclude_user_input_flag()
    try:
        if flag is not None:
            QtWidgets.QApplication.processEvents(flag, int(max_time_ms))
        else:
            QtWidgets.QApplication.processEvents()
    except TypeError:
        try:
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass
    except Exception:
        pass


def _repaint_now(widget=None):
    if widget is not None:
        try:
            widget.repaint()
        except Exception:
            pass
    try:
        main = FreeCADGui.getMainWindow()
        if main is not None:
            main.repaint()
    except Exception:
        pass
    _process_events()


class LongOperationFeedback:
    """Small synchronous feedback helper for FreeCAD GUI operations."""

    def __init__(self, operation, initial_stage="Preparando operacion"):
        self.operation = str(operation or "Proceso").strip() or "Proceso"
        self.initial_stage = str(initial_stage or "Preparando operacion")
        self.started_at = None
        self.cursor_set = False
        self.active = False

    def start(self):
        if self.active:
            return self
        self.active = True
        self.started_at = time.perf_counter()
        wait_cursor = _wait_cursor_enum()
        if wait_cursor is not None:
            try:
                QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(wait_cursor))
                self.cursor_set = True
            except Exception:
                self.cursor_set = False
        notice = long_process_message(self.operation)
        FreeCAD.Console.PrintMessage(LOG_PREFIX + notice + "\n")
        bar = _status_bar()
        if bar is not None:
            try:
                bar.showMessage(notice)
            except Exception:
                pass
        # The warning must already be painted before the expensive phase starts.
        _repaint_now(bar)
        self.stage(self.initial_stage)
        return self

    def stage(self, text):
        message = process_stage(self.operation, text)
        FreeCAD.Console.PrintMessage(LOG_PREFIX + message + "\n")
        bar = _status_bar()
        if bar is not None:
            try:
                # Keep the hourglass/stage visible for the whole synchronous phase.
                bar.showMessage(message)
            except Exception:
                pass
        _repaint_now(bar)
        return message

    def finish(self, success=True, error=""):
        if not self.active:
            return 0.0
        elapsed = max(0.0, time.perf_counter() - (self.started_at or time.perf_counter()))
        if self.cursor_set:
            try:
                QtWidgets.QApplication.restoreOverrideCursor()
            except Exception:
                pass
        self.cursor_set = False
        self.active = False
        if success:
            message = "%s | Finalizado en %.1f s" % (self.operation, elapsed)
            FreeCAD.Console.PrintMessage(LOG_PREFIX + message + "\n")
        else:
            message = "%s | Interrumpido tras %.1f s" % (self.operation, elapsed)
            if error:
                message += " | %s" % str(error)
            FreeCAD.Console.PrintWarning(LOG_PREFIX + message + "\n")
        bar = _status_bar()
        if bar is not None:
            try:
                bar.showMessage(message, 5000)
            except Exception:
                pass
        _process_events()
        return elapsed

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc, _tb):
        self.finish(success=exc is None, error=str(exc or ""))
        return False
