"""Small parameter dialog shared by native BIM doors, windows and openings.

Descripcion: solicita dimensiones y tolerancia sin contener logica geometrica.
Fecha y hora: 2026-09-01 09:05 America/Costa_Rica
Version: 0.3.0
Instrucciones: mantener este dialogo como adaptador GUI del nucleo opening_utils.
"""

from __future__ import annotations

import FreeCAD
from PySide import QtWidgets

from ..core.process_feedback import long_process_message


PREFERENCES_ROOT = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB"


class OpeningParametersDialog(QtWidgets.QDialog):
    """Collect parameters for one door or window generation command."""

    def __init__(self, opening_kind, source_count, wall_count, defaults, parent=None):
        super().__init__(parent)
        self.kind = str(opening_kind)
        section = {
            "door": "DoorsBIM",
            "window": "WindowsBIM",
            "opening": "OpeningsBIM",
        }[self.kind]
        self.params = FreeCAD.ParamGet(PREFERENCES_ROOT + "/" + section)
        visible = {"door": "puertas", "window": "ventanas", "opening": "aberturas"}[self.kind]
        self.setWindowTitle("FA %s BIM" % visible.capitalize())
        self.setMinimumWidth(460)

        layout = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "Sketches fuente: %d\nMuros BIM candidatos: %d\n"
            "El ancho se obtiene de cada eje y el host se valida geometricamente."
            % (int(source_count), int(wall_count))
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        warning = QtWidgets.QLabel(long_process_message("La creacion de %s BIM" % visible))
        warning.setWordWrap(True)
        warning_font = warning.font()
        warning_font.setBold(True)
        warning.setFont(warning_font)
        layout.addWidget(warning)

        form = QtWidgets.QFormLayout()
        self.height = self._length_spin(100.0, 10000.0, 100.0)
        default_height = float({
            "door": defaults.get("door_height_mm", 2100.0),
            "window": defaults.get("window_height_mm", 1200.0),
            "opening": defaults.get("opening_height_mm", 2100.0),
        }[self.kind])
        self.height.setValue(self.params.GetFloat("height_mm", default_height))
        form.addRow("Altura", self.height)

        self.sill = None
        if self.kind in ("window", "opening"):
            self.sill = self._length_spin(0.0, 10000.0, 100.0)
            self.sill.setValue(
                self.params.GetFloat(
                    "sill_mm",
                    float(
                        defaults.get("window_sill_mm", 900.0)
                        if self.kind == "window"
                        else defaults.get("opening_sill_mm", 0.0)
                    ),
                )
            )
            form.addRow(
                "Antepecho" if self.kind == "window" else "Altura desde piso",
                self.sill,
            )

        self.tolerance = self._length_spin(1.0, 5000.0, 25.0)
        self.tolerance.setValue(self.params.GetFloat("host_tolerance_mm", 250.0))
        form.addRow("Tolerancia para buscar muro", self.tolerance)

        self.replace_existing = QtWidgets.QCheckBox(
            "Reemplazar solamente %s creadas por este comando" % visible
        )
        self.replace_existing.setChecked(
            self.params.GetBool("replace_existing", True)
        )
        form.addRow("", self.replace_existing)
        layout.addLayout(form)

        note = QtWidgets.QLabel(
            "Los objetos manuales y los resultados historicos de Puriscal no se eliminan. "
            "Si dos muros son equivalentes, el eje se omite como ambiguo."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _length_spin(minimum, maximum, step):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(float(minimum), float(maximum))
        spin.setDecimals(1)
        spin.setSingleStep(float(step))
        spin.setSuffix(" mm")
        return spin

    def values(self):
        result = {
            "height_mm": float(self.height.value()),
            "sill_mm": float(self.sill.value()) if self.sill is not None else 0.0,
            "host_tolerance_mm": float(self.tolerance.value()),
            "replace_existing": bool(self.replace_existing.isChecked()),
        }
        self.params.SetFloat("height_mm", result["height_mm"])
        self.params.SetFloat("sill_mm", result["sill_mm"])
        self.params.SetFloat("host_tolerance_mm", result["host_tolerance_mm"])
        self.params.SetBool("replace_existing", result["replace_existing"])
        return result
