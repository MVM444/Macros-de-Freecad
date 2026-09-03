"""Small PySide dialog for a parametric service platform front."""

from __future__ import annotations

from dataclasses import replace

import FreeCAD
from PySide import QtWidgets

from ..modules.service_platform.calculator import calculate_layout, calculate_line_layout
from ..modules.service_platform.model import PlatformOptions
from ..modules.service_platform.validation import PlatformValidationError


PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/ServicePlatform"


class ServicePlatformDialog(QtWidgets.QDialog):
    """Collect the initial parameters and preview the derived dimensions."""

    def __init__(self, parent=None, axis_length_mm=None):
        super().__init__(parent)
        self.axis_length_mm = None if axis_length_mm is None else float(axis_length_mm)
        self.params = FreeCAD.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle("FA Frente de plataforma de atencion")
        self.setMinimumWidth(500)
        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel(
            "La linea seleccionada define posicion, orientacion y longitud total. "
            "Elija el numero de puestos y el lado del funcionario mirando de P0 hacia P1."
            if self.axis_length_mm is not None
            else "Genera un frente modular heredado. La referencia PL-01 orienta los valores iniciales."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QtWidgets.QFormLayout()
        self.total_width = self._length("total_width_mm", 100.0, 100000.0, 100.0, 3840.0)
        if self.axis_length_mm is not None:
            self.total_width.setValue(self.axis_length_mm)
            self.total_width.setEnabled(False)
        self.positions = QtWidgets.QSpinBox()
        self.positions.setRange(1, 50)
        positions_key = "source_service_positions" if self.axis_length_mm is not None else "service_positions"
        self.positions.setValue(self.params.GetInt(positions_key, 3 if self.axis_length_mm is not None else 2))
        self.desk_depth = self._length("desk_depth_mm", 100.0, 3000.0, 50.0, 600.0)
        self.desk_height = self._length("desk_height_mm", 500.0, 1500.0, 10.0, 740.0)
        self.counter_depth = self._length("counter_depth_mm", 100.0, 1500.0, 50.0, 300.0)
        self.glass_top = self._length("glass_top_mm", 800.0, 3000.0, 50.0, 1800.0)
        self.glass_opening_enabled = QtWidgets.QCheckBox("Crear una abertura real por puesto")
        self.glass_opening_enabled.setChecked(
            self.params.GetBool("glass_opening_enabled", True)
        )
        self.glass_opening_width = self._length(
            "glass_opening_width_mm", 1.0, 3000.0, 10.0, 300.0
        )
        self.glass_opening_height = self._length(
            "glass_opening_height_mm", 1.0, 2000.0, 10.0, 300.0
        )
        self.glass_opening_bottom = self._length(
            "glass_opening_bottom_mm", 0.0, 3000.0, 10.0, 740.0
        )
        self.staff_depth = self._length("staff_zone_depth_mm", 100.0, 10000.0, 100.0, 1800.0)
        self.public_depth = self._length("public_zone_depth_mm", 100.0, 10000.0, 100.0, 1500.0)
        self.staff_side = QtWidgets.QComboBox()
        self.staff_side.addItems(["Izquierda", "Derecha"])
        saved_side = self.params.GetString("staff_side", "left").strip().lower()
        self.staff_side.setCurrentIndex(1 if saved_side == "right" else 0)
        self.invert_direction = QtWidgets.QCheckBox("Invertir direccion P0 / P1")
        self.invert_direction.setChecked(self.params.GetBool("invert_direction", False))
        self.create_3d = QtWidgets.QCheckBox("Crear mobiliario 3D")
        self.create_3d.setChecked(self.params.GetBool("create_3d_furniture", True))
        self.create_3d.setVisible(self.axis_length_mm is None)
        self.create_zones = QtWidgets.QCheckBox("Mostrar areas de atencion (opcional)")
        self.create_zones.setChecked(
            self.params.GetBool("show_service_areas", False)
            if self.axis_length_mm is not None
            else self.params.GetBool("create_functional_zones", True)
        )
        form.addRow("Ancho total del frente", self.total_width)
        form.addRow("Cantidad de puestos", self.positions)
        form.addRow("Lado del funcionario", self.staff_side)
        form.addRow("Profundidad de escritorio", self.desk_depth)
        form.addRow("Altura de mostrador", self.desk_height)
        form.addRow("Profundidad de mostrador", self.counter_depth)
        form.addRow("Cota superior del vidrio", self.glass_top)
        if self.axis_length_mm is not None:
            form.addRow("", self.glass_opening_enabled)
            form.addRow("Ancho de abertura del vidrio", self.glass_opening_width)
            form.addRow("Alto de abertura del vidrio", self.glass_opening_height)
            form.addRow("Cota inferior de abertura", self.glass_opening_bottom)
        form.addRow("Profundidad area de funcionario", self.staff_depth)
        form.addRow("Profundidad area publica", self.public_depth)
        form.addRow("", self.invert_direction)
        form.addRow("", self.create_3d)
        form.addRow("", self.create_zones)
        layout.addLayout(form)

        self.summary = QtWidgets.QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("QLabel { padding: 8px; background: palette(alternate-base); }")
        layout.addWidget(self.summary)
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        for widget in (
            self.total_width,
            self.positions,
            self.desk_depth,
            self.desk_height,
            self.counter_depth,
            self.glass_top,
            self.glass_opening_width,
            self.glass_opening_height,
            self.glass_opening_bottom,
            self.staff_depth,
            self.public_depth,
        ):
            widget.valueChanged.connect(self._update_summary)
        self.staff_side.currentIndexChanged.connect(self._update_summary)
        self.invert_direction.toggled.connect(self._update_summary)
        self.glass_opening_enabled.toggled.connect(self._update_summary)
        self._update_summary()

    def _length(self, key, minimum, maximum, step, default):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(1)
        spin.setSuffix(" mm")
        spin.setValue(self.params.GetFloat(key, default))
        return spin

    def options(self):
        defaults = PlatformOptions()
        values = replace(
            defaults,
            total_width_mm=float(self.total_width.value()),
            service_positions=int(self.positions.value()),
            desk_depth_mm=float(self.desk_depth.value()),
            desk_height_mm=float(self.desk_height.value()),
            counter_depth_mm=float(self.counter_depth.value()),
            glass_top_mm=float(self.glass_top.value()),
            glass_opening_width_mm=float(self.glass_opening_width.value()),
            glass_opening_height_mm=float(self.glass_opening_height.value()),
            glass_opening_bottom_mm=float(self.glass_opening_bottom.value()),
            glass_opening_enabled=bool(self.glass_opening_enabled.isChecked()),
            divider_depth_mm=float(self.desk_depth.value()),
            staff_zone_depth_mm=float(self.staff_depth.value()),
            public_zone_depth_mm=float(self.public_depth.value()),
            create_3d_furniture=(
                True if self.axis_length_mm is not None else bool(self.create_3d.isChecked())
            ),
            create_functional_zones=(
                False if self.axis_length_mm is not None else bool(self.create_zones.isChecked())
            ),
            staff_side="right" if self.staff_side.currentIndex() == 1 else "left",
            invert_direction=bool(self.invert_direction.isChecked()),
            show_service_areas=(
                bool(self.create_zones.isChecked()) if self.axis_length_mm is not None else False
            ),
        )
        self.params.SetFloat("total_width_mm", values.total_width_mm)
        self.params.SetInt(
            "source_service_positions" if self.axis_length_mm is not None else "service_positions",
            values.service_positions,
        )
        self.params.SetFloat("desk_depth_mm", values.desk_depth_mm)
        self.params.SetFloat("desk_height_mm", values.desk_height_mm)
        self.params.SetFloat("counter_depth_mm", values.counter_depth_mm)
        self.params.SetFloat("glass_top_mm", values.glass_top_mm)
        self.params.SetFloat("glass_opening_width_mm", values.glass_opening_width_mm)
        self.params.SetFloat("glass_opening_height_mm", values.glass_opening_height_mm)
        self.params.SetFloat("glass_opening_bottom_mm", values.glass_opening_bottom_mm)
        self.params.SetBool("glass_opening_enabled", values.glass_opening_enabled)
        self.params.SetFloat("staff_zone_depth_mm", values.staff_zone_depth_mm)
        self.params.SetFloat("public_zone_depth_mm", values.public_zone_depth_mm)
        self.params.SetBool("create_3d_furniture", values.create_3d_furniture)
        self.params.SetBool("create_functional_zones", values.create_functional_zones)
        self.params.SetString("staff_side", values.staff_side)
        self.params.SetBool("invert_direction", values.invert_direction)
        self.params.SetBool("show_service_areas", values.show_service_areas)
        return values

    def _update_summary(self, *_args):
        try:
            values = self.options()
            layout = (
                calculate_line_layout(values)
                if self.axis_length_mm is not None
                else calculate_layout(values)
            )
            self.summary.setText(
                "Ancho por puesto: %.1f mm\n"
                "%s: %.1f mm\n"
                "Divisiones: %d\n"
                "Lado del funcionario: %s\n"
                "Profundidad total aproximada: %.1f mm"
                % (
                    layout.position_width_mm,
                    "Ancho recomendado" if self.axis_length_mm is not None else "Ancho minimo requerido",
                    layout.minimum_total_width_mm,
                    layout.divider_count,
                    "derecha" if values.staff_side == "right" else "izquierda",
                    layout.approximate_total_depth_mm,
                )
            )
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        except PlatformValidationError as exc:
            self.summary.setText("No se puede generar: %s" % exc)
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
