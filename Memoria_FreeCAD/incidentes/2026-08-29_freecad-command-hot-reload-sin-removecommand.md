# FreeCAD 1.1.3: comandos Python persistentes durante hot reload

Fecha: 2026-08-29
Equipo: DESKTOP-5586S7P
Estado: confirmado mediante MCP

## Sintoma

Despues de purgar y volver a importar un Workbench, un ID estable registrado con
`FreeCADGui.addCommand()` continuaba ejecutando una instancia Python de un modulo
anterior. Los archivos y `sys.modules` mostraban el build nuevo, pero el boton real
llamaba el callback viejo.

## Causa

FreeCAD 1.1.3 no expone `FreeCADGui.removeCommand`. Volver a ejecutar
`addCommand()` con el mismo ID no garantiza reemplazar el objeto Python que FreeCAD
conserva internamente.

## Patron validado

Registrar desde el primer arranque un proxy pequeno y estable. En `Activated()`,
`GetResources()` e `IsActive()` el proxy importa el modulo por nombre y crea/delega
a la clase vigente. De esta manera el objeto persistente no contiene la logica que
se desea recargar.

La regresion pura `tests/test_reloadable_command.py` reemplaza el modulo bajo el
mismo nombre y comprueba que el mismo proxy llama primero `First` y despues
`Second`. En FreeCAD limpio se encontro una instancia
`ReloadableCommandProxy('FA_CreateDoorsFromSketch', ...)` registrada y una sola
accion visible en `FA Aberturas BIM`.

## Precaucion

Un callback antiguo creado antes de introducir el proxy no se transforma por si
solo durante esa misma sesion. La garantia completa comienza en un arranque natural
que registre el proxy. No usar ciclos de borrar/recrear UI como sustituto de una API
de eliminacion de comandos que no existe.
