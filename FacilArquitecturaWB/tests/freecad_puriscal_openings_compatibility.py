"""Compatibility smoke test for existing Puriscal BIM openings.

Descripcion: valida que los comandos nuevos no dupliquen aberturas historicas FA.
Fecha: 2026-08-09
Version: 0.1.0
Instrucciones: abrir solo la copia temporal y guardar el resultado en .codex_tmp.
"""

from __future__ import annotations

import os
import sys

import FreeCAD


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.core.opening_utils import (  # noqa: E402
    collect_bim_walls,
    collect_opening_sketches_from_document,
    collect_opening_sketches_from_selection,
    create_openings_from_centerlines,
)


def role_count(doc, role):
    return len([obj for obj in doc.Objects if str(getattr(obj, "FA_Role", "")) == role])


def main():
    source = os.path.join(
        REPO_DIR, ".codex_tmp", "Puriscal_Depurado_openings_audit_20260809.FCStd"
    )
    output = os.path.join(
        REPO_DIR, ".codex_tmp", "Puriscal_Depurado_openings_compatibility.FCStd"
    )
    assert os.path.isfile(source)
    doc = FreeCAD.openDocument(source)
    doc.recompute()
    wall = doc.getObject("Wall002")
    door_axes = doc.getObject("Sketch_Centros_Puertas")
    window_axes = doc.getObject("Sketch_Centros_Ventanas")
    assert wall is not None
    assert door_axes is not None
    assert window_axes is not None
    before_doors = role_count(doc, "door")
    before_windows = role_count(doc, "window")
    assert before_doors == 19
    assert before_windows == 8

    assert collect_opening_sketches_from_selection([door_axes, wall], "door") == [door_axes]
    assert collect_opening_sketches_from_selection([window_axes, wall], "window") == [window_axes]
    assert collect_opening_sketches_from_document(doc, "door") == [door_axes]
    assert collect_opening_sketches_from_document(doc, "window") == [window_axes]
    assert collect_bim_walls(doc, [door_axes, wall]) == [wall]

    doc.openTransaction("Puriscal compatibility doors")
    doors, door_summary = create_openings_from_centerlines(
        doc,
        doc.getObject("FA_BIM"),
        [door_axes],
        [wall],
        "door",
        height_mm=2100.0,
        host_tolerance_mm=250.0,
        replace_existing=True,
    )
    doc.commitTransaction()
    assert doors == []
    assert door_summary["created_count"] == 0
    assert door_summary["skipped_existing_count"] == 19

    doc.openTransaction("Puriscal compatibility windows")
    windows, window_summary = create_openings_from_centerlines(
        doc,
        doc.getObject("FA_BIM"),
        [window_axes],
        [wall],
        "window",
        height_mm=1200.0,
        sill_mm=900.0,
        host_tolerance_mm=250.0,
        replace_existing=True,
    )
    doc.commitTransaction()
    assert windows == []
    assert window_summary["created_count"] == 0
    assert window_summary["skipped_existing_count"] == 8
    assert role_count(doc, "door") == before_doors
    assert role_count(doc, "window") == before_windows

    doc.saveAs(output)
    FreeCAD.closeDocument(doc.Name)
    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    assert role_count(reopened, "door") == 19
    assert role_count(reopened, "window") == 8
    assert all(
        list(getattr(obj, "Hosts", []) or [])
        for obj in reopened.Objects
        if str(getattr(obj, "FA_Role", "")) in ("door", "window")
    )
    FreeCAD.closeDocument(reopened.Name)
    print(
        "PURISCAL_OPENINGS_COMPATIBILITY_OK",
        "doors=19 windows=8 created=0 duplicates=0 persistence=ok",
        output,
    )


if __name__ == "__main__":
    main()
