# -*- coding: utf-8 -*-
"""
Module: electriccr.ui.plan_selection
Purpose: Redirect A1 PLAN selection to its authoritative Owner without persistent overlays.

Main behavior:
- Observe FreeCAD GUI selection only for ElectricCR A1 PLAN objects.
- If PLAN or one of its subelements is clicked, remove that PLAN selection and select only Owner/App::Link.
- Keep PLAN hidden from the model tree with ViewObject.ShowInTree=False when supported.
- Do not create Coin/Draft overlays and do not force persistent preselection.

Important for future modifications:
- Device/Owner remains the only logical selection and spatial authority.
- PLAN remains documentation only; do not add a second Placement, identity, snap system, or grip system.
- FreeCAD 1.1.3 preselection is transient and must not be used as persistent selected feedback.
- Draft ghostTracker was tested as persistent feedback and rejected after real tests produced stale graphics
  and Access violation errors during move/delete/reopen workflows.
- Keep this module GUI-only and independent from PLAN geometry generation.
- Once initialized, keep the redirector installed across workbench changes.
- Repeated install() calls preserve the singleton; uninstall() is explicit maintenance only.
- Verify multi-document behavior and Workbench switching in real FreeCAD 1.1.3.

Version: 0.4.1
Date: 2026-09-08 14:05 America/Costa_Rica
Target: FreeCAD 1.1.3
"""

import FreeCAD as App

try:
    import FreeCADGui as Gui
except Exception:
    Gui = None


_OBSERVER_ATTR = "_ElectricCRPlanSelectionRedirector"


def _log_info(message):
    try:
        App.Console.PrintMessage("[ElectricCR][PLAN Select] %s\n" % message)
    except Exception:
        pass


def _log_warning(message):
    try:
        App.Console.PrintWarning("[ElectricCR][PLAN Select] %s\n" % message)
    except Exception:
        pass


def _document_by_name(name):
    try:
        return (App.listDocuments() or {}).get(str(name or ""))
    except Exception:
        return None


def _is_a1_owner(candidate):
    if candidate is None:
        return False
    try:
        if str(getattr(candidate, "TypeId", "") or "") != "App::Link":
            return False
        props = set(getattr(candidate, "PropertiesList", []) or [])
        if "RepresentationContract" not in props:
            return False
        return str(getattr(candidate, "RepresentationContract", "") or "") == "PhysicalDocumentationA1"
    except Exception:
        return False


def _is_a1_plan(candidate):
    """Return True only for an owned ElectricCR A1 PLAN documentation object."""
    if candidate is None:
        return False
    try:
        props = set(getattr(candidate, "PropertiesList", []) or [])
        required = {"DocumentationOnly", "RepresentationRole", "Owner"}
        if not required.issubset(props):
            return False
        if not bool(getattr(candidate, "DocumentationOnly", False)):
            return False
        if str(getattr(candidate, "RepresentationRole", "") or "") != "PLAN":
            return False
        owner = getattr(candidate, "Owner", None)
        if not _is_a1_owner(owner):
            return False
        return getattr(candidate, "Document", None) is getattr(owner, "Document", None)
    except Exception:
        return False


def selection_owner(candidate):
    """Resolve the authoritative device selected through an A1 PLAN object."""
    if not _is_a1_plan(candidate):
        return None
    return getattr(candidate, "Owner", None)


def normalize_plan_tree_visibility(doc=None):
    """Hide A1 PLAN helpers from the model tree without changing viewport visibility."""
    if Gui is None:
        return 0
    docs = [doc] if doc is not None else list((App.listDocuments() or {}).values())
    changed = 0
    for current_doc in docs:
        if current_doc is None:
            continue
        for obj in list(getattr(current_doc, "Objects", []) or []):
            if not _is_a1_plan(obj):
                continue
            try:
                if bool(obj.ViewObject.ShowInTree):
                    obj.ViewObject.ShowInTree = False
                    changed += 1
            except Exception:
                pass
    return changed


class PlanSelectionRedirector:
    """Small GUI observer that replaces PLAN selection with Owner selection."""

    def __init__(self):
        self._redirecting = False

    def addSelection(self, doc_name, obj_name, sub_name, point):
        if self._redirecting or Gui is None:
            return
        doc = _document_by_name(doc_name)
        if doc is None:
            return
        candidate = doc.getObject(str(obj_name or ""))
        owner = selection_owner(candidate)
        if owner is None or getattr(owner, "Document", None) is not doc:
            return

        self._redirecting = True
        try:
            try:
                Gui.Selection.removeSelection(
                    str(doc_name or ""),
                    str(obj_name or ""),
                    str(sub_name or ""),
                )
            except Exception as exc:
                _log_warning(
                    "cannot remove PLAN selection %s.%s: %s"
                    % (obj_name, sub_name or "", exc)
                )
                return

            Gui.Selection.addSelection(owner)
            _log_info(
                "redirected %s%s -> %s; feedback=native-owner-only"
                % (
                    getattr(candidate, "Name", obj_name),
                    (".%s" % sub_name) if sub_name else "",
                    getattr(owner, "Name", ""),
                )
            )
        except Exception as exc:
            _log_warning("redirect failed for %s: %s" % (obj_name, exc))
        finally:
            self._redirecting = False

    # Intentionally no persistent hover/selection feedback hooks.
    def removeSelection(self, doc_name, obj_name, sub_name):
        return

    def setPreselection(self, doc_name, obj_name, sub_name):
        return

    def clearSelection(self, doc_name):
        return


def install():
    """Install exactly one redirector instance for the current GUI process."""
    if Gui is None:
        return False
    existing = getattr(Gui, _OBSERVER_ATTR, None)
    if existing is not None:
        # Activation can repeat many times. Do not detach/recreate the runtime
        # observer; development reloads must explicitly uninstall it first.
        normalize_plan_tree_visibility()
        return True

    observer = PlanSelectionRedirector()
    try:
        Gui.Selection.addObserver(observer)
        setattr(Gui, _OBSERVER_ATTR, observer)
        normalize_plan_tree_visibility()
        _log_info("observer installed (safe redirect-only mode)")
        return True
    except Exception as exc:
        _log_warning("observer install failed: %s" % exc)
        return False


def uninstall():
    """Explicit development/maintenance teardown, never workbench deactivation."""
    if Gui is None:
        return False
    observer = getattr(Gui, _OBSERVER_ATTR, None)
    if observer is None:
        return True
    try:
        Gui.Selection.removeObserver(observer)
    except Exception as exc:
        _log_warning("observer remove failed: %s" % exc)
        return False
    try:
        delattr(Gui, _OBSERVER_ATTR)
    except Exception:
        try:
            setattr(Gui, _OBSERVER_ATTR, None)
        except Exception:
            pass
    _log_info("observer removed")
    return True


def is_installed():
    return bool(Gui is not None and getattr(Gui, _OBSERVER_ATTR, None) is not None)
