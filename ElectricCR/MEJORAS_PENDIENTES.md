# ElectricCR - Mejoras pendientes y observaciones de trabajo

**Proposito:** Mantener una memoria viva de mejoras, observaciones funcionales y hallazgos que todavia no constituyen cambios aceptados. Este archivo sirve como puente para Marco, GPT y Codex.

**Version:** 2026-08-14, America/Costa_Rica.

**FreeCAD objetivo:** 1.1.3

## Reglas de uso

- Registrar aqui ideas, defectos, dependencias rotas y mejoras detectadas durante pruebas reales.
- No considerar una nota de este archivo como cambio aceptado ni como autorizacion para eliminar codigo.
- Antes de implementar una mejora, revisar codigo actual, respaldos, historial y documentacion relacionada.
- Cuando una mejora sea implementada y validada, trasladar su estado a `RESULTADO_CODEX.md`, `REVISION_MACROS.md` y, cuando corresponda, `HISTORIAL_CAMBIOS.md`.
- Evitar duplicar herramientas: preferir motores generales con adaptadores o comandos pequenos.

---

## 1. Areas - dependencia faltante de AnalizarAreasDesdeMuroBIM

### Estado tecnico 2026-08-11

RESUELTA EN EL REPOSITORIO / VALIDACION FUNCIONAL DE MARCO PENDIENTE.

- La macro visible carga ahora
  `FacilArquitecturaWB/core/rectangular_area_analysis.py` mediante una ruta
  relativa al repositorio.
- La copia historica y su motor se localizaron en `Scripts Varios`, se leyeron
  completos y permanecen sin modificar.
- Se conservaron `FA_RectangularAreas`, `Spreadsheet_Analisis_Areas`, los
  cuatro modos de inferencia, rotulos, colores y propiedades ElectricCR.
- La prueba temporal aprobo seleccion de dos muros, reejecucion, Undo/Redo,
  guardar/reabrir y consumidores de cielos, tomacorrientes e iluminacion.
- FreeCAD MCP 1.1.3 ejecuto la `.FCMacro` visible desde el repositorio.

### Hallazgo

`Areas/AnalizarAreasRectangularesDesdeMurosBIM.FCMacro` es un lanzador y tiene `# Transaction: self`.

El mensaje:

`ElectricCR: transaccion externa omitida (macro autogestiona transaccion)`

NO es un error. El fallo real ocurre porque intenta ejecutar:

`AnalizarAreasDesdeMuroBIM.FCMacro`

usando una ruta relativa que termina buscando el archivo directamente bajo el directorio general de macros.

### Ubicacion real encontrada en la computadora de Marco

`C:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Scripts Varios\FacilArquitectura_BIM\AnalizarAreasDesdeMuroBIM.FCMacro`

### Importancia funcional

La documentacion de FacilArquitectura indica que esta macro fue validada y genera, entre otros:

- `FA_RectangularAreas`
- `Spreadsheet_Analisis_Areas`
- propiedades de area y recinto utilizadas por ElectricCR.

### Pendiente

- No borrar la copia localizada en `Scripts Varios` hasta verificar la migracion.
- Marco debe validar el resultado con muros y rotulos de un proyecto real.
- No retirar la copia historica hasta que esa validacion sea aceptada.

---

## 2. Espacio BIM como fuente espacial comun de ElectricCR

### Decision aceptada 2026-08-14

Conservar los algoritmos actuales de deteccion y calculo de recintos, pero usar
Espacio BIM como objeto base cuando funcione correctamente.

El objetivo no es descartar el trabajo existente. Los algoritmos actuales deben
poder seguir generando el contorno, nombre y medidas del recinto, y utilizar ese
resultado para crear o actualizar un `Arch Space` cuando sea seguro.

Informacion espacial comun deseable:

- nombre normalizado del recinto;
- tipo o descripcion funcional;
- geometria;
- area en m2;
- perimetro;
- largo y ancho cuando sean aplicables;
- altura y volumen;
- nivel o piso;
- identificacion estable para que los calculos lo referencien.

Iluminacion, tomacorrientes, deteccion de incendio, HVAC y otros sistemas deben
usar el mismo espacio como fuente. Cada calculo puede indicar si el recinto
aplica y conservar un area ajustada. No se requiere otra geometria si solamente
cambia el uso del dato o el valor efectivo del calculo.

Los objetos Area actuales se mantienen como compatibilidad y fallback para
contornos o flujos que Espacio BIM no resuelva correctamente.

### Herramientas y logica que deben preservarse

- `Areas/AreaPorClick.FCMacro` mientras siga siendo parte del flujo activo.
- `Areas/RectFromLines.FCMacro`.
- `Areas/RectFromSelection.FCMacro`.
- El motor reutilizable
  `FacilArquitecturaWB/core/rectangular_area_analysis.py`.
- Algoritmos poligonales y consumidores actuales de nombre, area y recinto que
  se confirmen al revisar el codigo.

El lanzador historico
`AnalizarAreasRectangularesDesdeMurosBIM.FCMacro` puede permanecer archivado;
esto no autoriza a eliminar su motor reusable.

### Pendientes de investigacion e implementacion

1. Inventariar que tipos de objetos Area producen actualmente las herramientas
   activas y que propiedades consumen las tablas.
2. Crear una prueba controlada que genere un Espacio BIM a partir del resultado
   de los algoritmos existentes, sin modificar proyectos reales.
3. Comparar Area, nombre, perimetro y geometria entre el objeto actual y el
   Espacio BIM.
4. Probar recintos rectangulares, poligonales, no convexos, abiertos y con
   cambios posteriores en los muros o limites.
5. Verificar Undo/Redo, guardar/reabrir, etiquetas y visibilidad en planta.
6. Revisar la actualizacion de `DatosRecintos`, hojas de iluminacion y demas
   tablas sin cambiar inicialmente sus contratos.
7. Definir una relacion estable entre Espacio BIM y cada calculo, incluyendo:
   `Usar`, `AreaBase`, `AreaAjustada`, sistema y motivo del ajuste.
8. Preparar un adaptador de compatibilidad para que los consumidores puedan leer
   primero Espacio BIM y usar Area legacy como fallback.
9. Probar primero en La Cruz Version 2.1 y despues en un proyecto completo como
   Puriscal.
10. No migrar automaticamente documentos existentes ni eliminar Areas hasta que
    Marco valide funcionalmente el nuevo flujo.
11. Preparar antes de programar una comparacion documentada entre Area actual y
    Espacio BIM: creacion, limites, propiedades, actualizacion, tablas,
    limitaciones y capacidades que deben conservarse de cada solucion.

Estado actual: DECISION DEFINIDA / IMPLEMENTACION Y VALIDACION PENDIENTES.

La tabla real de La Cruz muestra que esta estructura ya empieza a existir y
puede servir como caso de prueba.

### Observacion de nombres

Debe normalizarse cuando FreeCAD agrega sufijos numericos para nombres unicos. Ejemplo:

`Archivo en 2 Niveles001` -> nombre funcional esperado `Archivo en 2 Niveles`.

---

## 3. Iluminacion - calculo automatico de cantidad y cuadricula

### Macro identificada

`Iluminacion/Actualizar_Iluminacion_Completa.FCMacro`

Esta macro:

- calcula la cantidad minima requerida de luminarias segun area, descripcion y flujo luminoso;
- calcula o conserva `Rows` y `Columns`;
- guarda propiedades como:
  - `Rows`
  - `Columns`
  - `LightingRequiredCount`
  - `LightingQuantity`
  - `LightingLayoutManual`
  - `LightingRecalculateLayout`
  - `LightingLastAutoRows`
  - `LightingLastAutoColumns`;
- actualiza `DatosRecintos`;
- actualiza la tabla legacy de iluminacion;
- permite conservar una distribucion manual si el usuario modifica filas y columnas.

### Distribucion geometrica

`Iluminacion/ColocarLuminarias_Link.FCMacro` usa `Rows` y `Columns` de cada rectangulo para crear una cuadricula y colocar las luminarias por celda.

Si existe alineamiento de cielo modular, intenta usarlo; si no, distribuye proporcionalmente cada luminaria en el centro de su celda.

### Relacion funcional deseada

El flujo deberia quedar claramente definido como:

1. Area/recinto.
2. Calculo de cantidad requerida.
3. Determinacion de filas y columnas.
4. Creacion de la cuadricula logica de celdas.
5. Colocacion de luminarias.
6. Posibilidad de ajuste manual de filas/columnas sin que una actualizacion posterior lo destruya.

---

## 4. Biblioteca interna de objetos maestros debe permanecer oculta

### Caso observado - La Cruz Version 2.1

Arbol actual:

```text
electrico
|-- _lib                                vis=1
|   `-- Luminarias_Link_Masters         vis=1
|       `-- Master Link Luminaria...    vis=1
`-- Luminaria_Link
    `-- luminarias colocadas            vis=1
```

### Regla deseada

Toda biblioteca interna de objetos maestros de ElectricCR debe permanecer oculta por defecto.

Aplicar a:

- `_lib`;
- `Luminarias_Link_Masters`;
- maestros de luminarias;
- maestros de tomacorrientes;
- maestros de apagadores;
- detectores;
- camaras;
- sensores;
- cualquier otro objeto maestro utilizado mediante `App::Link`.

Los objetos `App::Link` realmente colocados en el proyecto SI deben permanecer visibles.

### Implementacion futura recomendada

Crear o reutilizar un helper comun de biblioteca que garantice:

- grupo biblioteca oculto;
- subgrupos de masters ocultos;
- objetos master ocultos;
- masters no seleccionables cuando corresponda;
- enlaces colocados visibles y seleccionables.

No corregir esta regla macro por macro si puede resolverse de forma centralizada.

---

## 5. Conectar - consolidacion de herramientas repetidas

### Principio confirmado

TP y TCOM son tableros. El nombre del tablero no debe definir un algoritmo distinto.

La arquitectura futura debe trabajar con conceptos generales como:

- origen;
- circuito;
- tablero destino;
- puertos;
- cara de conexion;
- ruta;
- lineas guia opcionales.

### Lineas guia

Las lineas guia son opcionales.

- Si existe una guia seleccionada o claramente aplicable: usar ruteo guiado.
- Si no existe o no se selecciona: continuar con ruteo automatico directo.
- La ausencia de guia nunca debe impedir crear el alimentador.

### Familias a consolidar

Entre otras:

- `Conectar_Alimentadores_a_Tablero_Auto.FCMacro`
- `Conectar_Circuitos_TP_a_Cara_Superior_Tablero.FCMacro`
- `Conectar_Circuitos_TCOM_a_Cara_Superior_Tablero.FCMacro`
- `Conectar_Octogonales_Ortogonal_por_Circuito_TP.FCMacro`
- `Conectar_Octogonales_Ortogonal_por_Circuito_TCOM.FCMacro`
- `Conectar_Tableros_Cara_Superior.FCMacro`
- `Conectar_Desconectores_HVAC_a_TP.FCMacro`
- `Preparar_Red_TCOM_Completa.FCMacro`

Objetivo de interfaz aproximado:

- `Conectar Alimentadores`
- `Conectar Circuito / Backbone`
- `Ajustar Ruta`

Las variantes reemplazadas deben respaldarse antes de retirarlas de la barra y no deben borrarse fisicamente sin aprobacion expresa.

---

## 6. Casos reales para pruebas futuras

### La Cruz Version 2.1

Usar como caso real para validar:

- nombres de recintos;
- clasificacion de descripcion;
- area/largo/ancho;
- calculo de luminarias;
- filas y columnas;
- colocacion por celdas;
- bibliotecas ocultas;
- comportamiento de `App::Link`.

### Datos observados

La hoja `DatosRecintos` contiene columnas como:

- Recinto
- Area (m^2)
- Largo (m)
- Ancho (m)
- Altura (m)
- Filas
- Columnas
- Descripcion
- Cantidad Luminarias
- Tipo Luminaria
- Lumens Unitarios
- Potencia Unitaria (W)

Esta estructura es una buena base para futuras reglas por tipo de recinto.

---

## 7. Notas que requieren revision antes de automatizar

Algunos recintos muestran clasificaciones discutibles o heredadas. Ejemplos detectados:

- `Sala de Lactancia` -> `Sala de Reuniones`
- `Cuarto Electrico y Servidor` -> `Taller`
- `Comedor` -> `Cocina`

No convertir estas asociaciones en reglas permanentes sin revision funcional.

---

## 8. Tableros - herramienta esencial y defecto de orientacion al insertar en muro

### Herramienta

`ElectricCR/Insertar_Tablero.FCMacro`

Se considera una herramienta ESENCIAL de ElectricCR. La macro es una interfaz para el backend:

`ElectricCR/electriccr/features/tablero_electrico.py`

Permite insertar como `App::Link`:

- Tablero;
- Desconector;
- Interruptor.

Mantener esta herramienta como candidata prioritaria a comando estable del Workbench.

### Defecto observado - La Cruz Version 2.1

Al seleccionar una pared/cara y pedir insertar un tablero, el tablero se esta colocando torcido respecto al muro.

### Causa probable a verificar

En `_face_context_from_face()` el backend calcula dos referencias:

- vector desde el centro del objeto propietario hacia el centro de la cara (`outward`);
- normal geometrica real de la cara (`normal`).

Actualmente se prioriza `outward` cuando existe y solo se usa la normal si ese vector no es valido.

En un muro largo, irregular o con centro geometrico desplazado, el vector centro-del-muro -> centro-de-cara puede tener componente tangencial y no ser perpendicular a la cara. Esto puede explicar una rotacion ligeramente torcida.

Esta es una HIPOTESIS TECNICA basada en el codigo actual y debe comprobarse en FreeCAD antes de corregir.

### Comportamiento deseado

Cuando la insercion se realiza sobre una cara vertical plana de un muro:

- la orientacion debe derivarse principalmente de la normal geometrica real de la cara;
- el tablero debe quedar paralelo al plano del muro;
- el frente debe quedar hacia el lado correcto;
- la vista/camara o el centro global del muro solo deberian ayudar a resolver el signo interior/exterior, no crear una direccion oblicua;
- debe funcionar en muros horizontales, verticales, diagonales y segmentos de muros complejos.

Crear prueba especifica con muro diagonal y con muro largo/irregular.

---

## 9. Asignar Tableros y Circuitos - herramienta esencial sin icono

### Macro identificada

`Configuracion del proyecto/Asignar_Tableros_y_Circuitos.FCMacro`

Menu actual:

`Asignar tableros y circuitos (pestanas)`

La macro no declara actualmente una linea `# Icon:` en su encabezado.

### Importancia funcional

Se considera otra herramienta ESENCIAL de ElectricCR porque organiza la asignacion electrica y produce las hojas:

- `Asignacion_Red`
- `Red_Origenes`

Su interfaz trabaja con:

- pestanas por tablero para asignar circuitos y componentes aguas abajo;
- pestana de origen para indicar de donde viene cada tablero/desconector/interruptor.

Esta informacion es fundamental para separar correctamente:

`asignacion electrica -> motor de conexiones -> geometria`

Por tanto no debe clasificarse como utilidad secundaria solamente por estar en `Configuracion del proyecto`.

### Pendientes

- marcar como NUCLEO/ESENCIAL en la revision de macros cuando corresponda;
- crear/asignar un icono coherente con ElectricCR;
- revisar si su logica debe convertirse en servicio estable de asignaciones, conservando la interfaz por pestanas;
- evitar que los motores geometricos tengan que inferir relaciones que ya estan definidas en `Asignacion_Red` y `Red_Origenes`.

---

## 10. Capturar Arbol de Grupos - herramienta de diagnostico

### Macro identificada

`Configuracion del proyecto/Capturar_Arbol_Grupos_Documento.FCMacro`

Los mensajes `[ARBOL_GRUPOS] Exportado:` NO indican un error ni una modificacion del modelo.

La macro toma una instantanea del arbol de grupos del documento activo y genera tres representaciones:

- `.txt` legible para personas;
- `.md` para documentacion/GPT/Codex;
- `.json` para procesamiento automatico.

Los archivos se guardan actualmente en:

`Configuracion del proyecto/_reportes_arbol/`

### Alcance

- Si hay grupos seleccionados, exporta esos grupos como raiz.
- Si no hay grupos seleccionados, exporta los grupos raiz del documento.

El mensaje:

`Resumen: scope=documento | raiz=6 | clipboard=SI`

significa:

- `scope=documento`: se capturo el arbol del documento completo porque no se uso una seleccion de grupos como raiz;
- `raiz=6`: encontro seis grupos raiz;
- `clipboard=SI`: tambien copio el reporte textual al portapapeles.

### Clasificacion y ubicacion propuesta

Herramienta de SOPORTE / DIAGNOSTICO para GPT, Codex y desarrollo. Debe moverse, no eliminarse, desde `Configuracion del proyecto` hacia el directorio `Programacion`, junto con su subdirectorio `_reportes_arbol`. No necesita ocupar una posicion prioritaria en las barras normales de produccion.

---

## 11. Ruta Critica solo seleccionados - usar subelementos seleccionados y radio EMT configurable

### Macro identificada

`Conectar/RutaCritica_Seleccionados.FCMacro`

Se considera una herramienta util e interesante que conviene conservar y mejorar.

### Defecto actual

La macro usa `Selection.getSelection()` y reduce la seleccion a objetos. Luego calcula origen y destinos con `base.get_connection_point(obj)`, que usa principalmente `Placement.Base` mas altura relativa. Por ello, seleccionar una cara, vertice, arista o punto concreto no cambia realmente el punto geometrico desde donde nace o termina la ruta.

Tambien aplica actualmente un `FilletRadius` fijo de `500.0 mm` a todas las rutas.

### Comportamiento deseado

La herramienta debe trabajar con puntos de seleccion reales, conservando el orden de seleccion:

1. Primer elemento/subelemento seleccionado = origen.
2. Siguientes elementos/subelementos seleccionados = destinos.
3. Si se selecciona un vertice, usar el vertice exacto.
4. Si se selecciona una cara, usar el centro geometrico/centro de masa de la cara.
5. Si se selecciona una arista o un punto sobre geometria, usar un criterio explicito y predecible; preferir el punto 3D realmente seleccionado cuando exista.
6. Si solo se selecciona un objeto sin subelemento, conservar como fallback su punto de conexion actual.
7. No deduplicar solamente por nombre de objeto: dos subelementos distintos del mismo objeto pueden representar dos puntos diferentes.

La ruta ortogonal puede seguir usando la logica actual de altura Z y agrupacion en `Conexiones`.

### Reutilizacion dentro del repositorio

`Conectar/Ajustar_Alimentador_o_Ramal_Manual.FCMacro` ya implementa conceptos equivalentes para resolver:

- vertice exacto;
- centro de arista circular;
- punto medio de linea;
- centro de masa de cara;
- punto 3D seleccionado;
- verificacion de capacidad de radio de curva.

Antes de duplicar esta logica, estudiar si conviene extraer un helper comun para puntos de seleccion y/o capacidad de fillet.

### Radio de curvatura

El usuario debe poder modificar el radio de redondeo antes de generar las rutas.

Requisitos:

- radio editable en mm;
- permitir `0` para ruta sin redondeo;
- guardar un valor predeterminado razonable para EMT de 50 mm (2 pulgadas nominales);
- si un tramo es demasiado corto para el radio solicitado, no debe fallar toda la ruta: reducir a un radio geometricamente posible o informar claramente el radio efectivo usado;
- registrar en consola radio solicitado y radio efectivo.

Como referencia inicial de fabricante, herramientas Greenlee para EMT de 2 pulgadas usan radios al eje cercanos a 229-233 mm, por lo que un valor aproximado de 230-235 mm es candidato razonable a predeterminado. La decision final debe validarse funcionalmente antes de fijarla como criterio general de ElectricCR.

### Interfaz sugerida

En lugar de preguntar solo `Altura Z`, usar un dialogo pequeno con al menos:

- `Altura ruta Z (mm)`;
- `Radio curva (mm)`;

con el radio precargado pero editable.

### Pruebas necesarias

- objeto -> objeto;
- vertice -> vertice;
- cara -> cara usando centro de cada cara;
- cara -> objeto;
- punto seleccionado -> cara;
- varios destinos en una sola ejecucion;
- dos subelementos distintos del mismo objeto;
- radio 0;
- radio predeterminado EMT 50 mm;
- radio mayor que el permitido por segmentos cortos;
- Undo/Redo;
- comprobar que las rutas siguen agrupandose correctamente en `Conexiones`.

---

## 12. Estado

Este documento contiene PENDIENTES y observaciones.

No implica que las mejoras ya esten implementadas, probadas o aceptadas.

Cuando una observacion pase a desarrollo, Codex debe registrar el resultado tecnico y Marco debe validar el comportamiento real en FreeCAD antes de integrarla definitivamente.

---

## Reorganizacion de macros e iconos - 2026-08-12

La tarea de depuracion de interfaz fue programada y ejecutada parcialmente en
esta sesion. Falta recargar ElectricCR en FreeCAD y confirmar visualmente que
las barras no conserven comandos cacheados de las rutas antiguas.

Pendientes de validacion:

- confirmar que `Ordenar_Tomas_XY` y `Ordenar_Tomas_XY_Horario` aparecen solo en
  `Tomacorrientes`;
- confirmar que las cuatro macros bajo `Xcluidos` no aparecen en menus ni barras;
- ejecutar ambas macros movidas en un documento temporal;
- confirmar que `Alinear` conserva `Rayo.svg` por la decision documentada;
- confirmar que la barra global `Programacion` no cambia.

---

## 13. Interfaz - advertencia PySide6 en selector de modos

### Archivo

`ElectricCR/ui/mode_combo.py`

### Hallazgo

La funcion `_disconnect_combo(combo)` ejecuta actualmente:

`combo.currentIndexChanged.disconnect()`

sin especificar un receptor. Cuando `ensure_mode_combo()` acaba de crear el
selector, la senal todavia no tiene un manejador conectado y PySide6 puede
emitir:

`RuntimeWarning: Failed to disconnect (None)`

El `try/except` no evita necesariamente el aviso porque Qt puede emitirlo como
advertencia de ejecucion y no como una excepcion Python convencional.

### Impacto

- severidad baja;
- no bloquea la activacion de ElectricCR;
- no altera actualmente el cambio de modos;
- el `disconnect()` general tiene el riesgo adicional de desconectar receptores
  ajenos si en el futuro otras partes de ElectricCR escuchan
  `currentIndexChanged`.

### Correccion recomendada

Mantener un manejador propio asociado al combo y desconectar solamente ese
manejador durante una recarga:

1. comprobar si el combo conserva un manejador anterior;
2. si existe, ejecutar `disconnect(manejador_anterior)`;
3. crear el nuevo manejador;
4. guardarlo como atributo del combo;
5. conectarlo una sola vez.

### Decision

PENDIENTE DE MANTENIMIENTO MENOR. No requiere cambiar la logica de modos ni
mezclarse con la tarea actual de reorganizacion de macros e iconos.

---

## 14. Panel de macros ElectricCR - lanzador y diagnostico

### Objetivo

Evolucionar `Panel de macros ElectricCR` desde un lanzador buscable hacia un centro ligero de herramientas y diagnostico, manteniendo una vista normal simple para uso diario.

### Mejoras acordadas

- columnas con ancho automatico en primera apertura y persistencia despues de ajuste manual;
- icono visible y de tamano legible junto al nombre de herramienta;
- mostrar grupo, cantidad de usos y ultimo uso en la vista normal;
- panel de detalles con ruta, comando, icono resuelto, estado del icono, estadisticas y gestion de transaccion cuando pueda determinarse;
- botones `Ejecutar`, `Copiar ruta` y `Copiar diagnostico`;
- modo `Diagnostico` con estado OK / REVISAR / ERROR;
- filtros utiles como Todas, Mas usadas, Nunca usadas y Con Rayo;
- reutilizar `ElectricCR/usage_log.py` en vez de crear otro sistema de estadisticas;
- exponer metadatos desde el registro de comandos para evitar que el Panel duplique la resolucion de archivos/iconos/toolbars.

### Regla de iconos

`Rayo.svg` no es automaticamente un error. Si la funcion o el icono apropiado son dudosos, mantener Rayo y marcar la herramienta como pendiente/revisar. No inventar un icono solo para eliminar el Rayo.

### Fase 2 futura

Dejar para una tarea posterior el registro estructurado de ejecuciones correctas/fallidas, ultimo error e historial de errores por herramienta.

### Referencia de tarea

Preparada como tarea separada: `TAREA_PANEL_MACROS_ELECTRICCR.md`.


---

## 15. Panel de macros ElectricCR - catalogo vivo, comentarios y uso real/pruebas

### Estado

IMPLEMENTADA / PROBADA TECNICAMENTE / VALIDADA VISUALMENTE EN MCP.

### Objetivo

Ampliar la Fase 1 ya funcional del Panel para convertirlo en un inventario vivo
que pueda leer directamente GPT/Codex y que permita registrar la evaluacion
humana de cada herramienta.

### Mejoras acordadas

- botones `Contraer grupos` y `Expandir grupos`;
- descripcion objetiva de que hace cada macro;
- comentario editable por macro;
- estado manual y decision separados del diagnostico tecnico automatico;
- catalogo versionado `ElectricCR/data/macros_catalog.json`;
- reporte humano `ElectricCR/MACROS_CATALOGO.md` generado desde el JSON;
- usar `Inventario_Clasificacion_ElectricCR_2026-08-08.xlsx` como semilla
  historica, reconciliandola con decisiones mas recientes;
- separar estadisticas nuevas en uso real, pruebas e historico sin clasificar;
- boton `Probar` separado de `Ejecutar`;
- filtros por comentarios, pendientes de revisar, decision y uso real;
- ampliar `Copiar diagnostico` con descripcion, comentario, decision y
  estadisticas separadas.

### Regla de datos

El Excel no debe convertirse en dependencia de runtime. Se usa como fuente de
migracion/inventario historico. El JSON sera el registro estructurado del Panel
y el Markdown una vista generada para lectura humana/Codex.

Los conteos anteriores a la separacion uso/prueba no deben reclasificarse como
uso real; conservarlos como historico sin clasificar.

### Referencia de tarea

`TAREA_PANEL_MACROS_ELECTRICCR_FASE2.md`

### Resultado Fase 2 - 2026-08-12

Se generaron 192 entradas en el catalogo JSON: 122 herramientas activas
reconciliadas con el registro de ElectricCR y 70 entradas historicas no activas.
Se encontraron 69 descripciones desde metadatos oficiales o encabezados de
macro; el resto queda explicitamente sin descripcion. No se encontro una copia
local del Excel indicado, por lo que no se usaron datos historicos del Excel.
El Panel ahora permite editar comentario, estado manual y decision, contraer o
expandir grupos, consultar historicas y separar uso real, pruebas e historico.
Las ejecuciones normales se clasifican como `real` y el boton `Probar` como
`test`; los conteos anteriores permanecen como `legacy/unclassified`.

Correccion posterior verificada: al cambiar de macro, el comentario se guarda
contra la seleccion anterior antes de cargar la nueva. Se agrego cache de filas,
estadisticas, recursos de comandos y catalogo para que buscar no reconstruya
192 entradas en cada tecla.
