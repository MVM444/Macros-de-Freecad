# Cierre formal A1 v1 - 2026-09-14

**A1 / Objeto electromecanico comun v1 = ACEPTADO** por Marco.

La prueba de cierre es la [regresion real FreeCAD 1.1.3 del 14/9](../2026-09-14_a1_undo_lifecycle/README.md), con 19 etapas finales PASS. `closure_verification.json` confirma los ocho SHA-256 actuales contra summary.json y registra SHA-256 del README aprobado. No se ha modificado codigo funcional durante el cierre.

Antes de la interrupcion se ejecuto una comprobacion parcial independiente (regression.json: creacion, movimiento, Delete/Undo/Redo, rollback y replay completo). No constituye una nueva regresion completa: no incluye control diferido de consola ni persistencia. Se conserva por trazabilidad, sin usarla para sustituir o elevar la evidencia aprobada. Al retomar a las 12:44 se respetó la instruccion de no repetir pruebas. La sesion FreeCAD no contenia documentos abiertos. La primera consulta auxiliar de limpieza uso un alias Python no definido y dio NameError; la consulta siguiente importo FreeCAD y confirmo sesion vacia. No fue una prueba de A1 ni una regresion del producto.

Git fsck completo --no-reflogs --no-dangling devolvio 0. La inconsistencia historica bad tree object HEAD no se reproduce; no se reparo Git. DEV permanece en agent/respaldo-electriccr-2026-08-10 con cambios ajenos preservados. El staging preexistente y limpio de codex/cierre-a1-20260909 aisla el cierre sobre su ultimo commit 285d5a7.

`publication_manifest.json` relaciona archivos de A1/Demo y pruebas copiados byte por byte desde DEV. Incluye la Demo ya existente porque la prueba de lifecycle depende de ella y aun no estaba en esa rama. InitGui solo difiere por su registro Demo; fabrica, seleccion y adaptador semantico ya coinciden con esa rama. No se copian cambios de otras herramientas ni catalogos. Se exporta evidencia original de antes, intento intermedio FAIL y final PASS con rutas locales anonimizadas en staging; los originales DEV permanecen intactos. No se publica el inventario privado de cambios locales ni el diagnostico general de equipo. Los dos avisos hasher mismatch son no bloqueantes aceptados.

## Default

A1 no queda como default global. Evidencia de codigo: objeto_toma_uno.py conserva separate_documentation=False; InstalarTomacorrientesEnParedesBIM y ColocarApagadoresEnPuertas ofrecen use_a1=False. ColocarLuminarias_Link usa crear_toma_uno para maestro y doc.addObject('App::Link') para ocurrencias; ColocarDetectores_NFPA usa crear_toma_uno directo. Cambiar solo el opt-in de la fabrica no convierte esas rutas ni demuestra compatibilidad. La Demo pide A1 explicitamente. Adoptarlo globalmente requiere trabajo funcional posterior y pruebas de cuatro familias; no se ejecuta en este cierre.

Documentos actualizados: RESULTADO_CODEX, ESTADO_PROYECTO, TAREA_ACTUAL, HISTORIAL_CAMBIOS, DECISIONES_TECNICAS y Memoria_FreeCAD. Estado aceptado del contrato: NUCLEO / ESTABLE / COMPROBADA. No release, main, integracion nueva ni siguiente fase. El recibo Git se registra al confirmar push.

Revision final de diff: solo A1, Demo y evidencia ya existentes en DEV, mas cierre documental. diff --check pasa excluyendo changes.diff: ese artefacto conserva espacios de contexto propios del formato unified diff, no errores nuevos de codigo. Compilacion y pruebas focales se acreditan con la evidencia PASS previa, sin reejecucion por instruccion de Marco.
