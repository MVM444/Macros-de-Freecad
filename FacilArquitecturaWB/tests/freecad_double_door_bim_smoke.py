"""FreeCADCmd smoke test for the generic double BIM door factory."""

from __future__ import annotations

import json
import os
import sys

import Arch
import FreeCAD as App
import Part
import Sketcher


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))
MACROS_ROOT = os.path.dirname(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from FacilArquitecturaWB.core.double_door_bim import (  # noqa: E402
    GENERATOR,
    create_double_door_bim,
    host_insertion_for_wall,
    validate_host_opening,
)


def main():
    doc = App.newDocument("FA_DoubleDoorBIM_Smoke")
    wall_sketch = doc.addObject("Sketcher::SketchObject", "WallCenterline")
    wall_sketch.addGeometry(
        Part.LineSegment(App.Vector(-3000.0, 0.0, 0.0), App.Vector(3000.0, 0.0, 0.0)),
        False,
    )
    wall = Arch.makeWall(wall_sketch, width=200.0, height=3000.0, name="SmokeWall")
    wall.Label = "Muro BIM de prueba"
    wall.IfcType = "Wall"
    doc.recompute()
    before = wall.Shape.copy()
    before_volume = float(wall.Shape.Volume)

    group = doc.addObject("App::DocumentObjectGroup", "FA_Doors")
    host_context = host_insertion_for_wall(
        wall, 2000.0, App.Vector(0.0, 0.0, 0.0)
    )
    door, profile = create_double_door_bim(
        doc,
        placement=host_context["placement"],
        host=wall,
        target_container=group,
        opening=0,
        host_context=host_context,
    )
    wall.touch()
    doc.recompute()
    cut_result = validate_host_opening(
        door, wall, before, host_context=host_context
    )
    cut_volume = cut_result["cut_volume_mm3"]

    assert door.TypeId == "Part::FeaturePython"
    assert door.Proxy.__class__.__module__ == "ArchWindow"
    assert door.IfcType == "Door"
    assert abs(door.Width.Value - 2000.0) < 1e-6
    assert abs(door.Height.Value - 2100.0) < 1e-6
    assert len(door.WindowParts) == 65
    assert len(door.Shape.Solids) == 13
    assert door.Base is profile and door.Profile is profile
    assert profile.Owner is door
    if App.GuiUp and profile.ViewObject:
        assert not profile.ViewObject.Visibility
    assert wall in list(door.Hosts)
    assert door.FA_HostWallName == wall.Name
    assert bool(door.MoveWithHost)
    assert door.HoleWire == 1
    assert door.HoleDepth.Value == 0.0
    assert door.Subvolume is None
    assert door.FA_GeneratedBy == GENERATOR
    assert cut_volume > 1.0
    assert cut_result["cut_status"] == "new_bim_cut"
    assert cut_result["intersection_after_mm3"] <= 1.0
    assert float(wall.Shape.Volume) < before_volume - 1.0
    assert door.FA_CutStatus == "new_bim_cut"

    existing_hole_shape = wall.Shape.copy()
    overlap_door, overlap_profile = create_double_door_bim(
        doc,
        placement=host_context["placement"],
        host=wall,
        target_container=group,
        opening=0,
        label="Puerta doble sobre hueco existente",
        host_context=host_context,
    )
    wall.touch()
    doc.recompute()
    overlap_result = validate_host_opening(
        overlap_door,
        wall,
        existing_hole_shape,
        host_context=host_context,
    )
    assert overlap_result["cut_status"] == "preexisting_opening"
    assert overlap_result["cut_volume_mm3"] == 0.0
    assert overlap_result["nominal_overlap_mm3"] > 1.0
    overlap_door.Hosts = []
    doc.removeObject(overlap_door.Name)
    doc.removeObject(overlap_profile.Name)
    wall.touch()
    doc.recompute()

    materials = list(door.Material.Materials)
    assert len(materials) == 3
    assert [int(material.Transparency) for material in materials] == [0, 0, 70]
    for material in materials:
        assert "DiffuseColor" in material.Material
        assert "Transparency" in material.Material
        diffuse = tuple(
            float(value)
            for value in material.Material["DiffuseColor"].strip("()[]").split(",")
        )
        assert len(diffuse) == 3
    assert materials[0].Color[:3] != materials[1].Color[:3]
    assert materials[2].Color[:3] != materials[0].Color[:3]

    initial_centers = _solid_centers(door)
    fixed = initial_centers[0]
    opening_centers = {}
    for opening in (25, 50, 100, 0):
        door.Opening = opening
        doc.recompute()
        assert len(door.Shape.Solids) == 13
        opening_centers[opening] = _solid_centers(door)
    opened = opening_centers[25]
    fixed_after = opening_centers[0][0]
    assert (fixed_after - fixed).Length < 1e-6
    assert opened[1].y > initial_centers[1].y + 1.0
    assert opened[7].y > initial_centers[7].y + 1.0
    assert opened[1].x < initial_centers[1].x
    assert opened[7].x > initial_centers[7].x
    for indexes in (range(1, 7), range(7, 13)):
        anchor = indexes[0]
        for index in indexes:
            before_distance = (initial_centers[index] - initial_centers[anchor]).Length
            after_distance = (opened[index] - opened[anchor]).Length
            assert abs(before_distance - after_distance) < 1e-6
            assert (opened[index] - initial_centers[index]).Length > 1.0
    for before_center, closed_center in zip(initial_centers, opening_centers[0]):
        assert (before_center - closed_center).Length < 1e-6

    wall_position_before = App.Vector(wall.Placement.Base)
    door_position_before = App.Vector(door.Placement.Base)
    move_vector = App.Vector(350.0, -125.0, 40.0)
    wall.Placement.Base = wall.Placement.Base + move_vector
    wall_position_after = App.Vector(wall.Placement.Base)
    door_position_after = App.Vector(door.Placement.Base)
    assert (wall_position_after - wall_position_before - move_vector).Length < 1e-6
    assert (door_position_after - door_position_before - move_vector).Length < 1e-6
    doc.recompute()

    second, second_profile = create_double_door_bim(
        doc,
        placement=App.Placement(
            App.Vector(4500.0, 0.0, 0.0), App.Rotation(App.Vector(0, 0, 1), 90.0)
        ),
        target_container=group,
        opening=25,
        label="Puerta doble BIM libre",
    )
    doc.recompute()
    assert list(second.Hosts) == []
    assert second.FA_HostWallName == ""
    assert not bool(second.MoveWithHost)
    assert second.Material is door.Material
    assert second_profile.Owner is second
    assert abs(second.Placement.Base.x - 4500.0) < 1e-6
    assert len(second.Shape.Solids) == 13

    output_dir = os.path.join(MACROS_ROOT, ".codex_tmp")
    os.makedirs(output_dir, exist_ok=True)
    output = os.path.join(output_dir, "FacilArquitectura_DoubleDoorBIM.FCStd")
    doc.recompute()
    object_count = len(doc.Objects)
    hosted_name = door.Name
    doc.saveAs(output)
    App.closeDocument(doc.Name)

    reopened = App.openDocument(output)
    reopened.recompute()
    reopened.recompute()
    assert len(reopened.Objects) == object_count
    reopened_hosted = reopened.getObject(hosted_name)
    assert reopened_hosted is not None
    assert reopened_hosted.IfcType == "Door"
    assert len(reopened_hosted.Shape.Solids) == 13
    assert len(reopened_hosted.Hosts) == 1
    assert reopened_hosted.FA_HostWallName == reopened_hosted.Hosts[0].Name
    assert bool(reopened_hosted.MoveWithHost)
    assert reopened_hosted.FA_CutStatus == "new_bim_cut"
    for material in reopened_hosted.Material.Materials:
        assert "Transparency" in material.Material

    reopened_wall = reopened_hosted.Hosts[0]
    reopened_profile = reopened_hosted.Profile
    restored_volume = float(reopened_wall.Shape.Volume)
    reopened_hosted.Hosts = []
    reopened.removeObject(reopened_hosted.Name)
    reopened.removeObject(reopened_profile.Name)
    reopened_wall.touch()
    reopened.recompute()
    assert float(reopened_wall.Shape.Volume) > restored_volume + 1.0
    result = {
        "cut_volume_mm3": round(cut_volume, 3),
        "cut_status": cut_result["cut_status"],
        "door_followed_wall_mm": [move_vector.x, move_vector.y, move_vector.z],
        "doors": 2,
        "host_delete_restored_wall": True,
        "hosted_wall_cut": True,
        "preexisting_opening_supported": True,
        "material_transparency": [0, 0, 70],
        "objects": object_count,
        "opening_values_checked": [0, 25, 50, 100, 0],
        "output": output,
        "persistence": "ok",
        "solids_per_door": 13,
    }
    App.closeDocument(reopened.Name)
    print("FA_DOUBLE_DOOR_BIM_SMOKE_OK " + json.dumps(result, sort_keys=True))


def _solid_centers(door):
    return [App.Vector(solid.CenterOfMass) for solid in door.Shape.Solids]


if __name__ == "__main__":
    main()
