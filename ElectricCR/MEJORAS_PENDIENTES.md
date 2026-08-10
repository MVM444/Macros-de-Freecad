# ElectricCR - Mejoras pendientes y observaciones de trabajo

**Proposito:** Mantener una memoria viva de mejoras, observaciones funcionales y hallazgos que todavia no constituyen cambios aceptados. Este archivo sirve como puente para Marco, GPT y Codex.

**Version:** 2026-08-10 11:28, America/Costa_Rica.

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

## 8. Estado

Este documento contiene PENDIENTES y observaciones.

No implica que las mejoras ya esten implementadas, probadas o aceptadas.

Cuando una observacion pase a desarrollo, Codex debe registrar el resultado tecnico y Marco debe validar el comportamiento real en FreeCAD antes de integrarla definitivamente.
