"""GUI registration for MEPWorkbenchCR."""

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

import importlib
import os
import sys

# Bootstrap import paths early so serialized proxies can resolve MEPWorkbenchCR.*
_THIS_DIR = os.path.abspath(os.path.dirname(__file__))
_PARENT_DIR = os.path.abspath(os.path.dirname(_THIS_DIR))
for _path in (_THIS_DIR, _PARENT_DIR):
    if _path and _path not in sys.path:
        sys.path.insert(0, _path)

import FreeCAD
import FreeCADGui

try:
    from PySide2 import QtGui
except Exception:  # pragma: no cover
    try:
        from PySide import QtGui
    except Exception:  # pragma: no cover
        QtGui = None

try:
    from .MEP.i18n import tr
    # Preferred path when loaded as package: MEPWorkbenchCR.InitGui
    from .MEP.hvac import hvac_condensing
    from .MEP.hvac import hvac_equipment
    from .MEP.hvac import hvac_label
    from .MEP.hvac import hvac_ports
    from .MEP.hvac import hvac_project
    from .MEP.hvac import hvac_route
    from .MEP.hvac import hvac_space
    from .MEP.hvac import hvac_validate
except Exception:
    from MEP.i18n import tr
    # Fallback path for direct module loading from workbench folder.
    from MEP.hvac import hvac_condensing
    from MEP.hvac import hvac_equipment
    from MEP.hvac import hvac_label
    from MEP.hvac import hvac_ports
    from MEP.hvac import hvac_project
    from MEP.hvac import hvac_route
    from MEP.hvac import hvac_space
    from MEP.hvac import hvac_validate

LOG_PREFIX = "[MEP-HVAC] "
WORKBENCH_ID = "MEPWorkbenchCR"
ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "resources", "icons"))
RELOAD_DEBUG_REV = "2026-03-30-r2"
COMMAND_NAMES_CLEANUP = [
    "MEP_HVAC_CreateProject",
    "MEP_HVAC_CreateSpace",
    "MEP_HVAC_Calculate",
    "MEP_HVAC_AlignObjects",
    "MEP_HVAC_InsertEvaporator",
    "MEP_HVAC_PlaceCeilingUnits",
    "MEP_HVAC_AssignEvaporatorSpace",
    "MEP_HVAC_AssignSpace",
    "MEP_HVAC_ToggleLabels",
    "MEP_HVAC_SetVisualModeAll",
    "MEP_HVAC_InsertCondenser",
    "MEP_HVAC_AssignCondenserUnits",
    "MEP_HVAC_CreateRoute",
    "MEP_HVAC_Validate",
    "MEP_HVAC_RefreshModels",
    "MEP_HVAC_Export2D",
    "MEP_HVAC_ReloadWorkbench",
]


def _icon(icon_name, fallback_name="hvac.svg"):
    """Return icon path with a safe fallback to avoid missing icon warnings."""
    icon_path = os.path.abspath(os.path.join(ICONS_DIR, icon_name))
    if os.path.exists(icon_path):
        return icon_path.replace(os.sep, "/")

    fallback_path = os.path.abspath(os.path.join(ICONS_DIR, fallback_name))
    if os.path.exists(fallback_path):
        print(
            LOG_PREFIX
            + "Icono no encontrado ({0}), usando fallback ({1})".format(icon_name, fallback_name)
        )
        return fallback_path.replace(os.sep, "/")

    return icon_path.replace(os.sep, "/")


ICON_PATH = _icon("hvac.svg")
ICON_PROJECT = _icon("hvac_project.svg")
ICON_SPACE = _icon("hvac_space.svg")
ICON_CALCULATE = _icon("hvac_calculate.svg")
ICON_VALIDATE = _icon("hvac_validate.svg", "hvac_calculate.svg")
ICON_EVAPORATOR = _icon("hvac_evaporator.svg")
ICON_CONDENSER = _icon("hvac_condenser.svg")
ICON_ASSIGN = _icon("hvac_assign.svg", "hvac_condenser.svg")
ICON_ROUTE = _icon("hvac_route.svg")
ICON_LABELS = _icon("hvac_labels.svg")
ICON_RELOAD = _icon("hvac_reload.svg")
ICON_ALIGN = _icon("hvac_align_v1.svg", "hvac_align.svg")
MODULE_SOURCE = os.path.abspath(__file__).replace(os.sep, "/")
ALIGN_MACRO_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "Objetos", "Alinear.FCMacro")
)
EXPORT_2D_MACRO_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "Configuracion del proyecto",
        "Exportar_DXF_DWG_Plano_Trabajo.FCMacro",
    )
)
DRAFT_COMMAND_CANDIDATES = [
    "Draft_SelectPlane",
    "Draft_Line",
    "Draft_Wire",
    "Draft_Rectangle",
    "Draft_Polygon",
    "Draft_Circle",
    "Draft_ArcTools",
    "Draft_Move",
    "Draft_Rotate",
    "Draft_Offset",
    "Draft_Trimex",
]
EQUIP_OBSERVER_ATTR = "_MEP_HVAC_EQUIP_OBSERVER"


def _log(message):
    text = LOG_PREFIX + str(message)
    print(text)


def _file_signature(path):
    try:
        stat = os.stat(path)
        return "mtime={0};size={1}".format(int(stat.st_mtime), int(stat.st_size))
    except Exception:
        return "mtime=?;size=?"


def _resolve_git_dir(start_path):
    current = os.path.abspath(os.path.dirname(start_path))
    while True:
        dot_git = os.path.join(current, ".git")
        if os.path.isdir(dot_git):
            return dot_git
        if os.path.isfile(dot_git):
            try:
                with open(dot_git, "r", encoding="utf-8") as handle:
                    text = handle.read().strip()
                if text.lower().startswith("gitdir:"):
                    raw = text.split(":", 1)[1].strip()
                    git_dir = raw if os.path.isabs(raw) else os.path.abspath(os.path.join(current, raw))
                    if os.path.isdir(git_dir):
                        return git_dir
            except Exception:
                pass
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return ""


def _read_git_head_short(start_path):
    git_dir = _resolve_git_dir(start_path)
    if not git_dir:
        return "n/a"
    head_path = os.path.join(git_dir, "HEAD")
    try:
        with open(head_path, "r", encoding="utf-8") as handle:
            head_text = handle.read().strip()
    except Exception:
        return "n/a"
    sha = ""
    if head_text.startswith("ref:"):
        ref_rel = head_text.split(":", 1)[1].strip()
        ref_path = os.path.join(git_dir, ref_rel.replace("/", os.sep))
        try:
            with open(ref_path, "r", encoding="utf-8") as handle:
                sha = handle.read().strip()
        except Exception:
            sha = ""
    else:
        sha = head_text
    if not sha:
        return "n/a"
    return sha[:12]


def _log_reload_debug(context):
    source = os.path.abspath(__file__).replace(os.sep, "/")
    signature = _file_signature(__file__)
    git_head = _read_git_head_short(__file__)
    module_id = str(id(sys.modules.get(__name__)))
    _log(
        "ReloadDebug[{0}] rev={1} head={2} sig={3} module_id={4} source={5}".format(
            context,
            RELOAD_DEBUG_REV,
            git_head,
            signature,
            module_id,
            source,
        )
    )


def _refresh_icon_cache():
    """Refresh icon search path and clear Qt pixmap cache."""
    try:
        FreeCADGui.addIconPath(ICONS_DIR.replace(os.sep, "/"))
    except Exception:
        pass
    if QtGui is not None:
        try:
            QtGui.QPixmapCache.clear()
        except Exception:
            pass


def _ensure_draft_commands_loaded():
    """Try to load Draft command registrations without failing workbench init."""
    for module_name in ("DraftGui", "Draft"):
        try:
            importlib.import_module(module_name)
        except Exception:
            continue


def _available_draft_commands():
    _ensure_draft_commands_loaded()
    try:
        available = set(FreeCADGui.listCommands() or [])
    except Exception:
        available = set()
    return [command for command in DRAFT_COMMAND_CANDIDATES if command in available]


def _init_draft_snap_toolbar(workbench):
    """Create Draft snap toolbar using Draft's own command registry (ElectricCR-style)."""
    try:
        from draftutils import init_tools as _draft_tools
    except Exception:
        _log("Draft snap tools not available (draftutils.init_tools)")
        return []
    try:
        available = set(FreeCADGui.listCommands() or [])
    except Exception:
        available = set()
    try:
        snap_commands = [c for c in _draft_tools.get_draft_snap_commands() if c in available]
    except Exception:
        snap_commands = []
    if not snap_commands:
        _log("Draft snap commands not available in this session")
        return []
    try:
        _draft_tools.init_toolbar(workbench, "Draft snap", snap_commands)
    except Exception as exc:
        _log("Draft snap toolbar init failed: {0}".format(exc))
        return []
    _log("Draft snap toolbar integrated: {0}".format(", ".join(snap_commands)))
    return snap_commands


def _activate_draft_snap_runtime():
    """Enable Draft runtime snap UI (toolbar + snapper overlay + statusbar)."""
    try:
        import DraftTools  # noqa: F401
    except Exception:
        pass
    try:
        if hasattr(FreeCADGui, "draftToolBar"):
            FreeCADGui.draftToolBar.Activated()
    except Exception:
        pass
    try:
        if hasattr(FreeCADGui, "Snapper"):
            FreeCADGui.Snapper.show()
    except Exception:
        pass
    try:
        from draftutils import init_draft_statusbar

        init_draft_statusbar.show_draft_statusbar()
    except Exception:
        pass


def _deactivate_draft_snap_runtime():
    """Hide Draft runtime snap UI when leaving workbench."""
    try:
        if hasattr(FreeCADGui, "draftToolBar"):
            FreeCADGui.draftToolBar.Deactivated()
    except Exception:
        pass
    try:
        if hasattr(FreeCADGui, "Snapper"):
            FreeCADGui.Snapper.hide()
    except Exception:
        pass
    try:
        from draftutils import init_draft_statusbar

        init_draft_statusbar.hide_draft_statusbar()
    except Exception:
        pass


def _ensure_package_parent_in_path():
    package_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.dirname(package_dir))
    for path in (package_dir, parent_dir):
        if path and path not in sys.path:
            sys.path.insert(0, path)


def _unregister_commands():
    removed = 0
    remover = getattr(FreeCADGui, "removeCommand", None)
    if remover is None:
        return 0
    for cmd_name in list(COMMAND_NAMES_CLEANUP):
        try:
            remover(cmd_name)
            removed += 1
        except Exception:
            continue
    return removed


def _purge_reload_modules():
    for name in list(sys.modules.keys()):
        if (
            name == "MEPWorkbenchCR"
            or name.startswith("MEPWorkbenchCR.")
            or name == "MEP"
            or name.startswith("MEP.")
        ):
            sys.modules.pop(name, None)


def _reload_workbench():
    _log_reload_debug("before_reload")
    _refresh_icon_cache()
    _ensure_package_parent_in_path()
    try:
        listed = dict(getattr(FreeCADGui, "listWorkbenches", lambda: {})() or {})
    except Exception:
        listed = {}
    if WORKBENCH_ID in listed and hasattr(FreeCADGui, "removeWorkbench"):
        try:
            FreeCADGui.activateWorkbench("StartWorkbench")
        except Exception:
            pass
        try:
            FreeCADGui.removeWorkbench(WORKBENCH_ID)
        except Exception:
            pass

    removed_commands = _unregister_commands()
    if removed_commands > 0:
        _log("Comandos HVAC desregistrados antes de recarga: {0}".format(removed_commands))

    _purge_reload_modules()
    importlib.invalidate_caches()
    module = None
    for module_name in ("MEPWorkbenchCR.InitGui", "InitGui"):
        try:
            module = importlib.import_module(module_name)
            module = importlib.reload(module)
            break
        except Exception:
            continue
    if module is None:
        _log("No se pudo importar InitGui para recarga runtime")
        return
    if hasattr(module, "_log_reload_debug"):
        module._log_reload_debug("after_reload")
    if hasattr(module, "_refresh_icon_cache"):
        try:
            module._refresh_icon_cache()
        except Exception:
            pass
    _log("Reload source: {0}".format(getattr(module, "__file__", "")))
    FreeCADGui.activateWorkbench(WORKBENCH_ID)


def _load_hvac_runtime_module(module_basename):
    existing = globals().get(str(module_basename), None)
    if existing is not None:
        try:
            return importlib.reload(existing)
        except Exception:
            try:
                return existing
            except Exception:
                pass

    candidates = (
        "MEPWorkbenchCR.MEP.hvac.{0}".format(module_basename),
        "MEP.hvac.{0}".format(module_basename),
    )
    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)
            module = importlib.reload(module)
            return module
        except Exception:
            continue
    return None


def _load_hvac_runtime_package():
    candidates = (
        "MEPWorkbenchCR.MEP.hvac",
        "MEP.hvac",
    )
    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)
            module = importlib.reload(module)
            for submodule_name in (
                "hvac_space",
                "hvac_label",
                "hvac_equipment",
                "hvac_ports",
                "hvac_project",
                "hvac_condensing",
                "hvac_route",
                "hvac_sheet",
                "hvac_validate",
            ):
                submodule = getattr(module, submodule_name, None)
                if submodule is None:
                    continue
                try:
                    importlib.reload(submodule)
                except Exception:
                    continue
            return module
        except Exception:
            continue
    return None


def _load_hvac_equipment_runtime():
    """Force runtime reload of hvac_equipment to avoid stale command cache."""
    return _load_hvac_runtime_module("hvac_equipment")


def _load_hvac_project_runtime():
    return _load_hvac_runtime_module("hvac_project")


def _load_hvac_condensing_runtime():
    return _load_hvac_runtime_module("hvac_condensing")


def _load_hvac_route_runtime():
    return _load_hvac_runtime_module("hvac_route")


def _load_hvac_validate_runtime():
    return _load_hvac_runtime_module("hvac_validate")


def _load_hvac_ports_runtime():
    return _load_hvac_runtime_module("hvac_ports")


def _load_hvac_space_runtime():
    """Force runtime reload of hvac_space for create/calculate commands."""
    return _load_hvac_runtime_module("hvac_space")


def _load_hvac_label_runtime():
    """Force runtime reload of hvac_label for label updates and toggles."""
    return _load_hvac_runtime_module("hvac_label")


def _run_external_macro(macro_path):
    """Execute an external FCMacro file in-process."""
    resolved = os.path.abspath(str(macro_path or ""))
    if not resolved or not os.path.exists(resolved):
        raise FileNotFoundError("Macro no encontrada: {0}".format(resolved))
    text = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            with open(resolved, "r", encoding=encoding) as handle:
                text = handle.read()
            break
        except Exception:
            continue
    if text is None:
        raise RuntimeError("No se pudo leer macro: {0}".format(resolved))
    namespace = {
        "__file__": resolved,
        "__name__": "__main__",
    }
    code = compile(text, resolved, "exec")
    exec(code, namespace, namespace)


def _update_document_after_command(
    doc,
    update_labels=False,
    sanitize_ports=True,
    sanitize_condensers=False,
    sanitize_equipments=True,
):
    """Apply common post-command updates when possible."""
    if doc is None:
        return

    runtime_project = _load_hvac_project_runtime() or hvac_project
    runtime_ports = _load_hvac_ports_runtime() or hvac_ports
    runtime_label = _load_hvac_label_runtime() or hvac_label
    runtime_space = _load_hvac_space_runtime() or hvac_space
    runtime_equipment = _load_hvac_equipment_runtime() or hvac_equipment
    runtime_condensing = None

    if bool(sanitize_equipments):
        # Clean damaged equipment first to avoid access violations during next upgrades/recompute.
        try:
            if hasattr(runtime_equipment, "sanitize_all_equipments"):
                runtime_equipment.sanitize_all_equipments(doc)
        except Exception:
            pass

    try:
        if hasattr(runtime_space, "upgrade_spaces_schema"):
            runtime_space.upgrade_spaces_schema(doc, rebind_proxy=True, recalc=False)
    except Exception:
        pass

    if bool(sanitize_condensers):
        try:
            runtime_condensing = _load_hvac_condensing_runtime() or hvac_condensing
            if hasattr(runtime_condensing, "sanitize_all_condensers"):
                runtime_condensing.sanitize_all_condensers(doc)
        except Exception:
            pass

    try:
        if hasattr(runtime_project, "ensure_hvac_root_group"):
            runtime_project.ensure_hvac_root_group(doc)
        if hasattr(runtime_project, "ensure_hvac_label_group"):
            runtime_project.ensure_hvac_label_group(doc)
    except Exception:
        pass

    try:
        if hasattr(runtime_label, "clear_roomlabel_backlinks"):
            runtime_label.clear_roomlabel_backlinks(doc)
    except Exception:
        pass

    try:
        if hasattr(runtime_label, "sync_all_labels_visibility"):
            runtime_label.sync_all_labels_visibility(doc)
    except Exception:
        pass

    if bool(update_labels):
        try:
            runtime_label.update_all_labels(doc, ensure_visible=True)
        except Exception:
            pass

    if bool(sanitize_ports):
        try:
            runtime_ports.sanitize_all_ports(doc)
        except Exception:
            pass

    try:
        if hasattr(runtime_project, "organize_hvac_objects"):
            runtime_project.organize_hvac_objects(doc)
    except Exception:
        pass

    try:
        doc.recompute()
    except Exception:
        pass
    try:
        visual_stats = _enforce_hvac_visual_modes(doc)
        _log(
            "[MEP-HVAC][Visual] Sync resumen: owners={0}, symbols={1}, infos={2}, orphans={3}, info_orphans={4}".format(
                int(visual_stats.get("owners", 0) or 0),
                int(visual_stats.get("symbols", 0) or 0),
                int(visual_stats.get("infos", 0) or 0),
                int(visual_stats.get("orphans", 0) or 0),
                int(visual_stats.get("info_orphans", 0) or 0),
            )
        )
        if int(visual_stats.get("orphans", 0) or 0) > 0:
            _log(
                "[MEP-HVAC][Visual] Simbolos 2D huerfanos ocultados: {0}".format(
                    int(visual_stats.get("orphans", 0) or 0)
                )
            )
        if int(visual_stats.get("info_orphans", 0) or 0) > 0:
            _log(
                "[MEP-HVAC][Visual] Textos Info2D sin padre visibles: {0}".format(
                    int(visual_stats.get("info_orphans", 0) or 0)
                )
            )
    except Exception:
        pass


def _is_hvac_evaporator_link(obj):
    if obj is None:
        return False
    try:
        props = list(getattr(obj, "PropertiesList", []) or [])
        if "MEPType" not in props:
            return False
        return str(getattr(obj, "MEPType", "") or "") == str(getattr(hvac_equipment, "MEP_TYPE", "HVACEvaporator"))
    except Exception:
        return False


def _is_hvac_condenser_link(obj):
    if obj is None:
        return False
    try:
        if str(getattr(obj, "TypeId", "") or "") != "App::Link":
            return False
        props = list(getattr(obj, "PropertiesList", []) or [])
        if "MEPType" not in props:
            return False
        return str(getattr(obj, "MEPType", "") or "") == str(getattr(hvac_condensing, "MEP_TYPE", "HVACCondenser"))
    except Exception:
        return False


def _is_hvac_symbol2d(obj):
    if obj is None:
        return False
    try:
        props = list(getattr(obj, "PropertiesList", []) or [])
        if "MEPType" not in props:
            return False
        mep = str(getattr(obj, "MEPType", "") or "")
        return mep in {
            str(getattr(hvac_equipment, "SYMBOL2D_MEP_TYPE", "HVACEquipment2D")),
            str(getattr(hvac_condensing, "SYMBOL2D_MEP_TYPE", "HVACCondenser2D")),
        }
    except Exception:
        return False


def _is_hvac_info2d(obj):
    if obj is None:
        return False
    try:
        props = list(getattr(obj, "PropertiesList", []) or [])
        if "MEPType" not in props:
            name = str(getattr(obj, "Name", "") or "")
            label = str(getattr(obj, "Label", "") or "")
            return (
                name.startswith("HVAC_EvapInfo2D")
                or name.startswith("HVAC_CondInfo2D")
                or label.startswith("HVAC_INFO2D_")
                or label.startswith("HVAC_INFO2D_COND_")
            )
        mep = str(getattr(obj, "MEPType", "") or "")
        if mep == str(getattr(hvac_equipment, "INFO2D_MEP_TYPE", "HVACEquipmentInfo2D")):
            return True
        if mep == str(getattr(hvac_condensing, "INFO2D_MEP_TYPE", "HVACCondenserInfo2D")):
            return True
        name = str(getattr(obj, "Name", "") or "")
        label = str(getattr(obj, "Label", "") or "")
        return (
            name.startswith("HVAC_EvapInfo2D")
            or name.startswith("HVAC_CondInfo2D")
            or label.startswith("HVAC_INFO2D_")
            or label.startswith("HVAC_INFO2D_COND_")
        )
    except Exception:
        return False


def _find_hvac_parent_for_symbol(symbol_obj):
    if symbol_obj is None:
        return None
    doc = getattr(symbol_obj, "Document", None)
    if doc is None:
        return None
    try:
        for candidate in list(getattr(doc, "Objects", []) or []):
            if candidate is None or candidate is symbol_obj:
                continue
            props = list(getattr(candidate, "PropertiesList", []) or [])
            if "Symbol2D" not in props:
                continue
            try:
                linked_symbol = getattr(candidate, "Symbol2D", None)
            except Exception:
                linked_symbol = None
            if linked_symbol is not symbol_obj:
                continue
            if _is_hvac_evaporator_link(candidate) or _is_hvac_condenser_link(candidate):
                return candidate
    except Exception:
        return None
    return None


def _find_hvac_parent_for_info(info_obj):
    if info_obj is None:
        return None
    doc = getattr(info_obj, "Document", None)
    if doc is None:
        return None
    try:
        for candidate in list(getattr(doc, "Objects", []) or []):
            if candidate is None or candidate is info_obj:
                continue
            props = list(getattr(candidate, "PropertiesList", []) or [])
            if "Info2D" not in props:
                continue
            try:
                linked_info = getattr(candidate, "Info2D", None)
            except Exception:
                linked_info = None
            if linked_info is not info_obj:
                continue
            if _is_hvac_evaporator_link(candidate) or _is_hvac_condenser_link(candidate):
                return candidate
    except Exception:
        return None
    return None


def _xy_synced_placement(source_placement, target_placement):
    try:
        z_value = float(getattr(target_placement.Base, "z", 0.0))
    except Exception:
        z_value = 0.0
    try:
        base = FreeCAD.Vector(
            float(getattr(source_placement.Base, "x", 0.0)),
            float(getattr(source_placement.Base, "y", 0.0)),
            z_value,
        )
        rotation = FreeCAD.Rotation(getattr(source_placement, "Rotation", FreeCAD.Rotation()))
        return FreeCAD.Placement(base, rotation)
    except Exception:
        return target_placement


def _visual_mode_flags(mode_value):
    mode = str(mode_value or "Ambos").strip()
    show_3d = mode in {"Ambos", "Solo3D"}
    show_2d = mode in {"Ambos", "Solo2D"}
    if mode == "Ninguno":
        show_3d = False
        show_2d = False
    return bool(show_3d), bool(show_2d)


def _set_view_visibility(obj, visible):
    if obj is None:
        return False
    try:
        view = getattr(obj, "ViewObject", None)
        if view is None:
            return False
        view.Visibility = bool(visible)
        return True
    except Exception:
        return False


def _enforce_hvac_visual_modes(doc):
    if doc is None:
        return {"owners": 0, "symbols": 0, "orphans": 0, "infos": 0, "info_orphans": 0}

    owners = 0
    symbols = 0
    orphans = 0
    infos = 0
    info_orphans = 0
    linked_symbol_names = set()
    linked_info_names = set()

    for obj in list(getattr(doc, "Objects", []) or []):
        if not (_is_hvac_evaporator_link(obj) or _is_hvac_condenser_link(obj)):
            continue
        owners += 1
        mode = str(getattr(obj, "VisualMode", "Ambos") or "Ambos")
        show_3d, show_2d = _visual_mode_flags(mode)
        _set_view_visibility(obj, show_3d)

        symbol_obj = None
        try:
            if "Symbol2D" in list(getattr(obj, "PropertiesList", []) or []):
                symbol_obj = getattr(obj, "Symbol2D", None)
        except Exception:
            symbol_obj = None

        if symbol_obj is not None:
            symbol_name = str(getattr(symbol_obj, "Name", "") or "")
            if symbol_name and doc.getObject(symbol_name) is not None:
                linked_symbol_names.add(symbol_name)
        try:
            if "VisualMode" in list(getattr(symbol_obj, "PropertiesList", []) or []):
                symbol_obj.VisualMode = mode
        except Exception:
            pass
        if _set_view_visibility(symbol_obj, show_2d):
            symbols += 1

        info_obj = None
        try:
            if "Info2D" in list(getattr(obj, "PropertiesList", []) or []):
                info_obj = getattr(obj, "Info2D", None)
        except Exception:
            info_obj = None
        if info_obj is not None:
            info_name = str(getattr(info_obj, "Name", "") or "")
            if info_name and doc.getObject(info_name) is not None:
                linked_info_names.add(info_name)
        show_info2d = bool(show_2d) and bool(getattr(obj, "ShowInfo2D", True))
        if _set_view_visibility(info_obj, show_info2d):
            infos += 1

    for symbol_obj in list(getattr(doc, "Objects", []) or []):
        if not _is_hvac_symbol2d(symbol_obj):
            continue
        symbol_name = str(getattr(symbol_obj, "Name", "") or "")
        if symbol_name in linked_symbol_names:
            continue

        parent = _find_hvac_parent_for_symbol(symbol_obj)
        if parent is not None:
            mode = str(getattr(parent, "VisualMode", "Ambos") or "Ambos")
            _, show_2d = _visual_mode_flags(mode)
            if _set_view_visibility(symbol_obj, show_2d):
                symbols += 1
            continue

        if _set_view_visibility(symbol_obj, False):
            orphans += 1

    for info_obj in list(getattr(doc, "Objects", []) or []):
        if not _is_hvac_info2d(info_obj):
            continue
        info_name = str(getattr(info_obj, "Name", "") or "")
        if info_name in linked_info_names:
            continue
        parent = _find_hvac_parent_for_info(info_obj)
        if parent is not None:
            mode = str(getattr(parent, "VisualMode", "Ambos") or "Ambos")
            _, show_2d = _visual_mode_flags(mode)
            show_info2d = bool(show_2d) and bool(getattr(parent, "ShowInfo2D", True))
            if _set_view_visibility(info_obj, show_info2d):
                infos += 1
            continue
        # Keep unlinked info labels visible to avoid silently "losing" text in user files.
        if _set_view_visibility(info_obj, True):
            info_orphans += 1

    return {
        "owners": owners,
        "symbols": symbols,
        "orphans": orphans,
        "infos": infos,
        "info_orphans": info_orphans,
    }


class _HVACEquipmentObserver:
    WATCHED_EVAP_PROPS = {
        "Height",
        "BaseLevel",
        "Model",
        "Type",
        "CapacityBTU",
        "SystemType",
        "Symbol2DSize",
        "ShowInfo2D",
        "Info2DSize",
        "VisualMode",
        "UsePorts",
        "Placement",
    }
    WATCHED_COND_PROPS = {
        "Model",
        "Discharge",
        "CapacityBTU",
        "Symbol2DSize",
        "ShowInfo2D",
        "Info2DSize",
        "VisualMode",
        "Placement",
    }
    WATCHED_SYMBOL_PROPS = {
        "VisualMode",
    }

    def __init__(self):
        self._busy = False

    def slotChangedObject(self, obj, prop):  # noqa: N802 (FreeCAD callback)
        if self._busy or obj is None:
            return
        prop_name = str(prop or "")

        self._busy = True
        try:
            handled = False
            if _is_hvac_symbol2d(obj) and prop_name in self.WATCHED_SYMBOL_PROPS:
                mep = str(getattr(obj, "MEPType", "") or "")
                parent = _find_hvac_parent_for_symbol(obj)
                if mep == str(getattr(hvac_equipment, "SYMBOL2D_MEP_TYPE", "HVACEquipment2D")):
                    if parent is not None:
                        if prop_name == "VisualMode" and hasattr(parent, "VisualMode"):
                            target_mode = str(getattr(obj, "VisualMode", "") or "")
                            try:
                                parent.VisualMode = target_mode
                            except Exception:
                                pass
                        runtime_equipment = hvac_equipment
                        runtime_equipment.refresh_equipment(parent)
                        handled = True
                elif mep == str(getattr(hvac_condensing, "SYMBOL2D_MEP_TYPE", "HVACCondenser2D")):
                    if parent is not None:
                        if prop_name == "VisualMode" and hasattr(parent, "VisualMode"):
                            target_mode = str(getattr(obj, "VisualMode", "") or "")
                            try:
                                parent.VisualMode = target_mode
                            except Exception:
                                pass
                        runtime_condensing = hvac_condensing
                        if hasattr(runtime_condensing, "refresh_condenser"):
                            runtime_condensing.refresh_condenser(parent)
                        handled = True
            elif _is_hvac_evaporator_link(obj) and prop_name in self.WATCHED_EVAP_PROPS:
                runtime_equipment = hvac_equipment
                runtime_equipment.refresh_equipment(obj)
                handled = True
            elif _is_hvac_condenser_link(obj) and prop_name in self.WATCHED_COND_PROPS:
                runtime_condensing = hvac_condensing
                if hasattr(runtime_condensing, "refresh_condenser"):
                    runtime_condensing.refresh_condenser(obj)
                handled = True

            if handled:
                doc = getattr(obj, "Document", None)
                if doc is not None:
                    try:
                        doc.recompute()
                    except Exception:
                        pass
        except Exception as exc:
            _log("Observer HVAC omitido ({0}): {1}".format(prop_name, exc))
        finally:
            self._busy = False


def _remove_hvac_equipment_observer():
    existing = getattr(FreeCAD, EQUIP_OBSERVER_ATTR, None)
    if existing is None:
        return
    try:
        FreeCAD.removeDocumentObserver(existing)
    except Exception:
        pass
    try:
        delattr(FreeCAD, EQUIP_OBSERVER_ATTR)
    except Exception:
        pass


def _ensure_hvac_equipment_observer():
    _remove_hvac_equipment_observer()
    observer = _HVACEquipmentObserver()
    try:
        FreeCAD.addDocumentObserver(observer)
        setattr(FreeCAD, EQUIP_OBSERVER_ATTR, observer)
    except Exception as exc:
        _log("No se pudo registrar observer evaporadora: {0}".format(exc))


class _BaseCommand:
    """Shared implementation for command activation checks."""

    CommandName = ""
    MenuText = ""
    ToolTip = ""

    def IsActive(self):  # noqa: N802 (FreeCAD API)
        return FreeCAD.ActiveDocument is not None

    def GetResources(self):  # noqa: N802 (FreeCAD API)
        return {
            "MenuText": self.MenuText,
            "ToolTip": self.ToolTip,
            "Pixmap": getattr(self, "IconPath", ICON_PATH),
        }


class CmdCreateHVACProject(_BaseCommand):
    CommandName = "MEP_HVAC_CreateProject"
    MenuText = tr("cmd.create_project.menu")
    ToolTip = tr("cmd.create_project.tooltip")
    IconPath = ICON_PROJECT

    def Activated(self):  # noqa: N802
        _log(tr("cmd.create_project.run"))
        try:
            runtime_project = _load_hvac_project_runtime() or hvac_project
            runtime_project.get_or_create_project(FreeCAD.ActiveDocument)
            _update_document_after_command(FreeCAD.ActiveDocument, update_labels=False, sanitize_ports=False)
        except Exception as exc:
            _log(tr("cmd.create_project.error", error=exc))


class CmdCreateHVACSpace(_BaseCommand):
    CommandName = "MEP_HVAC_CreateSpace"
    MenuText = tr("cmd.create_space.menu")
    ToolTip = tr("cmd.create_space.tooltip")
    IconPath = ICON_SPACE

    def Activated(self):  # noqa: N802
        _log(tr("cmd.create_space.run"))
        try:
            runtime_space = _load_hvac_space_runtime() or hvac_space
            runtime_label = _load_hvac_label_runtime() or hvac_label
            _log(
                "CreateSpace runtime: space_rev={0} space_src={1} label_rev={2} label_src={3} label_posdebug={4}".format(
                    getattr(runtime_space, "SPACE_DEBUG_REV", "n/a"),
                    getattr(runtime_space, "__file__", "n/a"),
                    getattr(runtime_label, "LABEL_DEBUG_REV", "n/a"),
                    getattr(runtime_label, "__file__", "n/a"),
                    getattr(runtime_label, "DEBUG_LABEL_POSITION", "n/a"),
                )
            )
            spaces = runtime_space.create_spaces_from_selection(FreeCAD.ActiveDocument)
            if spaces:
                runtime_label.update_all_labels(FreeCAD.ActiveDocument, ensure_visible=True)
            _update_document_after_command(
                FreeCAD.ActiveDocument,
                update_labels=False,
                sanitize_ports=False,
                sanitize_equipments=False,
            )
        except Exception as exc:
            _log(tr("cmd.create_space.error", error=exc))


class CmdCalculateHVAC(_BaseCommand):
    CommandName = "MEP_HVAC_Calculate"
    MenuText = tr("cmd.calculate.menu")
    ToolTip = tr("cmd.calculate.tooltip")
    IconPath = ICON_CALCULATE

    def Activated(self):  # noqa: N802
        _log(tr("cmd.calculate.run"))
        try:
            runtime_space = _load_hvac_space_runtime() or hvac_space
            runtime_hvac = _load_hvac_runtime_package()
            _log(
                "Calculate runtime: space_rev={0} space_src={1} hvac_pkg={2}".format(
                    getattr(runtime_space, "SPACE_DEBUG_REV", "n/a"),
                    getattr(runtime_space, "__file__", "n/a"),
                    getattr(runtime_hvac, "__file__", "n/a") if runtime_hvac is not None else "n/a",
                )
            )
            if hasattr(runtime_space, "cleanup_non_area_spaces"):
                runtime_space.cleanup_non_area_spaces(FreeCAD.ActiveDocument)
            if hasattr(runtime_space, "cleanup_duplicate_spaces"):
                runtime_space.cleanup_duplicate_spaces(FreeCAD.ActiveDocument)
            if hasattr(runtime_space, "cleanup_nested_spaces"):
                runtime_space.cleanup_nested_spaces(FreeCAD.ActiveDocument)
            if hasattr(runtime_space, "upgrade_spaces_schema"):
                runtime_space.upgrade_spaces_schema(FreeCAD.ActiveDocument, rebind_proxy=True, recalc=False)
            if runtime_space.has_area_selection():
                spaces = runtime_space.prepare_spaces_from_selection_quick(FreeCAD.ActiveDocument)
                if spaces:
                    _log(tr("cmd.calculate.quick_spaces", count=len(spaces)))
            if runtime_hvac is not None and hasattr(runtime_hvac, "recalculate_document"):
                runtime_hvac.recalculate_document(FreeCAD.ActiveDocument)
                _update_document_after_command(FreeCAD.ActiveDocument, update_labels=False, sanitize_ports=True)
            else:
                _log("No se pudo cargar modulo HVAC runtime para recalculo")
                _update_document_after_command(FreeCAD.ActiveDocument, update_labels=True, sanitize_ports=True)
        except Exception as exc:
            _log(tr("cmd.calculate.error", error=exc))


class CmdValidateHVAC(_BaseCommand):
    CommandName = "MEP_HVAC_Validate"
    MenuText = tr("cmd.validate.menu")
    ToolTip = tr("cmd.validate.tooltip")
    IconPath = ICON_VALIDATE

    def Activated(self):  # noqa: N802
        _log(tr("cmd.validate.run"))
        try:
            runtime_validate = _load_hvac_validate_runtime() or hvac_validate
            report = runtime_validate.validate_document(FreeCAD.ActiveDocument, recalc_first=True)
            _log(
                tr(
                    "cmd.validate.summary",
                    errors=report.get("errors", 0),
                    warnings=report.get("warnings", 0),
                    infos=report.get("infos", 0),
                )
            )
            _update_document_after_command(
                FreeCAD.ActiveDocument,
                update_labels=False,
                sanitize_ports=False,
                sanitize_equipments=False,
            )
        except Exception as exc:
            _log(tr("cmd.validate.error", error=exc))


class CmdInsertEvaporator(_BaseCommand):
    CommandName = "MEP_HVAC_InsertEvaporator"
    MenuText = tr("cmd.insert_evaporator.menu")
    ToolTip = tr("cmd.insert_evaporator.tooltip")
    IconPath = ICON_EVAPORATOR

    def Activated(self):  # noqa: N802
        _log(tr("cmd.insert_evaporator.run"))
        try:
            runtime_module = _load_hvac_equipment_runtime()
            if runtime_module is None:
                runtime_module = hvac_equipment
            _log(
                "InsertEvap runtime module rev={0} source={1}".format(
                    getattr(runtime_module, "EQUIP_DEBUG_REV", "n/a"),
                    getattr(runtime_module, "__file__", "n/a"),
                )
            )
            runtime_module.insert_evaporator_from_selection(FreeCAD.ActiveDocument)
            _update_document_after_command(FreeCAD.ActiveDocument, update_labels=True, sanitize_ports=True)
        except Exception as exc:
            _log(tr("cmd.insert_evaporator.error", error=exc))


class CmdPlaceCeilingUnits(_BaseCommand):
    CommandName = "MEP_HVAC_PlaceCeilingUnits"
    MenuText = tr("cmd.place_ceiling.menu")
    ToolTip = tr("cmd.place_ceiling.tooltip")
    IconPath = ICON_EVAPORATOR

    def Activated(self):  # noqa: N802
        _log(tr("cmd.place_ceiling.run"))
        try:
            runtime_module = _load_hvac_equipment_runtime()
            if runtime_module is None:
                runtime_module = hvac_equipment
            runtime_module.place_ceiling_units_from_selection(FreeCAD.ActiveDocument)
            _update_document_after_command(FreeCAD.ActiveDocument, update_labels=True, sanitize_ports=True)
        except Exception as exc:
            _log(tr("cmd.place_ceiling.error", error=exc))


class CmdAssignEvaporatorSpace(_BaseCommand):
    CommandName = "MEP_HVAC_AssignSpace"
    MenuText = tr("cmd.assign_space.menu")
    ToolTip = tr("cmd.assign_space.tooltip")
    IconPath = ICON_ASSIGN

    def Activated(self):  # noqa: N802
        _log(tr("cmd.assign_space.run"))
        try:
            runtime_module = _load_hvac_equipment_runtime()
            if runtime_module is None:
                runtime_module = hvac_equipment
            runtime_module.assign_selected_equipments_to_selected_space(
                FreeCAD.ActiveDocument,
                lock_manual=True,
            )
            _update_document_after_command(FreeCAD.ActiveDocument, update_labels=True, sanitize_ports=True)
        except Exception as exc:
            _log(tr("cmd.assign_space.error", error=exc))


class CmdInsertCondenser(_BaseCommand):
    CommandName = "MEP_HVAC_InsertCondenser"
    MenuText = tr("cmd.insert_condenser.menu")
    ToolTip = tr("cmd.insert_condenser.tooltip")
    IconPath = ICON_CONDENSER

    def Activated(self):  # noqa: N802
        _log(tr("cmd.insert_condenser.run"))
        try:
            runtime_condensing = _load_hvac_condensing_runtime() or hvac_condensing
            runtime_condensing.insert_condenser_from_selection(FreeCAD.ActiveDocument)
            _update_document_after_command(FreeCAD.ActiveDocument, update_labels=False, sanitize_ports=True)
        except Exception as exc:
            _log(tr("cmd.insert_condenser.error", error=exc))


class CmdAssignCondenserUnits(_BaseCommand):
    CommandName = "MEP_HVAC_AssignCondenserUnits"
    MenuText = tr("cmd.assign_units.menu")
    ToolTip = tr("cmd.assign_units.tooltip")
    IconPath = ICON_ASSIGN

    def Activated(self):  # noqa: N802
        _log(tr("cmd.assign_units.run"))
        try:
            runtime_condensing = _load_hvac_condensing_runtime() or hvac_condensing
            runtime_condensing.assign_selected_units_to_selected_condenser(
                FreeCAD.ActiveDocument,
                append=True,
            )
            _update_document_after_command(FreeCAD.ActiveDocument, update_labels=False, sanitize_ports=True)
        except Exception as exc:
            _log(tr("cmd.assign_units.error", error=exc))


class CmdCreateHVACRoute(_BaseCommand):
    CommandName = "MEP_HVAC_CreateRoute"
    MenuText = tr("cmd.create_route.menu")
    ToolTip = tr("cmd.create_route.tooltip")
    IconPath = ICON_ROUTE

    def Activated(self):  # noqa: N802
        _log(tr("cmd.create_route.run"))
        try:
            runtime_route = _load_hvac_route_runtime() or hvac_route
            created_route = runtime_route.create_route_from_selection(FreeCAD.ActiveDocument)
            if created_route is None:
                _log("[MEP-HVAC][Route] Comando sin cambios")
                return
            _update_document_after_command(
                FreeCAD.ActiveDocument,
                update_labels=False,
                sanitize_ports=False,
                sanitize_equipments=False,
            )
        except Exception as exc:
            _log(tr("cmd.create_route.error", error=exc))


class CmdToggleHVACLabels(_BaseCommand):
    CommandName = "MEP_HVAC_ToggleLabels"
    MenuText = tr("cmd.toggle_labels.menu")
    ToolTip = tr("cmd.toggle_labels.tooltip")
    IconPath = ICON_LABELS

    def Activated(self):  # noqa: N802
        _log(tr("cmd.toggle_labels.run"))
        try:
            runtime_project = _load_hvac_project_runtime() or hvac_project
            _log(
                "ToggleHVAC runtime: project_src={0}".format(
                    getattr(runtime_project, "__file__", "n/a"),
                )
            )
            if hasattr(runtime_project, "toggle_hvac_visibility"):
                runtime_project.toggle_hvac_visibility(FreeCAD.ActiveDocument)
            else:
                runtime_label = _load_hvac_label_runtime() or hvac_label
                runtime_label.toggle_labels(FreeCAD.ActiveDocument)
            _update_document_after_command(FreeCAD.ActiveDocument, update_labels=False, sanitize_ports=False)
        except Exception as exc:
            _log(tr("cmd.toggle_labels.error", error=exc))


class CmdSetHVACVisualModeAll(_BaseCommand):
    CommandName = "MEP_HVAC_SetVisualModeAll"
    MenuText = tr("cmd.visual_mode_all.menu")
    ToolTip = tr("cmd.visual_mode_all.tooltip")
    IconPath = ICON_LABELS

    @staticmethod
    def _pick_mode(options):
        if not FreeCAD.GuiUp:
            return None
        try:
            from PySide2 import QtWidgets
        except Exception:
            try:
                from PySide import QtGui as QtWidgets  # type: ignore
            except Exception:
                return None
        try:
            selected, ok = QtWidgets.QInputDialog.getItem(
                None,
                tr("cmd.visual_mode_all.pick_title"),
                tr("cmd.visual_mode_all.pick_prompt"),
                list(options),
                0,
                False,
            )
            if ok and selected:
                return str(selected)
        except Exception:
            return None
        return None

    def Activated(self):  # noqa: N802
        _log(tr("cmd.visual_mode_all.run"))
        try:
            doc = FreeCAD.ActiveDocument
            if doc is None:
                return

            runtime_equipment = _load_hvac_equipment_runtime() or hvac_equipment
            runtime_condensing = _load_hvac_condensing_runtime() or hvac_condensing

            options = list(getattr(runtime_equipment, "VISUAL_MODE_OPTIONS", ["Ambos", "Solo2D", "Solo3D", "Ninguno"]))
            mode = self._pick_mode(options)
            if not mode:
                _log(tr("cmd.visual_mode_all.cancel"))
                return
            mode_value = str(mode)
            show_3d = mode_value in {"Ambos", "Solo3D"}
            show_2d = mode_value in {"Ambos", "Solo2D"}
            if mode_value == "Ninguno":
                show_3d = False
                show_2d = False

            changed_evap = 0
            changed_cond = 0

            _remove_hvac_equipment_observer()
            try:
                for equipment_obj in list(runtime_equipment.find_equipments(doc) or []):
                    if equipment_obj is None:
                        continue
                    try:
                        props = list(getattr(equipment_obj, "PropertiesList", []) or [])
                        if "VisualMode" not in props:
                            continue
                        previous = str(getattr(equipment_obj, "VisualMode", "") or "")
                        equipment_obj.VisualMode = str(mode)
                        if previous != str(mode):
                            changed_evap += 1
                        runtime_equipment.refresh_equipment(equipment_obj)
                        if hasattr(equipment_obj, "ViewObject") and equipment_obj.ViewObject is not None:
                            equipment_obj.ViewObject.Visibility = bool(show_3d)
                    except Exception:
                        continue

                for condenser_obj in list(runtime_condensing.find_condensers(doc) or []):
                    if condenser_obj is None:
                        continue
                    try:
                        props = list(getattr(condenser_obj, "PropertiesList", []) or [])
                        if "VisualMode" not in props:
                            continue
                        previous = str(getattr(condenser_obj, "VisualMode", "") or "")
                        condenser_obj.VisualMode = str(mode)
                        if previous != str(mode):
                            changed_cond += 1
                        if hasattr(runtime_condensing, "refresh_condenser"):
                            runtime_condensing.refresh_condenser(condenser_obj)
                        if hasattr(condenser_obj, "ViewObject") and condenser_obj.ViewObject is not None:
                            condenser_obj.ViewObject.Visibility = bool(show_3d)
                    except Exception:
                        continue

                # Force 2D visibility globally as final pass. This also covers legacy
                # or temporarily orphan 2D symbols that are not currently linked.
                symbols = []
                if hasattr(runtime_equipment, "find_symbol2d_objects"):
                    symbols.extend(list(runtime_equipment.find_symbol2d_objects(doc) or []))
                if hasattr(runtime_condensing, "find_symbol2d_objects"):
                    symbols.extend(list(runtime_condensing.find_symbol2d_objects(doc) or []))

                for obj in list(getattr(doc, "Objects", []) or []):
                    if obj is None:
                        continue
                    name = str(getattr(obj, "Name", "") or "")
                    label = str(getattr(obj, "Label", "") or "")
                    if (
                        _is_hvac_symbol2d(obj)
                        or name.startswith("HVAC_Evap2D")
                        or name.startswith("HVAC_Cond2D")
                        or label.startswith("HVAC_2D_")
                        or label.startswith("HVAC_2D_COND_")
                    ):
                        symbols.append(obj)

                seen_symbol_names = set()
                unique_symbols = []
                for symbol in symbols:
                    if symbol is None:
                        continue
                    symbol_name = str(getattr(symbol, "Name", "") or "")
                    if not symbol_name or symbol_name in seen_symbol_names:
                        continue
                    if doc.getObject(symbol_name) is None:
                        continue
                    seen_symbol_names.add(symbol_name)
                    unique_symbols.append(symbol)

                for symbol_obj in unique_symbols:
                    try:
                        if hasattr(symbol_obj, "ViewObject") and symbol_obj.ViewObject is not None:
                            symbol_obj.ViewObject.Visibility = bool(show_2d)
                    except Exception:
                        continue
                _log(
                    "[MEP-HVAC][Visual] Modo global aplicado: modo={0}, show_3d={1}, show_2d={2}, simbolos_2d={3}".format(
                        mode_value,
                        bool(show_3d),
                        bool(show_2d),
                        len(unique_symbols),
                    )
                )
            finally:
                _ensure_hvac_equipment_observer()

            _update_document_after_command(
                doc,
                update_labels=False,
                sanitize_ports=False,
                sanitize_condensers=False,
                sanitize_equipments=False,
            )
            _log(
                tr(
                    "cmd.visual_mode_all.applied",
                    mode=mode,
                    evaporators=changed_evap,
                    condensers=changed_cond,
                )
            )
        except Exception as exc:
            _log(tr("cmd.visual_mode_all.error", error=exc))


class CmdRefreshHVACModels(_BaseCommand):
    CommandName = "MEP_HVAC_RefreshModels"
    MenuText = tr("cmd.refresh_models.menu")
    ToolTip = tr("cmd.refresh_models.tooltip")
    IconPath = ICON_RELOAD

    def Activated(self):  # noqa: N802
        _log(tr("cmd.refresh_models.run"))
        try:
            doc = FreeCAD.ActiveDocument
            runtime_equipment = _load_hvac_equipment_runtime() or hvac_equipment
            runtime_condensing = _load_hvac_condensing_runtime() or hvac_condensing
            _remove_hvac_equipment_observer()
            try:
                if hasattr(runtime_equipment, "refresh_step_models"):
                    runtime_equipment.refresh_step_models(doc)
                if hasattr(runtime_condensing, "refresh_step_models"):
                    runtime_condensing.refresh_step_models(doc)
            finally:
                _ensure_hvac_equipment_observer()
            _update_document_after_command(
                doc,
                update_labels=False,
                sanitize_ports=False,
                sanitize_condensers=False,
                sanitize_equipments=False,
            )
        except Exception as exc:
            _log(tr("cmd.refresh_models.error", error=exc))


class CmdExportHVAC2D(_BaseCommand):
    CommandName = "MEP_HVAC_Export2D"
    MenuText = tr("cmd.export_2d.menu")
    ToolTip = tr("cmd.export_2d.tooltip")
    IconPath = ICON_ROUTE

    def Activated(self):  # noqa: N802
        _log(tr("cmd.export_2d.run"))
        try:
            doc = FreeCAD.ActiveDocument
            if doc is None:
                return
            runtime_equipment = _load_hvac_equipment_runtime() or hvac_equipment
            runtime_condensing = _load_hvac_condensing_runtime() or hvac_condensing

            symbols = []
            if hasattr(runtime_equipment, "find_symbol2d_objects"):
                symbols.extend(list(runtime_equipment.find_symbol2d_objects(doc) or []))
            if hasattr(runtime_equipment, "find_info2d_objects"):
                symbols.extend(list(runtime_equipment.find_info2d_objects(doc) or []))
            if hasattr(runtime_condensing, "find_symbol2d_objects"):
                symbols.extend(list(runtime_condensing.find_symbol2d_objects(doc) or []))

            unique = []
            seen = set()
            for obj in symbols:
                name = str(getattr(obj, "Name", "") or "")
                if not name or name in seen:
                    continue
                if doc.getObject(name) is None:
                    continue
                seen.add(name)
                unique.append(obj)

            if not unique:
                _log(tr("cmd.export_2d.none"))
                return

            previous_selection = []
            try:
                previous_selection = list(FreeCADGui.Selection.getSelection() or [])
            except Exception:
                previous_selection = []

            try:
                FreeCADGui.Selection.clearSelection()
                for obj in unique:
                    try:
                        FreeCADGui.Selection.addSelection(doc.Name, obj.Name)
                    except Exception:
                        continue
                _run_external_macro(EXPORT_2D_MACRO_PATH)
            finally:
                try:
                    FreeCADGui.Selection.clearSelection()
                    for obj in previous_selection:
                        try:
                            if doc.getObject(str(getattr(obj, "Name", "") or "")) is not None:
                                FreeCADGui.Selection.addSelection(doc.Name, obj.Name)
                        except Exception:
                            continue
                except Exception:
                    pass
        except Exception as exc:
            _log(tr("cmd.export_2d.error", error=exc))


class CmdReloadWorkbench(_BaseCommand):
    CommandName = "MEP_HVAC_ReloadWorkbench"
    MenuText = tr("cmd.reload.menu")
    ToolTip = tr("cmd.reload.tooltip")
    IconPath = ICON_RELOAD

    def IsActive(self):  # noqa: N802
        return True

    def Activated(self):  # noqa: N802
        _log(tr("cmd.reload.run"))
        try:
            _log_reload_debug("manual_reload")
            _reload_workbench()
        except Exception as exc:
            _log(tr("cmd.reload.error", error=exc))


class CmdAlignObjects(_BaseCommand):
    CommandName = "MEP_HVAC_AlignObjects"
    MenuText = tr("cmd.align.menu")
    ToolTip = tr("cmd.align.tooltip")
    IconPath = ICON_ALIGN

    def Activated(self):  # noqa: N802
        _log(tr("cmd.align.run"))
        try:
            _run_external_macro(ALIGN_MACRO_PATH)
        except Exception as exc:
            _log(tr("cmd.align.error", error=exc))


def _build_command_instances():
    return [
        CmdCreateHVACProject(),
        CmdCreateHVACSpace(),
        CmdCalculateHVAC(),
        CmdAlignObjects(),
        CmdInsertEvaporator(),
        CmdPlaceCeilingUnits(),
        CmdAssignEvaporatorSpace(),
        CmdToggleHVACLabels(),
        CmdSetHVACVisualModeAll(),
        CmdInsertCondenser(),
        CmdAssignCondenserUnits(),
        CmdCreateHVACRoute(),
        CmdValidateHVAC(),
        CmdRefreshHVACModels(),
        CmdExportHVAC2D(),
        CmdReloadWorkbench(),
    ]


def _main_command_names():
    return [
        CmdCreateHVACSpace.CommandName,
        CmdCalculateHVAC.CommandName,
        CmdAlignObjects.CommandName,
        CmdToggleHVACLabels.CommandName,
        CmdSetHVACVisualModeAll.CommandName,
        CmdInsertEvaporator.CommandName,
        CmdPlaceCeilingUnits.CommandName,
        CmdAssignEvaporatorSpace.CommandName,
    ]


def _system_command_names():
    return [
        CmdCreateHVACProject.CommandName,
        CmdInsertCondenser.CommandName,
        CmdAssignCondenserUnits.CommandName,
        CmdCreateHVACRoute.CommandName,
        CmdValidateHVAC.CommandName,
        CmdRefreshHVACModels.CommandName,
        CmdExportHVAC2D.CommandName,
        CmdReloadWorkbench.CommandName,
    ]


class MEPWorkbenchCR(FreeCADGui.Workbench):
    """MEP Workbench focused on HVAC MVP."""

    MenuText = tr("wb.menu_text")
    ToolTip = tr("wb.tooltip")
    Icon = ICON_PATH

    def _ensure_draft_ui_registered(self):
        """Late-bind Draft UI when commands become available after workbench init."""
        draft_commands = _available_draft_commands()
        if not draft_commands:
            return False

        if not bool(getattr(self, "_draft_toolbar_registered", False)):
            self.appendToolbar(tr("wb.toolbar.draft"), draft_commands)
            self._draft_toolbar_registered = True
            _log("Draft tools integrated: {0}".format(", ".join(draft_commands)))

        if not bool(getattr(self, "_draft_menu_registered", False)):
            self.appendMenu([tr("wb.menu"), tr("wb.menu.draft")], draft_commands)
            self._draft_menu_registered = True

        if not bool(getattr(self, "_draft_snap_registered", False)):
            snap_commands = _init_draft_snap_toolbar(self)
            if snap_commands:
                self._draft_snap_registered = True
        return True

    def Initialize(self):  # noqa: N802
        _log(tr("wb.log.initializing"))
        _refresh_icon_cache()
        _log("Icon align cargado desde: {0}".format(ICON_ALIGN))
        self._draft_toolbar_registered = False
        self._draft_menu_registered = False
        self._draft_snap_registered = False
        removed_commands = _unregister_commands()
        if removed_commands > 0:
            _log("Comandos HVAC desregistrados en Initialize: {0}".format(removed_commands))
        commands = _build_command_instances()
        for command in commands:
            FreeCADGui.addCommand(command.CommandName, command)

        main_commands = _main_command_names()
        system_commands = _system_command_names()
        draft_commands = _available_draft_commands()

        self.appendToolbar(tr("wb.toolbar.main"), main_commands)
        self.appendToolbar(tr("wb.toolbar.system"), system_commands)
        if draft_commands:
            self.appendToolbar(tr("wb.toolbar.draft"), draft_commands)
            self._draft_toolbar_registered = True
            _log("Draft tools integrated: {0}".format(", ".join(draft_commands)))
        else:
            _log("Draft tools not available in this session")
        snap_commands = _init_draft_snap_toolbar(self)
        if snap_commands:
            self._draft_snap_registered = True

        self.appendMenu([tr("wb.menu"), tr("wb.menu.main")], main_commands)
        self.appendMenu([tr("wb.menu"), tr("wb.menu.system")], system_commands)
        if draft_commands:
            self.appendMenu([tr("wb.menu"), tr("wb.menu.draft")], draft_commands)
            self._draft_menu_registered = True

    def Activated(self):  # noqa: N802
        _log(tr("wb.log.activated"))
        _log_reload_debug("workbench_activated")
        _log("InitGui source: {0}".format(MODULE_SOURCE))
        _activate_draft_snap_runtime()
        if not bool(getattr(self, "_draft_toolbar_registered", False)):
            if self._ensure_draft_ui_registered():
                _log("Draft tools integrated on activation (late load)")
            else:
                _log("Draft tools still unavailable on activation")
        _ensure_hvac_equipment_observer()
        doc = FreeCAD.ActiveDocument
        if doc is not None:
            try:
                _update_document_after_command(
                    doc,
                    update_labels=False,
                    sanitize_ports=False,
                    sanitize_equipments=False,
                )
            except Exception as exc:
                _log("Post-activate HVAC update skipped: {0}".format(exc))

    def Deactivated(self):  # noqa: N802
        _remove_hvac_equipment_observer()
        _deactivate_draft_snap_runtime()
        _log(tr("wb.log.deactivated"))


def _ensure_clean_registration():
    """Avoid stale registration after live-reload in development."""

    try:
        existing = dict(getattr(FreeCADGui, "listWorkbenches", lambda: {})() or {})
    except Exception:
        existing = {}
    if WORKBENCH_ID in existing and hasattr(FreeCADGui, "removeWorkbench"):
        try:
            _unregister_commands()
            try:
                FreeCADGui.activateWorkbench("StartWorkbench")
            except Exception:
                pass
            FreeCADGui.removeWorkbench(WORKBENCH_ID)
        except Exception as exc:
            _log(tr("wb.log.clean_registration_failed", error=exc))


_ensure_clean_registration()
FreeCADGui.addWorkbench(MEPWorkbenchCR())
