# -*- coding: utf-8 -*-
"""
Module: electriccr.features.plan_lifecycle
Purpose: Keep A1 documentation objects tied to the lifecycle of their authoritative device.

Main behavior:
- Observe FreeCAD App document events.
- When a PhysicalDocumentationA1 owner is deleted, remove its PLAN documentation too.
- Prefer removing the PLAN while the same FreeCAD transaction is still open so Undo/Redo
  treats owner + documentation as one semantic deletion.
- Do not modify Placement, geometry, PLAN expressions, or selection.

Important:
- This observer is part of the A1 data lifecycle, not a GUI synchronization mechanism.
- It remains installed after leaving the ElectricCR Workbench once ElectricCR is initialized.
- Direct re-entrant removal inside slotDeletedObject is avoided while a transaction is open;
  PLAN removal is queued and flushed before recompute or transaction close.
- If FreeCAD does not emit the application-wide before-close callback for a transaction,
  slotCommitTransaction performs a safe fallback cleanup in a second transaction.
- Never mutate the document while FreeCAD is performing Undo/Redo/rollback.
- Python exposes Transacting and HasPendingTransaction as boolean attributes;
  the similarly named C++ methods are not available on DocumentPy in 1.1.3.
- Validate real FreeCAD 1.1.3 Undo/Redo and multi-document behavior before declaring stable.

Version: 0.1.2
Date: 2026-09-14 07:39 America/Costa_Rica
Target: FreeCAD 1.1.3
"""

import FreeCAD as App

from . import objeto_toma_uno as device_core


_OBSERVER_ATTR = "_ElectricCRPlanLifecycleObserver"


def _log_info(message):
    try:
        App.Console.PrintMessage("[ElectricCR][PLAN Lifecycle] %s\n" % message)
    except Exception:
        pass


def _log_warning(message):
    try:
        App.Console.PrintWarning("[ElectricCR][PLAN Lifecycle] %s\n" % message)
    except Exception:
        pass


def _safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


def _document_by_name(name):
    try:
        return (App.listDocuments() or {}).get(_safe_text(name))
    except Exception:
        return None


def _is_a1_owner(candidate):
    if candidate is None:
        return False
    try:
        if not device_core.is_electriccr_device(candidate):
            return False
    except Exception:
        return False
    props = set(getattr(candidate, "PropertiesList", []) or [])
    if "RepresentationContract" not in props:
        return False
    return _safe_text(getattr(candidate, "RepresentationContract", "")) == device_core.REPRESENTATION_CONTRACT_A1


def documentation_names_for_owner(owner):
    """Return existing PLAN object names tied to one A1 owner, without mutating the document."""
    if not _is_a1_owner(owner):
        return []
    doc = getattr(owner, "Document", None)
    if doc is None:
        return []

    names = []
    seen = set()

    # Fast persistent lookup retained on the owner.
    props = set(getattr(owner, "PropertiesList", []) or [])
    if "DocumentationRepresentationName" in props:
        name = _safe_text(getattr(owner, "DocumentationRepresentationName", ""))
        if name and doc.getObject(name) is not None:
            names.append(name)
            seen.add(name)

    # Relationship lookup is the authoritative fallback while Owner is still alive.
    try:
        plan = device_core.get_plan_representation(owner)
    except Exception:
        plan = None
    name = _safe_text(getattr(plan, "Name", ""))
    if name and name not in seen and doc.getObject(name) is not None:
        names.append(name)
        seen.add(name)

    # Defensive scan in case the persistent name was stale but Owner links are still valid.
    for candidate in list(getattr(doc, "Objects", []) or []):
        if candidate is owner:
            continue
        cprops = set(getattr(candidate, "PropertiesList", []) or [])
        if not {"DocumentationOnly", "RepresentationRole", "Owner"}.issubset(cprops):
            continue
        if not bool(getattr(candidate, "DocumentationOnly", False)):
            continue
        if _safe_text(getattr(candidate, "RepresentationRole", "")) != device_core.REPRESENTATION_ROLE_PLAN:
            continue
        if getattr(candidate, "Owner", None) is not owner:
            continue
        name = _safe_text(getattr(candidate, "Name", ""))
        if name and name not in seen:
            names.append(name)
            seen.add(name)

    return names


class PlanLifecycleObserver:
    """App document observer that keeps A1 PLAN lifetime coupled to its device owner."""

    def __init__(self):
        self._pending = {}  # doc_name -> set(plan_name)
        self._processing = False

    def _queue(self, doc, names):
        doc_name = _safe_text(getattr(doc, "Name", ""))
        if not doc_name:
            return
        bucket = self._pending.setdefault(doc_name, set())
        bucket.update(name for name in names if name)

    def _discard_document(self, doc):
        doc_name = _safe_text(getattr(doc, "Name", doc))
        if doc_name:
            self._pending.pop(doc_name, None)

    def _flush_document(self, doc, open_fallback_transaction=False):
        if self._processing or doc is None:
            return []
        # FreeCAD transaction replay (Undo/Redo/rollback) already owns object
        # lifetime. Removing related objects from inside that replay can corrupt
        # the transaction stack and has produced an Access violation in 1.1.3.
        try:
            if bool(doc.Transacting):
                return []
        except Exception:
            pass
        doc_name = _safe_text(getattr(doc, "Name", ""))
        names = sorted(self._pending.pop(doc_name, set()))
        if not names:
            return []

        existing = [name for name in names if doc.getObject(name) is not None]
        if not existing:
            return []

        opened = False
        self._processing = True
        try:
            if open_fallback_transaction and not bool(doc.HasPendingTransaction):
                doc.openTransaction("ElectricCR remove PLAN with deleted device")
                opened = True

            removed = []
            for name in existing:
                if doc.getObject(name) is not None:
                    doc.removeObject(name)
                    removed.append(name)

            if opened:
                doc.commitTransaction()

            if removed:
                _log_info(
                    "removed orphan PLAN after owner deletion doc=%s plans=%s"
                    % (doc_name, ",".join(removed))
                )
            return removed
        except Exception as exc:
            if opened:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            # Keep unresolved names pending so a later callback can retry.
            self._queue(doc, existing)
            _log_warning(
                "cannot remove PLAN after owner deletion doc=%s plans=%s error=%s"
                % (doc_name, ",".join(existing), exc)
            )
            return []
        finally:
            self._processing = False

    def _flush_all_pending_in_current_transactions(self):
        for doc_name in list(self._pending):
            doc = _document_by_name(doc_name)
            if doc is None:
                self._pending.pop(doc_name, None)
                continue
            try:
                if bool(doc.Transacting):
                    continue
            except Exception:
                pass
            try:
                pending = bool(doc.HasPendingTransaction)
            except Exception:
                pending = False
            if pending:
                self._flush_document(doc, open_fallback_transaction=False)

    def slotDeletedObject(self, obj):
        """Called by FreeCAD while obj is about to be removed."""
        if self._processing or obj is None:
            return
        if not _is_a1_owner(obj):
            return

        doc = getattr(obj, "Document", None)
        if doc is None:
            return
        # Critical safety rule: during Undo/Redo/rollback FreeCAD is replaying
        # its own transaction. The matching PLAN is already part of that replay
        # when it was created/deleted in the original transaction, so do not
        # queue or remove anything here.
        try:
            if bool(doc.Transacting):
                return
        except Exception:
            pass
        names = documentation_names_for_owner(obj)
        if not names:
            return

        self._queue(doc, names)
        _log_info(
            "queued owner=%s plans=%s"
            % (_safe_text(getattr(obj, "Name", "")), ",".join(names))
        )

        # Direct scripting may delete without an undo transaction. In that case
        # there is nothing to preserve as one Undo step, so clean immediately.
        try:
            has_transaction = bool(doc.HasPendingTransaction)
        except Exception:
            has_transaction = False
        if not has_transaction:
            self._flush_document(doc, open_fallback_transaction=False)

    def slotBeforeCloseTransaction(self, abort):
        """Flush pending PLAN deletions before the current application transaction closes."""
        if bool(abort):
            # slotAbortTransaction(doc) will clear each affected document.
            return
        self._flush_all_pending_in_current_transactions()

    def slotBeforeRecomputeDocument(self, doc):
        """Std_Delete recomputes before closing its transaction.

        Drain the existing queue before expressions can read a deleted Owner.
        The shared flush guard prevents any removal during transaction replay.
        """
        self._flush_document(doc, open_fallback_transaction=False)

    def slotCommitTransaction(self, doc):
        """Fallback for transactions that did not trigger slotBeforeCloseTransaction."""
        if self._processing or doc is None:
            return
        try:
            if bool(doc.Transacting):
                return
        except Exception:
            pass
        doc_name = _safe_text(getattr(doc, "Name", ""))
        if not self._pending.get(doc_name):
            return
        self._flush_document(doc, open_fallback_transaction=True)

    def slotAbortTransaction(self, doc):
        self._discard_document(doc)

    def slotDeletedDocument(self, doc):
        self._discard_document(doc)


def install():
    """Install one process-wide App observer. Safe to call repeatedly."""
    existing = getattr(App, _OBSERVER_ATTR, None)
    if existing is not None:
        return True

    observer = PlanLifecycleObserver()
    try:
        App.addDocumentObserver(observer)
        setattr(App, _OBSERVER_ATTR, observer)
        _log_info("observer installed")
        return True
    except Exception as exc:
        _log_warning("observer install failed: %s" % exc)
        return False


def uninstall():
    """Remove the process-wide observer. Intended for development/reload diagnostics."""
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
    _log_info("observer removed")
    return True


def is_installed():
    return getattr(App, _OBSERVER_ATTR, None) is not None
