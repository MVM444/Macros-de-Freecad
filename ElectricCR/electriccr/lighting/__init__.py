"""Lighting calculation helpers for ElectricCR.

This package contains calculation/read adapters only.  Physical luminaire
creation and placement remain in the existing ElectricCR tools.
"""

from .room_calculation import collect_lighting_rooms, select_authoritative_rooms

__all__ = ["collect_lighting_rooms", "select_authoritative_rooms"]
