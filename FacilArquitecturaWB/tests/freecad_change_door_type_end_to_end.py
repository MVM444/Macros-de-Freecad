"""FreeCAD 1.1.3 end-to-end validation for FA_ChangeDoorType."""

from __future__ import annotations

import os
import sys

import Arch
import ArchWindowPresets
import FreeCAD
import Part


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(PACKAGE_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from FacilArquitecturaWB.core.bim_structure_utils import add_to_level, ensure_bim_structure  # noqa: E402
from FacilArquitecturaWB.core.door_type_utils import (  # noqa: E402
    change_door_types,
    door_compatibility,
    door_preset_name,
    native_door_presets,
)
from FacilArquitecturaWB.core.opening_utils import (  # noqa: E402
    GENERATED_BY_DOORS,
    create_openings_from_centerlines,
)


def add_line(sketch, x1, x2):
    return sketch.addGeometry(
        Part.LineSegment(FreeCAD.Vector(x1, 0, 0), FreeCAD.Vector(x2, 0, 0)),
        False,
    )


def generated_doors(doc):
    return [
        obj
        for obj in doc.Objects
        if str(getattr(obj, "FA_GeneratedBy", "") or "") == GENERATED_BY_DOORS
        and str(getattr(obj, "FA_Role", "") or "") == "door"
    ]


def placement_values(obj):
    return tuple(round(float(value), 8) for value in obj.Placement.Matrix.A)


def assert_host_cut(door):
    for host in list(door.Hosts):
        subvolume = door.Proxy.getSubVolume(door, host=host)
        assert subvolume.Volume > 1.0
        assert host.Shape.common(subvolume).Volume <= max(1.0, subvolume.Volume * 1e-7)


def main():
    presets = native_door_presets()
    assert presets == ["Simple door", "Glass door"], presets
    assert "Sliding door" not in presets
    output = os.path.join(REPO_DIR, ".codex_tmp", "fa_change_door_type.FCStd")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    doc = FreeCAD.newDocument("FAChangeDoorType")
    structure = ensure_bim_structure(doc, "Edificio prueba", "Nivel 00", 0.0)
    level = structure["level"]

    wall_axis = doc.addObject("Sketcher::SketchObject", "WallAxis")
    add_line(wall_axis, 0.0, 9000.0)
    wall = Arch.makeWall(wall_axis, width=200.0, height=3000.0, name="Wall")
    add_to_level(level, wall, source_sketch=wall_axis)

    source_a = doc.addObject("Sketcher::SketchObject", "Sketch_Centros_Puertas_A")
    source_a.addProperty("App::PropertyString", "FA_CenterlineKind", "FacilArquitectura")
    source_a.FA_CenterlineKind = "doors"
    add_line(source_a, 500.0, 1300.0)
    add_line(source_a, 2200.0, 3200.0)
    source_b = doc.addObject("Sketcher::SketchObject", "Sketch_Centros_Puertas_B")
    source_b.addProperty("App::PropertyString", "FA_CenterlineKind", "FacilArquitectura")
    source_b.FA_CenterlineKind = "doors"
    add_line(source_b, 4300.0, 5500.0)
    doc.recompute()

    first_two, _ = create_openings_from_centerlines(
        doc, level, [source_a], [wall], "door", 2100.0, host_tolerance_mm=100.0
    )
    last_one, _ = create_openings_from_centerlines(
        doc, level, [source_b], [wall], "door", 2300.0, host_tolerance_mm=100.0
    )
    original = first_two + last_one
    assert [round(door.Width.Value, 3) for door in original] == [800.0, 1000.0, 1200.0]
    assert [round(door.Height.Value, 3) for door in original] == [2100.0, 2100.0, 2300.0]
    original[0].Opening = 65
    original[0].addProperty("App::PropertyString", "FA_CustomPreserved", "FacilArquitectura")
    original[0].FA_CustomPreserved = "trace-ok"
    snapshots = {
        door.Name: {
            "identity": door,
            "label": door.Label,
            "placement": placement_values(door),
            "width": door.Width.Value,
            "height": door.Height.Value,
            "hosts": list(door.Hosts),
            "normal": (door.Normal.x, door.Normal.y, door.Normal.z),
            "opening": int(door.Opening),
            "source": door.FA_SourceSketch,
            "index": int(door.FA_SourceGeometryIndex),
        }
        for door in original
    }
    cut_volume_before = wall.Shape.Volume

    changed, summary = change_door_types(doc, original, "Glass door")
    assert summary["identity_preserved"] is True
    assert summary["changed_count"] == 3
    assert summary["validated_host_count"] == 3
    assert all(door_preset_name(door, presets) == "Glass door" for door in changed)
    assert all(len(door.Shape.Solids) == 3 for door in changed)
    assert len(generated_doors(doc)) == 3
    assert abs(wall.Shape.Volume - cut_volume_before) < 1.0
    for door in changed:
        snap = snapshots[door.Name]
        assert door is snap["identity"]
        assert door.Label == snap["label"]
        assert placement_values(door) == snap["placement"]
        assert door.Width.Value == snap["width"]
        assert door.Height.Value == snap["height"]
        assert list(door.Hosts) == snap["hosts"]
        assert (door.Normal.x, door.Normal.y, door.Normal.z) == snap["normal"]
        assert int(door.Opening) == snap["opening"]
        assert door.IfcType == "Door"
        assert door not in level.Group and door.Base not in level.Group
        assert door.FA_TargetLevel == level.Name
        assert door.Base.FA_TargetLevel == level.Name
        assert door.FA_SourceSketch is snap["source"]
        assert int(door.FA_SourceGeometryIndex) == snap["index"]
        assert bool(door.FA_TypeOverride)
        assert_host_cut(door)
    assert changed[0].FA_CustomPreserved == "trace-ok"
    assert not [
        obj for obj in doc.Objects
        if getattr(obj, "IfcType", "") == "Door" and obj not in changed
    ]

    # Repeat both directions on the same identities.
    change_door_types(doc, changed, "Simple door")
    assert all(door_preset_name(door, presets) == "Simple door" for door in changed)
    assert all(len(door.Shape.Solids) == 2 for door in changed)
    change_door_types(doc, [changed[0]], "Glass door", preserve_opening=False)
    assert door_preset_name(changed[0], presets) == "Glass door"
    assert door_preset_name(changed[1], presets) == "Simple door"
    assert int(changed[0].Opening) == 0

    # Regeneration must honor the per-index override stored on the source Sketch.
    regenerated_a, regen_summary = create_openings_from_centerlines(
        doc,
        level,
        [source_a],
        [wall],
        "door",
        2100.0,
        host_tolerance_mm=100.0,
        replace_existing=True,
    )
    assert regen_summary["removed_count"] == 2
    regenerated_a.sort(key=lambda obj: int(obj.FA_SourceGeometryIndex))
    assert [door_preset_name(obj, presets) for obj in regenerated_a] == [
        "Glass door",
        "Simple door",
    ]
    assert all(bool(obj.FA_TypeOverride) for obj in regenerated_a)
    assert all(obj.Hosts == [wall] for obj in regenerated_a)
    assert all(obj not in level.Group and obj.Base not in level.Group for obj in regenerated_a)
    assert all(
        obj.FA_TargetLevel == level.Name and obj.Base.FA_TargetLevel == level.Name
        for obj in regenerated_a
    )
    assert all(
        obj.Base.ViewObject is None or not obj.Base.ViewObject.Visibility
        for obj in regenerated_a
    )
    assert all(not obj.Shape.isNull() for obj in regenerated_a)
    assert all(assert_host_cut(obj) is None for obj in regenerated_a)
    assert len(generated_doors(doc)) == 3

    # Rejection coverage: native Window, Opening Element and special FA double door.
    window = ArchWindowPresets.makeWindowPreset(
        "Fixed", 900, 1200, 50, 50, 50, 100, 40, 0, 30
    )
    opening = ArchWindowPresets.makeWindowPreset(
        "Opening only", 900, 2100, 50, 50, 50, 100, 40, 0, 30
    )
    special = doc.addObject("Part::FeaturePython", "SpecialDoubleDoor")
    special.addProperty("App::PropertyString", "IfcType")
    special.IfcType = "Door"
    special.addProperty("App::PropertyString", "FA_GeneratedBy")
    special.FA_GeneratedBy = "FA_InsertDoubleDoorBIM"
    assert not door_compatibility(window)[0]
    assert not door_compatibility(opening)[0]
    accepted, reason = door_compatibility(special)
    assert not accepted and "puerta doble" in reason
    window_name, window_base_name = window.Name, window.Base.Name
    opening_name, opening_base_name = opening.Name, opening.Base.Name
    doc.removeObject(window_name)
    doc.removeObject(window_base_name)
    doc.removeObject(opening_name)
    doc.removeObject(opening_base_name)
    doc.removeObject(special.Name)
    doc.recompute()

    doc.saveAs(output)
    doc_name = doc.Name
    FreeCAD.closeDocument(doc_name)
    reopened = FreeCAD.openDocument(output)
    reopened.recompute()
    saved = generated_doors(reopened)
    assert len(saved) == 3
    assert sorted(door_preset_name(obj, presets) for obj in saved) == [
        "Glass door",
        "Simple door",
        "Simple door",
    ]
    assert all(obj.IfcType == "Door" and obj.Hosts for obj in saved)
    assert all(not obj.Shape.isNull() for obj in saved)
    reopened_level = next(
        obj for obj in reopened.Objects
        if getattr(obj, "IfcType", "") == "Building Storey"
    )
    assert all(
        obj not in reopened_level.Group and obj.Base not in reopened_level.Group
        for obj in saved
    )
    assert all(
        obj.FA_TargetLevel == reopened_level.Name
        and obj.Base.FA_TargetLevel == reopened_level.Name
        for obj in saved
    )
    for obj in saved:
        assert_host_cut(obj)
    FreeCAD.closeDocument(reopened.Name)
    print(
        "FA_CHANGE_DOOR_TYPE_OK",
        output,
        "presets=%s identity=ok multiple=3 dimensions=varied host-cut=ok "
        "repeat=ok regeneration=ok rejection=ok persistence=ok"
        % ",".join(presets),
    )


if __name__ == "__main__":
    main()
