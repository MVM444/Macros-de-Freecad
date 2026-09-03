# -*- coding: utf-8 -*-
"""Panel searchable para ejecutar y diagnosticar macros ElectricCR.

Revision: 2026-08-12 16:35 America/Costa_Rica
FreeCAD: 1.1.3
"""

import json
import os
import unicodedata

import FreeCAD as App
import FreeCADGui as Gui

from .. import usage_log
from .. import catalog


COMMAND_NAME = "ElectricCR_MacroLauncher"
_MACRO_GROUPS = []
_MACRO_METADATA = {}
ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons")
_ORG = "MVM444"
_APP = "ElectricCR"
_COLUMN_NAMES = ["Herramienta", "Grupo", "Usos", "Ultimo uso", "Estado", "Icono", "Archivo"]
_FILTERS = ["Todas", "Mas usadas", "Sin uso real registrado", "Con pruebas", "Nunca ejecutadas",
            "Con comentarios", "Pendientes de revisar", "Decision: Archivar", "Historicas",
            "Con Rayo", "Con problemas/errores"]
_ROWS_CACHE = None
_CATALOG_CACHE = None
_COMMANDS_CACHE = None
_RESOURCE_CACHE = {}


def _icon(name):
    for candidate in (f"{name}.svg", f"{name}.png", name):
        path = os.path.join(ICONS_DIR, candidate)
        if os.path.exists(path):
            return path
    return ""


def _qmods():
    for candidate in ("PySide6", "PySide2", "PySide"):
        try:
            if candidate == "PySide":
                from PySide import QtCore, QtGui
                return QtGui, QtCore, QtGui
            module = __import__(candidate, fromlist=["QtCore", "QtGui", "QtWidgets"])
            return module.QtWidgets, module.QtCore, module.QtGui
        except Exception:
            continue
    return None, None, None


def _user_role(QtCore):
    try:
        return QtCore.Qt.ItemDataRole.UserRole
    except Exception:
        return QtCore.Qt.UserRole


def _normalize(text):
    s = str(text or "").strip().lower()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _command_obj(cmd_name):
    try:
        if hasattr(Gui, "Command") and hasattr(Gui.Command, "getCommand"):
            return Gui.Command.getCommand(cmd_name)
    except Exception:
        pass
    try:
        if hasattr(Gui, "getCommand"):
            return Gui.getCommand(cmd_name)
    except Exception:
        pass
    return None


def _command_registered(cmd_name):
    """Return whether FreeCAD exposes the command in the current session."""
    if _command_obj(cmd_name) is not None:
        return True
    try:
        commands = Gui.listCommands()
        return str(cmd_name) in {str(value) for value in commands}
    except Exception:
        return False


def _command_resources(cmd_name):
    if cmd_name in _RESOURCE_CACHE:
        return dict(_RESOURCE_CACHE[cmd_name])
    cmd = _command_obj(cmd_name)
    if cmd:
        for attr in ("GetResources", "getResources"):
            if hasattr(cmd, attr):
                try:
                    resources = getattr(cmd, attr)()
                    if isinstance(resources, dict):
                        _RESOURCE_CACHE[cmd_name] = dict(resources)
                        return dict(resources)
                except Exception:
                    pass
    return {}


def invalidate_macro_panel_cache():
    """Invalidate expensive registry/catalog lookups before a new panel open."""
    global _ROWS_CACHE, _CATALOG_CACHE, _COMMANDS_CACHE, _RESOURCE_CACHE
    _ROWS_CACHE = None
    _CATALOG_CACHE = None
    _COMMANDS_CACHE = None
    _RESOURCE_CACHE = {}


def _settings(QtCore):
    try:
        return QtCore.QSettings(_ORG, _APP)
    except Exception:
        return None


def _stats_index():
    stats = usage_log.get_stats()
    tools = stats.get("tools", {}) if isinstance(stats, dict) else {}
    index = {}
    for key, value in tools.items() if isinstance(tools, dict) else []:
        if not isinstance(value, dict):
            continue
        key_norm = str(key).replace("\\", "/").lower()
        index.setdefault(key_norm, value)
        if key_norm.startswith("macro:"):
            index.setdefault(key_norm[6:].rstrip("/"), value)
    return index


def _stats_for(meta, index=None):
    path = str(meta.get("macro") or "")
    rel = str(meta.get("macro_rel") or "").replace("\\", "/").lower().strip("/")
    norm = path.replace("\\", "/").lower()
    index = index if index is not None else _stats_index()
    rec = index.get("macro:" + norm) or index.get(norm) or index.get(rel, {})
    if not rec and rel:
        suffix = "/" + rel
        rec = next((value for key, value in index.items() if key.endswith(suffix)), {})
    try:
        count = int(rec.get("count", 0))
    except Exception:
        count = 0
    try:
        real_count = int(rec.get("real_count", 0))
    except Exception:
        real_count = 0
    try:
        test_count = int(rec.get("test_count", 0))
    except Exception:
        test_count = 0
    try:
        historical_count = int(rec.get("historical_count", max(0, count - real_count - test_count)))
    except Exception:
        historical_count = max(0, count - real_count - test_count)
    return {
        "count": count,
        "real_count": real_count,
        "test_count": test_count,
        "historical_count": historical_count,
        "first_ts": str(rec.get("first_ts") or ""),
        "last_ts": str(rec.get("last_ts") or ""),
        "last_real_ts": str(rec.get("last_real_ts") or ""),
        "last_test_ts": str(rec.get("last_test_ts") or ""),
    }


def _metadata_rows(force=False):
    """Use metadata resolved by commands/macros.py; fallback remains safe."""
    global _ROWS_CACHE, _CATALOG_CACHE, _COMMANDS_CACHE
    if _ROWS_CACHE is not None and not force:
        return _ROWS_CACHE
    try:
        from . import macros as registry
        registered = registry.get_registered_macro_metadata()
    except Exception:
        registered = {}
    try:
        catalog_data = catalog.ensure_catalog(list(registered.values()))
    except Exception as exc:
        catalog_data = catalog.load_catalog()
        try:
            App.Console.PrintWarning(f"[ElectricCR][MacroPanel] catalogo no disponible: {exc}\n")
        except Exception:
            pass
    _CATALOG_CACHE = catalog_data
    try:
        _COMMANDS_CACHE = {str(value) for value in Gui.listCommands()}
    except Exception:
        _COMMANDS_CACHE = set()
    stats_index = _stats_index()
    rows = []
    for group_title, cmds in _MACRO_GROUPS:
        for cmd_name in cmds or []:
            cmd_name = str(cmd_name)
            meta = dict(registered.get(cmd_name, {}))
            resources = _command_resources(cmd_name)
            meta.setdefault("command", cmd_name)
            meta.setdefault("label", str(resources.get("MenuText") or cmd_name).replace("&", "").strip())
            meta.setdefault("group", str(group_title or "Macros"))
            meta.setdefault("toolbar", str(group_title or "Macros"))
            meta.setdefault("icon", str(resources.get("Pixmap") or ""))
            meta.setdefault("icon_status", "RAYO" if os.path.basename(meta.get("icon", "")).lower().startswith("rayo") else "NO RESUELTO")
            meta.setdefault("macro", "")
            meta.setdefault("macro_rel", os.path.basename(meta.get("macro", "")))
            meta.setdefault("transaction", "desconocida")
            meta["file_exists"] = bool(meta.get("macro") and os.path.isfile(meta.get("macro")))
            meta["stats"] = _stats_for(meta, stats_index)
            meta["registered"] = (cmd_name in _COMMANDS_CACHE) if _COMMANDS_CACHE else _command_registered(cmd_name)
            meta["catalog_path"] = catalog.relative_path(meta.get("macro") or meta.get("macro_rel") or "")
            entry = catalog.entry_for_meta(meta, catalog_data)
            for key in ("description", "description_source", "description_confidence",
                        "fuente_descripcion", "confianza_descripcion", "gpt_description",
                        "description_alternative", "description_discrepancy", "description_discrepancy_note",
                        "comment", "manual_status", "decision",
                        "role", "maturity", "verified_result", "recommended_visibility", "priority",
                        "retirement_risk", "dependencies", "recommended_action", "confidence",
                        "technical_note", "last_reviewed", "active"):
                meta[key] = entry.get(key, meta.get(key, ""))
            meta["row_key"] = cmd_name
            meta["state"] = _state_for(meta)
            rows.append(meta)
    # Historical entries remain available through the Historicas filter.
    active_paths = {str(row.get("catalog_path")) for row in rows}
    for path, entry in sorted(catalog_data.get("entries", {}).items()):
        if path in active_paths or entry.get("active"):
            continue
        historical = dict(entry)
        historical.update({
            "command": "",
            "macro": os.path.join(catalog.REPO_ROOT, path.replace("/", os.sep)),
            "macro_rel": path,
            "toolbar": entry.get("group") or "Historicas",
            "group": entry.get("group") or "Historicas",
            "icon": "",
            "icon_status": "NO RESUELTO",
            "file_exists": os.path.isfile(os.path.join(catalog.REPO_ROOT, path.replace("/", os.sep))),
            "registered": False,
            "catalog_path": path,
            "stats": _stats_for({"macro": os.path.join(catalog.REPO_ROOT, path.replace("/", os.sep)), "macro_rel": path}, stats_index),
            "row_key": "catalog:" + path,
            "historical": True,
        })
        historical["state"] = "HISTORICA"
        rows.append(historical)
    _ROWS_CACHE = rows
    return rows


def _state_for(meta):
    if not meta.get("registered") or not meta.get("file_exists"):
        return "ERROR"
    if str(meta.get("icon_status")) == "NO RESUELTO":
        return "ERROR"
    if str(meta.get("icon_status")) == "RAYO":
        return "REVISAR"
    return "OK"


def _format_ts(value):
    text = str(value or "")
    return text.replace("T", " ")[:19] if text else "Nunca"


def _filter_match(meta, filter_name):
    stats = meta.get("stats", {})
    count = int(stats.get("count", 0))
    real_count = int(stats.get("real_count", 0))
    test_count = int(stats.get("test_count", 0))
    status = str(meta.get("icon_status", ""))
    state = str(meta.get("state", ""))
    if filter_name == "Sin uso real registrado":
        return real_count == 0
    if filter_name == "Con pruebas":
        return test_count > 0
    if filter_name == "Mas usadas":
        return count > 0
    if filter_name == "Nunca usadas":
        return real_count == 0 and test_count == 0 and int(stats.get("historical_count", 0)) == 0
    if filter_name == "Con comentarios":
        return bool(str(meta.get("comment", "")).strip())
    if filter_name == "Pendientes de revisar":
        return str(meta.get("manual_status", "SIN_REVISAR")) != "REVISADA"
    if filter_name == "Decision: Archivar":
        return str(meta.get("decision", "")) == "ARCHIVAR"
    if filter_name == "Historicas":
        return bool(meta.get("historical"))
    if filter_name == "Con Rayo":
        return status == "RAYO"
    if filter_name == "Con problemas/errores":
        return state in {"ERROR", "REVISAR"}
    return True


def register_macro_launcher(macro_groups):
    global _MACRO_GROUPS, _MACRO_METADATA
    clean_groups = []
    try:
        for title, cmds in macro_groups or []:
            clean_cmds = [str(cmd) for cmd in (cmds or []) if str(cmd or "").strip()]
            if clean_cmds:
                clean_groups.append((str(title or "Macros"), clean_cmds))
    except Exception:
        clean_groups = []
    _MACRO_GROUPS = clean_groups
    invalidate_macro_panel_cache()
    _MACRO_METADATA = {}
    try:
        from . import macros as registry
        _MACRO_METADATA = registry.get_registered_macro_metadata()
    except Exception:
        pass
    try:
        Gui.addCommand(COMMAND_NAME, MacroLauncherCmd())
    except Exception:
        pass
    return COMMAND_NAME


class MacroLauncherCmd:
    def GetResources(self):
        return {
            "Pixmap": _icon("Panel_Macros_ElectricCR"),
            "MenuText": "Panel de macros ElectricCR",
            "ToolTip": "Buscar, ejecutar y diagnosticar macros ElectricCR.",
        }

    def IsActive(self):
        return True

    def Activated(self):
        invalidate_macro_panel_cache()
        try:
            usage_log.log_tool(COMMAND_NAME, {"source": "toolbar", "usage_kind": "real"})
        except Exception:
            pass

        QtWidgets, QtCore, QtGui = _qmods()
        if QtWidgets is None or QtCore is None or QtGui is None:
            App.Console.PrintMessage("ElectricCR: macros disponibles\n")
            for meta in _metadata_rows():
                App.Console.PrintMessage(f"[{meta.get('group')}] {meta.get('label')}\n")
            return

        role = _user_role(QtCore)
        settings = _settings(QtCore)
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Panel de macros ElectricCR")
        dialog.resize(920, 650)
        layout = QtWidgets.QVBoxLayout(dialog)

        top = QtWidgets.QHBoxLayout()
        search = QtWidgets.QLineEdit(dialog)
        search.setPlaceholderText("Buscar por grupo, nombre, comando o archivo...")
        filter_combo = QtWidgets.QComboBox(dialog)
        filter_combo.addItems(_FILTERS)
        diagnostic = QtWidgets.QCheckBox("Diagnostico", dialog)
        top.addWidget(search, 1)
        top.addWidget(filter_combo)
        top.addWidget(diagnostic)
        layout.addLayout(top)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, dialog)
        tree = QtWidgets.QTreeWidget(splitter)
        tree.setRootIsDecorated(True)
        tree.setAlternatingRowColors(True)
        tree.setIconSize(QtCore.QSize(28, 28))
        try:
            tree.setUniformRowHeights(False)
            tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        except Exception:
            tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        details_panel = QtWidgets.QWidget(splitter)
        details_layout = QtWidgets.QVBoxLayout(details_panel)
        details_layout.setContentsMargins(4, 4, 4, 4)
        details = QtWidgets.QTextEdit(details_panel)
        details.setReadOnly(True)
        details.setPlaceholderText("Seleccione una herramienta para ver sus detalles.")
        details_layout.addWidget(details, 1)

        review_form = QtWidgets.QFormLayout()
        description_label = QtWidgets.QLabel(details_panel)
        description_label.setWordWrap(True)
        description_label.setText("Descripcion: sin descripcion registrada")
        review_form.addRow("Descripcion", description_label)
        manual_status = QtWidgets.QComboBox(details_panel)
        manual_status.addItems(["SIN_REVISAR", "REVISAR", "REVISADA"])
        review_form.addRow("Estado manual", manual_status)
        decision_combo = QtWidgets.QComboBox(details_panel)
        decision_combo.addItems(["SIN_DECISION", "MANTENER", "MEJORAR", "MOVER", "FUSIONAR", "OCULTAR", "ARCHIVAR"])
        review_form.addRow("Decision", decision_combo)
        comment_edit = QtWidgets.QTextEdit(details_panel)
        comment_edit.setPlaceholderText("Comentario de revision para esta macro...")
        comment_edit.setMaximumHeight(70)
        review_form.addRow("Comentario", comment_edit)
        save_review_button = QtWidgets.QPushButton("Guardar comentario/estado", details_panel)
        review_form.addRow("", save_review_button)
        details_layout.addLayout(review_form)
        splitter.setSizes([450, 170])
        layout.addWidget(splitter, 1)

        button_row = QtWidgets.QHBoxLayout()
        adjust_button = QtWidgets.QPushButton("Ajustar columnas", dialog)
        copy_path_button = QtWidgets.QPushButton("Copiar ruta", dialog)
        copy_diag_button = QtWidgets.QPushButton("Copiar diagnostico", dialog)
        collapse_button = QtWidgets.QPushButton("Contraer grupos", dialog)
        expand_button = QtWidgets.QPushButton("Expandir grupos", dialog)
        run_button = QtWidgets.QPushButton("Ejecutar", dialog)
        test_button = QtWidgets.QPushButton("Probar", dialog)
        close_button = QtWidgets.QPushButton("Cerrar", dialog)
        button_row.addWidget(adjust_button)
        button_row.addWidget(copy_path_button)
        button_row.addWidget(copy_diag_button)
        button_row.addWidget(collapse_button)
        button_row.addWidget(expand_button)
        button_row.addStretch(1)
        button_row.addWidget(run_button)
        button_row.addWidget(test_button)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        current_rows = []
        review_dirty = False

        def item_meta(item):
            if item is None:
                return None
            try:
                cmd = str(item.data(0, role) or "")
            except Exception:
                cmd = ""
            if not cmd:
                return None
            return next((row for row in current_rows if row.get("row_key") == cmd or row.get("command") == cmd), None)

        def save_state():
            if settings is None:
                return
            try:
                values = {name: int(tree.columnWidth(i)) for i, name in enumerate(_COLUMN_NAMES[:tree.columnCount()])}
                settings.setValue("macro_panel/column_widths", json.dumps(values))
                settings.setValue("macro_panel/size", dialog.size())
                settings.setValue("macro_panel/splitter", splitter.sizes())
                settings.sync()
            except Exception:
                pass

        def restore_state_or_adjust():
            restored = False
            if settings is not None:
                try:
                    raw = settings.value("macro_panel/column_widths", "")
                    values = json.loads(str(raw)) if raw else {}
                    for i, name in enumerate(_COLUMN_NAMES[:tree.columnCount()]):
                        if name in values and int(values[name]) > 20:
                            tree.setColumnWidth(i, int(values[name]))
                            restored = True
                    raw_sizes = settings.value("macro_panel/splitter", None)
                    if raw_sizes:
                        sizes = [int(x) for x in raw_sizes]
                        if len(sizes) == 2:
                            splitter.setSizes(sizes)
                except Exception:
                    restored = False
            if not restored:
                tree.resizeColumnToContents(0)
                for index in range(1, tree.columnCount()):
                    tree.resizeColumnToContents(index)
                tree.setColumnWidth(0, min(360, max(220, tree.columnWidth(0))))
                for index in range(1, tree.columnCount()):
                    tree.setColumnWidth(index, min(260, max(90, tree.columnWidth(index))))

        def selected_meta():
            item = tree.currentItem()
            meta = item_meta(item)
            if meta is not None:
                return meta
            if item is not None and item.childCount() > 0:
                return item_meta(item.child(0))
            return None

        def save_review(show_message=False, meta_override=None):
            nonlocal review_dirty
            meta = meta_override or selected_meta()
            if not meta or not meta.get("catalog_path") or not review_dirty:
                return False
            try:
                entry = catalog.update_entry(meta.get("catalog_path"), {
                    "comment": str(comment_edit.toPlainText()),
                    "manual_status": str(manual_status.currentText()),
                    "decision": str(decision_combo.currentText()),
                })
                meta.update({"comment": entry.get("comment", ""),
                             "manual_status": entry.get("manual_status", "SIN_REVISAR"),
                             "decision": entry.get("decision", "SIN_DECISION"),
                             "last_reviewed": entry.get("last_reviewed", "")})
                review_dirty = False
                if show_message:
                    status_label.setText("Revision guardada: " + str(meta.get("label", meta.get("name", ""))))
                return True
            except Exception as exc:
                App.Console.PrintError(f"[ElectricCR][MacroPanel] no se pudo guardar revision: {exc}\n")
                return False

        def set_review_dirty(*_args):
            nonlocal review_dirty
            review_dirty = True

        def on_current_item_changed(current, previous):
            # Qt has already changed currentItem when this signal runs. Save
            # against the previous item explicitly so a comment never moves to
            # the newly selected macro.
            save_review(meta_override=item_meta(previous))
            update_details()

        def detail_text(meta):
            if not meta:
                return "Seleccione una herramienta para ver sus detalles."
            stats = meta.get("stats", {})
            obs = []
            if meta.get("icon_status") == "RAYO":
                obs.append("Icono generico Rayo.svg: no se considera un error; revisar si existe un recurso especifico.")
            if not meta.get("file_exists"):
                obs.append("El archivo fuente no existe en la ruta registrada.")
            if not meta.get("registered"):
                obs.append("El comando no aparece registrado en FreeCAD.")
            lines = [
                f"Nombre: {meta.get('label', '')}",
                f"Grupo/barra: {meta.get('toolbar') or meta.get('group', '')}",
                f"Archivo: {meta.get('macro_rel') or meta.get('macro', '')}",
                f"Ruta: {meta.get('macro', '')}",
                f"Comando: {meta.get('command', '')}",
                f"Icono: {meta.get('icon', '') or 'sin resolver'}",
                f"Estado icono: {meta.get('icon_status', 'NO RESUELTO')}",
                f"Estado general: {meta.get('state', 'ERROR')}",
                f"Descripcion: {meta.get('description') or 'Sin descripcion registrada'}",
                f"Fuente descripcion: {meta.get('description_source') or meta.get('fuente_descripcion') or 'sin fuente'}",
                f"Confianza descripcion: {meta.get('description_confidence') or meta.get('confianza_descripcion') or 'sin indicar'}",
                f"Comentario: {meta.get('comment') or 'sin comentario'}",
                f"Estado manual: {meta.get('manual_status', 'SIN_REVISAR')}",
                f"Decision: {meta.get('decision', 'SIN_DECISION')}",
                f"Archivo existe: {'SI' if meta.get('file_exists') else 'NO'}",
                f"Uso total: {stats.get('count', 0)}",
                f"Uso real: {stats.get('real_count', 0)}",
                f"Pruebas: {stats.get('test_count', 0)}",
                f"Historico sin clasificar: {stats.get('historical_count', 0)}",
                f"Primer uso: {_format_ts(stats.get('first_ts'))}",
                f"Ultimo uso: {_format_ts(stats.get('last_ts'))}",
                f"Ultimo uso real: {_format_ts(stats.get('last_real_ts'))}",
                f"Ultima prueba: {_format_ts(stats.get('last_test_ts'))}",
                f"Transaccion: {meta.get('transaction', 'desconocida')}",
            ]
            if meta.get("dependencies"):
                lines.append("Dependencias: " + ", ".join(str(value) for value in meta.get("dependencies", [])))
            if meta.get("technical_note"):
                lines.append("Nota tecnica: " + str(meta.get("technical_note")))
            if meta.get("description_discrepancy"):
                lines.append("Discrepancia: " + str(meta.get("description_discrepancy_note") or "Existe una alternativa GPT pendiente de revision."))
                lines.append("Alternativa GPT: " + str(meta.get("description_alternative") or ""))
            if obs:
                lines.append("Observaciones:")
                lines.extend(f"- {value}" for value in obs)
            return "\n".join(lines)

        def update_details(*_args):
            nonlocal review_dirty
            meta = selected_meta()
            details.setPlainText(detail_text(meta))
            description_label.setText("Descripcion: " + str(meta.get("description") or "Sin descripcion registrada") if meta else "Descripcion: sin descripcion registrada")
            manual_status.blockSignals(True)
            decision_combo.blockSignals(True)
            comment_edit.blockSignals(True)
            try:
                manual_status.setCurrentText(str(meta.get("manual_status", "SIN_REVISAR")) if meta else "SIN_REVISAR")
                decision_combo.setCurrentText(str(meta.get("decision", "SIN_DECISION")) if meta else "SIN_DECISION")
                comment_edit.setPlainText(str(meta.get("comment", "")) if meta else "")
            finally:
                manual_status.blockSignals(False)
                decision_combo.blockSignals(False)
                comment_edit.blockSignals(False)
            review_dirty = False

        def populate():
            nonlocal current_rows
            save_review()
            query = _normalize(search.text())
            tokens = [token for token in query.split() if token]
            filter_name = str(filter_combo.currentText())
            current_rows = _metadata_rows(force=not bool(current_rows))
            tree.clear()
            diagnostic_mode = bool(diagnostic.isChecked())
            columns = _COLUMN_NAMES if diagnostic_mode else _COLUMN_NAMES[:4]
            tree.setColumnCount(len(columns))
            tree.setHeaderLabels(columns)
            total = 0
            grouped = {}
            for meta in current_rows:
                if bool(meta.get("historical")) != (filter_name == "Historicas"):
                    continue
                haystack = _normalize(" ".join(str(meta.get(key, "")) for key in (
                    "toolbar", "group", "label", "command", "macro_rel", "description", "comment")))
                if tokens and not all(token in haystack for token in tokens):
                    continue
                if not _filter_match(meta, filter_name):
                    continue
                grouped.setdefault(str(meta.get("toolbar") or meta.get("group") or "Macros"), []).append(meta)
            for group_title in sorted(grouped, key=_normalize):
                group_item = QtWidgets.QTreeWidgetItem([group_title] + [""] * (len(columns) - 1))
                tree.addTopLevelItem(group_item)
                for meta in sorted(grouped[group_title], key=lambda row: _normalize(row.get("label", ""))):
                    stats = meta.get("stats", {})
                    values = [meta.get("label", ""), meta.get("toolbar", ""), str(stats.get("count", 0)), _format_ts(stats.get("last_ts"))]
                    if diagnostic_mode:
                        values.extend([meta.get("state", "ERROR"), meta.get("icon_status", "NO RESUELTO"), "SI" if meta.get("file_exists") else "NO"])
                    child = QtWidgets.QTreeWidgetItem(values)
                    child.setData(0, role, meta.get("row_key") or meta.get("command", ""))
                    icon_path = str(meta.get("icon") or "")
                    if icon_path:
                        try:
                            child.setIcon(0, QtGui.QIcon(icon_path))
                        except Exception:
                            pass
                    group_item.addChild(child)
                    total += 1
                group_item.setExpanded(True if query or filter_name != "Historicas" else False)
            status = f"{total} herramientas"
            if diagnostic_mode:
                status += " | modo diagnostico"
            if tree.topLevelItemCount() > 0 and tree.topLevelItem(0).childCount() > 0:
                tree.setCurrentItem(tree.topLevelItem(0).child(0))
            status_label.setText(status)
            restore_state_or_adjust()
            update_details()

        def run_current():
            meta = selected_meta()
            if not meta or not meta.get("command") or meta.get("historical"):
                return
            try:
                usage_log.mark_next_execution("real")
                Gui.runCommand(meta.get("command", ""))
            except Exception as exc:
                usage_log.clear_execution_kind()
                App.Console.PrintError(f"[ElectricCR][MacroPanel] no se pudo ejecutar {meta.get('command')}: {exc}\n")

        def test_current():
            meta = selected_meta()
            if not meta or not meta.get("command") or meta.get("historical"):
                return
            try:
                usage_log.mark_next_execution("test")
                Gui.runCommand(meta.get("command", ""))
            except Exception as exc:
                usage_log.clear_execution_kind()
                App.Console.PrintError(f"[ElectricCR][MacroPanel] no se pudo probar {meta.get('command')}: {exc}\n")

        def copy_path():
            meta = selected_meta()
            if meta and meta.get("macro"):
                QtWidgets.QApplication.clipboard().setText(str(meta.get("macro")))

        def copy_diagnostic():
            meta = selected_meta()
            if meta:
                text = "[ElectricCR][MacroPanel] Diagnostico\n" + detail_text(meta)
                QtWidgets.QApplication.clipboard().setText(text)

        def collapse_groups():
            for index in range(tree.topLevelItemCount()):
                tree.topLevelItem(index).setExpanded(False)

        def expand_groups():
            for index in range(tree.topLevelItemCount()):
                tree.topLevelItem(index).setExpanded(True)

        def adjust_columns():
            for index in range(tree.columnCount()):
                tree.resizeColumnToContents(index)
            tree.setColumnWidth(0, min(360, max(220, tree.columnWidth(0))))
            for index in range(1, tree.columnCount()):
                tree.setColumnWidth(index, min(260, max(90, tree.columnWidth(index))))
            save_state()

        status_label = QtWidgets.QLabel(dialog)
        layout.insertWidget(1, status_label)
        search.textChanged.connect(populate)
        filter_combo.currentTextChanged.connect(populate)
        diagnostic.toggled.connect(populate)
        tree.currentItemChanged.connect(on_current_item_changed)
        comment_edit.textChanged.connect(set_review_dirty)
        manual_status.currentTextChanged.connect(set_review_dirty)
        decision_combo.currentTextChanged.connect(set_review_dirty)
        tree.itemDoubleClicked.connect(lambda _item, _column: run_current())
        adjust_button.clicked.connect(adjust_columns)
        copy_path_button.clicked.connect(copy_path)
        copy_diag_button.clicked.connect(copy_diagnostic)
        collapse_button.clicked.connect(collapse_groups)
        expand_button.clicked.connect(expand_groups)
        save_review_button.clicked.connect(lambda: save_review(True))
        run_button.clicked.connect(run_current)
        test_button.clicked.connect(test_current)
        close_button.clicked.connect(dialog.reject)
        try:
            if settings is not None:
                size = settings.value("macro_panel/size", None)
                if size:
                    dialog.resize(size)
        except Exception:
            pass
        dialog.finished.connect(lambda _result: (save_review(), save_state()))
        populate()
        search.setFocus()
        try:
            dialog.exec()
        except AttributeError:
            dialog.exec_()
