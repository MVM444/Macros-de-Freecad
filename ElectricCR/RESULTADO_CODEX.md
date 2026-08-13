# ElectricCR - Resultado de Codex

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
