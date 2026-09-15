## Demo Escalera minima 0.10.6 - abertura paramétrica del cielo suspendido

Fecha: 2026-09-15 15:20 America/Costa_Rica  
Build: `0.14.12 / 2026.09.15.6`  
Demo core: `0.9.4`  
Cielorrasos: `0.7.3`

La prueba de la build `.5` confirmo que el master ya es editable y que el buque Arch de la losa superior sigue `Stairs.Placement`. El defecto restante estaba en el cielo: `create_modular_ceilings()` recortaba las zonas de exclusion directamente dentro de la Shape de paneles durante la creacion, por lo que la abertura quedaba congelada en coordenadas mundo.

Exclusivamente para `Demo Escalera minima`, el generador de cielorraso conserva ahora una Base completa y fija y materializa la abertura mediante un `Part::Cut`. Su herramienta oculta `FA_CeilingDynamicOpening` se construye en el marco local inicial de la escalera y su Placement sigue por expresion a `FA Escalera entre losas`. De esta forma la escalera mueve el buque del cielo sin trasladar el resto del cielorraso. El modo normal de cielorrasos continua usando el recorte estatico durante generacion.

El master no mantiene un PropertyLink inverso al cielo dinamico, porque eso produciria el ciclo `Stairs -> CeilingCut -> Cutter -> Stairs`; en esta Demo conserva los Names JSON y el diagnostico los reconoce.

Validacion fuera de FreeCAD: `py_compile` y contrato puro aprobados. El smoke requerido es mover y girar la escalera y confirmar que buque de losa + buque de cielorraso siguen juntos, manteniendo fijo el cielo general.

---

## Demo Escalera minima 0.10.5 - la escalera es la autoridad de Placement

Fecha: 2026-09-15 15:05 America/Costa_Rica  
Build: `0.14.12 / 2026.09.15.5`  
Demo core: `0.9.3`  
Adaptador escalera: `0.6.4`

La prueba real de la build `.4` confirmo que las bases ya son objetos Draft Line/Wire y que existe un buque Arch nativo, pero revelo que mover la escalera no era posible: el siguiente recompute restauraba el `Placement` del Wire fuente. El problema era contractual, no geometrico: la expresion del master convertia el Wire oculto en autoridad.

En 0.10.5, exclusivamente para `Demo Escalera minima`, el master `FA Escalera entre losas` recibe el Placement inicial del Wire y despues queda libre para edicion directa. El Wire conserva la geometria local de dos segmentos como referencia inicial; no gobierna la posicion. El cutter de `Subtractions` se construye en el mismo marco local y sigue el `Placement` del master. El PLAN 2D principal tambien sigue al master.

Como un cutter que depende del master formaria un ciclo si el master mantuviera PropertyLinks de vuelta hacia Level/losa/cutter, este modo de prueba conserva esos identificadores mediante nombres estables. El flujo normal de `FA Escalera entre losas` y Casa demo 2 pisos no cambia. El diagnostico puro se amplio para reconocer estos nombres y seguir validando Levels y Subtractions.

Validacion fuera de FreeCAD: `py_compile` aprobado y spec minimo JSON-compatible. La siguiente prueba debe mover y girar el master, recomputar y comprobar que escalera + buque + PLAN 2D permanecen juntos. Las barandas nativas se verifican aparte en runtime por su comportamiento particular en FreeCAD 1.1.3.

---

## Demo Escalera minima 0.10.3 - contrato explicito de cielorraso

Fecha: 2026-09-15 14:12 America/Costa_Rica  
Build: `0.14.12 / 2026.09.15.3`  
Demo core: `0.9.1`

El smoke de 0.10.2 confirmo que la ruta canonica de `create_bim_spaces()` ya crea correctamente el Space auxiliar. La ejecucion fallo despues en `_ceiling_options()` porque el spec de Demo Escalera minima no incluia `ceiling`.

La correccion se hace en el nucleo declarativo, no mediante un fallback del comando: `build_minimal_stair_demo_spec()` conserva para Nivel 00 la misma seccion de cielorraso de la Casa 2 pisos (600 mm, cota 2700 mm, panel 15 mm, junta 5 mm, tolerancia 50 mm) y activa `apply_ceiling_exclusion=True`. El cielorraso inferior pasa asi a formar parte explicita del contrato reproducible de la demo minima.

Se conserva `create_opening_liner=False`: este ejemplo todavia no crea tapichel. Nivel 01 mantiene solo su losa; no se agregan los demas componentes de la casa. Las barandas siguen siendo las nativas de FreeCAD y el comando las hace visibles al final.

Validacion fuera de FreeCAD: `py_compile` aprobado y spec minimo JSON-compatible con cielorraso solo en Nivel 00 y exclusion de escalera activa. Smoke real build `.3` pendiente.

---

## Demo Escalera minima 0.10.2 - correccion del Space auxiliar de cielorraso

Fecha: 2026-09-15 13:35 America/Costa_Rica  
Build: `0.14.12 / 2026.09.15.2`

El primer smoke del cielorraso en la Demo Escalera minima confirmo la escalera, el hueco nativo de losa y el calculo `l_union_v2`, pero se detuvo al crear el Space auxiliar: el registro construido por la Demo no llevaba `polygon_mm`, requerido por `space_utils._face_from_record()`.

La version 0.10.2 elimina ese registro manual. `create_bim_spaces()` reconstruye ahora su propio registro JSON-compatible desde el Sketch cerrado auxiliar, usando la misma ruta de produccion empleada por FA Espacios BIM. El Space y su Base permanecen ocultos y solo sirven de soporte para reutilizar `create_modular_ceilings()`.

La Demo mantiene `include_ceiling=True`, aplica la exclusion de la escalera al cielorraso de Nivel 00 y, al finalizar, muestra las barandas nativas ya creadas por FreeCAD. No crea tapichel y no cambia la Casa demo 2 pisos. `py_compile` aprobado; smoke real build `.2` pendiente.

---

## Demo 0.9.2 - correccion runtime del tapichel y DAG

Fecha: 2026-09-14 17:11 America/Costa_Rica  
Build: `0.14.11 / 2026.09.14.5`

El primer smoke de Demo 0.9.1 llego correctamente a la escalera, el buque nativo de losa y la exclusion del cielorraso, pero fallo al crear el tapichel porque el orquestador usaba dos nombres de argumento distintos a la firma canonica. Demo 0.9.2 corrige la llamada a `create_stair_opening_liner()` usando `plane_id="lower_ceiling"` y `level=ground.level`.

Ademas, la escalera que conecta dos pisos se aloja ahora directamente en el Building comun. Esto permite conservar los enlaces `FA_LowerLevel` y `FA_UpperLevel` sin crear el ciclo de dependencia que aparecia cuando el master estaba contenido dentro del mismo Level inferior. Las bases y representaciones PLAN permanecen en el Level correspondiente.

El generador de cielorraso 0.7.1 tambien interrumpe el bucle de exclusiones cuando un panel queda completamente eliminado; ya no intenta aplicar un segundo boolean sobre una `Null shape`.

La proxima ejecucion debe completar la Demo, crear el tapichel, no emitir warnings DAG ni Null shape y terminar mostrando el diagnostico automatico.

---

## Demo 0.9.1 - tapichel perimetral del buque

Fecha: 2026-09-14 16:41 America/Costa_Rica  
Build: `0.14.11 / 2026.09.14.4`

La Demo de dos pisos agrega un remate vertical alrededor del buque de escalera para ocultar el plenum del cielorraso. `create_stair_opening_liner()` usa la misma exclusion `lower_ceiling` calculada por altura libre, construye el tapichel desde la cara inferior del cielorraso hasta la cara inferior de la losa superior y lo hace crecer hacia afuera del paso. Espesor nominal Demo: **100 mm**.

El tapichel se crea despues del cielorraso, dentro de la transaccion multinivel, se aloja en Nivel 00 y queda enlazado a la escalera. No sustituye el hueco Arch de la losa ni la exclusion de paneles. La ubicacion/giro de la escalera y la simplificacion final del contorno del buque siguen pendientes de una iteracion visual posterior.

---

# Actualizacion 2026-09-14 15:40 America/Costa_Rica - Demo 0.9.0 / buque real de escalera

La casa fija de dos pisos deja de usar solamente previews de holgura. El flujo nuevo conserva la escalera `Arch.makeStairs()` y aplica dos salidas derivadas de la misma envolvente de altura libre:

- **Losa Nivel 01:** volumen auxiliar oculto registrado en `Structure001.Subtractions` mediante la API Arch Remove; la losa original permanece parametrica y el corte es reversible.
- **Cielorraso Nivel 00:** el generador 600x600 recibe las zonas XY antes de crear paneles y recorta los paneles que intersectan el paso.
- **Documentacion:** permanecen `PLAN - Hueco losa escalera` y `PLAN - Exclusion cielorraso escalera`.

Orden especial de la Demo de dos pisos: Nivel 00 hasta Spaces -> Nivel 01 hasta muros/losa -> escalera + buque -> cielorraso Nivel 00 con exclusion -> resto de Nivel 01 -> diagnostico automatico.

La build preparada es `2026.09.14.3`. Requiere smoke en FreeCAD 1.1.3 antes de considerarse validada.

---

## Demo 0.8.2 - escalera reubicada y preview de altura libre

Fecha: 2026-09-09 20:20 America/Costa_Rica  
Build: `0.14.11 / 2026.09.09.7`

La casa de dos pisos mueve la escalera canonica lejos de la fachada frontal y calcula dos zonas de holgura: una para la cara inferior de la losa superior y otra para la cara inferior del cielorraso de Nivel 00. Se muestran como PLAN 2D de **PREVIEW**. No se aplican aun cortes reales; el objetivo de esta build es validar visualmente la ubicacion y la geometria derivada antes de modificar losa/cielo.

Recorrido: `P0=(5200,4200)`, `P1=(5200,1900)`, `P2=(2700,1900) mm`. Altura libre de calculo: 2100 mm, configurable. El preview de cielorraso comienza antes que el de losa porque su plano esta mas bajo.

---

## Demo 0.8.1 - diagnostico automatico y entrega de reporte

Fecha: 2026-09-09 16:25 America/Costa_Rica
Build: `0.14.11 / 2026.09.09.6`

Al finalizar una generacion satisfactoria, `FA Demo edificio` ejecuta el mismo motor de `FA Informe diagnostico` sobre **todo el documento**, pasando una seleccion vacia explicita para que la seleccion residual de FreeCAD no cambie el alcance. El informe MD/JSON/TXT se escribe en `_reportes_diagnostico` bajo el MacroDir configurado.

El cuadro final de la Demo es ahora el dialogo reutilizable del diagnostico. Muestra conteos y alcance, y ofrece `Copiar ruta del MD`, `Abrir carpeta` y `Cerrar`. La ruta no se copia automaticamente. La Demo guiada usa el mismo mecanismo al completar su ultimo paso. Si el informe falla, la Demo ya creada se conserva y se informa el fallo por separado.

El comando manual `FA Informe diagnostico` tambien protege contra selecciones residuales: cuando existe una seleccion pregunta si el usuario desea `Documento completo` o `Solo seleccion`; ya no interpreta silenciosamente un objeto seleccionado como alcance intencional.

---

# Actualizacion 2026-09-09 15:25 - Demo 0.8.0 / escalera canonica

La casa fija de dos pisos incorpora ahora **una unica escalera canonica** mediante la misma herramienta reutilizable de produccion: `fa_stair_core.plan_angled_stair()` -> `stair_freecad_adapter.build_stair_context()` -> `stair_freecad_adapter.create_native_stair()` -> `Arch.makeStairs()`. La Demo solo aporta el recorrido fuente reproducible; no genera una geometria de escalera paralela.

Recorrido fijo: `(5200,500) -> (5200,2800) -> (2700,2800)` mm, ancho 1000 mm, objetivo de contrahuella 175 mm. El plan puro produce 17 contrahuellas (8+9), 176.47 mm y giro 90 deg.

Para FreeCAD 1.1.3 las barandillas que `Arch.makeStairs()` crea para la escalera multisegmento se mantienen como objetos nativos pero se dejan ocultas en esta fase, debido al comportamiento defectuoso observado en la prueba real anterior. No se implementan barandillas FA sustitutas. La losa superior todavia no se corta; esa abertura queda como fase siguiente tras validar la escalera base.

La prueba esperada de la Demo 0.8.0 es: una sola escalera, recorrido fuente no raiz, `FA_LowerLevel=Nivel 00`, `FA_UpperLevel=Nivel 01`, PLAN 2D presente y sin railings largos visibles.

---

## Demo de dos pisos v0.7.0 - Levels reales, planta superior distinta y cielos por nivel

Fecha: 2026-09-09 12:20 America/Costa_Rica
Workbench: Facil Arquitectura 0.14.11
Build: 2026.09.09.1
Comando: `FA_DemoBuilding` 0.7.0

La prueba real de la version 0.6.0 confirmo que la geometria de Nivel 01 alcanzaba Z=3000 mm, pero revelo tres defectos de contrato: el adaptador podia reutilizar el unico Level existente al solicitar `Nivel 01`; el segundo cielorraso reutilizaba nombres globales y podia eliminar objetos del Nivel 00; y la planta superior seguia pareciendose demasiado a la planta baja, incluyendo una puerta exterior.

Correcciones 0.7.0:

- `ensure_bim_structure()` agrega `create_level_if_label_missing=False`; el valor predeterminado conserva el flujo historico, mientras la demo multinivel exige un Level nuevo si no existe una coincidencia exacta.
- La demo verifica antes de aberturas que `Nivel 00` y `Nivel 01` sean dos objetos `Building Storey` distintos dentro del mismo Building.
- `ceiling_utils.create_modular_ceilings()` acepta nombres opcionales de grupo y Spreadsheet. La demo usa namespaces `Nivel00` y `Nivel01` y no elimina cielos del otro piso.
- Nivel 01 deja de ser una copia: dos tabiques en T producen tres recintos (`Distribuidor y futura escalera`, `Dormitorio principal`, `Dormitorio secundario`), dos puertas exclusivamente interiores y cinco ventanas diferentes.
- Se conserva una zona declarada para futura escalera BIM nativa; no se crea una escalera FA paralela.
- `GeneratedObjects` filtra adicionalmente referencias que ya no pertenezcan al documento.
- Se incrementa el build general a `2026.09.09.1`, reutilizando el aviso de cambio de build que ya existe en `InitGui.py`.

Validacion previa fuera de FreeCAD: `py_compile` aprobado; 7/7 pruebas del nucleo demo, 8/8 de estructura BIM, 8/8 de cielorrasos y 2/2 contratos focales multinivel aprobados. Pendiente smoke real en FreeCAD 1.1.3.

---

# FA Demo edificio automatico

Fecha: 2026-09-02 America/Costa_Rica

## Ampliacion: casa fija de dos pisos - 2026-09-08

Se agrega una tercera opcion al comando `FA Demo edificio`: `Casa fija 2 pisos 6 x 8 m`. El ejemplo de una planta y el modo aleatorio se conservan sin cambios.

Contrato de la nueva demo:

- un unico Building BIM nativo;
- `Nivel 00` a 0 mm y `Nivel 01` a 3000 mm;
- huella 6000 x 8000 mm en ambos niveles;
- losa inferior y losa de entrepiso; la segunda losa reutiliza `create_site_floor_from_sketches(..., create_site=False)` para no crear un segundo Site;
- muros, puertas, ventanas, recintos, Spaces BIM y cielorraso se materializan en cada Level reutilizando los servicios vigentes;
- el segundo nivel usa una posicion distinta del tabique interior para que no sea una simple copia geometrica;
- el techo se crea unicamente en `Nivel 01`;
- la especificacion completa se guarda en el controlador `FA_DemoBuilding` y enlaza ambos Levels;
- la demo guiada de 14 pasos permanece limitada por ahora a los modos de una planta; la opcion de dos pisos usa generacion completa inmediata.

La escalera se declara como requisito de integracion nativa, pero no se crea una geometria FA paralela. Debe incorporarse solo despues de verificar en FreeCAD 1.1.3 la API/comando BIM nativo apropiado y su relacion correcta con ambos Levels.

Validacion previa: `py_compile` aprobado para los modulos modificados, 7/7 pruebas focales del nucleo de demo aprobadas y prueba contractual nueva del orquestador multinivel aprobada. Queda pendiente smoke real en FreeCAD 1.1.3 para confirmar cotas globales, arbol BIM, hosts de aberturas, losa de entrepiso, techo, guardar/reabrir y no regresion del demo de una planta. No se incrementa `BUILD_ID` general hasta esa validacion.

---
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


## Correccion smoke real 2026-09-08 - puerta interior Nivel 01

La primera ejecucion real del modo `Casa fija 2 pisos 6 x 8 m` en FreeCAD 1.1.3 completo el Nivel 00 y avanzo el Nivel 01 hasta la creacion de puertas. `Door 02` fue rechazada con `no hay muro compatible dentro de 300.0 mm`.

Causa confirmada: el tabique del Nivel 01 se habia desplazado de Y=5200 mm a Y=4000 mm para diferenciar la distribucion superior, pero la `Puerta interior` conservaba la coordenada heredada Y=5200 mm de la casa canonica de una planta. El resolver de hosts funciono correctamente al rechazarla.

Correccion: `build_two_storey_demo_spec()` conserva ancho y centro X de la puerta interior y mueve sus dos extremos a la misma coordenada Y del tabique superior. Se agrega prueba de regresion que exige coincidencia exacta entre la coordenada Y de la puerta interior y la del muro anfitrion del Nivel 01.

Validacion local del nucleo: 7/7 pruebas aprobadas y `py_compile` aprobado. Queda pendiente repetir el smoke completo en FreeCAD 1.1.3. Los `ReferenceError` de `ArchWindow.py` observados despues del rechazo aparecieron durante el aborto/limpieza del documento parcial y se consideran consecuencia del fallo, no su causa primaria.


## Correccion smoke multinivel - Nivel 01 y aviso previo - 2026-09-08

La segunda prueba real detecto que el arbol podia contener `Nivel 00` y `Nivel 01` pero la geometria del nivel superior quedaba superpuesta en Z=0. La causa no era la especificacion de planta sino el momento en que se asignaba la elevacion al `Arch BuildingPart`.

`ArchBuildingPart` desplaza los hijos que ya existen cuando cambia su `Placement`. La primera implementacion creaba `Nivel 01` directamente con `Placement.Z = 3000 mm` y luego agregaba los objetos, por lo que esos hijos nuevos permanecian en coordenadas globales de planta baja.

Correccion:
- `Nivel 01` se crea temporalmente en Z=0.
- se materializan losa, muros, puertas, ventanas, recintos, Espacios BIM, cielorraso y techo usando las mismas herramientas FA;
- al finalizar el nivel, se actualiza el `Placement` del Level a +3000 mm mediante `ensure_bim_structure(...)`;
- se fuerza `LevelOffset = 0` porque la autoridad geometrica es `Placement.Z`;
- se valida que los muros del nivel queden aproximadamente en Z=3000 mm.

Ademas, antes de cualquier generacion completa se muestra un `QMessageBox` modal indicando que el proceso puede tardar varios segundos o algunos minutos y que FreeCAD puede permanecer ocupado durante los recomputes. La Vista de reportes conserva el feedback detallado existente.

Estado: sintaxis y contrato estatico aprobados. Falta repetir el smoke real en FreeCAD 1.1.3.

---

## Demo Escalera minima - origen local, bases Draft y buque solidario - 2026-09-15

A partir del build `2026.09.15.4`, solo el modo `Demo Escalera minima` activa un marco local editable para la escalera. El primer punto del recorrido es `(0,0,0)` local y el Draft Wire fuente lleva en su `Placement` la posicion real del arranque. Ese Wire es la autoridad de posicion del ejemplo.

Las tres bases que consume `Arch.makeStairs()` dejan de ser `Part::Feature` genericos en este modo: los tramos son Draft Line y el descanso es Draft Wire. El adaptador mantiene la implementacion anterior como predeterminada para no alterar ni la Casa demo 2 pisos ni el comando normal de escalera.

El volumen `FA_StairSlabOpeningVolume` se calcula en el mismo marco local y su Placement referencia el recorrido. De esta forma la sustraccion Arch de la losa puede seguir traslaciones/rotaciones del recorrido aun cuando FreeCAD 1.1.3 no propaga de forma general el movimiento entre objetos BIM y sus adiciones/sustracciones.

Pendiente de prueba real: generar la demo, revisar el origen visual, confirmar tipos Draft de las bases y transformar el recorrido verificando escalera + buque + PLAN 2D. El cielorraso conserva por ahora su exclusion calculada al generar; esta tarea no extiende aun la actualizacion dinamica de paneles despues de mover la escalera.

---

## Demo Escalera minima - tapichel dinamico - build 2026.09.15.7

Nota de continuidad: el texto historico de build `.4` describia el Draft Wire como autoridad de posicion. Ese contrato fue refinado posteriormente: desde build `.5` la autoridad editable es `FA Escalera entre losas.Placement`; el Wire conserva solo el marco local inicial. Desde build `.6`, los buques de losa y cielorraso siguen al master.

La build `.7` incorpora tambien el tapichel lateral usado por Casa demo 2 pisos. Se mantiene la misma geometria `side_walls_open_ends`: el cierre ocupa solo los bordes laterales del hueco entre cielorraso y cara inferior de la losa, deja libres la entrada y la salida de la escalera y no invade la envolvente de altura libre.

Para el ejemplo minimo, `create_stair_opening_liner()` trabaja opcionalmente en coordenadas locales y su Placement sigue al master. El enlace inverso se sustituye por `FA_OpeningLinerName` para evitar ciclos DAG. La exclusion dinamica del cielorraso incluye la banda exterior correspondiente al espesor del tapichel y su junta, de forma que los paneles terminan contra la cara exterior del cierre.

La Casa demo 2 pisos conserva la llamada historica y no cambia su comportamiento. Pendiente verificar en FreeCAD 1.1.3 que, al trasladar o girar la escalera, se muevan conjuntamente el buque de losa, el buque de cielorraso y el tapichel.
