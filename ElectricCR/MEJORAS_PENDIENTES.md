# ElectricCR - Mejoras pendientes y observaciones de trabajo

**Proposito:** Mantener una memoria viva de mejoras, observaciones funcionales y hallazgos que todavia no constituyen cambios aceptados. Este archivo sirve como puente para Marco, GPT y Codex.

**Version:** 2026-08-10 19:14, America/Costa_Rica.

**FreeCAD objetivo:** 1.1.3

## Reglas de uso

- Registrar aqui ideas, defectos, dependencias rotas y mejoras detectadas durante pruebas reales.
- No considerar una nota de este archivo como cambio aceptado ni como autorizacion para eliminar codigo.
- Antes de implementar una mejora, revisar codigo actual, respaldos, historial y documentacion relacionada.
- Cuando una mejora sea implementada y validada, trasladar su estado a `RESULTADO_CODEX.md`, `REVISION_MACROS.md` y, cuando corresponda, `HISTORIAL_CAMBIOS.md`.
- Evitar duplicar herramientas: preferir motores generales con adaptadores o comandos pequenos.

---

## 1. Areas - dependencia faltante de AnalizarAreasDesdeMuroBIM

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

- Recuperar la version correcta dentro del repositorio.
- No borrar la copia localizada en `Scripts Varios` hasta verificar la migracion.
- Evitar que una instalacion limpia dependa de archivos residuales fuera de `Macros-de-Freecad`.
- Revisar si la logica debe integrarse posteriormente a `FacilArquitecturaWB/core` en vez de mantenerse como macro externa.

---

## 2. Areas como fuente espacial comun de ElectricCR

Los objetos Area deberian evolucionar hacia una fuente espacial comun para otras disciplinas.

Informacion deseable por Area:

- nombre normalizado del recinto;
- tipo o descripcion funcional;
- geometria;
- area en m2;
- largo;
- ancho;
- altura;
- propiedades de iluminacion;
- propiedades de tomacorrientes;
- propiedades de deteccion de incendio;
- propiedades HVAC;
- otros sistemas futuros.

La tabla real de La Cruz muestra que esta estructura ya empieza a existir y puede servir como caso de prueba.

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
