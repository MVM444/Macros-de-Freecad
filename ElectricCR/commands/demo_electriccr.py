# -*- coding: utf-8 -*-
"""GUI commands for the canonical ElectricCR A1 demo.

Purpose:
- Expose demo generation and its read-only audit through the ElectricCR workbench.

Main behavior:
- Create command always opens a NEW demo document and never edits the active project.
- Audit command checks the active demo document without repairing it.

Future modification guidance:
- Keep this module as a thin GUI adapter; creation/audit logic belongs in electriccr.demo.

Version: 0.1.1
Date/time: 2026-09-10 10:19 America/Costa_Rica
Target: FreeCAD 1.1.3.
"""

from __future__ import annotations

import os

import FreeCAD as App
import FreeCADGui as Gui


CREATE_COMMAND_NAME = "ElectricCR_DemoA1_Create"
AUDIT_COMMAND_NAME = "ElectricCR_DemoA1_Audit"
CREATE_COMMAND_LABEL = "Demo ElectricCR A1"
AUDIT_COMMAND_LABEL = "Auditar Demo ElectricCR A1"
ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons")


def _icon(primary_name):
    """Return a command-specific icon, with the WB logo only as emergency fallback."""
    for name in (primary_name, "Rayo.svg", "Rayo.png"):
        path = os.path.join(ICONS_DIR, name)
        if os.path.exists(path):
            return path
    return ""


def _fit_demo_view():
    try:
        view = Gui.activeDocument().activeView()
        view.viewAxonometric()
        view.fitAll()
    except Exception:
        pass


class CreateElectricDemoCommand:
    def GetResources(self):
        return {
            "Pixmap": _icon("Demo_ElectricCR_A1.svg"),
            "MenuText": CREATE_COMMAND_LABEL,
            "ToolTip": (
                "Crea en un documento nuevo la demo canonica ElectricCR: "
                "2 Spaces BIM y 7 dispositivos A1 con PLAN."
            ),
        }

    def Activated(self):
        try:
            from ..electriccr.demo.electric_demo_freecad import create_fixed_demo
            from ..electriccr.demo.electric_demo_audit import audit_demo, format_console_summary

            result = create_fixed_demo()
            report = audit_demo(result["document"], result["spec"])
            App.Console.PrintMessage(format_console_summary(report) + "\n")
            if report["status"] != "PASS":
                App.Console.PrintWarning(
                    "[ElectricCR][Demo] La demo se creo, pero la auditoria inicial no paso. Revise la consola.\n"
                )
            _fit_demo_view()
        except Exception as exc:
            App.Console.PrintError("[ElectricCR][Demo] error=%s\n" % exc)
            raise

    def IsActive(self):
        return True


class AuditElectricDemoCommand:
    def GetResources(self):
        return {
            "Pixmap": _icon("Auditar_Demo_ElectricCR_A1.svg"),
            "MenuText": AUDIT_COMMAND_LABEL,
            "ToolTip": "Auditoria read-only del documento demo ElectricCR activo.",
        }

    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintWarning("[ElectricCR][Demo Audit] No hay documento activo.\n")
            return
        try:
            from ..electriccr.demo.electric_demo_audit import audit_demo, format_console_summary

            report = audit_demo(doc)
            App.Console.PrintMessage(format_console_summary(report) + "\n")
            for item in report["checks"]:
                if item["status"] != "PASS":
                    App.Console.PrintWarning(
                        "[ElectricCR][Demo Audit] %s %s: %s\n"
                        % (item["status"], item["code"], item["message"])
                    )
        except Exception as exc:
            App.Console.PrintError("[ElectricCR][Demo Audit] error=%s\n" % exc)
            raise

    def IsActive(self):
        return App.ActiveDocument is not None


def register_commands():
    registered = set(Gui.listCommands())
    if CREATE_COMMAND_NAME not in registered:
        Gui.addCommand(CREATE_COMMAND_NAME, CreateElectricDemoCommand())
    registered = set(Gui.listCommands())
    if AUDIT_COMMAND_NAME not in registered:
        Gui.addCommand(AUDIT_COMMAND_NAME, AuditElectricDemoCommand())
    return [CREATE_COMMAND_NAME, AUDIT_COMMAND_NAME]


__all__ = [
    "CREATE_COMMAND_NAME",
    "AUDIT_COMMAND_NAME",
    "register_commands",
]
