# -*- coding: utf-8 -*-
"""
Module: electriccr.features.plan_live_sync
Purpose: Keep the A1 PLAN representation current while its authoritative Owner is edited.

Main behavior:
- Observe FreeCAD App object changes.
- When Placement of a PhysicalDocumentationA1 Owner changes, recompute only its PLAN feature.
- Keep A1 ModoVisual and MostrarModelo3D/MostrarSimboloPlano synchronized with the two ViewObjects.
- On document activation, normalize A1 PLAN ViewObject.ShowInTree=False without changing geometry.
- Preserve Device/Owner.Placement as the single spatial authority and the existing PLAN expression.
- Avoid full-document recomputes during interactive transforms.

Important:
- This module does not assign PLAN.Placement directly and does not create a second authority.
- It is intentionally narrow: only A1 Owner changes can trigger PLAN recompute.
- It never recomputes while FreeCAD is performing Undo/Redo/rollback.
- It must remain cheap enough for interactive Transform/Draft Move; do not add geometry regeneration here.
- Validate behavior in real FreeCAD 1.1.3 before declaring stable.

Version: 0.4.1
Date: 2026-09-08 14:05 America/Costa_Rica
Target: FreeCAD 1.1.3
"""

import FreeCAD as App

from . import objeto_toma_uno as device_core


_OBSERVER_ATTR = "_ElectricCRPlanLiveSyncObserver"


def _log_warning(message):
    try:
        App.Console.PrintWarning("[ElectricCR][PLAN Live] %s\n" % message)
    except Exception:
        pass


def _safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _property_name(prop):
    """Best-effort property-name extraction across FreeCAD Python wrappers."""
    if prop is None:
        return ""
    for attr in ("Name", "name"):
        try:
            value = getattr(prop, attr, None)
            if value:
                return str(value)
        except Exception:
            pass
    try:
        getter = getattr(prop, "getName", None)
        if callable(getter):
            value = getter()
            if value:
                return str(value)
    except Exception:
        pass
    try:
        text = str(prop)
    except Exception:
        return ""
    # Some wrappers stringify directly to the property name.
    return text if text and " " not in text and "<" not in text else ""


def _is_a1_owner(candidate):
    if candidate is None:
        return False
    try:
        if _safe_text(getattr(candidate, "TypeId", "")) != "App::Link":
            return False
        if not device_core.is_electriccr_device(candidate):
            return False
    except Exception:
        return False
    props = set(getattr(candidate, "PropertiesList", []) or [])
    if "RepresentationContract" not in props:
        return False
    return _safe_text(getattr(candidate, "RepresentationContract", "")) == device_core.REPRESENTATION_CONTRACT_A1


def _plan_for_owner(owner):
    try:
        plan = device_core.get_plan_representation(owner)
    except Exception:
        plan = None
    if plan is None:
        return None
    try:
        if getattr(plan, "Document", None) is not getattr(owner, "Document", None):
            return None
    except Exception:
        return None
    return plan



def _normalize_plan_tree(doc):
    try:
        from ElectricCR.ui import plan_selection
        plan_selection.normalize_plan_tree_visibility(doc)
    except Exception:
        pass


class PlanLiveSyncObserver:
    """Targeted App observer for interactive Owner -> PLAN visual refresh."""

    def __init__(self):
        self._processing = False

    def slotChangedObject(self, obj, prop):
        if self._processing or obj is None or not _is_a1_owner(obj):
            return

        doc = getattr(obj, "Document", None)
        if doc is None:
            return

        # Never intervene while FreeCAD replays transaction state.
        try:
            if bool(doc.isPerformingTransaction()):
                return
        except Exception:
            pass

        prop_name = _property_name(prop)

        # Keep historical ModoVisual coherent with separated A1 views.
        if prop_name == "ModoVisual":
            self._processing = True
            try:
                device_core.apply_visual_mode(
                    obj,
                    getattr(obj, "ModoVisual", "Ambos"),
                    update_mode_property=False,
                )
            except Exception as exc:
                _log_warning(
                    "visual mode sync failed owner=%s error=%s"
                    % (_safe_text(getattr(obj, "Name", "")), exc)
                )
            finally:
                self._processing = False
            return

        if prop_name in {"MostrarModelo3D", "MostrarSimboloPlano"}:
            self._processing = True
            try:
                device_core.set_representation_visibility(obj)
            except Exception as exc:
                _log_warning(
                    "visibility flag sync failed owner=%s prop=%s error=%s"
                    % (_safe_text(getattr(obj, "Name", "")), prop_name, exc)
                )
            finally:
                self._processing = False
            return

        # Placement is the interactive transform path. DocumentationPlaneZ also
        # participates in the PLAN expression and benefits from immediate refresh.
        if prop_name and prop_name not in {"Placement", "DocumentationPlaneZ"}:
            return

        plan = _plan_for_owner(obj)
        if plan is None:
            return

        # Ignore objects being removed/restored. `Removing` is available on
        # DocumentObjectPy in current FreeCAD; access defensively for 1.1.x.
        try:
            if bool(getattr(obj, "Removing", False)) or bool(getattr(plan, "Removing", False)):
                return
        except Exception:
            pass

        self._processing = True
        try:
            # Recompute only the lightweight PLAN feature. The native expression
            # reads the current Owner.Placement; no document-wide recompute is needed.
            plan.recompute()
        except Exception as exc:
            _log_warning(
                "targeted recompute failed owner=%s plan=%s prop=%s error=%s"
                % (
                    _safe_text(getattr(obj, "Name", "")),
                    _safe_text(getattr(plan, "Name", "")),
                    prop_name or "?",
                    exc,
                )
            )
        finally:
            self._processing = False

    def slotActivateDocument(self, doc):
        """Normalize GUI-only PLAN tree state whenever a document becomes active."""
        if doc is None:
            return
        _normalize_plan_tree(doc)



def install():
    """Install one process-wide observer. Safe to call repeatedly."""
    existing = getattr(App, _OBSERVER_ATTR, None)
    if existing is not None:
        return True
    observer = PlanLiveSyncObserver()
    try:
        App.addDocumentObserver(observer)
        setattr(App, _OBSERVER_ATTR, observer)
        return True
    except Exception as exc:
        _log_warning("observer install failed: %s" % exc)
        return False


def uninstall():
    """Remove the observer. Intended for development/reload diagnostics."""
    observer = getattr(App, _OBSERVER_ATTR, None)
    if observer is None:
        return True
    try:
        App.removeDocumentObserver(observer)
    except Exception as exc:
        _log_warning("observer remove failed: %s" % exc)
        return False
    try:
        delattr(App, _OBSERVER_ATTR)
    except Exception:
        try:
            setattr(App, _OBSERVER_ATTR, None)
        except Exception:
            pass
    return True


def is_installed():
    return getattr(App, _OBSERVER_ATTR, None) is not None
