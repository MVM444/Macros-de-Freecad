"""FA Model Diagnostic command.

Name: cmd_model_diagnostic.py
Purpose: generate a read-only Markdown/JSON diagnostic of the active FreeCAD
model for human review and GPT/Codex feedback.
Main behavior: capture the Tree View and internal relations through the shared
FreeCAD adapter, run the independent diagnostic core, save MD+JSON+TXT, and
present explicit actions to copy the MD path or open its folder.
Future modifications: keep this command thin; capture belongs in
model_diagnostic_freecad.py and analysis/rendering in model_diagnostic_core.py.
Version: 0.2.0
Date and time: 2026-09-09 16:25 America/Costa_Rica
FreeCAD target: 1.1.3.
"""

from __future__ import annotations

import datetime
import json
import os
import re

import FreeCAD as App
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

from .. import i18n
from ..core.model_diagnostic_core import analyze_snapshot, render_markdown, render_text
from ..core.model_diagnostic_freecad import capture_document_snapshot
from ..core.reloadable_command import ReloadableCommandProxy

COMMAND_VERSION = "0.2.0"
COMMAND_NAME = "FA_ModelDiagnostic"
LOG = "[FA DIAGNOSTICO] "
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "diagnostic_report.svg")
).replace(os.sep, "/")


def _log(text):
    App.Console.PrintMessage(LOG + str(text) + "\n")


def _sanitize_filename(value):
    base = str(value or "Documento").strip() or "Documento"
    base = re.sub(r"[^0-9A-Za-z_ -]+", "_", base)
    base = re.sub(r"\s+", "_", base).strip(" _")
    return base or "Documento"


def _output_dir():
    """Return the diagnostics folder under the configured FreeCAD Macro directory.

    The Macro directory is user-configurable and may live inside a synchronized
    location such as OneDrive. Resolve it through FreeCAD instead of hardcoding
    a Windows user/path. Fall back to the Workbench-local folder only if the
    FreeCAD API does not return a usable Macro directory.
    """
    macro_dir = ""
    try:
        macro_dir = str(App.getUserMacroDir(True) or "").strip()
    except Exception:
        macro_dir = ""
    if macro_dir:
        return os.path.abspath(os.path.join(macro_dir, "_reportes_diagnostico"))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "_reportes_diagnostico"))


def _copy_to_clipboard(text):
    """Copy text only when explicitly requested by a UI/caller."""
    try:
        app = QtWidgets.QApplication.instance()
        clipboard = app.clipboard() if app is not None else None
        if clipboard is None:
            return False
        clipboard.setText(str(text))
        return True
    except Exception:
        return False


def _open_folder(path):
    """Open one local folder through Qt without shell-specific commands."""
    try:
        folder = os.path.abspath(str(path or ""))
        if not folder or not os.path.isdir(folder):
            return False
        return bool(QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder)))
    except Exception:
        return False


def _scope_text(result):
    snapshot = dict(result.get("snapshot") or {})
    meta = dict(snapshot.get("meta") or {})
    scope = str(meta.get("scope") or "").strip()
    if scope == "seleccion":
        count = len(list(snapshot.get("selected_objects") or []))
        return i18n.bi("Seleccion (%d objeto(s))" % count, "Selection (%d object(s))" % count)
    return i18n.bi("Documento completo", "Full document")


def _choose_manual_scope(selection, parent=None):
    """Prevent a residual Tree selection from silently shrinking the report scope.

    No selection means full document. When a selection exists, full-document
    diagnosis is the default button and the user may explicitly choose selection.
    Return [] for full document, a list for selection, or None for cancel.
    """
    selection = list(selection or [])
    if not selection:
        return []

    box = QtWidgets.QMessageBox(parent)
    box.setWindowTitle(i18n.bi("FA Informe diagnostico", "FA Diagnostic Report"))
    box.setIcon(QtWidgets.QMessageBox.Question)
    box.setText(
        i18n.bi(
            "Hay %d objeto(s) seleccionado(s).\n\nQue alcance desea diagnosticar?" % len(selection),
            "%d object(s) are selected.\n\nWhich scope do you want to diagnose?" % len(selection),
        )
    )
    full_button = box.addButton(
        i18n.bi("Documento completo", "Full document"), QtWidgets.QMessageBox.AcceptRole
    )
    selection_button = box.addButton(
        i18n.bi("Solo seleccion", "Selection only"), QtWidgets.QMessageBox.ActionRole
    )
    cancel_button = box.addButton(QtWidgets.QMessageBox.Cancel)
    try:
        box.setDefaultButton(full_button)
    except Exception:
        pass
    box.exec() if hasattr(box, "exec") else box.exec_()
    clicked = box.clickedButton()
    if clicked is full_button:
        return []
    if clicked is selection_button:
        return selection
    if clicked is cancel_button:
        return None
    return None


def generate_report(
    doc=None,
    selection=None,
    output_dir=None,
    objective="",
    copy_prompt=True,
):
    """Generate MD/JSON/TXT and return paths + payloads. Read-only on document.

    ``selection=[]`` explicitly forces full-document scope. ``selection=None``
    preserves the historic adapter behavior of consulting the current GUI
    selection. Automatic callers such as FA Demo must therefore pass ``[]``.
    Clipboard writes are optional so normal UI flows do not overwrite user data.
    """
    doc = doc or App.ActiveDocument
    if doc is None:
        raise RuntimeError("No hay documento activo.")
    snapshot = capture_document_snapshot(doc, selection=selection)
    snapshot.setdefault("meta", {})["objective"] = str(objective or "").strip()
    diagnostic = analyze_snapshot(snapshot)
    markdown = render_markdown(snapshot, diagnostic)
    text_report = render_text(snapshot, diagnostic)

    target_dir = os.path.abspath(output_dir or _output_dir())
    os.makedirs(target_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    label = str(getattr(doc, "Label", "") or getattr(doc, "Name", "") or "Documento")
    base = "FA_Diagnostico_%s_%s" % (_sanitize_filename(label), stamp)
    md_path = os.path.join(target_dir, base + ".md")
    txt_path = os.path.join(target_dir, base + ".txt")
    json_path = os.path.join(target_dir, base + ".json")

    payload = {
        "snapshot": snapshot,
        "diagnostic": diagnostic,
    }
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(markdown)
    with open(txt_path, "w", encoding="utf-8") as handle:
        handle.write(text_report)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)

    prompt = (
        "Adjunto el informe '%s'. Analice primero los hallazgos y la jerarquia del modelo FreeCAD. "
        "No proponga cambios hasta separar errores reales, advertencias y relaciones intencionales."
        % os.path.basename(md_path)
    )
    copied = _copy_to_clipboard(prompt) if bool(copy_prompt) else False
    return {
        "md_path": md_path,
        "json_path": json_path,
        "txt_path": txt_path,
        "snapshot": snapshot,
        "diagnostic": diagnostic,
        "prompt": prompt,
        "prompt_copied": copied,
    }


class DiagnosticResultDialog(QtWidgets.QDialog):
    """Reusable result dialog for the manual command and automatic Demo report."""

    def __init__(self, result, parent=None, title=None, intro=""):
        super().__init__(parent)
        self.result = result
        self.setWindowTitle(title or i18n.bi("FA Informe diagnostico", "FA Diagnostic Report"))
        self.setMinimumWidth(720)

        counts = dict(result.get("diagnostic", {}).get("counts") or {})
        ok_count = int(counts.get("OK", 0))
        info_count = int(counts.get("INFO", 0))
        layout = QtWidgets.QVBoxLayout(self)

        if intro:
            intro_label = QtWidgets.QLabel(str(intro))
            intro_label.setWordWrap(True)
            layout.addWidget(intro_label)

        summary = QtWidgets.QLabel(
            i18n.bi(
                "Diagnostico: %d errores | %d advertencias | %d OK | %d informativos\nAlcance: %s"
                % (
                    int(counts.get("ERROR", 0)),
                    int(counts.get("WARN", 0)),
                    ok_count,
                    info_count,
                    _scope_text(result),
                ),
                "Diagnostic: %d errors | %d warnings | %d OK | %d info\nScope: %s"
                % (
                    int(counts.get("ERROR", 0)),
                    int(counts.get("WARN", 0)),
                    ok_count,
                    info_count,
                    _scope_text(result),
                ),
            )
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        layout.addWidget(QtWidgets.QLabel(i18n.bi("Reporte Markdown principal:", "Primary Markdown report:")))
        self.path_edit = QtWidgets.QLineEdit(str(result.get("md_path") or ""))
        self.path_edit.setReadOnly(True)
        layout.addWidget(self.path_edit)

        secondary = QtWidgets.QLabel(
            i18n.bi(
                "Tambien se generaron JSON y TXT en la misma carpeta.",
                "JSON and TXT were also generated in the same folder.",
            )
        )
        secondary.setWordWrap(True)
        layout.addWidget(secondary)

        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        buttons = QtWidgets.QHBoxLayout()
        self.copy_button = QtWidgets.QPushButton(i18n.bi("Copiar ruta del MD", "Copy MD path"))
        self.open_button = QtWidgets.QPushButton(i18n.bi("Abrir carpeta", "Open folder"))
        self.close_button = QtWidgets.QPushButton(i18n.bi("Cerrar", "Close"))
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.open_button)
        buttons.addStretch(1)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

        self.copy_button.clicked.connect(self._copy_path)
        self.open_button.clicked.connect(self._open_report_folder)
        self.close_button.clicked.connect(self.accept)

    def _copy_path(self):
        path = str(self.result.get("md_path") or "")
        if _copy_to_clipboard(path):
            self.status.setText(i18n.bi("Ruta del MD copiada al portapapeles.", "MD path copied to clipboard."))
        else:
            self.status.setText(i18n.bi("No se pudo copiar la ruta.", "Could not copy the path."))

    def _open_report_folder(self):
        path = str(self.result.get("md_path") or "")
        folder = os.path.dirname(path)
        if _open_folder(folder):
            self.status.setText(i18n.bi("Carpeta abierta.", "Folder opened."))
        else:
            self.status.setText(i18n.bi("No se pudo abrir la carpeta.", "Could not open the folder."))


def show_report_dialog(result, parent=None, title=None, intro=""):
    """Show the reusable diagnostic result dialog and return it after closing."""
    dialog = DiagnosticResultDialog(result, parent=parent, title=title, intro=intro)
    dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
    return dialog


class CommandClass:
    CommandName = COMMAND_NAME

    def GetResources(self):  # noqa: N802
        return {
            "MenuText": i18n.bi("FA Informe diagnostico", "FA Diagnostic Report"),
            "ToolTip": i18n.bi(
                "Generar un informe MD/JSON de solo lectura con arbol, relaciones y hallazgos para revisar el modelo o enviarlo a GPT/Codex.",
                "Generate a read-only MD/JSON report with tree, relations, and findings for model review or GPT/Codex feedback.",
            ),
            "Pixmap": ICON_PATH,
        }

    def Activated(self):  # noqa: N802
        try:
            doc = App.ActiveDocument
            if doc is None:
                raise RuntimeError(i18n.bi("No hay documento activo.", "There is no active document."))
            current_selection = list(FreeCADGui.Selection.getSelection() or [])
            selection = _choose_manual_scope(current_selection, parent=FreeCADGui.getMainWindow())
            if selection is None:
                _log("Informe cancelado por el usuario antes de capturar el modelo.")
                return
            result = generate_report(doc=doc, selection=selection, copy_prompt=False)
            counts = result["diagnostic"]["counts"]
            _log(
                "Informe generado | version=%s | alcance=%s | objetos=%d | errores=%d | advertencias=%d | MD=%s"
                % (
                    COMMAND_VERSION,
                    result["snapshot"].get("meta", {}).get("scope", ""),
                    result["diagnostic"]["object_count"],
                    counts.get("ERROR", 0),
                    counts.get("WARN", 0),
                    result["md_path"],
                )
            )
            show_report_dialog(result, parent=FreeCADGui.getMainWindow())
        except Exception as exc:
            App.Console.PrintError(LOG + "Error: %s\n" % exc)
            QtWidgets.QMessageBox.critical(
                FreeCADGui.getMainWindow(),
                i18n.bi("FA Informe diagnostico", "FA Diagnostic Report"),
                str(exc),
            )

    def IsActive(self):  # noqa: N802
        return App.ActiveDocument is not None


def register():
    command = ReloadableCommandProxy(
        __name__, class_name="CommandClass", command_name=CommandClass.CommandName
    )
    FreeCADGui.addCommand(command.CommandName, command)
    return command
