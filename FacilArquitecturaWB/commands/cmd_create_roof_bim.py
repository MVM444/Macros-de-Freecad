"""Comando preliminar FA Crear cubierta BIM desde Sketch.

Nombre: cmd_create_roof_bim.py
Proposito: crear Arch Roof nativo desde un Sketch cerrado rectangular de cubierta.
Funcion principal: traducir pendiente/alero/espesor a listas por borde de Arch Roof.
FreeCAD objetivo: 1.1.3.
Version: 0.1.0-preMCP
Fecha y hora: 2026-08-30 12:32 America/Costa_Rica

Instrucciones de mantenimiento:
- NO registrar desde InitGui.py antes de la validacion FreeCAD/MCP.
- Mantener el Sketch cerrado como Base directa de Roof.
- En huellas cuadradas exigir direccion de hastial explicita; no adivinar.
"""

from __future__ import annotations

import FreeCAD
import FreeCADGui

from .roof_command_common import (
    current_selection,
    document_for_source,
    ensure_target_level,
    finish_transaction,
    open_transaction,
    parse_gable_edge_indices,
    require_single_sketch,
    select_results,
)
from ..core.command_errors import handle_command_exception
from ..core.project_structure import msg
from ..core.roof_bim_utils import create_roof_from_plan, plan_roof_from_sketch, remove_previous_component


class CommandClass:
    CommandName = "FA_CreateRoofFromSketch"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Cubierta BIM desde Sketch [pre-MCP]",
            "ToolTip": "Crear una cubierta Arch Roof a dos aguas desde un Sketch cerrado.",
        }

    def Activated(self):  # noqa: N802
        doc = None
        opened = False
        try:
            selection = current_selection()
            sketch = require_single_sketch(selection, "el contorno de cubierta")
            doc = document_for_source(sketch)
            prefs = FreeCAD.ParamGet(
                "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/RoofSystem/Roof"
            )
            params = {
                "roof_type": prefs.GetString("roof_type", "gable"),
                "slope_deg": prefs.GetFloat("slope_deg", 20.0),
                "thickness_mm": prefs.GetFloat("thickness_mm", 50.0),
                "overhang_mm": prefs.GetFloat("overhang_mm", 600.0),
                "gable_edge_indices": parse_gable_edge_indices(
                    prefs.GetString("gable_edge_indices", "")
                ),
            }
            plan = plan_roof_from_sketch(sketch, params=params)  # read-only validation first
            opened = open_transaction(doc, "FA Cubierta BIM")
            level = ensure_target_level(doc, selection)
            remove_previous_component(doc, sketch, "roof")
            roof = create_roof_from_plan(doc, level, sketch, plan)
            doc.recompute()
            finish_transaction(doc, opened, commit=True)
            opened = False
            select_results([roof])
            msg(
                "FA Cubierta BIM: pendiente %.2f deg | hastiales=%s | Level: %s"
                % (
                    plan["parameters"]["slope_deg"],
                    plan["native"]["gable_edge_indices"],
                    level.Label,
                )
            )
        except Exception as exc:
            if doc is not None:
                finish_transaction(doc, opened, commit=False)
            handle_command_exception("FA Cubierta BIM", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    """Registro disponible para la fase posterior a MCP; no invocar aun desde InitGui.py."""
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
