"""FA Stair Between Slabs command.

Nombre: cmd_stair_between_slabs.py
Proposito: crear una escalera BIM Arch nativa entre dos losas usando un Wire/Sketch en L.
Funcion principal: diagnosticar la seleccion, planificar con fa_stair_core y materializar mediante
stair_freecad_adapter; no corta la losa superior en esta primera version.
Mantenimiento: conservar este comando como capa GUI delgada; la geometria numerica pertenece al
nucleo independiente y la creacion FreeCAD al adaptador.
Version: 0.2.0
Fecha y hora: 2026-09-09 15:20 America/Costa_Rica
FreeCAD objetivo: 1.1.3
"""

from __future__ import annotations

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from .. import i18n
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.fa_stair_core import StairPlanError, plan_angled_stair
from ..core.project_structure import msg, warn
from ..core.reloadable_command import ReloadableCommandProxy
from ..core.stair_freecad_adapter import analyze_selection, create_native_stair


PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/StairBetweenSlabs"


class StairOptionsDialog(QtWidgets.QDialog):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.params = FreeCAD.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle(i18n.bi("FA Escalera entre losas", "FA Stair between slabs"))
        self.setMinimumWidth(480)
        layout = QtWidgets.QVBoxLayout(self)

        lower = context["lower_info"]
        upper = context["upper_info"]
        info = QtWidgets.QLabel(
            i18n.bi(
                "Losa inferior: %s (Z sup. %.1f mm)\nLosa superior: %s (Z sup. %.1f mm)\n"
                "El sentido del Wire define el ascenso.",
                "Lower slab: %s (top Z %.1f mm)\nUpper slab: %s (top Z %.1f mm)\n"
                "The Wire direction defines the ascent.",
            )
            % (
                getattr(context["lower"], "Label", ""),
                lower["top_z"],
                getattr(context["upper"], "Label", ""),
                upper["top_z"],
            )
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QtWidgets.QFormLayout()
        self.width = self._spin("width_mm", 500.0, 5000.0, 50.0, 1000.0)
        self.target_riser = self._spin("target_riser_mm", 100.0, 250.0, 5.0, 175.0)
        self.structure = self._spin("structure_thickness_mm", 50.0, 500.0, 10.0, 150.0)
        self.reverse = QtWidgets.QCheckBox(i18n.bi("Invertir sentido del Wire", "Reverse Wire direction"))
        self.reverse.setChecked(self.params.GetBool("reverse", False))
        self.create_plan = QtWidgets.QCheckBox(i18n.bi("Crear representacion PLAN 2D", "Create PLAN 2D representation"))
        self.create_plan.setChecked(self.params.GetBool("create_plan", True))
        form.addRow(i18n.bi("Ancho", "Width"), self.width)
        form.addRow(i18n.bi("Contrahuella objetivo", "Target riser"), self.target_riser)
        form.addRow(i18n.bi("Espesor estructura", "Structure thickness"), self.structure)
        form.addRow("", self.reverse)
        form.addRow("", self.create_plan)
        layout.addLayout(form)

        note = QtWidgets.QLabel(
            i18n.bi(
                "Primera version integrada: usa Arch.makeStairs() como autoridad geometrica. "
                "La losa superior todavia no se corta automaticamente.",
                "First integrated version: Arch.makeStairs() remains the geometry authority. "
                "The upper slab is not cut automatically yet.",
            )
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _spin(self, key, minimum, maximum, step, default):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(1)
        spin.setSingleStep(step)
        spin.setSuffix(" mm")
        spin.setValue(self.params.GetFloat(key, default))
        return spin

    def options(self):
        values = {
            "width_mm": float(self.width.value()),
            "target_riser_mm": float(self.target_riser.value()),
            "structure_thickness_mm": float(self.structure.value()),
            "reverse": bool(self.reverse.isChecked()),
            "create_plan": bool(self.create_plan.isChecked()),
        }
        for key in ("width_mm", "target_riser_mm", "structure_thickness_mm"):
            self.params.SetFloat(key, values[key])
        self.params.SetBool("reverse", values["reverse"])
        self.params.SetBool("create_plan", values["create_plan"])
        return values


class CommandClass:
    CommandName = "FA_StairBetweenSlabs"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Escalera entre losas", "FA Stair between slabs"),
            "ToolTip": i18n.bi(
                "Crear una escalera Arch nativa entre dos losas a partir de un Wire/Sketch abierto de dos segmentos.",
                "Create a native Arch stair between two slabs from an open two-segment Wire/Sketch.",
            ),
            "Pixmap": ":/icons/Arch_Stairs.svg",
        }

    def Activated(self):  # noqa: N802
        doc = FreeCAD.ActiveDocument
        transaction_open = False
        try:
            if doc is None:
                raise RuntimeError(i18n.bi("No hay un documento activo.", "There is no active document."))
            context = analyze_selection(doc, FreeCADGui.Selection.getSelection())
            dialog = StairOptionsDialog(context, parent=FreeCADGui.getMainWindow())
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                msg("FA Escalera entre losas: operacion cancelada por el usuario.")
                return
            options = dialog.options()
            points = list(context["points"])
            if options["reverse"]:
                points.reverse()
            plan = plan_angled_stair(
                [(point.x, point.y, point.z) for point in points],
                context["lower_info"]["top_z"],
                context["upper_info"]["top_z"],
                width_mm=options["width_mm"],
                target_riser_mm=options["target_riser_mm"],
                landing_depth_mm=options["width_mm"],
            )
            for warning in plan["warnings"]:
                warn(warning)
            msg(
                "FA Escalera planificada | angulo %.1f deg | %d+descanso+%d | riser %.1f mm | tread %.1f/%.1f mm"
                % (
                    plan["geometry"]["turn_angle_deg"],
                    plan["steps"]["flight1_risers"],
                    plan["steps"]["flight2_risers"],
                    plan["steps"]["riser_mm"],
                    plan["steps"]["tread1_mm"],
                    plan["steps"]["tread2_mm"],
                )
            )
            doc.openTransaction("FA Escalera entre losas")
            transaction_open = True
            result = create_native_stair(
                doc,
                context,
                plan,
                structure_thickness_mm=options["structure_thickness_mm"],
                create_plan=options["create_plan"],
                railings_mode="hidden_native_freecad_1_1_3_multisegment",
                prevent_duplicate=True,
            )
            doc.recompute()
            doc.commitTransaction()
            transaction_open = False
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(result["master"])
            msg(
                "FA Escalera creada: %s | losa superior sin cortar | PLAN2D=%s | barandillas=%s"
                % (getattr(result["master"], "Label", "Stair"), bool(result["plan2d"]), result.get("railing_status", ""))
            )
        except StairPlanError as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception(
                i18n.bi("FA Escalera entre losas", "FA Stair between slabs"),
                UserFacingError(str(exc)),
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception(i18n.bi("FA Escalera entre losas", "FA Stair between slabs"), exc)

    def IsActive(self):  # noqa: N802
        return FreeCAD.ActiveDocument is not None


def register():
    command = ReloadableCommandProxy(
        __name__, class_name="CommandClass", command_name=CommandClass.CommandName
    )
    FreeCADGui.addCommand(command.CommandName, command)
    return command
