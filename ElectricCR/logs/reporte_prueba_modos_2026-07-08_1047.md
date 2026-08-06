# Reporte de prueba de modos ElectricCR

Fecha: 2026-07-08 10:47 Costa Rica

## Objetivo

Probar una interfaz compacta por modos sin dividir ElectricCR en varios
workbenches y sin ocultar el acceso completo a las macros desde los menus.

## Configuracion probada

- Modo de interfaz: `modes_prototype`.
- Selector principal: lista desplegable en la barra `ElectricCR`.
- Panel acoplable: `ElectricCR Modos`, disponible desde menu.
- Barras permanentes: `Objetos` y `Draft compacto`.
- Modos manuales:
  - `Areas`: muestra `Areas`.
  - `Iluminacion`: muestra `Iluminacion`.
  - `Tomacorrientes`: muestra `Tomacorrientes`.
  - `Conexiones`: muestra `Conectar`, `Cajas` y `Tableros`.
  - `Personalizado`: lee su seleccion desde `custom_mode_toolbars`.

## Resultado de validacion

- `python -m py_compile`: correcto.
- `python -m json.tool ElectricCR/config.json`: correcto.
- `python ElectricCR/tests/simulate_mode_interface.py`: correcto.

El simulador confirmo que:

- Hay 5 modos en la lista desplegable.
- `Objetos` permanece visible en todos los modos.
- `Draft compacto` permanece visible en todos los modos.
- `Conexiones` incluye `Conectar`, `Cajas` y `Tableros`.
- `Personalizado` muestra la seleccion configurable actual.
- Si falta una barra esperada, se reporta como `missing` sin romper la carga.

## Pendiente

La prueba fue automatizada con stubs de FreeCAD. Falta una revision visual
dentro de FreeCAD para verificar posicion final, iconos disponibles y comodidad
real de uso con proyectos existentes.
