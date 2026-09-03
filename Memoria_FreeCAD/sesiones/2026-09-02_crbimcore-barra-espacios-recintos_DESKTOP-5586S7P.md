# CRBIMCore - barra comun Espacios y Recintos v0.1

Fecha: 2026-09-02 America/Costa_Rica
Equipo: DESKTOP-5586S7P
FreeCAD: 1.1.3 revision 20260725

## Resultado reusable

- `Arch_Space` es el command ID nativo disponible; `BIM_Space` no existe en
  esta instalacion.
- Una operacion comun de recintos funciona bien separando nucleo puro,
  adaptador FreeCAD sin GUI y wrappers pequenos de comandos.
- Los Workbenches deben registrar exactamente los mismos command IDs mediante
  un helper idempotente, no copiar clases.
- FreeCAD puede reutilizar una `QToolBar` con el mismo titulo entre Workbenches.
  Para mantener el orden visual es necesario reordenar las acciones existentes
  al activar cada Workbench, sin volver a registrar los comandos.
- Para permitir Labels repetidos sin cambiar la preferencia del usuario, puede
  habilitarse temporalmente `DuplicateLabels` durante la asignacion y restaurar
  su valor exacto en `finally`.
- `PoligonosRecintosDesdeArchWalls.FCMacro` es un productor geometrico
  transversal: sus Draft Wires sirven a Areas, cielorrasos y consumidores 2D.
  No debe clasificarse como legacy ni ocultarse.

## Validacion

Space, Area, prioridad Space, AMBIGUOUS, NOT_FOUND, Info read-only, naming,
Undo/Redo, persistencia, HVAC/SubArea, registro doble, barras FA/ElectricCR y
productor poligonal aprobaron mediante MCP. No se modificaron FCStd originales.
