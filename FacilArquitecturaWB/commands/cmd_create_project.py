"""FA_CreateProject command.

Descripcion: crea Building/Level nativos y solo los datos auxiliares necesarios.
Fecha y hora: 2026-08-27 16:28 UTC-06:00
Version: 0.2.0
Instrucciones: comando idempotente; no destruir trabajo del usuario.
"""

from __future__ import annotations

import os
import time

import FreeCAD
import FreeCADGui

from ..core.parameters import ensure_parameter_sheet
from ..core.command_errors import handle_command_exception
from ..core.bim_structure_utils import ensure_bim_structure
from ..core.project_structure import active_or_new_document, ensure_project_support_structure, msg

ICON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "facilarq.svg")).replace(
    os.sep, "/"
)
COMMAND_VERSION = str(int(time.time()))


class CommandClass:
    """FreeCAD command for creating the base Facil Arquitectura project."""

    CommandName = "FA_CreateProject_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Crear proyecto",
            "ToolTip": "Crear Edificio/Nivel BIM nativos y los datos auxiliares minimos de Facil Arquitectura.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            doc = active_or_new_document()
            spatial = ensure_bim_structure(doc)
            _doc, _root, groups = ensure_project_support_structure(doc, keys=("parameters",))
            ensure_parameter_sheet(doc, groups["parameters"])
            doc.recompute()
            msg(
                "FA_CreateProject completado: Building=%s | Level=%s | sin ramas legacy vacias."
                % (spatial["building"].Label, spatial["level"].Label)
            )
        except Exception as exc:
            handle_command_exception("FA Crear proyecto", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
