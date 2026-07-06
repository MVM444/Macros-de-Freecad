# Add Light Properties Tool

## Purpose

The `GameEngineExport_AddLightProperties` command stores CGE light metadata on a luminaire master object. `App::Link` instances inherit those properties during X3D export while using their own placement.

## Stored Master Properties

Properties are stored on the master object under the `GameEngineLight` group with the `CGE_Light*` prefix. Links are not modified in this first version.

Main properties:

- `CGE_LightEnabled`
- `CGE_LightType`
- `CGE_LightPattern`
- `CGE_LightDirection`
- `CGE_LightOriginMode`
- `CGE_LightOffset`
- `CGE_LightIntensity`
- `CGE_LightRange`
- `CGE_LightRows`
- `CGE_LightCols`
- `CGE_LightCount`
- `CGE_LightColorR/G/B`
- `CGE_LightLocalX/Y/Z`
- `CGE_LightPreviewEnabled`

## Export Behavior

During export, `core/lights.py` resolves each selected object:

- If the object is an `App::Link`, it resolves `LinkedObject` as the master and uses the Link placement.
- If the object is a normal object, it uses the object as its own master and placement.
- If the object is inside an `App::Part`, `PartDesign::Body`, or another placement container, parent placements are accumulated before generating the X3D light position.
- PointLight positions are generated in FreeCAD world millimeters, then `core/exporter_x3d.py` applies the existing mm-to-m and -90 X conversion.
- A hidden master with Links is treated as a library object and does not generate its own light instance.

Temporary preview objects named `CGE_TempLightPreview*` and optional origin markers named `CGE_LightOrigin_*` are excluded from geometry export.

## Visibility Notes

Exported `PointLight` nodes use an attenuation profile to avoid constant light over the whole radius. `Interior` is the safe default for building scenes.

`shadows="true"` on many `PointLight` nodes can overload Castle Viewer shaders and produce purple geometry with warnings about `castle_projected_tex_coord_*`. For this reason, point-light shadows are experimental, disabled by default, and capped by the exporter.

The **Atenuacion / Falloff** selector controls the X3D `attenuation` attribute:

- `Interior`: `1 0.25 0.04`
- `Soft`: `1 0.08 0.01`
- `Constant`: `1 0 0`

The export panel logs prepared light counts with the `[GAMEEXPORT]` prefix:

- `manual`: objects marked with the legacy point-light flag.
- `cge`: lights generated from `CGE_Light*` master properties and `App::Link` instances.
- `total`: total `PointLight` nodes requested for X3D postprocessing.
- `shadows`: how many exported PointLight nodes request X3D shadows.
- `falloff`: attenuation profile written to X3D.

For interior scenes, enable **Materiales X3D / X3D Materials** and use **Architectural** or **Bright** if the geometry materials are still too dark. This modifies only the exported X3D file, not the FreeCAD `.FCStd` document.

Shadows depend on suitable geometry. Walls with thickness and closed faces block lights more reliably than single open surfaces.

## Debugging

The export panel writes a diagnostic snapshot next to the exported X3D:

`<OutputBase>.gee.debug.json`

The snapshot records:

- Workbench debug version.
- Export objects and their global base placement.
- Legacy manual point lights skipped because a CGE light exists on the same source/master.
- CGE source candidates, resolved masters, local points, placement bases, and final world positions in millimeters.
- PointLight entries sent to the X3D postprocessor.

The console also logs `[GAMEEXPORT] [DEBUG] X3D PointLight written` with the FreeCAD world millimeter position, converted X3D meter position, shadows flag and attenuation.

Legacy manual lights marked with `IsGameExportLight` are also included in the snapshot. When such a light has geometry, or is an `App::Link` to a master with geometry, its point is placed from the transformed local bounding box instead of raw `Placement.Base`. This prevents linked luminaires with `Placement.Base.z = 0` from exporting their light at floor/origin height.

## Emissive Luminaire Geometry

X3D `PointLight` nodes illuminate nearby geometry but do not make the luminaire mesh itself glow. This matters for panel undersides and tube-lamp interiors because face normals and back faces may not receive visible light.

During X3D postprocessing, objects that generated light entries are mapped back to their exported object group by export order. Their `Material` nodes are marked with `GameExport_Emitter_*` and receive an emissive warm-white material. This is X3D-only and does not change the FreeCAD `.FCStd` material.

## Current Limitations

- `ReferenceMarker` is prepared in the property model but disabled in the UI for this first version.
- App::Link scale is not explicitly handled; placement and rotation are used.
- Distribution is limited to 25 PointLights per luminaire instance.
