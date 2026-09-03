"""Small, self-disabling compatibility helpers for supported FreeCAD builds.

The DXF helper is intentionally isolated from the importer.  It works around
FreeCAD issue #31637 only while the installed Draft importer still exposes the
problematic ``suspendWaitCursor``/``resumeWaitCursor`` pattern.  Once that
structural pattern disappears, the normal FreeCAD path is used automatically.
"""

from __future__ import annotations

import ast
import dis
import inspect
import re
import textwrap
import threading
from contextlib import contextmanager
from dataclasses import dataclass

try:
    import FreeCAD as App
except ImportError:  # Unit tests run outside FreeCAD.
    App = None


AFFECTED = "affected"
NOT_AFFECTED = "not_affected"
UNKNOWN = "unknown"

_OLD_CURSOR_CALLS = frozenset(("suspendWaitCursor", "resumeWaitCursor"))
_FIXED_CURSOR_CALLS = frozenset(("suspendCursor", "resumeCursor"))
_RELEVANT_CURSOR_CALLS = _OLD_CURSOR_CALLS | _FIXED_CURSOR_CALLS
_PATCH_LOCK = threading.RLock()


@dataclass(frozen=True)
class FreeCADVersionInfo:
    major: int | None
    minor: int | None
    patch: int | None
    revision: str
    build: str
    raw: tuple[str, ...]

    @property
    def triplet(self):
        if None in (self.major, self.minor, self.patch):
            return None
        return self.major, self.minor, self.patch

    @property
    def display(self):
        if self.triplet is None:
            return ".".join(self.raw[:3]) if self.raw else "unknown"
        return "%d.%d.%d" % self.triplet


@dataclass(frozen=True)
class DxfWaitCursorAssessment:
    state: str
    reason: str
    version: FreeCADVersionInfo
    structural_calls: tuple[str, ...] = ()
    inspection_method: str = "unavailable"


@dataclass
class DxfWaitCursorSession:
    assessment: DxfWaitCursorAssessment
    applied: bool = False
    restored: bool = True


def _integer_prefix(value):
    match = re.match(r"\s*(\d+)", str(value or ""))
    return int(match.group(1)) if match else None


def freecad_version_info(app_module=None):
    """Return the native FreeCAD version fields without parsing About text."""
    module = App if app_module is None else app_module
    try:
        raw = tuple(str(value) for value in module.Version())
    except Exception:
        raw = ()
    padded = raw + ("", "", "", "", "", "")
    return FreeCADVersionInfo(
        major=_integer_prefix(padded[0]),
        minor=_integer_prefix(padded[1]),
        patch=_integer_prefix(padded[2]),
        revision=padded[3],
        build=padded[5],
        raw=raw,
    )


def _compat_log(message, warning=False, app_module=None):
    module = App if app_module is None else app_module
    line = "[FACILARQ][COMPAT] %s\n" % message
    console = getattr(module, "Console", None)
    if console is None:
        return line
    printer = getattr(console, "PrintWarning" if warning else "PrintMessage", None)
    if callable(printer):
        printer(line)
    return line


def _import_compat_log(message, app_module=None):
    module = App if app_module is None else app_module
    line = "[FACILARQ][IMPORT] %s\n" % message
    console = getattr(module, "Console", None)
    printer = getattr(console, "PrintMessage", None) if console is not None else None
    if callable(printer):
        printer(line)
    return line


def _cursor_calls_from_ast(function):
    source = inspect.getsource(function)
    tree = ast.parse(textwrap.dedent(source))
    calls = set()
    for node in ast.walk(tree):
        target = node.func if isinstance(node, ast.Call) else None
        if not isinstance(target, ast.Attribute):
            continue
        if target.attr not in _RELEVANT_CURSOR_CALLS:
            continue
        calls.add(target.attr)
    return frozenset(calls)


def _cursor_calls_from_bytecode(function):
    calls = {
        str(instruction.argval)
        for instruction in dis.get_instructions(function)
        if instruction.opname in ("LOAD_ATTR", "LOAD_METHOD")
        and instruction.argval in _RELEVANT_CURSOR_CALLS
    }
    return frozenset(calls)


def _inspect_importer_cursor_pattern(import_dxf_module):
    function = getattr(import_dxf_module, "_import_dxf_file", None)
    if not callable(function):
        return None, "unavailable", "importDXF._import_dxf_file is unavailable"
    try:
        return _cursor_calls_from_ast(function), "ast", "source AST inspected"
    except Exception as ast_error:
        try:
            return _cursor_calls_from_bytecode(function), "bytecode", "bytecode inspected"
        except Exception as bytecode_error:
            return (
                None,
                "unavailable",
                "inspection failed: %s; %s" % (ast_error, bytecode_error),
            )


def detect_dxf_waitcursor_bug(app_module=None, gui_module=None, import_dxf_module=None):
    """Classify FreeCAD's installed Draft DXF WaitCursor implementation."""
    version = freecad_version_info(app_module)
    if gui_module is None:
        try:
            import FreeCADGui as gui_module
        except ImportError:
            gui_module = None
    if import_dxf_module is None:
        try:
            import importDXF as import_dxf_module
        except ImportError:
            import_dxf_module = None

    has_old_api = bool(
        gui_module is not None
        and callable(getattr(gui_module, "suspendWaitCursor", None))
        and callable(getattr(gui_module, "resumeWaitCursor", None))
    )
    native_gui_already_patched = bool(
        getattr(gui_module, "__name__", "") == "FreeCADGui"
        and has_old_api
        and not (
            inspect.isbuiltin(gui_module.suspendWaitCursor)
            and inspect.isbuiltin(gui_module.resumeWaitCursor)
        )
    )
    calls, method, detail = _inspect_importer_cursor_pattern(import_dxf_module)

    if calls is not None:
        old = _OLD_CURSOR_CALLS.intersection(calls)
        fixed = _FIXED_CURSOR_CALLS.intersection(calls)
        if old == _OLD_CURSOR_CALLS and not fixed:
            if not has_old_api:
                return DxfWaitCursorAssessment(
                    UNKNOWN,
                    "problematic importer pattern found but legacy GUI APIs are unavailable",
                    version,
                    tuple(sorted(calls)),
                    method,
                )
            if native_gui_already_patched:
                return DxfWaitCursorAssessment(
                    UNKNOWN,
                    "FreeCADGui WaitCursor APIs were already replaced externally",
                    version,
                    tuple(sorted(calls)),
                    method,
                )
            return DxfWaitCursorAssessment(
                AFFECTED,
                "problematic Draft cursor pair detected structurally (%s)" % detail,
                version,
                tuple(sorted(calls)),
                method,
            )
        if not old and (not fixed or fixed == _FIXED_CURSOR_CALLS):
            return DxfWaitCursorAssessment(
                NOT_AFFECTED,
                "problematic Draft cursor pair is absent (%s)" % detail,
                version,
                tuple(sorted(calls)),
                method,
            )
        return DxfWaitCursorAssessment(
            UNKNOWN,
            "mixed or incomplete Draft cursor pattern (%s)" % detail,
            version,
            tuple(sorted(calls)),
            method,
        )

    # FreeCAD 1.1.3 was verified A/B on the target host.  This exact fallback
    # keeps that build usable if inspect/dis are unavailable, without guessing
    # about later versions.  A structural fixed pattern always wins above.
    if version.triplet == (1, 1, 3) and has_old_api:
        return DxfWaitCursorAssessment(
            AFFECTED,
            "verified FreeCAD 1.1.3 fallback; structural inspection unavailable",
            version,
            (),
            method,
        )
    return DxfWaitCursorAssessment(
        UNKNOWN,
        "cannot classify installed Draft importer safely: %s" % detail,
        version,
        (),
        method,
    )


def needs_dxf_waitcursor_workaround(app_module=None, gui_module=None, import_dxf_module=None):
    """Return True only when the installed importer is positively affected."""
    return detect_dxf_waitcursor_bug(app_module, gui_module, import_dxf_module).state == AFFECTED


def _noop_waitcursor(*_args, **_kwargs):
    return None


@contextmanager
def dxf_waitcursor_workaround(app_module=None, gui_module=None, import_dxf_module=None):
    """Temporarily neutralize FreeCAD #31637 for one synchronous DXF import."""
    if gui_module is None:
        try:
            import FreeCADGui as gui_module
        except ImportError:
            gui_module = None
    if import_dxf_module is None:
        try:
            import importDXF as import_dxf_module
        except ImportError:
            import_dxf_module = None

    assessment = detect_dxf_waitcursor_bug(app_module, gui_module, import_dxf_module)
    version = assessment.version
    _compat_log(
        "FreeCAD version: %s | revision=%s | build=%s"
        % (version.display, version.revision or "unknown", version.build or "unknown"),
        app_module=app_module,
    )
    _compat_log(
        "DXF WaitCursor bug #31637: %s | %s"
        % (assessment.state, assessment.reason),
        warning=assessment.state == UNKNOWN,
        app_module=app_module,
    )
    session = DxfWaitCursorSession(assessment=assessment)

    if assessment.state != AFFECTED:
        if assessment.state == NOT_AFFECTED:
            _compat_log(
                "FreeCAD DXF WaitCursor fix detected; workaround disabled",
                app_module=app_module,
            )
        yield session
        return

    original_suspend = getattr(gui_module, "suspendWaitCursor", None)
    original_resume = getattr(gui_module, "resumeWaitCursor", None)
    if not callable(original_suspend) or not callable(original_resume):
        _compat_log(
            "DXF WaitCursor bug #31637: unknown | native functions are not safely replaceable",
            warning=True,
            app_module=app_module,
        )
        yield session
        return

    with _PATCH_LOCK:
        try:
            gui_module.suspendWaitCursor = _noop_waitcursor
            gui_module.resumeWaitCursor = _noop_waitcursor
            if (
                gui_module.suspendWaitCursor is not _noop_waitcursor
                or gui_module.resumeWaitCursor is not _noop_waitcursor
            ):
                raise RuntimeError("FreeCADGui WaitCursor functions are not replaceable")
        except Exception as exc:
            gui_module.suspendWaitCursor = original_suspend
            gui_module.resumeWaitCursor = original_resume
            session.restored = bool(
                gui_module.suspendWaitCursor is original_suspend
                and gui_module.resumeWaitCursor is original_resume
            )
            if not session.restored:
                raise RuntimeError("No fue posible restaurar las funciones WaitCursor de FreeCAD")
            _compat_log(
                "DXF WaitCursor bug #31637: unknown | monkeypatch rejected: %s" % exc,
                warning=True,
                app_module=app_module,
            )
            yield session
            return

        session.applied = True
        session.restored = False
        _import_compat_log(
            "Workaround #31637 aplicado temporalmente",
            app_module=app_module,
        )
        try:
            yield session
        finally:
            gui_module.suspendWaitCursor = original_suspend
            gui_module.resumeWaitCursor = original_resume
            session.restored = bool(
                gui_module.suspendWaitCursor is original_suspend
                and gui_module.resumeWaitCursor is original_resume
            )
            if not session.restored:
                raise RuntimeError("No fue posible restaurar las funciones WaitCursor de FreeCAD")
            _compat_log("Workaround #31637 restaurado", app_module=app_module)
