# Reusable X3D export pipeline

## Purpose

Keep fixes discovered in real projects inside GameEngineExportWB as reusable
behavior. Project names, labels and output files are validation examples, not
runtime dependencies.

## Default scene selection

The Workbench applies these rules to an empty export list and uses the same
policy to complete a saved explicit list with hidden 3D objects:

1. Include visible objects with solid, face, mesh or point geometry supported
   by the X3D exporter.
2. Include hidden objects with a positive-volume solid or a real mesh when
   `include_hidden_3d_objects` is enabled. This includes ceilings, columns,
   furniture, equipment and `App::Link` instances.
3. Exclude linked library masters to avoid exporting the master and every
   instance at the same time.
4. Exclude sketches, drafting objects, wire-only shapes, helper objects and
   hidden linked instances that contain only faces or other 2D geometry.
5. Honor optional `GameExportInclude` and `GameExportExclude` boolean
   properties. Exclusion has priority.
6. Exclude content stored in library, master, internal, reference, prototype or
   catalog groups. This prevents hidden source geometry from being exported
   beside its placed instances.

The option is stored in `ParamGet` as `include_hidden_3d_objects` and in the
document sidecar:

```json
{
  "scene_selection": {
    "automatic_3d_scene": true,
    "include_hidden_3d_objects": true
  }
}
```

The legacy `include_hidden_3d_links` setting is read as a fallback. Existing
explicit entries remain unchanged; completion only appends valid hidden 3D
objects that are not already selected.

When `automatic_3d_scene` is enabled, the reusable selection is authoritative
and a stale explicit list is kept only for the panel UI. Disable the option to
export the explicit list. This avoids exporting old library masters and 2D
symbols saved by earlier Workbench versions.

## Runtime reload

Opening the export panel reloads the light, scene, persistence and panel modules
in dependency order. The console records the version and source path of every
module. This prevents a new panel from calling old core code kept in the
FreeCAD Python process.

The toolbar also includes `Reload Workbench`. It replaces the registered
command handlers and reloads the export runtime without restarting FreeCAD.
Use it once after updating a session that still has the older panel command
registered. Later panel openings reload the core automatically.

## Architectural complete profile

The Lighting tab provides a reusable profile that enables automatic complete
scene selection, hidden 3D objects, global light, automatic 3D luminaires and
the `Soft` material profile. It disables legacy manual PointLight selection and
PointLight shadows to avoid duplicates and shader resource overflow. Interior
PointLight attenuation is `1 0.30 0.06` with ambient intensity `0.02`.
Configured CGE luminaires are normalized to a 4.0 m export radius. The global
light uses ambient intensity `0.12` and the warm architectural color. These
overrides are applied only to the X3D payload and do not modify the FCStd.

## Visibility isolation

FreeCAD GUI export can omit an explicitly supplied object when the object or a
parent group is hidden. The exporter therefore:

1. Takes a visibility snapshot for every object in the involved documents.
2. Exposes selected objects and their complete parent chain.
3. Runs the normal FreeCAD X3D exporter.
4. Restores the snapshot in repeated passes, including exception paths.
5. Never saves the FreeCAD document as part of this operation.

## Luminaire classification

Automatic light generation requires an `App::Link` whose linked master has a
positive-volume 3D solid. This rejects embedded symbols, wires and planar
annotations.

Luminaire meaning can come from:

- Common luminaire names in English or Spanish.
- `GameExportRole`, `IfcType`, `PredefinedType`, `ObjectType`, `Category`,
  `Role`, `EquipmentType` or `DeviceType`.
- `IsGameExportLuminaire`, `IsLuminaire` or `IsLightFixture` boolean metadata.
- Explicit GameEngineLight properties configured by the light tool.

## Diagnostics

Console messages use `[GAMEEXPORT]` and report selected objects, skipped 2D
helpers, hidden objects, linked masters, hidden 3D links and explicit
overrides. The `.gee.debug.json` snapshot records the selected objects and
generated light entries for each export.

## Validation baseline

Unit tests cover:

- Hidden 3D objects and links with generic names.
- Internal library masters and artificial-thickness 2D helpers.
- Completing a saved explicit list with hidden 3D objects.
- Effective visibility through hidden parent groups.
- Disabling hidden object inclusion.
- Explicit include and exclude overrides.
- Complete visibility restoration after an export exception.
- Luminaire detection through semantic IFC metadata.
- Solid-only light origins when a master also contains a 2D symbol.
