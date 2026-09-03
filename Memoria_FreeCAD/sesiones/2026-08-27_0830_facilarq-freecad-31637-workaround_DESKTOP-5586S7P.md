# Sesion FreeCAD - workaround DXF WaitCursor #31637

Fecha: 2026-08-27 America/Costa_Rica
Equipo: DESKTOP-5586S7P
Proyecto: Macros-de-Freecad / FacilArquitecturaWB
FreeCAD: 1.1.3 revision 20260725
Version FA: 0.14.4 / build 2026.08.27.1
Estado: PROGRAMADO / COMPILADO / PROBADO / VERIFICADO_MCP / PENDIENTE_USUARIO

## Cambio

- nueva utilidad `core/freecad_compat.py`;
- deteccion estructural AST/bytecode con estados `affected`, `not_affected` y
  `unknown`;
- monkeypatch limitado a una llamada `importDXF.insert()` y restaurado en
  `finally`;
- desactivacion automatica cuando desaparece el patron antiguo;
- sin cambios en FreeCAD instalado ni otros Workbenches.

## Pruebas

- `compileall`: aprobado;
- 161/161 pruebas Python: aprobadas;
- excepcion controlada en FreeCAD real: funciones restauradas exactamente;
- tres DWG reales: 139/140 cada uno, 15 textos, 15 capas, 53 links;
- DXF real: 137/138, 15 textos, 13 capas, 53 links;
- Puertas=11 y Ventanas=15;
- cero muestras de WaitCursor posterior;
- pan, zoom, seleccion y teclado respondieron;
- preferencias Draft y funciones nativas restauradas despues de cada corrida.
- los cuatro documentos temporales se cerraron sin guardar; FreeCAD quedo
  abierto y sin documentos.

## Nota de recarga

Una primera prueba mediante hot-reload conservo una instancia antigua del comando
y reprodujo el fallo. Se cerro solo el documento de prueba, se reinicio FreeCAD y
se cargo 0.14.4 desde cero. Las cuatro pruebas finales corresponden a esa sesion
limpia. Para validar esta actualizacion, reiniciar FreeCAD antes de probar.

## Pendiente

El usuario debe realizar la importacion manual real y confirmar respuesta
inmediata y contenido. No declarar resuelta la tarea antes de esa validacion.

Git: rama `agent/respaldo-electriccr-2026-08-10`, commit base `707a0fc`; sin
commit ni push, con cambios previos ajenos en el worktree.
