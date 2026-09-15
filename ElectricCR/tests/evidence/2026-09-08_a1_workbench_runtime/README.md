# Evidencia A1: cambios de Workbench

Cierre: 2026-09-08 17:49 -0600, America/Costa_Rica. **A1 = APROBADO PARA CONTINUAR** dentro del alcance probado: inicializar ElectricCR una vez en la sesion y continuar en ElectricCR, BIM, Draft o Part.

FreeCAD 1.1.3 real, revision 20260725, commit 145529fe741292ff0b3977a01195bf0247425794. Regresion final: 2026-09-08T17:36:24.420274-06:00 a 2026-09-08T17:44:52.151735-06:00. Proceso GUI nuevo despues del reinicio; los cambios de produccion se cargaron normalmente.

Fuente original: `C:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Sucursales\Upala\1416 Levantamiento 250424 Compu D.FCStd`. Tamano 1363006 bytes; SHA256 `F5E1A372D162F02E5D91CD874F47A13B412380972F0604E27D9D77D71E87077F`. Original sin cambios. Copia destructiva: `C:\Users\marco\AppData\Local\Temp\ecr_a1_acceptance_20260908_5_mtcyyd\A1_workbench_regression.FCStd`. La copia y sus FCBak permanecen en TEMP; no se incorporan modelos al repositorio.

## Archivos verificables

- `baseline_selection.json`: antes del cambio, el redirector desaparece en BIM/Draft/Part; lifecycle y live sync permanecen.
- `baseline_delete_plan.json`: seleccionar PLAN y ejecutar Std_Delete en Part deja 10 Owners / 9 PLAN, con Owner sin PLAN; Undo recupero la pareja. No se demostro PLAN huerfano por este mecanismo.
- `changes.patch`: delta exacto de esta tarea contra los tres archivos al iniciar el diagnostico, separado del trabajo previo sin commit.
- `fixed_selection.json`: prueba posterior al cambio sobre un Owner existente en los cuatro Workbenches.
- `results.json`: 44 registros, incluidos intentos finales del auditor, todos sin inconsistencias A1; `passed=true`, fuente y datos de Owners conservados.
- JSON por etapa: inventario completo, expresiones, Placement real/evaluado, enlaces, grupos, propiedades y estados nativos.
- `owner_serialization_comparison.json`: todos los valores y definiciones de propiedades de los 10 Owners coinciden con Document.xml original; diferencias solo en atributos nativos `status`. Incluye Host, Space, puerta, identidad, master y Placement.
- `audit_native_touched.json`: recalculo -> auditoria -> recalculo; el auditor puede activar marcadores Touched durante lecturas/evaluacion nativa. No son Invalid/Error ni cambios de valores.
- `part_plan_before_delete.png`, `part_plan_after_delete.png`, `part_plan_after_undo.png`: misma vista, simbolo presente -> vista vacia -> simbolo restaurado. Clic de raton real sobre Edge13 del PLAN en Part/Solo2D selecciono solo Owner.
- `console.txt`: consola capturada sin ocultar errores de diagnostico. Cero errores de binding Placement o Access violation. Contiene una consulta visual CenterOfMass no disponible en Part.Compound, dos aserciones demasiado estrictas de State/status y una ruta incorrecta del modulo de prueba; fueron errores del instrumento, corregidos y explicados en results.json.

## Secuencia y limites

Se creo exactamente un dispositivo nuevo con la fabrica A1 y adaptador semantico vigentes, en una transaccion. Inventario inicial/final: 10/10; con sonda: 11/11. No se sincronizaron ni repararon objetos despues de Undo/Redo para esconder fallos.

En BIM: seleccion PLAN -> Owner, Draft.move/rotate, guardar, Std_Delete, Undo, Redo, Undo, nuevo movimiento (RedoCount=0), guardar/cerrar/reabrir. En Draft: seleccion, mover/girar, Delete, Undo, Redo, Undo, guardar/cerrar/reabrir. En Part: seleccion, mover/girar, Solo2D/Solo3D/Ambos, clic real en PLAN, Delete, Undo, Redo, Undo, guardar/cerrar/reabrir, seleccionar, mover/girar y repetir Delete/Undo/Redo; guardar/cerrar/reabrir sin la sonda, auditoria final y cierre.

Giro efectivo comprobado tambien en los quaternion JSON: 0 -> 25 -> 40 -> 65 -> 90 -> 115 grados en Owner y PLAN. Movimiento/giro usan las API nativas Draft sobre la seleccion GUI real; no se afirma haber arrastrado el manipulador Transform con el raton. El seguimiento se lee antes del recompute global. La seleccion de PLAN se prueba con Gui.Selection en los cuatro Workbenches y ademas con raton real en Part. Mismo singleton tras cambios de WB, reapertura y dos instalaciones repetidas de cada servicio. Activar de nuevo un documento bajo Part vuelve a poner ShowInTree=False.

El auditor identifica Owners por contrato A1 y detecta enlaces rotos/candidatos PLAN. No puede clasificar como A1 un dispositivo que ya hubiera perdido simultaneamente contrato y PLAN antes del inventario inicial. La invariancia del inventario y la comparacion de valores serializados cubren los Owners actuales de esta copia.

No se valido arrancar directamente en BIM sin inicializar ElectricCR en esa sesion, ni las herramientas deliberadamente excluidas. Los guards preexistentes que invocan hasPendingTransaction()/isPerformingTransaction() no prueban proteccion de replay en 1.1.3: esa version expone HasPendingTransaction/Transacting. No se modificaron esos guards; la secuencia real documentada paso.

## Reutilizacion

En la consola Python de FreeCAD 1.1.3, inicializar ElectricCR normalmente e importar `tests/freecad_a1_runtime_regression.py` mediante importlib.util.spec_from_file_location. Construir `RuntimeRegression(source, work_dir)` con una carpeta TEMP nueva y llamar `create()`. Los metodos `switch_select`, `move`, `delete`, `undo_delete`, `redo_delete`, `save_reopen` y `finish` permiten repetir la secuencia anterior observando cada fase. `finish` requiere que la sonda ya este eliminada y que se haya reabierto la copia. Nunca pasar un documento original como destino; el constructor copia la fuente, verifica hash y rechaza un destino existente. El auditor `freecad_a1_runtime_audit.py` puede reutilizarse sin escribir archivos ni asignar propiedades.
