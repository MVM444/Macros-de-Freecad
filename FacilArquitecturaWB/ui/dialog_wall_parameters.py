"""Shared dialog for completing the wall contract on generic Sketches."""

from __future__ import annotations

import FreeCAD
from PySide import QtWidgets

from ..core.bim_utils import wall_thickness_from_sketch


PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/WallsBIM"


class WallSketchParametersDialog(QtWidgets.QDialog):
    """Ask for metadata needed to use generic sketches as wall centerlines."""

    def __init__(self, sketches, params, parent=None):
        super().__init__(parent)
        self.params_store = FreeCAD.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle("FA Convertir Sketch a eje de muro BIM")
        self.setMinimumWidth(520)
        layout = QtWidgets.QVBoxLayout(self)
        names = [str(getattr(obj, "Label", getattr(obj, "Name", "Sketch"))) for obj in sketches]
        shown = names[:8]
        if len(names) > len(shown):
            shown.append("... y %d mas" % (len(names) - len(shown)))
        intro = QtWidgets.QLabel(
            "Los siguientes Sketches no tienen todos los metadatos de muro:\n\n- "
            + "\n- ".join(shown)
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        default_thickness = _first_positive(
            [wall_thickness_from_sketch(sketch) for sketch in sketches],
            self.params_store.GetFloat(
                "wall_thickness_mm", float(params.get("int_wall_thickness_mm", 100.0))
            ),
        )
        default_height = _first_positive(
            [_quantity_value(getattr(sketch, "FA_WallHeight", 0.0)) for sketch in sketches],
            self.params_store.GetFloat(
                "wall_height_mm", float(params.get("wall_height_mm", 3000.0))
            ),
        )
        form = QtWidgets.QFormLayout()
        self.thickness = QtWidgets.QDoubleSpinBox()
        self.thickness.setRange(1.0, 5000.0)
        self.thickness.setDecimals(1)
        self.thickness.setSingleStep(10.0)
        self.thickness.setSuffix(" mm")
        self.thickness.setValue(default_thickness)
        self.height = QtWidgets.QDoubleSpinBox()
        self.height.setRange(100.0, 50000.0)
        self.height.setDecimals(1)
        self.height.setSingleStep(100.0)
        self.height.setSuffix(" mm")
        self.height.setValue(default_height)
        self.wall_type = QtWidgets.QComboBox()
        self.wall_type.addItem("Muro interior", "interior")
        self.wall_type.addItem("Muro exterior", "exterior")
        self.wall_type.addItem("Muro generico", "muro")
        saved_type = self.params_store.GetString("wall_type", "interior")
        index = self.wall_type.findData(saved_type)
        self.wall_type.setCurrentIndex(index if index >= 0 else 0)
        form.addRow("Espesor para datos faltantes", self.thickness)
        form.addRow("Altura para datos faltantes", self.height)
        form.addRow("Clasificacion", self.wall_type)
        layout.addLayout(form)

        note = QtWidgets.QLabel(
            "Solo se completan valores faltantes. Las dimensiones positivas existentes y la geometria "
            "del Sketch se conservan. El Sketch seleccionado pasa a ser la Base parametrica del muro."
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
        result = {
            "thickness": float(self.thickness.value()),
            "height": float(self.height.value()),
            "wall_type": str(self.wall_type.currentData()),
        }
        self.params_store.SetFloat("wall_thickness_mm", result["thickness"])
        self.params_store.SetFloat("wall_height_mm", result["height"])
        self.params_store.SetString("wall_type", result["wall_type"])
        return result


def _quantity_value(value):
    try:
        return float(getattr(value, "Value", value))
    except Exception:
        return 0.0


def _first_positive(values, fallback):
    for value in values:
        if float(value) > 0.0:
            return float(value)
    return float(fallback)

