"""Comando preliminar FA Crear cerchas BIM desde Sketch.

Nombre: cmd_create_trusses_bim.py
Proposito: crear un datum Arch Axis y una sola celosia/Truss BIM maestra repetida por sus posiciones.
Funcion principal: planificar primero con roof_system_core y materializar dentro de un Level nativo.
FreeCAD objetivo: 1.1.3.
Version: 0.2.0-preMCP
Fecha y hora: 2026-08-30 16:22 America/Costa_Rica

Instrucciones de mantenimiento:
- NO importar ni registrar desde InitGui.py antes de la validacion FreeCAD/MCP.
- Conservar el Sketch como fuente y el Arch Axis como datum documental visible.
- Reemplazar solamente resultados FA_RoofSystem del mismo Sketch.
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
    require_single_sketch,
    select_results,
)
from ..core.command_errors import handle_command_exception
from ..core.project_structure import msg
from ..core.roof_bim_utils import (
    create_truss_axis_family,
    create_trusses_from_plan,
    plan_trusses_from_sketch,
    remove_previous_component,
)


class CommandClass:
    CommandName = "FA_CreateTrussesFromSketch"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Cerchas BIM desde Sketch [pre-MCP]",
            "ToolTip": "Crear un Axis BIM y una cercha maestra repetida en las posiciones definidas por las lineas de un Sketch.",
        }

    def Activated(self):  # noqa: N802
        doc = None
        opened = False
        try:
            selection = current_selection()
            sketch = require_single_sketch(selection, "los ejes de cerchas")
            doc = document_for_source(sketch)
            prefs = FreeCAD.ParamGet(
                "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/RoofSystem/Trusses"
            )
            params = {
                "slant_type": prefs.GetString("slant_type", "Double"),
                "pitch_deg": prefs.GetFloat("pitch_deg", 20.0),
                "height_start_mm": prefs.GetFloat("height_start_mm", 150.0),
                "derive_height_end_from_pitch": prefs.GetBool("derive_height_end_from_pitch", True),
                "strut_height_mm": prefs.GetFloat("strut_height_mm", 50.0),
                "strut_width_mm": prefs.GetFloat("strut_width_mm", 50.0),
                "rod_type": prefs.GetString("rod_type", "Square"),
                "rod_direction": prefs.GetString("rod_direction", "Forward"),
                "rod_size_mm": prefs.GetFloat("rod_size_mm", 25.0),
                "rod_sections": prefs.GetInt("rod_sections", 6),
                "rod_end": prefs.GetBool("rod_end", True),
                "rod_mode": prefs.GetString("rod_mode", "/|\\|/|\\"),
            }
            plan = plan_trusses_from_sketch(sketch, params=params)  # read-only validation first
            opened = open_transaction(doc, "FA Cerchas BIM")
            level = ensure_target_level(doc, selection)
            remove_previous_component(doc, sketch, "trusses")
            axis = create_truss_axis_family(
                doc,
                level,
                sketch,
                plan,
                extension_mm=prefs.GetFloat("axis_extension_mm", 500.0),
            )
            trusses = create_trusses_from_plan(doc, level, sketch, plan, axis_family=axis)
            doc.recompute()
            finish_transaction(doc, opened, commit=True)
            opened = False
            select_results([axis] + trusses)
            msg("FA Cerchas BIM: %d posiciones | 1 Truss + Axis | Level: %s" % (plan["count"], level.Label))
        except Exception as exc:
            if doc is not None:
                finish_transaction(doc, opened, commit=False)
            handle_command_exception("FA Cerchas BIM", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    """Registro disponible para la fase posterior a MCP; no invocar aun desde InitGui.py."""
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
