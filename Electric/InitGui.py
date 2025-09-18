#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import types
import FreeCAD as App
import FreeCADGui as Gui


def _icon_path():
    base = os.path.dirname(__file__)
    svg = os.path.join(base, "Resources", "electric_cr.svg")
    return svg if os.path.exists(svg) else ""


class ElecCR_InsertarTomacorrienteCmd:
    def GetResources(self):
        return {
            "Pixmap": _icon_path(),
            "MenuText": "Insertar tomacorriente",
            "ToolTip": "Inserta un tomacorriente 2D/3D en el documento.",
        }

    def IsActive(self):
        return True

    def Activated(self):
        base = os.path.dirname(__file__)
        macro_path = os.path.join(base, "Insertar", "Insertar_Tomacorriente.FCMacro")
        if not os.path.exists(macro_path):
            App.Console.PrintError("[ELEC][ERROR] No se encuentra Insertar_Tomacorriente.FCMacro\n")
            return
        try:
            with open(macro_path, "r", encoding="utf-8") as fh:
                src = fh.read()
            mod = types.ModuleType("Insertar_Tomacorriente")
            mod.__file__ = macro_path
            exec(compile(src, macro_path, "exec"), mod.__dict__)
            if hasattr(mod, "insertar_tomacorriente"):
                mod.insertar_tomacorriente()
            else:
                App.Console.PrintError("[ELEC][ERROR] La macro no expone insertar_tomacorriente()\n")
        except Exception as exc:
            App.Console.PrintError(f"[ELEC][ERROR] Falla al ejecutar macro: {exc}\n")


class ElectricCRWorkbench(Gui.Workbench):
    MenuText = "Electric"
    ToolTip = "Herramientas eléctricas (Costa Rica)"
    Icon = _icon_path()

    def Initialize(self):
        Gui.addCommand("ElecCR_InsertarTomacorriente", ElecCR_InsertarTomacorrienteCmd())
        # Menú: Electric > Insertar > Insertar tomacorriente
        self.appendMenu(["Electric", "Insertar"], ["ElecCR_InsertarTomacorriente"])
        # Barra: Electric - Insertar
        self.appendToolbar("Electric - Insertar", ["ElecCR_InsertarTomacorriente"])

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(ElectricCRWorkbench())
