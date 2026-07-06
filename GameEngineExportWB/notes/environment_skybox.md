# Environment Skybox

The **Configuracion / Config** tab can add an X3D `Background` skybox during export postprocessing.

The sky folder is not hardcoded to a user path. The panel derives it from the configured Castle executable when possible:

```text
<CastleModelViewer>/castle-model-viewer.exe
<CastleModelViewer>/example_models/skies
```

The user can still override the folder manually with **Examinar / Browse**.

## Input folder

The selected folder must contain six image files whose names end with:

- `back`
- `bottom`
- `front`
- `left`
- `right`
- `top`

For example, Castle Model Viewer example skies use names like:

- `foggy_sky_back.png`
- `foggy_sky_bottom.png`
- `foggy_sky_front.png`
- `foggy_sky_left.png`
- `foggy_sky_right.png`
- `foggy_sky_top.png`

## Export behavior

- The FreeCAD `.FCStd` document is not modified.
- The X3D postprocessor copies the six images to `<BaseName>_assets/skies/`.
- The exported X3D receives a `Background` node with `backUrl`, `bottomUrl`, `frontUrl`, `leftUrl`, `rightUrl` and `topUrl`.
- URLs are written as relative paths so the X3D can be moved together with its assets folder.

## Persistence

The export panel stores environment settings in ParamGet:

- `env_use_skybox`
- `env_skybox_dir`

It also writes the document sidecar:

```json
{
  "environment": {
    "use_skybox": true,
    "skybox_source": "castle_executable",
    "skybox_dir": ""
  }
}
```

When the folder is selected manually, `skybox_source` becomes `manual` and `skybox_dir` stores the selected folder.

## Logs

Successful exports print:

```text
[GAMEEXPORT] Applied X3D skybox background from <folder>
```

If the folder does not contain all six faces:

```text
[GAMEEXPORT][WARN] Skybox enabled but no complete cubemap was found: <folder>
```
