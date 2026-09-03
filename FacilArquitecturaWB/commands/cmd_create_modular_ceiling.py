"""FA_CreateModularCeiling command.

Descripcion: crea cielo suspendido modular y reserva luminarias ElectricCR.
Funcion principal: integrar los cielos en el Level BIM sin perder la logica modular validada.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-09-01 14:35 America/Costa_Rica.
Version: 0.5.0.
"""

from __future__ import annotations

import os
import time

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from .. import i18n
from ..core.ceiling_utils import (
    collect_electriccr_luminaires,
    collect_rooms,
    create_modular_ceilings,
)
from ..core.bim_structure_utils import (
    adopt_auxiliary_sources,
    ensure_bim_structure,
    ensure_level_auxiliary_group,
    is_building,
    selected_level,
)
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import active_or_new_document, msg


ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "modular_ceiling.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))
PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/ModularCeiling"


class ModularCeilingDialog(QtWidgets.QDialog):
    def __init__(self, room_count, luminaire_count, selected_rooms, parent=None):
        super().__init__(parent)
        self.params = FreeCAD.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle(i18n.bi("FA Cielo suspendido modular", "FA Modular suspended ceiling"))
        self.setMinimumWidth(480)
        layout = QtWidgets.QVBoxLayout(self)
        source = i18n.bi(
            "%d recintos %s | %d luminarias ElectricCR detectadas",
            "%d rooms %s | %d ElectricCR luminaires detected",
        ) % (
            room_count,
            i18n.bi("seleccionados", "selected") if selected_rooms else i18n.bi("detectados automaticamente", "detected automatically"),
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
        self.align_lights = QtWidgets.QCheckBox(i18n.bi("Ajustar la fase de la reticula a las luminarias", "Align grid phase to luminaires"))
        self.align_lights.setChecked(self.params.GetBool("align_to_luminaires", True))
        self.documentary_grid = QtWidgets.QCheckBox(i18n.bi("Crear reticula 2D documental (opcional)", "Create documentary 2D grid (optional)"))
        self.documentary_grid.setChecked(self.params.GetBool("create_documentary_grid", False))
        self.replace_previous = QtWidgets.QCheckBox(i18n.bi("Reemplazar cielos generados anteriormente", "Replace previously generated ceilings"))
        self.replace_previous.setChecked(self.params.GetBool("replace_previous", True))
        form.addRow(i18n.bi("Modulo nominal", "Nominal module"), self.module)
        form.addRow(i18n.bi("Cota inferior del cielo", "Ceiling underside elevation"), self.elevation)
        form.addRow(i18n.bi("Espesor del panel", "Panel thickness"), self.thickness)
        form.addRow(i18n.bi("Junta visible", "Visible joint"), self.gap)
        form.addRow(i18n.bi("Tolerancia luminaria-centro", "Luminaire-center tolerance"), self.tolerance)
        form.addRow("", self.align_lights)
        form.addRow("", self.documentary_grid)
        form.addRow("", self.replace_previous)
        layout.addLayout(form)

        note = QtWidgets.QLabel(i18n.bi(
            "Las luminarias existentes no se mueven. Las celdas que ocupan se reservan y "
            "las incompatibilidades quedan registradas en el cuadro de cielos. La reticula "
            "se calcula siempre; su objeto 2D solo se crea si se solicita.",
            "Existing luminaires are not moved. Their occupied cells are reserved and "
            "incompatibilities are recorded in the ceiling schedule. The grid is always "
            "calculated; its 2D object is created only when requested.",
        ))
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
            "create_documentary_grid": bool(self.documentary_grid.isChecked()),
            "replace_previous": bool(self.replace_previous.isChecked()),
        }
        for key in (
            "module_mm", "ceiling_elevation_mm", "panel_thickness_mm", "joint_gap_mm",
            "alignment_tolerance_mm",
        ):
            self.params.SetFloat(key, values[key])
        self.params.SetBool("align_to_luminaires", values["align_to_luminaires"])
        self.params.SetBool("create_documentary_grid", values["create_documentary_grid"])
        self.params.SetBool("replace_previous", values["replace_previous"])
        return values


def _building_parent(level):
    """Return the unique native Building parent of a Level when available."""
    if level is None:
        return None
    parents = [obj for obj in list(getattr(level, "InList", []) or []) if is_building(obj)]
    return parents[0] if len(parents) == 1 else None


class CommandClass:
    CommandName = "FA_CreateModularCeiling_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Cielo 600x600 con luminarias ElectricCR", "FA 600x600 ceiling with ElectricCR luminaires"),
            "ToolTip": i18n.bi("Crear cielo suspendido modular por recinto, integrarlo al Level BIM y reservar celdas de luminarias ElectricCR.", "Create a modular suspended ceiling per room, integrate it into the BIM Level, and reserve ElectricCR luminaire cells."),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            doc = active_or_new_document()
            selection = list(FreeCADGui.Selection.getSelection() or [])
            rooms = collect_rooms(doc, selection)
            if selection and not rooms:
                raise UserFacingError(i18n.bi("La seleccion no contiene recintos rectangulares o poligonales validos.", "The selection contains no valid rectangular or polygonal rooms."))
            if not rooms:
                raise UserFacingError(i18n.bi("No se encontraron recintos poligonales ni rectangulos del analisis de areas.", "No polygonal rooms or rectangles from the area analysis were found."))
            preferred_level = selected_level(selection or rooms)
            preferred_building = _building_parent(preferred_level)
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
            spatial = ensure_bim_structure(
                doc,
                building=preferred_building,
                level=preferred_level,
            )
            auxiliary_group = ensure_level_auxiliary_group(doc, spatial["level"])
            adopt_auxiliary_sources(doc, spatial["level"], rooms)
            result = create_modular_ceilings(
                doc,
                None,
                rooms,
                luminaires,
                options,
                level=spatial["level"],
                schedule_group=auxiliary_group,
            )
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
