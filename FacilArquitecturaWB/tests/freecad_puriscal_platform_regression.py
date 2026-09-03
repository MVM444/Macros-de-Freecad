"""Non-destructive Puriscal regression for the line-driven service platform."""

from __future__ import annotations

import math
import os
import sys

import FreeCAD
import Part


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
MACROS_DIR = os.path.dirname(REPO_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.core.bim_structure_utils import add_to_container, collect_buildings  # noqa: E402
from FacilArquitecturaWB.core.opening_utils import collect_bim_walls, wall_source_segments  # noqa: E402
from FacilArquitecturaWB.modules.service_platform.builder import (  # noqa: E402
    create_service_platform_from_axis,
    update_service_platform_front,
)
from FacilArquitecturaWB.modules.service_platform.model import PlatformOptions  # noqa: E402
from FacilArquitecturaWB.modules.service_platform.source import axis_reference_from_source  # noqa: E402


def main():
    source_path = os.path.join(
        MACROS_DIR,
        "Respaldos",
        "Proyectos_prueba",
        "Puriscal",
        "Puriscal Depurado.FCStd",
    )
    output_dir = os.path.join(REPO_DIR, ".codex_tmp")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "Puriscal_Plataforma_desde_linea_regression.FCStd")
    source_mtime = os.path.getmtime(source_path)
    doc = FreeCAD.openDocument(source_path)
    doc.recompute()
    walls = collect_bim_walls(doc)
    wall_count = len(walls)
    candidates = []
    for wall in walls:
        for item in wall_source_segments(wall):
            segment = item["segment"]
            length = math.hypot(segment[3] - segment[0], segment[4] - segment[1])
            if length >= 3200.0:
                candidates.append((length, wall, segment))
    assert candidates, "Puriscal no contiene un tramo BIM de al menos 3200 mm"
    _length, expected_wall, segment = max(candidates, key=lambda item: item[0])
    expected_wall_name = expected_wall.Name
    ux = (segment[3] - segment[0]) / _length
    uy = (segment[4] - segment[1]) / _length
    margin = (_length - 3000.0) * 0.5
    first = (
        segment[0] + margin * ux,
        segment[1] + margin * uy,
        segment[2],
    )
    second = (first[0] + 3000.0 * ux, first[1] + 3000.0 * uy, first[2])
    sketch = doc.addObject("Sketcher::SketchObject", "Sketch_Centro_Plataforma_Prueba_Puriscal")
    sketch.Label = "Centro plataforma - prueba no destructiva"
    sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(*first), FreeCAD.Vector(*second)), False)
    buildings = collect_buildings(doc)
    if len(buildings) == 1:
        add_to_container(buildings[0], sketch)
    doc.recompute()
    result = create_service_platform_from_axis(
        doc,
        axis_reference_from_source(sketch),
        PlatformOptions(service_positions=3, staff_side="left", show_service_areas=False),
    )
    doc.recompute()
    assert result["host_wall"] is expected_wall
    assert len(result["root"].Group) == 2
    assert abs(result["layout"].position_width_mm - 1000.0) < 1e-6
    assert result["root"].FA_GlassOpeningCount == 3
    assert len(result["glass"].Shape.Solids) == 9
    assert len(collect_bim_walls(doc)) == wall_count
    if len(buildings) == 1:
        assert result["root"] in list(buildings[0].Group)
    before_update = len(doc.Objects)
    update_service_platform_front(doc, result["root"])
    doc.recompute()
    assert len(doc.Objects) == before_update
    assert len(collect_bim_walls(doc)) == wall_count
    root_name = result["root"].Name
    doc.saveAs(output_path)
    FreeCAD.closeDocument(doc.Name)
    assert os.path.getmtime(source_path) == source_mtime
    reopened = FreeCAD.openDocument(output_path)
    reopened.recompute()
    restored = reopened.getObject(root_name)
    assert restored is not None and restored.HostWall is not None
    assert restored.FA_GlassOpeningCount == 3
    before_restore = len(reopened.Objects)
    update_service_platform_front(reopened, restored)
    reopened.recompute()
    assert len(reopened.Objects) == before_restore
    FreeCAD.closeDocument(reopened.Name)
    print(
        "PURISCAL_PLATFORM_REGRESSION_OK",
        output_path,
        "host=" + expected_wall_name,
        "walls=" + str(wall_count),
    )


if __name__ == "__main__":
    main()
