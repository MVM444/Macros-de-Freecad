# Web Preview

The export panel includes **Vista previa Web / Web preview** in the Output group.

## Behavior

1. Reuses the normal X3D export flow.
2. Generates `index.html` next to the exported X3D.
3. Embeds the exported X3D `Scene` inside the HTML page.
4. Starts a background HTTP server bound to `127.0.0.1`.
5. Opens `http://127.0.0.1:<port>/index.html` in a new browser tab.

The preview never opens a `file://` URL.

## Local HTTP server

The server uses only Python standard-library modules: `http.server`,
`socketserver`, `threading`, and related URL helpers.

- It scans ports 8000 through 9000 and skips ports that cannot be bound.
- It serves only the directory that contains the generated `index.html`.
- It runs in daemon threads so it does not block or keep FreeCAD alive.
- It is reused when the next preview uses the same output directory.
- It stops when another preview directory replaces it.
- It stops after 15 minutes without HTTP requests.
- It stops during Workbench hot restart and normal Python/FreeCAD shutdown.
- It verifies one HTTP response before the browser is opened.

## X3DOM

The generated page links the stable X3DOM release:

- `https://www.x3dom.org/release/x3dom.js`
- `https://www.x3dom.org/release/x3dom.css`

The scene is embedded instead of loaded through an `Inline` node. `Viewpoint`
and `NavigationInfo` remain in their original order and are not changed by the
preview generator.

The HTML copy sets `NavigationInfo headlight="true"` only when the scene does
not contain `DirectionalLight`, `PointLight`, or `SpotLight` nodes. This gives
legacy unlit scenes a camera fill light without overexposing configured scenes.
All other navigation attributes and the initial `Viewpoint` remain unchanged.
The source X3D file is never rewritten by this Web-only compatibility adjustment.

XML-style self-closing X3D tags are expanded before embedding. This matters because the HTML parser does not treat custom X3D tags as XML void elements, so markup like `<Material ... />` can break the DOM tree when pasted directly into HTML.

## Files

The generated `index.html` is written in the same output folder as the X3D file. Relative asset paths such as `<BaseName>_assets/textures/...` and `<BaseName>_assets/skies/...` remain valid.

Local absolute paths and `file://` asset references are rewritten as relative
HTTP paths. An asset outside the served directory is copied to
`.gee_web_assets/` first. Remote `http://`, `https://`, `data:`, and `blob:`
references are preserved.

## Notes

The generated page includes a small status indicator. It reports whether X3DOM failed to load, whether the `Scene` node is missing, or whether no `Shape` nodes were detected.

This preview is intended as a quick browser check. Castle Game Engine remains the target runtime for final validation.
