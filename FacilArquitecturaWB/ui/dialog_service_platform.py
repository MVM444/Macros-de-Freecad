"""Small PySide dialog for a parametric service platform front."""

from __future__ import annotations

import FreeCAD
from PySide import QtWidgets

from ..modules.service_platform.calculator import calculate_layout
from ..modules.service_platform.model import PlatformOptions
from ..modules.service_platform.validation import PlatformValidationError


PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/ServicePlatform"


class ServicePlatformDialog(QtWidgets.QDialog):
    """Collect the initial parameters and preview the derived dimensions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.params = FreeCAD.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle("FA Frente de plataforma de atencion")
        self.setMinimumWidth(500)
        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel(
            "Genera un frente modular con sketches maestros, sobres de trabajo, "
            "divisiones y zonas funcionales. La referencia PL-01 orienta los valores iniciales."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QtWidgets.QFormLayout()
        self.total_width = self._length("total_width_mm", 100.0, 100000.0, 100.0, 3840.0)
        self.positions = QtWidgets.QSpinBox()
        self.positions.setRange(1, 50)
        self.positions.setValue(self.params.GetInt("service_positions", 2))
        self.desk_depth = self._length("desk_depth_mm", 100.0, 3000.0, 50.0, 600.0)
        self.staff_depth = self._length("staff_zone_depth_mm", 100.0, 10000.0, 100.0, 1800.0)
        self.public_depth = self._length("public_zone_depth_mm", 100.0, 10000.0, 100.0, 1500.0)
        self.create_3d = QtWidgets.QCheckBox("Crear mobiliario 3D")
        self.create_3d.setChecked(self.params.GetBool("create_3d_furniture", True))
        self.create_zones = QtWidgets.QCheckBox("Crear zonas funcionales")
        self.create_zones.setChecked(self.params.GetBool("create_functional_zones", True))
        form.addRow("Ancho total del frente", self.total_width)
        form.addRow("Cantidad de puestos", self.positions)
        form.addRow("Profundidad de escritorio", self.desk_depth)
        form.addRow("Profundidad area de funcionario", self.staff_depth)
        form.addRow("Profundidad area publica", self.public_depth)
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

        for widget in (self.total_width, self.positions, self.desk_depth, self.staff_depth, self.public_depth):
            widget.valueChanged.connect(self._update_summary)
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
        values = PlatformOptions(
            total_width_mm=float(self.total_width.value()),
            service_positions=int(self.positions.value()),
            desk_depth_mm=float(self.desk_depth.value()),
            desk_height_mm=defaults.desk_height_mm,
            desk_thickness_mm=defaults.desk_thickness_mm,
            side_margin_mm=defaults.side_margin_mm,
            divider_thickness_mm=defaults.divider_thickness_mm,
            divider_depth_mm=float(self.desk_depth.value()),
            divider_height_mm=defaults.divider_height_mm,
            staff_zone_depth_mm=float(self.staff_depth.value()),
            public_zone_depth_mm=float(self.public_depth.value()),
            front_offset_mm=defaults.front_offset_mm,
            minimum_position_width_mm=defaults.minimum_position_width_mm,
            create_3d_furniture=bool(self.create_3d.isChecked()),
            create_functional_zones=bool(self.create_zones.isChecked()),
        )
        self.params.SetFloat("total_width_mm", values.total_width_mm)
        self.params.SetInt("service_positions", values.service_positions)
        self.params.SetFloat("desk_depth_mm", values.desk_depth_mm)
        self.params.SetFloat("staff_zone_depth_mm", values.staff_zone_depth_mm)
        self.params.SetFloat("public_zone_depth_mm", values.public_zone_depth_mm)
        self.params.SetBool("create_3d_furniture", values.create_3d_furniture)
        self.params.SetBool("create_functional_zones", values.create_functional_zones)
        return values

    def _update_summary(self, *_args):
        try:
            values = self.options()
            layout = calculate_layout(values)
            self.summary.setText(
                "Ancho por puesto: %.1f mm\n"
                "Ancho minimo requerido: %.1f mm\n"
                "Divisiones: %d\n"
                "Profundidad total aproximada: %.1f mm"
                % (
                    layout.position_width_mm,
                    layout.minimum_total_width_mm,
                    layout.divider_count,
                    layout.approximate_total_depth_mm,
                )
            )
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        except PlatformValidationError as exc:
            self.summary.setText("No se puede generar: %s" % exc)
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
