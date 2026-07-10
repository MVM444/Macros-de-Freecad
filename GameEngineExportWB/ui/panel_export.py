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
import json
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
DEBUG_VERSION = "2026-07-08-ground-texture-fallback"


def _qt_button_mask(*buttons) -> int:
    mask = 0
    for button in buttons:
        try:
            mask |= int(button)
            continue
        except TypeError:
            pass
        value = getattr(button, "value", button)
        mask |= int(value)
    return mask


class ExportTaskPanel:
    """TaskPanel to manage selection and export workflow."""

    def __init__(self):
        FreeCAD.Console.PrintMessage("[GAMEEXPORT] Opening export panel\n")
        FreeCAD.Console.PrintMessage("[GAMEEXPORT] Debug version: " + DEBUG_VERSION + "\n")
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
        self.version_label = QtGui.QLabel(_git_last_update_label() + " | Panel: " + DEBUG_VERSION)
        self.version_label.setStyleSheet("color: #1f4e79; font-size: 11px;")
        layout.addWidget(self.version_label)

        self.tabs = QtGui.QTabWidget()
        layout.addWidget(self.tabs)

        scene_tab = QtGui.QWidget()
        scene_layout = QtGui.QVBoxLayout(scene_tab)
        scene_layout.addWidget(self._build_root_group())
        scene_layout.addWidget(self._build_gamestart_group())
        scene_layout.addWidget(self._build_lists_group())
        scene_layout.addWidget(self._build_output_group())
        scene_layout.addStretch()
        self.tabs.addTab(scene_tab, "Escena / Scene")

        lighting_tab = self._build_lighting_tab()
        self.tabs.addTab(lighting_tab, "Iluminacion / Lighting")

        textures_tab = self._build_textures_tab()
        self.tabs.addTab(textures_tab, "Texturas / Textures")

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

        layout.addWidget(QtGui.QLabel("Yaw (deg)"), 1, 0)
        self.spin_gl_yaw = QtGui.QDoubleSpinBox()
        self.spin_gl_yaw.setRange(-180.0, 180.0)
        self.spin_gl_yaw.setSingleStep(1.0)
        layout.addWidget(self.spin_gl_yaw, 1, 1)

        layout.addWidget(QtGui.QLabel("Pitch (deg)"), 2, 0)
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

        self.chk_gl_shadows = QtGui.QCheckBox("Sombras / Shadows")
        self.chk_gl_shadows.setToolTip(
            "ES: Activa sombras X3D para la luz global. Puede bajar el rendimiento.\n"
            "EN: Enable X3D shadows for the global light. May reduce performance."
        )
        layout.addWidget(self.chk_gl_shadows, 5, 0, 1, 2)

        return group

    def _build_scene_lights_group(self):
        group = QtGui.QGroupBox("Luces de escena / Scene lights")
        layout = QtGui.QVBoxLayout(group)

        self.chk_pointlights = QtGui.QCheckBox("Exportar PointLights / Export point lights")
        self.chk_pointlights.setToolTip(
            "ES: Marca luminarias para exportarlas como PointLight.\nEN: Mark fixtures to export as PointLight."
        )
        layout.addWidget(self.chk_pointlights)

        render_row = QtGui.QHBoxLayout()
        self.chk_pointlight_shadows = QtGui.QCheckBox(
            "Sombras limitadas / Limited shadows"
        )
        self.chk_pointlight_shadows.setToolTip(
            "ES: Experimental. Activa sombras solo en pocas PointLight para evitar shaders morados/lentos.\n"
            "EN: Experimental. Enables shadows on only a few PointLights to avoid slow/purple shaders."
        )
        render_row.addWidget(self.chk_pointlight_shadows)

        render_row.addWidget(QtGui.QLabel("Max sombras / Max shadows"))
        self.spin_max_shadow_lights = QtGui.QSpinBox()
        self.spin_max_shadow_lights.setRange(0, 4)
        self.spin_max_shadow_lights.setValue(1)
        render_row.addWidget(self.spin_max_shadow_lights)

        render_row.addWidget(QtGui.QLabel("Atenuacion / Falloff"))
        self.combo_pointlight_falloff = QtGui.QComboBox()
        self.combo_pointlight_falloff.addItems(["Interior", "Soft", "Constant"])
        render_row.addWidget(self.combo_pointlight_falloff)
        render_row.addStretch()
        layout.addLayout(render_row)

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

    def _build_lighting_tab(self):
        tab = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(tab)
        layout.addWidget(self._build_global_light_group())
        layout.addWidget(self._build_scene_lights_group())
        layout.addWidget(self._build_materials_group())
        layout.addStretch()
        return tab

    def _build_materials_group(self):
        group = QtGui.QGroupBox("Materiales X3D / X3D Materials")
        grid = QtGui.QGridLayout(group)

        self.chk_improve_interior_lighting = QtGui.QCheckBox(
            "Mejorar iluminacion interior / Improve interior lighting"
        )
        grid.addWidget(self.chk_improve_interior_lighting, 0, 0, 1, 2)

        grid.addWidget(QtGui.QLabel("Modo / Mode"), 1, 0)
        self.combo_interior_lighting_mode = QtGui.QComboBox()
        self.combo_interior_lighting_mode.addItems(["None", "Soft", "Architectural", "Bright"])
        self.chk_improve_interior_lighting.toggled.connect(self._on_improve_interior_lighting_toggled)
        self.combo_interior_lighting_mode.currentIndexChanged.connect(self._on_material_lighting_mode_changed)
        grid.addWidget(self.combo_interior_lighting_mode, 1, 1)

        return group

    def _build_textures_tab(self):
        tab = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(tab)
        layout.addWidget(self._build_ground_texture_group())
        layout.addStretch()
        return tab

    def _build_ground_texture_group(self):
        group = QtGui.QGroupBox("Textura de suelo / Ground texture")
        grid = QtGui.QGridLayout(group)

        self.chk_ground_texture = QtGui.QCheckBox("Aplicar textura al objeto suelo / Apply texture to ground object")
        self.chk_ground_texture.setToolTip(
            "ES: Cambia solo el X3D exportado; no modifica materiales de FreeCAD.\n"
            "EN: Changes only the exported X3D; FreeCAD materials are not modified."
        )
        self.chk_ground_texture.toggled.connect(self._update_ground_texture_status)
        grid.addWidget(self.chk_ground_texture, 0, 0, 1, 4)

        grid.addWidget(QtGui.QLabel("Objeto / Object"), 1, 0)
        self.ground_object_line = QtGui.QLineEdit()
        self.ground_object_line.setReadOnly(True)
        grid.addWidget(self.ground_object_line, 1, 1)
        btn_ground_selection = QtGui.QPushButton("Tomar seleccion / Use selection")
        btn_ground_selection.clicked.connect(self._use_selection_as_ground_texture_object)
        grid.addWidget(btn_ground_selection, 1, 2, 1, 2)

        grid.addWidget(QtGui.QLabel("Textura / Texture"), 2, 0)
        self.ground_texture_line = QtGui.QLineEdit()
        self.ground_texture_line.textChanged.connect(self._update_ground_texture_status)
        grid.addWidget(self.ground_texture_line, 2, 1)
        btn_texture_browse = QtGui.QPushButton("Examinar / Browse")
        btn_texture_browse.clicked.connect(self._browse_ground_texture)
        grid.addWidget(btn_texture_browse, 2, 2, 1, 2)

        grid.addWidget(QtGui.QLabel("Repetir S / Repeat S"), 3, 0)
        self.spin_ground_repeat_s = QtGui.QDoubleSpinBox()
        self.spin_ground_repeat_s.setRange(0.01, 1000.0)
        self.spin_ground_repeat_s.setDecimals(2)
        self.spin_ground_repeat_s.setSingleStep(1.0)
        self.spin_ground_repeat_s.setValue(20.0)
        grid.addWidget(self.spin_ground_repeat_s, 3, 1)

        grid.addWidget(QtGui.QLabel("Repetir T / Repeat T"), 3, 2)
        self.spin_ground_repeat_t = QtGui.QDoubleSpinBox()
        self.spin_ground_repeat_t.setRange(0.01, 1000.0)
        self.spin_ground_repeat_t.setDecimals(2)
        self.spin_ground_repeat_t.setSingleStep(1.0)
        self.spin_ground_repeat_t.setValue(20.0)
        grid.addWidget(self.spin_ground_repeat_t, 3, 3)

        self.chk_ground_planar_uv = QtGui.QCheckBox("Generar UV planar XY / Generate planar XY UV")
        self.chk_ground_planar_uv.setChecked(True)
        self.chk_ground_planar_uv.setToolTip(
            "ES: Crea coordenadas UV desde X/Y del objeto exportado para evitar textura estirada.\n"
            "EN: Creates UV coordinates from exported object X/Y to avoid stretched texture."
        )
        grid.addWidget(self.chk_ground_planar_uv, 4, 0, 1, 4)

        self.ground_texture_status_label = QtGui.QLabel("")
        self.ground_texture_status_label.setStyleSheet("color: #475569;")
        grid.addWidget(self.ground_texture_status_label, 5, 0, 1, 4)

        return group

    def _add_skybox_controls(self, grid, row_offset: int) -> None:
        sky_label = QtGui.QLabel("Cielo Castle Viewer / Castle Viewer sky")
        sky_label.setStyleSheet("font-weight: bold;")
        grid.addWidget(sky_label, row_offset, 0, 1, 4)

        self.chk_environment_skybox = QtGui.QCheckBox("Usar cielo de Castle Viewer / Use Castle Viewer sky")
        self.chk_environment_skybox.setToolTip(
            "ES: Inserta un Background con las seis imagenes de example_models/skies.\n"
            "EN: Insert a Background using the six images from example_models/skies."
        )
        self.chk_environment_skybox.toggled.connect(self._update_skybox_status)
        grid.addWidget(self.chk_environment_skybox, row_offset + 1, 0, 1, 4)

        grid.addWidget(QtGui.QLabel("Carpeta skies / Skies folder"), row_offset + 2, 0)
        self.skybox_dir_line = QtGui.QLineEdit()
        self.skybox_dir_line.textChanged.connect(self._update_skybox_status)
        grid.addWidget(self.skybox_dir_line, row_offset + 2, 1)

        btn_detect = QtGui.QPushButton("Detectar / Detect")
        btn_detect.clicked.connect(self._detect_skybox_dir_from_config)
        grid.addWidget(btn_detect, row_offset + 2, 2)

        btn_browse = QtGui.QPushButton("Examinar / Browse")
        btn_browse.clicked.connect(self._browse_skybox_dir)
        grid.addWidget(btn_browse, row_offset + 2, 3)

        self.skybox_status_label = QtGui.QLabel("")
        self.skybox_status_label.setStyleSheet("color: #475569;")
        grid.addWidget(self.skybox_status_label, row_offset + 3, 0, 1, 4)

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
        self.cge_path_line.textChanged.connect(self._update_skybox_status)
        cge_layout.addWidget(self.cge_path_line, 0, 1)
        btn_cge_browse = QtGui.QPushButton("Examinar / Browse")
        btn_cge_browse.clicked.connect(self._browse_cge_path)
        cge_layout.addWidget(btn_cge_browse, 0, 2)
        self._add_skybox_controls(cge_layout, 1)
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
        self.chk_gl_shadows.setChecked(bool(self.params.GetBool("gl_shadows", False)))
        color_string = self.params.GetString("gl_color", "255,243,217")
        self.global_light_color = self._color_from_param_string(color_string, self.global_light_color)
        self._update_global_color_button()
        self.chk_pointlights.setChecked(bool(self.params.GetBool("export_pointlights", False)))
        shadow_version = self.params.GetString("pointlight_shadow_version", "")
        self.chk_pointlight_shadows.setChecked(
            bool(self.params.GetBool("pointlight_shadows", False)) and shadow_version == "limited-v1"
        )
        self.spin_max_shadow_lights.setValue(int(self.params.GetInt("pointlight_max_shadows", 1)))
        self._set_point_light_falloff_mode(self.params.GetString("pointlight_falloff", "Interior"))
        self.chk_improve_interior_lighting.setChecked(
            bool(self.params.GetBool("improve_interior_lighting", False))
        )
        self._set_material_lighting_mode(self.params.GetString("interior_lighting_mode", "None"))
        self.chk_environment_skybox.setChecked(bool(self.params.GetBool("env_use_skybox", False)))
        stored_skybox_dir = self.params.GetString("env_skybox_dir", "").strip()
        self.skybox_dir_line.setText(stored_skybox_dir or self._discover_skybox_dir())
        self._update_skybox_status()
        self.chk_ground_texture.setChecked(bool(self.params.GetBool("ground_texture_enabled", False)))
        self.ground_object_line.setText(self.params.GetString("ground_texture_object", ""))
        self.ground_texture_line.setText(self.params.GetString("ground_texture_path", ""))
        self.spin_ground_repeat_s.setValue(float(self.params.GetFloat("ground_texture_repeat_s", 20.0)))
        self.spin_ground_repeat_t.setValue(float(self.params.GetFloat("ground_texture_repeat_t", 20.0)))
        self.chk_ground_planar_uv.setChecked(bool(self.params.GetBool("ground_texture_planar_uv", True)))
        self._update_ground_texture_status()
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
            if "shadows" in global_cfg:
                self.chk_gl_shadows.setChecked(bool(global_cfg.get("shadows", False)))

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

        point_options = data.get("point_light_options")
        if isinstance(point_options, dict):
            if "shadows" in point_options:
                has_safe_limit = "max_shadow_lights" in point_options
                self.chk_pointlight_shadows.setChecked(bool(point_options.get("shadows", False)) and has_safe_limit)
            if "max_shadow_lights" in point_options:
                self.spin_max_shadow_lights.setValue(
                    max(0, min(4, int(point_options.get("max_shadow_lights", 1) or 1)))
                )
            if "falloff" in point_options:
                self._set_point_light_falloff_mode(str(point_options.get("falloff", "Interior")))

        materials_cfg = data.get("materials")
        if isinstance(materials_cfg, dict):
            if "improve_interior_lighting" in materials_cfg:
                self.chk_improve_interior_lighting.setChecked(
                    bool(materials_cfg.get("improve_interior_lighting", False))
                )
            if "interior_lighting_mode" in materials_cfg:
                self._set_material_lighting_mode(str(materials_cfg.get("interior_lighting_mode", "None")))

        environment_cfg = data.get("environment")
        if isinstance(environment_cfg, dict):
            if "use_skybox" in environment_cfg:
                self.chk_environment_skybox.setChecked(bool(environment_cfg.get("use_skybox", False)))
            if "skybox_dir" in environment_cfg:
                sidecar_skybox_dir = str(environment_cfg.get("skybox_dir", "") or "").strip()
                if sidecar_skybox_dir:
                    self.skybox_dir_line.setText(sidecar_skybox_dir)
            if not self.skybox_dir_line.text().strip():
                    self.skybox_dir_line.setText(self._discover_skybox_dir())
            self._update_skybox_status()

        ground_cfg = data.get("ground_texture")
        if isinstance(ground_cfg, dict):
            if "enabled" in ground_cfg:
                self.chk_ground_texture.setChecked(bool(ground_cfg.get("enabled", False)))
            if "object_name" in ground_cfg:
                self.ground_object_line.setText(str(ground_cfg.get("object_name", "") or ""))
            if "texture_path" in ground_cfg:
                self.ground_texture_line.setText(str(ground_cfg.get("texture_path", "") or ""))
            if "repeat_s" in ground_cfg:
                self.spin_ground_repeat_s.setValue(float(ground_cfg.get("repeat_s", self.spin_ground_repeat_s.value())))
            if "repeat_t" in ground_cfg:
                self.spin_ground_repeat_t.setValue(float(ground_cfg.get("repeat_t", self.spin_ground_repeat_t.value())))
            if "generate_planar_uv" in ground_cfg:
                self.chk_ground_planar_uv.setChecked(bool(ground_cfg.get("generate_planar_uv", True)))
            self._update_ground_texture_status()

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
            "shadows": bool(self.chk_gl_shadows.isChecked()),
        }
        data["navigation"] = self._navigation_config()
        data["materials"] = self._material_lighting_config()
        data["environment"] = self._environment_config_for_sidecar()
        data["point_light_options"] = self._point_light_options_config()
        data["ground_texture"] = self._ground_texture_config()

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
            if not exporter_x3d.detect_skybox_faces(self.skybox_dir_line.text().strip()):
                detected = self._discover_skybox_dir()
                if detected:
                    self.skybox_dir_line.setText(detected)
            self._update_skybox_status()

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

        form.addRow("Latitud (deg)", lat_spin)
        form.addRow("Longitud (deg)", lon_spin)
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
            "Luz solar: yaw {:.1f} deg, pitch {:.1f} deg (altura solar {:.1f} deg)".format(
                yaw, pitch, altitude
            )
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
            "shadows": bool(self.chk_gl_shadows.isChecked()),
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

    def _material_lighting_config(self) -> dict:
        return {
            "improve_interior_lighting": bool(self.chk_improve_interior_lighting.isChecked()),
            "interior_lighting_mode": self._material_lighting_mode(),
        }

    def _ground_texture_config(self, log: bool = False) -> dict:
        object_name = self.ground_object_line.text().strip()
        doc = FreeCAD.ActiveDocument
        target_obj = self._find_ground_texture_object(doc, object_name)
        cfg = {
            "enabled": bool(self.chk_ground_texture.isChecked()),
            "object_name": object_name,
            "object_label": str(getattr(target_obj, "Label", "") or "") if target_obj is not None else "",
            "texture_path": self.ground_texture_line.text().strip(),
            "repeat_s": float(self.spin_ground_repeat_s.value()),
            "repeat_t": float(self.spin_ground_repeat_t.value()),
            "generate_planar_uv": bool(self.chk_ground_planar_uv.isChecked()),
        }
        if log and cfg["enabled"]:
            if not cfg["object_name"]:
                FreeCAD.Console.PrintWarning("[GAMEEXPORT][WARN] Ground texture enabled without object.\n")
            elif target_obj is None:
                FreeCAD.Console.PrintWarning(
                    "[GAMEEXPORT][WARN] Ground texture object not found in document: "
                    + cfg["object_name"]
                    + "; exporter will try inferred terrain target.\n"
                )
            if not cfg["texture_path"]:
                FreeCAD.Console.PrintWarning("[GAMEEXPORT][WARN] Ground texture enabled without texture file.\n")
            elif not os.path.isfile(cfg["texture_path"]):
                FreeCAD.Console.PrintWarning(
                    "[GAMEEXPORT][WARN] Ground texture file not found: " + cfg["texture_path"] + "\n"
                )
            else:
                FreeCAD.Console.PrintMessage(
                    "[GAMEEXPORT] Ground texture enabled for object "
                    + cfg["object_name"]
                    + ": "
                    + cfg["texture_path"]
                    + "\n"
                )
        return cfg

    def _use_selection_as_ground_texture_object(self):
        selection = FreeCADGui.Selection.getSelection()
        if not selection:
            self.status_label.setText("Seleccione el objeto suelo.")
            return
        obj = selection[0]
        self.ground_object_line.setText(str(getattr(obj, "Name", "") or ""))
        self.chk_ground_texture.setChecked(True)
        self._update_ground_texture_status()
        label = getattr(obj, "Label", "") or getattr(obj, "Name", "")
        self.status_label.setText("Objeto suelo seleccionado: " + str(label))

    def _browse_ground_texture(self):
        start = self.ground_texture_line.text().strip() or os.path.expanduser("~")
        selected, _ = QtGui.QFileDialog.getOpenFileName(
            self.widget,
            "Seleccionar textura de suelo / Select ground texture",
            start,
            "Images (*.png *.jpg *.jpeg *.webp);;All files (*.*)",
        )
        if selected:
            self.ground_texture_line.setText(selected)
            self.chk_ground_texture.setChecked(True)
            self._update_ground_texture_status()

    def _update_ground_texture_status(self, *_args) -> None:
        if not hasattr(self, "ground_texture_status_label"):
            return
        if not bool(self.chk_ground_texture.isChecked()):
            self.ground_texture_status_label.setText("Textura de suelo desactivada / Ground texture disabled")
            return
        object_name = self.ground_object_line.text().strip()
        texture_path = self.ground_texture_line.text().strip()
        if not object_name:
            self.ground_texture_status_label.setText("Falta seleccionar objeto suelo")
            return
        if not texture_path:
            self.ground_texture_status_label.setText("Falta seleccionar archivo de textura")
            return
        if not os.path.isfile(texture_path):
            self.ground_texture_status_label.setText("Archivo de textura no encontrado")
            return
        if self._find_ground_texture_object(FreeCAD.ActiveDocument, object_name) is None:
            self.ground_texture_status_label.setText("Objeto suelo no encontrado; se intentara detectar terreno")
            return
        self.ground_texture_status_label.setText("Textura lista para aplicar al X3D")

    def _find_ground_texture_object(self, doc, object_name):
        if doc is None or not object_name:
            return None
        obj = doc.getObject(object_name)
        if obj is not None:
            return obj
        for candidate in getattr(doc, "Objects", []):
            if str(getattr(candidate, "Label", "") or "") == object_name:
                return candidate
        return None

    def _point_light_options_config(self) -> dict:
        shadows = bool(self.chk_pointlight_shadows.isChecked())
        falloff = self._point_light_falloff_mode()
        max_shadow_lights = max(0, min(4, int(self.spin_max_shadow_lights.value())))
        attenuation = {
            "Interior": "1 0.25 0.04",
            "Soft": "1 0.08 0.01",
            "Constant": "1 0 0",
        }.get(falloff, "1 0.25 0.04")
        return {
            "shadows": shadows,
            "max_shadow_lights": max_shadow_lights,
            "falloff": falloff,
            "attenuation": attenuation,
            "ambient_intensity": 0.04 if falloff == "Interior" else 0.10,
        }

    def _point_light_falloff_mode(self) -> str:
        mode = str(self.combo_pointlight_falloff.currentText() or "Interior")
        if mode not in {"Interior", "Soft", "Constant"}:
            return "Interior"
        return mode

    def _set_point_light_falloff_mode(self, mode: str) -> None:
        clean_mode = mode if mode in {"Interior", "Soft", "Constant"} else "Interior"
        index = self.combo_pointlight_falloff.findText(clean_mode)
        if index < 0:
            index = 0
        self.combo_pointlight_falloff.setCurrentIndex(index)

    def _environment_config(self, log: bool = False) -> dict:
        use_skybox = bool(self.chk_environment_skybox.isChecked())
        skybox_dir = self.skybox_dir_line.text().strip()
        detected = self._discover_skybox_dir()
        source = "manual"
        if use_skybox and not exporter_x3d.detect_skybox_faces(skybox_dir):
            if detected:
                skybox_dir = detected
                self.skybox_dir_line.setText(detected)
                if log:
                    FreeCAD.Console.PrintMessage(
                        "[GAMEEXPORT] Skybox folder auto-detected from Castle executable: "
                        + detected
                        + "\n"
                    )
        if detected and skybox_dir == detected:
            source = "castle_executable"
        if use_skybox and log:
            if exporter_x3d.detect_skybox_faces(skybox_dir):
                FreeCAD.Console.PrintMessage("[GAMEEXPORT] Environment skybox enabled: " + skybox_dir + "\n")
            else:
                FreeCAD.Console.PrintWarning(
                    "[GAMEEXPORT][WARN] Environment skybox enabled but no complete skies folder was found.\n"
                )
        elif log:
            FreeCAD.Console.PrintMessage("[GAMEEXPORT] Environment skybox disabled\n")
        return {
            "use_skybox": use_skybox,
            "skybox_dir": skybox_dir,
            "skybox_source": source,
        }

    def _environment_config_for_sidecar(self) -> dict:
        cfg = self._environment_config(log=False)
        if cfg.get("skybox_source") == "castle_executable":
            cfg["skybox_dir"] = ""
        return cfg

    def _browse_skybox_dir(self):
        start_dir = self.skybox_dir_line.text().strip() or self._discover_skybox_dir() or os.path.expanduser("~")
        selected = QtGui.QFileDialog.getExistingDirectory(
            self.widget,
            "Seleccionar carpeta skies / Select skies folder",
            start_dir,
        )
        if selected:
            self.skybox_dir_line.setText(selected)
            self._update_skybox_status()

    def _detect_skybox_dir_from_config(self):
        detected = self._discover_skybox_dir()
        if detected:
            self.skybox_dir_line.setText(detected)
            self.chk_environment_skybox.setChecked(True)
            self._update_skybox_status()
            self.status_label.setText("Cielo detectado: " + detected)
        else:
            self._update_skybox_status()
            self.status_label.setText("No se encontro carpeta skies junto al ejecutable Castle.")

    def _update_skybox_status(self, *_args) -> None:
        if not hasattr(self, "skybox_status_label"):
            return
        folder = self.skybox_dir_line.text().strip() if hasattr(self, "skybox_dir_line") else ""
        faces = exporter_x3d.detect_skybox_faces(folder)
        if not bool(self.chk_environment_skybox.isChecked()):
            if len(faces) == 6:
                self.skybox_status_label.setText("Cielo desactivado. Cubemap valido detectado.")
            else:
                detected = self._discover_skybox_dir()
                if detected:
                    self.skybox_status_label.setText("Cielo desactivado. Detectado junto al ejecutable Castle.")
                else:
                    self.skybox_status_label.setText("Cielo desactivado. Use Detectar o Examinar.")
            return
        if len(faces) == 6:
            self.skybox_status_label.setText("Cubemap completo: 6 imagenes detectadas")
        else:
            detected = self._discover_skybox_dir()
            if detected and detected != folder:
                self.skybox_status_label.setText("Cubemap detectado junto al ejecutable Castle. Pulse Detectar.")
            else:
                self.skybox_status_label.setText("Falta cubemap completo: back, bottom, front, left, right, top")

    def _discover_skybox_dir(self) -> str:
        for candidate in self._skybox_candidate_dirs():
            if exporter_x3d.detect_skybox_faces(str(candidate)):
                return str(candidate)
        return ""

    def _skybox_candidate_dirs(self) -> list[Path]:
        candidates: list[Path] = []

        def add_candidate(path_value) -> None:
            if not path_value:
                return
            try:
                path = Path(str(path_value)).expanduser()
            except Exception:
                return
            if path not in candidates:
                candidates.append(path)

        cge_text = ""
        if hasattr(self, "cge_path_line"):
            cge_text = self.cge_path_line.text().strip()
        if not cge_text and hasattr(self, "cge_path"):
            cge_text = str(self.cge_path or "").strip()

        if cge_text:
            exe_path = Path(cge_text).expanduser()
            bases = [exe_path.parent, exe_path.parent.parent]
            for base in bases:
                add_candidate(base / "example_models" / "skies")
                add_candidate(base / "data" / "example_models" / "skies")

        home = Path.home()
        add_candidate(home / "Desktop" / "castle-model-viewer" / "example_models" / "skies")
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            add_candidate(Path(userprofile) / "Desktop" / "castle-model-viewer" / "example_models" / "skies")

        return candidates

    def _on_improve_interior_lighting_toggled(self, checked) -> None:
        if bool(checked) and self._material_lighting_mode() == "None":
            self._set_material_lighting_mode("Architectural")

    def _on_material_lighting_mode_changed(self, *_args) -> None:
        if self._material_lighting_mode() != "None":
            self.chk_improve_interior_lighting.setChecked(True)

    def _material_lighting_mode(self) -> str:
        mode = str(self.combo_interior_lighting_mode.currentText() or "None")
        if mode not in {"None", "Soft", "Architectural", "Bright"}:
            return "None"
        return mode

    def _set_material_lighting_mode(self, mode: str) -> None:
        clean_mode = mode if mode in {"None", "Soft", "Architectural", "Bright"} else "None"
        index = self.combo_interior_lighting_mode.findText(clean_mode)
        if index < 0:
            index = 0
        self.combo_interior_lighting_mode.setCurrentIndex(index)

    def _normalize_nav_speed(self, speed: float) -> float:
        """Normalize navigation speed and migrate legacy bad default 2000->2."""
        if speed >= 1500.0:
            return 2.0
        return max(0.1, min(10000.0, float(speed)))

    def _point_light_entries(self, doc, export_objects=None, debug_records=None):
        entries = []
        manual_count = 0
        if self.chk_pointlights.isChecked():
            self._update_light_names()
            for data in lights.gather_point_light_data(
                doc,
                self.light_names,
                skip_effective_cge=True,
                debug_records=debug_records,
            ):
                entries.append(self._point_light_entry_dict(data))
                manual_count += 1
            if manual_count == 0:
                FreeCAD.Console.PrintWarning(
                    "[GAMEEXPORT][WARN] Manual point lights enabled but no tagged objects were found.\n"
                )
        cge_data = lights.gather_cge_light_data(doc, export_objects, debug_records)
        if not cge_data and export_objects is not None:
            FreeCAD.Console.PrintWarning(
                "[GAMEEXPORT][WARN] No CGE lights found in export selection; retrying full document scan.\n"
            )
            if debug_records is not None:
                debug_records.append({"event": "cge_fallback_full_document_scan"})
            cge_data = lights.gather_cge_light_data(doc, None, debug_records)
        cge_count = 0
        for data in cge_data:
            entries.append(self._point_light_entry_dict(data))
            cge_count += 1
        point_options = self._point_light_options_config()
        shadow_indices = set()
        if point_options["shadows"] and point_options["max_shadow_lights"] > 0:
            ranked = sorted(
                range(len(entries)),
                key=lambda idx: float(entries[idx].get("intensity", 0.0) or 0.0),
                reverse=True,
            )
            shadow_indices = set(ranked[: point_options["max_shadow_lights"]])
        for index, entry in enumerate(entries):
            entry["shadows"] = index in shadow_indices
            entry["falloff"] = point_options["falloff"]
            entry["attenuation"] = point_options["attenuation"]
            entry["ambient_intensity"] = point_options["ambient_intensity"]
        if entries:
            shadowed_count = len(shadow_indices)
            if point_options["shadows"] and shadowed_count < len(entries):
                FreeCAD.Console.PrintWarning(
                    "[GAMEEXPORT][WARN] PointLight shadows limited to "
                    + str(shadowed_count)
                    + " of "
                    + str(len(entries))
                    + " lights to avoid Castle shader resource overflow.\n"
                )
            FreeCAD.Console.PrintMessage(
                "[GAMEEXPORT] PointLight entries prepared: "
                + f"manual={manual_count}, cge={cge_count}, total={len(entries)}, "
                + "shadowed="
                + str(shadowed_count)
                + ", falloff="
                + str(point_options["falloff"])
                + "\n"
            )
        elif debug_records is not None:
            debug_records.append({"event": "no_point_lights_prepared"})
        return entries

    @staticmethod
    def _point_light_entry_dict(data):
        return {
            "name": data.name,
            "label": data.label,
            "position_mm": data.position_mm,
            "intensity": data.intensity,
            "color": data.color_rgb,
            "radius": data.radius,
        }

    def _save_debug_snapshot(
        self,
        file_path: Path,
        doc,
        export_objects,
        point_entries,
        debug_records,
        environment_cfg=None,
        ground_texture_cfg=None,
    ) -> None:
        debug_path = file_path.with_suffix(".gee.debug.json")
        try:
            payload = {
                "debug_version": DEBUG_VERSION,
                "document": {
                    "name": str(getattr(doc, "Name", "") or ""),
                    "label": str(getattr(doc, "Label", "") or ""),
                    "file": str(getattr(doc, "FileName", "") or ""),
                },
                "output_x3d": str(file_path),
                "export_object_count": len(export_objects or []),
                "export_objects": [self._debug_object_info(obj) for obj in export_objects or []],
                "point_light_count": len(point_entries or []),
                "point_lights": list(point_entries or []),
                "light_source_names": self._light_source_names_from_entries(point_entries),
                "environment": dict(environment_cfg or {}),
                "ground_texture": dict(ground_texture_cfg or {}),
                "records": list(debug_records or []),
            }
            debug_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True), encoding="utf-8")
            FreeCAD.Console.PrintMessage("[GAMEEXPORT] Debug snapshot saved at " + str(debug_path) + "\n")
        except Exception as exc:
            FreeCAD.Console.PrintWarning("[GAMEEXPORT][WARN] Could not save debug snapshot: " + str(exc) + "\n")

    @staticmethod
    def _light_source_names_from_entries(point_entries) -> list:
        names = []
        seen = set()
        for entry in point_entries or []:
            name = str(entry.get("name", "") or "")
            if "_CGE_" in name:
                name = name.split("_CGE_", 1)[0]
            if name and name not in seen:
                seen.add(name)
                names.append(name)
        return names

    @staticmethod
    def _debug_object_info(obj):
        if obj is None:
            return None
        placement = lights.get_global_placement(obj)
        base = getattr(placement, "Base", None)
        return {
            "name": str(getattr(obj, "Name", "") or ""),
            "label": str(getattr(obj, "Label", "") or ""),
            "type_id": str(getattr(obj, "TypeId", "") or ""),
            "global_base_mm": [
                float(getattr(base, "x", 0.0)),
                float(getattr(base, "y", 0.0)),
                float(getattr(base, "z", 0.0)),
            ],
        }

    def getStandardButtons(self):
        return _qt_button_mask(QtGui.QDialogButtonBox.Ok, QtGui.QDialogButtonBox.Cancel)

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
        light_debug_records = []
        point_light_entries = self._point_light_entries(doc, export_objects, light_debug_records)
        lighting_cfg = {
            "global": self._global_light_config(),
            "point_lights": point_light_entries,
            "navigation": self._navigation_config(),
        }
        material_cfg = self._material_lighting_config()
        material_cfg["light_source_names"] = self._light_source_names_from_entries(point_light_entries)
        environment_cfg = self._environment_config(log=True)
        ground_texture_cfg = self._ground_texture_config(log=True)
        self._save_debug_snapshot(
            file_path,
            doc,
            export_objects,
            point_light_entries,
            light_debug_records,
            environment_cfg,
            ground_texture_cfg,
        )
        try:
            exporter_x3d.export_to_x3d(
                export_objects,
                file_path,
                gamestart_meta,
                lighting_cfg,
                material_cfg,
                environment_cfg,
                ground_texture_cfg,
            )
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
        self.params.SetBool("gl_shadows", bool(self.chk_gl_shadows.isChecked()))
        self.params.SetString("gl_color", self._color_to_param_string(self.global_light_color))
        self.params.SetBool("export_pointlights", bool(self.chk_pointlights.isChecked()))
        self.params.SetBool("pointlight_shadows", bool(self.chk_pointlight_shadows.isChecked()))
        self.params.SetInt("pointlight_max_shadows", int(self.spin_max_shadow_lights.value()))
        self.params.SetString("pointlight_shadow_version", "limited-v1")
        self.params.SetString("pointlight_falloff", self._point_light_falloff_mode())
        self.params.SetBool(
            "improve_interior_lighting", bool(self.chk_improve_interior_lighting.isChecked())
        )
        self.params.SetString("interior_lighting_mode", self._material_lighting_mode())
        self.params.SetBool("env_use_skybox", bool(self.chk_environment_skybox.isChecked()))
        self.params.SetString("env_skybox_dir", self.skybox_dir_line.text().strip())
        self.params.SetBool("ground_texture_enabled", bool(self.chk_ground_texture.isChecked()))
        self.params.SetString("ground_texture_object", self.ground_object_line.text().strip())
        self.params.SetString("ground_texture_path", self.ground_texture_line.text().strip())
        self.params.SetFloat("ground_texture_repeat_s", float(self.spin_ground_repeat_s.value()))
        self.params.SetFloat("ground_texture_repeat_t", float(self.spin_ground_repeat_t.value()))
        self.params.SetBool("ground_texture_planar_uv", bool(self.chk_ground_planar_uv.isChecked()))

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
