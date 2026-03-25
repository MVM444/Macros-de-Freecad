# Recurrent Issues - ElectricCR

## Macro icons not showing in toolbar

Root cause:
- ElectricCR registers macros through `ElectricCR/commands/macros.py`.
- Toolbar icons are resolved by `icon_for_macro()`, not only by `# Icon:` in the macro header.

Stable resolution policy:
1. Keep a valid `# Icon: <name>.svg` header in the macro.
2. Ensure `<name>.svg` exists next to the macro file.
3. Prefer also placing the same icon under:
   - `ElectricCR/icons/<Group>/<name>.svg`
4. If icon resolution changes, update `icon_for_macro()` first, not each macro manually.

Verification checklist:
- Reload ElectricCR workbench.
- Confirm command `Pixmap` resolves to an existing file path.
- If command id is versioned by icon mtime, ensure icon timestamp is updated.

## Transform tool disabled on device links (context menu)

Recurrent symptom:
- Right click > `Transform` appears disabled on `App::Link` devices
  (reported for switches, may affect any device link).

Current technical context (as of 2026-03-23):
1. `crear_toma_link()` was updated to force:
   - `LinkTransform = True`
   - editable `Placement` and `LinkPlacement`
   - `ViewObject.Selectable = True`
2. Legacy links can keep old locked states, so a repair macro was added:
   - `Objetos/Habilitar_Transform_en_Links_Dispositivos.FCMacro`

Status:
- Partially mitigated (new links should be transformable).
- Still marked recurrent until validated in right-click context menu on real files.

Do not forget next validation:
1. Reload ElectricCR.
2. Run `Habilitar_Transform_en_Links_Dispositivos`.
3. Verify right-click `Transform` is enabled on a selected device link.

## UI canon for ElectricCR macros

Canonical rule for this project:
1. Prefer FreeCAD `Task Panel` forms (`Gui.Control.showDialog(panel)`) over modal `QDialog.exec_()`.
2. Keep forms non-blocking for 3D interaction, especially when the workflow requires picking points or geometry.
3. For point-capture workflows, allow the user to:
   - keep panel open,
   - select in 3D view,
   - press capture button (`origen`/`destino`),
   - apply global transform/translation.
4. If Task Panel is unavailable, use classic dialog only as fallback.

Reason:
- Modal dialogs block reliable selection and cause recurrent user friction in geometry-alignment workflows.

## CSV assistants: type mapping canon

Canonical rule for two-step CSV workflows:
1. In conversion step, expose per-sketch mapping for:
   - source sketch/type -> target object (base)
   - source sketch/type -> functional kind (`techo`, `apagador`, `toma`, `sensor`, etc.)
2. Keep defaults in `Auto`, but let user override each type explicitly before inserting.
3. Use functional kind to drive insertion engine:
   - wall devices (`apagador`, `toma`, `sensor`, etc.) via device factory
   - ceiling/general items (`techo`, `otro`) via `App::Link` to selected base
4. Persist this behavior as UI expectation for future import/export tools.
5. Persist assistant settings per document (scale, filters, object/type mapping), not only per macro session.
6. Support staged conversion:
   - convert one type at a time
   - mark type as pending (do not insert yet)
7. Do not hardcode CSV sample paths in production macros; default CSV path must be resolved from current project folder and persisted per document.
8. If per-sketch mapping UI grows, provide a floating mapping window to keep the main Task Panel compact.
9. For conversion workflows, split UI into:
   - basic conversion tab (safe defaults)
   - optional/advanced tab (alignment, overrides, mapping)

## Link selection blocked in 3D view (tree selection only)

Recurrent symptom:
- `App::Link` luminarias can be selected from Model tree, but not by clicking in 3D view.

Root cause pattern:
1. `ViewObject.Selectable` and/or `ViewObject.Pickable` were disabled on links.
2. In some files, parent/child container chain also had pick flags disabled, blocking 3D picking.
3. Legacy runs could leave old blocked states in existing links.

Stable resolution policy:
1. For link insertion macros, always force on links:
   - `Selectable = True`
   - `Pickable = True` (when property exists)
2. Keep master prototypes non-selectable, but do not propagate that state to runtime link instances.
3. Add post-run recovery that unlocks pick flags for all links in document and related chain.
4. Keep a manual recovery path in assistant tools ("Desproteger" action) for legacy files.

Verification checklist:
1. Insert at least one link instance.
2. Click instance in 3D view (not only in tree).
3. Confirm selected object `TypeId == App::Link`.
4. Confirm transform/move tools operate on the selected link.

## Luminarias placement canon (no clones)

Canonical rule:
1. Do not use `Draft.clone` for luminarias placement workflows.
2. Keep only two active placement variants:
   - `ColocarLuminarias_Objeto`: one object per cell.
   - `ColocarLuminarias_Link`: same grid flow, but using `App::Link`.
3. Archive deprecated placement macros in `Respaldos/...` so they are not auto-registered in toolbar.
4. Keep explicit headers in active macros:
   - `# MenuText: ...`
   - `# ToolTip: ...`
   - `# Icon: ColocarLuminarias.svg`

## Ctrl+Z in legacy macros (transaction ownership)

Recurrent symptom:
- `Ctrl+Z` does not revert macro insertion (reported in `ColocarLuminarias_Link`).

Root cause pattern:
1. ElectricCR launcher (`ElectricCR/commands/macros.py`) wrapped every macro in a transaction.
2. Some legacy macros already open/commit/abort their own transaction.
3. Double transaction ownership can make undo behavior unreliable in some flows.

Stable resolution policy:
1. Launcher must skip wrapper transaction when macro self-manages transaction.
2. Detection rules:
   - explicit header: `# Transaction: self`
   - or macro source contains `openTransaction(` and `commitTransaction(`/`abortTransaction(`.
3. For old macros under review, always verify:
   - exactly one transaction owner path (launcher or macro, not both)
   - `Ctrl+Z` reverts full insertion batch in one step.

Verification checklist:
1. Run macro from ElectricCR toolbar.
2. Insert test batch (at least 3 elements).
3. Press `Ctrl+Z` once and confirm batch rollback.
4. Press `Ctrl+Y` once and confirm redo works.

## Organizar luminarias por Areas: evitar auto-indexado recursivo

Recurrent symptom:
- Running organizer multiple times over selected area groups keeps renaming buckets (`Apoyo001`, `Apoyo005`, etc.).

Root cause pattern:
1. Selection may contain previously generated index links (`ORG_LUM_IDX`).
2. Macro treated those links as source luminarias and re-indexed them again.

Stable resolution policy:
1. Never use generated index links as direct source luminarias.
2. If selected object is generated index link, resolve to its linked source object first.
3. Deduplicate source objects by `Name` before organizing.

Current UI canon for this macro:
1. Use Task Panel form with explicit selectors:
   - source luminarias: selection/document/group
   - areas group: auto/group
2. Keep two operation modes:
   - reacomodar objetos
   - indice con links
3. Keep optional renaming by area/apagador from the same form.
