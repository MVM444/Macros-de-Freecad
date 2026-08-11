# -*- coding: utf-8 -*-
"""Servicios reutilizables de conexiones ElectricCR.

Este paquete sustituye gradualmente motores geometricos incrustados en macros
TP/TCOM. Las macros historicas permanecen como comandos de compatibilidad.
Compatible con FreeCAD 1.1.3. Inicio: 2026-08-08 18:01 CST.
Advertencia: importar estos servicios; no usar una ``.FCMacro`` como biblioteca.
"""

from .backbone import connect_backbone
from .feeders import connect_circuit_feeders, connect_equipment_feeders

__all__ = [
    "connect_backbone",
    "connect_circuit_feeders",
    "connect_equipment_feeders",
]
