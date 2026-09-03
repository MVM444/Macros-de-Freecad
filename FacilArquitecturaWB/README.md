# FacilArquitecturaWB


Workbench independiente para FreeCAD 1.1.3 orientado a crear una base arquitectonica BIM editable desde planos existentes o desde Sketches ya depurados.


Version vigente: `0.14.11` | build `2026.09.02.8`. Conserva sin cambios la baseline tecnica de FA Puertas BIM validada en la build `.3` (63/63 pruebas focales y smoke real de host/corte en FreeCAD 1.1.3) y agrega la integracion liviana para excluir los Espacios BIM de la geometria de GameEngineExport mediante `GameExportExclude=True`. Se conserva el tratamiento `BOUNDED`, pero GeometryIndex 1 del levantamiento 1416 sigue siendo una limitacion visual conocida y no se declara corregido; requiere revision manual hasta disponer de overrides persistentes por elemento. No se agregaran mas heuristicas geometricas para esa excepcion. `FA Techo desde rectangulo` mantiene la correccion de apoyo validada previamente. Al recargar con `FacilArquitecturaLoader.FCMacro`, la consola debe mostrar `VERSION CARGADA: v0.14.11 | build 2026.09.02.8`. Los proyectos heredados con `FA_Project` conservan tambien `FA_WorkbenchVersion` y `FA_WorkbenchBuild`.


## Instalacion independiente

La version publicable de Facil Arquitectura esta preparada para instalarse como un unico Addon. No requiere que el usuario instale por separado el componente comun de Recintos/Espacios usado durante el desarrollo. Durante DEV se prefiere la fuente compartida `CRBIMCore`; si esa fuente externa no existe, FA carga automaticamente una copia interna generada bajo `_bundled/CRBIMCore`.

La carpeta `_bundled` no es una segunda fuente de verdad: es un espejo de distribucion. Sus archivos no deben editarse manualmente; deben regenerarse desde el `CRBIMCore` compartido antes de cada RELEASE. La utilidad `tools/sync_bundled_crbimcore.py` permite sincronizarlo y comprobar hashes con `--check`. Una instalacion limpia debe probarse sin ningun `CRBIMCore` externo presente.

**English:** the publishable Addon is self-contained. A clean installation does not require a separate CRBIMCore installation; the bundled mirror is used automatically when the shared development package is unavailable.


## FA JSON visual + copia de errores - build 2026.09.02.7

`FA JSON` amplia el contrato bidireccional con `create_site_object`. La primera variante soportada es `object_type: "tree"`: crea/reutiliza un `App::Part` ligero con tronco y copa 3D, propiedades parametricas FA y un simbolo documental 2D (`<name>_Plan`) formado por circulo+cruz. Los objetos se agrupan en `FA_SiteObjects` y el grupo se enlaza bajo `Site` cuando el Site admite `addObject`, evitando una jerarquia paralela. La reejecucion del mismo `name` actualiza solo objetos previamente generados por FA JSON; si el nombre pertenece a un objeto ajeno, la operacion se rechaza.

El boton **Ejemplo** ahora genera tres arboles alrededor de la casa Demo canonica, de forma suficientemente visible para comprobar ChatGPT -> JSON -> FreeCAD. `Dry-run` informa `CREATE`/`UPDATE`, posicion, dimensiones, contenedor y simbolo 2D antes de escribir. La entrada sigue sin ejecutar Python arbitrario.

La pestana **Resultado** incorpora **Copiar resultado/error**. Todos los fallos de `Validar`, `Dry-run`, del dry-run previo a `Aplicar` y de la aplicacion final se convierten en `facil-arquitectura.command-result` estructurado con `ok=false`, `stage`, `error.type` y `error.message`, para copiarlo directamente de FreeCAD y pegarlo de vuelta en ChatGPT.

Validacion previa: `tests/test_json_command_core.py` 6/6 y `py_compile` de `json_command_core.py` + `cmd_json_inspector.py` aprobados. Pendiente: smoke real en FreeCAD 1.1.3 para confirmar geometria/colores, pertenencia al Site, Undo/Redo, reejecucion idempotente y copia al portapapeles.

## FA JSON bidireccional - build 2026.09.02.6

`FA_JSONInspector` (`FA JSON`) permanece a la par de `FA Demo edificio`, pero ahora es bidireccional. La pestana **Salida** conserva el snapshot determinista de solo lectura. La pestana **Entrada** permite pegar un sobre `facil-arquitectura.command` generado por ChatGPT/MCP, validarlo, ejecutar `dry-run` y solo despues aplicarlo mediante confirmacion explicita. La entrada no ejecuta Python arbitrario.

Operaciones iniciales admitidas: `set_properties` sobre propiedades existentes y soportadas; `apply_elements` para `windows`/`doors` reutilizando `ElementDataCore` y sus adaptadores; y `create_demo` para materializar una Demo desde una `specification` JSON completa. El snapshot `facil-arquitectura.snapshot` no se aplica directamente, evitando escrituras accidentales al pegar un diagnostico completo.

Cuando el documento proviene de `FA Demo edificio`, el snapshot reconoce el controlador `FA_DemoBuilding` e incorpora directamente su `SpecificationJSON`, `StepPlanJSON`, semilla, modo de ejecucion, paso actual y enlaces a fuentes, Spaces, cielorrasos y objetos generados. Para puertas y ventanas reutiliza los extractores existentes basados en `ElementDataCore`, por lo que no crea un segundo contrato de elementos. El dialogo permite actualizar, copiar al portapapeles y guardar un archivo `*.fa.json`.

Arquitectura: `core/json_snapshot_core.py` permanece independiente de FreeCAD/GUI/Qt; `commands/cmd_json_inspector.py` actua como adaptador FreeCAD y comando visible. Validacion previa: `py_compile` aprobado, contrato puro comprobado y prueba focal `tests/test_json_snapshot_core.py` agregada. Falta el smoke GUI en FreeCAD 1.1.3 despues de sincronizar/recargar el Workbench.

## Desarrollo asistido por inteligencia artificial

Facil Arquitectura ha sido desarrollada en gran parte mediante herramientas de inteligencia artificial, bajo direccion humana. Su codigo, arquitectura y comportamiento requieren revision y validacion por programadores profesionales antes de considerarla apta para entornos de produccion, uso critico o distribucion amplia.

**English:** Facil Arquitectura has been developed largely using artificial intelligence tools under human direction. Its source code, architecture, and behavior require review and validation by professional software developers before it should be considered suitable for production environments, critical use, or broad distribution.


## Cierre de interfaz y ayuda - build 2026.09.02.4

La interfaz principal se organiza por flujo de trabajo: `FA Proyecto BIM`, `FA DWG/DXF y preparacion 2D`, `FA Dibujo 2D`, `FA Snaps`, `FA Estructura BIM`, `FA Aberturas BIM`, `FA Recintos (Experimental)`, `FA Techos y cielorrasos` y `FA Auxiliares BIM`.

- `FA Proyecto BIM`: Demo edificio + FA JSON + Ayuda.
- `FA DWG/DXF y preparacion 2D`: Importar DWG/DXF + cerrar buques + recopilar rotulos de recintos.
- `FA Recintos (Experimental)`: deteccion/consulta/nombre y creacion de BIM Spaces. Su generacion sigue en desarrollo, pero BIM Space es el objeto previsto para compartir recinto, nombre, area, nivel y geometria con otros Workbenches de ingenieria e instalaciones.
- `FA Techos y cielorrasos`: integra techo, editor de ejes de cerchas y cielorraso modular por recinto/Space.

La Ayuda integrada incluye `Primeros pasos`, `DWG / DXF`, `Flujo de trabajo`, `Barras`, `Demo` e `Informacion`. El flujo recomendado desde CAD queda documentado de forma explicita: seleccionar escala/unidad del dibujo original y capas utiles; usar `FA Centros desde seleccion` para paredes, `FA Centros de ventanas` y `FA Centros de puertas`; revisar/cerrar buques cuando corresponda; generar paredes, puertas y ventanas BIM; crear/identificar Recintos/Espacios; dibujar un rectangulo sobre el perimetro de paredes para `FA Techo desde rectangulo`; y crear cielorraso preferiblemente a partir de BIM Spaces.

`FA Cielo 600x600` acepta BIM Spaces y recintos poligonales/rectangulares validos. Si no existe seleccion, busca recintos disponibles y da prioridad a BIM Spaces. La reticula siempre se calcula internamente; su objeto 2D documental permanente es opcional. Las luminarias compatibles existentes pueden reservar celdas sin ser desplazadas.

El flujo CAD se documenta de forma conservadora: DXF se importa directamente; DWG requiere un convertidor externo configurado en FreeCAD, normalmente ODA File Converter, o puede convertirse previamente a DXF. La reconstruccion desde CAD ha sido probada con un numero limitado de ejemplos y puede requerir seleccion cuidadosa de capas, limpieza y correccion manual; la Demo no se presenta como validacion de cualquier DWG.

Facil Arquitectura no pretende sustituir el trabajo de un arquitecto, dibujante especializado, modelador BIM ni las herramientas arquitectonicas existentes en FreeCAD. Su objetivo es facilitar un modelo arquitectonico rapido y suficientemente organizado para continuar trabajo de ingenieria, especialmente con otros Workbenches de ingenieria e instalaciones.

Se mantiene la base i18n Espanol/Ingles (`i18n.py` + fuente `.ts`). Antes de RELEASE queda obligatorio compilar/probar el catalogo `.qm` y completar el barrido de cualquier dialogo secundario aun no internacionalizado.


## Herramientas nativas integradas y contrato de exportacion - build 2026.09.01.10

El Workbench reutiliza directamente los comandos disponibles en FreeCAD 1.1.3 y los filtra con `FreeCADGui.listCommands()` para no duplicar implementaciones ni fallar cuando una herramienta opcional no este registrada. Se agregan barras compactas:

- `FA Dibujo 2D`: prefiere `BIM_Sketch` y usa `Sketcher_NewSketch` como fallback; incorpora Line, Wire, Rectangle, Circle, Polygon, Move, Rotate, Trimex, Upgrade, Downgrade y Draft->Sketch cuando existen.
- `FA Snaps`: Endpoint, Midpoint, Center, Intersection, Perpendicular y Ortho disponibles.
- `FA Auxiliares BIM`: Space, SectionPlane, Create2DViews, Stairs y SelectPlane cuando existen en la instalacion.

Al activar FA, una migracion idempotente revisa solamente los objetos generados por `FA_CreateBIMSpaces` (`FA_Role=bim_space` o `space_base`) y asegura `GameExportExclude=True`. Los Espacios nuevos ya reciben esa propiedad desde su creacion. La propiedad es un contrato de datos; FA no importa ni depende de GameEngineExportWB.


## Documentacion


- [Documentacion completa del workbench](DOCUMENTACION_WORKBENCH.md): arquitectura,
  comandos, flujo DXF-BIM, contratos de objetos, macros complementarias y caso validado
  de Puriscal.
- [Importacion controlada DWG/DXF](docs/IMPORTACION_CAD_DWG_DXF.md): unidades,
  conversion temporal, validacion y limitaciones de bloques.
- [Notas de investigacion](NOTES_RESEARCH.md): decisiones y referencias que dieron
  origen al alcance.


## Alcance inicial


El workbench importa DWG/DXF como referencia, pero no convierte DXF/PDF/imagenes automaticamente a BIM. Crea una estructura organizada, parametros, sketches maestros y muros BIM basicos usando herramientas existentes de FreeCAD/Arch/BIM.


Comandos incluidos:


- `FA_JSONInspector`: muestra un snapshot JSON read-only del documento activo y reconoce de forma directa la especificacion/guion de `FA_DemoBuilding`.
- `FA_ImportCADReference`: importa DWG/DXF en un documento nuevo con unidad real controlada y sin guardarlo.
- `FA_CreateBIMStructure`: crea o reutiliza un `Building` y un `Building Storey` nativos.
- `FA_RebuildBIMModel`: analiza los Sketches, permite corregir su asignacion y coordina la reconstruccion BIM completa.
- `FA_CreateProject`: crea `FA_Project`, grupos base y `Spreadsheet_Parametros`.
- `FA_CreateMasterSketches`: crea sketches maestros editables y vacios en XY.
- `FA_CenterlinesFromSelection`: crea `Sketch_Centros` desde shapes, layers, grupos o `Part::Feature` con `Shape` Compound. En paredes descompone sus bordes solo en memoria, reproduce el resultado estable de `Draft Downgrade / splitWires`, conserva la fuente y reemplaza de forma segura una ejecucion previa de la misma seleccion.
- `FA_WindowCenterlinesFromSelection`: crea un nuevo `Sketch_Centros` con un eje principal por shape de ventana.
- `FA_DoorCenterlinesFromSelection`: crea un nuevo `Sketch_Centros` con el eje cerrado de cada simbolo de puerta.
- `FA_CreateDoorsFromSketch`: crea puertas nativas Arch desde los ejes, resuelve el muro anfitrion y valida el corte real.
- `FA_ChangeDoorType`: cambia el preset BIM nativo de una o varias puertas existentes sin perder identidad, dimensiones, Placement, host ni trazabilidad.
- `FA_CreateWindowsFromSketch`: crea ventanas nativas Arch desde los ejes, con altura y antepecho configurables, y valida el corte real.
- `FA_WindowTable`: crea, extrae, valida, importa, exporta y aplica `Spreadsheet_Ventanas` sobre ventanas BIM nativas.
- `FA_DoorTable`: crea, extrae, valida, importa, exporta y aplica `Spreadsheet_Puertas`; admite presets instalados, nombre logico de tipo, puerta doble FA, bisagra y sentido de apertura.
- `FA_CreateOpeningsFromSketch`: crea solamente vanos BIM nativos desde las lineas de uno o varios Sketches.
- `FA_InsertDoubleDoorBIM`: inserta una puerta Arch/BIM Europa de dos hojas, libre o alojada en un muro seleccionado.
- `FA_CloseWallSketch`: acepta un muro BIM, su Sketch Base o un Sketch generico; completa los metadatos faltantes y cierra los buques validados por puertas o ventanas.
- `FA_CreateSampleGeometry`: agrega geometria simple de muestra a sketches vacios solo para pruebas.
- `FA_CreateWallsFromSketch`: crea un muro BIM con `Arch.makeWall` y `Base` directa desde cualquier Sketch seleccionado; si faltan espesor, altura o clasificacion solicita esos datos.
- `FA_CreateColumnsFromSketch`: convierte dos familias de lineas de un Sketch en `Arch Axis`, un `AxisSystem` y columnas `Arch Structure` colocadas en sus cruces reales.
- `FA_CreateBuildingGrid`: crea una cuadricula nativa `ArchGrid` auxiliar dentro del Level; no crea ni sustituye muros BIM.
- `FA_CreateSiteFloorBIM`: crea/reutiliza `Site -> Building -> Level`, aloja la losa en el Level y puede recortar el terreno de prueba bajo la huella.
- `FA_CollectRoomLabels`: recopila rotulos de recintos, consolida duplicados y actualiza `Spreadsheet_Rotulos_Recintos`.
- `FA_CreateModularCeiling`: genera cielos suspendidos por recintos rectangulares o poligonales dentro del Level, recorta la reticula nominal de 600x600 mm y reserva celdas de luminarias compatibles.
- `FA_CreateServicePlatformFront`: crea una plataforma compacta desde una arista recta o un Sketch con exactamente una linea principal.
- `FA_UpdateServicePlatformFront`: relee la linea fuente y actualiza cuerpo y vidrios en los mismos objetos, sin duplicarlos.
- `FA_AddCashierServiceWindow`: deja previsto y validado el flujo independiente para una futura ventanilla de caja alojada en un muro BIM.


## Tablas de elementos


Desde la build `2026.09.01.11`, las hojas gestionadas por ElementDataCore se alojan en `Level -> Auxiliares FA` cuando existe un Level BIM inequívoco. Solo documentos sin contexto BIM suficiente conservan como fallback compatible `FA_Project/06_Tables`. `FA Tabla de ventanas` reutiliza/mueve su hoja existente y `FA Tabla de puertas` crea `Spreadsheet_Puertas` sin forzar un segundo arbol cuando el Level ya existe. El Sketch actual manda en posicion, orientacion y ancho; las tablas mandan en propiedades transferibles.


Para puertas, `DoorType` es un nombre logico editable y `TypeRef` identifica el preset/factory real. Los presets de puerta instalados en FreeCAD se descubren dinamicamente. La puerta doble de FA usa `TypeSource=fa_double` y `TypeRef=architecture.door.double_leaf.glazed.europa`. La tabla conserva bisagra (`START/END/BOTH`), lado de apertura y `OpensInward`.


## Reconstruccion BIM nativa desde Sketches


El flujo nuevo no crea `FA_Project` ni una jerarquia paralela. En un documento que
contenga Sketches depurados, ejecute `FA Reconstruir modelo BIM`, revise las
asignaciones propuestas y confirme. La clasificacion usa primero `FA_Role`,
`FA_ElementType`, `FA_CenterlineKind` y propiedades dimensionales; despues usa
`Name`/`Label`, y finalmente permite asignacion manual.


Resultado principal:


```text
Building
`-- Level / Building Storey
    |-- Sketch de muros
    |-- Wall (Base = Sketch de muros)
    |-- Columns / AxisSystem
    |-- Doors (Hosts = Wall)
    `-- Windows (Hosts = Wall)
```


Los comandos antiguos `FA_CreateWallsBIM`, `FA_CreateAxesColumnsBIM`,
`FA_CreateDoorsBIM` y `FA_CreateWindowsBIM` permanecen registrados como aliases de
compatibilidad. Desde v0.14.0 la losa se integra al `Level`; los `Space` nativos
continuan como fase posterior hasta validar el flujo de Areas/Wires/Spaces.


La prueba sobre una copia de La Cruz 2.1 confirmo un muro con Base Sketch directa,
14 columnas, huecos reales de puerta/ventana, guardado/reapertura, idempotencia y
Undo/Redo. Consulte [el resultado tecnico](RESULTADO_CODEX_RECONSTRUCCION_BIM.md).


## Plataforma de atencion desde una linea


1. Dibuje o seleccione una arista recta, o un `Sketcher::SketchObject` con exactamente una linea no constructiva.
2. Ejecute `FA Plataforma desde linea`.
3. Indique puestos, lado del funcionario mirando de P0 hacia P1, alturas y profundidades. `Invertir direccion` intercambia P0/P1 sin cambiar implicitamente el lado escogido.
4. Para regenerar, edite las propiedades del objeto `Plataforma de atencion`, seleccione el objeto o uno de sus dos hijos y ejecute `FA Actualizar frente de plataforma`.


La linea es la autoridad para longitud, posicion y orientacion. Un frente de 3000 mm con tres puestos produce modulos exactos de 1000 mm, sin descontar margenes. Si existe un muro BIM colineal se enlaza en `HostWall`; no se crea ni duplica ningun muro. El arbol visible queda compacto:


```text
Plataforma de atencion
|-- Cuerpo_Plataforma
`-- Vidrios_Plataforma
```


Las areas de funcionario/publico estan desactivadas por defecto (`MostrarAreasAtencion = false`). La hoja `Spreadsheet_Platform` permanece oculta como respaldo compatible. Los frentes historicos con seis sketches y zonas conservan su generador y su ruta de actualizacion anterior.


Cada puesto crea una abertura geometrica real dentro de `Vidrios_Plataforma`, sin objetos visibles adicionales. Se controla con `MostrarAberturaVidrio`, `AnchoAberturaVidrio`, `AltoAberturaVidrio` y `AlturaAberturaVidrio`; esta ultima es la cota inferior absoluta desde la base local de la plataforma. Al cambiar estas propiedades, `FA Actualizar frente de plataforma` regenera los mismos dos objetos sin duplicarlos.


La referencia `PL-01`, paginas 33-34 de `Guia Estandarizacion 050626 2`, respalda la altura de mostrador de 740 mm y la cota superior del vidrio de 1800 mm. No muestra de forma inequivoca el ancho y alto del hueco frontal: los 300 x 300 mm iniciales son un valor de modelado provisional y editable, no una dimension normativa. El objeto lo registra como `FA_GlassOpeningDimensionStatus = PROVISIONAL_EDITABLE_NO_NORMATIVO`. La herramienta tampoco genera el recinto completo de caja.


## Puertas y ventanas BIM


Flujo de puertas:


```text
FA Centros de puertas -> seleccionar Sketch de ejes -> FA Puertas BIM
```


Flujo de ventanas:


```text
FA Centros de ventanas -> seleccionar Sketch de ejes -> FA Ventanas BIM
```


Se pueden seleccionar tambien uno o varios muros BIM junto con los Sketches. Si no se
seleccionan muros, el comando examina los muros BIM del documento. El anfitrion se
elige por orientacion, distancia al eje, proyeccion sobre soporte colineal y cota Z;
si dos muros resultan equivalentes el eje se omite como ambiguo. El ancho siempre
proviene de la linea fuente. Cada resultado es un `ArchWindow._Window` con
`IfcType = Door` o `IfcType = Window`, Sketch `Base`, `Hosts = [muro]`,
`MoveWithHost = True` y trazabilidad `FA_*`.


### Tabla de ventanas


`FA Tabla de ventanas`, dentro de la barra `FA Aberturas BIM`, usa una unica
`Spreadsheet_Ventanas` por documento. Puede llenarse desde ventanas BIM
existentes o editarse como plantilla y transferirse mediante copia nativa de la
Spreadsheet o archivo CSV nativo.


Al validar/aplicar, el Sketch actual manda sobre posicion, orientacion y ancho;
la tabla manda sobre altura, antepecho, preset y propiedades transferibles; el
documento destino vuelve a resolver `Hosts`, Level y relaciones BIM. La
validacion no modifica el modelo y clasifica cada fila como `MATCH`, `CAMBIO`,
`NO_MATCH` o `AMBIGUO`. `Aplicar` siempre muestra primero el dry-run y nunca
aplica coincidencias ambiguas.


El CSV de `Spreadsheet::Sheet` comprobado en FreeCAD 1.1.3 es UTF-8 y queda
separado por tabuladores aunque su extension sea `.csv`. Para una transferencia
completa dentro de FreeCAD tambien puede copiarse la Spreadsheet entre
documentos.


Desde la version 0.9.0 la seleccion explicita de un Sketch de abertura tiene
prioridad sobre metadatos historicos incorrectos como `FA_CenterlineKind = walls`,
siempre que el Sketch no tenga espesor de muro ni sea una Base generada. Tambien se
aceptan Sketches seleccionados mediante `App::Link`. Si no se
selecciona un Sketch valido, el comando busca automaticamente en el documento una
fuente identificada por nombre o metadatos, por ejemplo `Sketch_Centros_Ventanas` o
`FA_CenterlineKind = windows`. Los Sketches genericos no identificados nunca se usan
automaticamente.


Reejecutar reemplaza solamente resultados del mismo comando y fuente. Los objetos
manuales y las 27 aberturas historicas de Puriscal se reconocen y no se duplican.


### Cambiar el tipo de puertas existentes


Seleccione una o varias puertas `ArchWindow` con `IfcType = Door` y ejecute
`FA Cambiar tipo de puerta` en la barra `FA Aberturas BIM`. El dialogo consulta en
tiempo real `ArchWindowPresets.WindowPresets`; en FreeCAD 1.1.3 instalado se
detectaron `Simple door` y `Glass door`. No se muestra `Sliding door` porque esa
instalacion no lo incluye.


El cambio conserva la misma identidad del objeto y transfiere desde un preset
nativo temporal solamente `Base`, `WindowParts`, `Preset`, `Frame` y `Offset`.
Despues restaura y valida ancho, alto, Placement, Hosts, Normal, apertura,
contenedor, propiedades `FA_*` y el corte real del Wall. Los auxiliares temporales
se eliminan solo despues de validar. Las puertas dobles especiales de FA se
rechazan sin modificarlas porque su familia de dos hojas no es compatible con los
presets simples instalados.


En la version 0.13.1 se corrigio el boton `Aplicar`: Qt clasifica ese boton como
`ApplyRole` y no emite automaticamente la señal `accepted`, por lo que ahora el
clic se conecta de forma explicita con la aceptacion del dialogo.


Una puerta procedente de `FA_CreateDoorsFromSketch` recibe
`FA_TypeOverride = true`. El Sketch fuente guarda por indice el mapa JSON
`FA_DoorTypeOverrides`, por lo que una regeneracion posterior respeta la excepcion
individual sin cambiar las otras lineas del Sketch.


### Aberturas BIM sin puerta ni ventana


Seleccione uno o varios Sketches de vanos y ejecute `FA Aberturas BIM desde Sketch`
en la barra `FA Aberturas BIM`. Cada linea recta genera una instancia independiente:
su longitud define el ancho y todos los ejes del mismo Sketch comparten la altura y
la altura desde piso indicadas en el dialogo (2100 y 0 mm inicialmente).


El resultado es un `ArchWindow._Window` nativo con `IfcType = Opening Element`,
`WindowParts = []`, sin solidos, simbolos, hoja, marco ni vidrio. Su perfil cerrado
permanece oculto y el Wall se perfora mediante `Hosts` y `getSubVolume()` de
FreeCAD. La reejecucion reemplaza exclusivamente objetos con
`FA_GeneratedBy = FA_CreateOpeningsFromSketch` de los Sketches seleccionados.


La puerta doble se inserta desde la barra `FA Aberturas BIM`. Si se selecciona un
muro, conviene pulsar primero el punto deseado sobre el muro y luego ejecutar
`FA Insertar puerta doble BIM`; el comando alinea la puerta con el eje, conserva
`Hosts` y `MoveWithHost`, y valida el hueco real. `Hosts` es la unica relacion BIM
autoritativa al muro; `FA_HostWallName` conserva su nombre estable sin crear enlaces
inversos duplicados. Sin muro seleccionado solicita
X, Y, Z y rotacion para crear una puerta BIM libre.


Desde v0.11.0 las herramientas se presentan en cinco barras tematicas:
`FA Proyecto BIM`, `FA Estructura BIM`, `FA Aberturas BIM`, `FA Recintos y cielos`
y `FA Plataforma`. Los comandos no se movieron ni se eliminaron; solamente cambio
su agrupacion visible.


## Instalacion


Copiar la carpeta `FacilArquitecturaWB` al directorio `Mod` de FreeCAD o mantenerla en una ruta que FreeCAD cargue como Mod.


Durante desarrollo, tambien puede ejecutarse la macro `FacilArquitecturaLoader.FCMacro` desde la raiz del directorio de macros. Esa macro agrega `Macros-de-Freecad` a `sys.path`, recarga `FacilArquitecturaWB` y activa el workbench sin tener que reiniciar FreeCAD.


Estructura esperada:


```text
Mod/
  FacilArquitecturaWB/
    Init.py
    InitGui.py
    commands/
    core/
    resources/
```


Luego abrir FreeCAD 1.1.3 y seleccionar el workbench visible como `Facil Arquitectura`.


## Prueba rapida


1. Activar `Facil Arquitectura`.
2. Abrir un documento con Sketches depurados.
3. Ejecutar `FA Reconstruir modelo BIM`.
4. Confirmar o corregir los Sketches de muros, columnas, puertas, ventanas y referencias.
5. Confirmar. El resultado queda dentro de `Building -> Level` y puede seguirse editando con BIM.


Como alternativa, se pueden ejecutar por separado `FA Crear estructura BIM`,
`FA Muros BIM desde Sketch`, `FA Columnas BIM desde Sketch`, `FA Puertas BIM` y
`FA Ventanas BIM`.


Si solo se quiere probar el flujo sin un plano real, ejecutar `FA Crear geometria de muestra` antes de crear los muros BIM.


## Centros desde DXF


Si un DXF importado contiene shapes de muros, ventanas, puertas u otros elementos dentro de un layer o grupo:


1. Seleccionar el layer, grupo o los shapes del mismo tipo.
2. Ejecutar `FA Centros desde seleccion`.
3. Revisar el nuevo sketch `Sketch_Centros_<nombre de la seleccion>`.
4. Copiar o adaptar esas lineas al sketch maestro que corresponda.


Cada ejecucion registra `FA_ElementType`, `FA_ExtractionMode`, `FA_ExtractionStrategy` y los nombres de fuente. Si se procesa de nuevo exactamente la misma seleccion con la misma estrategia, reemplaza solamente sus Sketches FA anteriores; otras selecciones, estrategias y Sketches manuales se conservan.


Los layers que contienen instancias `App::Link`, como los objetos `LinkU` de bloques DXF, se procesan usando el `Shape` transformado de cada link. La propiedad `Group` reenviada por el objeto enlazado no se recorre como un grupo normal; asi se conservan todas las posiciones de las instancias y no se agregan los shapes base ocultos.


Desde v0.14.2, un `Part::Feature` cuyo `ShapeType` sea `Compound` y se procese con la estrategia automatica se descompone **virtualmente por bordes**, igual que `Draft Downgrade / splitWires`. El objeto fuente no se modifica ni se crean objetos intermedios. Las instancias `App::Link`, puertas, ventanas, Shapes no Compound y tipos Part derivados conservan su ruta anterior. `Pared_Concreto001` del levantamiento 1416 fue validado en FreeCAD 1.1.3: 37 lineas de muro de 150 mm y una cruz de columna de 2 lineas, identicas al flujo de 140 bordes explotados.


Cuando puede medir la distancia entre caras o el ancho de un perfil cerrado, el comando general separa los ejes en sketches como `..._Espesor_100mm` y `..._Espesor_200mm`. Espesores con diferencias de hasta 10 mm se consideran el mismo grupo. La propiedad `FA_WallThickness` conserva el valor representativo y el sketch principal usa `FA_RelatedCenterlineSketches` para enlazar los sketches adicionales de la misma ejecucion.


Antes de crear los sketches, los tramos colineales cortados dentro de una misma zona continua de muro se consolidan y sus extremos cercanos se llevan al cruce real de los ejes. Un eje que sobrepasa una esquina se recorta hasta la interseccion. Si existe una linea de cierre transversal, ese extremo representa el borde real del muro y nunca se prolonga dentro de otra pared, aunque sus ejes esten cercanos. Se agregan restricciones `Horizontal`, `Vertical`, `Coincident` y `PointOnObject` cuando son geometricamente seguras; las diagonales se conservan sin forzarlas a ortogonales.


Cuando el DXF importa cada borde como un Shape independiente, el comando reconstruye los remates usando tambien las lineas cortas que no califican como caras longitudinales. Si una cara longitudinal esta fragmentada, recompone sus tramos hasta el remate real; no los une cuando existe una linea perpendicular de cierre. Los perfiles rectangulares compactos, proporcionados y con al menos 82% de area llena se interpretan como columnas y generan dos ejes en cruz dentro de un sketch adicional `..._Columnas`, en vez de mezclarse con los grupos de espesor de paredes.


`FA Centros` nunca acepta un `Sketch_Centros_...` previamente generado como fuente. Reprocesar los ejes como si fueran caras produce espesores falsos y cruces incorrectos; por eso el comando elimina esos objetos de una seleccion mixta y cancela la operacion si no queda geometria original. Para reducir falsos positivos en esquinas, una cruz de columna requiere actualmente un perfil cerrado con lado menor de al menos 250 mm.


La creacion completa de todos los sketches de una ejecucion usa una sola transaccion documental: `Ctrl+Z` elimina el resultado completo. `FA Muros BIM desde centros` usa una segunda transaccion y crea un `Arch Wall` por Sketch, manteniendo ese Sketch como `Base` parametrica. El muro vincula `Width` con `FA_WallThickness` y `Height` con `FA_WallHeight`; editar las lineas o esas propiedades recompone el objeto BIM. Si se selecciona el sketch principal, tambien procesa automaticamente su lista `FA_RelatedCenterlineSketches`.


Un Sketch generico ya no se rechaza. El comando muestra los Sketches sin contrato de muro y solicita espesor, altura y clasificacion. Al aceptar agrega `FA_WallThickness`, `FA_WallHeight`, `FA_Role = centerlines`, `FA_CenterlineKind = walls` y `FA_ElementType`, sin modificar la geometria. Si el Sketch tenia otro rol o tipo, los conserva como `FA_PreviousRole` y `FA_PreviousElementType`. Las dimensiones positivas ya existentes nunca se sustituyen. Cancelar el dialogo no modifica el Sketch.


Los errores corregibles, como no seleccionar un objeto o seleccionar el tipo equivocado, se muestran como una advertencia breve y no producen el bloque `Running the Python command failed`. Los fallos internos tampoco se propagan al ejecutor de comandos; conservan un detalle tecnico identificado con `[FACILARQ]` en `Report view`.


`FA Ejes y columnas BIM` usa el sketch seleccionado como fuente. Agrupa lineas colineales, conserva separaciones no uniformes y admite una reticula rotada siempre que tenga exactamente dos familias no paralelas. Crea las familias con `Arch.makeAxis` y las agrupa con `Arch.makeAxisSystem`. Si una reticula completa esta alineada con X/Y, asigna el sistema a una sola columna `Arch.makeStructure` para que BIM la replique. Si la reticula esta incompleta o girada, crea columnas BIM solo en los cruces presentes en el sketch; asi evita columnas inventadas y conserva su orientacion. El sketch conserva `FA_AxisExtension`, `FA_AxisTolerance`, `FA_ColumnWidth`, `FA_ColumnDepth` y `FA_ColumnHeight`. Cambiar las dimensiones actualiza y mantiene centradas las columnas; cambiar la posicion de los ejes requiere volver a ejecutar el comando. La operacion completa admite `Ctrl+Z`.


`FA Cuadricula ArchGrid de referencia` crea un `ArchGrid` mediante `Arch.makeGrid()` como ayuda geometrica, no como generador de paredes. Prefiere `Sketch_Cerrado_*` cuando existe y mantiene trazabilidad hacia sketches de muros y aberturas. Como `ArchGrid` prolonga sus filas y columnas por todo el rectangulo, se conserva oculto y una representacion recortada muestra los tramos utiles. Desde v0.14.0 este comando no ejecuta `Arch.makeWall`, no crea `FA_ReconstructedWallBase` y no oculta los muros BIM originales. La creacion de muros se realiza solamente con `FA Muros BIM desde Sketch`. Si una reejecucion encuentra una salida legacy de pared reconstruida, elimina exclusivamente aquella salida generada y restaura la visibilidad de los muros FA que la version anterior podia haber ocultado. `grid_primary_support_mm`, `grid_cluster_tolerance_mm` y `grid_max_lines_per_direction` siguen controlando la simplificacion semantica del ArchGrid.


Para ventanas con marcos u otros detalles internos, usar `FA Centros de ventanas`. Este comando agrupa primero shapes y bordes separados hasta 250 mm que parecen formar una misma ventana y luego genera un unico eje principal por grupo. El comando general permanece disponible para muros de cualquier material, espesores diferentes y geometria representada por pares de bordes.


Para puertas con hoja y arco de giro, usar `FA Centros de puertas`. El comando agrupa los detalles del simbolo, identifica la radial que coincide con la hoja abierta y genera la radial opuesta como eje del buque cerrado. Si el arco circular no se puede reconocer, usa el eje dominante del grupo como respaldo y lo informa en la consola.


`FA Cerrar buques de puertas y ventanas` acepta uno o mas muros BIM, sus Sketches Base o Sketches genericos de pared. Puede seleccionarse tambien los Sketches de puertas y ventanas que delimitan el alcance; sin ellos, los identifica por `FA_CenterlineKind` y por compatibilidad historica. La abertura se analiza primero como evidencia local: se agrupan solamente ejes consecutivos sobre la misma pared, se buscan soportes colineales a ambos lados y se exige un candidato unico. Una abertura mayor que el limite generico puede justificar su propio buque; una puerta junto a esquina o T extiende unicamente el tramo de su eje hasta la pared de apoyo, sin mover ni borrar esa pared. Los candidatos equivalentes quedan `AMBIGUOUS` y no se aplican. `diagnose_closed_wall_sketches(...)` y `diagnose_wall_gap_closures(...)` devuelven un plan JSON-compatible y no modifican el documento. El resultado no destructivo `Sketch_Cerrado_*` conserva `Placement`, espesor, altura y metadatos, agrega restricciones y trazabilidad por Sketch/`GeometryIndex`. Por defecto no se cierra ninguna discontinuidad sin evidencia de puerta, ventana o el fallback avanzado de mochetas.


Limitaciones actuales:


- Para perfiles cerrados o shapes complejos y alargados obtiene un eje principal, util para muchas representaciones de ventanas y puertas.
- Si el DXF trae elementos como dos lineas de borde, las empareja por direccion, separacion y solape para crear una linea central.
- Admite geometria ortogonal y diagonal. Un borde largo puede emparejarse con varios tramos cortos.
- Los contornos compactos ambiguos que no tienen una direccion dominante se omiten; el conteo queda en `FA_IgnoredCompactCount`.
- Geometria DXF abierta, muy fragmentada o con separaciones mayores a 800 mm entre caras puede requerir ajuste manual.
- Las uniones entre sketches de espesores distintos coinciden geometricamente, pero no reciben una restriccion cruzada entre documentos Sketcher independientes.


Estructura esperada en documentos nuevos:


- `Building` BIM nativo como edificio autoritativo.
- `Building Storey` (`Nivel 00` por defecto) como residencia de los elementos arquitectonicos permanentes.
- `FA_Project` reservado para datos y auxiliares que realmente se necesiten; `FA Crear proyecto` no crea ramas legacy vacias.
- `Spreadsheet_Parametros` dentro de `FA_Parameters`.
- Sketches maestros dentro de `FA_MasterSketches` solo cuando se ejecuta su comando.
- Cuadriculas, trazados de construccion y otras salidas auxiliares dentro de una rama `Auxiliares FA` del Level cuando deban persistir.
- Las referencias temporales de importacion CAD pueden permanecer en la raiz del documento y no se consideran parte del modelo BIM terminado.


**Regla de residencia de objetos:** toda herramienta de Facil Arquitectura que cree un objeto permanente debe insertarlo automaticamente en la estructura espacial y funcional correcta del edificio, usando preferentemente la contencion BIM nativa `Building -> Level`. Los objetos temporales, de diagnostico, construccion o compatibilidad deben ubicarse en ramas auxiliares y, cuando corresponda, permanecer ocultos. Las relaciones nativas `Base`, `Host`, `Group` y equivalentes tienen prioridad sobre grupos paralelos creados solo para ordenar visualmente.


## Decisiones aplicadas desde NOTES_RESEARCH.md


- Usar el importador DXF existente de FreeCAD/Draft en futuras etapas; no crear importador propio.
- Usar Arch/BIM para muros y objetos arquitectonicos; no reinventar BIM.
- Tratar DWG, PDF e imagenes como flujos futuros o referencias externas, no como conversion automatica inicial.
- Crear sketches maestros por sistema/tipo constructivo, no un sketch por objeto.
- Mantener el workbench como orquestador simple y robusto.


## Pendientes


Actualizado: 2026-08-23. Esta seccion es la fuente de verdad de pendientes funcionales de Facil Arquitectura. No implica autorizacion para modificar codigo sin revisar primero la implementacion vigente, las dependencias nativas de FreeCAD 1.1.3 y el comportamiento real del documento.


### 1. Estructura BIM y arbol de trabajo


**Estado 2026-08-27:** REGLA CANONICA INCORPORADA / VALIDACION EN FREECAD PENDIENTE. Los objetos permanentes de los comandos BIM actuales usan `Building -> Level`. Los comandos `FA Crear proyecto`, sketches maestros, centros de paredes/puertas/ventanas, cierre de buques, recopilacion de rotulos y geometria de muestra crean solo las ramas auxiliares que realmente necesitan; ya no materializan el arbol legacy completo por efecto lateral. `FA_CreateBuildingGrid` enruta su salida de referencia a `Auxiliares FA` dentro del Level.


- Consolidar la estructura final alrededor de `Site -> Building -> Level` y evitar ramas paralelas que saquen elementos terminados del modelo BIM.
- Asociar los elementos arquitectonicos generados al nivel correspondiente sin crear grupos o niveles artificiales cuando FreeCAD ya exprese la relacion mediante `Base`, `Host`, `Group` u otras relaciones nativas.
- Evitar apariciones duplicadas en el arbol causadas por agrupaciones explicitas innecesarias.
- Mantener como criterio de UX: Facil Arquitectura debe ser facil primero, correcto siempre y tan exacto como sea razonablemente posible.


### 2. `FA_CreateBuildingGrid` como herramienta auxiliar


**Estado 0.14.0:** IMPLEMENTADO EN CODIGO / VALIDACION EN FREECAD PENDIENTE.


- `FA_CreateBuildingGrid` / `ArchGrid` queda como referencia y ayuda de reconstruccion dentro del Level.
- Ya no genera automaticamente muros BIM ni oculta/sustituye los muros existentes. La reejecucion detecta la salida legacy de pared reconstruida y restaura la visibilidad de los muros FA que aquella version podia haber ocultado.
- La creacion de muros permanece en la accion explicita `FA_CreateWallsFromSketch`.
- La preparacion/correccion de geometria fuente permanece separada de la creacion BIM.


### 3. Puertas BIM


- Diagnosticar y corregir duplicados para garantizar conceptualmente `1 linea de Sketch -> 1 puerta`.
- Mantener identificacion estable de cada instancia entre regeneraciones.
- Al actualizar desde `FA_CreateDoorsFromSketch`, conservar bisagra, sentido de apertura y porcentaje/estado visual de apertura.
- No borrar y recrear ciegamente puertas existentes si puede preservarse su identidad.
- Diagnosticar el caso en que una puerta cercana a un encuentro perpendicular recorta de mas el muro; revisar tramo anfitrion, `Normal`, `HoleDepth`, `Hosts` y geometria real del buque antes de corregir.
- La longitud de la linea del Sketch no se considera por si sola un ancho legitimo: representa principalmente ubicacion, orientacion y una estimacion inicial.


### 4. Resolver aberturas de puertas y ventanas con logica comun


- Crear un resolvedor comun de aberturas para puertas y ventanas.
- Usar el muro anfitrion y el tramo correcto como referencia geometrica principal.
- Usar muros vecinos/perpendiculares como referencias fuertes cuando un extremo de la linea llegue o quede muy cerca de ellos.
- No introducir separaciones automaticas si la fuente indica que la abertura llega al encuentro.
- Separar claramente posicion aproximada, ancho inferido y ancho final del buque.
- Resolver el buque antes de crear la puerta o ventana BIM.


### 5. Sketches de puertas y ventanas - pendiente conceptual


- Estudiar ayudas graficas para visualizar las caras reales del muro cuando el Sketch de muros contiene solo ejes y el espesor vive como parametro.
- Estudiar restricciones minimas de posicion/alineacion con el muro sin volver complejo el flujo.
- Mantener este punto como investigacion conceptual por ahora; no exige automatizacion inmediata.


### 6. Ventanas BIM


- Aplicar el mismo resolvedor geometrico de aberturas usado por puertas.
- Mantener el principio `1 Sketch = 1 familia/tipo + N instancias`.
- Integrar una tabla/Spreadsheet de parametros comunes de familia cuando corresponda (altura, antepecho, preset/tipo BIM, marco/material y otros parametros comunes).
- Evitar duplicar como entrada editable un ancho que pueda derivarse de la geometria resuelta.
- Asociar correctamente ventanas con Wall, Level y, cuando sea util, Space.


### 7. Areas, recintos, Wires y Spaces BIM


- Integrar en FA las herramientas de areas ya existentes antes de crear soluciones paralelas.
- Prioridad: recintos desde muros BIM.
- Mantener `Draft Wire` cerrado como geometria maestra sencilla, editable y compartida.
- Conservar herramientas de apoyo como recinto por click y poligono desde limites seleccionados para casos incompletos.
- Compartir los Wires con otros Workbenches y consumidores de ingenieria, iluminacion, incendios, cielos e instalaciones.
- Evolucionar hacia `Arch Space` / Space BIM nativo como representacion arquitectonica final cuando funcione correctamente, manteniendo compatibilidad con Areas legacy mientras sea necesario.
- Normalizar nombre, area, perimetro, nivel e identificacion estable del recinto.


### 8. `FA_CollectRoomLabels`


- Usar Upala como caso de regresion para diagnosticar por que no se detectan determinados textos DXF.
- Revisar tipos reales de objeto de texto, visibilidad de capas/grupos padre, alcance de busqueda fuera de `FA_Project` y posible contenido dentro de bloques.
- No corregir por suposicion: primero identificar el tipo real de objeto y la ruta por la que llega al documento.


### 9. `FA_CreateSiteFloorBIM` - Piso BIM y Terreno


**Estado 0.14.0:** IMPLEMENTADO EN CODIGO / VALIDACION EN FREECAD PENDIENTE. La losa se contiene en el `Level`, el `Site` contiene el `Building` y el terreno de prueba dispone de `CutUnderBuilding` para no generar caras bajo la huella.


- Verificar en FreeCAD real la integracion clara de Site, terreno y piso/losa dentro del arbol BIM.
- Separar responsabilidades actualmente ambiguas entre `Site`, terreno y huella/losa.
- Asociar piso/losa al Level correcto.
- Revisar grupos o niveles intermedios innecesarios y visibilidades inconsistentes.
- Validar el recorte del terreno bajo la losa/edificio para confirmar que no queden caras superpuestas ni huecos no deseados.
- Conservar la geometria original necesaria del terreno sin destruir informacion de referencia.
- Verificar que el resultado sea estable para secciones, TechDraw, DXF y documentacion 2D.


### 10. `FA_CreateModularCeiling` - Cielos suspendidos


**Estado 0.14.0:** INTEGRACION AL LEVEL IMPLEMENTADA EN CODIGO / VALIDACION EN FREECAD PENDIENTE. El grupo `FA_Ceilings` se mueve a un unico contenedor `Level`; el Spreadsheet queda fuera del arbol geometrico cuando no existe un grupo documental legacy.


- Conservar el algoritmo actual de modulacion, recorte, alineacion con luminarias, reserva de celdas y cuadro de cantidades.
- Validar que los cielos permanezcan dentro del Level sin ramas duplicadas ni referencias rotas.
- Relacionar cada cielo con su recinto/Space fuente.
- Estudiar en FreeCAD 1.1.3 si `Covering` / `IfcCovering` con `PredefinedType = CEILING` es una base nativa adecuada antes de reemplazar la representacion actual.
- Separar conceptualmente cielo constructivo BIM, reticula auxiliar/documental y Spreadsheet.


### 11. Rendimiento y compatibilidad del importador


**Estado 0.14.4:** WORKAROUND PRODUCTIVO PARA FREECAD #31637 / PENDIENTE
VALIDACION MANUAL DEL USUARIO. FreeCAD 1.1.3 deja activo un `WaitCursor` global
despues de ciertas importaciones DXF por Python. FA detecta estructuralmente el
patron antiguo en `importDXF._import_dxf_file()` y neutraliza
`suspendWaitCursor`/`resumeWaitCursor` solamente durante `importDXF.insert()`.
Las funciones nativas se restauran en `finally`, incluso ante excepciones.


La compatibilidad se desactiva automaticamente cuando el importador instalado ya
no contiene el par problematico. Un estado `unknown` no aplica monkeypatch. La
correccion no modifica FreeCAD instalado ni cambia preferencias globales de forma
permanente. Tres DWG consecutivos y el DXF real de Upala devolvieron cursor,
mouse y teclado inmediatamente; la aceptacion final requiere la prueba manual del
usuario despues de reiniciar FreeCAD y cargar 0.14.4.


### 12. Trabajo 2D, representacion 3D y salida documental


- Siempre que sea tecnicamente razonable, cada elemento debe conservar una unica identidad BIM; la representacion 2D y la geometria 3D deben derivarse del mismo objeto o de dependencias vinculadas, no de copias independientes que deban sincronizarse manualmente.
- Favorecer el trabajo directo en planta 2D para colocar, seleccionar, mover, rotar y editar elementos mediante simbologia tecnica, especialmente cuando sea mas sencillo que manipular el modelo 3D.
- Utilizar el 3D para visualizacion, coordinacion espacial, comprobacion de alturas, interferencias y revision del resultado.
- Todo elemento calculado o generado por FA debe poder producir una representacion 2D comprensible, identificable y exportable.
- Revisar progresivamente salida a TechDraw/DXF de Level, Spaces, muros, puertas, ventanas, piso/terreno y cielos.
- Evitar soluciones 3D que no puedan documentarse de forma razonable.


### 13. Exportacion final de modelo BIM limpio


- Crear una herramienta final `FA Exportar modelo BIM limpio`.
- Generar un nuevo `.FCStd` con el modelo BIM terminado y solo las dependencias imprescindibles para conservar edicion y parametria.
- Excluir DXF, capas, bloques, diagnosticos, objetos temporales y geometria de reconstruccion innecesaria.
- Mantener la estructura `Site -> Building -> Level -> elementos BIM`.
- No eliminar Sketches Base u otras dependencias si un objeto BIM las necesita para seguir funcionando; ocultarlas/organizarlas cuando corresponda.
- Considerar una segunda salida IFC de entrega a partir de la misma estructura final.
- Usar esta exportacion como prueba de calidad: un elemento que no pueda trasladarse limpiamente probablemente sigue demasiado acoplado al proceso de reconstruccion.


### 14. Herramientas generales aun no implementadas


- `FA_CleanReference`
- `FA_CopySelectedLinesToSketch`
- `FA_ExportJSON`
- `FA_ElectromechanicalBase`
- `FA_CalibrateReferenceImage`
- `FA_ImportReferenceImage`


### Prioridad de desarrollo actual


1. Estructura BIM `Site -> Building -> Level` y reglas de pertenencia al arbol.
2. Areas/Wires/Spaces como base espacial comun.
3. Puertas y ventanas con resolvedor robusto de aberturas y preservacion de estado por instancia.
4. Integrar piso, terreno y cielos dentro de la estructura BIM.
5. Diagnosticar rendimiento del importador.
6. Consolidar salida documental 2D.
7. Implementar `FA Exportar modelo BIM limpio` como cierre del flujo.




## Arbol BIM y aviso de version - 0.14.5


- Puertas y ventanas alojadas conservan `Hosts=[Wall]` como relacion nativa y ya no se agregan tambien a `Level.Group`; asi el mismo objeto no aparece dos veces en el arbol.
- Los `Base`/Sketch internos de esas aberturas tampoco se agregan como hermanos directos del Level; permanecen accesibles por la relacion `Base` del objeto BIM.
- `FA_TargetLevel` conserva la trazabilidad espacial sin crear una segunda residencia visible.
- Las puertas dobles alojadas siguen la misma regla; una puerta doble libre si permanece directamente en el Level.
- Al activar el Workbench, se compara la identidad `VERSION + BUILD_ID` con la ultima notificada. Una version o build nuevo muestra una sola ventana `Workbench recargado correctamente`; activaciones posteriores de la misma identidad permanecen silenciosas.




### Puertas cercanas a esquina (build 2026.08.29.1)


Validado en FreeCAD 1.1.3: si una puerta esta a menos de 180 mm de una pared
lateral unica, la jamba se ajusta a la cara de esa pared sin cambiar el ancho del
Sketch; para una hoja se infiere la bisagra en ese extremo y el giro hacia la misma
pared. Tambien funciona cuando el tramo anfitrion y la pared lateral pertenecen al
mismo `Arch Wall` multisegmento. Las ambiguedades no se modifican y una puerta
alejada conserva su posicion. Ver `TAREA_ACTUAL.md` y
`tests/freecad_door_corner_snap_end_to_end.py`.


### Giro fisico, NO_FIT y cruces (build 2026.08.30.1)


La segunda fase traduce la direccion fisica de la hoja al token nativo
`Mode1/Mode2` de `WindowParts`. La decision usa el eje real desde la bisagra hacia
la otra jamba y el vector deseado de la hoja abierta; por eso invertir START/END
del segmento no cambia la puerta fisica. Solo se modifica el token del componente
abatible del preset nativo; `Normal` no sustituye el modo de giro.


Antes de mover una jamba se verifican ambos extremos. Si el ancho del Sketch no
cabe entre caras laterales, FA conserva posicion y ancho, informa `NO_FIT` y guarda
la luz disponible y penetracion prevista. En cruces o T inversas puede alinearse
una cara inequivoca (`JAMB_ONLY`), pero bisagra y apertura quedan `AUTO` salvo que
la Tabla de Puertas u otra autoridad explicita las defina.


### GeometryIndex 9: cara interna sin traslacion (build 2026.08.30.2)


La prueba A/B del levantamiento 1416 confirmo que una cara candidata situada dentro
del propio tramo no representa una jamba exterior segura. En ese `JAMB_ONLY`, FA
conserva la posicion proyectada del Sketch y mantiene la cara solo como diagnostico.
Las caras ubicadas antes o despues del tramo siguen ajustando la jamba. Esta regla
recupera la posicion pre-snap del indice 9 sin alterar Servicio Sanitario, `NO_FIT`,
Mode1/Mode2 ni la Tabla de Puertas.




### FA Techo BIM (0.14.9 / build 2026.08.30.3)


Se incorpora `FA_CreateRoofSystemBIM` como flujo publicado para crear el sistema completo de techo desde tres Sketches seleccionados: cerchas/ejes, clavadores en planta y contorno cerrado de cubierta. El comando identifica la funcion de los Sketches antes de escribir y materializa el sistema completo de una sola vez.


El arbol de produccion prioriza relaciones BIM nativas y evita duplicacion visual: una `Draft Line` sirve como Base de una unica `Arch Truss`, un `Arch Axis` repite las cerchas, cada faldon usa su propio `Arch Frame` y perfil C, y `Arch Roof` conserva solamente su Base necesaria. Los Sketches fuente no se reubican y la superficie maestra de calculo no se conserva como objeto permanente. Los comandos parciales de cercha, clavadores y cubierta permanecen internos mientras se valida el flujo completo.


Pruebas puras del nucleo: 20/20. Compilacion y contrato estatico de integracion: aprobados. Pendiente: smoke test real del boton y del arbol producido dentro de FreeCAD 1.1.3.




### FA Prototipo techo por ejes (0.14.10 / build 2026.08.30.4)


Boton experimental separado de `FA Techo BIM`. Crea un documento nuevo y autocontenido para validar una entrada sin Sketches: `Draft Rectangle` como huella, `Arch Axis` como fuente de las posiciones de cerchas y `Arch Axis` inclinado usado directamente como `Base` de cada `Arch Frame` de clavadores. El prototipo usa separacion maxima de 800 mm con retiros inicial/final de 200 mm; el ejemplo de 8 x 12 m y pendiente 20 grados produce 6 clavadores por faldon a 771.342 mm. No sustituye aun el flujo estable de tres Sketches.




## Prototipo techo por ejes - build 2026.08.30.5


- El comando experimental `FA_RoofAxisPrototype` conserva la huella como `Draft Rectangle` y la Base de cercha como `Draft Line`.
- Los clavadores dejan de usar `Arch Frame`: cada faldon usa una sola `Arch Structure` con `IfcType=Beam`, una seccion rectangular `Draft Rectangle` y un `Arch Axis` para repetir el elemento maestro.
- La Base de cubierta del prototipo pasa tambien a `Draft Rectangle`.
- Se mantiene el reparto uniforme con separacion maxima de 800 mm y retiros extremos configurables.
- `FA_CreateRoofSystemBIM` / `FA Techo BIM` estable no se modifica en este build.
- Pendiente de validacion en FreeCAD 1.1.3 real: Shape de ambos Beam, cantidad de solidos y contacto con cerchas/cubierta.




## FA Techo desde rectangulo - 0.14.11


Se publica el segundo boton de `FA Techo BIM` como **FA Techo desde rectangulo**. El comando estable `FA Techo BIM` basado en tres Sketches se conserva sin cambios.


Flujo: seleccionar exactamente un `Draft Rectangle` horizontal y ejecutar el boton. El rectangulo del usuario se conserva visible, en su ubicacion y jerarquia original. El comando crea dentro de `Techo BIM`: ejes de cerchas, una cercha BIM maestra repetida por `Axis`, dos sistemas de clavadores `Arch Structure/Beam + Axis` y la cubierta `Arch Roof`. La geometria auxiliar simple usa `Draft Line` y `Draft Rectangle`.


Preferencias editables y persistentes: pendiente, direccion de cumbrera, separacion de cerchas, modo de distribucion de cerchas, redondeo 50/100 mm, apoyo XY automatico sobre muros o bordes del Rectangle, ajuste simetrico fino de apoyos, altura de talon, separacion de clavadores, modo de distribucion y redondeo de clavadores, retiros alero/cumbrera, seccion rectangular de clavador, alero de cubierta, espesor de cubierta y fuente de cota de apoyo.


La separacion de clavadores usa por defecto el modo `fixed`: conserva el valor ingresado en los intervalos interiores y permite que solamente el primero y el ultimo sean excepciones. El modo `rounded` calcula un nominal practico redondeado a 50 o 100 mm sin superar la separacion maxima solicitada.

Desde build `2026.08.31.4`, las cerchas extremas ya no dependen obligatoriamente de los bordes del Rectangle. En modo automatico el adaptador lee las lineas transversales de `Wall.Base` y busca dos ejes de muro cercanos a los extremos de la cumbrera; esto funciona tambien cuando un unico objeto Wall contiene el perimetro completo. Si no se resuelven dos apoyos confiables, el comando vuelve al Rectangle y lo informa. Un ajuste simetrico editable permite desplazar ambos apoyos hacia dentro o fuera sin perder el automatismo.

La distribucion de cerchas admite ahora los mismos criterios constructivos que los clavadores: `fixed` conserva la separacion ingresada en los intervalos interiores y absorbe la diferencia de forma simetrica en los extremos; `rounded` calcula un nominal de 50/100 mm sin superar la separacion maxima solicitada. La huella, el apoyo estructural y el borde de cubierta se mantienen como referencias separadas.



La **Huella techo** y la **Base cubierta** son objetos distintos intencionalmente. La huella es la referencia del usuario en la cota de apoyo; la Base cubierta es un `Draft Rectangle` interno y oculto, elevado para colocar la cara inferior de la cubierta sobre la cara superior de los clavadores. Usar la huella directamente como `Roof.Base` la ocultaria/acoplaria al Roof y podria producir jerarquia visual no deseada.


Si existen muros BIM bajo la huella, el comando analiza sus coronaciones sin modificarlos. El usuario puede usar la Z del rectangulo o la coronacion mediana cuando las alturas de muro son coherentes. Si son ambiguas, se conserva la Z del rectangulo y se informa en la Vista de reportes.




### Hot-reload de FA Techo


Desde build `2026.08.30.8`, `FA_RoofAxisPrototype` se registra mediante `ReloadableCommandProxy`,
el mismo patron ya usado por `FA_CreateDoorsFromSketch`. En FreeCAD 1.1.3, que no expone
`FreeCADGui.removeCommand`, la primera migracion desde el comando directo requiere reiniciar
FreeCAD una vez. Despues, el ID estable resuelve la `CommandClass` del modulo vigente en cada uso.
El build conserva tambien el hotfix que recomputa y valida la Base `Draft Rectangle` antes de
`Arch.makeRoof()`.


## Editor sencillo de ejes de cerchas - build 2026.08.31.5

Se agrega el comando `FA Editar ejes de cerchas` como interfaz amigable sobre el mismo `Arch Axis` nativo creado por `FA Techo desde rectangulo`. No crea ejes paralelos ni reemplaza el objeto BIM.

Flujo: seleccionar `Ejes de cerchas` o `Cerchas BIM` -> abrir el editor -> escoger modo, separacion maxima y retiros de primera/ultima cercha -> revisar la previsualizacion -> Aplicar.

Modos disponibles: mantener separacion con extremos simetricos, distribucion uniforme, nominal redondeado a 50 mm y nominal redondeado a 100 mm. El cambio actualiza `Axis.Distances`/`Angles`, las propiedades FA de distribucion y la cercha vinculada mediante su propiedad nativa `Axis`. No modifica clavadores, cubierta, pendiente ni apoyos estructurales.

## Ajuste de interfaz de techo - build 2026.08.31.6

- Se retira de la barra el boton legado `FA Techo BIM` (`FA_CreateRoofSystemBIM`). La barra `FA Techo BIM` se conserva como grupo y queda con `FA Techo desde rectangulo` y `FA Editar ejes de cerchas`.
- El comando legado se archiva para referencia/recuperacion futura; no se elimina su historia.
- Se agregan iconos SVG propios para `FA Techo desde rectangulo` y `FA Editar ejes de cerchas`.
- La simplificacion adicional del editor de ejes queda documentada en `PENDIENTE_FA_EDITOR_EJES_CERCHAS.md`.


## FA Demo edificio - build 2026.08.31.7

Se agrega `FA Demo edificio` a `FA Proyecto BIM` como demostracion automatica de extremo a extremo. Cada ejecucion abre un documento nuevo y crea fuentes 2D y arquitectura BIM mediante la secuencia `Sketches -> piso/losa -> muros -> puertas/ventanas -> techo a dos aguas`.

El modo fijo genera la casa canonica de 6 x 8 m. El modo aleatorio es reproducible por semilla: la misma semilla produce exactamente la misma especificacion JSON. La generacion aleatoria vive en `core/demo_building_core.py`, independiente de FreeCAD/Qt, mientras `commands/cmd_demo_building.py` reutiliza las utilidades vigentes de proyecto, Building/Level, muros, piso, aberturas y el techo actual por ejes. El documento generado conserva un controlador `FA_DemoBuilding` con semilla, resumen y especificacion completa.

La demo conserva los Sketches de muros y centros de aberturas como fuentes 2D identificables y un `Draft Rectangle` como huella del techo. `FA Techo desde rectangulo` expone ademas `create_roof_from_rectangle_programmatic(...)` para que la misma implementacion pueda ser reutilizada por la demo y, mas adelante, por MCP sin pasar por el dialogo.

Validacion previa a publicacion: 6/6 pruebas focales, compilacion de sintaxis aprobada y 5000 semillas aleatorias validadas. El smoke test real del boton en FreeCAD 1.1.3 queda pendiente. Como este build agrega una accion a la barra `FA Proyecto BIM`, se recomienda reiniciar completamente FreeCAD despues de sincronizarlo.

Detalle y contrato: `DEMO_EDIFICIO_AUTOMATICO.md`.

## Casa demo v2 - build 2026.08.31.9

`FA Demo edificio` amplía el caso existente sin crear un segundo comando. La secuencia demostrativa pasa a ser `Sketches -> piso/losa -> muros -> puertas/ventanas -> recintos 2D -> Espacios BIM -> cielorraso 600x600 -> techo`.

Los recintos se obtienen con la lógica vigente de `create_closed_room_sketch`, de modo que la demo conserva un Sketch documental 2D identificable. A partir de cada recinto se crea un `Arch Space` nativo con un sólido Base oculto. El Space conserva `FA_RoomID`, `FA_RoomName`, `FA_RoomArea`, `FA_SpaceHeight` y `FA_FloorPolygonJSON` para reutilización posterior.

El cielorraso reutiliza `create_modular_ceilings()` y acepta ahora Spaces BIM FA como entrada. Cuando existe `FA_FloorPolygonJSON`, el patrón se recorta contra el polígono exacto del recinto; si falta, conserva el fallback geométrico previo. El módulo nominal de la demo es 600 x 600 mm y el caso fijo usa cota de cielo 2700 mm.

La casa canónica 6 x 8 m contiene dos recintos simples: `Estar-comedor` y `Dormitorio`. El modo aleatorio sigue siendo reproducible por semilla y genera también sus polígonos de recinto, altura de Space y cielorraso de forma determinista.

Nota visual: las puertas BIM nativas de FreeCAD se materializan mediante el objeto `Arch Window` con preset de puerta, por lo que su ViewProvider puede mostrar el icono de ventana en el árbol. Casa demo v2 no sustituye ese ViewProvider; queda como mejora visual separada para no comprometer el comportamiento BIM nativo.

Validación previa: 10/10 pruebas focales de demo/core/contrato y compilación de sintaxis aprobada. Falta la prueba integral en FreeCAD 1.1.3 de Spaces, cielorrasos y árbol resultante.


## FA Demo guiada - build 2026.08.31.10

`FA Demo edificio` mantiene un unico comando, un unico generador y la misma `SpecificationJSON`, pero ahora permite `Generar edificio completo` o `Demostracion guiada paso a paso`. El nucleo puro `core/demo_guided_core.py` declara 14 pasos estables; `DemoBuildingSession` ejecuta esos pasos reutilizando las herramientas reales de piso, muros, aberturas, recintos, Spaces, cielorraso y techo.

El modo guiado usa un panel acoplable no modal con Reiniciar, Anterior, Reproducir/Pausa, Siguiente, velocidad y encuadre automatico. Cada avance es una transaccion independiente. `Anterior` reconstruye deterministicamente la misma especificacion hasta N-1 en vez de eliminar objetos manualmente. El modo completo conserva su transaccion atomica original.

Validacion previa: 15/15 pruebas focales de demo/core/contrato y compilacion de sintaxis aprobada. Falta la prueba visual/funcional en FreeCAD 1.1.3.

### FA Demo edificio - saneamiento 2026.09.01.1

La primera prueba real del modo guiado completo 14/14 pasos en FreeCAD 1.1.3. Esta build elimina el ciclo de dependencias causado por enlazar `Site` desde `FA_DemoBuilding` y corrige la sincronizacion temprana de `Spreadsheet_Parametros` mediante recompute explicito. No cambia la geometria, la semilla, el guion ni el resultado BIM de la demo.



### FA Demo guiada - pulido visual 2026.09.01.2

El reproductor guiado conserva los mismos 14 pasos y la misma materializacion BIM. Ahora muestra el icono real asociado a cada etapa, aplica transparencia u ocultamiento temporal de objetos 3D para que los Sketches fuente sean legibles y agrega `Cerrar demostracion`, que cierra solo el panel y conserva el documento. La presentacion original se restaura al cambiar de paso o cerrar el reproductor. Tambien se redisenaron con color los iconos recientes de demo, techo desde rectangulo, editor de ejes, tabla de puertas y tabla de ventanas.


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


## Build 2026.09.01.5 - correccion feedback techo programatico

Se corrige una referencia residual a `feedback` dentro de `create_roof_from_rectangle_programmatic()`. El adaptador usado por Demo/MCP acepta ahora `feedback=None` y solo emite etapas cuando el llamador suministra un objeto de feedback. La ruta interactiva del boton conserva su propio `LongOperationFeedback`. No se modifica geometria de techo, cerchas ni clavadores.


## Build 2026.09.01.6 - aviso previo visible, panel estable y jardin demo

El helper comun de operaciones largas cambia el aviso a futuro y agrega el indicador `⏳`. Antes del primer calculo costoso fuerza el repintado/actualizacion de GUI; el panel guiado reserva una zona de estado fija y los cuatro controles de reproduccion conservan posiciones estables aunque cambie el texto. La regla se actualiza tambien en `AGENTS.md` para todos los Workbenches.

`FA Demo edificio` reutiliza ahora el terreno ya existente de `FA Piso BIM`: crea un `Arch Site` con `Terrain` plano, verde, recortado bajo la huella y etiquetado `Jardin - Demo`. No se crea un sistema paisajistico paralelo.


## Build 2026.09.01.7 - color visible del jardin

Correccion visual de la Casa demo: `Arch.makeSite` puede ocultar la Base/Terrain y mostrar la Shape del propio Site. La demo aplica ahora el mismo verde al Terrain y al `Arch Site`, y reaplica el estilo despues del recompute final. No cambia geometria, margen, recorte ni jerarquia BIM del jardin.

## Build 2026.09.01.8 - historial local de uso de comandos

Facil Arquitectura incorpora un registro local de uso compatible conceptualmente con antecedentes internos del proyecto. `usage_log.py` mantiene dos fuentes bajo `logs/`: `tool_usage.json` para acumulados por herramienta y `tool_events.jsonl` para la secuencia de eventos.

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


## Build 2026.09.01.11 - normalizacion del arbol BIM

La estructura autoritativa del modelo queda fijada en `Site -> Building -> Level`. Los flujos normales ya no deben mantener `FA_Project` como segundo arbol cuando existe un Level BIM inequívoco.

- `Level -> Auxiliares FA` concentra Sketches fuente/derivados, cuadros y tablas que necesitan persistir y que no sean ya Base nativa de otro objeto.
- Las ramas legacy `01_Parameters`, `02_MasterSketches`, `04_Areas` y `06_Tables` se migran de forma no destructiva a `Auxiliares FA`; si quedan vacias y fueron creadas por FA, se retiran junto con `FA_Project` vacio.
- Sketches creados manualmente por el usuario se adoptan solo cuando su contexto es seguro. Si un Sketch ya es `Base` nativa de un muro u otro elemento, esa relacion sigue siendo la autoridad y no se duplica en `Auxiliares FA`. Grupos de usuario ajenos a FA no se mueven.
- Los `Arch Space` quedan como miembros directos del Level; se retiran cascaras vacias `FA_BIMSpaces`/`FA_DemoSpaces`.
- `Site` y la losa dejan de conservar enlaces `PropertyLinkList` de trazabilidad a Sketches que hacian aparecer fuentes bajo `Sitio BIM`; la dependencia geometrica real permanece en `FA_FloorFootprint.Sources` y la trazabilidad adicional se guarda por nombres.
- La reticula de cielo de 600x600 sigue calculandose siempre, pero el objeto `Reticula cielo - ...` pasa a ser documental y opcional. Por defecto no se materializa. Si el usuario lo solicita, se aloja con los auxiliares/documentacion y se marca `FA_DocumentaryOnly=True`.
- El Demo no crea `FA_Project`, no crea un grupo clasificador de Spaces y no materializa reticulas documentales por defecto.
- Las tablas de puertas/ventanas y el cuadro de rotulos usan `Auxiliares FA` cuando el Level es inequívoco; el fallback legacy solo se conserva para documentos sin contexto BIM resoluble.

Validacion previa a FreeCAD real: `23/23` pruebas focales de contrato/migracion/estructura/cielos aprobadas y `py_compile` aprobado. Pendiente: repetir en FreeCAD 1.1.3 el Demo y el flujo manual desde Sketches y comparar ambos arboles.
