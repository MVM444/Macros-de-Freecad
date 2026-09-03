"""FreeCAD 1.1 smoke test for compact platforms driven by source lines."""

from __future__ import annotations

import os
import sys

import Arch
import FreeCAD
import Part
import Sketcher


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.modules.service_platform.builder import (  # noqa: E402
    create_service_platform_from_axis,
    update_service_platform_front,
)
from FacilArquitecturaWB.modules.service_platform.model import PlatformOptions  # noqa: E402
from FacilArquitecturaWB.modules.service_platform.source import (  # noqa: E402
    axis_reference_from_source,
    resolve_axis_from_selection,
)
from FacilArquitecturaWB.modules.service_platform.validation import PlatformValidationError  # noqa: E402


def _sketch(doc, name, first, second, placement=None):
    sketch = doc.addObject("Sketcher::SketchObject", name)
    sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(*first), FreeCAD.Vector(*second)), False)
    if placement is not None:
        sketch.Placement = placement
    return sketch


def _assert_compact(result, positions):
    root = result["root"]
    assert len(list(root.Group)) == 2, [obj.Name for obj in root.Group]
    assert result["body"] in root.Group and result["glass"] in root.Group
    opening_has_lower_piece = root.AlturaAberturaVidrio.Value > root.AlturaMostrador.Value
    pieces_per_position = 4 if opening_has_lower_piece else 3
    expected_glass_solids = positions * (pieces_per_position if root.MostrarAberturaVidrio else 1)
    assert len(result["glass"].Shape.Solids) == expected_glass_solids
    assert root.FA_GlassOpeningCount == (positions if root.MostrarAberturaVidrio else 0)
    assert result["glass"].FA_GlassOpeningCount == root.FA_GlassOpeningCount
    expected_body = 2 + positions + max(positions - 1, 0) + positions + 1
    assert len(result["body"].Shape.Solids) == expected_body, len(result["body"].Shape.Solids)
    assert root.MostrarAreasAtencion is False
    assert root.IfcType == "Furniture" and root.FA_CreateWall is False
    assert root.LongitudTotal.Value > 0.0
    assert root.SourceObject is not None


class _SelectionRecord:
    def __init__(self, obj, names=None):
        self.Object = obj
        self.SubElementNames = list(names or [])


def main():
    output_dir = os.path.join(REPO_DIR, ".codex_tmp")
    os.makedirs(output_dir, exist_ok=True)
    output = os.path.join(output_dir, "service_platform_line_smoke.FCStd")

    doc = FreeCAD.newDocument("ServicePlatformLineSmoke")
    placement = FreeCAD.Placement(
        FreeCAD.Vector(1250.0, 2400.0, 0.0),
        FreeCAD.Rotation(FreeCAD.Vector(0.0, 0.0, 1.0), 30.0),
    )
    source = _sketch(doc, "Sketch_Centro_Plataforma", (0, 0, 0), (3000, 0, 0), placement)
    doc.recompute()
    axis = axis_reference_from_source(source)
    selected_axis = resolve_axis_from_selection([_SelectionRecord(source)])
    assert selected_axis.source_object is source
    assert abs(axis.frame().length_mm - 3000.0) < 1e-6
    result = create_service_platform_from_axis(
        doc,
        axis,
        PlatformOptions(
            total_width_mm=1.0,
            service_positions=3,
            staff_side="left",
            create_functional_zones=False,
            show_service_areas=False,
        ),
    )
    doc.recompute()
    _assert_compact(result, 3)
    root = result["root"]
    body = result["body"]
    glass = result["glass"]
    assert root.MostrarAberturaVidrio is True
    assert abs(root.AnchoAberturaVidrio.Value - 300.0) < 1e-6
    assert abs(root.AltoAberturaVidrio.Value - 300.0) < 1e-6
    assert root.FA_GlassOpeningDimensionStatus == "PROVISIONAL_EDITABLE_NO_NORMATIVO"

    # The compound is genuinely empty at the center of every opening.
    frame = result["axis"].frame(False)
    for index in range(3):
        point = frame.local_to_global(index * 1000.0 + 500.0, 0.0, 890.0)
        assert not glass.Shape.isInside(FreeCAD.Vector(*point), 1e-6, True), point
    object_count = len(doc.Objects)

    # Width and height regenerate the existing glass representation in place.
    initial_glass_volume = glass.Shape.Volume
    root.AnchoAberturaVidrio = 420.0
    root.AltoAberturaVidrio = 260.0
    root.AlturaAberturaVidrio = 800.0
    resized = update_service_platform_front(doc, root)
    doc.recompute()
    assert resized["glass"] is glass
    assert glass.Shape.Volume != initial_glass_volume
    assert len(doc.Objects) == object_count

    # A translated and rotated source is reread; representations update in place.
    source.Placement = FreeCAD.Placement(
        FreeCAD.Vector(4200.0, -1750.0, 0.0),
        FreeCAD.Rotation(FreeCAD.Vector(0.0, 0.0, 1.0), 90.0),
    )
    root.NumeroPuestos = 1
    root.LadoFuncionario = "right"
    root.InvertirDireccion = True
    updated = update_service_platform_front(doc, root)
    doc.recompute()
    _assert_compact(updated, 1)
    assert updated["body"] is body and updated["glass"] is glass
    assert len(doc.Objects) == object_count
    assert abs(body.Shape.BoundBox.XMin - 3600.0) < 1e-4, body.Shape.BoundBox.XMin

    # Optional areas are not present by default and can be toggled without duplicates.
    root.MostrarAreasAtencion = True
    with_areas = update_service_platform_front(doc, root)
    doc.recompute()
    areas = with_areas["areas"]
    assert areas is not None
    root.MostrarAreasAtencion = False
    without_areas = update_service_platform_front(doc, root)
    doc.recompute()
    assert without_areas["areas"] is None

    # Direct Part/Draft-style single-edge sources work without a wall.
    edge_source = doc.addObject("Part::Feature", "Linea_Plataforma_Directa")
    edge_source.Shape = Part.makeLine(FreeCAD.Vector(0, 5000, 0), FreeCAD.Vector(5000, 5000, 0))
    direct_axis = resolve_axis_from_selection([_SelectionRecord(edge_source, ["Edge1"])])
    direct = create_service_platform_from_axis(
        doc,
        direct_axis,
        PlatformOptions(service_positions=5, staff_side="right", show_service_areas=False),
    )
    doc.recompute()
    _assert_compact(direct, 5)
    assert direct["host_wall"] is None

    # Compact v0.10.0 owners without the four new properties migrate on update.
    old_root = direct["root"]
    old_count = len(doc.Objects)
    for name in (
        "AnchoAberturaVidrio",
        "AltoAberturaVidrio",
        "AlturaAberturaVidrio",
        "MostrarAberturaVidrio",
    ):
        old_root.removeProperty(name)
    migrated = update_service_platform_front(doc, old_root)
    doc.recompute()
    assert migrated["root"].MostrarAberturaVidrio is True
    assert migrated["root"].FA_GlassOpeningCount == 5
    assert len(doc.Objects) == old_count

    # A unique collinear Arch Wall is linked, not recreated.
    wall_axis = _sketch(doc, "WallAxis", (-1000, 9000, 0), (5000, 9000, 0))
    wall = Arch.makeWall(wall_axis)
    wall.Width = 120.0
    wall.Height = 3000.0
    hosted_source = _sketch(doc, "HostedPlatformAxis", (0, 9000, 0), (3000, 9000, 0))
    doc.recompute()
    wall_count = sum(1 for obj in doc.Objects if str(getattr(getattr(obj, "Proxy", None), "Type", "")) == "Wall")
    hosted = create_service_platform_from_axis(
        doc,
        axis_reference_from_source(hosted_source),
        PlatformOptions(service_positions=3, show_service_areas=False),
    )
    doc.recompute()
    assert hosted["host_wall"] is wall
    assert hosted["root"].HostWall is wall
    assert wall_count == sum(
        1 for obj in doc.Objects if str(getattr(getattr(obj, "Proxy", None), "Type", "")) == "Wall"
    )

    # Ambiguous Sketches and sloped lines fail before creating a platform.
    ambiguous = _sketch(doc, "AmbiguousAxis", (0, 0, 0), (1000, 0, 0))
    ambiguous.addGeometry(Part.LineSegment(FreeCAD.Vector(0, 100, 0), FreeCAD.Vector(1000, 100, 0)), False)
    sloped = _sketch(doc, "SlopedAxis", (0, 0, 0), (1000, 0, 20))
    for invalid in (ambiguous, sloped):
        before = len(doc.Objects)
        try:
            axis_reference_from_source(invalid)
            raise AssertionError("Invalid source accepted: %s" % invalid.Name)
        except PlatformValidationError:
            pass
        assert len(doc.Objects) == before

    doc.recompute()
    root_name = root.Name
    body_name = body.Name
    glass_name = glass.Name
    doc.saveAs(output)
    FreeCAD.closeDocument(doc.Name)
    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    restored_root = reopened.getObject(root_name)
    assert restored_root.SourceObject is not None
    assert reopened.getObject(body_name) is not None
    assert reopened.getObject(glass_name) is not None
    before_update = len(reopened.Objects)
    restored = update_service_platform_front(reopened, restored_root)
    reopened.recompute()
    assert len(reopened.Objects) == before_update
    assert restored["body"].Name == body_name and restored["glass"].Name == glass_name
    reopened.save()
    FreeCAD.closeDocument(reopened.Name)
    print("SERVICE_PLATFORM_LINE_SMOKE_OK", output)


if __name__ == "__main__":
    main()
