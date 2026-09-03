"""Create the line-driven platform result on a copy of La Cruz 2.1."""

from __future__ import annotations

import os
import sys

import FreeCAD
import Part


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.modules.service_platform.builder import (  # noqa: E402
    create_service_platform_from_axis,
    update_service_platform_front,
)
from FacilArquitecturaWB.modules.service_platform.model import PlatformOptions  # noqa: E402
from FacilArquitecturaWB.modules.service_platform.source import axis_reference_from_source  # noqa: E402


def main():
    input_path = os.path.join(REPO_DIR, ".codex_tmp", "La_Cruz_V2_1_clean_audit.FCStd")
    output_path = os.path.join(REPO_DIR, ".codex_tmp", "La_Cruz_V2_2_Plataforma_desde_linea.FCStd")
    source_mtime = os.path.getmtime(input_path)
    doc = FreeCAD.openDocument(input_path)
    sketch = doc.addObject("Sketcher::SketchObject", "Sketch_Centro_Plataforma")
    sketch.Label = "Centro plataforma de atencion"
    sketch.addGeometry(
        Part.LineSegment(
            FreeCAD.Vector(8457.343, 0.0, 0.0),
            FreeCAD.Vector(11457.343, 0.0, 0.0),
        ),
        False,
    )
    doc.recompute()
    result = create_service_platform_from_axis(
        doc,
        axis_reference_from_source(sketch),
        PlatformOptions(service_positions=3, staff_side="left", show_service_areas=False),
    )
    doc.recompute()
    assert abs(result["layout"].position_width_mm - 1000.0) < 1e-6
    assert len(result["root"].Group) == 2
    assert result["root"].FA_GlassOpeningCount == 3
    assert len(result["glass"].Shape.Solids) == 9
    for index in range(3):
        point = result["axis"].frame().local_to_global(index * 1000.0 + 500.0, 0.0, 890.0)
        assert not result["glass"].Shape.isInside(FreeCAD.Vector(*point), 1e-6, True)
    assert result["host_wall"] is None
    before_update = len(doc.Objects)
    update_service_platform_front(doc, result["root"])
    doc.recompute()
    assert len(doc.Objects) == before_update
    root_name = result["root"].Name
    doc.saveAs(output_path)
    FreeCAD.closeDocument(doc.Name)
    assert os.path.getmtime(input_path) == source_mtime
    reopened = FreeCAD.openDocument(output_path)
    reopened.recompute()
    root = reopened.getObject(root_name)
    assert root is not None and root.SourceObject is not None
    assert len(root.Group) == 2
    assert root.FA_GlassOpeningCount == 3
    assert len(root.FA_GlassRepresentation.Shape.Solids) == 9
    FreeCAD.closeDocument(reopened.Name)
    print(
        "LA_CRUZ_PLATFORM_LINE_OK",
        output_path,
        "positions=3",
        "module=1000.0mm",
        "glass_openings=3",
    )


if __name__ == "__main__":
    main()
