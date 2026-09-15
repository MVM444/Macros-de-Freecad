## Estado actual - 2026-09-14 21:26 -0600 - ElectricCR / Alinear en planta v0.2 validada

**Marco confirma funcionamiento real en FreeCAD 1.1.3 con referencia por cara plana.**

`Objetos/Alinear_En_Planta.FCMacro` queda funcionalmente validada en el caso probado: seleccionar objeto + cara lateral plana permite corregir posicion X/Y y giro Z con el flujo simple previsto. Se mantiene la v0.2.0 y no se requieren cambios adicionales de codigo por esta prueba.

Estado de ciclo: IMPLEMENTADA / PROBADA EN CASO REAL / VALIDADA FUNCIONALMENTE EN EL CASO PROBADO. Clasificacion: OPERATIVA / CANDIDATA / COMPROBADA-PARCIAL. Undo/Redo, persistencia y matriz completa de referencias no se declaran comprobados porque no fueron mencionados en la validacion de Marco.

---

## Estado actual - 2026-09-14 21:26 -0600 - ElectricCR / Alinear en planta v0.2

**`Objetos/Alinear_En_Planta.FCMacro` actualizada en Google Drive con soporte de arista recta + cara plana; prueba real FreeCAD 1.1.3 pendiente.**

La herramienta mantiene el flujo de dos selecciones y un clic. Con una arista proyecta el punto de insercion a su recta XY; con una cara plana deriva la direccion en planta desde la normal del plano y proyecta X/Y al plano conservando exactamente `Placement.Base.z`. El giro sigue limitado a un delta alrededor de Z y escoge el eje local X/Y que necesita menor correccion.

La v0.2.0 rechaza caras curvas, caras horizontales sin direccion XY, aristas verticales en planta y selecciones ambiguas. Sintaxis y pruebas matematicas aisladas PASS. Archivo vigente re-leido desde Drive: 16.169 bytes, SHA-256 `41064649bdedc88e54d86c5ae3102727da1beae229b3c601ac6e9e3e1c439184`.

Estado de ciclo: IMPLEMENTADA / POR PROBAR TECNICAMENTE EN FREECAD REAL. Clasificacion provisional: OPERATIVA / CANDIDATA / POR VERIFICAR. Pendiente: validar tablero + arista y tablero + cara lateral de muro, Undo/Redo y guardado/reapertura. `Objetos/Alinear.FCMacro`, A1 e integracion de barra permanecen sin cambios.
---

## Recibo de cierre Git - 2026-09-14T12:50:03-06:00

**A1 / Objeto electromecanico comun v1 = ACEPTADO**. FreeCAD 1.1.3; regresion lifecycle/Undo del 2026-09-14: PASS.

Commit de cierre: `38d4d0d140a0ea67785b177964664221b4d4a5b6`. Rama: `codex/cierre-a1-20260909`. Push a origin: **SUCCESS**, verificado mediante referencia remota identica. Incluye 48 archivos de A1/Demo, pruebas, evidencia anonimizada y documentacion; ningun cambio funcional nuevo durante el cierre. Se usa el staging A1 existente para preservar el trabajo ajeno de DEV, cuya rama permanece `agent/respaldo-electriccr-2026-08-10`.

Cierre finalizado. A1 default global pendiente de trabajo funcional separado; no se implementa automaticamente. Sin merge a main, RELEASE ni siguiente fase. Este recibo documental registra el commit de cierre ya publicado.

---

## Cierre formal vigente - 2026-09-14T12:46:32-06:00

**A1 / Objeto electromecanico comun v1 = ACEPTADO**

Marco acepta formalmente el contrato y la regresion real FreeCAD 1.1.3 del 2026-09-14 como prueba de cierre. Las 19 etapas finales PASS documentadas en [la evidencia aprobada](tests/evidence/2026-09-14_a1_undo_lifecycle/README.md) cubren Demo 2 Spaces / 5 walls / 7 Owners / 7 PLAN, movimiento con transaccion propia y Undo/Redo, Delete/Undo/Redo Owner+PLAN, rollback, Undo/Redo de creacion completa, guardar/cerrar/reabrir, BIM/Draft/Part y seleccion PLAN -> Owner. Cero Access violation, PLAN huerfanos y errores Placement finales. Los dos avisos nativos `TopoShapeExpansion.cpp(983): hasher mismatch` se aceptan como observacion no bloqueante por no afectar integridad, persistencia ni comportamiento.

Verificacion documental del cierre: las ocho huellas SHA-256 de summary.json coinciden con los archivos actuales. No se modifica funcionalidad ni se repiten pruebas al retomar. La comprobacion parcial de cierre iniciada antes de la interrupcion queda conservada por separado; no sustituye la regresion completa aprobada. [Verificacion de huellas y alcance](tests/evidence/2026-09-14_a1_v1_closure/README.md).

Contrato estable: Device/Owner = App::Link, identidad electrica unica y Placement autoritativo; fisico 3D y PLAN documental Part::Feature reconstruible, schema 2, DocumentationOnly, Owner PropertyLinkHidden, Placement derivado, SnapPoints=[Vector(0,0,0)], fuera de grupos de usuario y oculto en el arbol. Runtime A1 permanece activo al cambiar de Workbench tras inicializar ElectricCR.

A1 sigue **opt-in**, salvo la Demo que lo solicita explicitamente. No se convierte en default en este cierre: la fabrica conserva separate_documentation=False; tomas y apagadores ofrecen use_a1=False; ColocarLuminarias_Link crea enlaces mediante una ruta propia y ColocarDetectores_NFPA usa crear_toma_uno (FeaturePython directo). No existe un unico interruptor cuya activacion cubra de forma segura las cuatro familias. Adaptar esas rutas y validar su creacion/edicion seria trabajo funcional adicional. Pendiente separado, no bloqueante para aceptar v1; legacy y documentos existentes se conservan.

Clasificacion del contrato A1: NUCLEO / ESTABLE / COMPROBADA, aceptada por Marco. No implica RELEASE ni migracion general. Se preservan los FAIL y las restricciones historicas como antecedentes; las frases antiguas 'pendiente aceptacion' o 'sin autorizacion Git' no describen el estado vigente. No iniciar otra fase.

Git: integridad comprobada (fsck completo, codigo 0). DEV contiene trabajo ajeno, preservado; cierre aislado sobre la rama A1 existente `codex/cierre-a1-20260909`, desde su staging limpio. Commit/push autorizados para este cierre; recibo definitivo confirmado al inicio de este documento. Sin merge a main ni release.

---

## Estado actual - 2026-09-14 07:46 -0600 - A1 Undo corregido y probado

**Regresion FreeCAD 1.1.3 PASS. Contrato A1 conservado. Pendiente revision/aceptacion; sin publicacion.**

Access violation de Undo Demo reproducido dos veces y corregido: lifecycle usaba nombres C++ inexistentes en Python, ignoraba el estado de replay y borraba PLAN durante Undo. Ahora lifecycle/live sync leen Transacting y HasPendingTransaction donde corresponde; lifecycle vacia su cola antes del recompute de Delete con el callback nativo existente. Sin cambios de seleccion, fabrica, Demo, registry ni masters.

19 etapas finales PASS: 2 Spaces/5 walls/7 Owners/7 PLAN; movimiento transaccional y Undo/Redo, Delete/Undo/Redo, rollback, Undo/Redo de toda la creacion, guardar/reabrir y movimientos con BIM/Draft/Part. Smoke original y prueba sin instrumentacion aprobados. Consola final sin Access violation/errores Placement/unknown opcode; dos avisos nativos hasher mismatch documentados, sin fallo de integridad observado. Documentos de prueba cerrados; observers normales instalados.

La escritura Placement sin transaccion no genera Undo propio; la prueba explicita si lo hace. No se infiere el comando historico de Marco. [Evidencia y limites](tests/evidence/2026-09-14_a1_undo_lifecycle/README.md). Codigo previo preservado y diff verificado sin Git. No IFC, Upala, otras herramientas, commit/push ni HISTORIAL_CAMBIOS. Tarea detenida tras documentar y probar la correccion; los bloques inferiores son historicos.

---

## Estado actual - 2026-09-13 16:49 -0600 - Recuperar Tasks

**Mecanismo probado en FreeCAD 1.1.3; panel negro no reproducido. Codigo funcional sin cambios.**

La tarea mas reciente de la conciliacion del 12/9 era validar Recuperar Tasks. Prueba real MCP/GUI en DESKTOP-5586S7P: dos documentos temporales, 28 ejecuciones aprobadas, Sketch nativo preservado, diez pulsaciones con cinco docks y 897 widgets constantes, seis cambios A/B, sin duplicados ni cambios de datos/camara/seleccion por el recuperador. Ambos documentos cerrados sin guardar. Auditorias y capturas del escritorio verificadas; visibilidad inicial de Tasks restaurada.

Una barra Programacion con nueve botones, Recuperar Tasks unico; macro v0.1.0 y toolbar v1.1.0 previas de GPT, hashes sin cambios. Metadata de Demo ya usa App::FeaturePython; no se rehizo la correccion historica. `tab=unknown` con docks separados es una limitacion del diagnostico, sin perdida de visibilidad demostrada. Cero errores del recuperador; un error previo de importacion al arrancar FacilArquitecturaWB queda registrado separadamente, fuera de alcance.

SOPORTE / CANDIDATA / COMPROBADA-PARCIAL. Pendiente: prueba durante el panel negro real y aceptacion funcional. Undo Demo A1 / PLAN Lifecycle sigue independiente y no se probó en esta ejecucion. No hay operaciones IFC, Upala o Git, ni nueva aprobacion A1/RELEASE. [Resultado y evidencia](tests/evidence/2026-09-13_tasks_recovery_gui/README.md). Memoria de equipo y sesion actualizadas. Las entradas inferiores se conservan como antecedentes.

---

## Conciliacion G/E - 2026-09-12 - estado de continuidad

Conciliacion documental autorizada por Marco: Google Drive es la fuente principal de desarrollo y OneDrive la copia de trabajo/sincronizacion. Esta entrada integra las contribuciones de ambas copias; no constituye validacion funcional de FreeCAD ni activa sincronizacion automatica.

Contexto vigente: el avance GPT mas reciente disponible corresponde a Programacion / Recuperar Tasks (2026-09-10 17:54), implementado y pendiente de prueba GUI real. El diagnostico/correccion de Undo Demo A1 / PLAN Lifecycle del 10/9 14:01 sigue siendo un pendiente independiente. No se ejecuta ninguna de esas tareas durante la conciliacion.

La inspeccion Codex del 12/9 que se conserva a continuacion fue escrita desde E, que no contenia el avance GPT de Recuperar Tasks. Su afirmacion sobre la tarea mas reciente debe leerse con esa limitacion de contexto; sus hallazgos de archivos, falta de skill y error Git son observaciones historicas de aquella inspeccion, no pruebas nuevas. Se mantienen las atribuciones GPT/Codex y las conclusiones tecnicas originales. No se duplico el historial comun.

Los siguientes bloques conservan primero la inspeccion Codex del 12/9, luego las aportaciones GPT del 10/9 y finalmente el historial compartido. El trabajo funcional posterior requiere una instruccion separada; esta fase se limita a conciliar y verificar archivos.

---

## Continuidad vigente - 2026-09-12 - inspeccion previa, desarrollo detenido

La tarea vigente es el diagnostico/correccion del Access violation en Undo de Demo A1 / PLAN Lifecycle, definida el 2026-09-10 14:01 al final de TAREA_ACTUAL.md. No esta resuelta.

Se encontro trabajo local anterior que los resumenes iniciales no reflejaban: metadata ya usa App::FeaturePython y existe Demo_ElectricCR_A1_Prueba_Arquitectura.FCMacro. Se preservo todo, sin atribuir autoria ni validacion nueva. Git status falla con `bad tree object HEAD`; el inventario parcial del indice no permite declarar el arbol limpio ni reconstruir todo el historial.

Bloqueo: falta la skill obligatoria freecad-cr-workbench-architecture y su contrato, exigidos por AGENTS.md padre. Se busco tambien fuera de la ruta indicada sin encontrarla. La skill de memoria si se localizo en .agents/skills/freecad-project-memory y se leyo. No se modifico codigo, ejecuto FreeCAD ni demostro la causa del fallo. Sin commit/push, reparacion Git, cambios de modelos ni actualizacion de HISTORIAL_CAMBIOS.

[Inspeccion, limites y hashes previos](tests/evidence/2026-09-12_continuity_inventory/README.md). Solo se anadio documentacion de continuidad y evidencia del inventario. Arreglo: SOPORTE / DESARROLLO / POR VERIFICAR. Siguiente paso: recuperar la skill de arquitectura y su contrato; completar contexto y reproducir el fallo en FreeCAD 1.1.3 antes de modificar lifecycle. AGENTS ElectricCR aun indica 1.1.1; prevalece 1.1.3 para esta tarea. Las entradas inferiores se conservan como antecedentes.

---

## Estado vigente - 2026-09-10 17:54 -0600 America/Costa_Rica - Programacion / Recuperar Tasks

**Implementado en Google Drive; prueba real en FreeCAD 1.1.3 pendiente.**

> Trabajo directo de GPT; no atribuir a Codex.

Se agrego `RecuperarPanelTareas.FCMacro` v0.1.0 y su SVG a la carpeta `Programación` vigente, y se actualizo `programacion_toolbar.py` en su misma identidad a v1.1.0 con el comando unico `Programacion_RecoverTasks`. La herramienta captura estado PRE/POST de documento, MDI, TaskDialog, centralWidget, Model/Tasks y docks; refresca usando `showModelView()` y retorno condicional a `showTaskView()` sin cerrar tareas ni restaurar/redimensionar el layout global.

Bytes re-leidos desde Drive: sintaxis PASS para macro y toolbar; cero llamadas prohibidas de cierre/destruccion/reset global detectadas; comando nuevo presente una sola vez. La auditoria read-only existente no fue modificada. El panel negro aun no se ha reproducido ni validado con esta version, por lo que el estado es **IMPLEMENTADA / POR VALIDAR EN GUI REAL**.

---

## Demo ElectricCR A1 v0.1 - 2026-09-09 22:39 -0600 America/Costa_Rica

**PRUEBA REAL FAIL; PRIMER FALLO REPRODUCIDO; SIN MODIFICAR CODIGO.** A1 aprobado permanece sin cambios.

Se ejecuto `tests/freecad_electric_demo_smoke.py` original en FreeCAD 1.1.3 (2026-09-09T22:37:32.318785-06:00). Falla en `electriccr/demo/electric_demo_freecad.py:100`, `_create_metadata`: `doc.addObject("App::Feature", "ECR_Demo_Metadata")` produce `TypeError: Document::addObject: 'App::Feature' is not a document object type`. La misma llamada en un documento vacio reprodujo el error.

La demo se cierra al fallar antes de crear edificio, Oficina, Bodega, muros o dispositivos. No se alcanzaron auditoria 7/7, movimiento, Undo/Redo, Delete, save/reopen ni comprobacion visual. No aprobar esas etapas. Todos los documentos de esta prueba quedaron cerrados.

Resultado, traceback y consola: [evidencia del primer fallo](tests/evidence/2026-09-09_electric_demo_v01_first_failure/README.md). El registro distingue un KeyError previo de preparacion (Workbench no registrado; test luego importado directamente) del fallo real reproducido. No se hicieron cambios de codigo, IFC, apertura de Upala, reparaciones, commit/push ni diagnostico de fallos posteriores.

---

## Estado vigente - 2026-09-09 22:09 -0600 America/Costa_Rica - Demo ElectricCR A1 v0.1 implementada en Drive

**A1 permanece aprobado. Se implemento un banco de pruebas autocontenido y canonico; falta validarlo en FreeCAD 1.1.3 real.**

> Trabajo directo de GPT en Drive; no atribuir a Codex.

La demo adopta el mismo patron arquitectonico que resulto util en Facil Arquitectura: especificacion pura reproducible -> adaptador FreeCAD -> auditor -> comando/boton -> macro minima. No depende de Upala, Chomes ni otro modelo productivo.

V0.1 crea un documento nuevo con edificio, Nivel 00, Oficina/Bodega como Spaces nativos, cinco muros BIM y siete identidades A1 (2 tomas, 2 apagadores, 2 luminarias, 1 sensor). Cada dispositivo recibe UID determinista y conserva el contrato Owner App::Link + master fisico + PLAN. IFC, Circuit real, Control real y variantes aleatorias quedan expresamente fuera de esta version.

Archivos nuevos en Drive: `electriccr/demo/electric_demo_core.py`, `electric_demo_freecad.py`, `electric_demo_audit.py`, `commands/demo_electriccr.py`, `Demo_ElectricCR_A1.FCMacro`, `tests/test_electric_demo_core.py` y `tests/freecad_electric_demo_smoke.py`. `InitGui.py` fue actualizado en su mismo ID para registrar `Demo ElectricCR A1` y `Auditar Demo ElectricCR A1`.

Verificacion disponible: 7/7 pruebas puras aprobadas y compilacion sintactica aprobada. Estado de producto: **IMPLEMENTADA / POR PROBAR TECNICAMENTE EN FREECAD REAL**. No se afirma todavia que RoomResolver, Arch Space/Wall, GUI, Undo/Redo o save/reopen hayan pasado con esta demo concreta.

---

## Estado vigente - 2026-09-09 22:09 -0600 America/Costa_Rica - estudio GPT de interoperabilidad IFC

**A1 permanece aprobado. La integracion IFC se orienta provisionalmente a un adaptador de exportacion alrededor de A1; no existe integracion productiva implementada.**

> Trabajo directo de GPT en Drive; no atribuir a Codex.

La investigacion de FreeCAD 1.1.3 confirma que el exportador/NativeIFC ya aporta piezas reutilizables suficientes para evitar un segundo modelo electrico persistente: creacion de productos IFC desde objetos FreeCAD, representacion geometrica mediante el exportador existente, ObjectPlacement, GlobalId, Psets, contextos Model/Plan y trabajo sobre un `ifcopenshell.file` existente.

Decision de estudio actual:

```text
ElectricCR A1 = autoridad de diseno
IFC            = proyeccion/intercambio
NativeIFC      = infraestructura reutilizable
PLAN           = documentacion ElectricCR; no segunda identidad IFC
```

La prueba real NativeIFC previa sigue siendo `COMPROBADA-PARCIAL`; no demuestra que NativeIFC deba sustituir `App::Link + master`. Se mantiene como candidata para interoperabilidad y semantica IFC.

Nueva propuesta de validacion: una macro/demo autocontenida de ElectricCR, equivalente en filosofia a la Demo Casa de 2 Plantas, para crear un modelo electrico pequeno y reproducible y ejercer el adaptador IFC cuando exista. Estado actual de esa macro: **DEFINIDA CONCEPTUALMENTE / NO IMPLEMENTADA / PENDIENTE DE AUTORIZACION**.

---

## Estado vigente - 2026-09-09 20:02 -0600 America/Costa_Rica

**A1 aprobado y cerrado en GitHub; experimento NativeIFC completado sin modificar A1.**

A1 cerrado en GitHub: [4a9ade9](https://github.com/MVM444/Macros-de-Freecad/commit/4a9ade9645d9227ac5323676ee911c972502e869), constancia [285d5a7](https://github.com/MVM444/Macros-de-Freecad/commit/285d5a74b6463dc859d0bc0a940b2879aa6c4c2a), rama `codex/cierre-a1-20260909`; ambos pushes confirmados, staging limpio. Se separaron cambios ajenos y la evidencia publica se anonimizo conforme AGENTS. No merge a main ni release Addon. DEV funcional sin cambios.

Prueba real IFC4: cuatro Part::FeaturePython (Outlet, SwitchingDevice, LightFixture, ElectricDistributionBoard), GUID/StepId y Placement/Pset editados persistentes tras FCStd+IFC y reapertura IFC. Type=None; cuatro ocurrencias, un proyecto de infraestructura. Mallas genericas sin solidos, sin excepciones de consola. No se uso Upala ni conversiones existentes. Todo cerrado y evidencia archivada.

Decision provisional: explorar **NativeIFC como capa/adaptador alrededor de A1 (opcion2)**. Los mapas IFC permiten compartir representacion, pero no se probo Type compartido ni equivalencia con App::Link. No adoptar nucleo ni hibrido todavia. No hay integracion implementada. Detalles/campos/limitaciones en [reporte](tests/evidence/2026-09-09_nativeifc_four_elements/README.md) y RESULTADO_CODEX.md. NativeIFC = EXPERIMENTAL / COMPROBADA-PARCIAL; A1 mantiene su estado previo.

---

## A1 GitHub closure confirmed - 2026-09-09T09:16:00.625279-06:00

Commit: `4a9ade9645d9227ac5323676ee911c972502e869`.
Branch: `codex/cierre-a1-20260909`.
Remote: https://github.com/MVM444/Macros-de-Freecad . Push: **SUCCESS**, upstream configured and remote branch created.

26 files: approved A1 implementation/dependencies, generic tests, documentation and anonymized evidence. No new functionality. Unrelated door-side hunks and other local work excluded. Public documentation retains history with neutralized local references; complete DEV records retain their identity/location. No merge to main or Addon release performed.

---

## Estado vigente - 2026-09-08 17:49 -0600 America/Costa_Rica

**A1 = APROBADO PARA CONTINUAR** en FreeCAD 1.1.3, despues de inicializar ElectricCR una vez por sesion; verificacion funcional tambien con BIM, Draft y Part activos.

Se corrigio la causa demostrada: Deactivated desinstalaba el redirector PLAN -> Owner. Lifecycle y live sync ya sobrevivian. Antes del cambio, Std_Delete sobre PLAN en Part dejaba Owner sin PLAN (10/9). Ahora seleccion e instalacion son persistentes/idempotentes y se corrigio la ruta de importacion para normalizar el arbol.

Modelo actual de `C:\Users\marco\...\Upala\1416 Levantamiento 250424 Compu D.FCStd`: **10 Owners / 10 PLAN**, cero inconsistencias. Copia temporal: exactamente un dispositivo nuevo, movimiento/giro, modos visuales, Delete/Undo/Redo en BIM/Draft/Part, save/close/reopen y repeticion final aprobados; vuelve a 10/10. Cero errores Placement o Access violation observados. Owner conserva identidad, Placement, Host/Space/puerta; PLAN fuera del arbol y grupos. Original intacto, SHA256 `F5E1A372D162F02E5D91CD874F47A13B412380972F0604E27D9D77D71E87077F`.

Evidencia y limites en [RESULTADO_CODEX.md](RESULTADO_CODEX.md) y [reporte de regresion](tests/evidence/2026-09-08_a1_workbench_runtime/README.md). El instrumento registra por separado errores de diagnostico corregidos y marcadores Touched de evaluacion nativa; no hubo inconsistencia A1 final.

Cambios funcionales acotados: InitGui.py, ui/plan_selection.py, electriccr/features/plan_live_sync.py. No se redisenaron A1 ni lifecycle, ni se repararon PLAN actuales. Pendientes no bloqueantes: feedback persistente, NativeIFC/IFC, arbol semantico/Wall-electrico, ClaimHosted, Rectangle006 historico y orientacion en muros inclinados. No usar ghostTracker. No se valido arranque directo en otro WB sin inicializar ElectricCR.

Sin commit/push ni confirmacion de sincronizacion Drive. Resultado funcional validado por Codex; no registrar aceptacion definitiva de Marco en HISTORIAL_CAMBIOS. Esta entrada sustituye el bloqueo de fuente de las 12:32 y las propuestas antiguas de overlay; entradas inferiores historicas.

---
## Estado vigente - 2026-09-08 12:32 America/Costa_Rica

**AUDITORIA A1 ACTUAL PENDIENTE DE ACCESO A LA FUENTE; SIN REGRESION ACTUAL DEMOSTRADA.**

Marco informa validacion manual APROBADA en FreeCAD 1.1.3: crear/guardar, Delete Owner+PLAN, Undo enlazado, Redo, guardar/cerrar/reabrir. La auditoria independiente 1:1 y la regresion sobre copia quedan pendientes porque el archivo validado bajo `C:\Users\mmfallas\...\Upala\1416 Levantamiento 250424 Compu D.FCStd` no existe en este host (`DESKTOP-5586S7P`, usuario `marco`). Se solicito su ruta accesible.

No usar la copia antigua local del 5/9 a las 22:02 para juzgar el estado actual. Su problema historico era Owner=None en PLAN huerfanos; no binding persistido corrupto demostrado. Sin cambios de codigo ni reparaciones. No hay cifras actuales de Owners/PLAN verificadas por Codex. Detalle en la entrada del 8/9 de RESULTADO_CODEX.md.

A1 conserva Owner App::Link como unica identidad/autoridad espacial y PLAN Part::Feature documental reconstruible. Quedan fuera de esta auditoria los temas expresamente diferidos por el usuario. Sin commit/push.

---
## Estado 2026-09-05 21:01 - cierre A1: feedback PLAN y multiparentalidad diagnosticada

Estado: **IMPLEMENTADO EN DRIVE / POR VALIDAR EN FREECAD 1.1.3 / A1 OPT-IN**.

- `plan_selection.py` v0.3.0 usa overlay GUI-only basado en Draft `ghostTracker`; Owner sigue siendo la unica seleccion logica.
- `plan_live_sync.py` v0.3.0 mantiene el overlay alineado con PLAN y normaliza PLAN fuera del arbol.
- `objeto_toma_uno.py` permanece en rev N: PLAN.Owner hidden; Host/MuroReferencia sin cambio.
- Los 10 apagadores repetidos de Upala son una sola instancia cada uno con dos TreeParents (`Wall` + `Apagadores BIM`), no duplicados de datos.
- Se descarto por ahora convertir `Host` a hidden: FreeCAD BIM usa `Wall.InList + Host` tambien para `getMovableChildren()`, por lo que eliminar backlink podria perder movimiento nativo con host.
- `ClaimHosted=False` es candidato nativo para la vista del arbol, pero es global; proyeccion por referencia indice es la alternativa localizada ya compatible con el contrato semantico. Decision pendiente de prueba comparativa.
- Pendientes separados: referencia comun `Rectangle006`; orientacion en muros inclinados; integracion global `FA_Project/05_Electromechanical`.

---

## Estado 2026-09-05 20:22 - feedback PLAN completo y Owner Hidden implementados / prueba real pendiente

Nueva observacion real de Marco: el PLAN redirige correctamente la seleccion al Owner, pero
el feedback grafico nativo quedaba sobre una sola `Edge`/`Vertex`, no sobre el simbolo completo.

Implementado en Drive:

```text
plan_selection.py v0.2.0
  hover/clic Edge|Vertex PLAN
      -> preselection PLAN con subname=""
      -> simbolo completo como feedback visual
      -> seleccion logica sigue siendo Owner solamente

objeto_toma_uno.py rev N
  PLAN.Owner = App::PropertyLinkHidden
  PLAN legado PropertyLink -> migracion transaccional al sincronizar
  expresion PLAN <- Owner preservada/verificada
```

Estado:

```text
seleccion PLAN -> Owner                  APROBADO REAL previo
feedback PLAN completo                   IMPLEMENTADO / PRUEBA REAL PENDIENTE
Solo2D con Owner oculto                  IMPLEMENTADO / PRUEBA REAL PENDIENTE
PropertyLinkHidden                       IMPLEMENTADO / PRUEBA REAL PENDIENTE
Delete sin aviso                         OBJETIVO DE PRUEBA REAL
Delete Owner + PLAN                      APROBADO REAL previo
Undo/Redo sin crash                      PENDIENTE CRITICO
save/reopen                              PENDIENTE para rev N
A1 default                               NO
muro inclinado junto a puerta            PENDIENTE DIFERIDO
```

No se creo segunda identidad, Placement, snap, grip ni comando Delete paralelo.

---

## Estado 2026-09-05 - A1 Solo2D/Solo3D corregido en Drive, prueba real pendiente

Causa del problema recurrente identificada: el gestor existente escribia `ModoVisual`,
mientras A1 usaba `MostrarModelo3D` y `MostrarSimboloPlano` para dos ViewObjects separados.

Se corrigio el puente entre ambos contratos:

```text
Ambos   -> 3D ON  / PLAN ON
Solo2D  -> 3D OFF / PLAN ON
Solo3D  -> 3D ON  / PLAN OFF
```

Archivos modificados en sus mismos IDs:
- `electriccr/features/objeto_toma_uno.py` rev M;
- `electriccr/features/plan_live_sync.py` v0.2.0;
- `InitGui.py`.

Se reutiliza `Gestionar_Visibilidad_ElectricCR.FCMacro`; no se creo otro gestor. La barra
principal ElectricCR intentara exponer el gestor existente, `Draft Move` y `Snap Special`
si esos comandos estan registrados al inicializar.

Estado:

```text
Transformar Owner + PLAN en vivo       APROBADO REAL
seleccion PLAN -> Owner                APROBADO REAL
Solo2D/Solo3D/Ambos                    IMPLEMENTADO / PRUEBA REAL PENDIENTE
Snap Special en barra ElectricCR       IMPLEMENTADO / PRUEBA GUI PENDIENTE
feedback visual PLAN seleccionado      PENDIENTE
Delete Owner + PLAN                    FUNCIONA; aviso de dependencia pendiente
muro inclinado junto a puerta          PENDIENTE DIFERIDO
A1 default                             NO
```

---

## Estado 2026-09-05 16:10 - Transformar aprobado; visibilidad UX y orientacion quedan pendientes

Prueba real de Marco en Upala / FreeCAD 1.1.3:

```text
Transformar Owner -> PLAN sigue en vivo   FUNCIONA
seleccion PLAN -> Owner                    FUNCIONA
solo 3D / solo 2D como UX clara           PENDIENTE / problema recurrente
alineacion de dispositivo en muro inclinado junto a puerta
                                             PENDIENTE
```

La sincronizacion en vivo mediante Transformar se considera validada en el caso probado.

La colocacion junto a puertas conserva una deuda geometrica: si el muro esta inclinado, el
dispositivo no se orienta paralelo a la pared. Debe diagnosticarse aparte usando la direccion
real del tramo/host y sin alterar la tarea A1 actual.

La separacion interna de visibilidades no equivale todavia a una experiencia clara de
`Solo 3D` / `Solo 2D`; mantener este punto abierto.

A1 continua opt-in.

---

## Estado 2026-09-05 16:10 - A1 refresco interactivo y seguridad Undo en prueba

Validacion real en Upala:

```text
Transformar usa origen 2D              FUNCIONA
3D se mueve en vivo                    FUNCIONA
PLAN se mueve en vivo                  FALLA: queda atras hasta F5/recompute
expresion PLAN<-Owner                  SIGUE INTACTA
SnapPoints PLAN (0,0,0)                PRESENTE
Undo de creacion con lifecycle         FALLO GRAVE: Access violation
```

Correcciones GPT en Drive:

- `plan_lifecycle.py` 0.1.1 ignora completamente Undo/Redo/rollback mediante
  `Document.isPerformingTransaction()`.
- nuevo `plan_live_sync.py` recompone solo el PLAN asociado cuando cambia
  `Owner.Placement`, evitando `doc.recompute()` global.
- `InitGui.py` instala el nuevo observer.

`Draft Snap Special` no es un comando visible de movimiento: es un modo de snap consumido por
`Draft Move` y otras herramientas que piden puntos. Ya esta declarado en `Draft compacto`;
si la sesion no reconstruyo la toolbar, requiere reinicio/reconstruccion del Workbench.

A1 continua opt-in hasta aprobar Transformar/Draft Move, Undo/Redo, Delete y dos documentos.

---

## Estado 2026-09-05 15:43 - A1 seleccion y borrado validados; dos detalles UX pendientes

Validacion real de Marco en FreeCAD 1.1.3:

```text
clic PLAN -> Owner                  FUNCIONA
mover Owner -> PLAN + 3D            FUNCIONA
ocultar Owner -> solo 3D oculto     FUNCIONA / comportamiento deseado
Delete Owner -> Owner + PLAN        FUNCIONA
aviso Std_Delete de dependencia     PENDIENTE DE ELIMINAR
resaltado visual de PLAN            PENDIENTE
```

El aviso se debe a que `PLAN.Owner` sigue siendo `App::PropertyLink`, por lo que
`Std_Delete` detecta PLAN como dependencia antes de que el observador de ciclo de vida
pueda borrarlo.

Se identifico `App::PropertyLinkHidden` como alternativa nativa especificamente oculta al
chequeo de dependencias. No se adopta aun: debe probarse en FreeCAD 1.1.3 que la expresion
de Placement sigue propagando movimiento/giro y que Undo/Redo/save/reopen permanecen
correctos.

Para feedback visual se mantiene Owner como unica seleccion logica. Se probara primero
`Gui.Selection.setPreselection()` sobre PLAN; no se seleccionaran Owner+PLAN juntos.

`Draft Snap Special` es el snap nativo que consume `PLAN.SnapPoints=[(0,0,0)]`; se activa
desde Draft Snap/Draft Snap Widget y esta expuesto tambien en `Draft compacto`.

A1 continua opt-in.

---

## Estado 2026-09-05 14:35 - A1 punto de insercion nativo implementado en Drive

Se adopto el mecanismo nativo `SnapPoints` + `Draft Snap Special`.

```text
PLAN.SnapPoints = [(0,0,0)]
Draft Move       = ya disponible
Snap Special     = agregado a Draft compacto
```

No se agrego geometria al PLAN ni al STEP, por lo que el DXF no cambia por esta
implementacion. El punto local se transforma mediante `PLAN.Placement`, que ya
deriva del Owner.

Auditoria:
- toma/apagador/etiqueta ya tienen geometria en el origen;
- luminaria redonda puede usar Snap Center;
- luminaria 60x60 no tiene vertex central, por lo que `SnapPoints` aporta una
  referencia uniforme;
- tres recursos declarados por el registry (`toma_gfci.step`, `toma_240v.step`,
  `toma_tv.step`) no se localizaron en Drive y quedan como deuda independiente.

Estado:

```text
seleccion PLAN -> Owner        VALIDADA EN CASO REAL
movimiento 2D/3D conjunto      VALIDADO EN CASO REAL
borrado Owner + PLAN           IMPLEMENTADO / POR VERIFICAR
SnapPoint PLAN (0,0,0)         IMPLEMENTADO / POR VERIFICAR
A1 default                     TODAVIA NO
```

---

## Estado 2026-09-05 14:05 - A1 seleccion/movimiento validado; borrado conjunto implementado en Drive

Validacion de Marco en FreeCAD 1.1.3:

- clic PLAN -> seleccion del Owner: FUNCIONA;
- PLAN ya no aparece como segunda identidad al seleccionar: FUNCIONA en el caso probado;
- mover dispositivo -> 2D y 3D juntos: FUNCIONA;
- Delete Owner -> PLAN huerfano con `Owner=null`: FALLA CONFIRMADA.

GPT implemento en Drive `electriccr/features/plan_lifecycle.py` y conecto su instalacion
desde `InitGui.py`. El modulo observa eliminaciones A1 y elimina la documentacion PLAN
asociada, intentando mantener ambos borrados en una misma transaccion de FreeCAD.

Estado:

```text
seleccion PLAN -> Owner        VALIDADA FUNCIONALMENTE EN CASO PROBADO
movimiento Owner -> PLAN       VALIDADO FUNCIONALMENTE EN CASO PROBADO
borrado Owner + PLAN           IMPLEMENTADO / POR VERIFICAR EN FREECAD REAL
A1 default                     TODAVIA NO
migracion legacy               NO
```

Pendiente prioritario: Delete + Undo/Redo + dos documentos abiertos.

---

# ACTUALIZACION 2026-09-05 - UX 2D de A1 pendiente antes del default

FreeCAD objetivo: 1.1.3
Estado vigente: **SINCRONIZACION ESPACIAL A1 CERRADA / EDICION DESDE PLAN
PENDIENTE / A1 CONTINUA OPT-IN**.

La expresion nativa PLAN <- Owner ya mantiene X/Y/orientacion y Z documental,
pero el PLAN sigue siendo actualmente un objeto seleccionable independiente. Al
hacer clic en el simbolo puede aparecer el auxiliar `...[PLAN]` en el arbol y,
por estar su Placement gobernado por expresion, no constituye una interfaz libre
de movimiento.

Nuevo criterio de producto:

- clic sobre PLAN debe seleccionar el `Owner` principal;
- PLAN debe quedar oculto del arbol como auxiliar documental cuando sea viable;
- con 3D oculto y PLAN visible debe poder trabajarse en planta;
- mover desde 2D debe modificar `Owner.Placement`, nunca un Placement PLAN
  independiente;
- el punto de insercion/arrastre del simbolo debe ser el origen local `(0,0,0)`;
- reutilizar primero `Draft Move` y snaps nativos antes de crear un dragger
  propio;
- verificar seleccion redirigida con multiples documentos en FreeCAD 1.1.3.

No se genera todavia una nueva `TAREA_ACTUAL.md`; este bloque es estudio previo
para cerrar el contrato antes de entregarlo a Codex.

---

# ACTUALIZACION 2026-09-05 - sincronizacion espacial A1 PLAN/Owner cerrada

FreeCAD objetivo: 1.1.3
Estado vigente: **EXPRESION NATIVA IMPLEMENTADA Y PROBADA / A1 APTO PARA
DEFAULT DE OBJETOS NUEVOS / DEFAULT AUN OPT-IN**.

PLAN permanece `Part::Feature DocumentationOnly` con `Owner` PropertyLink, pero
su Placement ya no es una copia libre. Una expresion nativa deriva X/Y y
rotacion desde `Owner.Placement`, y Z desde `Owner.DocumentationPlaneZ`.
`PlanSymbolScale` continua afectando solo la Shape documental.

`RepresentationSignature` esquema 2 ya no contiene Placement, UID ni Z
documental. Mover o girar un dispositivo no reconstruye el simbolo; FreeCAD
recalcula su transformacion por la dependencia guardada en el documento.

La prueba sobre copia de Chomes reprodujo y corrigio los 259 mm de
`TomaBIM_011`, y aprobo toma/apagador A1, movimiento, giro, altura, Z, escala,
Undo/Redo, save/reopen, recompute repetido, DXF e inexistencia de huerfanos.
El original permanecio byte a byte igual y los temporales se eliminaron.

Los objetos nuevos quedan corregidos. Los PLAN A1 esquema 1 existentes reciben
la expresion cuando se sincronizan; no hubo migracion productiva. A1 permanece
opt-in porque esta tarea no autoriza cambiar el default.

---

# ACTUALIZACION HISTORICA 2026-09-03 - defecto de sincronizacion espacial A1 PLAN/Owner

FreeCAD objetivo: 1.1.3
Estado vigente: **A1 OPT-IN / DEFAULT SUSPENDIDO / SINCRONIZACION ESPACIAL PENDIENTE**.

Un uso real posterior a la aceptacion GUI detecto en `Chomes-Segundo Piso.FCStd`
que el PLAN de un dispositivo A1 no sigue automaticamente un movimiento manual
del `App::Link` propietario.

Evidencia del caso `TomaBIM_011`:

```text
ElementUID = 975bd98d-7a56-4765-b5d5-f6d778452c90
Owner Placement = (19263, 11260, 0)
PLAN Placement  = (19004, 11260, 0)
delta X = 259 mm
PLAN.Owner = Link_TomaBIM_011
PLAN.ExpressionEngine = []
```

La aceptacion anterior demostro creacion, separacion fisica/documental,
save/reopen, Undo/Redo e invariancia fisica, pero no incluyo mover/girar
manualmente un dispositivo despues de creado y comprobar seguimiento automatico
del PLAN.

Por tanto, la conclusion anterior `A1 APTO PARA DEFAULT` queda **suspendida**,
no eliminada del historial. Antes de cualquier cambio de default debe cerrarse
`ElectricCR / A1 sincronizacion espacial PLAN-Owner`.

Regla vigente:

```text
Device.Placement = unica autoridad espacial
Physical 3D      = representacion derivada
PLAN 2D          = representacion derivada
```

PLAN puede mantener escala, visibilidad, variante grafica y Z documental propios,
pero no X/Y/orientacion independientes del dispositivo.

No se modifico codigo, Chomes, objetos legacy ni el default productivo en esta
actualizacion documental.

---

# ElectricCR - Estado actual del proyecto

## Estado vigente - aceptacion funcional GUI A1 cerrada

Ultima actualizacion: 2026-09-03 America/Costa_Rica
FreeCAD objetivo: 1.1.3
Estado: **ACEPTACION GUI APROBADA / A1 APTO PARA DEFAULT DE OBJETOS NUEVOS /
DEFAULT LEGACY TODAVIA INTACTO**.

Los comandos completos registrados de tomacorrientes sobre muros BIM y
apagadores junto a puertas BIM aprobaron legacy por defecto, A1 opt-in y
reapertura de sus dialogos. La casilla A1 no persiste. Los objetos creados por
la GUI llegaron al contrato `PhysicalDocumentationA1` ya documentado sin
fallback a `LegacyCompound`.

La copia temporal de Upala produjo 31 tomas A1 sobre los 19 tramos del muro
seleccionado y un apagador A1 junto a `Window`. El arbol temporal tuvo 32
identidades, 32 PLAN, cero huerfanos y UID unicos. Las instancias conservaron
Host, Space, PuertaOrigen cuando aplica, Placement, altura, master fisico y
PLAN documental; aprobaron invariancia fisica, Undo/Redo y save/reopen estable.

No se detecto una falla reproducible y no se modifico codigo. El original de
Upala conservo hash, tamano y fecha; los temporales fueron eliminados. La
evidencia vive en la carpeta `ElectricCR/Pruebas y regresiones` de Drive.

La decision de aptitud no cambia el valor predeterminado en esta fase. Activar
A1 como default requiere una tarea separada y no implica migrar objetos legacy.

## Estado vigente - Contrato A1 fisico/documental

Ultima actualizacion: 2026-09-03 America/Costa_Rica
FreeCAD objetivo: 1.1.3
Estado: **IMPLEMENTADO COMO RUTA OPT-IN / VERIFICADO MCP / SIN MIGRACION PRODUCTIVA**.

El diagnostico del codigo demostro que A1 no existia aun: la ruta vigente
componia `symbol2D` y `model3D` dentro de una misma `Shape`. Ahora
`PhysicalDocumentationA1` mantiene exclusivamente el modelo fisico 3D en la
Shape del master/`App::Link`, y crea PLAN como representacion
`DocumentationOnly` independiente con enlace `Owner` a la unica identidad.

El contrato semantico comun de la instancia incorpora `ElementUID`, `Space` y
`Host`. Los masters A1 usan nombres separados de los `LegacyCompound`; la ruta
legacy sigue siendo el valor por defecto, de modo que no hubo migracion ni
recompute de objetos existentes.

La prueba `tests/freecad_electromechanical_outlet_switch_a1_smoke.py`, ejecutada
por MCP en FreeCAD 1.1.3, creo en un documento temporal exactamente un
tomacorriente y un apagador. Ambos aprobaron Shape/Volume/BoundBox/Solids,
PLAN plano e independiente, UID/Space/Host, Placement, altura mediante relink,
App::Link/master, save/reopen, Undo/Redo, sincronizacion idempotente y DXF PLAN.
El documento temporal y su DXF se eliminaron al finalizar.

No se modifico el documento productivo abierto ni los dispositivos de Upala;
no se hizo commit ni push. La adopcion o migracion productiva continua fuera de
alcance y requiere autorizacion separada.


### Integracion real A1 cerrada

Las herramientas reales de tomacorrientes generales sobre muros BIM y
apagadores junto a puertas BIM ya aceptan A1 de forma opt-in. La casilla queda
desmarcada y no se persiste, de modo que `LegacyCompound` sigue siendo el
default productivo. Ambas reutilizan `crear_toma_link`, el adaptador semantico y
la representacion PLAN A1 existentes; no se creo otra arquitectura.

La prueba controlada `tests/freecad_upala_real_placement_a1_smoke.py` aprobo por
MCP en FreeCAD 1.1.3 con exactamente una toma A1 y un apagador A1. Se verifico
Shape fisica, PLAN separado, UID, Host, Space/RoomResolver, PuertaOrigen,
Placement, relink de altura, save/reopen, Undo/Redo, DXF e invariancia fisica
durante sincronizacion PLAN. La fuente de Upala permanecio byte a byte igual y
los temporales fueron eliminados.

Drive conserva evidencia historica de los 48 tomacorrientes y 11 apagadores
legacy. El FCStd vigente ya no los contenia al ejecutar esta fase (187 objetos,
cero dispositivos ElectricCR), por lo que esa discrepancia queda expresamente
documentada y no se presenta como una comparacion inexistente dentro del mismo
archivo. No se migro ni modifico ninguna identidad legacy.

`Apagador - Rectangle006` fue investigado: `Rectangle006` era `AreaRecinto`, no
la puerta. La puerta era `Window` y el host `Wall`. El Label derivaba del
recinto auxiliar; la diferencia entre su Placement historico y el punto de
jamba producido por el algoritmo vigente queda abierta, sin correccion
intuitiva.


## Barra comun Espacios y Recintos v0.1

Ultima actualizacion: 2026-09-02 America/Costa_Rica
Estado: **INTEGRADA Y VERIFICADA MCP EN FREECAD 1.1.3**.

ElectricCR puede cargar los comandos comunes sin activar Facil Arquitectura.
El registro es idempotente y la barra fue verificada visualmente. Se conserva
visible `PoligonosRecintosDesdeArchWalls.FCMacro` como **Recintos desde muros
BIM**, sin cambiar su algoritmo, metadatos, enlaces ni regeneracion.

Esta integracion no migra Areas, no crea Spaces y no modifica dispositivos.


### Contrato transversal con Facil Arquitectura y dispositivos A1

A partir del resultado A1 del 2026-09-03 queda definido:

```text
FA/BIM Space  -> Device.Space
FA/BIM Wall   -> Device.Host
FA/BIM Door   -> Switch.PuertaOrigen cuando aplique
Level         -> derivado de Space
```

FA conserva la autoria arquitectonica; `CRBIMCore.RoomResolver` resuelve la
identidad espacial; ElectricCR consume esos enlaces. Sketches, Areas y poligonos
legacy pueden mantenerse como compatibilidad/auxiliares, pero no desplazan a un
objeto BIM valido como autoridad.

El Space real permanece bajo Building/Level. El arbol ElectricCR es una
proyeccion reproducible y no debe mover ni duplicar el Space.


## Estado vigente - Prototipo luminaria semantica y arbol idempotente

Ultima actualizacion: 2026-09-02 America/Costa_Rica
FreeCAD objetivo: 1.1.3
Estado: **CERRADO / IMPLEMENTADO / VERIFICADO MCP EN FREECAD 1.1.3**.

Revalidado el 2026-09-02 sin cambios funcionales: modulos cargados desde DEV,
pruebas puras y smoke integral aprobados, cero documentos/temporales residuales.

La fase 2A de RoomResolver permanece cerrada y verificada. No se reabre ni se modifica su baseline.

Hallazgo principal de esa fase historica: ElectricCR ya posee un nucleo generico en
`electriccr/features/objeto_toma_uno.py`. En el prototipo semantico de luminaria
se conservaba la representacion legacy compuesta; la fase A1 posterior ya separo
la Shape fisica del PLAN documental sin crear una segunda identidad funcional.

Por tanto, la direccion vigente es **auditar y evolucionar este nucleo**. `Arch
Equipment` se compara como posible capacidad nativa BIM/IFC o adaptador; no se
adopta como reemplazo automatico.

El contrato `relaciones -> arbol` permanece autoritativo. El trabajo actual define
los futuros enlaces `Space`, `Circuit`, `Panel`, `Control`, `System`, `Level` y
`Host`, la compatibilidad con masters/App::Link y la reconstruccion idempotente del
arbol. No se han modificado dispositivos, FCStd, masters ni codigo.

Documento de diseno:
`ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md`.

La matriz de decision ya se cerro a nivel de diseno: `App::Link` vigente es la identidad operativa preferida para el primer prototipo; `TomaUnoProxy` conserva el nucleo geometrico/masters y `Arch Equipment` se compara especificamente por BIM/IFC. El contrato minimo propone `ElementUID`, `Space` y `Circuit`, derivando Level/Panel cuando sea posible.

El prototipo reversible ya fue implementado y probado con una sola luminaria
temporal. La identidad operativa sigue siendo el `App::Link` actual, enriquecido
solo con `ElementUID` y `Space`. El arbol se deriva de `Space`, `CircuitoID` y
los LinkList existentes de Control, usa claves estables y es idempotente.

La rama visual utiliza un `App::Link` de indice marcado como referencia de
proyeccion. Esto evita retirar la luminaria fisica de su grupo manual, porque
los `App::DocumentObjectGroup` de FreeCAD mantienen pertenencia visual
exclusiva. Los masters permanecen ocultos en `_lib/_lib_devices`.

El comparador `Arch Equipment` confirma propiedades BIM/IFC y `IfcType=Light
Fixture`, pero requiere Base/copia geometrica. No sustituye el esquema de master
compartido. No se autoriza desde este cierre una migracion de dispositivos ni
el inicio de tomacorrientes/apagadores.

---

## Estado vigente - RoomResolver fase 2A

Ultima actualizacion: 2026-09-01 America/Costa_Rica
FreeCAD: 1.1.3 revision 20260725
Estado: **CERRADA / VERIFICADA MCP**.

El calculo integral de iluminacion enumera recintos mediante `CRBIMCore`.
Space tiene prioridad sobre Area heredada, la hoja `DatosRecintos` conserva su
contrato de 12 columnas y el comando no escribe propiedades de layout en
Spaces. La compatibilidad legacy de Areas permanece.

El contrato `relaciones -> arbol` esta documentado y la ruta A1 opt-in ya
verifico `Space` y `Host` en dispositivos temporales. Los dispositivos legacy
no han sido migrados. Circuit, Panel, Control/System y la integracion productiva
siguen en consolidacion; `Level` se deriva de Space por defecto.

La reconstruccion idempotente del arbol se probo en prototipo, pero no se ha
aplicado a proyectos reales.

---

**Proposito:** Resumir la arquitectura vigente y el estado de integracion que debe conocerse antes de modificar objetos ElectricCR.

**Version:** 2026-08-12 14:30, America/Costa_Rica.

## Entorno

- Version objetivo actual: FreeCAD 1.1.3.
- Repositorio: `MVM444/Macros-de-Freecad`.
- Workbench principal en esta carpeta: `ElectricCR/`.
- Macros auxiliares relacionadas se encuentran tambien en carpetas como `Objetos/`, `Deteccion/`, `Iluminacion/` y `Resources/`.
- El flujo obligatorio de trabajo y validacion se documenta en `FLUJO_GPT_CODEX.md`.
- El mapa operativo vivo del Workbench se documenta en `MAPA_WORKBENCH.md`.
- Las decisiones de depuracion y migracion macro por macro se registran en `REVISION_MACROS.md`.

## Memoria operativa del proyecto

ElectricCR adopta como regla que el repositorio debe contener suficiente contexto para que Marco, GPT y Codex puedan retomar el proyecto sin reconstruir de memoria como funciona el Workbench.

Codex debe reconstruir el contexto desde la documentacion y el codigo antes de pedirle al usuario explicaciones que pueda obtener por inspeccion tecnica.

`MAPA_WORKBENCH.md` describe como funciona el sistema actual.

`REVISION_MACROS.md` registra que se ha decidido sobre cada macro durante la depuracion y migracion.

Si el codigo actual contradice la documentacion, debe describirse el comportamiento real desde el codigo y corregirse la documentacion.

## Estado arquitectonico del Workbench

ElectricCR ya funciona como un Workbench Python mediante `ElectricCR/InitGui.py` y `Gui::PythonWorkbench`.

Sin embargo, una parte importante de sus herramientas se incorpora actualmente mediante el registro dinamico de archivos `.FCMacro` realizado por `ElectricCR/commands/macros.py`.

Esto significa que el Workbench actual es hibrido:

- infraestructura Python propia del Workbench;
- modulos Python internos;
- objetos ElectricCR propios;
- macros registradas como comandos;
- herramientas de soporte, pruebas y recursos.

El auto-registro de macros se considera una arquitectura de transicion. La existencia de una macro en una carpeta escaneada no demuestra que deba pertenecer al Workbench definitivo.

## Estrategia de evolucion adoptada

No se reinicia ElectricCR desde cero.

Se conserva y respalda el Workbench actual y se realiza una migracion progresiva.

La secuencia adoptada es:

```text
reconstruir contexto
  -> revisar macro dentro de su familia
  -> clasificar
  -> decidir destino ElectricCR
  -> migrar solo si corresponde
  -> probar tecnicamente
  -> validar funcionalmente
  -> aceptar e integrar
```

La revision se realiza inicialmente en este orden:

1. Areas
2. Objetos
3. Iluminacion
4. Tomacorrientes
5. Deteccion
6. Cajas
7. Tableros y Configuracion del proyecto
8. Conectar

`Conectar` se deja para una fase avanzada debido a la cantidad de estrategias geometricas, solapamientos y dependencias historicas.

## Estado de la tarea activa - Panel de macros ElectricCR

El lanzador de macros ya dispone de una implementacion local ampliada en
`ElectricCR/commands/macro_launcher.py`. La fuente de metadatos es
`ElectricCR/commands/macros.py` y las estadisticas siguen viniendo de
`ElectricCR/usage_log.py`; no se creo un segundo sistema de conteo ni se
escanea el repositorio desde el panel.

Estado: **PROGRAMADO / COMPILADO / PROBADO TECNICAMENTE / VALIDADO VISUALMENTE EN MCP**.

La prueba simulada con FreeCADCmd 1.1.3 registro 16 grupos y 122 comandos con
iconos especificos o `Rayo.svg`. El intento de validacion visual mediante MCP
expiró por timeout de la sesion GUI, por lo que la validacion visual en el
FreeCAD de Marco queda pendiente en ese primer intento. La verificacion
posterior esta documentada abajo. No se modificaron documentos FCStd.

## Arquitectura de dispositivos ElectricCR

## Estado de la tarea activa - Integracion de descripciones GPT

Estado: **IMPLEMENTADA / COMPILADA / PROBADA / VERIFICADA_MCP /
VALIDADA_VISUALMENTE**.

Se integraron por `ruta` las 192 entradas de
`ElectricCR/MACROS_DESCRIPCIONES_GPT.json`. El catalogo conserva 192
descripciones funcionales: 133 sustituyeron textos vacios o genericos y 59
descripciones locales concretas se mantuvieron. En 36 casos se registro la
alternativa GPT y la discrepancia sin reemplazar el texto local.

Los campos manuales de comentario, estado, decision y las estadisticas de
uso real, prueba e historico no fueron modificados. El Panel busca tambien
en la descripcion y muestra descripcion, fuente, confianza y discrepancias
en el detalle y en `Copiar diagnostico`.

La prueba en FreeCAD 1.1.3 valido 12 grupos, 192 filas catalogadas, una
busqueda por texto exclusivo de descripcion, diagnostico con descripcion y
comentario, y una herramienta visible de cada grupo principal. No se
modificaron documentos FCStd ni se hizo commit o push.

## Estado de la tarea activa - Panel Fase 2

Estado: **IMPLEMENTADA / COMPILADA / PROBADA / VERIFICADA_MCP /
VALIDADA_VISUALMENTE**.

El catalogo JSON contiene 192 entradas: 122 activas y 70 historicas. El Panel
lee descripciones, permite comentarios/estado/decision manuales, conserva la
Fase 1, separa uso real/pruebas/historico y ofrece filtros de auditoria,
historicas y contraer/expandir grupos. La prueba MCP con FreeCAD 1.1.3 mostro
12 grupos y 122 herramientas activas; la prueba de botones registro una
ejecucion real y una prueba en un log temporal. No se modificaron FCStd.

Correccion posterior: el comentario ahora se guarda contra el elemento
anterior de `currentItemChanged`, evitando que pase a la macro nueva. Las filas,
estadisticas, recursos de comandos y catalogo se cachean durante la apertura;
la busqueda ya no recalcula todo por cada tecla.

### Verificacion visual posterior del Panel

La validacion MCP posterior confirmo que la captura minima provenia de la
prueba segura: esa prueba habia sustituido en memoria `_MACRO_GROUPS` por un
grupo unico, aunque el registro de metadatos conservaba 122 comandos reales.
Al reconstruir los grupos desde el registro, el Panel real mostro 12 grupos y
122 filas, filtros, panel de detalles, botones y modo diagnostico. No se
modificaron documentos FCStd.

El modulo central revisado es:

- `ElectricCR/electriccr/features/objeto_toma_uno.py`

Este modulo permite representar tomacorrientes, apagadores, luminarias, sensores, rociadores, altavoces y camaras mediante:

- Un simbolo 2D cargado desde el registro.
- Un modelo 3D cargado desde el registro.
- Un objeto `Part::FeaturePython` directo o una instancia `App::Link` hacia un maestro oculto.

## Geometria local legacy y contrato A1

En la ruta `LegacyCompound` de objetos directos creados por `TomaUnoProxy`:

- El simbolo 2D se construye en `Z = 0` del sistema local del objeto.
- El modelo 3D se traslada en Z segun `AlturaRel`.
- `OffsetX`, `OffsetY` y `Giro` se aplican en coordenadas locales.
- El `Placement` posiciona y rota el conjunto completo en el documento.

Consecuencia legacy:

- Cambiar `AlturaRel` debe mover solamente el componente 3D dentro de la Shape compuesta.
- Cambiar `Placement.Base.z` mueve el conjunto compuesto.

En `PhysicalDocumentationA1`, verificado el 2026-09-03, `obj.Shape` contiene
solamente 3D fisico y PLAN es un `Part::Feature DocumentationOnly` separado,
controlado por `Owner`. Cambiar visibilidad o escala de PLAN no modifica
Volume, BoundBox ni Solids del dispositivo fisico.

## Objetos directos

La macro:

- `Deteccion/ColocarDetectores_NFPA.FCMacro`

crea actualmente sensores mediante `crear_toma_uno`, es decir, como objetos directos `Part::FeaturePython`. Despues asigna `AlturaRel`, `ModoVisual`, `Categoria`, `Placement` y ejecuta `touch()`.

Para estos objetos, cambiar `AlturaRel` y recomputar deberia reconstruir la geometria sin elevar el simbolo 2D.

## Objetos App::Link

La funcion `crear_toma_link` crea una instancia `App::Link` hacia un maestro oculto. El maestro se identifica mediante una combinacion de:

- Clave de registro.
- Tipo logico.
- Modo visual.
- Orientacion.
- Altura relativa.

La instancia recibe propiedades informativas como `Tipo`, `KeyRegistro`, `ModoVisual`, `AlturaRel` y `OrientacionPared`.

Regla vigente:

- Cambiar `AlturaRel` directamente en el enlace no garantiza que cambie la geometria si el enlace conserva el mismo maestro.
- La geometria fisica pertenece al `LinkedObject`.
- Los cambios de altura semantica en enlaces deben resolver o crear un maestro compatible y reasignar `LinkedObject` cuando corresponda.
- En A1, el master es fisico (`_A1Physical`) y no contiene symbol2D.
- PLAN se sincroniza como documentacion separada y no determina la identidad del master fisico.
- La ruta legacy permanece disponible para compatibilidad y no se migra automaticamente.

## Herramienta de altura y rotacion

Archivo:

- `Objetos/cambiar_altura_y_rotacion_objetos.FCMacro`

La version modernizada implementa tratamiento semantico por familia:

- ElectricCR directo: modifica `AlturaRel` y conserva el `Placement` base.
- ElectricCR `App::Link`: localiza o crea el maestro adecuado y relinka la instancia.
- HVAC MEP: utiliza la API existente de altura de instalacion.
- Objeto simple: conserva compatibilidad mediante `Placement.Base.z`.
- Rotacion: compone yaw sobre Z global conservando orientaciones tecnicas existentes.

Estado de esta herramienta:

- Implementada.
- Probada tecnicamente con FreeCAD 1.1.3 en la estacion utilizada por Codex.
- Version objetivo del proyecto: FreeCAD 1.1.3.
- Validacion visual y funcional de Marco con objetos reales todavia pendiente.
- Clasificacion provisional: `NUCLEO / CANDIDATA / PROMETEDORA`.

No debe promoverse a `ESTABLE / COMPROBADA` hasta completar la validacion funcional correspondiente.

## Referencia existente en MEPWorkbenchCR

Archivo principal revisado:

- `MEPWorkbenchCR/MEP/hvac/hvac_equipment.py`

El sistema HVAC maneja propiedades y funciones semanticas de altura de montaje y maestros compatibles. Este patron debe reutilizarse conceptualmente para ElectricCR, evitando copiar codigo sin revisar dependencias.

## Control de integracion de nuevas herramientas

ElectricCR adopta formalmente tres ejes de evaluacion:

1. Rol funcional.
2. Madurez.
3. Resultado comprobado.

Adicionalmente, durante la migracion se asigna una `Decision ElectricCR` independiente, registrada en `REVISION_MACROS.md`.

El inventario de herramientas utiliza estos ejes para distinguir herramientas productivas, candidatas, experimentales, duplicadas, incompletas, fallidas, abandonadas o pendientes de verificar.

Reglas vigentes:

- Una herramienta nueva no sustituye automaticamente una anterior.
- Una ejecucion correcta no equivale a validacion funcional.
- Un numero alto de ejecuciones puede provenir de pruebas o depuracion y no demuestra uso operativo.
- Los resultados negativos deben documentarse, no ocultarse.
- Las herramientas `FALLIDA`, `DESVIADA`, `DUPLICADA`, `INCOMPLETA` o `ABANDONADA` pueden conservarse temporalmente como evidencia o respaldo, pero no deben presentarse como mejoras productivas.
- Cuando no exista evidencia suficiente debe utilizarse `POR VERIFICAR`.

## Ciclo de vida adoptado

```text
CONTEXTO RECONSTRUIDO
  -> DEFINIDA
  -> IMPLEMENTADA
  -> PROBADA TECNICAMENTE
  -> VALIDADA FUNCIONALMENTE
  -> REVISADA POR GPT
  -> ACEPTADA
  -> INTEGRADA
```

La documentacion de cada tarea debe reflejar con precision en que etapa se encuentra. `HISTORIAL_CAMBIOS.md` se reserva para cambios aceptados.


## Estado 2026-09-05 21:50 America/Costa_Rica - A1 en modo seguro por rollback de overlay

Estado: **IMPLEMENTADO EN DRIVE / REQUIERE REINICIO Y VALIDACION EN FREECAD 1.1.3 / A1 OPT-IN**.

- `plan_selection.py` v0.4.0: solo redireccion PLAN -> Owner; overlay `ghostTracker` descartado por Access violation y residuos graficos.
- `plan_live_sync.py` v0.4.0: sin refresco de overlay; conserva recompute dirigido del PLAN.
- `objeto_toma_uno.py` rev O: PLAN se mantiene auxiliar y fuera de grupos de usuario; `sync_plan_representation()` limpia pertenencia accidental a grupos.
- `ShowInTree=False` se conserva.
- Rectangle009 y Rectangle010 ausentes por borrado intencional de prueba, no por fallo del lifecycle.
- Multiparentalidad Owner bajo `Wall` + `Apagadores BIM` sigue pendiente y no se toca en este cierre.
