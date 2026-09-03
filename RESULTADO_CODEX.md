# RESULTADO CODEX

## CRBIMCore / Barra comun Espacios y Recintos v0.1 - 2026-09-02

Estado: **COMPLETADA Y VERIFICADA MEDIANTE MCP EN FREECAD 1.1.3**.

Se implementaron los comandos comunes `CRBIM_SelectRoom`, `CRBIM_RoomInfo`,
`CRBIM_NameRoom` y `CRBIM_RoomGuide` con arquitectura
nucleo JSON-compatible -> adaptador FreeCAD -> wrappers GUI pequenos. Facil
Arquitectura y ElectricCR registran los mismos command IDs, sin copiar la
implementacion y sin depender uno del otro.

La prueba real confirmo `Arch_Space` como command ID nativo; `BIM_Space` no
existe en esta instalacion. Space conserva prioridad sobre Area legacy,
`AMBIGUOUS` y `NOT_FOUND` no se resuelven silenciosamente, Info es read-only y
Nombrar cambia solo `Label`, admite nombres repetidos y conserva identidad,
geometria, Base, Placement, metadatos y jerarquia.

Resultados: 20/20 pruebas puras, smoke comun, RoomResolver, sincronizacion de
Spaces FA, macro poligonal, wrappers reales, seleccion por punto, Undo/Redo,
guardado/reapertura y registro idempotente aprobados. Las barras se verificaron
visualmente en ambos Workbenches. `PoligonosRecintosDesdeArchWalls.FCMacro`
permanece sin cambios de algoritmo y visible en ElectricCR como **Recintos desde
muros BIM**.

No se modificaron FCStd originales, no se inicio v0.2 y no se hizo commit/push.

---

## ElectricCR / RoomResolver fase 2A - 2026-09-01

Estado: **COMPLETADA / VERIFICADA MCP en FreeCAD 1.1.3**.

Se integro RoomResolver en el calculo de iluminacion sin migrar luminarias,
tomacorrientes ni apagadores. Space-only, Area-only, prioridad Space,
AMBIGUOUS, NOT_FOUND, doble recalculo y reapertura aprobaron. `DatosRecintos`
conserva 12 columnas y los Spaces permanecen read-only.

Contrato del arbol: `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md`. Resultado
completo: `ElectricCR/RESULTADO_CODEX.md`. La fase de objeto electromecanico y
reconstruccion idempotente queda pendiente y no debe iniciarse automaticamente.

---

Ultima tarea: `FA Cambiar tipo de puerta`.

Estado: PROGRAMADO / COMPILADO / PROBADO / VERIFICADO_MCP / VERIFICADO_VISUAL.  
Version/build FacilArquitecturaWB: `0.13.1` / `2026.08.13.2`.  
FreeCAD real: `1.1.3`.

Correccion 2026-08-13: el boton `Aplicar` del dialogo ahora conecta su clic
directamente con la aceptacion. El rol Qt `ApplyRole` no emitia `accepted` y
por eso el dialogo no hacia nada. La prueba GUI del clic y la prueba integral BIM
volvieron a aprobar en FreeCAD real.

Se agrego `FA_ChangeDoorType` a `FA Aberturas BIM`. La herramienta cambia una o
varias puertas existentes entre los presets nativos instalados (`Simple door` y
`Glass door`) conservando la identidad, dimensiones, Placement, host, corte,
contenedor y trazabilidad. Una regeneracion desde Sketch respeta el override por
indice. Ventanas, Opening Elements y puertas dobles incompatibles se rechazan sin
daño.

Pruebas principales:

- 148/148 pruebas Python y `compileall` aprobados;
- lote de tres puertas con dimensiones variadas;
- cambios repetidos en ambos sentidos;
- corte real y persistencia FCStd;
- regresiones de aberturas y puerta doble;
- comando/barra y geometria verificados por MCP en FreeCAD 1.1.3;
- captura isometrica de `Glass door` alojada verificada visualmente;
- documento del usuario no guardado ni modificado.

El informe autocontenido, archivos, evidencia y procedimiento exacto se encuentra
en `FacilArquitecturaWB/RESULTADO_CODEX.md`.

Git: rama `agent/respaldo-electriccr-2026-08-10`, commit base `707a0fc`, cambios
sin commit; no se hizo commit ni push.
