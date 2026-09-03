# CRBIMCore

Version inicial: `0.1.0`

`CRBIMCore` es el paquete neutral compartido para contratos BIM comunes. No fusiona los Workbenches y no contiene comandos de interfaz.

## Barra comun Espacios y Recintos v0.1

Validada en FreeCAD `1.1.3`, revision `20260725`, el 2026-09-02.

Los command IDs comunes son `CRBIM_SelectRoom`, `CRBIM_RoomInfo`,
`CRBIM_NameRoom` y `CRBIM_RoomGuide`. Facil Arquitectura y ElectricCR llaman
al mismo registro idempotente en `CRBIMCore.commands.common_rooms`; no existen
copias por Workbench.

La implementacion mantiene tres capas:

```text
room_operations_core.py       nucleo puro JSON-compatible
freecad_room_operations.py    adaptador FreeCAD sin GUI
commands/common_rooms.py      wrappers GUI y registro pequeno
```

El command ID nativo comprobado para crear un Space es `Arch_Space`; la barra
comun no lo duplica. Space es la identidad fisica canonica y una Area legacy
valida es fallback. `AMBIGUOUS` y `NOT_FOUND` nunca aplican cambios.

`CRBIM_NameRoom` cambia unicamente `Label` dentro de una transaccion y conserva
`Name`, UID/ID de recinto, Base, Shape, Placement y jerarquia. La preferencia de
etiquetas duplicadas se habilita solo durante la asignacion y se restaura aun
si ocurre un error.

## RoomResolver fase 1

La primera funcionalidad validada es un resolver de identidad de recinto estrictamente read-only.

Arquitectura:

```text
room_resolver_core.py       nucleo puro JSON-compatible
        ^
        |
freecad_room_adapter.py     traduccion read-only de objetos FreeCAD
        ^
        |
consumidores de disciplina  adopcion incremental
```

`room_resolver_core.py` no importa `FreeCAD`, `FreeCADGui`, Qt, Draft, Arch ni un Workbench. `freecad_room_adapter.py` tampoco importa GUI o Qt y trabaja por inspeccion de objetos existentes.

## Contrato de resultado

Cada resolucion devuelve un diccionario serializable con:

- `status`: `RESOLVED`, `AMBIGUOUS` o `NOT_FOUND`;
- `source_kind`: `NATIVE_SPACE` o `LEGACY_AREA` cuando se resuelve;
- `room_uid`, `room_id`, `name`, `object_name` y `level`;
- `area_m2`, `centroid_mm` y `polygon_mm`;
- `confidence`, `is_native_space` e `is_legacy`;
- `diagnostics` y, en ambiguedad, `alternatives`.

El objeto FreeCAD nunca forma parte del contrato serializable.

## Prioridad y seguridad

1. Un `Arch/BIM Space` nativo valido tiene prioridad sobre una Area heredada que contiene el mismo punto.
2. Si no existe Space, se admite una Area fisica heredada reconocida.
3. Dos Spaces plausibles producen `AMBIGUOUS`; el resolver no elige el mas pequeno.
4. Ausencia de candidato produce `NOT_FOUND`, no una excepcion.
5. Un Level explicito puede desambiguar; un candidato sin Level solo se usa como fallback cuando no existe coincidencia exacta.
6. Una referencia explicita se resuelve por `object_name` sin ranking geometrico.

## Candidatos FreeCAD

El adaptador reconoce como Space nativo cualquiera de estas evidencias, sin exigir propiedades `FA_*`:

- `TypeId=Arch::Space` cuando exista;
- `IfcType=Space`;
- `Proxy.Type=Space`.

Los fallbacks heredados requieren geometria plana valida y metadatos, por ejemplo:

- `ElectricCRTipo=Area`;
- `FA_RectangularAreaAnalysis`;
- `AreaPorClick`;
- `FA_PolygonalRoomsFromArchWalls` / `FA_Role=room_polygon`;
- Draft cerrado con cara, area y metadatos de recinto.

El nombre del grupo `FA_RectangularAreas` por si solo no convierte un objeto en candidato.

## HVAC y SubArea

- `HVACSpace.BaseSpace` se sigue hasta el Space o Area fisica real.
- Un `HVACSpace` sin `BaseSpace`, incluso convertido y con Shape propio, devuelve `NOT_FOUND` y no se incorpora como recinto arquitectonico.
- `SubArea` se excluye de la identidad fisica comun.

## API publica de fase 1

Nucleo puro:

- `normalize_candidate(...)` / `normalize_candidates(...)`;
- `resolve_room_for_point(candidates, point_mm, ...)`;
- `resolve_room_reference(candidates, object_name)`;
- `resolve_room_for_object(candidates, subject, ...)`.

Adaptador FreeCAD:

- `collect_room_candidates(doc, ...)`;
- `resolve_room_for_point(doc, point_mm, ...)`;
- `resolve_room_reference(doc, reference)`;
- `resolve_room_for_object(doc, obj, ...)`.

Todas las operaciones son de lectura. No crean UID, propiedades, objetos, transacciones ni migraciones.

## Validacion 2026-09-01

- 11 pruebas puras aprobadas fuera de FreeCAD.
- Importacion del adaptador fuera de FreeCAD aprobada.
- Smoke en FreeCAD 1.1.3: 8 candidatos, prioridad Space sobre Area, fallbacks heredados, ambiguedad, `NOT_FOUND`, HVAC enlazado, HVAC convertido excluido, SubArea excluida y resolucion por objeto.
- Firma de 17 objetos identica antes/despues de resolver.
- Guardar/cerrar/reabrir mantuvo el mismo resultado.
- Regresion de Espacios FA: E2E real aprobado y 22 contratos focales aprobados.

## Adopcion ElectricCR fase 2A

ElectricCR es el primer consumidor disciplinario validado. Su adaptador
`ElectricCR.electriccr.lighting.room_calculation` enumera recintos para el
calculo de iluminacion sin incorporar referencias FreeCAD al contrato neutral.

- Space-only y Area-legacy-only producen registros compatibles de calculo.
- Space + Area superpuestos conserva solo el Space autoritativo.
- Ambiguedad se excluye y diagnostica; ausencia conserva `NOT_FOUND`.
- La adopcion no escribe sobre Spaces ni modifica elementos electricos.

Esta adopcion no cambia el contrato publico de `CRBIMCore 0.1.0`.

## Fuera de alcance

El nucleo no migra HVAC ni MEPWorkbenchCR, no agrega UI y no escribe relaciones
`Space`. ElectricCR adopta solamente la capa de calculo de iluminacion en fase
2A; las demas disciplinas requieren fases posteriores autorizadas por separado.
