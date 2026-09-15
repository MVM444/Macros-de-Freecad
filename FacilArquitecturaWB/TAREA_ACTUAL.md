# TAREA ACTUAL - 2026-09-15 15:20 America/Costa_Rica - Demo Escalera minima / buque dinamico de cielorraso

Workbench: **Facil Arquitectura**  
Herramienta: **FA Demo edificio -> Demo Escalera minima**  
FreeCAD objetivo: **1.1.3**  
Workbench: **0.14.12 / build 2026.09.15.6**  
Comando Demo: **0.10.6**  
Demo core: **0.9.4**  
Cielorrasos: **0.7.3**  
Estado: `CORREGIDO EN DRIVE / PY_COMPILE Y CONTRATO PURO OK / SMOKE REAL PENDIENTE`

## Hallazgo del smoke build .5

Mover `FA Escalera entre losas` ya mueve el buque estructural de la losa, pero la abertura del cielo suspendido permanece en la posicion inicial. La causa es que el cielo 600x600 se generaba con las zonas de exclusion ya recortadas en coordenadas mundo; despues del primer calculo no existia ninguna dependencia geometrica con `Stairs.Placement`.

## Correccion exclusiva de Demo Escalera minima

- `ceiling_exclusion_follows_master=True` se activa solo en el spec minimo.
- El cielo modular completo queda fijo en coordenadas del edificio.
- La abertura pasa a un `Part::Cut` paramétrico: su Base es el cielo completo y su Tool es `FA_CeilingDynamicOpening`, oculto y construido en coordenadas locales de la escalera.
- `FA_CeilingDynamicOpening.Placement` usa expresion hacia `Stairs.Placement`; mover o girar la escalera debe mover solo el buque del cielo.
- Para evitar el ciclo `Stairs -> CeilingCut -> Cutter -> Stairs`, el master conserva los cielos recortados mediante `FA_CeilingObjectNamesJSON`, no PropertyLinkList, solo en esta Demo.
- El diagnostico 0.2.2 reconoce tambien ese contrato por nombres.
- Casa demo 2 pisos y el comando normal conservan el recorte estatico historico; no reciben el modo dinamico.

## Verificacion fuera de FreeCAD

- `py_compile` de `ceiling_utils.py`, `cmd_demo_building.py`, `demo_building_core.py`, `model_diagnostic_core.py` y `constants.py`: OK.
- Spec minimo JSON: `placement_authority=master`, `opening_follows_master=True`, `ceiling_exclusion_follows_master=True`: OK.
- Contrato estatico: el modo dinamico crea `Part::Cut`, el cutter sigue `Stairs.Placement` y el camino estatico sigue siendo el predeterminado: OK.

## Siguiente smoke

Hot restart -> confirmar build `.6` -> generar solo `Demo Escalera minima`. Mover en XY y girar `FA Escalera entre losas`; despues de recompute deben acompañar la escalera tanto el buque de la losa como el buque del cielo suspendido, mientras la reticula/paneles generales del cielo permanecen fijos.

---

# TAREA ACTUAL - 2026-09-15 15:05 America/Costa_Rica - Demo Escalera minima / Placement autoritativo en la escalera

Workbench: **Facil Arquitectura**  
Herramienta: **FA Demo edificio -> Demo Escalera minima**  
FreeCAD objetivo: **1.1.3**  
Workbench: **0.14.12 / build 2026.09.15.5**  
Comando Demo: **0.10.5**  
Demo core: **0.9.3**  
Adaptador escalera: **0.6.4**  
Estado: `CORREGIDO EN DRIVE / PY_COMPILE Y CONTRATO PURO OK / SMOKE DE MOVIMIENTO PENDIENTE`

## Hallazgo del smoke build .4

La Demo completa y su diagnostico mostraron las bases como Draft Line/Wire y el buque nativo en `Subtractions`, pero al mover manualmente `FA Escalera entre losas` la escalera regresaba al punto original durante el recompute. La causa fue la expresion `Stairs.Placement = Wire.Placement`: el Wire oculto seguia siendo la autoridad de posicion.

## Correccion exclusiva de Demo Escalera minima

- `Stairs.Placement` pasa a ser editable y autoritativo; se inicializa una sola vez con el Placement del Wire de referencia y no queda esclavizado por expresion.
- El Wire conserva puntos locales y queda solo como referencia inicial; las bases nativas siguen siendo Draft Line + Draft Wire + Draft Line en coordenadas locales.
- El buque estructural se construye en el marco local de la escalera y su `Placement` depende de `Stairs.Placement`.
- Para evitar el ciclo `Stairs -> Level/Slab -> Subtractions -> Cutter -> Stairs`, solo en esta Demo los enlaces contextuales de losas/Levels y el enlace inverso al cutter se conservan por `Name` estable; el modo normal y Casa demo 2 pisos mantienen PropertyLinks sin cambios.
- El PLAN 2D principal usa `Stairs.Placement` como transformacion.
- `model_diagnostic_core.py` 0.2.1 reconoce el contrato por nombres de la Demo para seguir comprobando Levels y Subtractions.

## Verificacion fuera de FreeCAD

- `py_compile` de adaptador, Demo, core, diagnostico y constantes: OK.
- Spec minimo JSON: `placement_authority=master`, `context_links_mode=names`, `opening_follows_master=True`, `opening_follows_source=False`: OK.
- Casa demo 2 pisos no recibe estas opciones y conserva la ruta historica.

## Siguiente smoke

Hot restart -> confirmar build `.5` -> generar solo `Demo Escalera minima`. Mover `FA Escalera entre losas` en XY y luego girarla. Tras recompute, la escalera no debe regresar y el buque de la losa debe acompañar la misma transformacion. Revisar tambien PLAN 2D y barandas; estas ultimas requieren confirmacion runtime porque FreeCAD 1.1.3 las crea como objetos nativos separados.

---

# TAREA ACTUAL - 2026-09-15 14:12 America/Costa_Rica - Demo Escalera minima / contrato de cielorraso

Workbench: **Facil Arquitectura**  
Herramienta: **FA Demo edificio -> Demo Escalera minima**  
FreeCAD objetivo: **1.1.3**  
Workbench: **0.14.12 / build 2026.09.15.3**  
Comando Demo: **0.10.3**  
Demo core: **0.9.1**  
Estado: `CORREGIDO EN DRIVE / PY_COMPILE Y CONTRATO PURO OK / NUEVO SMOKE FREECAD PENDIENTE`

## Diagnostico del smoke build .2

La correccion anterior del Space auxiliar funciono: FreeCAD creo el Sketch cerrado y sincronizo 1 Space BIM. El siguiente fallo fue `KeyError: 'ceiling'` en `_ceiling_options(self.spec)`. La causa es contractual: `build_minimal_stair_demo_spec()` eliminaba la seccion `ceiling` del spec de Nivel 00 aunque el materializador ejecuta `ground._step_ceiling()`.

## Correccion

- `demo_building_core.py` 0.9.1 conserva en **Nivel 00** la seccion canonica `ceiling` heredada de la Casa 2 pisos: modulo 600 mm, elevacion 2700 mm, panel 15 mm, junta 5 mm y tolerancia 50 mm.
- La Demo minima activa `apply_ceiling_exclusion=True`, por lo que el cielorraso debe usar las dos zonas `l_union_v2` ya calculadas por la escalera.
- `create_opening_liner=False` se conserva: no se crea tapichel en este banco de prueba todavia.
- No se agregan muros, puertas, ventanas, recintos de la casa, techo ni cielorraso en Nivel 01.
- `cmd_demo_building.py` sube a 0.10.3 solo para identificar claramente esta revision de la Demo.
- Build general: `2026.09.15.3`.

## Verificacion fuera de FreeCAD

- `py_compile demo_building_core.py cmd_demo_building.py constants.py`: OK.
- Contrato puro: `apply_ceiling_exclusion=True`, `create_opening_liner=False`, `Nivel 00.spec.ceiling.module_mm=600`, Nivel 01 sin seccion de cielo, JSON serializable: OK.

## Siguiente smoke

Hot restart -> confirmar build `.3` -> generar `Demo Escalera minima`. Debe superar la etapa de Space y entrar al generador de cielorraso; revisar visualmente abertura L, paneles, barandas nativas y diagnostico final. Casa demo 2 pisos permanece fuera de alcance.

---

# TAREA ACTUAL - 2026-09-15 13:35 America/Costa_Rica - Demo Escalera minima / cielorraso y barandas

Workbench: **Facil Arquitectura**  
Herramienta: **FA Demo edificio -> Demo Escalera minima**  
FreeCAD objetivo: **1.1.3**  
Workbench: **0.14.12 / build 2026.09.15.2**  
Comando Demo: **0.10.2**  
Estado: `CORRECCION EN DRIVE / PY_COMPILE OK / NUEVO SMOKE FREECAD PENDIENTE`

## Contexto

El smoke real de build `.1` confirmo que la Demo crea correctamente dos Levels, ambas losas, la escalera nativa y el hueco `l_union_v2` de la losa superior. Tambien calculo las dos zonas de exclusion del cielorraso. La ejecucion se detuvo al preparar el Space auxiliar del cielorraso con `Recinto sin poligono suficiente`.

## Causa y correccion

`_prepare_minimal_stair_ceiling_context()` construia manualmente un `room_record` sin `polygon_mm`, pero `space_utils._face_from_record()` exige ese poligono. Se elimina ese registro paralelo: `create_bim_spaces()` recibe ahora `room_records=None` y reconstruye su registro JSON-compatible directamente desde el Sketch documental cerrado mediante su ruta canonica. Se conservan las etiquetas descriptivas del Space/Base solo como presentacion.

La Demo sigue usando el generador normal de cielorrasos 600x600 con exclusion de escalera y hace visibles las barandas nativas al final. No se crea tapichel y no se modifica Casa demo 2 pisos.

## Verificacion

- `py_compile cmd_demo_building.py constants.py`: OK.
- Contrato estatico: Demo `0.10.2`, `room_records=None`, sin registro manual `STAIR_DEMO_CEILING_AREA`: OK.
- Pendiente: hot restart, confirmar build `2026.09.15.2`, generar `Demo Escalera minima` y revisar cielorraso, abertura, barandas y diagnostico.

---

# TAREA ACTUAL - 2026-09-14 20:00 America/Costa_Rica - Buque L continuo y tapichel sin invadir paso

Workbench: **Facil Arquitectura**  
Herramienta: **FA Escalera entre losas / FA Demo edificio 2 pisos**  
FreeCAD objetivo: **1.1.3**  
Build: **0.14.11 / 2026.09.14.6**  
Demo: **0.9.3**  
Nucleo escalera: **0.3.0**  
Adaptador escalera: **0.6.0**

## Cambio

- `plan_stair_clearance()` deja de describir el giro mediante cuatro rectangulos independientes cuando el descanso requiere holgura. Ahora genera dos brazos solapados cuya union es una **L continua** (`l_union_v2`).
- Cada plano publica `liner_open_ends` para entrada y salida de la escalera.
- El PLAN 2D usa el contorno exterior fusionado de la L, no los rectangulos constructivos internos.
- `create_stair_opening_liner()` omite los bordes transversales de entrada/salida y resta finalmente el prisma del paso libre, por lo que el tapichel no puede invadir la envolvente de circulacion.
- La Demo declara `clearance_geometry_revision=l_union_v2` y `opening_liner_mode=side_walls_open_ends`.

## Verificacion fuera de FreeCAD

- `py_compile`: OK.
- Pruebas puras `test_stair_core.py + test_demo_building_core.py`: **11/11 OK**.
- FreeCAD real: **pendiente smoke build .6**.

## Siguiente prueba

Hot restart -> Casa fija 2 pisos 6x8 m. Confirmar visualmente: buque L completo, ausencia de muesca en el giro, tapicheles laterales sin cerrar entrada/salida, diagnostico sin errores.

---

# TAREA ACTUAL - 2026-09-14 17:11 America/Costa_Rica - Correccion smoke tapichel / DAG escalera

Workbench: **Facil Arquitectura**  
Herramienta: **FA Escalera entre losas / FA Demo edificio 2 pisos**  
FreeCAD objetivo: **1.1.3**  
Build: **0.14.11 / 2026.09.14.5**  
Demo: **0.9.2**  
Adaptador escalera: **0.5.1**  
Cielorraso: **0.7.1**  
Estado: `CORREGIDO EN DRIVE / PRUEBAS FOCALES OK / NUEVO SMOKE FREECAD PENDIENTE`

## Diagnostico del smoke real build .4

El registro real confirma que FreeCAD cargo correctamente `v0.14.11 | build 2026.09.14.4` y ejecuto `FA Demo edificio 2 pisos` con Demo 0.9.1. La ejecucion llego hasta la creacion de escalera, sustraccion de losa y exclusion de cielorraso, pero se interrumpio al crear el tapichel:

`create_stair_opening_liner() got an unexpected keyword argument 'ceiling_plane_id'`

Causa directa: el orquestador Demo llamaba la funcion con `ceiling_plane_id` y `target_container`, mientras la API canonica del adaptador usa `plane_id` y `level`.

El mismo registro mostro dos problemas adicionales que deben corregirse antes de repetir el smoke:

- `The graph must be a DAG`: la escalera master se insertaba dentro de `Nivel 00` y al mismo tiempo conservaba `FA_LowerLevel -> Nivel 00`, formando el ciclo de dependencia `Nivel 00 -> escalera -> Nivel 00`.
- `No se pudo recortar un panel por zona de exclusion: Null shape`: un panel podia quedar completamente eliminado por una primera zona y el bucle intentaba volver a cortar la Shape nula con zonas posteriores.

Los `ReferenceError` de `ArchWindow.py` aparecen despues de la excepcion principal durante la interrupcion/rollback y se consideran efecto secundario hasta repetir el smoke sin la excepcion.

## Correccion build .5

1. Demo 0.9.2 usa los nombres canonicos `plane_id="lower_ceiling"` y `level=ground.level`.
2. El adaptador 0.5.1 conserva alias de compatibilidad para `ceiling_plane_id` y `target_container` durante ventanas de sincronizacion/hot-reload, pero los nuevos callers usan solo la API canonica.
3. La escalera inter-nivel deja de ser hija directa del Level inferior. Se coloca en el `Building` comun, conserva `FA_LowerLevel` y `FA_UpperLevel`, y mantiene bases/PLAN en el Level inferior. Si no existe un Building padre unico, queda sin contenedor antes que crear un ciclo DAG.
4. Cielorraso 0.7.1 detiene el recorte cuando el panel ya se volvio `Null shape`, evitando operaciones OCCT invalidas y warnings falsos.
5. Build general incrementado a `2026.09.14.5`.

## Verificacion fuera de FreeCAD

- Compilacion sintactica de los 7 archivos modificados: OK.
- Pruebas focales nuevas/afectadas: **5/5 OK**.
- Se agregaron regresiones estaticas para nombres de argumentos del tapichel y contencion del master fuera del Level inferior.
- Se agrego regresion funcional para detener el recorte de cielorraso al quedar una Shape nula.

## Nuevo smoke requerido

1. Hot restart y confirmar `v0.14.11 | build 2026.09.14.5`.
2. Generar `Casa fija 2 pisos 6 x 8 m`.
3. No debe aparecer el `TypeError` de `ceiling_plane_id`.
4. No deben aparecer mensajes `The graph must be a DAG`.
5. No deben aparecer warnings `No se pudo recortar un panel ... Null shape`.
6. Debe crearse el `Tapichel perimetral - buque escalera`.
7. La Demo debe completar las etapas restantes y abrir el diagnostico automatico.
8. Revisar visualmente el cierre del plenum y luego guardar/reabrir.

---

# TAREA ACTUAL - 2026-09-14 16:41 America/Costa_Rica - Tapichel perimetral del buque de escalera

Workbench: **Facil Arquitectura**  
Herramienta: **FA Escalera entre losas / FA Demo edificio 2 pisos**  
FreeCAD objetivo: **1.1.3**  
Build: **0.14.11 / 2026.09.14.4**  
Demo: **0.9.1**  
Adaptador escalera: **0.5.0**  
Estado: `IMPLEMENTADO EN DRIVE / PRUEBAS FOCALES OK / SMOKE FREECAD PENDIENTE`

## Objetivo y cambio

La prueba real del buque y de la exclusion del cielorraso mostro el plenum visible alrededor de la abertura. Se agrega un **tapichel perimetral** derivado de la misma zona de exclusion del cielorraso. El tapichel baja desde la cara inferior de la losa superior hasta el plano inferior del cielorraso, con espesor nominal Demo de **100 mm**, creciendo hacia afuera del hueco para no reducir la envolvente de altura libre.

- `stair_freecad_adapter.create_stair_opening_liner()` crea/reutiliza `FA_StairOpeningLiner` como `Part::Feature` y lo enlaza al master mediante `FA_OpeningLiner`.
- El objeto queda en `Nivel 00`, con trazabilidad de losa, cotas, espesor, esquema y zonas JSON.
- La Demo lo crea despues del cielorraso, dentro de la misma transaccion multinivel.
- Se conserva la sustraccion nativa Arch de la losa y la exclusion previa de paneles; el tapichel no participa en la sustraccion y no crea una segunda escalera.
- La orientacion de la escalera y la simplificacion del buque (posible giro de 90 grados) quedan como ajuste separado despues de validar primero este remate.

## Validacion fuera de FreeCAD

- `py_compile`: OK.
- `test_demo_building_core.py`: **7/7 OK**.
- contratos focales Demo: **2/2 OK**.
- contrato estatico del tapichel: **5/5 OK**.

## Smoke requerido

Generar de nuevo `Casa fija 2 pisos 6 x 8 m` en build `.4`. Desde abajo, no debe verse el plenum por el canto del buque: debe aparecer un cierre vertical continuo entre cielorraso y losa. Revisar tambien desde Nivel 01 que el tapichel no invada el paso calculado. Despues se ajustara la implantacion/giro de la escalera y la forma final del buque.

---

# TAREA ACTUAL - 2026-09-14 15:40 America/Costa_Rica - FA Escalera entre losas / buque real de losa + cielorraso

Workbench: **Facil Arquitectura**  
Herramienta: **FA Escalera entre losas**  
Banco de prueba: **FA Demo edificio - Casa fija 2 pisos 6x8 m**  
FreeCAD objetivo: **1.1.3**  
Workbench: **0.14.11 / build 2026.09.14.3**  
Demo: **0.9.0**  
Adaptador escalera: **0.4.0**  
Cielorraso: **0.7.0**  
Estado: `IMPLEMENTADO EN DRIVE / 22 PRUEBAS FOCALES OK / SMOKE FREECAD REAL PENDIENTE`

## Objetivo

Convertir la envolvente ya validada de altura libre en un buque fisico real para subir al Nivel 01 y retirar el cielorraso que invade el paso, conservando la losa Arch original, la escalera nativa y la documentacion PLAN 2D.

## Investigacion y decision de arquitectura

FreeCAD BIM/Arch ya resuelve huecos parametricos mediante la propiedad nativa `Subtractions` de los Arch Components. `Arch.removeComponents(..., host)` registra el objeto cortador como sustraccion y `ArchComponent.processSubShapes()` aplica el boolean al recomputar. Se reutiliza esa capacidad en la losa creada por `Arch.makeStructure`; no se reemplaza `Structure001` por un Part::Cut ni por una losa FA paralela.

Para cielorraso no existe un host Arch equivalente en el flujo actual: FA genera un `Part::Feature` compuesto por paneles. La solucion implementada agrega `exclusion_zones_world_mm` al generador modular para que los paneles nazcan recortados por las zonas de altura libre. No se ocultan paneles a posteriori.

## Cambios implementados

- `stair_freecad_adapter.create_native_slab_opening()` crea/reutiliza un `Part::Feature` cortador y lo incorpora a `upper_slab.Subtractions` mediante `Arch.removeComponents`, con fallback directo a `Subtractions` si la API no estuviera expuesta.
- El cortador atraviesa el espesor completo de la losa con margen vertical, queda oculto y conserva trazabilidad por nombres/JSON sin enlaces de retorno que formen ciclos DAG.
- `ceiling_utils` acepta zonas de exclusion XY globales; las transforma al sistema local de cada recinto y recorta las caras de panel antes de extruirlas.
- La Demo de dos pisos difiere la creacion del cielorraso de Nivel 00 hasta que existe la losa superior y se ha calculado la escalera. Luego genera el cielo directamente con la exclusion.
- Los previews dejan de ser solo preview cuando ambos cambios se aplican: se conservan como `PLAN - Hueco losa escalera` y `PLAN - Exclusion cielorraso escalera`, ocultos por defecto pero exportables/documentales.
- El diagnostico agrega comprobaciones `STAIR_SLAB_OPENING_APPLIED` y `STAIR_CEILING_EXCLUSION_APPLIED`; confirma que el cortador esta realmente en `Subtractions` de la losa y que existe cielorraso recortado + PLAN.
- Se eliminaron enlaces de retorno desde cutter/ceiling/PLAN hacia master cuando el master/host ya los enlaza, para evitar ciclos de dependencia.
- La especificacion Demo activa `cut_upper_slab=True` y `apply_ceiling_exclusion=True`.

## Verificacion fuera de FreeCAD

- `py_compile`: aprobado para los modulos modificados.
- Pruebas focales: **22/22 OK**.
- Se preserva el recorrido canonico `[(5200,4200),(5200,1900),(2700,1900)]`, 2100 mm de altura libre y los margenes ya validados en la build anterior.

## Smoke requerido en FreeCAD 1.1.3

1. Cargar build `2026.09.14.3`.
2. Generar `Casa fija 2 pisos 6 x 8 m`.
3. Desde la vista interior usada por el usuario, debe desaparecer la losa sobre el tramo final y quedar un buque continuo hasta Nivel 01.
4. El cielorraso de Nivel 00 debe desaparecer donde la envolvente de 2100 mm lo requiere, comenzando antes que el hueco estructural.
5. `Structure001.Subtractions` debe contener un unico `Buque escalera - sustraccion losa`.
6. El diagnostico automatico debe quedar sin ERROR/WARN y agregar los OK de losa y cielorraso.
7. Probar Undo/Redo de la transaccion de la Demo y guardar/reabrir antes de declarar cerrada la fase.

No se habilita aun el corte automatico en el comando interactivo para modelos arbitrarios: primero debe pasar este smoke controlado de la Demo.

---

# TAREA ACTUAL - 2026-09-14 11:50 America/Costa_Rica - FA Centros de ventanas / seleccion por Layer Draft

Workbench: **Facil Arquitectura**  
Herramienta: **FA Centros de ventanas**  
FreeCAD objetivo: **1.1.3**  
Workbench: **0.14.11 / build 2026.09.14.2**  
`centerline_utils.py`: **0.24.0**  
Estado: `CORRECCION IMPLEMENTADA EN DRIVE / 47/47 PRUEBAS UNITARIAS OK / SMOKE LAYER REAL PENDIENTE`

## Retroalimentacion real que abre esta revision

La build `2026.09.14.1` fue probada por el usuario en Guadalupe. **Seleccionando cada Shape/App::Link individualmente funciona**, pero seleccionando la capa completa `Ventanas` el resultado no es correcto. Esta observacion sustituye el supuesto anterior de que el problema restante era solamente el clustering entre Links.

## Diagnostico confirmado

Se inspecciono en modo read-only el `Document.xml` real de `L1 D.R.S.C.130613.FCStd`. `Layer002` es un Draft Layer real (`App::FeaturePython`, proxy `draftobjects.layer.Layer`) cuyo `Group` contiene exactamente 7 miembros: seis `App::Link` (`Link__U5_`, `Link__U6_`, `Link__U11_`, `Link__U12_`, `Link__U5_001`, `Link__U26_`) y el `Part::Feature` `Ventanas`.

La ruta de `profile_axis` 0.23.0 ya extraia correctamente **6 ejes** antes del postprocesado. El error ocurria despues: `create_centerline_sketch_from_objects()` enviaba esos ejes al mismo `_prepare_centerline_groups()` usado por redes de muros. Esa fase consolidaba ejes de ventanas colineales cercanos como si fueran tramos de una pared continua. En la regresion Guadalupe:

- eje `1512 mm` + eje `14239 mm` -> falso eje de **15901 mm**;
- eje `2434 mm` + eje `297 mm` -> falso eje de **2881 mm**;
- resultado final: **4 lineas** en vez de 6.

Esto explica exactamente por que ejecutar Shape por Shape funcionaba y ejecutar todo el Layer no.

## Correccion implementada

1. Los Draft Layers seleccionados por `FA Centros de ventanas` se expanden explicitamente desde su propiedad `Group`, manteniendo cada miembro como raiz de seleccion independiente.
2. Los `App::Link` siguen aislados por instancia como en 0.23.0.
3. Los `Part::Feature` que son miembros de un Layer de ventanas se analizan tambien de forma independiente; una seleccion manual directa de varios Shapes conserva el clustering compartido historico.
4. Para `extraction_strategy=profile_axis`, los ejes ya resueltos se consideran **identidades discretas de ventanas**. Se omite la consolidacion de red de muros (`_prepare_centerline_groups`) y solo se eliminan duplicados geometricos exactos.
5. No se modifica `door_swing`, la extraccion general de muros ni las herramientas BIM posteriores.
6. Se agregan trazas especificas: expansion del Draft Layer, Shapes de Layer aislados y mensaje de que la consolidacion de red fue omitida.

## Regresion automatizada

`tests/test_centerline_network.py`: **47/47 OK**.

Cobertura nueva:

- Draft Layer realista `App::FeaturePython + Proxy.Type=Layer`: dos ventanas plain cercanas permanecen como dos ejes; la misma seleccion manual directa conserva el comportamiento compartido anterior.
- Layer Guadalupe completo: seis Links complejos de 46 bordes + `Part::Feature Ventanas` -> **6 ejes finales**, con longitudes `297, 1512, 2434, 5334, 5334, 14239 mm`.
- Se conserva la regresion de Link ambiguo y los casos simples existentes.

`py_compile`: aprobado. El FCStd original solo fue inspeccionado como ZIP/XML; no fue modificado.

## Smoke requerido en FreeCAD 1.1.3

1. Cargar la build **2026.09.14.2**.
2. Abrir el documento/copia de Guadalupe.
3. Seleccionar **solo el Layer `Ventanas`** y ejecutar `FA Centros de ventanas`.
4. Esperado: **6 lineas**, no 4; no deben aparecer los falsos ejes de 15901 mm ni 2881 mm.
5. Deben conservarse los dos ejes verticales de 5334 mm de las instancias rotadas -90 grados.
6. Repetir un Shape individual para confirmar que el caso que ya funcionaba permanece correcto.

GitHub `main` sigue deliberadamente sin actualizar porque esta varias versiones atras respecto de la fuente vigente de Drive; no hacer un push parcial.

---

# TAREA ACTUAL - 2026-09-09 20:20 America/Costa_Rica - Escalera Demo reubicada + preview de holgura losa/cielorraso

Workbench: **Facil Arquitectura**  
FreeCAD objetivo: **1.1.3**  
Build: **0.14.11 / 2026.09.09.7**  
Demo: **0.8.2**  
FA Escalera entre losas: core **0.2.0** / adaptador **0.3.0**  
Estado: `IMPLEMENTADO EN DRIVE / PRUEBAS PURAS Y CONTRATOS OK / SMOKE FREECAD PENDIENTE`

## Objetivo

Corregir la ubicacion poco natural de la escalera de la casa canonica de dos pisos y definir, antes de cortar geometria, una envolvente de altura libre que produzca dos previews documentales independientes: hueco de losa superior y exclusion del cielorraso inferior.

## Cambios

- Recorrido Demo v2: `P0=(5200,4200) -> P1=(5200,1900) -> P2=(2700,1900) mm`. Mantiene longitudes utiles 2300/2500 mm, 17 contrahuellas y huellas 257.14/250 mm sin warnings del planner.
- La nueva posicion aleja la escalera de la fachada frontal y mantiene el preview del hueco estructural dentro del distribuidor de Nivel 01, sin atravesar el tabique de dormitorios en Y=3500.
- `fa_stair_core.plan_stair_clearance()` calcula zonas JSON-compatible por plano de obstaculo usando una envolvente lineal de narices de peldanos. Parametros Demo: altura libre 2100 mm, margen lateral 50 mm y margen de aproximacion 100 mm.
- Planos calculados: cara inferior de losa superior y cara inferior del cielorraso de Nivel 00. El cielo comienza a requerir exclusion antes que la losa, como corresponde por estar a menor cota.
- `stair_freecad_adapter.create_clearance_previews()` crea dos PLAN 2D visibles, etiquetados `PREVIEW - Hueco losa escalera` y `PREVIEW - Exclusion cielorraso escalera`, enlazados a la escalera y alojados en sus Levels respectivos.
- **No se corta todavia** la losa y **no se eliminan todavia** paneles de cielorraso. Esta build es deliberadamente de previsualizacion/diagnostico para validar la geometria real antes de aplicar booleans o exclusiones.
- El diagnostico automatico de Demo 0.8.1 se conserva.

## Prueba requerida

1. Confirmar build `2026.09.09.7` y Demo `0.8.2`.
2. Generar `Casa fija 2 pisos 6 x 8 m`.
3. Revisar visualmente la nueva posicion de la escalera.
4. Deben verse dos contornos PLAN de preview, uno cerca de la cara inferior de la losa superior y otro en el plano del cielorraso inferior.
5. El preview de losa no debe invadir el muro horizontal de Nivel 01 en Y=3500.
6. El preview de cielorraso debe extenderse un poco mas hacia el arranque que el preview de losa.
7. Adjuntar/copy-pastear la ruta del diagnostico automatico.
8. Si la ubicacion y previews son correctos, siguiente fase: aplicar `Subtractions` nativas a la losa y zonas de exclusion al generador de cielorraso.

---

# TAREA ACTUAL - 2026-09-09 16:25 America/Costa_Rica - Diagnostico automatico de FA Demo + acciones de reporte

Workbench: **Facil Arquitectura**  
FreeCAD objetivo: **1.1.3**  
Build: **0.14.11 / 2026.09.09.6**  
Demo: **0.8.1**  
FA Informe diagnostico: **0.2.0**  
Estado: `IMPLEMENTADO EN DRIVE / PRUEBAS FOCALES OK / SMOKE FREECAD PENDIENTE`

## Cambios vigentes

- `FA Demo edificio` genera automaticamente un diagnostico **del documento completo** al finalizar la generacion inmediata.
- La Demo pasa `selection=[]` al motor para ignorar cualquier seleccion residual del Tree View.
- La Demo guiada genera el mismo informe al completar el ultimo paso; si se reconstruye hacia un paso anterior, queda habilitada una nueva captura final.
- `FA Informe diagnostico` manual ya no reduce silenciosamente el alcance: si existe seleccion pregunta `Documento completo / Solo seleccion / Cancelar`, con documento completo como opcion predeterminada.
- El resultado usa un dialogo reutilizable con `Copiar ruta del MD`, `Abrir carpeta` y `Cerrar`. Copiar la ruta ocurre solo al pulsar el boton y no pisa el portapapeles automaticamente.
- La macro historica `CapturarArbolYPrompt.FCMacro` conserva su comportamiento anterior de copiar el prompt mediante `copy_prompt=True`.
- El fallo del diagnostico automatico no invalida ni revierte una Demo ya creada; se informa por separado.

## Prueba al abrir FreeCAD

1. Confirmar build `2026.09.09.6` y Demo `0.8.1`.
2. Ejecutar `FA Demo edificio -> Casa fija 2 pisos 6 x 8 m`.
3. Al finalizar debe abrirse directamente el dialogo `FA Demo edificio - diagnostico`.
4. El alcance debe indicar **Documento completo**, aun si FreeCAD dejo algun objeto seleccionado.
5. Probar `Copiar ruta del MD` y pegarla en un editor; debe copiar la ruta completa del `.md`.
6. Probar `Abrir carpeta`; debe abrir `_reportes_diagnostico` mediante Qt.
7. Ejecutar luego `FA Informe diagnostico` con un objeto seleccionado y confirmar que pregunta el alcance antes de capturar.

---

# TAREA ACTUAL - 2026-09-09 15:25 - Escalera canonica integrada en FA Demo edificio

Workbench: **Facil Arquitectura**  
FreeCAD objetivo: **1.1.3**  
Build de desarrollo: **0.14.11 / 2026.09.09.5**  
Demo: **0.8.0**  
Estado: `IMPLEMENTADO EN DRIVE / PRUEBAS PURAS Y CONTRATOS OK / SMOKE FREECAD PENDIENTE`

## Objetivo inmediato

Usar **FA Demo edificio - 2 pisos** como banco de prueba de la herramienta real `FA Escalera entre losas`, sin implementar una escalera especial para la Demo.

## Implementacion vigente

- La Demo define un unico recorrido canonico de tres puntos dentro del distribuidor frontal de Nivel 01.
- `cmd_demo_building.py` crea solo el recorrido fuente y llama al mismo `plan_angled_stair()` + `build_stair_context()` + `create_native_stair()` del comando normal.
- La geometria de escalera sigue siendo autoridad de `Arch.makeStairs()`; no hay solidos de escalera FA paralelos.
- Se corrigio `resolve_level_context()`: un Level nativo padre directo gana antes de recorrer dependencias indirectas. Esto debe recuperar correctamente `FA_UpperLevel=Nivel 01` pese al enlace del controlador Demo.
- Se agrego proteccion contra una segunda escalera FA entre las mismas dos losas.
- Un recorrido fuente raiz se adopta en `Auxiliares FA`; el recorrido de Demo permanece en su grupo deliberado de fuentes.
- En FreeCAD 1.1.3 las barandillas nativas de la escalera multisegmento se conservan pero se ocultan en esta fase (`FA_RailingStatus=native_hidden_freecad_1_1_3_multisegment`). No se crea una barandilla paralela.
- La losa superior continua **sin hueco** en esta fase.
- El PLAN 2D documental se conserva.

## Escalera canonica

```text
P0 = (5200,  500) mm
P1 = (5200, 2800) mm
P2 = (2700, 2800) mm
Ancho = 1000 mm
Contrahuella objetivo = 175 mm
```

Plan puro esperado: 17 contrahuellas, reparto 8+9, contrahuella ~176.47 mm, giro 90 deg, huellas ~257.14/250 mm.

## Prueba al reabrir FreeCAD

1. Sin reutilizar el documento viejo con las dos escaleras manuales, ejecutar **FA Demo edificio -> Casa fija 2 pisos 6 x 8 m**.
2. Confirmar `Version de prueba: 0.8.0` y build `2026.09.09.5`.
3. Debe aparecer **una sola** escalera en Nivel 00 enlazando las dos losas.
4. No deben verse las barandillas largas defectuosas de la prueba anterior.
5. Ejecutar `FA Informe diagnostico` sobre el documento completo.
6. Esperado: desaparecen `DUPLICATE_STAIRS_SAME_SLABS`, `STAIR_LEVEL_CONTEXT_INCOMPLETE` y `STAIR_SOURCE_IS_ROOT`.
7. La falta de hueco de la losa superior sigue siendo pendiente deliberado.

---

# TAREA ACTUAL - 2026-09-09 - FA Informe diagnostico 0.1.1

Fecha: 2026-09-09 15:05 America/Costa_Rica
Workbench: Facil Arquitectura `0.14.11 / 2026.09.09.4`
FreeCAD objetivo: `1.1.3`
Estado: IMPLEMENTADO EN DRIVE / PRUEBA REAL DE RUTA PENDIENTE

Ajuste: los reportes MD/TXT/JSON ya no se guardan por defecto dentro del paquete del Workbench. `cmd_model_diagnostic.py` resuelve el directorio de macros configurado mediante `FreeCAD.getUserMacroDir(True)` y crea alli `_reportes_diagnostico`. Esto evita rutas Windows hardcodeadas y permite que la carpeta de macros sincronizada por el usuario transporte los reportes entre equipos. Si la API no devuelve una ruta util, se conserva como fallback la carpeta local del Workbench.

Prueba inmediata: ejecutar nuevamente `FA Informe diagnostico` y confirmar que el cuadro final muestre una ruta bajo `<MacroDir>\_reportes_diagnostico\`. No modificar el modelo.

---

# TAREA ACTUAL - 2026-09-09 - FA Escalera entre losas

Fecha: 2026-09-09 12:58 America/Costa_Rica
Workbench: Facil Arquitectura `0.14.11 / 2026.09.09.2`
FreeCAD objetivo: `1.1.3`
Estado: IMPLEMENTADO EN DRIVE / PRUEBAS PURAS APROBADAS / SMOKE REAL PENDIENTE

Objetivo inmediato: validar `FA Escalera entre losas` sobre la demo de dos pisos ya generada por el usuario. La herramienta debe reutilizar `Arch.makeStairs()` como autoridad geometrica, planificar mediante el nucleo independiente `fa_stair_core.py`, conservar enlaces a las dos losas y Levels y crear PLAN 2D documental.

Prueba requerida:
1. Reiniciar/activar FA y confirmar aviso de build `2026.09.09.2`.
2. En la demo 2 pisos, crear o usar un Wire/Sketch abierto de exactamente dos segmentos en L.
3. Seleccionar losa inferior + losa superior + Wire/Sketch y ejecutar `FA Escalera entre losas`.
4. Confirmar que se crea una escalera Arch nativa con tres segmentos (tramo + descanso + tramo), que arranca en la cara superior de la losa inferior y termina en la superior.
5. Revisar ancho, contrahuella, huellas, PLAN 2D, pertenencia al Level inferior y enlaces `FA_LowerSlab/FA_UpperSlab/FA_LowerLevel/FA_UpperLevel`.
6. No cortar todavia la losa superior; el hueco es una fase posterior.
7. Ejecutar `CapturarArbolYPrompt.FCMacro` al terminar para revisar el arbol/relaciones antes de integrar la escalera automaticamente en la Demo.

Nota: el ultimo modelo de demo se genero correctamente segun reporte del usuario, pero la Demo aun no exporta automaticamente MD/JSON; la retroalimentacion estructural del ultimo modelo sigue pendiente de una nueva captura.

---

# TAREA ACTUAL - 2026-09-09 - FA Demo edificio 0.7.0

Fecha: 2026-09-09 12:20 America/Costa_Rica
Estado: IMPLEMENTADO EN DRIVE / PRUEBAS PURAS APROBADAS / SMOKE FREECAD PENDIENTE
Build general: `0.14.11 / 2026.09.09.1`

Objetivo del siguiente smoke real:

1. Al activar Facil Arquitectura despues de sincronizar/reiniciar, debe aparecer el aviso de cambio de build a `2026.09.09.1`.
2. `Site -> Building` debe contener exactamente dos Levels nativos distintos: `Nivel 00` y `Nivel 01`.
3. `Nivel 01` debe permanecer en Z=3000 mm y el techo en la planta superior.
4. Planta superior: tres recintos, dos puertas interiores, ninguna puerta exterior y cinco ventanas distintas a Nivel 00.
5. Los cielorrasos/tablas de Nivel 00 y Nivel 01 deben coexistir; la creacion del segundo no debe borrar el primero.
6. No deben aparecer `PropertyLinkList: invalid document object` ni `The graph must be a DAG` al finalizar.
7. Confirmar que la casa de una planta y la demo guiada siguen sin regresiones.

Pendiente posterior, separado del smoke: integrar la macro existente `CapturarArbolYPrompt.FCMacro` como diagnostico MD/JSON reutilizable para GPT/Codex, en vez de crear un sistema paralelo.

---

# Tarea actual 2026-09-08 - FA Demo edificio de dos pisos

Workbench: Facil Arquitectura `0.14.11`. FreeCAD objetivo: `1.1.3`.
Estado: **implementacion en Drive completada; smoke real pendiente; build general sin incrementar**.

Objetivo inmediato: validar `FA Demo edificio -> Casa fija 2 pisos 6 x 8 m`. Debe crear un unico Building con `Nivel 00` a 0 mm y `Nivel 01` a 3000 mm, una losa por nivel, muros/puertas/ventanas/Spaces en ambos niveles y techo solamente en el nivel superior. Verificar que la segunda losa no cree un segundo Site.

Pruebas requeridas en FreeCAD real:

1. Arbol `Site -> Building -> Nivel 00 / Nivel 01`.
2. Elevaciones globales correctas: segundo piso +3000 mm y cubierta sobre +6000 mm aproximadamente.
3. Puertas y ventanas hospedadas en muros del Level correcto.
4. Spaces y cielorrasos contenidos por el Level correspondiente.
5. Losa de entrepiso persistente, sin reemplazar la losa inferior.
6. Guardar/reabrir, Undo/Redo de la transaccion completa y no regresion de `Casa fija 6 x 8 m`.
7. La escalera nativa queda pendiente de verificacion de API/runtime; no crear una escalera FA paralela.

Archivos principales modificados: `core/demo_building_core.py`, `commands/cmd_demo_building.py`, `core/site_floor_utils.py`, `tests/test_demo_building_core.py`, `tests/test_demo_building_contract.py`.

---

# Tarea actual 2026-09-03 - validar FA Reparar puertas guiado por jamba (build 2026.09.03.6)

Workbench: Facil Arquitectura `0.14.11`. FreeCAD: `1.1.3`.

Objetivo inmediato: validar en la copia Upala_GUI_Acceptance que una puerta mal posicionada puede repararse seleccionando **puerta + jamba**. Flujo: seleccionar puerta, ejecutar `FA Reparar puertas`, seleccionar una arista vertical de la jamba de pared (o preseleccionar puerta+jamba), confirmar el diagnostico y comprobar que `Width` se conserva. La consola debe mostrar `jamba seleccionada`, `endpoint`, `shift`, `Base` antes/despues y `verify`. Si la verificacion no queda dentro de tolerancia, la transaccion debe abortarse. Probar despues Undo/Redo e idempotencia. No modificar todavia `FA Puertas BIM`.

---

# TAREA ACTUAL - FA Reparar puertas / criterio asistido legado

Fecha y hora: 2026-09-03 14:24 America/Costa_Rica  
Workbench: Facil Arquitectura `0.14.11`  
Build objetivo: `2026.09.03.5`  
FreeCAD: `1.1.3`

## Objetivo

Corregir exclusivamente `FA Reparar puertas` para que documentos historicos producidos bajo el contrato de segmento de hoja no sean redimensionados incorrectamente al aplicar la regla nueva de buque completo. No modificar todavia `FA Puertas BIM`.

## Diagnostico confirmado

En Upala, la build `.4` cargo correctamente y produjo `resize_and_move`, `Width=763.851 -> 663.851 mm`. La diferencia `100 mm` coincide con `Frame2+Frame3`, firma del contrato historico BOUNDED.

## Implementacion requerida

- Nucleo independiente de GUI con semanticas `AUTO`, `BUQUE_COMPLETE`, `LEGACY_LEAF`.
- `LEGACY_LEAF`: expandir temporalmente el segmento fuente por `Frame2`/`Frame3`; no tocar el Sketch.
- `AUTO`: usar pista explicita si existe o detectar la firma numerica historica.
- Antes de escribir, pedir al usuario confirmar que representa el segmento.
- Replanificar despues de la eleccion del usuario.
- Mantener la prioridad `inside -> no-op`, `fits -> move_only`, `oversized -> resize_and_move`.
- Mantener transaccion, rollback, Undo/Redo, verificacion posterior e idempotencia.
- Registrar criterio y longitudes fuente/efectiva en consola y propiedades.
- No modificar bisagra, apertura, Host ni generador original.

## Validacion esperada

- Pruebas puras focales 15/15 o superiores.
- Smoke real en `Upala_GUI_Acceptance` o copia segura del levantamiento.
- Para la puerta historica: con `LEGACY_LEAF`/`AUTO`, `Width` debe permanecer `763.851 mm`; el plan debe ser `move_only` y corregir el desfase de `75 mm`.
- Reejecucion posterior: `OK`, sin cambios adicionales.
- Probar Deshacer/Rehacer y guardar/reabrir.

---

# TAREA VIGENTE - ElectricCR / RoomResolver fase 2A + contrato semantico del arbol

Fecha: 2026-09-01 America/Costa_Rica
Proyecto: `Programacion en FreeCAD`
Componentes: `ElectricCR`, `CRBIMCore 0.1.0`, compatibilidad con `FacilArquitecturaWB`
FreeCAD objetivo: `1.1.3`
Estado: `COMPLETADA / PROBADA / VERIFICADA MCP`

## Objetivo

Adoptar `CRBIMCore.RoomResolver` en el calculo de iluminacion de ElectricCR sin redefinir todavia los objetos fisicos de luminarias, tomacorrientes ni apagadores, y dejar definido el contrato semantico que permitira reconstruir el arbol electrico desde relaciones estables en vez de usar la posicion en grupos como fuente de verdad.

La regla central de esta fase es:

> Las relaciones semanticas son la verdad; el arbol del modelo es una vista reproducible de esas relaciones.

## Contexto que debe preservarse

Existe una estructura historica/canonica de iluminacion:

`electrico/Iluminacion/Circuitos/<Circuito>/Recintos/<Recinto>/Apagadores/<Apagador>/Luminarias`

Tambien existen herramientas reales que ya organizan el arbol, entre otras:

- `Configuracion del proyecto/Organizar_Documento_Electrico.FCMacro`;
- `Configuracion del proyecto/Ordenar_Arbol_Electrico_Auto.FCMacro`;
- `Configuracion del proyecto/Ordenar_Grupos_ElectricCR.FCMacro`;
- `Configuracion del proyecto/Mover_Seleccion_a_Circuito.FCMacro`;
- `Iluminacion/Organizar_Luminarias_por_Circuito_y_Apagador.FCMacro`;
- `Iluminacion/Actualizar_Iluminacion_Completa.FCMacro`;
- `Iluminacion/Hoja_Iluminacion.FCMacro` o su nombre real equivalente con acentos.

No crear un segundo sistema de arbol en paralelo. Auditar y reutilizar/extender lo existente.

## Principios de arquitectura

1. El `Arch/BIM Space` permanece en la jerarquia arquitectonica nativa, normalmente bajo Building/Level. No moverlo al arbol electrico.
2. Los elementos ElectricCR pueden organizarse visualmente bajo la rama electrica, pero su pertenencia a recinto, circuito, tablero, sistema o control debe poder existir independientemente de esa posicion visual.
3. El arbol electrico debe poder reconstruirse de forma idempotente desde relaciones/propiedades estables.
4. La jerarquia visual no debe ser la unica forma de determinar `Circuito`, `Recinto`, `Apagador`, `Panel` o `Sistema`.
5. `RoomResolver` debe ser la fuente comun para resolver el recinto fisico: `NATIVE_SPACE` primero, `LEGACY_AREA` como fallback.
6. No crear objetos de recinto duplicados dentro del arbol electrico. Si se necesita un nodo `Recintos/<Recinto>`, debe ser un contenedor/vista electrica, no una segunda identidad arquitectonica.
7. No fijar todavia el modelo final de luminaria/toma/apagador sin auditar los App::Link, masters, propiedades y herramientas actuales.
8. Conservar el flujo 2D -> 3D y la futura posibilidad de que una sola identidad electromecanica tenga representacion documental 2D y representacion 3D.

## Alcance funcional de fase 2A

### A. Integracion piloto de RoomResolver

Auditar e integrar solamente la capa de calculo/lectura de iluminacion que actualmente obtiene datos de Areas, rotulos, grupos o tablas.

Objetivo minimo:

- obtener recinto mediante `CRBIMCore.RoomResolver`;
- leer nombre, area y los metadatos disponibles del recinto resuelto;
- mantener compatibilidad con Areas heredadas por el fallback del resolver;
- conservar los contratos actuales de `DatosRecintos`, hoja de iluminacion y calculo de cantidad/filas/columnas;
- no cambiar en esta fase la logica de colocacion fisica de luminarias.

### B. Contrato semantico del arbol

Auditar las herramientas actuales del arbol y documentar, sin migracion masiva, que relaciones ya existen y cuales faltan para reconstruir la jerarquia.

Como minimo estudiar:

- elemento -> Space/Recinto;
- elemento -> Circuito;
- circuito -> Tablero;
- luminaria -> Apagador/control cuando exista;
- elemento -> Sistema/Disciplina cuando corresponda;
- elemento -> Level cuando corresponda.

Preferir `App::PropertyLink` o mecanismos nativos equivalentes cuando ya existan o sean compatibles, pero no agregar propiedades nuevas masivamente en esta fase sin justificarlo y probarlo.

## Fuera de alcance

- No redefinir todavia el objeto electromecanico generico definitivo.
- No migrar luminarias actuales a un tipo nuevo.
- No migrar tomacorrientes ni apagadores.
- No modificar la geometria, Placement, master ni LinkedObject de elementos existentes salvo que una prueba temporal controlada lo requiera y sea explicitamente reversible.
- No cambiar `ColocarLuminarias_Link` ni otras herramientas de colocacion para usar nuevos objetos.
- No reorganizar automaticamente proyectos reales del usuario.
- No mover `Arch Space` al arbol electrico.
- No eliminar Areas legacy, grupos, macros o propiedades existentes.
- No convertir la jerarquia visual en fuente autoritativa de relaciones.
- No modificar MEPWorkbenchCR/HVAC en esta tarea.

## Auditoria obligatoria antes de programar

1. Leer `AGENTS.md` y `$freecad-cr-workbench-architecture`.
2. Leer la documentacion vigente de `CRBIMCore.RoomResolver`.
3. Inspeccionar codigo real de las macros/herramientas citadas y cualquier backend comun que ya usen.
4. Inventariar como se identifican hoy luminarias, tomas y apagadores: `App::Link`, master, propiedades, nombres, grupos, circuito, recinto, etc.
5. Identificar donde se construye/actualiza `DatosRecintos` y la hoja de iluminacion.
6. Identificar exactamente que logica usa hoy `Actualizar_Iluminacion_Completa` para detectar recintos.
7. Identificar como `Organizar_Documento_Electrico` y `Organizar_Luminarias_por_Circuito_y_Apagador` derivan la ruta del arbol.
8. Revisar muestras de arbol existentes, especialmente La Cruz y capturas recientes, sin modificar los FCStd originales.
9. Confirmar si ya existe un helper neutral o ElectricCR para relaciones semanticas antes de crear otro.

## Comportamiento esperado del piloto

El calculo de iluminacion debe funcionar en tres escenarios controlados:

1. documento con solo `Arch Space` nativo;
2. documento con solo Area legacy compatible;
3. documento con Space + Area legacy superpuestos, donde gana el Space.

Ademas:

- `AMBIGUOUS` no debe elegir silenciosamente un recinto;
- `NOT_FOUND` debe conservar un comportamiento seguro y diagnosticable;
- los resultados legacy deben mantenerse cuando solo existan Areas;
- no debe ser necesario crear luminarias para probar la resolucion espacial y el calculo.

## DatosRecintos y compatibilidad

Conservar columnas, nombres y contratos existentes salvo necesidad comprobada. Si se requiere informacion adicional para trazabilidad, preferir una extension compatible y documentada, por ejemplo una fuente de recinto o UID, sin romper consumidores actuales.

No asumir que `Largo` y `Ancho` existen para todos los Spaces. Para recintos no rectangulares, el calculo debe distinguir entre datos geometricos realmente disponibles y aproximaciones legacy. No inventar dimensiones sin una regla explicita.

## Contrato objetivo del arbol, aun no migrado

La rama historica de iluminacion se conserva conceptualmente:

```text
electrico
  Iluminacion
    Circuitos
      <Circuito>
        Recintos
          <Recinto>
            Apagadores
              <Apagador>
                Luminarias
                  <Luminaria...>
```

Pero los nodos deben ser una proyeccion de relaciones. El `Arch Space` real sigue en Building/Level y no se duplica ni se mueve.

Para otros sistemas no forzar esta misma forma si su semantica es distinta. Ejemplo ya definido: sensores de humo pueden organizarse por zonas.

## Pruebas obligatorias

Como minimo:

1. `RoomResolver` sigue aprobando su suite existente.
2. Calculo iluminacion con Space-only.
3. Calculo iluminacion con legacy-only.
4. Space + Area -> Space autoritativo.
5. `AMBIGUOUS` -> sin asignacion silenciosa.
6. `NOT_FOUND` -> resultado seguro.
7. `DatosRecintos` conserva contrato esperado.
8. Recalculo no duplica filas/objetos ni cambia luminarias existentes.
9. Firma documental de los elementos fisicos permanece sin cambios en pruebas read-only de calculo.
10. Auditoria del arbol demuestra que el organizador puede evolucionar hacia reconstruccion por relaciones sin depender solo del padre visual.
11. Smoke real FreeCAD 1.1.3 mediante MCP sobre documento temporal/demo; no guardar originales.

## Documentacion y cierre

Al terminar:

- actualizar este `TAREA_ACTUAL.md` con resultado real;
- actualizar `RESULTADO_CODEX.md` y `ESTADO_PROYECTO.md` del componente correspondiente;
- actualizar documentacion de ElectricCR y/o `CRBIMCore` cuando cambie un contrato;
- registrar una decision reusable en `Memoria_FreeCAD/` si se confirma el principio `relaciones -> arbol`;
- documentar claramente que el rediseño del objeto electromecanico sigue pendiente;
- dejar una recomendacion concreta para la siguiente fase: auditoria/diseno del objeto electromecanico comun y posterior reconstruccion idempotente del arbol.

## Criterio de cierre

Cerrar solamente cuando:

- ElectricCR use RoomResolver en el calculo piloto de iluminacion sin perder compatibilidad legacy;
- ningun elemento fisico haya sido migrado o reemplazado;
- el arbol actual haya sido auditado y exista un contrato documentado que separe relaciones semanticas de jerarquia visual;
- las pruebas controladas y el smoke FreeCAD 1.1.3 aprueben;
- no haya regresion de CRBIMCore ni del calculo de iluminacion existente.

## Instruccion a Codex

Implementar y probar solo esta fase 2A. Diagnosticar primero. Reutilizar las herramientas reales del arbol y de iluminacion. No redefinir todavia luminarias/tomas/apagadores, no migrar elementos y no reorganizar FCStd originales. Detenerse al documentar el resultado.

## Resultado de cierre 2026-09-01

- `Actualizar_Iluminacion_Completa.FCMacro` usa el adaptador read-only
  `ElectricCR.electriccr.lighting.room_calculation`, basado en `CRBIMCore`.
- Space-only, legacy-only y Space sobre Area aprobaron; el Space es autoritativo.
- `AMBIGUOUS` y `NOT_FOUND` quedan diagnosticados sin asignacion silenciosa.
- `DatosRecintos` conserva exactamente 12 encabezados; la tabla legacy y la
  formula existente de cantidad/filas/columnas permanecen.
- Areas heredadas conservan sus propiedades de layout. Los Spaces no reciben
  `Rows`, `Columns` ni propiedades ElectricCR nuevas.
- El comando completo se ejecuto dos veces sin duplicar hojas/objetos y sin
  crear luminarias.
- Firma de Shape, Placement, Name, TypeId y propiedades del Space: estable,
  incluyendo guardar/cerrar/reabrir.
- La auditoria confirma propiedades explicitas antes que padre visual,
  `PropertyLinkList` en controles y faltantes de enlaces uniformes para Room,
  Panel, Level y System.
- Contrato documentado en `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md`.
- Las copias locales de La Cruz revisadas contienen arquitectura/plataforma,
  pero no un arbol electrico util para inferir relaciones historicas; no se
  abrieron ni guardaron modelos originales.

Pruebas: 17 pruebas puras, smoke RoomResolver fase 1, smoke legacy de Areas,
smoke fase 2A y smoke read-only del contrato semantico, todos aprobados en
FreeCAD 1.1.3 cuando aplica.

La fase se detiene aqui. Sigue pendiente, fuera de alcance, el diseno del objeto
electromecanico comun y la reconstruccion idempotente del arbol desde relaciones.


---

# TAREA ACTUAL - 2026-09-09 - FA Informe diagnostico

Fecha: 2026-09-09 14:55 America/Costa_Rica
Workbench: Facil Arquitectura `0.14.11 / 2026.09.09.3`
FreeCAD objetivo: `1.1.3`
Estado: IMPLEMENTADO EN DRIVE / PRUEBAS PURAS APROBADAS / SMOKE FREECAD PENDIENTE

Objetivo:
- formalizar la macro historica `CapturarArbolYPrompt.FCMacro` como motor reutilizable del Workbench;
- generar diagnostico de solo lectura en TXT/Markdown/JSON;
- conservar jerarquia visual mediante `ViewProvider.claimChildren()` con fallback `Group`;
- separar captura FreeCAD de analisis puro JSON-compatible;
- detectar inicialmente errores de lectura/estado, ciclos, padres visuales multiples, Levels BIM y relaciones de FA Escalera entre losas;
- mantener la macro historica como wrapper pequeno del mismo motor.

Implementacion:
- `core/model_diagnostic_core.py` 0.1.0: analisis y render MD/TXT independiente de FreeCAD/Qt.
- `core/model_diagnostic_freecad.py` 0.1.0: snapshot read-only de arbol, relaciones, estado, Placement y BoundBox.
- `commands/cmd_model_diagnostic.py` 0.1.0: comando `FA_ModelDiagnostic` / `FA Informe diagnostico`.
- `resources/icons/diagnostic_report.svg`.
- `CapturarArbolYPrompt.FCMacro` 2.0.0: wrapper compatible; ya no duplica el motor.
- `InitGui.py`: comando agregado a `FA Proyecto BIM`.
- build general: `2026.09.09.3`.

Pruebas fuera de FreeCAD:
- `py_compile`: OK.
- `test_model_diagnostic_core.py`: 2/2.
- `test_model_diagnostic_contract.py`: 2/2.
- total focal: 4/4.

Smoke requerido en FreeCAD real:
1. Hot Restart y confirmar build `2026.09.09.3`.
2. Abrir la casa demo con escalera ya generada.
3. Ejecutar `FA Informe diagnostico` sin seleccion.
4. Confirmar creacion de TXT/MD/JSON en `_reportes_diagnostico`.
5. Verificar que el MD detecta dos escaleras entre las mismas losas y los Wire fuente como raices, sin modificar el documento.
6. Subir el MD al chat para revisar precision/ruido de las reglas antes de automatizarlo al final de la Demo.

---

# TAREA ACTUAL - 2026-09-15 - Demo Escalera minima / marco local editable

Fecha: 2026-09-15 14:24 America/Costa_Rica
Workbench: Facil Arquitectura `0.14.12 / 2026.09.15.4`
FreeCAD objetivo: `1.1.3`
Estado: IMPLEMENTADO EN DRIVE / PY_COMPILE APROBADO / PRUEBA REAL PENDIENTE

Alcance estricto: solo `Demo Escalera minima`. No se cambia el comportamiento visible de `Casa demo 2 pisos` ni del comando interactivo `FA Escalera entre losas`.

Objetivo:
- colocar el origen/Placement de la escalera en su arranque real;
- usar un Draft Wire real como recorrido y autoridad de Placement del ejemplo;
- usar Draft Line para ambos tramos base y Draft Wire para el descanso, en lugar de `Part::Feature` genericos;
- hacer que el buque nativo de la losa superior se construya en el mismo marco local y siga el Placement del recorrido.

Implementacion:
- `build_minimal_stair_demo_spec()` activa `editable_local_frame`, `base_geometry_mode=draft_line_wire` y `opening_follows_source` solo para esta demo.
- el recorrido guarda puntos locales con `(0,0,0)` en el arranque y Placement global en el punto inicial;
- el adaptador conserva su ruta historica como predeterminada y expone opciones opt-in para bases Draft/locales y buque ligado al recorrido;
- el PLAN 2D y las barandillas nativas reciben la misma autoridad de Placement cuando el modo local esta activo.

Validacion pendiente en FreeCAD real:
1. Hot restart y confirmar build `2026.09.15.4`.
2. Generar `Demo Escalera minima`.
3. Confirmar que el gizmo/origen de `FA Escalera entre losas` aparece en el arranque inferior.
4. Confirmar que las bases son Draft Line / Draft Wire.
5. Mover o rotar el `FA Escalera - Recorrido demo` y verificar que escalera + buque de losa + PLAN 2D acompanen la transformacion.
6. Verificar que `Casa demo 2 pisos` no cambio.

---

# TAREA ACTUAL - 2026-09-15 - Demo Escalera minima / tapichel dinamico

Fecha: 2026-09-15 16:17 America/Costa_Rica
Workbench: Facil Arquitectura `0.14.12 / 2026.09.15.7`
FreeCAD objetivo: `1.1.3`
Estado: IMPLEMENTADO EN DRIVE / PY_COMPILE APROBADO / PRUEBA REAL PENDIENTE

Alcance estricto: solo `Demo Escalera minima`. `Casa demo 2 pisos` conserva su comportamiento historico; se reutiliza la misma funcion de tapichel mediante parametros opt-in.

Estado acumulado del ejemplo:
- desde build `.5`, `FA Escalera entre losas.Placement` es la autoridad editable; el recorrido Draft queda como referencia inicial;
- desde build `.6`, el buque de losa y el recorte dinamico del cielorraso siguen el Placement del master;
- build `.7` agrega el tapichel lateral de 100 mm, reutilizando `create_stair_opening_liner()` de Casa demo 2 pisos.

Implementacion build `.7`:
- `create_stair_opening_liner()` acepta opcionalmente `placement_source` y `link_master_liner`;
- en modo dinamico convierte zonas y extremos abiertos al marco local de la escalera y enlaza `liner.Placement` a `Stairs.Placement`;
- evita el ciclo DAG guardando `FA_OpeningLinerName` en el master en lugar de un PropertyLink inverso;
- `build_minimal_stair_demo_spec()` activa `create_opening_liner=True` y `opening_liner_follows_master=True`;
- el recorte de cielorraso ya incluye el espesor exterior del tapichel mediante `build_ceiling_finish_exclusion_zones()`;
- la Casa demo 2 pisos sigue usando la llamada historica sin `placement_source`.

Validacion fuera de FreeCAD:
- `py_compile` aprobado para `stair_freecad_adapter.py`, `demo_building_core.py`, `cmd_demo_building.py` y `constants.py`;
- contrato puro: tapichel activo, sigue master, exclusion de cielo sigue master, espesor 100 mm.

Smoke requerido:
1. Hot restart y confirmar build `2026.09.15.7`.
2. Generar `Demo Escalera minima`.
3. Verificar que el tapichel cierre visualmente el plenum entre cielorraso y cara inferior de losa, dejando abiertos entrada y salida de la escalera.
4. Mover y girar `FA Escalera entre losas` y confirmar que se mueven juntos buque de losa + buque de cielo + tapichel + PLAN.
5. Confirmar ausencia de ciclos DAG y que Casa demo 2 pisos no cambio.
