# TAREA VIGENTE - CRBIMCore / Barra comun de Espacios y Recintos

Fecha: 2026-09-02 America/Costa_Rica
Proyecto: Programacion en FreeCAD
Componentes: CRBIMCore, FacilArquitecturaWB, ElectricCR, MEPWorkbenchCR
FreeCAD objetivo: 1.1.3
Estado: IMPLEMENTACION CODEX AUTORIZADA / ALCANCE V0.1 CERRADO

## Objetivo cerrado

Implementar una barra `Espacios y Recintos` que comparta operaciones sobre la misma identidad espacial sin duplicar Space, Areas ni codigo entre Workbenches.

Documento autoritativo:
`CRBIMCore/BARRA_COMUN_ESPACIOS_RECINTOS.md`

## Regla principal

`Arch/BIM Space` es la identidad fisica canonica cuando existe.
`CRBIMCore.RoomResolver` usa Area legacy valida como fallback.

## Comandos comunes v0.1

- `CRBIM_SelectRoom` -> Seleccionar recinto.
- `CRBIM_RoomInfo` -> Info recinto.
- `CRBIM_NameRoom` -> Nombrar recinto.
- `CRBIM_RoomGuide` -> Guia Espacios y Recintos.

## Productores preservados en v0.1

FA conserva:
- Detectar recintos 2D.
- Crear / actualizar espacios BIM.

ElectricCR conserva durante la transicion:
- AreaPorClick.
- RectFromBoundaryLines.

### Productor transversal protegido: PoligonosRecintosDesdeArchWalls

`Areas/PoligonosRecintosDesdeArchWalls.FCMacro` **NO es legacy** y no debe deprecarse ni ocultarse.

La auditoria del README vigente confirma que:
- obtiene recintos poligonales directamente desde muros `Arch Wall` o `FA_Role=wall`;
- usa la union de las caras superiores de los muros para que puertas y ventanas no interrumpan la huella;
- crea un `Draft Wire` cerrado, editable mediante `Points`, con `MakeFace=True` y cara valida;
- conserva vertices reales del `OuterWire`;
- soporta recintos rectangulares, en L y otros contornos poligonales;
- registra `ElectricCRTipo=Area`, `FA_Role=room_polygon`, area, perimetro, vertices, `FA_GeometrySource=AUTO_BIM`, `FA_GeometryType=DraftWire` y enlaces a muros fuente;
- es util no solo para recintos, sino tambien como geometria base para cielorrasos y otros consumidores.

En esta primera implementacion:
- conservar la macro existente y su algoritmo sin reescribirlo;
- mantenerla visible en la barra `Espacios y Recintos` de ElectricCR con el texto `Recintos desde muros BIM`;
- no moverla aun a CRBIMCore ni hacer que FA dependa de ElectricCR;
- documentarla como candidata prioritaria a extraer despues a un productor geometrico neutral reutilizable;
- no alterar su formato de salida ni metadatos.

Limitacion conocida a preservar/documentar: al regenerar, la macro reemplaza sus propias salidas y actualmente puede perder correcciones manuales hechas en `Points`; no resolver esto dentro de la tarea v0.1.

MEP no crea recinto fisico comun en esta fase.

## Contrato de naming cerrado

La macro legacy auditada cambia `Label` de cualquier seleccion y usa la hoja `NombresEstandar`.

El nuevo comando:
- acepta solo Space o Area fisica valida;
- cambia solo `Label`;
- conserva `Name`, `FA_RoomUID`, `FA_RoomID`, Base, Shape, Placement y jerarquia;
- usa transaccion y Undo/Redo;
- puede reutilizar la hoja `NombresEstandar`;
- permite nombres repetidos;
- nunca renombra dispositivos o contenedores por accidente.

## Arquitectura requerida

```text
room_operations_core.py       # puro, JSON-compatible
        |
freecad_room_operations.py    # FreeCAD, sin GUI pesada
        |
commands/common_rooms.py      # registro/wrappers pequenos
```

Registrar los mismos command IDs desde FA/ElectricCR mediante helper idempotente.
No registrar dos implementaciones.

## Pruebas minimas futuras

- Space unico.
- Area legacy unica.
- Space + Area: Space gana.
- dos Spaces: AMBIGUOUS.
- NOT_FOUND.
- Info read-only.
- Naming conserva UID/Base/geometria.
- Undo/Redo.
- guardar/reabrir.
- FA sin regresion.
- ElectricCR funciona sin FA activo.
- HVACSpace.BaseSpace sigue resolviendo.
- SubArea sigue excluida.
- `Arch_Space` verificado en FreeCAD real.

## Primera implementacion Codex AUTORIZADA

Implementar solamente:
1. tres comandos funcionales comunes;
2. guia;
3. registro desde FA y ElectricCR;
4. pruebas puras + MCP;
5. sin modificar FCStd originales.

## Fuera de alcance

- no migrar Areas;
- no crear Space automaticamente;
- no asignar elementos al Space;
- no reescribir productores;
- conservar y registrar `PoligonosRecintosDesdeArchWalls.FCMacro` en ElectricCR;
- no reorganizar arbol;
- no iniciar refactor de dispositivo electromecanico;
- no commit/push salvo instruccion.

## Instruccion de ejecucion Codex

La implementacion esta autorizada por el usuario.

Codex debe:
1. leer `AGENTS.md` y las Skills aplicables;
2. leer este `TAREA_ACTUAL.md` y `BARRA_COMUN_ESPACIOS_RECINTOS.md`;
3. diagnosticar codigo y barras actuales antes de modificar;
4. comprobar mediante MCP el command ID nativo de Space en FreeCAD 1.1.3;
5. implementar solo el alcance v0.1;
6. reutilizar `CRBIMCore.RoomResolver`;
7. registrar la barra/comandos desde FA y ElectricCR sin duplicar logica;
8. preservar `PoligonosRecintosDesdeArchWalls.FCMacro` exactamente como productor funcional y mantenerlo visible en ElectricCR;
9. usar documento temporal para pruebas y no modificar FCStd originales;
10. actualizar `RESULTADO_CODEX.md`, `ESTADO_PROYECTO.md` y memoria reusable correspondiente;
11. detenerse sin commit/push y sin iniciar v0.2.

## Cierre comprobado - 2026-09-02

La v0.1 fue implementada y verificada en FreeCAD 1.1.3 revision 20260725.

- `Arch_Space` fue confirmado como command ID nativo; no existe `BIM_Space`.
- Los cuatro comandos comunes usan una sola implementacion y registro
  idempotente desde FA y ElectricCR.
- Las pruebas obligatorias de resolucion, lectura, naming, Undo/Redo,
  guardado/reapertura, HVAC/SubArea y no duplicacion aprobaron.
- Los smokes de FA y del productor poligonal aprobaron.
- La barra fue inspeccionada visualmente en ambos Workbenches.
- No se modificaron modelos originales, no se inicio v0.2 y no hubo commit/push.

Tarea cerrada. Una fase posterior requiere autorizacion nueva.
