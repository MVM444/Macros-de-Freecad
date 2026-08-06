"""FA_CreateModularCeiling command.

Descripcion: crea cielo suspendido modular y reserva luminarias ElectricCR.
Fecha: 2026-07-26
Version: 0.2.0
"""

from __future__ import annotations

import os
import time

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from ..core.ceiling_utils import (
    collect_electriccr_luminaires,
    collect_rooms,
    create_modular_ceilings,
)
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import ensure_project_structure, msg


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "modular_ceiling.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))
PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/ModularCeiling"


class ModularCeilingDialog(QtWidgets.QDialog):
    def __init__(self, room_count, luminaire_count, selected_rooms, parent=None):
        super().__init__(parent)
        self.params = FreeCAD.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle("FA Cielo suspendido modular")
        self.setMinimumWidth(480)
        layout = QtWidgets.QVBoxLayout(self)
        source = "%d recintos %s | %d luminarias ElectricCR detectadas" % (
            room_count,
            "seleccionados" if selected_rooms else "detectados automaticamente",
            luminaire_count,
        )
        label = QtWidgets.QLabel(source)
        label.setWordWrap(True)
        layout.addWidget(label)

        form = QtWidgets.QFormLayout()
        self.module = self._length_spin("module_mm", 100.0, 2400.0, 50.0, 600.0)
        self.elevation = self._length_spin("ceiling_elevation_mm", 1000.0, 10000.0, 50.0, 2700.0)
        self.thickness = self._length_spin("panel_thickness_mm", 1.0, 100.0, 1.0, 15.0)
        self.gap = self._length_spin("joint_gap_mm", 0.0, 50.0, 1.0, 5.0)
        self.tolerance = self._length_spin("alignment_tolerance_mm", 0.0, 300.0, 5.0, 50.0)
        self.align_lights = QtWidgets.QCheckBox("Ajustar la fase de la reticula a las luminarias")
        self.align_lights.setChecked(self.params.GetBool("align_to_luminaires", True))
        self.replace_previous = QtWidgets.QCheckBox("Reemplazar cielos generados anteriormente")
        self.replace_previous.setChecked(self.params.GetBool("replace_previous", True))
        form.addRow("Modulo nominal", self.module)
        form.addRow("Cota inferior del cielo", self.elevation)
        form.addRow("Espesor del panel", self.thickness)
        form.addRow("Junta visible", self.gap)
        form.addRow("Tolerancia luminaria-centro", self.tolerance)
        form.addRow("", self.align_lights)
        form.addRow("", self.replace_previous)
        layout.addLayout(form)

        note = QtWidgets.QLabel(
            "Las luminarias existentes no se mueven. Las celdas que ocupan se reservan y "
            "las incompatibilidades quedan registradas en el cuadro de cielos."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _length_spin(self, key, minimum, maximum, step, default):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(1)
        spin.setSuffix(" mm")
        spin.setValue(self.params.GetFloat(key, default))
        return spin

    def options(self):
        values = {
            "module_mm": float(self.module.value()),
            "ceiling_elevation_mm": float(self.elevation.value()),
            "panel_thickness_mm": float(self.thickness.value()),
            "joint_gap_mm": float(self.gap.value()),
            "alignment_tolerance_mm": float(self.tolerance.value()),
            "align_to_luminaires": bool(self.align_lights.isChecked()),
            "replace_previous": bool(self.replace_previous.isChecked()),
        }
        for key in (
            "module_mm", "ceiling_elevation_mm", "panel_thickness_mm", "joint_gap_mm",
            "alignment_tolerance_mm",
        ):
            self.params.SetFloat(key, values[key])
        self.params.SetBool("align_to_luminaires", values["align_to_luminaires"])
        self.params.SetBool("replace_previous", values["replace_previous"])
        return values


class CommandClass:
    CommandName = "FA_CreateModularCeiling_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Cielo 600x600 con luminarias ElectricCR",
            "ToolTip": "Crear cielo suspendido modular por recinto y reservar las celdas de luminarias ElectricCR.",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            doc, _root, groups = ensure_project_structure()
            selection = list(FreeCADGui.Selection.getSelection() or [])
            rooms = collect_rooms(doc, selection)
            if selection and not rooms:
                raise UserFacingError("La seleccion no contiene recintos rectangulares o poligonales validos.")
            if not rooms:
                raise UserFacingError("No se encontraron recintos poligonales ni rectangulos del analisis de areas.")
            luminaires = collect_electriccr_luminaires(doc)
            dialog = ModularCeilingDialog(
                len(rooms), len(luminaires), bool(selection), parent=FreeCADGui.getMainWindow()
            )
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            options = dialog.options()
            try:
                doc.openTransaction("FA Cielo suspendido modular")
                transaction_open = True
            except Exception:
                transaction_open = False
            result = create_modular_ceilings(doc, groups["bim"], rooms, luminaires, options)
            doc.recompute()
            if transaction_open:
                doc.commitTransaction()
                transaction_open = False
            total_panels = sum(plan["full_panels"] + plan["partial_panels"] for plan in result["plans"])
            reserved = sum(plan["reserved_count"] for plan in result["plans"])
            incompatible = sum(plan["incompatible_luminaires"] for plan in result["plans"])
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(result["group"])
            msg(
                "FA_CreateModularCeiling completado. Recintos=%d | paneles=%d | celdas luminaria=%d | incompatibles=%d"
                % (len(result["plans"]), total_panels, reserved, incompatible)
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Cielo suspendido modular", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
