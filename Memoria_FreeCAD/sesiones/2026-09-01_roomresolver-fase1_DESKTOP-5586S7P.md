# Sesion FreeCAD - RoomResolver comun fase 1

Fecha: 2026-09-01 America/Costa_Rica
Equipo: `DESKTOP-5586S7P`
FreeCAD: `1.1.3`, revision `20260725`
Proyecto: `Programacion en FreeCAD`

## Decision reusable

La identidad fisica de recinto se resuelve en un nucleo neutral:

1. `Arch/BIM Space` nativo;
2. Area heredada con geometria y metadatos suficientes;
3. `NOT_FOUND`.

Dos candidatos plausibles producen `AMBIGUOUS`; no se elige por menor area. `HVACSpace.BaseSpace` es un enlace hacia la fuente fisica. HVAC convertido sin enlace y SubArea no son identidades arquitectonicas.

## Estado

- `programado`: `CRBIMCore 0.1.0`, nucleo puro, adaptador read-only, pruebas y documentacion.
- `compilado`: cuatro archivos Python sin errores.
- `probado`: 11/11 pruebas puras, importacion fuera de FreeCAD y 22/22 contratos FA.
- `verificado_mcp`: smoke de 17 objetos/8 candidatos, firma sin cambios, guardar/reabrir estable y E2E FA aprobado.
- `verificado_visual`: no aplica; la fase no produce ni modifica geometria visible.

No se modificaron modelos originales ni consumidores ElectricCR/HVAC/MEP. La adopcion por disciplinas queda para una tarea posterior explicita.

Hashes SHA-256 de cierre:

- `room_resolver_core.py`: `9515118A01352D32B67A6D4714C93FEEC3828581F3D16C62E73220BDB62825B5`;
- `freecad_room_adapter.py`: `9789FE97DADEEE7DE34444BF927C3C2A70652768B6D3D01374B08740AF2018E1`;
- `freecad_room_resolver_smoke.py`: `C34306F01AC7656812328E8BF917170825EF9E47C846CCB3B1ECFCA92BBF9DC8`.
