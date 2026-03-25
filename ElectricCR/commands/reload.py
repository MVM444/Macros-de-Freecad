# -*- coding: utf-8 -*-

import os
import importlib
import FreeCAD as App
import FreeCADGui as Gui

from .. import usage_log

ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons")


def _icon(name):
    for candidate in (f"{name}.svg", f"{name}.png", name):
        p = os.path.join(ICONS_DIR, candidate)
        if os.path.exists(p):
            return p
    # fallback
    for candidate in ("Rayo.svg", "Rayo.png", "Rayo"):
        p = os.path.join(ICONS_DIR, candidate)
        if os.path.exists(p):
            return p
    return ""


class ReloadElectricCR:
    def GetResources(self):
        return {
            'Pixmap': _icon('ReloadElectricCR'),
            'MenuText': 'Recargar ElectricCR',
            'ToolTip': 'Recarga módulos y reinicia el workbench',
        }

    def Activated(self):
        try:
            usage_log.log_tool(COMMAND_NAME, {"source": "command"})
        except Exception:
            pass
        # Elegir un WB de respaldo seguro
        fallback = 'StartWorkbench'
        try:
            wb_map = Gui.listWorkbenches()
            keys = set(wb_map.keys()) if isinstance(wb_map, dict) else set(wb_map)
            if 'DraftWorkbench' in keys:
                fallback = 'DraftWorkbench'
        except Exception:
            pass

        # Si estamos en ElectricCR, cambia primero al fallback
        try:
            current = None
            try:
                current = Gui.activeWorkbench()
            except Exception:
                current = None
            if current and getattr(current, '__class__', type('x',(object,),{})).__name__ == 'ElectricCRWorkbench':
                Gui.activateWorkbench(fallback)
        except Exception:
            pass

        # Recargar módulos del paquete
        try:
            import importlib
            import sys
            names = [n for n in list(sys.modules.keys()) if n == 'ElectricCR' or n.startswith('ElectricCR.')]
            for name in names:
                sys.modules.pop(name, None)
            importlib.invalidate_caches()
            importlib.import_module('ElectricCR.commands.macros')
            importlib.import_module('ElectricCR.InitGui')
            App.Console.PrintMessage('ElectricCR: modulos recargados.\n')
        except Exception as e:
            App.Console.PrintError(f'ElectricCR: error recargando modulos: {e}\n')

        # Forzar reconstrucción
        try:
            # Marcar instancia como no construida si existe
            try:
                wb = Gui.getWorkbench('ElectricCRWorkbench')
                if wb:
                    setattr(wb, '_built', False)
            except Exception:
                pass
            Gui.activateWorkbench('ElectricCRWorkbench')
        except Exception as e:
            App.Console.PrintError(f'ElectricCR: no se pudo reactivar el WB: {e}\n')

    def IsActive(self):
        return True


COMMAND_NAME = 'ElectricCR_Reload'
Gui.addCommand(COMMAND_NAME, ReloadElectricCR())
