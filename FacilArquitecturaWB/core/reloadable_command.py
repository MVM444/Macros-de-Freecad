"""Stable FreeCAD command proxy for the development hot-reload workflow.

FreeCAD 1.1.3 does not expose ``FreeCADGui.removeCommand``.  A command object
registered under a stable ID can therefore outlive the Python module that created
it.  This neutral proxy keeps the ID stable while resolving the current command
class from ``sys.modules`` on every use.
"""

from __future__ import annotations

import importlib


class ReloadableCommandProxy:
    """Delegate FreeCAD command calls to the current module implementation."""

    def __init__(self, module_name, class_name="CommandClass", command_name=""):
        self.module_name = str(module_name)
        self.class_name = str(class_name)
        self.CommandName = str(command_name)

    def _implementation(self):
        module = importlib.import_module(self.module_name)
        return getattr(module, self.class_name)()

    def GetResources(self):  # noqa: N802
        return self._implementation().GetResources()

    def Activated(self):  # noqa: N802
        return self._implementation().Activated()

    def IsActive(self):  # noqa: N802
        return self._implementation().IsActive()
