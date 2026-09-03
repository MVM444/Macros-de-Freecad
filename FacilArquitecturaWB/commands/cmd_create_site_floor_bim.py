"""FA_CreateSiteFloorBIM command.

Descripcion: crea losa BIM y terreno desde sketches arquitectonicos.
Funcion principal: integrar Site -> Building -> Level -> Slab y recortar el terreno bajo la losa.
Instrucciones: conservar parametros entre ejecuciones, dependencias nativas y una transaccion para Ctrl-Z.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-08-19 21:32 UTC-06:00.
Version: 0.2.0.
"""

from __future__ import annotations

import os
import time

import FreeCAD
import FreeCADGui
from PySide import QtWidgets

from ..core.bim_structure_utils import ensure_bim_structure, is_building, selected_level
from ..core.command_errors import UserFacingError, handle_command_exception
from ..core.project_structure import active_or_new_document, msg
from ..core.site_floor_utils import collect_plan_sketches, create_site_floor_from_sketches

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "site_floor_bim.svg")
).replace(os.sep, "/")
COMMAND_VERSION = str(int(time.time()))
PREFERENCES_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB/SiteFloor"


class SiteFloorDialog(QtWidgets.QDialog):
    """Persistent options for the BIM slab and disposable test terrain."""

    def __init__(self, source_count, selected_sources, parent=None):
        super().__init__(parent)
        self.params = FreeCAD.ParamGet(PREFERENCES_PATH)
        self.setWindowTitle("FA Piso BIM y terreno")
        self.setMinimumWidth(430)

        layout = QtWidgets.QVBoxLayout(self)
        source_text = (
            "%d sketches seleccionados" % source_count
            if selected_sources
            else "%d sketches detectados automaticamente" % source_count
        )
        source_label = QtWidgets.QLabel(
            source_text + "\nFuentes: centros de muros, ventanas y puertas."
        )
        source_label.setWordWrap(True)
        layout.addWidget(source_label)

        form = QtWidgets.QFormLayout()
        self.floor_thickness = self._length_spin(50.0, 1000.0, 10.0)
        self.floor_thickness.setValue(self.params.GetFloat("floor_thickness_mm", 150.0))
        form.addRow("Espesor del piso", self.floor_thickness)

        self.floor_overhang = self._length_spin(0.0, 3000.0, 50.0)
        self.floor_overhang.setValue(self.params.GetFloat("floor_overhang_mm", 100.0))
        form.addRow("Sobresaliente del piso", self.floor_overhang)

        self.floor_top_z = self._length_spin(-10000.0, 10000.0, 50.0)
        self.floor_top_z.setValue(self.params.GetFloat("floor_top_z_mm", 0.0))
        form.addRow("Cota superior", self.floor_top_z)

        self.create_terrain = QtWidgets.QCheckBox("Crear terreno irregular de prueba")
        self.create_terrain.setChecked(self.params.GetBool("create_test_terrain", True))
        form.addRow("", self.create_terrain)

        self.cut_terrain = QtWidgets.QCheckBox("Recortar terreno bajo la losa")
        self.cut_terrain.setChecked(self.params.GetBool("cut_terrain_under_building", True))
        form.addRow("", self.cut_terrain)

        self.terrain_margin = self._length_spin(500.0, 50000.0, 500.0)
        self.terrain_margin.setValue(self.params.GetFloat("terrain_margin_mm", 5000.0))
        form.addRow("Margen del terreno", self.terrain_margin)

        self.pad_margin = self._length_spin(0.0, 10000.0, 250.0)
        self.pad_margin.setValue(self.params.GetFloat("pad_margin_mm", 1000.0))
        form.addRow("Margen plataforma plana", self.pad_margin)

        self.terrain_variation = self._length_spin(0.0, 5000.0, 50.0)
        self.terrain_variation.setValue(self.params.GetFloat("terrain_variation_mm", 500.0))
        form.addRow("Relieve de prueba", self.terrain_variation)

        self.terrain_seed = QtWidgets.QSpinBox()
        self.terrain_seed.setRange(0, 2147483647)
        self.terrain_seed.setValue(self.params.GetInt("terrain_seed", 12345))
        form.addRow("Semilla del terreno", self.terrain_seed)

        self.replace_previous = QtWidgets.QCheckBox("Reemplazar piso y terreno anteriores")
        self.replace_previous.setChecked(self.params.GetBool("replace_previous", True))
        form.addRow("", self.replace_previous)
        layout.addLayout(form)

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
        spin.setSingleStep(float(step))
        spin.setDecimals(1)
        spin.setSuffix(" mm")
        return spin

    def options(self):
        values = {
            "floor_thickness_mm": float(self.floor_thickness.value()),
            "floor_overhang_mm": float(self.floor_overhang.value()),
            "floor_top_z_mm": float(self.floor_top_z.value()),
            "create_test_terrain": bool(self.create_terrain.isChecked()),
            "cut_terrain_under_building": bool(self.cut_terrain.isChecked()),
            "terrain_margin_mm": float(self.terrain_margin.value()),
            "pad_margin_mm": float(self.pad_margin.value()),
            "terrain_variation_mm": float(self.terrain_variation.value()),
            "terrain_seed": int(self.terrain_seed.value()),
            "replace_previous": bool(self.replace_previous.isChecked()),
        }
        for key in (
            "floor_thickness_mm",
            "floor_overhang_mm",
            "floor_top_z_mm",
            "terrain_margin_mm",
            "pad_margin_mm",
            "terrain_variation_mm",
        ):
            self.params.SetFloat(key, values[key])
        self.params.SetInt("terrain_seed", values["terrain_seed"])
        self.params.SetBool("create_test_terrain", values["create_test_terrain"])
        self.params.SetBool("cut_terrain_under_building", values["cut_terrain_under_building"])
        self.params.SetBool("replace_previous", values["replace_previous"])
        return values


def _building_parent(level):
    """Return the unique native Building parent of a Level when available."""
    if level is None:
        return None
    parents = [obj for obj in list(getattr(level, "InList", []) or []) if is_building(obj)]
    return parents[0] if len(parents) == 1 else None


class CommandClass:
    """FreeCAD command for generating a BIM slab and test terrain."""

    CommandName = "FA_CreateSiteFloorBIM_" + COMMAND_VERSION

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "FA Piso BIM y terreno",
            "ToolTip": (
                "Crear una losa BIM desde sketches de muros, ventanas y puertas, "
                "integrada al Level, con terreno de prueba recortado bajo la losa."
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        doc = None
        transaction_open = False
        try:
            doc = active_or_new_document()
            selection = list(FreeCADGui.Selection.getSelection() or [])
            sketches = collect_plan_sketches(doc, selection=selection)
            if selection and not sketches:
                raise UserFacingError(
                    "La seleccion no contiene sketches de muros, ventanas o puertas."
                )
            if not sketches:
                raise UserFacingError(
                    "No se encontraron sketches de muros, ventanas o puertas con geometria."
                )

            dialog = SiteFloorDialog(
                len(sketches),
                bool(selection),
                parent=FreeCADGui.getMainWindow(),
            )
            accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if accepted != QtWidgets.QDialog.Accepted:
                return
            options = dialog.options()

            preferred_level = selected_level(selection)
            preferred_building = _building_parent(preferred_level)

            try:
                doc.openTransaction("FA Piso BIM y terreno")
                transaction_open = True
            except Exception:
                transaction_open = False
            spatial = ensure_bim_structure(
                doc,
                building=preferred_building,
                level=preferred_level,
            )
            created = create_site_floor_from_sketches(
                doc,
                doc.getObject("FA_BIM"),
                sketches,
                options,
                building=spatial["building"],
                level=spatial["level"],
            )
            doc.recompute()
            if transaction_open:
                doc.commitTransaction()
                transaction_open = False

            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(created["site"])
                FreeCADGui.Selection.addSelection(created["slab"])
            except Exception:
                pass
            msg("FA_CreateSiteFloorBIM completado.")
        except Exception as exc:
            if transaction_open and doc is not None:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            handle_command_exception("FA Piso BIM y terreno", exc)

    def IsActive(self):  # noqa: N802
        return True


def register():
    command = CommandClass()
    FreeCADGui.addCommand(command.CommandName, command)
    return command
