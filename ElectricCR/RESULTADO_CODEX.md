## Validacion de Marco - 2026-09-14 21:26 -0600 - ElectricCR / Objetos / Alinear en planta v0.2

Marco probo la version v0.2.0 en FreeCAD 1.1.3 y confirma: **FUNCIONA**. La validacion corresponde al uso real posterior a la ampliacion para aceptar cara plana como referencia. Por tanto, queda demostrada funcionalmente la correccion planar del objeto usando una cara lateral plana: ajuste X/Y y giro alrededor de Z sin redisenar la herramienta ni sustituir `Objetos/Alinear.FCMacro`.

Esta confirmacion no documenta una prueba explicita de Undo/Redo, guardado/reapertura ni una matriz completa de referencias; esos puntos permanecen sin afirmar. Clasificacion actual: OPERATIVA / CANDIDATA / COMPROBADA-PARCIAL, con validacion funcional real del caso probado.

---

## Trabajo GPT - 2026-09-14 21:26 -0600 - ElectricCR / Objetos / Alinear en planta v0.2

> Trabajo directo de GPT en Google Drive; no atribuir a Codex.

**ACTUALIZADA EN DRIVE / SINTAXIS Y MATEMATICA DE PROYECCION APROBADAS / PRUEBA REAL FREECAD 1.1.3 PENDIENTE.**

Se amplio `Objetos/Alinear_En_Planta.FCMacro` en su mismo archivo de Drive, de v0.1.0 a v0.2.0, para aceptar como segunda referencia una **arista recta** o una **cara plana**. El icono y la integracion de barra permanecen sin cambios; `Objetos/Alinear.FCMacro`, `InitGui.py`, `config.json`, A1 y Tableros no se modificaron.

Con arista se conserva el algoritmo anterior: proyeccion ortogonal de `Placement.Base` sobre la recta XY y menor giro global Z usando el eje local X/Y mas cercano. Con cara, la macro toma normales en varios puntos del dominio parametrico para rechazar superficies curvas, obtiene la direccion en planta como interseccion del plano de la cara con XY y proyecta el punto de insercion al plano modificando solo X/Y. La componente Z original se conserva incluso para una cara plana inclinada. Una cara horizontal se rechaza porque su normal no define direccion XY util.

La seleccion de referencia ahora distingue explicitamente subelementos `Edge` y `Face`. Como conveniencia, un objeto completo con una sola cara se acepta como cara y uno con una sola arista se acepta como arista; geometria con multiples subelementos requiere seleccionar explicitamente la cara/arista deseada. Se mantienen las guardas de contenedores con transformacion XY, transaccion propia, rollback y trazas `[OBJ-ALIGN]`.

Verificacion fuera de FreeCAD: compilacion Python PASS. Pruebas matematicas aisladas PASS para plano vertical X constante, plano vertical Y constante y plano inclinado `x+z=const`, verificando que Z permanece inalterado; el caso horizontal se rechaza por no admitir proyeccion XY. El archivo re-leido de Drive mide 16.169 bytes y su SHA-256 es `41064649bdedc88e54d86c5ae3102727da1beae229b3c601ac6e9e3e1c439184`, identico al generado.

Pendiente obligatorio: prueba real en FreeCAD 1.1.3 con al menos (a) tablero + arista de muro y (b) tablero + cara lateral plana de muro, incluyendo cara de muro inclinada en planta si esta disponible; verificar posicion XY, giro esperado, Z inalterado, Undo/Redo, guardado/reapertura y mensajes de consola. La herramienta sigue **OPERATIVA / CANDIDATA / POR VERIFICAR** hasta esa validacion. No se actualiza HISTORIAL_CAMBIOS ni se publica en GitHub en esta etapa.
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

## Resultado Codex - 2026-09-14 07:46 -0600 - A1 Undo / PLAN Lifecycle

**CORRECCION PROBADA EN FREECAD 1.1.3: regresion final PASS. A1 intacto. Sin commit/push.**

Se reprodujo Access violation dos veces al deshacer la creacion de Demo. Causa demostrada: las guardas usaban metodos C++ inexistentes en Python y silenciaban AttributeError. Con `Transacting=True`, lifecycle encolaba y eliminaba PLAN dentro del replay nativo (14 entradas en dos Undo). FreeCAD devolvia incluso con documento vacio, pero registraba Access violation posteriormente; no se considero PASS.

Cambio minimo en `electriccr/features/plan_lifecycle.py` y `plan_live_sync.py`: usar los atributos booleanos Python `Transacting` / `HasPendingTransaction`. Lifecycle vacia su cola existente tambien en `slotBeforeRecomputeDocument`. Ese callback se justifico al detectar que Std_Delete recomputa antes de cerrar su transaccion: el intento intermedio daba error Placement con Owner ya borrado y PLAN aun pendiente. La evidencia de ese FAIL se conserva. Sin nuevos timers ni redisenos.

FreeCAD 1.1.3 revision 20260725, DESKTOP-5586S7P, pruebas 07:32-07:46. Resultado: 19 etapas PASS; creacion 2 Spaces/5 walls/7 Owners/7 PLAN, movimiento con entrada Undo independiente, Undo/Redo de movimiento, Delete/Undo/Redo del par, rollback antes/despues del flush, Undo/Redo de creacion completa, guardar/cerrar/reabrir y movimientos en BIM/Draft/Part. Seleccion PLAN hacia Owner unico comprobada. Smoke original sin cambios e Undo/Redo completo sin instrumentacion tambien PASS; vista vacia sin graficos residuales tras Undo. Observers restaurados sin wrappers y cero documentos temporales abiertos.

Consola final: cero Access violation, errores Placement, unknown opcode o traceback; dos avisos nativos `TopoShapeExpansion.cpp(983): hasher mismatch` en Redo, sin fallo de integridad/persistencia observado. Se registran sin ampliar alcance. La traza final tiene cero encolados/flush de lifecycle durante replay.

Movimiento: asignar Placement sin abrir transaccion reprodujo cambio de posicion sin nueva entrada Undo; con transaccion explicita se verifica la entrada propia y el replay correcto. El gesto historico exacto no quedo registrado, por lo que no se atribuye a Draft Move ni seleccion. El smoke existente ya usaba transaccion y quedo intacto.

[Causa, matriz, consola previa/intermedia/final, fuentes nativas y diff](tests/evidence/2026-09-14_a1_undo_lifecycle/README.md). Fuentes actuales y hashes previos preservados, sin descartar cambios locales ni consultar Git. Nuevas pruebas: `tests/freecad_a1_transaction_probe.py` y `tests/freecad_a1_lifecycle_regression.py`; compilacion PASS. Seleccion, fabrica, Demo, auditor, smoke e InitGui sin cambios verificados. Metadata ya estaba corregida; no se reimplemento. No se tocaron IFC, Upala, registry, masters u otras herramientas.

Documentacion actualizada: RESULTADO_CODEX, ESTADO_PROYECTO, TAREA_ACTUAL, evidencia y sesion Memoria_FreeCAD. Clasificacion NUCLEO / CANDIDATA / COMPROBADA-PARCIAL: correccion tecnicamente verificada, pendiente revision/aceptacion; no RELEASE automatica. No requiere cambio de MAPA_WORKBENCH/REVISION_MACROS. HISTORIAL_CAMBIOS intacto. Trabajo detenido al terminar pruebas y documentacion.

---

## Resultado Codex - 2026-09-13 16:49 -0600 - Recuperar Tasks

**Prueba tecnica GUI FreeCAD 1.1.3: PASS. Sin cambios de codigo funcional. Panel negro no reproducido; no se declara resuelto.**

Se reconstruyo el estado real leyendo instrucciones, conciliacion vigente y fuentes locales. La prioridad actual es validar Programacion / Recuperar Tasks, implementado previamente por GPT; Undo Demo A1 / PLAN Lifecycle es independiente. `_create_metadata()` ya usa `App::FeaturePython`; se confirmo su hash sin cambios y no se rehizo esa correccion. Las skills de arquitectura y memoria estan disponibles en este equipo.

Pruebas por MCP en DESKTOP-5586S7P, 16:41-16:46, FreeCAD 1.1.3 / revision 20260725, Python 3.11.14 y Qt/PySide6 6.8.3. FreeCAD estaba cerrado y se inicio automaticamente; MCP conecto al tercer intento. Dos documentos temporales, 28 ejecuciones: creacion del escenario, seleccion/vista/datos conservados, tarea Sketch nativa preservada, diez pulsaciones y seis alternancias A/B con recuperacion antes/despues. Cinco docks constantes, cero duplicados y 897 widgets constantes durante los diez ciclos. Auditoria antes/despues y revision visual del escritorio realizadas. Ambos documentos cerrados sin guardar; visibilidad inicial de Tasks restaurada.

Fuente cargada: carpeta local Programacion vigente, macro v0.1.0 y toolbar v1.1.0. Compilacion PASS; una barra y nueve botones, Recuperar Tasks unico. Hashes de macro, toolbar, helper, auditor y SVG identicos antes/despues. Se conservaron los demas botones, sin ejecutar sus funciones ajenas al alcance.

Consola: 28 BEFORE/AFTER/RESULT, cero ERROR/WARNING del recuperador. Error separado de arranque a las 16:39:25 en FacilArquitecturaWB/InitGui.py: `attempted relative import with no known parent package`; no investigado. Limitacion confirmada: `tab=unknown` con Model/Tasks como docks separados; la visibilidad se mantuvo en la prueba. No se demostro una regresion que justifique cambiar codigo.

[Matriz, consola, hashes y capturas](tests/evidence/2026-09-13_tasks_recovery_gui/README.md). Solo se agregaron evidencia de pruebas y documentacion, y se actualizo Memoria_FreeCAD (sesion y equipo, conservando el registro anterior). No se tocaron IFC, Upala ni Git. No se modifican MAPA_WORKBENCH, REVISION_MACROS o HISTORIAL_CAMBIOS; no hay nueva funcionalidad ni aceptacion para RELEASE.

Clasificacion: SOPORTE / CANDIDATA / COMPROBADA-PARCIAL; PROBADA TECNICAMENTE / VERIFICADO_MCP / VERIFICADO_VISUAL del mecanismo. Complementa la auditoria existente. Pendiente de Marco: validar durante una reproduccion real del panel negro. Undo Demo A1 / PLAN Lifecycle sigue pendiente por separado. Se detiene el trabajo tras probar y documentar, sin ampliar alcance.

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

## Trabajo GPT - 2026-09-10 17:54 -0600 America/Costa_Rica - Programacion / Recuperar panel Tasks

> Esta entrada corresponde a trabajo directo de GPT en Google Drive; no es resultado de Codex.

Marco autorizo una herramienta paliativa y diagnostica para el fallo visual asociado a Combo View / Tasks al cambiar entre documentos. Antes de implementar se reviso la barra Programacion vigente, `programacion_common.py`, `AuditarInterfazFreeCAD.FCMacro`, `UI_Audit_FreeCAD.FCMacro` y la auditoria runtime previa. Se confirmo en la API de FreeCAD que `ControlPy` expone `activeDialog()`, `showModelView()` y `showTaskView()`.

Cambios en Drive:

- nuevo `Programación/RecuperarPanelTareas.FCMacro` v0.1.0;
- nuevo `Programación/RecuperarPanelTareas.svg`;
- `Programación/programacion_toolbar.py` v1.1.0, misma identidad de archivo, con `Programacion_RecoverTasks` insertado junto a `Programacion_UIAudit`;
- no se modificaron las macros de auditoria existentes.

La recuperacion registra BEFORE/AFTER y diferencias de documento, MDI, TaskDialog, centralWidget, pestaña Model/Tasks, todos los docks, geometria/tamanos y duplicados. La accion usa `showModelView()`, actualizacion GUI/event loop y vuelve a `showTaskView()` solamente cuando el estado previo lo requiere. No usa `closeDialog`, `resizeDocks`, `restoreState`, `setCentralWidget`, `splitDockWidget`, destruccion/reparenting de docks ni operaciones sobre objetos de documento.

Verificacion GPT: compilacion sintactica PASS sobre los bytes finales re-leidos desde Drive; inspeccion de guardas PASS; comando nuevo aparece una sola vez en el manifiesto. **FreeCAD 1.1.3 GUI no fue ejecutado desde este entorno**, por lo que quedan pendientes la prueba de dos documentos, TaskDialog nativo, 10 ciclos y la comprobacion durante el panel negro real. No se declara resuelto el defecto visual.

---

## Demo ElectricCR A1 v0.1 - 2026-09-09 22:39 -0600 America/Costa_Rica

**PRUEBA REAL FAIL; PRIMER FALLO REPRODUCIDO; SIN MODIFICAR CODIGO.** A1 aprobado permanece sin cambios.

Se ejecuto `tests/freecad_electric_demo_smoke.py` original en FreeCAD 1.1.3 (2026-09-09T22:37:32.318785-06:00). Falla en `electriccr/demo/electric_demo_freecad.py:100`, `_create_metadata`: `doc.addObject("App::Feature", "ECR_Demo_Metadata")` produce `TypeError: Document::addObject: 'App::Feature' is not a document object type`. La misma llamada en un documento vacio reprodujo el error.

La demo se cierra al fallar antes de crear edificio, Oficina, Bodega, muros o dispositivos. No se alcanzaron auditoria 7/7, movimiento, Undo/Redo, Delete, save/reopen ni comprobacion visual. No aprobar esas etapas. Todos los documentos de esta prueba quedaron cerrados.

Resultado, traceback y consola: [evidencia del primer fallo](tests/evidence/2026-09-09_electric_demo_v01_first_failure/README.md). El registro distingue un KeyError previo de preparacion (Workbench no registrado; test luego importado directamente) del fallo real reproducido. No se hicieron cambios de codigo, IFC, apertura de Upala, reparaciones, commit/push ni diagnostico de fallos posteriores.

---

## Trabajo GPT - 2026-09-09 22:09 -0600 America/Costa_Rica - implementacion Drive de Demo ElectricCR A1 v0.1

> Esta entrada corresponde a trabajo directo de GPT; no es resultado de Codex.

Marco autorizo la implementacion de una Demo/Macro de pruebas autocontenida. Se investigo y reutilizo el patron de la Demo Casa de 2 Plantas de Facil Arquitectura: nucleo puro reproducible, adaptador FreeCAD y diagnostico separado. Tambien se verifico en la API oficial de FreeCAD 1.1.3 que `Arch.makeSpace()` acepta un objeto solido como Base y que `Arch.makeWall()` crea muros parametrizados a partir de una geometria base; no se implementaron versiones propias de Space o Wall.

Se implemento en Drive:
- `electriccr/demo/electric_demo_core.py` v0.1.0: escenario fijo JSON-compatible y UIDs UUIDv5 deterministas;
- `electriccr/demo/electric_demo_freecad.py` v0.1.0: documento nuevo, Building/Level, Spaces, Walls y 7 Owners A1 usando servicios existentes;
- `electriccr/demo/electric_demo_audit.py` v0.1.0: auditor read-only de UID, Owner/PLAN, master, Placement, Space, Host, snaps y huerfanos;
- `commands/demo_electriccr.py`: comandos crear/auditar;
- `Demo_ElectricCR_A1.FCMacro`: lanzador pequeno;
- `tests/test_electric_demo_core.py`;
- `tests/freecad_electric_demo_smoke.py`: regresion real preparada;
- `InitGui.py`: registro de los dos comandos en menu/barra ElectricCR.

Resultado verificable en el entorno GPT:

```text
pytest test_electric_demo_core.py   7 passed
py_compile                         PASS
FreeCAD 1.1.3 real                PENDIENTE
```

La demo no implementa todavia IFC, Circuit como entidad, Control como entidad ni randomizacion. `CircuitoID` se usa solo como dato de compatibilidad para que el escenario empiece a ejercer la semantica existente sin fijar una arquitectura de circuito aun pendiente.

No se modificaron A1, PLAN, lifecycle, selection, live sync, masters ni `registry_electric.json`. No se toco ningun FCStd productivo y no se hizo commit/push.

---

## Trabajo GPT - 2026-09-09 22:09 -0600 America/Costa_Rica - investigacion del adaptador IFC A1

> Esta entrada corresponde a trabajo directo de GPT en Drive; no es resultado de Codex.

Se amplio la investigacion posterior al experimento NativeIFC de cuatro elementos sin modificar codigo productivo. La conclusion provisional es conservar A1 como autoridad de diseno y estudiar NativeIFC/IfcOpenShell como capa transitoria de exportacion/interoperabilidad.

Puntos demostrados por lectura del codigo FreeCAD 1.1.3 y coherentes con el experimento real previo:
- NativeIFC puede crear productos IFC desde objetos FreeCAD y reutiliza actualmente el exportador Arch para construir la representacion geometrica;
- `ObjectPlacement` puede derivarse del `Placement` FreeCAD;
- el exportador puede operar sobre un `ifcopenshell.file` ya existente y devuelve las entidades creadas, habilitando resolver `Device.Space` contra el `IfcSpace` del mismo archivo;
- FreeCAD puede conservar/generar GUID IFC; para ElectricCR se recomienda evaluar `GlobalId` determinista derivado de `ElementUID` para evitar dos identidades independientes;
- NativeIFC soporta Psets editables, aunque cantidades/Qto conservan limitaciones/TODO;
- el contexto `Plan` existe, pero PLAN A1 no debe exportarse como segundo dispositivo electrico.

Riesgo principal: convertir/agregar directamente un Owner A1 a NativeIFC puede reemplazar/eliminar el objeto FreeCAD original dependiendo de `KeepAggregated`. Por ello no se recomienda probar esa ruta en modelos productivos.

Tambien se detectaron deudas semanticas del registro para una fase futura: `Telecom_TV` usa `IfcCommunicationsOutlet` y debe revisarse contra la taxonomia IFC vigente; `Luminaria 60x60` y `Sensor_Humo` no tienen clase IFC en el registro. No se modifico el registro en esta fase.

Se propone como siguiente instrumento de validacion una macro/demo autocontenida de ElectricCR, analoga a la Demo Casa de 2 Plantas, que genere un escenario reproducible para probar elementos A1, Space y exportacion IFC. No se genero codigo porque requiere autorizacion expresa de Marco.

---

## Resultado vigente - 2026-09-09 20:02 -0600 America/Costa_Rica

**A1 = APROBADO PARA CONTINUAR. Cierre GitHub completado. Experimento NativeIFC de cuatro elementos completado.**

A1 cerrado en GitHub: [4a9ade9](https://github.com/MVM444/Macros-de-Freecad/commit/4a9ade9645d9227ac5323676ee911c972502e869), constancia [285d5a7](https://github.com/MVM444/Macros-de-Freecad/commit/285d5a74b6463dc859d0bc0a940b2879aa6c4c2a), rama `codex/cierre-a1-20260909`; ambos pushes confirmados, staging limpio. Se separaron cambios ajenos y la evidencia publica se anonimizo conforme AGENTS. No merge a main ni release Addon. DEV funcional sin cambios.

NativeIFC real en FreeCAD 1.1.3/IfcOpenShell 0.8.4, 2026-09-09T09:21:49.645609-06:00 a 2026-09-09T09:22:33.267892-06:00: esquema **IFC4**; exactamente IfcOutlet, IfcSwitchingDevice, IfcLightFixture e **IfcElectricDistributionBoard**. Son Part::FeaturePython; Class=IfcClass, GlobalId unico, StepId 23/39/55/71, Type=None (propiedad App::PropertyLink). Cuatro IfcElement y un IfcProject de infraestructura; sin Upala ni conversiones existentes.

| Clase | PredefinedType inicial | Plantillas Pset aplicables | Edicion / FCStd+IFC / reabrir IFC |
| --- | --- | --- | --- |
| IfcOutlet | POWEROUTLET | 10 | APROBADO |
| IfcSwitchingDevice | TOGGLESWITCH | 12 | APROBADO |
| IfcLightFixture | POINTSOURCE | 10 | APROBADO |
| IfcElectricDistributionBoard | DISTRIBUTIONBOARD | 11 | APROBADO |

Todos nacieron sin Psets adjuntos. Se editaron etiqueta/descripcion, PredefinedType=USERDEFINED, ObjectType=ProbeDevice, Placement/giro15 grados y un Pset simple (before -> after). Persistieron GUIDs, StepIds, atributos, Placement y Pset tras guardar IFC+FCStd, cerrar/reabrir FCStd y reabrir el IFC. Consola sin excepciones. Capturas revisadas; cuatro mallas/superficies, Shape no nula y 0 solidos. Prueba mediante propiedades Python nativas/callbacks reales; no se afirma edicion manual del panel ni autonomia FCStd sin companero IFC.

| Alternativa | Evidencia a favor | Limite / decision provisional |
| --- | --- | --- |
| 1. NativeIFC como nucleo | Clase, GlobalId, atributos IFC, Placement y Pset editados/persistidos nativamente en las cuatro clases. | No adoptar todavia: no se probo edicion colectiva por Type, rendimiento, documentos grandes ni equivalencia con App::Link. |
| 2. NativeIFC como capa/adaptador alrededor de A1 | Permite estudiar semantica/intercambio IFC conservando el A1 aprobado. | **Opcion recomendada para el siguiente diseno exploratorio**, sin implementar aun. Definir primero una sola autoridad para identidad, Placement y propiedades. |
| 3. Hibrida | Los mapas IFC pueden compartir representacion, mientras A1 conserva su autoría y documentacion. | Hipotesis pendiente; duplicar motores introduce sincronizacion y persistencia adicionales. No hay integracion validada. |


IFC/IfcOpenShell y NativeIFC ofrecen RepresentationMaps/IfcMappedItem al asignar un Type con mapas, pero NativeIFC usa Part::FeaturePython y Shape por objeto; **no se demostro equivalencia de rendimiento ni funcionamiento con Master + App::Link**. Type=None en los cuatro: no se crearon ocurrencias extra. Desasignar Type y Psets no simples tienen limites visibles en codigo; no se probaron esas rutas. La recomendacion de opcion2 es para estudio posterior, no una integracion aprobada. Fuentes primarias y distincion entre hecho/prueba/inferencia en el reporte.

Evidencia completa, GlobalId/Placement/Psets por elemento, hashes y limites: [reporte NativeIFC](tests/evidence/2026-09-09_nativeifc_four_elements/README.md), [results.json](tests/evidence/2026-09-09_nativeifc_four_elements/results.json). Modelos desechables en `C:\Users\marco\AppData\Local\Temp\ecr_nativeifc_four_20260909`; documentos cerrados. Helper nuevo: tests/freecad_nativeifc_four_elements_probe.py. Se preservaron hashes de los13 archivos A1 revisados; no se modificaron PLAN, lifecycle, seleccion, masters o produccion.

Documentacion actualizada: resultado, estado, tarea y memoria. NativeIFC queda **SOPORTE / EXPERIMENTAL / COMPROBADA-PARCIAL**. Sin integracion A1-NativeIFC, puertos ni cambios arquitectonicos. Esta fase nueva permanece local y no se mezcla con el cierre A1 publicado. Entradas inferiores historicas.

---

## A1 GitHub closure confirmed - 2026-09-09T09:16:00.625279-06:00

Commit: `4a9ade9645d9227ac5323676ee911c972502e869`.
Branch: `codex/cierre-a1-20260909`.
Remote: https://github.com/MVM444/Macros-de-Freecad . Push: **SUCCESS**, upstream configured and remote branch created.

26 files: approved A1 implementation/dependencies, generic tests, documentation and anonymized evidence. No new functionality. Unrelated door-side hunks and other local work excluded. Public documentation retains history with neutralized local references; complete DEV records retain their identity/location. No merge to main or Addon release performed.

---

## Cierre vigente A1 - 2026-09-08 17:49 -0600 America/Costa_Rica

**A1 = APROBADO PARA CONTINUAR**, con ElectricCR inicializado una vez por sesion. Seleccion, movimiento, giro y Delete/Undo/Redo funcionan tambien con BIM, Draft y Part activos. Correccion minima implementada y validada en FreeCAD 1.1.3 real; no implica aceptacion definitiva de otros pendientes ni cambia el opt-in A1.

Esta entrada sustituye el bloqueo de ruta de las 12:32 y los planes historicos de feedback de septiembre 5. El usuario corrigio la fuente a `C:\Users\marco`; el archivo actual ya no es la copia antigua con siete PLAN huerfanos. Los apartados inferiores se conservan como historia, no como instrucciones vigentes. No reintroducir ghostTracker.

### Fuente protegida y entorno

- Original: `C:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Sucursales\Upala\1416 Levantamiento 250424 Compu D.FCStd`.
- 1363006 bytes; fecha de archivo 2026-09-08 09:44:46 -06:00; SHA256 `F5E1A372D162F02E5D91CD874F47A13B412380972F0604E27D9D77D71E87077F` antes y despues.
- Copia verificada para pruebas: `C:\Users\marco\AppData\Local\Temp\ecr_a1_acceptance_20260908_5_mtcyyd\A1_workbench_regression.FCStd`. Original nunca guardado ni modificado.
- FreeCAD 1.1.3, revision 20260725, commit 145529fe741292ff0b3977a01195bf0247425794, Windows DESKTOP-5586S7P. Regresion final 2026-09-08T17:36:24.420274-06:00 a 2026-09-08T17:44:52.151735-06:00, en sesion GUI reiniciada con el codigo cargado normalmente.
- Evidencia durable: [tests/evidence/2026-09-08_a1_workbench_runtime/README.md](tests/evidence/2026-09-08_a1_workbench_runtime/README.md), con resultados JSON, consola, capturas y delta exacto de codigo.

### Causa demostrada y correccion

Se revisaron primero InitGui.py, ui/plan_selection.py, electriccr/features/plan_live_sync.py y plan_lifecycle.py. Initialize ya instalaba lifecycle y live sync como observers de documento; ambos seguian activos al salir de ElectricCR. Activated instalaba el redirector de seleccion y Deactivated lo desinstalaba explicitamente. La matriz nativa anterior al cambio confirma que solo ese servicio desaparecia en BIM/Draft/Part.

Consecuencia reproducida en copia: con Part activo, seleccionar PLAN y ejecutar Std_Delete borraba solo PLAN. Quedaban 10 Owners y 9 PLAN; auditoria `owner_without_plan` y `owner_without_linked_plan`. Undo restauraba el par. Es un fallo GUI con consecuencia de integridad (Owner sin PLAN); no se demostro un PLAN huerfano nuevo por este mecanismo. El borrado directo de Owner seguia eliminando ambos porque lifecycle permanecia instalado. No es corrupcion persistida de binding y no se reconstruyo ningun PLAN existente.

Delta funcional exclusivo de esta tarea:

1. `InitGui.py`: instalar seleccion tambien al Initialize y conservarla en Deactivated; paneles/barras siguen su ciclo GUI habitual.
2. `ui/plan_selection.py` v0.4.1: install idempotente, reutiliza singleton; uninstall queda solo para mantenimiento/recarga explicita. Filtros y seleccion unica de Owner conservados.
3. `electriccr/features/plan_live_sync.py` v0.4.1: corregir import de normalizacion de arbol a `ElectricCR.ui`, ruta real del paquete.

`plan_lifecycle.py`, fabrica A1, contrato, propiedades, expresion canonica, Host/Space/puerta y ClaimHosted no se modificaron en este delta. Los archivos funcionales ya tenian trabajo previo sin commit; `changes.patch` separa exactamente este cambio. Se reutilizaron observers y comandos nativos existentes: REUTILIZAR App.addDocumentObserver/Gui.Selection.addObserver, Std_Delete/Undo/Redo y Draft.move/rotate; EXTENDER solo duracion e idempotencia del adaptador de seleccion. No se creo otro runtime ni se repitio investigacion amplia.

### Auditoria y regresion real

| Comprobacion | Resultado |
| --- | --- |
| Inventario actual inicial y final tras reapertura | 10 Owners App::Link / 10 PLAN Part::Feature |
| Unico dispositivo nuevo de prueba | 11/11; vuelve a 10/10 al eliminarlo |
| UID, master, contrato, referencias reciprocas, schema=2, DocumentationOnly, Owner hidden, expresion y Placement real | APROBADO |
| Huerfanos, Owners sin PLAN, duplicados UID/claims/PLAN, enlaces cruzados, expresiones rotas, estados Invalid/Error | 0 en todas las etapas posteriores al cambio |
| PLAN -> Owner existente en ElectricCR/BIM/Draft/Part | APROBADO; solo Owner seleccionado |
| BIM: mover/girar, guardar, Delete/Undo/Redo/Undo, mover, save/close/reopen | APROBADO |
| Draft: seleccionar, mover/girar, Delete/Undo/Redo/Undo, save/close/reopen | APROBADO |
| Part: seleccionar, mover/girar, Ambos/Solo2D/Solo3D, Delete/Undo/Redo | APROBADO |
| Part: clic real sobre PLAN, guardar/cerrar/reabrir, repetir movimiento y Delete/Undo/Redo | APROBADO |
| Reapertura final sin sonda, auditar y cerrar | APROBADO; 10/10 |
| PLAN acompana antes de recompute global | APROBADO; XY, Z documental y giro |
| Instalacion repetida, cambio de WB/documento, ShowInTree=False, fuera de grupos | APROBADO; mismos tres singletons |
| Valores serializados de todos los Owners existentes, incluido Placement/Host/Space/puerta | Iguales al original |
| Graficos residuales tras Delete / PLAN duplicados o huerfanos | 0 observados |

El nuevo movimiento tras Undo invalido Redo (RedoCount=0); Redo del borrado se probo antes de ese nuevo movimiento y en secuencias nuevas validas. No hubo reparacion, sync o reconstruccion despues del replay. Girar se verifico en las rotaciones reales Owner/PLAN (0, 25, 40, 65, 90, 115 grados). Movimiento y giro se ejecutaron con API Draft sobre la seleccion GUI; clic fisico de PLAN comprobado ademas con raton en Part. Capturas de la misma vista demuestran desaparicion y retorno tras Undo; PLAN no figura como segundo dispositivo del arbol.

Consola: cero `No attribute named 'Placement'`, cero Access violation y cero errores de recompute A1 observados. Se conserva consola completa: hubo errores del instrumento de prueba (consulta CenterOfMass inexistente, dos comparaciones de estado transitorio y una ruta de importacion corregida). No se presentan como errores del producto ni se ocultan. El mensaje lifecycle «removed orphan PLAN after owner deletion» describe su eliminacion dentro del ciclo de borrado; las auditorias no dejan huerfanos.

El primer cierre estricto detecto solo State/status Touched. Se demostro con recompute -> auditoria -> recompute que lecturas/evaluacion nativa del auditor activan esos marcadores y un recalculo de 22 features los limpia. La comparacion final excluye solamente State/status; sigue rechazando Invalid/Error y conserva todos los demas campos. Comparacion XML independiente: valores y definiciones de todas las propiedades Owner sin cambios; solo difieren atributos nativos status. No se modifico codigo de produccion para este ajuste del instrumento.

### Archivos y limites de aprobacion

Nuevos helpers reutilizables: `tests/freecad_a1_runtime_audit.py` (inventario sin asignaciones/reparaciones) y `tests/freecad_a1_runtime_regression.py` (copia verificada, secuencia controlada). Sintaxis AST validada en estos dos y los tres archivos funcionales; revision independiente del delta y de los resultados sin hallazgos bloqueantes. Documentacion actualizada en sus ubicaciones: RESULTADO_CODEX.md, ESTADO_PROYECTO.md, TAREA_ACTUAL.md y Memoria_FreeCAD/sesiones/2026-09-08_electriccr-a1-runtime-workbench_DESKTOP-5586S7P.md.

Alcance aprobado: contrato A1 actual, despues de inicializar ElectricCR una vez en cada sesion de FreeCAD. No se promete runtime antes de esa inicializacion. El auditor reconoce Owners por contrato A1; la perdida simultanea de contrato y PLAN anterior al inventario inicial requeriria otra fuente de identidad. Los guards preexistentes de lifecycle/live sync invocan metodos hasPendingTransaction()/isPerformingTransaction() ausentes en 1.1.3 (expone HasPendingTransaction/Transacting); no se atribuye la aprobacion a esos guards. No fueron modificados: las operaciones reales probadas aprobaron y no justifican una ampliacion arquitectonica.

Pendientes no bloqueantes y fuera de esta tarea: feedback persistente PLAN, NativeIFC/IFC electrico, arbol semantico y doble aparicion Wall/electrico, ClaimHosted, relacion historica Rectangle006, orientacion en muros inclinados. Rectangle009/010 no se reportan como perdida accidental. A1 conserva una unica identidad/autoridad espacial en Owner; PLAN es auxiliar documental reconstruible.

Clasificacion: servicio estructural A1 existente, corregido localmente y validado funcionalmente por Codex en FreeCAD 1.1.3; listo para continuar desarrollo dentro del alcance anterior. Sin commit ni push. Drive sigue siendo fuente de verdad; cambios locales autorizados, sin afirmar sincronizacion Drive no verificada. HISTORIAL_CAMBIOS no se actualiza como aceptacion definitiva de Marco.

---
## Auditoria A1 actual - 2026-09-08 12:32 America/Costa_Rica

Estado: PENDIENTE DE ACCESO AL MODELO ACTUAL. No es una regresion actual demostrada ni un dictamen negativo sobre A1.

La instruccion vigente sustituye el diagnostico de la copia antigua por una auditoria de cierre del modelo ya validado manualmente por Marco. Objetivo: FreeCAD 1.1.3; correspondencia Owner/PLAN 1:1 y regresion controlada de un dispositivo nuevo mediante Std_Delete, Undo, Redo y guardar/cerrar/reabrir. No modificar codigo si pasa; detenerse ante una regresion actual reproducible.

Fuente actual indicada por el usuario:
`C:\Users\mmfallas\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Sucursales\Upala\1416 Levantamiento 250424 Compu D.FCStd`

Esa ruta no existe en este host (`DESKTOP-5586S7P`, usuario `marco`). Se solicito la ubicacion accesible de la version validada. La copia local homonima bajo `C:\Users\marco` conserva fecha 2026-09-05 22:02:29, 1345428 bytes y SHA-256 `2522F5F33E7D86ABEB3EBE6737AE5B63EC6DAF7A4C38750309B4B8D49A00E91E`; corresponde al estado antiguo y NO se utiliza para decidir la estabilidad actual.

Evidencia actual disponible:

- Prueba manual declarada por el usuario: crear, guardar, Delete de Owner+PLAN, Undo enlazado, Redo, guardar, cerrar y reabrir: APROBADA.
- Inventario independiente del modelo actual: NO EJECUTADO; cantidades Owners/PLAN e inconsistencias actuales: NO DISPONIBLES.
- Regresion independiente sobre copia del modelo actual: NO EJECUTADA por falta de la fuente.
- Errores de consola actuales: NO EVALUADOS. No se extrapolan los errores historicos.
- FreeCAD 1.1.3 local fue identificado en el diagnostico previo: revision 20260725, commit 145529fe741292ff0b3977a01195bf0247425794.

Preparacion completada sin cambiar produccion: revision acotada de la fabrica, observers y pruebas existentes; auditor read-only preparado en `%TEMP%\ecr_plan_diagnosis_20260908\audit_current_a1.py`. Para crear el unico dispositivo se reutilizara `crear_toma_link(... separate_documentation=True, recompute=False)`, `ensure_device_semantics(... manage_transaction=False)` y `sync_plan_representation(... manage_transaction=False)` en una transaccion. El Delete se probara con `Std_Delete`, no con una funcion que borre manualmente ambos objetos. Tras Undo/Redo se recuperaran los objetos por nombre y no se ejecutaran reparaciones que oculten regresiones. Redo inmediato se verifica antes de mover; un movimiento nuevo tras Undo invalida el Redo anterior.

Evidencia historica separada: el diagnostico previo en una copia temporal confirmo siete PLAN con Owner=None, Placement legible y fallo tambien al evaluar de nuevo Owner.Placement; los Owners ya no estaban. No demuestra corrupcion de binding ni un fallo vigente del modelo validado. Se conserva el reporte temporal `readonly_report.json`; no se reparo nada. Rectangle009/010 fueron borrados intencionalmente y no se reportan como perdida accidental.

Archivos funcionales modificados: NINGUNO. Originales y respaldos no modificados. Documentacion de esta pausa: RESULTADO_CODEX.md, ESTADO_PROYECTO.md y TAREA_ACTUAL.md en sus ubicaciones existentes. Sin commit/push. Los cambios documentales se realizan localmente; no se afirma una sincronizacion Drive no verificada.

Conclusion: falta la fuente actual para emitir `A1 = APROBADO PARA CONTINUAR` o demostrar una regresion actual. El estado antiguo no justifica declarar `A1 = NO APROBADO`.

---
## Trabajo GPT 2026-09-05 21:01 - feedback PLAN persistente y diagnostico nativo del arbol

> Trabajo directo de GPT en Drive; no atribuir a Codex.

### Feedback PLAN

La prueba real de Marco demostro que `Gui.Selection.setPreselection(PLAN, "")` resalta el PLAN completo pero deja de hacerlo cuando cambia la preseleccion del cursor. Se reutilizo `draftguitools.gui_trackers.ghostTracker` de FreeCAD 1.1.3 como overlay Coin temporal, sin seleccionar PLAN logicamente.

Implementado:
- `plan_selection.py` v0.3.0: overlay persistente completo, unpickable, GUI-only; Owner unica seleccion; PLAN `ShowInTree=False` cuando se soporta; cleanup al deseleccionar/salir del Workbench.
- `plan_live_sync.py` v0.3.0: refresca overlay despues de Placement/giro/visibilidad y al activar documentos.

### Multiparentalidad

El arbol de Upala confirma `TreeParents=[Wall, Apagadores BIM]` para cada apagador A1. FreeCAD BIM `claimChildren()` usa el parametro `ClaimHosted` (default True) para presentar hosted objects bajo su host.

Durante la investigacion se detecto una restriccion importante: `ArchComponent.getMovableChildren()` tambien descubre hosted objects por `Wall.InList` y `Device.Host`; si el objeto no tiene `MoveWithHost`, lo considera movible. Por ello convertir `Device.Host` a `PropertyLinkHidden` eliminaria el backlink y podria eliminar una capacidad BIM existente.

Se habia preparado rev O con Host hidden, pero **se revirtio antes de prueba de usuario**. Drive conserva `objeto_toma_uno.py` rev N. No se cambia Host/MuroReferencia.

Candidatos pendientes:
- `ClaimHosted=False`: nativo, preserva backlinks y movimiento, pero afecta globalmente la vista BIM;
- referencia de proyeccion electrica: localizada y alineada con el contrato semantico, pero requiere lifecycle/seleccion adicional;
- Host hidden solo si se implementa y prueba un reemplazo explicito para movimiento con host.

### Verificacion

`py_compile` de `plan_selection.py`, `plan_live_sync.py` y `objeto_toma_uno.py`: APROBADO.
No se modifico ningun FCStd.
Prueba GUI real del overlay: PENDIENTE.

---

## Trabajo GPT 2026-09-05 20:22 - feedback PLAN completo y PropertyLinkHidden

> Trabajo directo de GPT en Drive; no atribuir a Codex.

Marco aporto nueva evidencia en Upala / FreeCAD 1.1.3: al apuntar/clicar el PLAN el sistema
redirige correctamente la seleccion a Owner, pero el highlight nativo cae sobre el
subelemento alcanzado (`Edge6`, `Edge18`, `Vertex41`, etc.) y no sobre todo el simbolo.
El mismo caso sigue mostrando el dialogo `Dependencias del objeto` listando el PLAN antes
de borrar el Owner.

Investigacion nativa adicional:
- la API Python 1.1.3 define `Gui.Selection.setPreselection(obj, subname="", ...)`;
- usar subname vacio permite pedir preseleccion del objeto completo;
- Draft Layer en FreeCAD usa propiedades `*Link*Hidden` precisamente para evitar avisos
  `might break` al borrar objetos y migra tipos dinamicos mediante `removeProperty()` +
  `addProperty()` conservando el valor.

Cambios guardados en los mismos IDs de Drive:

1. `electriccr/ui/plan_selection.py` v0.2.0
   - normaliza hover de `Edge`/`Vertex` a preseleccion del PLAN completo;
   - tras redirigir la seleccion a Owner reaplica feedback PLAN completo;
   - PLAN nunca entra como segunda seleccion logica.

2. `electriccr/features/objeto_toma_uno.py` rev N
   - `Owner` documental pasa a `App::PropertyLinkHidden`;
   - los PLAN A1 existentes con `App::PropertyLink` se migran transaccionalmente al pasar
     por `sync_plan_representation()`;
   - se preservan expresiones que referencian Owner y se verifica nuevamente el binding
     canonico `PLAN.Placement <- Owner`;
   - dry-run reporta `MIGRATE_PLAN_OWNER_LINK_HIDDEN`.

Verificacion realizada fuera de FreeCAD real:
- `python -m py_compile`: APROBADO para ambos archivos;
- actualizacion in-place de Drive: APROBADA.

Prueba real 1.1.3 sigue obligatoria antes de declarar estable, especialmente Delete,
Undo/Redo y persistencia save/reopen. A1 permanece opt-in.

---

## Trabajo GPT 2026-09-05 - correccion del modo visual A1

> Trabajo directo de GPT en Drive; no atribuir a Codex.

Se identifico que el problema recurrente de Solo2D/Solo3D no era falta de una herramienta:
ya existe `Gestionar_Visibilidad_ElectricCR.FCMacro`, que opera mediante `ModoVisual`.

El defecto era de integracion A1: las representaciones separadas usaban
`MostrarModelo3D` / `MostrarSimboloPlano` y no reaccionaban automaticamente a
`ModoVisual`.

Cambios:
- `objeto_toma_uno.py` rev M: traduccion bidireccional coherente entre modos canonicos y
  flags de visibilidad A1;
- `plan_live_sync.py` v0.2.0: sincroniza visibilidad en cambios interactivos y conserva
  la actualizacion de Placement ya aprobada;
- `InitGui.py`: agrega a la barra principal ElectricCR, cuando existen, `Draft_Move`,
  `Draft_Snap_Special` y el comando historico `Gestionar_Visibilidad_ElectricCR`.

No se creo un gestor alternativo, no se reconstruyo geometria y no se modificaron FCStd.

Verificacion:
- compilacion/sintaxis en memoria: OK;
- Drive actualizado en los mismos IDs: OK;
- prueba funcional FreeCAD 1.1.3 de los tres modos visuales: PENDIENTE.

---

## Trabajo GPT 2026-09-05 16:10 - separacion visual durante Transformar y Access violation en Undo

> Trabajo directo de GPT/Marco; no atribuir a Codex.

En Upala, Marco confirmo que el dragger `Transformar` queda en el origen 2D pero mueve visualmente
solo el Owner/3D. PLAN conserva temporalmente el Placement anterior y se corrige con F5/recompute.
El JSON posterior mantiene Owner, expresion schema 2 y SnapPoints `(0,0,0)`, por lo que la
dependencia persistente sigue valida; el defecto es de refresco interactivo.

El registro tambien mostro un `Access violation` dentro de `Transactions.cpp` al hacer Undo de la
transaccion de creacion de apagadores. Antes del fallo, `plan_lifecycle` estaba eliminando PLANs mientras
FreeCAD ya deshacia los Owners. Se clasifica como regresion critica introducida por el observer.

Cambios GPT en Drive:

- `plan_lifecycle.py` 0.1.1: guardas `Document.isPerformingTransaction()` en delete/flush/commit;
- nuevo `plan_live_sync.py`: `PLAN.recompute()` dirigido ante cambio de `Owner.Placement`;
- `InitGui.py`: instala live sync.

Compilacion sintactica local de los tres archivos: OK. Prueba real FreeCAD 1.1.3: PENDIENTE.

`Draft Snap Special` queda aclarado como modo de snap para Draft Move; no interviene en Transformar.

A1 permanece opt-in.

---

## Trabajo GPT 2026-09-05 15:43 - validacion de campo posterior: seleccion visual y Delete

> Trabajo directo de GPT/Marco; no atribuir a Codex.

Marco probo en Upala con FreeCAD 1.1.3:

- PLAN redirige correctamente la seleccion al Owner;
- 2D y 3D se mueven juntos;
- FreeCAD resalta visualmente solo el 3D del Owner, no PLAN;
- ocultar Owner deja PLAN visible, confirmando visibilidad fisica/documental independiente;
- Delete elimina Owner + PLAN con el nuevo lifecycle;
- antes del borrado aparece el dialogo nativo `Dependencias del objeto` listando PLAN.

La causa del dialogo es anterior al observer: `Std_Delete` detecta
`PLAN.Owner : App::PropertyLink` como dependencia.

Investigacion oficial posterior identifica `App::PropertyLinkHidden`, heredero de
`PropertyLink`, cuya finalidad es ocultar la referencia al chequeo de dependencias.
Se clasifica como **REUTILIZAR SI PASA PROBE REAL**. No se modifico aun el tipo de
`Owner`, porque debe comprobarse que la expresion PLAN<-Owner sigue recibiendo
actualizaciones/recompute.

Para el feedback visual se evita doble seleccion. Primera alternativa a probar:
preseleccion nativa de PLAN mediante `Gui.Selection.setPreselection()` mientras Owner
permanece como unica seleccion funcional.

`Draft Snap Special` se confirma como modo nativo Draft/BIM que consume los `SnapPoints`
especiales del objeto. PLAN ya expone `(0,0,0)`.

Estado: desarrollo activo; A1 sigue opt-in.

---

## Trabajo GPT 2026-09-05 14:35 - punto de insercion PLAN / Snap Special

Este bloque corresponde a trabajo directo de GPT en Drive; no atribuir a Codex.

### Investigacion

Se confirmo en el codigo actual de Draft que `snapToSpecials()` consume cualquier
objeto con `SnapPoints` y transforma cada punto local con `obj.Placement.multVec(p)`.
Esto permite implementar el punto base CAD sin geometria auxiliar.

Se auditaron los STEP 2D vigentes. Toma y apagador ya poseen referencias geometricas
en `(0,0,0)`; otros simbolos no son uniformes, por lo que se adopta SnapPoints como
contrato comun.

### Cambios

- `electriccr/features/objeto_toma_uno.py` rev L:
  `PLAN.SnapPoints=[Vector(0,0,0)]` y diagnostico
  `SET_PLAN_INSERTION_SNAP`.
- `InitGui.py`: agrega `Draft_Snap_Special` a `Draft compacto`.
- `tests/freecad_plan_owner_spatial_sync_a1_smoke.py`: verifica SnapPoints y su
  transformacion mundial.

No se modificaron recursos STEP ni Shape PLAN. No se hizo migracion automatica.

### Verificacion

- compilacion sintactica: OK;
- inspeccion STEP: OK;
- prueba interactiva FreeCAD del nuevo Snap Special: PENDIENTE.

Clasificacion provisional:
- Rol: SOPORTE/UX del nucleo A1.
- Madurez: DESARROLLO.
- Resultado: POR VERIFICAR.

---

## Trabajo GPT 2026-09-05 14:05 - ciclo de vida PLAN al borrar Owner

> Esta seccion corresponde a trabajo directo de GPT en Google Drive; no es resultado de Codex.

### Hallazgo de campo

Marco valido seleccion PLAN -> Owner y movimiento conjunto 2D/3D. Al borrar un
dispositivo, su PLAN persiste con `Owner=null`. Se confirma un defecto distinto de la
sincronizacion espacial: **borrado semantico incompleto**.

### Investigacion

Se revisaron mecanismos nativos de FreeCAD:

- `ViewProvider.onDelete()` admite eliminar objetos relacionados;
- `App::PropertyLink` rompe referencias al objeto eliminado;
- `PropertyLinkChild` no se toma como garantia de cascada;
- `App::DocumentObserverPython` expone `slotDeletedObject`;
- `Document.hasPendingTransaction()` permite coordinar con Undo/Redo.

No se sustituye el `ViewProviderLink` nativo del `App::Link`.

### Codigo modificado en Drive

- NUEVO: `ElectricCR/electriccr/features/plan_lifecycle.py`
- MODIFICADO: `ElectricCR/InitGui.py`

El observador se instala idempotentemente desde `Initialize()` y permanece activo
despues de cambiar de Workbench.

### Pruebas

Fuera de FreeCAD real:

- sintaxis: OK;
- mock transaccion abierta: OK;
- mock sin transaccion: OK;
- mock fallback post-commit: OK.

Prueba real FreeCAD 1.1.3: PENDIENTE.

Clasificacion provisional:

```text
Rol: NUCLEO / SOPORTE DE CICLO DE VIDA
Madurez: DESARROLLO
Resultado: POR VERIFICAR
```

No autoriza A1 default ni migracion legacy.

---

## Nota posterior 2026-09-05 - UX 2D no cubierta por el cierre PLAN/Owner

El resultado de Codex sobre sincronizacion espacial sigue siendo valido: PLAN
sigue automaticamente el Placement del Owner mediante expresion persistente.

Despues del cierre se identifica un requisito adicional que esa tarea no tenia
como alcance: **editar el mismo dispositivo desde su representacion 2D**.
Actualmente hacer clic en PLAN puede seleccionar el `Part::Feature` documental y
mostrarlo como objeto auxiliar en el arbol; ademas su Placement, correctamente
gobernado por expresion, no debe editarse como segunda autoridad.

La solucion a estudiar no es eliminar la expresion ni volver a unir 2D/3D. El
contrato nuevo es:

```text
clic/mover 3D  -> Device.Placement
clic/mover PLAN -> Device.Placement
Device.Placement -> PLAN por expresion
```

La preferencia preliminar es ocultar PLAN del arbol, redirigir seleccion a Owner
y reutilizar `Draft Move` con el origen local `(0,0,0)` del simbolo como punto
base. Se requiere prueba real en FreeCAD 1.1.3 antes de convertir esta nota en
implementacion.

Esta nota no modifica retrospectivamente el resultado tecnico cerrado por
Codex; amplia el contrato de UX para la siguiente fase.

---

# ElectricCR - Resultado de Codex

## Resultado 2026-09-05 - A1 sincronizacion espacial PLAN-Owner

**Objetivo:** hacer que `Device.Placement` sea la unica autoridad espacial y
que PLAN siga automaticamente X/Y/orientacion, conservando
`DocumentationPlaneZ` y `PlanSymbolScale` como parametros documentales.

**Estado:** IMPLEMENTADO Y PROBADO EN FREECAD 1.1.3 / A1 APTO PARA DEFAULT DE
OBJETOS NUEVOS / DEFAULT TODAVIA OPT-IN.

### Diagnostico confirmado

`sync_plan_representation` calculaba `_plan_placement(owner)` y lo asignaba una
sola vez a `PLAN.Placement`. `Owner` ya era `App::PropertyLink`, pero el PLAN
era `Part::Feature` sin expresion ni proxy. El enlace creaba dependencia de
pertenencia, no una regla para derivar Placement. `RepresentationSignature`
incluia UID, X/Y/Z y quaternion, de modo que tambien confundia transformacion
espacial con geometria documental.

La copia del FCStd guardado mostro `TomaBIM_011` y su PLAN alineados en
X=`19003.999751956`; el movimiento a X=`19263` estaba en la sesion real no
guardada descrita por el usuario. La regresion reprodujo exactamente ese estado
en la copia, dejando PLAN atras `259.000248044 mm` antes de sincronizar.

### Evaluacion nativa y decision

La documentacion oficial de FreeCAD confirma expresiones sobre Placement
completo, componentes, vectores y rotaciones. Una prueba minima en 1.1.3
demostro que esta expresion atraviesa `Owner`, responde a movimiento/giro y Z,
participa en Undo/Redo y persiste despues de save/reopen:

```text
placement(vector(Owner.Placement.Base.x;
                 Owner.Placement.Base.y;
                 Owner.DocumentationPlaneZ);
          Owner.Placement.Rotation)
```

Clasificacion:

- expresion nativa: **REUTILIZAR**;
- PLAN `Part::FeaturePython`: **COEXISTIR / RESERVA NO NECESARIA**;
- observador GUI/Qt: **DESCARTAR**, porque la dependencia parametrica resuelve
  el caso sin estado global.

### Cambio minimo

Solo se modifico
`ElectricCR/electriccr/features/objeto_toma_uno.py`:

- `REPRESENTATION_SCHEMA_VERSION` paso de 1 a 2;
- PLAN sigue siendo `Part::Feature` y `Owner` sigue siendo `PropertyLink`;
- `PLAN.Placement` recibe la expresion nativa persistente;
- una sincronizacion actualiza automaticamente PLAN antiguos sin expresion;
- `RepresentationSignature` conserva solo version, `KeyRegistro`, giro/offset
  local del simbolo y `PlanSymbolScale`;
- Placement, UID y `DocumentationPlaneZ` salieron de la firma.

No se combinaron 2D/3D, no se agrego proxy, observador, comando ni arquitectura
paralela. `separate_documentation=False` permanece como default del API.

### Pruebas y resultados

`freecad_plan_owner_expression_probe.py` aprobo expresion, PropertyLink,
movimiento, giro, Z, Undo/Redo y save/reopen en un fixture minimo.

`freecad_plan_owner_spatial_sync_a1_smoke.py` aprobo sobre copia temporal de
Chomes:

| prueba | resultado |
|---|---|
| desfase de campo | reproducido 259.000248044 mm y corregido por sincronizacion |
| mover Owner X/Y | PLAN siguio automaticamente |
| girar Owner | PLAN copio la rotacion completa de planta |
| `AlturaRel` | 300 -> 450 mm en toma; 1200 -> 1350 mm en apagador, sin deriva PLAN |
| `DocumentationPlaneZ` | 225 mm toma / 75 mm apagador; solo transformacion Z |
| `PlanSymbolScale` | 1.35 toma / 0.80 apagador; solo geometria documental |
| Undo/Redo | aprobado para movimiento y giro en ambas familias |
| save/reopen | expresiones, Owner, Placement y propiedades persistieron |
| recompute repetido | tres pasadas, conteo y Placement estables |
| huerfanos | cero |
| DXF | dos PLAN, 20008 bytes |
| Shape fisica | toma 84518.072443 mm3 / 18 solidos; apagador 82232.284217 mm3 / 2 solidos |

La regresion A1 general
`freecad_electromechanical_outlet_switch_a1_smoke.py` tambien aprobo nuevamente
con save/reopen, Undo/Redo, escala, alturas, DXF y cero huerfanos.

El original de Chomes no se guardo ni modifico. Antes y despues conservo
SHA-256 `E36A28A4AADE9615701B7B7354F905EA370B1FD057F5F2D0AD8A66E785404E7D`,
`3898540` bytes y la misma fecha. El FCStd temporal fue eliminado. Drive guarda
`A1_PLAN_OWNER_SYNC_2026-09-05_reporte.json` y
`A1_PLAN_OWNER_SYNC_2026-09-05.dxf`.

### Compatibilidad y limite deliberado

Los PLAN nuevos reciben la expresion durante su creacion/sincronizacion. Los
PLAN A1 esquema 1 existentes se actualizan de forma idempotente la proxima vez
que pasan por `sync_plan_representation`; no se hizo una migracion automatica
del documento productivo.

Clasificacion provisional:

- Rol funcional: **NUCLEO DE REPRESENTACION**;
- Madurez: **ACTIVA / A1 OPT-IN**;
- Resultado comprobado: **COMPROBADA TECNICAMENTE EN FREECAD 1.1.3**;
- Decision: **A1 APTO PARA DEFAULT DE OBJETOS NUEVOS**, sin cambiarlo en esta
  tarea y sin migrar legacy.

---

## Nota historica posterior al cierre 2026-09-03 - hallazgo de campo no cubierto por la aceptacion

La aceptacion GUI registrada abajo fue correcta para el alcance ejecutado en ese
momento: creacion desde los comandos completos, contrato A1, separacion
fisica/documental, save/reopen, Undo/Redo e invariancia fisica.

Posteriormente, un uso real en `Chomes-Segundo Piso.FCStd` revelo un escenario
que esa prueba no incluia: **mover manualmente una identidad A1 despues de
creada y comprobar si PLAN la sigue automaticamente**.

Caso:

```text
TomaBIM_011 / Link_TomaBIM_011
ElementUID = 975bd98d-7a56-4765-b5d5-f6d778452c90
Owner Placement X/Y = 19263 / 11260
PLAN Placement X/Y  = 19004 / 11260
Delta X = 259 mm
PLAN.Owner = Link_TomaBIM_011
PLAN.ExpressionEngine = []
```

`RepresentationSignature` del PLAN conserva tambien la posicion anterior.

Por este hallazgo, la decision historica `A1 APTO PARA SER DEFAULT` queda
**suspendida hasta corregir y verificar la sincronizacion espacial PLAN-Owner**.
No se modifica retrospectivamente el resultado de Codex: se amplian los
criterios de aceptacion con una regresion que faltaba.

No se realizo cambio de codigo en esta nota documental.

---

# ElectricCR - Resultado de Codex

## Resultado 2026-09-03 - aceptacion funcional GUI de A1

**Estado:** APROBADA EN FREECAD 1.1.3 / SIN CAMBIOS DE CODIGO / A1 APTO PARA
SER DEFAULT DE OBJETOS NUEVOS, PERO TODAVIA OPT-IN.

Se activaron desde `ElectricCRWorkbench` los dos comandos registrados reales y
se recorrieron seis dialogos completos: legacy, A1 y reapertura para toma; y
legacy, A1 y reapertura para apagador. En las seis aperturas la casilla A1
inicio desmarcada. Solo quedo marcada en las dos ejecuciones opt-in, y al
reabrir cada herramienta volvio a desmarcarse.

La ejecucion legacy creo 31 tomas sobre los 19 tramos del `Wall` seleccionado y
un apagador junto a `Window`; todos fueron `LegacyCompound` y se eliminaron
mediante Undo despues de comprobar Redo. La ejecucion A1 creo, por el mismo
algoritmo productivo, 31 tomas y un apagador. Antes de guardar habia 32
identidades A1, 32 PLAN, cero PLAN huerfanos y todos los UID eran unicos.

Instancias representativas verificadas:

| propiedad | tomacorriente | apagador |
|---|---|---|
| contrato | `PhysicalDocumentationA1` | `PhysicalDocumentationA1` |
| Host / Space | `Wall` / `Space` | `Wall` / `Space` |
| PuertaOrigen | no aplica | `Window` |
| altura | 300 mm | 1200 mm |
| Placement XY / yaw | 1878.748293, 9250 / 0 grados | 3145.344424, 8632.545499 / -90 grados |
| volumen / solidos | 84518.072443 / 18 | 82232.284217 / 2 |
| PLAN | documental, Owner correcto, volumen 0, solidos 0 | documental, Owner correcto, volumen 0, solidos 0 |

La Shape fisica no cambio al alternar la visibilidad de PLAN. Undo/Redo aprobo
en ambas familias. Save/reopen mantuvo 260 objetos antes y despues, incluso
tras un segundo recompute, y conservo contrato, UID, Host, Space, master,
Placement y metricas fisicas. El apagador conservo la regla productiva de jamba
de 150 mm y cara interior; no se modifico el caso historico
`Apagador - Rectangle006`.

El DXF documental ya habia sido aprobado para el mismo contrato PLAN en el
baseline MCP vigente; la aceptacion GUI confirmo que los comandos completos
producen ese contrato sin contaminar la Shape fisica.

El original de Upala permanecio byte a byte igual: SHA-256
`103FD471564E589F8E952954848A519D20AC58527C1ADCF39053CFCE3FF07F1E` y
`1237860` bytes. La copia temporal se cerro y elimino. Drive conserva el informe
`Aceptacion_GUI_A1_2026-09-03_reporte.json` y seis capturas de los dialogos.

El primer puente MCP de interfaz quedo ocupado al intentar capturar la vista
completa del modelo pesado. Para no reiniciar ni arriesgar documentos abiertos
del usuario, la aceptacion se completo en una segunda sesion GUI aislada de
FreeCAD 1.1.3, siempre mediante los comandos registrados y sus dialogos reales.
La sesion principal quedo con los dos documentos Chomes originales abiertos.

**Decision:** A1 es **APTO PARA SER DEFAULT DE OBJETOS NUEVOS**. Esta tarea no
activa ese cambio, no migra legacy y no autoriza cambios productivos masivos.

## Resultado 2026-09-03 - A1 opt-in en algoritmos BIM reales

**Estado:** IMPLEMENTADO / VERIFICADO POR MCP EN FREECAD 1.1.3 / DEFAULT LEGACY INTACTO.

### Generadores reales confirmados

`ElectricCR/commands/macros.py` registra y lanza:

- `ElectricCR_Tomacorrientes_InstalarTomacorrientesEnParedesBIM` ->
  `Tomacorrientes/InstalarTomacorrientesEnParedesBIM.FCMacro`;
- `ElectricCR_Iluminaci_n_ColocarApagadoresEnPuertas` ->
  `Iluminación/ColocarApagadoresEnPuertas.FCMacro`.

El tomacorriente se decide mediante los tramos del muro, intervalos de
puertas/ventanas, espacios utilizables, separacion y cara interior. El apagador
se decide mediante puerta BIM, tramo de muro paralelo, aperturas, jamba libre y
cara del recinto. Los dos crean la instancia mediante
`electriccr.features.objeto_toma_uno.crear_toma_link`.

### Integracion

Las dos macros agregan una casilla A1 opt-in desmarcada. No se guarda en
preferencias. Cuando se marca:

- se exige `PhysicalDocumentationA1`; no existe fallback silencioso a legacy;
- Placement y metadatos siguen procediendo del algoritmo existente;
- `ensure_device_semantics` asigna UID, Space y Host dentro de la transaccion
  exterior mediante el nuevo parametro `manage_transaction=False`;
- `sync_plan_representation` crea PLAN independiente;
- un apagador legacy existente se preserva y se omite en vez de migrarse.

### Evidencia Upala y discrepancia del baseline

Google Drive es la evidencia primaria del estado historico: los inventarios
`Arbol_Grupos_1416_Levantamiento_250424_Compu_D_20260903_091034` y
`..._092039` registran 48 tomacorrientes y 11 apagadores legacy. En el momento
de la prueba, el archivo guardado y el documento abierto de Upala ya habian
vuelto a 187 objetos y cero dispositivos ElectricCR. La prueba no oculta esta
discrepancia ni atribuye una causa sin evidencia.

El caso `Apagador - Rectangle006` quedo explicado por relaciones reales del
inventario de Drive:

- identidad `Link_Apagador_Sketch_Centros_Puertas_001`;
- puerta `Window`;
- muro `Wall`;
- `AreaRecinto=Rectangle`, Label `Rectangle006`;
- master legacy `Master_Apagador_Simple_Apagador_Ambos_Vertical_1200`.

El Label reflejaba el recinto auxiliar, no una puerta llamada Rectangle006. Su
Placement historico `[2995.344424,8632.545499,0]` coincide con el origen de la
puerta, mientras el algoritmo vigente calculo la jamba a
`[3145.344424,8632.545499,0]`. No se aplico ninguna correccion.

### Prueba MCP controlada

`tests/freecad_upala_real_placement_a1_smoke.py` copio el FCStd vigente a TEMP,
derivo un Space nativo temporal del `Rectangle006` existente y ejecuto los
helpers reales. Creo exactamente:

- `Link_TomaBIM_049`, Host `Wall`, altura 300 -> 450 mm;
- `Link_Apagador_Sketch_Centros_Puertas_001`, Host `Wall`,
  `PuertaOrigen=Window`, altura 1200 -> 1350 mm.

Ambos tuvieron contrato A1 en Link y master, ElementUID unico, Space resuelto,
Shape fisica con volumen/solidos y PLAN `DocumentationOnly/Owner` con volumen y
solidos cero. La toma midio Volume `84518.072443` y 18 Solids; el apagador
Volume `82232.284217` y 2 Solids. La sincronizacion PLAN no cambio
Volume/BoundBox/Solids fisicos. Aprobaron relink conservando Placement,
Undo/Redo individual, save/reopen y DXF documental de `11104` bytes.

El verificador comparo SHA-256 y tamano de la fuente antes/despues, restauro el
documento activo anterior y elimino FCStd, DXF y `.FCBak` temporales. Una
repeticion headless tambien aprobo y dejo `TEMP_LEFT=0`.

Las pruebas unitarias de `RoomResolver`, semantica de dispositivos, recintos de
iluminacion y cambio de altura aprobaron. `pytest` no esta instalado en el
entorno. La prueba comun `CRBIMCore/tests/test_common_rooms_contract.py` conserva
un fallo ajeno y preexistente porque el `FacilArquitecturaWB/InitGui.py` ya
modificado en el arbol de trabajo no contiene el import esperado; no se altero
ese archivo como parte de esta integracion.

No se modifico el original, no hubo migracion masiva, no se cambio el default,
no se hizo commit ni push.

## Resultado 2026-09-03 - A1 fisico/documental, tomacorriente y apagador

**Estado:** IMPLEMENTADO COMO PROTOTIPO OPT-IN / VERIFICADO MCP EN FREECAD 1.1.3.

### Diagnostico previo

La implementacion A1 real no coincidia con lo descrito en el diseno. Antes de
esta tarea, `TomaUnoProxy._build_shape()` agregaba el simbolo 2D y el modelo 3D
a la misma lista y asignaba `Part.makeCompound(shapes)` a `obj.Shape`. No habia
PLAN independiente ni un contrato de representacion persistente. Por ello el
punto de partida se clasifico como `LegacyCompound`, no como A1.

Tambien se evaluaron las alternativas visuales A/B/C. Cambiar el ViewProvider
de un `App::Link` es una intervencion fragil sobre el proveedor nativo y una
escena Coin del ViewProvider no constituye una fuente documental semantica para
DXF. Se adopto la alternativa C: auxiliar PLAN controlado, ocultable en el arbol
y vinculado a la identidad.

### Implementacion

- `RepresentationContract` distingue `LegacyCompound` de
  `PhysicalDocumentationA1`.
- A1 crea masters fisicos separados; la `Shape` contiene solamente `model3D`.
- PLAN es `Part::Feature`, `DocumentationOnly`, rol `PLAN`, sin `ElementUID` y
  con `Owner` hacia el `App::Link`.
- La instancia conserva la unica identidad, `Placement`, master, `AlturaRel`,
  registro y propiedades legacy; agrega `ElementUID`, `Space` y `Host`.
- Cambiar escala o visibilidad PLAN no reconstruye ni altera la Shape fisica.
- El cambio de altura conserva UID, Space, Host y Placement y relinka a otro
  master A1 inmutable.
- Save/reopen conserva ambas representaciones y sus enlaces.
- El exportador DXF experimental consume exclusivamente PLAN.
- La sincronizacion es idempotente y existen funciones de eliminacion
  controlada y auditoria de huerfanos.
- La ruta legacy continua siendo el default para no migrar documentos.

### Evidencia MCP

El script `tests/freecad_electromechanical_outlet_switch_a1_smoke.py` creo un
documento temporal con exactamente un tomacorriente y un apagador. Resultado:

| verificacion | tomacorriente | apagador |
|---|---:|---:|
| contrato instancia/master | `PhysicalDocumentationA1` | `PhysicalDocumentationA1` |
| altura final | 450 mm | 1350 mm |
| Shape Volume | 84518.072443 | 82232.284217 |
| Shape Solids | 18 | 2 |
| Shape BoundBox Z | 414.76..484.76 | 1291.453..1408.547 |
| PLAN Volume / Solids | 0 / 0 | 0 / 0 |
| PLAN BoundBox Z | 0..0 | 0..0 |
| ElementUID | `...0001` | `...0002` |

Los dos enlaces apuntaron a masters A1 propios de sus alturas. `Space` resolvio
al Space nativo temporal y `Host` al muro BIM temporal. Los Placement fueron
`[1000,100,0]` sin giro y `[2000,100,0]` con giro Z de 12 grados, y se
mantuvieron despues del cambio de altura y save/reopen.

Undo/Redo aprobo para creacion conjunta, visibilidad y altura. La segunda
sincronizacion PLAN produjo cero cambios. El DXF de exactamente dos PLAN midio
`18405` bytes. No quedaron PLAN huerfanos, FCStd, DXF ni documento temporal.

MCP listo antes y despues solamente el documento previamente abierto
`_1416_Levantamiento_250424_Compu_D`; no se activo, guardo ni modifico. No se
tocaron Upala, los 48 tomacorrientes ni los 11 apagadores existentes.

### Verificaciones adicionales

- `ECR_SEMANTIC_DEVICE_CORE_OK`.
- Seis pruebas puras de resolucion espacial de iluminacion aprobaron.
- `py_compile` y `git diff --check` aprobaron en los archivos A1.
- `freecadcmd` reprodujo la prueba; emitio un error de inicializacion previo de
  `FacilArquitecturaWB/Init.py`, ajeno a esta implementacion.
- No se hizo commit ni push.

## Resultado 2026-09-01 - Prototipo luminaria semantica y arbol idempotente

**Estado:** IMPLEMENTADO / PROBADO / VERIFICADO MCP EN FREECAD 1.1.3.

**Revalidacion 2026-09-02:** la fuente DEV seguia cargada desde
`Macros-de-Freecad`; `ECR_SEMANTIC_DEVICE_CORE_OK`, las 11 pruebas puras de
RoomResolver y `ECR_SEMANTIC_LUMINAIRE_PROTOTYPE_OK` aprobaron nuevamente. El
smoke confirmo los mismos resultados de UID, Space, proyeccion idempotente,
altura, DXF, Equipment, Undo/Redo y guardar/reabrir. No quedaron documentos ni
temporales abiertos y no se hicieron cambios funcionales adicionales.

Se implemento el prototipo autorizado sobre una sola luminaria temporal creada
por `objeto_toma_uno.crear_toma_link()` con el registro real
`Luminaria LED Redonda 1000lm`. La instancia conserva su master compartido,
`Placement`, representacion 2D/3D, `AlturaRel`, `Tipo`, `KeyRegistro`,
`ModoVisual` y orientacion. Solo recibe `ElementUID` y `Space`.

### Evidencia funcional real

- `ElementUID` se crea una vez, es unico y persiste tras recompute y
  guardar/cerrar/reabrir.
- RoomResolver usa el `Placement` global de la instancia `App::Link`, no la
  posicion local del master. Un resultado `RESOLVED` enlaza el `Arch Space`;
  `AMBIGUOUS` y `NOT_FOUND` no escriben valor en `Space`.
- El Space `Sala de Espera` permanecio bajo `Ground Floor`, con el mismo Base,
  Shape y Placement, y sin propiedades ElectricCR.
- El cambio 2700 -> 2850 mm reutilizo el mecanismo actual de relink: cambio el
  master inmutable, no la identidad del Link; UID, Space y Placement se
  conservaron. El simbolo 2D siguio en Z local 0 y el modelo 3D quedo a altura.
- El Link se exporto correctamente a un DXF temporal no vacio.
- Los masters quedaron en `electrico/_lib/_lib_devices`. Se corrigio el detalle
  previo por el que `TomaUnoProxy.execute()` podia volverlos visibles despues
  del recompute; `EsPrototipo` mantiene ahora el ViewProvider oculto.

### Arbol idempotente

Ruta materializada:

```text
electrico/Iluminacion/Circuitos/IL-TEST/Recintos/Sala de Espera/Apagadores/S1/Luminarias
```

Las autoridades fueron `Space`, `CircuitoID` y los `PropertyLinkList` del
Control temporal. Los grupos tienen rol y clave estables, y el helper usa
`dry_run=True` por defecto. La segunda aplicacion produjo `0` cambios y `0`
duplicados, sin tocar UID, Space, master o Placement.

FreeCAD asigna una pertenencia visual exclusiva a objetos dentro de
`App::DocumentObjectGroup`. Para que el arbol sea realmente una vista y no
reorganice la instancia fisica, `Luminarias` contiene una referencia indice
`App::Link` marcada `ECR_ProjectionReference`, enlazada a la luminaria real por
`LinkedObject` y `ECR_SourceElementUID`. Es el mismo patron conceptual del
organizador vigente; no constituye una segunda familia electromecanica.

### Comparador Arch Equipment

En FreeCAD 1.1.3 `Arch.makeEquipment()` produjo `Part::FeaturePython` con
`Proxy.Type=Equipment`, `Base`, `GlobalId`, `IfcProperties` e `IfcType`. Se
configuro exitosamente como `Light Fixture`, porque el valor nativo por defecto
fue `Furniture`. Guardar/reabrir y Undo/Redo aprobaron.

Equipment aporta clasificacion BIM/IFC nativa, pero para esta prueba necesito un
Base/copia controlada de la geometria; el `App::Link` comparte master y conserva
mejor la arquitectura liviana actual. No hay evidencia para sustituir el Link.

### Codigo y pruebas

Archivos funcionales:

- `ElectricCR/electriccr/semantic/device_core.py` (nucleo puro JSON-compatible);
- `ElectricCR/electriccr/semantic/freecad_adapter.py` (UID, Space y proyeccion);
- `ElectricCR/electriccr/features/objeto_toma_uno.py` (ocultacion persistente de masters);
- `ElectricCR/tests/test_semantic_device_core.py`;
- `ElectricCR/tests/freecad_semantic_luminaire_prototype_smoke.py`.

Pruebas aprobadas:

- `ROOM_RESOLVER_CORE_TESTS_OK 11`;
- `ECR_LIGHTING_ROOM_TESTS_OK 6`;
- `ECR_SEMANTIC_DEVICE_CORE_OK`;
- `ROOM_RESOLVER_FREECAD_SMOKE_OK`;
- `ECR_ROOMRESOLVER_PHASE2A_OK`;
- regresion de altura/rotacion semantica;
- `PASS ColocarLuminarias_Link altura`;
- `ECR_SEMANTIC_LUMINAIRE_PROTOTYPE_OK`;
- inspeccion visual isometrica y planta del documento temporal.

Procedimiento de repeticion:

1. ejecutar desde la raiz del repositorio
   `python ElectricCR/tests/test_semantic_device_core.py`;
2. en FreeCAD 1.1.3, ejecutar mediante MCP o consola Python
   `ElectricCR/tests/freecad_semantic_luminaire_prototype_smoke.py` con
   `runpy.run_path(..., run_name="__main__")`;
3. comprobar la salida `ECR_SEMANTIC_LUMINAIRE_PROTOTYPE_OK` y que el script
   cierre el documento `ECR_SemanticLuminairePrototype` y elimine su FCStd/DXF
   temporal;
4. repetir la matriz indicada arriba para regresion de RoomResolver, fase 2A y
   altura de los Link.

### Decision de cierre

1. Si: el `App::Link` actual puede ser la identidad operativa enriquecida sin
   perder las funciones verificadas.
2. Si: `ElementUID + Space + CircuitoID + Control/Apagador legacy` bastan para
   proyectar la primera rama de iluminacion.
3. Equipment aporta IFC/BIM nativo, pero no justifica sustituir el master/Link;
   puede reservarse para una futura capa IFC si aparece una necesidad concreta.
4. Si: la rama se reconstruye idempotentemente sin usar el padre visual como
   autoridad.
5. Siguiente cambio minimo recomendado: exponer este adaptador primero como
   herramienta opt-in y probarlo en una copia controlada. Debe evitarse una
   migracion masiva o iniciar otra familia dentro de esta fase.

No se incremento version/build, no se hizo commit/push y no se modifico ningun
modelo original. La tarea se detuvo antes de tomacorrientes y apagadores.

---

## Resultado 2026-09-01 - RoomResolver fase 2A y contrato del arbol

**Estado:** IMPLEMENTADA / COMPILADA / PROBADA / VERIFICADA_MCP.

Se integro `CRBIMCore.RoomResolver` en la enumeracion de recintos de
`Iluminación/Actualizar_Iluminacion_Completa.FCMacro`. La formula de iluminacion,
las 12 columnas de `DatosRecintos`, la tabla legacy y los ajustes de layout
heredados se conservaron.

Resultado real en FreeCAD 1.1.3:

- Space-only: 1 recinto, 12.00 m2, filas/columnas calculadas sin escribir sobre
  el Space;
- Area-only: mismo resultado de la ruta legacy y propiedades `Rows/Columns`
  conservadas;
- Space + Area: una sola fila, correspondiente al Space;
- dos Spaces superpuestos: `AMBIGUOUS`, cero filas autoritativas;
- punto exterior: `NOT_FOUND`;
- comando completo repetido: dos hojas estables, sin duplicados ni luminarias;
- guardar/cerrar/reabrir: Space y hoja restaurados, Space sin propiedades de
  layout ElectricCR;
- firma fisica de Spaces/Areas y `LinkedObject`/Placement del probe electrico:
  sin cambios.

Pruebas aprobadas:

- 17 pruebas puras (`CRBIMCore` + selector ElectricCR);
- `ROOM_RESOLVER_FREECAD_SMOKE_OK` (8 candidatos, 17 objetos, read-only y
  reapertura estable);
- smoke heredado de Areas BIM, incluyendo consumidor de iluminacion;
- `ECR_ROOMRESOLVER_PHASE2A_OK`;
- `ECR_SEMANTIC_TREE_CONTRACT_OK`.

Auditoria del arbol:

- propiedades explicitas de recinto/circuito/apagador preceden el padre visual;
- controles ya conservan `PropertyLinkList` a luminarias y apagadores;
- circuito->tablero sigue como texto;
- no existe contrato uniforme de enlaces para Space, Level y System;
- la ruta visual determinista puede proyectarse desde relaciones, pero la
  reconstruccion completa no se implemento en esta fase.

No se modificaron luminarias, tomacorrientes, apagadores, masters,
`LinkedObject`, `ColocarLuminarias_Link`, MEPWorkbenchCR ni modelos originales.
No se incremento version/build porque ElectricCR no mantiene en esta ruta un
build funcional independiente y la tarea no autorizo una publicacion.

Archivos funcionales nuevos/modificados:

- `ElectricCR/electriccr/lighting/room_calculation.py`;
- `ElectricCR/electriccr/lighting/__init__.py`;
- `Iluminación/Actualizar_Iluminacion_Completa.FCMacro`;
- dos pruebas MCP y una prueba pura bajo `ElectricCR/tests/`;
- `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md` y documentacion asociada.

Pendiente futuro: diseno/auditoria del objeto electromecanico comun y luego
reconstruccion idempotente del arbol. No iniciar sin una tarea nueva.

---

## Resultado 2026-08-12 - Integracion de descripciones GPT

**Estado:** IMPLEMENTADA / COMPILADA / PROBADA / VERIFICADA_MCP /
**VALIDADA_VISUALMENTE**.

Se integraron las 192 entradas de `MACROS_DESCRIPCIONES_GPT.json` por la ruta
estable `ruta`. El catalogo ahora tiene 192 descripciones funcionales; 133
reemplazaron campos vacios o genericos y 59 conservaron una descripcion local
concreta. En 36 casos se conservaron textos locales distintos y se guardo la
alternativa GPT en `description_alternative`, con discrepancia documentada para
revision posterior.

Se conservaron sin cambios los comentarios, estados manuales, decisiones y
estadisticas externas de uso. La procedencia queda en
`fuente_descripcion`/`confianza_descripcion` y en los aliases internos
`description_source`/`description_confidence`.

El Panel ahora incluye la descripcion en la busqueda y muestra descripcion,
fuente y confianza en detalles y `Copiar diagnostico`. La validacion MCP en
FreeCAD 1.1.3 comprobo 12 grupos principales, una busqueda por la palabra
`delimitadas` contenida solo en una descripcion, descripcion visible para una
herramienta de cada grupo, diagnostico con descripcion/comentario y catalogo
sin perdida de campos protegidos.

Smoke test Fase 2 ampliado y `py_compile`: PASS. No se modifico ningun FCStd,
no se ejecuto ninguna macro para generar descripciones y no se hizo commit ni
push.

## Correccion posterior Fase 2 - comentarios y lentitud

Se confirmo un defecto en el cambio de seleccion: el evento de Qt ya habia
cambiado `currentItem` cuando se guardaba el comentario, por lo que el texto
podía terminar en la macro nueva. Se corrigio guardando contra el elemento
anterior recibido por `currentItemChanged` y luego cargando el comentario de la
nueva seleccion.

Tambien se corrigio la lentitud: la busqueda ya no reconstruye el catalogo ni
consulta comandos, archivos y estadisticas para cada tecla. Las filas se
construyen una vez por apertura y se reutilizan para filtros/busqueda; las
estadisticas y recursos de comandos se indexan en memoria. La medicion MCP paso
de reconstrucciones repetidas a aproximadamente 0.068 s la primera carga y
0.000002 s una lectura cacheada.

Los comentarios que permanecen en el catalogo son revisiones reales de Marco:
`Areas/CrearMurosEntreEspacios.FCMacro` y
`Areas/PoligonoFromBoundaryLines.FCMacro`. No quedo el texto de prueba usado
durante la validacion.

La prueba de cambio de seleccion confirmo que el comentario se guarda en la
macro anterior y que la siguiente macro carga su propio comentario. No se
modifico ningun FCStd ni se hizo commit/push.

## Resultado 2026-08-12 - Panel Fase 2

**Estado:** IMPLEMENTADA / COMPILADA / PROBADA / VERIFICADA_MCP /
**VERIFICADA_VISUALMENTE**.

### Catalogo y descripciones

- Se reviso el patron oficial de metadatos de macros de FreeCAD (`__Name__`,
  `__Comment__`, `__Help__`, `__Status__`, `__Requires__` e `__Icon__`) y se
  adopto solo como lectura segura, sin ejecutar macros durante el catalogado.
- Se creo `ElectricCR/data/macros_catalog.json`, esquema 1, con 192 entradas.
- 122 entradas corresponden a herramientas activas registradas por ElectricCR;
  70 son macros historicas no activas.
- 69 macros tienen descripcion obtenida desde metadatos oficiales o encabezados;
  las restantes indican claramente que no tienen descripcion.
- No se encontro localmente el Excel `Inventario_Clasificacion_ElectricCR_2026-08-08.xlsx`;
  no se inventaron datos historicos a partir de esa fuente.
- Se creo `ElectricCR/MACROS_CATALOGO.md`, generado deterministicamente desde
  el JSON mediante `ElectricCR/catalog.py`.

### Panel y revision manual

`macro_launcher.py` conserva la Fase 1 y agrega comentario multilinea editable,
estado manual, decision, guardado atomico, filtros nuevos, entradas historicas,
`Contraer grupos`, `Expandir grupos` y `Probar`. `Copiar diagnostico` incluye
descripcion, fuente, comentario, estado/decision y estadisticas separadas.

### Estadisticas

`usage_log.py` conserva `count` y los conteos anteriores como
`historical_count`. Las nuevas ejecuciones se separan en `real_count` y
`test_count`, con `last_real_ts` y `last_test_ts`. El boton `Ejecutar` marca uso
real y `Probar` marca prueba sin reclasificar el historial.

### Pruebas

- `smoke_macro_panel_phase2.py`: catalogo, descripciones, comentarios,
  escritura atomica, JSON invalido, Markdown determinista y conteos real/test/
  historico: PASS.
- Py_compile de los modulos modificados: PASS.
- FreeCAD 1.1.3 mediante MCP: 12 grupos, 122 filas activas, 70 historicas,
  filtros, busqueda con expansion, contraer/expandir, comentario/estado/decision
  persistentes y modo Diagnostico: PASS.
- Prueba MCP de botones: `Probar` produjo `test_count=1` y `Ejecutar`
  `real_count=1` en un registro temporal, sin modificar un FCStd.
- Capturas visuales: `C:\Users\marco\AppData\Local\Temp\ElectricCR_Panel_Fase2_Final.png` y
  `C:\Users\marco\AppData\Local\Temp\ElectricCR_Panel_Fase2_Validation.png`.

No se hizo commit ni push y no se modifico `HISTORIAL_CAMBIOS.md`.

## Validacion visual 2026-08-12 - Panel real ElectricCR

**Estado:** VERIFICADO_MCP / VERIFICADO_VISUAL en FreeCAD 1.1.3.

La ventana de la captura inicial no era el Panel real con el registro completo.
La prueba segura habia ejecutado `register_macro_launcher([('Prueba', [...])])`
y habia reemplazado en memoria `_MACRO_GROUPS` por un unico grupo de prueba.
El registro de metadatos no se habia perdido: conservaba 122 comandos reales,
pero la vista construia sus filas desde `_MACRO_GROUPS`. Ademas,
`ElectricCR_TestPanelSafe` quedo registrado en la sesion como residuo de la
prueba; no existe como herramienta real de ElectricCR.

Se reconstruyeron los grupos de la sesion a partir de
`get_registered_macro_metadata()` sin cambiar el codigo funcional. La
validacion del lanzador real mostro 12 grupos y 122 herramientas, vista normal
con 4 columnas, filtros, casilla `Diagnostico`, panel de detalles, botones
`Ajustar columnas`, `Copiar ruta`, `Copiar diagnostico`, `Ejecutar` y `Cerrar`,
ademas del modo diagnostico con 7 columnas y estados OK/REVISAR/ERROR.

Los modulos cargados provinieron del repositorio local esperado:
`ElectricCR/commands/macros.py` y `ElectricCR/commands/macro_launcher.py`.
La captura de la interfaz real queda en
`C:\Users\marco\AppData\Local\Temp\ElectricCR_Panel_Real_Validation.png`.
La captura del modo diagnostico queda en
`C:\Users\marco\AppData\Local\Temp\ElectricCR_Panel_Real_Diagnostic_Validation.png`;
esta muestra las 7 columnas y los estados `OK`, `REVISAR` y `ERROR` segun
corresponde.

La prueba segura sigue siendo un comando residual de la sesion porque esta
version de FreeCAD no expone `Gui.removeCommand`; esto no afecta al Panel real
ni a su registro. No se revirtio la implementacion, no se modifico ningun
FCStd y no se hizo commit ni push.

## Resultado 2026-08-12 - panel de macros ElectricCR

**Estado:** PROGRAMADO / COMPILADO / PROBADO TECNICAMENTE;
**VALIDACION VISUAL MCP COMPLETADA POSTERIORMENTE**. El primer intento habia
quedado pendiente por timeout de despacho de la sesion GUI.

### Cambios realizados

- `ElectricCR/commands/macros.py` ahora conserva un registro unico de metadatos
  por comando: macro, ruta relativa, grupo/barra efectiva, icono y su estado,
  clasificacion de transaccion y existencia del archivo.
- `ElectricCR/commands/macro_launcher.py` fue ampliado con vista normal,
  modo `Diagnostico`, filtros, iconos visibles, panel de detalles, estadisticas
  tomadas de `usage_log.py` y acciones para ejecutar, copiar ruta y copiar
  diagnostico.
- Las columnas, el tamano de ventana y el divisor se guardan con `QSettings`
  usando nombres estables. `Ajustar columnas` recalcula y persiste los anchos.
- `Rayo.svg` se conserva como estado `REVISAR`, no como error automatico.
  Los iconos especificos se muestran como `OK`; archivos inexistentes o
  comandos no registrados se marcan como `ERROR`.
- La persistencia usa `QSettings` y el panel de detalles usa un `QSplitter`,
  siguiendo los patrones documentados para PySide6/Qt.

### Pruebas

- Compilacion con FreeCADCmd 1.1.3: aprobada para `macro_launcher.py` y
  `macros.py`.
- Registro simulado de macros: 16 grupos y 122 metadatos; se detectaron iconos
  `ESPECIFICO` y `RAYO`, y los filtros devolvieron resultados coherentes.
- El primer intento de recargar y abrir el panel mediante MCP no respondio
  dentro de 90 s. Una segunda validacion identifico la contaminacion de
  `_MACRO_GROUPS` por la prueba segura y luego abrio el Panel real con el
  registro completo; el resultado esta documentado arriba.
- No se abrio, modifico ni guardo ningun archivo FCStd y no se actualizo
  `HISTORIAL_CAMBIOS.md`.

### Pendiente

La Fase 2 (conteo estructurado de exito/error por ejecucion) permanece fuera de
esta tarea.

## Resultado 2026-08-12 - reorganizacion de macros legacy e iconos

**Estado:** PROGRAMADO / MOVILIZADO / COMPILADO / PROBADO TECNICAMENTE;
VALIDACION VISUAL EN LA SESION DE MARCO PENDIENTE.

### Acciones realizadas

- `Objetos/Ordenar_Tomas_XY.FCMacro` y
  `Objetos/Ordenar_Tomas_XY_Horario.FCMacro` se movieron a
  `Tomacorrientes/`, preservando nombres y contenido.
- Se archivaron sin borrar:
  - `Objetos/HVAC_Etiqueta_Libre.FCMacro` en `Xcluidos/Objetos/`;
  - `Areas/actualizar_rectangulos_con_spreadsheet().FCMacro` en `Xcluidos/Areas/`;
  - `Areas/AnalizarAreasRectangularesDesdeMurosBIM.FCMacro` en `Xcluidos/Areas/`;
  - `Cajas/CajaEMT.FCMacro` en `Xcluidos/Cajas/`.
- `FacilArquitecturaWB/core/rectangular_area_analysis.py` y
  `ElectricCR/electriccr/features/caja_emt_octogonal.py` no se movieron ni
  modificaron por esta tarea.
- Se crearon iconos SVG para `Ordenar_Tomas_XY`,
  `Ordenar_Tomas_XY_Horario`, `Habilitar_Transform_en_Links_Dispositivos` y
  `Asignar_Tableros_y_Circuitos`.
- `Alinear` conserva deliberadamente `Rayo.svg`: el recurso de
  MEPWorkbenchCR no se copio ni se introdujo una dependencia cruzada.
- El smoke test rectangular fue adaptado para probar el motor reusable y
  verificar que el lanzador archivado permanece como respaldo.

El identificador automatico de comando cambia de prefijo `ElectricCR_Objetos_`
 a `ElectricCR_Tomacorrientes_` porque el registrador deriva el prefijo de la
 carpeta. El nombre de archivo, etiqueta y contenido de las macros se
 conservaron; una sesion limpia de FreeCAD debe registrar solamente el nuevo
 prefijo.

### Dependencias y registro

`ElectricCR/commands/macros.py` excluye `Xcluidos` del escaneo, por lo que las
cuatro herramientas archivadas no deben crear comandos. El registro de uso
historico conserva las rutas anteriores como evidencia; no se reescribieron
logs ni se interpretaron sus conteos como prueba funcional.

### Limitaciones y siguiente paso

### Pruebas realizadas

- `py_compile` de las dos macros movidas, `Habilitar_Transform...`,
  `Asignar_Tableros_y_Circuitos` y los smoke tests: aprobado.
- FreeCADCmd 1.1.3: `smoke_macro_reorganization.py`, aprobado; ambas macros
  conservaron su ordenamiento y los SVG pasaron XML.
- FreeCADCmd 1.1.3: `smoke_rectangular_areas_bim.py`, aprobado; el motor
  reusable funciona sin el lanzador visible archivado.
- Resolucion de iconos mediante `ElectricCR.commands.macros.icon_for_macro`:
  aprobada para los cuatro iconos nuevos; `Alinear` cae deliberadamente a
  `Rayo.svg` durante el registro.
- Registro simulado de `register_predefined_macros`: las dos macros movidas
  aparecen como `Tomacorrientes` y las cuatro archivadas no se registran.
- MCP: FreeCAD 1.1.3 respondio al preflight. La activacion del Workbench en la
  sesion GUI tardo mas de 90 s y dejo comandos antiguos en cache; no se declara
  validacion visual ni se reinicio la instancia del usuario.

Los avisos de arranque sobre la ruta ausente de
`AppData/Roaming/FreeCAD/v1-1/Mod/FacilArquitecturaWB` son externos a esta
tarea y no impidieron los smoke tests. No se abrio ni guardo ningun FCStd real
y no se actualizo `HISTORIAL_CAMBIOS.md`.

---

## Resultado 2026-08-11 - analisis rectangular BIM autocontenido

**Estado:** PROGRAMADO / COMPILADO / PROBADO / VERIFICADO_MCP;
VALIDACION DE MARCO PENDIENTE.

La copia historica `Xcluidos/Areas/AnalizarAreasRectangularesDesdeMurosBIM.FCMacro`
ya no se registra en la interfaz ni busca `AnalizarAreasDesdeMuroBIM.FCMacro`
fuera del repositorio. La implementacion
historica se localizo en `Scripts Varios/FacilArquitectura_BIM`, se leyo junto
con su motor de 28666 bytes y permanece intacta. Su logica fue incorporada a
`FacilArquitecturaWB/core/rectangular_area_analysis.py`; la macro visible valida
uno o varios muros y llama ese motor mediante una ruta relativa.

Se conservaron los cuatro modos de inferencia, `FA_RectangularAreas`,
`Spreadsheet_Analisis_Areas`, rectangulos Draft, rotulos, colores, propiedades
ElectricCR y enlaces a muros/ejes. No se creo `ArchSpace` y no se reemplazo el
flujo poligonal.

La prueba integral aprobo con Python de FreeCAD y mediante MCP en FreeCAD
1.1.3: seleccion GUI de dos muros, dos recintos, metadatos, hoja,
reejecucion, Undo/Redo, guardado/reapertura temporal, cielos, tomacorrientes e
iluminacion. No se modifico ningun FCStd original.

El Panel de macros dejo de usar `Rayo`: ahora usa
`ElectricCR/icons/Panel_Macros_ElectricCR.svg`. MCP confirmo la accion visible
en la barra `ElectricCR` con icono Qt no nulo. Clasificacion provisional de la
macro: OPERATIVA / ACTIVA / COMPROBADA-PARCIAL; decision ElectricCR POR
VERIFICAR FUNCIONALMENTE.

Commit/push: no.

## Resultado 2026-08-11 - recintos BIM como Draft Wires editables

**Estado:** IMPLEMENTADO Y PROBADO TECNICAMENTE EN FREECAD 1.1.3;
NO_VERIFICADO_MCP; VALIDACION VISUAL/FUNCIONAL DE MARCO PENDIENTE.

### Causa confirmada

`Areas/PoligonosRecintosDesdeArchWalls.FCMacro` creaba cada salida mediante
`doc.addObject("Part::Feature", ...)` y asignaba una cara estatica a `Shape`.
La deteccion geometrica funcionaba, pero no existian `Points`, `Closed` ni
`MakeFace` editables.

### Cambio realizado

- Se mantuvo intacta la deteccion de huellas y huecos de muros BIM.
- Los puntos se obtienen de `OuterWire.OrderedVertexes`, sin BoundingBox ni
  simplificacion del contorno.
- Cada recinto se crea con
  `Draft.make_wire(points, closed=True, face=True)`.
- Los puntos quedan en Z local 0 y la elevacion visual de 20 mm se aplica por
  `Placement` una sola vez.
- Se conservaron grupo, Spreadsheet, estilo, propiedades ElectricCR,
  metadatos FacilArquitectura y `FA_SourceWalls`.
- Se agregaron `FA_GeometrySource = AUTO_BIM` y
  `FA_GeometryType = DraftWire`.

### Pruebas

- La prueba previa reprodujo el tipo estatico `Part::Feature`.
- Smoke integral aprobado en FreeCAD 1.1.3 con tres recintos: rectangular,
  concavo y ocho vertices con segmento corto.
- Aprobados: cara, propiedades Draft, edicion de puntos, recompute, Undo/Redo,
  guardado/reapertura temporal, regeneracion sin duplicados, cielo suspendido
  y clasificacion espacial de tomacorrientes.
- `py_compile`: aprobado.
- `FacilArquitecturaWB.tests.test_ceiling_utils`: 7/7 aprobadas.

### Limitaciones

Una nueva ejecucion reemplaza correcciones manuales de `Points`. Los metadatos
geometricos propios son una instantanea de generacion y no se actualizan con un
observer. Preservar/conciliar ediciones manuales queda pendiente.

MCP rechazo dos conexiones con `WinError 10061`; no se declara verificacion
MCP ni visual. No se modifico ningun `.FCStd` original, ni se hizo commit o
push.

Clasificacion provisional: OPERATIVA / ACTIVA / COMPROBADA-PARCIAL.
Decision ElectricCR: POR VERIFICAR hasta la prueba real de Marco.

---

## Resultado 2026-08-10 - popup oscuro de Registrar acometida

**Estado:** CORREGIDO Y PROBADO TECNICAMENTE; VALIDACION REAL DE MARCO PENDIENTE.

### Causa confirmada

El formulario ya contenia `QComboBox QAbstractItemView` con fondo claro y
texto oscuro. Sin embargo, dentro del Task Panel de FreeCAD/Qt6 la lista del
combo se muestra como una ventana popup separada y puede quedar fuera del
arbol que hereda el QSS de `AcometidaRoot`. La captura real mostro que el tema
oscuro de FreeCAD prevalecia en esa ventana.

### Cambio realizado

- Se mantuvo el QSS general y el diseño azul/blanco existente.
- Se agrego `_acometida_combo_popup_qss()` con colores explicitos para vista,
  items normales, seleccionados y deshabilitados.
- `_style_acometida_combo_popup()` aplica el estilo directamente a la vista y
  al viewport nativos de cada `QComboBox`.
- No se sustituyeron controles, flechas, modelos ni delegados.
- No se modificaron formulas, tablas, estado, rutas ni Spreadsheet.

### Pruebas realizadas

- `py_compile`: correcto.
- Smoke test en FreeCAD 1.1.3 con tema oscuro y claro: correcto.
- El test ahora reparenta el formulario dentro de un `QDockWidget` `Tareas`,
  reproduciendo la topologia de Gui.Control.
- Los tres tabs y las listas emergentes se renderizaron; en el popup oscuro se
  observo fondo blanco, texto `#1f2d3d` y seleccion azul con texto blanco.

Archivos modificados:

- `Configuracion del proyecto/Registrar_Acometida_y_Ruta.FCMacro`;
- `ElectricCR/tests/smoke_registrar_acometida_qss.py`;
- documentacion de tarea y resultado.

No se modifico ningun FCStd ni `HISTORIAL_CAMBIOS.md`. Marco debe cerrar el
panel anterior y abrirlo de nuevo para cargar el codigo actualizado.

---

## Contexto anterior: centro de circulo en Ruta critica

### Resultado 2026-08-10 - centro de circulo en Ruta critica

**Estado:** IMPLEMENTADO Y PROBADO TECNICAMENTE; VALIDACION VISUAL DE MARCO PENDIENTE.

### Causa confirmada

`Conectar/selection_geometry.py` ya reconocia una curva circular y podia leer
`Curve.Center`, pero primero aceptaba `SelectionObject.PickedPoints`. En una
seleccion real ese punto esta sobre la circunferencia, por lo que el centro no
llegaba a utilizarse.

### Cambio realizado

- Las aristas circulares y arcos se resuelven primero mediante `Curve.Center`.
- El tipo de seleccion se registra como `CIRCLE_CENTER`.
- Las aristas lineales y las demas curvas mantienen la prioridad y fallbacks
  anteriores.
- La macro de ruta consume el helper comun sin duplicar geometria.

### Pruebas realizadas

- `py_compile`: correcto.
- Circulo Part real con un punto seleccionado sobre la circunferencia: el
  resolver devolvio exactamente el centro.
- Ruta completa desde un vertice hasta el circulo: `ECR_PuntoDestino` y la
  geometria terminaron en el centro, con `ECR_TipoSeleccionDestino` igual a
  `CIRCLE_CENTER`.
- Suite completa de Ruta critica en FreeCAD 1.1.3: `ALL_OK`, incluyendo
  seleccion de caras/aristas/vertices, radios, Draft, Undo/Redo y persistencia.

No se abrio ni guardo ningun documento original. Falta la validacion visual de
Marco antes de actualizar `HISTORIAL_CAMBIOS.md`.

---

## Contexto anterior: RectFromBoundaryLines con caras de muros BIM

### Resultado 2026-08-10 - RectFromBoundaryLines con caras de muros BIM

**Estado:** IMPLEMENTADO Y PROBADO TECNICAMENTE; VALIDACION VISUAL DE MARCO PENDIENTE.

### Causa confirmada

`Areas/RectFromBoundaryLines.FCMacro` recorria solamente subelementos cuyo
nombre comenzaba por `Edge`. Las selecciones `Face...` se ignoraban, aunque
pertenecieran a un muro BIM valido.

### Cambio realizado

- Se preservo el flujo anterior de 2 a N aristas lineales.
- Las caras verticales de muros Arch/BIM se proyectan como una linea limite en
  el plano XY.
- Para una cara horizontal, que contiene el lado interior y el exterior del
  muro, se elige el borde recto mas cercano al punto donde se hizo clic.
- Se reconocen `Arch Wall`, IFC Wall y objetos con `FA_Role = wall`.
- El rectangulo agrega `FA_SourceMethod` y `FA_SourceWalls` para conservar la
  relacion explicita con los muros, sin modificar estos ultimos.
- Selecciones mixtas de aristas y caras siguen el mismo calculo de rectangulo.

### Pruebas realizadas

- `py_compile` de macro y prueba: correcto.
- FreeCAD 1.1.3 con cuatro muros Arch reales: las caras interiores generaron
  un rectangulo de 3800 x 2800 mm y 10.64 m2.
- Cara superior: un clic cercano al borde interior selecciono ese borde y no
  el exterior.
- Regresion con cuatro aristas tradicionales: 4000 x 3000 mm.
- `FA_SourceWalls`, Undo/Redo y guardar/reabrir una copia temporal: correctos.
- El documento original de trabajo no se abrio, modifico ni guardo.

Archivo de prueba:
`ElectricCR/tests/smoke_rect_from_boundary_bim_faces.py`.

### Validacion pendiente

Marco debe confirmar en FreeCAD GUI el comportamiento sobre las paredes de su
modelo, en especial que el clic sobre una cara superior este cerca del borde
interior deseado. No se actualiza `HISTORIAL_CAMBIOS.md` en esta etapa.

---

## Contexto anterior: Ruta critica solo seleccionados

**Estado:** IMPLEMENTACION COMPLETA / PRUEBAS TECNICAS REALIZADAS / VALIDACION FUNCIONAL DE MARCO PENDIENTE.

**Fecha:** 2026-08-10, America/Costa_Rica.

**Alcance actual:** `Conectar/RutaCritica_Seleccionados.FCMacro`.

## Resultado - Ruta critica solo seleccionados

### Objetivo original

Conservar la herramienta existente y permitir que cada ruta salga y llegue a
la geometria realmente seleccionada, con radio de curva editable y reduccion
segura cuando la polilinea no admite el radio solicitado.

### Contexto y busqueda previa

- Se leyeron las instrucciones, mapa, estado, decisiones, flujo, revision de
  macros y tarea vigente de ElectricCR.
- Se revisaron por completo `RutaCritica_Seleccionados.FCMacro` y su macro
  base `medir_distancia_y_dibujar_ruta.FCMacro`.
- Se revisaron la resolucion de geometria y el calculo de radio de
  `Ajustar_Alimentador_o_Ramal_Manual.FCMacro`, ademas del helper de seleccion
  de MEPWorkbenchCR y los modulos Python existentes en `Conectar/`.
- `ElectricCR/MEJORAS_PENDIENTES.md` no existia en la rama activa, ramas
  locales/remotas disponibles ni historial Git local; se creo como registro
  vivo sin sustituir documentacion previa.
- La documentacion oficial de FreeCAD confirma que `getSelectionEx()` entrega
  `Object`, `SubObjects` y `SubElementNames`, y la API de
  `Gui::SelectionObject` expone los puntos de seleccion. La implementacion de
  Draft 1.1.3 confirma que `FilletRadius` se aplica al recomputar el Wire:
  [Draft get_selection_ex](https://freecad.github.io/SourceDoc/de/d75/group__draftutils.html),
  [Gui::SelectionObject](https://freecad.github.io/API/d1/d4e/classGui_1_1SelectionObject.html),
  [Draft make_wire](https://freecad.github.io/SourceDoc/d5/d7f/group__draftmake.html).
- El manual Greenlee consultado publica para EMT de 2 pulgadas un radio de
  9.59 pulgadas, aproximadamente 244 mm. Por eso 235 mm se adopta solamente
  como referencia inicial redondeada y editable, no como constante normativa:
  [Greenlee IM975REV14](https://greenlee-cdn.ebizcdn.com/media/IM975REV14.pdf).

### Causa confirmada

La macro obtenia primero `getSelection()`, reducia la seleccion a objetos,
eliminaba repetidos por `Object.Name` y calculaba ambos extremos mediante
`base.get_connection_point(obj)`. Asi se perdian cara, arista, vertice y punto
de clic, y dos caras del mismo objeto no podian formar una ruta. Ademas,
`FilletRadius` estaba fijado en 500 mm y no se comprobaba contra las longitudes
disponibles.

### Solucion implementada

- `Conectar/selection_geometry.py` centraliza la interpretacion geometrica:
  `Face.CenterOfMass`, `Vertex.Point`, punto de clic verificado sobre arista,
  centro de arista circular, punto medio por longitud/parametro y fallback de
  objeto inyectable.
- La identidad usa documento, objeto, subelemento, tipo y coordenada. Dos
  caras o vertices del mismo objeto permanecen como selecciones distintas.
- El primer registro aplanado de `SelectionEx` es origen; los restantes son
  destinos y mantienen el orden de `SelectionEx` y de sus subelementos.
- Un solo dialogo solicita `Altura ruta Z (mm)` y `Radio curva (mm)`, con
  valores iniciales 3000 y 235 mm. Radio 0 conserva la polilinea sin fillet.
- Se conserva `route_z_level()`, por lo que la ruta no baja por debajo de los
  endpoints cuando la altura solicitada es menor.
- El radio maximo uniforme considera cuanto consume cada curva en los tramos
  adyacentes. Si el radio solicitado no cabe, se reduce con margen; si no hay
  esquina util, se mantiene la ruta sin curva y se registra la advertencia.
- Tras recomputar, si Draft no produjo ninguna arista curva, la propiedad se
  vuelve a 0 y la ruta ortogonal se conserva.
- Los Wires guardan nombres internos, tipos y subelementos de origen/destino,
  puntos, altura, radio solicitado/efectivo y generador como metadatos. Los
  objetos se guardan por nombre `PropertyString`, no `PropertyLink`, para no
  introducir ciclos DAG con los grupos `Conexiones`.
- Se agrego una transaccion por ejecucion y se conservaron nombres, grupos,
  multiples destinos, omision de rutas/anotaciones, logs, recompute y
  `USE_RESULTS_SHEET=False`.
- El ajuste manual ahora delega la resolucion de subgeometria y el calculo de
  radio maximo al mismo helper; no quedan dos implementaciones independientes
  de esas reglas.
- La dependencia historica de la macro base `.FCMacro` no se amplio ni se
  modifico en esta tarea; el nuevo codigo comun vive en un modulo `.py`.

### Archivos

Modificados:

- `Conectar/RutaCritica_Seleccionados.FCMacro`.
- `Conectar/Ajustar_Alimentador_o_Ramal_Manual.FCMacro`.
- `ElectricCR/TAREA_ACTUAL.md`.
- `ElectricCR/RESULTADO_CODEX.md`.
- `ElectricCR/REVISION_MACROS.md`.

Creados:

- `Conectar/selection_geometry.py`.
- `ElectricCR/tests/smoke_ruta_critica_seleccionados.py`.
- `ElectricCR/MEJORAS_PENDIENTES.md`.
- `Conectar/Backups/ruta_critica_seleccion_20260810/` con las dos versiones
  previas y sus hashes.

No se modifico ningun documento `.FCStd` de proyecto y no se actualizo
`HISTORIAL_CAMBIOS.md`.

### Pruebas tecnicas

Se ejecuto `smoke_ruta_critica_seleccionados.py` mediante FreeCADCmd 1.1.3.
Resultado final:

```text
[RUTA-SEL-TEST] FreeCAD 1.1.3
[RUTA-SEL-TEST] selection semantics OK
[RUTA-SEL-TEST] route height and radius math OK
[RUTA-SEL-TEST] shared manual-adjust helper OK
[RUTA-SEL-TEST] Draft geometry OK
[RUTA-SEL-TEST] macro/save/reopen/undo/redo OK
[RUTA-SEL-TEST] ALL_OK
```

Casos cubiertos:

- objeto a objeto;
- cara a cara y cara a objeto;
- vertice a cara;
- arista/punto fiable y fallback de arista;
- centro de arista circular;
- dos caras del mismo objeto;
- un origen con varios destinos;
- altura menor y mayor que los endpoints;
- radio 235 mm, otro radio, 0 y radio excesivo para una ruta corta;
- geometria Draft real con aristas curvas;
- metadatos;
- ejecucion repetida;
- Undo/Redo;
- guardar, cerrar y reabrir una copia temporal.

Tambien se abrio el dialogo con Qt en modo `offscreen`, se acepto
automaticamente y devolvio `(4321.0, 235.0)`, confirmando que ambos controles
se construyen y entregan sus valores en FreeCAD 1.1.3.

Los avisos de arranque de `DevPathsBootstrap` y la ruta local ausente de
`FacilArquitecturaWB` son externos a esta macro y no impidieron `ALL_OK`.

### Resultado y limites

- Rol funcional: OPERATIVA.
- Madurez: CANDIDATA.
- Resultado comprobado: COMPROBADA-PARCIAL.
- Decision ElectricCR: POR VERIFICAR.
- Relacion con herramientas anteriores: mejora la macro existente y comparte
  un helper con Ajustar Ruta; no crea otra macro especializada ni sustituye la
  macro base.

La prueba headless no puede generar una seleccion real con raton porque
`FreeCADGui.Selection` no esta disponible en FreeCADCmd. Falta que Marco
compruebe desde FreeCAD GUI el orden real de sus selecciones, el punto de clic
sobre aristas, el dialogo y el resultado visual de las curvas. Por ello no se
declara aceptada ni integrada.

---

## Resultado anterior - legibilidad del panel Registrar acometida y ruta

## Resultado - legibilidad del panel Registrar acometida y ruta

### Contexto y busqueda previa

- Se leyeron las instrucciones y documentos vigentes de ElectricCR, el
  contrato comun de arquitectura y la macro completa.
- `ElectricCR/MEJORAS_PENDIENTES.md` no existe en la rama activa ni aparece
  en el historial Git disponible.
- No se encontro un helper comun de estilos reutilizable. Solo existe otro
  QSS local casi identico en `Conectar_Cajas_a_Tablero_Auto.FCMacro`, con el
  mismo problema de contraste; no se reutilizo.
- Se reviso la documentacion oficial de Qt sobre cascada QSS, colores de
  primer plano/fondo, seleccion, `QCheckBox`, vistas de items y pestanas, asi
  como la guia oficial de compatibilidad Qt/PySide para addons FreeCAD 1.x.

### Causa confirmada

El QSS local imponia fondos blancos a `QComboBox`, `QDoubleSpinBox`,
`QSpinBox` y `QLineEdit`, pero no imponia su color de texto. `QCheckBox`, las
pestanas no seleccionadas y el popup de los combos tampoco tenian colores
completos. Por la cascada de estilos, un tema oscuro de FreeCAD podia aportar
texto o fondos oscuros incompatibles con el diseno claro del panel.

### Cambios aplicados

- Texto oscuro explicito en combos, spinboxes, line edits, checkboxes y
  pestanas.
- Texto y fondos diferenciados para controles y pestanas deshabilitados.
- Fondo blanco, texto oscuro, seleccion azul y texto seleccionado blanco en
  `QComboBox QAbstractItemView`.
- Regla explicita para items seleccionados del popup.
- Fondo transparente para labels y checkboxes, evitando que hereden bloques
  oscuros del tema anfitrion.
- Fondo blanco explicito en las tres paginas mediante el nombre interno
  `AcometidaTabPage`.
- Flechas de combos, indicadores de checkboxes, botones de spinbox y botones
  azules no fueron redisenados.

No se modificaron formulas, factores, tablas AWG, breaker, caida de tension,
rutas, Spreadsheet, `_acometida_state.json`, seleccion de objetos, botones ni
flujo Task Panel/dialogo.

### Pruebas realizadas

Se agrego `ElectricCR/tests/smoke_registrar_acometida_qss.py` y se ejecuto con
FreeCAD 1.1.3. El test crea solamente un documento temporal en memoria,
instancia el formulario y valida:

- altura de ruta 2500.0 y area total visibles;
- texto presente en todos los combos solicitados;
- texto completo de los tres checkboxes;
- nombres de las tres pestanas;
- resultados de Demanda Auto y controles de Seleccion Final;
- presencia de todas las reglas QSS requeridas;
- render de las tres pestanas y del popup bajo un tema oscuro simulado;
- render equivalente bajo un tema claro simulado.

Resultado: `PASS Registrar_Acometida_y_Ruta QSS`. La inspeccion de las ocho
capturas confirmo texto legible y seleccion azul con texto blanco en ambos
temas. Los avisos de arranque sobre `DevPathsBootstrap` y un directorio local
ausente de `FacilArquitecturaWB` son externos a esta macro.

### Estado provisional

- Rol funcional: OPERATIVA.
- Madurez: ACTIVA.
- Resultado comprobado: COMPROBADA-PARCIAL.
- Decision ElectricCR: POR VERIFICAR, porque no se hizo una revision
  electrica funcional de la macro y falta la validacion visual de Marco.
- Relacion con herramientas anteriores: corrige la interfaz existente; no la
  reemplaza, duplica ni refactoriza.
- `MAPA_WORKBENCH.md` y `REVISION_MACROS.md`: sin cambios, porque no cambio la
  arquitectura ni se completo una revision macro por macro.
- `HISTORIAL_CAMBIOS.md`: no actualizado.

La version previa y su hash estan respaldados en
`Configuracion del proyecto/Backups/legibilidad_acometida_20260810/`.

---

## Resultado anterior - altura de luminarias Link

### Fallo reproducido

La altura elegida en el dialogo llegaba a `altura_rel`, pero se reemplazaba
dentro del ciclo por area. Si el area tenia `LightingMountHeight`, se usaba
ese valor; de lo contrario se usaba la altura predeterminada del registro.
Para `Luminaria 60x60` el resultado recurrente era 3000 mm.

### Correccion

- `LightingTypeKey` sigue determinando el tipo de luminaria de cada area.
- La altura escrita en el dialogo determina `AlturaRel` del maestro 3D para
  todas las areas procesadas en esa ejecucion.
- El maestro se marca para recomputacion despues de asignar la altura.
- El registro de consola ahora muestra la altura efectiva por area.
- Se conservo la representacion dual: simbolo 2D local en Z=0 y modelo 3D a
  `AlturaRel`.

### Prueba automatica

Se agrego `ElectricCR/tests/smoke_colocar_luminarias_link_altura.py` y se
ejecuto con FreeCAD 1.1.3. Comprueba:

- un area con tipo asignado distinto del tipo general del dialogo;
- prioridad de 5000 mm elegidos sobre `LightingMountHeight=3000 mm`;
- maestros `App::Link` a 2500 y 5000 mm;
- `Shape.BoundBox.ZMin=0` en ambos casos por el simbolo 2D;
- aumento de `Shape.BoundBox.ZMax` de 2600 a 5100 mm;
- enlace hacia el maestro correcto;
- `Placement.Base.z=0` de la instancia;
- persistencia de la altura, geometria y enlace despues de guardar y reabrir
  un FCStd temporal.

La prueba termino `PASS`. Los avisos de `DevPathsBootstrap` y del directorio
ausente de `FacilArquitecturaWB` pertenecen al arranque local de FreeCADCmd y
no afectaron la comprobacion.

### Respaldo

La version anterior y su SHA256 estan en
`Iluminacion/Backups/altura_link_20260810/`.

No se modifico ni guardo ningun documento de proyecto. No se actualizo
`HISTORIAL_CAMBIOS.md` porque falta la validacion visual de Marco.

---

**Alcance anterior:** Motor general de alimentadores y backbone, compatibilidad, interfaz y pruebas de `Conectar/`.

## Resultado de la consolidacion 2026-08-08

La auditoria que sigue en este documento se uso como base. No se asumio que
la macro mas nueva fuera mejor: se extrajeron las capacidades comunes y se
conservaron las versiones previas en un respaldo verificable.

### Arquitectura implementada

Se creo `ElectricCR/electriccr/connections/` con responsabilidades separadas:

| Modulo | Responsabilidad |
|---|---|
| `assignments.py` | Resolver circuito, tablero aguas arriba y aliases heredados sin inventar asignaciones. |
| `panels.py` | Detectar tableros reales, excluir rutas y obtener/distribuir puntos en la cara superior del `Shape`. |
| `ports.py` | Leer `Ports` tipados o `PuertosJSON`, detectar ocupacion y elegir un puerto disponible. |
| `routing.py` | Ruta ortogonal directa, ruta guiada opcional, carriles, simplificacion, retroceso y curvas. |
| `feeders.py` | Circuito/equipo/desconector/tablero secundario hacia cualquier tablero asignado. |
| `backbone.py` | Caja octagonal hacia caja octagonal dentro de cualquier circuito. |

Los objetos de ruta quedan en grupos superiores bajo `ElectricCR_Conexiones`.
El grupo de circuito se conserva mediante `PropertyLink`; no se introduce la
relacion inversa grupo-hijo que anteriormente podia formar ciclos DAG.

### Herramientas visibles

La barra normal `Conectar` queda orientada a tres comandos:

- `Conectar Alimentadores...`;
- `Conectar Circuito / Backbone...`;
- `Ajustar Ruta...`.

Las variantes TP, TCOM, HVAC, tablero-tablero, TCOM completa y el motor v1 se
conservan como wrappers o dependencias en `Conectar Legacy`. No se borraron.
Los identificadores de comando ya no dependen de la fecha de modificacion del
archivo o del icono.

### Compatibilidad y deuda conservada

- TP y TCOM Top ahora son wrappers del mismo motor general.
- Los backbones TP y TCOM son wrappers del mismo motor general.
- `Preparar_Red_TCOM_Completa` es un orquestador de los servicios Python.
- `Conectar_Desconectores_HVAC_a_TP` conserva nombre y propiedades historicas,
  pero resuelve asignacion y geometria mediante servicios comunes.
- `Conectar_Tableros_Cara_Superior` usa el mismo motor de equipos.
- El alimentador de `Preparar_Red_Iluminacion_Completa` ya no carga la macro TP
  como biblioteca.
- `alimentadores_backend.py`, `ramales_backend.py` y
  `Conectar_Cajas_a_Tablero_Auto.FCMacro` permanecen como
  `LEGACY-DEPENDENCIA` para flujos de ramales que no fueron sustituidos en esta
  tarea. No son usados por el nuevo alimentador/backbone.
- El wrapper HVAC aun carga la macro de tabla de tableros mediante `runpy` para
  compatibilidad de calculo; no es una dependencia geometrica.

### Respaldo

Las versiones previas y sus hashes SHA256 estan en:

`Conectar/Backups/consolidacion_conexiones_20260808/INVENTARIO.txt`

El inventario incluye tambien el registro de comandos y el orquestador de
iluminacion antes de retirar su dependencia TP.

### Investigacion previa

Se revisaron la API oficial `ArchPipe` de FreeCAD y el proyecto Quetzal/Dodo.
Proveen objetos y operaciones utiles para tuberias/conectores, pero no resuelven
la asignacion electrica circuito-tablero, las guias, los carriles, la reserva de
puertos ni la idempotencia requerida. Por ello se conservaron `Shape`, enlaces
y transacciones nativas, y el ruteo electrico permanece en ElectricCR.

- https://freecad.github.io/SourceDoc/de/d7d/namespaceArchPipe.html
- https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/BIM/Arch.py
- https://github.com/EdgarJRobles/quetzal

### Pruebas realizadas

Version ejecutada: FreeCAD 1.1.3, revision 20260725.

| Prueba | Resultado |
|---|---|
| Sintaxis de modulos, wrappers, comandos y pruebas | OK, 23 archivos. |
| Alimentador directo sin guia | OK. |
| Alimentador con guia seleccionada | OK, modo `GUIADO`. |
| Mismo motor para TP, TCOM, TS y TAA | OK. |
| Cara superior real y varias llegadas distribuidas | OK. |
| Puerto ocupado con alternativa disponible | OK. |
| Segunda ejecucion y actualizacion por movimiento | OK, sin duplicados. |
| Backbone TP y TCOM | OK, mismo motor. |
| Undo/Redo | OK con `Document.UndoMode=1`. |
| Guardar, cerrar y reabrir | OK. |
| Compatibilidad de desconectores y ranuras historicas | OK. |
| Interfaz reducida y IDs estables | OK. |
| Selector de nueve modos del Workbench | OK; se corrigio una expectativa obsoleta del test. |
| Copia de Puriscal | OK: 3 tableros reales, 23 circuitos, 23 alimentadores y 13 tramos de backbone de muestra. |
| Red completa de iluminacion en salida temporal | OK: 4 circuitos, 93 ramales y 4 alimentadores actualizados. |

Archivos de prueba principales:

- `ElectricCR/tests/smoke_connections_general.py`;
- `ElectricCR/tests/smoke_connections_puriscal_copy.py`;
- `ElectricCR/tests/test_connections_interface.py`;
- `ElectricCR/tests/smoke_distributed_disconnect_feeders.py`;
- `ElectricCR/tests/smoke_red_iluminacion_completa.py`.

### Modelo Puriscal y limitaciones

El original `Puriscal 03-08-2026.FCStd` no se guardo ni se sobrescribio. Su
SHA256 antes de las pruebas fue
`C9F64EF66574180CF77CD32A54D71F3812D160B92FF7F57EE7B4CF9B97E72EFE`.
Las pruebas se guardaron bajo `%LOCALAPPDATA%/Temp`.

El documento original ya informa `The graph must be a DAG` al abrir y deja
objetos HVAC/Text tocados al recomputar. Los mismos avisos aparecen en las
copias, pero no impidieron crear, actualizar, guardar y reabrir las rutas. No
se modifico el modelo para corregir esa deuda.

FreeCADCmd tambien informa dos problemas externos a esta tarea:

- `Mod/DevPathsBootstrap/Init.py` usa `__file__` en un contexto donde no existe;
- falta la ruta configurada `.../Mod/FacilArquitecturaWB/FacilArquitecturaWB`.

### Clasificacion provisional

El motor general queda `NUCLEO / CANDIDATA / COMPROBADA-PARCIAL`. Las pruebas
tecnicas son suficientes para retirar wrappers de la barra normal, pero no para
declarar la experiencia visual aceptada. `HISTORIAL_CAMBIOS.md` no se actualizo;
falta que Marco valide las rutas desde la interfaz grafica.

## Anexo: auditoria comparativa previa

## 1. Resumen ejecutivo

La familia no contiene una sucesion lineal donde cada archivo nuevo reemplaza al anterior. Contiene herramientas para problemas distintos y dos generaciones parcialmente solapadas.

Hallazgos principales:

1. `Conectar_Alimentadores_a_Tablero_Auto.FCMacro` era un controlador especializado en alimentadores. Su motor real estaba repartido entre `alimentadores_backend.py` y `Conectar_Cajas_a_Tablero_Auto.FCMacro`.
2. `Conectar_Cajas_a_Tablero_Auto.FCMacro` era un motor monolitico general: planeaba bajantes, backbone y alimentador, gestionaba puertos, rutas guia, perimetro, curvas, metadatos y grupos.
3. Las macros posteriores TP/TCOM resuelven un subconjunto: una caja origen por circuito hacia la cara superior de un tablero concreto. No heredan rutas guia, orden manual por secciones ni la distribucion general de carriles.
4. Las macros posteriores si aportan mejoras observables: verifican una cara superior real del `Shape`, crean enlaces explicitos mediante propiedades `Link`, usan claves simples para actualizar objetos y, en TCOM, reservan puertos ya usados.
5. `Conectar_Octogonales_Ortogonal_por_Circuito_TP.FCMacro` no es un alimentador: crea el backbone interno caja-caja mediante un arbol de expansion minima. Debe evaluarse aparte.
6. `Ajustar_Alimentador_o_Ramal_Manual.FCMacro` tampoco genera la red inicial: modifica localmente una ruta existente y contiene la logica mas rica para preservar tramos, evitar retrocesos y mantener curvas.
7. La auditoria encontro una ruptura de integridad: `alimentadores_backend.py` y `ramales_backend.py` cargan en tiempo de ejecucion `Conectar_Cajas_a_Tablero_Auto.FCMacro`, eliminado de `HEAD/main` en el commit `727b151` del 2026-06-12. La dependencia ya fue recuperada localmente, pero aun no esta incorporada a un commit.
8. Antes de la recuperacion, una copia limpia no podia ejecutar las API que llaman `cargar_backend_v1()`. El arbol de trabajo local vuelve a contener la dependencia; falta probar el flujo en FreeCAD y versionar la recuperacion si se aprueba.
9. La logica mas general esta en la combinacion historica `Conectar_Cajas_a_Tablero_Auto.FCMacro` + `alimentadores_backend.py`; la logica mas clara para cara superior real esta en TP Top; la logica mas desarrollada para correccion local esta en Ajuste Manual.
10. No hay evidencia suficiente para decidir todavia que herramienta debe sustituir a otra. Se aplica la regla: **nueva no significa mejor**.

Durante la auditoria no se modifico codigo. Posteriormente se recuperaron los dos archivos historicos por solicitud expresa de Marco. No se actualizo `HISTORIAL_CAMBIOS.md`.

## 2. Mapa funcional de la familia Conectar

| Categoria | Problema | Herramientas principales |
|---|---|---|
| A. Alimentadores hacia tablero | Caja principal del circuito -> tablero | `Conectar_Alimentadores_a_Tablero_Auto.FCMacro`, `alimentadores_backend.py`, parte de `Conectar_Cajas_a_Tablero_Auto.FCMacro`, TP Top y TCOM Top |
| B. Backbone interno | Caja -> caja -> caja dentro del circuito | Parte de `Conectar_Cajas_a_Tablero_Auto.FCMacro`, `ramales_backend.py`, `Conectar_Octogonales_Ortogonal_por_Circuito_TP.FCMacro` |
| C. Ramales | Dispositivo -> caja y fallbacks locales | `Conectar_Circuitos_Ramales_Auto.FCMacro`, `ramales_backend.py`, parte de la v1 |
| D. Ajuste manual | Corregir una ruta ya creada sin redibujar toda la red | `Ajustar_Alimentador_o_Ramal_Manual.FCMacro` |
| E. Infraestructura auxiliar | Proponer canales o rutas guia | `Proponer_Rutas_Guia_Auto.FCMacro` y rutas seleccionadas por el flujo anterior |

Estas categorias comparten geometria ortogonal, puertos y curvas, pero no son el mismo problema funcional.

## 3. Arquitectura actual

La arquitectura observable tiene tres formas distintas:

```text
Generacion anterior de alimentadores
Conectar_Alimentadores_a_Tablero_Auto.FCMacro [recuperada localmente]
  -> alimentadores_backend.py [presente]
     -> Conectar_Cajas_a_Tablero_Auto.FCMacro [recuperada localmente]

Ramales generales
Conectar_Circuitos_Ramales_Auto.FCMacro [presente]
  -> ramales_backend.py [presente]
     -> Conectar_Cajas_a_Tablero_Auto.FCMacro [recuperada localmente]

Generacion posterior especializada
TP Top [presente, autocontenida]
  -> TCOM Top carga el codigo de TP Top
  -> Backbone TP carga el codigo de TP Top
     -> Backbone TCOM carga Backbone TP y TCOM Top
```

La primera arquitectura intentaba separar UI y motor, pero la extraccion quedo incompleta. La dependencia ausente ya fue recuperada localmente. La tercera evita ese backend, aunque usa archivos `.FCMacro` como bibliotecas Python.

## 4. Generacion anterior de alimentadores

### `Conectar/Conectar_Alimentadores_a_Tablero_Auto.FCMacro`

**Problema:** generar solamente el alimentador de cada circuito hacia un tablero, usando rutas guia y una distribucion coordinada.

**Entrada:** documento activo; tablero seleccionado o persistido; caras seleccionadas; una o varias polilineas guia; grupos de circuito detectados; orden manual opcional; altura, radio, separacion e inicio del abanico.

**Salida:** alimentadores EMT agrupados bajo cada circuito; metadatos de circuito, extremos, puertos y ruta; configuracion persistida.

**Flujo:**

1. Carga `alimentadores_backend.py`.
2. Resuelve tablero, caras y rutas guia.
3. Detecta circuitos y construye un plan por circuito.
4. Elige una caja alimentadora.
5. Asigna seccion, carril y punto de entrada al tablero.
6. Reserva puertos usados y genera o recalcula el alimentador.
7. Reutiliza o limpia grupos generados.

**Dependencias directas:** `alimentadores_backend.py`, FreeCAD, FreeCADGui y Qt.

**Dependencias indirectas:** `Conectar_Cajas_a_Tablero_Auto.FCMacro`, `component_classifier.py`, utilidades de agrupacion y, opcionalmente, NetworkX.

**Funciones externas reutilizadas:** `candidate_circuit_groups()`, `sort_circuit_groups_manual()`, `collect_circuit_objects()`, `build_plan_for_circuit()`, `feeder_source_from_plan()`, `feeder_lane_map()`, `connect_pair()`, reserva de puertos y limpieza del backend.

**Estado observable:** recuperado en el arbol de trabajo desde `b7d4fef`, todavia sin commit. El registro historico acumula 182 ejecuciones y ultima ejecucion el 2026-03-28, pero no distingue uso operativo de iteraciones de desarrollo.

### `Conectar/alimentadores_backend.py`

**Problema:** ofrecer una API mas pequena para alimentadores sin duplicar inmediatamente el motor maduro de la v1.

**Entrada:** grupos, objetos, cajas, tablero, guias, configuracion y mapas de carriles.

**Salida:** planes, fuente alimentadora, carriles, offsets, puntos de entrada, conexiones y limpieza de grupos.

**Capacidades propias confirmadas:** carriles por guia/seccion, direccion local de la guia, seleccion mejorada de caja alimentadora, parches para cara Top/Bottom, radio efectivo, stub de puerto, entrada guiada, mapa manual de salidas y limpieza de grupos duplicados.

**Dependencia critica:** casi toda la API delega funciones a `cargar_backend_v1()`, que busca exactamente `Conectar_Cajas_a_Tablero_Auto.FCMacro` en la misma carpeta.

**Funciones externas reutilizadas:** entre otras, `_default_config()`, `_selection_context()`, `_candidate_circuit_groups()`, `_build_plan_for_circuit()`, `_feeder_lane_map()`, `_route_rect_for_circuit()`, `_connect_pair()`, `_reserve_existing_ports()` y `_delete_autoroute_feeders()` de la v1.

**Estado observable:** presente y con su dependencia fisica recuperada localmente. Sigue sin ser un modulo autonomo y su ejecucion funcional en FreeCAD queda por verificar.

### `Conectar/Conectar_Cajas_a_Tablero_Auto.FCMacro`

**Problema:** resolver en una sola herramienta bajantes, backbone, alimentador y agrupacion para circuitos electricos.

**Entrada:** seleccion o grupos de circuito; dispositivos; cajas; tablero/ancla; caras; rutas guia; configuracion geometrica y de usuario.

**Salida:** Draft Wires o polilineas de canalizacion con `CircuitoID`, nombres de origen/destino, puertos, `LinkKind`, `AutoRouteKey`, radio, diametro y generador; grupos `Tuberias_EMT`; estadisticas y log de depuracion.

**Flujo:**

1. Clasifica circuitos, dispositivos, cajas, tablero y guias.
2. Relaciona dispositivos con cajas mediante claves de origen.
3. Planea bajantes y fallbacks.
4. Ordena cajas y crea backbone.
5. Elige la caja mas conveniente para el alimentador.
6. Selecciona y reserva puertos.
7. Traza por perimetro, ortogonal o por guia.
8. Distribuye carriles y puntos sobre las caras del tablero.
9. Aplica radio posible, metadatos e idempotencia por clave.

**Funciones externas reutilizadas:** clasificacion desde `component_classifier.py`, agrupacion desde `conexiones_grouping.py` cuando esta disponible y construccion/edicion de wires mediante FreeCAD Draft/Part.

**Estado observable:** recuperado en el arbol de trabajo desde `b7d4fef`, todavia sin commit. Fue documentado en marzo como backend legado estable que debia conservarse por dependencia activa. El registro historico acumula 137 ejecuciones hasta el 2026-03-26. La documentacion tambien registra problemas recurrentes de cruces y llegada al tablero, por lo que "estable" describe la base recuperada, no perfeccion geometrica.

## 5. Generacion posterior TP/TCOM

### `Conectar/Conectar_Circuitos_TP_a_Cara_Superior_Tablero.FCMacro`

**Problema:** conectar cada circuito `TP-001..TP-018` desde la caja octogonal mas cercana hasta una ranura fija de la cara superior real del tablero TP.

**Entrada:** un unico tablero TP seleccionado o detectable; grupos TP con cajas; parametros de altura, separacion, despeje, radio y stub; filtro opcional `circuit_ids` para ejecucion programatica.

**Salida:** un `Part::Feature` por circuito, grupo `Alimentadores TP-xxx` y propiedades `CajaOrigen`, `TableroDestino`, `PuertoOrigen`, puntos, cara, slot, altura y `RutaJSON`.

**Flujo:** detecta TP; busca una cara horizontal real en `Shape.Faces`; encuentra circuitos; toma la caja mas cercana; elige puerto hacia el tablero; asigna una matriz fija de 2 x 9; enruta por un carril exterior segun lado; crea o actualiza por `CircuitoID`.

**Capacidades mejoradas:** valida la cara mediante normal, cota y pertenencia; usa `PropertyLink`; actualiza el objeto existente; transaccion unica; limpieza de grupos vacios.

**Capacidades no heredadas:** rutas guia, caras alternativas, orden manual, secciones, mapa manual de salidas, carriles por guia y seleccion espacial avanzada de caja.

**Funciones externas reutilizadas:** solamente API de FreeCAD/Part/Qt; su logica geometrica principal esta dentro de la propia macro.

**Estado observable:** presente desde el commit `c33efce` del 2026-08-06. No aparece en la telemetria consolidada disponible; no se encontro una prueba automatica ni una validacion visual registrada en esta auditoria.

### `Conectar/Conectar_Circuitos_TCOM_a_Cara_Superior_Tablero.FCMacro`

**Problema:** el mismo subconjunto para `TCOM-01..TCOM-05` y tablero TCOM.

**Entrada/salida:** equivalentes a TP, con deteccion por `Codigo=TCOM` o etiqueta, y cajas asociadas por grupo o `CircuitosJSON`.

**Diferencias confirmadas:** distribuye cinco puntos a lo largo del eje mayor de la cara; consulta puertos ya usados; puede advertir y reutilizar un puerto si todos estan ocupados.

**Dependencia directa:** lee, compila y ejecuta `Conectar_Circuitos_TP_a_Cara_Superior_Tablero.FCMacro` para reutilizar deteccion de cara, puertos, ruta, wire redondeado y utilidades.

**Funciones externas reutilizadas:** `_top_face_from_panel()`, `_is_real_octagonal_box()`, `_walk_group()`, `_box_ports_world()`, `_source_port_toward_panel()`, `_nearest_source_box()`, `_route_side()`, `_route_points()`, `_rounded_wire()` y `_unique_name()` de TP Top.

**Estado observable:** presente; sin registro de uso en la telemetria consolidada.

### Comparacion de generaciones

Las versiones TP/TCOM no reemplazan realmente a la generacion anterior. Simplifican un caso concreto y cambian la estrategia:

- anterior: tablero generico + caras seleccionables + rutas guia + carriles coordinados + orden manual;
- posterior: prefijo fijo + tablero fijo + cara Top obligatoria + slots fijos + ruta ortogonal directa.

La posterior mejora la comprobacion de la cara real y la trazabilidad mediante enlaces. Pierde generalidad y capacidades de coordinacion. Ambas generaciones contienen valor preservable.

## 6. Backbone de circuitos

### `Conectar/Conectar_Octogonales_Ortogonal_por_Circuito_TP.FCMacro`

**Problema:** enlazar todas las cajas octogonales dentro de cada circuito TP, sin conectar al tablero ni a los dispositivos.

**Entrada:** grupos TP y sus cajas; alimentador TP existente opcional para escoger la raiz; altura, radio, stub y diametro.

**Salida:** `Part::Feature` caja-caja dentro de `Ramales EMT TP-xxx`, con `ConexionKey`, `CajaOrigen`, `CajaDestinoLink`, puertos, puntos, `RutaJSON` y estado.

**Flujo:** detecta cajas mediante las funciones de TP Top; elige como raiz la caja usada por el alimentador; construye un arbol de expansion minima; reserva puertos ocupados por bajantes y alimentadores; evalua dos rutas ortogonales y penaliza cercania a cajas intermedias; crea o actualiza enlaces y elimina obsoletos.

**Funciones externas reutilizadas:** deteccion de circuitos, lectura de puertos, simplificacion, wire redondeado y nombres unicos desde TP Top.

**Estado observable:** presente; no tiene registro de uso en la telemetria consolidada. Su estrategia MST es distinta del orden perimetral del motor anterior y ninguna puede declararse superior sin validacion visual.

### `Conectar/ramales_backend.py`

**Problema:** centralizar el planeamiento y trazado de la red interna para `Conectar_Circuitos_Ramales_Auto.FCMacro`.

**Entrada:** grupo de circuito; dispositivos; cajas; relaciones caja-dispositivo; configuracion; grupo destino y puertos usados.

**Salida:** plan tipado (`drop_box`, fallback, `backbone`, variantes de iluminacion), orden de cajas y wires de ramal.

**Capacidades propias:** clasificacion de luminarias/apagadores, orden por recintos, troncal de iluminacion, deteccion de solapamiento con troncal existente, deteccion de retroceso en extremos y cruce del interior de cajas.

**Dependencia critica:** tambien carga `Conectar_Cajas_a_Tablero_Auto.FCMacro` como modulo y delega clasificacion, orden perimetral, rectangulo de ruta, claves, reserva de puertos y trazado final.

**Funciones externas reutilizadas:** `_import_component_classifier()`, `_map_boxes_by_source()`, `_source_key()`, `_order_boxes_by_perimeter()`, `_route_rect_for_circuit()`, `_collect_existing_route_keys()`, `_reserve_existing_ports()` y `_connect_pair()` de la v1.

**Nota de duplicacion:** `Conectar_Circuitos_Ramales_Auto.FCMacro` conserva una segunda implementacion interna de varias operaciones de plan, perimetro y wire. El flujo actual de `procesar_circuito()` usa el backend compartido, por lo que una porcion considerable de esa implementacion local parece codigo residual o fallback no invocado por el camino principal.

## 7. Ajuste manual

### `Conectar/Ajustar_Alimentador_o_Ramal_Manual.FCMacro`

**Problema:** mover localmente el extremo de un alimentador o ramal existente hacia una referencia seleccionada, conservando la mayor parte posible de la ruta.

**Entrada:** una ruta existente y una referencia: vertice, borde, cara, punto seleccionado u objeto/caja.

**Salida:** modifica `Points` o `Shape` del objeto existente y ajusta `FilletRadius`/`RadioCurvatura`; no crea una red nueva.

**Flujo:** identifica ruta y objetivo sin depender del orden de seleccion; determina extremo editable y extremo de tablero; genera candidatos locales; preserva prefijo/sufijo; penaliza zigzag, falta de capacidad de fillet y retroceso; colapsa escaleras y backtracking; aplica el mejor candidato en una transaccion.

**Capacidades unicas:** corte dentro de segmentos, reenganche congelado, repeticion de la geometria guia existente, preservacion del extremo de tablero, salida perpendicular desde caja y calculo del radio maximo posible.

**Funciones externas reutilizadas:** API de seleccion y transacciones de FreeCAD y `Part.makePolygon()` como fallback; no carga otro backend o `.FCMacro`.

**Limitacion confirmada:** al modificar la geometria no actualiza propiedades como `RutaJSON`, `PuntoOrigen` o `PuntoDestino`. Es posible que la geometria visible y ciertos metadatos queden desincronizados.

**Estado observable:** presente. Las notas registran que Marco aprobo visualmente un resultado y el historial de uso contiene 100 ejecuciones hasta el 2026-03-26; la cantidad puede incluir depuracion repetida.

## 8. Matriz comparativa

Leyenda: `SI`, `NO`, `PARCIAL`, `NO APLICA`, `POR CONFIRMAR`.

| Capacidad | Alimentadores Auto | TP Top | TCOM Top | Backbone TP | Ajuste Manual | Observacion |
|---|---|---|---|---|---|---|
| Deteccion de tablero | SI | SI | SI | NO APLICA | PARCIAL | Ajuste reconoce el extremo de tablero en una ruta existente. |
| Soporte para TP | SI | SI | NO | SI | SI | Auto y Ajuste no dependen del prefijo TP. |
| Soporte para TCOM | SI | NO | SI | NO | SI | Auto era generico; Ajuste opera sobre ruta existente. |
| Soporte para otros tableros | SI | NO | NO | NO | SI | TP/TCOM codifican tipo y rango. |
| Deteccion de circuitos | SI | SI | SI | SI | NO APLICA | TCOM combina grupo y `CircuitosJSON`. |
| Seleccion de caja origen | SI | SI | SI | NO APLICA | NO | Auto usa plan/mejor fuente; TP/TCOM usan cercania al tablero. |
| Rutas guia | SI | NO | NO | NO | PARCIAL | Ajuste conserva una ruta existente, pero no consume objetos guia. |
| Carriles | SI | SI | SI | NO | NO | TP/TCOM solo separan por rango dentro de cada lado. |
| Distribucion sobre cara del tablero | SI | SI | SI | NO APLICA | PARCIAL | Ajuste preserva el extremo reconocido. |
| Seleccion de cara | SI | NO | NO | NO APLICA | NO | TP/TCOM fuerzan Top. |
| Cara superior real | PARCIAL | SI | SI | NO APLICA | PARCIAL | Anterior calcula sobre dimensiones/BB orientada; TP/TCOM validan `Shape.Faces`. |
| Uso de puertos de cajas | SI | SI | SI | SI | PARCIAL | Ajuste usa geometria de caja para salida perpendicular. |
| Reserva de puertos | SI | NO | SI | SI | NO APLICA | TP elige un puerto hacia el tablero sin mapa de ocupacion. |
| Ruta ortogonal | SI | SI | SI | SI | SI | Estrategias distintas. |
| Curvas / fillet | SI | SI | SI | SI | SI | Todas ajustan o construyen curvas, con distinto control. |
| Radio de curvatura | SI | SI | SI | SI | SI | La generacion anterior y Ajuste reducen radio segun capacidad. |
| Control de cruces | PARCIAL | PARCIAL | PARCIAL | PARCIAL | NO | Hay orden/penalizaciones, pero no prueba global de intersecciones. |
| Proteccion contra backtracking | SI | NO | NO | NO | SI | La v1 recorta retroceso; Ajuste lo penaliza y colapsa. |
| Limpieza de grupos | SI | SI | PARCIAL | SI | NO APLICA | TCOM reutiliza grupo, pero no hace barrido general de vacios. |
| Reutilizacion de objetos existentes | SI | SI | SI | SI | SI | Auto puede omitir/recalcular; las nuevas actualizan por clave. |
| Actualizacion sin duplicar | SI | SI | SI | SI | SI | La semantica exacta de Auto depende de configuracion. |
| Undo/Redo transaccional | SI | SI | SI | SI | SI | Observado en el codigo; no equivale a prueba GUI. |
| Trazabilidad mediante propiedades | SI | SI | SI | SI | PARCIAL | Ajuste conserva propiedades, pero no sincroniza todos los datos geometricos. |
| Configuracion de usuario | SI | SI | SI | SI | NO | Ajuste usa constantes internas. |
| Generalizacion a otros tableros | SI | NO | NO | NO | PARCIAL | Ajuste no genera; corrige rutas existentes. |
| Dependencia de otra `.FCMacro` | SI | NO | SI | SI | NO | En Auto es indirecta mediante el backend. |
| Dependencia de backend Python | SI | NO | NO | NO | NO | TP/TCOM son macros especializadas. |
| Reutilizacion futura como modulo | PARCIAL | PARCIAL | PARCIAL | PARCIAL | PARCIAL | Hay funciones valiosas, pero los limites de modulo no estan resueltos. |

## 9. Duplicaciones encontradas

### Duplicacion de codigo

- TP Top y TCOM Top repiten deteccion especifica, configuracion, escritura de propiedades, gestion de grupos y bucle de ejecucion. TCOM delega la geometria comun a TP mediante `exec()`.
- Backbone TCOM carga simultaneamente Backbone TP y TCOM Top; usa el MST, puertos y ruta del primero y la deteccion de circuitos del segundo.
- `Conectar_Circuitos_Ramales_Auto.FCMacro` conserva funciones locales de plan, perimetro y creacion de wires, pero el camino principal usa `ramales_backend.py`.
- La v1, `alimentadores_backend.py` y `ramales_backend.py` contienen capas de parche y envoltura alrededor de las mismas funciones profundas.

### Duplicacion funcional

- Alimentadores Auto, TP Top y TCOM Top producen caja principal -> tablero, pero con reglas y capacidades distintas.
- La v1, `ramales_backend.py` y Backbone TP resuelven caja -> caja, pero la v1/ramales usan orden perimetral y Backbone TP usa MST.
- Ajuste Manual comparte primitivas geometricas con los generadores, pero su funcion es diferente: editar una ruta existente.

No toda duplicacion funcional debe eliminarse. Algunas variantes representan estrategias geometricas que aun requieren comparacion visual.

## 10. Capacidades unicas

| Capacidad | Fuente actual o historica |
|---|---|
| Rutas guia como canales | `Conectar_Cajas_a_Tablero_Auto.FCMacro` + `alimentadores_backend.py` |
| Carriles globales y por guia/seccion | `alimentadores_backend.py` |
| Orden manual de guias, circuitos y circuitos por seccion | `Conectar_Alimentadores_a_Tablero_Auto.FCMacro` |
| Matriz manual de salidas del tablero | controlador anterior + `alimentadores_backend.py` |
| Cara seleccionable entre Top/Bottom/North/South/East/West | generacion anterior |
| Cara Top verificada contra geometria real | TP Top, reutilizada por TCOM Top |
| Reserva de puertos frente a rutas existentes | v1, TCOM Top y Backbone TP |
| Plan integrado de bajantes, backbone y alimentador | `Conectar_Cajas_a_Tablero_Auto.FCMacro` |
| Backbone MST con raiz tomada del alimentador | Backbone TP |
| Plan especializado de iluminacion por apagadores/recintos | `ramales_backend.py` |
| Edicion local con preservacion de prefijo/sufijo | Ajuste Manual |
| Deteccion y colapso de escalera/backtracking | Ajuste Manual |
| Calculo de radio admisible despues de editar | Ajuste Manual |
| Propuesta automatica de infraestructura guia | `Proponer_Rutas_Guia_Auto.FCMacro` |

## 11. Dependencias y deuda tecnica

Casos confirmados donde una `.FCMacro` se usa como modulo Python:

1. `alimentadores_backend.py` usa `SourceFileLoader` sobre `Conectar_Cajas_a_Tablero_Auto.FCMacro`.
2. `ramales_backend.py` usa `SourceFileLoader` sobre el mismo archivo.
3. TCOM Top lee, compila y ejecuta TP Top.
4. Backbone TP lee, compila y ejecuta TP Top.
5. Backbone TCOM lee, compila y ejecuta Backbone TP y TCOM Top.
6. Flujos relacionados como `Preparar_Red_Iluminacion_Completa.FCMacro` y `Preparar_Red_TCOM_Completa.FCMacro` tambien cargan macros como fuentes auxiliares.

Esto es deuda tecnica porque mezcla comando, UI y biblioteca; depende de nombres/rutas fisicas; dificulta pruebas aisladas; y puede ejecutar codigo de nivel superior si el guardado `__main__` cambia. No se corrigio en esta tarea.

## 12. Problemas de integridad del repositorio

### Estado en `HEAD/main` y recuperacion local

El commit apuntado por `HEAD/main` no contiene:

- `Conectar/Conectar_Alimentadores_a_Tablero_Auto.FCMacro`
- `Conectar/Conectar_Cajas_a_Tablero_Auto.FCMacro`

Tampoco aparecen en la punta de las ramas locales o remotas actualmente registradas. Sin embargo, ambos archivos fueron recuperados despues de la auditoria en el arbol de trabajo local y actualmente figuran como nuevos sin seguimiento.

### Evidencia historica

- Commit `2003355` del 2026-03-25: ambos archivos estaban versionados.
- Commit `b7d4fef` del 2026-04-15: contiene la ultima revision localizada de la v1.
- Commit `727b151` del 2026-06-12: elimina 8.131 lineas entre ambos archivos, sin una explicacion especifica de sustitucion en el mensaje.
- Commit `c33efce` del 2026-08-06: agrega TP Top, TCOM Top y Backbone TP.
- `Conectar/Backups/respaldo_alimentadores_20260319_114918.zip` conserva ambos archivos y el backend.
- Los inventarios de respaldo del 2026-03-19 dicen expresamente que la v1 debia permanecer porque `alimentadores_backend.py` y `ramales_backend.py` dependian de ella.

### Consecuencia ejecutable

Antes de la recuperacion, `ruta_macro_v1()` en ambos backends resolvia una ruta inexistente y `cargar_backend_v1()` lanzaba `RuntimeError`. Actualmente la ruta vuelve a existir en el arbol local. Por ello:

- `alimentadores_backend.py` vuelve a encontrar localmente su backend v1;
- el flujo principal de `Conectar_Circuitos_Ramales_Auto.FCMacro` vuelve a encontrar localmente esa dependencia;
- los archivos TP/TCOM posteriores si pueden operar sin la v1, salvo sus propias dependencias entre macros.

La recuperacion local no corrige todavia GitHub ni una copia limpia: hasta que se versionen los archivos, una instalacion nueva seguira careciendo de ellos. No se ejecuto aun una macro sobre un documento de FreeCAD; solo se verificaron existencia, identidad exacta de blobs y sintaxis.

## 13. Capacidades que deberian preservarse

Sin decidir aun la arquitectura final, una consolidacion futura no deberia perder:

1. Seleccion de caja alimentadora basada en el plan, no solamente la caja mas cercana al tablero.
2. Rutas guia y proyeccion de entrada/salida sobre su orientacion local.
3. Carriles globales, por guia y por seccion, con separacion consistente.
4. Orden manual de guias, circuitos y salidas del tablero.
5. Eleccion y verificacion de caras reales del tablero.
6. Enlaces tipados a caja y tablero, ademas de identificadores estables.
7. Reserva de puertos y preferencia por puertos cardinales en backbone/alimentadores.
8. Dos estrategias de backbone conservadas para validar: perimetro y MST.
9. Idempotencia, limpieza de grupos y eliminacion de objetos obsoletos.
10. Proteccion contra retroceso, escalera, curvas imposibles y segmentos demasiado cortos.
11. Ajuste manual local que preserve el resto de la ruta.
12. Sincronizacion futura entre geometria visible y metadatos de ruta despues del ajuste manual.

## 14. Preguntas que solo Marco puede responder

1. En proyectos reales, ¿el resultado preferido para los alimentadores era el flujo por rutas guia de marzo o la ruta directa por carriles laterales de TP/TCOM creada en agosto?
2. ¿Las macros TP/TCOM aparecieron porque la generacion anterior producia un resultado visual inaceptable, o solamente para resolver rapidamente el caso concreto de Puriscal?
3. Entre backbone perimetral y backbone MST, ¿cual representa mejor la instalacion que se quiere documentar cuando ambas rutas son tecnicamente posibles?
4. ¿El ajuste manual conserva hoy el resultado visual que Marco aprobo en marzo, especialmente cerca del tablero y en cajas octogonales?

## 15. Recomendaciones para la siguiente etapa

1. Validar primero en FreeCAD la dependencia historica ya recuperada; despues decidir si se conserva temporalmente o se extraen sus funciones maduras.
2. Preparar casos geometricos reproducibles para alimentador simple, varias guias, Top rotado, puertos ocupados, backbone perimetral y backbone MST.
3. Comparar resultados visuales antes de declarar reemplazos.
4. Separar en el futuro un modulo de geometria sin UI; las macros deben ser comandos, no bibliotecas cargadas con `exec()`.
5. Mantener alimentador, backbone, ramal y ajuste manual como servicios funcionales separados aunque compartan primitivas.
6. Definir un esquema canonico de propiedades y enlaces; evitar que Ajuste Manual deje `RutaJSON` y puntos de extremo obsoletos.
7. No eliminar respaldos ni archivos historicos hasta que la extraccion haya reproducido las capacidades enumeradas y Marco valide el resultado.

## Clasificacion provisional por herramienta

| Herramienta | Rol funcional | Madurez | Resultado comprobado | Decision ElectricCR provisional |
|---|---|---|---|---|
| `Conectar_Alimentadores_a_Tablero_Auto.FCMacro` | OPERATIVA | REVISAR-INTEGRIDAD | COMPROBADA-PARCIAL | POR VERIFICAR |
| `alimentadores_backend.py` | NUCLEO | LEGACY-DEPENDENCIA | POR VERIFICAR | POR VERIFICAR |
| `Conectar_Cajas_a_Tablero_Auto.FCMacro` | NUCLEO | LEGACY-DEPENDENCIA | COMPROBADA-PARCIAL | POR VERIFICAR |
| `Conectar_Circuitos_TP_a_Cara_Superior_Tablero.FCMacro` | ESPECIALIZADA | CANDIDATA | POR VERIFICAR | POR VERIFICAR |
| `Conectar_Circuitos_TCOM_a_Cara_Superior_Tablero.FCMacro` | ESPECIALIZADA | CANDIDATA | POR VERIFICAR | POR VERIFICAR |
| `Conectar_Octogonales_Ortogonal_por_Circuito_TP.FCMacro` | ESPECIALIZADA | CANDIDATA | POR VERIFICAR | POR VERIFICAR |
| `ramales_backend.py` | NUCLEO | LEGACY-DEPENDENCIA | POR VERIFICAR | POR VERIFICAR |
| `Conectar_Circuitos_Ramales_Auto.FCMacro` | OPERATIVA | REVISAR-INTEGRIDAD | COMPROBADA-PARCIAL | POR VERIFICAR |
| `Ajustar_Alimentador_o_Ramal_Manual.FCMacro` | OPERATIVA | ACTIVA | COMPROBADA-PARCIAL | POR VERIFICAR |
| `Proponer_Rutas_Guia_Auto.FCMacro` | SOPORTE | CANDIDATA | POR VERIFICAR | POR VERIFICAR |

Las clasificaciones describen la evidencia disponible. No autorizan fusiones, descartes, migraciones ni restauraciones adicionales.
# Resultado 2026-08-10 - ciclo de vida de docks Qt6

Objetivo: corregir la acumulacion confirmada de `QDockWidget` ElectricCR sin
refactor general ni cambios funcionales.

Causa confirmada: coexistian patrones de recreacion inmediata; Endpoints solo
cerraba el dock anterior y acumulaba instancias permanentemente. Ademas
tabulaba con Combo View y llamaba `resizeDocks()` sobre MainWindow.

Archivos funcionales modificados:

- `ElectricCR/ui/dock_manager.py` (nuevo gestor pequeno);
- `Areas/AreaPorClick.FCMacro`;
- `Conectar/Panel_Conexiones_Endpoints.FCMacro`;
- `Conectar/Conectar_Circuitos_Ramales_Auto.FCMacro`;
- `Conectar/Conectar_Circuitos_Luminarias_Auto.FCMacro`;
- `Conectar/Conectar_Cajas_a_Tablero_Auto.FCMacro`;
- `Conectar/Proponer_Rutas_Guia_Auto.FCMacro`.

Pruebas: Endpoints 20 ciclos; cada panel restante 10 ciclos; Tasks nativo 10
ciclos; secuencia combinada 5 rondas; cambio de workbench incluido; GameExport
hot reload 10 ciclos separados. Todos los docks migrados mantuvieron conteo 1
por `objectName`. No se modifico ni guardo el documento de trabajo; la prueba
nativa uso y cerro un documento temporal.

Resultado tecnico: acumulacion de docks corregida y probada. Pantalla negra no
reproducida; validacion funcional durante uso real pendiente.

Clasificacion provisional: Rol SOPORTE/SISTEMA; Madurez ACTIVA; Resultado
COMPROBADA-PARCIAL hasta validacion visual de Marco.


## Trabajo GPT 2026-09-05 21:50 America/Costa_Rica - rollback del overlay PLAN y limpieza de pertenencia a grupos

> Trabajo directo de GPT en Drive; no atribuir a Codex.

La prueba real en Upala invalido `plan_selection.py` v0.3.0: `Draft ghostTracker` dejo representaciones graficas residuales tras Move/Delete y la sesion termino con multiples `Access violation` y `SystemError: unknown opcode`.

Cambios aplicados:
- `plan_selection.py` v0.4.0: eliminado `ghostTracker`, cache `_FEEDBACK`, reconstruccion de overlays y preseleccion persistente. Seleccion logica sigue siendo exclusivamente Owner.
- `plan_live_sync.py` v0.4.0: eliminadas llamadas de refresco del overlay; se mantiene recompute dirigido de PLAN y normalizacion `ShowInTree=False`.
- `objeto_toma_uno.py` rev O: nuevo control para que PLAN no sea miembro de `App::DocumentObjectGroup`; el dry-run informa `DETACH_PLAN_FROM_GROUPS` y la sincronizacion elimina esa pertenencia accidental.

Verificacion estatica: `py_compile` OK en los tres archivos.
Verificacion FreeCAD real: pendiente tras reinicio completo.

Aclaracion de prueba: Rectangle009 y Rectangle010 fueron eliminados intencionalmente por Marco durante Delete/Undo/Redo.
