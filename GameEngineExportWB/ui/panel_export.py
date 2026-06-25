"""Export TaskPanel for Game Engine Export WB.

Descripcion rapida: panel para escoger objetos, ruta y ejecutar la exportacion X3D.
Fecha y hora: 2025-10-13 19:00 UTC.
Instrucciones clave:
- Trabajar con listas de objetos disponibles y seleccionados.
- Leer configuracion previa desde ParamGet y permitir ajustes rapidos.
- Realizar exportacion inmediata al aceptar, con logs [GAMEEXPORT].
"""

# Qt compatibility for FreeCAD 1.x (PySide6) and older builds.
def _ensure_qt_compat():
    import sys
    import types

    QtCore = QtGui = QtWidgets = None
    binding_name = None

    for candidate in ("PySide6", "PySide2", "PySide"):
        try:
            if candidate == "PySide":
                from PySide import QtCore as _QtCore, QtGui as _QtGui
                _QtWidgets = _QtGui
            else:
                module = __import__(candidate, fromlist=["QtCore", "QtGui", "QtWidgets"])
                _QtCore = module.QtCore
                _QtGui = module.QtGui
                _QtWidgets = module.QtWidgets
            QtCore, QtGui, QtWidgets = _QtCore, _QtGui, _QtWidgets
            binding_name = candidate
            break
        except Exception:
            continue

    if QtCore is None:
        return

    qtgui_compat = types.ModuleType("QtGui")
    qtgui_compat.__dict__.update(getattr(QtGui, "__dict__", {}))
    qtgui_compat.__dict__.update(getattr(QtWidgets, "__dict__", {}))

    qtsvg_compat = None
    for module_name in ("QtSvg", "QtSvgWidgets"):
        try:
            module = __import__(binding_name, fromlist=[module_name])
            qt_module = getattr(module, module_name)
        except Exception:
            continue
        if qtsvg_compat is None:
            qtsvg_compat = types.ModuleType("QtSvg")
        qtsvg_compat.__dict__.update(getattr(qt_module, "__dict__", {}))

    qtuitools_compat = None
    try:
        module = __import__(binding_name, fromlist=["QtUiTools"])
        qtuitools_compat = module.QtUiTools
    except Exception:
        pass

    for package_name in ("PySide2", "PySide"):
        package = sys.modules.get(package_name)
        if package is None:
            package = types.ModuleType(package_name)
            sys.modules[package_name] = package
        package.QtCore = QtCore
        package.QtGui = qtgui_compat
        package.QtWidgets = QtWidgets
        sys.modules[package_name + ".QtCore"] = QtCore
        sys.modules[package_name + ".QtGui"] = qtgui_compat
        sys.modules[package_name + ".QtWidgets"] = QtWidgets
        if qtsvg_compat is not None:
            package.QtSvg = qtsvg_compat
            sys.modules[package_name + ".QtSvg"] = qtsvg_compat
        if qtuitools_compat is not None:
            package.QtUiTools = qtuitools_compat
            sys.modules[package_name + ".QtUiTools"] = qtuitools_compat


_ensure_qt_compat()

import datetime
import math
import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from PySide import QtCore, QtGui

from ..core import exporter_x3d, gamestart, persist, lights
from . import panel_info
from .output_defaults import compute_output_defaults, normalize_base_name, persist_output_settings


def _git_last_update_label() -> str:
    try:
        repo_root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=iso"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=1.5,
            check=True,
        )
        ts = completed.stdout.strip()
        if ts:
            return f"Actualizado: {ts}"
    except Exception:
        pass
    return "Actualizado: desconocido"

FreeCAD = __import__("FreeCAD")
FreeCADGui = __import__("FreeCADGui")

PARAM_GROUP = "User parameter:Plugins/GameEngineExportWB"


class ExportTaskPanel:
    """TaskPanel to manage selection and export workflow."""

    def __init__(self):
        FreeCAD.Console.PrintMessage("[GAMEEXPORT] Opening export panel\n")
        self.params = FreeCAD.ParamGet(PARAM_GROUP)
        self.widget = QtGui.QWidget()
        self.widget.setWindowTitle("Game Engine Export - Seleccion y exportacion")
        self.form = self.widget
        self.root_names = []
        self.export_names = set()
        self.light_names = set()
        self.sidecar_data = {}
        self.doc_path = None
        self.global_light_color = (1.0, 0.95, 0.85)
        self.light_color_current = (1.0, 1.0, 1.0)

        layout = QtGui.QVBoxLayout(self.widget)
        self.version_label = QtGui.QLabel(_git_last_update_label())
        self.version_label.setStyleSheet("color: #1f4e79; font-size: 11px;")
        layout.addWidget(self.version_label)

        self.tabs = QtGui.QTabWidget()
        layout.addWidget(self.tabs)

        scene_tab = QtGui.QWidget()
        scene_layout = QtGui.QVBoxLayout(scene_tab)
        scene_layout.addWidget(self._build_root_group())
        scene_layout.addWidget(self._build_gamestart_group())
        scene_layout.addWidget(self._build_lists_group())
        scene_layout.addWidget(self._build_global_light_group())
        scene_layout.addWidget(self._build_scene_lights_group())
        scene_layout.addWidget(self._build_output_group())
        scene_layout.addStretch()
        self.tabs.addTab(scene_tab, "Escena / Scene")

        materials_tab = QtGui.QWidget()
        materials_layout = QtGui.QVBoxLayout(materials_tab)
        materials_layout.addWidget(QtGui.QLabel("Materiales / Materials\n(Proximamente / Coming soon)"))
        materials_layout.addStretch()
        self.tabs.addTab(materials_tab, "Materiales / Materials")

        config_tab = self._build_config_tab()
        self.tabs.addTab(config_tab, "Configuracion / Config")

        info_tab = panel_info.build_info_tab()
        self.tabs.addTab(info_tab, "Informacion / About")
        self.status_label = QtGui.QLabel("")
        self.status_label.setStyleSheet("color: #2563eb;")
        layout.addWidget(self.status_label)
        layout.addStretch()

        self._load_defaults()
        self._refresh_available()

    def _build_root_group(self):
        group = QtGui.QGroupBox("Raiz / Root")
        layout = QtGui.QHBoxLayout(group)

        self.root_line = QtGui.QLineEdit()
        self.root_line.setReadOnly(True)
        layout.addWidget(self.root_line, stretch=1)

        btn_use_selection = QtGui.QPushButton("Tomar seleccion / Use selection")
        btn_use_selection.setToolTip(
            "ES: Agrega los objetos/grupos seleccionados como raices.\nEN: Append selected objects/groups as roots."
        )
        btn_use_selection.clicked.connect(self._use_selection_as_root)
        layout.addWidget(btn_use_selection)

        self.btn_clear_root = QtGui.QPushButton("Limpiar / Clear")
        self.btn_clear_root.setToolTip(
            "ES: Quita todas las raices seleccionadas.\nEN: Remove all selected roots."
        )
        self.btn_clear_root.clicked.connect(self._clear_root_selection)
        layout.addWidget(self.btn_clear_root)

        return group

    def _build_gamestart_group(self):
        group = QtGui.QGroupBox("GameStart")
        layout = QtGui.QHBoxLayout(group)
        self.gamestart_line = QtGui.QLineEdit()
        self.btn_create_gamestart = QtGui.QPushButton("Crear / Create")
        self.label_gamestart_state = QtGui.QLabel("")
        self.btn_create_gamestart.setToolTip(
            "ES: Crea un marcador (cono+base). Sus propiedades definen el Viewpoint inicial.\n"
            "EN: Creates a marker (cone+base). Its properties define the initial Viewpoint."
        )
        layout.addWidget(self.gamestart_line)
        layout.addWidget(self.btn_create_gamestart)
        layout.addWidget(self.label_gamestart_state)
        self.btn_create_gamestart.clicked.connect(self._create_gamestart)
        return group

    def _build_lists_group(self):
        group = QtGui.QGroupBox("Objetos / Objects")
        main_layout = QtGui.QVBoxLayout(group)
        layout = QtGui.QHBoxLayout()

        self.list_available = QtGui.QListWidget()
        self.list_available.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.list_available)

        btn_layout = QtGui.QVBoxLayout()
        btn_add = QtGui.QPushButton(">>")
        btn_remove = QtGui.QPushButton("<<")
        btn_add.clicked.connect(self._move_selected_to_export)
        btn_remove.clicked.connect(self._move_selected_to_available)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.list_export = QtGui.QListWidget()
        self.list_export.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.list_export)

        main_layout.addLayout(layout)

        actions_layout = QtGui.QHBoxLayout()
        btn_add_selection = QtGui.QPushButton("Agregar seleccion / Add selection")
        btn_add_selection.setToolTip(
            "ES: Usa la seleccion actual del 3D (por ejemplo con Shift+B) y la agrega a A exportar.\n"
            "EN: Use current 3D selection (for example with Shift+B) and add it to To export."
        )
        btn_add_selection.clicked.connect(self._add_current_selection_to_export)
        btn_refresh = QtGui.QPushButton("Actualizar lista")
        btn_refresh.clicked.connect(self._refresh_available)
        btn_clear = QtGui.QPushButton("Limpiar seleccion")
        btn_clear.clicked.connect(self._clear_export_list)
        btn_diagnose = QtGui.QPushButton("Diagnosticar exportacion")
        btn_diagnose.clicked.connect(self._diagnose_export_selection)
        actions_layout.addWidget(btn_add_selection)
        actions_layout.addWidget(btn_refresh)
        actions_layout.addWidget(btn_clear)
        actions_layout.addWidget(btn_diagnose)
        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        return group

    def _build_global_light_group(self):
        group = QtGui.QGroupBox("Luz global / Global light")
        layout = QtGui.QGridLayout(group)

        self.chk_global_light = QtGui.QCheckBox("Habilitar / Enable")
        self.chk_global_light.setToolTip(
            "ES: Inserta un DirectionalLight que ilumina la escena. Yaw/Pitch definen la direccion.\n"
            "EN: Insert a DirectionalLight for the whole scene. Yaw/Pitch control the direction."
        )
        layout.addWidget(self.chk_global_light, 0, 0, 1, 3)

        layout.addWidget(QtGui.QLabel("Yaw (°)"), 1, 0)
        self.spin_gl_yaw = QtGui.QDoubleSpinBox()
        self.spin_gl_yaw.setRange(-180.0, 180.0)
        self.spin_gl_yaw.setSingleStep(1.0)
        layout.addWidget(self.spin_gl_yaw, 1, 1)

        layout.addWidget(QtGui.QLabel("Pitch (°)"), 2, 0)
        self.spin_gl_pitch = QtGui.QDoubleSpinBox()
        self.spin_gl_pitch.setRange(-90.0, 90.0)
        self.spin_gl_pitch.setSingleStep(1.0)
        layout.addWidget(self.spin_gl_pitch, 2, 1)

        layout.addWidget(QtGui.QLabel("Intensidad"), 3, 0)
        self.spin_gl_intensity = QtGui.QDoubleSpinBox()
        self.spin_gl_intensity.setRange(0.0, 5.0)
        self.spin_gl_intensity.setSingleStep(0.1)
        layout.addWidget(self.spin_gl_intensity, 3, 1)

        self.btn_gl_color = QtGui.QPushButton("Color...")
        self.btn_gl_color.setToolTip(
            "ES: Selecciona el color de la luz. Valor sugerido: blanco calido.\n"
            "EN: Choose the light color. Suggested: warm white."
        )
        self.btn_gl_color.clicked.connect(self._choose_global_color)
        layout.addWidget(self.btn_gl_color, 4, 0)

        self.btn_gl_time = QtGui.QPushButton("Hora solar... / Solar time...")
        self.btn_gl_time.setToolTip(
            "ES: Calcula yaw/pitch aproximados segun latitud y hora.\nEN: Estimate yaw/pitch from latitude and time."
        )
        self.btn_gl_time.clicked.connect(self._open_solar_dialog)
        layout.addWidget(self.btn_gl_time, 4, 1)

        return group

    def _build_scene_lights_group(self):
        group = QtGui.QGroupBox("Luces de escena / Scene lights")
        layout = QtGui.QVBoxLayout(group)

        self.chk_pointlights = QtGui.QCheckBox("Exportar PointLights / Export point lights")
        self.chk_pointlights.setToolTip(
            "ES: Marca luminarias para exportarlas como PointLight.\nEN: Mark fixtures to export as PointLight."
        )
        layout.addWidget(self.chk_pointlights)

        btn_row = QtGui.QHBoxLayout()
        self.btn_add_light = QtGui.QPushButton("Agregar seleccion como luz")
        self.btn_add_light.setToolTip(
            "ES: Marca los objetos seleccionados como luminarias.\nEN: Mark selected objects as light sources."
        )
        self.btn_add_light.clicked.connect(self._add_lights_from_selection)
        self.btn_remove_light = QtGui.QPushButton("Quitar seleccion como luz")
        self.btn_remove_light.setToolTip(
            "ES: Elimina el marcado de luminaria para los items seleccionados en la lista.\n"
            "EN: Remove light flag for the selected items in the list."
        )
        self.btn_remove_light.clicked.connect(self._remove_lights_from_list)
        btn_row.addWidget(self.btn_add_light)
        btn_row.addWidget(self.btn_remove_light)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.list_lights = QtGui.QListWidget()
        self.list_lights.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.list_lights.setAlternatingRowColors(True)
        layout.addWidget(self.list_lights)
        self.list_lights.itemSelectionChanged.connect(self._on_lights_selection_changed)

        controls = QtGui.QHBoxLayout()
        controls.addWidget(QtGui.QLabel("Intensidad"))
        self.spin_light_intensity = QtGui.QDoubleSpinBox()
        self.spin_light_intensity.setRange(0.0, 5.0)
        self.spin_light_intensity.setSingleStep(0.1)
        controls.addWidget(self.spin_light_intensity)

        controls.addWidget(QtGui.QLabel("Radio (m)"))
        self.spin_light_radius = QtGui.QDoubleSpinBox()
        self.spin_light_radius.setRange(0.1, 200.0)
        self.spin_light_radius.setSingleStep(0.5)
        controls.addWidget(self.spin_light_radius)

        self.btn_light_color = QtGui.QPushButton("Color luz...")
        self.btn_light_color.clicked.connect(self._choose_light_color)
        controls.addWidget(self.btn_light_color)

        self.btn_apply_light_props = QtGui.QPushButton("Aplicar a seleccion")
        self.btn_apply_light_props.clicked.connect(self._apply_light_properties)
        controls.addWidget(self.btn_apply_light_props)
        controls.addStretch()

        layout.addLayout(controls)

        self.btn_apply_light_props.setEnabled(False)
        self._update_light_color_button()

        return group

    def _build_output_group(self):
        group = QtGui.QGroupBox("Salida / Output")
        grid = QtGui.QGridLayout(group)

        grid.addWidget(QtGui.QLabel("Carpeta / Folder"), 0, 0)
        self.output_dir_line = QtGui.QLineEdit()
        grid.addWidget(self.output_dir_line, 0, 1)
        btn_browse_dir = QtGui.QPushButton("Examinar / Browse")
        btn_browse_dir.clicked.connect(self._browse_output_dir)
        grid.addWidget(btn_browse_dir, 0, 2)

        grid.addWidget(QtGui.QLabel("Nombre base / Base name"), 1, 0)
        self.base_name_line = QtGui.QLineEdit()
        grid.addWidget(self.base_name_line, 1, 1)

        self.launch_checkbox = QtGui.QCheckBox("Lanzar Castle Engine al exportar")
        grid.addWidget(self.launch_checkbox, 2, 0, 1, 3)

        return group

    def _build_config_tab(self):
        """Build in-dialog configuration tab (no separate command required)."""
        tab = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(tab)

        nav_group = QtGui.QGroupBox("Castle Model Viewer")
        nav_grid = QtGui.QGridLayout(nav_group)
        nav_grid.addWidget(QtGui.QLabel("Velocidad WALK / Walk speed"), 0, 0)
        self.spin_nav_speed = QtGui.QDoubleSpinBox()
        self.spin_nav_speed.setRange(0.1, 10000.0)
        self.spin_nav_speed.setDecimals(2)
        self.spin_nav_speed.setSingleStep(0.1)
        nav_grid.addWidget(self.spin_nav_speed, 0, 1)

        nav_grid.addWidget(QtGui.QLabel("Altura avatar (mm) / Avatar height (mm)"), 1, 0)
        self.spin_eye_height_mm = QtGui.QDoubleSpinBox()
        self.spin_eye_height_mm.setRange(100.0, 5000.0)
        self.spin_eye_height_mm.setDecimals(0)
        self.spin_eye_height_mm.setSingleStep(50.0)
        self.spin_eye_height_mm.setSuffix(" mm")
        nav_grid.addWidget(self.spin_eye_height_mm, 1, 1)

        gravity_label = QtGui.QLabel(
            "Gravedad / Gravity: Z+ (fija por conversion de ejes -90 X en exportacion)"
        )
        gravity_label.setWordWrap(True)
        nav_grid.addWidget(gravity_label, 2, 0, 1, 2)
        layout.addWidget(nav_group)

        cge_group = QtGui.QGroupBox("Castle Engine")
        cge_layout = QtGui.QGridLayout(cge_group)
        cge_layout.addWidget(QtGui.QLabel("Ejecutable / Executable"), 0, 0)
        self.cge_path_line = QtGui.QLineEdit()
        cge_layout.addWidget(self.cge_path_line, 0, 1)
        btn_cge_browse = QtGui.QPushButton("Examinar / Browse")
        btn_cge_browse.clicked.connect(self._browse_cge_path)
        cge_layout.addWidget(btn_cge_browse, 0, 2)
        layout.addWidget(cge_group)

        layout.addStretch()
        return tab

    def _load_defaults(self):
        doc = FreeCAD.ActiveDocument
        doc_path = None
        if doc and getattr(doc, "FileName", ""):
            doc_path = Path(doc.FileName)
        self.doc_path = doc_path

        output_dir, base_name, _ = compute_output_defaults(self.params, doc_path)
        self.output_dir_line.setText(output_dir)
        self.base_name_line.setText(base_name)
        self.launch_checkbox.setChecked(bool(self.params.GetBool("launch_cge", False)))
        self.cge_path = self.params.GetString("cge_path", "")
        self.cge_path_line.setText(self.cge_path)
        nav_speed = self._normalize_nav_speed(float(self.params.GetFloat("nav_speed", 2.0)))
        self.spin_nav_speed.setValue(nav_speed)
        self.spin_eye_height_mm.setValue(float(self.params.GetFloat("nav_eye_height_mm", 1600.0)))
        self.chk_global_light.setChecked(bool(self.params.GetBool("gl_enabled", False)))
        self.spin_gl_yaw.setValue(float(self.params.GetFloat("gl_yaw", -30.0)))
        self.spin_gl_pitch.setValue(float(self.params.GetFloat("gl_pitch", -45.0)))
        self.spin_gl_intensity.setValue(float(self.params.GetFloat("gl_intensity", 1.2)))
        color_string = self.params.GetString("gl_color", "255,243,217")
        self.global_light_color = self._color_from_param_string(color_string, self.global_light_color)
        self._update_global_color_button()
        self.chk_pointlights.setChecked(bool(self.params.GetBool("export_pointlights", False)))
        gamestart_label = self.params.GetString("gamestart_label", "GameStart")
        self.gamestart_line.setText(gamestart_label)
        self.root_names = []
        self._load_sidecar()
        self._update_gamestart_state()
        self._update_global_color_button()

    def _load_sidecar(self):
        """Load document-specific preferences from sidecar JSON."""
        self.export_names = set()
        self.sidecar_data = {}
        self.doc_path = None
        self._set_root_names([])

        doc = FreeCAD.ActiveDocument
        if not doc or not getattr(doc, "FileName", ""):
            self._update_root_line()
            return
        self.doc_path = Path(doc.FileName)
        data = persist.load_sidecar(self.doc_path)
        if not data:
            return

        self.sidecar_data = data

        candidate_roots: List[str] = []
        stored_roots = data.get("root_names")
        if isinstance(stored_roots, (list, tuple)):
            candidate_roots = [str(item) for item in stored_roots if str(item).strip()]
        else:
            root_name = str(data.get("root_name", ""))
            if root_name:
                for part in root_name.replace(";", ",").split(","):
                    part = part.strip()
                    if part:
                        candidate_roots.append(part)
        self._set_root_names(candidate_roots)

        export_names = data.get("export_names") or data.get("export_list") or []
        self.export_names = {name for name in export_names if isinstance(name, str)}

        gamestart_label = data.get("gamestart_label")
        if gamestart_label:
            self.gamestart_line.setText(gamestart_label)

        output_cfg = data.get("output", {})
        if isinstance(output_cfg, dict):
            if output_cfg.get("dir"):
                self.output_dir_line.setText(output_cfg["dir"])
            if output_cfg.get("base_name"):
                self.base_name_line.setText(output_cfg["base_name"])

        global_cfg = data.get("global_light")
        if isinstance(global_cfg, dict):
            if "enabled" in global_cfg:
                self.chk_global_light.setChecked(bool(global_cfg.get("enabled", False)))
            if "yaw" in global_cfg:
                self.spin_gl_yaw.setValue(float(global_cfg.get("yaw", self.spin_gl_yaw.value())))
            if "pitch" in global_cfg:
                self.spin_gl_pitch.setValue(float(global_cfg.get("pitch", self.spin_gl_pitch.value())))
            if "intensity" in global_cfg:
                self.spin_gl_intensity.setValue(float(global_cfg.get("intensity", self.spin_gl_intensity.value())))
            if "color" in global_cfg:
                self.global_light_color = self._color_from_config_value(global_cfg["color"])
                self._update_global_color_button()

        navigation_cfg = data.get("navigation")
        if isinstance(navigation_cfg, dict):
            if "speed" in navigation_cfg:
                self.spin_nav_speed.setValue(
                    self._normalize_nav_speed(float(navigation_cfg.get("speed", self.spin_nav_speed.value())))
                )
            if "eye_height_mm" in navigation_cfg:
                self.spin_eye_height_mm.setValue(
                    float(navigation_cfg.get("eye_height_mm", self.spin_eye_height_mm.value()))
                )

        if "export_pointlights" in data:
            self.chk_pointlights.setChecked(bool(data.get("export_pointlights", False)))

        scene_lights = data.get("scene_lights", [])
        resolved_names: set[str] = set()
        if isinstance(scene_lights, (list, tuple)):
            for value in scene_lights:
                candidate = str(value)
                obj = doc.getObject(candidate)
                if obj is None:
                    obj = next((o for o in doc.Objects if getattr(o, "Label", "") == candidate), None)
                if obj is not None:
                    resolved_names.add(obj.Name)
        if not resolved_names:
            label_list = data.get("scene_light_labels", [])
            if isinstance(label_list, (list, tuple)):
                for label in label_list:
                    obj = next((o for o in doc.Objects if getattr(o, "Label", "") == str(label)), None)
                    if obj is not None:
                        resolved_names.add(obj.Name)
        self.light_names = resolved_names
        lights.apply_light_names(doc, self.light_names)

    def _apply_export_selection(self):
        """Move saved export items from available list into export list."""
        if not self.export_names:
            return

        added_names = set()
        move_items = []
        for idx in range(self.list_available.count()):
            item = self.list_available.item(idx)
            name = item.data(QtCore.Qt.UserRole)
            if name in self.export_names:
                move_items.append(item)

        for item in move_items:
            name = item.data(QtCore.Qt.UserRole)
            new = QtGui.QListWidgetItem(item.text())
            new.setData(QtCore.Qt.UserRole, name)
            self.list_export.addItem(new)
            row = self.list_available.row(item)
            self.list_available.takeItem(row)
            added_names.add(name)

        remaining = set(self.export_names) - added_names
        doc = FreeCAD.ActiveDocument
        for name in sorted(remaining):
            obj = doc.getObject(name) if doc else None
            text = self._format_object_label(obj, name)
            item = QtGui.QListWidgetItem(text)
            item.setData(QtCore.Qt.UserRole, name)
            if obj is None:
                item.setForeground(QtGui.QBrush(QtGui.QColor("#9ca3af")))
            self.list_export.addItem(item)

        self._update_export_names()

    def _update_export_names(self):
        """Refresh the cached set of export object names."""
        self.export_names = {
            self.list_export.item(i).data(QtCore.Qt.UserRole)
            for i in range(self.list_export.count())
        }

    def _save_sidecar(self, output_dir: str, base_name: str, gamestart_label: str):
        """Persist current selections to the sidecar JSON."""
        if self.doc_path is None:
            FreeCAD.Console.PrintMessage("[GAMEEXPORT] Sidecar not saved (document without file path)\n")
            return

        doc = FreeCAD.ActiveDocument
        data = dict(self.sidecar_data) if isinstance(self.sidecar_data, dict) else {}

        root_labels = []
        if doc:
            for name in self.root_names:
                obj = doc.getObject(name)
                if obj is not None and getattr(obj, "Label", ""):
                    root_labels.append(obj.Label)

        data["root_names"] = list(self.root_names)
        data["root_name"] = ";".join(self.root_names)
        data["root_label"] = ", ".join(root_labels)
        data["export_names"] = sorted(self.export_names)
        data["gamestart_label"] = gamestart_label
        data["output"] = {"dir": output_dir, "base_name": base_name}

        global_color_ints = [int(max(0, min(255, round(c * 255.0)))) for c in self.global_light_color]
        data["global_light"] = {
            "enabled": bool(self.chk_global_light.isChecked()),
            "yaw": float(self.spin_gl_yaw.value()),
            "pitch": float(self.spin_gl_pitch.value()),
            "intensity": float(self.spin_gl_intensity.value()),
            "color": global_color_ints,
        }
        data["navigation"] = self._navigation_config()

        data["export_pointlights"] = bool(self.chk_pointlights.isChecked())
        self._update_light_names()
        data["scene_lights"] = sorted(self.light_names)

        if doc:
            data["document_label"] = doc.Label
            export_labels = []
            for name in data["export_names"]:
                obj = doc.getObject(name)
                if obj is not None:
                    export_labels.append(obj.Label)
            if export_labels:
                data["export_labels"] = export_labels
            light_labels = []
            for name in data["scene_lights"]:
                obj = doc.getObject(name)
                if obj is not None:
                    light_labels.append(obj.Label)
            if light_labels:
                data["scene_light_labels"] = light_labels

        self.sidecar_data = data
        persist.save_sidecar(self.doc_path, data)

    def _refresh_available(self):
        previous_export = set(self.export_names)
        self.list_export.clear()
        self.export_names = previous_export
        self.list_available.clear()
        selected_light_names = []
        if hasattr(self, "list_lights"):
            selected_light_names = [
                self.list_lights.item(i).data(QtCore.Qt.UserRole)
                for i in range(self.list_lights.count())
                if self.list_lights.item(i).isSelected()
            ]
            self.list_lights.clear()
        doc = FreeCAD.ActiveDocument
        if doc is None:
            self.status_label.setText("No hay documento activo.")
            self.light_names = set()
            return

        roots = self._resolve_root_objects(doc)
        objects = self._collect_objects_for_display(doc, roots)

        gs_label = self.gamestart_line.text().strip() or "GameStart"
        gs_obj = gamestart.find_gamestart(doc, gs_label)
        gs_name = gs_obj.Name if gs_obj else None

        seen = set()
        for obj in objects:
            if obj is None:
                continue
            if obj.Name in seen:
                continue
            seen.add(obj.Name)
            if obj.Name == gs_name or getattr(obj, "Label", "") == gs_label:
                continue
            if getattr(obj, "ViewObject", None) is None and not hasattr(obj, "Group"):
                continue
            item = QtGui.QListWidgetItem(self._format_object_label(obj, obj.Name))
            item.setData(QtCore.Qt.UserRole, obj.Name)
            self.list_available.addItem(item)

        self.status_label.setText(f"Objetos disponibles: {self.list_available.count()}")
        self._update_gamestart_state()
        self._apply_export_selection()
        self._refresh_light_list(selected_light_names)

    def _clear_export_list(self):
        self.list_export.clear()
        self._update_export_names()

    def _move_selected_to_export(self):
        selected = list(self.list_available.selectedItems())
        if not selected:
            return
        for item in self.list_available.selectedItems():
            new = QtGui.QListWidgetItem(item.text())
            new.setData(QtCore.Qt.UserRole, item.data(QtCore.Qt.UserRole))
            self.list_export.addItem(new)
        for item in self.list_available.selectedItems():
            row = self.list_available.row(item)
            self.list_available.takeItem(row)
        self._update_export_names()

    def _move_selected_to_available(self):
        selected = list(self.list_export.selectedItems())
        if not selected:
            return
        for item in self.list_export.selectedItems():
            new = QtGui.QListWidgetItem(item.text())
            new.setData(QtCore.Qt.UserRole, item.data(QtCore.Qt.UserRole))
            self.list_available.addItem(new)
        for item in self.list_export.selectedItems():
            row = self.list_export.row(item)
            self.list_export.takeItem(row)
        self._update_export_names()

    def _add_current_selection_to_export(self):
        """Add current 3D selection (e.g. selected with Shift+B) into export list."""
        doc = FreeCAD.ActiveDocument
        if doc is None:
            self.status_label.setText("No hay documento activo.")
            return

        selected = FreeCADGui.Selection.getSelection()
        if not selected:
            self.status_label.setText("Seleccion vacia.")
            return

        export_names = {
            self.list_export.item(i).data(QtCore.Qt.UserRole)
            for i in range(self.list_export.count())
        }
        available_by_name = {}
        for i in range(self.list_available.count()):
            item = self.list_available.item(i)
            available_by_name[item.data(QtCore.Qt.UserRole)] = item

        added = 0
        for obj in selected:
            if obj is None or obj.Document != doc:
                continue
            name = obj.Name
            if name in export_names:
                continue

            existing = available_by_name.get(name)
            if existing is not None:
                row = self.list_available.row(existing)
                self.list_available.takeItem(row)
                new_item = QtGui.QListWidgetItem(existing.text())
                new_item.setData(QtCore.Qt.UserRole, name)
            else:
                new_item = QtGui.QListWidgetItem(self._format_object_label(obj, name))
                new_item.setData(QtCore.Qt.UserRole, name)

            self.list_export.addItem(new_item)
            export_names.add(name)
            added += 1

        self._update_export_names()
        self.status_label.setText(f"Agregados a exportar: {added}")

    def _use_selection_as_root(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            self.status_label.setText("No hay documento activo.")
            return
        selected = FreeCADGui.Selection.getSelection()
        if not selected:
            self.status_label.setText("Seleccion vacia.")
            return
        added = []
        for obj in selected:
            if obj is None or obj.Document != doc:
                continue
            if obj.Name not in self.root_names:
                self.root_names.append(obj.Name)
                added.append(obj.Label if getattr(obj, "Label", "") else obj.Name)
        if not added:
            self.status_label.setText("Raices sin cambios.")
        else:
            self.status_label.setText("Raices agregadas: " + ", ".join(added))
        self._update_root_line()
        self._refresh_available()

    def _clear_root_selection(self):
        self.root_names = []
        self._update_root_line()
        self._refresh_available()
        self.status_label.setText("Raices limpiadas.")

    def _set_root_names(self, names):
        doc = FreeCAD.ActiveDocument
        unique = []
        if doc:
            for name in names:
                obj = doc.getObject(str(name))
                if obj is not None and obj.Name not in unique:
                    unique.append(obj.Name)
        self.root_names = unique
        self._update_root_line()

    def _update_root_line(self):
        if not self.root_names:
            self.root_line.setText("")
            return
        doc = FreeCAD.ActiveDocument
        display_names = []
        for name in self.root_names:
            label = name
            if doc:
                obj = doc.getObject(name)
                if obj is not None:
                    lbl = getattr(obj, "Label", "")
                    if lbl and lbl != name:
                        label = f"{lbl} ({name})"
                    else:
                        label = name
            display_names.append(label)
        self.root_line.setText(", ".join(display_names))

    def _resolve_root_objects(self, doc):
        if doc is None:
            return []
        resolved = []
        valid_names = []
        for name in self.root_names:
            obj = doc.getObject(name)
            if obj is not None:
                resolved.append(obj)
                valid_names.append(obj.Name)
        if valid_names != self.root_names:
            self.root_names = valid_names
            self._update_root_line()
        return resolved

    def _collect_objects_for_display(self, doc, roots):
        if doc is None:
            return []
        seen = set()
        ordered = []

        def traverse(obj):
            if obj is None or obj.Name in seen:
                return
            seen.add(obj.Name)
            if self._is_exportable_object(obj):
                ordered.append(obj)
            if hasattr(obj, "Group"):
                for child in obj.Group:
                    traverse(child)

        if roots:
            for root in roots:
                traverse(root)
        else:
            for obj in doc.Objects:
                traverse(obj)
        return ordered

    def _format_object_label(self, obj, fallback_name):
        if obj is None:
            return fallback_name
        label = getattr(obj, "Label", "")
        if label and label != obj.Name:
            return f"{label} ({obj.Name})"
        return obj.Name

    def _is_exportable_object(self, obj):
        if obj is None:
            return False
        if hasattr(obj, "Group"):
            return True
        view = getattr(obj, "ViewObject", None)
        if view is None or getattr(view, "Visibility", True) is False:
            return False
        type_id = getattr(obj, "TypeId", "")
        if type_id.startswith("App::Annotation") or type_id.startswith("Spreadsheet::"):
            return False
        if type_id.startswith("TechDraw::"):
            return False
        if hasattr(obj, "LinkedObject") and obj.LinkedObject is None:
            return False
        if not hasattr(obj, "Shape") and not hasattr(obj, "Mesh"):
            return False
        return True

    def _browse_output_dir(self):
        start_dir = self.output_dir_line.text() or os.path.expanduser("~")
        selected = QtGui.QFileDialog.getExistingDirectory(
            self.widget, "Seleccionar carpeta de salida", start_dir
        )
        if selected:
            self.output_dir_line.setText(selected)

    def _browse_cge_path(self):
        start = self.cge_path_line.text().strip() or os.path.expanduser("~")
        selected, _ = QtGui.QFileDialog.getOpenFileName(
            self.widget,
            "Seleccionar ejecutable Castle / Select Castle executable",
            start,
        )
        if selected:
            self.cge_path_line.setText(selected)

    def _create_gamestart(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            self.status_label.setText("No hay documento activo.")
            return
        label = self.gamestart_line.text().strip() or "GameStart"
        obj = gamestart.ensure_gamestart(doc, label)
        created = obj is not None
        if created:
            self.gamestart_line.setText(obj.Label)
        self._update_gamestart_state()
        doc.recompute()
        self._refresh_available()
        if created:
            self.status_label.setText("GameStart creado.")
        else:
            self.status_label.setText("No se pudo crear GameStart.")

    def _update_gamestart_state(self):
        doc = FreeCAD.ActiveDocument
        label = self.gamestart_line.text().strip() or "GameStart"
        obj = gamestart.find_gamestart(doc, label) if doc else None
        if obj:
            self.label_gamestart_state.setText("GameStart listo")
            self.label_gamestart_state.setStyleSheet("color: #16a34a;")
        else:
            self.label_gamestart_state.setText("GameStart no encontrado")
            self.label_gamestart_state.setStyleSheet("color: #dc2626;")
        return obj

    @staticmethod
    def _color_from_param_string(text: str, default: tuple[float, float, float]) -> tuple[float, float, float]:
        try:
            parts = [int(p) for p in text.split(",")]
            if len(parts) == 3:
                return tuple(max(0.0, min(1.0, p / 255.0)) for p in parts)
        except Exception:
            pass
        return default

    def _color_from_config_value(self, value) -> tuple[float, float, float]:
        if isinstance(value, str):
            return self._color_from_param_string(value, self.global_light_color)
        if isinstance(value, (list, tuple)) and len(value) == 3:
            try:
                if any(float(v) > 1.0 for v in value):
                    return tuple(max(0.0, min(1.0, float(v) / 255.0)) for v in value)
                return tuple(max(0.0, min(1.0, float(v))) for v in value)
            except Exception:
                pass
        return self.global_light_color

    @staticmethod
    def _color_to_param_string(color: tuple[float, float, float]) -> str:
        vals = [max(0, min(255, int(round(c * 255.0)))) for c in color]
        return "{},{},{}".format(*vals)

    def _update_global_color_button(self) -> None:
        r, g, b = [max(0, min(255, int(round(c * 255.0)))) for c in self.global_light_color]
        qcolor = QtGui.QColor(r, g, b)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        text_color = "#000000" if luminance > 150 else "#ffffff"
        self.btn_gl_color.setStyleSheet(
            f"background-color: {qcolor.name()}; color: {text_color}; border: 1px solid #444;"
        )

    def _choose_global_color(self):
        current = QtGui.QColor(
            int(self.global_light_color[0] * 255),
            int(self.global_light_color[1] * 255),
            int(self.global_light_color[2] * 255),
        )
        new_color = QtGui.QColorDialog.getColor(current, self.widget, "Seleccionar color / Select color")
        if new_color.isValid():
            self.global_light_color = (
                new_color.red() / 255.0,
                new_color.green() / 255.0,
                new_color.blue() / 255.0,
            )
            self._update_global_color_button()
            if isinstance(self.sidecar_data, dict):
                gl_cfg = dict(self.sidecar_data.get("global_light", {}))
                gl_cfg["color"] = [new_color.red(), new_color.green(), new_color.blue()]
                self.sidecar_data["global_light"] = gl_cfg

    def _open_solar_dialog(self):
        now = datetime.datetime.now()
        offset_hours = -time.timezone / 3600.0
        if time.daylight and time.localtime().tm_isdst:
            offset_hours += 1.0

        gl_cfg = self.sidecar_data.get("global_light") if isinstance(self.sidecar_data, dict) else {}
        if not isinstance(gl_cfg, dict):
            gl_cfg = {}

        lat_default = float(gl_cfg.get("latitude", 10.0))
        lon_default = float(gl_cfg.get("longitude", -84.0))
        tz_default = float(gl_cfg.get("timezone", offset_hours))
        timestamp = gl_cfg.get("timestamp")
        stored_dt = None
        if isinstance(timestamp, str):
            try:
                stored_dt = datetime.datetime.fromisoformat(timestamp)
            except Exception:
                stored_dt = None
        if stored_dt is None:
            stored_dt = now

        dialog = QtGui.QDialog(self.widget)
        dialog.setWindowTitle("Hora solar / Solar time")
        main_layout = QtGui.QVBoxLayout(dialog)
        form = QtGui.QFormLayout()

        lat_spin = QtGui.QDoubleSpinBox()
        lat_spin.setRange(-90.0, 90.0)
        lat_spin.setDecimals(3)
        lat_spin.setValue(lat_default)

        lon_spin = QtGui.QDoubleSpinBox()
        lon_spin.setRange(-180.0, 180.0)
        lon_spin.setDecimals(3)
        lon_spin.setValue(lon_default)

        tz_spin = QtGui.QDoubleSpinBox()
        tz_spin.setRange(-14.0, 14.0)
        tz_spin.setSingleStep(0.25)
        tz_spin.setDecimals(2)
        tz_spin.setValue(tz_default)

        dt_edit = QtGui.QDateTimeEdit()
        dt_edit.setCalendarPopup(True)
        dt_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        dt_edit.setDateTime(
            QtCore.QDateTime(
                stored_dt.year,
                stored_dt.month,
                stored_dt.day,
                stored_dt.hour,
                stored_dt.minute,
                stored_dt.second,
            )
        )

        btn_now = QtGui.QPushButton("Usar ahora / Use current time")

        def _apply_now():
            current_dt = QtCore.QDateTime.currentDateTime()
            dt_edit.setDateTime(current_dt)

        btn_now.clicked.connect(_apply_now)

        form.addRow("Latitud (°)", lat_spin)
        form.addRow("Longitud (°)", lon_spin)
        form.addRow("Zona horaria UTC", tz_spin)
        form.addRow("Fecha y hora", dt_edit)

        main_layout.addLayout(form)
        main_layout.addWidget(btn_now)

        button_box = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        main_layout.addWidget(button_box)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        if dialog.exec_() != QtGui.QDialog.Accepted:
            return

        lat = float(lat_spin.value())
        lon = float(lon_spin.value())
        tz_hours = float(tz_spin.value())
        qdt = dt_edit.dateTime()
        dt = datetime.datetime(
            qdt.date().year(),
            qdt.date().month(),
            qdt.date().day(),
            qdt.time().hour(),
            qdt.time().minute(),
            qdt.time().second(),
        )

        try:
            yaw, pitch, altitude = self._compute_solar_angles(lat, lon, tz_hours, dt)
        except ValueError as exc:
            self.status_label.setText(str(exc))
            return

        self.chk_global_light.setChecked(True)
        self.spin_gl_yaw.setValue(yaw)
        self.spin_gl_pitch.setValue(pitch)
        self.status_label.setText(
            "Luz solar: yaw {:.1f}°, pitch {:.1f}° (altura solar {:.1f}°)".format(yaw, pitch, altitude)
        )

        if not isinstance(self.sidecar_data, dict):
            self.sidecar_data = {}
        gl_cfg = dict(self.sidecar_data.get("global_light", {}))
        gl_cfg.update(
            {
                "enabled": True,
                "yaw": yaw,
                "pitch": pitch,
                "intensity": float(self.spin_gl_intensity.value()),
                "color": [
                    int(max(0, min(255, round(self.global_light_color[0] * 255.0)))),
                    int(max(0, min(255, round(self.global_light_color[1] * 255.0)))),
                    int(max(0, min(255, round(self.global_light_color[2] * 255.0)))),
                ],
                "latitude": lat,
                "longitude": lon,
                "timezone": tz_hours,
                "timestamp": dt.isoformat(timespec="minutes"),
            }
        )
        self.sidecar_data["global_light"] = gl_cfg

    def _compute_solar_angles(
        self, latitude: float, longitude: float, tz_hours: float, dt: datetime.datetime
    ) -> tuple[float, float, float]:
        lat_rad = math.radians(latitude)
        n = dt.timetuple().tm_yday
        decl_deg = 23.45 * math.sin(math.radians((360.0 / 365.0) * (284 + n)))
        decl_rad = math.radians(decl_deg)
        B = math.radians((360.0 / 365.0) * (n - 81))
        eq_time = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
        lstm = 15.0 * tz_hours
        local_minutes = dt.hour * 60.0 + dt.minute + dt.second / 60.0
        time_offset = eq_time + 4.0 * (longitude - lstm)
        true_solar_minutes = local_minutes + time_offset
        solar_time_hours = true_solar_minutes / 60.0
        hour_angle_rad = math.radians(15.0 * (solar_time_hours - 12.0))

        altitude_rad = math.asin(
            math.sin(lat_rad) * math.sin(decl_rad)
            + math.cos(lat_rad) * math.cos(decl_rad) * math.cos(hour_angle_rad)
        )
        if altitude_rad <= 0:
            raise ValueError("Sol por debajo del horizonte para esa hora.")

        azimuth_rad = math.atan2(
            -math.sin(hour_angle_rad),
            math.tan(decl_rad) * math.cos(lat_rad) - math.sin(lat_rad) * math.cos(hour_angle_rad),
        )

        dx = math.cos(altitude_rad) * math.sin(azimuth_rad)
        dy = -math.cos(altitude_rad) * math.cos(azimuth_rad)
        dz = math.sin(altitude_rad)
        horizontal = math.sqrt(max(1e-9, dx * dx + dy * dy))
        yaw_deg = math.degrees(math.atan2(dx, -dy))
        yaw_deg = ((yaw_deg + 180.0) % 360.0) - 180.0
        pitch_deg = math.degrees(math.atan2(-dz, horizontal))
        pitch_deg = max(-90.0, min(90.0, pitch_deg))
        altitude_deg = math.degrees(altitude_rad)
        return yaw_deg, pitch_deg, altitude_deg
    def _update_light_names(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            self.light_names = set()
            return
        current = lights.list_point_lights(doc)
        self.light_names = {obj.Name for obj in current}

    def _refresh_light_list(self, selected_names: Optional[List[str]] = None):
        if selected_names is None:
            selected_names = [
                self.list_lights.item(i).data(QtCore.Qt.UserRole)
                for i in range(self.list_lights.count())
                if self.list_lights.item(i).isSelected()
            ]
        selected_set = set(selected_names or [])

        self.list_lights.clear()
        doc = FreeCAD.ActiveDocument
        if doc is None:
            self.btn_apply_light_props.setEnabled(False)
            return
        self._update_light_names()
        for obj in lights.list_point_lights(doc):
            props = lights.get_light_properties(obj)
            color = props["color"]
            color_hex = "#{:02x}{:02x}{:02x}".format(
                int(color[0] * 255),
                int(color[1] * 255),
                int(color[2] * 255),
            )
            text = (
                f"{obj.Label} ({obj.Name})  "
                f"I={props['intensity']:.2f}  R={props['radius']:.1f}  C={color_hex}"
            )
            item = QtGui.QListWidgetItem(text)
            item.setData(QtCore.Qt.UserRole, obj.Name)
            self.list_lights.addItem(item)
            if obj.Name in selected_set:
                item.setSelected(True)

        self._on_lights_selection_changed()

    def _update_light_color_button(self):
        r = int(max(0, min(255, round(self.light_color_current[0] * 255.0))))
        g = int(max(0, min(255, round(self.light_color_current[1] * 255.0))))
        b = int(max(0, min(255, round(self.light_color_current[2] * 255.0))))
        color = QtGui.QColor(r, g, b)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        text_color = "#000000" if luminance > 150 else "#ffffff"
        self.btn_light_color.setStyleSheet(
            f"background-color: {color.name()}; color: {text_color}; border: 1px solid #444;"
        )

    def _choose_light_color(self):
        current = QtGui.QColor(
            int(self.light_color_current[0] * 255),
            int(self.light_color_current[1] * 255),
            int(self.light_color_current[2] * 255),
        )
        chosen = QtGui.QColorDialog.getColor(current, self.widget, "Color de luz / Light color")
        if chosen.isValid():
            self.light_color_current = (
                chosen.red() / 255.0,
                chosen.green() / 255.0,
                chosen.blue() / 255.0,
            )
            self._update_light_color_button()

    def _on_lights_selection_changed(self):
        items = self.list_lights.selectedItems()
        has_selection = bool(items)
        self.btn_apply_light_props.setEnabled(has_selection)
        doc = FreeCAD.ActiveDocument
        if not has_selection or doc is None:
            return
        name = items[0].data(QtCore.Qt.UserRole)
        obj = doc.getObject(name) if name else None
        if obj is None:
            return
        props = lights.get_light_properties(obj)
        self.spin_light_intensity.setValue(props["intensity"])
        self.spin_light_radius.setValue(props["radius"])
        self.light_color_current = props["color"]
        self._update_light_color_button()

    def _apply_light_properties(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            self.status_label.setText("No hay documento activo.")
            return
        items = self.list_lights.selectedItems()
        if not items:
            self.status_label.setText("Selecciona una luz en la lista.")
            return
        objects = []
        names = []
        for item in items:
            name = item.data(QtCore.Qt.UserRole)
            obj = doc.getObject(name) if name else None
            if obj is not None:
                objects.append(obj)
                names.append(obj.Name)
        if not objects:
            self.status_label.setText("No se encontraron objetos para actualizar.")
            return
        lights.set_light_properties(
            doc,
            objects,
            intensity=self.spin_light_intensity.value(),
            radius=self.spin_light_radius.value(),
            color=self.light_color_current,
        )
        labels = [getattr(obj, "Label", obj.Name) for obj in objects]
        self.status_label.setText("Luces actualizadas: " + ", ".join(labels))
        self._refresh_light_list(names)
        if isinstance(self.sidecar_data, dict):
            self.sidecar_data["scene_lights"] = sorted(self.light_names)

    def _add_lights_from_selection(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            self.status_label.setText("No hay documento activo.")
            return
        selection = FreeCADGui.Selection.getSelection()
        if not selection:
            self.status_label.setText("Seleccion vacia.")
            return
        names = lights.tag_selection_as_light(doc, selection)
        if names:
            self.status_label.setText("Marcadas como luz: " + ", ".join(names))
        else:
            self.status_label.setText("No se pudo marcar seleccion.")
        self._refresh_light_list(names)
        if isinstance(self.sidecar_data, dict):
            self.sidecar_data["scene_lights"] = sorted(self.light_names)

    def _remove_lights_from_list(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            self.status_label.setText("No hay documento activo.")
            return
        items = self.list_lights.selectedItems()
        if not items:
            self.status_label.setText("Selecciona una luz en la lista.")
            return
        objects = []
        for item in items:
            name = item.data(QtCore.Qt.UserRole)
            obj = doc.getObject(name) if name else None
            if obj is not None:
                objects.append(obj)
        if not objects:
            self.status_label.setText("No se encontraron objetos para quitar.")
            return
        names = lights.untag_selection_as_light(doc, objects)
        if names:
            self.status_label.setText("Luces quitadas: " + ", ".join(names))
        else:
            self.status_label.setText("No se pudo quitar la marca de luz.")
        self._refresh_light_list()
        if isinstance(self.sidecar_data, dict):
            self.sidecar_data["scene_lights"] = sorted(self.light_names)

    def _global_light_config(self) -> dict | None:
        if not self.chk_global_light.isChecked():
            return None
        return {
            "enabled": True,
            "yaw": float(self.spin_gl_yaw.value()),
            "pitch": float(self.spin_gl_pitch.value()),
            "intensity": float(self.spin_gl_intensity.value()),
            "color": self.global_light_color,
        }

    def _navigation_config(self) -> dict:
        speed = self._normalize_nav_speed(float(self.spin_nav_speed.value()))
        if abs(speed - float(self.spin_nav_speed.value())) > 1e-9:
            self.spin_nav_speed.setValue(speed)
        return {
            "speed": speed,
            "eye_height_mm": float(self.spin_eye_height_mm.value()),
            "gravity_up": "Z+",
        }

    def _normalize_nav_speed(self, speed: float) -> float:
        """Normalize navigation speed and migrate legacy bad default 2000->2."""
        if speed >= 1500.0:
            return 2.0
        return max(0.1, min(10000.0, float(speed)))

    def _point_light_entries(self, doc):
        if not self.chk_pointlights.isChecked():
            return []
        self._update_light_names()
        entries = []
        for data in lights.gather_point_light_data(doc, self.light_names):
            entries.append(
                {
                    "name": data.name,
                    "label": data.label,
                    "position_mm": data.position_mm,
                    "intensity": data.intensity,
                    "color": data.color_rgb,
                    "radius": data.radius,
                }
            )
        return entries

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)

    def accept(self):
        if self._export_scene():
            FreeCADGui.Control.closeDialog()
            return True
        return False

    def reject(self):
        FreeCAD.Console.PrintMessage("[GAMEEXPORT] Export dialog cancelled\n")
        FreeCADGui.Control.closeDialog()
        return True

    def _collect_export_objects(self, doc, gamestart_obj):
        export_names = [
            self.list_export.item(i).data(QtCore.Qt.UserRole)
            for i in range(self.list_export.count())
        ]
        export_objects = []
        for name in export_names:
            obj = doc.getObject(name)
            if obj is not None and obj is not gamestart_obj:
                export_objects.append(obj)

        if not export_objects:
            FreeCAD.Console.PrintMessage("[GAMEEXPORT] Export list empty, using entire document\n")
            export_objects = [obj for obj in doc.Objects if obj is not gamestart_obj]

        return export_objects

    def _diagnose_export_selection(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            self.status_label.setText("No hay documento activo.")
            return

        gamestart_label = self.gamestart_line.text().strip() or "GameStart"
        gamestart_obj = gamestart.find_gamestart(doc, gamestart_label)
        export_objects = self._collect_export_objects(doc, gamestart_obj)
        if not export_objects:
            self.status_label.setText("No hay objetos para diagnosticar.")
            return

        diag = exporter_x3d.diagnose_export_candidates(export_objects, log=True)
        total = int(diag.get("total", 0))
        skipped = len(diag.get("skipped", []))
        exportable = len(diag.get("exportable", []))
        self.status_label.setText(
            f"Diagnostico: {exportable}/{total} exportables, {skipped} omitidos (ver consola)."
        )

    def _export_scene(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            FreeCAD.Console.PrintError("[GAMEEXPORT] No active document to export\n")
            return False

        gamestart_label = self.gamestart_line.text().strip() or "GameStart"
        gamestart_obj = gamestart.find_gamestart(doc, gamestart_label)
        export_objects = self._collect_export_objects(doc, gamestart_obj)

        if not export_objects:
            FreeCAD.Console.PrintError("[GAMEEXPORT] No geometry selected for export\n")
            return False

        output_dir = self.output_dir_line.text().strip()
        base_name = self.base_name_line.text().strip()
        if not output_dir:
            FreeCAD.Console.PrintError("[GAMEEXPORT] Output folder is empty\n")
            return False
        if not base_name:
            base_name = doc.Label.replace(" ", "_") or doc.Name

        safe_base_name = normalize_base_name(base_name)

        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as exc:
            FreeCAD.Console.PrintError("[GAMEEXPORT] Cannot create output folder: " + str(exc) + "\n")
            return False

        file_path = Path(output_dir) / (safe_base_name + ".x3d")
        gamestart_meta = gamestart.get_metadata(gamestart_obj) if gamestart_obj else None
        lighting_cfg = {
            "global": self._global_light_config(),
            "point_lights": self._point_light_entries(doc),
            "navigation": self._navigation_config(),
        }
        try:
            exporter_x3d.export_to_x3d(export_objects, file_path, gamestart_meta, lighting_cfg)
        except Exception as exc:
            FreeCAD.Console.PrintError("[GAMEEXPORT] Export failed: " + str(exc) + "\n")
            return False

        # Persist last choices
        persist_output_settings(self.params, output_dir, base_name, self.doc_path)
        self.params.SetBool("launch_cge", bool(self.launch_checkbox.isChecked()))
        self.cge_path = self.cge_path_line.text().strip()
        self.params.SetString("cge_path", self.cge_path)
        self.params.SetFloat("nav_speed", float(self.spin_nav_speed.value()))
        self.params.SetFloat("nav_eye_height_mm", float(self.spin_eye_height_mm.value()))
        self.params.SetString("gamestart_label", gamestart_label)
        self.params.SetBool("gl_enabled", bool(self.chk_global_light.isChecked()))
        self.params.SetFloat("gl_yaw", float(self.spin_gl_yaw.value()))
        self.params.SetFloat("gl_pitch", float(self.spin_gl_pitch.value()))
        self.params.SetFloat("gl_intensity", float(self.spin_gl_intensity.value()))
        self.params.SetString("gl_color", self._color_to_param_string(self.global_light_color))
        self.params.SetBool("export_pointlights", bool(self.chk_pointlights.isChecked()))

        self._update_export_names()
        self._save_sidecar(output_dir, base_name, gamestart_label)

        if self.launch_checkbox.isChecked():
            self._launch_castle_engine(str(file_path))

        self.status_label.setText("Exportacion completada: " + str(file_path))
        return True

    def _launch_castle_engine(self, file_path):
        cge_path = self.cge_path.strip()
        if not cge_path:
            FreeCAD.Console.PrintError("[GAMEEXPORT] Castle Engine path not configured\n")
            return
        if not os.path.isfile(cge_path):
            FreeCAD.Console.PrintError("[GAMEEXPORT] Castle Engine executable not found\n")
            return
        try:
            subprocess.Popen([cge_path, file_path])
            FreeCAD.Console.PrintMessage("[GAMEEXPORT] Launching Castle Engine\n")
        except Exception as exc:
            FreeCAD.Console.PrintError("[GAMEEXPORT] Failed to launch Castle Engine: " + str(exc) + "\n")


__all__ = ["ExportTaskPanel"]
