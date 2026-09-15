# Recuperar Tasks - validacion GUI real

Fecha: 2026-09-13, America/Costa_Rica. Pruebas: 16:41:10-16:45:30; limpieza de visibilidad: 16:46. Equipo: DESKTOP-5586S7P, PID 22684. FreeCAD 1.1.3, revision 20260725 / 145529fe741292ff0b3977a01195bf0247425794; Python 3.11.14, PySide6/Qt 6.8.3.

**Mecanismo de refresco y diagnostico probado. Panel negro no reproducido; su resolucion NO esta demostrada. Sin cambios de codigo funcional.**

## Contexto real y alcance

La conciliacion inicial del 12/9 de TAREA_ACTUAL identifica Recuperar Tasks como el avance mas reciente, implementado y pendiente de GUI. La entrada inferior que priorizaba Undo A1 esta explicitamente contextualizada como historica. La instruccion actual de continuar exclusivamente lo pendiente se aplico a estas pruebas; no se mezclo el diagnostico independiente de Undo Demo A1 / PLAN Lifecycle.

Se releyeron AGENTS de ElectricCR y padre, tarea vigente, estado/resultado, flujo y referencias del proyecto; skills de arquitectura y memoria con contrato y disponibilidad MCP. Se inspeccionaron los archivos locales y la auditoria previa de paneles, sin repetir investigacion amplia ni buscar una implementacion nueva. Las dos skills estan disponibles en este equipo; su ausencia del 12/9 no se reprodujo.

`electriccr/demo/electric_demo_freecad.py:100` ya utiliza `App::FeaturePython`. SHA256 confirmado antes/despues: `3f199c02a666417e05312f3845e7f31420bdc0d34d0aa3fe0dc75297d106681d`. No se ejecuto la demo ni se rehizo esa correccion.

La fuente cargada del controlador Programacion coincide con la carpeta local `Macros/Programacion` (nombre fisico con tilde). Macro v0.1.0 y toolbar v1.1.0, autoria GPT previa. Rutas exactas, fechas, tamanos y hashes: [preflight.json](preflight.json). No se consulto ni modifico Git, IFC o Upala.

## Disponibilidad y preparacion

MCP inicialmente devolvio WinError 10061. FreeCAD estaba cerrado: se inicio el ejecutable 1.1 y su MCP existente arranco automaticamente. Dos respuestas de conexion rechazada en total; tercer intento conectado, sin cambios de configuracion. La sesion inicial no tenia documentos ni TaskDialog. Se comprobo en vivo la existencia de `Control.showModelView`, `showTaskView` y `activeDialog`.

Compilacion de los bytes locales de macro, toolbar, helper comun y auditor: PASS. No se modificaron esos archivos ni el SVG. Una sola barra Programacion, nueve botones visibles/habilitados, un solo Recuperar Tasks. Las acciones reales se dispararon con `QAction.trigger()`, que llama al comando registrado; tres ejecuciones adicionales se hicieron por la macro original para recuperar su resultado estructurado. Total: 28 ejecuciones, 25 por el boton.

## Matriz de pruebas

| Prueba | Resultado observado |
|---|---|
| A: dos documentos sin TaskDialog | PASS. TasksRecovery_A (caja) y TasksRecovery_B (cilindro); contenido, documento activo, seleccion y camaras conservados por cada recuperacion. |
| Tasks visible sin TaskDialog | Visibilidad y geometria conservadas; la deteccion de pestana informa `unknown` con docks separados. |
| B: tarea nativa | PASS. Sketcher::SketchObject en edicion con un segmento y restriccion de 20 mm; dialogo, edicion, geometria y restricciones conservados, tambien por el boton. |
| C: diez pulsaciones con Sketch activo | PASS. Cinco docks y 897 QWidget antes/despues en cada ciclo y despues de regresar al event loop; sin duplicados ni acumulacion observada. |
| D: seis cambios A/B | PASS. Recuperacion antes/despues de cada cambio. Cinco docks y 1113 widgets constantes en esta fase. Geometria central por recuperacion: [741,99,947,1046] sin cambios. |
| E: auditoria existente antes/despues | PASS en escenarios medidos. Durante alternancias: cinco docks, cero duplicados y 13 widgets relevantes en ambos snapshots. |
| F: fallo negro real | NO REPRODUCIDO. Capturas del escritorio muestran vista y tarea reconocibles; no se simulo una averia ni se atribuye a la macro una recuperacion del negro. |
| G: limpieza | PASS. Ambos documentos temporales cerrados sin guardar; cero documentos y cero TaskDialog al terminar. Se restauro la visibilidad inicial de Tasks mediante su accion nativa. FreeCAD permanece abierto. |

Los 28 registros tienen todos los controles aprobados. La auditoria final vuelve a cinco docks, tres visibles, dos ocultos y nueve widgets relevantes, sin duplicados; area central [741,99,1819,1046]. Esto acredita esas mediciones y la visibilidad restaurada, no una comparacion binaria de todo el layout.

Se conservaron los nueve botones y su estado. No se ejecuto la funcionalidad de los otros ocho comandos porque no forma parte de esta tarea. No se ensayo recarga de un controlador de una version anterior.

## Consola y limites

[console.txt](console.txt) contiene 28 BEFORE, 28 AFTER y 28 RESULT; 13 retornos condicionales a `showTaskView()`. Cero WARNING/ERROR del recuperador; ninguna excepcion durante sus pruebas.

Existe un error previo y separado, a las 16:39:25: `FacilArquitecturaWB/InitGui.py` informa `attempted relative import with no known parent package`. No se diagnostico ni corrigio en esta tarea. Por ello no se afirma que toda la consola de arranque este libre de errores.

`_tab_state()` busca QTabWidget; esta sesion usa docks Model y Tasks separados y devuelve `unknown`. La visibilidad se mantuvo en la prueba sin dialogo y `activeDialog()` sostuvo el retorno cuando habia una tarea. Es una limitacion diagnostica confirmada, sin regresion funcional demostrada en estos casos. No se justifica cambiar codigo por esa observacion aislada.

Las capturas `00`-`04` obtenidas con `QMainWindow.grab()` contienen artefactos del area OpenGL y no sirven para afirmar un fallo de la vista real. La revision visual se hizo con las capturas nativas del escritorio `05`, `06` y `07`: caja reconocible y croquis/tarea conservados antes/despues.

## Evidencia y continuidad

- [summary.json](summary.json): entorno, resumen, conteos, cierre y hashes sin cambios.
- [runs.json](runs.json): 28 comparaciones PRE/POST con controles y resultados de la macro cuando disponibles.
- [preflight.json](preflight.json): archivos reales, version, barra y compilacion.
- [console.txt](console.txt): Report View conservado, incluyendo error de arranque separado.
- [probe_helpers.py](probe_helpers.py): funciones de medicion del ensayo; necesitan el contexto de la prueba, no son un comando ni una macro de produccion.
- [06_desktop_sketch_before.png](06_desktop_sketch_before.png) y [07_desktop_sketch_after.png](07_desktop_sketch_after.png): revision visual de la tarea nativa.
- `host_diagnostic.json`: diagnostico actual; `host_diagnostic_previous.json`: registro anterior conservado antes de actualizar la memoria del equipo.

Para repetir: iniciar FreeCAD 1.1.3 con Programacion, crear dos documentos temporales con primitivas, auditar, pulsar Recuperar Tasks al alternar documentos, abrir Sketch nativo con geometria y restriccion, pulsar diez veces y auditar de nuevo. Mantener el dialogo abierto durante los ciclos. Cerrar solamente los documentos de prueba al terminar. No usar el smoke global que cierra la aplicacion.

Clasificacion: SOPORTE / CANDIDATA / COMPROBADA-PARCIAL. Complementa la auditoria read-only existente; no la reemplaza. Estado: PROBADA TECNICAMENTE / VERIFICADO_MCP / VERIFICADO_VISUAL del mecanismo. Pendiente: medir y validar manualmente durante una reproduccion real del panel negro. Undo Demo A1 / PLAN Lifecycle permanece independiente y sin nueva prueba. No se actualiza HISTORIAL_CAMBIOS ni se promueve a RELEASE. MAPA_WORKBENCH y REVISION_MACROS no requieren cambios por esta validacion sin funcionalidad nueva.
