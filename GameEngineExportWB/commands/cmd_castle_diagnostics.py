"""FreeCAD adapter for Castle Model Viewer diagnostics."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import FreeCAD
import FreeCADGui

try:
    from PySide import QtCore, QtGui
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets

    for name in (
        "QApplication",
        "QCheckBox",
        "QComboBox",
        "QDialog",
        "QDialogButtonBox",
        "QFileDialog",
        "QFormLayout",
        "QHBoxLayout",
        "QLabel",
        "QLineEdit",
        "QMessageBox",
        "QProgressDialog",
        "QPushButton",
        "QSpinBox",
        "QVBoxLayout",
    ):
        if not hasattr(QtGui, name) and hasattr(QtWidgets, name):
            setattr(QtGui, name, getattr(QtWidgets, name))

from . import cmd_analyze_x3d
from ..core import castle_diagnostics


LOG_PREFIX = "[GAMEEXPORT] "
PARAM_GROUP = "User parameter:Plugins/GameEngineExportWB"
MODE_KEY = "castle_diagnostics_mode"
VALIDATE_KEY = "castle_diagnostics_validate"
SHADER_DEBUG_KEY = "castle_diagnostics_shader_debug"
VIEWPOINT_KEY = "castle_diagnostics_viewpoint"
WIDTH_KEY = "castle_diagnostics_width"
HEIGHT_KEY = "castle_diagnostics_height"
AA_KEY = "castle_diagnostics_anti_alias"
ICON_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "resources",
        "icons",
        "castle_diagnostics.svg",
    )
).replace(os.sep, "/")


class DiagnosticDialog(QtGui.QDialog):
    def __init__(self, x3d_path: Path, parent=None):
        super().__init__(parent)
        self.params = FreeCAD.ParamGet(PARAM_GROUP)
        self.x3d_path = Path(x3d_path)
        self.setWindowTitle("Game Engine Export - Diagn\u00f3stico Castle")
        self.setMinimumWidth(650)
        self._build()

    def _build(self):
        layout = QtGui.QVBoxLayout(self)
        source = QtGui.QLabel("X3D: " + str(self.x3d_path))
        source.setWordWrap(True)
        layout.addWidget(source)

        form = QtGui.QFormLayout()
        self.mode = QtGui.QComboBox()
        self.mode.addItem("Analizar y abrir Castle", "interactive")
        self.mode.addItem("Captura automatica desde GameStart", "capture")
        self.mode.addItem("Solo analizar", "analyze")
        saved_mode = self.params.GetString(MODE_KEY, "interactive")
        saved_index = self.mode.findData(saved_mode)
        if saved_index >= 0:
            self.mode.setCurrentIndex(saved_index)
        form.addRow("Modo", self.mode)

        viewer_row = QtGui.QHBoxLayout()
        self.viewer = QtGui.QLineEdit(self.params.GetString("cge_path", ""))
        browse = QtGui.QPushButton("Examinar")
        browse.clicked.connect(self._browse)
        viewer_row.addWidget(self.viewer, 1)
        viewer_row.addWidget(browse)
        form.addRow("Castle Model Viewer", viewer_row)

        self.validate = QtGui.QCheckBox("Validar con castle-model-converter")
        self.validate.setChecked(self.params.GetBool(VALIDATE_KEY, True))
        form.addRow("", self.validate)
        self.shader_debug = QtGui.QCheckBox("Registrar shaders GLSL")
        self.shader_debug.setChecked(self.params.GetBool(SHADER_DEBUG_KEY, True))
        form.addRow("", self.shader_debug)

        self.viewpoint = QtGui.QLineEdit(
            self.params.GetString(VIEWPOINT_KEY, "GameStart") or "GameStart"
        )
        form.addRow("Viewpoint", self.viewpoint)
        self.width = QtGui.QSpinBox()
        self.width.setRange(320, 7680)
        self.width.setValue(self.params.GetInt(WIDTH_KEY, 1600))
        form.addRow("Ancho captura", self.width)
        self.height = QtGui.QSpinBox()
        self.height.setRange(240, 4320)
        self.height.setValue(self.params.GetInt(HEIGHT_KEY, 900))
        form.addRow("Alto captura", self.height)
        self.aa = QtGui.QSpinBox()
        self.aa.setRange(0, 4)
        self.aa.setValue(self.params.GetInt(AA_KEY, 4))
        form.addRow("Antialias", self.aa)
        layout.addLayout(form)

        note = QtGui.QLabel(
            "No modifica el FCStd ni el X3D. Los resultados se guardan en "
            "_castle_debug. La captura y el registro de Castle pueden continuar "
            "en segundo plano."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.mode.currentIndexChanged.connect(self._update_controls)
        self._update_controls()

    def _browse(self):
        selected, _ = QtGui.QFileDialog.getOpenFileName(
            self,
            "Seleccionar Castle Model Viewer",
            self.viewer.text().strip() or os.path.expanduser("~"),
        )
        if selected:
            self.viewer.setText(selected)

    def _update_controls(self):
        capture = self.mode.currentData() == "capture"
        needs_viewer = self.mode.currentData() != "analyze"
        # Keep the path editable in analyze-only mode because the companion
        # converter is discovered beside Castle Model Viewer.
        self.viewer.setEnabled(True)
        self.viewpoint.setEnabled(capture)
        self.width.setEnabled(capture)
        self.height.setEnabled(capture)
        self.aa.setEnabled(capture)
        self.shader_debug.setEnabled(needs_viewer)

    def options(self):
        return {
            "mode": str(self.mode.currentData()),
            "viewer_path": self.viewer.text().strip(),
            "validate": bool(self.validate.isChecked()),
            "shader_debug": bool(self.shader_debug.isChecked()),
            "viewpoint": self.viewpoint.text().strip() or "GameStart",
            "width": int(self.width.value()),
            "height": int(self.height.value()),
            "anti_alias": int(self.aa.value()),
        }

    def save_preferences(self, options):
        self.params.SetString(MODE_KEY, options["mode"])
        self.params.SetBool(VALIDATE_KEY, options["validate"])
        self.params.SetBool(SHADER_DEBUG_KEY, options["shader_debug"])
        self.params.SetString(VIEWPOINT_KEY, options["viewpoint"])
        self.params.SetInt(WIDTH_KEY, options["width"])
        self.params.SetInt(HEIGHT_KEY, options["height"])
        self.params.SetInt(AA_KEY, options["anti_alias"])
        if options["viewer_path"]:
            self.params.SetString("cge_path", options["viewer_path"])


class CommandClass:
    CommandName = "GameEngineExport_CastleDiagnostics"

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": "Diagn\u00f3stico Castle / Castle Diagnostics",
            "ToolTip": (
                "Analiza y valida el X3D, registra shaders y puede abrir Castle "
                "o generar una captura desde GameStart"
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        path = cmd_analyze_x3d._choose_x3d_path()
        if path is None:
            FreeCAD.Console.PrintMessage(LOG_PREFIX + "Castle diagnostics cancelled\n")
            return
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Castle diagnostics X3D: " + str(path) + "\n"
        )

        dialog = DiagnosticDialog(path, FreeCADGui.getMainWindow())
        if dialog.exec_() != QtGui.QDialog.Accepted:
            return
        options = dialog.options()
        dialog.save_preferences(options)
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Castle diagnostics mode: " + options["mode"] + "\n"
        )

        def diagnostic_log(level, message):
            text = LOG_PREFIX + "[" + str(level).upper() + "] " + str(message) + "\n"
            if str(level).upper() == "WARN":
                FreeCAD.Console.PrintWarning(text)
            elif str(level).upper() == "ERROR":
                FreeCAD.Console.PrintError(text)
            else:
                FreeCAD.Console.PrintMessage(text)

        progress = QtGui.QProgressDialog(
            "Analizando X3D sin modificarlo...",
            "Cancelar",
            0,
            100,
            FreeCADGui.getMainWindow(),
        )
        progress.setWindowTitle("Diagn\u00f3stico Castle")
        progress.setMinimumDuration(0)

        def update_progress(bytes_read, total_hint):
            if total_hint > 0:
                progress.setRange(0, 100)
                progress.setValue(min(99, int(100.0 * bytes_read / total_hint)))
            else:
                progress.setRange(0, 0)
            QtGui.QApplication.processEvents()
            return not progress.wasCanceled()

        try:
            importlib.invalidate_caches()
            diagnostics = importlib.reload(castle_diagnostics)
            analyzer = cmd_analyze_x3d._load_analyzer_module()
            manifest = diagnostics.run_diagnostic(
                path,
                analyzer_module=analyzer,
                progress_callback=update_progress,
                document=str(getattr(FreeCAD.ActiveDocument, "Name", "") or ""),
                log_callback=diagnostic_log,
                **options,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "AnalysisCancelled":
                FreeCAD.Console.PrintWarning(LOG_PREFIX + "Castle diagnostics cancelled by user\n")
                return
            FreeCAD.Console.PrintError(LOG_PREFIX + "Castle diagnostics failed: " + str(exc) + "\n")
            QtGui.QMessageBox.critical(
                FreeCADGui.getMainWindow(),
                "Diagn\u00f3stico Castle",
                "No se pudo completar el diagnostico:\n" + str(exc),
            )
            return
        finally:
            progress.close()

        outputs = manifest.get("outputs", {})
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Castle diagnostic manifest: " + str(outputs.get("manifest", "")) + "\n"
        )
        message = (
            "Diagnostico iniciado correctamente.\n\n"
            "Resumen: " + str(outputs.get("summary", "")) + "\n"
            "JSON: " + str(outputs.get("manifest", ""))
        )
        if manifest.get("castle"):
            message += "\nCastle PID: " + str(manifest["castle"].get("pid", ""))
        QtGui.QMessageBox.information(
            FreeCADGui.getMainWindow(), "Diagn\u00f3stico Castle", message
        )
        try:
            QtGui.QDesktopServices.openUrl(
                QtCore.QUrl.fromLocalFile(str(outputs.get("summary", "")))
            )
        except Exception:
            pass

    def IsActive(self):  # noqa: N802
        return True


__all__ = ["CommandClass", "DiagnosticDialog"]
