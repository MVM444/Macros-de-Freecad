# Facil Arquitectura - RELEASE manifest

Version objetivo: `0.14.11`  
Build DEV preparada: `2026.09.02.8`  
FreeCAD minimo para la primera publicacion: `1.1.3`

## Principio

El repositorio RELEASE debe contener un Addon autosuficiente. El usuario no debe instalar por separado `CRBIMCore`. Durante desarrollo, la fuente autoritativa de ese componente permanece en `Macros-de-Freecad/CRBIMCore`; el subarbol `FacilArquitecturaWB/_bundled/CRBIMCore` es un espejo generado de distribucion y no se edita manualmente.

## Incluir en RELEASE

- `Init.py`, `InitGui.py`, `__init__.py`, `package.xml`, `README.md`.
- `LICENSE-Code`, `LICENSE-Assets`, `THIRD_PARTY_NOTICES.md`.
- `commands/`, `core/`, `ui/`, `resources/`, `translations/`, `modules/` y `docs/` cuando sean necesarios en runtime/documentacion publica.
- `i18n.py` y `usage_log.py` si siguen siendo utilizados por la build publicada.
- `_bundled/CRBIMCore/` con exclusivamente el runtime necesario y sus iconos. Debe coincidir con `python tools/sync_bundled_crbimcore.py --check`.
- `FA JSON`: `commands/cmd_json_inspector.py`, `core/json_command_core.py`, `core/json_snapshot_core.py`, `resources/icons/json_inspector.svg`.
- Demo, Ayuda, flujo DWG/DXF, paredes, puertas, ventanas, Recintos/Espacios, techo y cielorraso que formen parte de la interfaz publicada.

## No incluir en RELEASE

- `Respaldos_*`, `archive/`, `.codex_tmp/`, `__pycache__/`, `logs/` y archivos `*.log`.
- `TAREA_ACTUAL.md`, tareas anteriores, prompts Codex, resultados internos, pendientes y auditorias de desarrollo que no sean documentacion publica.
- modelos de prueba, datos institucionales, rutas locales, credenciales o archivos personales.
- el arbol neutral externo `Macros-de-Freecad/CRBIMCore` como dependencia separada.

## Tests

Las pruebas deben ejecutarse antes del staging. La carpeta `tests/` puede mantenerse en GitHub si se decide que aporta valor a revision/CI, pero no debe ser necesaria para ejecutar el Workbench. `test_json_command_core.py`, `test_json_snapshot_core.py` y el contrato de bundle forman parte obligatoria de la validacion.
