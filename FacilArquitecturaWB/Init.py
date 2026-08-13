"""FacilArquitecturaWB bootstrap.

Descripcion: arranque minimo del workbench Facil Arquitectura.
Objetivo: descubrir y registrar el Workbench sin ejecutar reconstruccion BIM.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 23:40 UTC-06:00.
Version: 0.9.0.
Instrucciones de mantenimiento: no cargar logica pesada aqui; FreeCAD importa este
modulo al descubrir el workbench.
"""

from . import InitGui  # noqa: F401
