# Sesion FreeCAD - correccion Aplicar en cambiar tipo de puerta

Fecha/hora: 2026-08-13 12:58:39 -06:00  
Equipo: DESKTOP-5586S7P  
Rama/commit: `agent/respaldo-electriccr-2026-08-10` / `707a0fc`  
Estado: `CORREGIDO / COMPILADO / PROBADO_GUI / VERIFICADO_MCP`

## Problema

En `FA Cambiar tipo de puerta`, seleccionar `Glass door` y pulsar `Aplicar`
no cerraba el dialogo ni ejecutaba el cambio.

## Causa y solucion

`QDialogButtonBox.Apply` usa `ApplyRole` y no emite la señal
`QDialogButtonBox.accepted`. Se sustituyo esa conexion por
`apply_button.clicked.connect(self.accept)`.

Se agrego una prueba GUI especifica que crea el dialogo en FreeCAD, pulsa el
boton `Aplicar` y exige el resultado `QDialog.Accepted`.

## Resultado y pruebas

- FacilArquitecturaWB `0.13.1`, build `2026.08.13.2`.
- 148/148 pruebas Python aprobadas.
- `compileall` y `package.xml` aprobados.
- Smoke GUI del clic en `Aplicar`: aprobado en FreeCAD 1.1.3.
- Prueba integral BIM de tres puertas: aprobada otra vez, incluidos tipo, identidad,
  host, corte, regeneracion, rechazos y persistencia.
- Workbench recargado en vivo y version/build comprobados por MCP.

## Seguridad

`La_Cruz_Versión_2_1` permanecio abierto, activo y sin guardar. Los documentos
temporales de prueba se cerraron y FreeCAD no se cerro.

## Siguiente paso

Seleccionar una puerta del proyecto, elegir `Glass door` y pulsar `Aplicar`
para la validacion visual manual.
