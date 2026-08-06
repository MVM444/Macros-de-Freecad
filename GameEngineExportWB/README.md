# Game Engine Export WB

## Resumen / Summary

Game Engine Export WB prepara escenas de FreeCAD para Castle Game Engine con escala en metros, rotacion global en X de -90 grados y soporte para Viewpoint inicial, luces y persistencia de configuracion.

## Estado

Version inicial 0.1.0 (2025-10-13 13:54 UTC). Solo contiene la estructura base y paneles de interfaz sin logica de exportacion.

## Instalacion rapida

1. Mantener la carpeta `Macros-de-Freecad/GameEngineExportWB` dentro del directorio de macros de FreeCAD.
2. Reiniciar FreeCAD.
3. Seleccionar el workbench **Game Engine Export WB**.

## Abrir el proyecto en Visual Studio Code

1. Abre Visual Studio Code y elige **File > Open Folder**.
2. Selecciona la carpeta raiz que contiene `Macros-de-Freecad/GameEngineExportWB`.
3. Cuando el editor termine de indexar, podras navegar por los subdirectorios `core`, `ui`, `commands` y `resources`.
4. Si deseas conservar notas de las sesiones, utiliza el archivo `notes/GameEngineExportWB_chat.md` descrito mas adelante.

## Aplicar cambios en Visual Studio Code

1. Abre la misma carpeta del repositorio en Visual Studio Code.
2. En la vista **Source Control** revisa los cambios pendientes y usa **Pull** para traer la ultima version.
3. Conserva `GameEngineExportLoader.FCMacro` en la raiz de `FreeCAD/Macro` y `GameEngineExportWB` dentro de `Macros-de-Freecad`.
4. Ejecuta la macro `GameEngineExportLoader.FCMacro` desde FreeCAD para recargar el workbench y ver los cambios sin reiniciar.
5. Si modificas archivos, confirma en el panel de Source Control que los cambios se hayan guardado y versionado antes de probar en FreeCAD.

## Cargar el workbench en FreeCAD

1. Ejecuta `GameEngineExportLoader.FCMacro` desde la carpeta de macros de FreeCAD.
2. El loader cierra el TaskPanel activo, purga comandos/modulos anteriores, agrega `Macros-de-Freecad` al `sys.path` y registra de nuevo el workbench.
3. Desde la barra superior elige el workbench **Game Engine Export WB**.
4. Abre el comando **GameEngineExport Open** para mostrar el TaskPanel.
5. Veras mensajes `[GAMEEXPORT]` en la consola de reportes confirmando la carga.

## Uso rapido

Abre el comando **GameEngineExport Open** para mostrar el panel principal. Desde ahi puedes elegir la raiz de la escena, listas de objetos, marcador GameStart, iluminacion, cielo de Castle Viewer, materiales X3D y carpeta de salida.

El comando **Ejemplo rapido / Quick Example** (`GameEngineExport_QuickExample_*`) genera una casa u oficina de prueba con sketches, `Arch Wall`, buques de puertas/ventanas, terreno irregular y losa de piso. Sirve para crear escenas BIM rapidas cuando se quiere probar exportacion sin preparar un modelo manualmente.

Los sketches quedan como fuente parametrica:

- `GEE_SK_ExteriorWalls`
- `GEE_SK_InteriorWalls`
- `GEE_SK_DoorOpenings`
- `GEE_SK_WindowOpenings`

Las paredes se crean con `Arch.makeWall(...)` desde esos sketches. Los buques se crean como cutters parametricos enlazados a los sketches de puertas y ventanas, y se asignan como `Subtractions` de los muros.

El grupo `SiteAndFloors` incluye:

- `GEE_Terrain_Irregular`: terreno triangulado no plano para probar exportacion de suelo, sombras y textura.
- `GEE_Building_Floor_Slab`: losa/piso del edificio, elevada sobre el terreno y con sobresaliente visible. Si `Arch.makeStructure` esta disponible, se genera como estructura BIM; si no, queda como solido `Part`.

El panel permite activar `Aplanar terreno bajo edificio`. Con esa opcion, el area de la casa/oficina y un margen configurable quedan en una plataforma horizontal real dentro de la malla del terreno; si se desactiva, el relieve continua bajo la huella del edificio.

El generador tambien crea `AI_Contexto_QuickExample`, un `App::TextDocument` con JSON del ejemplo: dimensiones, semilla, recintos aproximados, sketches, muros, buques, terreno, losa y objetos creados. La opcion `Copiar contexto JSON al portapapeles` copia ese JSON al generar.

El comando **Importar JSON / Import JSON** (`GameEngineExport_ImportJSONExample`) abre un dialogo para pegar JSON de ChatGPT y reconstruir una casa u oficina con el mismo motor del Quick Example. Acepta JSON puro o texto con encabezado y extrae automaticamente el bloque desde el primer `{` hasta el ultimo `}`. La reconstruccion usa `dimensions`, `terrain`, `segments` y `rooms`; la seccion `objects` se ignora porque pertenece al documento anterior.

Flujo recomendado:

- Genere un `Quick Example`.
- Copie el JSON desde `AI_Contexto_QuickExample`.
- Modifique ese JSON en ChatGPT.
- Abra `Importar JSON / Import JSON`.
- Pegue el JSON y pulse `Generar`.

Hay un ejemplo en `examples/json/quick_example_house_sample.json`.

El comando **Puertas y ventanas BIM** agrega objetos de puerta/ventana sobre el ultimo `GEE_QuickExample_*`. Lee los sketches `GEE_SK_DoorOpenings` y `GEE_SK_WindowOpenings`, intenta crear objetos con `Arch.makeWindow(...)` y agrega hojas de puerta abiertas a 90 grados para pruebas visuales y de exportacion.

El comando **Agregar techo / Add Roof** agrega un techo sencillo al ultimo `GEE_QuickExample_*` generado o importado desde JSON. Lee `GEE_ContextJSON` cuando esta disponible, toma `width_mm`, `depth_mm`, `wall_height_mm` y los segmentos exteriores, y crea un techo a dos aguas como solido `Part::Feature` exportable a X3D. Internamente ejecuta `macros/AgregarTechoBIM_QuickExample.FCMacro`.

Parametros iniciales del techo:

- Tipo: dos aguas con cumbrera longitudinal.
- Alero: `600 mm`.
- Altura de cumbrera: `1800 mm` sobre la altura de muro.
- Espesor: `120 mm`.
- Material visual: teja oscura.

Por ahora no usa un objeto techo BIM complejo. Queda etiquetado con propiedades `GEE_Role = roof`, `IfcType = Roof`, `GEE_QuickExampleObject = True` y `GEE_BIMFallback = True` para exportacion, filtrado y futuras conversiones BIM.

Para proyectos que no vienen del Quick Example existen macros genericas:

- `CrearPuertasBIMDesdeSketch.FCMacro`: convierte el sketch seleccionado en puertas `Arch_Window` con `IfcType = Door` y apertura nativa `Opening = 100`.
- `CrearVentanasBIMDesdeSketch.FCMacro`: convierte el sketch seleccionado en ventanas `Arch_Window` con marco y vidrio definidos en `WindowParts`.

En ambos casos el sketch debe contener lineas de centro de los buques. No dependen de nombres `GEE_*` ni de grupos del generador. Las macros usan una transaccion de FreeCAD, por lo que `Ctrl+Z` elimina el conjunto completo creado.

Reglas de ventana:

- La cota `Z` del sketch o de la linea seleccionada se usa como base/antepecho de la ventana.
- La altura de ventana se indica en un dialogo.
- Si el sketch contiene geometria con variacion vertical suficiente en `Z`, la macro puede deducir la altura del buque.
- La macro genera un sketch rectangular de perfil por cada buque y llama `Arch.makeWindow(baseobj=perfil_sketch, parts=...)`, replicando el flujo de la herramienta BIM `Arch_Window` sin agregar geometria auxiliar `Part`.

## Materiales e iluminacion interior

En la pestana **Iluminacion / Lighting**, marca **Mejorar iluminacion interior / Improve interior lighting** y usa **Architectural** o **Bright** para interiores cerrados. Este ajuste solo modifica el X3D exportado mediante atributos `ambientIntensity`, `emissiveColor` y `shininess`; no cambia los materiales del archivo `.FCStd`.

Los `PointLight` exportados usan **Atenuacion / Falloff = Interior** para evitar una iluminacion constante hasta el borde del radio. Las **Sombras limitadas / Limited shadows** son experimentales y estan desactivadas por defecto: si se activan, solo se escriben en unas pocas luces para evitar errores de shader morado y lentitud en Castle Viewer.

Nota: las sombras dependen de la geometria. Paredes con espesor y caras cerradas funcionan mejor que superficies simples de una sola cara.

## Cielo Castle Viewer

En la pestana **Configuracion / Config**, marca **Usar cielo de Castle Viewer / Use Castle Viewer sky** para insertar un `Background` con seis imagenes de cielo en el X3D exportado.

La macro detecta la carpeta desde el ejecutable configurado. Si el ejecutable esta en `<CastleModelViewer>/castle-model-viewer.exe`, busca automaticamente `<CastleModelViewer>/example_models/skies`. Tambien puedes usar **Detectar / Detect** o **Examinar / Browse** si la carpeta esta en otra ubicacion.

El selector acepta una carpeta con archivos terminados en `back`, `bottom`, `front`, `left`, `right` y `top`, como `foggy_sky_back.png`.

Durante el postproceso, las imagenes se copian junto al X3D en `<BaseName>_assets/skies/` y el `Background` usa rutas relativas. Esto mantiene portable la exportacion y no modifica el archivo `.FCStd`.

Cuando la carpeta se detecta desde el ejecutable, el sidecar guarda el modo automatico en vez de guardar una ruta absoluta de usuario. Asi otro equipo puede usar su propio ejecutable Castle y su propia carpeta `example_models/skies`.

## Textura de suelo

En la pestana **Texturas / Textures**, puedes seleccionar el objeto suelo existente de FreeCAD y aplicar una textura solo al X3D exportado. Usa **Tomar seleccion / Use selection** con el suelo seleccionado, elige una imagen `.png`, `.jpg`, `.jpeg` o `.webp`, y ajusta **Repetir S/T**.

La textura se copia a `<BaseName>_assets/textures/` y se referencia con ruta relativa. El repetido se aplica con `TextureTransform scale="S T"`. Si **Generar UV planar XY / Generate planar XY UV** esta activo, el exportador crea `TextureCoordinate` desde las coordenadas X/Y del objeto para estabilizar el mapeo sobre el suelo.

Si el objeto guardado ya no existe en el documento actual, el panel lo avisa y el exportador intenta usar un objetivo de terreno por nombre, por ejemplo `terrain`, `ground`, `suelo`, `grass`, `floor` o `slab`. Esto cubre casos donde FreeCAD cambia el objeto exportado despues de regenerar un ejemplo o un compound.

## Herramienta Add Light Properties

El comando **Agregar propiedades a luz** (`GameEngineExport_AddLightProperties`) permite seleccionar una luminaria master o una instancia `App::Link`. Si se selecciona un Link, el comando resuelve el master y guarda alli las propiedades `CGE_Light*`; el Link no se modifica.

Durante la exportacion X3D, cada Link genera sus propios `PointLight` usando su `Placement`. La configuracion vive en el master y las instancias heredan intensidad, color, rango, direccion, offset y distribucion.

La vista previa crea objetos temporales `CGE_TempLightPreview*`, que se excluyen de la geometria exportada.

### Luminarias 3D automaticas

La opcion **Detectar luminarias 3D automaticamente / Auto-detect 3D luminaires** crea una luz para cada instancia `App::Link` de luminaria que tenga un solido con volumen. El origen se calcula con la envolvente de los solidos, no con la envolvente completa del objeto. Asi se ignoran simbolos 2D, lineas y anotaciones incluidos dentro del mismo master.

En distribuciones `Grid`, `Line` o `Ring`, la intensidad configurada representa la potencia total de la luminaria y se reparte entre los puntos generados. Esto evita que un panel de cuatro puntos produzca cuatro veces la intensidad solicitada.

Cuando la lista de exportacion esta vacia, el Workbench crea una seleccion 3D automatica. Si existe una lista explicita guardada, la conserva y aplica la misma politica para completarla con objetos 3D ocultos. Cuando esta activa **Incluir objetos 3D ocultos / Include hidden 3D objects**, incluye cualquier objeto con un solido de volumen positivo o una malla real aunque el objeto o su grupo esten ocultos. Esto cubre cielorrasos, columnas, equipos, mobiliario e instancias `App::Link` sin depender de los nombres usados por un proyecto. Excluye sketches, objetos `Part2DObject`, geometria de solo lineas, objetos identificados como 2D aunque tengan un espesor artificial, textos auxiliares, masters usados por `App::Link` y contenido de grupos de biblioteca, masters, internos, referencias, prototipos o catalogos.

Antes de llamar al exportador GUI, el Workbench activa temporalmente la visibilidad de los objetos seleccionados y sus grupos padre. Esto evita que FreeCAD omita dispositivos de grupos electricos o HVAC ocultos. Al terminar, incluso si ocurre una excepcion, restaura una instantanea completa de `ViewObject.Visibility` sin guardar el documento.

Para excepciones documentales, un objeto o su master enlazado puede tener propiedades booleanas `GameExportInclude` o `GameExportExclude`. La exclusion tiene prioridad. Estas propiedades son opcionales; el Workbench no las agrega ni modifica automaticamente.

La deteccion automatica de luminarias acepta nombres comunes, metadatos semanticos como `IfcType`, `PredefinedType`, `ObjectType`, `Category`, `Role`, `EquipmentType`, `DeviceType` y `GameExportRole`, o una propiedad booleana `IsGameExportLuminaire`, `IsLuminaire` o `IsLightFixture`. Siempre exige un solido 3D con volumen antes de generar una luz.

## Vista previa Web

En **Salida / Output**, el boton **Vista previa Web / Web preview** exporta el X3D con el mismo flujo normal, genera un `index.html` junto al X3D e inicia un servidor HTTP local en segundo plano. El navegador abre siempre `http://127.0.0.1:<puerto>/index.html`; no se utiliza `file://`.

El servidor usa solo librerias estandar de Python, escucha exclusivamente en `127.0.0.1`, busca un puerto libre entre 8000 y 9000 y sirve unicamente la carpeta del HTML. Se reutiliza para vistas de la misma carpeta y se cierra al cambiar de carpeta, tras 15 minutos sin solicitudes, durante la recarga del Workbench o al terminar FreeCAD.

La pagina usa X3DOM estable desde `https://www.x3dom.org/release/`. El `Scene` del X3D se inserta directamente dentro del HTML, conservando `Viewpoint` y `NavigationInfo`. El generador convierte etiquetas X3D autocerradas a cierres explicitos compatibles con HTML y muestra un estado de carga en la barra superior. Los assets relativos, como texturas y cielos en `<BaseName>_assets/`, siguen funcionando. Las referencias locales absolutas o `file://` se convierten a rutas relativas; si apuntan fuera de la carpeta servida, el recurso se copia a `.gee_web_assets/`.

Para evitar interiores oscuros en archivos sin iluminacion, el HTML activa `headlight="true"` en una copia del `NavigationInfo` solo cuando no existen nodos `DirectionalLight`, `PointLight` o `SpotLight`. Si el X3D ya contiene luces, conserva el valor exportado para no sobreexponer la vista previa. Este ajuste no modifica el X3D exportado, el documento FreeCAD ni la iluminacion usada por Castle Game Engine.

## Archivos incluidos

- `Init.py`, `InitGui.py`: arranque del workbench y registro de comandos.
- `core/`: modulos para exportar, manejar luces, persistencia y utilidades.
- `ui/`: paneles TaskPanel de escena, configuracion y texto informativo.
- `commands/`: comando principal GameEngineExport_Open.
- `core/quick_examples.py`: generador de ejemplos rapidos con Sketcher y Arch Wall.
- `core/json_importer.py`: lectura, validacion y reconstruccion de Quick Example desde JSON.
- `macros/AgregarPuertasVentanasBIM_QuickExample.FCMacro`: macro usada por el comando de puertas y ventanas BIM.
- `macros/AgregarTechoBIM_QuickExample.FCMacro`: macro independiente para agregar un techo simple exportable al ultimo Quick Example.
- `macros/bim_from_selected_sketch.py`: base reutilizable para crear puertas o ventanas desde el sketch seleccionado.
- `macros/CrearPuertasBIMDesdeSketch.FCMacro`: macro generica de puertas desde sketch seleccionado.
- `macros/CrearVentanasBIMDesdeSketch.FCMacro`: macro generica de ventanas desde sketch seleccionado.
- `resources/icons/gameexport.svg`: icono del workbench.
- `resources/icons/add_light_properties.svg`: icono del comando para propiedades de luz.
- `resources/icons/quick_example.svg`: icono del comando de ejemplo rapido.
- `resources/icons/import_json_example.svg`: icono del comando para importar JSON.
- `resources/icons/bim_doors_windows.svg`: icono del comando para puertas y ventanas BIM.
- `resources/icons/quick_example_roof.svg`: icono del comando para agregar techo simple.
- `examples/json/quick_example_house_sample.json`: payload de prueba para importacion JSON.
- `notes/GameEngineExportWB_chat.md`: registro de conversaciones y decisiones relevantes.
- `notes/add_light_properties.md`: nota tecnica del comando de propiedades de luz.
- `notes/web_preview.md`: nota tecnica de la vista previa Web con X3DOM.
- `notes/puriscal_complete_export.md`: diagnostico y validacion de la exportacion completa de Puriscal.
- `notes/reusable_export_pipeline.md`: politica general reutilizable de seleccion, visibilidad, luminarias y diagnostico.
- `notes/environment_skybox.md`: nota tecnica de cielo cubemap X3D.
- `notes/ground_texture.md`: nota tecnica de textura aplicada a objeto suelo exportado.
- `../GameEngineExportLoader.FCMacro`: macro para recargar el workbench en FreeCAD sin reiniciar.

## Ubicacion dentro del repositorio / Location inside repository

- El codigo fuente del workbench vive en `Macros-de-Freecad/GameEngineExportWB` dentro del repositorio.
- El icono y otros recursos estan en `Macros-de-Freecad/GameEngineExportWB/resources`.
- La macro de recarga rapida esta en la raiz del repositorio como `GameEngineExportLoader.FCMacro`.
- Si abres el repositorio desde Visual Studio Code veras la macro en el nivel superior junto a la carpeta `Macros-de-Freecad/`.
- Al clonar o descargar desde GitHub, verifica que la carpeta `Macros-de-Freecad/GameEngineExportWB` exista.
- En el disco local puedes usar **File > Open Folder** en Visual Studio Code y apuntar a la carpeta que contiene `Macros-de-Freecad/GameEngineExportWB`; en el panel izquierdo deberias ver tambien `GameEngineExportLoader.FCMacro`.

## Ubicacion del loader / Loader location

- Ruta relativa dentro del repositorio: `GameEngineExportLoader.FCMacro`.
- En FreeCAD, el archivo anterior queda en `FreeCAD/Macro` y busca el workbench en `Macros-de-Freecad/GameEngineExportWB`.
- En caso de dudas, busca `[GAMEEXPORT]` en la consola de FreeCAD despues de ejecutar la macro para confirmar que se encontro y cargo el workbench.

## Workbench vs macro

- **Workbench**: ofrece menus y toolbars propios, y carga paneles dedicados sin mezclar con otras macros. Es mas facil mantener configuraciones (ParamGet) y sidecars por archivo, y se actualiza como paquete completo.
- **Macro unitaria**: suele ser un unico archivo en `Macro/`, rapida de compartir pero tiende a mezclar UI y logica en un bloque, con menos separacion de modulos y sin menues persistentes. Para funciones simples es ligera, pero para flujos largos se vuelve dificil de mantener.
- **En este proyecto**: se eligio workbench porque necesitamos paneles, comandos y persistencia, ademas de iconos y recursos adicionales. La macro `GameEngineExportLoader` solo se usa para recargar rapido durante el desarrollo.

## Creditos

Creado por el Ing. Marco Vinicio Mora Fallas con ayuda de ChatGPT (99.9%).

