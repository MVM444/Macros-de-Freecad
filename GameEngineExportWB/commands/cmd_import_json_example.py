"""Command to import a Quick Example JSON payload.

Fecha: 2026-07-11.
Objetivo: pegar JSON de ChatGPT y reconstruir una casa u oficina BIM.
Instrucciones principales:
- Usar dialogo local, sin API externa.
- Aceptar JSON puro o texto con JSON embebido.
- Delegar validacion y generacion a core.json_importer.
"""

from __future__ import annotations

import importlib
import os

import FreeCAD
import FreeCADGui

from ..core import json_importer
from ..ui.panel_export import _ensure_qt_compat


_ensure_qt_compat()

from PySide import QtGui  # noqa: E402


LOG_PREFIX = "[GAMEEXPORT] "
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "import_json_example.svg")
).replace(os.sep, "/")


class CommandClass:
    """FreeCAD command wrapper for importing quick example JSON."""

    CommandName = "GameEngineExport_ImportJSONExample"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "Importar JSON / Import JSON",
            "ToolTip": "Pegar JSON de ChatGPT y reconstruir casa u oficina",
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        global json_importer
        importlib.invalidate_caches()
        json_importer = importlib.reload(json_importer)
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Opening JSON import dialog\n")
        dialog = ImportJSONDialog()
        dialog.exec_()

    def IsActive(self):  # noqa: N802
        return True


class ImportJSONDialog(QtGui.QDialog):
    """Dialog for paste/load JSON and generating the model."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GameEngineExport - Import JSON")
        self.resize(760, 560)
        self._build_ui()

    def _build_ui(self):
        layout = QtGui.QVBoxLayout(self)

        self.text = QtGui.QPlainTextEdit()
        self.text.setPlaceholderText("Pegue aqui JSON puro o texto con un bloque JSON.")
        layout.addWidget(self.text, 1)

        top_buttons = QtGui.QHBoxLayout()
        self.btn_paste = QtGui.QPushButton("Pegar portapapeles")
        self.btn_file = QtGui.QPushButton("Cargar archivo JSON")
        self.btn_paste.clicked.connect(self._paste_clipboard)
        self.btn_file.clicked.connect(self._load_file)
        top_buttons.addWidget(self.btn_paste)
        top_buttons.addWidget(self.btn_file)
        top_buttons.addStretch(1)
        layout.addLayout(top_buttons)

        self.clear_previous = QtGui.QCheckBox("Borrar ejemplos rapidos anteriores")
        self.clear_previous.setChecked(True)
        self.copy_context = QtGui.QCheckBox("Copiar contexto actualizado al portapapeles")
        self.copy_context.setChecked(False)
        layout.addWidget(self.clear_previous)
        layout.addWidget(self.copy_context)

        bottom = QtGui.QHBoxLayout()
        bottom.addStretch(1)
        self.btn_generate = QtGui.QPushButton("Generar")
        self.btn_cancel = QtGui.QPushButton("Cancelar")
        self.btn_generate.clicked.connect(self._generate)
        self.btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(self.btn_generate)
        bottom.addWidget(self.btn_cancel)
        layout.addLayout(bottom)

    def _paste_clipboard(self):
        app = QtGui.QApplication.instance()
        if app is None:
            return
        self.text.setPlainText(app.clipboard().text())

    def _load_file(self):
        path, _selected = QtGui.QFileDialog.getOpenFileName(
            self,
            "Cargar archivo JSON",
            "",
            "JSON (*.json);;Texto (*.txt);;Todos (*.*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                self.text.setPlainText(handle.read())
        except Exception as exc:
            QtGui.QMessageBox.critical(self, "GameEngineExport - Import JSON", str(exc))

    def _generate(self):
        raw = self.text.toPlainText()
        try:
            payload = json_importer.load_payload_from_text(raw)
            root, _payload, context_text = json_importer.generate_quick_example_from_payload(
                payload,
                {
                    "clear_previous": bool(self.clear_previous.isChecked()),
                    "copy_context": bool(self.copy_context.isChecked()),
                },
            )
            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(root)
                FreeCADGui.SendMsgToActiveView("ViewFit")
            except Exception:
                pass
            if self.copy_context.isChecked():
                app = QtGui.QApplication.instance()
                if app is not None:
                    app.clipboard().setText(context_text)
            FreeCAD.Console.PrintMessage(LOG_PREFIX + "JSON example imported: " + str(root.Label) + "\n")
            self.accept()
        except Exception as exc:
            FreeCAD.Console.PrintError(LOG_PREFIX + "JSON import error: " + str(exc) + "\n")
            QtGui.QMessageBox.critical(self, "GameEngineExport - Import JSON", str(exc))
