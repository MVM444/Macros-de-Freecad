"""Small dialog for native BIM Building and Level parameters.

Descripcion: solicita nombre de Building, Level y elevacion.
Objetivo: mantener el comando espacial independiente y sencillo.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 21:24 UTC-06:00.
Version: 0.1.0.
Instrucciones de mantenimiento: no agregar opciones de modelado de disciplina aqui.
"""

from __future__ import annotations

from PySide import QtWidgets


class BIMStructureDialog(QtWidgets.QDialog):
    def __init__(self, building_name="Edificio", level_name="Nivel 00", elevation=0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FA Crear estructura BIM")
        self.setMinimumWidth(390)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.building_name = QtWidgets.QLineEdit(str(building_name))
        self.level_name = QtWidgets.QLineEdit(str(level_name))
        self.elevation = QtWidgets.QDoubleSpinBox()
        self.elevation.setRange(-100000.0, 100000.0)
        self.elevation.setDecimals(1)
        self.elevation.setSuffix(" mm")
        self.elevation.setValue(float(elevation))
        form.addRow("Edificio", self.building_name)
        form.addRow("Nivel", self.level_name)
        form.addRow("Elevacion", self.elevation)
        layout.addLayout(form)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return {
            "building_name": str(self.building_name.text()).strip() or "Edificio",
            "level_name": str(self.level_name.text()).strip() or "Nivel 00",
            "elevation_mm": float(self.elevation.value()),
        }
