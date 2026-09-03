"""FacilArquitecturaWB package.

Descripcion: paquete base del workbench Facil Arquitectura.
Objetivo: publicar version y build sin dependencias de Codex/MCP.
FreeCAD objetivo: 1.1.3.
Fecha: 2026-09-01.
Version: 0.14.11.
Instrucciones de mantenimiento: mantener este paquete pequeno y modular.
"""

from .core.constants import BUILD_ID as __build__
from .core.constants import VERSION as __version__
