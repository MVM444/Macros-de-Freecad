# Documentacion del Workbench Facil Arquitectura

Version documentada: `0.7.0`
Build: `2026.08.05.1`
FreeCAD validado: `1.1.3` (compatible con el objetivo 1.1.1)

## 1. Proposito

`FacilArquitecturaWB` organiza un flujo reproducible para reconstruir una base BIM
editable desde planos existentes, principalmente DXF. Usa herramientas nativas de
FreeCAD, Draft, Arch y BIM; no define un formato BIM propio.

Sus responsabilidades son organizar el documento, extraer centros y espesores,
reconstruir paredes, crear objetos BIM, recopilar datos de recintos y mantener
trazabilidad entre el DXF, los Sketches y el modelo.

## 2. Estado de implementacion

### 2.1 Comandos nativos

El workbench registra actualmente 17 comandos:

| Comando interno | Funcion |
|---|---|
| `FA_ImportCADReference` | Importa DWG/DXF en un documento nuevo con unidad real controlada. |
| `FA_CreateProject` | Crea `FA_Project`, grupos y parametros. |
| `FA_CreateMasterSketches` | Crea Sketches editables por disciplina. |
| `FA_CenterlinesFromSelection` | Extrae centros genericos y espesores. |
| `FA_WindowCenterlinesFromSelection` | Obtiene un eje por simbolo de ventana. |
| `FA_DoorCenterlinesFromSelection` | Obtiene el eje cerrado de cada puerta. |
| `FA_CloseWallSketch` | Reconstruye centros sobre huecos justificados. |
| `FA_CreateSampleGeometry` | Agrega geometria de prueba. |
| `FA_CreateWallsBIM` | Crea muros Arch/BIM desde centros. |
| `FA_CreateAxesColumnsBIM` | Crea ejes, sistemas y columnas BIM. |
| `FA_CreateBuildingGrid` | Crea ArchGrid, trazado editable y muro reconstruido. |
| `FA_CreateSiteFloorBIM` | Crea losa arquitectonica y terreno de prueba. |
| `FA_CollectRoomLabels` | Consolida nombres y datos de recintos. |
| `FA_CreateModularCeiling` | Crea cielo 600x600, lo recorta contra recintos rectangulares o poligonales y reserva luminarias ElectricCR. |
| `FA_CreateServicePlatformFront` | Crea un frente parametrico de puestos de atencion al publico. |
| `FA_UpdateServicePlatformFront` | Regenera el frente seleccionado desde su hoja sin duplicar representaciones. |
| `FA_AddCashierServiceWindow` | Reserva el comando independiente para una futura ventanilla fija en muro BIM. |

### 2.2 Macros complementarias validadas

Estas funciones ya fueron validadas con el modelo de Puriscal, pero aun viven como
macros independientes del directorio de macros:

| Macro | Resultado |
|---|---|
| `AnalizarAreasDesdeMuroBIM.FCMacro` | Areas rectangulares, propiedades ElectricCR e informe. |
| `InsertarPuertasBIMDesdeRecintos.FCMacro` | Puertas BIM orientadas hacia los recintos. |
| `AgregarPuertasFrentePuriscal.FCMacro` | Completa el frente con una puerta sencilla y un vano BIM de doble hoja, sin sustituir las puertas interiores. |
| `InsertarVentanasBIMDesdeRecintos.FCMacro` | Ventanas BIM alojadas en el muro. |
| `OrganizarPuriscalDepurado.FCMacro` | Organiza un modelo de un piso como IfcSite > IfcBuilding, sin Level, y crea la acera frontal. |

Usan convenciones `FA_*` y forman parte del flujo documentado, pero todavia no son
botones propios del workbench. Su integracion futura debe separar nucleo en `core/`,
adaptador GUI en `commands/`, iconos en `resources/icons/` y pruebas en `tests/`.

`RecopilarRotulosRecintos.FCMacro` es un lanzador compatible del comando nativo; no
mantiene una segunda implementacion.

### 2.3 Frente parametrico de plataforma de atencion

El modulo `service_platform_front` usa como propietario semantico el grupo
`FA_ServicePlatformFront`. Sus seis sketches (`SK_PA_FrontAxis`,
`SK_PA_DeskEnvelopes`, `SK_PA_Dividers`, `SK_PA_StaffZones`,
`SK_PA_PublicZones` y `SK_PA_PositionAxes`) son representaciones vinculadas mediante
`Owner`. La geometria 3D de muebles y zonas tambien conserva `Owner`,
`RepresentationRole`, `FA_ModulePart` y `FA_GeneratedBy`. Como el grupo ya contiene
las representaciones, `Owner` usa `App::PropertyLinkHidden`: sigue siendo un enlace
real, pero no introduce un ciclo en el grafo de recomputacion de FreeCAD.

La hoja `Spreadsheet_Platform` contiene aliases estables. El ancho por puesto se
calcula descontando dos margenes laterales y las divisiones. Si queda bajo
`minimum_position_width_mm`, no se crea ni se elimina geometria y se informa el
ancho total minimo recomendado.

Al actualizar, solo se eliminan objetos con
`FA_GeneratedBy = FA_CreateServicePlatformFront` dentro de `01_MasterSketches` y
`02_Geometry`. La hoja, el grupo principal, los metadatos y cualquier objeto manual
permanecen. `FA_Reviewed` y `FA_IncludeCashier` no se reinician durante la
actualizacion.

La referencia `PL-01` de la `Guia Estandarizacion 050626 2`, paginas 33-34, aporta
los valores iniciales de dos puestos y escritorio aproximado de 1800 x 600 x 740
mm. No se copia la distribucion completa ni se modela el recinto de caja. La futura
ventanilla permanece como comando independiente sobre un muro BIM existente.

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
|-- modules/service_platform/ # calculo y generador del frente de atencion
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

`FA_Project` conserva `FA_WorkbenchVersion` y `FA_WorkbenchBuild`. Los nombres
internos estables se usan para automatizacion; FreeCAD puede agregar sufijos a las
etiquetas visibles al recrear objetos durante una sesion.

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

Metadatos relevantes:

- `FA_ElementType`, `FA_ExtractionMode` y `FA_CenterlineKind`.
- `FA_WallThickness` y `FA_WallHeight`.
- `FA_RelatedCenterlineSketches`.

No se debe reprocesar un `Sketch_Centros_*` como si fuera geometria DXF original.

### C. Cerrar huecos y reconstruir paredes

1. Seleccionar los Sketches de paredes.
2. Ejecutar `FA Cerrar huecos de paredes`.
3. Revisar `Sketch_Cerrado_*`.
4. Ejecutar `FA Cuadricula ArchGrid para reconstruir paredes`.

El cierre usa los ejes de puertas y ventanas como evidencia. La cuadricula crea:

- un `ArchGrid` nativo con `Arch.makeGrid()`;
- `FA_GridWallTrace`, Sketch visible y editable;
- `FA_ReconstructedWallBase`;
- un muro BIM reconstruido.

El ArchGrid atraviesa todo su rectangulo por diseño. Se conserva oculto y
`FA_GridWallTrace` representa solamente los tramos reales. Si el usuario completa
manualmente ese Sketch, pasa a ser la fuente autoritativa y no debe regenerarse sin
preservarlo.

### D. Crear muro BIM

Seleccionar un Sketch de centros con `FA_WallThickness` y ejecutar
`FA Muros BIM desde centros`.

El muro conserva el Sketch como `Base`, enlaza `Width` con el espesor y `Height` con la
altura, y se crea mediante `Arch.makeWall`.

### E. Recintos y areas

1. Ejecutar `FA Recopilar rotulos de recintos`.
2. Seleccionar el muro BIM autoritativo.
3. Ejecutar `AnalizarAreasDesdeMuroBIM.FCMacro`.

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

`InsertarPuertasBIMDesdeRecintos.FCMacro` proyecta cada eje sobre el muro, identifica
los recintos de ambos lados, escoge la bisagra mas cercana a una esquina, orienta la
hoja hacia el interior y crea el preset nativo `Simple door` alojado en el muro.

Contrato:

- Grupo `FA_BIMDoors` y hoja `Spreadsheet_Puertas_BIM`.
- `IfcType = Door`, `Opening = 100`, `SymbolPlan = True`.
- `FA_SourceGeometryIndex`, `FA_TargetRoom`, `FA_HingePoint`.
- `FA_CornerDistance`, `FA_OpeningSide`, `FA_InferenceConfidence`.

### G. Ventanas BIM

`InsertarVentanasBIMDesdeRecintos.FCMacro` proyecta ejes sobre lineas colineales
completas, admite paños largos que cruzan varios tramos del Sketch, enlaza recintos y
usa los parametros de antepecho y altura.

Presets actuales:

- ancho menor de 900 mm: `Open 1-pane`;
- ancho igual o mayor de 900 mm: `Sliding 2-pane`.

Contrato:

- Grupo `FA_BIMWindows` y hoja `Spreadsheet_Ventanas_BIM`.
- `IfcType = Window`, `Opening = 0`, `SymbolPlan = True`.
- `FA_SourceGeometryIndex`, `FA_WallOffset`, `FA_SillHeight`.
- `FA_WindowHeight`, `FA_PresetName`, `FA_AdjacentRooms`.
- `FA_InferenceConfidence`.

### H. Losa y estructura

`FA Losa y sitio BIM` calcula la huella desde Sketches arquitectonicos. Los Sketches
de columnas `P4` no deben ampliar la losa.

`FA Ejes y columnas BIM` crea `Arch Axis`, `AxisSystem` y columnas `Arch Structure`.
Esos ejes estructurales no deben confundirse con el ArchGrid arquitectonico.

### I. Cielo suspendido y luminarias ElectricCR

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

## 7. Trazabilidad y reemplazo seguro

Los flujos agregan `FA_GeneratedBy` y `FA_Role`. Al repetirse, reemplazan solamente
objetos creados por el mismo generador.

Generadores principales:

- `FA_CreateBuildingGrid` y `FA_CreateWallsBIM`.
- `FA_CollectRoomLabels`.
- `FA_RectangularAreaAnalysis`.
- `FA_InsertDoorsBIM`.
- `FA_InsertWindowsBIM`.
- `FA_CreateModularCeiling`.

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
        VERSION CARGADA: v0.7.0 | build 2026.08.05.1
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

Ultimo resultado verificado: 96 pruebas de Facil Arquitectura, 3 pruebas del
alineador modular de ElectricCR y 5 pruebas de navegacion Game Engine Export aprobadas.

Al integrar areas, puertas y ventanas como comandos nativos se deben agregar pruebas
puras de su logica geometrica antes de registrar los botones.

## 11. Limitaciones y ruta de desarrollo

- DWG y DXF se importan mediante FreeCAD/Draft; DWG requiere un convertidor compatible configurado.
- Areas, puertas y ventanas funcionan como macros complementarias; falta su integracion
  formal en `commands/` y `core/`.
- Los recintos irregulares requieren medicion poligonal.
- Los paños largos de ventana pueden requerir division en modulos.
- Los Sketches corregidos manualmente deben preservarse antes de regenerar.
- Faltan exportacion JSON y base electromecanica.

Ruta recomendada:

1. integrar el analisis de areas como comando nativo;
2. integrar puertas BIM y sus reglas de bisagra/apertura;
3. integrar ventanas BIM y presets configurables;
4. agregar medicion poligonal de recintos;
5. ampliar pruebas con un modelo sintetico equivalente a Puriscal.
