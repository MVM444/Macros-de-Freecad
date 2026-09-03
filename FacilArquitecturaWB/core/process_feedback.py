"""Nucleo neutral para mensajes de operaciones potencialmente largas.

Nombre: process_feedback.py
Proposito: definir textos y metadatos reutilizables para informar al usuario
cuando una operacion puede tardar varios segundos o incluso algunos minutos.
Funcion principal: producir mensajes JSON-compatible sin importar FreeCAD ni Qt.
Instrucciones relevantes para futuras modificaciones:
- No importar FreeCAD, FreeCADGui ni Qt.
- No inventar porcentajes de avance cuando el algoritmo no los conoce.
- Mantener el mensaje principal breve y comun para todos los Workbenches.
- El aviso debe estar redactado en futuro: debe advertir antes del calculo costoso.
- Usar un indicador visual estable (reloj de arena o equivalente) sin depender de Qt.
Version: 0.2.0
Fecha y hora: 2026-09-01 09:50 America/Costa_Rica
"""

from __future__ import annotations


LONG_PROCESS_MARKER = "\u23f3"
LONG_PROCESS_MESSAGE = (
    "El siguiente proceso puede tardar varios segundos o algunos minutos. "
    "FreeCAD puede permanecer ocupado mientras se realiza el calculo."
)


def long_process_message(operation=""):
    """Return the standard user-facing notice for a potentially long operation."""
    name = str(operation or "").strip()
    body = "%s %s" % (LONG_PROCESS_MARKER, LONG_PROCESS_MESSAGE)
    if not name:
        return body
    return "%s %s: %s" % (LONG_PROCESS_MARKER, name, LONG_PROCESS_MESSAGE)


def process_stage(operation, stage):
    """Return one concise stage message suitable for console/status-bar use."""
    name = str(operation or "Proceso").strip() or "Proceso"
    current = str(stage or "Trabajando").strip() or "Trabajando"
    return "%s %s | %s" % (LONG_PROCESS_MARKER, name, current)
