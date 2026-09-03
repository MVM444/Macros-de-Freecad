"""Small action chooser for FA Tabla de ventanas."""

from __future__ import annotations

from PySide import QtWidgets


ACTIONS = (
    ("open", "Crear / abrir tabla", "Crea o abre Spreadsheet_Ventanas."),
    ("extract", "Extraer del modelo", "Lee ventanas BIM nativas y actualiza la tabla."),
    ("validate", "Validar contra Sketch", "Dry-run con MATCH, CAMBIO, NO_MATCH y AMBIGUO."),
    ("apply", "Aplicar tabla", "Crea o actualiza solo coincidencias seguras."),
    ("import", "Importar CSV", "Importa mediante Spreadsheet::Sheet.importFile()."),
    ("export", "Exportar CSV", "Exporta mediante Spreadsheet::Sheet.exportFile()."),
)


class WindowTableDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.action_name = ""
        self.setWindowTitle("FA Tabla de ventanas")
        self.setMinimumWidth(430)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel(
            "La geometría procede del Sketch actual; altura, antepecho y preset "
            "proceden de la tabla. Validar no modifica ventanas."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        for action_name, title, tooltip in ACTIONS:
            button = QtWidgets.QPushButton(title)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _checked=False, name=action_name: self._choose(name))
            layout.addWidget(button)
        cancel = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel)
        cancel.rejected.connect(self.reject)
        layout.addWidget(cancel)

    def _choose(self, action_name):
        self.action_name = str(action_name)
        self.accept()
