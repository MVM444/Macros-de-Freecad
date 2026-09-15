# A1 / PLAN Lifecycle - Undo Demo - 2026-09-14

**CORRECCION PROBADA EN FREECAD 1.1.3. Regresion final PASS, sin Access violation.**

Equipo DESKTOP-5586S7P, PID 41788. FreeCAD 1.1.3 revision 20260725 / 145529fe741292ff0b3977a01195bf0247425794. Diagnostico y pruebas 07:32-07:46, America/Costa_Rica. Solo documentos temporales nuevos. Ningun modelo de produccion abierto. Sin operaciones Git, IFC, registry, recursos maestros ni otras herramientas.

## Estado real preservado

Se releyeron AGENTS y tarea vigente y se inspeccionaron lifecycle, live sync, seleccion, fabrica, Demo y auditor/smoke. Se aplicaron las skills de arquitectura y memoria ya leidas. La instruccion del 14/9 reactiva explicitamente Undo A1 y deja Recuperar Tasks fuera del alcance.

[baseline.json](baseline.json) y `before/` preservan bytes, fechas y hashes previos. Lifecycle, live sync, seleccion, InitGui y adaptador Demo coincidian con los hashes registrados el 12/9. No se atribuye origen a los archivos sin comparador historico ni se declara limpio el repositorio: Git no fue consultado. Metadata ya utiliza App::FeaturePython y se dejo intacta; tambien se conserva la prueba parcial de arquitectura preexistente.

## Causa demostrada

Las guardas llamaban `doc.isPerformingTransaction()` y `doc.hasPendingTransaction()`. Esos nombres C++ NO existen en el Document Python de esta instalacion. Cada intento generaba AttributeError, absorbido por `except Exception: pass` o por el valor falso de respaldo. La API Python real expone los booleanos `doc.Transacting` y `doc.HasPendingTransaction`; [native_python_api.json](native_python_api.json) registra tipos y errores reales.

Al deshacer la creacion, FreeCAD entra en replay (`Transacting=True`). Lifecycle recibia slotDeletedObject para Owner, ignoraba de hecho el estado nativo, encolaba su PLAN y, al interpretar erradamente que no habia transaccion, lo eliminaba sincronicamente desde ese callback. La traza muestra _queue -> _flush_document -> borrado PLAN dentro del replay. Esa intervencion concurrente con la gestion nativa de la transaccion reprodujo Access violation en dos Undo completos (uno doc.undo y otro Std_Undo).

Consola previa, 07:36:37 y 07:37:49:

```text
<Exception> Access violation
<App> Transactions.cpp(203): Exception on undo 'ElectricCR: crear demo A1':Access violation
```

La llamada devolvio y el documento llego a cero objetos. NO se considero PASS: las excepciones nativas aparecieron en Report View despues de devolver el callback. Esto demuestra que ni una auditoria posterior ni el retorno Python bastan para aprobar Undo.

En las dos reproducciones previas se registraron 14 entradas de encolado y 14 flush dentro de replay. En la regresion corregida: **cero encolados y cero flush dentro de replay**. Live sync tenia la misma consulta inexistente y recibia cambios de Placement durante Undo/Redo; se corrigio tambien su guarda. No se atribuye un crash independiente a live sync ni a seleccion sin evidencia; seleccion y fabrica quedaron intactas.

## Timing y correccion minima

| Operacion | Transacting | HasPendingTransaction | Actuacion |
|---|---:|---:|---|
| Escritura dentro de transaccion de movimiento | false | true | Sincronizacion normal permitida. |
| Borrado normal de Owner | false | true | Encolar PLAN; evitar borrado reentrante. |
| Recompute nativo de Std_Delete | false | true | Vaciar cola antes de evaluar expresiones. |
| Undo/Redo de objetos | true | true observado en replay | No encolar, eliminar ni recomputar PLAN desde observers. |
| Callback de abort/rollback | true | false observado | Descartar cola, dejando restauracion a FreeCAD. |
| Fuera de transaccion | false | false | Conservar ruta de limpieza inmediata existente. |

Primer intento: corregir solo los nombres de API elimino Access violation, pero expuso un error Placement durante Delete. Al reconocer la transaccion, PLAN quedaba en cola mientras Std_Delete recomputaba con Owner ya eliminado; slotBeforeCloseTransaction llegaba despues. Esa prueba se marco FAIL y se conserva en `intermediate_*`.

Se verifico el callback nativo slotBeforeRecomputeDocument: llega antes del error, con la transaccion abierta y la cola pendiente. La correccion final agrega ese callback y reutiliza _flush_document, con su guarda Transacting. No introduce timers, nuevos estados de replay, cambios de expresiones ni redisenos.

Archivos funcionales modificados:

- `electriccr/features/plan_lifecycle.py` v0.1.2: atributos Python correctos y vaciado de la cola existente antes del recompute.
- `electriccr/features/plan_live_sync.py` v0.4.2: lectura correcta de Transacting para no recomputar durante replay.

[changes.diff](changes.diff) muestra el cambio completo de archivos existentes, generado contra los bytes preservados sin usar Git. [summary.json](summary.json) verifica que seleccion, fabrica, Demo, auditor, smoke original e InitGui no cambiaron. Nuevas pruebas focales: `tests/freecad_a1_transaction_probe.py` y `tests/freecad_a1_lifecycle_regression.py`.

Precedentes nativos consultados: [DocumentPyImp.cpp del commit ejecutado](https://github.com/FreeCAD/FreeCAD/blob/145529fe741292ff0b3977a01195bf0247425794/src/App/DocumentPyImp.cpp) expone HasPendingTransaction; [DocumentObserverPython.cpp](https://github.com/FreeCAD/FreeCAD/blob/145529fe741292ff0b3977a01195bf0247425794/src/App/DocumentObserverPython.cpp) ofrece slotBeforeRecomputeDocument; [referencia C++ de Document](https://freecad.github.io/SourceDoc/d8/d3e/classApp_1_1Document.html) define replay/rollback. Decision: REUTILIZAR estado/callback nativo; ADAPTAR el observer existente. No crear un administrador de transacciones paralelo. AGENTS conserva el objetivo historico 1.1.1; prevalece 1.1.3 solicitado, sin modificar AGENTS.

## Movimiento sin entrada Undo

Se reprodujo la diferencia en el mismo Owner: asignar Placement sin openTransaction cambia X de 900 a 925, pero UndoNames sigue conteniendo solo `ElectricCR: crear demo A1`. Con openTransaction, el movimiento agrega una entrada independiente y HasPendingTransaction pasa a true; Undo/Redo revierte/restaura ese movimiento. Ver fases `move_without_transaction` y `move_with_transaction` de before_trace.jsonl.

El smoke original ya abria una transaccion explicita y paso sin cambios. El registro historico no conserva el comando exacto con que Marco movio el dispositivo: no permite atribuir su ausencia de Undo a Draft Move o al redirector. Se confirma el mecanismo de escritura sin transaccion y la solucion verificable para la regresion, sin inventar esa atribucion historica.

## Regresion real final

| Prueba | Resultado |
|---|---|
| Crear Demo | PASS: 2 Spaces, 5 walls, 7 Owners, 7 PLAN. |
| Movimiento y giro de un Owner | PASS: transaccion propia en UndoNames; Placement/PLAN siguen, UID/master/Space/Host se conservan. |
| Undo/Redo de movimiento | PASS; auditoria canonica tras Undo e integridad con coordenadas intencionales tras mover/Redo. |
| Std_Delete / Undo / Redo | PASS: exactamente dos objetos menos; una sola entrada Delete; restaura par coherente. |
| Rollback de borrado pendiente | PASS: Owner vuelve, cola descartada, PLAN enlazado. |
| Rollback despues de recompute/flush | PASS: restaura el par aunque ambos ya se habian eliminado dentro de la transaccion. |
| Undo completo de creacion | PASS: cero objetos y vista vacia; consola sin Access violation. |
| Redo completo de creacion | PASS: auditoria 2/5/7/7. |
| Guardar/cerrar/reabrir | PASS: 2/5/7/7, enlaces y Placement validos. |
| Movimiento + Undo/Redo con BIM, Draft, Part | PASS despues de reabrir; PLAN selecciona solo Owner en los tres. |
| Delete/Undo/Redo con Part tras reabrir | PASS: par eliminado/restaurado, sin huerfanos. |
| Smoke original sin instrumentacion | PASS; archivo original intacto. |
| Undo/Redo completo sin instrumentacion | PASS adicional; captura vacia sin graficos residuales. |
| Consola comprobada en llamada posterior | Cero Access violation, unknown opcode, errores Placement o traceback en ejecucion final. |

19 etapas registradas PASS, incluyendo controles de consola; ver [regression.json](regression.json). Compilacion de los cuatro archivos nuevos/modificados: PASS. Se retiraron los wrappers de diagnostico y el observer temporal. FreeCAD permanece abierto con ElectricCR, cero documentos de prueba abiertos. El FCStd desechable conservado para reproducibilidad esta bajo TEMP; su ruta exacta consta en summary.json.

La consola final contiene dos mensajes nativos `TopoShapeExpansion.cpp(983): hasher mismatch` durante Redo de creacion. No causaron excepcion, objeto Invalid ni fallo de auditoria/persistencia; se registran como limite, sin ampliar la investigacion. No se afirma que toda la consola carezca de avisos.

## Evidencia y reproduccion

- `before_trace.jsonl` / `before_console.txt`: reproduccion original, flags y cola.
- `intermediate_trace.jsonl`, `intermediate_console.txt`, `intermediate_regression.json`: intento incompleto rechazado por error Placement.
- `after_trace.jsonl` / `after_console.txt`: prueba final y consola conservada.
- `demo_after_reopen.png`: demo reabierta reconocible; `empty_after_creation_undo.png`: vista vacia sin dispositivos residuales.
- `baseline.json`, `before/`, `changes.diff`, `native_python_api.json`, `summary.json`: estado previo, cambio y verificacion final.

La prueba es por etapas, desde una sesion vacia FreeCAD 1.1.3 con ElectricCR DEV cargado. Importar `freecad_a1_lifecycle_regression.py` sin ejecutar automaticamente nada; llamar `stage('create', setup, carpeta_evidencia)`, luego move, delete_pair, rollback, replay_creation, save_reopen, move con BIMWorkbench/DraftWorkbench/PartWorkbench. Llamar console_check en una invocacion posterior para recibir mensajes nativos diferidos. Cerrar solamente el documento creado por la prueba. `freecad_a1_transaction_probe.py` es instrumentacion optativa; install/uninstall conservan las decisiones del observer y deben usarse solo en documentos desechables.

Estado: NUCLEO / CANDIDATA / COMPROBADA-PARCIAL (correccion tecnicamente verificada; pendiente revision/aceptacion del proyecto, no RELEASE automatica). A1 mantiene Owner App::Link, identidad unica y Placement autoritativo, fisico 3D y PLAN documental. No cambiar MAPA_WORKBENCH ni REVISION_MACROS: no se modifica arquitectura ni catalogo de herramientas. HISTORIAL_CAMBIOS queda intacto hasta aceptacion. Tarea detenida tras pruebas/documentacion; sin commit/push.
