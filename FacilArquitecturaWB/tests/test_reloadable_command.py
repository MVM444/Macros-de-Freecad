"""Pure regression tests for stable FreeCAD command hot reload."""

from __future__ import annotations

import sys
import types
import unittest

from FacilArquitecturaWB.core.reloadable_command import ReloadableCommandProxy


class ReloadableCommandTests(unittest.TestCase):
    def test_registered_proxy_resolves_replaced_module_implementation(self):
        module_name = "fa_test_reloadable_command"
        calls = []

        class First:
            def Activated(self):  # noqa: N802
                calls.append("first")

            def GetResources(self):  # noqa: N802
                return {"MenuText": "First"}

            def IsActive(self):  # noqa: N802
                return True

        class Second(First):
            def Activated(self):  # noqa: N802
                calls.append("second")

            def GetResources(self):  # noqa: N802
                return {"MenuText": "Second"}

        try:
            sys.modules[module_name] = types.SimpleNamespace(CommandClass=First)
            proxy = ReloadableCommandProxy(
                module_name, command_name="FA_StableCommand"
            )
            proxy.Activated()

            sys.modules[module_name] = types.SimpleNamespace(CommandClass=Second)
            proxy.Activated()

            self.assertEqual(["first", "second"], calls)
            self.assertEqual("Second", proxy.GetResources()["MenuText"])
            self.assertTrue(proxy.IsActive())
            self.assertEqual("FA_StableCommand", proxy.CommandName)
        finally:
            sys.modules.pop(module_name, None)


if __name__ == "__main__":
    unittest.main()
