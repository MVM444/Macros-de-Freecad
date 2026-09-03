"""Comando preliminar FA Crear clavadores/correas BIM desde Sketch.

Nombre: cmd_create_purlins_bim.py
Proposito: crear clavadores BIM usando un Sketch 3D o lineas 2D proyectadas a cubierta; en modo proyectado usa un Arch Frame por faldon.
Funcion principal: planificar sin escribir, reemplazar solo resultados propios y crear perfil C + Frames por faldon.
FreeCAD objetivo: 1.1.3.
Version: 0.2.0-preMCP
Fecha y hora: 2026-08-30 15:55 America/Costa_Rica

Instrucciones de mantenimiento:
- NO registrar desde InitGui.py antes de probar orientacion de Frame/perfil C en FreeCAD real.
- `source_3d` requiere un unico Sketch de paths ya espaciales.
- `project_plan_to_gable` requiere Sketch de clavadores 2D + Sketch rectangular de cubierta.
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
    selected_sketches,
    select_results,
)
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import msg
from ..core.roof_bim_utils import (
    create_purlins_from_plan,
    plan_projected_purlins_from_sketch,
    plan_purlins_from_sketch,
    plan_roof_from_sketch,
    remove_previous_component,
)


def _resolve_projection_sources(sketches, roof_params):
    if len(sketches) != 2:
        raise UserFacingError(
            "Modo project_plan_to_gable: seleccione exactamente el Sketch 2D de clavadores y el Sketch cerrado de cubierta."
        )
    roof_candidates = []
    for sketch in sketches:
        try:
            plan_roof_from_sketch(sketch, params=roof_params)
            roof_candidates.append(sketch)
        except Exception:
            pass
    if len(roof_candidates) != 1:
        raise UserFacingError(
            "No se pudo identificar de forma inequivoca el Sketch de cubierta entre los dos Sketches seleccionados."
        )
    roof_sketch = roof_candidates[0]
    purlin_sketch = sketches[0] if sketches[1] is roof_sketch else sketches[1]
    return purlin_sketch, roof_sketch


class CommandClass:
    CommandName = "FA_CreatePurlinsFromSketch"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Clavadores BIM desde Sketch [pre-MCP]",
            "ToolTip": "Crear clavadores/correas Arch Frame desde paths 3D o desde lineas 2D proyectadas a una cubierta a dos aguas.",
        }

    def Activated(self):  # noqa: N802
        doc = None
        opened = False
        try:
            selection = current_selection()
            sketches = selected_sketches(selection)
            prefs = FreeCAD.ParamGet(
                "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/RoofSystem/Purlins"
            )
            layout_mode = prefs.GetString("layout_mode", "project_plan_to_gable")
            purlin_params = {
                "profile_type": prefs.GetString("profile_type", "C"),
                "profile_width_mm": prefs.GetFloat("profile_width_mm", 50.0),
                "profile_height_mm": prefs.GetFloat("profile_height_mm", 100.0),
                "profile_thickness_mm": prefs.GetFloat("profile_thickness_mm", 2.0),
                "layout_mode": layout_mode,
                "align": prefs.GetBool("align", True),
                "rotation_deg": prefs.GetFloat("rotation_deg", 0.0),
                "fuse": prefs.GetBool("fuse", False),
                "ifc_type": prefs.GetString("ifc_type", "Beam"),
            }
            roof_prefs = FreeCAD.ParamGet(
                "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/RoofSystem/Roof"
            )
            roof_params = {
                "roof_type": roof_prefs.GetString("roof_type", "gable"),
                "slope_deg": roof_prefs.GetFloat("slope_deg", 20.0),
                "thickness_mm": roof_prefs.GetFloat("thickness_mm", 50.0),
                "overhang_mm": roof_prefs.GetFloat("overhang_mm", 600.0),
                "gable_edge_indices": parse_gable_edge_indices(
                    roof_prefs.GetString("gable_edge_indices", "")
                ),
            }
            roof_sketch = None
            if layout_mode == "project_plan_to_gable":
                purlin_sketch, roof_sketch = _resolve_projection_sources(sketches, roof_params)
                plan = plan_projected_purlins_from_sketch(
                    purlin_sketch,
                    roof_sketch,
                    purlin_params=purlin_params,
                    roof_params=roof_params,
                )
            elif layout_mode == "source_3d":
                if len(sketches) != 1:
                    raise UserFacingError("Modo source_3d: seleccione exactamente un Sketch de clavadores.")
                purlin_sketch = sketches[0]
                plan = plan_purlins_from_sketch(purlin_sketch, params=purlin_params)
            else:
                raise UserFacingError("layout_mode debe ser source_3d o project_plan_to_gable.")

            doc = document_for_source(purlin_sketch)
            opened = open_transaction(doc, "FA Clavadores BIM")
            level = ensure_target_level(doc, selection)
            remove_previous_component(doc, purlin_sketch, "purlins")
            frames = create_purlins_from_plan(
                doc,
                level,
                purlin_sketch,
                plan,
                roof_source_sketch=roof_sketch,
            )
            doc.recompute()
            finish_transaction(doc, opened, commit=True)
            opened = False
            select_results(frames)
            msg(
                "FA Clavadores BIM: %d elementos | modo=%s | Level: %s"
                % (plan["count"], plan.get("layout_mode", layout_mode), level.Label)
            )
        except Exception as exc:
            if doc is not None:
                finish_transaction(doc, opened, commit=False)
            handle_command_exception("FA Clavadores BIM", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    """Registro disponible para la fase posterior a MCP; no invocar aun desde InitGui.py."""
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
