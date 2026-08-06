"""Master-sketch creation for service platform fronts."""

from __future__ import annotations

import FreeCAD
import Part
import Sketcher

from .calculator import position_origins
from .properties import tag_representation


SKETCH_SPECS = (
    ("SK_PA_FrontAxis", "front_axis", (0.90, 0.55, 0.10)),
    ("SK_PA_DeskEnvelopes", "desk_envelopes", (0.55, 0.30, 0.12)),
    ("SK_PA_Dividers", "dividers", (0.25, 0.25, 0.25)),
    ("SK_PA_StaffZones", "staff_zones", (0.20, 0.65, 0.25)),
    ("SK_PA_PublicZones", "public_zones", (0.20, 0.40, 0.85)),
    ("SK_PA_PositionAxes", "position_axes", (0.85, 0.65, 0.15)),
)


def create_master_sketches(doc, group, owner, options, layout):
    """Create exactly one master sketch per geometric system."""
    result = {}
    for label, role, color in SKETCH_SPECS:
        name = "%s__%s" % (owner.Name, label)
        sketch = doc.addObject("Sketcher::SketchObject", name)
        sketch.Label = label
        group.addObject(sketch)
        tag_representation(sketch, owner, "Plan", role)
        _set_view(sketch, color)
        result[label] = sketch

    y0 = options.front_offset_mm
    _add_line(result["SK_PA_FrontAxis"], 0.0, y0, options.total_width_mm, y0)
    _add_axis_constraint(result["SK_PA_FrontAxis"], 0)

    origins = position_origins(options, layout)
    for x in origins:
        _add_rectangle(
            result["SK_PA_DeskEnvelopes"], x, y0, layout.position_width_mm, options.desk_depth_mm
        )
        _add_rectangle(
            result["SK_PA_StaffZones"],
            x,
            y0 + options.desk_depth_mm,
            layout.position_width_mm,
            options.staff_zone_depth_mm,
        )
        _add_rectangle(
            result["SK_PA_PublicZones"],
            x,
            y0 - options.public_zone_depth_mm,
            layout.position_width_mm,
            options.public_zone_depth_mm,
        )
        axis_x = x + layout.position_width_mm * 0.5
        index = _add_line(
            result["SK_PA_PositionAxes"],
            axis_x,
            y0 - options.public_zone_depth_mm,
            axis_x,
            y0 + options.desk_depth_mm + options.staff_zone_depth_mm,
            construction=True,
        )
        _add_axis_constraint(result["SK_PA_PositionAxes"], index, vertical=True)

    for index in range(layout.divider_count):
        x = origins[index] + layout.position_width_mm
        _add_rectangle(
            result["SK_PA_Dividers"],
            x,
            y0,
            options.divider_thickness_mm,
            options.divider_depth_mm,
        )
    return result


def _add_line(sketch, x1, y1, x2, y2, construction=False):
    geometry = Part.LineSegment(
        FreeCAD.Vector(float(x1), float(y1), 0.0),
        FreeCAD.Vector(float(x2), float(y2), 0.0),
    )
    try:
        return sketch.addGeometry(geometry, bool(construction))
    except TypeError:
        index = sketch.addGeometry(geometry)
        if construction:
            try:
                sketch.toggleConstruction(index)
            except Exception:
                pass
        return index


def _add_rectangle(sketch, x, y, width, depth):
    indices = (
        _add_line(sketch, x, y, x + width, y),
        _add_line(sketch, x + width, y, x + width, y + depth),
        _add_line(sketch, x + width, y + depth, x, y + depth),
        _add_line(sketch, x, y + depth, x, y),
    )
    for index, kind in zip(indices, ("Horizontal", "Vertical", "Horizontal", "Vertical")):
        _safe_constraint(sketch, Sketcher.Constraint(kind, index))
    for left, right in zip(indices, indices[1:] + indices[:1]):
        _safe_constraint(sketch, Sketcher.Constraint("Coincident", left, 2, right, 1))


def _add_axis_constraint(sketch, index, vertical=False):
    _safe_constraint(sketch, Sketcher.Constraint("Vertical" if vertical else "Horizontal", index))


def _safe_constraint(sketch, constraint):
    try:
        sketch.addConstraint(constraint)
    except Exception:
        pass


def _set_view(obj, color):
    try:
        obj.ViewObject.LineColor = color
        obj.ViewObject.LineWidth = 2.0
    except Exception:
        pass
