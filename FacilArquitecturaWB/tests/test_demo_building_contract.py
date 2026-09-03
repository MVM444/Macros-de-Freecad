from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_demo_command_reuses_existing_bim_utilities():
    text = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    assert "build_demo_spec" in text
    assert "create_site_floor_from_sketches" in text
    assert "create_walls_from_centerline_sketches" in text
    assert "create_openings_from_centerlines" in text
    assert "create_closed_room_sketch" in text
    assert "create_bim_spaces" in text
    assert "def _make_bim_spaces" not in text
    assert "create_modular_ceilings" in text
    assert "create_roof_from_rectangle_programmatic" in text
    assert 'CommandName = "FA_DemoBuilding"' in text
    assert "ReloadableCommandProxy" in text
    assert "App.newDocument" in text


def test_roof_exposes_programmatic_adapter_without_dialog():
    text = (ROOT / "commands" / "cmd_roof_axis_prototype.py").read_text(encoding="utf-8")
    assert "def create_roof_from_rectangle_programmatic(" in text
    assert "save_preferences=False" in text
    assert "manage_transaction=True" in text


def test_initgui_registers_demo_in_project_toolbar():
    text = (ROOT / "InitGui.py").read_text(encoding="utf-8")
    assert "cmd_demo_building" in text
    assert '"demo_building": cmd_demo_building.register().CommandName' in text
    project_chunk = text.split('"FA Proyecto BIM"', 1)[1].split('),', 1)[0]
    assert 'registered["demo_building"]' in project_chunk


def test_demo_recomputes_wall_sources_before_floor_bounds_are_read():
    text = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    wall_sources = text.split("def _step_wall_sources(self):", 1)[1].split("def _step_floor(self):", 1)[0]
    floor_step = text.split("def _step_floor(self):", 1)[1].split("def _step_walls(self):", 1)[0]
    assert "self.doc.recompute()" in wall_sources
    assert "_validate_recomputed_footprint(self.exterior_sketch, self.spec)" in wall_sources
    assert "create_site_floor_from_sketches(" in floor_step
    assert "building_width_mm" in text
    assert "_sync_demo_parameter_sheet(self.parameter_sheet, self.spec)" in text


def test_demo_v2_ceiling_accepts_native_spaces():
    text = (ROOT / "core" / "ceiling_utils.py").read_text(encoding="utf-8")
    assert "def _is_bim_space" in text
    assert "FA_FloorPolygonJSON" in text
    assert "if spaces:" in text


def test_guided_demo_reuses_same_session_and_specification():
    text = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    assert "class DemoBuildingSession" in text
    assert "class GuidedDemoDock" in text
    assert "QtCore.QTimer" in text
    assert '"Demostracion guiada paso a paso", "guided"' in text
    assert "session.execute_step(number, manage_transaction=False)" in text
    assert "self.session.execute_step(number, manage_transaction=True)" in text
    assert "rebuild_to_step" in text
    assert "start_guided_demo(spec)" in text




def test_guided_demo_dock_is_idempotent_across_hot_reload():
    text = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    assert 'GUIDED_DOCK_OBJECT_NAME = "FA_DemoGuidedDock"' in text
    assert "main_window.findChildren(QtWidgets.QDockWidget)" in text
    assert "main_window.removeDockWidget(dock)" in text
    assert "dock.deleteLater()" in text
    assert "cleanup_guided_demo_docks()" in text
    assert "cleanup_guided_demo_docks(main_window=main_window, keep=current)" in text
    close_event = text.split("def closeEvent(self, event):", 1)[1].split("def start_guided_demo", 1)[0]
    assert "_clear_active_guided_dock(self)" in close_event
    assert "resizeDocks(" not in text
    assert "tabifyDockWidget(" not in text

def test_guided_demo_separates_opening_sources_from_bim_materialization():
    text = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    assert "def _step_door_sources(self):" in text
    assert "def _step_doors(self):" in text
    assert "def _step_window_sources(self):" in text
    assert "def _step_windows(self):" in text
    door_source = text.index("def _step_door_sources(self):")
    doors = text.index("def _step_doors(self):")
    window_source = text.index("def _step_window_sources(self):")
    windows = text.index("def _step_windows(self):")
    assert door_source < doors < window_source < windows


def test_guided_demo_visual_presentation_and_close_contract():
    text = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    assert "from PySide import QtCore, QtGui, QtWidgets" in text
    assert "def apply_guided_presentation(self, step_id):" in text
    assert "transparency=80" in text
    assert "visibility=False" in text
    assert "self.session.apply_guided_presentation(meta[\"id\"])" in text
    assert "self.step_icon" in text
    assert "QtGui.QIcon" in text
    assert "Cerrar demostracion" in text
    assert "self.close_button.clicked.connect(self.close)" in text
    close_event = text.split("def closeEvent(self, event):", 1)[1].split("def start_guided_demo", 1)[0]
    assert "restore_guided_presentation" in close_event
    assert "close_document" not in close_event


def test_demo_defaults_to_guided_and_migrates_old_profile_once():
    text = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    assert 'execution_default_profile' in text
    assert 'self.params.SetString("execution", "guided")' in text
    assert 'GetString("execution", "guided")' in text
    assert 'currentData() or "guided"' in text


def test_initgui_exposes_room_detection_spaces_and_first_steps():
    text = (ROOT / "InitGui.py").read_text(encoding="utf-8")
    assert '"detect_rooms": cmd_detect_rooms_2d.register().CommandName' in text
    assert '"bim_spaces": cmd_create_bim_spaces.register().CommandName' in text
    assert '"first_steps": cmd_first_steps.register().CommandName' in text
    rooms = text.split('"FA Recintos y cielos"', 1)[1].split('),', 1)[0]
    assert 'registered["detect_rooms"]' in rooms
    assert 'registered["bim_spaces"]' in rooms
    assert 'first_steps.schedule_startup_tips()' in text


def test_spaces_service_is_shared_and_export_hint_is_non_importing():
    text = (ROOT / "core" / "space_utils.py").read_text(encoding="utf-8")
    demo = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    command = (ROOT / "commands" / "cmd_create_bim_spaces.py").read_text(encoding="utf-8")
    assert "Arch.makeSpace" in text
    assert "GameExportExclude" in text
    assert "import GameEngineExport" not in text
    assert "from GameEngineExport" not in text
    assert "create_bim_spaces(" in demo
    assert "create_bim_spaces(" in command


def test_long_operation_feedback_is_used_in_key_commands():
    opening_dialog = (ROOT / "ui" / "dialog_opening_parameters.py").read_text(encoding="utf-8")
    doors = (ROOT / "commands" / "cmd_create_doors_bim.py").read_text(encoding="utf-8")
    windows = (ROOT / "commands" / "cmd_create_windows_bim.py").read_text(encoding="utf-8")
    roof = (ROOT / "commands" / "cmd_roof_axis_prototype.py").read_text(encoding="utf-8")
    assert "long_process_message" in opening_dialog
    assert "LongOperationFeedback" in doors
    assert "LongOperationFeedback" in windows
    assert "LongOperationFeedback" in roof
    assert "long_process_message" in roof


def test_demo_long_process_warning_is_painted_and_controls_are_stable():
    text = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    ui = (ROOT / "ui" / "process_feedback.py").read_text(encoding="utf-8")
    assert "self.status_frame.setFixedHeight(86)" in text
    assert "self.duration_note.setMinimumHeight(64)" in text
    assert "controls.addWidget(button, 1)" in text
    assert "def _flush_panel(self):" in text
    assert "FreeCADGui.updateGui()" in text
    assert "widget.repaint()" in text
    assert "El siguiente proceso" in (ROOT / "core" / "process_feedback.py").read_text(encoding="utf-8")
    assert "bar.showMessage(notice)" in ui
    assert "_repaint_now(bar)" in ui


def test_demo_creates_native_site_terrain_as_garden():
    command = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    core = (ROOT / "core" / "demo_building_core.py").read_text(encoding="utf-8")
    assert '"garden_enabled": True' in core
    assert '"create_test_terrain": bool(site_spec.get("garden_enabled", True))' in command
    assert 'terrain.Label = "Jardin - Demo"' in command
    assert '"terrain_variation_mm": 0.0' in core
    assert 'items.append(self.floor_result.get("terrain"))' in command


def test_demo_styles_both_terrain_and_arch_site_as_green_garden():
    command = (ROOT / "commands" / "cmd_demo_building.py").read_text(encoding="utf-8")
    assert 'garden_shape_color = (0.30, 0.62, 0.24)' in command
    assert 'terrain.ViewObject.ShapeColor = garden_shape_color' in command
    assert 'site.ViewObject.ShapeColor = garden_shape_color' in command
    assert 'for garden_obj in (terrain, site):' in command


def test_detect_rooms_falls_back_to_document_when_selection_is_irrelevant():
    text = (ROOT / "commands" / "cmd_detect_rooms_2d.py").read_text(encoding="utf-8")
    assert "if not sources and selection:" in text
    assert "collect_room_source_sketches(doc,selection=None)" in text
    assert "La seleccion actual no contiene fuentes de planta" in text


def test_room_commands_use_reloadable_proxies_in_freecad_113():
    for relative_path in (
        "commands/cmd_detect_rooms_2d.py",
        "commands/cmd_create_bim_spaces.py",
    ):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "ReloadableCommandProxy" in text, relative_path
        assert 'command = ReloadableCommandProxy(' in text, relative_path
        assert '__name__, class_name="CommandClass"' in text, relative_path


def test_room_detection_updates_single_documentary_sketch_in_place():
    text = (ROOT / "core" / "room_utils.py").read_text(encoding="utf-8")
    assert "def _generated_room_sketches(" in text
    assert "def _clear_room_sketch_geometry(" in text
    assert "if len(previous) == 1:" in text
    assert "sketch = previous[0]" in text
    assert "_clear_room_sketch_geometry(sketch)" in text
