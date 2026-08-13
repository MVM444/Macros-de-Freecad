"""Full native BIM reconstruction validation on a copy of La Cruz 2.1.

Descripcion: reconstruye muros y columnas completos y una muestra controlada de
puerta/ventana en un Building/Level; guarda, reabre y repite el flujo.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 23:05 UTC-06:00.
Version: 0.1.0.
Instrucciones de mantenimiento: la entrada debe ser la copia .codex_tmp; nunca
guardar sobre La Cruz Version 2.1.FCStd.
"""

from __future__ import annotations

import os
import sys

import FreeCAD


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.core.bim_rebuild_utils import (  # noqa: E402
    rebuild_bim_model,
    suggest_rebuild_assignments,
)
from FacilArquitecturaWB.core.opening_utils import (  # noqa: E402
    evaluate_wall_candidate,
    sketch_segments,
)


def _by_name(doc, name):
    obj = doc.getObject(name)
    assert obj is not None, name
    return obj


def _count(doc, ifc_type):
    return len([obj for obj in doc.Objects if str(getattr(obj, "IfcType", "")) == ifc_type])


def _keep_one_hosted_axis(source, wall_source, tolerance=300.0):
    wall_segments = [item["segment"] for item in sketch_segments(wall_source)]
    candidates = [
        item
        for item in sketch_segments(source)
        if evaluate_wall_candidate(item["segment"], wall_segments, tolerance) is not None
    ]
    assert candidates, "No compatible axis in " + source.Name
    keep = int(candidates[0]["index"])
    for geometry_index in range(len(source.Geometry)):
        should_be_construction = geometry_index != keep
        if bool(source.getConstruction(geometry_index)) != should_be_construction:
            source.toggleConstruction(geometry_index)
    return keep


def main():
    source = os.path.join(REPO_DIR, ".codex_tmp", "La_Cruz_V2_1_clean_audit.FCStd")
    output = os.path.join(REPO_DIR, ".codex_tmp", "La_Cruz_V2_1_BIM_validated_sample.FCStd")
    assert os.path.isfile(source), source
    doc = FreeCAD.openDocument(source)
    doc.UndoMode = 1
    analysis = suggest_rebuild_assignments(doc)
    suggested = analysis["assignments"]
    assert suggested["walls"].Name == "FA_GridWallTrace"
    assert suggested["columns"].Name == "Sketch_Centros_Columna_Metalica_Columnas"
    assert suggested["doors"].Name == "Sketch_Centros_Puertas"
    assert {obj.Name for obj in suggested["windows"]} == {
        "Sketch_Centros_Ventanas_de_S_S",
        "Sketch_Centros_Ventanas001",
        "Sketch_Centros_Ventanales",
    }
    assignments = dict(suggested)
    assignments["windows"] = [_by_name(doc, "Sketch_Centros_Ventanas_de_S_S")]
    # The native preset recomputes the compound Wall three times per opening.
    # Keep one real La Cruz axis of each kind for bounded persistence testing;
    # pure tests above still validate discovery of all four user-reported sources.
    _keep_one_hosted_axis(assignments["doors"], assignments["walls"])
    _keep_one_hosted_axis(assignments["windows"][0], assignments["walls"])
    options = {
        "building_name": "Edificio La Cruz",
        "level_name": "Nivel 00",
        "elevation_mm": 0.0,
        "wall_thickness_mm": 150.0,
        "wall_height_mm": 3000.0,
        "column_width_mm": 150.0,
        "column_depth_mm": 150.0,
        "column_height_mm": 3000.0,
        "door_height_mm": 2100.0,
        "window_height_mm": 1200.0,
        "window_sill_mm": 900.0,
        "host_tolerance_mm": 300.0,
    }
    doc.openTransaction("La Cruz BIM rebuild validation")
    result = rebuild_bim_model(doc, assignments, options)
    doc.recompute()
    doc.commitTransaction()
    assert result["building"].IfcType == "Building"
    assert result["level"].IfcType == "Building Storey"
    assert result["level"] in result["building"].Group
    assert len(result["walls"]) == 1
    assert result["walls"][0].Base is suggested["walls"]
    assert result["walls"][0] in result["level"].Group
    assert result["columns"] is not None
    assert result["columns"]["points"]
    assert all(column.IfcType == "Column" for column in result["columns"]["columns"])
    assert result["doors"]
    assert result["windows"]
    assert all(obj.Hosts == [obj.FA_HostWall] for obj in result["doors"] + result["windows"])
    assert all(float(obj.FA_CutVolume_mm3) > 0.0 for obj in result["doors"] + result["windows"])
    assert doc.getObject("FA_Project") is None
    assert doc.getObject("FA_Doors") is None
    assert doc.getObject("FA_Windows") is None
    assert all(source_obj in result["level"].Group for source_obj in result["organized_sources"])
    counts = {
        "doors": len(result["doors"]),
        "windows": len(result["windows"]),
        "columns": len(result["columns"]["points"]),
    }
    doc.saveAs(output)
    FreeCAD.closeDocument(doc.Name)

    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    assert _count(reopened, "Building") == 1
    assert _count(reopened, "Building Storey") == 1
    assert _count(reopened, "Wall") >= 1
    reopened_analysis = suggest_rebuild_assignments(reopened)
    reopened_assignments = dict(reopened_analysis["assignments"])
    reopened_assignments["windows"] = [_by_name(reopened, "Sketch_Centros_Ventanas_de_S_S")]
    reopened.openTransaction("La Cruz BIM rebuild idempotence")
    repeated = rebuild_bim_model(reopened, reopened_assignments, options)
    reopened.recompute()
    reopened.commitTransaction()
    assert len(repeated["doors"]) == counts["doors"]
    assert len(repeated["windows"]) == counts["windows"]
    assert len(repeated["columns"]["points"]) == counts["columns"]
    assert _count(reopened, "Building") == 1
    assert _count(reopened, "Building Storey") == 1
    reopened.undo()
    reopened.recompute()
    reopened.redo()
    reopened.recompute()
    reopened.save()
    FreeCAD.closeDocument(reopened.Name)
    print(
        "LA_CRUZ_BIM_REBUILD_OK",
        "walls=1 columns=%d doors_sample=%d windows_sample=%d persistence=ok idempotence=ok undo_redo=ok"
        % (counts["columns"], counts["doors"], counts["windows"]),
        output,
    )


if __name__ == "__main__":
    main()
