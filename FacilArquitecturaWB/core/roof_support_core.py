"""Resolucion geometrica pura de apoyos extremos para FA Techo.

Nombre: roof_support_core.py
Proposito: seleccionar los ejes de apoyo extremos de las cerchas a partir de
candidatos ya expresados en coordenadas locales de la cumbrera.
Funcion principal: escoger de forma determinista los apoyos cercanos a ambos
extremos del rectangulo y aplicar un ajuste simetrico opcional.
FreeCAD objetivo: 1.1.3.
Version: 0.1.0
Fecha y hora: 2026-08-31 12:50 America/Costa_Rica

Instrucciones de mantenimiento:
- Mantener este modulo independiente de FreeCAD, FreeCADGui y Qt.
- Las posiciones son milimetros medidos desde el origen del Rectangle a lo largo
  de la direccion de cumbrera.
- No inferir apoyos si no existen candidatos suficientemente cercanos a ambos
  extremos; el adaptador debe usar entonces el Rectangle como fallback.
- Un ajuste positivo mueve ambas cerchas extremas hacia el interior; uno negativo
  las mueve hacia el exterior.
"""

from __future__ import annotations


_EPS = 1e-9


def select_end_support_axes(candidate_positions_mm, ridge_length_mm, edge_tolerance_mm=1000.0):
    """Return the best wall-axis candidates near both ridge ends, or ``None``.

    Candidates may include interior transverse walls. Only positions within
    ``edge_tolerance_mm`` of the rectangle start/end are eligible. The closest
    candidate to each end wins. Both supports must be distinct and ordered.
    """
    ridge = float(ridge_length_mm)
    tol = float(edge_tolerance_mm)
    if ridge <= 0.0:
        raise ValueError("ridge_length_mm debe ser mayor que cero")
    if tol < 0.0:
        raise ValueError("edge_tolerance_mm no puede ser negativo")

    values = sorted({float(v) for v in candidate_positions_mm or []})
    start_candidates = [v for v in values if abs(v) <= tol]
    end_candidates = [v for v in values if abs(v - ridge) <= tol]
    if not start_candidates or not end_candidates:
        return None

    start = min(start_candidates, key=lambda v: (abs(v), v))
    end = min(end_candidates, key=lambda v: (abs(v - ridge), -v))
    if end - start <= _EPS:
        return None

    return {
        "source": "walls",
        "candidate_count": len(values),
        "start_axis_mm": float(start),
        "end_axis_mm": float(end),
        "start_delta_from_rectangle_mm": float(start),
        "end_delta_from_rectangle_mm": float(end - ridge),
    }


def apply_symmetric_support_adjust(start_axis_mm, end_axis_mm, adjust_mm=0.0):
    """Apply a symmetric fine adjustment to two support axes.

    Positive values move supports inward. Negative values move them outward.
    """
    start = float(start_axis_mm)
    end = float(end_axis_mm)
    adjust = float(adjust_mm)
    result_start = start + adjust
    result_end = end - adjust
    if result_end - result_start <= _EPS:
        raise ValueError("El ajuste de apoyo deja sin longitud util entre cerchas extremas")
    return {
        "start_axis_mm": result_start,
        "end_axis_mm": result_end,
        "support_length_mm": result_end - result_start,
        "adjust_mm": adjust,
    }
