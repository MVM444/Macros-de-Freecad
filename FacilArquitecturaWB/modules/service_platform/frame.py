"""FreeCAD-independent local frame calculations for a selected platform line."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .validation import PlatformValidationError


MIN_AXIS_LENGTH_MM = 500.0
MAX_AXIS_Z_DELTA_MM = 1.0


@dataclass(frozen=True)
class AxisFrame:
    """Right-handed XY frame whose local X follows P0 to P1."""

    p0: tuple[float, float, float]
    p1: tuple[float, float, float]
    length_mm: float
    x_unit: tuple[float, float]
    left_unit: tuple[float, float]
    angle_deg: float

    def local_to_global(self, x: float, y: float, z: float = 0.0):
        return (
            self.p0[0] + float(x) * self.x_unit[0] + float(y) * self.left_unit[0],
            self.p0[1] + float(x) * self.x_unit[1] + float(y) * self.left_unit[1],
            self.p0[2] + float(z),
        )


def build_axis_frame(first, second, invert=False) -> AxisFrame:
    """Validate a horizontal-in-plan line and derive its local coordinate frame."""
    p0 = _point(first)
    p1 = _point(second)
    if bool(invert):
        p0, p1 = p1, p0
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    length = math.hypot(dx, dy)
    if length < MIN_AXIS_LENGTH_MM:
        raise PlatformValidationError(
            "La linea seleccionada mide %.1f mm; debe medir al menos %.1f mm."
            % (length, MIN_AXIS_LENGTH_MM)
        )
    if abs(p1[2] - p0[2]) > MAX_AXIS_Z_DELTA_MM:
        raise PlatformValidationError(
            "La linea debe estar en un plano horizontal; la diferencia Z es %.1f mm."
            % abs(p1[2] - p0[2])
        )
    unit = (dx / length, dy / length)
    return AxisFrame(
        p0=p0,
        p1=p1,
        length_mm=length,
        x_unit=unit,
        left_unit=(-unit[1], unit[0]),
        angle_deg=math.degrees(math.atan2(unit[1], unit[0])),
    )


def _point(value):
    if hasattr(value, "x"):
        return float(value.x), float(value.y), float(getattr(value, "z", 0.0))
    values = tuple(float(item) for item in value)
    if len(values) == 2:
        return values[0], values[1], 0.0
    if len(values) != 3:
        raise PlatformValidationError("Cada extremo de la linea debe tener dos o tres coordenadas.")
    return values
