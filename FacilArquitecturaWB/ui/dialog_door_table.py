"""Action chooser for FA Tabla de puertas.

Nombre: dialog_door_table.py
Proposito: exponer un unico dialogo pequeno para operar Spreadsheet_Puertas.
Funcionamiento: selecciona crear/abrir, extraer, validar, aplicar, importar o exportar.
FreeCAD objetivo: 1.1.3
Version: 0.1.0
Fecha y hora: 2026-08-28 17:42 UTC-06:00
Mantenimiento: conservar la GUI delgada; la logica pertenece a core/door_table_utils.py.
"""

from __future__ import annotations

from PySide import QtWidgets


ACTIONS = (
    ("open", "Crear / abrir tabla", "Crea o abre Spreadsheet_Puertas dentro de 06_Tables."),
    ("extract", "Extraer del modelo", "Lee puertas BIM nativas y actualiza la tabla."),
    ("validate", "Validar contra Sketch", "Dry-run con MATCH, CAMBIO, NO_MATCH y AMBIGUO."),
    ("apply", "Aplicar tabla", "Crea o actualiza solo coincidencias seguras, conservando tipo, bisagra y apertura."),
    ("import", "Importar CSV", "Importa mediante Spreadsheet::Sheet.importFile()."),
    ("export", "Exportar CSV", "Exporta mediante Spreadsheet::Sheet.exportFile()."),
)


class DoorTableDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.action_name = ""
        self.setWindowTitle("FA Tabla de puertas")
        self.setMinimumWidth(470)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel(
            "La geometria (posicion, orientacion y ancho) procede del Sketch actual. "
            "La tabla conserva altura, tipo de puerta, bisagra y sentido de apertura. "
            "Validar no modifica las puertas."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        for action_name, title, tooltip in ACTIONS:
            button = QtWidgets.QPushButton(title)
            button.setToolTip(tooltip)
            button.clicked.connect(
                lambda _checked=False, name=action_name: self._choose(name)
            )
            layout.addWidget(button)
        cancel = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel)
        cancel.rejected.connect(self.reject)
        layout.addWidget(cancel)

    def _choose(self, action_name):
        self.action_name = str(action_name)
        self.accept()
