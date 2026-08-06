# Puriscal complete X3D export

Date: 2026-07-30

## Objective

Use `Puriscal Depurado` as a real Workbench export and fix luminaire origins when a master contains both a 3D body and a 2D symbol.

## Root cause

The affected luminaire master has a complete Shape bounding box from Z 0 to Z 2740 mm. Its positive-volume solid exists only from Z 2640 to Z 2740 mm. The Z 0 limit belongs to 2D edges embedded in the compound.

The previous light origin used the complete Shape bounding box, so a downward light could be placed at the 2D symbol. The new calculation joins only positive-volume `Shape.Solids` bounding boxes. Draft symbols, wires and planar helpers cannot define the light origin.

## Workbench behavior

- The Lighting tab includes `Auto-detect 3D luminaires`.
- Only luminaire `App::Link` instances with a real solid are detected.
- Existing `CGE_Light*` configuration remains authoritative.
- Automatic lights are not duplicated for configured CGE masters.
- Grid, line and ring patterns share the total intensity between generated points.
- An empty export list selects the complete reusable 3D scene.
- A saved explicit list is completed with valid hidden 3D geometry when the
  persistent option is enabled.
- Linked masters, sketches, `Part2DObject`, wire-only objects and `HVAC_2D` helpers are excluded.
- Hidden selected devices and parent groups are exposed only while the GUI exporter runs.
- A complete document visibility snapshot is restored after export, including exception paths.
- Web preview enables its camera headlight only for X3D scenes without light nodes.

## Puriscal validation

The active FreeCAD document contained 1700 objects. The final automatic scene
selected 412 3D objects, including:

- 91 outlet links.
- 19 sensor objects.
- 6 HVAC 3D links.
- 0 HVAC 2D objects.
- 61 luminaire instances.
- 18 ceiling objects.
- 1 column structure object.
- Hidden doors, windows and equipment required to complete the building.
- 0 internal library or linked master objects.

Lighting output:

- 49 automatic single-point luminaires at Z 2620 mm.
- 12 configured panel luminaires with 4 points each at Z 2970 mm.
- 97 PointLight nodes total.
- Configured panel intensity 1.0 is divided into 4 points of 0.25.
- Automatic single lights use intensity 0.55 and radius 6 m.
- Point lights do not request shadows.
- One global DirectionalLight requests shadows.
- Material profile is `Soft`.

The first visibility-respecting export contained only 126 Shape nodes because
all 61 luminaires, 91 outlets and 6 HVAC links were hidden in FreeCAD. The first
device-complete export produced 834 Shape nodes. The final building-complete
export temporarily exposed 407 hidden 3D objects and produced 1236 Shape nodes,
1235 Material nodes, 595 Transform nodes, 97 PointLight nodes, one
DirectionalLight, one Viewpoint, one NavigationInfo and one skybox Background.
The 48 configured panel points use intensity 0.25 and radius 4 m. The 49
automatic luminaire points use intensity 0.55 and radius 6 m. All point lights
use ambient intensity 0.02 and attenuation `1 0.30 0.06`.

The real restoration check found zero visibility differences after leaving the
export context. The final X3D size is 111989372 bytes and the generated HTML is
112161557 bytes. The preview keeps `headlight=false` because the scene already
contains 98 light nodes. It contains no `file://` or Windows absolute asset URL.

The source FCStd SHA-256 was identical before and after export:

`001a19c616ad47b1cb38d0df8e941d747d3c63f6c74cbeb8c8a523859863af62`

Generated files:

- `Puriscal_Depurado_GameEngineExport/Puriscal_Depurado.x3d`
- `Puriscal_Depurado_GameEngineExport/index.html`
- `Puriscal_Depurado_GameEngineExport/Puriscal_Depurado.gee.debug.json`
- `Puriscal_Depurado_GameEngineExport/Puriscal_Depurado_assets/skies/`
