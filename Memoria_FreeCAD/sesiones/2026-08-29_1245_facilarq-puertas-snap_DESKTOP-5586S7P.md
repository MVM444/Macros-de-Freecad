# Sesion FacilArquitecturaWB - puertas BIM y snap lateral

Fecha: 2026-08-29
Equipo: DESKTOP-5586S7P
FreeCAD: 1.1.3 revision 20260725
Workbench: FacilArquitecturaWB 0.14.8 / build 2026.08.29.1
Estado: verificado_mcp

## Diagnostico

El documento 1416 contiene 10 ejes de puerta y un solo `Arch Wall` con 20
segmentos. El resolvedor excluia el objeto Wall completo al descartar el segmento
anfitrion; por ello no veia paredes laterales que pertenecian al mismo Wall. Tambien
se comprobo que FreeCAD 1.1.3 conserva callbacks de comandos Python durante hot
reload porque no dispone de `removeCommand`.

## Cambios

- descomposicion virtual por segmento del mismo Wall en `opening_utils.py`;
- `FA_CornerWall` como nombre estable, no enlace `MoveWithHost` adicional;
- `ReloadableCommandProxy` para `FA_CreateDoorsFromSketch`;
- normalizacion de textos de Spreadsheet en tablas de puertas y ventanas;
- regresiones BIM actualizadas al contrato `FA_TargetLevel`.

## Pruebas

- documento 1416 en copia segura: 10 puertas, snaps en indices 1/6/8, ancho, host y
  cortes correctos;
- modelo controlado: near/far/ambiguous, hoja a 90 grados, reejecucion, Undo/Redo y
  reapertura;
- siete pruebas MCP integrales: todas aprobadas;
- suite pura: 220/221; falla preexistente de rotulos de recintos;
- `compileall`: aprobado.

El hot restart ejecutado desde MCP cerro FreeCAD inesperadamente. Se inicio de nuevo
la misma version y se uso el dialogo nativo de recuperacion; el documento fue
`Recuperado con exito` con 137 objetos, archivo asociado y `isTouched=False`. El
Workbench se cargo luego de forma normal y confirmo build 2026.08.29.1, comandos y
proxy. FreeCAD permanece abierto.

## Pendiente separado

Revisar en una tarea independiente la duplicacion historica de desplazamiento que
puede producir `FA_HostWall` como `PropertyLink` adicional a `Hosts`.
