"""Small parameter dialog shared by native BIM doors and windows.

Descripcion: solicita dimensiones y tolerancia sin contener logica geometrica.
Fecha: 2026-08-09
Version: 0.1.0
Instrucciones: mantener este dialogo como adaptador GUI del nucleo opening_utils.
"""

from __future__ import annotations

import FreeCAD
from PySide import QtWidgets


PREFERENCES_ROOT = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB"


class OpeningParametersDialog(QtWidgets.QDialog):
    """Collect parameters for one door or window generation command."""

    def __init__(self, opening_kind, source_count, wall_count, defaults, parent=None):
        super().__init__(parent)
        self.kind = str(opening_kind)
        section = "DoorsBIM" if self.kind == "door" else "WindowsBIM"
        self.params = FreeCAD.ParamGet(PREFERENCES_ROOT + "/" + section)
        visible = "puertas" if self.kind == "door" else "ventanas"
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

        form = QtWidgets.QFormLayout()
        self.height = self._length_spin(100.0, 10000.0, 100.0)
        default_height = float(
            defaults.get("door_height_mm", 2100.0)
            if self.kind == "door"
            else defaults.get("window_height_mm", 1200.0)
        )
        self.height.setValue(self.params.GetFloat("height_mm", default_height))
        form.addRow("Altura", self.height)

        self.sill = None
        if self.kind == "window":
            self.sill = self._length_spin(0.0, 10000.0, 100.0)
            self.sill.setValue(
                self.params.GetFloat(
                    "sill_mm", float(defaults.get("window_sill_mm", 900.0))
                )
            )
            form.addRow("Antepecho", self.sill)

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
