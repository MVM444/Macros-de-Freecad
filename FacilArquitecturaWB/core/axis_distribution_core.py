"""Distribucion parametrica de ejes para Facil Arquitectura.

Nombre: axis_distribution_core.py
Proposito: calcular posiciones de ejes con separacion uniforme, separacion nominal
con excepciones en extremos y separacion calculada redondeada.
Funcion principal: producir datos JSON-compatibles para Arch Axis sin depender de FreeCAD.
FreeCAD objetivo: 1.1.3.
Version: 0.2.0
Fecha y hora: 2026-08-30 20:35 America/Costa_Rica

Instrucciones de mantenimiento:
- Mantener este modulo independiente de FreeCAD, FreeCADGui y Qt.
- La primera entrada de ``distances_mm`` es la distancia desde el origen del Axis
  hasta el primer eje; las siguientes son intervalos entre ejes.
- En modo ``fixed`` conservar la separacion nominal en los intervalos interiores
  y absorber el ajuste solamente en el primero y el ultimo.
- En modo ``rounded`` usar un nominal redondeado al paso pedido sin superar
  ``max_spacing_mm``; los extremos pueden ser excepciones.
- Nunca superar la separacion maxima solicitada entre ejes.
"""

from __future__ import annotations

import math

_EPS = 1e-9


def _validated_lengths(total_length_mm, spacing_mm, start_offset_mm, end_offset_mm):
    total = float(total_length_mm)
    spacing = float(spacing_mm)
    start = float(start_offset_mm)
    end = float(end_offset_mm)
    if total <= 0.0:
        raise ValueError("total_length_mm debe ser mayor que cero")
    if spacing <= 0.0:
        raise ValueError("spacing_mm debe ser mayor que cero")
    if start < 0.0 or end < 0.0:
        raise ValueError("Los retiros no pueden ser negativos")
    usable = total - start - end
    if usable < -_EPS:
        raise ValueError("Los retiros superan la longitud disponible")
    return total, spacing, start, end, max(0.0, usable)


def _result(total, requested, start, end, usable, intervals, mode, nominal=None, extra=None):
    distances = [start] + [float(v) for v in intervals]
    positions = []
    acc = 0.0
    for distance in distances:
        acc += distance
        positions.append(acc)
    data = {
        "total_length_mm": float(total),
        "max_spacing_mm": float(requested),
        "start_offset_mm": float(start),
        "end_offset_mm": float(end),
        "usable_length_mm": float(usable),
        "spacing_mm": float(nominal if nominal is not None else (intervals[0] if intervals else 0.0)),
        "axis_count": len(positions),
        "distances_mm": distances,
        "positions_mm": positions,
        "intervals_mm": [float(v) for v in intervals],
        "mode": str(mode),
    }
    if intervals:
        data["min_interval_mm"] = min(intervals)
        data["max_interval_mm"] = max(intervals)
        data["first_interval_mm"] = intervals[0]
        data["last_interval_mm"] = intervals[-1]
    else:
        data["min_interval_mm"] = 0.0
        data["max_interval_mm"] = 0.0
        data["first_interval_mm"] = 0.0
        data["last_interval_mm"] = 0.0
    if extra:
        data.update(extra)
    return data


def plan_uniform_axis_distribution(
    total_length_mm: float,
    max_spacing_mm: float,
    start_offset_mm: float = 0.0,
    end_offset_mm: float = 0.0,
) -> dict:
    """Return a fully equidistant layout not exceeding ``max_spacing_mm``."""
    total, maximum, start, end, usable = _validated_lengths(
        total_length_mm, max_spacing_mm, start_offset_mm, end_offset_mm
    )
    if usable <= _EPS:
        return _result(total, maximum, start, end, usable, [], "uniform", nominal=0.0)
    interval_count = max(1, int(math.ceil((usable / maximum) - 1e-12)))
    spacing = usable / interval_count
    return _result(
        total,
        maximum,
        start,
        end,
        usable,
        [spacing] * interval_count,
        "uniform",
        nominal=spacing,
    )


def plan_fixed_axis_distribution(
    total_length_mm: float,
    spacing_mm: float,
    start_offset_mm: float = 0.0,
    end_offset_mm: float = 0.0,
) -> dict:
    """Keep the entered spacing in interior intervals and adjust only both ends.

    The first and last *intervals between axes* are allowed to be exceptions.
    The explicit ``start_offset_mm`` and ``end_offset_mm`` from roof edges to the
    first/last axes remain unchanged.
    """
    total, nominal, start, end, usable = _validated_lengths(
        total_length_mm, spacing_mm, start_offset_mm, end_offset_mm
    )
    if usable <= _EPS:
        return _result(total, nominal, start, end, usable, [], "fixed", nominal=nominal)

    interval_count = max(1, int(math.ceil((usable / nominal) - 1e-12)))
    if interval_count == 1:
        intervals = [usable]
    elif interval_count == 2:
        edge = usable / 2.0
        intervals = [edge, edge]
    else:
        interior_count = interval_count - 2
        edge = (usable - interior_count * nominal) / 2.0
        # By construction edge is in (nominal/2, nominal], aside from tolerance.
        if edge <= _EPS or edge > nominal + 1e-7:
            # Defensive fallback; should not normally be reached.
            spacing = usable / interval_count
            intervals = [spacing] * interval_count
        else:
            intervals = [edge] + [nominal] * interior_count + [edge]

    return _result(total, nominal, start, end, usable, intervals, "fixed", nominal=nominal)


def plan_rounded_axis_distribution(
    total_length_mm: float,
    max_spacing_mm: float,
    round_step_mm: float = 50.0,
    start_offset_mm: float = 0.0,
    end_offset_mm: float = 0.0,
) -> dict:
    """Use a practical rounded nominal spacing, with edge exceptions if needed.

    The ideal uniform spacing is calculated first using the minimum number of
    intervals required by ``max_spacing_mm``. The nominal value is rounded upward
    to the requested construction step (normally 50 or 100 mm), without exceeding
    the requested maximum. If that is not possible, the largest rounded value below
    the maximum is used and the fixed planner may add one interval.
    """
    total, maximum, start, end, usable = _validated_lengths(
        total_length_mm, max_spacing_mm, start_offset_mm, end_offset_mm
    )
    step = float(round_step_mm)
    if step <= 0.0:
        raise ValueError("round_step_mm debe ser mayor que cero")
    if usable <= _EPS:
        return _result(
            total,
            maximum,
            start,
            end,
            usable,
            [],
            "rounded",
            nominal=0.0,
            extra={"round_step_mm": step, "ideal_spacing_mm": 0.0},
        )

    minimum_intervals = max(1, int(math.ceil((usable / maximum) - 1e-12)))
    ideal = usable / minimum_intervals
    rounded = math.ceil((ideal - 1e-12) / step) * step
    if rounded > maximum + 1e-9:
        rounded = math.floor((maximum + 1e-12) / step) * step
    if rounded <= _EPS:
        rounded = maximum

    data = plan_fixed_axis_distribution(total, rounded, start, end)
    data["mode"] = "rounded"
    data["max_spacing_mm"] = maximum
    data["rounded_nominal_mm"] = rounded
    data["round_step_mm"] = step
    data["ideal_spacing_mm"] = ideal
    return data
