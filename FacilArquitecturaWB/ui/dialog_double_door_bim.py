"""Parameter dialog for the generic Facil Arquitectura double BIM door."""

from __future__ import annotations

import FreeCAD
from PySide import QtWidgets


PREFERENCES_ROOT = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/DoubleDoorBIM"


class DoubleDoorBIMDialog(QtWidgets.QDialog):
    """Collect dimensions, opening and free-placement coordinates."""

    def __init__(self, host_label="", picked_on_host=False, parent=None):
        super().__init__(parent)
        self.params = FreeCAD.ParamGet(PREFERENCES_ROOT)
        self.host_available = bool(host_label)
        self.setWindowTitle("FA Insertar puerta doble BIM")
        self.setMinimumWidth(500)

        layout = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "Crea una puerta Arch/BIM nativa de dos hojas con sistema Europa.\n"
            + (
                "Muro seleccionado: %s. La puerta se ubicara en el punto pulsado sobre "
                "el muro o, si no hay punto, en el centro de su tramo." % host_label
                if self.host_available
                else "No hay muro seleccionado. Se usara el Placement libre indicado abajo."
            )
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QtWidgets.QFormLayout()
        self.width = self._length_spin(800.0, 10000.0, 100.0)
        self.width.setValue(self.params.GetFloat("width_mm", 2000.0))
        form.addRow("Ancho total", self.width)

        self.height = self._length_spin(1200.0, 10000.0, 100.0)
        self.height.setValue(self.params.GetFloat("height_mm", 2100.0))
        form.addRow("Altura total", self.height)

        self.opening = QtWidgets.QSpinBox()
        self.opening.setRange(0, 100)
        self.opening.setSuffix(" %")
        self.opening.setValue(self.params.GetInt("opening_percent", 0))
        form.addRow("Apertura inicial", self.opening)

        self.use_host = QtWidgets.QCheckBox("Alojar y cortar el muro seleccionado")
        self.use_host.setEnabled(self.host_available)
        self.use_host.setChecked(self.host_available)
        if self.host_available and picked_on_host:
            self.use_host.setToolTip("Se usara el punto pulsado sobre el muro.")
        form.addRow("Anfitrion", self.use_host)

        self.x = self._coordinate_spin()
        self.y = self._coordinate_spin()
        self.z = self._coordinate_spin()
        self.rotation = QtWidgets.QDoubleSpinBox()
        self.rotation.setRange(-360.0, 360.0)
        self.rotation.setDecimals(1)
        self.rotation.setSingleStep(5.0)
        self.rotation.setSuffix(" deg")
        self.x.setValue(self.params.GetFloat("x_mm", 0.0))
        self.y.setValue(self.params.GetFloat("y_mm", 0.0))
        self.z.setValue(self.params.GetFloat("z_mm", 0.0))
        self.rotation.setValue(self.params.GetFloat("rotation_deg", 0.0))
        form.addRow("X libre", self.x)
        form.addRow("Y libre", self.y)
        form.addRow("Z libre", self.z)
        form.addRow("Rotacion libre", self.rotation)
        layout.addLayout(form)

        self.use_host.toggled.connect(self._update_free_placement_state)
        self._update_free_placement_state(self.use_host.isChecked())

        note = QtWidgets.QLabel(
            "La geometria se crea con Arch.makeWindow, IfcType Door, dos hojas y "
            "WindowParts. La opcion libre no crea un muro ni un hueco."
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

    @staticmethod
    def _coordinate_spin():
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-1000000.0, 1000000.0)
        spin.setDecimals(1)
        spin.setSingleStep(100.0)
        spin.setSuffix(" mm")
        return spin

    def _update_free_placement_state(self, hosted):
        enabled = not bool(hosted)
        for widget in (self.x, self.y, self.z, self.rotation):
            widget.setEnabled(enabled)

    def values(self):
        result = {
            "width_mm": float(self.width.value()),
            "height_mm": float(self.height.value()),
            "opening_percent": int(self.opening.value()),
            "use_host": bool(self.use_host.isChecked() and self.host_available),
            "x_mm": float(self.x.value()),
            "y_mm": float(self.y.value()),
            "z_mm": float(self.z.value()),
            "rotation_deg": float(self.rotation.value()),
        }
        self.params.SetFloat("width_mm", result["width_mm"])
        self.params.SetFloat("height_mm", result["height_mm"])
        self.params.SetInt("opening_percent", result["opening_percent"])
        self.params.SetFloat("x_mm", result["x_mm"])
        self.params.SetFloat("y_mm", result["y_mm"])
        self.params.SetFloat("z_mm", result["z_mm"])
        self.params.SetFloat("rotation_deg", result["rotation_deg"])
        return result
