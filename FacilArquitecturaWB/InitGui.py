"""FacilArquitecturaWB GUI bootstrap.

Descripcion: registra el workbench Facil Arquitectura y sus comandos iniciales.
Objetivo: exponer comandos independientes y el asistente de reconstruccion BIM nativa.
FreeCAD objetivo: 1.1.3.
Fecha y hora: 2026-09-02 16:22 America/Costa_Rica.
Version: 0.14.11.
Instrucciones de mantenimiento: mantener comandos pequenos y cargar modulos del
workbench de forma explicita. El historial de uso debe observar la interfaz sin
sustituir ni envolver la logica funcional de los comandos.
"""

from __future__ import annotations

import importlib
import os

import FreeCAD
import FreeCADGui

from . import usage_log
from . import i18n
from .commands import cmd_centerlines_from_selection
from .commands import cmd_change_door_type
from .commands import cmd_collect_room_labels
from .commands import cmd_create_building_grid
from .commands import cmd_create_bim_structure
from .commands import cmd_create_closed_rooms
from .commands import cmd_create_doors_bim
from .commands import cmd_create_axes_columns_bim
from .commands import cmd_create_master_sketches
from .commands import cmd_create_modular_ceiling
from .commands import cmd_create_openings_bim
from .commands import cmd_create_project
from .commands import cmd_rebuild_bim_model
from .commands import cmd_create_sample_geometry
from .commands import cmd_create_site_floor_bim
from .commands import cmd_create_service_platform_front
from .commands import cmd_create_walls_bim
from .commands import cmd_create_windows_bim
from .commands import cmd_door_centerlines_from_selection
from .commands import cmd_import_cad_reference
from .commands import cmd_insert_double_door_bim
from .commands import cmd_window_centerlines_from_selection
from .commands import cmd_window_table
from .commands import cmd_door_table
from .commands import cmd_update_service_platform_front
from .commands import cmd_add_cashier_service_window
from .commands import cmd_roof_axis_prototype
from .commands import cmd_edit_truss_axes
from .commands import cmd_demo_building
from .commands import cmd_json_inspector
from .commands import cmd_detect_rooms_2d
from .commands import cmd_create_bim_spaces
from .commands import cmd_first_steps
from .commands import cmd_help
from .ui import first_steps
from .core.constants import BUILD_ID, LOG_PREFIX, VERSION, WORKBENCH_ID, WORKBENCH_NAME


REGISTERED_COMMANDS = []

_USAGE_LOG_ENABLED = False
_CONNECTED_USAGE_ACTIONS = set()
_USAGE_ACTION_CALLBACKS = {}
_COMMAND_GROUP_BY_ID = {}
_USAGE_LOG_OWNER = object()


def _common_rooms_module():
    """Load the neutral room commands, preferring the shared DEV source.

    Public/staged installs carry an exact generated mirror under
    ``FacilArquitecturaWB._bundled.CRBIMCore`` so the Workbench remains
    self-contained.  The external ``CRBIMCore`` package remains the
    authoritative source during monorepo development.
    """
    try:
        return importlib.import_module("CRBIMCore.commands.common_rooms")
    except ModuleNotFoundError as exc:
        missing = str(getattr(exc, "name", "") or "")
        if missing and not missing.startswith("CRBIMCore"):
            raise
    package_name = str(__package__ or "FacilArquitecturaWB")
    return importlib.import_module(
        package_name + "._bundled.CRBIMCore.commands.common_rooms"
    )


def _qt_action_class():
    """Return QAction across the Qt bindings supported by FreeCAD."""
    for package in ("PySide6", "PySide2", "PySide"):
        try:
            module = __import__(package, fromlist=["QtGui", "QtWidgets"])
            qtgui = getattr(module, "QtGui", None)
            qtwidgets = getattr(module, "QtWidgets", None)
            action_cls = getattr(qtgui, "QAction", None) if qtgui is not None else None
            if action_cls is None and qtwidgets is not None:
                action_cls = getattr(qtwidgets, "QAction", None)
            if action_cls is not None:
                return action_cls
        except Exception:
            continue
    return None


def _action_command_id(action) -> str:
    """Resolve the FreeCAD command id represented by a QAction."""
    try:
        name = str(action.objectName() or "")
    except Exception:
        name = ""
    if not name:
        try:
            data = action.data()
            if isinstance(data, str):
                name = data
        except Exception:
            pass
    if not name:
        return ""
    return name.replace("&", "").strip()


def _should_log_command(command_id: str) -> bool:
    return bool(command_id) and command_id.startswith(
        ("FA_", "CRBIM_", "Draft_", "BIM_", "Arch_", "Sketcher_")
    )


def _fa_is_active() -> bool:
    try:
        wb = FreeCADGui.activeWorkbench()
    except Exception:
        wb = None
    if wb is None:
        return False
    try:
        if wb.__class__.__name__ == WORKBENCH_ID:
            return True
    except Exception:
        pass
    try:
        return str(getattr(wb, "MenuText", "") or "") == WORKBENCH_NAME
    except Exception:
        return False


def _on_usage_action(action) -> None:
    if not _USAGE_LOG_ENABLED or not _fa_is_active():
        return
    command_id = _action_command_id(action)
    if not _should_log_command(command_id):
        return
    meta = {"source": "gui_action"}
    try:
        text = str(action.text() or "").replace("&", "").strip()
    except Exception:
        text = ""
    if text:
        meta["text"] = text
    group = _COMMAND_GROUP_BY_ID.get(command_id)
    if group:
        meta["group"] = group
    usage_log.log_tool(command_id, meta)


def _connect_usage_logger() -> int:
    """Connect existing FreeCAD QActions once; safe to call after hot reloads."""
    action_cls = _qt_action_class()
    if action_cls is None:
        return 0
    try:
        main_window = FreeCADGui.getMainWindow()
    except Exception:
        main_window = None
    if main_window is None:
        return 0

    # Keep the registry on FreeCAD's persistent main window so a development
    # hot reload can disconnect callbacks created by the previous Python module.
    try:
        registry = getattr(main_window, "_facilarq_usage_registry", None)
    except Exception:
        registry = None
    if not isinstance(registry, dict) or registry.get("owner") is not _USAGE_LOG_OWNER:
        if isinstance(registry, dict):
            for old_action, old_callback in registry.get("connections", {}).values():
                try:
                    old_action.triggered.disconnect(old_callback)
                except Exception:
                    pass
        registry = {"owner": _USAGE_LOG_OWNER, "connections": {}}
        try:
            setattr(main_window, "_facilarq_usage_registry", registry)
        except Exception:
            pass

    connections = registry.setdefault("connections", {})
    connected = 0
    try:
        actions = list(main_window.findChildren(action_cls))
    except Exception:
        actions = []
    for action in actions:
        key = id(action)
        if key in connections or key in _CONNECTED_USAGE_ACTIONS:
            continue
        command_id = _action_command_id(action)
        if not _should_log_command(command_id):
            continue
        try:
            callback = lambda _checked=False, a=action: _on_usage_action(a)
            action.triggered.connect(callback)
            connections[key] = (action, callback)
            _CONNECTED_USAGE_ACTIONS.add(key)
            _USAGE_ACTION_CALLBACKS[key] = callback
            connected += 1
        except Exception:
            continue
    return connected


def _ensure_native_freecad_commands() -> set:
    """Load native Draft/Arch/BIM command providers and return available ids.

    This follows the ElectricCR integration pattern: reuse native commands, never
    duplicate their implementation, and expose only commands registered by the
    current FreeCAD installation.
    """
    for module_name in ("Draft", "DraftGui", "Arch", "ArchGui", "BIM"):
        try:
            importlib.import_module(module_name)
        except Exception:
            continue

    # BIM_Sketch lives in the BIM command package on modern FreeCAD builds.
    # Importing it is harmless when already registered and improves availability
    # when the user enters FA before ever activating the BIM workbench.
    for module_name in ("bimcommands.BimSketch",):
        try:
            importlib.import_module(module_name)
        except Exception:
            pass
    try:
        return set(FreeCADGui.listCommands())
    except Exception:
        return set()


def _available_commands(available: set, candidates) -> list:
    """Return candidate command ids that exist, preserving order and uniqueness."""
    result = []
    seen = set()
    for command_id in candidates:
        command_id = str(command_id or "")
        if not command_id or command_id in seen or command_id not in available:
            continue
        seen.add(command_id)
        result.append(command_id)
    return result


def _preferred_sketch_command(available: set) -> list:
    """Prefer BIM_Sketch; fall back to the standard Sketcher command."""
    for command_id in ("BIM_Sketch", "Sketcher_NewSketch"):
        if command_id in available:
            return [command_id]
    return []


def _toolbar_title(key):
    """Return one workflow toolbar title in the active FreeCAD language."""
    titles = {
        "project": i18n.bi("FA Proyecto BIM", "FA BIM Project"),
        "cad": i18n.bi("FA DWG/DXF y preparacion 2D", "FA DWG/DXF & 2D Prep"),
        "draw": i18n.bi("FA Dibujo 2D", "FA 2D Drawing"),
        "snaps": "FA Snaps",
        "structure": i18n.bi("FA Estructura BIM", "FA BIM Structure"),
        "openings": i18n.bi("FA Aberturas BIM", "FA BIM Openings"),
        "rooms": i18n.bi("FA Recintos (Experimental)", "FA Rooms (Experimental)"),
        "roof": i18n.bi("FA Techos y cielorrasos", "FA Roofs & Ceilings"),
        "aux": i18n.bi("FA Auxiliares BIM", "FA BIM Utilities"),
    }
    return titles[str(key)]


def _common_room_label_overrides():
    """Visible labels for CRBIMCore room commands while FA is active."""
    return {
        "CRBIM_SelectRoom": i18n.bi("Seleccionar recinto", "Select room"),
        "CRBIM_RoomInfo": i18n.bi("Informacion del recinto", "Room information"),
        "CRBIM_NameRoom": i18n.bi("Nombrar recinto", "Name room"),
        "CRBIM_RoomGuide": i18n.bi("Guia de recintos", "Room guide"),
    }


def _native_toolbar_specs():
    """Return the compact native FreeCAD toolbars exposed by FA."""
    available_native = _ensure_native_freecad_commands()
    specs = []
    draw_2d = _preferred_sketch_command(available_native) + _available_commands(
        available_native,
        [
            "Draft_Line", "Draft_Wire", "Draft_Rectangle", "Draft_Circle",
            "Draft_Polygon", "Draft_Move", "Draft_Rotate", "Draft_Trimex",
            "Draft_Upgrade", "Draft_Downgrade", "Draft_Draft2Sketch",
        ],
    )
    if draw_2d:
        specs.append((_toolbar_title("draw"), draw_2d))
    snap_commands = _available_commands(
        available_native,
        [
            "Draft_Snap_Endpoint", "Draft_Snap_Midpoint", "Draft_Snap_Center",
            "Draft_Snap_Intersection", "Draft_Snap_Perpendicular", "Draft_Snap_Ortho",
        ],
    )
    if snap_commands:
        specs.append((_toolbar_title("snaps"), snap_commands))
    bim_aux = _available_commands(
        available_native,
        ["Arch_Space", "Arch_SectionPlane", "BIM_Create2DViews", "Arch_Stairs", "Draft_SelectPlane"],
    )
    if bim_aux:
        specs.append((_toolbar_title("aux"), bim_aux))
    return specs


def _ensure_native_toolbars(workbench) -> int:
    """Create missing native FA toolbars and make existing ones visible."""
    specs = _native_toolbar_specs()
    if not specs:
        return 0
    expected_titles = {name for name, _commands in specs}
    existing_titles = set()
    main_window = None
    toolbar_class = None
    try:
        main_window = FreeCADGui.getMainWindow()
    except Exception:
        pass
    for package in ("PySide6", "PySide2", "PySide"):
        if toolbar_class is not None:
            break
        try:
            module = __import__(package, fromlist=["QtWidgets", "QtGui"])
            qtwidgets = getattr(module, "QtWidgets", None)
            if qtwidgets is not None:
                toolbar_class = getattr(qtwidgets, "QToolBar", None)
            if toolbar_class is None:
                qtgui = getattr(module, "QtGui", None)
                if qtgui is not None:
                    toolbar_class = getattr(qtgui, "QToolBar", None)
        except Exception:
            continue
    if main_window is not None and toolbar_class is not None:
        try:
            for toolbar in main_window.findChildren(toolbar_class):
                title = str(toolbar.windowTitle() or "")
                if title:
                    existing_titles.add(title)
                if title in expected_titles:
                    toolbar.setVisible(True)
        except Exception:
            pass
    created = 0
    for toolbar_name, commands in specs:
        if toolbar_name in existing_titles:
            continue
        try:
            workbench.appendToolbar(toolbar_name, commands)
            created += 1
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                LOG_PREFIX + "No se pudo crear barra nativa %s: %s\n" % (toolbar_name, exc)
            )
    return created


_VERSION_PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/FacilArquitecturaWB"
_VERSION_PARAM_KEY = "LastNotifiedVersion"
_BUILD_PARAM_KEY = "LastNotifiedBuild"


def _previous_document_version():
    """Find a prior FA version in open documents for first notification migration."""
    try:
        documents = dict(getattr(FreeCAD, "listDocuments", lambda: {})() or {})
    except Exception:
        documents = {}
    for doc in documents.values():
        try:
            root = doc.getObject("FA_Project")
        except Exception:
            root = None
        previous = str(getattr(root, "FA_ProjectVersion", "") or "") if root else ""
        if previous and previous != VERSION:
            return previous
    return ""


def _notify_version_change():
    """Show one dialog per loaded VERSION + BUILD_ID identity."""
    try:
        params = FreeCAD.ParamGet(_VERSION_PARAM_PATH)
        previous_version = str(params.GetString(_VERSION_PARAM_KEY, "") or "")
        previous_build = str(params.GetString(_BUILD_PARAM_KEY, "") or "")
    except Exception as exc:
        FreeCAD.Console.PrintWarning(LOG_PREFIX + "No se pudo leer version notificada: %s\n" % exc)
        return

    if not previous_version:
        previous_version = _previous_document_version()
        if not previous_version and not previous_build:
            params.SetString(_VERSION_PARAM_KEY, VERSION)
            params.SetString(_BUILD_PARAM_KEY, BUILD_ID)
            return

    if previous_version == VERSION and previous_build == BUILD_ID:
        return

    # Persist first so repeated activations/hot restarts at the same identity stay silent.
    params.SetString(_VERSION_PARAM_KEY, VERSION)
    params.SetString(_BUILD_PARAM_KEY, BUILD_ID)
    display_previous_version = previous_version or "no registrada"
    display_previous_build = previous_build or "no registrado"
    FreeCAD.Console.PrintMessage(
        LOG_PREFIX + "Cambio de instalacion detectado: v%s build %s -> v%s build %s\n"
        % (display_previous_version, display_previous_build, VERSION, BUILD_ID)
    )
    if not getattr(FreeCAD, "GuiUp", False):
        return
    try:
        from PySide import QtWidgets

        QtWidgets.QMessageBox.information(
            None,
            "Facil Arquitectura",
            i18n.bi(
                "Workbench recargado correctamente.\n\nVersion anterior: %s\nBuild anterior: %s\n\nVersion actual: %s\nBuild actual: %s" % (display_previous_version, display_previous_build, VERSION, BUILD_ID),
                "Workbench reloaded successfully.\n\nPrevious version: %s\nPrevious build: %s\n\nCurrent version: %s\nCurrent build: %s" % (display_previous_version, display_previous_build, VERSION, BUILD_ID),
            ),
        )
    except Exception as exc:
        FreeCAD.Console.PrintWarning(
            LOG_PREFIX + "No se pudo mostrar aviso de actualizacion: %s\n" % exc
        )


class FacilArquitecturaWorkbench(FreeCADGui.Workbench):
    """Workbench definition for Facil Arquitectura."""

    MenuText = WORKBENCH_NAME
    ToolTip = i18n.bi("Organizar planos y crear base arquitectonica BIM editable", "Organize drawings and create an editable architectural BIM base") + " | v%s build %s" % (VERSION, BUILD_ID)
    Icon = os.path.abspath(os.path.join(os.path.dirname(__file__), "resources", "icons", "facilarq.svg")).replace(
        os.sep, "/"
    )

    def Initialize(self):  # noqa: N802
        global REGISTERED_COMMANDS, _COMMAND_GROUP_BY_ID
        i18n.install_translation_path()
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "VERSION CARGADA: v%s | build %s\n" % (VERSION, BUILD_ID)
        )
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Inicializando workbench Facil Arquitectura\n")
        registered = {
            "import_reference": cmd_import_cad_reference.register().CommandName,
            "bim_structure": cmd_create_bim_structure.register().CommandName,
            "rebuild": cmd_rebuild_bim_model.register().CommandName,
            "project": cmd_create_project.register().CommandName,
            "master_sketches": cmd_create_master_sketches.register().CommandName,
            "centerlines": cmd_centerlines_from_selection.register().CommandName,
            "window_centerlines": cmd_window_centerlines_from_selection.register().CommandName,
            "door_centerlines": cmd_door_centerlines_from_selection.register().CommandName,
            "doors_from_sketch": cmd_create_doors_bim.register().CommandName,
            "door_table": cmd_door_table.register().CommandName,
            "change_door_type": cmd_change_door_type.register().CommandName,
            "windows_from_sketch": cmd_create_windows_bim.register().CommandName,
            "window_table": cmd_window_table.register().CommandName,
            "openings_from_sketch": cmd_create_openings_bim.register().CommandName,
            "double_door": cmd_insert_double_door_bim.register().CommandName,
            "close_wall_sketch": cmd_create_closed_rooms.register().CommandName,
            "detect_rooms": cmd_detect_rooms_2d.register().CommandName,
            "bim_spaces": cmd_create_bim_spaces.register().CommandName,
            "room_labels": cmd_collect_room_labels.register().CommandName,
            "sample": cmd_create_sample_geometry.register().CommandName,
            "axes_columns": cmd_create_axes_columns_bim.register().CommandName,
            "building_grid": cmd_create_building_grid.register().CommandName,
            "walls": cmd_create_walls_bim.register().CommandName,
            "site_floor": cmd_create_site_floor_bim.register().CommandName,
            "ceiling": cmd_create_modular_ceiling.register().CommandName,
            "platform_create": cmd_create_service_platform_front.register().CommandName,
            "platform_update": cmd_update_service_platform_front.register().CommandName,
            "cashier_window": cmd_add_cashier_service_window.register().CommandName,
            "roof_axis_prototype": cmd_roof_axis_prototype.register().CommandName,
            "edit_truss_axes": cmd_edit_truss_axes.register().CommandName,
            "demo_building": cmd_demo_building.register().CommandName,
            "json_inspector": cmd_json_inspector.register().CommandName,
            "help": cmd_help.register().CommandName,
            "first_steps": cmd_first_steps.register().CommandName,
        }
        common_room_commands = []
        try:
            common_rooms = _common_rooms_module()
            common_room_commands = common_rooms.ensure_common_room_commands_registered()
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                LOG_PREFIX + "No se pudieron registrar comandos comunes de recintos: %s\n" % exc
            )
        native_toolbar_specs = _native_toolbar_specs()

        native_toolbar_map = dict(native_toolbar_specs)
        toolbar_specs = (
            (
                _toolbar_title("project"),
                [registered["demo_building"], registered["json_inspector"], registered["help"]],
            ),
            (
                _toolbar_title("cad"),
                [
                    registered["import_reference"],
                    registered["close_wall_sketch"],
                    registered["room_labels"],
                ],
            ),
            (_toolbar_title("draw"), native_toolbar_map.get(_toolbar_title("draw"), [])),
            (_toolbar_title("snaps"), native_toolbar_map.get(_toolbar_title("snaps"), [])),
            (
                _toolbar_title("structure"),
                [
                    registered["building_grid"],
                    registered["centerlines"],
                    registered["walls"],
                    registered["axes_columns"],
                    registered["site_floor"],
                ],
            ),
            (
                _toolbar_title("openings"),
                [
                    registered["door_centerlines"],
                    registered["doors_from_sketch"],
                    registered["change_door_type"],
                    registered["door_table"],
                    registered["double_door"],
                    registered["window_centerlines"],
                    registered["windows_from_sketch"],
                    registered["window_table"],
                    registered["openings_from_sketch"],
                ],
            ),
            (
                _toolbar_title("rooms"),
                (
                    common_room_commands[:3]
                    + (["Separator"] if common_room_commands else [])
                    + [registered["detect_rooms"], registered["bim_spaces"]]
                    + (["Separator", common_room_commands[3]] if len(common_room_commands) >= 4 else [])
                ),
            ),
            (
                _toolbar_title("roof"),
                [registered["roof_axis_prototype"], registered["edit_truss_axes"], registered["ceiling"]],
            ),
            (
                _toolbar_title("aux"),
                native_toolbar_map.get(_toolbar_title("aux"), []),
            ),
        )
        all_toolbar_specs = tuple((name, items) for name, items in toolbar_specs if items)
        _COMMAND_GROUP_BY_ID = {}
        for toolbar_name, command_names in all_toolbar_specs:
            for command_id in command_names:
                if command_id == "Separator":
                    continue
                _COMMAND_GROUP_BY_ID.setdefault(command_id, toolbar_name)
            self.appendToolbar(toolbar_name, command_names)

        menu_commands = []
        for _toolbar_name, command_names in all_toolbar_specs:
            if menu_commands:
                menu_commands.append("Separator")
            menu_commands.extend(command_names)
        menu_commands.extend(["Separator", registered["first_steps"]])
        self.appendMenu("Facil Arquitectura", menu_commands)

        advanced_commands = [
            registered["rebuild"],
            registered["bim_structure"],
            registered["project"],
            registered["master_sketches"],
            registered["sample"],
        ]
        special_commands = [
            registered["platform_create"],
            registered["platform_update"],
            registered["cashier_window"],
        ]
        self.appendMenu(["Facil Arquitectura", i18n.bi("Avanzado / compatibilidad", "Advanced / compatibility")], advanced_commands)
        self.appendMenu(["Facil Arquitectura", i18n.bi("Especiales", "Special tools")], special_commands)
        _COMMAND_GROUP_BY_ID.setdefault(registered["first_steps"], "FA Menu")
        for command_id in advanced_commands:
            _COMMAND_GROUP_BY_ID.setdefault(command_id, "FA Avanzado")
        for command_id in special_commands:
            _COMMAND_GROUP_BY_ID.setdefault(command_id, "FA Especiales")
        REGISTERED_COMMANDS = list(registered.values()) + list(common_room_commands)
        connected = _connect_usage_logger()
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Historial de uso listo: %d acciones observadas\n" % connected
        )
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Barras organizadas: " + ", ".join(name for name, _items in all_toolbar_specs) + "\n"
        )
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Comandos registrados: " + ", ".join(REGISTERED_COMMANDS) + "\n"
        )

    def Activated(self):  # noqa: N802
        global _USAGE_LOG_ENABLED
        _USAGE_LOG_ENABLED = True
        created_native = _ensure_native_toolbars(self)
        connected = _connect_usage_logger()
        if created_native:
            FreeCAD.Console.PrintMessage(
                LOG_PREFIX + "Barras nativas recuperadas al activar: %d\n" % created_native
            )
        try:
            doc = FreeCAD.ActiveDocument
        except Exception:
            doc = None
        if doc is not None:
            try:
                from .core.space_utils import migrate_game_export_exclusions

                migration = migrate_game_export_exclusions(doc, dry_run=False)
                if migration.get("changed", 0):
                    FreeCAD.Console.PrintMessage(
                        LOG_PREFIX
                        + "Migracion GameExportExclude: %d objetos FA actualizados\n"
                        % migration["changed"]
                    )
            except Exception as exc:
                FreeCAD.Console.PrintWarning(
                    LOG_PREFIX + "No se pudo migrar exclusiones GameExport: %s\n" % exc
                )
        FreeCAD.Console.PrintMessage(
            LOG_PREFIX + "Workbench activado | v%s build %s\n" % (VERSION, BUILD_ID)
        )
        if connected:
            FreeCAD.Console.PrintMessage(
                LOG_PREFIX + "Historial de uso: %d acciones nuevas conectadas\n" % connected
            )
        _notify_version_change()
        first_steps.schedule_startup_tips()
        try:
            common_rooms = _common_rooms_module()
            common_rooms.schedule_room_toolbar_layout(
                [
                    "CRBIM_SelectRoom", "CRBIM_RoomInfo", "CRBIM_NameRoom",
                    "Separator", "FA_DetectRooms2D", "FA_CreateBIMSpaces",
                    "Separator", "CRBIM_RoomGuide",
                ],
                title=_toolbar_title("rooms"),
                label_overrides=_common_room_label_overrides(),
            )
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                LOG_PREFIX + "No se pudo ordenar Espacios y Recintos: %s\n" % exc
            )

    def Deactivated(self):  # noqa: N802
        global _USAGE_LOG_ENABLED
        _USAGE_LOG_ENABLED = False
        FreeCAD.Console.PrintMessage(LOG_PREFIX + "Workbench desactivado\n")


def _ensure_clean_registration():
    """Try to remove a previous registration during development reloads."""
    try:
        workbenches = dict(getattr(FreeCADGui, "listWorkbenches", lambda: {})() or {})
    except Exception:
        workbenches = {}
    if WORKBENCH_ID in workbenches and hasattr(FreeCADGui, "removeWorkbench"):
        try:
            FreeCADGui.removeWorkbench(WORKBENCH_ID)
        except Exception:
            pass


_ensure_clean_registration()
FreeCADGui.addWorkbench(FacilArquitecturaWorkbench())
