# Approved A1 evidence - public extract

`acceptance.json` retains all 44 stage records and final pass flags from the real FreeCAD 1.1.3 GUI regression of 2026-09-08. It also records the pre-fix failure, environment, source hash, private-report hash and test limitations. Model paths, internal names outside the probe, full inventories and console are retained privately in DEV. No test model is distributed.

The three images show the same view before Delete, after Delete (empty) and after Undo (symbol restored). They contain only the generic symbol and view background.

Reusable test helpers: ../../freecad_a1_runtime_audit.py and ../../freecad_a1_runtime_regression.py. The latter requires FreeCAD 1.1.3 GUI and an explicitly provided reference source plus a fresh temporary output directory; it copies and hashes the source before any destructive operation. Read the helper before use. Nothing here auto-opens a production file.

Diagnostic exceptions from the original run are disclosed in acceptance.json. Touched state alone is not classified as data corruption; Invalid/Error and inconsistent relationships are failures. Quaternion evidence confirmed rotations 0,25,40,65,90,115 degrees in both Owner and PLAN. No broader UI gesture, startup-before-initialization, or NativeIFC claim is implied.
