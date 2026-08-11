"""Full native BIM rebuild of every assigned La Cruz opening axis.

Descripcion: ejecuta una reconstruccion completa sobre la copia limpia de La Cruz,
incluyendo los cuatro Sketches de ventanas seleccionados por el usuario.
Objetivo: validar el caso real aunque los presets nativos requieran varios minutos.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 23:40 UTC-06:00.
Version: 0.1.0.
Instrucciones de mantenimiento: nunca guardar sobre el archivo original del usuario.
"""

from __future__ import annotations

import os
import sys

import FreeCAD
import Draft


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.core.bim_rebuild_utils import (  # noqa: E402
    rebuild_bim_model,
    suggest_rebuild_assignments,
)


def main():
    source = os.environ.get("FA_LA_CRUZ_SOURCE") or os.path.join(
        REPO_DIR, ".codex_tmp", "La_Cruz_V2_1_clean_audit.FCStd"
    )
    output = os.environ.get("FA_LA_CRUZ_OUTPUT") or os.path.join(
        REPO_DIR, ".codex_tmp", "La_Cruz_V2_1_BIM_full.FCStd"
    )
    assert os.path.isfile(source), source
    doc = FreeCAD.openDocument(source)
    analysis = suggest_rebuild_assignments(doc)
    assignments = dict(analysis["assignments"])
    assignments["windows"] = [
        doc.getObject(name)
        for name in (
            "Sketch_Centros_Ventanas_de_S_S",
            "Sketch_Centros_Ventanas001",
            "Sketch_Centros_Ventanales",
            "Sketch_Centros_Seleccion_14_objetos",
        )
    ]
    assert all(assignments["windows"])
    options = {
        "building_name": "Edificio La Cruz",
        "level_name": "Nivel 00",
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
    doc.openTransaction("La Cruz full native BIM rebuild")
    result = rebuild_bim_model(doc, assignments, options)
    doc.recompute()
    doc.commitTransaction()
    assert Draft.getType(result["walls"][0]) == "Wall"
    assert all(Draft.getType(obj) == "Structure" and obj.IfcType == "Column" for obj in result["columns"]["columns"])
    assert all(Draft.getType(obj) == "Window" and obj.IfcType == "Door" for obj in result["doors"])
    assert all(Draft.getType(obj) == "Window" and obj.IfcType == "Window" for obj in result["windows"])
    assert all(obj.Hosts == [result["walls"][0]] for obj in result["doors"] + result["windows"])
    assert all(float(obj.FA_CutVolume_mm3) > 0.0 for obj in result["doors"] + result["windows"])
    doc.saveAs(output)
    counts = (len(result["columns"]["points"]), len(result["doors"]), len(result["windows"]))
    rejected = (
        result["door_summary"]["rejected_count"],
        result["window_summary"]["rejected_count"],
    )
    FreeCAD.closeDocument(doc.Name)

    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    walls = [obj for obj in reopened.Objects if Draft.getType(obj) == "Wall"]
    doors = [obj for obj in reopened.Objects if getattr(obj, "IfcType", "") == "Door"]
    windows = [obj for obj in reopened.Objects if getattr(obj, "IfcType", "") == "Window"]
    assert len(walls) == 1
    assert len(doors) == counts[1]
    assert len(windows) == counts[2]
    assert all(obj.Hosts == [walls[0]] for obj in doors + windows)
    FreeCAD.closeDocument(reopened.Name)
    print(
        "LA_CRUZ_BIM_FULL_OK",
        "columns=%d doors=%d windows=%d rejected_doors=%d rejected_windows=%d persistence=ok"
        % (counts[0], counts[1], counts[2], rejected[0], rejected[1]),
        output,
        flush=True,
    )


if __name__ == "__main__":
    main()
