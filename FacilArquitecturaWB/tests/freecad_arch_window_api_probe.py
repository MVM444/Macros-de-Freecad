"""Inspect native Arch door/window hosting in FreeCAD 1.1.3.

Description: audit-only executable probe for the API used by FacilArquitecturaWB.
Date: 2026-08-09
Version: 0.1.0
Maintenance: keep assertions focused on native Arch behavior, not FA implementation.
"""

from __future__ import annotations

import json
import os

import FreeCAD
import Arch
import ArchWindow


def preset_placement(x, z, wall_width):
    origin = FreeCAD.Vector(float(x), -float(wall_width) * 0.5, float(z))
    rotation = FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90)
    return FreeCAD.Placement(origin, rotation)


def main():
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_dir = os.path.dirname(package_dir)
    output_dir = os.path.join(repo_dir, ".codex_tmp")
    os.makedirs(output_dir, exist_ok=True)
    output_fcstd = os.path.join(output_dir, "freecad_arch_window_api_probe.FCStd")
    output_json = os.path.join(output_dir, "freecad_arch_window_api_probe.json")

    doc = FreeCAD.newDocument("ArchWindowAPIProbe")
    wall_width = 200.0
    wall = Arch.makeWall(None, length=5000.0, width=wall_width, height=3000.0)
    wall.Label = "Probe Wall"
    doc.recompute()
    volume_before = float(wall.Shape.Volume)

    door = Arch.makeWindowPreset(
        "Simple door",
        width=900.0,
        height=2100.0,
        h1=50.0,
        h2=50.0,
        h3=0.0,
        w1=wall_width,
        w2=40.0,
        o1=0.0,
        o2=(wall_width - 40.0) * 0.5,
        placement=preset_placement(700.0, 0.0, wall_width),
    )
    door.Label = "Probe Door"
    door.Opening = 100
    door.SymbolPlan = True
    door.HoleDepth = 0
    door.Hosts = [wall]
    wall.touch()
    doc.recompute()
    volume_after_door = float(wall.Shape.Volume)

    window = Arch.makeWindowPreset(
        "Sliding 2-pane",
        width=1200.0,
        height=1200.0,
        h1=60.0,
        h2=60.0,
        h3=0.0,
        w1=wall_width,
        w2=40.0,
        o1=0.0,
        o2=(wall_width - 40.0) * 0.5,
        placement=preset_placement(-1000.0, 900.0, wall_width),
    )
    window.Label = "Probe Window"
    window.Opening = 0
    window.SymbolPlan = True
    window.HoleDepth = 0
    window.Hosts = [wall]
    wall.touch()
    doc.recompute()
    volume_after_window = float(wall.Shape.Volume)
    door_subvolume = door.Proxy.getSubVolume(door, host=wall)
    window_subvolume = window.Proxy.getSubVolume(window, host=wall)

    assert door.TypeId == "Part::FeaturePython"
    assert window.TypeId == "Part::FeaturePython"
    assert door.IfcType == "Door"
    assert window.IfcType == "Window"
    assert door.Hosts == [wall]
    assert window.Hosts == [wall]
    print(
        "ARCH_WINDOW_API_VOLUMES",
        volume_before,
        volume_after_door,
        volume_after_window,
        "DOOR_HOLE",
        float(door.HoleDepth.Value),
        "WINDOW_HOLE",
        float(window.HoleDepth.Value),
        "WINDOW_BASE",
        tuple(window.Base.Placement.Base),
        "WINDOW_NORMAL",
        tuple(window.Normal),
        "DOOR_SUBVOLUME",
        float(door_subvolume.Volume) if door_subvolume else None,
        tuple(door_subvolume.BoundBox.Center) if door_subvolume else None,
        "WINDOW_SUBVOLUME",
        float(window_subvolume.Volume) if window_subvolume else None,
        tuple(window_subvolume.BoundBox.Center) if window_subvolume else None,
        "WINDOW_COMMON",
        float(wall.Shape.common(window_subvolume).Volume) if window_subvolume else None,
        "WALL_BBOX",
        (
            wall.Shape.BoundBox.XMin,
            wall.Shape.BoundBox.YMin,
            wall.Shape.BoundBox.ZMin,
            wall.Shape.BoundBox.XMax,
            wall.Shape.BoundBox.YMax,
            wall.Shape.BoundBox.ZMax,
        ),
        "WINDOW_SUB_BBOX",
        (
            window_subvolume.BoundBox.XMin,
            window_subvolume.BoundBox.YMin,
            window_subvolume.BoundBox.ZMin,
            window_subvolume.BoundBox.XMax,
            window_subvolume.BoundBox.YMax,
            window_subvolume.BoundBox.ZMax,
        ) if window_subvolume else None,
    )
    assert volume_after_door < volume_before
    assert volume_after_window < volume_after_door

    report = {
        "freecad_version": FreeCAD.Version(),
        "archwindow_allowed_hosts_exists": hasattr(ArchWindow, "AllowedHosts"),
        "door": {
            "type_id": door.TypeId,
            "proxy_module": door.Proxy.__class__.__module__,
            "proxy_class": door.Proxy.__class__.__name__,
            "base_type_id": door.Base.TypeId,
            "hosts_property_type": door.getTypeIdOfProperty("Hosts"),
            "hole_depth_exists": "HoleDepth" in door.PropertiesList,
            "opening_exists": "Opening" in door.PropertiesList,
            "window_parts_exists": "WindowParts" in door.PropertiesList,
            "move_with_host": bool(door.MoveWithHost),
            "ifc_type": door.IfcType,
        },
        "window": {
            "type_id": window.TypeId,
            "proxy_module": window.Proxy.__class__.__module__,
            "proxy_class": window.Proxy.__class__.__name__,
            "base_type_id": window.Base.TypeId,
            "hosts_property_type": window.getTypeIdOfProperty("Hosts"),
            "hole_depth_exists": "HoleDepth" in window.PropertiesList,
            "opening_exists": "Opening" in window.PropertiesList,
            "window_parts_exists": "WindowParts" in window.PropertiesList,
            "move_with_host": bool(window.MoveWithHost),
            "ifc_type": window.IfcType,
        },
        "wall": {
            "volume_before": volume_before,
            "volume_after_door": volume_after_door,
            "volume_after_window": volume_after_window,
            "door_cut_volume": volume_before - volume_after_door,
            "window_cut_volume": volume_after_door - volume_after_window,
        },
    }
    doc.saveAs(output_fcstd)
    with open(output_json, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    document_name = doc.Name
    wall_name = wall.Name
    door_name = door.Name
    window_name = window.Name
    FreeCAD.closeDocument(document_name)

    reopened = FreeCAD.openDocument(output_fcstd)
    reopened.recompute()
    reopened_wall = reopened.getObject(wall_name)
    reopened_door = reopened.getObject(door_name)
    reopened_window = reopened.getObject(window_name)
    assert reopened_door.Hosts == [reopened_wall]
    assert reopened_window.Hosts == [reopened_wall]
    assert float(reopened_wall.Shape.Volume) < volume_before
    FreeCAD.closeDocument(reopened.Name)
    print("ARCH_WINDOW_API_PROBE_OK", json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
