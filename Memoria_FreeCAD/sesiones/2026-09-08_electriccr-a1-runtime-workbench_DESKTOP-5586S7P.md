# ElectricCR A1: runtime entre Workbenches

Fecha: 2026-09-08 17:49 -0600, America/Costa_Rica. Host DESKTOP-5586S7P. FreeCAD 1.1.3 revision 20260725.

Resultado: **A1 = APROBADO PARA CONTINUAR**, inicializando ElectricCR una vez en la sesion. Referencia completa: [RESULTADO_CODEX.md](../../ElectricCR/RESULTADO_CODEX.md) y [evidencia](../../ElectricCR/tests/evidence/2026-09-08_a1_workbench_runtime/README.md).

La causa actual era Deactivated -> plan_selection.uninstall(). Lifecycle y live sync seguian activos. Fuera de ElectricCR, seleccionar PLAN y Std_Delete en Part dejaba Owner sin PLAN (10/9); Undo restauraba. No confundir con los siete PLAN huerfanos antiguos con Owner=None, ni inferir binding persistido corrupto.

Correccion minima: instalar seleccion tambien en Initialize, conservar los tres servicios entre Workbenches, reutilizar singleton al install y corregir normalizador a ElectricCR.ui. Uninstall explicito solo para mantenimiento/recarga. No ghostTracker ni feedback persistente; una unica seleccion logica Owner. Sin cambios a lifecycle, fabrica, contrato A1 o Host/Space/puerta.

Original actual de Upala, bajo usuario marco, 1363006 bytes y hash F5E1A372D162F02E5D91CD874F47A13B412380972F0604E27D9D77D71E87077F, quedo intacto. Copia temporal auditada 10/10; un dispositivo nuevo 11/11; secuencia completa BIM/Draft/Part con movimiento/giro, seleccion, Delete/Undo/Redo y save/reopen vuelve a 10/10. Cero fallos Placement, Access violation, huerfanos o duplicados observados. Clic real PLAN en Part selecciono Owner; capturas Delete/Undo sin residuos.

Leccion del auditor: lecturas/evalExpression nativas pueden marcar dependencias Link Touched, aun sin asignaciones; recompute las limpia. No comparar State/status transitorios como datos persistentes. Se comprobo por separado igualdad de todos los valores serializados de los Owners, incluidas relaciones y Placement. El reporte preserva errores del instrumento de prueba corregidos.

Limites: runtime despues de inicializar ElectricCR; no se probo arranque directo en BIM sin esa inicializacion. Guards preexistentes hasPendingTransaction()/isPerformingTransaction() no corresponden a API 1.1.3 (HasPendingTransaction/Transacting); no atribuir proteccion a esos guards ni ampliarlos sin regresion concreta. La auditoria reconoce Owners por contrato A1; no reconstruye identidades perdidas antes del inventario.

Sin commit/push, sin afirmar sincronizacion Drive. Otros pendientes excluidos permanecen separados. Archivos especializados/evidencia se mantienen en subdirectorios; no modelos ni herramientas en raiz Macros.
