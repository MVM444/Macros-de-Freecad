# FacilArquitecturaWB - Especificacion FA Techo, Cerchas y Clavadores


Fecha: 2026-08-29 America/Costa_Rica
FreeCAD objetivo: 1.1.3
Workbench: FacilArquitecturaWB
Estado: DISENO / INVESTIGACION PREVIA A IMPLEMENTACION


## 1. Proposito


Definir el subsistema de techo de FacilArquitecturaWB antes de desarrollar el ejemplo automatico.
La herramienta debe seguir la filosofia del Workbench: el usuario dibuja y edita Sketches
simples; FA interpreta esos Sketches y crea o actualiza objetos BIM nativos de FreeCAD.


No se pretende crear objetos BIM paralelos ni reemplazar las herramientas existentes de BIM.
FA actua como capa de orquestacion y simplificacion, orientada a los sistemas de techo de uso
comun en Costa Rica y Latinoamerica.


## 2. Regla principal de flujo


Siempre que sea razonable:


Sketch editable -> interpretacion FA -> datum/eje BIM cuando corresponda -> objeto BIM nativo


Para techo:


- Sketch de ejes de cerchas -> ejes/referencias FA-BIM -> celosias/cerchas BIM.
- Sketch de clavadores -> layout -> Frame/Structure BIM con perfil seleccionado.
- Sketch de cubierta -> contorno cerrado -> Roof BIM.


El Sketch es la fuente geometrica editable. El objeto BIM es el resultado constructivo.


## 3. Capacidades nativas que se deben reutilizar


### 3.1 Truss / celosia


FreeCAD BIM dispone de Truss. Puede crearse a partir de un objeto lineal seleccionado,
incluyendo una linea Draft o un Sketch. La API expone Arch.makeTruss(baseobj).


Propiedades nativas relevantes que deben validarse en FreeCAD 1.1.3 antes de cerrar la API FA:


- TrussAngle
- SlantType
- Normal
- HeightStart
- HeightEnd
- StrutStartOffset
- StrutEndOffset
- StrutHeight
- StrutWidth
- RodType
- RodDirection
- RodSize
- RodSections
- RodEnd
- RodMode


FA no debe duplicar la generacion interna de barras si Truss nativo resuelve adecuadamente
la geometria requerida. Los presets regionales de FA deben traducirse a estas propiedades.


### 3.2 Roof / cubierta inclinada


FreeCAD BIM dispone de Roof. Arch.makeRoof() crea una cubierta a partir de un contorno cerrado.
Permite definir por borde angulo, recorrido/run, espesor, alero/overhang y relaciones entre faldones.


Esto debe ser la primera opcion para la envolvente general de cubierta.


### 3.3 Frame / clavadores y correas


Arch Frame crea elementos mediante la extrusion de un perfil sobre las aristas de un layout,
que puede ser un Sketch. Permite Align, Rotation, Offset y seleccion de aristas.


Es un candidato directo para los clavadores/correas, porque conserva exactamente el flujo
Sketch -> perfil -> elementos lineales 3D.


Los perfiles deben reutilizar Arch Profile o perfiles propios compatibles con BIM cuando sea posible.
FreeCAD admite perfiles parametrizados y perfiles personalizados mediante profiles.csv.


### 3.4 Panel


Arch Panel puede representar paneles, incluso ondulados/trapezoidales. No debe sustituir a Roof
como envolvente principal en la primera version, pero puede evaluarse posteriormente para una
representacion detallada de laminas metalicas individuales o panelizadas.


## 4. Terminologia FA para Costa Rica y Latinoamerica


La interfaz debe usar lenguaje comprensible regionalmente y conservar equivalencias tecnicas:


- Cercha / Celosia: objeto principal de estructura reticulada. Internamente, Truss BIM cuando aplique.
- Clavador / Correa: elemento secundario que recibe la cubierta. Internamente, Frame o Structure.
- Cubierta: envolvente superior inclinada. Internamente, Roof BIM inicialmente.
- Cumbrera: encuentro superior de faldones.
- Alero: proyeccion de cubierta mas alla del apoyo.
- Faldon: plano inclinado de la cubierta.


En la interfaz puede mostrarse "Clavadores / correas" para evitar ambiguedad entre paises.


## 5. Flujo propuesto de usuario


### 5.1 Cerchas


1. Crear o seleccionar un Sketch dentro del Level.
2. Cada linea valida representa una posicion logica de cercha; una familia congruente se materializa con una sola Base y un solo Truss repetido por Axis.
3. Ejecutar `FA Crear cerchas`.
4. FA valida lineas, Level, cotas y orientacion.
5. FA crea/reutiliza el datum/eje necesario y genera una celosia BIM por linea.
6. El Sketch fuente queda enlazado para actualizacion posterior.


El usuario no debe necesitar cambiar al Workbench BIM ni editar directamente propiedades internas
de Truss para un caso habitual.


### 5.2 Clavadores / correas


Dos modos deben estudiarse:


A. Sketch explicito:
- el usuario dibuja las lineas de clavadores sobre el plano o faldon;
- FA usa ese Sketch como layout y genera Frame/Structure con el perfil seleccionado.


B. Generacion parametrica desde cubierta/cerchas:
- el usuario indica separacion nominal;
- FA calcula lineas de clavadores sobre cada faldon;
- FA conserva una representacion fuente editable o regenerable, evitando geometria opaca.


Para la primera implementacion se prefiere el modo A o un modo B muy controlado, porque mantiene
la filosofia de Sketches como fuente de verdad.


### 5.3 Cubierta


1. Crear o seleccionar un Sketch cerrado que defina la huella/contorno de cubierta.
2. Ejecutar `FA Crear cubierta`.
3. Elegir tipologia basica: una agua o dos aguas inicialmente.
4. Definir pendiente, alero y espesor.
5. FA traduce esos datos a Roof BIM.
6. El Sketch permanece como Base/fuente parametricamente trazable siempre que la API nativa lo permita.


## 6. Tipologias iniciales


Primera fase:


- Cubierta a una agua.
- Cubierta a dos aguas.
- Cercha/celosia simple compatible con Truss nativo.
- Clavadores/correas rectos con perfil seleccionable.


Preparar arquitectura para fases posteriores:


- cuatro aguas;
- cubiertas combinadas;
- limatesas y limahoyas;
- cerchas regionales parametrizadas;
- canoas y bajantes;
- panelizacion detallada de lamina;
- elementos de borde, fascia y cumbrera.


No intentar resolver todas estas variantes en la primera version.


## 7. Presets regionales


FA debe ofrecer presets de uso, pero nunca confundirlos con calculo estructural certificado.


Ejemplos de datos de preset:


- sistema: cercha metalica liviana;
- tipo de cubierta: una agua / dos aguas;
- pendiente;
- separacion de cerchas;
- perfil de elementos principales;
- perfil de diagonales/montantes cuando Truss lo permita;
- tipo y separacion de clavadores;
- perfil de clavadores;
- alero;
- espesor/tipo documental de cubierta.


Los perfiles y separaciones deben considerarse datos de modelado. Si en el futuro se agrega calculo
estructural, este debe ser un modulo claramente separado y verificable.


## 8. Arquitectura de software preferida


core/roof_definition.py
- modelos de datos JSON-compatible;
- validacion geometrica y semantica independiente de FreeCADGui/Qt;
- presets y normalizacion de parametros.


freecad/truss_adapter.py
- adaptacion a Arch.makeTruss y propiedades de Truss;
- lectura/actualizacion de objetos existentes;
- sin logica GUI.


freecad/purlin_adapter.py
- adaptacion a Arch.makeFrame / Arch Structure / perfiles;
- generacion desde Sketch/layout.


freecad/roof_adapter.py
- adaptacion a Arch.makeRoof;
- lectura/actualizacion y enlace con Sketch fuente.


commands/
- FA_CreateTrussesFromSketch
- FA_CreatePurlinsFromSketch
- FA_CreateRoofFromSketch


La GUI y comandos deben ser finos. La logica principal debe quedar reutilizable desde FreeCAD,
macros pequenas, MCP y futuras pruebas automatizadas.


## 9. Datos y trazabilidad


Los objetos generados por FA deben conservar, cuando sea razonable:


- SourceSketch
- GeometryIndex o identificador estable de linea/contorno
- Level
- tipo FA
- parametros de preset
- version/schema de datos
- referencia a perfil
- relacion con objeto BIM nativo


La reejecucion debe preferir KEEP/UPDATE/REPLACE seguro en lugar de duplicar objetos.
No sustituir objetos manuales ambiguos sin diagnostico.


## 10. JSON


El subsistema debe poder representarse con datos JSON-compatible para reutilizacion futura y para
el ejemplo automatico. El JSON describe intencion arquitectonica, no operaciones GUI.


Ejemplo conceptual:


```json
{
  "roof_system": {
    "type": "gable",
    "pitch_deg": 20,
    "eave_mm": 600,
    "trusses": {
      "source_sketch": "Sketch_Ejes_Cerchas",
      "preset": "metal_light"
    },
    "purlins": {
      "source_sketch": "Sketch_Clavadores",
      "profile": "C",
      "spacing_mm": 1000
    },
    "covering": {
      "source_sketch": "Sketch_Cubierta",
      "native_type": "Roof",
      "thickness_mm": 50
    }
  }
}
```


## 11. Representacion documental 2D


El subsistema debe producir informacion comprensible en planos:


- ejes de cerchas identificables;
- cerchas numeradas o etiquetadas;
- direccion y separacion de clavadores/correas;
- pendiente de faldones;
- cumbrera;
- aleros;
- contorno de cubierta;
- seccion o elevacion basica de cercha cuando corresponda.


La geometria 3D no sustituye esta salida documental.


## 12. Validacion obligatoria antes de estabilizar e integrar


Se permite avanzar implementacion aislada, pruebas puras y adaptadores sin GUI. Antes de registrar comandos como funcionalidad estable, incrementar version/build o declarar el subsistema validado, comprobar en FreeCAD real mediante MCP:


1. Crear Truss nativo desde una linea de Sketch y comprobar Base/Placement/propiedades.
2. Determinar exactamente que geometria de cercha produce cada SlantType/RodMode y si permite
   representar una cercha comun de una o dos aguas de CR/LatAm sin geometria paralela.
3. Modificar el Sketch fuente y comprobar si Truss actualiza correctamente.
4. Crear Roof nativo desde Sketch cerrado y comprobar actualizacion al editar huella, pendiente y alero.
5. Crear Frame desde Sketch de varias lineas y un perfil C/RH; comprobar orientacion, Align, Rotation,
   offsets, rendimiento y estabilidad al editar el Sketch.
6. Verificar contencion correcta dentro de Building/Level.
7. Verificar guardar/cerrar/reabrir.
8. Verificar Undo/Redo y reejecucion sin duplicados.
9. Verificar una representacion 2D razonable para planta y seccion.


Si Truss nativo no representa bien la tipologia regional necesaria, documentar primero la limitacion.
Solo entonces estudiar una extension sobre objetos BIM nativos, evitando crear un sistema paralelo.


## 13. Secuencia de desarrollo antes del ejemplo automatico


Fase A - Cerchas
- diagnostico MCP del Truss nativo;
- adaptador FA;
- comando desde Sketch;
- presets minimos;
- pruebas.


Fase B - Clavadores/correas
- diagnostico Frame/Profile;
- comando desde Sketch;
- perfiles;
- pruebas y salida 2D.


Fase C - Cubierta
- diagnostico Roof;
- una y dos aguas;
- alero/pendiente/espesor;
- pruebas y salida 2D.


Fase D - Integracion
- relacion cerchas-clavadores-cubierta;
- actualizacion coherente;
- JSON;
- organizacion del arbol.


Solo despues de estas fases debe desarrollarse el ejemplo automatico, que debe consumir los mismos
comandos/adaptadores ya validados y no implementar geometria especial para la demostracion.


## 14. Relacion con TAREA_ACTUAL.md


No reemplazar el TAREA_ACTUAL vigente mientras permanezca activa la tarea de diagnostico de puertas.
Este documento es una especificacion de diseno separada. Cuando la tarea de puertas se cierre y el
usuario autorice la implementacion, preparar una nueva TAREA_ACTUAL para FA Techo/Cerchas/Clavadores.


## 15. Fuentes investigadas


- FreeCAD BIM / Arch Truss: herramienta nativa desde linea o Sketch; Arch.makeTruss().
- FreeCAD Arch Roof: cubierta desde contorno cerrado; Arch.makeRoof() con angulos, run, espesor y alero.
- FreeCAD Arch Frame: extrusion de perfiles sobre layouts/Sketches; candidato para clavadores/correas.
- FreeCAD Arch Profile: perfiles parametrizados y perfiles personalizados.
- FreeCAD Arch Panel: paneles y geometria corrugada/trapezoidal, candidato para detalle futuro.
- Lineamientos tecnicos de Costa Rica consultados: emplean expresamente el termino "clavadores"
  en detalles de cubierta, consistente con la nomenclatura regional propuesta para FA.




## 16. Inicio de implementacion en Drive


Estado actualizado: IMPLEMENTACION INICIAL AISLADA / PRE-MCP.


Se agregaron sin registrar aun comandos GUI:


- `core/roof_system_core.py`: nucleo independiente, JSON-compatible, para validar y planificar ejes de cerchas, clavadores/correas y contorno de cubierta. El contrato declara `structural_design_status = GEOMETRIC_ONLY` para evitar confundir modelado con dimensionamiento estructural.
- `core/roof_bim_utils.py`: adaptador FreeCAD/BIM preliminar. Extrae lineas y contornos desde Sketches y prepara materializacion mediante `Arch.makeTruss`, `Arch.makeFrame` y `Arch.makeRoof`. Mantiene `dry_run=True` como modo seguro y trazabilidad `FA_SourceSketch`/`FA_SourceGeometryIndex`.
- `tests/test_roof_system_core.py`: pruebas focales del nucleo sin dependencia de FreeCAD.


La primera verificacion local de sintaxis y contrato fue satisfactoria. Se comprobo un plan JSON con dos cerchas, un clavador y una cubierta de cuatro bordes.


Limites deliberados de esta etapa:


- No se modifico `InitGui.py` ni se registraron botones.
- No se modifico `TAREA_ACTUAL.md`, que continua dedicada al diagnostico de puertas.
- El adaptador ya puede construir una seccion C cerrada de pared delgada para `Frame`; su orientacion visual exacta sobre faldones (`Align`, `Rotation`, `BasePoint`) queda pendiente de prueba en FreeCAD real.
- La API preliminar ya traduce las listas por borde de `Roof` y las propiedades principales de `Truss` a partir del codigo fuente oficial. Su comportamiento real en FreeCAD 1.1.3 queda pendiente de prueba MCP antes de estabilizar la API.
- No hay calculo estructural ni seleccion automatica de perfiles.




## 17. Revision de implementacion sin Codex - 2026-08-30


Por decision del usuario se continua el desarrollo en ChatGPT y Google Drive sin Codex mientras no haya creditos disponibles. Las pruebas dependientes del entorno real de FreeCAD/MCP se posponen, pero permanecen obligatorias antes de declarar estable la funcionalidad.


Estado: `IMPLEMENTACION PRELIMINAR / VALIDACION FREECAD PENDIENTE`.


### 17.1 Hallazgos confirmados en el codigo fuente oficial de FreeCAD


Se revisaron `ArchTruss.py`, `ArchAxis.py`, `ArchFrame.py`, `ArchRoof.py` y pruebas BIM oficiales.


- `Truss` exige una Base con una sola arista util. El `Arch Axis` no sustituye esa Base, pero la propiedad nativa `Axis` de `ArchComponent` permite repetir una unica cercha maestra en todos los puntos del eje.
- `Truss.SlantType` admite `Simple` y `Double`. El modo `Double` divide el vano en el punto medio y construye las dos mitades hacia el centro, adecuado como primera aproximacion geometrica para una cercha a dos aguas.
- `TrussAngle` es calculado por el objeto nativo y no debe tratarse como parametro de entrada FA.
- Para `SlantType=Double`, FA puede derivar `HeightEnd` a partir de media luz y pendiente: `HeightEnd = HeightStart + (L/2) * tan(pendiente)`.
- `Arch Axis` conserva valor documental y funcional: ejes visibles, numeracion, burbujas y puntos de repeticion. Para una familia de cerchas iguales, FA usara un solo Axis, una sola Base de una arista y un solo Truss maestro repetido mediante la propiedad nativa `Axis`.
- `Arch Frame` toma un layout como Base y extruye un perfil por sus aristas. Por tanto el Sketch de clavadores puede ser Base directa de un Frame compacto cuando sus lineas ya representan la geometria espacial correcta.
- `Arch Roof` trabaja con listas por borde (`Angles`, `Runs`, `Thickness`, `Overhang`, `IdRel`), no con un unico valor escalar de pendiente o alero.
- En `Arch Roof`, un borde con angulo 90 grados actua como borde de hastial. Para una cubierta rectangular a dos aguas, FA asigna pendiente a los dos bordes de alero y 90 grados a los dos bordes de hastial.
- El Sketch cerrado de cubierta puede usarse directamente como Base de `Arch.makeRoof`, sin copiar el contorno a un objeto auxiliar.


### 17.2 Contrato del nucleo 0.3.0


`core/roof_system_core.py` pasa a schema `2` y mantiene dos estados explicitos:


- `structural_design_status = GEOMETRIC_ONLY`;
- `validation_status = PENDING_FREECAD_MCP`.


El nucleo ahora:


- valida que los ejes de cerchas formen una sola familia paralela y aproximadamente coplanar;
- soporta plan geometrico de cercha `Simple` y `Double`;
- deriva altura de cumbrera desde pendiente y vano cuando corresponde;
- representa clavadores como un Frame con multiples aristas y un perfil compartido;
- prepara un perfil C geometrico parametrico para modelado, no para calculo estructural;
- reconoce inicialmente cubiertas rectangulares a dos aguas;
- detecta automaticamente los bordes de hastial cuando el rectangulo no es cuadrado;
- rechaza un cuadrado ambiguo si no se indican expresamente los bordes de hastial;
- genera las listas nativas de Roof por borde y datos documentales de cumbrera.


### 17.3 Adaptador FreeCAD 0.3.0-preMCP


`core/roof_bim_utils.py` mantiene `dry_run=True` por defecto y queda preparado para:


- crear una familia `Arch Axis` visible para los ejes de cerchas;
- crear una sola Base auxiliar de una arista, materializar un unico `Arch.makeTruss` y asignarle el `Arch Axis` para repetirlo nativamente;
- usar directamente el Sketch de clavadores como Base de un unico `Arch Frame`;
- crear una seccion C cerrada de pared delgada como perfil de Frame;
- usar directamente el Sketch cerrado de cubierta como Base de `Arch.makeRoof`;
- eliminar/reemplazar solo objetos propios de `FA_RoofSystem`, conservando fuentes y evitando borrar objetos manuales ambiguos.


### 17.4 Pruebas disponibles sin FreeCAD


`tests/test_roof_system_core.py` contiene 23 pruebas focales y todas pasan (`23/23`). Cubren paralelismo de cerchas, calculo geometrico de altura central, rechazo de ejes no coplanares, contrato de clavadores, cubierta rectangular a dos aguas, ambiguedad de cubierta cuadrada, proyeccion 2D de clavadores sobre ambos faldones, cubiertas rectangulares rotadas y serializacion JSON completa.


Estas pruebas no sustituyen FreeCAD real. Quedan pendientes: geometria visual de Truss, orientacion de perfil C en Frame, recompute al editar Sketches, contencion en Level, Undo/Redo, guardar/reabrir, idempotencia real y salida documental 2D.


### 17.5 Modos preliminares de clavadores


El nucleo 0.3.0 implementa dos modos sin fijar aun cual sera la interfaz definitiva:


1. `source_3d`: el Sketch ya contiene los paths espaciales correctos y se usa directamente como Base de Frame;
2. `project_plan_to_gable`: el usuario dibuja lineas 2D en planta paralelas a la cumbrera y FA calcula su cota sobre cada faldon. El adaptador genera un layout 3D auxiliar oculto y conserva el Sketch 2D como fuente editable.


La proyeccion funciona tambien con huellas rectangulares rotadas y rechaza lineas fuera de la franja entre aleros o no paralelas a la cumbrera. Falta comprobar en FreeCAD real la orientacion del perfil C y decidir cual de los dos modos sera el predeterminado de la interfaz.


### 17.6 Comandos preliminares no registrados


Se agregaron a `commands/`, sin importarlos desde `InitGui.py`:


- `roof_command_common.py`: seleccion, transacciones y resolucion de Level;
- `cmd_create_trusses_bim.py`: `FA_CreateTrussesFromSketch`;
- `cmd_create_purlins_bim.py`: `FA_CreatePurlinsFromSketch`;
- `cmd_create_roof_bim.py`: `FA_CreateRoofFromSketch`.


Los tres planifican/validan antes de abrir transaccion, reemplazan solamente objetos generados por `FA_RoofSystem` desde la misma fuente y conservan el registro `register()` dormido para la fase posterior a MCP. No se modifico `InitGui.py`, ni version/build del Workbench, ni `TAREA_ACTUAL.md`.


### 17.7 Correccion de familia de cerchas - una Base + un Truss + Axis


Revision 2026-08-30 posterior a la comprobacion manual del arbol de FreeCAD.


Se confirma como modelo objetivo para una familia de cerchas geometricamente iguales:


- una sola Base lineal requerida por `Arch Truss`;
- un solo objeto `Arch Truss` maestro;
- un solo `Arch Axis` con todas las posiciones;
- la propiedad nativa `Truss.Axis` gobierna la repeticion geometrica mediante `ArchComponent.spread()`;
- BIM oculta la Base al incorporarla al componente, por lo que FA no debe duplicar esa logica de visibilidad;
- no se crean cinco Bases ni cinco objetos Truss para cinco cerchas iguales.


El nucleo usa `representation = ONE_TRUSS_AXIS_SPREAD` y conserva las lineas fuente como posiciones logicas. Antes de aceptar esta materializacion valida que todas sean copias por traslacion de una misma cercha: misma luz, mismo nivel, misma orientacion y sin escalonamiento longitudinal. Si no cumplen ese contrato, se rechaza la familia en lugar de deformarla silenciosamente.


El adaptador `roof_bim_utils.py` materializa una unica Base local y comprueba contra los puntos reales devueltos por `Axis.Proxy.getPoints()` que la repeticion reconstruya todas las posiciones nativas previstas. El arbol generado debe tender conceptualmente a:


```text
Cercha BIM 01
└── Base cercha 01


Ejes
```


Las multiples cerchas visibles forman parte de la Shape compuesta del unico Truss repetido por Axis. Por tanto no son objetos BIM individuales con propiedades o identificadores independientes. Esta decision es deliberada para el caso de familias identicas y mantiene el arbol minimo validado por el usuario.






## 18. Integracion de produccion en Facil Arquitectura 0.14.9


Fecha: 2026-08-30 16:55 America/Costa_Rica.


Se adopta como ruta publicada el comando unico `FA_CreateRoofSystemBIM` / **FA Techo BIM**.
Los comandos parciales de cerchas, clavadores y cubierta permanecen como auxiliares internos y no se registran en `InitGui.py` mientras no exista una razon funcional para exponer dos flujos paralelos.


### 18.1 Contrato de entrada


El usuario selecciona exactamente tres Sketches, en cualquier orden:


1. posiciones/ejes logicos de cerchas;
2. lineas de clavadores en planta;
3. contorno cerrado rectangular de cubierta.


El comando identifica primero el Sketch de cubierta y prueba las dos permutaciones restantes mediante el plan completo. Si la identificacion no es inequivoca, no modifica el documento.


### 18.2 Arbol de produccion


La salida principal queda dentro de un unico grupo visual `Techo BIM` contenido directamente en el Level objetivo:


```text
Techo BIM
├── Ejes
├── Cerchas BIM
│   └── Base cercha
├── Clavadores BIM - faldon izquierdo
│   ├── Base clavadores - faldon izquierdo
│   └── Perfil C clavadores - faldon izquierdo
├── Clavadores BIM - faldon derecho
│   ├── Base clavadores - faldon derecho
│   └── Perfil C clavadores - faldon derecho
└── Cubierta BIM
    └── Base cubierta
```


Reglas de limpieza:


- `Base cercha` es una `Draft Line` de dos puntos, no un `Part::Feature` artificial;
- se crea una sola Base, un solo `Arch Truss` y un solo `Arch Axis`;
- la cercha se repite mediante la propiedad nativa `Truss.Axis`;
- las Bases y perfiles auxiliares no se agregan tambien al grupo `Techo BIM`; quedan reclamados por sus relaciones nativas `Base`/`Profile`;
- cada faldon usa su propio perfil para evitar un perfil compartido con varios padres visuales;
- la superficie maestra es un concepto de calculo y validacion del nucleo, no un objeto persistente del arbol normal;
- los Sketches fuente permanecen donde estaban y no se copian ni reagrupan;
- `Base cubierta` solo se materializa cuando el apilado cercha-clavador-cubierta exige desplazar la Base de `Arch Roof`.


### 18.3 Estado de validacion


La geometria cercha-clavador-cubierta fue validada manualmente en FreeCAD 1.1.3 mediante la macro v016 previa a esta integracion. Las pruebas independientes del nucleo pasan 20/20 en el entorno de GPT.


Pendiente antes de considerar 0.14.9 cerrada: smoke test del comando ya registrado en el Workbench real, comprobando seleccion de tres Sketches, Undo/Redo, repeticion sin duplicados, guardado/reapertura y arbol final.




## 19. Prototipo sin Sketches: Rectangle + Arch Axis


Fecha: 2026-08-30 18:45 America/Costa_Rica.


Se incorpora en 0.14.10 build `2026.08.30.4` un boton experimental separado: `FA_RoofAxisPrototype` / **FA Prototipo techo por ejes**. No reemplaza `FA Techo BIM`. Siempre crea un documento nuevo para evitar modificar modelos existentes durante la validacion.


Hallazgo nativo decisivo: aunque `Arch Frame` hereda la propiedad `Axis` de `ArchComponent`, `ArchFrame._Frame.execute()` construye y asigna directamente `obj.Shape` y no pasa por `ArchComponent.applyShape()/spread()`. Por tanto `Frame.Axis` no es una ruta funcional para repetir clavadores. La solucion reutiliza otra capacidad nativa mas directa: un `Arch Axis` es `Part::FeaturePython` con aristas validas y puede ser directamente `Frame.Base`; `ArchFrame` extruye el perfil sobre cada arista de esa Base.


Modelo del prototipo:


```text
Techo BIM - prototipo por ejes
├── Huella techo - Draft Rectangle
├── Ejes de cerchas
├── Cerchas BIM
│   └── Base cercha [Draft Line]
├── Clavadores BIM - faldon izquierdo
│   ├── Ejes clavadores - faldon izquierdo [Frame.Base, visible]
│   └── Perfil C clavadores - faldon izquierdo
├── Clavadores BIM - faldon derecho
│   ├── Ejes clavadores - faldon derecho [Frame.Base, visible]
│   └── Perfil C clavadores - faldon derecho
└── Cubierta BIM
    └── Base cubierta
```


El nucleo nuevo `axis_distribution_core.py` calcula una distribucion uniforme con separacion maxima y retiros extremos. Para un faldon de 4 m de carrera horizontal a 20 grados, longitud inclinada 4256.711 mm, separacion maxima 800 mm y retiros de 200/200 mm, genera 6 ejes y separacion real 771.342 mm. Las distancias se almacenan directamente en `Arch Axis.Distances`, por lo que el eje queda como fuente parametrica editable y no requiere un Sketch duplicado.


Pendiente: smoke test en FreeCAD 1.1.3 del boton experimental y revision del arbol, orientacion de perfiles, contacto cercha-clavador-cubierta y comportamiento al editar `Distances`/`Placement` de los ejes.




## Prototipo por ejes: correccion Structure/Beam (build 2026.08.30.5)


### Hallazgo de la prueba anterior


El prototipo con `Arch Axis` usado como `Arch Frame.Base` genero ejes validos pero ambos `Arch Frame` quedaron sin Shape valido. El reparto parametrico si fue correcto: para el ejemplo de 8 x 12 m y pendiente de 20 grados se obtuvieron 6 ejes por faldon, separacion real 771.342 mm, maximo 800 mm y retiros 200/200 mm.


### Patron nativo adoptado para la siguiente prueba


Se adopta el mismo mecanismo de repeticion que ya utilizan componentes derivados de `ArchComponent` cuando terminan su calculo mediante `applyShape()`: un elemento maestro mas la propiedad `Axis`. Para clavadores se prueba `Arch Structure` con `IfcType=Beam`, no `Arch Frame`.


Estructura conceptual por faldon:


```text
Ejes clavadores [Arch Axis]
        |
        +--> Clavadores BIM [1 Arch Structure/Beam maestro]
                  `-- Seccion rectangular clavador [Draft Rectangle, oculta]
```


El `Structure.Placement` del maestro permanece identidad; los puntos del Axis realizan la colocacion de las copias. El Axis izquierdo recorre el faldon desde el alero izquierdo y sus vigas se extruyen en +Y. El Axis derecho recorre desde el alero derecho y sus vigas se extruyen en -Y.


### Regla de simplificacion geometrica


Cuando una referencia pueda expresarse correctamente con geometria nativa simple, preferir:


1. `Draft Line` para una linea base o direccion.
2. `Draft Rectangle` para huellas, contornos rectangulares y secciones rectangulares.
3. `Arch Axis` para familias repetidas y documentacion de ejes.
4. Crear un objeto BIM adicional solo cuando aporte comportamiento BIM real.


En este prototipo la huella, la seccion de clavador y la Base rectangular de cubierta usan `Draft Rectangle`; la Base de cercha usa `Draft Line`.


La solucion estable `FA Techo BIM` no se sustituye hasta validar este patron en FreeCAD 1.1.3 real.




## 20. FA Techo desde rectangulo - flujo funcional 0.14.11


### 20.1 Entrada


El flujo funcional acepta exactamente un `Draft Rectangle` horizontal seleccionado. La fuente no se mueve, no se oculta, no se reparenta y no se convierte a Sketch. Se conserva como referencia documental y editable del usuario. La orientacion alrededor de Z se respeta.


### 20.2 Cumbrera y faldones


La direccion de cumbrera puede ser automatica sobre el lado largo o forzada paralela a `Length`/`Height`. El sistema deriva el vano transversal, la longitud de cumbrera y ambos planos inclinados a partir del Rectangle y la pendiente.


### 20.3 Ejes de cerchas y clavadores


Las cerchas usan una `Draft Line` maestra, un `Arch Truss` y un `Arch Axis`. Los clavadores usan una seccion `Draft Rectangle`, un `Arch Structure` con `IfcType=Beam` y un `Arch Axis` inclinado por faldon. No se usan Sketches ni `Arch Frame`.


Para clavadores, el modo predeterminado `fixed` conserva la separacion nominal ingresada en los intervalos interiores. La diferencia geometrica se absorbe simetricamente en el primer y ultimo intervalo entre ejes; los retiros explicitos desde alero y cumbrera se mantienen. Ningun intervalo supera la separacion solicitada.


El modo `rounded` calcula primero la cantidad minima de intervalos que cumple el maximo, obtiene la separacion ideal y selecciona un nominal practico redondeado al paso de 50 o 100 mm, sin superar el maximo. Los extremos siguen pudiendo ser excepciones.


### 20.4 Huella y Base cubierta


Se mantienen separadas. La huella es fuente del usuario en cota de apoyo. `Base cubierta` es un `Draft Rectangle` generado, interno y oculto, con la misma planta/orientacion pero desplazado verticalmente `altura_talon_cercha + altura_clavador / cos(pendiente)`. La Base inferior de la cercha permanece exactamente en la cota de apoyo; la altura de talon eleva el cordon superior, los clavadores y la cubierta. Esta separacion mantiene la cubierta apoyada sobre los clavadores sin mover ni convertir la huella en hijo nativo de `Arch Roof`.


### 20.5 Muros BIM


Antes de crear, se buscan de forma solo-lectura muros BIM cuya envolvente XY intersecta la huella. Se calcula coronacion mediana y dispersion. Si las coronaciones son coherentes, el usuario puede tomar esa cota como apoyo; si son ambiguas se mantiene la Z del Rectangle. La deteccion tambien ayuda a resolver el `Level` cuando los muros pertenecen claramente a uno.


Una fase posterior podra generar la propia huella desde muros exteriores, pero no se automatiza mientras la clasificacion exterior/interior y los cambios de altura puedan ser ambiguos.


### 20.6 Repeticion y trazabilidad


Los objetos generados se identifican por `FA_Generator=FA_RoofFromRectangle` y `FA_SourceName=<Name del Rectangle>`. `FA_SourceName` es texto, no `App::Link`, para evitar ab


### 20.7 Cota de apoyo de cerchas - correccion 2026-08-31


En `Arch Truss`, la linea Base define el plano inferior desde el que se construye el cordon inferior. `HeightStart` no es un desplazamiento negativo de la cercha: define la elevacion del cordon superior en el alero respecto de esa Base.


Regla vigente para `FA Techo desde rectangulo`:


- `Base cercha Z = cota de apoyo` obtenida del Rectangle o de la coronacion coherente de muros BIM;
- `HeightStart = altura de talon`, editable y persistente como preferencia;
- los ejes de clavadores se elevan exactamente `HeightStart` para apoyar sobre la cara superior de la cercha;
- `Base cubierta` se eleva `HeightStart + altura_clavador / cos(pendiente)` para conservar el contacto sobre los clavadores;
- antes de confirmar la transaccion se valida que `Truss.Shape.BoundBox.ZMin` coincida con la cota de apoyo; si no coincide se hace rollback.


El build `2026.08.31.1` conserva el patron `Draft Line + Arch Truss + Arch Axis` para cerchas y `Draft Rectangle + Arch Structure/Beam + Arch Axis` para clavadores. La prueba real debe confirmar simultaneamente `delta apoyo cerchas = 0`, `clavador-cercha = 0` y `clavador-cubierta = 0`.
anicos de dependencias hacia la fuente. Repetir el comando sobre la misma huella reemplaza solo los objetos de este generador dentro de una transaccion.