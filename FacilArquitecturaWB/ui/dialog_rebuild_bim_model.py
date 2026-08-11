"""Small assignment dialog for native BIM reconstruction from Sketches.

Descripcion: permite confirmar o corregir Sketches de muros, columnas, puertas y
ventanas, junto con los parametros esenciales del modelo.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-09 23:05 UTC-06:00.
Version: 0.1.0.
Instrucciones de mantenimiento: mantener la GUI separada de los servicios BIM.
"""

from __future__ import annotations

from PySide import QtCore, QtWidgets


class RebuildBIMModelDialog(QtWidgets.QDialog):
    """Confirm automatic classification and collect reconstruction parameters."""

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.sketches = {
            str(record["sketch"].Name): record["sketch"] for record in analysis["records"]
        }
        self.setWindowTitle("FA Reconstruir modelo BIM desde Sketches")
        self.setMinimumWidth(650)
        layout = QtWidgets.QVBoxLayout(self)

        info = QtWidgets.QLabel(
            "Revise las asignaciones detectadas. Los muros, columnas y aberturas se "
            "crearan como objetos BIM nativos dentro de un Building y un Level."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        assignment_group = QtWidgets.QGroupBox("Asignacion de Sketches")
        assignment_form = QtWidgets.QFormLayout(assignment_group)
        suggested = analysis["assignments"]
        self.wall_combo = self._combo(suggested.get("walls"))
        self.column_combo = self._combo(suggested.get("columns"), optional=True)
        self.door_combo = self._combo(suggested.get("doors"), optional=True)
        assignment_form.addRow("Muros", self.wall_combo)
        assignment_form.addRow("Columnas", self.column_combo)
        assignment_form.addRow("Puertas", self.door_combo)

        self.window_list = QtWidgets.QListWidget()
        self.window_list.setMaximumHeight(125)
        selected_windows = {obj.Name for obj in suggested.get("windows", [])}
        for sketch in self._ordered_sketches():
            item = QtWidgets.QListWidgetItem(self._display(sketch))
            item.setData(QtCore.Qt.UserRole, sketch.Name)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(
                QtCore.Qt.Checked if sketch.Name in selected_windows else QtCore.Qt.Unchecked
            )
            self.window_list.addItem(item)
        assignment_form.addRow("Ventanas (una o varias)", self.window_list)

        self.slab_combo = self._combo(None, optional=True)
        self.slab_combo.setEnabled(False)
        self.slab_combo.setToolTip("La losa BIM permanece diferida en esta fase estable.")
        assignment_form.addRow("Losa (fase posterior)", self.slab_combo)

        self.reference_list = QtWidgets.QListWidget()
        self.reference_list.setMaximumHeight(95)
        selected_references = {obj.Name for obj in suggested.get("references", [])}
        for sketch in self._ordered_sketches():
            item = QtWidgets.QListWidgetItem(self._display(sketch))
            item.setData(QtCore.Qt.UserRole, sketch.Name)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(
                QtCore.Qt.Checked if sketch.Name in selected_references else QtCore.Qt.Unchecked
            )
            self.reference_list.addItem(item)
        assignment_form.addRow("Referencias", self.reference_list)
        layout.addWidget(assignment_group)

        structure_group = QtWidgets.QGroupBox("Estructura espacial y dimensiones")
        form = QtWidgets.QFormLayout(structure_group)
        self.building_name = QtWidgets.QLineEdit("Edificio")
        self.level_name = QtWidgets.QLineEdit("Nivel 00")
        self.elevation = self._spin(-100000.0, 100000.0, 0.0)
        self.wall_thickness = self._spin(10.0, 5000.0, 150.0)
        self.wall_height = self._spin(100.0, 20000.0, 3000.0)
        self.column_width = self._spin(10.0, 5000.0, 400.0)
        self.column_depth = self._spin(10.0, 5000.0, 400.0)
        self.door_height = self._spin(100.0, 10000.0, 2100.0)
        self.window_height = self._spin(100.0, 10000.0, 1200.0)
        self.window_sill = self._spin(0.0, 10000.0, 900.0)
        self.host_tolerance = self._spin(1.0, 5000.0, 250.0)
        form.addRow("Edificio", self.building_name)
        form.addRow("Nivel", self.level_name)
        form.addRow("Elevacion", self.elevation)
        form.addRow("Espesor / altura de muro", self._pair(self.wall_thickness, self.wall_height))
        form.addRow("Ancho / fondo de columna", self._pair(self.column_width, self.column_depth))
        form.addRow("Altura de puerta", self.door_height)
        form.addRow("Altura / antepecho de ventana", self._pair(self.window_height, self.window_sill))
        form.addRow("Tolerancia para host", self.host_tolerance)
        layout.addWidget(structure_group)

        unclassified = [
            record["sketch"] for record in analysis["records"] if record["suggested_role"] is None
        ]
        note = QtWidgets.QLabel(
            "Sin clasificar automaticamente: %s\n"
            "La losa y los Spaces se mantienen diferidos hasta completar su validacion nativa."
            % (", ".join(self._display(obj) for obj in unclassified) or "ninguno")
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        windows = []
        for index in range(self.window_list.count()):
            item = self.window_list.item(index)
            if item.checkState() == QtCore.Qt.Checked:
                windows.append(self.sketches[str(item.data(QtCore.Qt.UserRole))])
        references = []
        for index in range(self.reference_list.count()):
            item = self.reference_list.item(index)
            if item.checkState() == QtCore.Qt.Checked:
                references.append(self.sketches[str(item.data(QtCore.Qt.UserRole))])
        assignments = {
            "walls": self._combo_object(self.wall_combo),
            "columns": self._combo_object(self.column_combo),
            "doors": self._combo_object(self.door_combo),
            "windows": windows,
            "references": references,
        }
        options = {
            "building_name": self.building_name.text().strip() or "Edificio",
            "level_name": self.level_name.text().strip() or "Nivel 00",
            "elevation_mm": float(self.elevation.value()),
            "wall_thickness_mm": float(self.wall_thickness.value()),
            "wall_height_mm": float(self.wall_height.value()),
            "column_width_mm": float(self.column_width.value()),
            "column_depth_mm": float(self.column_depth.value()),
            "column_height_mm": float(self.wall_height.value()),
            "door_height_mm": float(self.door_height.value()),
            "window_height_mm": float(self.window_height.value()),
            "window_sill_mm": float(self.window_sill.value()),
            "host_tolerance_mm": float(self.host_tolerance.value()),
        }
        return assignments, options

    def _combo(self, suggested, optional=False):
        combo = QtWidgets.QComboBox()
        if optional:
            combo.addItem("No asignar", "")
        for sketch in self._ordered_sketches():
            combo.addItem(self._display(sketch), sketch.Name)
        if suggested is not None:
            index = combo.findData(suggested.Name)
            if index >= 0:
                combo.setCurrentIndex(index)
        return combo

    def _combo_object(self, combo):
        name = str(combo.currentData() or "")
        return self.sketches.get(name)

    def _ordered_sketches(self):
        return sorted(self.sketches.values(), key=lambda obj: self._display(obj).casefold())

    @staticmethod
    def _display(sketch):
        label = str(getattr(sketch, "Label", sketch.Name) or sketch.Name)
        return label if label == sketch.Name else "%s (%s)" % (label, sketch.Name)

    @staticmethod
    def _spin(minimum, maximum, value):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(float(minimum), float(maximum))
        spin.setDecimals(1)
        spin.setSingleStep(50.0)
        spin.setSuffix(" mm")
        spin.setValue(float(value))
        return spin

    @staticmethod
    def _pair(first, second):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(first)
        layout.addWidget(second)
        return widget
