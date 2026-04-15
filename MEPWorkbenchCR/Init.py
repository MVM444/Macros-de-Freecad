"""Bootstrap module for MEPWorkbenchCR."""

import os
import sys


def _ensure_import_paths():
    """Make package/module imports stable in both Addon and Macro layouts."""
    package_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.dirname(package_dir))

    for path in (package_dir, parent_dir):
        if path and path not in sys.path:
            sys.path.insert(0, path)


def _register_legacy_aliases():
    """Expose legacy module aliases used by older saved documents."""
    try:
        import MEPWorkbenchCR.MEP as mep_pkg

        # Many legacy proxies were serialized as MEP.* or MEPWorkbenchCR.MEP.*
        sys.modules.setdefault("MEP", mep_pkg)
    except Exception:
        pass


_ensure_import_paths()
_register_legacy_aliases()

