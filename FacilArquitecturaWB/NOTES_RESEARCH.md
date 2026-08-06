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
