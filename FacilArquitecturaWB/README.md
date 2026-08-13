# FacilArquitecturaWB

Workbench independiente para FreeCAD 1.1.3 orientado a crear una base arquitectonica BIM editable desde planos existentes o desde Sketches ya depurados.

Version actual: `0.9.0` | build `2026.08.09.5`. Al recargar con `FacilArquitecturaLoader.FCMacro`, la consola debe mostrar `VERSION CARGADA: v0.9.0 | build 2026.08.09.5`. Los proyectos heredados con `FA_Project` conservan tambien `FA_WorkbenchVersion` y `FA_WorkbenchBuild`.

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

- `FA_ImportCADReference`: importa DWG/DXF en un documento nuevo con unidad real controlada y sin guardarlo.
- `FA_CreateBIMStructure`: crea o reutiliza un `Building` y un `Building Storey` nativos.
- `FA_RebuildBIMModel`: analiza los Sketches, permite corregir su asignacion y coordina la reconstruccion BIM completa.
- `FA_CreateProject`: crea `FA_Project`, grupos base y `Spreadsheet_Parametros`.
- `FA_CreateMasterSketches`: crea sketches maestros editables y vacios en XY.
- `FA_CenterlinesFromSelection`: crea un nuevo `Sketch_Centros` generico desde shapes o un layer seleccionado.
- `FA_WindowCenterlinesFromSelection`: crea un nuevo `Sketch_Centros` con un eje principal por shape de ventana.
- `FA_DoorCenterlinesFromSelection`: crea un nuevo `Sketch_Centros` con el eje cerrado de cada simbolo de puerta.
- `FA_CreateDoorsFromSketch`: crea puertas nativas Arch desde los ejes, resuelve el muro anfitrion y valida el corte real.
- `FA_CreateWindowsFromSketch`: crea ventanas nativas Arch desde los ejes, con altura y antepecho configurables, y valida el corte real.
- `FA_CloseWallSketch`: acepta un muro BIM, su Sketch Base o un Sketch generico; completa los metadatos faltantes y cierra los buques validados por puertas o ventanas.
- `FA_CreateSampleGeometry`: agrega geometria simple de muestra a sketches vacios solo para pruebas.
- `FA_CreateWallsFromSketch`: crea un muro BIM con `Arch.makeWall` y `Base` directa desde cualquier Sketch seleccionado; si faltan espesor, altura o clasificacion solicita esos datos.
- `FA_CreateColumnsFromSketch`: convierte dos familias de lineas de un Sketch en `Arch Axis`, un `AxisSystem` y columnas `Arch Structure` colocadas en sus cruces reales.
- `FA_CreateBuildingGrid`: crea una cuadricula nativa `ArchGrid` desde los centros de paredes existentes.
- `FA_CreateSiteFloorBIM`: crea una losa BIM desde sketches de muros, ventanas y puertas, y un terreno irregular de prueba.
- `FA_CollectRoomLabels`: recopila rotulos de recintos, consolida duplicados y actualiza `Spreadsheet_Rotulos_Recintos`.
- `FA_CreateModularCeiling`: genera cielos suspendidos por recintos rectangulares o poligonales, recorta la reticula nominal de 600x600 mm contra el perimetro real y reserva las celdas ocupadas por luminarias ElectricCR.
- `FA_CreateServicePlatformFront`: crea un frente parametrico de puestos de atencion con seis sketches maestros, mobiliario simple y zonas funcionales.
- `FA_UpdateServicePlatformFront`: reconstruye el frente seleccionado desde su `Spreadsheet_Platform` y conserva objetos ajenos al generador.
- `FA_AddCashierServiceWindow`: deja previsto y validado el flujo independiente para una futura ventanilla de caja alojada en un muro BIM.

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
compatibilidad. La losa y los `Space` nativos se dejaron para una fase posterior,
porque no se consideran todavia suficientemente estables para el asistente.

La prueba sobre una copia de La Cruz 2.1 confirmo un muro con Base Sketch directa,
14 columnas, huecos reales de puerta/ventana, guardado/reapertura, idempotencia y
Undo/Redo. Consulte [el resultado tecnico](RESULTADO_CODEX_RECONSTRUCCION_BIM.md).

## Frente parametrico de plataforma

Ejecute `FA Crear frente de plataforma`, indique el ancho total y la cantidad de puestos y acepte. El resultado se organiza como `FA_ServicePlatformFront` con parametros, seis sketches maestros, geometria y metadatos. `SK_PA_FrontAxis` es una sola linea de centro de longitud igual al frente; `origin_x_mm` y `front_offset_mm` permiten ubicarla en el plano general. Para modificarlo, cambie los valores de `Spreadsheet_Platform`, seleccione el grupo o cualquiera de sus representaciones y ejecute `FA Actualizar frente de plataforma`.

La referencia `PL-01`, paginas 33-34 de `Guia Estandarizacion 050626 2`, se usa solamente para los valores iniciales (dos puestos y muebles de aproximadamente 1800 x 600 x 740 mm). No fija una norma ni genera el recinto completo de caja.

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

Cada ejecucion crea sketches nuevos y conserva los anteriores. Si se procesa dos veces la misma seleccion, agrega una secuencia como `_002`, `_003`, etc. El sketch incluye `FA_ElementType` y `FA_ExtractionMode` para identificar el contenido y el metodo utilizado.

Los layers que contienen instancias `App::Link`, como los objetos `LinkU` de bloques DXF, se procesan usando el `Shape` transformado de cada link. La propiedad `Group` reenviada por el objeto enlazado no se recorre como un grupo normal; asi se conservan todas las posiciones de las instancias y no se agregan los shapes base ocultos.

Cuando puede medir la distancia entre caras o el ancho de un perfil cerrado, el comando general separa los ejes en sketches como `..._Espesor_100mm` y `..._Espesor_200mm`. Espesores con diferencias de hasta 10 mm se consideran el mismo grupo. La propiedad `FA_WallThickness` conserva el valor representativo y el sketch principal usa `FA_RelatedCenterlineSketches` para enlazar los sketches adicionales de la misma ejecucion.

Antes de crear los sketches, los tramos colineales cortados dentro de una misma zona continua de muro se consolidan y sus extremos cercanos se llevan al cruce real de los ejes. Un eje que sobrepasa una esquina se recorta hasta la interseccion. Si existe una linea de cierre transversal, ese extremo representa el borde real del muro y nunca se prolonga dentro de otra pared, aunque sus ejes esten cercanos. Se agregan restricciones `Horizontal`, `Vertical`, `Coincident` y `PointOnObject` cuando son geometricamente seguras; las diagonales se conservan sin forzarlas a ortogonales.

Cuando el DXF importa cada borde como un Shape independiente, el comando reconstruye los remates usando tambien las lineas cortas que no califican como caras longitudinales. Si una cara longitudinal esta fragmentada, recompone sus tramos hasta el remate real; no los une cuando existe una linea perpendicular de cierre. Los perfiles rectangulares compactos, proporcionados y con al menos 82% de area llena se interpretan como columnas y generan dos ejes en cruz dentro de un sketch adicional `..._Columnas`, en vez de mezclarse con los grupos de espesor de paredes.

`FA Centros` nunca acepta un `Sketch_Centros_...` previamente generado como fuente. Reprocesar los ejes como si fueran caras produce espesores falsos y cruces incorrectos; por eso el comando elimina esos objetos de una seleccion mixta y cancela la operacion si no queda geometria original. Para reducir falsos positivos en esquinas, una cruz de columna requiere actualmente un perfil cerrado con lado menor de al menos 250 mm.

La creacion completa de todos los sketches de una ejecucion usa una sola transaccion documental: `Ctrl+Z` elimina el resultado completo. `FA Muros BIM desde centros` usa una segunda transaccion y crea un `Arch Wall` por Sketch, manteniendo ese Sketch como `Base` parametrica. El muro vincula `Width` con `FA_WallThickness` y `Height` con `FA_WallHeight`; editar las lineas o esas propiedades recompone el objeto BIM. Si se selecciona el sketch principal, tambien procesa automaticamente su lista `FA_RelatedCenterlineSketches`.

Un Sketch generico ya no se rechaza. El comando muestra los Sketches sin contrato de muro y solicita espesor, altura y clasificacion. Al aceptar agrega `FA_WallThickness`, `FA_WallHeight`, `FA_Role = centerlines`, `FA_CenterlineKind = walls` y `FA_ElementType`, sin modificar la geometria. Si el Sketch tenia otro rol o tipo, los conserva como `FA_PreviousRole` y `FA_PreviousElementType`. Las dimensiones positivas ya existentes nunca se sustituyen. Cancelar el dialogo no modifica el Sketch.

Los errores corregibles, como no seleccionar un objeto o seleccionar el tipo equivocado, se muestran como una advertencia breve y no producen el bloque `Running the Python command failed`. Los fallos internos tampoco se propagan al ejecutor de comandos; conservan un detalle tecnico identificado con `[FACILARQ]` en `Report view`.

`FA Ejes y columnas BIM` usa el sketch seleccionado como fuente. Agrupa lineas colineales, conserva separaciones no uniformes y admite una reticula rotada siempre que tenga exactamente dos familias no paralelas. Crea las familias con `Arch.makeAxis` y las agrupa con `Arch.makeAxisSystem`. Si una reticula completa esta alineada con X/Y, asigna el sistema a una sola columna `Arch.makeStructure` para que BIM la replique. Si la reticula esta incompleta o girada, crea columnas BIM solo en los cruces presentes en el sketch; asi evita columnas inventadas y conserva su orientacion. El sketch conserva `FA_AxisExtension`, `FA_AxisTolerance`, `FA_ColumnWidth`, `FA_ColumnDepth` y `FA_ColumnHeight`. Cambiar las dimensiones actualiza y mantiene centradas las columnas; cambiar la posicion de los ejes requiere volver a ejecutar el comando. La operacion completa admite `Ctrl+Z`.

`FA Cuadricula ArchGrid para reconstruir paredes` crea un objeto BIM mediante `Arch.makeGrid()`, no familias `Arch Axis`. Prefiere los sketches `Sketch_Cerrado_*` generados por `FA Cerrar huecos de paredes`; esos sketches prolongan los centros de pared sobre los huecos confirmados por los sketches existentes de puertas y ventanas. Si no existe una copia cerrada, usa el sketch de centros con espesor medido. El ArchGrid enlaza por separado las fuentes de paredes y las fuentes de aberturas para conservar trazabilidad. Como `ArchGrid` prolonga siempre sus filas y columnas por todo el rectangulo, el objeto BIM se conserva oculto y el comando crea `FA_GridWallTrace` como `Sketcher::SketchObject` editable. Este sketch naranja combina los segmentos reales del sketch reconstruido con ejes de puertas y ventanas ajustados al centro de la pared mas cercana; solo acepta aberturas colineales conectadas a menos de 3000 mm, por lo que descarta simbolos exteriores aislados. Antes de crear el Sketch, une tramos colineales, ajusta los pequeños desfases de esquina y divide las lineas en cada cruce. El Sketch recibe restricciones `Horizontal`, `Vertical` y `Coincident`, de modo que los encuentros comparten vertices reales y no solo coordenadas visualmente parecidas. Se crea a Z = 0 y hereda `FA_WallThickness`, `FA_WallHeight` y `FA_CenterlineKind = walls`; por ello puede seleccionarse directamente y usarse con `FA Muros BIM desde centros`, incluso despues de corregirlo manualmente. A partir de este trazado el comando tambien genera `FA_ReconstructedWallBase` y un muro BIM `Paredes BIM reconstruidas sin puertas ni ventanas`; el muro original queda oculto, no eliminado. Asi no aparecen prolongaciones artificiales y tanto las guias como los solidos quedan cerrados. `grid_primary_support_mm`, `grid_cluster_tolerance_mm` y `grid_max_lines_per_direction` controlan la simplificacion semantica del ArchGrid. Al volver a ejecutar el comando se reemplazan solamente los objetos generados por este flujo.

Para ventanas con marcos u otros detalles internos, usar `FA Centros de ventanas`. Este comando agrupa primero shapes y bordes separados hasta 250 mm que parecen formar una misma ventana y luego genera un unico eje principal por grupo. El comando general permanece disponible para muros de cualquier material, espesores diferentes y geometria representada por pares de bordes.

Para puertas con hoja y arco de giro, usar `FA Centros de puertas`. El comando agrupa los detalles del simbolo, identifica la radial que coincide con la hoja abierta y genera la radial opuesta como eje del buque cerrado. Si el arco circular no se puede reconocer, usa el eje dominante del grupo como respaldo y lo informa en la consola.

`FA Cerrar huecos de paredes` acepta seleccionar uno o mas muros BIM, sus Sketches Base o Sketches genericos de pared. Al seleccionar un muro sigue `Base` y `FA_SourceSketch` hasta el eje autoritativo. Si el Sketch no tiene espesor, altura o clasificacion, solicita esos datos y lo convierte dentro de la misma transaccion; no convierte bocetos identificados como puertas, ventanas o columnas. Crea una copia `Sketch_Cerrado_*` por cada espesor y busca automaticamente sketches de centros de puertas y ventanas en el documento. Cuando un buque coincide con el espacio entre dos lineas colineales, alarga ambos extremos hasta un punto comun sin desplazar la linea completa ni cambiar su orientacion. El resultado conserva `Placement`, `FA_WallThickness`, `FA_WallHeight` y los metadatos de tipo del sketch fuente, y recibe restricciones `Coincident`, `Horizontal`, `Vertical` o `Angle`. Por defecto no cierra huecos sin un sketch de buque que los justifique. Si cambia una fuente, se debe volver a ejecutar el comando.

Limitaciones actuales:

- Para perfiles cerrados o shapes complejos y alargados obtiene un eje principal, util para muchas representaciones de ventanas y puertas.
- Si el DXF trae elementos como dos lineas de borde, las empareja por direccion, separacion y solape para crear una linea central.
- Admite geometria ortogonal y diagonal. Un borde largo puede emparejarse con varios tramos cortos.
- Los contornos compactos ambiguos que no tienen una direccion dominante se omiten; el conteo queda en `FA_IgnoredCompactCount`.
- Geometria DXF abierta, muy fragmentada o con separaciones mayores a 800 mm entre caras puede requerir ajuste manual.
- Las uniones entre sketches de espesores distintos coinciden geometricamente, pero no reciben una restriccion cruzada entre documentos Sketcher independientes.

Resultado esperado:

- Grupo `FA_Project`.
- Grupos `00_Reference`, `01_Parameters`, `02_MasterSketches`, `03_BIM`, `04_Areas`, `05_Electromechanical`.
- Hoja `Spreadsheet_Parametros`.
- Sketches maestros editables y vacios.
- Muros Arch/BIM basicos dentro de `03_BIM`.

## Decisiones aplicadas desde NOTES_RESEARCH.md

- Usar el importador DXF existente de FreeCAD/Draft en futuras etapas; no crear importador propio.
- Usar Arch/BIM para muros y objetos arquitectonicos; no reinventar BIM.
- Tratar DWG, PDF e imagenes como flujos futuros o referencias externas, no como conversion automatica inicial.
- Crear sketches maestros por sistema/tipo constructivo, no un sketch por objeto.
- Mantener el workbench como orquestador simple y robusto.

## Pendientes

- `FA_CleanReference`
- `FA_CopySelectedLinesToSketch`
- Integrar como comandos nativos las macros validadas de areas, puertas BIM y ventanas BIM.
- Agregar areas poligonales para recintos irregulares.
- `FA_ExportJSON`
- `FA_ElectromechanicalBase`
- `FA_CalibrateReferenceImage`
- `FA_ImportReferenceImage`
