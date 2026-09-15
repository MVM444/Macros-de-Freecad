# Barra comun de Espacios y Recintos

Fecha: 2026-09-03 America/Costa_Rica
Estado: V0.1 IMPLEMENTADA Y VERIFICADA MCP / CONTRATO DE CONSUMO A1 DEFINIDO
FreeCAD objetivo: 1.1.3

## 1. Principio

Una sola identidad de recinto fisico debe ser compartida por todos los Workbenches.

```text
geometria / deteccion
        |
        v
Arch/BIM Space canonico
        |
        v
CRBIMCore.RoomResolver
        |
        +-- FacilArquitecturaWB
        +-- ElectricCR
        +-- MEPWorkbenchCR
        `-- futuros consumidores
```

Si no existe un Space, RoomResolver conserva compatibilidad temporal con Areas legacy validas.

Regla:

> El Space/Area fisico resuelto es la identidad espacial. Los objetos disciplinares consumen esa identidad; no crean otro recinto arquitectonico.

## 2. Nombre visible de la barra

Nombre adoptado para esta fase:

**Espacios y Recintos**

El termino `Areas` queda reservado para objetos y herramientas legacy que todavia producen geometria de recinto.

No se renombra destructivamente ninguna macro ni ruta durante esta fase de diseno.

## 3. Hallazgos de la auditoria

### 3.1 FreeCAD nativo

FreeCAD 1.1.3 dispone del comando nativo `Arch_Space` y de `Arch.makeSpace`.

La herramienta nativa se conserva como capacidad BIM disponible, pero no se duplica dentro de CRBIMCore.

La barra comun debe reutilizar la identidad `Arch/BIM Space`, no crear una clase paralela.

### 3.2 Facil Arquitectura

FA ya dispone de un flujo funcional y no destructivo:

- `FA Detectar recintos 2D`;
- `FA Crear espacios BIM`;
- `core/room_utils.py`;
- `core/space_utils.py`.

`FA Crear espacios BIM` crea/actualiza Arch Spaces nativos y conserva identidad mediante `FA_RoomUID`, con estados `MATCH`, `CAMBIO`, `NO_MATCH` y `AMBIGUO`.

Conclusion:

- detectar geometria de recintos es un **productor arquitectonico**;
- crear/actualizar Space es **autoria arquitectonica**;
- estos comandos siguen siendo de FA;
- sus servicios internos pueden ser reutilizables, pero no se convierten automaticamente en comandos comunes de CRBIMCore.

### 3.3 ElectricCR - antigua barra Areas

Herramientas inventariadas:

| Herramienta actual | Funcion | Decision para Espacios y Recintos |
|---|---|---|
| `Areas/AreaPorClick.FCMacro` | Detecta un recinto por click y crea Area legacy | MANTENER como productor ElectricCR durante transicion; candidato futuro a emitir contrato neutral |
| `Areas/AsignarNombreEstandar.FCMacro` | Aplica nombre estandar a recinto | EVOLUCIONAR a comando comun `Nombrar recinto` compatible con Space y Area |
| `Areas/CrearMurosEntreEspacios.FCMacro` | Dibuja referencias entre objetos | MOVER/CONSERVAR en Facil Arquitectura; no pertenece al nucleo comun |
| `Areas/Guia_Areas.FCMacro` | Guia operativa | EVOLUCIONAR a `Guia Espacios y Recintos` |
| `Areas/PoligonoFromBoundaryLines.FCMacro` | Poligono desde limites seleccionados | PRODUCTOR avanzado/secundario; no boton comun principal |
| `Areas/PoligonosRecintosDesdeArchWalls.FCMacro` | Poligonos exactos desde huella de muros Arch/BIM | PRODUCTOR TRANSVERSAL PROTEGIDO; mantener visible y funcional; candidato prioritario a extraer luego a nucleo geometrico neutral |
| `Areas/RectFromBoundaryLines.FCMacro` | Rectangulo desde limites de muros | MANTENER visible en ElectricCR durante transicion; productor muy usado |
| `Areas/RectFromLines.FCMacro` | Rectangulo desde lineas | LEGACY/SECUNDARIO |
| `Areas/RectFromSelection.FCMacro` | Rectangulo desde seleccion | LEGACY/SECUNDARIO |
| `Areas/SustituirAreasPorRectangulosNuevos.FCMacro` | Sustituye Areas anteriores | LEGACY / revisar antes de volver a exponer |

El historial de uso confirma que la antigua barra era transversal y operativa, principalmente por `RectFromBoundaryLines`, `AreaPorClick` y `AsignarNombreEstandar`. La migracion a Space no debe eliminar esos flujos sin sustituto probado.

### 3.4 MEPWorkbenchCR

`HVACSpace.BaseSpace` puede enlazar al Space/Area fisico.

Reglas ya cerradas:

- `HVACSpace.BaseSpace` se sigue hasta la identidad fisica;
- un `HVACSpace` sin BaseSpace no es un recinto arquitectonico comun;
- `SubArea` no es un recinto arquitectonico comun.

Por tanto, MEP es inicialmente consumidor de la barra comun, no productor de Space.


## 3.5 Productor transversal protegido: recintos desde muros BIM

La auditoria del README de `Areas` confirma que `PoligonosRecintosDesdeArchWalls.FCMacro` tiene un valor distinto al de RoomResolver y al de Arch Space.

Su salida es geometria 2D reusable:

```text
muros Arch/BIM
     |
union de caras superiores
     |
huecos interiores cerrados
     |
Draft Wire cerrado + MakeFace
     |
     +-- recinto/Area
     +-- cielorraso
     +-- calculos por recinto
     `-- otros consumidores 2D
```

La macro conserva `Points` editables, cara valida, trazabilidad a muros fuente y metadatos de area. Esto la convierte en un **productor geometrico transversal**, no en una simple macro legacy de ElectricCR.

FreeCAD nativo `Arch Space` puede definirse desde un solido o caras limite, pero eso no reemplaza la obtencion automatica de un contorno 2D editable para consumidores documentales. Por tanto, ambas capacidades son complementarias.

Decision v0.1:

- conservar el algoritmo actual sin refactor destructivo;
- mantener el boton `Recintos desde muros BIM` en ElectricCR dentro de `Espacios y Recintos`;
- no hacer que FA importe ElectricCR;
- despues de estabilizar la barra, estudiar extraer la logica geometrica a un servicio neutral compartido por FA, ElectricCR y MEP;
- preservar como deuda conocida que una regeneracion puede sustituir correcciones manuales en `Points`.

## 4. Clasificacion conceptual

### A. Operaciones comunes CRBIMCore

Son operaciones que significan lo mismo desde cualquier Workbench.

1. Resolver / seleccionar recinto.
2. Informacion del recinto.
3. Nombrar recinto.
4. Guia Espacios y Recintos.

### B. Productores arquitectonicos FA

1. Detectar recintos 2D.
2. Crear / actualizar Spaces BIM.
3. Algoritmos de geometria arquitectonica que se consoliden en FA.

### C. Productores legacy ElectricCR durante transicion

1. Recinto por click (`AreaPorClick`).
2. Rectangulo desde limites (`RectFromBoundaryLines`).
3. `PoligonosRecintosDesdeArchWalls` como **productor transversal protegido**, no legacy. Debe conservarse porque genera contornos 2D editables y validos para recintos, cielorrasos y otros consumidores.
4. Poligono desde lineas limite como herramienta avanzada.

### D. Consumidores disciplinares

- iluminacion;
- tomacorrientes;
- deteccion;
- HVAC;
- otros sistemas MEP.

Los consumidores resuelven Space/Area mediante CRBIMCore.

## 5. Barra minima comun v0.1

### 5.1 `Seleccionar recinto`

Objetivo:

- aceptar seleccion actual o un punto clicado;
- resolver con `CRBIMCore.RoomResolver`;
- seleccionar el objeto fisico resuelto;
- no escribir propiedades.

Salida visible minima:

```text
Estado: RESOLVED | AMBIGUOUS | NOT_FOUND
Fuente: SPACE | AREA_LEGACY
Objeto: Name / Label
```

Si es `AMBIGUOUS`, mostrar candidatos y no escoger silenciosamente.

### 5.2 `Info recinto`

Operacion read-only.

Debe mostrar como minimo:

- Name;
- Label;
- tipo/fuente (`Space` o Area legacy);
- area;
- identificador persistente si existe (`FA_RoomUID`);
- identificador documental si existe (`FA_RoomID`);
- Level derivado cuando sea posible;
- Base/fuente geometrica cuando exista;
- estado RoomResolver.

No debe escribir datos ElectricCR/MEP sobre el Space.

### 5.3 `Nombrar recinto`

Evolucion conceptual de `AsignarNombreEstandar`.

Debe aceptar:

- Arch/BIM Space;
- Area legacy valida.

Reglas:

- modificar solamente los campos de nombre que correspondan;
- no cambiar `FA_RoomUID`;
- no cambiar Base;
- no cambiar geometria;
- no convertir Area a Space;
- conservar lista de nombres estandar existente si resulta compatible.

La implementacion debe auditar primero exactamente que propiedades modifica la macro legacy.

### 5.4 `Guia Espacios y Recintos`

Reemplaza conceptualmente `Guia Areas`.

Debe explicar:

```text
1. Como obtener el recinto.
2. Diferencia Space / Area legacy.
3. Como nombrarlo.
4. Como usan el recinto ElectricCR y MEP.
5. Como crear/actualizar Spaces desde Facil Arquitectura.
6. Que significa AMBIGUOUS / NOT_FOUND.
```

La guia puede registrarse desde varios Workbenches usando una sola fuente.

## 6. Comandos que NO entran en el nucleo comun v0.1

### `Crear / actualizar Space`

No sera boton comun v0.1.

Razon:

- es autoria arquitectonica;
- FA ya dispone de un flujo probado y persistente;
- ElectricCR debe poder consumir recintos sin depender de FA;
- si ElectricCR solo tiene Areas legacy, RoomResolver ya permite continuar.

La API de creacion de Space puede reutilizarse mas adelante si se extrae un contrato neutral suficientemente claro.

### `Asignar seleccion al Space`

Se aplaza a v0.2.

Razon:

cada familia utiliza relaciones distintas:

- dispositivo ElectricCR -> `Space`;
- HVACSpace -> `BaseSpace`;
- otros elementos pueden usar otro contrato.

Antes de exponer un boton comun debe existir un registro/adaptador de asignacion por tipo, con `dry_run` y sin inventar propiedades.

## 7. Composicion visible por Workbench

La barra puede compartir nombre y comandos comunes sin exigir exactamente los mismos productores.

### Facil Arquitectura

```text
Espacios y Recintos
  [Seleccionar recinto]
  [Info recinto]
  [Nombrar recinto]
  ---
  [Detectar recintos 2D]
  [Crear / actualizar espacios BIM]
  ---
  [Guia]
```

### ElectricCR - transicion

```text
Espacios y Recintos
  [Seleccionar recinto]
  [Info recinto]
  [Nombrar recinto]
  ---
  [Recinto por click]              # legacy productor
  [Rectangulo desde limites]       # legacy productor
  [Recintos desde muros BIM]       # productor transversal protegido
  ---
  [Guia]
```

Las herramientas avanzadas/legacy restantes deben quedar en menu/panel y no ocupar la barra principal.

### MEPWorkbenchCR - primera etapa

```text
Espacios y Recintos
  [Seleccionar recinto]
  [Info recinto]
  [Nombrar recinto]
  ---
  [Guia]
```

Los comandos propios de HVAC/SubArea permanecen en sus barras disciplinares.

## 8. Regla de registro

No copiar implementaciones entre Workbenches.

Arquitectura objetivo:

```text
CRBIMCore
  room_resolver_core.py
  freecad_room_adapter.py
  room_commands/            # futuro, si se aprueba
        |
        +-- resolver/seleccionar
        +-- info
        +-- nombrar
        `-- guia

FA / ElectricCR / MEP
        |
        `-- registran los mismos command IDs comunes
            y agregan solo sus productores propios
```

CRBIMCore no se convierte por ello en un Workbench visual independiente.

## 9. Regla del arbol

El Space real permanece bajo la jerarquia arquitectonica Building/Level.

ElectricCR y MEP pueden mostrar:

```text
Recintos
  Oficina
```

como contenedor o referencia de proyeccion, pero nunca como un segundo Space.

## 10. Compatibilidad

- Space nativo: autoridad principal.
- Area legacy valida: fallback.
- `AMBIGUOUS`: no elegir automaticamente.
- `NOT_FOUND`: no crear ni asignar silenciosamente.
- No borrado de Areas.
- No migracion automatica en v0.1.
- No cambio de IDs persistentes.
- `dry_run` para cualquier futura operacion de migracion/asignacion.

## 11. Criterios de aceptacion para futura implementacion

### Pruebas puras

- RoomResolver mantiene sus pruebas actuales.
- formateo de info no requiere FreeCADGui;
- naming neutral no toca UID/geometry en mocks.

### FreeCAD real 1.1.3

1. Space unico -> seleccionar e informar correctamente.
2. Area legacy unica -> seleccionar e informar como fallback.
3. Space + Area superpuestos -> Space gana.
4. dos Spaces plausibles -> AMBIGUOUS, sin seleccion arbitraria.
5. punto exterior -> NOT_FOUND.
6. nombrar Space conserva Name interno/UID/Base segun contrato acordado.
7. nombrar Area legacy conserva geometria y propiedades.
8. FA sigue creando/actualizando Spaces sin regresion.
9. ElectricCR sigue funcionando sin FA activo.
10. HVACSpace.BaseSpace sigue resolviendo la identidad fisica.
11. SubArea sigue excluida.
12. Undo/Redo para el unico comando comun de escritura (`Nombrar recinto`).
13. guardar/cerrar/reabrir conserva resultados.
14. no modificar ningun FCStd original durante smoke.

## 12. Auditoria cerrada de `AsignarNombreEstandar`

La version auditada de la macro legacy:

- crea o usa una hoja `NombresEstandar`;
- propone nombres como Oficina, Sala de Espera, Bodega, Recepcion y Pasillo;
- permite refrescar la lista desde la hoja;
- marca visualmente en gris los nombres ya utilizados;
- permite reutilizar un nombre;
- cambia solamente `obj.Label`;
- actualmente acepta cualquier objeto seleccionado;
- no valida que el objeto sea un recinto;
- no protege explicitamente UID/Base/geometria;
- no abre una transaccion propia para el cambio de nombre.

Por tanto, la GUI/lista es reutilizable conceptualmente, pero la operacion de escritura debe rehacerse sobre el contrato CRBIMCore.

### Contrato seguro de `Nombrar recinto`

Entrada:

- uno o varios objetos seleccionados que sean directamente:
  - Arch/BIM Space valido, o
  - Area legacy valida reconocida por RoomResolver.

No se renombraran dispositivos, grupos, proyecciones del arbol ni otros objetos aunque puedan estar dentro de un recinto.

Comportamiento:

1. validar todos los objetos;
2. separar validos de rechazados;
3. mostrar resumen antes de escribir cuando existan rechazados;
4. abrir una unica transaccion;
5. cambiar solamente `Label`;
6. no modificar `Name` interno;
7. no modificar `FA_RoomUID`;
8. no modificar `FA_RoomID`;
9. no modificar Base, Shape, Placement ni pertenencia BIM;
10. marcar el nombre en `NombresEstandar` solo como estado de interfaz;
11. recomputar una vez;
12. permitir Undo/Redo.

Se permiten nombres repetidos porque varios recintos pueden compartir una denominacion funcional como `Oficina`.

## 13. Command IDs comunes

IDs internos propuestos y ya suficientemente estables para la primera implementacion:

```text
CRBIM_SelectRoom
CRBIM_RoomInfo
CRBIM_NameRoom
CRBIM_RoomGuide
```

Textos visibles:

```text
Seleccionar recinto
Info recinto
Nombrar recinto
Guia Espacios y Recintos
```

Regla de registro:

- cada Workbench llama a un helper comun `ensure...registered`;
- si el command ID ya existe en `FreeCADGui.listCommands()`, no se vuelve a registrar;
- la toolbar del Workbench puede incluir el mismo ID ya registrado;
- no se copia la implementacion entre FA, ElectricCR y MEP.

## 14. Iconos

No se necesita diseñar iconografia antes del prototipo.

Se puede reutilizar temporalmente:

- el icono existente de `Guia_Areas` para la guia;
- iconos simples propios de CRBIMCore para seleccionar, informar y nombrar.

Los nombres de recurso deben evitar caracteres especiales:

```text
CRBIM_SelectRoom.svg
CRBIM_RoomInfo.svg
CRBIM_NameRoom.svg
CRBIM_RoomGuide.svg
```

No reemplazar iconos legacy hasta verificar visualmente la barra.

## 15. FreeCAD nativo

La documentacion vigente de FreeCAD mantiene la herramienta Arch Space y describe su uso desde la barra/menu BIM. La comprobacion final del command ID `Arch_Space` debe hacerse en la instalacion real FreeCAD 1.1.3 mediante MCP antes de implementar cualquier fallback.

La barra comun no duplicara el comando nativo Space.

## 16. Arquitectura de implementacion propuesta

```text
CRBIMCore
  room_resolver_core.py              # existente, puro
  freecad_room_adapter.py            # existente, FreeCAD read-only
  room_operations_core.py            # futuro: contratos info/naming, puro
  freecad_room_operations.py         # futuro: seleccion/transacciones/adaptacion

FA / ElectricCR / MEP
  commands/common_rooms.py           # wrapper/registro pequeno
```

No colocar Qt ni `FreeCADGui` en `room_operations_core.py`.

La guia puede ser un recurso Markdown comun abierto por un wrapper GUI pequeno.

## 17. Estado previo a implementacion v0.1 (historico)

El diseño funcional v0.1 queda cerrado.

La primera tarea Codex, si el usuario la autoriza, debe limitarse a:

1. `CRBIM_SelectRoom`;
2. `CRBIM_RoomInfo`;
3. `CRBIM_NameRoom`;
4. `CRBIM_RoomGuide`;
5. registro idempotente desde FA y ElectricCR;
6. prueba de ElectricCR sin FA activo;
7. verificacion MCP en FreeCAD 1.1.3.

No debe:

- modificar productores;
- migrar Areas;
- crear Spaces automaticamente;
- asignar dispositivos a Space;
- reorganizar arboles;
- tocar MEP salvo smoke de compatibilidad.

## 18. Pendiente separado

El refactor de `objeto_toma_uno.py` hacia `dispositivo_electromecanico.py` pertenece a otro hilo y no debe mezclarse con esta barra.

## 19. Resultado comprobado de la v0.1

Estado al 2026-09-02: implementada y validada mediante MCP en FreeCAD 1.1.3.

- Command ID nativo confirmado: `Arch_Space`; `BIM_Space` no esta registrado.
- Los cuatro comandos comunes se registran una sola vez desde Facil
  Arquitectura o ElectricCR.
- Space unico, Area unica, prioridad Space, AMBIGUOUS y NOT_FOUND aprobaron.
- Info no modifica el documento.
- Nombrar conserva identidad, UID/ID, Base, Shape, Placement y contencion;
  permite Labels repetidos y aprueba Undo/Redo y reapertura.
- `HVACSpace.BaseSpace` continua resolviendo el recinto fisico y `SubArea`
  continua excluida.
- Las barras se verificaron visualmente con orden estable en ambos Workbenches.
- `PoligonosRecintosDesdeArchWalls.FCMacro` continua visible en ElectricCR como
  **Recintos desde muros BIM** y aprobo contornos rectangulares, en L y
  poligonales, Points editables, MakeFace, metadatos, enlaces y regeneracion.

La limitacion conocida del productor poligonal se conserva deliberadamente:
regenerar puede sustituir correcciones manuales hechas en `Points`. Resolverla
no pertenece a la v0.1.


## 20. Contrato de consumo por dispositivos electromecanicos A1

Estado al 2026-09-03: contrato transversal definido a partir de la barra v0.1,
`CRBIMCore.RoomResolver` y del prototipo `PhysicalDocumentationA1` verificado en
ElectricCR sobre FreeCAD 1.1.3.

La barra comun no crea una segunda identidad espacial para ElectricCR. El flujo
autoritativo queda:

```text
Facil Arquitectura / BIM
  Wall / Door / Window / Space
              |
              v
CRBIMCore.RoomResolver
              |
              v
ElectricCR dispositivo A1
  Space        -> Arch/BIM Space canonico
  Host         -> soporte BIM real
  Level        -> derivado de Space cuando sea posible
  PuertaOrigen -> Door BIM real cuando la familia lo requiera
```

### 20.1 Reglas de autoridad

- `Space` del dispositivo es un `App::PropertyLink` a la identidad espacial
  canonica cuando RoomResolver devuelve `RESOLVED`.
- `AMBIGUOUS` y `NOT_FOUND` no producen asignacion silenciosa.
- `Host` enlaza el soporte BIM real: muro, cielo, piso u otro host valido. Un
  Sketch auxiliar no sustituye al Host.
- `Level` se deriva del Space siempre que exista una relacion arquitectonica
  suficiente; no se duplica por defecto en la instancia.
- `PuertaOrigen` es una extension de familia para apagadores u otros dispositivos
  cuya regla de colocacion dependa de una puerta. Debe apuntar a la puerta BIM,
  no al Sketch auxiliar usado para calcular posicion.
- `Area`, `AreaRecinto`, `Recinto` y nombres de Sketch permanecen unicamente como
  compatibilidad legacy o evidencia diagnostica durante la transicion.

### 20.2 Productores y consumidores

Facil Arquitectura conserva la autoria de:

- deteccion geometrica arquitectonica;
- creacion/actualizacion de Arch/BIM Spaces;
- Wall, Door y Window BIM.

ElectricCR consume esas identidades. No debe importar ni copiar los algoritmos
de autoria de FA para crear un recinto paralelo.

El productor transversal `Recintos desde muros BIM` sigue siendo util para
geometria 2D y para fallback legacy, pero no desplaza al Space canonico cuando
este existe.

### 20.3 Relacion con el arbol

El Space real permanece bajo `Site/Building/Level`. Las ramas disciplinares
pueden mostrar el recinto mediante nodos o `App::Link` de proyeccion, pero nunca
mover, duplicar o convertir el Space para satisfacer una jerarquia visual.

La posicion en el arbol no asigna `Space`, `Host` ni `Level`. Las relaciones son
la autoridad y el arbol se reconstruye desde ellas.

### 20.4 Estado respecto a objetos existentes

La prueba A1 de ElectricCR ya verifico `ElementUID`, `Space` y `Host` en un
Tomacorriente y un Apagador temporales con contrato
`PhysicalDocumentationA1`.

Los tomacorrientes y apagadores legacy existentes en proyectos reales no se
migran por esta decision. Su adaptacion debe ser opt-in, con diagnostico previo,
`dry_run` cuando corresponda y sin sustituir objetos funcionales hasta contar
con una prueba real controlada.

### 20.5 Consecuencia para una futura barra v0.2

`Asignar seleccion al Space` solo puede incorporarse cuando exista un adaptador
por tipo de objeto que conozca su propiedad autoritativa (`Space`, `BaseSpace`,
etc.). No se agregaran propiedades genericas por nombre ni se inventaran enlaces
sobre objetos desconocidos.
