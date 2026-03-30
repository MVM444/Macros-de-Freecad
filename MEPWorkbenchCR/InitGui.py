"""GUI registration for MEPWorkbenchCR."""

import importlib
import os
import sys

import FreeCAD
import FreeCADGui

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
    from .MEP.hvac import recalculate_document
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
    from MEP.hvac import recalculate_document

LOG_PREFIX = "[MEP-HVAC] "
WORKBENCH_ID = "MEPWorkbenchCR"
ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "resources", "icons"))


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


def _log(message):
    text = LOG_PREFIX + str(message)
    print(text)


def _ensure_package_parent_in_path():
    package_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.dirname(package_dir))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)


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

    _purge_reload_modules()
    importlib.invalidate_caches()
    module = importlib.import_module("MEPWorkbenchCR.InitGui")
    importlib.reload(module)
    _log("Reload source: {0}".format(getattr(module, "__file__", "")))
    FreeCADGui.activateWorkbench(WORKBENCH_ID)


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
            hvac_project.get_or_create_project(FreeCAD.ActiveDocument)
            FreeCAD.ActiveDocument.recompute()
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
            hvac_space.create_space_from_selection(FreeCAD.ActiveDocument)
            FreeCAD.ActiveDocument.recompute()
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
            if hvac_space.has_area_selection():
                spaces = hvac_space.prepare_spaces_from_selection_quick(FreeCAD.ActiveDocument)
                if spaces:
                    _log(tr("cmd.calculate.quick_spaces", count=len(spaces)))
            recalculate_document(FreeCAD.ActiveDocument)
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
            report = hvac_validate.validate_document(FreeCAD.ActiveDocument, recalc_first=True)
            _log(
                tr(
                    "cmd.validate.summary",
                    errors=report.get("errors", 0),
                    warnings=report.get("warnings", 0),
                    infos=report.get("infos", 0),
                )
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
            hvac_equipment.insert_evaporator_from_selection(FreeCAD.ActiveDocument)
            FreeCAD.ActiveDocument.recompute()
        except Exception as exc:
            _log(tr("cmd.insert_evaporator.error", error=exc))


class CmdInsertCondenser(_BaseCommand):
    CommandName = "MEP_HVAC_InsertCondenser"
    MenuText = tr("cmd.insert_condenser.menu")
    ToolTip = tr("cmd.insert_condenser.tooltip")
    IconPath = ICON_CONDENSER

    def Activated(self):  # noqa: N802
        _log(tr("cmd.insert_condenser.run"))
        try:
            hvac_condensing.insert_condenser_from_selection(FreeCAD.ActiveDocument)
            FreeCAD.ActiveDocument.recompute()
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
            hvac_condensing.assign_selected_units_to_selected_condenser(
                FreeCAD.ActiveDocument,
                append=True,
            )
            FreeCAD.ActiveDocument.recompute()
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
            hvac_route.create_route_from_selection(FreeCAD.ActiveDocument)
            FreeCAD.ActiveDocument.recompute()
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
            hvac_label.toggle_labels(FreeCAD.ActiveDocument)
            FreeCAD.ActiveDocument.recompute()
        except Exception as exc:
            _log(tr("cmd.toggle_labels.error", error=exc))


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
            _reload_workbench()
        except Exception as exc:
            _log(tr("cmd.reload.error", error=exc))


def _build_command_instances():
    return [
        CmdCreateHVACProject(),
        CmdCreateHVACSpace(),
        CmdCalculateHVAC(),
        CmdInsertEvaporator(),
        CmdToggleHVACLabels(),
        CmdInsertCondenser(),
        CmdAssignCondenserUnits(),
        CmdCreateHVACRoute(),
        CmdValidateHVAC(),
        CmdReloadWorkbench(),
    ]


def _main_command_names():
    return [
        CmdCreateHVACSpace.CommandName,
        CmdCalculateHVAC.CommandName,
        CmdToggleHVACLabels.CommandName,
        CmdInsertEvaporator.CommandName,
    ]


def _system_command_names():
    return [
        CmdCreateHVACProject.CommandName,
        CmdInsertCondenser.CommandName,
        CmdAssignCondenserUnits.CommandName,
        CmdCreateHVACRoute.CommandName,
        CmdValidateHVAC.CommandName,
        CmdReloadWorkbench.CommandName,
    ]


class MEPWorkbenchCR(FreeCADGui.Workbench):
    """MEP Workbench focused on HVAC MVP."""

    MenuText = tr("wb.menu_text")
    ToolTip = tr("wb.tooltip")
    Icon = ICON_PATH

    def Initialize(self):  # noqa: N802
        _log(tr("wb.log.initializing"))
        commands = _build_command_instances()
        for command in commands:
            FreeCADGui.addCommand(command.CommandName, command)

        main_commands = _main_command_names()
        system_commands = _system_command_names()

        self.appendToolbar(tr("wb.toolbar.main"), main_commands)
        self.appendToolbar(tr("wb.toolbar.system"), system_commands)

        self.appendMenu([tr("wb.menu"), tr("wb.menu.main")], main_commands)
        self.appendMenu([tr("wb.menu"), tr("wb.menu.system")], system_commands)

    def Activated(self):  # noqa: N802
        _log(tr("wb.log.activated"))
        doc = FreeCAD.ActiveDocument
        if doc is not None:
            try:
                hvac_project.ensure_hvac_root_group(doc)
                if hasattr(hvac_project, "ensure_hvac_label_group"):
                    hvac_project.ensure_hvac_label_group(doc)
                hvac_project.organize_hvac_objects(doc)
                hvac_ports.sanitize_all_ports(doc)
                doc.recompute()
            except Exception:
                pass

    def Deactivated(self):  # noqa: N802
        _log(tr("wb.log.deactivated"))


def _ensure_clean_registration():
    """Avoid stale registration after live-reload in development."""

    try:
        existing = dict(getattr(FreeCADGui, "listWorkbenches", lambda: {})() or {})
    except Exception:
        existing = {}
    if WORKBENCH_ID in existing and hasattr(FreeCADGui, "removeWorkbench"):
        try:
            try:
                FreeCADGui.activateWorkbench("StartWorkbench")
            except Exception:
                pass
            FreeCADGui.removeWorkbench(WORKBENCH_ID)
        except Exception as exc:
            _log(tr("wb.log.clean_registration_failed", error=exc))


_ensure_clean_registration()
FreeCADGui.addWorkbench(MEPWorkbenchCR())
