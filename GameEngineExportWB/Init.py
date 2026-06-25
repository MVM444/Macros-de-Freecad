"""GameEngineExportWB bootstrap module

Descripcion rapida: estructura base para el workbench de exportacion hacia Castle Game Engine.
Fecha y hora: 2025-10-13 13:54 UTC.
Instrucciones clave:
- Mantener escala mm a m y rotacion global -90 grados en X en la logica futura.
- No usar acentos ni caracteres especiales en cadenas tecnicas.
- Mostrar logs con prefijo [GAMEEXPORT].
- Recordar la meta final de integrar macros funcionales en un workbench FreeCAD.

Este modulo solo prepara el paquete sin cargar componentes pesados.
"""

from . import InitGui  # noqa: F401  # mantener import minimo para FreeCAD
