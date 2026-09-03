# DISENO_ELEMENTDATA_TABLAS - FacilArquitecturaWB

Fecha y hora: 2026-08-23 16:59 America/Costa_Rica  
FreeCAD objetivo: 1.1.3  
Estado: ESPECIFICACION PREVIA A CODEX / SIN IMPLEMENTACION TODAVIA

## 1. Proposito

Definir una arquitectura reutilizable para transferir informacion de elementos entre versiones de un mismo proyecto FreeCAD sin copiar ciegamente objetos BIM completos.

Primer caso real: ventanas.

Ejemplo esperado:

```text
Upala version anterior
  -> ventanas BIM existentes
  -> extraer Spreadsheet_Ventanas
  -> copiar/exportar la tabla

Upala version nueva
  -> Sketch_Centros_Ventanas reconstruido
  -> pegar/importar Spreadsheet_Ventanas
  -> validar correspondencias
  -> recrear/actualizar ventanas BIM
```

La tabla no sustituye al Sketch. El Sketch sigue siendo la autoridad geometrica principal.

## 2. Decision principal de arquitectura

No crear una sola Spreadsheet plana con todas las categorias y cientos de columnas.

Usar:

```text
ElementDataCore
   |
   +-- Spreadsheet_Ventanas
   +-- Spreadsheet_Puertas       # futuro
   +-- Spreadsheet_Equipos       # futuro
   +-- Spreadsheet_Luminarias    # futuro
   +-- otras categorias
```

Los usuarios ven tablas separadas por categoria. El nucleo comun comparte contratos, identificadores, validacion, matching, serializacion y dry_run.

## 3. Reutilizacion de FreeCAD antes de crear codigo propio

La implementacion debe reutilizar y verificar en FreeCAD real 1.1.3:

### 3.1 Arch/BIM Window

Las ventanas actuales de FacilArquitecturaWB ya son objetos nativos `ArchWindow._Window` con `IfcType = Window`, `Base`, `Hosts`, `WindowParts`, `Preset`, dimensiones y propiedades FA de trazabilidad.

Decision: no crear un nuevo tipo `FA_Window`.

### 3.2 Spreadsheet

Usar `Spreadsheet::Sheet` como representacion visible y editable de datos por categoria.

La tabla sera una capa de intercambio y edicion. Evitar conectar masivamente la misma tabla en ambos sentidos mediante Expressions si eso puede crear dependencias/ciclos o una red dificil de mantener.

Preferir operaciones explicitas:

```text
modelo -> extraer -> Spreadsheet_Ventanas
Spreadsheet_Ventanas -> validar -> aplicar -> modelo
```

### 3.3 Schedule / Report

Investigar y reutilizar los mecanismos nativos disponibles para consultar objetos y propiedades del modelo. La documentacion revisada muestra `Schedule` y herramientas BIM de reporte/consulta; Codex debe comprobar con MCP cuales estan realmente disponibles y utilizables en la instalacion FreeCAD 1.1.3 del usuario antes de duplicar logica.

### 3.4 Manage Doors and Windows

Codex debe inspeccionar mediante MCP el administrador nativo de puertas/ventanas de BIM y determinar si alguna parte de su seleccion, edicion o presentacion puede reutilizarse.

## 4. Autoridad de datos para ventanas

### Del Sketch

Autoritativo para:

- posicion XY;
- orientacion;
- longitud/ancho del vano;
- identidad geometrica aproximada de cada eje.

Si el ancho cambia en la version nueva, la ventana debe adoptar el ancho del Sketch nuevo salvo una regla explicita futura.

### De la tabla

Autoritativo para:

- `ElementID` visible, por ejemplo `V-001`;
- altura;
- antepecho;
- preset/tipo;
- datos de marco/apertura que se decida conservar;
- nombre de recinto/ubicacion cuando exista;
- observaciones;
- version de esquema.

### Del modelo destino

Se resuelve nuevamente:

- `Hosts`;
- muro compatible;
- Level/Building Storey;
- relaciones BIM;
- Placement final coherente con el Sketch y el antepecho.

No copiar `HostWall.Name` antiguo como autoridad.

## 5. Esquema comun minimo

Cada registro debe poder serializarse como diccionario JSON-compatible.

Campos comunes propuestos:

```text
SchemaVersion
ElementID
Category
SourceSketch
GeometryIndex
CenterX
CenterY
Length
AngleDeg
LevelKey
RoomKey
GeneratedBy
Notes
```

No todos son obligatorios. La implementacion debe distinguir entre datos de identidad, datos geometricos de verificacion y datos descriptivos.

## 6. Campos especificos de ventanas

Primera version propuesta:

```text
Height
SillHeight
Preset
Opening
Frame
Offset
IfcType
```

`Width` puede aparecer en la Spreadsheet como dato informativo/diagnostico, pero el ancho aplicado debe provenir del Sketch actual.

No asumir que existe una propiedad nativa estable `SillHeight` util para este flujo. Codex debe verificar la API real 1.1.3 y aplicar el antepecho mediante el mecanismo nativo correcto, normalmente relacionado con Placement/Base Sketch, conservando ademas `FA_SillHeight` si hace falta como dato explicito de transferencia.

## 7. Matching entre tabla y Sketch

No depender solo de `GeometryIndex`.

Orden propuesto:

1. buscar por `SourceSketch + GeometryIndex`;
2. validar firma geometrica;
3. si el indice no coincide, buscar por proximidad geometrica;
4. comparar centro, longitud y angulo con tolerancias explicitas;
5. aceptar solo coincidencia unica y suficientemente buena;
6. clasificar como `AMBIGUO` si hay dos o mas candidatos equivalentes;
7. clasificar como `NO_MATCH` si no existe candidato seguro.

Estados de dry_run:

```text
MATCH
CAMBIO
NO_MATCH
AMBIGUO
```

La primera version no debe adivinar correspondencias.

## 8. Spreadsheet_Ventanas propuesta

Columnas visibles iniciales:

```text
A  ElementID
B  SourceSketch
C  GeometryIndex
D  CenterX
E  CenterY
F  WidthSketch
G  AngleDeg
H  Height
I  SillHeight
J  Preset
K  Opening
L  Room
M  Level
N  Status
O  Notes
```

Las columnas pueden cambiar despues de la prueba MCP, pero conservar la separacion conceptual entre geometria del Sketch y propiedades transferibles.

## 9. Operaciones de usuario

Una sola herramienta conceptual `FA Tabla de ventanas` puede exponer tres acciones:

### Extraer del modelo

- detectar ventanas BIM validas;
- recuperar sus propiedades;
- recuperar trazabilidad FA cuando exista;
- crear/actualizar `Spreadsheet_Ventanas`;
- no modificar geometria.

### Validar tabla contra Sketch

- solo lectura;
- producir `MATCH/CAMBIO/NO_MATCH/AMBIGUO`;
- no crear, borrar ni modificar ventanas;
- imprimir resumen `[FACILARQ]`.

### Aplicar tabla

- abrir transaccion;
- usar solamente filas validas;
- reutilizar generador nativo vigente de ventanas;
- resolver host nuevamente;
- conservar objetos manuales no relacionados;
- evitar duplicados;
- soportar Undo/Redo.

## 10. Intercambio entre archivos

Primera necesidad: copiar y pegar la Spreadsheet entre archivos FreeCAD.

Tambien conviene soportar exportacion/importacion CSV si FreeCAD la proporciona de manera estable para `Spreadsheet::Sheet`.

El nucleo debe quedar preparado para JSON compatible:

```json
{
  "schema_version": 1,
  "project_key": "Upala",
  "categories": {
    "windows": []
  }
}
```

No implementar una base de datos externa en la primera version.

## 11. Reutilizacion futura por otros Workbenches

El contrato comun puede reutilizarse mas adelante para:

- puertas de FacilArquitecturaWB;
- luminarias, tomacorrientes, tableros y camaras de ElectricCR;
- equipos HVAC;
- otros elementos cuyo patron sea `geometria = ubicacion` y `tabla = especificacion`.

No introducir dependencias de FacilArquitecturaWB hacia ElectricCR/HVAC en esta fase.

## 12. API deseable para MCP

Funciones del nucleo, sin GUI cuando sea posible:

```text
extract_elements(category, document=None) -> dict/list JSON-compatible
build_table_data(category, records) -> dict/list
validate_records(category, records, geometry_source, tolerance) -> report
apply_records(category, records, geometry_source, dry_run=True) -> report
serialize_records(records) -> dict
```

Los nombres definitivos deben adaptarse a la estructura existente y no duplicar funciones de `opening_utils.py` ni `bim_utils.py`.

## 13. Seguridad y trazabilidad

- lectura por defecto;
- `dry_run=True` por defecto en funciones aplicables;
- transacciones FreeCAD para escrituras;
- no borrar objetos manuales;
- no modificar coincidencias ambiguas;
- mensajes `[FACILARQ]` utiles;
- resultado JSON-compatible para MCP;
- una sola fuente de verdad por archivo;
- conservar caracteristicas que ya funcionan.

## 14. Pruebas de aceptacion

Caso principal:

1. abrir una copia de Upala anterior con ventanas BIM;
2. extraer `Spreadsheet_Ventanas`;
3. copiar/exportar la tabla;
4. abrir Upala nuevo con Sketch de ventanas equivalente;
5. pegar/importar la tabla;
6. ejecutar validacion en dry_run;
7. revisar coincidencias;
8. aplicar;
9. verificar ancho desde Sketch nuevo;
10. verificar altura, antepecho y preset desde tabla;
11. verificar host nuevo;
12. reejecutar sin duplicados;
13. Undo/Redo;
14. guardar/cerrar/reabrir.

Prueba de robustez:

- reordenar indices geometricos sin mover las ventanas y comprobar recuperacion por firma;
- mover una ventana fuera de tolerancia y exigir `NO_MATCH`;
- crear dos candidatos equivalentes y exigir `AMBIGUO`.

## 15. Trabajo previo ya realizado por GPT

Antes de Codex quedan definidos:

- separacion entre tablas visibles y nucleo comun;
- autoridad de datos Sketch/tabla/modelo destino;
- esquema comun minimo;
- esquema especifico de ventanas;
- matching por indice + firma geometrica;
- dry_run y estados de validacion;
- flujo Upala anterior -> tabla -> Upala nuevo;
- puntos nativos de FreeCAD que deben verificarse/reutilizarse.

Codex no debe empezar redisenando estos puntos sin una razon tecnica demostrable. Debe primero verificar la API/GUI real de FreeCAD 1.1.3 mediante MCP y ajustar solo lo necesario.

## 16. Fuentes tecnicas revisadas

- FreeCAD Arch Window: https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/BIM/ArchWindow.py
- FreeCAD Arch Window Presets: https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/BIM/ArchWindowPresets.py
- FreeCAD Spreadsheet Workbench: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Spreadsheet_Workbench.md
- FreeCAD Expressions: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Expressions.md
- FreeCAD BIM Workbench documentation: https://github.com/FreeCAD/FreeCAD-documentation

Estas fuentes orientan la arquitectura, pero la instalacion real FreeCAD 1.1.3 del usuario mediante MCP es la autoridad final para disponibilidad y comportamiento.


---

# Extension 2026-08-28 - Tabla de Puertas

Estado: IMPLEMENTACION CANDIDATA 0.14.8 / PENDIENTE VALIDACION FREECAD REAL.

La segunda categoria productiva de `ElementDataCore` es `doors`. Se conserva el mismo contrato geometrico y de matching usado por ventanas; no se crea un nucleo paralelo.

## Autoridad de datos

- Sketch destino: posicion, orientacion y ancho de cada puerta.
- Tabla: altura, tipo, numero de hojas, bisagra, lado/sentido de apertura, porcentaje de apertura, Room/Level descriptivos y notas.
- Documento destino: Host, Level real y relaciones BIM.

## Tipos extensibles

Cada fila usa `DoorType` como nombre logico y separa la implementacion en `TypeSource` y `TypeRef`. Primera version:

- `native_preset`: `TypeRef` es un preset de puerta realmente instalado/publicado por `ArchWindowPresets`. Esto permite agregar presets FreeCAD sin modificar ElementDataCore.
- `fa_double`: `TypeRef=architecture.door.double_leaf.glazed.europa`, reutilizando `core/double_door_bim.py`.

Un `DoorType` de usuario puede llamarse, por ejemplo, `Puerta Oficina`, mientras `TypeRef=Glass door`. Un tipo/factory desconocido se rechaza en dry-run; nunca se sustituye silenciosamente.

## Bisagra y apertura

Se reutilizan los metadatos historicos del proyecto:

- `HingeEndpoint`: `START`, `END`, `BOTH` o `AUTO` respecto al segmento del Sketch.
- `HingePointX/Y`: coordenadas de comprobacion/transferencia.
- `OpeningSide`: `LEFT`, `RIGHT`, `IN`, `OUT` o `AUTO`.
- `OpensInward`: booleano descriptivo respecto al recinto.
- `Opening`: porcentaje grafico BIM.

La puerta doble usa `BOTH`. La tabla conserva los datos; no depende de volver a inferirlos desde Areas/recintos en cada transferencia.

## Organizacion visible

Las hojas ElementData se colocan bajo:

```text
FA_Project
`-- 06_Tables
    |-- Tabla de ventanas
    `-- Tabla de puertas
```

La migracion de una `Spreadsheet_Ventanas` existente es no destructiva: se reutiliza el mismo objeto y se agrega al grupo cuando la herramienta vuelve a abrirlo.

## Seguridad

Mantener `dry_run=True`, `MATCH/CAMBIO/NO_MATCH/AMBIGUO`, proteccion de objetos manuales, una transaccion por aplicacion e idempotencia `KEEP`. El override historico `FA_DoorTypeOverrides` sigue aplicando al comando normal de puertas, pero no puede sustituir un tipo explicitamente autoritativo de `Spreadsheet_Puertas`.
