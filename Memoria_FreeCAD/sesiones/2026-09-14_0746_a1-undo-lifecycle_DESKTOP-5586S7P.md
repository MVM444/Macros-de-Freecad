# ElectricCR A1 Undo / PLAN Lifecycle

2026-09-14 07:46 -06:00, DESKTOP-5586S7P, FreeCAD 1.1.3 revision 20260725. Estado: probado en GUI real, verificado MCP y visualmente, sin publicacion.

Reproducidos dos Access violation al deshacer creacion Demo. Causa: nombres C++ inexistentes en Python (`isPerformingTransaction()` / `hasPendingTransaction()`), cuyas excepciones se silenciaban. Lifecycle encolaba y eliminaba PLAN dentro del replay: 14 entradas en dos Undo. Atributos Python correctos: Transacting y HasPendingTransaction. Tras la correccion, cero encolados/flush durante replay.

Corregidos solo plan_lifecycle.py y plan_live_sync.py. Lifecycle reutiliza ademas slotBeforeRecomputeDocument para vaciar la cola antes del recompute de Std_Delete; esperar hasta cierre producia un error Placement transitorio, detectado y rechazado en prueba intermedia. Sin cambios de A1, seleccion, fabrica, Demo, registry o masters.

Regresion final: 19 etapas PASS, 2 Spaces/5 walls/7 Owners/7 PLAN; movimiento transaccional y Undo/Redo, Delete/Undo/Redo, rollback antes/despues del flush, Undo/Redo completo, persistencia y movimiento en BIM/Draft/Part. Smoke original y Undo/Redo sin instrumentacion tambien pasan. Cero documentos abiertos al terminar. Cero Access violation/Placement/unknown opcode en consola final; dos avisos nativos hasher mismatch conservados como limite no bloqueante observado.

Placement escrito sin transaccion no agrega Undo; con openTransaction si. No existe registro suficiente para atribuir el gesto historico de Marco a un comando Draft concreto.

Regla reusable: comprobar nombres y tipos de la API Python nativa; no trasladar nombres C++ suponiendo que existen. Revisar consola despues de retornar al event loop: FreeCAD puede devolver sin excepcion Python y registrar un Access violation diferido.

[Evidencia completa](../../ElectricCR/tests/evidence/2026-09-14_a1_undo_lifecycle/README.md). Actualizados resultado, estado y tarea; no Git, IFC ni modelos productivos. Correccion detenida para revision/aceptacion, sin commit/push ni HISTORIAL_CAMBIOS.
