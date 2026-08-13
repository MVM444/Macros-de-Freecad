"""FA_CloseWallSketch command.

Descripcion: copia sketches de paredes y extiende lineas sobre puertas y ventanas.
Fecha: 2026-08-09
Version: 0.3.0
Instrucciones: una sola transaccion para permitir Ctrl-Z.
"""

from __future__ import annotations

import os
import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from ..core.bim_utils import prepare_sketches_as_wall_centerlines, sketches_requiring_wall_metadata
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.constants import BUILD_ID
from ..core.parameters import ensure_parameter_sheet, read_parameters
from ..core.project_structure import ensure_project_structure, msg
from ..core.room_utils import (
    collect_opening_sketches,
    collect_selected_wall_candidates,
    create_closed_wall_sketches,
)
from ..ui.dialog_wall_parameters import WallSketchParametersDialog

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "closed_rooms.svg")
).replace(os.sep, "/")
PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/ClosedRooms"


class ClosedRoomsDialog(QtWidgets.QDialog):
    def __init__(self, wall_count, opening_count, parent=None):
        super().__init__(parent)
        self.params = FreeCAD.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle("FA Cerrar huecos del sketch de paredes")
        self.setMinimumWidth(460)

        layout = QtWidgets.QVBoxLayout(self)
        description = QtWidgets.QLabel(
            "Sketches de pared seleccionados: %d\n"
            "Sketches de puertas o ventanas detectados: %d\n"
            "Se copiara cada sketch y solo se alargaran lineas colineales que delimitan un buque."
            % (wall_count, opening_count)
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QtWidgets.QFormLayout()
        self.max_gap = QtWidgets.QDoubleSpinBox()
        self.max_gap.setRange(100.0, 10000.0)
        self.max_gap.setDecimals(0)
        self.max_gap.setSingleStep(100.0)
        self.max_gap.setSuffix(" mm")
        self.max_gap.setValue(self.params.GetFloat("max_gap_mm", 3000.0))
        form.addRow("Buque maximo a cerrar", self.max_gap)

        self.alignment_tolerance = QtWidgets.QDoubleSpinBox()
        self.alignment_tolerance.setRange(0.1, 100.0)
        self.alignment_tolerance.setDecimals(1)
        self.alignment_tolerance.setSingleStep(1.0)
        self.alignment_tolerance.setSuffix(" mm")
        self.alignment_tolerance.setValue(
            self.params.GetFloat("alignment_tolerance_mm", 5.0)
        )
        form.addRow("Tolerancia de alineacion", self.alignment_tolerance)

        self.angle_tolerance = QtWidgets.QDoubleSpinBox()
        self.angle_tolerance.setRange(0.1, 15.0)
        self.angle_tolerance.setDecimals(1)
        self.angle_tolerance.setSingleStep(0.5)
        self.angle_tolerance.setSuffix(" grados")
        self.angle_tolerance.setValue(
            self.params.GetFloat("angle_tolerance_deg", 2.0)
        )
        form.addRow("Tolerancia angular", self.angle_tolerance)

        self.close_unmarked = QtWidgets.QCheckBox(
            "Cerrar tambien huecos sin sketch de puerta o ventana"
        )
        self.close_unmarked.setChecked(self.params.GetBool("close_unmarked_gaps", False))
        form.addRow("", self.close_unmarked)

        self.replace_previous = QtWidgets.QCheckBox("Reemplazar copias cerradas anteriores")
        self.replace_previous.setChecked(self.params.GetBool("replace_previous", True))
        form.addRow("", self.replace_previous)
        layout.addLayout(form)

        note = QtWidgets.QLabel(
            "La posicion, orientacion, espesor, altura y Placement del sketch fuente "
            "se conservan. Se recrean restricciones de orientacion y coincidencia. "
            "Si cambia una fuente, ejecute nuevamente el comando."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def options(self):
        values = {
            "max_gap_mm": float(self.max_gap.value()),
            "alignment_tolerance_mm": float(self.alignment_tolerance.value()),
            "angle_tolerance_deg": float(self.angle_tolerance.value()),
            "close_unmarked_gaps": bool(self.close_unmarked.isChecked()),
            "replace_previous": bool(self.replace_previous.isChecked()),
        }
        self.params.SetFloat("max_gap_mm", values["max_gap_mm"])
        self.params.SetFloat("alignment_tolerance_mm", values["alignment_tolerance_mm"])
        self.params.SetFloat("angle_tolerance_deg", values["angle_tolerance_deg"])
        self.params.SetBool("close_unmarked_gaps", values["close_unmarked_gaps"])
        self.params.SetBool("replace_previous", values["replace_previous"])
        return values


class CommandClass:
    CommandName = "FA_CloseWallSketch"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Cerrar huecos de paredes",
            "ToolTip": (
                "Cerrar huecos desde un muro BIM, su Sketch Base o un Sketch generico; "
                "solicita los parametros de muro que falten."
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            msg(
                "FA_CloseWallSketch ejecutando | build %s | comando %s"
                % (BUILD_ID, self.CommandName)
            )
            doc, _root, groups = ensure_project_structure()
            selection = list(FreeCADGui.Selection.getSelection() or [])
            msg(
                "Seleccion recibida: %s"
                % (
                    ", ".join(
                        str(getattr(obj, "Label", getattr(obj, "Name", "?")) or "?")
                        for obj in selection
                    )
                    or "(vacia)"
                )
            )
            if not selection:
                raise UserFacingError(
                    "Seleccione el sketch de centros de paredes que desea copiar y cerrar."
                )
            opening_sketches = collect_opening_sketches(doc, selection=selection)
            wall_sketches = collect_selected_wall_candidates(selection, opening_sketches)
            if not wall_sketches:
                raise UserFacingError(
                    "La seleccion no contiene un muro BIM ni un Sketch de pared convertible. "
                    "Seleccione el muro, su Sketch Base o un Sketch generico con geometria."
                )
            missing = sketches_requiring_wall_metadata(wall_sketches)
            conversion_values = None
            if missing:
                sheet = ensure_parameter_sheet(doc, groups["parameters"])
                params = read_parameters(sheet)
                parameter_dialog = WallSketchParametersDialog(
                    missing, params, parent=FreeCADGui.getMainWindow()
                )
                accepted = (
                    parameter_dialog.exec()
                    if hasattr(parameter_dialog, "exec")
                    else parameter_dialog.exec_()
                )
                if accepted != QtWidgets.QDialog.Accepted:
                    return
                conversion_values = parameter_dialog.values()
            msg(
                "Clasificacion: paredes=%d | puertas_ventanas=%d"
                % (len(wall_sketches), len(opening_sketches))
            )

            dialog = ClosedRoomsDialog(
                len(wall_sketches),
                len(opening_sketches),
                parent=FreeCADGui.getMainWindow(),
            )
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            options = dialog.options()

            try:
                doc.openTransaction("FA Cerrar huecos de paredes")
                transaction_open = True
            except Exception:
                transaction_open = False
            if conversion_values is not None:
                wall_sketches = prepare_sketches_as_wall_centerlines(
                    wall_sketches,
                    conversion_values["thickness"],
                    conversion_values["height"],
                    conversion_values["wall_type"],
                )
            sketches, summary = create_closed_wall_sketches(
                doc,
                groups["master_sketches"],
                wall_sketches,
                opening_sketches,
                max_gap_mm=options["max_gap_mm"],
                alignment_tolerance_mm=options["alignment_tolerance_mm"],
                angle_tolerance_deg=options["angle_tolerance_deg"],
                close_unmarked_gaps=options["close_unmarked_gaps"],
                replace_previous=options["replace_previous"],
            )
            doc.recompute()
            if transaction_open:
                doc.commitTransaction()
                transaction_open = False

            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(sketches[0])
            except Exception:
                pass
            msg(
                "FA_CloseWallSketch completado. Sketches=%d | huecos_cerrados=%d"
                % (len(sketches), summary["closed_gap_count"])
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Cerrar huecos de paredes", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
