## Validacion funcional - 2026-09-14 21:26 -0600 - ElectricCR / Objetos / Alinear en planta v0.2

Marco confirma en FreeCAD 1.1.3 que la herramienta **funciona** en el caso real probado despues de ampliar la referencia a cara plana. Se considera validado funcionalmente el flujo objeto + cara lateral plana -> correccion XY + giro Z, conservando Z segun el contrato v0.2.

No se registran como comprobados en esta confirmacion Undo/Redo, guardado/reapertura ni todos los casos de arista/cara; esos puntos solo deben cerrarse si se prueban explicitamente. Estado: VALIDADA FUNCIONALMENTE EN CASO REAL / COMPROBADA-PARCIAL.

---

## Tarea vigente - 2026-09-14 21:26 -0600 America/Costa_Rica - ElectricCR / Objetos / Alinear en planta v0.2

> Instruccion autorizada por Marco en ChatGPT. Trabajo directo de GPT en Google Drive. Esta tarea sustituye como tarea vigente a los bloques historicos inferiores; no reabrir A1 ni otras tareas cerradas.

### Objetivo

Mantener la herramienta simple para corregir objetos insertados torcidos en planta, pero permitir que la referencia sea tanto una **arista recta** como una **cara plana**. Caso inicial: tablero electrico cuya desviacion se limita a posicion X/Y y rotacion alrededor de Z. La herramienta permanece en la barra **Objetos** de ElectricCR y no sustituye `Objetos/Alinear.FCMacro`.

### Contrato funcional v0.2

1. Seleccionar primero el objeto a corregir.
2. Seleccionar despues una arista recta o una cara plana de referencia.
3. Ejecutar **Alinear en planta**.
4. Con arista: proyectar `Placement.Base` sobre la recta XY infinita de la arista.
5. Con cara: obtener la normal de la cara plana, derivar su direccion en planta y proyectar X/Y del punto de insercion sobre el plano manteniendo exactamente Z.
6. Aplicar solamente el menor giro alrededor del eje global Z para dejar paralelo a la referencia el eje local X o Y que requiera menor correccion.
7. Conservar `Placement.Base.z`, geometria, escala, propiedades electricas y organizacion del objeto.
8. Rechazar referencias curvas, caras horizontales sin direccion XY, aristas verticales en planta y selecciones ambiguas.
9. Usar transaccion propia para Undo/Redo y diagnostico `[OBJ-ALIGN]`.

### Cambios autorizados y realizados

- Actualizar en su misma identidad `Objetos/Alinear_En_Planta.FCMacro` de v0.1.0 a v0.2.0.
- Mantener `Objetos/Alinear_En_Planta.svg` sin cambios.
- Actualizar documentacion vigente de tarea/resultado/estado.

No modificar `Objetos/Alinear.FCMacro`, A1, Tableros, modelos productivos, `InitGui.py` ni `config.json`.

### Verificacion disponible y pendiente

- Compilacion sintactica fuera de FreeCAD: PASS.
- Pruebas matematicas aisladas: PASS para cara vertical, cara inclinada y conservacion de Z; cara horizontal rechazada.
- Relectura desde Drive: bytes y SHA-256 identicos al archivo generado.
- Prueba real pendiente en FreeCAD 1.1.3: tablero torcido + arista de muro y tablero torcido + cara lateral de muro, comprobando XY, Z, giro, Undo/Redo y persistencia. No declarar la herramienta validada funcionalmente hasta esa prueba.
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

## Continuidad vigente - 2026-09-14 07:46 -0600 - A1 / PLAN Lifecycle probado

**Tarea del 14/9 ejecutada: Access violation de Undo Demo reproducido, correccion minima aplicada y regresion real FreeCAD 1.1.3 PASS. Detenerse; no iniciar otra tarea ni publicar.**

Causa: metodos C++ inexistentes en la API Python, cuyas excepciones anulaban las guardas de transaccion. Lifecycle eliminaba PLAN dentro de Undo. Se usan Transacting / HasPendingTransaction en lifecycle/live sync y se drena la cola existente antes del recompute nativo de Delete. No cambia el contrato A1 ni la fabrica, seleccion o Demo.

19 etapas finales PASS: Demo 2/5/7/7; movimiento con transaccion verificable y Undo/Redo; Delete/Undo/Redo del par; rollback antes/despues de flush; Undo/Redo de creacion completa; guardar/cerrar/reabrir; movimiento con BIM, Draft y Part. Smoke original e Undo completo sin instrumentacion tambien pasan. Se reviso consola en llamada posterior para no aceptar como PASS un Access violation diferido. Cero errores Access violation/Placement/unknown opcode finales; dos avisos nativos hasher mismatch documentados sin fallo de integridad observado.

[Resultado y evidencia](tests/evidence/2026-09-14_a1_undo_lifecycle/README.md). Correccion tecnicamente verificada y pendiente revision/aceptacion del proyecto; sin commit/push. El origen exacto del gesto historico de movimiento no esta registrado: se reprodujo que escribir Placement sin transaccion no agrega Undo, y con transaccion explicita si. No atribuirlo a Draft sin evidencia.

Metadata/App::Feature y Recuperar Tasks quedan historicos. No tocar IFC, Upala, registry, masters, otras herramientas ni Git. No continuar los bloques inferiores como si fueran pendientes actuales de esta ejecucion.

---

## Continuidad vigente - 2026-09-13 16:49 -0600 - Recuperar Tasks probado

**Prueba tecnica de Recuperar Tasks en FreeCAD 1.1.3 completada: PASS. Sin modificar codigo funcional. La resolucion del panel negro sigue sin demostrarse.**

Se ejecuto exclusivamente la validacion pendiente identificada por la conciliacion inicial del 12/9: 28 ejecuciones sobre dos documentos temporales, tarea Sketch nativa preservada, diez pulsaciones sin acumulacion (cinco docks, 897 widgets), seis alternancias A/B, auditoria antes/despues y comprobacion visual. Cero errores del recuperador. Documentos cerrados sin guardar; visibilidad inicial de Tasks restaurada. El error de arranque de FacilArquitecturaWB queda registrado aparte y no se investigo.

No se reprodujo el panel negro. Proximo paso de esta herramienta: validacion funcional durante una reproduccion real, conservando los snapshots BEFORE/AFTER. `tab=unknown` con docks separados es una limitacion documentada; la visibilidad se conservo en los ensayos. No se declara solucion definitiva ni RELEASE.

El diagnostico de Access violation en Undo Demo A1 / PLAN Lifecycle del 10/9 14:01 permanece como pendiente independiente; no se ejecuto ni se mezclo con estas pruebas. `_create_metadata()` ya usa App::FeaturePython; no reabrir el fallo historico de App::Feature. No hubo cambios IFC, Upala o Git.

[Resultado, consola y evidencia](tests/evidence/2026-09-13_tasks_recovery_gui/README.md). Trabajo detenido tras probar y documentar. Los bloques inferiores son antecedentes; no interpretar los antiguos FAIL ni bloqueos de skills como pruebas del estado actual.

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

## Avance GPT - 2026-09-10 17:54 -0600 America/Costa_Rica - Programacion / Recuperar panel Tasks

> Trabajo directo de GPT en Google Drive; no atribuir a Codex.

Estado: **IMPLEMENTADA EN DRIVE / SINTAXIS APROBADA / PRUEBA REAL FREECAD 1.1.3 PENDIENTE**.

Se implemento la primera version paliativa y diagnostica autorizada:

- `Programación/RecuperarPanelTareas.FCMacro` v0.1.0, archivo nuevo en la carpeta Programacion vigente;
- `Programación/RecuperarPanelTareas.svg`, icono propio;
- `Programación/programacion_toolbar.py` actualizado en su mismo archivo a v1.1.0; agrega exactamente un comando estable `Programacion_RecoverTasks` junto a la auditoria existente.

Comportamiento implementado: snapshot BEFORE de documento/subventana MDI, `activeDialog()`, `centralWidget`, pestaña Model/Tasks, todos los `QDockWidget`, geometria/tamanos y duplicados; recuperacion suave mediante `FreeCADGui.Control.showModelView()`, `FreeCADGui.updateGui()` + procesamiento de eventos Qt y retorno condicional a `showTaskView()` si habia TaskDialog o Tasks estaba visible; snapshot AFTER y diferencias. Trazas: `[TASK-RECOVERY][BEFORE|ACTION|AFTER|RESULT|WARNING|ERROR]`.

Guardas verificadas por inspeccion estatica: no contiene `closeDialog()`, `resizeDocks()`, `restoreState()`, `setCentralWidget()`, `splitDockWidget()`, `removeDockWidget()` ni `deleteLater()`. No crea, borra, recomputa, guarda ni cambia documentos. `UI_Audit_FreeCAD.FCMacro` y `AuditarInterfazFreeCAD.FCMacro` quedaron sin modificar.

Verificacion realizada sobre los bytes re-leidos desde Drive: compilacion sintactica de `RecuperarPanelTareas.FCMacro` y `programacion_toolbar.py` = **PASS**; `Programacion_RecoverTasks` aparece una sola vez en el manifiesto.

Pendiente obligatorio: prueba real en FreeCAD 1.1.3 con dos documentos temporales, TaskDialog nativo, 10 ciclos y reproduccion controlada del panel negro. **No afirmar todavia que el panel negro queda resuelto.** Tras sincronizar Drive con la carpeta local de macros, reiniciar FreeCAD o recargar el bootstrap de Programacion y validar el boton.

---

## Tarea vigente - 2026-09-10 15:40 -0600 America/Costa_Rica - Programacion / Recuperar panel Tasks

> Instruccion autorizada por Marco en ChatGPT. Implementar y probar en FreeCAD 1.1.3. Esta tarea es independiente de ElectricCR A1; conservar las entradas historicas inferiores sin reabrirlas ni mezclarlas.

### Objetivo

Crear una herramienta paliativa y diagnostica para el problema visual en el que una zona/panel negro tapa la vista al trabajar con FreeCAD y cambiar entre documentos, aparentemente relacionado con Combo View / Tasks. Debe agregarse a la barra global **Programacion**, no a FacilArquitecturaWB, porque es una utilidad transversal de interfaz.

Nombre sugerido del archivo: `Programación/RecuperarPanelTareas.FCMacro` (adaptar solo si la estructura real vigente de Programacion usa otro nombre/directorio equivalente).
Boton sugerido: **Recuperar Tasks**.
CommandName estable: definir siguiendo el patron vigente de `Programación/programacion_toolbar.py`.

### Antes de modificar

1. Leer `AGENTS.md` y la skill `$freecad-cr-workbench-architecture` indicada por el repositorio.
2. Localizar y revisar la fuente vigente de `Programación/programacion_toolbar.py`, `Programación/UI_Audit_FreeCAD.FCMacro` y cualquier manifiesto/registrador actual de la barra. No crear un segundo toolbar ni un loader paralelo.
3. Confirmar en FreeCAD 1.1.3 las APIs disponibles de `FreeCADGui.Control`, en particular `showModelView()`, `showTaskView()` y `activeDialog()`. Preferir estas APIs de FreeCAD sobre manipular directamente el contenido de Tasks.
4. Revisar la auditoria ya existente `AUDITORIA_RUNTIME_PANELES_FREECAD_1_1_3.md`. Antecedente importante: no usar `resizeDocks()`, `restoreState()`, `setCentralWidget()`, `splitDockWidget()` ni cambios globales de layout para esta herramienta.
5. Diagnosticar primero el estado real de la sesion antes de aplicar recuperacion.

### Comportamiento requerido v0.1

Al pulsar **Recuperar Tasks**:

1. Capturar snapshot PREVIO, sin modificar documentos:
   - documento activo y, si es accesible de forma segura, subventana MDI activa;
   - `FreeCADGui.Control.activeDialog()` y si existe TaskDialog activo;
   - `QMainWindow.centralWidget()` y su geometria/tamano;
   - todos los `QDockWidget` relevantes, con especial atencion a Combo View / Model / Tasks: `objectName`, titulo, visible, floating, area, size, minimumSize, maximumSize y geometry;
   - conteo por `objectName` y advertencia de duplicados;
   - si puede determinarse sin fragilidad, pestaña Model/Tasks actualmente visible.

2. Escribir trazas claras a Report View / consola con prefijo estable, por ejemplo:
   - `[TASK-RECOVERY][BEFORE]`
   - `[TASK-RECOVERY][ACTION]`
   - `[TASK-RECOVERY][AFTER]`
   - `[TASK-RECOVERY][WARNING]`
   - `[TASK-RECOVERY][ERROR]`

3. Recuperacion suave, sin cerrar ni cancelar tareas:
   - guardar si antes estaba visible Tasks y/o habia `activeDialog()`;
   - llamar `FreeCADGui.Control.showModelView()`;
   - devolver control al ciclo Qt de forma segura (`FreeCADGui.updateGui()` y/o procesamiento de eventos pendiente segun API real verificada);
   - si antes habia una tarea activa o la pestaña Tasks era la visible, volver con `FreeCADGui.Control.showTaskView()` y actualizar GUI;
   - si no habia tarea activa y estaba Model, dejar Model.

4. Capturar snapshot POSTERIOR con los mismos campos y registrar diferencias utiles: central geometry, docks duplicados, Combo/Tasks, activeDialog y visibilidad.

5. La macro NO debe:
   - llamar `FreeCADGui.Control.closeDialog()` en v0.1;
   - cerrar/cancelar una operacion del usuario;
   - crear, borrar, recomputar, guardar ni modificar objetos de ningun `.FCStd`;
   - cambiar de documento activo;
   - cambiar el tamano global mediante `resizeDocks()`;
   - restaurar `MainWindowState`;
   - destruir/reparentar docks;
   - ocultar el problema mediante un reset agresivo.

6. Si una operacion de recuperacion falla, capturar la excepcion, registrar suficiente contexto y dejar la interfaz lo mas intacta posible. No lanzar una cascada de intentos agresivos.

### Reutilizacion del diagnostico existente

Preferir extraer/reutilizar funciones de diagnostico de `UI_Audit_FreeCAD.FCMacro` solo si puede hacerse sin romper su uso independiente. Si la auditoria es monolitica, no duplicar cientos de lineas: factorizar un helper neutral pequeno en `Programación/` y adaptar ambas macros solo si la regresion es simple y segura. Si factorizar introduce riesgo, implementar un snapshot minimo deliberadamente acotado en la nueva macro y documentar la duplicacion minima.

`UI_Audit_FreeCAD.FCMacro` debe seguir siendo estrictamente read-only. No convertirla en una macro de reparacion.

### Integracion en barra Programacion

- Integrar un unico comando nuevo en la barra global existente.
- Mantener CommandName estable e idempotencia del registrador.
- No crear una segunda `QToolBar`.
- Conservar todos los botones actuales y su orden salvo la insercion razonable del nuevo boton cerca de `UI_Audit_FreeCAD`.
- Crear icono SVG propio sencillo si el patron vigente lo exige; no reutilizar un icono que induzca a error.
- Mantener la macro dentro del directorio de macros de FreeCAD / `Programación`.

### Encabezado obligatorio

La macro y cualquier helper nuevo deben incluir al inicio: nombre, proposito, funcionamiento principal, advertencias para futuras modificaciones, version, fecha y hora. Evitar tildes/caracteres especiales en identificadores internos, aunque las etiquetas visibles pueden usar espanol normal.

### Pruebas obligatorias

Primero sintaxis/compilacion. Luego prueba real en FreeCAD 1.1.3, preferiblemente por MCP si esta disponible:

A. Con dos documentos temporales simples abiertos, sin TaskDialog: alternar documentos y ejecutar **Recuperar Tasks**. Debe conservar documentos, seleccion razonablemente, vista y estado Model; cero excepciones.

B. Abrir una tarea nativa segura (por ejemplo editar/crear Sketch en documento temporal), ejecutar **Recuperar Tasks** y comprobar que la tarea sigue activa despues del refresco; no debe cerrarse ni perder datos.

C. Ejecutar el boton 10 veces seguidas. Confirmar que no aumenta el numero de docks, no aparecen duplicados y no se crean widgets persistentes nuevos.

D. Alternar A <-> B varias veces y ejecutar el recuperador antes/despues. Registrar geometria central y Combo/Tasks.

E. Ejecutar `UI_Audit_FreeCAD.FCMacro` antes y despues para verificar que el nuevo boton no altera permanentemente el layout.

F. Si se logra reproducir el panel negro en la sesion de prueba sin arriesgar documentos del usuario, ejecutar el boton durante el fallo y documentar si recupera visualmente la vista. Si no se puede reproducir de manera controlada, NO afirmar que el fallo negro esta resuelto: declarar solamente que el mecanismo de refresco y diagnostico fue validado.

G. No usar documentos productivos ni guardar modificaciones en archivos reales del usuario. Usar documentos nuevos/temporales y cerrarlos al finalizar.

### Criterios de aceptacion

- Boton **Recuperar Tasks** visible una sola vez en Programacion.
- Auditoria PRE/POST legible y suficientemente compacta.
- `showModelView()` -> ciclo de eventos -> retorno condicional a `showTaskView()` funciona sin cerrar TaskDialog.
- 10 ciclos sin acumulacion de docks/widgets atribuibles a la macro.
- No modifica ni guarda `.FCStd`.
- No toca layout global con APIs agresivas.
- No degrada los botones existentes de Programacion.
- Si el negro no pudo reproducirse, resultado debe decirlo explicitamente.

### Documentacion al finalizar

Actualizar `RESULTADO_CODEX.md` y `ESTADO_PROYECTO.md` con: archivos modificados, causa/hipotesis, API FreeCAD realmente usada, pruebas, conteos before/after, limitaciones y si el negro fue o no reproducido/recuperado. Actualizar `TAREA_ACTUAL.md` arriba de esta entrada con el resultado final. Si corresponde, dejar memoria tecnica en `Memoria_FreeCAD/`. No mezclar esta tarea con reparaciones de `Panel_Conexiones_Endpoints.FCMacro`; si el diagnostico vuelve a apuntar a ese panel, documentarlo como hallazgo separado y detener cualquier cambio funcional adicional salvo autorizacion expresa.

No hacer commit/push automatico salvo que el flujo vigente de Codex lo requiera expresamente y las pruebas hayan pasado; priorizar primero validacion real de Marco.

---

## Tarea vigente - Demo ElectricCR A1 v0.1 - 2026-09-09 22:39 -0600 America/Costa_Rica

**PRUEBA FREECAD 1.1.3 EJECUTADA: FAIL. DETENIDA TRAS EL PRIMER FALLO REPRODUCIBLE, SIN MODIFICAR CODIGO.** A1 sigue aprobado.

`tests/freecad_electric_demo_smoke.py` falla al crear metadata: `electriccr/demo/electric_demo_freecad.py:100` pide `App::Feature`, que FreeCAD 1.1.3 rechaza como tipo de objeto de documento. Misma llamada reproducida en documento vacio; no se ensayaron reparaciones.

No se generaron Oficina, Bodega, muros ni los7 dispositivos; revision visual pendiente por este fallo. No se alcanzaron las regresiones posteriores del smoke. Documentos temporales cerrados. [Resultado y consola](tests/evidence/2026-09-09_electric_demo_v01_first_failure/README.md).

Cumplida la instruccion de ejecutar, diagnosticar el primer fallo y detenerse antes de modificar. No ejecutar IFC, abrir Upala, ampliar diagnostico ni cambiar el tipo por iniciativa propia. Esperar nueva instruccion para corregir la demo. La especificacion GPT de abajo se conserva como antecedente.

---

## Tarea vigente - 2026-09-09 22:09 -0600 America/Costa_Rica - Demo ElectricCR A1 canonica v0.1

> Trabajo directo de GPT en Drive; no atribuir a Codex. A1 aprobado se reutiliza sin redisenarlo.

Estado: **IMPLEMENTADA EN DRIVE / CORE PURO 7-7 APROBADO / SINTAXIS APROBADA / PRUEBA REAL FREECAD 1.1.3 PENDIENTE**.

Marco autorizo desarrollar una macro/demo de pruebas equivalente en filosofia a la Demo Casa de 2 Plantas de Facil Arquitectura. La primera version se limita deliberadamente al contrato A1 + Space/Host y NO implementa todavia exportacion IFC, objetos Circuit ni objetos Control.

Arquitectura implementada:

```text
electriccr/demo/electric_demo_core.py      # especificacion pura JSON-compatible
        |
        v
electriccr/demo/electric_demo_freecad.py   # Arch Space/Wall + fabrica A1 existente
        |
        +--> electric_demo_audit.py          # auditor read-only
        |
        v
commands/demo_electriccr.py                # dos comandos GUI finos
        |
        `--> Demo_ElectricCR_A1.FCMacro      # lanzador manual minimo
```

Escenario canonico fijo v0.1:
- 1 edificio / 1 Nivel 00;
- 2 `Arch Space` nativos: Oficina y Bodega;
- 5 muros BIM nativos y una losa de apoyo;
- 2 tomacorrientes A1;
- 2 apagadores A1;
- 2 luminarias A1;
- 1 sensor de humo A1;
- 7 `ElementUID` deterministas UUIDv5;
- `CircuitoID` solo como texto de compatibilidad/demo (`T-01`, `IL-01`, `FA-01`), sin inventar aun un objeto Circuit.

Reglas de seguridad:
- el comando siempre crea un documento NUEVO; nunca reutiliza ni modifica el proyecto activo;
- usa `Arch.makeSpace()` y `Arch.makeWall()` nativos;
- usa `crear_toma_link(... separate_documentation=True)` existente;
- usa `ensure_device_semantics()` para UID/Space/Host;
- usa `sync_plan_representation()` para PLAN;
- una transaccion exterior agrupa la generacion y un fallo cierra el documento demo incompleto;
- el auditor no recomputa, repara ni escribe propiedades;
- IFC queda fuera de v0.1 para aislar primero la estabilidad del banco de pruebas A1.

Verificacion GPT disponible sin FreeCAD real:
- `py_compile`: APROBADO para core, adapter, audit, command, macro, test puro y smoke real preparado;
- `pytest tests/test_electric_demo_core.py`: **7 passed**;
- determinismo, serializacion JSON, UID unicos, ubicacion de cada dispositivo dentro de su Space, hosts validos y conteos canonicos: APROBADOS.

Prueba real siguiente, unica razon actual para pasar a Codex/MCP: ejecutar `tests/freecad_electric_demo_smoke.py` en FreeCAD 1.1.3 y comprobar generacion visual, RoomResolver/Space, 7 Owner/7 PLAN, movimiento Owner->PLAN, Undo/Redo, Std_Delete lifecycle y save/reopen. No modificar codigo por intuicion si falla; diagnosticar primero.

No ejecutar aun IFC ni ampliar la demo hasta cerrar esta prueba.

---

## Tarea vigente - 2026-09-09 22:09 -0600 America/Costa_Rica - investigacion GPT del adaptador IFC A1

> Trabajo directo de GPT en Drive; no atribuir a Codex. No se modifica codigo productivo.

Estado: **DISENO DOCUMENTADO / A1 SIN CAMBIOS / CODEX NO REQUERIDO TODAVIA**.

A partir del cierre A1 y del experimento NativeIFC ya aprobado, la siguiente arquitectura de estudio queda acotada a una capa de interoperabilidad IFC alrededor de A1. A1 conserva la autoria del elemento electrico durante la edicion en FreeCAD; NativeIFC/IfcOpenShell se reutiliza para construir la salida IFC sin convertir ni reemplazar automaticamente los `App::Link` productivos.

Contrato provisional:

```text
A1 Owner / App::Link
  ElementUID + Placement + relaciones + master fisico
        |
        `-- adaptador IFC de exportacion
              |-- GlobalId determinista desde ElementUID
              |-- clase / PredefinedType desde registro + esquema
              |-- Representation desde geometria A1
              |-- ObjectPlacement desde Owner.Placement
              |-- Psets estandar cuando existan
              `-- Space -> IfcSpace del mismo modelo IFC
```

Hallazgos que condicionan la implementacion futura:
- no usar `NativeIFC.aggregate()` sobre Owners productivos como mecanismo de integracion: la ruta puede crear un nuevo objeto IFC y eliminar/reemplazar el objeto FreeCAD original segun `KeepAggregated`;
- el master A1 no debe equipararse automaticamente a `IfcTypeProduct`, porque hoy su firma incorpora propiedades de ocurrencia como altura/orientacion;
- `PLAN` no es un segundo producto electrico IFC; como maximo puede estudiarse posteriormente como `IfcAnnotation` en contexto Plan;
- el registro actual ya contiene `IfcOutlet`, `IfcSwitchingDevice` e `IfcLightFixture`, pero hay clasificaciones pendientes de depurar antes de escribir un mapeo definitivo;
- tablero debe resolverse por esquema (`IfcElectricDistributionBoard` en IFC4; `IfcDistributionBoard` en IFC4X3).

Siguiente prueba propuesta, aun **sin programar**: crear una macro de demostracion/regresion semejante a la Demo Casa de 2 Plantas, pero para ElectricCR/IFC. Debe generar un escenario pequeno desde cero, reproducible, que permita probar A1 + Space + varias familias + exportacion IFC y luego auditar identidad, Placement, Psets, containment, save/reopen y ausencia de modificaciones destructivas. La macro se desarrollara solo tras autorizacion expresa de Marco.

No modificar por esta fase `registry_electric.json`, A1, PLAN, lifecycle, seleccion, masters ni documentos productivos.

---

## Tarea vigente - cierre 2026-09-09 20:02 -0600 America/Costa_Rica

**COMPLETADA: cierre A1 GitHub + experimento NativeIFC desechable. A1 = APROBADO PARA CONTINUAR.**

A1 cerrado en GitHub: [4a9ade9](https://github.com/MVM444/Macros-de-Freecad/commit/4a9ade9645d9227ac5323676ee911c972502e869), constancia [285d5a7](https://github.com/MVM444/Macros-de-Freecad/commit/285d5a74b6463dc859d0bc0a940b2879aa6c4c2a), rama `codex/cierre-a1-20260909`; ambos pushes confirmados, staging limpio. Se separaron cambios ajenos y la evidencia publica se anonimizo conforme AGENTS. No merge a main ni release Addon. DEV funcional sin cambios.

NativeIFC probado en FreeCAD 1.1.3, esquema IFC4: exactamente4 elementos (IfcOutlet, IfcSwitchingDevice, IfcLightFixture, IfcElectricDistributionBoard) y proyecto de infraestructura. Identidad/campos/Psets/Placement, edicion, guardar/cerrar/reabrir FCStd con IFC companero y apertura IFC: APROBADOS. Type=None; reutilizacion multiple investigada solo en fuentes/codigo. No repetir estas pruebas ni abrir Upala para esta tarea.

Recomendacion para decidir la siguiente tarea: opcion2, estudiar capa/adaptador alrededor de A1 con autoridad unica por dato. No es autorizacion para implementar integracion, reemplazar A1 ni crear una solucion hibrida. No se tocaron PLAN, lifecycle, seleccion, masters, puertos o dispositivos productivos. NativeIFC sigue experimental; faltan pruebas de Type compartido, rendimiento, edicion colectiva y otros limites documentados si se elige profundizar.

Evidencia y matriz: [reporte NativeIFC](tests/evidence/2026-09-09_nativeifc_four_elements/README.md), RESULTADO_CODEX.md y ESTADO_PROYECTO.md. Documentos temporales cerrados; resultados y helper guardados localmente. Siguiente accion depende de la opcion que indique Marco; no desarrollar automaticamente una integracion.

Entradas inferiores historicas.

---

## Tarea vigente - 2026-09-09T09:16:00.625279-06:00

A1 = APROBADO PARA CONTINUAR. Cierre GitHub completado: `4a9ade9645d9227ac5323676ee911c972502e869`, rama `codex/cierre-a1-20260909`, push exitoso. No cambiar funcionalidad A1.

Siguiente fase autorizada: experimento NativeIFC nuevo/desechable en FreeCAD 1.1.3, exactamente cuatro ocurrencias (Outlet, SwitchingDevice, LightFixture, tablero con clase del esquema real). Sin Upala, conversiones existentes, integracion A1, PLAN/lifecycle/seleccion/masters ni puertos. Registrar esquema, identidad, propiedades, Placement, Type/Psets, edicion y persistencia tras guardar/cerrar/reabrir. Investigar reutilizacion por Type sin desarrollar integracion. Matriz de decision y evidencia en resultado, estado, tarea y memoria.

---

## Tarea vigente - cierre 2026-09-08 17:49 -0600 America/Costa_Rica

**ElectricCR — A1 fisico + PLAN 2D: COMPLETADA. A1 = APROBADO PARA CONTINUAR.** FreeCAD objetivo 1.1.3. Aprobacion comprobada con ElectricCR inicializado una vez por sesion y despues con BIM/Draft/Part activos.

Ultima instruccion atendida: diagnosticar por que PLAN vuelve a seleccionarse al salir de ElectricCR, aplicar correccion minima del runtime si se confirma y completar regresion fuera del Workbench. No repetir investigacion amplia ni reconstruir PLAN sanos.

Fuente actual correcta y protegida: `C:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Sucursales\Upala\1416 Levantamiento 250424 Compu D.FCStd`. SHA256 `F5E1A372D162F02E5D91CD874F47A13B412380972F0604E27D9D77D71E87077F`. El bloqueo de ruta mmfallas de las 12:32 queda resuelto; no usar la copia antigua para juzgar el estado actual. Pruebas destructivas hechas solo en `C:\Users\marco\AppData\Local\Temp\ecr_a1_acceptance_20260908_5_mtcyyd\A1_workbench_regression.FCStd`.

Causa: Deactivated quitaba solo el observer de seleccion; lifecycle/live sync seguian. Delete de PLAN en Part reprodujo Owner sin PLAN. Correccion: instalar seleccion en Initialize, conservarla entre Workbenches, hacer install idempotente y corregir import de normalizacion del arbol. Sin redisenar contrato ni cambiar lifecycle.

Regresion cerrada:

- Auditoria inicial y final: 10 Owners / 10 PLAN, correspondencia 1:1 y cero inconsistencias.
- Crear un dispositivo nuevo (11/11); PLAN -> Owner, mover/girar y seguimiento real antes de recompute global.
- BIM: guardar, Delete/Undo/Redo/Undo, nuevo movimiento en secuencia valida y guardar/cerrar/reabrir.
- Draft: mover/girar, Delete/Undo/Redo/Undo y guardar/cerrar/reabrir.
- Part: Ambos/Solo2D/Solo3D, clic real PLAN -> Owner, Delete/Undo/Redo, guardar/cerrar/reabrir, repetir movimiento y borrado; reapertura final 10/10.
- Servicios idempotentes, PLAN sin segunda identidad/entrada en arbol ni grupos; cero huerfanos/duplicados, errores Placement, Access violation o graficos residuales observados.
- Original sin cambios; todos los valores serializados de Owners conservados. Estado temporal Touched del auditor documentado aparte, no es cambio de Placement ni fallo de recompute.

Ver [RESULTADO_CODEX.md](RESULTADO_CODEX.md) y [evidencia completa](tests/evidence/2026-09-08_a1_workbench_runtime/README.md) para causa, delta, consola y limites. No afirmar que los guards preexistentes de transaccion usan correctamente la API 1.1.3 ni que el runtime se instala antes de inicializar ElectricCR.

Pendientes expresamente separados y no bloqueantes: feedback persistente PLAN, NativeIFC/IFC electrico, arbol semantico, doble aparicion Wall/electrico, ClaimHosted, Rectangle006 historico y orientacion en muros inclinados. No ghostTracker, no preselection persistente, no seleccionar Owner+PLAN, no ocultar Host. Sin commit/push. Siguiente trabajo: el desarrollo que indique Marco sobre esta base A1; no reabrir automaticamente los pendientes excluidos.

Las entradas siguientes son historicas y no reemplazan esta tarea vigente.

---
## Tarea vigente - 2026-09-08 12:32 America/Costa_Rica

Cierre de auditoria A1 fisico + PLAN 2D en FreeCAD 1.1.3. Auditar 1:1 y ejecutar una regresion de un dispositivo nuevo (movimiento, Std_Delete, Undo/Redo, guardar/cerrar/reabrir) exclusivamente en copia temporal verificable del archivo ACTUAL validado por Marco. Si todo pasa, aprobar A1 para continuar sin cambios de codigo; ante regresion actual reproducible, detenerse y documentar antes de cambiar arquitectura.

Fuente indicada: `C:\Users\mmfallas\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Sucursales\Upala\1416 Levantamiento 250424 Compu D.FCStd`. No accesible en este host `DESKTOP-5586S7P`/`marco`; ruta actual solicitada. No sustituirla por la copia antigua de `marco` ni asumir que sus PLAN huerfanos siguen presentes.

Estado: pendiente de fuente actual. Validacion manual del usuario: APROBADA. Auditoria/regresion independiente actual: NO EJECUTADA. Sin cambios funcionales, reparaciones, commit o push. Ver RESULTADO_CODEX.md para evidencia y secuencia preparada. No retomar las investigaciones amplias ni los temas excluidos en la instruccion actual.

---
## Avance GPT 2026-09-05 21:01 - feedback PLAN persistente y diagnostico seguro de multiparentalidad A1

> Trabajo directo de GPT en Drive; no atribuir a Codex. FreeCAD objetivo 1.1.3.

### Hallazgos de campo incorporados

Marco confirmo en Upala que la preseleccion completa ya resalta todo el simbolo PLAN al hacer clic, pero desaparece al mover el cursor mientras Owner/3D continua seleccionado. `Gui.Selection.setPreselection()` queda clasificado como mecanismo de hover, no como feedback persistente.

La auditoria del arbol mostro que los 10 apagadores A1 no son objetos duplicados: cada `App::Link` tiene dos `TreeParents`, `Apagadores BIM` y `Wall`. Los PLAN aparecen ademas como auxiliares raiz. Se registra aparte que apagadores Rectangle006..Rectangle014 comparten referencia a `Rectangle006`; no se toca en esta fase.

### Investigacion nativa

- Draft 1.1.3 dispone de `draftguitools.gui_trackers.ghostTracker`, overlay Coin temporal utilizado por herramientas nativas como Move/Rotate/Scale.
- BIM/Arch `ViewProviderComponent.claimChildren()` agrega hosted objects al arbol cuando `ClaimHosted=True` (default nativo).
- `Component.getMovableChildren()` tambien usa `Wall.InList` + `Device.Host`; para objetos sin `MoveWithHost`, el hosted object se considera movible con el host.
- `App::PropertyLinkHidden` elimina el backlink/InList. Aunque resolveria la segunda aparicion bajo Wall, tambien eliminaria ese comportamiento nativo de movimiento con host.

### Decision de seguridad

Se llego a implementar localmente un prototipo `Host -> PropertyLinkHidden`, pero **se revirtio antes de prueba de usuario** al comprobar la dependencia de `getMovableChildren()`. `objeto_toma_uno.py` vuelve a rev N; `Host` y `MuroReferencia` no se modifican en esta fase.

La correccion de multiparentalidad queda abierta hasta elegir una estrategia que no pierda comportamiento existente. Alternativas nativas/reutilizables a evaluar:

1. `ClaimHosted=False`: solucion nativa minima y conserva backlinks/movimiento, pero es una preferencia BIM global y puede cambiar otras ramas del arbol; no adoptar sin prueba/decision explicita.
2. Proyeccion electrica por referencia indice, patron ya contemplado en `CONTRATO_ARBOL_SEMANTICO.md`: permite ocultar la identidad fisica del arbol y mostrar una referencia electrica unica, pero requiere lifecycle/seleccion de la referencia.
3. Host hidden + movimiento con host explicito A1: localizado, pero crearia responsabilidad nueva y no se justifica mientras exista comportamiento BIM reutilizable.

### Cambios que si quedan implementados

1. `electriccr/ui/plan_selection.py` v0.3.0
   - Owner sigue siendo la unica seleccion logica;
   - preseleccion completa se usa solo para hover;
   - feedback persistente PLAN usa el `ghostTracker` nativo de Draft, GUI-only y `UNPICKABLE`;
   - overlay no entra en documento, Undo/Redo, guardado, DXF ni arbol;
   - overlay se elimina al deseleccionar, ocultar PLAN o salir de ElectricCR;
   - PLAN A1 se normaliza a `ViewObject.ShowInTree=False` cuando la API lo permite.

2. `electriccr/features/plan_live_sync.py` v0.3.0
   - refresca overlay despues de Placement/DocumentationPlaneZ y cambios de visibilidad;
   - al activar documento normaliza PLAN fuera del arbol;
   - no asigna PLAN.Placement y conserva la expresion PLAN<-Owner.

3. `electriccr/features/objeto_toma_uno.py` permanece rev N
   - PLAN.Owner = `App::PropertyLinkHidden`;
   - no se altera Host/MuroReferencia.

### Prueba real siguiente

Tras reiniciar FreeCAD:

1. seleccionar PLAN en Solo2D y mover el cursor: el simbolo completo debe seguir resaltado;
2. seleccionar Owner 3D directamente con PLAN visible: PLAN debe mostrar feedback persistente;
3. Transformar/mover/girar: PLAN y overlay deben seguir al Owner sin F5;
4. Solo3D retira overlay; Ambos/Solo2D lo restauran cuando corresponda;
5. PLAN no debe aparecer como raiz del arbol;
6. Delete sin aviso, Undo, Redo, save/reopen y cero PLAN huerfanos;
7. la duplicacion Owner bajo `Wall` + `Apagadores BIM` puede continuar por ahora: queda diagnosticada, no se forzara una correccion que rompa host behavior.

Estado: **FEEDBACK IMPLEMENTADO EN DRIVE / SINTAXIS APROBADA / PRUEBA REAL PENDIENTE / ARBOL MULTIPARENTAL DIAGNOSTICADO Y SIN CAMBIO RIESGOSO / A1 OPT-IN**.

---

## Avance GPT 2026-09-05 20:22 - PLAN completo en feedback visual + PropertyLinkHidden implementados en Drive

### Hallazgo nuevo de campo

Marco confirmo en Upala / FreeCAD 1.1.3 que al apuntar o clicar el PLAN el feedback nativo
se limita al subelemento alcanzado (`Edge`, `Vertex`), por lo que visualmente se ilumina una
linea o punto y no el simbolo 2D completo. La redireccion funcional PLAN -> Owner sigue
correcta y no debe cambiar.

Contrato mantenido:

```text
seleccion logica = Owner solamente
feedback visual  = PLAN completo
```

### Cambio minimo implementado

`electriccr/ui/plan_selection.py` v0.2.0:
- normaliza la preseleccion de cualquier `Edge`/`Vertex` de un PLAN A1 al objeto PLAN completo;
- usa la API nativa `Gui.Selection.setPreselection(plan, "")`;
- despues de redirigir el clic a Owner vuelve a aplicar la preseleccion del PLAN completo,
  porque `addSelection()` puede limpiar la preseleccion actual;
- no agrega PLAN a `Gui.Selection`;
- no cambia Placement, Shape ni propiedades documentales.

`electriccr/features/objeto_toma_uno.py` rev N:
- PLAN nuevos usan `App::PropertyLinkHidden` para `Owner`;
- PLAN A1 existentes con `App::PropertyLink` se migran dentro de
  `sync_plan_representation()` mediante remove/add de la propiedad, patron usado tambien
  por herramientas nativas de FreeCAD al cambiar tipos de propiedades dinamicas;
- las expresiones que atraviesan `Owner` se conservan y la expresion canonica de Placement
  se vuelve a verificar inmediatamente;
- dry-run informa `MIGRATE_PLAN_OWNER_LINK_HIDDEN`.

### Verificacion disponible en esta sesion

- investigacion FreeCAD 1.1.3: `setPreselection(obj, subname="")` es API Python nativa;
- FreeCAD Draft Layer usa explicitamente `PropertyLinkListHidden` para evitar el aviso
  `might break` y migra propiedades con `removeProperty()` + `addProperty()`;
- sintaxis Python de ambos archivos modificados: APROBADA;
- archivos actualizados conservando sus mismos IDs de Drive: APROBADO.

### Prueba real obligatoria siguiente

En copia temporal de Upala:

1. reiniciar/recargar ElectricCR;
2. pasar el cursor por distintas lineas del PLAN: debe resaltarse el simbolo completo;
3. clicar PLAN: `Gui.Selection` debe contener solo Owner y PLAN debe conservar feedback completo;
4. probar Solo2D con 3D oculto;
5. sincronizar un PLAN A1 existente y comprobar `Owner` = `App::PropertyLinkHidden`;
6. mover/girar Owner y comprobar PLAN en vivo;
7. Delete sin dialogo de dependencias;
8. Undo / Redo sin Access violation;
9. save/reopen;
10. cero PLAN huerfanos.

A1 continua opt-in. La orientacion en muros inclinados sigue diferida y no se mezcla con este cierre.

---

## Avance GPT 2026-09-05 - correccion A1 Solo2D/Solo3D implementada en Drive

### Causa confirmada

El gestor historico `Configuracion del proyecto/Gestionar_Visibilidad_ElectricCR.FCMacro`
ya implementa `ModoVisual = Ambos / Solo2D / Solo3D`, pero A1 separo las representaciones
en dos ViewObjects y agrego:

```text
Owner.MostrarModelo3D
Owner.MostrarSimboloPlano
```

Estas propiedades no estaban sincronizadas automaticamente con `ModoVisual`. Por eso el
problema recurrente podia persistir aunque el gestor reportara que habia aplicado Solo2D
o Solo3D.

### Correccion GPT en Drive

`electriccr/features/objeto_toma_uno.py` rev M:
- agrega un contrato canonico de modo visual;
- `Ambos` -> 3D visible + PLAN visible;
- `Solo2D` -> 3D oculto + PLAN visible;
- `Solo3D` -> 3D visible + PLAN oculto;
- `MostrarModelo3D` / `MostrarSimboloPlano` siguen siendo flags persistentes independientes;
- cuando el par coincide con un modo canonico, `ModoVisual` se refleja tambien;
- no reconstruye Shape ni cambia Placement/Owner/expresion PLAN.

`electriccr/features/plan_live_sync.py` v0.2.0:
- sigue actualizando PLAN durante Transformar;
- observa tambien `ModoVisual`, `MostrarModelo3D` y `MostrarSimboloPlano`;
- aplica solamente visibilidad de ViewObjects;
- limita el owner interactivo A1 a `App::Link`;
- mantiene guardia de Undo/Redo/rollback.

`InitGui.py`:
- reutiliza los comandos ya existentes;
- agrega `Draft_Move` y `Draft_Snap_Special` a la barra principal ElectricCR cuando estan registrados;
- localiza dinamicamente el comando existente `Gestionar_Visibilidad_ElectricCR` y lo agrega a la misma barra;
- no crea un segundo gestor de visibilidad.

### Reutilizacion de herramienta existente

No se crea un sistema paralelo. Se conserva como interfaz principal:

```text
Configuracion del proyecto/Gestionar_Visibilidad_ElectricCR.FCMacro
```

El catalogo ElectricCR ya la describe como panel para mostrar/ocultar/aislar sistemas y
controlar modo visual 2D/3D.

### Verificacion

- sintaxis de los tres archivos modificados: APROBADA en memoria;
- cambios guardados conservando los mismos IDs de Drive;
- prueba real FreeCAD 1.1.3 de Solo2D/Solo3D/Ambos: PENDIENTE;
- `Transformar` Owner + PLAN en vivo: YA APROBADO por Marco.

Pendientes separados:
- feedback visual de PLAN cuando la seleccion logica es Owner;
- dialogo de dependencia al borrar (PropertyLinkHidden solo candidato, no aplicado);
- orientacion paralela a muros inclinados en colocacion junto a puertas, diferido por Marco.

A1 continua opt-in hasta la prueba real de visibilidad.

---

## Avance de campo 2026-09-05 16:10 - Transformar aprobado y nuevos pendientes

Validacion de Marco en FreeCAD 1.1.3:

- `Transformar` sobre el Owner A1 ya mueve correctamente el dispositivo y el PLAN sin requerir F5: **APROBADO**.
- La UX de visibilidad **solo 3D / solo 2D** no muestra un cambio claro para el usuario y se registra como problema recurrente pendiente. No darla por cerrada solo porque las representaciones tengan `Visibility` independiente internamente.
- Pendiente separado en la herramienta de colocacion junto a puertas: cuando el muro/segmento host esta inclinado, el tomacorriente/dispositivo no queda orientado paralelo a la pared. La orientacion debe derivarse de la tangente/direccion real del muro o tramo host, no asumir ejes X/Y. No mezclar esta correccion con la UX A1 actual.

Estado parcial:

```text
Transformar Owner + PLAN en vivo          APROBADO EN CASO REAL
seleccion PLAN -> Owner                   APROBADO
alineacion en muro inclinado junto puerta PENDIENTE
UX solo 3D / solo 2D                      PENDIENTE RECURRENTE
A1 default                                TODAVIA NO
```

---

## Avance GPT 2026-09-05 16:10 - Transformar deja PLAN atras hasta recompute; Undo inseguro corregido

### Validacion real de Marco

Documento: Upala / FreeCAD 1.1.3.

Marco confirmo:

- `Transformar` coloca el manipulador en el origen del simbolo 2D;
- durante el drag se mueve visualmente solo el Owner/3D;
- PLAN conserva el Placement anterior hasta recompute/F5;
- despues de recompute PLAN vuelve a coincidir;
- `Snap Special` puede activarse, pero por si solo no produce un cambio visible;
- durante Undo de `ElectricCR: colocar apagadores junto a puertas BIM` aparecio `Access violation`.

El PLAN inspeccionado conserva:

```text
Owner = Link_Apagador_...008
ExpressionEngine = Placement <- Owner.Placement
RepresentationSchemaVersion = 2
SnapPoints = [(0,0,0)]
```

Por tanto no se perdio el contrato; el defecto es de **refresco/recompute interactivo**.

### Correccion GPT en Drive

1. `plan_lifecycle.py` 0.1.1:
   - no interviene si `doc.isPerformingTransaction()` es verdadero;
   - evita borrar/encolar PLAN durante Undo/Redo/rollback;
   - protege tambien los flush/fallbacks contra transaction replay.

   Motivo: FreeCAD ya reproduce creacion/borrado de Owner+PLAN en la transaccion original.
   El observer no debe mutar el documento mientras el motor de Undo/Redo esta reproduciendo esa transaccion.

2. Nuevo `electriccr/features/plan_live_sync.py`:
   - observa cambios de objetos A1;
   - ante cambio de `Owner.Placement` (y `DocumentationPlaneZ`) ejecuta `PLAN.recompute()`;
   - recompone solamente el PLAN, no todo el documento;
   - nunca asigna `PLAN.Placement` directamente;
   - no actua durante Undo/Redo/rollback.

3. `InitGui.py` instala ambos observers de forma idempotente.

### Regla sobre Snap Special

`Draft Snap Special` es un **modo de captura**, no un comando de movimiento ni un marcador permanente.
Solo se aprecia cuando una herramienta como `Draft Move` solicita un punto y el cursor puede capturar
`PLAN.SnapPoints=(0,0,0)`. No tiene efecto sobre el dragger nativo de `Transformar`.

`InitGui.py` vigente ya contiene `Draft_Snap_Special` dentro de la barra `Draft compacto`. Si no aparece
en la sesion actual, reiniciar FreeCAD o reconstruir la barra es necesario porque la instancia del Workbench
puede conservar `_built=True` y no reconstruir toolbars tras una simple recarga de modulo.

### Prueba real siguiente

Tras reiniciar FreeCAD 1.1.3 con el codigo sincronizado:

1. crear/sincronizar un apagador A1;
2. usar `Transformar`;
3. comprobar si PLAN se mueve durante el drag o, como minimo, al soltar sin F5;
4. mover repetidamente y vigilar rendimiento;
5. Undo/Redo de la transformacion;
6. Undo de la transaccion de creacion de varios apagadores: **no debe existir Access violation**;
7. Redo;
8. Delete individual y Undo/Redo;
9. probar `Draft Move` con `Snap Special` para verificar captura del origen 0,0,0.

Estado: `IMPLEMENTADO EN DRIVE / PRUEBA REAL OBLIGATORIA / A1 CONTINUA OPT-IN`.

---

## Avance GPT 2026-09-05 15:43 - validacion real de seleccion, visibilidad y borrado

### Validacion funcional de Marco en FreeCAD 1.1.3

Sobre Upala se confirmo:

- clic sobre PLAN -> la seleccion funcional queda en el Owner `App::Link`;
- 2D y 3D se mueven juntos;
- visualmente FreeCAD resalta solamente el 3D del Owner; PLAN no queda resaltado;
- al ocultar el Owner se oculta solamente el 3D y PLAN permanece visible;
- Delete sobre Owner elimina ahora Owner + PLAN, pero `Std_Delete` muestra antes un dialogo
  de dependencias indicando que PLAN puede romperse.

La separacion de visibilidad es correcta para el objetivo de trabajar en planta. El
problema pendiente es que, cuando el 3D esta oculto, la identidad seleccionada puede no
tener feedback visual sobre PLAN.

### Diagnostico del aviso de dependencias

El aviso aparece antes de que `plan_lifecycle.py` pueda ejecutar la limpieza. La GUI
`Std_Delete` detecta el enlace normal:

```text
PLAN.Owner : App::PropertyLink
```

como una dependencia entrante y pregunta al usuario antes de borrar.

FreeCAD dispone de `App::PropertyLinkHidden`, documentado en el codigo fuente como un
PropertyLink oculto al chequeo de dependencias. Hereda de `PropertyLink` y es el candidato
nativo preferente para evitar el dialogo sin crear un comando Delete ElectricCR propio.

NO cambiar todavia la propiedad productiva. Antes se requiere un probe real en FreeCAD
1.1.3 que demuestre simultaneamente:

1. `PLAN.Owner` funciona como `App::PropertyLinkHidden`;
2. la expresion `PLAN.Placement <- Owner.Placement` sigue actualizando movimiento/giro;
3. recompute automatico no se pierde por ocultar esa arista de dependencia;
4. Delete Owner no muestra el dialogo de dependencias;
5. `plan_lifecycle.py` sigue borrando PLAN;
6. Undo/Redo restaura/elimina ambos en una sola operacion;
7. save/reopen conserva Owner y expresion;
8. no aparecen ciclos ni PLAN huerfanos.

Si falla la propagacion parametrica, conservar `PropertyLink` normal y buscar otra
estrategia de borrado sin ocultar la dependencia.

### Feedback visual PLAN sin doble seleccion

No seleccionar PLAN logicamente junto con Owner: comandos como Draft Move/Delete podrian
recibir dos objetos y PLAN tiene Placement gobernado por expresion.

Primera prueba nativa a realizar:

```text
Owner = seleccion logica
PLAN  = preseleccion/highlight visual temporal
```

mediante `Gui.Selection.setPreselection(...)`.

La preseleccion es nativa pero puede desaparecer al mover el cursor. Solo adoptarla si en
FreeCAD 1.1.3 produce una UX estable. Si no, estudiar un overlay Coin/ViewProvider visual
que no modifique propiedades del documento ni convierta PLAN en segunda seleccion.

### Que es Draft Snap Special

`Draft Snap Special` es un modo nativo de Draft/BIM. Hace que las herramientas que piden
puntos, como `Draft Move`, puedan capturar los puntos especiales declarados por un objeto.

A1 declara:

```text
PLAN.SnapPoints = [Vector(0,0,0)]
```

por lo que Snap Special permite capturar exactamente el punto de insercion del simbolo.

Se activa desde la barra **Draft Snap** o desde el widget de snaps de Draft/BIM, pulsando
**Snap Special**. ElectricCR tambien lo expone en `Draft compacto` cuando el codigo vigente
esta cargado. Debe estar activo `Snap Lock` para que el snapping funcione.

No se considera ideal exigir este paso manual para siempre. Si el flujo final requiere una
herramienta ElectricCR de mover desde planta, esta debera reutilizar Draft Snap y activar/
restaurar el modo necesario sin crear un sistema de snap paralelo.

Estado actualizado:

```text
seleccion PLAN -> Owner              VALIDADA EN CASO REAL
movimiento 2D/3D conjunto            VALIDADO EN CASO REAL
visibilidad 3D independiente         VALIDADA EN CASO REAL
feedback visual PLAN seleccionado    PENDIENTE
borrado Owner + PLAN                 VALIDADO, CON DIALOGO MOLESTO
PropertyLinkHidden para Owner        CANDIDATO NATIVO / POR PROBAR
SnapPoint PLAN (0,0,0)               IMPLEMENTADO / PRUEBA UX PENDIENTE
A1 default                           TODAVIA NO
```

---

## Avance GPT 2026-09-05 14:35 - punto de insercion PLAN con Draft Snap Special

### Hallazgo nativo

FreeCAD Draft ya implementa el concepto requerido mediante `SnapPoints` + `Draft Snap Special`.

El `Snapper` nativo evalua cualquier objeto con propiedad `SnapPoints` y transforma
cada vector local mediante `obj.Placement.multVec(p)`. Por tanto, A1 puede definir:

```text
PLAN.SnapPoints = [Vector(0,0,0)]
```

sin agregar geometria al `Shape`, sin crear otra identidad y sin contaminar DXF.

`Draft Move` ya esta disponible en `Draft compacto` y usa el flujo nativo:

```text
objeto seleccionado -> punto base -> punto destino
```

### Auditoria de prototipos 2D actuales

Registro vigente:
- `Tomacorriente_120V -> toma_normal.step`
- `Apagador_Simple -> switch_simple.step`

Inspeccion STEP:
- `toma_normal.step`: un borde/curva comienza en aproximadamente `(0,0,0)`, por lo
  que Snap Endpoint ya puede capturar el origen;
- `switch_simple.step`: contiene un `GEOMETRIC_CURVE_SET` con un
  `CARTESIAN_POINT` en aproximadamente `(0,0,0)`;
- `etiqueta_circuito.step`: contiene un borde cuyo endpoint esta en `(0,0,0)`;
- `Luminaria_LED_Redonda_1000lm_2D.step`: circulo centrado en `(0,0,0)`, capturable
  por Snap Center, pero sin vertex explicito en el centro;
- `Luminaria 60x60.step`: no expone geometria capturable en el centro;
- `Sensor de Humo.step`: contiene multiples colocaciones geometricas con centro en
  el origen, pero no un vertex explicito equivalente al apagador.

Ademas, `registry_electric.json` referencia `toma_gfci.step`, `toma_240v.step` y
`toma_tv.step`, pero esos recursos no aparecen actualmente en Drive. Registrar como
deuda separada; no mezclar con esta tarea.

### Implementacion GPT en Drive

`electriccr/features/objeto_toma_uno.py` rev L:
- agrega `App::PropertyVectorList SnapPoints` a PLAN A1;
- fija exactamente un punto local `Vector(0,0,0)`;
- `sync_plan_representation(..., dry_run=True)` informa
  `SET_PLAN_INSERTION_SNAP` cuando falta o es incorrecto;
- no cambia `Shape`, `RepresentationSignature` ni esquema 2;
- los PLAN existentes reciben la propiedad solo cuando pasan explicitamente por
  `sync_plan_representation`; no hay migracion masiva.

`InitGui.py`:
- agrega `Draft_Snap_Special` a `Draft compacto`;
- conserva `Draft_Move`, `Draft_Snap_Endpoint` y `Draft_Snap_Center`.

`tests/freecad_plan_owner_spatial_sync_a1_smoke.py`:
- exige un solo SnapPoint local `(0,0,0)`;
- verifica que `PLAN.Placement.multVec(SnapPoint)` coincida con
  `PLAN.Placement.Base`.

Compilacion sintactica de los tres archivos: OK.

### Prueba real pendiente

En FreeCAD 1.1.3:
1. crear/sincronizar toma A1 y apagador A1;
2. ocultar 3D y dejar PLAN visible;
3. clic PLAN -> Owner;
4. activar `Draft Move`;
5. activar `Snap Special`;
6. capturar el punto de insercion `(0,0,0)` como punto base;
7. mover a un punto destino;
8. verificar Owner/PLAN/3D;
9. Undo/Redo;
10. repetir con un simbolo sin vertex central, preferiblemente luminaria 60x60.

Estado: `IMPLEMENTADO EN DRIVE / POR VERIFICAR EN FREECAD REAL`.

---

## Avance GPT 2026-09-05 14:05 - borrado conjunto Owner + PLAN

### Validacion funcional de Marco

En FreeCAD 1.1.3, sobre Upala, Marco confirmo:

- clic sobre PLAN ya no deja seleccionado el auxiliar documental;
- queda seleccionado el dispositivo principal/Owner;
- al mover el dispositivo, 2D y 3D se mueven juntos;
- al borrar el dispositivo con Delete, el PLAN no se borra y queda huerfano.

Evidencia observada despues del borrado:

```text
Apagador - Rectangle009 [PLAN]
DocumentationOnly = true
RepresentationRole = PLAN
RepresentationSchemaVersion = 2
Owner = null
ExpressionEngine conserva referencia .Owner...
```

Por tanto, seleccion y sincronizacion espacial quedan funcionalmente confirmadas en
este caso; el nuevo defecto es de **ciclo de vida/borrado semantico**.

### Investigacion nativa

- `App::PropertyLink` rompe el enlace cuando desaparece el objeto referenciado, pero
  no implica borrado en cascada.
- `App::PropertyLinkChild` expresa alcance/child y puede influir en jerarquia, pero
  no se adopta como garantia de borrado cascada.
- `Gui::ViewProvider.onDelete()` permite que un ViewProvider elimine otros objetos,
  pero el Owner es `App::Link` con `ViewProviderLink` nativo y no debe sustituirse.
- FreeCAD ofrece `App.addDocumentObserver()` y `slotDeletedObject(obj)` para observar
  objetos que estan por eliminarse.
- `App::Document.hasPendingTransaction()` permite saber si la eliminacion forma parte
  de una transaccion Undo/Redo.

Se evita convertir Owner a `App::LinkPython`, sustituir `ViewProviderLink`, introducir
grupos artificiales o modificar el contrato PLAN <- Owner solo para resolver borrado.

### Implementacion GPT en Drive

Nuevo modulo:

```text
ElectricCR/electriccr/features/plan_lifecycle.py
```

Responsabilidad:

```text
Delete Owner A1
    -> slotDeletedObject(owner)
    -> resolver DocumentationRepresentationName / Owner relation
    -> poner PLAN en cola
    -> si existe transaccion:
         borrar PLAN antes de cerrar la misma transaccion cuando FreeCAD lo permita
       si no existe:
         borrar PLAN directamente
    -> fallback despues de commit si el callback before-close no ocurrio
```

`InitGui.py` instala este observador desde `Initialize()` y **no lo desinstala al
cambiar de Workbench**, porque el borrado conjunto pertenece al contrato de datos y no
solo a la UX de ElectricCR.

El observador:

- actua unicamente sobre Owner `PhysicalDocumentationA1`;
- reutiliza `objeto_toma_uno.is_electriccr_device()` y `get_plan_representation()`;
- no modifica Placement, Shape, expresiones ni seleccion;
- evita borrado reentrante con guardia;
- soporta varios documentos por nombre;
- conserva pendientes si un borrado falla.

### Pruebas ejecutadas fuera de FreeCAD real

- compilacion sintactica de `plan_lifecycle.py`: OK;
- compilacion sintactica del `InitGui.py` modificado: OK;
- mock con transaccion abierta: PLAN eliminado sin abrir segunda transaccion;
- mock sin transaccion: PLAN eliminado inmediatamente;
- mock fallback post-commit: PLAN eliminado en transaccion de recuperacion.

### Prueba real pendiente obligatoria

En FreeCAD 1.1.3:

1. crear toma A1 y apagador A1;
2. confirmar clic PLAN -> Owner;
3. Delete sobre Owner;
4. confirmar que desaparecen Owner y PLAN;
5. confirmar cero `DocumentationOnly` con `Owner=null`;
6. Undo: deben volver Owner + PLAN enlazados;
7. Redo: deben desaparecer ambos;
8. repetir con 2 documentos abiertos;
9. guardar/reabrir y repetir;
10. comprobar que eliminar un objeto legacy no dispara esta limpieza.

Hasta esa prueba, ciclo de vida A1 = `IMPLEMENTADO / POR VERIFICAR`.

---

## Investigacion nativa adicional 2026-09-05 - priorizar transformacion de App::Link

Antes de implementar UX propia, queda obligatorio probar primero la infraestructura nativa de FreeCAD 1.1.3.

Hallazgos verificados en la documentacion/codigo fuente oficial de FreeCAD:

- `Gui::ViewProviderDragger` es la clase base para ViewProviders que modifican el `Placement` de geometria.
- `ViewProviderDragger` dispone de `TransformOrigin`; el dragger se posiciona como `ObjectPlacement * TransformOrigin` y al finalizar escribe de vuelta el `Placement` del objeto.
- El propio codigo de FreeCAD documenta que el centro de transformacion debe corresponder al origen.
- `Gui::ViewProviderLink` ya implementa edicion `Transform`, `DraggerContext`, `initDraggingPlacement()`, `currentDraggingPlacement()` y `updateDraggingPlacement()` para `App::Link`.
- `ViewProviderLink.doubleClicked()` puede entrar directamente en modo `Transform`.
- `ViewProviderDragger.forwardToLink()` ya contiene el patron nativo de reenviar una edicion al primer `App::Link` de una cadena de subobjetos.
- `Draft Move` mueve objetos 2D y 3D usando punto base y punto destino y utiliza Draft Snap.
- `App::Link.Placement` es una propiedad nativa absoluta de la instancia; no hace falta crear una segunda coordenada para la representacion PLAN.

Orden de reutilizacion obligatorio:

1. probar `ViewProviderLink` / modo `Transform` nativo sobre el Owner;
2. probar `TransformOrigin=(0,0,0)` y verificar que el manipulador coincide con el punto de insercion;
3. probar `Draft Move` + Draft Snap usando el mismo origen;
4. resolver clic PLAN -> Owner con la menor capa posible de seleccion;
5. `SelectionObserver` solo si la seleccion nativa/ViewProvider no puede representar PLAN como superficie de clic del Owner;
6. un dragger ElectricCR propio solo si FreeCAD 1.1.3 demuestra una limitacion concreta.

No modificar `ViewProviderLink` nativo ni sustituirlo. No duplicar un sistema de grips que FreeCAD ya proporciona.

Fuentes de referencia:
- FreeCAD `src/Gui/ViewProviderDragger.cpp/.h`
- FreeCAD `src/Gui/ViewProviderLink.cpp/.h`
- FreeCAD `Draft_Move`
- FreeCAD `Draft_Snap`
- FreeCAD `Scripted_objects` / seleccion mediante ViewProvider

---

# TAREA VIGENTE - ElectricCR / A1 edicion interactiva desde PLAN 2D

Fecha: 2026-09-05 12:37 America/Costa_Rica
FreeCAD objetivo: `1.1.3`
Estado: `ACTIVA / UX 2D PENDIENTE / A1 CONTINUA OPT-IN`

## 0. Contexto y objetivo

La sincronizacion espacial A1 `PLAN <- Owner` ya esta implementada y probada mediante una expresion nativa persistente. Esa solucion debe conservarse.

El nuevo problema es de **interaccion/edicion desde planta**:

- al hacer clic sobre el simbolo PLAN, FreeCAD selecciona hoy el auxiliar documental `...[PLAN]`;
- `PLAN.Placement` esta gobernado por expresion y por diseño no debe convertirse en una segunda autoridad editable;
- el usuario necesita poder ocultar el 3D y trabajar practicamente solo con el 2D, como en un plano normal;
- mover desde el 2D debe mover la identidad funcional y, por consecuencia, tambien el 3D;
- el punto local `(0,0,0)` del simbolo 2D debe actuar como punto de insercion, snap y referencia preferente de arrastre/movimiento.

Objetivo funcional:

```text
                 Device / App::Link
                 identidad unica
                      |
              Device.Placement
              unica autoridad
                 /          \
                /            \
          Physical 3D       PLAN 2D
              ^                ^
              |                |
        editar desde 3D   editar desde 2D
              \                /
               \              /
                Device.Placement
```

No crear una dependencia bidireccional entre dos Placements. El PLAN sigue derivando su transformacion desde `Owner.Placement`. La edicion desde 2D debe escribir en el `Owner`.

## 1. Fuente de verdad y entorno de trabajo

Trabajar directamente sobre el arbol local real que usa FreeCAD en esta computadora:

`C:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\`

No crear una copia paralela del codigo. Google Drive conserva documentacion, tareas y evidencias, pero el codigo debe modificarse en el arbol local vigente.

Leer antes de modificar:

- `AGENTS.md`;
- Skills aplicables;
- `ElectricCR/TAREA_ACTUAL.md`;
- `ElectricCR/RESULTADO_CODEX.md`;
- `ElectricCR/ESTADO_PROYECTO.md`;
- `ElectricCR/docs/RESUMEN_DISPOSITIVO_ELECTROMECANICO.md`;
- `ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md`;
- codigo vigente de `electriccr/features/objeto_toma_uno.py`;
- carga/activacion GUI de ElectricCR y cualquier observador de seleccion ya existente.

## 2. Regla de seleccion PLAN -> Owner

Comportamiento requerido:

```text
clic sobre geometria de PLAN
        -> resolver PLAN.Owner
        -> seleccion funcional final = Owner / Device
```

Ejemplo real:

```text
Apagador - Rectangle006 [PLAN]
ECR_DocPlan_...
        -> Owner
Apagador - Rectangle006
Link_Apagador_Rectangle006
```

El usuario no debe percibir PLAN como una segunda identidad funcional.

Requisitos:

- conservar `PLAN.Owner` como enlace documental;
- PLAN no recibe `ElementUID` propio;
- si se selecciona PLAN en la vista 3D, redirigir la seleccion al Owner;
- evitar recursividad de seleccion y parpadeos;
- la solucion debe ser limitada a PLAN ElectricCR (`DocumentationOnly=true`, `RepresentationRole=PLAN`, Owner valido), no afectar otros objetos de FreeCAD;
- probar con varios documentos abiertos y cambios de pestaña/documento en FreeCAD 1.1.3;
- si FreeCAD permite resolverlo mediante mecanismo nativo del ViewProvider/seleccion, preferirlo; usar `Gui.Selection` observer solo si es la solucion minima y robusta para este caso;
- no usar la seleccion para sincronizar Placement: esa responsabilidad sigue en la expresion ya aprobada.

## 3. PLAN oculto del arbol, visible en la vista

Evaluar y aplicar, si es estable en 1.1.3, que los PLAN A1 nuevos queden ocultos del arbol (`ShowInTree=false` o mecanismo nativo equivalente), manteniendo:

- geometria visible en planta;
- exportacion DXF;
- `Owner`;
- expresion de Placement;
- save/reopen;
- posibilidad de diagnostico por propiedades/API aunque no aparezca como una identidad normal en el arbol.

No ocultar el Device/Owner principal.

Para PLAN existentes, no hacer barrido masivo del documento productivo. La actualizacion puede ocurrir de forma idempotente al pasar por el sincronizador A1, salvo que la prueba justifique otra estrategia explicita y segura.

## 4. Edicion desde 2D con 3D oculto

Debe ser posible este flujo:

```text
MostrarModelo3D = false
MostrarSimboloPlano = true

usuario trabaja en planta
        -> selecciona simbolo 2D
        -> la seleccion funcional es Owner
        -> mueve el dispositivo desde la planta
        -> cambia Owner.Placement
        -> expresion actualiza PLAN
        -> al volver a mostrar 3D, el modelo esta en la nueva posicion
```

Primera opcion a reutilizar: herramientas nativas de Draft/FreeCAD, especialmente `Draft Move`, snaps y punto base/destino.

No crear de entrada un dragger propio ni un modo de edicion paralelo. Solo considerar un manipulador propio si la prueba real demuestra que Draft/FreeCAD no proporciona una UX util.

La operacion debe participar correctamente en transaccion/Undo/Redo.

## 5. Origen local `(0,0,0)` como punto de insercion y arrastre

Contrato para simbolos ElectricCR 2D:

```text
local (0,0,0)
    = punto de insercion
    = referencia de Placement
    = snap principal
    = punto base preferente para movimiento desde planta
```

El usuario indica que los bloques/simbolos 2D ya pueden contener un punto dibujado en el origen. Auditar antes de modificar recursos:

1. revisar los prototipos STEP 2D usados por tomacorriente y apagador;
2. comprobar si existe un Vertex/punto util exactamente en `(0,0,0)`;
3. comprobar si Draft Snap puede capturarlo de manera fiable en la vista;
4. comprobar que el origen local transformado coincide con `Owner.Placement.Base` en planta;
5. no insertar geometria adicional en todos los prototipos sin verificar impacto visual y DXF;
6. si hace falta un mecanismo de SnapPoints, reutilizar capacidades nativas cuando sea posible y no duplicar informacion sin necesidad.

El punto de origen es una referencia de insercion/edicion, no una segunda coordenada independiente del Device.

## 6. Movimiento bidireccional sin doble autoridad

Debe aprobar simultaneamente:

```text
mover Device/3D
    -> Owner.Placement cambia
    -> PLAN sigue por expresion

mover desde PLAN/2D
    -> se modifica Owner.Placement
    -> PLAN sigue por expresion
    -> 3D aparece en la nueva posicion
```

Nunca:

```text
PLAN.Placement libre <-> Owner.Placement
```

porque produciria dos autoridades/ciclos.

## 7. Casos reales de prueba

Usar copia temporal/controlada; nunca guardar pruebas destructivas sobre originales.

### 7.1 Upala - apagador

Caso recomendado:

- `Apagador - Rectangle006`;
- `Link_Apagador_Rectangle006`;
- PLAN `Apagador - Rectangle006 [PLAN]`.

Comprobar:

1. clic en PLAN selecciona Owner;
2. auxiliar PLAN no se presenta como identidad normal en el arbol si `ShowInTree=false` resulta estable;
3. ocultar 3D;
4. dejar PLAN visible;
5. activar movimiento nativo;
6. usar origen `(0,0,0)`/punto de insercion como punto base cuando sea viable;
7. mover X/Y;
8. `Owner.Placement` cambia;
9. PLAN queda alineado;
10. mostrar 3D y confirmar nueva posicion;
11. Undo/Redo;
12. save/reopen;
13. sin PLAN huerfano.

### 7.2 Tomacorriente A1

Repetir el flujo con una toma A1 nueva o fixture minimo.

### 7.3 Multidocumento

Con dos FCStd abiertos:

- seleccionar PLAN en documento A -> seleccionar Owner correcto de A;
- cambiar a documento B -> no redirigir a objetos de A;
- cerrar uno de los documentos -> observador/mecanismo queda estable;
- recargar/activar/desactivar Workbench -> no duplicar observadores.

## 8. Regresiones obligatorias

Conservar lo ya aprobado:

- expresion `PLAN.Placement <- Owner`;
- `RepresentationSchemaVersion=2`;
- `RepresentationSignature` sin coordenadas;
- `DocumentationPlaneZ`;
- `PlanSymbolScale`;
- Shape fisica 3D separada;
- PLAN volumen 0 / solidos 0;
- DXF desde PLAN;
- cambio de altura/relink;
- Space, Host, PuertaOrigen;
- UID unico solo en Device;
- cero huerfanos;
- save/reopen;
- Undo/Redo;
- compatibilidad legacy.

No volver a unir 2D+3D.

## 9. Criterio de aceptacion

La tarea aprueba si se demuestra en FreeCAD 1.1.3:

```text
clic PLAN -> Owner seleccionado                    OK
PLAN no se comporta como segunda identidad         OK
3D puede permanecer oculto                         OK
trabajo util solo con PLAN visible                 OK
mover desde 2D modifica Owner.Placement             OK
PLAN sigue automaticamente                         OK
al mostrar 3D coincide con nueva posicion           OK
origen 0,0,0 sirve como referencia/snap             OK
Undo/Redo                                           OK
save/reopen                                         OK
multidocumento estable                              OK
DXF y Shape fisica sin regresiones                  OK
cero huerfanos                                      OK
```

Solo despues de cerrar esta UX se reconsidera cambiar A1 a default para objetos nuevos. Esta tarea no cambia el default.

## 10. Restricciones

NO:

- cambiar A1 a default;
- migrar legacy;
- convertir masivamente PLAN existentes;
- modificar originales FCStd durante pruebas;
- eliminar la expresion de Placement aprobada;
- permitir un Placement PLAN independiente;
- crear otro objeto electromecanico;
- sustituir `objeto_toma_uno.py` por una arquitectura paralela;
- agregar un observador global que afecte objetos ajenos a ElectricCR;
- crear un dragger propio antes de probar la solucion nativa;
- hacer commit ni push.

## 11. Documentacion de cierre

Actualizar en las mismas ubicaciones:

- `ElectricCR/RESULTADO_CODEX.md`;
- `ElectricCR/ESTADO_PROYECTO.md`;
- `ElectricCR/TAREA_ACTUAL.md`;
- `ElectricCR/REVISION_MACROS.md` si cambia alguna macro/registro;
- `ElectricCR/docs/RESUMEN_DISPOSITIVO_ELECTROMECANICO.md`;
- `ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md` si cambia el mecanismo final.

Registrar exactamente:

- mecanismo usado para redirigir seleccion;
- si se usa o no `ShowInTree=false`;
- resultado de Draft Move/snaps;
- resultado del origen 0,0,0;
- pruebas toma/apagador/multidocumento;
- cualquier limitacion de FreeCAD 1.1.3.

---

## Historial previo

# TAREA VIGENTE - ElectricCR / A1 sincronizacion espacial PLAN-Owner

Fecha: 2026-09-03 20:25 America/Costa_Rica
FreeCAD objetivo: `1.1.3`
Estado: `CERRADA / EXPRESION NATIVA APROBADA / A1 APTO PARA DEFAULT NUEVO, AUN OPT-IN`

## Cierre 2026-09-05 - sincronizacion espacial aprobada

La causa quedo confirmada: el PLAN A1 era un `Part::Feature` cuyo
`App::PropertyLink Owner` expresaba pertenencia, pero `sync_plan_representation`
copiaba el Placement solo durante una sincronizacion explicita. Ademas,
`RepresentationSignature` mezclaba configuracion grafica con X/Y/Z/rotacion.
Por eso un movimiento posterior del `App::Link` no tocaba el PLAN.

Se evaluaron las tres alternativas documentadas en FreeCAD `1.1.3`:

| alternativa | clasificacion | resultado |
|---|---|---|
| expresion nativa en `Part::Feature` | REUTILIZAR | aprobada; atraviesa `Owner`, persiste y participa en recompute/Undo |
| `Part::FeaturePython` documental | COEXISTIR / NO NECESARIA | viable como reserva, pero agrega proxy sin aportar ventaja al caso |
| observador global GUI/Qt | DESCARTAR | innecesario y mas acoplado al ciclo de vida de la interfaz |

Mecanismo definitivo:

```text
PLAN.Placement = placement(
  vector(Owner.Placement.Base.x;
         Owner.Placement.Base.y;
         Owner.DocumentationPlaneZ);
  Owner.Placement.Rotation
)
```

`Device.Placement` es ahora la unica autoridad de X/Y/orientacion.
`DocumentationPlaneZ` conserva Z documental. `PlanSymbolScale` sigue
reconstruyendo solamente la geometria documental. La firma esquema `2` contiene
solo version, tipo/variante grafica, offsets del simbolo y escala; ya no contiene
UID, Placement ni Z documental.

La regresion `freecad_plan_owner_spatial_sync_a1_smoke.py` uso una copia
temporal de `Chomes-Segundo Piso.FCStd`. En ella reprodujo
`Owner X=19263`, `PLAN X=19003.999751956`, delta `259.000248044 mm`. Una
sincronizacion A1 instalo la expresion y corrigio el desfase sin editar PLAN.
Despues aprobaron:

- movimiento +500 mm en X y +275 mm en Y;
- giro del Owner a 90 grados;
- `AlturaRel` 300 -> 450 mm sin separar PLAN;
- `DocumentationPlaneZ=225 mm` sin cambiar la geometria documental;
- `PlanSymbolScale=1.35` sin alterar Shape fisica;
- Undo/Redo de movimiento y giro;
- un apagador A1 con giro a 83 grados, altura 1350 mm, Z documental 75 mm,
  escala 0.80 y `PuertaOrigen=Window011`;
- save/reopen, tres recomputes, sincronizacion idempotente y cero huerfanos;
- DXF documental de `20008` bytes y Shape fisica invariante durante exportacion.

La prueba A1 general de una toma y un apagador tambien aprobo nuevamente.
El original conservo SHA-256
`E36A28A4AADE9615701B7B7354F905EA370B1FD057F5F2D0AD8A66E785404E7D`,
tamano `3898540` bytes y fecha de modificacion. La copia FCStd se cerro y
elimino; informe y DXF quedaron en `ElectricCR/Pruebas y regresiones` de Drive.

Los PLAN A1 esquema 1 existentes reciben la dependencia cuando se ejecuta una
sincronizacion A1; no se hizo migracion productiva ni se modifico Chomes.

**Decision:** la tarea aprueba completamente y A1 vuelve a quedar **APTO PARA
SER DEFAULT DE OBJETOS NUEVOS**. Por restriccion de esta tarea, el default no se
cambio y A1 permanece opt-in hasta autorizacion separada.

## 0. Motivo de reapertura

Despues de la aceptacion GUI anterior, un uso real en `Chomes-Segundo Piso.FCStd`
revelo un caso que las pruebas anteriores no cubrieron: mover manualmente la
identidad `App::Link` A1 puede dejar su representacion `PLAN` en la posicion
anterior.

Caso real documentado por el usuario:

```text
Owner: Link_TomaBIM_011
ElementUID: 975bd98d-7a56-4765-b5d5-f6d778452c90
Owner.Placement: X=19263, Y=11260, Z=0
PLAN: ECR_DocPlan_975bd98d_7a56_4765_b5d5_f6d778452c90
PLAN.Placement: X=19004, Y=11260, Z=0
Diferencia X: 259 mm
PLAN.Owner: Link_TomaBIM_011
PLAN.ExpressionEngine: []
```

`RepresentationSignature` del PLAN conserva tambien la posicion previa
`X≈19003.999752`, lo que confirma que la representacion fue sincronizada en un
momento anterior pero no siguio el cambio posterior de Placement del Owner.

La relacion `PLAN.Owner -> dispositivo` expresa pertenencia, pero actualmente no
garantiza dependencia espacial dinamica.

## 1. Decision inmediata

Queda suspendida la recomendacion anterior de hacer A1 default para objetos
nuevos hasta corregir y verificar este defecto.

No revertir A1 a `LegacyCompound` ni volver a combinar 2D y 3D en una sola
Shape. La separacion fisica/documental se mantiene.

La correccion debe completar el contrato A1 con una sola autoridad espacial:

```text
Dispositivo A1
  |-- Placement                 <- UNICA AUTORIDAD ESPACIAL
  |-- LinkedObject/master       <- Shape fisica 3D
  `-- PLAN DocumentationOnly
       |-- Owner -> dispositivo
       |-- Shape 2D documental
       `-- transformacion derivada del Owner
```

## 2. Regla de transformacion

PLAN no debe tener una ubicacion independiente de la identidad.

Debe derivar automaticamente del Owner:

- X del Owner;
- Y del Owner;
- orientacion/yaw de planta del Owner;
- Z documental desde `DocumentationPlaneZ`;
- escala documental desde `PlanSymbolScale` u otra propiedad documental;
- cualquier offset documental debe ser explicito y separado del Placement
  fisico, nunca un desplazamiento accidental editable como segunda autoridad.

Cambiar `AlturaRel` puede modificar el modelo 3D/relink del master, pero no debe
separar PLAN en XY ni orientacion.

## 3. Arquitectura a conservar

Conservar sin regresion:

- una sola identidad `App::Link`;
- master fisico reutilizable e inmutable;
- Shape del master/Link exclusivamente fisica;
- PLAN sin volumen ni solidos;
- `DocumentationOnly=true`;
- `Owner` hacia la identidad;
- `ElementUID`, `Space`, `Host`, `PuertaOrigen` cuando aplique;
- DXF consumiendo PLAN;
- Undo/Redo;
- save/reopen;
- eliminacion y auditoria de PLAN huerfanos;
- compatibilidad `LegacyCompound` existente.

## 4. Diagnostico a realizar cuando vuelva Codex/MCP

Antes de modificar codigo, auditar exactamente:

1. implementacion vigente de `sync_plan_representation`;
2. como se calcula y escribe `PLAN.Placement`;
3. que incluye `RepresentationSignature` y por que contiene Placement;
4. si `Owner` es `App::PropertyLink` y que dependencias de recompute crea;
5. si una expresion nativa de FreeCAD 1.1.3 puede gobernar de forma robusta el
   Placement/rotacion de PLAN desde Owner manteniendo Z documental;
6. si `Part::FeaturePython` con proxy documental aporta una dependencia mas
   fiable que expresiones;
7. como afecta cada alternativa a save/reopen, Undo/Redo, clonacion/copia,
   renombrado, recompute y DXF.

No implementar un observador global de GUI/Qt como primera opcion. Preferir una
dependencia parametricamente representada en el documento de FreeCAD.

## 5. Hipotesis de solucion - no cerrada sin prueba real

Orden de preferencia a evaluar:

### Opcion A - dependencia nativa mediante expresiones

Mantener PLAN como `Part::Feature`, usando una dependencia persistente que derive
su transformacion del `Owner`.

Ventaja esperada: minimo cambio y dependencia almacenada en el documento.

Debe comprobarse en FreeCAD 1.1.3 que movimiento y rotacion manual del
`App::Link` disparen correctamente la actualizacion y que no se creen ciclos.

### Opcion B - PLAN como `Part::FeaturePython`

Proxy documental con `Owner` como entrada y `execute()` encargado de derivar
Placement/Shape documental.

Usarla solo si la opcion A no representa de forma robusta la dependencia.

### Opcion C - sincronizacion imperativa/observador

No preferida. Solo considerar si las dependencias nativas no resuelven el caso.
Debe evitar acoplamiento a `FreeCADGui`, Qt o eventos globales.

## 6. RepresentationSignature

Separar conceptualmente firma de geometria documental y transformacion espacial.

La firma no debe convertir un movimiento simple del dispositivo en una
reconstruccion completa del simbolo si familia, variante y escala no cambiaron.

Objetivo conceptual:

```text
RepresentationSignature
  -> familia/tipo
  -> variante del simbolo
  -> escala documental
  -> version del esquema

Placement PLAN
  -> derivado dinamicamente del Owner
```

Auditar antes de cambiar para conservar idempotencia y compatibilidad.

## 7. Caso de regresion principal - Chomes

No modificar el FCStd original del usuario durante la prueba.

Usar copia temporal/controlada del documento o recrear un fixture equivalente.

Caso obligatorio:

```text
Owner inicial X=19263, Y=11260
PLAN antiguo X=19004, Y=11260
```

Tras instalar la correccion y recomputar, la representacion debe quedar alineada
sin edicion manual del PLAN.

Luego probar:

1. mover Owner +500 mm en X -> PLAN sigue +500 mm;
2. mover Owner en Y -> PLAN sigue;
3. girar Owner 90 grados -> PLAN conserva orientacion de planta equivalente;
4. cambiar `AlturaRel` 300 -> 450 -> 3D cambia/relink, PLAN conserva XY/yaw;
5. cambiar `DocumentationPlaneZ` -> solo cambia Z documental;
6. cambiar `PlanSymbolScale` -> solo cambia escala documental;
7. Undo/Redo de movimiento y giro -> ambos regresan/avanzan juntos;
8. save/reopen -> dependencia persiste;
9. segundo recompute -> cero deriva y cero duplicados;
10. cero PLAN huerfanos.

Repetir con un apagador A1 orientado sobre muro para cubrir yaw y
`PuertaOrigen`.

## 8. Criterio de aceptacion

A1 solo puede volver a considerarse apto para default cuando se demuestre:

```text
Shape fisica separada              OK
PLAN documental separado           OK
una identidad semantica             OK
una sola autoridad espacial         OK
movimiento manual Owner -> PLAN     OK
rotacion manual Owner -> PLAN       OK
altura fisica no desplaza PLAN      OK
save/reopen                         OK
Undo/Redo                           OK
DXF desde PLAN                      OK
cero huerfanos                      OK
```

## 9. Restricciones

NO:

- activar A1 como default mientras esta tarea este abierta;
- migrar legacy;
- volver a combinar 2D y 3D;
- corregir manualmente los PLAN de Chomes como sustituto de la causa raiz;
- modificar el original `Chomes-Segundo Piso.FCStd` durante pruebas;
- crear un segundo objeto electromecanico;
- crear otro RoomResolver;
- redisenar el arbol;
- hacer commit/push sin autorizacion posterior.

## 10. Documentacion al cerrar

Actualizar en la misma ubicacion:

- `ElectricCR/TAREA_ACTUAL.md`;
- `ElectricCR/RESULTADO_CODEX.md`;
- `ElectricCR/ESTADO_PROYECTO.md`;
- `ElectricCR/docs/RESUMEN_DISPOSITIVO_ELECTROMECANICO.md`;
- `ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md` si cambia el
  mecanismo definitivo.

---

## Historial previo

# TAREA VIGENTE - ElectricCR / Aceptacion funcional GUI de A1

Fecha: 2026-09-03 12:54 America/Costa_Rica
FreeCAD objetivo: `1.1.3`
Estado: `CERRADA / ACEPTACION GUI APROBADA / APTO PARA DEFAULT DE OBJETOS NUEVOS`

## 0. Cierre de aceptacion funcional - 2026-09-03

Los dos comandos registrados reales se ejecutaron en FreeCAD `1.1.3` desde
`ElectricCRWorkbench`, usando sus dialogos completos sobre una copia temporal
controlada de Upala:

- `ElectricCR_Tomacorrientes_InstalarTomacorrientesEnParedesBIM`;
- `ElectricCR_Iluminaci_n_ColocarApagadoresEnPuertas`.

La prueba aprobo simultaneamente:

- legacy real por defecto en ambas herramientas;
- casilla A1 visible, desmarcada inicialmente y nuevamente desmarcada al
  reabrir cada comando;
- objetos GUI A1 con `PhysicalDocumentationA1`, `ElementUID`, `Host`, `Space`
  y, en el apagador, `PuertaOrigen`;
- `App::Link` hacia master fisico oculto, Shape exclusivamente 3D y PLAN
  `DocumentationOnly/Owner` independiente;
- Placement y alturas productivas de 300 mm para la toma y 1200 mm para el
  apagador, incluida la jamba de 150 mm;
- Undo/Redo, save/reopen y conteo estable despues de un segundo recompute;
- invariancia de Volume/BoundBox/Solids al cambiar la visibilidad de PLAN;
- cero PLAN huerfanos y UID unicos.

El muro BIM seleccionado contiene 19 tramos, por lo que el comando productivo
creo 31 tomas por ejecucion; esto es resultado de su algoritmo real, no de una
creacion auxiliar. Las ejecuciones legacy se deshicieron. La copia A1 contenia
31 tomas y un apagador, con 32 PLAN y sin huerfanos antes de save/reopen.

El DXF documental ya aprobado en el baseline A1 no se rediseño ni se reemplazo;
la GUI produjo exactamente el mismo contrato PLAN que alimenta ese exportador.
No aparecio una falla reproducible, por lo que no se modifico codigo.

La fuente original de Upala conservo SHA-256
`103FD471564E589F8E952954848A519D20AC58527C1ADCF39053CFCE3FF07F1E`,
tamano `1237860` bytes y fecha de modificacion. Los temporales se cerraron y
eliminaron. El informe JSON y seis capturas de dialogo quedaron en
`ElectricCR/Pruebas y regresiones` de Google Drive.

**Decision de cierre:** A1 queda **APTO PARA SER DEFAULT DE OBJETOS NUEVOS**.
Esta conclusion no cambia todavia el default productivo: legacy permanece como
valor predeterminado hasta una tarea y autorizacion separadas.

## 1. Objetivo

Validar en FreeCAD real que las dos herramientas productivas ya integradas con
`PhysicalDocumentationA1` funcionan correctamente desde el **comando completo
que usa el usuario**, no solamente desde helpers o scripts de smoke.

Herramientas:

- `ElectricCR_Tomacorrientes_InstalarTomacorrientesEnParedesBIM`;
- `ElectricCR_Iluminaci_n_ColocarApagadoresEnPuertas`.

Esta fase es principalmente de aceptacion. **No redisenar ni refactorizar si el
flujo ya funciona.** Modificar codigo solamente ante una falla reproducible de
esta prueba y conservar todas las caracteristicas que ya aprobaron.

## 2. Fuente de verdad y lectura previa

Usar Google Drive como fuente principal. Leer antes de ejecutar:

- `AGENTS.md`;
- Skills aplicables;
- `ElectricCR/TAREA_ACTUAL.md`;
- `ElectricCR/RESULTADO_CODEX.md`;
- `ElectricCR/ESTADO_PROYECTO.md`;
- `ElectricCR/docs/RESUMEN_DISPOSITIVO_ELECTROMECANICO.md`;
- `ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md`;
- `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md`;
- `CRBIMCore/BARRA_COMUN_ESPACIOS_RECINTOS.md`;
- codigo vigente de las dos macros y del nucleo A1.

No reconstruir archivos desde GitHub si Drive/local contiene una version mas
reciente.

## 3. Baseline ya aprobado - no repetir trabajo innecesario

Ya esta verificado por MCP:

- `RepresentationContract = PhysicalDocumentationA1`;
- `App::Link` como identidad;
- master fisico separado;
- `Shape` solo fisica 3D;
- PLAN `DocumentationOnly` con `Owner`;
- `ElementUID`;
- `Space`;
- `Host`;
- `PuertaOrigen` en apagador;
- Placement real de los algoritmos BIM;
- cambio de altura mediante relink;
- save/reopen;
- Undo/Redo;
- DXF documental;
- invariancia de Volume/BoundBox/Solids;
- default legacy intacto a nivel de implementacion.

No repetir estas pruebas exhaustivas salvo lo necesario para confirmar que el
**comando completo** llega correctamente a ese mismo contrato.

## 4. Regla de seguridad

No modificar ni guardar sobre el FCStd original de Upala.

Documento de referencia:

`1416 Levantamiento 250424 Compu D.FCStd`

Trabajar con copia temporal o documento temporal controlado. Verificar hash y
tamano del original antes/despues cuando se use una copia del archivo real.

Al finalizar:

- cerrar temporales;
- eliminar FCStd/DXF/FCBak temporales creados por la prueba;
- restaurar el documento activo previo;
- no dejar objetos de prueba en documentos del usuario.

## 5. Prueba A - tomacorrientes mediante comando real

Ejecutar el comando registrado real, no llamar directamente a `create_toma` ni
a `crear_toma_link` como sustituto de esta prueba.

### 5.1 Apertura de interfaz

Comprobar visualmente/MCP que el dialogo incluye la opcion A1 y que al abrirlo:

```text
A1 = desmarcado
```

No debe heredarse una seleccion A1 de una ejecucion anterior.

### 5.2 Comportamiento legacy por defecto

En un documento temporal adecuado, ejecutar una prueba minima con A1
**desmarcado**.

Confirmar que los nuevos dispositivos creados por esa ejecucion permanecen en
la ruta legacy esperada y que no aparecen parcialmente enriquecidos como A1.

No convertir objetos existentes.

Deshacer o descartar el documento temporal despues de registrar el resultado.

### 5.3 Comportamiento A1

Volver a ejecutar el comando completo con A1 marcado. Usar la geometria real de
Upala en copia temporal o un fixture minimo derivado de esa geometria cuando
sea necesario para mantener la prueba controlada.

No es obligatorio crear exactamente una toma si el comando completo, por su
naturaleza, genera varias. Usar el conjunto minimo razonable de parametros y
validar al menos una instancia representativa.

Confirmar en la instancia seleccionada:

```text
RepresentationContract = PhysicalDocumentationA1
ElementUID              = valido y unico
Host                    = muro BIM correcto
Space                   = Space canonico si RoomResolver = RESOLVED
LinkedObject            = master A1 fisico
PLAN.DocumentationOnly  = true
PLAN.Owner               = dispositivo A1
```

Confirmar que Placement, orientacion, altura, evitacion de puertas/ventanas y
cara interior siguen proviniendo del algoritmo productivo existente.

## 6. Prueba B - apagadores mediante comando real

Ejecutar el comando registrado real, no `_create_switch` directamente como
sustituto.

### 6.1 Apertura de interfaz

Comprobar que A1 aparece desmarcado al abrir el dialogo.

Despues de una ejecucion con A1 marcado, cerrar y volver a abrir el comando y
confirmar nuevamente:

```text
A1 = desmarcado
```

Esta comprobacion prueba que la opcion no se persiste accidentalmente.

### 6.2 Legacy por defecto

Ejecutar una prueba minima temporal con A1 desmarcado y confirmar que no se
migra ni se transforma silenciosamente un apagador legacy.

### 6.3 A1

Ejecutar con A1 marcado sobre una puerta BIM real/controlada. Validar al menos
un apagador:

```text
RepresentationContract = PhysicalDocumentationA1
ElementUID              = valido y unico
Host                    = Wall correcto
PuertaOrigen            = Door/Window BIM real
Space                   = Space canonico si RESOLVED
LinkedObject            = master A1 fisico
PLAN.DocumentationOnly  = true
PLAN.Owner               = apagador A1
```

Comprobar funcionalmente:

- lado de picaporte/jamba;
- `DistanciaJamba`;
- cara interior;
- orientacion sobre muro;
- altura;
- ausencia de colision con abertura inmediata segun las reglas existentes.

No corregir el caso historico `Apagador - Rectangle006` salvo que esta prueba
produzca una falla actual reproducible. El diagnostico historico queda cerrado:
`Rectangle006` era el auxiliar usado como `AreaRecinto`; la puerta era `Window`.

## 7. Contrato FA / CRBIMCore / ElectricCR a comprobar

Para cualquier instancia A1 creada por los comandos:

```text
FA/BIM Space -> Device.Space
FA/BIM Wall  -> Device.Host
FA/BIM Door  -> Switch.PuertaOrigen   # si aplica
Level        -> derivado desde Space
```

Reglas:

- no escribir propiedades ElectricCR en Space;
- no mover ni duplicar Space;
- Sketches, Areas o poligonos auxiliares pueden servir de calculo/fallback, pero
  no reemplazan silenciosamente una identidad BIM valida;
- `AMBIGUOUS` y `NOT_FOUND` no escriben una relacion inventada.

## 8. Arbol y documentacion

Inspeccionar el arbol despues de una creacion A1 y comprobar que:

- la identidad funcional sigue siendo el `App::Link`;
- el master permanece en `_lib/_lib_devices` y oculto;
- PLAN esta marcado como documental y no constituye una segunda identidad;
- no aparecen PLAN huerfanos;
- la ubicacion visual en grupos no se usa como autoridad de Space/Host;
- no se crean ramas duplicadas por repetir una sincronizacion.

No realizar en esta fase una reorganizacion general del arbol de Upala.

## 9. Verificacion fisica minima

No repetir toda la matriz A1 salvo que exista una discrepancia, pero para una
toma y un apagador creados por el comando completo registrar como minimo:

```text
Shape.Volume
Shape.BoundBox
len(Shape.Solids)
PLAN.Shape.Volume
len(PLAN.Shape.Solids)
```

Esperado:

- dispositivo fisico con geometria 3D real;
- PLAN con Volume 0 y Solids 0;
- sincronizar/mostrar/ocultar PLAN no cambia los valores fisicos.

## 10. Save/reopen y Undo/Redo

En la copia/documento temporal confirmar al menos una vez para cada familia:

- Undo de la creacion completa;
- Redo de la creacion;
- save/reopen conservando A1, UID, Host, Space, master y PLAN.

Si la operacion completa crea muchas instancias, validar una muestra
representativa y la consistencia de conteos antes/despues.

## 11. Decision sobre el default

**No cambiar el default en esta tarea.**

La salida de esta prueba debe terminar con una recomendacion explicita:

```text
A) APTO PARA HACER A1 DEFAULT EN OBJETOS NUEVOS
B) MANTENER A1 OPT-IN Y CORREGIR <fallas concretas>
```

Aunque el resultado sea A, no cambiar el default ni migrar legacy sin una
autorizacion posterior del usuario.

## 12. Regla de modificaciones

Si todas las pruebas pasan:

- NO modificar codigo funcional;
- actualizar solo documentacion de cierre.

Si aparece una falla:

1. diagnosticarla;
2. identificar la causa minima;
3. corregir sin reescribir la herramienta;
4. conservar algoritmos que ya funcionan;
5. repetir solo la prueba afectada y regresiones necesarias;
6. documentar exactamente que cambio y por que.

No crear otra API de dispositivo, otro RoomResolver, otro exportador DXF ni otro
sistema de arbol.

## 13. Documentacion de cierre

Actualizar en las mismas ubicaciones, sin copias paralelas:

- `ElectricCR/RESULTADO_CODEX.md`;
- `ElectricCR/ESTADO_PROYECTO.md`;
- `ElectricCR/TAREA_ACTUAL.md`;
- `ElectricCR/REVISION_MACROS.md`;
- `ElectricCR/docs/RESUMEN_DISPOSITIVO_ELECTROMECANICO.md`;
- `ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md` solo si una decision
  arquitectonica cambia;
- `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md` solo si la prueba descubre una
  relacion que obligue a ajustar el contrato.

Registrar capturas/diagnosticos MCP suficientes para distinguir:

- legacy default;
- A1 opt-in;
- estado de la casilla al reabrir;
- objeto A1 resultante y su PLAN.

## 14. Restricciones

NO:

- migrar dispositivos legacy;
- convertir en masa tomacorrientes/apagadores;
- cambiar A1 a default;
- reorganizar el arbol productivo de Upala;
- corregir `Rectangle006` por intuicion;
- modificar el original de Upala;
- hacer commit;
- hacer push.

## 15. Criterio de cierre

La tarea aprueba si los comandos completos demuestran simultaneamente:

1. legacy sigue siendo default real y no solo una constante en codigo;
2. la casilla A1 aparece y no persiste entre ejecuciones;
3. A1 creado por la GUI termina en `PhysicalDocumentationA1`;
4. toma conserva su algoritmo BIM productivo;
5. apagador conserva puerta/jamba/cara interior productivas;
6. Space/Host/PuertaOrigen siguen el contrato transversal;
7. PLAN sigue siendo documental y no altera Shape fisica;
8. save/reopen y Undo/Redo funcionan;
9. no se modifica el FCStd original;
10. no quedan temporales ni huerfanos.

Al cerrar, indicar si A1 queda **APTO PARA SER DEFAULT DE OBJETOS NUEVOS** o si
debe permanecer opt-in.

---

## Fase cerrada anterior - A1 opt-in en colocacion BIM real

# TAREA VIGENTE - ElectricCR / A1 opt-in en colocacion BIM real

Fecha: 2026-09-03 America/Costa_Rica
FreeCAD objetivo: `1.1.3`
Estado: `CERRADA / IMPLEMENTADA / VERIFICADA MCP`

## Cierre de integracion real 2026-09-03

Se integro el contrato ya verificado `PhysicalDocumentationA1` sin crear otra
arquitectura y sin cambiar el valor productivo predeterminado.

### Flujo real diagnosticado

`ElectricCR/commands/macros.py` escanea y registra las dos macros, y reconoce
que ambas administran su propia transaccion:

- `ElectricCR_Tomacorrientes_InstalarTomacorrientesEnParedesBIM` ejecuta
  `Tomacorrientes/InstalarTomacorrientesEnParedesBIM.FCMacro`;
- `ElectricCR_Iluminaci_n_ColocarApagadoresEnPuertas` ejecuta
  `Iluminación/ColocarApagadoresEnPuertas.FCMacro`.

La primera usa `wall_segments`, `opening_intervals`, `usable_runs`,
`positions_for_run`, `side_states` y `create_toma`. La segunda usa
`_collect_all_doors`, `_door_geometry`, `_world_line_segments`,
`_merge_wall_runs`, `_find_wall_run`, `_opening_intervals`,
`_find_free_scalar`, `_choose_side_mode`, `_build_plans` y `_create_switch`.
Ambas terminan en `electriccr.features.objeto_toma_uno.crear_toma_link`.

### Cambio implementado

- Las dos interfaces ofrecen una casilla A1 desmarcada en cada ejecucion.
- La opcion no se guarda en preferencias; `LegacyCompound` sigue siendo el
  default productivo.
- A1 pasa `separate_documentation=True`, exige el contrato resultante y falla
  en vez de degradarse silenciosamente a legacy.
- El mismo algoritmo real asigna Placement y metadatos; despues
  `ensure_device_semantics` agrega `ElementUID`, `Space` y `Host`, y
  `sync_plan_representation` materializa PLAN.
- `ensure_device_semantics(..., manage_transaction=False)` permite completar
  la semantica dentro de la transaccion ya abierta por cada macro.
- Una ejecucion A1 no actualiza ni convierte un apagador legacy encontrado;
  lo cuenta como `legacy_preservado`. Un A1 existente si puede actualizarse.

### Caso `Apagador - Rectangle006`

No se corrigio por intuicion. La evidencia de Drive y el artefacto documental
del 2026-09-03 muestran que:

- la identidad era `Link_Apagador_Sketch_Centros_Puertas_001`;
- `PuertaOrigen`/`ElementoOrigen` apuntaban a `Window`, una puerta BIM;
- `MuroReferencia` apuntaba a `Wall`;
- `AreaRecinto` apuntaba al objeto `Rectangle` cuyo Label era `Rectangle006`;
- por eso el Label generado fue `Apagador - Rectangle006`: el texto nombra el
  recinto auxiliar elegido, no identifica la puerta;
- su Placement historico fue `[2995.344424, 8632.545499, 0]`, mientras el
  algoritmo vigente produjo el punto de jamba controlado
  `[3145.344424, 8632.545499, 0]`.

La diferencia de Placement queda diagnosticada, no corregida: el estado
historico ya no esta en el FCStd vigente y no hay evidencia suficiente para
atribuirla a una causa unica.

### Upala y verificacion controlada

Drive conserva dos inventarios de las 09:10-09:20 con 48 tomacorrientes y 11
apagadores legacy. Al ejecutar esta fase, el FCStd guardado y la sesion abierta
ya contenian 187 objetos y cero dispositivos ElectricCR; por tanto no se afirma
falsamente que la prueba pudo comparar los 59 objetos dentro del mismo archivo.
Se uso la evidencia de Drive como baseline historico y una copia temporal del
FCStd vigente como caso geometrico real.

`tests/freecad_upala_real_placement_a1_smoke.py`, ejecutado por MCP en FreeCAD
1.1.3, creo exactamente una toma y un apagador A1 mediante los helpers reales.
Ambos aprobaron contrato A1, Shape fisica, PLAN `DocumentationOnly/Owner`,
ElementUID, Host=`Wall`, Space resuelto por RoomResolver, Placement, altura con
relink, save/reopen, Undo/Redo, DXF y la invariancia fisica durante la
sincronizacion PLAN. El apagador conservo `PuertaOrigen=Window`.

Resultado fisico inicial en la ejecucion MCP:

| objeto | Volume | Solids | BoundBox |
|---|---:|---:|---|
| toma A1 | `84518.072443` | `18` | `[1821.337475,9201.25,264.76]..[1936.337475,9258.749108,334.76]` |
| apagador A1 | `82232.284217` | `2` | `[3095.90278,8597.620499,1141.453]..[3159.237877,8667.470499,1258.547]` |

Los PLAN tuvieron Volume `0`, Solids `0` y Z `0`. El DXF midio `11104`
bytes. La prueba verifico hash/tamano invariables de la fuente, cerro la copia,
restauro el documento activo anterior y elimino FCStd, DXF y respaldos
temporales. No hubo migracion masiva, commit ni push.

---

## Fase previa - implementacion del contrato A1

## Diagnostico de la implementacion real

La documentacion anterior describia una unica identidad, pero el codigo real de
`electriccr/features/objeto_toma_uno.py` todavia ejecutaba este comportamiento:

- cargaba `symbol2D` y `model3D`;
- transformaba ambos;
- los incorporaba juntos con `Part.makeCompound(shapes)` a `obj.Shape`;
- `ModoVisual` decidia que geometria formaba parte de esa `Shape`.

Por tanto, al inicio de esta tarea **A1 no estaba implementado**. La presencia de
una propuesta en documentos no era evidencia de separacion fisica/documental.

## Contrato A1 implementado

La opcion seleccionada es una representacion PLAN auxiliar controlada
(alternativa C del estudio A/B/C), porque el ViewProvider sirve para apariencia
pero no ofrece por si solo una fuente semantica estable para DXF.

- La identidad colocada sigue siendo el `App::Link` ElectricCR.
- Su master A1 es inmutable, reutilizable y distinto de los masters legacy.
- `RepresentationContract = PhysicalDocumentationA1` se exige tanto en el Link
  como en el master.
- `obj.Shape` contiene exclusivamente el `model3D` fisico.
- PLAN es un `Part::Feature` auxiliar con `DocumentationOnly = true`,
  `RepresentationRole = PLAN` y `Owner` hacia la identidad.
- PLAN no tiene `ElementUID` y no es otra identidad electromecanica.
- La instancia contiene `ElementUID`, `Space` y `Host`.
- `DocumentationRepresentationName` permite resolver PLAN desde la identidad sin
  crear un ciclo de dependencias de FreeCAD.
- La visibilidad 3D/PLAN, escala PLAN y cota documental son independientes.
- El exportador documental recibe solamente los objetos PLAN.
- La eliminacion controlada retira identidad y documentacion; el auditor de
  huerfanos es idempotente.

Compatibilidad: los consumidores no migrados siguen creando
`LegacyCompound` por defecto. A1 solo se activa con
`separate_documentation=True`; no se modifico ningun objeto productivo.

## Prueba obligatoria ejecutada por MCP

Script: `tests/freecad_electromechanical_outlet_switch_a1_smoke.py`.

En un documento temporal se crearon exactamente dos identidades:

1. un `Tomacorriente_120V` a 300 mm, luego 450 mm;
2. un `Apagador_Simple` a 1200 mm, luego 1350 mm.

Ambos utilizaron exclusivamente `PhysicalDocumentationA1`. Resultado MCP en
FreeCAD `1.1.3`:

| objeto | Shape fisica final | PLAN final |
|---|---|---|
| tomacorriente | Volume `84518.072443`, Solids `18`, BoundBox Z `414.76..484.76` | Volume `0`, Solids `0`, BoundBox Z `0..0` |
| apagador | Volume `82232.284217`, Solids `2`, BoundBox Z `1291.453..1408.547` | Volume `0`, Solids `0`, BoundBox Z `0..0` |

Tambien aprobaron:

- UIDs unicos `...0001` y `...0002`;
- `Space` nativo resuelto y `Host` muro explicito;
- `Placement` de cada instancia sin cambios durante relink de altura;
- `App::Link` y master A1 despues de save/reopen;
- Undo/Redo de creacion conjunta, visibilidad y altura;
- sincronizacion PLAN idempotente;
- DXF documental de exactamente dos PLAN, `18405` bytes;
- cero representaciones huerfanas;
- cierre del documento y eliminacion de FCStd/DXF temporales.

MCP mostro antes y despues de la prueba solamente el documento productivo que
ya estaba abierto. No fue activado, guardado, migrado ni modificado. En
particular, no se tocaron Upala, sus 48 tomacorrientes ni sus 11 apagadores.

## Limites y siguiente paso

- No existe autorizacion para migrar instancias legacy.
- No se hizo commit ni push.
- La adopcion productiva de A1 requiere una tarea separada y una estrategia de
  migracion explicita; esta prueba no la autoriza.
- El error de inicializacion preexistente de `FacilArquitecturaWB/Init.py`
  observado en `freecadcmd` es ajeno a ElectricCR y no invalida la prueba MCP.

---

## Fase anterior archivada - luminaria semantica + arbol idempotente

Fecha: 2026-09-01 America/Costa_Rica
Proyecto: `Programacion en FreeCAD`
Componente principal: `ElectricCR`
Relacionados: `CRBIMCore 0.1.0`, `FacilArquitecturaWB`
FreeCAD objetivo: `1.1.3`
Estado: `CERRADA / IMPLEMENTADA / VERIFICADA MCP`

## Punto de partida obligatorio

La fase 2A de RoomResolver esta cerrada y verificada. La fase 2B de diseno en Drive tambien esta cerrada.

Leer antes de modificar:

- `AGENTS.md`;
- skill `$freecad-cr-workbench-architecture`;
- `ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md`;
- `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md`;
- `ElectricCR/ESTADO_PROYECTO.md`;
- codigo vigente `ElectricCR/electriccr/features/objeto_toma_uno.py`;
- `registry_electric.json` vigente.

Regla ya aprobada:

> Las relaciones semanticas son la verdad; el arbol del modelo es una vista reproducible de esas relaciones.

Y otra regla de esta tarea:

> No crear un segundo objeto electromecanico generico. Evolucionar/reutilizar el nucleo existente y probarlo de forma reversible.

## Objetivo

Construir y verificar en FreeCAD 1.1.3 un prototipo minimo con **una sola luminaria temporal** que demuestre que la instancia `App::Link` actual puede conservar su funcionamiento 2D/3D y masters, mientras recibe identidad y relacion espacial persistente suficientes para proyectar una rama electrica idempotente.

En paralelo, crear solo en el documento temporal un comparador `Arch Equipment` equivalente para medir que aporta BIM/IFC. No sustituir la luminaria Link ni decidir una migracion masiva en esta tarea.

## Alcance A - luminaria App::Link piloto

Usar el flujo real de `objeto_toma_uno.py` y el registro vigente para crear o reproducir una luminaria `App::Link` con master oculto.

La instancia piloto debe conservar sin cambios conceptuales:

- `LinkedObject` / master reutilizable;
- `Placement`;
- simbolo 2D;
- modelo 3D;
- `AlturaRel` y mecanismo actual de relink cuando aplique;
- `Tipo`, `Categoria`, `KeyRegistro`, `ModoVisual`, orientacion y metadatos legacy que ya funcionen.

Agregar solamente el contrato minimo necesario para el prototipo, preferentemente de forma reusable y no acoplada a GUI:

- `ElementUID`: identificador persistente y unico de la instancia;
- `Space`: `App::PropertyLink` al `Arch/BIM Space` canonico.

No agregar por ahora `Level` ni `Panel` a la luminaria:

- `Level` se deriva de `Space`;
- `Panel` se derivara de `Circuit` cuando exista un contrato de Circuit consolidado.

Para circuito/control, reutilizar la autoridad vigente y no inventar aun un nuevo tipo productivo:

- `CircuitoID` / propiedad equivalente existente para identificar el circuito del piloto;
- `ControlID` / `ApagadorID` y los `PropertyLinkList` existentes del Control cuando corresponda.

Si para la prueba hace falta un objeto Circuit o Control temporal, crearlo solo como fixture/probe del documento de prueba, claramente marcado como no productivo. No consolidar su clase como arquitectura definitiva.

## Alcance B - asignacion espacial

Usar `CRBIMCore.RoomResolver` para resolver el Space del punto/Placement de la luminaria piloto.

Comportamiento:

- `RESOLVED` -> asignar `Space` solo en la luminaria temporal;
- `AMBIGUOUS` -> no escribir enlace;
- `NOT_FOUND` -> no escribir enlace;
- no escribir propiedades ElectricCR sobre el Space;
- no duplicar ni mover el Space.

Probar persistencia de `ElementUID` y `Space` despues de guardar/cerrar/reabrir el documento temporal.

## Alcance C - arbol idempotente minimo

Implementar o prototipar, reutilizando primero organizadores existentes, una proyeccion minima para iluminacion:

```text
electrico
  Iluminacion
    Circuitos
      IL-TEST
        Recintos
          <RoomName>
            Apagadores
              S1
                Luminarias
                  <luminaria piloto>
```

Autoridades para este prototipo:

1. `Space` explicito de la luminaria para el recinto;
2. `CircuitoID` o contrato legacy estable vigente para el circuito;
3. relacion existente de Control (`PropertyLinkList`) y/o `ControlID` seguro para el apagador;
4. el padre visual actual solo como fallback diagnosticable, nunca como verdad.

Reglas:

- el Space real permanece en Building/Level;
- `Recintos/<RoomName>` es un contenedor visual, no un segundo Space;
- masters y `_lib` permanecen fuera de la rama funcional;
- repetir la reconstruccion debe reutilizar los mismos contenedores y no crear duplicados;
- una segunda ejecucion sin cambios debe reportar cero cambios materiales;
- la reconstruccion no debe modificar `ElementUID`, `Space`, `LinkedObject`, master ni `Placement`.

La herramienta/prototipo de arbol debe ofrecer `dry_run=True` por defecto si se materializa como helper reusable.

## Alcance D - comparador Arch Equipment

Solo en documento temporal, crear un `Arch Equipment` equivalente a la luminaria piloto, reutilizando cuando sea razonable la misma geometria/master o una copia controlada de la representacion.

Comparar y documentar:

- identidad y propiedades BIM nativas;
- comportamiento de `Base`/Placement;
- posibilidad de conservar una representacion 2D y 3D coherente;
- `IfcType` aplicable a luminaria en FreeCAD 1.1.3;
- guardar/reabrir;
- Undo/Redo;
- impacto en rendimiento/duplicacion geometrica a nivel cualitativo para este prototipo;
- viabilidad de salida IFC/2D sin asumir que deba sustituir `App::Link`.

No migrar la luminaria piloto hacia Equipment. El resultado debe ser comparativo.

## Salida documental 2D

Verificar que la luminaria piloto conserva una representacion 2D identificable y exportable. Para este prototipo basta comprobar una ruta documental basica existente (por ejemplo DXF/TechDraw/Shape 2D segun lo que ya use ElectricCR) sin redisenar el sistema de planos.

Si la ruta actual no exporta correctamente un `App::Link`, documentar el limite y no improvisar una solucion grande dentro de esta tarea.

## Arquitectura de codigo

Preferencia:

`core/helper semantico independiente de GUI -> adaptador FreeCAD -> comando/probe pequeno`

No introducir Qt/FreeCADGui en logica reusable.

Antes de crear modulos nuevos, buscar helpers existentes de:

- identificadores persistentes;
- propiedades ElectricCR;
- organizacion del arbol;
- reconocimiento de dispositivos;
- controles/circuitos;
- transacciones/dry-run.

## Pruebas obligatorias

Como minimo:

1. suite actual de `CRBIMCore.RoomResolver` sigue pasando;
2. pruebas existentes relevantes de `objeto_toma_uno.py` siguen pasando;
3. crear luminaria `App::Link` piloto desde registro/master vigente;
4. `ElementUID` creado una vez y estable en recompute/save/reopen;
5. `Space` resuelto y persistente;
6. `AMBIGUOUS` no escribe Space;
7. `NOT_FOUND` no escribe Space;
8. `LinkedObject` del piloto no cambia por agregar semantica;
9. Placement no cambia;
10. 2D y 3D mantienen comportamiento actual;
11. cambio de `AlturaRel` mantiene el mecanismo actual sin elevar el simbolo 2D;
12. reconstruccion de arbol crea la rama minima esperada;
13. segunda reconstruccion produce cero duplicados y cero cambios materiales;
14. masters siguen en `_lib` y no se mezclan con la rama funcional;
15. Space permanece bajo su jerarquia arquitectonica y sin propiedades ElectricCR nuevas;
16. guardar/cerrar/reabrir conserva UID, Space, LinkedObject y arbol;
17. Undo/Redo aprobado en operaciones de escritura del prototipo;
18. comparador `Arch Equipment` creado y evaluado en documento temporal;
19. verificacion documental 2D basica;
20. no se abre/guarda/modifica ningun FCStd original del usuario.

## Modelos y seguridad

- Usar documento temporal/demo creado por la prueba.
- Si se inspecciona La Cruz u otro modelo real, hacerlo lectura solamente y no guardar.
- No ejecutar reorganizacion sobre proyectos reales.
- No cambiar ni borrar masters productivos.
- No migrar tomacorrientes ni apagadores.
- No cambiar `ColocarLuminarias_Link` salvo que el prototipo requiera un adaptador minimo y reversible; preferir no tocarlo.
- No hacer migracion masiva de propiedades.

## Criterio de decision al cierre

El resultado debe responder con evidencia a estas preguntas:

1. ¿Puede el `App::Link` actual ser la identidad operativa enriquecida de una luminaria sin perder ninguna funcion actual?
2. ¿Son suficientes `ElementUID + Space + relaciones legacy/control existentes` para iniciar la reconstruccion del arbol?
3. ¿Que aporta realmente `Arch Equipment` que justifique integrarlo, envolverlo o reservarlo para BIM/IFC?
4. ¿La rama electrica puede reconstruirse idempotentemente sin usar el padre visual como autoridad?
5. ¿Que minimo cambio se recomienda para la siguiente fase y cual debe evitarse?

No declarar una arquitectura definitiva si la evidencia no la sostiene.

## Cierre real 2026-09-01

La fase se implemento y verifico exclusivamente en documentos temporales con
FreeCAD 1.1.3. No se abrio ni modifico ningun FCStd del usuario.

Resultado:

- la luminaria `App::Link` vigente admite `ElementUID` y `Space` sin cambiar
  `LinkedObject`, `Placement`, tipo, registro, modo visual ni orientacion;
- RoomResolver asigna unicamente un Space nativo en estado `RESOLVED`;
  `AMBIGUOUS` y `NOT_FOUND` dejan el enlace vacio;
- el cambio de `AlturaRel` conserva UID/Space/Placement y reenlaza al master
  inmutable esperado, manteniendo el simbolo 2D en Z local 0;
- el arbol se proyecta con claves estables y `dry_run=True` por defecto;
- como `App::DocumentObjectGroup` tiene pertenencia visual exclusiva, la rama
  contiene una referencia indice `App::Link` a la luminaria fisica. Este patron
  reutiliza el organizador existente y evita sacar la instancia de su grupo
  manual;
- la segunda proyeccion produjo cero cambios y cero objetos adicionales;
- los masters permanecen en `_lib/_lib_devices` y ahora conservan visibilidad
  oculta tambien despues de recompute/reapertura;
- guardar/cerrar/reabrir, Undo/Redo y exportacion DXF del Link aprobaron;
- el comparador `Arch Equipment` aprobo como `Light Fixture`, con propiedades
  BIM/IFC nativas, pero requirio `Base`/copia geometrica y no reemplazo al Link.

Las pruebas y decisiones completas quedaron en `RESULTADO_CODEX.md`. La tarea
se detiene aqui; no se iniciaron tomacorrientes, apagadores ni migraciones.

### Revalidacion 2026-09-02

Se releyo la tarea desde la fuente DEV sincronizada y se comprobo que seguia
cerrada. Sin modificar codigo, se repitieron el nucleo semantico, las 11 pruebas
de RoomResolver y el smoke integral en FreeCAD 1.1.3. Todos aprobaron; el
documento y los archivos temporales fueron eliminados por la prueba. No se
abrieron modelos originales ni se inicio una fase posterior.

## Documentacion de cierre

Al terminar:

- actualizar este `TAREA_ACTUAL.md` con resultado real;
- actualizar `ElectricCR/RESULTADO_CODEX.md`;
- actualizar `ElectricCR/ESTADO_PROYECTO.md`;
- actualizar `ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md` con la decision basada en pruebas;
- actualizar `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md` solo si el prototipo confirma cambios de contrato;
- registrar memoria reusable si se confirma la arquitectura;
- no hacer commit/push salvo instruccion posterior.

## Instruccion final a Codex

Implementar y probar **solo este prototipo de una luminaria en documento temporal**. Diagnosticar y reutilizar lo existente antes de crear codigo. No migrar dispositivos reales, no reorganizar modelos originales, no iniciar tomacorrientes/apagadores ni una fase posterior. Detenerse al documentar la comparacion y la recomendacion.


## Avance GPT 2026-09-05 21:50 America/Costa_Rica - rollback seguro del feedback PLAN y correccion de separacion en arbol

> Trabajo directo de GPT en Drive; no atribuir a Codex.

Prueba real de Upala: el overlay persistente basado en `Draft ghostTracker` dejo imagenes fantasma al mover/borrar y, tras reabrir, produjo multiples `Access violation` y `SystemError: unknown opcode`.

Correccion implementada en Drive:
- `electriccr/ui/plan_selection.py` v0.4.0: rollback a redireccion segura PLAN -> Owner; sin `ghostTracker`, sin overlay persistente y sin preseleccion forzada.
- `electriccr/features/plan_live_sync.py` v0.4.0: mantiene recompute PLAN y visibilidad, pero elimina todo refresco de overlay.
- `electriccr/features/objeto_toma_uno.py` rev O: PLAN no puede pertenecer a grupos de usuario; `sync_plan_representation()` detecta y elimina pertenencia accidental a `Apagadores BIM` u otros `DocumentObjectGroup`.
- Se conserva `PLAN.ViewObject.ShowInTree=False`, `PLAN.Owner=PropertyLinkHidden`, expresion PLAN<-Owner y A1 opt-in.

Dato de prueba aclarado por Marco: `Link_Apagador_Rectangle009` y `Link_Apagador_Rectangle010` fueron borrados intencionalmente durante las pruebas; no se consideran perdida accidental.

Pendiente de validacion real tras reinicio completo de FreeCAD: Delete/Undo/Redo, mover, guardar/reabrir, ausencia de Access violation, ausencia de ghosts y PLAN fuera del grupo electrico.

---

## Tarea vigente - 2026-09-10 14:01 -0600 America/Costa_Rica - ElectricCR A1: diagnosticar Access violation en Undo de Demo / PLAN Lifecycle

> Tarea preparada por GPT para Codex a partir de una prueba real de Marco en FreeCAD 1.1.3. No asumir la causa antes de reproducirla.

### Contexto confirmado

Workbench: `ElectricCR`  
Herramienta: `Demo ElectricCR A1` / contrato A1 Owner + PLAN  
FreeCAD real: **1.1.3**  
Documento temporal de prueba: `ElectricCR Demo A1 - Canonica`  
No usar ni modificar modelos reales del usuario.

La demo completa ya crea correctamente:

- 2 Spaces BIM nativos;
- 5 muros BIM;
- 7 Owners A1 (`App::Link`);
- 7 representaciones PLAN;
- auditoria inicial `PASS`, `errors=0`, `warnings=0`.

Se confirmo tambien que la seleccion de PLAN redirige al Owner y que, tras mover Owner, todas las comprobaciones A1 excepto la posicion canonica siguen aprobando. El PLAN acompana al Owner.

### Fallo real reproducido por Marco

Al pulsar `Ctrl+Z` en la demo se observo que FreeCAD intento deshacer la transaccion completa de creacion:

```text
[ElectricCR][PLAN Lifecycle] queued owner=ECR_Demo_outlet_office_01 plans=ECR_DocPlan_...
[ElectricCR][PLAN Lifecycle] removed orphan PLAN after owner deletion ...
... mismo patron para los 7 Owners/PLAN ...
<Exception> Access violation
<App> Transactions.cpp(203): Exception on undo 'ElectricCR: crear demo A1':Access violation
```

Despues del fallo, la auditoria volvio a `PASS`, lo que indica que el Undo fallo/retrocedio sin dejar inconsistencia persistente visible. No considerar esto una prueba aprobada de Undo.

Hipotesis de trabajo de GPT, **a verificar y no asumir**: durante Undo/Redo/rollback el observador `plan_lifecycle.py` puede estar reaccionando a borrados que pertenecen a la propia transaccion y eliminando PLAN manualmente mientras FreeCAD intenta revertir los mismos objetos, provocando doble gestion de ciclo de vida. Revisar si `Document.isPerformingTransaction()` u otra API/estado equivalente de FreeCAD 1.1.3 permite distinguir operaciones normales de callbacks causados por Undo/Redo/rollback.

Tambien hay que aclarar por que el movimiento previo no dejo una transaccion independiente encima de `ElectricCR: crear demo A1`, de modo que el primer `Ctrl+Z` apunto a la creacion completa de la demo.

### Objetivo

Diagnosticar y corregir, con el minimo cambio compatible, el `Access violation` de Undo/Redo relacionado con Owner/PLAN **sin romper el contrato A1 aprobado**.

### Archivos a inspeccionar primero

Respetar `AGENTS.md` y el orden de lectura del proyecto. Despues revisar como minimo:

- `ElectricCR/electriccr/features/plan_lifecycle.py`
- `ElectricCR/electriccr/features/plan_live_sync.py`
- `ElectricCR/ui/plan_selection.py`
- `ElectricCR/electriccr/features/objeto_toma_uno.py`
- `ElectricCR/electriccr/demo/electric_demo_freecad.py`
- `ElectricCR/electriccr/demo/electric_demo_audit.py`
- `ElectricCR/tests/freecad_electric_demo_smoke.py`
- pruebas A1/lifecycle existentes relacionadas con Delete/Undo/Redo.

Buscar tambien evidencia historica del fallo/soluciones anteriores en `RESULTADO_CODEX.md`, `ESTADO_PROYECTO.md`, `DECISIONES_TECNICAS.md`, `RECURRENT_NOTES.md` y Git.

Nota: `AGENTS.md` aun menciona FreeCAD 1.1.1, pero el proyecto y esta tarea usan **FreeCAD 1.1.3**. Documentar la discrepancia; no modificar `AGENTS.md` salvo que sea estrictamente necesario y se justifique.

### Diagnostico obligatorio antes de modificar

1. Reproducir el caso en documento temporal generado por la demo, con logging suficiente para distinguir:
   - borrado normal de Owner;
   - Undo de un borrado normal;
   - Redo;
   - Undo de la transaccion completa `ElectricCR: crear demo A1`;
   - rollback/abort si aplica.
2. Confirmar que callback/observer de `PLAN Lifecycle` se ejecuta durante Undo y en que estado esta el `Document`.
3. Investigar API y comportamiento real de FreeCAD 1.1.3 para detectar Undo/Redo/rollback, incluyendo `Document.isPerformingTransaction()` o alternativa oficial si corresponde.
4. No implementar una guarda basada solo en nombre de transaccion ni en timers si existe un estado nativo fiable.
5. Verificar si el problema proviene realmente de doble borrado, de referencias invalidas a `DocumentObject`, de procesamiento diferido/queued, o de otra causa.
6. Revisar por que el movimiento usado en la prueba no genero una entrada Undo propia. Determinar si fue una caracteristica de `Draft Move`, del modo de seleccion/redireccion, o de como se realizo la prueba. No mezclar esta causa con lifecycle si son problemas distintos.

### Restricciones

- No cambiar el contrato A1: Owner sigue siendo `App::Link`, `Owner.Placement` autoridad espacial unica, PLAN 2D documental separado, `Owner` 1:1, schema 2, `SnapPoints=[Vector(0,0,0)]`.
- No reintroducir `ghostTracker`, overlays persistentes ni feedback grafico experimental.
- No tocar IFC.
- No tocar Upala, Chomes ni otros modelos reales.
- No cambiar `registry_electric.json`.
- No cambiar masters ni recursos 2D/3D salvo que el diagnostico demuestre dependencia directa (improbable).
- No cambiar `plan_selection.py` ni `plan_live_sync.py` salvo evidencia reproducible de que participan en la causa.
- Preferir una guarda pequena y explicita en lifecycle frente a reescribir todo el observador.
- Mantener mensajes utiles de consola y no ocultar excepciones que puedan revelar un fallo real.
- No declarar solucion por pasar pruebas Python; debe pasar FreeCAD real 1.1.3.

### Pruebas de aceptacion en FreeCAD real 1.1.3

Crear siempre documento temporal nuevo. Como minimo:

1. `Demo ElectricCR A1` crea 2 Spaces / 5 walls / 7 Owners / 7 PLAN y auditoria inicial `PASS`.
2. Mover **un solo Owner** dentro de una transaccion de usuario verificable; PLAN sigue XY/rotacion y no cambia UID/master/Space/Host.
3. `Ctrl+Z` de ese movimiento revierte Owner y PLAN sin `Access violation`.
4. `Ctrl+Y` lo rehace sin `Access violation`.
5. Borrar un Owner de forma normal: lifecycle elimina exactamente su PLAN, no otros.
6. Undo del borrado restaura Owner + PLAN 1:1 coherentes.
7. Redo del borrado vuelve a eliminar el par sin huerfanos ni doble borrado.
8. Undo de la transaccion completa `ElectricCR: crear demo A1` no produce `Access violation`; FreeCAD debe gestionar la transaccion sin que lifecycle interfiera de forma peligrosa.
9. Redo de la creacion, si FreeCAD lo soporta de forma estable para este caso, restaura una demo coherente; si no, documentar el limite exacto sin forzarlo.
10. Guardar/cerrar/reabrir una demo canonica conserva 7 Owners / 7 PLAN y auditoria `PASS`.
11. Cambiar temporalmente de WB (BIM/Draft/Part) y repetir un movimiento + Undo para verificar que lifecycle/selection/live sync siguen activos sin regresion.
12. Sin `Access violation`, `unknown opcode`, ghosts ni PLAN huerfanos.

### Auditoria de la demo

No convertir el movimiento intencional en falso fallo estructural. Mantener clara la diferencia entre:

- auditoria **canonica**: puede exigir el Placement inicial exacto;
- comprobacion de **integridad A1** durante pruebas de movimiento: debe exigir Owner/PLAN, UID, master, Space, Host, schema, snaps y seguimiento de Placement, sin exigir coordenadas originales mientras el movimiento sea intencional.

No es obligatorio cambiar ahora el auditor si el smoke test puede verificar integridad directamente; si se cambia, hacerlo de forma explicita y sin relajar la auditoria canonica por defecto.

### Entregables de Codex

Al finalizar:

1. dejar la correccion minima en la unica fuente vigente de los archivos afectados;
2. ejecutar pruebas focales y la prueba real en FreeCAD 1.1.3;
3. guardar evidencia de consola/log de la reproduccion previa y de la prueba posterior;
4. actualizar `RESULTADO_CODEX.md` con diagnostico, causa demostrada, archivos modificados y pruebas;
5. actualizar `ESTADO_PROYECTO.md`;
6. actualizar este `TAREA_ACTUAL.md` con el resultado real;
7. actualizar `DECISIONES_TECNICAS.md` o `RECURRENT_NOTES.md` solo si la correccion establece una regla reusable;
8. no modificar `HISTORIAL_CAMBIOS.md` hasta que la solucion sea probada, revisada y aceptada;
9. no hacer commit/push GitHub en esta tarea salvo instruccion posterior de Marco/GPT.

### Criterio de cierre

No cerrar la tarea hasta responder con evidencia:

- causa exacta del `Access violation`;
- por que lifecycle reaccionaba durante Undo o, si la hipotesis era falsa, que componente lo causaba realmente;
- cambio minimo aplicado;
- resultado de Delete/Undo/Redo de un par Owner/PLAN;
- resultado de Undo de la transaccion completa de la demo;
- estado del movimiento y su transaccion propia;
- ausencia de regresiones A1.

**Detenerse despues de documentar y probar esta correccion. No iniciar IFC ni otras mejoras.**
