"""FacilArquitecturaWB package.

Descripcion: paquete base del workbench Facil Arquitectura.
Objetivo: publicar version y build sin dependencias de Codex/MCP.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 23:40 UTC-06:00.
Version: 0.9.0.
Instrucciones de mantenimiento: mantener este paquete pequeno y modular.
"""

from .core.constants import BUILD_ID as __build__
from .core.constants import VERSION as __version__
