# Build 2026.09.02.8 - cierre pre-RELEASE y Addon autosuficiente

Version: `0.14.11`  
FreeCAD objetivo: `1.1.3`  
Estado: preparado en Drive; smoke de instalacion limpia pendiente.

Facil Arquitectura deja de depender obligatoriamente de una instalacion externa de `CRBIMCore`. `InitGui.py` conserva `CRBIMCore` como fuente preferente durante desarrollo y, si el paquete externo no existe, carga `FacilArquitecturaWB._bundled.CRBIMCore.commands.common_rooms`. La copia `_bundled/CRBIMCore` es un espejo de distribucion generado desde la fuente neutral `Macros-de-Freecad/CRBIMCore`; no debe editarse manualmente ni convertirse en una segunda fuente de verdad. `tools/sync_bundled_crbimcore.py` realiza la sincronizacion por lista blanca de runtime y permite `--dry-run`, `--check` y salida JSON con hashes SHA-256.

El espejo incluido contiene solo el runtime requerido por FA para los comandos comunes de Recintos/Espacios: `room_resolver_core.py`, `room_operations_core.py`, `freecad_room_adapter.py`, `freecad_room_operations.py`, `commands/common_rooms.py`, los `__init__.py` correspondientes y cuatro iconos `CRBIM_*`. No se incluyen pruebas, `__pycache__`, documentos de coordinacion ni artefactos DEV del componente neutral.

Contrato de RELEASE: antes de publicar, regenerar/verificar el espejo contra `CRBIMCore` fuente y ejecutar un smoke con un perfil limpio de FreeCAD 1.1.3 donde el unico Addon del proyecto instalado sea Facil Arquitectura. Deben registrarse y funcionar `CRBIM_SelectRoom`, `CRBIM_RoomInfo`, `CRBIM_NameRoom` y `CRBIM_RoomGuide` usando exclusivamente el fallback interno.

Se agregan `RELEASE_MANIFEST.md`, `RELEASE_CHECKLIST.md`, `.gitignore` y `LICENSE-Code`. `package.xml` se alinea con `0.14.11` y declara FreeCAD 1.1.3 como minimo de esta primera publicacion. Las URLs de repositorio/bugtracker se incorporaran cuando exista el repositorio RELEASE; no deben inventarse antes.

---

# Build 2026.09.02.7 - FA JSON visual y errores copiables

Se agrega `create_site_object` al contrato `facil-arquitectura.command` version 1. La primera implementacion admite exclusivamente `object_type=tree`, con `name` ASCII seguro, `placement` en milimetros y `geometry` (`height_mm`, `crown_diameter_mm`, `trunk_diameter_mm`). El adaptador crea/reutiliza un `App::Part` con tronco/copa 3D y un objeto `<name>_Plan` de circulo+cruz como representacion documental 2D; `GameExportExclude=True` se aplica al simbolo 2D. Los arboles quedan bajo el grupo `FA_SiteObjects`, integrado en `Site` cuando es posible.

Seguridad/idempotencia: `dry-run` distingue `CREATE` de `UPDATE`; solo se actualiza un `name` existente si `FA_GeneratedBy=FA_JSON` y `FA_Role=site_tree`. Un objeto ajeno con el mismo `name` produce error y no se modifica. La aplicacion usa transaccion FreeCAD por operacion.

El ejemplo integrado deja de ser un simple cambio de `Label`: genera tres arboles alrededor de la Demo 6x8. La pestaña Resultado incorpora `Copiar resultado/error`. Los errores de `Validar`, `Dry-run`, validacion previa a `Aplicar` y aplicacion se serializan como `facil-arquitectura.command-result` con `ok=false`, `stage`, `error.type` y `error.message`, de modo que pueden copiarse y pegarse directamente en el chat de prueba.

Investigacion previa: no se localizo en FreeCAD/BIM un objeto nativo especifico de arbol que convenga reutilizar para este ejemplo; se conserva la jerarquia BIM existente y se usan objetos genericos de FreeCAD bajo Site. En el proyecto no existia `create_site_object` ni una herramienta equivalente.

Pruebas previas a FreeCAD real: `tests/test_json_command_core.py` 6/6 y `py_compile` de los modulos JSON aprobados. Pendiente smoke en FreeCAD 1.1.3: Demo -> Ejemplo -> Validar -> Dry-run -> Aplicar; confirmar tres arboles visibles, grupo bajo Site, simbolos 2D, reejecucion UPDATE sin duplicados, Undo/Redo y Copiar resultado/error.

## Contrato RELEASE - FA JSON

`FA JSON` forma parte de la funcionalidad obligatoria de cualquier version publicable de Facil Arquitectura. No debe perderse durante el staging, limpieza del repositorio ni migracion futura de estructura del Addon.

Archivos funcionales minimos que deben permanecer en el arbol distribuido:

- `commands/cmd_json_inspector.py`
- `core/json_command_core.py`
- `core/json_snapshot_core.py`
- `resources/icons/json_inspector.svg`
- registro de `cmd_json_inspector` en `InitGui.py` y presencia del comando en `FA Proyecto BIM`

Las pruebas de desarrollo `tests/test_json_command_core.py` y `tests/test_json_snapshot_core.py` deben formar parte de la validacion previa a RELEASE, aunque la decision final sobre distribuir o no la carpeta `tests/` se tome durante el staging publico.

Antes de considerar una RELEASE valida, probar en un perfil limpio de FreeCAD 1.1.3 como minimo: abrir `FA JSON`; generar/copiar una Salida JSON; cargar `Ejemplo`; `Validar`; ejecutar `Dry-run`; aplicar tras confirmacion; comprobar que la reejecucion controlada no duplica objetos; verificar Undo/Redo y que errores/resultados puedan copiarse. La interfaz y mensajes principales deben estar cubiertos en espanol e ingles.

`package.xml` no enumera archivos individuales del Workbench: el Addon distribuye el arbol del repositorio. Por ello, la inclusion de `FA JSON` depende de conservar estos archivos en el staging publico. Antes de la primera RELEASE debe actualizarse tambien la metadata de `package.xml`, actualmente anterior a `0.14.11`, junto con el resto de la preparacion de publicacion.

# Build 2026.09.02.6 - FA JSON bidireccional

`FA JSON` incorpora una pestana `Entrada` para el flujo ChatGPT/MCP -> FreeCAD. El contrato de escritura es `facil-arquitectura.command` version 1 y es distinto del snapshot `facil-arquitectura.snapshot`. La interfaz ofrece `Pegar`, `Ejemplo`, `Validar`, `Dry-run` y `Aplicar`; `Aplicar` vuelve a ejecutar el dry-run y solicita confirmacion explicita antes de escribir.

Operaciones iniciales: `set_properties` (solo propiedades existentes y tipos controlados, con propiedades geometricas/pesadas bloqueadas), `apply_elements` para puertas/ventanas reutilizando `ElementDataCore`, y `create_demo` para crear una casa Demo desde una especificacion JSON completa. No se permite codigo Python embebido. Las modificaciones de propiedades y los adaptadores de elementos usan transacciones FreeCAD/Undo.

Arquitectura: `core/json_command_core.py` valida/normaliza sin importar FreeCAD/GUI/Qt; `commands/cmd_json_inspector.py` actua como adaptador FreeCAD y GUI. Se agrego `tests/test_json_command_core.py`; pruebas puras: 4/4 y `py_compile` aprobado. Falta smoke real en FreeCAD 1.1.3 para confirmar la interfaz y una escritura/Undo real.

# Transparencia de desarrollo asistido por IA - 2026-09-02

Facil Arquitectura ha sido desarrollada en gran parte mediante herramientas de inteligencia artificial, bajo direccion humana. Esta condicion debe informarse en `Ayuda -> Informacion` y en la documentacion publica. El codigo, la arquitectura y el comportamiento del Workbench requieren revision y validacion por programadores profesionales antes de considerarse aptos para entornos de produccion, uso critico o distribucion amplia.

La declaracion publica debe mantenerse como minimo en Espanol e Ingles, siguiendo la politica general de internacionalizacion del proyecto.

---

# Build 2026.09.02.5 - FA JSON junto a Demo

Version: `0.14.11`  
FreeCAD objetivo: `1.1.3`  
Estado: implementado en Drive/DEV; compilacion y contrato puro aprobados; smoke GUI real pendiente.

Se incorpora `FA_JSONInspector` como segundo boton de `FA Proyecto BIM`, inmediatamente despues de `FA_DemoBuilding` y antes de Ayuda. La herramienta es estrictamente read-only y no abre transacciones. `core/json_snapshot_core.py` define el envelope JSON determinista sin dependencias FreeCAD/FreeCADGui/Qt; `commands/cmd_json_inspector.py` adapta el documento activo.

El snapshot contiene datos del Workbench/documento, seleccion, jerarquia de objetos, propiedades simples, Placement y resumen de Shape sin serializar geometria pesada. Si existe `FA_DemoBuilding`, incorpora `SpecificationJSON`, `StepPlanJSON`, semilla, ejecucion/paso y sus enlaces. Para `windows` y `doors` reutiliza `extract_window_records()` / `extract_door_records()`, que ya normalizan mediante `ElementDataCore`. El dialogo permite actualizar, copiar y guardar `*.fa.json`.

Pruebas previas a FreeCAD real: `py_compile` aprobado para el nuevo nucleo/comando y archivos de integracion; contrato puro comprobado; se agrega `tests/test_json_snapshot_core.py`. La verificacion definitiva pendiente es recargar FA en FreeCAD 1.1.3, confirmar la barra `Demo edificio -> FA JSON -> Ayuda`, generar la Demo y abrir/copiar/guardar su snapshot JSON.

---

# Build 2026.09.02.3 - cierre de interfaz, ayuda e i18n

Version: `0.14.11`  
FreeCAD objetivo: `1.1.3`  
Estado: implementado en DEV; smoke GUI Espanol/Ingles pendiente.

Se conserva el orden de barras por flujo real de uso: `Proyecto BIM -> DWG/DXF y preparacion 2D -> Dibujo 2D -> Snaps -> Estructura BIM -> Aberturas BIM -> Recintos (Experimental) -> Techos y cielorrasos -> Auxiliares BIM`. Importacion CAD, cierre de buques y recuperacion de rotulos quedan juntos; el cielorraso pertenece al sistema de techos.

La Ayuda integrada se amplia con pestanas `Primeros pasos`, `DWG/DXF`, `Flujo de trabajo`, `Barras`, `Demo` e `Informacion`. El flujo de trabajo documentado es:

1. Importar DWG/DXF.
2. Seleccionar escala/unidad del dibujo original y solamente las capas requeridas.
3. Paredes: capa seleccionada -> `FA Centros desde seleccion`.
4. Ventanas: capa seleccionada -> `FA Centros de ventanas`.
5. Puertas: capa seleccionada -> `FA Centros de puertas`.
6. Revisar los Sketches y usar `FA Cerrar buques` solo sobre interrupciones identificadas como buques validos.
7. Crear paredes BIM y luego puertas/ventanas BIM alojadas en sus muros.
8. Crear/identificar Recintos y BIM Spaces.
9. Dibujar un rectangulo que cubra el perimetro de paredes y usar `FA Techo desde rectangulo`.
10. Crear cielorraso preferiblemente seleccionando BIM Spaces y usando `FA Cielo 600x600`.

`FA Cielo 600x600` tambien acepta recintos poligonales o rectangulares validos. Sin seleccion intenta localizar recintos disponibles y prioriza BIM Spaces. Permite definir modulo, cota inferior, espesor, junta y alineacion con luminarias; las luminarias ElectricCR pueden reservar celdas sin ser movidas. La reticula se calcula siempre, mientras su objeto 2D documental permanente es opcional.

`FA Recintos (Experimental)` sigue marcado como experimental porque la deteccion/generacion puede requerir revision manual. No obstante, BIM Space se considera esencial para la arquitectura transversal: es el objeto previsto para compartir identidad de recinto, nombre, area, nivel y geometria con ElectricCR, MEP y futuros Workbenches sin duplicar recintos.

Condiciones CAD documentadas: DXF directo; DWG mediante el convertidor externo configurado por FreeCAD, normalmente ODA File Converter, con conversion previa a DXF como alternativa. El flujo DWG/DXF no se declara universal: solo se ha probado con un conjunto limitado de ejemplos y puede requerir seleccion de capas, limpieza o correccion manual.

Alcance de producto: Facil Arquitectura no pretende sustituir a un arquitecto, dibujante especializado, modelador BIM ni las herramientas arquitectonicas/BIM nativas o complementarias de FreeCAD. Su finalidad es simplificar tareas repetitivas y producir rapidamente una base arquitectonica suficientemente organizada para continuar trabajo de ingenieria, en particular con ElectricCR, MEP y otros sistemas.

Se mantiene la base i18n Espanol/Ingles (`i18n.py` + fuente `.ts`) y se internacionalizan Ayuda, Primeros pasos y los flujos principales. Antes de RELEASE se requiere compilar/probar `.qm` y completar cualquier texto secundario restante.

---

# Barra comun Espacios y Recintos - 2026-09-02

Facil Arquitectura expone `CRBIM_SelectRoom`, `CRBIM_RoomInfo`,
`CRBIM_NameRoom` y `CRBIM_RoomGuide` desde la implementacion compartida de
`CRBIMCore`. En la misma barra conserva `FA_DetectRooms2D` y
`FA_CreateBIMSpaces`; estos productores siguen siendo responsabilidad
arquitectonica de FA.

La barra fue verificada visualmente y su segunda carga no duplica comandos ni
acciones. Space conserva prioridad sobre Area legacy; AMBIGUOUS y NOT_FOUND no
aplican cambios. Esta integracion no cambia version/build de FA, que permanece
en `0.14.11 / 2026.09.01.14`.

---

# CRBIMCore 0.1.0 - RoomResolver comun fase 1 read-only

FreeCAD validado: `1.1.3`, revision `20260725`.

La identidad persistente de Espacios BIM de Facil Arquitectura queda disponible para futuros consumidores mediante un componente neutral de raiz, `CRBIMCore`. FacilArquitecturaWB no importa ElectricCR ni MEPWorkbenchCR, y estos Workbenches tampoco fueron modificados en esta fase.

`CRBIMCore.room_resolver_core` define el contrato JSON-compatible y la prioridad `NATIVE_SPACE > LEGACY_AREA > NOT_FOUND`. `CRBIMCore.freecad_room_adapter` traduce objetos existentes sin escribir propiedades: reconoce un `Arch Space` por `IfcType=Space`, `Proxy.Type=Space` o TypeId nativo, aunque no tenga metadatos FA.

Las Areas heredadas son fallback temporal cuando poseen geometria valida y evidencia como `ElectricCRTipo=Area`, generador conocido o rol de recinto. El nombre de un grupo no basta. Dos Spaces plausibles devuelven `AMBIGUOUS`; no se usa una regla de menor area.

`HVACSpace.BaseSpace` se sigue hasta el Space/Area fisica. Un HVAC convertido sin `BaseSpace` y una `SubArea` no se promueven a recinto arquitectonico.

La fase 1 no agrega botones ni comandos y no cambia `space_utils.py`. El smoke real comprobo firma documental identica antes/despues, persistencia al guardar/reabrir y ausencia de regresion en la sincronizacion FA. La documentacion canonica completa esta en `CRBIMCore/README.md`.

---

# Build 2026.09.01.14 - identidad persistente de Espacios BIM

Version: `0.14.11`
FreeCAD validado: `1.1.3`, revision `20260725`
Estado: smoke integral MCP aprobado.

`FA Detectar recintos 2D` y `FA Crear espacios BIM` forman un flujo no destructivo. El Sketch documental de recintos se actualiza en sitio cuando existe un unico resultado FA anterior, de modo que los `PropertyLink` hacia ese Sketch no se pierden. Ambos comandos usan `ReloadableCommandProxy`, necesario para que una recarga DEV de FreeCAD 1.1.3 resuelva la implementacion vigente aunque la API no disponga de `removeCommand`.

`core/space_utils.py` usa el siguiente contrato:

- `MATCH`: conserva el Space sin cambio geometrico.
- `CAMBIO`: actualiza en sitio el mismo Space y la misma Base.
- `NO_MATCH`: crea unicamente un Space nuevo.
- `AMBIGUO`: no aplica cambios automaticos.
- `stale`: reporta y conserva el Space; nunca lo borra durante la sincronizacion normal.

La identidad persistente se apoya en `FA_RoomUID`, mientras `FA_RoomID` sigue siendo un identificador documental legible. Un match seguro conserva `Name`, `FA_RoomID`, `FA_RoomUID`, Base, contencion BIM y enlaces externos. La autoridad geometrica sigue siendo el Sketch actual; el Space es el recinto BIM nativo autoritativo.

La recoleccion de Spaces existentes acepta objetos FA del mismo Sketch fuente con `FA_SpaceSchemaVersion` valido, aunque hayan sido materializados por la demo. Esto permite que `FA_DemoBuilding` y el comando interactivo compartan el mismo servicio sin crear familias duplicadas. No se consideran candidatos los Spaces Arch ajenos que carezcan del esquema/rol FA.

Validacion final: tres Spaces iniciales, un cambio conservando identidad, alta unica de un cuarto recinto, tres stale preservados, rechazo de un caso ambiguo, Undo/Redo y guardar-cerrar-reabrir con `PropertyLink` y `GameExportExclude` intactos. La demo permanecio con `Space` y `Space001` despues de resincronizar, con nuevos `0`.

`RoomResolver` no forma parte de esta build y no debe inferirse como implementado.

---

# ACTUALIZACION - Detectar recintos ignora selecciones irrelevantes

Fecha: 2026-09-01 America/Costa_Rica
Version/build vigente: `0.14.11 / 2026.09.01.13`
Estado: **CORRECCION IMPLEMENTADA / PRUEBA LOCAL APROBADA / SMOKE FREECAD 1.1.3 EN CURSO**.

Durante el smoke real sobre la demo aleatoria `FA_Demo_Casa_123456`, `FA Detectar recintos 2D` no encontro fuentes aunque la demo contiene Sketches de muros y aberturas. La causa fue el alcance de seleccion: cualquier objeto seleccionado se trataba como alcance explicito, incluso si no contenia Sketches de planta.

`commands/cmd_detect_rooms_2d.py` conserva prioridad para una seleccion realmente util, pero cuando esa seleccion produce cero fuentes reintenta automaticamente sobre el documento completo. La correccion no cambia la deteccion geometrica, `room_utils` ni el matching persistente de Spaces; solo evita que una seleccion accidental de un resultado BIM bloquee el flujo.

Prueba local focal: `1 passed`; compilacion Python aprobada. El smoke debe repetirse desde `FA Detectar recintos 2D` y continuar luego con la comprobacion de identidad persistente de `Arch Space`.

---

# ACTUALIZACION - Espacios BIM con identidad persistente

Fecha: 2026-09-01 America/Costa_Rica
Version/build vigente: `0.14.11 / 2026.09.01.12`
Estado: **IMPLEMENTADO EN DRIVE / 4 PRUEBAS FOCALES LOCALES APROBADAS / SMOKE FREECAD 1.1.3 PENDIENTE**.

`FA Crear espacios BIM` deja de borrar y recrear todos los `Arch Space` al actualizar recintos. `core/space_utils.py` incorpora planificacion no destructiva con estados `MATCH`, `CAMBIO`, `NO_MATCH` y `AMBIGUO`; un Space reconocido conserva su `Name`, `FA_RoomID`, `FA_RoomUID`, Base y enlaces externos, mientras su geometria y propiedades se actualizan en sitio. Los casos nuevos crean Space nuevo; los ambiguos no se modifican automaticamente y los Spaces antiguos no reconocidos se reportan como `stale` sin borrarse.

El servicio agrega `dry_run`, `FA_RoomUID`, `FA_SpaceSchemaVersion=3`, `FA_SpaceMatchStatus` y `FA_SpaceMatchScore`. El matching usa superposicion geometrica/IoU, relacion de area y distancia de centroide; el ID secuencial `R01/R02/...` se considera provisional frente a la identidad persistente de un Space existente. La GUI ahora habla de **actualizar** Espacios existentes sin cambiar su identidad, no de reemplazarlos.

Esta build no migra todavia ElectricCR, HVAC ni MEPWorkbenchCR. La validacion real pendiente debe comprobar `PropertyLink`, Undo/Redo, guardado/reapertura, alta de un recinto nuevo y comportamiento ambiguo antes de cerrar la etapa.

---

# ACTUALIZACION - Herramientas nativas y exclusion de Espacios en GameEngineExport

Fecha: 2026-09-01 America/Costa_Rica
Version/build vigente: `0.14.11 / 2026.09.01.11`
Estado: **IMPLEMENTADO EN DEV / PRUEBAS FOCALES LOCALES APROBADAS / SMOKE FREECAD 1.1.3 PENDIENTE**.

Cambios:

- `InitGui.py` incorpora barras compactas `FA Dibujo 2D`, `FA Snaps` y `FA Auxiliares BIM` reutilizando solamente comandos nativos presentes en `FreeCADGui.listCommands()`.
- Para Sketch se prioriza `BIM_Sketch`; si no esta registrado se usa `Sketcher_NewSketch` como fallback.
- El registro historico existente cubre tambien estas acciones nativas porque sus ids empiezan por `Draft_`, `BIM_`, `Arch_` o `Sketcher_`.
- `core/space_utils.py` incorpora `migrate_game_export_exclusions(doc, dry_run=...)`, limitada a objetos generados por `FA_CreateBIMSpaces`, para actualizar Espacios BIM heredados y sus bases con `GameExportExclude=True`.
- La migracion es idempotente, usa transaccion cuando hay cambios y no importa GameEngineExportWB.
- Pruebas focales locales: 2/2 para contrato de barras y migracion.

La correccion complementaria de GameEngineExportWB hace que `GameExportExclude=True` sea una exclusion dura incluso en listas explicitas/guardadas y en la barrera final de exportacion.

---

# CIERRE TEMPORAL - FA Puertas BIM / GeometryIndex 1

Fecha: 2026-08-31 America/Costa_Rica
Version/build vigente: `0.14.11 / 2026.08.31.4`
Estado: **CIERRE TEMPORAL CON LIMITACION CONOCIDA**.

La validacion manual del usuario sobre `FA_Geom1_Downstream` no acepto la posicion visual de GeometryIndex 1. Esto prevalece sobre la validacion MCP/captura previa: el caso **no se considera corregido**.

Se detiene deliberadamente la cadena de nuevas heuristicas. El build `.3` se conserva como baseline tecnico porque las pruebas focales y E2E aprobaron y no se observaron regresiones en los casos que funcionan. La excepcion de GeometryIndex 1 queda documentada como deuda tecnica localizada, no como bloqueo del Workbench.

Decision de arquitectura para el futuro: separar resolucion automatica segura de excepciones persistentes (`AUTO_OK`, `AUTO_AMBIGUOUS`, `MANUAL_OVERRIDE`) antes de intentar nuevas correcciones geometricas globales. No agregar otra tolerancia/score/caso especial al resolvedor solo por esta puerta.

### Baseline tecnica de cierre

La baseline de puertas `0.14.11 / 2026.08.31.3` se conserva funcional; el techo rectangular avanza en `2026.08.31.4`. Su cierre
tecnico aprobo 63/63 pruebas focales y un smoke en FreeCAD 1.1.3 que creo una
puerta Arch/BIM de 900 mm con host, subvolumen y corte real. El algoritmo no se
modifico durante el cierre y los respaldos `.2`/`.3` se conservaron.

Limitacion operativa: GeometryIndex 1 del levantamiento 1416 sigue sin satisfacer
la validacion visual manual. No debe presentarse como corregido. Hasta disponer de
un override persistente por elemento, esta excepcion requiere revision y ajuste
manual en una copia de trabajo. No se agregaran nuevas tolerancias o heuristicas
globales para este caso dentro de la baseline cerrada.

---

# Documentacion del Workbench Facil Arquitectura

Version candidata documentada: `0.14.11`
Build base documentado: `2026.08.31.4` (puertas/techo); build vigente general: `2026.09.02.6`
Estado 0.14.11: validado en FreeCAD real mediante MCP
FreeCAD objetivo: `1.1.3` (validado en las regresiones DWG, Compound, tablas y aberturas BIM)

## Puertas acotadas por dos jambas - estado BOUNDED

La posicion longitudinal y el ancho de una puerta provienen del Sketch. Cuando el
eje proyectado cabe completamente entre dos caras externas opuestas, con holgura
positiva, `FA Puertas BIM` no elige automaticamente la cara mas cercana: ambas son
geometricamente validas y esa eleccion trasladaria silenciosamente el buque.

En ese caso el resolvedor devuelve `FA_CornerStatus=BOUNDED`,
`FA_CornerSnapped=False` y conserva `FA_ProjectedFirst/Second`. La pared lateral
mejor puntuada aun puede resolver `FA_HingeEndpoint`, `FA_OpeningSide`,
`FA_OpensInward` y `Mode1/Mode2`; orientar y trasladar son decisiones separadas.

Esto no modifica:

- snaps unicos contra una sola cara externa;
- `NO_FIT`, que se evalua primero si una cara invade el ancho del eje;
- `JAMB_ONLY` y su proteccion de caras interiores;
- puertas dobles, Tabla de Puertas, Hosts ni cortes BIM.

La regresion real 1416 compara GeometryIndex 1 (`BOUNDED`, sin shift,
`START/RIGHT/Mode2`) con GeometryIndex 6 (`SNAPPED`, shift `-53.441 mm`,
`START/LEFT/Mode1`).

### Adaptacion del Base ArchWindow

En `Simple door`, `Wire0` representa el marco exterior y `Wire1` la hoja. Las
restricciones nativas `Frame2` y `Frame3` retraen `Wire1` normalmente 50 mm por
lado. Para una puerta `BOUNDED`, el segmento del Sketch representa la hoja
autoritativa y no existe un snap longitudinal que absorba ese marco.

El adaptador `bounded_leaf_authoritative` desplaza el origen exterior hacia atras
por `Frame2` y aumenta solamente la restriccion `Width` del Sketch Base en
`Frame2 + Frame3`. La propiedad publica `Window.Width`, `FA_Width_mm`,
`FA_ProjectedFirst/Second`, bisagra y apertura permanecen sin cambios. El marco y
el subvolumen de corte crecen alrededor de la hoja, no a costa de ella.

Trazabilidad adicional:

- `FA_BaseAlignmentMode = bounded_leaf_authoritative`;
- `FA_BaseOuterWidth_mm`;
- `FA_BaseFrameStart_mm`;
- `FA_BaseFrameEnd_mm`.

Las puertas `SNAPPED`, `JAMB_ONLY`, `NO_FIT`, ventanas y puertas dobles no pasan
por este adaptador.

## Importacion CAD determinista

`FA Importar referencia DWG/DXF` usa temporalmente el importador moderno en
modo de formas fusionadas, con textos, layouts, bloques y capas Draft activos.
No depende del modo global elegido en Preferencias. Al terminar restaura
exactamente todas las preferencias tocadas.

Los mensajes `[FACILARQ][IMPORT]` registran conversion, DXF temporal,
preferencias, importacion, recomputes, metadata, vista, limites, retornos,
QMessageBox y sondas del event loop.

Desde 0.14.4, `core/freecad_compat.py` contiene una compatibilidad temporal para
FreeCAD issue #31637. La deteccion inspecciona mediante AST o bytecode la
implementacion real de `importDXF._import_dxf_file()`. Solo el estado `affected`
neutraliza reversiblemente el par `suspendWaitCursor`/`resumeWaitCursor` durante
una insercion; `not_affected` usa FreeCAD normalmente y `unknown` no modifica las
funciones globales. La restauracion ocurre siempre en `finally`.

Mensajes esperados en FreeCAD 1.1.3:

```text
[FACILARQ][COMPAT] FreeCAD version: 1.1.3 | revision=... | build=...
[FACILARQ][COMPAT] DXF WaitCursor bug #31637: affected | ...
[FACILARQ][IMPORT] Workaround #31637 aplicado temporalmente
[FACILARQ][COMPAT] Workaround #31637 restaurado
```

En una version futura corregida debe aparecer
`FreeCAD DXF WaitCursor fix detected; workaround disabled`. Ese mensaje y la
prueba `test_fixed_importer_disables_workaround_and_inserts_normally` verifican
que FA no queda atado permanentemente a esta compatibilidad.

Para el levantamiento `1416 Levantamiento 250424` debe elegirse **Metros**:
la cabecera declara milimetros, pero la geometria esta expresada en metros.
`Pared_Concreto001` debe medir aproximadamente 10.788 x 23.530 m.

## 1. Proposito

`FacilArquitecturaWB` organiza un flujo reproducible para reconstruir una base BIM
editable desde planos existentes, principalmente DXF. Usa herramientas nativas de
FreeCAD, Draft, Arch y BIM; no define un formato BIM propio.

Sus responsabilidades son organizar el documento, extraer centros y espesores,
reconstruir paredes, crear objetos BIM, recopilar datos de recintos y mantener
trazabilidad entre el DXF, los Sketches y el modelo.

## 2. Estado de implementacion

### 2.1 Comandos nativos

El workbench conserva los comandos principales existentes; la version 0.14.0 corrige integracion espacial de varias herramientas sin retirar comandos. Los nombres anteriores
de muros, columnas, puertas y ventanas se conservan como aliases de compatibilidad:

| Comando interno | Funcion |
|---|---|
| `FA_ImportCADReference` | Importa DWG/DXF en un documento nuevo con unidad real controlada. |
| `FA_CreateBIMStructure` | Crea o reutiliza Building y Building Storey nativos. |
| `FA_RebuildBIMModel` | Clasifica Sketches y coordina la reconstruccion BIM nativa. |
| `FA_CreateProject` | Crea `FA_Project`, grupos y parametros. |
| `FA_CreateMasterSketches` | Crea Sketches editables por disciplina. |
| `FA_CenterlinesFromSelection` | Extrae centros genericos y espesores desde shapes, grupos y Compound sin explotar la fuente. |
| `FA_WindowCenterlinesFromSelection` | Obtiene un eje por simbolo de ventana. |
| `FA_DoorCenterlinesFromSelection` | Obtiene el eje cerrado de cada puerta. |
| `FA_CreateDoorsFromSketch` | Crea puertas Arch nativas, selecciona su host y valida el corte. |
| `FA_ChangeDoorType` | Cambia el preset nativo de puertas existentes conservando identidad, host y hueco. |
| `FA_CreateWindowsFromSketch` | Crea ventanas Arch nativas con altura y antepecho configurables. |
| `FA_WindowTable` | Administra `Spreadsheet_Ventanas`: plantilla, extraccion, validacion, transferencia y aplicacion sobre ventanas BIM nativas. |
| `FA_DoorTable` | Administra `Spreadsheet_Puertas`: tipos extensibles, puertas simples/dobles, bisagra, apertura, transferencia y aplicacion. |
| `FA_CreateOpeningsFromSketch` | Crea vanos `Opening Element` nativos, sin puerta ni ventana, desde lineas de Sketch. |
| `FA_InsertDoubleDoorBIM` | Inserta una puerta Arch/BIM Europa de dos hojas, libre o alojada en un muro. |
| `FA_CloseWallSketch` | Reconstruye centros sobre huecos justificados. |
| `FA_CreateSampleGeometry` | Agrega geometria de prueba. |
| `FA_CreateWallsFromSketch` | Crea muros Arch/BIM con Base Sketch directa. |
| `FA_CreateColumnsFromSketch` | Crea ejes, sistemas y columnas BIM dentro del Level. |
| `FA_CreateBuildingGrid` | Crea ArchGrid auxiliar dentro del Level. No genera ni sustituye muros BIM. |
| `FA_CreateSiteFloorBIM` | Crea Site/Building/Level, losa en el Level y terreno de prueba con recorte bajo la huella. |
| `FA_CollectRoomLabels` | Consolida nombres y datos de recintos. |
| `FA_CreateModularCeiling` | Crea cielo 600x600 dentro del Level, recorta contra el recinto y reserva luminarias ElectricCR. |
| `FA_CreateServicePlatformFront` | Crea una plataforma compacta desde una linea o un Sketch de una linea. |
| `FA_UpdateServicePlatformFront` | Relee la fuente y actualiza cuerpo y vidrios sin duplicar representaciones. |
| `FA_AddCashierServiceWindow` | Reserva el comando independiente para una futura ventanilla fija en muro BIM. |

La interfaz v0.13.1 conserva todos los comandos y mantiene cinco barras funcionales:
`FA Proyecto BIM`, `FA Estructura BIM`,
`FA Aberturas BIM`, `FA Recintos y cielos` y `FA Plataforma`. Los comandos de
muestra y la ventanilla futura quedan en el menu, no en las barras de uso diario.

### 2.1.1 ElementDataCore y Tabla de ventanas

`core/element_data_core.py` define el contrato independiente y JSON-compatible
para normalizar, serializar, validar y planificar datos de elementos. No importa
FreeCAD, FreeCADGui ni Qt. La primera categoria implementada es `Window`; el
contrato queda reutilizable sin crear un tipo BIM paralelo.

`core/window_table_utils.py` adapta ese contrato a ventanas nativas
`ArchWindow._Window`, Sketches de centros y `Spreadsheet::Sheet`. La hoja
canonica es `Spreadsheet_Ventanas`; se reutiliza si existe y contiene una fila
por instancia. Las columnas principales son identidad/firma geometrica,
`Height`, `SillHeight`, `Preset`, `Opening`, `Room`, `Level`, estado y notas;
tambien conserva `Frame`, `Offset`, `IfcType` y `SchemaVersion` cuando son
transferibles.

Autoridad aplicada:

- Sketch actual: centro, orientacion y ancho;
- tabla: altura, antepecho, preset y datos descriptivos transferibles;
- documento destino: muro anfitrion, Level, Placement y relaciones BIM.

El matching intenta primero `SourceSketch + GeometryIndex` y despues la firma
geometrica tolerante. Devuelve `MATCH`, `CAMBIO`, `NO_MATCH` o `AMBIGUO` y no
planifica escrituras ambiguas. `apply_records()` usa `dry_run=True` por defecto.
La interfaz muestra ese diagnostico antes de confirmar una aplicacion real.

Una ventana generada previamente por FA se conserva si no cambia. Si cambian
propiedades que exigen reconstruccion, se crea y valida primero la nueva ventana
nativa, incluyendo su `Base`, `Hosts` y corte del muro; solo despues se elimina
la anterior dentro de la misma transaccion. Una ventana manual en conflicto se
marca `AMBIGUO` y nunca se borra.

FreeCAD 1.1.3 no expone una propiedad nativa persistente `SillHeight` en
`ArchWindow._Window`: el antepecho real se representa por la cota Z del Sketch
`Base`. FA lee/escribe esa geometria y mantiene `FA_Sill_mm` como trazabilidad.
El nombre del preset es la referencia estable; el entero nativo es interno y
esta indexado desde uno.

La transferencia se comprobo tanto con `Document.copyObject(sheet, True)` como
con `Spreadsheet::Sheet.exportFile()`/`importFile()`. Este ultimo genera UTF-8
separado por tabuladores aunque la extension elegida sea `.csv`.

Prueba real MCP controlada: dos ventanas origen se extrajeron y aplicaron sobre
un Sketch destino reordenado. Los anchos finales provinieron del Sketch
(1100/1300 mm), mientras alturas (1250/1500 mm), antepechos (800/850 mm) y
preset provinieron de la tabla. Se validaron host nuevo, dry-run, reemplazo
seguro, reejecucion sin duplicados, Undo/Redo y guardar/cerrar/reabrir.

### 2.1.2 ElementDataCore y Tabla de puertas (0.14.8 candidata)

`ElementDataCore` incorpora la categoria `doors` sin dependencias GUI. `core/door_table_utils.py` es el adaptador FreeCAD y reutiliza `opening_utils.py`, `door_type_utils.py` y `double_door_bim.py`. `Spreadsheet_Puertas` y `Spreadsheet_Ventanas` quedan bajo `Level -> Auxiliares FA` cuando existe un Level BIM inequívoco; `FA_Project/06_Tables` se conserva solo como fallback legacy para documentos sin contexto BIM resoluble.

Autoridad de datos: Sketch destino para posicion/orientacion/ancho; tabla para altura, tipo, bisagra y apertura; documento destino para Host/Level. `DoorType` puede ser un nombre logico de usuario; `TypeRef` apunta al preset de puerta instalado o a una factory FA. Los presets instalados se descubren en `ArchWindowPresets`; la primera factory especial integrada es la puerta doble `architecture.door.double_leaf.glazed.europa`.

Campos de orientacion transferibles: `HingeEndpoint=START|END|BOTH|AUTO`, `OpeningSide=LEFT|RIGHT|IN|OUT|AUTO` y `OpensInward`. La API aplica dry-run primero y protege puertas manuales, `NO_MATCH` y `AMBIGUO`. La prueba MCP `tests/freecad_door_table_end_to_end.py` valido dos filas, dry-run, CREATE/KEEP/REPLACE, puerta doble, snap de marco, host/corte, Undo/Redo y guardar/reabrir. El lector de celdas normaliza ademas el apostrofo literal que `Spreadsheet::Sheet.getContents()` antepone a textos.

### 2.2 Macros historicas validadas

Estas funciones fueron validadas con el modelo de Puriscal y se conservan como
referencia o especializacion. Puertas y ventanas generales ya tienen comandos nativos:

| Macro | Resultado |
|---|---|
| `Xcluidos/Areas/AnalizarAreasRectangularesDesdeMurosBIM.FCMacro` | Lanzador historico archivado; el motor reusable activo es `core/rectangular_area_analysis.py`. |
| `InsertarPuertasBIMDesdeRecintos.FCMacro` | Puertas BIM orientadas hacia los recintos. |
| `AgregarPuertasFrentePuriscal.FCMacro` | Completa el frente con una puerta sencilla y un vano BIM de doble hoja, sin sustituir las puertas interiores. |
| `InsertarVentanasBIMDesdeRecintos.FCMacro` | Ventanas BIM alojadas en el muro. |
| `OrganizarPuriscalDepurado.FCMacro` | Organiza un modelo de un piso como IfcSite > IfcBuilding, sin Level, y crea la acera frontal. |

`InsertarPuertasBIMDesdeRecintos` y `InsertarVentanasBIMDesdeRecintos` aportaron la
geometria recuperada para `core/opening_utils.py`. Permanecen disponibles porque la
primera orienta puertas por recintos y la macro frontal conserva el caso doble
especifico de Puriscal. Los comandos generales no dependen de esas macros.

`RecopilarRotulosRecintos.FCMacro` es un lanzador compatible del comando nativo; no
mantiene una segunda implementacion.

### 2.3 Plataforma de atencion desde una linea

El flujo actual usa una arista recta o un `Sketcher::SketchObject` con exactamente
una linea no constructiva. Esa linea es autoritativa para P0, P1, longitud,
posicion, rotacion y cota. Se admite una linea horizontal, vertical o diagonal y un
Sketch con `Placement` trasladado/rotado; se rechazan curvas, Sketches ambiguos,
lineas menores de 500 mm y diferencias Z mayores de 1 mm.

El marco local usa X de P0 hacia P1 y una Y perpendicular. El usuario escoge el
lado del funcionario mirando de P0 a P1. `InvertirDireccion` intercambia los
extremos, mientras `LadoFuncionario` cambia de izquierda a derecha; son decisiones
independientes. La longitud no es un parametro libre: se relee de la fuente en cada
actualizacion. En este modo no se descuentan margenes ni divisiones; 3000 mm entre
tres puestos produce tres modulos exactos de 1000 mm.

El propietario semantico conserva propiedades editables y enlaces estables:

- `NumeroPuestos`, `AlturaMostrador`, `CotaSuperiorVidrio` y `ProfundidadEscritorio`;
- `MostrarAberturaVidrio`, `AnchoAberturaVidrio`, `AltoAberturaVidrio` y
  `AlturaAberturaVidrio`;
- `LadoFuncionario`, `InvertirDireccion` y `MostrarAreasAtencion`;
- `SourceObject`, `SourceSubelement` y `HostWall`, con aliases `FA_*`;
- `LongitudTotal`, derivada y de solo lectura.

La geometria opaca agrupa el panel inferior, mostrador, escritorios, divisiones y
parantes. Los paños se agrupan por separado con transparencia. El resultado visible
es deliberadamente compacto:

```text
Plataforma de atencion
|-- Cuerpo_Plataforma
`-- Vidrios_Plataforma
```

`Spreadsheet_Platform` se mantiene oculto y fuera del grupo como respaldo de
compatibilidad. Las zonas funcionales no se generan por defecto
(`MostrarAreasAtencion = false`); si se activan se crean como representacion
auxiliar oculta en el arbol. La plataforma entra en el `Building Storey` de su
fuente o, en modelos de un piso como Puriscal, en el `Building`, pero los dos hijos
permanecen contenidos solamente por su propietario.

`Vidrios_Plataforma` conserva un solo `Part::Feature`, pero cada pano se compone de
piezas simples alrededor de una abertura rectangular real: lateral izquierdo,
lateral derecho, vidrio superior y vidrio inferior solamente cuando la abertura
empieza por encima del mostrador. No se usa un solido superpuesto ni un booleano.
`AlturaAberturaVidrio` es la cota Z inferior local, no una distancia medida desde
el mostrador. Las validaciones impiden invadir montantes, bajar del mostrador o
superar la cota superior del vidrio.

La deteccion de host reutiliza muros Arch/BIM colineales. Copias explicitamente
rotuladas como auxiliares o referencias electricas se excluyen si existe un muro
arquitectonico primario. Nunca se crea un muro desde la linea. Si no hay host valido,
la plataforma se construye igualmente con `HostWall` vacio.

`FA Actualizar frente de plataforma` relee la geometria fuente y sustituye las
Shapes de `Cuerpo_Plataforma` y `Vidrios_Plataforma` en los mismos objetos. Asi sigue
movimientos y rotaciones, conserva propiedades/links y no produce duplicados. Los
frentes historicos anteriores a 0.10.0 conservan sus seis sketches, Spreadsheet,
zonas y algoritmo de actualizacion; no se migran ni se eliminan automaticamente.

La referencia `PL-01` de la `Guia Estandarizacion 050626 2`, paginas 33-34, respalda
el mostrador a 740 mm y el vidrio hasta 1800 mm. La referencia no acota de manera
inequivoca el hueco frontal. El valor inicial de 300 x 300 mm se conserva como
parametro provisional editable y no se presenta como norma. La herramienta no
modela caja como parte de esta plataforma.

## 2.4 Integracion BIM v0.14.0

Primera etapa implementada para que herramientas arquitectonicas no creen una rama `03_BIM` paralela en documentos nuevos:

- `FA_CreateBuildingGrid` es solo referencia: crea `ArchGrid` y representacion recortada dentro de `Auxiliares FA` bajo el `Level`, nunca `Arch.makeWall`. Si encuentra una salida legacy de pared reconstruida, restaura los muros FA que la version anterior podia haber ocultado.
- `FA_CreateSiteFloorBIM` reutiliza/crea `Building` y `Building Storey`, contiene la losa en el `Level` y crea el `Site` como raiz espacial. El terreno de prueba incorpora `CutUnderBuilding`.
- `FA_CreateModularCeiling` mueve `FA_Ceilings` a un unico `Level`, mantiene los links a recintos/luminarias y no obliga a crear `FA_Project` solo para ejecutar el comando.
- No se migro el cielo a `ArchCovering`: la alternativa nativa debe verificarse primero en FreeCAD 1.1.3 real.

Estado: codigo actualizado y `py_compile` aprobado; validacion visual/funcional en FreeCAD 1.1.3 pendiente.

## 3. Arquitectura

```text
FacilArquitecturaWB/
|-- Init.py
|-- InitGui.py
|-- README.md
|-- DOCUMENTACION_WORKBENCH.md
|-- NOTES_RESEARCH.md
|-- commands/          # adaptadores GUI
|-- core/              # algoritmos y creacion de objetos
|-- modules/service_platform/ # seleccion, marco local, plan y generadores compatible/compacto
|-- ui/                # dialogos pequenos de PySide
|-- resources/icons/   # iconos SVG
`-- tests/             # pruebas sin GUI
```

Convenciones:

- `commands/` valida seleccion, informa al usuario y llama al nucleo.
- `core/` contiene logica reutilizable y testeable.
- Cada operacion completa usa una transaccion cuando es posible.
- Los errores corregibles se muestran como advertencias breves.
- Los fallos internos se registran con `[FACILARQ]`.
- Los objetos generados conservan enlaces a sus fuentes.

## 4. Estructura del documento

### 4.1 Flujo BIM nativo desde Sketches

`FA_CreateBIMStructure` y `FA_RebuildBIMModel` producen esta jerarquia autoritativa:

```text
Building [IfcType = Building]
`-- Level [IfcType = Building Storey]
    |-- Sketch fuente de muros
    |-- Wall [Base = Sketch fuente]
    |-- Axis / AxisSystem / Columns
    |-- Door + su Sketch Base nativo
    |-- Window + su Sketch Base nativo
    `-- Sketches de referencia seleccionados
```

No se crean `FA_Project`, `03_BIM`, `FA_ReconstructedWallBase`, grupos de puertas o
grupos de ventanas. `Level.Group` es la relacion de contencion. `FA_TargetLevel` es
solo una clave de trazabilidad en texto; no es un enlace inverso, porque ese enlace
formaria un ciclo con la contencion nativa de `BuildingPart`.

#### Regla de residencia de objetos

Toda herramienta de Facil Arquitectura que cree un objeto permanente debe insertarlo
automaticamente en la estructura espacial y funcional correcta del edificio. Para los
elementos arquitectonicos, la residencia preferente es la contencion BIM nativa
`Building -> Level`; no se crean grupos paralelos solo para clasificar muros, puertas,
ventanas u otros elementos cuando `Level.Group`, `Base`, `Host` u otra relacion nativa
ya expresa correctamente su pertenencia.

Los objetos temporales, de diagnostico, construccion o compatibilidad deben ubicarse
en ramas auxiliares y, cuando corresponda, permanecer ocultos. `FA_CreateBuildingGrid`
usa una unica rama `Auxiliares FA` dentro del Level para el `ArchGrid` y su trazado
recortado. Las referencias CAD temporales (`_BlockDefinitions`, `_UnreferencedBlocks`,
`Capas` y equivalentes creados por el importador) pueden permanecer en la raiz y no se
reorganizan automaticamente.

La regla es no destructiva: no migra documentos existentes ni elimina grupos legacy.
Los nombres internos y adaptadores heredados se conservan mientras existan consumidores.

### 4.2 Flujo heredado DXF/Puriscal

```text
FA_Project
|-- 00_Reference          (FA_Reference)
|-- 01_Parameters         (FA_Parameters)
|   `-- Spreadsheet_Parametros
|-- 02_MasterSketches     (FA_MasterSketches)
|-- 03_BIM                (FA_BIM)
|-- 04_Areas              (FA_Areas)
`-- 05_Electromechanical  (FA_Electromechanical)
```

Este arbol completo se conserva exclusivamente como contrato legacy para herramientas
y documentos anteriores; `ensure_project_structure()` sigue disponible y no elimina ni
migra nada. Desde 2026-08-27, los comandos actuales usan una estructura de soporte por
demanda: `FA Crear proyecto` crea/reutiliza `Building -> Level` y solo `FA_Parameters`;
`FA Crear sketches maestros` agrega `FA_MasterSketches` cuando se necesita. Los comandos
de centros de paredes, puertas y ventanas, cierre de buques y geometria de muestra usan
solamente `FA_MasterSketches`; la recopilacion de rotulos usa solamente `FA_Parameters`.
No se crean `FA_Reference`, `FA_BIM`, `FA_Areas` ni `FA_Electromechanical` vacios por anticipado.
`FA_Project` conserva `FA_WorkbenchVersion` y `FA_WorkbenchBuild`. Los nombres internos
estables se usan para automatizacion; FreeCAD puede agregar sufijos a las etiquetas
visibles al recrear objetos durante una sesion.

## 5. Parametros principales

| Parametro | Valor inicial mm | Uso |
|---|---:|---|
| `wall_height_mm` | 3000 | Altura general de muros. |
| `ext_wall_thickness_mm` | 200 | Espesor exterior de respaldo. |
| `int_wall_thickness_mm` | 100 | Espesor interior de respaldo. |
| `door_height_mm` | 2100 | Altura de puertas. |
| `window_sill_mm` | 900 | Antepecho de ventanas. |
| `window_height_mm` | 1200 | Altura de ventanas. |
| `slab_thickness_mm` | 150 | Espesor de losa. |
| `grid_cluster_tolerance_mm` | 80 | Agrupacion de alineamientos. |
| `grid_primary_support_mm` | 5000 | Soporte minimo de eje principal. |
| `grid_max_lines_per_direction` | 8 | Limite de lineas por direccion. |
| `column_width_mm` | 400 | Ancho de columnas. |
| `column_depth_mm` | 400 | Fondo de columnas. |
| `column_height_mm` | 3000 | Altura de columnas. |

Al agregar parametros, el nucleo usa la siguiente fila realmente libre y preserva
parametros desconocidos o creados por el usuario.

## 6. Flujo completo DXF a BIM

### A. Preparar proyecto

1. Ejecutar `FA Importar referencia DWG/DXF`, elegir el archivo y su unidad real.
2. Ejecutar `FA Crear proyecto`.
3. Ejecutar `FA Crear sketches maestros`.
4. Mantener el DXF como referencia.

La importacion crea un documento nuevo sin guardar, conserva intacto el FCStd activo
y restaura las preferencias de Draft al terminar. Para archivos cuya cabecera no
coincide con sus coordenadas, la unidad elegida tiene prioridad. El procedimiento
completo se documenta en [Importacion controlada DWG/DXF](docs/IMPORTACION_CAD_DWG_DXF.md).

### B. Extraer centros

1. Seleccionar el layer o grupo de paredes y ejecutar `FA Centros desde seleccion`.
2. Revisar los Sketches separados por espesor.
3. Seleccionar puertas y ejecutar `FA Centros de puertas`.
4. Seleccionar ventanas y ejecutar `FA Centros de ventanas`.

El extractor empareja bordes, mide espesores, consolida tramos, respeta remates,
recorta sobrepasos, agrega restricciones seguras y separa perfiles de columnas.

Desde v0.14.2, si la estrategia es automatica y la seleccion es un `Part::Feature` con `ShapeType = Compound`, el nucleo crea una fuente virtual por cada borde, equivalente a `Draft Downgrade / splitWires`. La fuente permanece intacta y no aparecen objetos intermedios. `App::Link`, puertas, ventanas, Shapes no Compound y tipos Part derivados conservan deliberadamente sus rutas anteriores.

Regresion validada: `Pared_Concreto001` del documento `1416 Levantamiento 250424 Depurado`. El Compound directo y 140 bordes explotados producen exactamente 37 lineas de muro de 150 mm y una cruz de columna de 2 lineas.

La regresion dispone ademas de `tests/freecad_compound_centerlines_smoke.py`, que construye dos muros dentro de un Compound y verifica en FreeCAD real que la extraccion no requiera `Part Explode` ni genere objetos intermedios.

Metadatos relevantes:

- `FA_ElementType`, `FA_ExtractionMode` y `FA_CenterlineKind`.
- `FA_WallThickness` y `FA_WallHeight`.
- `FA_RelatedCenterlineSketches`.

No se debe reprocesar un `Sketch_Centros_*` como si fuera geometria DXF original.

### C. Cerrar buques de puertas y ventanas

1. Seleccionar los Sketches de paredes, su muro BIM o un Sketch generico con geometria.
2. Seleccionar opcionalmente los Sketches de puertas/ventanas que definen el alcance.
3. Ejecutar `FA Cerrar buques de puertas y ventanas` (`FA_CloseWallSketch`).
4. La herramienta analiza cada abertura o cadena consecutiva, conserva el eje real del muro y crea `Sketch_Cerrado_*` sin modificar la fuente.
5. Si dos cierres son equivalentes, informa ambiguedad y no modifica ese caso.

Para inspeccion automatizada se dispone de `diagnose_closed_wall_sketches(...)`, que devuelve un informe JSON-compatible con cierres, rechazos, Sketch fuente, `GeometryIndex`, score, modo y segmentos afectados. En la validacion real 1416, 25 geometrias de abertura formaron 23 regiones seguras; el Sketch paso de 37 a 19 lineas, sin ambiguos ni rechazos. El muro `Arch Wall` derivado produjo un solido valido, siguio los cambios del Sketch y acepto cortes BIM nativos de puerta y ventana.

Si se selecciona un muro BIM, el comando resuelve su eje mediante `Base` o
`FA_SourceSketch`. Si el Sketch es generico solicita espesor, altura y clasificacion,
y completa el contrato de muro dentro de la misma transaccion que crea la copia.
Los Sketches identificados como puertas, ventanas o columnas no se convierten en muros.

El cierre usa los ejes de puertas y ventanas como evidencia. La cuadricula auxiliar crea:

- un `ArchGrid` nativo con `Arch.makeGrid()`;
- una representacion recortada/editable de los tramos utiles.

Desde v0.14.0 la cuadricula no crea `FA_ReconstructedWallBase`, no ejecuta `Arch.makeWall`
y no oculta los muros existentes. La creacion de muros BIM es exclusivamente una accion
posterior y explicita mediante `FA Muros BIM desde Sketch`. Al reejecutarse sobre una salida
legacy, el comando retira sus antiguos objetos reconstruidos y restaura los muros FA que la
version anterior podia haber ocultado.

### D. Crear muro BIM

Seleccionar cualquier `Sketcher::SketchObject` con geometria y ejecutar
`FA Muros BIM desde Sketch`.

El muro conserva el Sketch como `Base`, enlaza `Width` con el espesor y `Height` con la
altura, y se crea mediante `Arch.makeWall`.

Si el Sketch no posee el contrato de eje de muro, el comando solicita:

- espesor para datos faltantes;
- altura para datos faltantes;
- clasificacion interior, exterior o generica.

La conversion agrega `FA_WallThickness`, `FA_WallHeight`,
`FA_Role = centerlines`, `FA_CenterlineKind = walls` y `FA_ElementType`. No cambia
la geometria ni crea una copia del Sketch. Los valores positivos existentes se
conservan; si habia otro rol o tipo se registran en `FA_PreviousRole` y
`FA_PreviousElementType`. Toda la conversion y la creacion del `Arch Wall` forman
una sola transaccion de Undo/Redo. Ejecutar nuevamente el comando sustituye solo
el muro generado desde ese mismo Sketch.

### E. Recintos y areas

1. Ejecutar `FA Recopilar rotulos de recintos`.
2. Seleccionar el muro BIM autoritativo.
3. Usar el motor `FacilArquitecturaWB/core/rectangular_area_analysis.py`; el
   lanzador historico queda en `Xcluidos/Areas/`.

La herramienta visible ya no depende de `Scripts Varios`. Su motor reutilizable
esta en `core/rectangular_area_analysis.py`; la copia historica externa se conserva
solo como referencia y no se modifica.

Resultados:

- `Spreadsheet_Rotulos_Recintos`.
- `FA_RectangularAreas`.
- `Spreadsheet_Analisis_Areas`.

Contrato ElectricCR:

- `ElectricCRTipo = Area`.
- `AreaM2`, `AreaID`, `Recinto` y `AreaNombre`.
- `Habitacion`, `Local`, `Espacio` y `Zona`.
- `VirtualClosures` y `Confidence`.

### F. Puertas BIM

Seleccionar uno o varios Sketches de centros y ejecutar `FA Puertas BIM`. Se pueden
seleccionar tambien muros BIM; de lo contrario se buscan en el documento. El comando
proyecta cada eje sobre soportes colineales, compara distancia, orientacion, sobrepaso
y Z, rechaza hosts ambiguos y crea el preset nativo `Simple door`.

Contrato del flujo BIM nativo:

- Contencion directa en el `Building Storey` seleccionado o creado.
- `IfcType = Door`, `Opening = 100`, `SymbolPlan = True`.
- Sketch `Base`, `Hosts = [wall]`, `HoleDepth = 0`, `MoveWithHost = True`.
- `FA_SourceSketch`, `FA_SourceGeometryIndex`, `FA_HostWall`.
- `FA_Width_mm`, `FA_Height_mm`, `FA_OpenDirection`, `FA_OpenAngle_deg`.
- `FA_HostScore`, `FA_WallOffset`, `FA_HostAngleError_deg`, `FA_CutVolume_mm3`.

La orientacion automatica hacia recintos y la deteccion de doble hoja permanecen en
las macros historicas como especializaciones; el comando general prioriza un objeto
BIM valido, alojado y con corte comprobado.

#### F.1 Puerta doble BIM Europa

`FA Insertar puerta doble BIM` usa `Arch.makeWindow` directamente y define 13
componentes `WindowParts`: marco exterior, dos marcos de hoja, cuatro travesanos,
dos paneles inferiores y cuatro vidrios. El resultado tiene `IfcType = Door`, dos
hojas gobernadas por `Mode1` y `Mode2`, materiales compartidos y Placement propio.

Con un muro seleccionado, el punto pulsado se proyecta y limita al tramo para que
el ancho completo quepa. Si no hay punto se usa el centro del tramo. La puerta
conserva `Hosts = [wall]`, `HoleWire = 1`, `HoleDepth = 0` y
`MoveWithHost = True`. `Hosts` es el unico enlace BIM autoritativo al muro:
FreeCAD 1.1.3 desplaza una vez por cada enlace inverso y los aliases `Host` y
`FA_HostWall` provocaban movimiento triple. `FA_HostWallName` mantiene la clave
estable sin duplicar relaciones. Antes de cerrar la transaccion se comprueba el
Subvolume nativo, la interseccion y la disminucion real del volumen del muro. Si el
muro ya tenia el hueco, se valida contra un soporte nominal del mismo tramo sin
exigir que la geometria visible de la puerta intersecte el muro. Sin muro se crea
como objeto BIM libre con X, Y, Z y rotacion configurables.

### F.2 Aberturas BIM desde Sketch

`FA Aberturas BIM desde Sketch` extiende `core/opening_utils.py`; no introduce un
segundo selector de hosts. Cada linea no constructiva se transforma a coordenadas
globales con el `Placement` del Sketch, se proyecta contra los ejes de los Walls y
se omite si no existe un anfitrion o si dos candidatos son equivalentes.

FreeCAD 1.1.3 contiene el preset `Opening only`. Su implementacion oficial crea un
perfil rectangular cerrado, llama `Arch.makeWindow(..., parts=[])`, asigna
`IfcType = Opening Element` y deja que `ArchWindow.getSubVolume()` produzca el
corte. FA usa directamente ese mecanismo equivalente para evitar los recomputes
internos del preset por cada instancia y recomputa el lote al final.

Contrato:

- `1 Sketch = 1 familia/configuracion + N instancias`.
- Ancho derivado de cada linea; altura inicial 2100 mm y altura desde piso 0 mm.
- `WindowParts = []`, `SymbolPlan = False`, sin Shape solida visible.
- `Hosts = [wall]`, `MoveWithHost = True`, `HoleDepth = 0`.
- `FA_SourceSketch`, `FA_SourceGeometryIndex`, `FA_HostWall`, dimensiones y evidencia de corte.
- Reemplazo limitado a `FA_GeneratedBy = FA_CreateOpeningsFromSketch`.
- Mensajes de lote con prefijo `[FACILARQ][ABERTURAS]`.

### G. Ventanas BIM

Seleccionar los Sketches de centros y ejecutar `FA Ventanas BIM`. El comando usa el
mismo selector geometrico de host, admite paños que cruzan varios tramos colineales y
solicita altura, antepecho y tolerancia.

Desde la version 0.9.0 la seleccion GUI se conserva antes de asegurar la estructura
Building/Level; tambien se resuelven `App::Link` hacia Sketches. Si no existe un Sketch
seleccionado, se buscan automaticamente fuentes identificadas como ventanas mediante
nombre, etiqueta, `FA_CenterlineKind` o `FA_ElementType`. Esta recuperacion no acepta
Sketches genericos ni los Sketches Base generados por puertas o ventanas.

Una seleccion explicita si acepta un Sketch generico sin espesor. Tambien corrige el
caso heredado donde `Sketch_Centros_Ventanas*` conserva por error
`FA_CenterlineKind = walls`: el nombre/tipo de ventana y la intencion explicita tienen
prioridad, sin permitir que un Sketch con `FA_WallThickness > 0` se convierta en abertura.

Presets actuales:

- ancho menor de 900 mm: `Open 1-pane`;
- ancho igual o mayor de 900 mm: `Sliding 2-pane`.

Contrato del flujo BIM nativo:

- Contencion directa en el `Building Storey` seleccionado o creado.
- `IfcType = Window`, `Opening = 0`, `SymbolPlan = True`.
- Sketch `Base`, `Hosts = [wall]`, `HoleDepth = 0`, `MoveWithHost = True`.
- `FA_SourceSketch`, `FA_SourceGeometryIndex`, `FA_HostWall`.
- `FA_Width_mm`, `FA_Height_mm`, `FA_Sill_mm`, `FA_PresetName`.
- Metricas del host y volumen de corte validados.

### H. Reconstruccion coordinada

`FA Reconstruir modelo BIM` analiza todos los Sketches y propone muros, columnas,
puertas, ventanas y referencias. La prioridad es metadata, propiedades especificas,
nombre/Label y, finalmente, asignacion manual. El dialogo permite escoger cualquier
Sketch para los roles principales y marcar varias ventanas o referencias.

El coordinador llama los mismos servicios usados por los comandos independientes,
en este orden: estructura, muros, columnas, puertas y ventanas. Toda la ejecucion
usa una transaccion. No necesita Internet, Codex ni MCP en runtime. La losa aparece
como fase diferida y no se genera automaticamente.

### I. Losa y estructura

`FA Losa y sitio BIM` calcula la huella desde Sketches arquitectonicos. Los Sketches
de columnas `P4` no deben ampliar la losa.

`FA Ejes y columnas BIM` crea `Arch Axis`, `AxisSystem` y columnas `Arch Structure`.
Esos ejes estructurales no deben confundirse con el ArchGrid arquitectonico.

### J. Cielo suspendido y luminarias ElectricCR

`FA Cielo 600x600 con luminarias ElectricCR` genera un cielo suspendido por cada
recinto. Si existen objetos `FA_Role = room_polygon`, estos tienen prioridad sobre
los rectangulos del analisis anterior. La fase de la reticula se calcula sobre la
caja local de cada recinto y cada celda se intersecta con la cara poligonal: las
celdas exteriores se omiten y las del perimetro se convierten en paneles recortados.
Cuando existen luminarias ElectricCR, intenta que sus centros coincidan con el
centro de una celda de 600x600 mm.

Reconoce objetos directos con `Tipo = Luminaria` y tambien instancias `App::Link`
cuyo objeto maestro tiene ese tipo. Las posiciones electricas son autoritativas:
el comando no mueve luminarias. Reserva la celda ocupada y registra como
incompatibilidad un desplazamiento mayor que la tolerancia, una celda perimetral
incompleta o dos luminarias dentro de la misma celda.

El resultado incluye `FA_CeilingPanels`, `FA_CeilingGrid` y
`Spreadsheet_CielosSuspendidos`. Los paneles se clasifican con
`IfcType = Covering` y `PredefinedType = CEILING`. Cada salida conserva
`FA_SourceRoom`, `FA_RoomGeometry`, el area del recinto fuente y la cantidad de
celdas recortadas por el perimetro.

### 6.4 Cambio de preset de puertas Arch/BIM existentes

`FA_ChangeDoorType` consulta `ArchWindowPresets.WindowPresets` en tiempo de
ejecucion y filtra nombres de puerta. En la instalacion validada de FreeCAD 1.1.3
los unicos presets integrados aplicables son `Simple door` y `Glass door`.

La propiedad nativa `Preset` es de solo lectura en la interfaz y no participa por
si sola en `ArchWindow._Window.onChanged()`. Por ello el comando genera una puerta
temporal mediante `ArchWindowPresets.makeWindowPreset()`, transfiere su Base y
`WindowParts` al mismo objeto seleccionado, restaura el estado arquitectonico y
valida el subvolumen contra cada host. Solo despues retira la puerta temporal y la
Base anterior que haya quedado sin referencias. La transaccion global revierte
todo el lote si falla una puerta.

Se conservan `Label`, `Placement`, `Width`, `Height`, `Hosts`, `Normal`,
`HoleDepth`, `Opening`, simbolos, `IfcType`, contenedor, material y propiedades
`FA_*`. El override individual queda en la puerta y, cuando existe
`FA_SourceSketch`, tambien en `FA_DoorTypeOverrides` del Sketch como mapa JSON por
`FA_SourceGeometryIndex`. Asi `FA_CreateDoorsFromSketch` respeta el tipo al
regenerar. Las puertas dobles especiales se rechazan porque su Base multicomponente
no es compatible con esta transferencia.

El dialogo conecta directamente el boton `Aplicar` con
`QDialog.accept()`. Esto es necesario porque `QDialogButtonBox.Apply` usa
`ApplyRole` y, a diferencia de `Ok`, no emite la señal `accepted` del
`QDialogButtonBox`.

## 7. Trazabilidad y reemplazo seguro

Los flujos agregan `FA_GeneratedBy` y `FA_Role`. Al repetirse, reemplazan solamente
objetos creados por el mismo generador.

Generadores principales:

- `FA_CreateBuildingGrid` y `FA_CreateWallsBIM` (alias de `FA_CreateWallsFromSketch`).
- `FA_CreateColumnsFromSketch` y alias `FA_CreateAxesColumnsBIM`.
- `FA_CollectRoomLabels`.
- `FA_RectangularAreaAnalysis`.
- `FA_CreateDoorsFromSketch`; aliases `FA_CreateDoorsBIM` y `FA_InsertDoorsBIM` para lectura/compatibilidad.
- `FA_CreateWindowsFromSketch`; aliases `FA_CreateWindowsBIM` y `FA_InsertWindowsBIM` para lectura/compatibilidad.
- `FA_CreateModularCeiling`.
- `FA_CreateServicePlatformFront` (modo compacto y modo historico compatible).

Los cambios manuales del usuario tienen prioridad. Nunca se deben sustituir objetos sin
comprobar su generador y sus enlaces fuente.

## 8. Caso validado: Puriscal

- DXF interpretado en milimetros.
- Losa aproximada: 26,061 x 30,245 x 150 mm.
- `FA_GridWallTrace`: 67 geometrías y 148 restricciones; completado manualmente.
- `Wall002`: 120 x 3000 mm, valido y un unico solido.
- 25 recintos.
- Area programada: 364.310 m2.
- Area rectangular: 360.124 m2; diferencia -1.15%.
- 18 puertas BIM logicas y 19 hojas: 17 puertas sencillas y una puerta doble.
- 8 ventanas BIM.
- Volumen final de `Wall002`: 78,366,382,109 mm3.
- La copia actual se revalido con 19 hojas de puerta y 8 ventanas nativas, todas con
  Sketch Base y `Hosts = [Wall002]`. Los comandos nuevos reconocieron los 27 indices
  historicos y crearon cero duplicados.

Hallazgos:

- La puerta de `PENSIONES` se infirio de un hueco real de pared y se agrego como
  geometria 16 del Sketch de puertas.
- En el frente, la geometria 17 genera una puerta sencilla de 1203 mm. Las
  geometrias contiguas 0 y 18 forman un unico vano de 1968 mm con dos hojas BIM,
  bisagras en los extremos y apertura hacia el interior.
- Una puerta hacia `PASILLO PRINCIPAL` conserva confianza `0.62` por estar a 1437 mm
  de una esquina.
- Una ventana se conserva como paño continuo de 5470 mm.
- Persisten tres traslapes pequenos en el analisis rectangular.

### 8.1 Modelo depurado y jerarquia espacial

`Puriscal Depurado.FCStd` conserva los resultados finales y las fuentes necesarias,
pero ordena el arbol mediante objetos BIM espaciales. Por ser un edificio de un solo
piso no se crea `Level` ni `Building Storey`.

```text
Sitio y terreno - Puriscal
|-- Terreno y obras exteriores
|   `-- Acera frontal 2.00 m
`-- Edificio Puriscal - un nivel
    |-- Elementos constructivos
    |-- Puertas y ventanas
    |-- Cielos suspendidos
    |-- Espacios de referencia
    `-- Fuentes y auxiliares
```

La acera es un `IfcType = Slab` de 11,591 x 2,000 x 150 mm, con su cara
superior en Z = 0. `Espacios de referencia` y `Fuentes y auxiliares` quedan ocultos,
no eliminados. Esta separacion permite una vista sencilla sin perder la capacidad de
regenerar analisis, puertas, ventanas o cielos.

La macro `OrganizarPuriscalDepurado.FCMacro` es idempotente y aplica esta estructura
sin insertar un nivel artificial.

El informe especifico del proyecto se conserva fuera del paquete como
`RESUMEN_CONSOLIDADO_PURISCAL_FACIL_ARQUITECTURA.md`.

## 9. Recarga durante desarrollo

Ejecutar `FacilArquitecturaLoader.FCMacro`. La macro agrega `Macros-de-Freecad` a
`sys.path`, purga modulos anteriores, vuelve a importar `InitGui`, registra los
comandos y activa el workbench sin cerrar FreeCAD.

La consola debe mostrar:

```text
        VERSION CARGADA: v0.14.2 | build 2026.08.23.2
```

## 10. Pruebas

Desde `Macros-de-Freecad`:

```powershell
python -m unittest discover -s 'FacilArquitecturaWB\tests' -p 'test_*.py'
python -m compileall -q 'FacilArquitecturaWB'
```

El planificador del cielo tiene pruebas especificas para cortes perimetrales,
reserva de una celda completa, deteccion de posiciones incompatibles y resolucion
de `App::Link` contra su maestro ElectricCR.

Ultimo resultado verificado: 151 pruebas de Facil Arquitectura aprobadas. En FreeCAD
1.1.3 se validaron la plataforma horizontal, vertical, diagonal, trasladada,
rotada, invertida, con lados izquierdo/derecho, uno/tres/cinco/ocho puestos,
una abertura real por puesto, cambios de ancho/alto, migracion v0.10.0,
actualizacion idempotente y persistencia FCStd. La prueba de Puriscal reutilizo
`Wall002`, mantuvo dos muros existentes y creo tres puestos de 1000 mm sin
duplicarlos. El generador historico de plataforma tambien conservo su prueba de
creacion, Undo/Redo, actualizacion y reapertura.

La puerta doble generica tiene ademas una prueba FreeCADCmd: dos puertas de 13
solidos, una alojada con corte real de 840 000 000 mm3 y otra libre, reutilizacion
del multimaterial y persistencia despues de guardar/reabrir. Una prueba GUI confirma
el comando `FA_InsertDoubleDoorBIM` y las cinco barras tematicas.

`FA_ChangeDoorType` tiene una prueba integral adicional con tres puertas de 800,
1000 y 1200 mm, alturas de 2100 y 2300 mm, cambio `Simple door` a `Glass door` y
regreso, identidad, Placement, Hosts, Normal, corte, lote, repeticion, regeneracion
por Sketch, rechazos y guardado/reapertura. La prueba MCP confirma ademas el comando
una sola vez en `FA Aberturas BIM` y cero auxiliares visibles. Una prueba GUI
especifica pulsa programaticamente el boton `Aplicar` y verifica que el dialogo
termine con `QDialog.Accepted`.

## 11. Limitaciones y ruta de desarrollo

La lista detallada y vigente de pendientes funcionales se mantiene en `README.md`, seccion `Pendientes`, para evitar listas paralelas que se desactualicen. Esta documentacion conserva solamente la ruta de desarrollo de alto nivel.

Limitaciones/prioridades actuales:

- consolidar el arbol BIM alrededor de `Site -> Building -> Level`;
- integrar Areas/Wires/Spaces como base espacial comun y reutilizable;
- resolver de forma comun y robusta los buques de puertas y ventanas;
- integrar piso, terreno y cielos dentro del arbol BIM sin perder la logica que ya funciona;
- garantizar representacion documental 2D comprensible y exportable;
- cerrar el flujo con una exportacion de modelo BIM limpio `.FCStd` y, cuando corresponda, IFC.

No se debe reemplazar una herramienta funcional por una solucion mas BIM si la nueva implementacion pierde capacidades ya validadas. Las mejoras deben reutilizar herramientas nativas de FreeCAD 1.1.3 cuando existan y conservar compatibilidad con los documentos actuales hasta completar validacion real.

## 12. Importacion DWG y Compound de paredes - 0.14.2

### 12.1 Diagnostico de importacion

El flujo `FA_ImportCADReference` fue instrumentado temporalmente en FreeCAD 1.1.3
con el DWG real `1416 Levantamiento 250424 Depurado.dwg`. La conversion, insercion,
recomputes, metadata, vista, limites, restauracion de preferencias y mensaje final
terminaron en 6.660 s. Ninguna variante que omitia una sola etapa revelo un
bloqueo del Workbench. Los controles DWG/DXF y el guardado FCStd tambien pasaron.

Una espera inicial provenia de `FreeCADMCP.gui_dispatch`: el guard de navegacion
veia un boton Qt retenido y no drenaba su cola. Este incidente no justifica quitar
`fitAll`, recomputes, metadata ni limites del importador. Ante un caso similar se
debe distinguir el tiempo del trabajo CAD del tiempo que una llamada pasa esperando
en la cola MCP.

### 12.2 Contrato de Compound para centros

Para `extraction_strategy = auto`, un `Part::Feature` cuya Shape sea `Compound` se
descompone en una fuente Python temporal por cada borde. Es equivalente a la salida
de `Draft Downgrade / splitWires`, pero no agrega objetos al documento. La seleccion,
etiqueta y conteo de fuente siguen refiriendose al objeto Compound real.

Este tratamiento ocurre antes de construir contexto topologico y source ids. Asi
una columna compacta solo bloquea sus propios cuatro bordes y no elimina todos los
bordes de pared del Compound. Los pares paralelos, espesores, merge/dedupe y cruces
de columna siguen usando el algoritmo existente.

No se aplica este cambio a App::Link, estrategias especializadas de puertas o
ventanas, Shapes no Compound ni tipos Part derivados. Los Sketches generados
registran `FA_ExtractionStrategy` y `FA_SourceObjectNames`; una reejecucion reemplaza
solo salidas `FA_Role = centerlines` que coincidan exactamente con ambos campos.

Caso real validado: `Pared_Concreto001`, 21 componentes y 140 bordes, produce 37
lineas de muro a 150 mm y una cruz de columna de 2 lineas. El resultado coincide
geometricamente con 140 bordes explotados; no aparecen 428, 440 ni 700 mm y la
fuente permanece intacta despues de reejecutar, Undo/Redo y guardar/reabrir.


## Integracion de aberturas alojadas y arbol limpio - 0.14.5

FreeCAD muestra una abertura alojada bajo su muro debido a la relacion nativa `Hosts`. La version anterior agregaba ademas la puerta/ventana y su `Base` directamente a `Level.Group`, por lo que el mismo `Window` y el mismo Sketch aparecian dos veces en el arbol.

Desde 0.14.5:

- una puerta, ventana o vano con host conserva `Hosts=[Wall]` y no se agrega tambien a `Level.Group`;
- su `Base` no se agrega como miembro directo del Level;
- ambos conservan `FA_TargetLevel` como trazabilidad textual sin enlace inverso ni segunda residencia;
- una puerta doble sin host si se agrega directamente al Level; una puerta doble alojada se muestra solamente a traves del muro;
- la correccion no crea copias ni migra automaticamente documentos ya existentes.

### Aviso de cambio de version

`InitGui.py` guarda `LastNotifiedVersion` y `LastNotifiedBuild` en parametros
persistentes de FreeCAD. `Activated()` compara la identidad completa
`VERSION + BUILD_ID`: una nueva version o un nuevo build muestra un solo
`QMessageBox`; activaciones posteriores de la misma identidad quedan silenciosas.
La migracion conserva `LastNotifiedVersion` heredado y registra el build actual
despues del primer aviso. Cuando existe informacion previa, el dialogo muestra
version/build anterior y actual.


## Puertas junto a pared lateral - snap de jamba (0.14.8 build 2026.08.29.1)

`FA Puertas BIM` y `FA Tabla de puertas` comparten ahora un plan geometrico de esquina.
Cuando un extremo del vano esta a `<= 180 mm` de una unica pared lateral compatible,
FA alinea la jamba con la **cara** de esa pared y no con su eje. El ancho derivado del
Sketch no cambia: ambos extremos se trasladan la misma distancia sobre el eje del muro
anfitrion.

Para una hoja se infieren bisagra en ese extremo y giro hacia la pared lateral. Para
dos hojas el marco puede hacer snap, pero la bisagra semantica continua siendo `BOTH`.
Si hay dos esquinas equivalentes o la pared lateral cruza claramente ambos lados del
host, no se infiere.

La tabla conserva autoridad sobre valores explicitamente escritos: un dato de bisagra
o apertura que contradiga el auto-snap no se reemplaza silenciosamente. Valores
`AUTO`/vacios si pueden resolverse por la geometria de esquina.

Una sola pared `Arch Wall` puede contener tanto el tramo anfitrion como sus paredes
laterales. El resolvedor excluye solo el segmento anfitrion real y presenta los
demas segmentos del mismo objeto como registros virtuales al planificador puro; no
crea objetos auxiliares ni un segundo algoritmo. `FA_CornerWall` guarda el `Name`
estable como texto de trazabilidad, no como un segundo `PropertyLink`, para evitar
una relacion adicional `MoveWithHost`.

La trazabilidad se guarda en propiedades `FA_Corner*`. La tolerancia de 180 mm fue
confirmada con el documento 1416 y con el modelo controlado
`tests/freecad_door_corner_snap_end_to_end.py`: snap unico, puerta alejada,
ambiguedad, ancho, bisagra, giro, corte, reejecucion, Undo/Redo y reapertura.

FreeCAD 1.1.3 no expone `FreeCADGui.removeCommand`. Para que el ID estable
`FA_CreateDoorsFromSketch` no conserve una clase Python antigua tras recargar el
Workbench, su registro usa `ReloadableCommandProxy`, que resuelve la implementacion
vigente en cada activacion. La barra `FA Aberturas BIM` contiene una sola accion
`FA Puertas BIM` y una sola `FA Tabla de puertas`.

### Correccion focalizada de giro y ajuste (build 2026.08.30.1)

El giro real de una puerta simple se resuelve con geometria fisica. El eje nativo
se toma desde la bisagra hacia la otra jamba; en FreeCAD 1.1.3 `Mode1` produce su
normal izquierda y `Mode2` la derecha. El adaptador cambia solamente el token
`Mode1/Mode2` del unico componente abatible de `Simple door` o `Glass door`.
La Tabla de Puertas conserva autoridad sobre valores explicitos y la idempotencia
compara tambien el modo nativo.

El plan separa `jamb_face_candidate` de `swing_direction_candidate`. Una cara
perpendicular inequivoca puede alinear una jamba aunque un cruce no permita inferir
el cuadrante; en ese caso el estado es `JAMB_ONLY` y la apertura queda `AUTO`.
Antes de aplicar cualquier snap se comparan ambas jambas con las caras opuestas.
Cuando el ancho excede la luz util, el estado es `NO_FIT`, no se reduce el ancho ni
se aplica el desplazamiento, y se registran `FA_AvailableWidth_mm` y
`FA_CornerPenetration_mm`.

La matriz MCP mide el vector real de la hoja en los solidos y cubre `Mode1`,
`Mode2`, inversiones START/END, `NO_FIT`, cruce, ausencia de lateral y ambiguedad.
En el documento 1416: GeometryIndex 6 se conserva; 1 cambia a `Mode2`; 8 reporta
`903.036 > 830.000 mm` y 73.036 mm de penetracion; 3 alinea la jamba con giro
`AUTO`. Host, corte, reejecucion, Undo/Redo y reapertura pasaron.

### Regresion de posicion GeometryIndex 9 (build 2026.08.30.2)

Una prueba A/B sobre la misma copia del levantamiento demostro que la capa de snap
desplazaba la puerta 9 `64.386719 mm`; sin snap se recuperaba la posicion funcional
anterior. La causa no era solamente la longitud del Sketch: en este cruce la cara
candidata quedaba dentro del propio segmento de la puerta.

Para `JAMB_ONLY`, si `target_axis_mm` queda estrictamente entre ambos extremos, el
plan conserva los endpoints proyectados, mantiene la cara como evidencia diagnostica
y no aplica la traslacion. La regla es geometrica, no depende del indice. Una cara
antes o despues del tramo sigue alineando la jamba como hasta ahora; por eso el
indice 3 y los restantes casos validos no cambian. Servicio Sanitario, `NO_FIT`,
Mode1/Mode2, Tabla de Puertas, Host/corte, idempotencia, Undo/Redo y reapertura
quedaron revalidados en FreeCAD 1.1.3.

## Principios de modelado por Sketches y ejes BIM

Facil Arquitectura adopta un flujo inspirado en Part Design para arquitectura: siempre que sea razonable, la geometria de diseno nace de un Sketch editable y el objeto BIM nativo es el resultado parametrico o reconstruible. El Sketch actua como editor geometrico 2D y conserva la intencion de diseno; FA interpreta esa geometria y crea o actualiza objetos nativos de FreeCAD/Arch/BIM en lugar de definir objetos BIM paralelos.

Los ejes se consideran referencias arquitectonicas y estructurales persistentes del edificio, no simples lineas auxiliares. Profesionalmente funcionan como datums de coordinacion para localizar columnas, vigas, muros estructurales, cimentaciones, cerchas/celosias, fachadas y otros sistemas. Cuando corresponda, FA debe transformar geometria sencilla de Sketch en `Arch Axis`, `AxisSystem` o `ArchGrid` y conservar esos objetos como parte del modelo y de su documentacion 2D.

Flujo conceptual preferido:

```text
Sketch editable
    -> interpretacion FA
    -> ejes/datum BIM cuando corresponda
    -> elementos BIM nativos
```

Ejemplos de autoridad geometrica:

- Sketch de muros: lineas -> muros Arch/BIM.
- Sketch de ejes: lineas -> `Arch Axis` / `AxisSystem` / reticula BIM.
- Sketch estructural: ejes e intersecciones -> columnas y otros elementos `Arch Structure`.
- Sketch de cerchas/celosias: ejes de ubicacion -> celosias BIM nativas; el eje define la posicion y la celosia es el elemento fisico asociado.
- Sketch de cubierta: contorno y/o trazados de control -> cubierta/roof BIM nativa.
- Sketch de aberturas: segmentos -> puertas, ventanas o vanos BIM nativos.

Para estructuras de techo, FA debe preferir el flujo basado en ejes que ya ofrece BIM. Las cerchas se trataran como celosias BIM nativas cuando la herramienta `Truss`/celosia resulte adecuada. FA simplificara su creacion y parametrizacion para sistemas de techo comunes en Costa Rica y Latinoamerica, sin reimplementar innecesariamente la geometria que BIM ya resuelve. Las correas, cubierta, aleros y demas componentes deben reutilizar igualmente las herramientas BIM/Arch existentes cuando sean adecuadas.

La relacion deseada es que una modificacion del Sketch o del eje pueda actualizar o regenerar de forma controlada el elemento BIM dependiente. Los ejes deben mantenerse identificables en el arbol del modelo y poder formar parte de planos y representaciones 2D. No todos los Sketches se convierten en ejes: solo aquellos cuya intencion sea una referencia o datum; los trazados fisicos, como muros o limites de cubierta, conservan su semantica propia.

Estos principios deben aplicarse tambien a ejemplos y demostraciones automaticas de FA: la demostracion debe mostrar Sketches y ejes sencillos que, mediante comandos de Facil Arquitectura, se transforman progresivamente en arquitectura BIM nativa. El usuario no debe necesitar reproducir manualmente el flujo del Workbench BIM estandar.


## FA Techo BIM - integracion 0.14.9

Fecha: 2026-08-30 16:55 America/Costa_Rica.

Se incorpora una nueva barra **FA Techo BIM** con un unico comando publicado: `FA_CreateRoofSystemBIM` (`FA Techo BIM`).

El comando recibe tres Sketches en cualquier orden y, despues de una planificacion de solo lectura, crea dentro del Level un grupo `Techo BIM` con objetos nativos de FreeCAD/BIM:

- un `Arch Axis` visible para las posiciones de cerchas;
- un unico `Arch Truss` llamado `Cerchas BIM`, repetido nativamente por `Axis`;
- una unica `Draft Line` oculta como Base de la cercha;
- un `Arch Frame` por faldon para clavadores, cada uno con Base y perfil propios;
- un `Arch Roof` con Base elevada cuando corresponde al apilado sobre clavadores.

Los Sketches fuente no se copian ni se mueven. Los objetos auxiliares Base/Profile no se agregan tambien al grupo principal, evitando padres visuales duplicados. La superficie maestra queda como concepto interno de calculo y no se crea en el documento normal.

Version del Workbench: `0.14.9`, build `2026.08.30.3`.

Validacion disponible al integrar: 20/20 pruebas focales del nucleo y prueba manual previa de geometria en FreeCAD 1.1.3. Queda pendiente el smoke test del comando registrado en el Workbench real.


## Integracion FA Techo desde rectangulo - 0.14.11 / build 2026.08.30.6

El toolbar `FA Techo BIM` conserva `FA_CreateRoofSystemBIM` y publica el segundo flujo como `FA_RoofAxisPrototype` con etiqueta **FA Techo desde rectangulo**, conservando temporalmente el ID historico para que el hot-reload no deje comandos duplicados.

El comando trabaja en el documento activo: seleccion de un `Draft Rectangle` horizontal, dialogo de parametros persistentes, planificacion previa, transaccion, resolucion de `Level`, grupo `Techo BIM`, creacion de cerchas/clavadores/cubierta, validacion de Shapes y cantidad de solidos, y rollback ante error.

La geometria de control se simplifica a `Draft Line`/`Draft Rectangle`. Los clavadores se materializan con el mecanismo nativo `Arch Structure/Beam + Axis`. La cubierta conserva una Base Rectangle interna separada de la huella para resolver el apilado vertical y evitar que la fuente quede oculta o con doble relacion visual.

Distribucion de clavadores: `fixed` conserva el valor solicitado en los intervalos interiores; `rounded` usa nominal redondeado a 50/100 mm sin exceder el maximo. Los extremos pueden ser excepciones.

Los muros BIM coincidentes se inspeccionan en modo lectura para informar coronacion y dispersion y, cuando son coherentes, pueden suministrar la cota de apoyo seleccionada por el usuario. No se alteran muros ni se infiere automaticamente la huella exterior en esta fase.


### Mejora de apoyos XY y distribucion - build 2026.08.31.4

El flujo conserva la Z de apoyo ya validada y agrega una resolucion independiente para XY. En modo automatico, las lineas de `Wall.Base` paralelas al vano transversal se proyectan al eje de cumbrera; solamente se aceptan candidatos cercanos a ambos extremos. El nucleo `core/roof_support_core.py`, independiente de FreeCAD/GUI/Qt, selecciona los dos apoyos extremos y aplica un ajuste simetrico opcional. Si la geometria de muro no permite resolver ambos ejes, el Rectangle sigue siendo el fallback seguro.

La posicion de la primera y ultima cercha queda definida por los apoyos estructurales; la cubierta sigue definida por la huella y sus aleros. Esto separa explicitamente **huella**, **apoyo estructural** y **borde de cubierta**. La distribucion interior de cerchas puede conservar el valor ingresado (`fixed`) o usar un nominal redondeado a 50/100 mm (`rounded`) sin superar el maximo.

La validacion previa al commit comprueba: Base inferior de cerchas en la cota de apoyo, primera/ultima cercha sobre los apoyos resueltos y continuidad geometrica `cercha-clavador-cubierta` dentro de 0.1 mm. La distancia global cerchas-muros se registra como diagnostico; no se convierte aun en bloqueo duro para evitar falsos negativos con muros compuestos o con geometria historica.


## Editor sencillo de ejes de cerchas - build 2026.08.31.5

Se agrega el comando `FA Editar ejes de cerchas` como interfaz amigable sobre el mismo `Arch Axis` nativo creado por `FA Techo desde rectangulo`. No crea ejes paralelos ni reemplaza el objeto BIM.

Flujo: seleccionar `Ejes de cerchas` o `Cerchas BIM` -> abrir el editor -> escoger modo, separacion maxima y retiros de primera/ultima cercha -> revisar la previsualizacion -> Aplicar.

Modos disponibles: mantener separacion con extremos simetricos, distribucion uniforme, nominal redondeado a 50 mm y nominal redondeado a 100 mm. El cambio actualiza `Axis.Distances`/`Angles`, las propiedades FA de distribucion y la cercha vinculada mediante su propiedad nativa `Axis`. No modifica clavadores, cubierta, pendiente ni apoyos estructurales.

## Ajuste de interfaz de techo - build 2026.08.31.6

- Se retira de la barra el boton legado `FA Techo BIM` (`FA_CreateRoofSystemBIM`). La barra `FA Techo BIM` se conserva como grupo y queda con `FA Techo desde rectangulo` y `FA Editar ejes de cerchas`.
- El comando legado se archiva para referencia/recuperacion futura; no se elimina su historia.
- Se agregan iconos SVG propios para `FA Techo desde rectangulo` y `FA Editar ejes de cerchas`.
- La simplificacion adicional del editor de ejes queda documentada en `PENDIENTE_FA_EDITOR_EJES_CERCHAS.md`.


## Demostracion automatica de edificio - build 2026.08.31.7

Se incorpora `FA_DemoBuilding` (`FA Demo edificio`) dentro de `FA Proyecto BIM`. Su finalidad es demostrar, en un documento nuevo y autocontenido, el flujo completo de Facil Arquitectura desde fuentes 2D simples hasta objetos BIM nativos.

El nucleo `core/demo_building_core.py` genera una especificacion JSON-compatible sin importar FreeCAD, FreeCADGui ni Qt. El caso canonico es una casa rectangular de 6000 x 8000 mm, una planta, un tabique interior, dos puertas, seis ventanas, losa y cubierta a dos aguas. El modo aleatorio utiliza una semilla explicita; la misma semilla debe conservar identidad geometrica y parametrica.

El adaptador `commands/cmd_demo_building.py` crea y conserva Sketches para muros y centros de aberturas; luego reutiliza `ensure_project_support_structure`, `ensure_bim_structure`, `create_site_floor_from_sketches`, `prepare_sketches_as_wall_centerlines`, `create_walls_from_centerline_sketches`, `create_openings_from_centerlines` y el flujo vigente de techo por rectangulo. No debe introducir implementaciones paralelas de Wall, Window, Door, Slab, Truss, Beam/Structure o Roof.

Para permitir esa composicion, `commands/cmd_roof_axis_prototype.py` publica `create_roof_from_rectangle_programmatic(...)`. La funcion usa el mismo plan, apoyos, distribuciones y validaciones del comando interactivo, acepta overrides de configuracion y por defecto no persiste preferencias de usuario.

La demo crea un objeto controlador `FA_DemoBuilding` con semilla, modo, resumen y la especificacion JSON completa. Toda materializacion se realiza dentro de una unica transaccion; un fallo debe abortar la operacion y cerrar el documento demo. Los Sketches y la huella de techo cumplen la funcion de representacion/documentacion 2D inicial.

Pruebas de integracion previas: 6/6 focales y 5000 especificaciones aleatorias validas. Pendiente de integracion: ejecutar el boton en FreeCAD 1.1.3 y revisar el arbol, los cortes de puertas/ventanas, el Shape de la losa y la continuidad cerchas-clavadores-cubierta. La composicion de la barra cambia en este build, por lo que la primera prueba debe hacerse despues de reiniciar completamente FreeCAD.

Especificacion ampliada: `DEMO_EDIFICIO_AUTOMATICO.md`.

## Casa demo v2: recintos, Espacios BIM y cielorraso - build 2026.08.31.9

Se extiende `FA_DemoBuilding` manteniendo el mismo ID y el mismo núcleo reproducible. No se agrega otro botón ni cambia la composición de la barra.

La materialización queda dividida en ocho pasos trazables: proyecto/Level, Sketches arquitectónicos, piso, muros, aberturas, recintos + Spaces, cielorrasos y techo. La etapa de recintos reutiliza `create_closed_room_sketch(...)` sobre los Sketches de muros exterior/interior y exige que la topología detectada coincida con los dos recintos declarados por la especificación.

Cada recinto se materializa además como `Arch Space` nativo. Para conservar una geometría de piso exacta y JSON-compatible se guarda `FA_FloorPolygonJSON`; el sólido Base usado por `Arch.makeSpace()` queda oculto y el Space es el objeto BIM visible. El caso canónico crea `Espacio BIM - Estar-comedor - Demo` y `Espacio BIM - Dormitorio - Demo`.

`core/ceiling_utils.py` amplía `collect_rooms()` y `_room_spec()` para reconocer Spaces BIM de FA. `create_modular_ceilings(...)` permanece como única implementación de cielorraso: usa módulo 600 mm, recorte a recinto, objetos `IfcType=Covering` / `PredefinedType=CEILING` y su schedule existente. Así no se crea lógica paralela para la demo.

El controlador `FA_DemoBuilding` enlaza `RoomSketch`, `Spaces` y `CeilingObjects`, además de los objetos existentes. La especificación pura incluye las secciones `rooms` y `ceiling`, por lo que una misma semilla reproduce también recintos y cielorrasos.

La observación de que una puerta aparece con icono de ventana corresponde al comportamiento nativo de FreeCAD: BIM Door usa el objeto `Window` con configuración de puerta y el ViewProvider de ArchWindow suministra el icono de ventana. No se cambia el ViewProvider en esta fase.

Pruebas focales de la ampliación: 10/10. Queda pendiente validar en FreeCAD 1.1.3 que los dos Spaces sean sólidos válidos, que se creen dos sistemas de cielorraso y que la casa completa conserve piso, muros, aberturas y techo sin regresión.


## Modo demostracion guiada - build 2026.08.31.10

`FA_DemoBuilding` conserva identidad y especificacion. Se agrega una segunda forma de ejecucion, no un segundo comando: completa o guiada. `core/demo_guided_core.py` declara el guion independiente de 14 pasos y `commands/cmd_demo_building.py` concentra la adaptacion FreeCAD en `DemoBuildingSession`. El modo completo recorre la misma sesion bajo una unica transaccion; el guiado abre una transaccion por paso.

La interfaz guiada es un `QDockWidget` no modal con `QTimer` para programar avances. La geometria nunca se calcula en segundo plano. Los pasos separan explicitamente el Sketch de puertas de la creacion de puertas BIM y el Sketch de ventanas de la creacion de ventanas BIM, de modo que la demostracion ensena el origen 2D antes de la materializacion hospedada.

La navegacion `Anterior`/`Reiniciar` usa reconstruccion determinista desde la misma especificacion/semilla y no una eliminacion manual de objetos. El controlador registra `ExecutionMode`, `CurrentStep`, `TotalSteps`, `PlaybackState`, `LastCompletedStep`, `LastError`, `AutoCamera` y `StepPlanJSON`.

Pruebas previas a integracion real: 15/15 focales de demo/core/contrato y `py_compile` aprobado. Pendiente: smoke en FreeCAD 1.1.3 del panel y de la secuencia completa.

## FA Demo edificio - saneamiento build 2026.09.01.1

Tras la primera prueba real del reproductor guiado en FreeCAD 1.1.3 (14/14 pasos), se corrigieron dos avisos no bloqueantes sin modificar la casa generada:

1. `GeneratedObjects` ya no enlaza `Site`, porque ese enlace cerraba el ciclo `Site -> Building -> Level -> FA_DemoSources -> FA_DemoBuilding -> Site` y FreeCAD reportaba `The graph must be a DAG`. Los contenedores se documentan ahora por nombre en `ContextContainersJSON`.
2. `Spreadsheet_Parametros` se recomputa antes de que la demo busque sus filas y despues de escribir los valores especificos de la casa. Esto evita la advertencia falsa de parametros no encontrados y conserva la hoja como representacion editable de los parametros de la demo.

El guion de 14 pasos, los modos fijo/aleatorio, la reproducibilidad por `seed` y el modo completo permanecen sin cambios.



## FA Demo edificio - pulido visual build 2026.09.01.2

Se conserva intacta la materializacion BIM de `FA_DemoBuilding`; los cambios de esta build son de interfaz y presentacion. `core/demo_guided_core.py` declara un nombre de icono SVG por cada uno de los 14 pasos. `GuidedDemoDock` resuelve ese recurso y lo presenta junto al titulo, sin trasladar Qt al nucleo.

`DemoBuildingSession.apply_guided_presentation()` usa exclusivamente propiedades de `ViewObject`. En los pasos donde se explican fuentes 2D, la sesion recuerda los estados originales y de-enfatiza temporalmente los objetos 3D que las ocultan. La restauracion ocurre antes de aplicar el siguiente estado, al reconstruir y al cerrar el panel. Ninguna transparencia o visibilidad temporal forma parte de `SpecificationJSON` ni modifica geometria BIM.

Se agrega el boton `Cerrar demostracion`: detiene el temporizador y restaura la presentacion, pero no llama `closeDocument()` ni elimina el resultado. Los cinco SVG recientes `demo_building`, `roof_from_rectangle`, `edit_truss_axes`, `door_table` y `window_table` se actualizan manteniendo su identidad de archivo.

Pruebas focales del cambio: 4/4; compilacion Python aprobada; cinco SVG parseados y renderizados correctamente. Queda pendiente la comprobacion visual en FreeCAD 1.1.3.


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


## Build 2026.09.01.5 - aislamiento del feedback en techo programatico

`create_roof_from_rectangle_programmatic()` acepta `feedback=None`. Las llamadas a `stage()` se protegen y la ruta programatica vuelve a ser utilizable por Demo/MCP sin requerir un objeto Qt. La ruta interactiva `_run_from_rectangle()` conserva `LongOperationFeedback`. Cambio limitado a feedback; sin cambios geometricos.


## Build 2026.09.01.6 - regla de aviso previo y jardin de demostracion

Se refuerza la regla global de operaciones lentas: el aviso debe estar pintado antes de la fase costosa, conservar un indicador visible de actividad y no provocar movimiento de controles por cambios de texto. El helper Qt usa repintado + `FreeCADGui.updateGui()` + procesamiento de eventos pendientes sin mover geometria a hilos secundarios.

La Casa demo activa el terreno ya implementado por `site_floor_utils`: `Arch.makeSite(..., baseobj=terrain)` con superficie plana verde recortada bajo la losa y etiqueta `Jardin - Demo`.


## Build 2026.09.01.7 - color visible del jardin

Correccion visual de la Casa demo: `Arch.makeSite` puede ocultar la Base/Terrain y mostrar la Shape del propio Site. La demo aplica ahora el mismo verde al Terrain y al `Arch Site`, y reaplica el estilo despues del recompute final. No cambia geometria, margen, recorte ni jerarquia BIM del jardin.

## Build 2026.09.01.8 - historial local de uso de comandos

Facil Arquitectura incorpora un registro local de uso compatible conceptualmente con el antecedente de ElectricCR. `usage_log.py` mantiene dos fuentes bajo `logs/`: `tool_usage.json` para acumulados por herramienta y `tool_events.jsonl` para la secuencia de eventos.

El enlace con la interfaz se realiza observando las `QAction` existentes; no se sustituyen, duplican ni envuelven los comandos funcionales de FA. Solo se registran acciones mientras Facil Arquitectura esta activo. El filtro reconoce comandos propios `FA_` y comandos nativos `Draft_`, `BIM_`, `Arch_` y `Sketcher_`, por lo que las futuras barras compactas de herramientas nativas quedaran cubiertas por el mismo historial.

Cada evento puede conservar `timestamp`, sesion, secuencia, equipo, comando, grupo/barra, etiqueta, comando/grupo anterior, segundos desde la accion anterior, documento activo y Workbench activo. El registro es exclusivamente local, no transmite datos, no modifica el documento FreeCAD y cualquier error de escritura se ignora para no interferir con la herramienta ejecutada.
Los archivos generados `logs/tool_usage*.json` y `logs/tool_events*.jsonl` quedan excluidos de Git/RELEASE por defecto; el nombre de archivo del documento puede registrarse, pero no su ruta local completa.

Este historial debe consultarse junto con el flujo funcional antes de agregar, retirar u ordenar herramientas. Los conteos por si solos no se consideran prueba suficiente de importancia operativa.

Validacion de esta integracion: comprobacion estatica y pruebas unitarias del logger fuera de FreeCAD. La conexion real de `QAction` debe comprobarse tambien en FreeCAD 1.1.3 durante la siguiente prueba GUI/MCP.



## Correccion 2026-09-01 - barras nativas y BIM Space en GameEngineExport

- FA vuelve a comprobar al activarse que existan y sean visibles las barras `FA Dibujo 2D`, `FA Snaps` y `FA Auxiliares BIM`; esto corrige recargas DEV donde `Initialize()` no se ejecutaba de nuevo.
- Las barras reutilizan comandos nativos registrados por FreeCAD; no duplican implementaciones Draft/BIM/Sketcher.
- GameEngineExport trata `IfcType=Space`, `Proxy.Type=Space` o `TypeId=Arch::Space` como volumen espacial semantico y lo excluye por defecto de la escena 3D.
- `GameExportExclude=True` sigue teniendo prioridad. `GameExportInclude=True` permite una inclusion intencional y explicita.
- La exclusion se aplica tambien a listas explicitas/guardadas y al filtro final de exportacion.
- Build FA asociado: `2026.09.01.9`.


## Build 2026.09.01.10 - simplificacion de interfaz e iconografia

- `FA Proyecto BIM` queda reducido a dos entradas de uso directo: importar referencia CAD y demo de edificio.
- `FA_RebuildBIMModel`, `FA_CreateBIMStructure`, `FA_CreateProject` y `FA_CreateMasterSketches` dejan la barra principal y permanecen disponibles en `Facil Arquitectura > Avanzado / compatibilidad`; no se elimina codigo ni compatibilidad.
- `FA_RebuildBIMModel` ya crea o reutiliza internamente Building y Level mediante `ensure_bim_structure()`, por lo que no necesita el boton separado de estructura para el flujo normal.
- `FA Plataforma` deja de ocupar una barra permanente. Sus comandos, junto con la ventana de servicio, pasan a `Facil Arquitectura > Especiales`.
- Las barras se ordenan por flujo de trabajo: Proyecto BIM -> Dibujo 2D -> Snaps -> Estructura BIM -> Aberturas BIM -> Recintos y cielos -> Techo BIM -> Auxiliares BIM.
- `FA Estructura BIM` se ordena como rejilla -> ejes -> muros -> columnas -> losa.
- `FA Aberturas BIM` agrupa primero el flujo de puertas, luego el de ventanas y finalmente la abertura generica.
- Se agregan iconos SVG diferenciados para crear puertas BIM, crear ventanas BIM, reconstruir modelo BIM y crear estructura BIM. Los comandos de centros de puertas/ventanas conservan sus iconos de ejes, evitando que una accion de analisis tenga el mismo icono que una accion de creacion BIM.
- No se cambian algoritmos geometricos ni datos del documento; el cambio es de interfaz, organizacion y recursos graficos.


## Normalizacion del arbol BIM - build 2026.09.01.11

### Contrato vigente

El arbol espacial autoritativo es `Site -> Building -> Level`. `FA_Project` deja de ser una segunda jerarquia normal y queda exclusivamente como compatibilidad cuando no puede resolverse un Level BIM.

Dentro del Level se admiten elementos arquitectonicos permanentes directos, sistemas funcionales como `Techo BIM` o `Cielos suspendidos`, y una unica rama `Auxiliares FA` para fuentes 2D, resultados documentales y tablas que necesiten persistir. No se crean grupos clasificadores solo para repetir lo que el Level ya expresa.

`ensure_bim_structure()` ejecuta una normalizacion conservadora de las ramas FA generadas. `migrate_legacy_support_to_level()` migra exclusivamente `FA_Parameters`, `FA_MasterSketches`, `FA_Areas` y `FA_Tables`; no toca grupos desconocidos del usuario. `adopt_auxiliary_sources()` mueve solo fuentes seguras. Un Sketch que ya sea Base nativa conserva esa dependencia como posicion canonica y no se agrega otra vez a Auxiliares.

Los comandos de centros, cierre de buques, deteccion de recintos, Spaces, puertas, ventanas, vanos, reconstruccion BIM, tablas y rotulos usan este contrato. La migracion no ocurre por el simple hecho de cargar el Workbench: se ejecuta dentro de operaciones FA que ya modifican el documento.

### Site y fuentes de piso

Las builds anteriores guardaban `FA_SourceSketches` como `App::PropertyLinkList` en Site/Slab solo para trazabilidad. FreeCAD podia reclamar esos Sketches como hijos visuales de `Sitio BIM`, creando un arbol confuso. Desde esta build Site/Slab guardan `FA_SourceSketchNames` como `StringList`; la dependencia geometrica real sigue en `FA_FloorFootprint.Sources` y la losa mantiene su Base nativa. En una reejecucion, cualquier `FA_SourceSketches` generado por FA se vacia.

### Spaces

`create_bim_spaces()` usa por defecto el Level directamente. Los grupos clasificadores `FA_BIMSpaces`/`FA_DemoSpaces` vacios se retiran. El Space mantiene `GameExportExclude=True` y su Base solida oculta conserva la misma exclusion.

### Cielo suspendido

La malla modular sigue siendo necesaria para calcular paneles, cortes y coordinacion con luminarias, pero no necesita ser un objeto permanente. `create_documentary_grid=False` es el valor predeterminado. La opcion GUI `Crear reticula 2D documental (opcional)` permite materializarla cuando se requiere una salida 2D; se marca `FA_DocumentaryOnly=True` y se enruta al grupo auxiliar/documental.

### Validacion

Pruebas fuera de FreeCAD: `23/23` aprobadas, incluyendo migracion de `FA_Project`, proteccion de grupos de usuario, Spaces directos al Level, reticula opt-in y eliminacion del enlace de trazabilidad Site->Sketch. Sintaxis Python aprobada. Falta la prueba real en FreeCAD 1.1.3 con los dos casos de referencia: Demo automatico y modelo construido manualmente desde Sketches.


## Correccion recurrente: docks despues de Hot restart - build 2026.09.02.2

Se confirmo en la Demo guiada un fallo recurrente de ciclo de vida Qt: el Hot restart reinicia globals Python, pero un `QDockWidget` puede permanecer vivo bajo `FreeCADGui.getMainWindow()`. La reapertura generaba un segundo `FA_DemoGuidedDock` y Qt comprimía la vista 3D.

El contrato vigente exige buscar todos los docks por `objectName`, retirar del layout los obsoletos antes de `deleteLater()`, no permitir que callbacks de docks viejos borren la referencia del reemplazo y no tocar `resizeDocks()`, `tabifyDockWidget()` ni `centralWidget`. `cmd_demo_building.register()` realiza la limpieza en cada recarga y `start_guided_demo()` repite la defensa antes de crear el panel. Esta regla se promovio tambien al documento general de requisitos recurrentes de paneles FreeCAD.
