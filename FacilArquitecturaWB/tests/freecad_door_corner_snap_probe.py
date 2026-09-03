"""Read-only MCP/FreeCAD probe for FA door corner snapping.

Nombre: freecad_door_corner_snap_probe.py
Proposito: diagnosticar en FreeCAD real que puertas tienen una pared lateral unica
cercana y que snap/bisagra/apertura propone Facil Arquitectura antes de modificar.
Funcionamiento: no crea ni elimina objetos; imprime un reporte JSON-compatible.
FreeCAD objetivo: 1.1.3.
Version: 0.1.0.
Fecha y hora: 2026-08-28 20:20 UTC-06:00.
Mantenimiento: mantener solo lectura. Ejecutar antes de validar cambios destructivos.
"""

from __future__ import annotations

import json

import FreeCAD

from FacilArquitecturaWB.core.opening_utils import (
    collect_bim_walls,
    collect_opening_sketches_from_document,
    resolve_door_corner_snap,
    select_best_host,
    sketch_segments,
    wall_source_segments,
)


def run(doc=None, host_tolerance_mm=250.0, corner_tolerance_mm=180.0):
    doc = doc or FreeCAD.ActiveDocument
    if doc is None:
        raise RuntimeError("No hay documento activo")
    sources = collect_opening_sketches_from_document(doc, "door")
    walls = collect_bim_walls(doc)
    wall_records = [
        {"wall": wall, "segments": [item["segment"] for item in wall_source_segments(wall)]}
        for wall in walls
    ]
    wall_records = [item for item in wall_records if item["segments"]]
    entries = []
    for source in sources:
        for axis in sketch_segments(source):
            selection = select_best_host(axis["segment"], wall_records, host_tolerance_mm)
            row = {
                "source": source.Name,
                "geometry_index": int(axis["index"]),
                "host_ambiguous": bool(selection["ambiguous"]),
                "host": "",
                "corner_applied": False,
                "corner_ambiguous": False,
            }
            if selection["ambiguous"] or selection["match"] is None:
                entries.append(row)
                continue
            match = selection["match"]
            row["host"] = match["wall"].Name
            corner = resolve_door_corner_snap(match, wall_records, tolerance_mm=corner_tolerance_mm)
            row.update(
                {
                    "corner_applied": bool(corner.get("applied")),
                    "corner_ambiguous": bool(corner.get("ambiguous")),
                    "side_wall": str(corner.get("side_wall_label") or ""),
                    "gap_before_mm": round(float(corner.get("snap_distance_mm") or 0.0), 3),
                    "shift_mm": round(float(corner.get("shift_mm") or 0.0), 3),
                    "hinge_endpoint": str(corner.get("hinge_endpoint") or "AUTO"),
                    "opening_side": str(corner.get("opening_side") or "AUTO"),
                    "opens_inward": corner.get("opens_inward"),
                    "reason": str(corner.get("reason") or ""),
                }
            )
            entries.append(row)
    report = {
        "document": doc.Name,
        "door_sketches": len(sources),
        "walls": len(wall_records),
        "door_axes": len(entries),
        "corner_snapped_candidates": sum(1 for item in entries if item["corner_applied"]),
        "corner_ambiguous": sum(1 for item in entries if item["corner_ambiguous"]),
        "entries": entries,
    }
    print("[FACILARQ][DOOR-CORNER] " + json.dumps(report, ensure_ascii=True, indent=2))
    return report


REPORT = run()
