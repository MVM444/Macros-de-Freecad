# -*- coding: utf-8 -*-
"""ElectricCR package bootstrap.

This package installs a small import alias so documents created with the old
dynamic tablero loader (`_electriccr_tablero_runtime_<stamp>`) can still be
restored after the loader was switched to a stable module name.
"""

import importlib
import importlib.abc
import importlib.util
import re
import sys


_LEGACY_TABLERO_RUNTIME_RE = re.compile(r"^_electriccr_tablero_runtime_\d+$")
_TABLERO_BACKEND_CANDIDATES = (
    "ElectricCR.electriccr.features.tablero_electrico",
    "electriccr.features.tablero_electrico",
)


class _LegacyTableroRuntimeAlias(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Redirect legacy runtime module names to the stable tablero backend."""

    def find_spec(self, fullname, path=None, target=None):
        del path, target
        if not _LEGACY_TABLERO_RUNTIME_RE.match(str(fullname or "")):
            return None
        return importlib.util.spec_from_loader(
            fullname,
            self,
            origin="ElectricCR legacy tablero runtime alias",
        )

    def create_module(self, spec):
        del spec
        return None

    def exec_module(self, module):
        backend = None
        last_error = None
        for mod_name in _TABLERO_BACKEND_CANDIDATES:
            try:
                backend = importlib.import_module(mod_name)
                break
            except Exception as ex:
                last_error = ex
        if backend is None:
            raise ImportError(
                "No se pudo redirigir el runtime legacy de tablero: {}".format(last_error)
            ) from last_error

        module.__doc__ = getattr(backend, "__doc__", None)
        module.__file__ = getattr(backend, "__file__", None)
        module.__loader__ = self
        module.__package__ = ""
        module.__dict__["__alias_target__"] = getattr(backend, "__name__", "")

        for key, value in vars(backend).items():
            if key in {"__name__", "__loader__", "__package__", "__spec__"}:
                continue
            module.__dict__[key] = value


def _install_legacy_tablero_runtime_alias():
    for finder in sys.meta_path:
        if isinstance(finder, _LegacyTableroRuntimeAlias):
            return finder
    finder = _LegacyTableroRuntimeAlias()
    sys.meta_path.insert(0, finder)
    return finder


_install_legacy_tablero_runtime_alias()
