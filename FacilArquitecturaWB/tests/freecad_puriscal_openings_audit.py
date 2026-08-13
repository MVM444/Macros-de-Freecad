"""Read-only audit of native openings in a copied Puriscal model.

Description: report existing FA door/window objects, hosts and source metadata.
Date: 2026-08-09
Version: 0.1.0
Maintenance: never save the inspected Puriscal copy from this script.
"""

from __future__ import annotations

import json
import os

import FreeCAD
import Draft


def quantity(value):
    try:
        return float(getattr(value, "Value", value))
    except Exception:
        return 0.0


def object_record(obj):
    hosts = list(getattr(obj, "Hosts", []) or [])
    source = getattr(obj, "FA_SourceDoorAxes", None) or getattr(
        obj, "FA_SourceWindowAxes", None
    )
    return {
        "name": obj.Name,
        "label": obj.Label,
        "draft_type": Draft.getType(obj),
        "type_id": obj.TypeId,
        "ifc_type": str(getattr(obj, "IfcType", "") or ""),
        "hosts": [host.Name for host in hosts],
        "base": getattr(getattr(obj, "Base", None), "Name", None),
        "source": getattr(source, "Name", None),
        "source_geometry_index": int(getattr(obj, "FA_SourceGeometryIndex", -1)),
        "source_geometry_indices": str(getattr(obj, "FA_SourceGeometryIndices", "") or ""),
        "width": quantity(getattr(obj, "Width", 0.0)),
        "height": quantity(getattr(obj, "Height", 0.0)),
        "sill": quantity(getattr(obj, "FA_SillHeight", 0.0)),
        "generated_by": str(getattr(obj, "FA_GeneratedBy", "") or ""),
    }


def main():
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_dir = os.path.dirname(package_dir)
    source = os.path.join(
        repo_dir, ".codex_tmp", "Puriscal_Depurado_openings_audit_20260809.FCStd"
    )
    output = os.path.join(repo_dir, ".codex_tmp", "puriscal_openings_audit.json")
    assert os.path.isfile(source), source

    doc = FreeCAD.openDocument(source)
    doc.recompute()
    doors = [obj for obj in doc.Objects if str(getattr(obj, "FA_Role", "")) == "door"]
    windows = [obj for obj in doc.Objects if str(getattr(obj, "FA_Role", "")) == "window"]
    walls = sorted(
        {host for obj in doors + windows for host in list(getattr(obj, "Hosts", []) or [])},
        key=lambda obj: obj.Name,
    )
    report = {
        "source_copy": source,
        "object_count": len(doc.Objects),
        "doors": [object_record(obj) for obj in doors],
        "windows": [object_record(obj) for obj in windows],
        "hosts": [
            {
                "name": wall.Name,
                "label": wall.Label,
                "draft_type": Draft.getType(wall),
                "type_id": wall.TypeId,
                "volume": quantity(getattr(wall.Shape, "Volume", 0.0)),
                "width": quantity(getattr(wall, "Width", 0.0)),
                "height": quantity(getattr(wall, "Height", 0.0)),
            }
            for wall in walls
        ],
    }
    assert doors
    assert windows
    assert all(record["draft_type"] == "Window" for record in report["doors"] + report["windows"])
    assert all(record["hosts"] for record in report["doors"] + report["windows"])
    assert all(record["base"] for record in report["doors"] + report["windows"])
    assert all(record["ifc_type"] == "Door" for record in report["doors"])
    assert all(record["ifc_type"] == "Window" for record in report["windows"])

    with open(output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=True)
    FreeCAD.closeDocument(doc.Name)
    print(
        "PURISCAL_OPENINGS_AUDIT_OK",
        "doors=%d" % len(doors),
        "windows=%d" % len(windows),
        "hosts=%s" % ",".join(item["name"] for item in report["hosts"]),
        "output=" + output,
    )


if __name__ == "__main__":
    main()
