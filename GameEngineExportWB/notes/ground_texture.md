# Ground Texture

The **Texturas / Textures** tab can apply an image texture to an existing exported ground object without changing the FreeCAD `.FCStd` document.

## Workflow

1. Select the ground object in FreeCAD.
2. Press **Tomar seleccion / Use selection**.
3. Enable **Aplicar textura al objeto suelo / Apply texture to ground object**.
4. Choose a texture image.
5. Set repeat values for S/T.
6. Export X3D.

## Export behavior

- The texture file is copied to `<BaseName>_assets/textures/`.
- The X3D `Appearance` for the selected exported object receives an `ImageTexture`.
- The same `Appearance` receives a `TextureTransform` using Repeat S/T as scale.
- The material is set to white diffuse color so the texture color is visible.
- When planar UV is enabled, the exporter adds normalized `TextureCoordinate` to each `IndexedFaceSet` shape using the exported object's X/Y coordinates.
- Paths are written relative to the X3D file.

## Sidecar

The document sidecar stores:

```json
{
  "ground_texture": {
    "enabled": true,
    "object_name": "Ground",
    "texture_path": "C:/path/to/grass.png",
    "repeat_s": 20.0,
    "repeat_t": 20.0,
    "generate_planar_uv": true
  }
}
```

## Notes

Planar UV uses X/Y because FreeCAD geometry is exported before the global FreeCAD Z-up to X3D Y-up transform is applied. This maps the typical FreeCAD ground plane to Castle's ground plane after the exporter transform.
