"""FA_CloseWallSketch command.

Nombre: cmd_create_closed_rooms.py
Proposito: ejecutar la reconstruccion no destructiva de continuidad de muros
sobre buques conocidos de puertas y ventanas.
Funcionamiento principal: toma sketches de paredes seleccionados, detecta
sketches de puertas/ventanas, aplica el nucleo de continuidad y crea copias
trazables dentro de MasterSketches.
Instrucciones para futuras modificaciones: conservar el ID interno
FA_CloseWallSketch y una sola transaccion para permitir Ctrl+Z.
Version: 0.10.0
Fecha y hora: 2026-09-02 12:35 America/Costa_Rica
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from .. import i18n

from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.constants import BUILD_ID
from ..core.bim_structure_utils import adopt_auxiliary_sources, ensure_auxiliary_parent
from ..core.project_structure import active_or_new_document, msg
from ..core.room_utils import (
    DEFAULT_ALIGNMENT_TOLERANCE_MM,
    DEFAULT_ANGLE_TOLERANCE_DEG,
    DEFAULT_MAX_GAP_MM,
    collect_selected_wall_candidates,
    create_closed_wall_sketches,
    resolve_opening_sketches,
)

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "closed_rooms.svg")
).replace(os.sep, "/")
PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/ClosedRooms"


class ClosedRoomsDialog(QtWidgets.QDialog):
    def __init__(self, wall_count, opening_count, opening_mode="automatic", parent=None):
        super().__init__(parent)
        self.params = FreeCAD.ParamGet(PREFERENCES_PATH)
        self.opening_mode = str(opening_mode or "automatic")
        self._migrate_default_profile()
        self.setWindowTitle(i18n.bi("FA Cerrar buques de puertas y ventanas", "FA Close door and window gaps"))
        self.setMinimumWidth(470)

        layout = QtWidgets.QVBoxLayout(self)
        if self.opening_mode == "selection":
            mode_text = i18n.bi(
                "SELECCION EXPLICITA: solo los sketches de puertas/ventanas seleccionados se toman como candidatos de abertura. No se agregan otros sketches del documento. Su geometria se usa como evidencia local autoritativa del buque.",
                "EXPLICIT SELECTION: only the selected door/window Sketches are used as opening candidates. No other document Sketches are added. Their geometry is used as authoritative local evidence for the gap.",
            )
        else:
            mode_text = i18n.bi(
                "AUTOMATICO: al no seleccionar sketches de abertura, se buscan candidatos de puertas/ventanas en el documento.",
                "AUTOMATIC: when no opening Sketches are selected, door/window candidates are searched in the document.",
            )
        description = QtWidgets.QLabel(i18n.bi(
            "Sketches de pared seleccionados: %d\nSketches de puertas o ventanas candidatos: %d\nModo de aberturas: %s\n%s\nLa puerta/ventana valida la zona del buque; la direccion final siempre la determinan los tramos de pared." % (wall_count, opening_count, self.opening_mode, mode_text),
            "Selected wall Sketches: %d\nDoor or window candidate Sketches: %d\nOpening mode: %s\n%s\nThe door/window validates the gap zone; the final direction is always determined by the wall segments." % (wall_count, opening_count, self.opening_mode, mode_text),
        ))
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QtWidgets.QFormLayout()
        self.max_gap = QtWidgets.QDoubleSpinBox()
        self.max_gap.setRange(100.0, 10000.0)
        self.max_gap.setDecimals(0)
        self.max_gap.setSingleStep(100.0)
        self.max_gap.setSuffix(" mm")
        self.max_gap.setValue(self.params.GetFloat("max_gap_mm", DEFAULT_MAX_GAP_MM))
        form.addRow(i18n.bi("Buque maximo a cerrar", "Maximum gap to close"), self.max_gap)

        self.alignment_tolerance = QtWidgets.QDoubleSpinBox()
        self.alignment_tolerance.setRange(0.1, 100.0)
        self.alignment_tolerance.setDecimals(1)
        self.alignment_tolerance.setSingleStep(1.0)
        self.alignment_tolerance.setSuffix(" mm")
        self.alignment_tolerance.setValue(
            self.params.GetFloat("alignment_tolerance_mm", DEFAULT_ALIGNMENT_TOLERANCE_MM)
        )
        form.addRow(i18n.bi("Tolerancia de alineacion", "Alignment tolerance"), self.alignment_tolerance)

        self.angle_tolerance = QtWidgets.QDoubleSpinBox()
        self.angle_tolerance.setRange(0.1, 15.0)
        self.angle_tolerance.setDecimals(1)
        self.angle_tolerance.setSingleStep(0.5)
        self.angle_tolerance.setSuffix(i18n.bi(" grados", " degrees"))
        self.angle_tolerance.setValue(
            self.params.GetFloat("angle_tolerance_deg", DEFAULT_ANGLE_TOLERANCE_DEG)
        )
        form.addRow(i18n.bi("Tolerancia angular", "Angular tolerance"), self.angle_tolerance)

        if self.opening_mode == "selection":
            mocheta_label = i18n.bi(
                "Completar ademas por pares de mochetas buques que NO esten en los sketches seleccionados (avanzado)",
                "Also complete gaps from jamb pairs that are NOT in the selected Sketches (advanced)",
            )
            mocheta_default = False
        else:
            mocheta_label = i18n.bi(
                "Usar pares de mochetas cuando falte puerta/ventana en los sketches",
                "Use jamb pairs when a door/window is missing from the Sketches",
            )
            mocheta_default = self.params.GetBool("close_mocheta_gaps", True)
        self.close_mochetas = QtWidgets.QCheckBox(mocheta_label)
        self.close_mochetas.setChecked(bool(mocheta_default))
        form.addRow("", self.close_mochetas)

        self.replace_previous = QtWidgets.QCheckBox(i18n.bi("Reemplazar copias cerradas anteriores", "Replace previous closed copies"))
        self.replace_previous.setChecked(self.params.GetBool("replace_previous", True))
        form.addRow("", self.replace_previous)
        layout.addLayout(form)

        note = QtWidgets.QLabel(i18n.bi(
            "La posicion, orientacion, espesor, altura y Placement del sketch fuente se conservan. Las paredes inclinadas mantienen su direccion real. En modo selection la inferencia por mochetas queda apagada por defecto para que la seleccion controle el alcance; puede activarse expresamente como opcion avanzada. Si cambia una fuente, ejecute nuevamente el comando.",
            "The source Sketch position, orientation, thickness, height, and Placement are preserved. Sloped walls keep their actual direction. In selection mode, jamb-pair inference is disabled by default so the selection controls the scope; it can be explicitly enabled as an advanced option. If a source changes, run the command again.",
        ))
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
            "close_mocheta_gaps": bool(self.close_mochetas.isChecked()),
            "replace_previous": bool(self.replace_previous.isChecked()),
        }
        self.params.SetFloat("max_gap_mm", values["max_gap_mm"])
        self.params.SetFloat("alignment_tolerance_mm", values["alignment_tolerance_mm"])
        self.params.SetFloat("angle_tolerance_deg", values["angle_tolerance_deg"])
        self.params.SetBool("close_mocheta_gaps", values["close_mocheta_gaps"])
        self.params.SetBool("replace_previous", values["replace_previous"])
        self.params.SetInt("defaults_profile", 2)
        return values

    def _migrate_default_profile(self):
        """Move untouched legacy defaults to the safer 0.6 profile."""
        if self.params.GetInt("defaults_profile", 0) >= 2:
            return
        old_gap = self.params.GetFloat("max_gap_mm", 3000.0)
        old_alignment = self.params.GetFloat("alignment_tolerance_mm", 5.0)
        old_angle = self.params.GetFloat("angle_tolerance_deg", 2.0)
        untouched = (
            abs(old_gap - 3000.0) < 1e-6
            and abs(old_alignment - 5.0) < 1e-6
            and abs(old_angle - 2.0) < 1e-6
        )
        if untouched:
            self.params.SetFloat("max_gap_mm", DEFAULT_MAX_GAP_MM)
            self.params.SetFloat("alignment_tolerance_mm", DEFAULT_ALIGNMENT_TOLERANCE_MM)
            self.params.SetFloat("angle_tolerance_deg", DEFAULT_ANGLE_TOLERANCE_DEG)
        self.params.SetBool("close_mocheta_gaps", True)
        self.params.SetInt("defaults_profile", 2)


class CommandClass:
    CommandName = "FA_CloseWallSketch"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Cerrar buques de puertas y ventanas", "FA Close door and window gaps"),
            "ToolTip": i18n.bi(
                "Copiar los sketches de pared seleccionados, reconstruir la continuidad sobre buques de puertas/ventanas y eliminar divisiones redundantes.",
                "Copy selected wall Sketches, rebuild continuity across door/window gaps, and remove redundant divisions.",
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
            doc = active_or_new_document()
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
                    "Seleccione el sketch de centros de paredes que desea copiar y reconstruir."
                )
            opening_sketches, opening_mode = resolve_opening_sketches(
                doc, selection=selection
            )
            wall_sketches = collect_selected_wall_candidates(
                selection, opening_sketches=opening_sketches
            )
            if not wall_sketches:
                raise UserFacingError(
                    "La seleccion no contiene un sketch de paredes utilizable. "
                    "Puede seleccionar el sketch de pared junto con los sketches "
                    "de puertas y ventanas que desea usar."
                )
            msg(
                "Clasificacion: paredes=%d | puertas_ventanas=%d | modo_aberturas=%s"
                % (len(wall_sketches), len(opening_sketches), opening_mode)
            )
            msg(
                "Sketches de abertura usados (%s): %s"
                % (
                    opening_mode,
                    ", ".join(
                        str(getattr(obj, "Label", getattr(obj, "Name", "?")) or "?")
                        for obj in opening_sketches
                    )
                    or "(ninguno)",
                )
            )

            dialog = ClosedRoomsDialog(
                len(wall_sketches),
                len(opening_sketches),
                opening_mode=opening_mode,
                parent=FreeCADGui.getMainWindow(),
            )
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            options = dialog.options()
            support_parent, target_level = ensure_auxiliary_parent(
                doc, wall_sketches + opening_sketches, legacy_key="master_sketches"
            )

            try:
                doc.openTransaction("FA Cerrar buques de puertas y ventanas")
                transaction_open = True
            except Exception:
                transaction_open = False
            sketches, summary = create_closed_wall_sketches(
                doc,
                support_parent,
                wall_sketches,
                opening_sketches,
                max_gap_mm=options["max_gap_mm"],
                alignment_tolerance_mm=options["alignment_tolerance_mm"],
                angle_tolerance_deg=options["angle_tolerance_deg"],
                close_unmarked_gaps=False,
                close_mocheta_gaps=options["close_mocheta_gaps"],
                opening_mode=opening_mode,
                replace_previous=options["replace_previous"],
            )
            if target_level is not None:
                adopt_auxiliary_sources(
                    doc, target_level, list(sketches) + wall_sketches + opening_sketches
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
                "FA_CloseWallSketch completado. Sketches=%d | modo_aberturas=%s | "
                "candidatos_abertura=%d | sketches_abertura_usados=%d | "
                "buques_cerrados=%d | por_mochetas=%d | segmentos_reducidos=%d | "
                "aberturas=%d usadas, %d ambiguas, %d sin cierre"
                % (
                    len(sketches),
                    summary.get("opening_mode", opening_mode),
                    summary.get("opening_candidate_count", len(opening_sketches)),
                    summary.get("used_opening_sketch_count", 0),
                    summary["closed_gap_count"],
                    summary.get("mocheta_gap_count", 0),
                    summary.get("segment_reduction_count", 0),
                    summary.get("matched_opening_count", 0),
                    summary.get("ambiguous_opening_count", 0),
                    summary.get("rejected_opening_count", 0),
                )
            )
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Cerrar buques de puertas y ventanas", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
