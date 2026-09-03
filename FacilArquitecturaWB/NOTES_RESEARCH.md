# NOTES_RESEARCH - FacilArquitecturaWB

Fecha: 2026-07-13
Proyecto: FacilArquitecturaWB
Objetivo: investigar si existen macros, Workbenches, plugins o flujos de trabajo de FreeCAD relacionados con importar planos DXF/PDF/imagen y convertirlos gradualmente en una base BIM editable.

## 1. Resumen ejecutivo

No se encontro una herramienta unica y madura que convierta automaticamente un plano CAD/PDF/PNG/JPG en un modelo BIM completo y confiable de FreeCAD. Lo que si existe es un conjunto de herramientas y flujos parciales que conviene reutilizar:

- FreeCAD Draft DXF para importar/exportar DXF.
- ODA File Converter, QCAD Pro o alternativas para convertir DWG a DXF cuando el origen es DWG.
- Arch Workbench / BIM Workbench para crear muros, estructuras, ventanas, espacios, ejes y otros objetos arquitectonicos parametricos.
- Image Plane / imagen de referencia calibrada para trabajar con planos raster, PNG, JPG o PDF escaneado convertido a imagen.
- QCAD Professional o Inkscape como herramientas externas opcionales para convertir PDF vectorial a DXF/SVG o para limpiar/vectorizar contenido antes de llevarlo a FreeCAD.

Conclusion: FacilArquitecturaWB debe ser un orquestador de flujo de trabajo, no un reemplazo del Workbench BIM. Debe importar/referenciar, limpiar, organizar, crear sketches maestros y llamar herramientas existentes de FreeCAD para generar BIM.

## 2. Hallazgos por necesidad

### 2.1 Importar DXF y limpiarlo

Hallazgo:
FreeCAD dispone del modulo Draft DXF para abrir, importar y exportar archivos DXF. Para DWG, FreeCAD puede apoyarse en convertidores externos que pasan DWG a DXF antes de usar el importador DXF.

Fuente principal:
- FreeCAD Wiki / Draft DXF.
- FreeCAD documentation / FreeCAD and DWG Import.

Reutilizacion recomendada:
- No crear un importador DXF propio.
- Usar el flujo existente de FreeCAD para importar DXF.
- FacilArquitecturaWB debe crear grupos, aislar referencia, ocultar o clasificar capas/objetos y preparar herramientas para copiar geometria limpia hacia sketches maestros.

Pendiente tecnico:
- Revisar con Codex como FreeCAD expone capas, grupos y objetos importados desde DXF.
- Crear herramienta FA_CleanReference solo como organizador inicial, no como limpiador avanzado automatico.

### 2.2 Convertir lineas o sketches en muros BIM

Hallazgo:
Arch Workbench puede crear muros desde cero o usando un objeto seleccionado como base. Arch usa objetos 2D de Draft para construir objetos arquitectonicos 3D parametricos. La documentacion indica que Arch/BIM ya contiene muros, estructuras, ventanas, espacios, ejes, grids y otros elementos.

Fuente principal:
- FreeCAD documentation / Arch Workbench.
- Arch Wall documentation.

Reutilizacion recomendada:
- No crear un objeto muro propio.
- Crear sketches maestros como Sketch_Muros_Ext_200 y Sketch_Muros_Int_100.
- Generar muros mediante Arch.makeWall o herramientas equivalentes.
- Guardar propiedades FA_SourceSketch, FA_WallType, FA_Thickness_mm y FA_Height_mm.

Pendiente tecnico:
- Validar en FreeCAD 1.1.1 el comportamiento de Arch.makeWall con Sketcher::SketchObject y con multiples lineas dentro de un mismo sketch.
- Determinar si conviene un muro por sketch o un objeto Arch Wall por cada sketch maestro.

### 2.3 Usar sketches maestros para generar arquitectura base

Hallazgo:
No se encontro un flujo oficial especifico llamado sketches maestros para arquitectura en FreeCAD, pero el enfoque es compatible con la filosofia parametrica de FreeCAD y con Arch/BIM, porque Arch puede usar objetos 2D como base de objetos 3D.

Reutilizacion recomendada:
- Crear un conjunto controlado de sketches maestros por sistema o tipo constructivo:
  - Sketch_Terreno
  - Sketch_Ejes
  - Sketch_Columnas
  - Sketch_Muros_Ext_200
  - Sketch_Muros_Int_100
  - Sketch_Puertas_900
  - Sketch_Ventanas_1200x1200
  - Sketch_Losa_Piso
- No crear un sketch por objeto individual.
- Vincular parametros principales desde una hoja Spreadsheet_Parametros.

Pendiente tecnico:
- Definir hasta que punto las restricciones de Sketcher deben ser automaticas o manuales.
- Crear comandos iniciales que generen sketches vacios o con geometria de ejemplo editable.

### 2.4 Convertir PDF a modelo FreeCAD

Hallazgo:
FreeCAD no debe tratarse como conversor principal de PDF a BIM. Si el PDF es vectorial, QCAD Professional puede abrir PDF y extraer datos vectoriales; tambien se puede usar Inkscape/SVG/DXF como flujo auxiliar. Si el PDF es escaneado, realmente es una imagen y debe tratarse como referencia, no como CAD editable confiable.

Fuente principal:
- QCAD Professional documentation / PDF Files.
- Foros de FreeCAD sobre PDF, SVG y DXF.

Reutilizacion recomendada:
- No implementar conversion PDF automatica en la primera etapa.
- Documentar flujo externo: PDF vectorial -> QCAD/Inkscape -> DXF/SVG -> FreeCAD.
- En FacilArquitecturaWB, concentrarse primero en DXF ya importado o importable.

Pendiente tecnico:
- En una etapa futura, crear FA_ImportReferencePDF solo como asistente documental, no como conversion BIM automatica.

### 2.5 Convertir PNG/JPG o PDF escaneado a modelo BIM

Hallazgo:
FreeCAD permite importar imagenes como referencia, colocarlas en el plano XY, calibrar escala con una distancia conocida y dibujar encima. La vectorizacion de imagenes con Inkscape existe, pero no produce una representacion 100% fiel y puede generar geometria pesada o dificil de editar.

Fuente principal:
- FreeCAD News / Tutorial: Importing and Using Scaled Reference Images.
- Inkscape Beginners' Guide / Tracing an Image.

Reutilizacion recomendada:
- Para imagenes, usar flujo asistido: importar imagen, calibrar, trazar sobre ella, generar sketches maestros.
- No prometer conversion automatica PNG/JPG -> BIM.
- En la primera etapa, solo dejar preparada la estructura para una futura herramienta FA_ImportImageReference.

Pendiente tecnico:
- Implementar mas adelante una herramienta de calibracion basada en dos puntos y una medida conocida, si FreeCAD no lo cubre de forma suficientemente comoda para el usuario.

## 3. Herramientas existentes que conviene reutilizar

### FreeCAD / Draft DXF
Uso recomendado:
- Importacion principal para DXF.
- No desarrollar importador propio.

### FreeCAD / Arch Workbench
Uso recomendado:
- Muros, estructuras, ventanas, espacios, ejes, grids, site, building, levels.
- Usar Arch.makeWall, Arch.makeStructure y objetos Arch existentes.

### FreeCAD / BIM Workbench
Uso recomendado:
- Interfaz mas amigable sobre Arch.
- No reemplazarlo; FacilArquitecturaWB debe coexistir y apoyarse en BIM.

### FreeCAD / Image Plane
Uso recomendado:
- Referencia calibrada para PNG/JPG/PDF escaneado.
- Trazado asistido sobre imagen.

### QCAD Professional
Uso recomendado:
- Conversion externa para PDF vectorial o DWG/DXF en flujos donde FreeCAD tenga limitaciones.

### Inkscape
Uso recomendado:
- Limpieza SVG o vectorizacion puntual.
- No usar como promesa de conversion exacta de imagen a CAD.

## 4. Decision de diseno para FacilArquitecturaWB

El Workbench debe iniciar con el caso mas controlable:

DXF -> referencia organizada -> sketches maestros -> muros BIM basicos.

No debe iniciar con:

PDF/PNG/JPG -> deteccion automatica -> BIM completo.

## 5. Primer alcance recomendado

Comandos iniciales:

1. FA_CreateProject
   - Crea grupos base.
   - Crea Spreadsheet_Parametros.

2. FA_CreateMasterSketches
   - Crea sketches maestros editables.
   - Puede incluir geometria simple de ejemplo.

3. FA_CreateWallsBIM
   - Toma Sketch_Muros_Ext_200 y Sketch_Muros_Int_100.
   - Crea muros con Arch.makeWall.

Comandos futuros:

- FA_ImportDXF
- FA_CleanReference
- FA_CopySelectedLinesToSketch
- FA_CreateColumnsBIM
- FA_CreateSlabBIM
- FA_CreateDoorsWindowsBIM
- FA_CreateAreas
- FA_ImportImageReference
- FA_CalibrateReference
- FA_ExportJSON

## 6. Riesgos identificados

- DXF puede venir sucio, con lineas duplicadas, bloques, hachurados, cotas y textos.
- DWG no debe asumirse nativo; generalmente debe pasar por conversion a DXF.
- PDF vectorial puede traer demasiadas entidades o geometria fuera de papel.
- PDF escaneado/PNG/JPG no contiene entidades CAD, solo pixeles.
- Vectorizar imagenes no garantiza exactitud ni buena topologia BIM.
- La deteccion automatica de muros, puertas y ventanas es un problema avanzado y debe dejarse para etapas futuras.

## 7. Recomendacion final

FacilArquitecturaWB debe iniciar como una herramienta simple y robusta de preparacion:

- Crear estructura de proyecto.
- Crear parametros.
- Crear sketches maestros.
- Convertir sketches de muros en Arch Walls.

Luego evolucionar hacia importacion/limpieza asistida de DXF y, posteriormente, hacia imagenes/PDF como referencias calibradas.

## 8. Actualizacion 2026-08-09 - reconstruccion BIM nativa

La revision del codigo instalado de FreeCAD 1.1.3 confirmo:

- `Arch.makeBuilding()` crea un `BuildingPart` con `IfcType = Building`.
- `Arch.makeFloor()` crea un `BuildingPart` con `IfcType = Building Storey`.
- `Arch.makeWall(sketch)` conserva el Sketch directamente como `Base` parametrica.
- `Arch.makeStructure()` produce las columnas nativas usadas por BIM.
- `Arch.makeWindowPreset()` y `Hosts = [wall]` producen Door/Window nativas y el
  muro obtiene el hueco mediante el mecanismo de subvolumen de `ArchWindow`.
- `Arch.makeSpace()` existe, pero la generacion automatica de Spaces y la losa se
  difieren hasta validar topologia cerrada con la misma profundidad que los muros.

La contencion nativa se realiza con `Building.Group -> Level` y
`Level.Group -> objetos`. No se debe agregar un `PropertyLink` inverso desde cada
objeto hacia el Level: FreeCAD considera esa combinacion un ciclo del grafo. La
trazabilidad `FA_TargetLevel` se guarda por eso como nombre estable en texto.

Se comprobo ademas que `Arch.makeWindowPreset()` ejecuta varias recomputaciones por
abertura. En un muro compuesto con decenas de puertas/ventanas el resultado sigue
siendo correcto, pero puede tardar varios minutos. La prueba automatica de La Cruz
usa todas las paredes y columnas y una muestra real de cada abertura para mantener
un tiempo acotado; el asistente permite seleccionar todas las fuentes en uso normal.

## 9. Actualizacion 2026-08-10 - plataforma de atencion desde linea

Se revisaron la documentacion y el catalogo oficial antes de implementar el flujo:

- BIM/Arch incluye objetos parametricos generales —muros, ventanas, paneles y
  mobiliario—, pero no un generador especifico de mostradores de atencion con
  paños de vidrio y puestos repetidos:
  <https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Arch_Workbench.md>.
- Draft admite lineas y objetos 2D con cualquier posicion/orientacion y estos pueden
  servir de base a objetos 3D:
  <https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Draft_Workbench.md>.
- Sketcher aporta la linea parametrica, su `Placement` y restricciones, por lo que
  no conviene copiar ni reemplazar el Sketch seleccionado:
  <https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Sketcher_Workbench.md>.
- El catalogo oficial contiene workbenches de gabinetes/madera, pero sus objetivos
  son manufactura de muebles y no resuelven el contrato BIM/CCSS de una plataforma
  institucional: <https://www.freecad.org/addons.php?lang=eng>.

Decision: no instalar una dependencia adicional. FacilArquitectura reutiliza la
seleccion de aristas/Sketches, `Placement`, `Part.makeBox`, `Part.makeCompound` y los
muros Arch existentes. El resultado conserva `SourceObject`, `SourceSubelement` y
`HostWall`, y mantiene en una ruta separada el generador historico de seis Sketches.

## 10. Actualizacion 2026-08-10 - abertura de atencion en vidrio

El detalle lateral y frontal confirma mostrador a 740 mm y vidrio hasta 1800 mm.
La ficha PL-01 identifica el frente Vc002 como vidrio de 16 mm con intercomunicador,
pero no aporta una cota inequivoca para el hueco de atencion. Vc003 (60 x 60) es una
ventana distinta y no se usa para dimensionar el frente.

Decision: generar una abertura real por modulo mediante piezas simples dentro del
mismo compound `Vidrios_Plataforma`. El valor inicial 300 x 300 mm es provisional,
editable y expresamente no normativo. El builder historico no cambia.

## 11. Actualizacion 2026-08-12 - Opening Element desde Sketch

La revision de fuentes primarias y del codigo instalado de FreeCAD 1.1.3 confirmo:

- `ArchWindowPresets.WindowPresets` incluye `Opening only`.
- Ese preset crea un rectangulo cerrado, usa `Arch.makeWindow(..., parts=[])` y
  asigna `IfcType = Opening Element`.
- `ArchWindow.getSubVolume()` usa el mayor wire del `Base`, calcula la profundidad
  desde el Wall anfitrion y devuelve el volumen que el Wall sustrae.
- La prueba oficial `TestArchWindow.test_custom_subvolume_creates_opening` valida
  que un Arch Window hospedado reduce realmente el volumen del muro.

Fuentes oficiales:

- <https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/BIM/ArchWindowPresets.py>
- <https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/BIM/ArchWindow.py>
- <https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/BIM/Arch.py>
- <https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Arch_Window.md>

Decision: extender `core/opening_utils.py` con el tipo `opening`. Para lotes se
reproduce el mecanismo nativo del preset mediante perfil cerrado y
`Arch.makeWindow(parts=[])`, evitando las recomputaciones internas por instancia.
No se crean booleanos FA, hojas, marcos, vidrios ni simbolos.
# Investigacion 2026-08-13 - cambio de tipo de puerta

La instalacion real FreeCAD 1.1.3 publica `WindowPresets` como lista de nombres y
solo contiene dos nombres de puerta: `Simple door` y `Glass door`; no contiene
`Sliding door`. `ArchWindowPresets.makeWindowPreset()` crea un Sketch, llama a
`Arch.makeWindow`, asigna `Preset`, `Frame`, `Offset` e `IfcType = Door` y hace
varios recomputes. `ArchWindow._Window.onChanged()` reacciona a Base,
`WindowParts`, Placement, dimensiones, Hosts y Opening, pero no a `Preset`.
La prueba real confirmo que transferir Base/WindowParts al mismo objeto conserva su
identidad y mantiene el Wall perforado.

# Investigacion 2026-08-23 - ElementData, tablas y herramientas nativas

Para transferir propiedades de ventanas entre versiones de un mismo proyecto se reviso primero la arquitectura existente de FacilArquitecturaWB y las herramientas nativas de FreeCAD/BIM.

Hallazgos y decisiones:

- Las ventanas FA ya son `ArchWindow._Window` nativas. No crear un objeto paralelo `FA_Window`.
- `Spreadsheet::Sheet` es adecuado como representacion visible, copiable y editable de datos por categoria.
- Evitar una Spreadsheet unica con todas las categorias y muchas columnas vacias. Usar tablas visibles separadas por categoria con un nucleo comun.
- Evitar una red bidireccional permanente de Expressions entre la misma hoja y los objetos si introduce ciclos o dependencias dificiles de mantener. Preferir operaciones explicitas `extraer -> validar -> aplicar`.
- FreeCAD/BIM dispone de mecanismos de Schedule/reporte/consulta y administracion de puertas/ventanas que deben verificarse mediante MCP antes de duplicar seleccion, consulta o GUI.
- El antepecho debe tratarse como dato transferible explicito y aplicarse mediante la API/Placement nativa validada en FreeCAD 1.1.3; no asumir una propiedad `SillHeight` estable sin comprobarla.
- El matching entre una tabla vieja y un Sketch nuevo no debe depender solamente de `GeometryIndex`; usar tambien firma geometrica `centro + longitud + angulo` con tolerancias y estados `MATCH/CAMBIO/NO_MATCH/AMBIGUO`.
- El Sketch es autoridad de posicion, orientacion y ancho. La tabla es autoridad de altura, antepecho, preset/tipo y datos descriptivos. El host y Level se resuelven de nuevo en el modelo destino.

Se creo la especificacion `DISENO_ELEMENTDATA_TABLAS.md` como contrato previo a Codex.

Fuentes base:

- https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/BIM/ArchWindow.py
- https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/BIM/ArchWindowPresets.py
- https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Spreadsheet_Workbench.md
- https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Expressions.md
- https://github.com/FreeCAD/FreeCAD-documentation

La disponibilidad exacta de Schedule/Report/Manage Doors and Windows debe comprobarse con MCP en la instalacion real FreeCAD 1.1.3 antes de implementar una capa paralela.

