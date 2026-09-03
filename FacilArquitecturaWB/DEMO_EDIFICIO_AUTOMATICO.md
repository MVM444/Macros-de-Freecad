# FA Demo edificio automatico

Fecha: 2026-09-02 America/Costa_Rica
Workbench: Facil Arquitectura
FreeCAD objetivo: 1.1.3
Version: 0.14.11
Build: 2026.09.02.2
Comando: `FA_DemoBuilding`

## Presentacion de usuario - build 2026.09.02.2

El dialogo de Demo distingue de forma explicita casa fija, casa aleatoria reproducible por semilla y ejecucion completa o guiada. Los textos principales siguen el idioma de FreeCAD (Espanol/Ingles). La interfaz indica que la Demo sirve para aprender y probar capacidades de FA, pero no valida que un DWG arbitrario pueda reconstruirse automaticamente.


## Objetivo

Crear un ejemplo pequeno, completo y repetible del flujo de Facil Arquitectura sin depender de un archivo previo. La demostracion abre un documento nuevo y materializa progresivamente fuentes 2D y objetos BIM nativos:

`Sketches -> piso/losa -> muros -> puertas/ventanas -> recintos 2D -> Espacios BIM -> cielorraso 600x600 -> huella de techo -> cerchas/clavadores/cubierta`.

La herramienta no modifica el documento de trabajo que estuviera abierto.

## Tipologia elegida

Se adopta una casa rectangular de una planta con cubierta simple a dos aguas. Esta tipologia se eligio porque permite demostrar todo el flujo arquitectonico con geometria facil de leer y de reproducir. Como referencia conceptual se revisaron ejemplos contemporaneos de microcabanas de huella rectangular y techo gable; la herramienta no copia ningun plano comercial y genera su propia geometria parametrica.

## Referencias conceptuales revisadas en Web

- Planner 5D, *Cozy Micro Cabin Plan for Weekend Escapes*: microcabana de una planta, huella aproximada 16 x 20 pies y techo simple a dos aguas; la ficha destaca la huella rectangular como simplificacion de cimentacion.
- Planner 5D, *Cozy Tiny Cabin House Plan with Open Studio Layout*: una planta, huella rectangular y cubierta simple front-to-back a dos aguas.

Estas referencias solo justifican la tipologia de demostracion. No se reproducen sus plantas, distribuciones ni dimensiones comerciales; la casa FA de 6 x 8 m y su generador aleatorio son propios.

## Caso canonico

La opcion `Casa fija 6 x 8 m` usa una especificacion constante:

- Huella: 6000 x 8000 mm.
- Altura de muros: 3000 mm.
- Muros exteriores: 200 mm.
- Un tabique interior: 120 mm, ubicado a Y=5200 mm.
- Puerta exterior: 1000 mm.
- Puerta interior: 900 mm.
- Seis ventanas.
- Antepecho de ventanas: 900 mm.
- Altura de ventanas: 1200 mm.
- Losa: 150 mm.
- Techo a dos aguas: 22 grados, alero 500 mm.
- Cerchas: separacion maxima 2800 mm.
- Clavadores: separacion maxima 800 mm.
- Semilla canonica: 20260831.

## Modo aleatorio reproducible

La opcion `Casa aleatoria reproducible` utiliza `random.Random(seed)` dentro de `core/demo_building_core.py`. No depende del estado global del generador aleatorio. La misma semilla produce exactamente la misma especificacion JSON.

Se varian dentro de limites conservadores: ancho y fondo de huella, altura de muro, posicion del tabique, espesores, ubicacion/ancho de puertas, ancho de ventanas, antepecho/altura de ventanas, espesor de losa, pendiente y alero de techo y separaciones de cerchas/clavadores.

Las aberturas mantienen margenes minimos respecto a esquinas y separaciones minimas entre ellas. Antes de entregar una especificacion, el nucleo la valida y comprueba que sea serializable a JSON.

## Arquitectura y reutilizacion

`core/demo_building_core.py` es independiente de FreeCAD, FreeCADGui y Qt. Solo decide datos y geometria logica.

`commands/cmd_demo_building.py` actua como adaptador FreeCAD y reutiliza las herramientas vigentes del Workbench:

- estructura de proyecto y parametros FA;
- Building/Level BIM nativos;
- preparacion y creacion de muros desde Sketches;
- piso/losa desde Sketch;
- creacion de puertas y ventanas hospedadas desde segmentos de centro;
- `FA Techo desde rectangulo` mediante su nuevo adaptador programatico;
- `ReloadableCommandProxy` para el comando registrado.

El adaptador de techo publicado en `cmd_roof_axis_prototype.py` se llama `create_roof_from_rectangle_programmatic(...)`. Reutiliza el mismo algoritmo validado del boton interactivo y no guarda preferencias salvo que el llamador lo solicite.

## Objetos fuente 2D

La demo conserva fuentes documentales identificables:

- `Sketch_Muros_Exteriores_Demo`;
- `Sketch_Muro_Interior_Demo`;
- `Sketch_Centros_Puertas_Demo`;
- `Sketch_Centros_Ventanas_Demo`;
- `Huella techo - Demo`, como `Draft Rectangle`.

Los Sketches de puertas y ventanas pueden quedar ocultos despues de materializar las aberturas, pero permanecen en el arbol y son recuperables para documentacion/diagnostico.

## Control y trazabilidad

Cada documento contiene `FA_DemoBuilding`, un objeto controlador con semilla, modo, resumen y la especificacion JSON completa. Esto permite reproducir una demostracion aleatoria y comparar el resultado con su entrada.

La materializacion se ejecuta en una sola transaccion. Si falla, se aborta y se cierra el documento de demostracion para no dejar una construccion parcial.

## Pruebas previas a publicacion

- 6/6 pruebas focales aprobadas.
- Sintaxis Python de todos los archivos nuevos/modificados: aprobada mediante `compile()`.
- 5000 semillas aleatorias consecutivas: especificaciones validas, sin violaciones del contrato del nucleo.
- Pendiente: smoke test real del boton y del arbol producido en FreeCAD 1.1.3.

## Uso

1. Reiniciar FreeCAD despues de instalar/sincronizar este build, porque se agrega un boton a una barra existente.
2. Abrir Facil Arquitectura.
3. Ejecutar `FA Demo edificio` desde `FA Proyecto BIM`.
4. Elegir casa fija o aleatoria reproducible.
5. En modo aleatorio, introducir una semilla.
6. Aceptar. La herramienta crea un documento nuevo y ajusta la vista al resultado.

## Limites de esta primera version

La demo busca mostrar el flujo del Workbench, no resolver distribucion arquitectonica avanzada. Por ahora usa una huella rectangular, un unico tabique interior, una planta, techo a dos aguas y una cantidad pequena de aberturas. La aleatoriedad se limita deliberadamente a casos que deberian ser geometricamente seguros y faciles de inspeccionar.

Las futuras ampliaciones deben seguir siendo reproducibles por semilla y no deben sustituir el caso canonico estable.


## Correccion de ejecucion build 2026.08.31.8

La primera prueba real en FreeCAD 1.1.3 detecto que el piso se intentaba crear inmediatamente despues de agregar geometria a los Sketches. `site_floor_utils.combined_sketch_bounds()` obtiene la huella desde `Sketch.Shape.BoundBox`, pero `SketchObject.Shape` se actualiza de forma diferida y todavia no estaba recomputado. Esto producia falsamente el mensaje de que la envolvente era demasiado pequena aunque la especificacion logica fuese 6000 x 8000 mm.

El adaptador ahora:

1. crea todos los Sketches fuente;
2. ejecuta `doc.recompute()`;
3. valida que el Sketch exterior materializado mida lo esperado en milimetros;
4. solo entonces crea el piso BIM;
5. sincroniza `Spreadsheet_Parametros` con las dimensiones reales de la demo en lugar de dejar los valores generales 12000 x 9000 del Workbench.

La prueba de contrato exige conservar el orden `recompute -> validar huella -> crear piso`.

## Casa demo v2 - recintos, Espacios BIM y cielorraso - build 2026.08.31.9

La segunda versión conserva la casa y el generador aleatorio de la primera demostración y agrega tres capas que forman parte del flujo normal de Fácil Arquitectura:

1. **Recintos documentales 2D.** Se ejecuta la lógica existente de detección de recintos sobre los Sketches de muros exterior e interior y se conserva el Sketch generado.
2. **Espacios BIM nativos.** Cada recinto se convierte en un `Arch Space` con volumen hasta la cota de cielorraso. La geometría de planta queda registrada como JSON en `FA_FloorPolygonJSON`.
3. **Cielorraso modular 600 x 600.** Se reutiliza el generador vigente de cielorrasos, ahora capaz de consumir directamente los Spaces BIM de la demo.

### Caso canónico v2

Para la casa fija de 6000 x 8000 mm, descontando espesores de muros, se materializan dos recintos sencillos:

- `R01 - Estar-comedor`: aproximadamente 29.23 m2.
- `R02 - Dormitorio`: aproximadamente 15.31 m2.

La altura de Space y cota de cielorraso es 2700 mm en el caso fijo. En modo aleatorio se calcula de forma conservadora en función de la altura de muros, con mínimo 2400 mm y máximo 2700 mm.

### Objetos adicionales esperados

El árbol de la demo debe incluir, además de los objetos de v1:

- `Sketch Recintos - Demo` (o etiqueta equivalente generada por la herramienta de recintos);
- grupo `Espacios BIM - Demo`;
- `Espacio BIM - Estar-comedor - Demo`;
- `Espacio BIM - Dormitorio - Demo`;
- los objetos de cielorraso modular generados por `create_modular_ceilings()`;
- el schedule de cielorrasos que ya forma parte de esa herramienta.

Los sólidos Base de los Spaces son auxiliares nativos y quedan ocultos.

### Contrato de reutilización

Casa demo v2 no implementa algoritmos paralelos. Reutiliza explícitamente:

- `create_closed_room_sketch(...)` para detectar/documentar recintos;
- `Arch.makeSpace(...)` para volumen BIM;
- `create_modular_ceilings(...)` para retícula, paneles y schedule;
- `create_roof_from_rectangle_programmatic(...)` para el techo.

La especificación `demo_building_core.py` sigue siendo independiente de FreeCAD/GUI/Qt y ahora añade `rooms` y `ceiling`. La misma semilla reproduce también estas secciones.

### Icono de puerta en el árbol

En FreeCAD 1.1.3 una puerta BIM puede aparecer con icono de ventana porque la herramienta BIM Door utiliza un objeto `Arch Window` configurado con preset de puerta y su ViewProvider nativo suministra el icono de ventana. No se modifica ese ViewProvider dentro de Casa demo v2; el asunto queda separado como mejora visual para no arriesgar cortes, hosting ni edición de las puertas.

### Validación previa a publicación

- 10/10 pruebas focales de núcleo y contrato: aprobadas.
- Sintaxis de los seis archivos nuevos/modificados principales: aprobada con `compile()`.
- Caso fijo: 2 recintos, módulo de cielo 600 mm, nombres y áreas válidos.
- Varias semillas aleatorias: determinismo de recintos/cielos confirmado.
- Pendiente: ejecutar la demo completa en FreeCAD 1.1.3 y verificar visualmente Spaces, cielorrasos, árbol y continuidad del resto del edificio.


## Modo demostracion guiada - build 2026.08.31.10

`FA Demo edificio` conserva el mismo comando y la misma especificacion del generador. El dialogo inicial agrega solamente la forma de ejecucion: `Generar edificio completo` o `Demostracion guiada paso a paso`. No se crea un segundo generador ni una segunda casa.

El guion declarativo vive en `core/demo_guided_core.py`, que no importa FreeCAD, FreeCADGui ni Qt. Define 14 pasos estables y JSON-compatibles: proyecto/Level, Sketches de muros, losa, muros, Sketch de puertas, puertas BIM, Sketch de ventanas, ventanas BIM, recintos 2D, Espacios BIM, cielorraso, huella de techo, techo BIM y finalizacion. Las recomendaciones de camara (`top`/`axon`) tambien son datos declarativos y no forman parte del modelo.

`commands/cmd_demo_building.py` incorpora `DemoBuildingSession`, adaptador comun de materializacion. El modo completo recorre los 14 pasos dentro de la transaccion atomica historica; el modo guiado ejecuta exactamente los mismos metodos con una transaccion por paso. De esta forma una correccion futura de piso, muros, aberturas, recintos, cielorraso o techo afecta a ambas formas de ejecucion sin duplicacion.

La interfaz guiada es un `QDockWidget` no modal para mantener visible simultaneamente el arbol y la vista 3D. Controles iniciales: `Reiniciar`, `Anterior`, `Reproducir/Pausa`, `Siguiente`, velocidad lenta/normal/rapida y `Encuadre automatico`. `QTimer` solamente programa el siguiente paso; nunca ejecuta geometria en un hilo paralelo.

`Anterior` no intenta borrar manualmente objetos ni depende de una cadena fragil de `undo()`: cierra exclusivamente el documento de demostracion no guardado y reconstruye la misma especificacion determinista hasta el paso anterior. Esto conserva la semilla y evita estados parciales de dependencias BIM.

El controlador `FA_DemoBuilding` agrega `ExecutionMode`, `CurrentStep`, `TotalSteps`, `PlaybackState`, `LastCompletedStep`, `LastError`, `AutoCamera` y `StepPlanJSON`. La `SpecificationJSON` existente sigue siendo la autoridad geometrica.

Validacion previa a FreeCAD real: sintaxis Python aprobada y 15/15 pruebas focales de demo/core/contrato aprobadas. Queda pendiente el smoke real en FreeCAD 1.1.3 del panel, los 14 pasos, Reproducir/Pausa, Anterior/Reiniciar y el resultado final.

## Saneamiento posterior a la primera prueba real - build 2026.09.01.1

La primera ejecucion guiada real en FreeCAD 1.1.3 completo 14/14 pasos con una casa aleatoria reproducible (`seed=123456`). Se detectaron dos avisos no bloqueantes y se corrigieron sin cambiar geometria, secuencia ni especificacion JSON:

- `The graph must be a DAG`: el controlador `FA_DemoBuilding` enlazaba `Site` dentro de `GeneratedObjects`. Como `Site -> Building -> Level -> FA_DemoSources -> FA_DemoBuilding` ya forma la cadena de contencion, el enlace inverso `FA_DemoBuilding -> Site` cerraba un ciclo. Desde esta build, `GeneratedObjects` contiene solo resultados hoja; los nombres de `Site`, `Building`, `Level` y `FA_DemoSources` se guardan en `ContextContainersJSON`, sin enlaces de dependencia.
- Falsa advertencia de parametros ausentes: `ensure_parameter_sheet()` acababa de escribir las celdas, pero `_sync_demo_parameter_sheet()` intentaba leerlas antes de recomputar el documento. Ahora se hace `recompute()` antes y despues de sincronizar, y la consola informa `Parametros demo sincronizados: 10/10` cuando la operacion queda completa.

La build conserva los 14 pasos del modo guiado, el modo completo atomico y la misma casa para una misma semilla. La correccion se valida estaticamente con compilacion Python, 2 pruebas focales nuevas de saneamiento, 5 pruebas del nucleo de la casa y comprobacion del guion de 14 pasos. Falta repetir la prueba real en FreeCAD para confirmar que desaparecen ambos avisos.



## Pulido visual del modo guiado - build 2026.09.01.2

La logica BIM validada de la build anterior se conserva sin cambios. Esta iteracion actua solamente sobre presentacion `ViewObject`, panel Qt e iconografia.

- Cada paso del guion declara ahora un archivo SVG en `core/demo_guided_core.py`. El dato sigue siendo JSON-compatible y no introduce dependencias de FreeCAD/Qt en el nucleo.
- El `QDockWidget` muestra un icono contextual de 44 px junto al titulo del paso. Se reutilizan iconos reales de las herramientas: piso, muros, centros de puertas/ventanas, recintos, cielorraso y techo.
- En pasos de fuente 2D, la demo modifica temporalmente solo la presentacion: puertas/ventanas muestran muros con 80% de transparencia y losa con 85%; recintos ocultan temporalmente muros y dejan la losa al 90% de transparencia; la huella de techo usa muros al 65%. Al cambiar de paso o cerrar el panel se restauran los valores originales.
- Se agrega `Cerrar demostracion`; detiene el `QTimer`, restaura la presentacion y cierra exclusivamente el panel. El documento generado permanece abierto.
- Se renuevan `demo_building.svg`, `roof_from_rectangle.svg`, `edit_truss_axes.svg`, `door_table.svg` y `window_table.svg` con una familia visual de alto contraste y color plano, manteniendo 64x64 y compatibilidad SVG.

Validacion previa: `py_compile` aprobado, 4/4 pruebas focales del nucleo/contrato visual aprobadas y 5/5 SVG validos y renderizables. Pendiente: smoke visual en FreeCAD 1.1.3 para confirmar transparencia, restauracion, iconos contextuales y boton Cerrar.


## Build 2026.09.01.3 - bienvenida, herramientas de recintos y feedback de procesos largos

- `FA Demo edificio` migra una sola vez su ejecucion predeterminada a `Demostracion guiada paso a paso`; despues respeta la preferencia explicita del usuario.
- Se agrego `FA Detectar recintos 2D` a `FA Recintos y cielos`, reutilizando `room_utils.create_closed_room_sketch`.
- Se agrego `FA Crear espacios BIM`, que reutiliza `core/space_utils.create_bim_spaces` y crea `Arch Space` nativos desde el Sketch documental de recintos. La demo usa exactamente el mismo servicio.
- La guia identifica la herramienta real de cada paso; Sketcher y Draft se presentan como herramientas nativas cuando corresponde.
- Se agrego una ventana `Facil Arquitectura - Primeros pasos`, no destructiva, con opcion `No volver a mostrar este mensaje`, Ayuda y Cerrar. Puede reabrirse desde `FA Primeros pasos`.
- Las operaciones potencialmente largas usan el texto comun `Este proceso puede tardar varios segundos o incluso algunos minutos...`, cursor de espera, barra de estado y mensajes por etapas. Puertas, ventanas, techo y la demo son los primeros comandos migrados.
- No se modifico GameEngineExportWB ni se agregaron propiedades especificas de exportacion a los Espacios BIM.
- La regla general de feedback de operaciones largas se incorporo a `AGENTS.md`; la adopcion en todos los Workbenches queda como migracion gradual, no como trabajo ya completado.


## Build 2026.09.01.4 - integracion de Espacios BIM con GameEngineExport

Los Espacios BIM creados por `FA Crear espacios BIM` y por `FA Demo edificio` conservan su geometria y propiedades BIM nativas dentro de FreeCAD, pero reciben el hint booleano `GameExportExclude=True`. La misma marca se aplica al `Part::Feature` Base oculto usado por `Arch.makeSpace()`.

GameEngineExportWB ya interpreta esa propiedad como una exclusion explicita de geometria, por lo que no fue necesario modificar ni importar el Workbench de exportacion. Esta integracion evita que el volumen del recinto o su Base auxiliar aparezcan como geometria exportable, sin eliminar la informacion de recinto del documento FreeCAD.

La integracion es deliberadamente liviana: Facil Arquitectura solo escribe una propiedad booleana en sus propios objetos; no depende del codigo de GameEngineExportWB.


## Build 2026.09.01.5 - correccion del paso 13 de techo

La prueba real con seed `123456789` detecto `name 'feedback' is not defined` al entrar al adaptador programatico del techo. La correccion mantiene `feedback` como argumento opcional y evita que Demo/MCP dependan de un feedback GUI interno. El calculo BIM del techo no cambia.


## Build 2026.09.01.6 - feedback visible y terreno/jardin

El paso de piso sigue usando `create_site_floor_from_sketches`, pero activa su terreno nativo y lo presenta como `Jardin - Demo`: superficie plana verde, margen de 2500 mm y recorte bajo el edificio. El `Arch Site` conserva ese objeto como Terrain, por lo que la demostracion ensena la jerarquia espacial y el terreno sin inventar un objeto BIM paralelo.

El panel guiado reserva 86 px para estado/aviso y mantiene los controles con reparto de ancho estable. Cuando el proximo paso es Puertas, Ventanas o Techo, se muestra antes de ejecutar `⏳ El siguiente proceso...`; al iniciar, el aviso se repinta y luego comienza el calculo.


## Build 2026.09.01.7 - color visible del jardin

Correccion visual de la Casa demo: `Arch.makeSite` puede ocultar la Base/Terrain y mostrar la Shape del propio Site. La demo aplica ahora el mismo verde al Terrain y al `Arch Site`, y reaplica el estilo despues del recompute final. No cambia geometria, margen, recorte ni jerarquia BIM del jardin.


## Normalizacion del arbol de la Demo - build 2026.09.01.11

La Demo se ajusta al mismo contrato que el flujo manual. No crea `FA_Project`. `Demo - Fuentes 2D y control` es la unica rama auxiliar especial y reside dentro del Level. Los Espacios BIM son miembros directos del Level y no se crea `FA_DemoSpaces`.

El cielo suspendido sigue calculando su reticula modular, pero la Demo llama el servicio con `create_documentary_grid=False`, por lo que no deja objetos `Reticula cielo - ...` en el arbol.

`Sitio BIM` ya no conserva enlaces de trazabilidad `PropertyLinkList` hacia los Sketches de planta; asi esos Sketches no aparecen como hijos adicionales del Site. La dependencia geometrica de la losa sigue documentada mediante la huella de piso.

La prueba pendiente en FreeCAD 1.1.3 debe comparar este resultado con una casa creada manualmente desde Sketches. Ambos flujos deben converger al mismo esquema `Site -> Building -> Level`, con diferencias unicamente en los auxiliares propios de la demostracion.


### Correccion recurrente de paneles - build 2026.09.02.2

La Demo guiada usa el dock estable `FA_DemoGuidedDock`. Un Hot restart puede conservar un `QDockWidget` de la carga anterior aunque el modulo Python pierda su referencia global. Para evitar que dos paneles compriman la vista 3D, el comando ahora busca todas las instancias por `objectName`, retira del layout los docks obsoletos durante `register()` y antes de abrir una nueva Demo, detiene sus timers y difiere solo la destruccion Qt. No modifica `Tasks`, otros docks nativos ni el `centralWidget` de FreeCAD.

La regresion debe verificarse con 10 ciclos Demo -> cerrar/Hot restart -> Demo manteniendo 0/1 `FA_DemoGuidedDock` y sin reduccion anomala de la vista 3D.
