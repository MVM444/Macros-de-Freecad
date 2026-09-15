# -*- coding: utf-8 -*-
"""A1 transaction trace for FreeCAD 1.1.3; explicit invocation only.

Records native flags and observer queues without changing their decisions.
Use only disposable documents. Native exceptions invalidate the run even when
a later audit succeeds. No production files are opened or saved by this helper.
Version: 0.1.0. Date: 2026-09-14, America/Costa_Rica.
"""
import json
import os
import time
import FreeCAD as App
from ElectricCR.electriccr.features import plan_lifecycle, plan_live_sync

PATH = None
PHASE = "setup"
ORIGINALS = []


def emit(event, doc=None, **extra):
    row = {"time": time.time(), "phase": PHASE, "event": event}
    if doc is not None:
        row.update(doc=doc.Name, transacting=doc.Transacting,
                   pending=doc.HasPendingTransaction,
                   undos=list(doc.UndoNames), redos=list(doc.RedoNames))
    observer = getattr(App, "_ElectricCRPlanLifecycleObserver", None)
    row["queue"] = {k: sorted(v) for k, v in getattr(observer, "_pending", {}).items()}
    row.update(extra)
    with open(PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, default=str) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def install(path):
    global PATH
    PATH = str(path)
    for cls, names in (
        (plan_lifecycle.PlanLifecycleObserver,
         ("slotDeletedObject", "_queue", "_flush_document", "slotCommitTransaction",
          "slotAbortTransaction", "slotBeforeCloseTransaction")),
        (plan_live_sync.PlanLiveSyncObserver, ("slotChangedObject",)),
    ):
        for name in names:
            original = getattr(cls, name)
            ORIGINALS.append((cls, name, original))

            def wrapper(self, *args, _fn=original, _name=name, **kwargs):
                obj = args[0] if args else None
                doc = getattr(obj, "Document", None)
                if doc is None and hasattr(obj, "Transacting"):
                    doc = obj
                if _name == "slotChangedObject" and (
                    str(args[1]) not in ("Placement", "LinkPlacement", "ModoVisual")
                    or not plan_live_sync._is_a1_owner(obj)
                ):
                    return _fn(self, *args, **kwargs)
                details = {"object": getattr(obj, "Name", ""),
                           "args": [str(a) for a in args[1:]]}
                emit(_name + ":enter", doc, **details)
                result = _fn(self, *args, **kwargs)
                emit(_name + ":exit", doc, **details)
                return result
            setattr(cls, name, wrapper)
    # FreeCAD captures observer methods at registration.
    plan_lifecycle.uninstall()
    plan_live_sync.uninstall()
    plan_lifecycle.install()
    plan_live_sync.install()


def uninstall():
    plan_lifecycle.uninstall()
    plan_live_sync.uninstall()
    for cls, name, original in ORIGINALS:
        setattr(cls, name, original)
    ORIGINALS.clear()
    plan_lifecycle.install()
    plan_live_sync.install()
