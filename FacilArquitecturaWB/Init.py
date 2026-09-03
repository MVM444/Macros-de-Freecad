"""FacilArquitecturaWB bootstrap.

Descripcion: arranque minimo del workbench Facil Arquitectura.
Objetivo: descubrir y registrar el Workbench sin ejecutar reconstruccion BIM.
FreeCAD objetivo: 1.1.3.
Fecha: 2026-08-29.
Version: 0.14.8.
Instrucciones de mantenimiento: no cargar logica pesada aqui; FreeCAD importa este
modulo al descubrir el workbench.
"""

from . import InitGui  # noqa: F401
