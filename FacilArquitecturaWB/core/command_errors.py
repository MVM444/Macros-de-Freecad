"""Consistent user-facing command errors for FacilArquitecturaWB.

Descripcion: evita que errores de seleccion esperados produzcan tracebacks de comandos Python.
Fecha: 2026-07-15
Version: 0.1.0
Instrucciones: los comandos deben manejar la excepcion y no volver a lanzarla a FreeCAD.
"""

from __future__ import annotations

import traceback

import FreeCAD

from .project_structure import err, warn


class UserFacingError(RuntimeError):
    """An actionable problem that does not represent a programming failure."""


def handle_command_exception(command_label, exception):
    """Report a command failure without propagating it to FreeCAD's command runner."""
    label = str(command_label or "Comando")
    message = str(exception).strip() or exception.__class__.__name__
    if isinstance(exception, UserFacingError):
        warn("%s: %s" % (label, message))
        _show_message("Facil Arquitectura", message, critical=False)
        return "warning"

    err("Error interno en %s: %s" % (label, message))
    detail = traceback.format_exc()
    if detail and detail.strip() != "NoneType: None":
        try:
            FreeCAD.Console.PrintError("[FACILARQ] Detalle tecnico:\n%s\n" % detail.rstrip())
        except Exception:
            pass
    _show_message(
        "Error de Facil Arquitectura",
        "%s\n\nRevise el panel Report view para el detalle tecnico." % message,
        critical=True,
    )
    return "error"


def _show_message(title, message, critical=False):
    if not bool(getattr(FreeCAD, "GuiUp", False)):
        return
    try:
        import FreeCADGui
        from PySide import QtWidgets

        parent = FreeCADGui.getMainWindow()
        if critical:
            QtWidgets.QMessageBox.critical(parent, title, message)
        else:
            QtWidgets.QMessageBox.warning(parent, title, message)
    except Exception:
        pass
