"""Dialog for changing installed native BIM door presets."""

from __future__ import annotations

import FreeCAD
from PySide import QtWidgets


PREFERENCES_ROOT = (
    "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/ChangeDoorType"
)


class ChangeDoorTypeDialog(QtWidgets.QDialog):
    """Choose one installed preset for one or more existing BIM doors."""

    def __init__(self, door_count, current_type, presets, parent=None):
        super().__init__(parent)
        self.params = FreeCAD.ParamGet(PREFERENCES_ROOT)
        self.setWindowTitle("FA Cambiar tipo de puerta")
        self.setMinimumWidth(470)

        layout = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "Puertas seleccionadas: %d\nTipo actual: %s"
            % (int(door_count), str(current_type or "Desconocido"))
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QtWidgets.QFormLayout()
        self.preset = QtWidgets.QComboBox()
        self.preset.addItems([str(item) for item in presets])
        remembered = self.params.GetString("target_preset", "")
        index = self.preset.findText(remembered)
        if index < 0 and current_type in presets and len(presets) > 1:
            index = next(
                (position for position, value in enumerate(presets) if value != current_type),
                0,
            )
        self.preset.setCurrentIndex(max(0, index))
        form.addRow("Nuevo tipo BIM", self.preset)

        self.preserve_dimensions = QtWidgets.QCheckBox("Conservar ancho y alto")
        self.preserve_dimensions.setChecked(True)
        self.preserve_dimensions.setEnabled(False)
        self.preserve_dimensions.setToolTip(
            "Esta version conserva siempre el vano exterior por seguridad."
        )
        form.addRow("", self.preserve_dimensions)

        self.preserve_opening = QtWidgets.QCheckBox("Conservar apertura (%)")
        self.preserve_opening.setChecked(
            self.params.GetBool("preserve_opening", True)
        )
        form.addRow("", self.preserve_opening)
        layout.addLayout(form)

        note = QtWidgets.QLabel(
            "El host, Placement, Normal, nivel, propiedades FA y trazabilidad se "
            "conservan siempre. Solo se ofrecen presets integrados en FreeCAD."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Apply | QtWidgets.QDialogButtonBox.Cancel
        )
        apply_button = buttons.button(QtWidgets.QDialogButtonBox.Apply)
        apply_button.setText("Aplicar")
        # ApplyRole does not emit QDialogButtonBox.accepted. Connect the
        # concrete button so clicking "Aplicar" actually closes the dialog
        # with QDialog.Accepted and lets the command perform the conversion.
        apply_button.clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        result = {
            "target_preset": str(self.preset.currentText()),
            "preserve_dimensions": True,
            "preserve_opening": bool(self.preserve_opening.isChecked()),
        }
        self.params.SetString("target_preset", result["target_preset"])
        self.params.SetBool("preserve_opening", result["preserve_opening"])
        return result
