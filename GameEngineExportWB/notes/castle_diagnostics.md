# Castle Diagnostics

Date: 2026-08-15

## Architecture

- `core/castle_diagnostics.py` is the reusable read-only core.
- `commands/cmd_castle_diagnostics.py` adapts the active FreeCAD document, Qt UI and ParamGet preferences.
- `macros/DiagnosticoCastle.FCMacro` is a small command launcher.
- `run_diagnostic(...)` accepts explicit values and returns a versioned JSON-compatible dictionary.
- The core does not import FreeCAD, FreeCADGui or Qt.

## Source selection

The command reuses `commands/cmd_analyze_x3d.py` and `ui/output_defaults.py`.
A saved document only searches its own folder and normalized stem. An unsaved
document has no associated X3D and therefore opens the manual file selector.
Stored output settings from another document are not used as a silent fallback.

## Outputs

Every generated file is contained in `_castle_debug` beside the selected X3D:

- versioned diagnostic JSON;
- Markdown summary;
- X3D analyzer JSON and Markdown;
- optional `castle-model-converter --validate` output;
- Castle shader/debug log;
- optional screenshot requested from `GameStart`.

Castle Model Viewer 5.2.0 on Windows does not accept the standard CGE
`--log-file` option. The core therefore captures standard output when available
and mirrors Castle's native per-user log into `_castle_debug` after that viewer
process exits.

The source FCStd and X3D are not written or copied by the diagnostic core.

## MCP boundary

A future MCP adapter should validate paths and numeric limits, call
`run_diagnostic(...)` directly, and return its dictionary without opening Qt
dialogs. The adapter must not execute arbitrary macro names or Python code.
