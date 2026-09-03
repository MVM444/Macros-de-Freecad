# Sesion FreeCAD - ElementDataCore y Tabla de ventanas

Fecha: 2026-08-28 America/Costa_Rica
Equipo: DESKTOP-5586S7P
Proyecto: Macros-de-Freecad / FacilArquitecturaWB
FreeCAD: 1.1.3 revision 20260725
Version FA: 0.14.6 / build 2026.08.28.1
Estado: IMPLEMENTADO / PROBADO_MCP / PENDIENTE UPALA REAL

## Patron reutilizable

Para transferir datos de elementos BIM entre documentos no se deben copiar
referencias internas ni crear un tipo paralelo. El patron validado separa:

- nucleo puro JSON-compatible para registros, validacion y matching;
- adaptador FreeCAD para objetos nativos y Spreadsheet;
- geometria autoritativa del documento destino;
- propiedades descriptivas autoritativas de la tabla;
- relaciones BIM resueltas nuevamente en el destino.

El nucleo usa `dry_run=True` por defecto y estados `MATCH`, `CAMBIO`,
`NO_MATCH`, `AMBIGUO`. Nunca aplica una coincidencia ambigua. Primero intenta la
identidad estructural y despues una firma geometrica tolerante.

## Hallazgos FreeCAD 1.1.3

- `ArchWindow._Window` no conserva una propiedad nativa persistente
  `SillHeight`; el antepecho es la Z del Sketch `Base`.
- `Preset` usa un entero interno indexado desde uno. Para intercambio debe
  guardarse el nombre estable del preset.
- Manage Doors and Windows y ArchSchedule son utiles para edicion/reporte, pero
  no sustituyen una tabla bidireccional por instancia.
- `Spreadsheet::Sheet.exportFile/importFile` conserva UTF-8, pero el archivo
  producido es tabulado aunque tenga extension `.csv`.
- `Document.copyObject(sheet, True)` es una alternativa valida entre documentos.

## Regla de actualizacion segura

Si una ventana FA no cambia, conservarla. Si debe reconstruirse, crear primero
la nueva ventana nativa, comprobar `Base`, `Hosts` y corte del muro y eliminar
la anterior solo despues, dentro de una transaccion. Una ventana manual en
conflicto se marca ambigua y nunca se elimina.

## Prueba

Dos ventanas nativas se extrajeron y transfirieron a un documento con Sketch
reordenado y anchos distintos. Los anchos finales 1100/1300 mm provinieron del
Sketch; alturas 1250/1500 mm y antepechos 800/850 mm provinieron de la tabla.
Se aprobaron dry-run, host nuevo, reejecucion sin duplicados, reemplazo seguro,
Undo/Redo y guardar/cerrar/reabrir.
Una ventana manual con `ElementID` coincidente produjo `SKIP=1` y conservo su
identidad, confirmando la barrera contra reemplazos de objetos ajenos.

Pendiente: validacion final con archivos reales de Upala.

Git: rama `agent/respaldo-electriccr-2026-08-10`, commit base `707a0fc`; sin
commit ni push, con cambios previos ajenos en el worktree.
