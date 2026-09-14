# -*- coding: utf-8 -*-
"""Explicit staged A1 regression in real FreeCAD 1.1.3.

New disposable demo only. Verify undo stack entries, replay and rollback, plus
native console errors after returning to the Qt event loop. A post-crash audit
is never sufficient for PASS. Does not quit FreeCAD or open production files.
Version: 0.1.0. Date: 2026-09-14 07:39 America/Costa_Rica.
"""
import copy
import json
import os
import tempfile
import traceback
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets
from ElectricCR.electriccr.demo.electric_demo_freecad import create_fixed_demo
from ElectricCR.electriccr.demo.electric_demo_audit import audit_demo
from ElectricCR.electriccr.demo.electric_demo_core import build_fixed_demo_spec

STATE = {}


def document():
    return App.getDocument(STATE['document'])


def audit(spec=None):
    report = audit_demo(document(), spec)
    assert report['status'] == 'PASS', report
    for obj in document().Objects:
        assert 'Invalid' not in obj.State, (obj.Name, obj.State)
        if getattr(obj, 'RepresentationRole', '') == 'PLAN':
            assert obj.TypeId == 'Part::Feature'
            assert not obj.ViewObject.ShowInTree
            assert obj.getTypeIdOfProperty('Owner') == 'App::PropertyLinkHidden'
            assert len(obj.SnapPoints) == 1
    return report['counts']


def setup(evidence):
    assert list(App.Version()[:3]) == ['1', '1', '3']
    assert not App.listDocuments(), 'Use an isolated empty session'
    STATE.update(evidence=str(evidence), stages=[], temp=tempfile.mkdtemp(prefix='electriccr_a1_undo_'))
    App.Console.PrintMessage('[A1 REGRESSION BEGIN] La demo puede tardar varios segundos.\n')
    Gui.updateGui()
    result = create_fixed_demo()
    STATE['document'] = result['document'].Name
    STATE['owner'] = result['owners']['outlet-office-01'].Name
    STATE['plan'] = result['owners']['outlet-office-01'].DocumentationRepresentationName
    STATE['object_count'] = len(document().Objects)
    assert document().UndoNames == ['ElectricCR: crear demo A1'], document().UndoNames
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
    return {'counts': audit(), 'undos': document().UndoNames}


def move(workbench='ElectricCRWorkbench'):
    Gui.activateWorkbench(workbench)
    d = document()
    o = d.getObject(STATE['owner'])
    plan = d.getObject(STATE['plan'])
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(plan)
    assert Gui.Selection.getSelection() == [o], 'PLAN must select only Owner'
    original = App.Placement(o.Placement)
    names = list(d.UndoNames)
    title = 'A1 regression move ' + workbench
    d.openTransaction(title)
    moved = App.Placement(original)
    moved.Base += App.Vector(250, 125, 0)
    moved.Rotation = App.Rotation(App.Vector(0, 0, 1), 15).multiply(original.Rotation)
    o.Placement = moved
    assert d.HasPendingTransaction and not d.Transacting
    d.commitTransaction()
    d.recompute()
    assert d.UndoNames == [title] + names, d.UndoNames
    spec = copy.deepcopy(build_fixed_demo_spec())
    item = next(x for x in spec['devices'] if x['internal_name'] == o.Name)
    item['placement']['x'] += 250
    item['placement']['y'] += 125
    item['placement']['yaw_deg'] += 15
    audit(spec)
    Gui.runCommand('Std_Undo'); d.recompute()
    assert d.UndoNames == names
    audit()
    Gui.runCommand('Std_Redo'); d.recompute()
    audit(spec)
    Gui.runCommand('Std_Undo'); d.recompute()
    return {'workbench': workbench, 'counts': audit(), 'independent_undo': True}


def delete_pair():
    d = document()
    names = list(d.UndoNames)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(d.getObject(STATE['owner']))
    Gui.runCommand('Std_Delete')
    assert all(d.getObject(STATE[k]) is None for k in ('owner', 'plan'))
    assert len(d.UndoNames) == len(names) + 1, d.UndoNames
    deleted_names = list(d.UndoNames)
    assert len(d.Objects) == STATE['object_count'] - 2
    Gui.runCommand('Std_Undo'); d.recompute(); audit()
    Gui.runCommand('Std_Redo'); d.recompute()
    assert all(d.getObject(STATE[k]) is None for k in ('owner', 'plan'))
    assert len(d.Objects) == STATE['object_count'] - 2
    Gui.runCommand('Std_Undo'); d.recompute()
    return {'counts': audit(), 'delete_undo_names': deleted_names}


def replay_creation():
    d = document()
    assert d.UndoNames == ['ElectricCR: crear demo A1'], d.UndoNames
    Gui.Selection.clearSelection()
    Gui.runCommand('Std_Undo')
    assert len(d.Objects) == 0 and d.UndoCount == 0
    Gui.runCommand('Std_Redo'); d.recompute()
    return {'empty_after_undo': True, 'restored': audit()}


def rollback():
    d = document()
    names = list(d.UndoNames)
    d.openTransaction('A1 rollback delete')
    d.removeObject(STATE['owner'])
    pending = copy.deepcopy(getattr(App, '_ElectricCRPlanLifecycleObserver')._pending)
    assert STATE['plan'] in pending[d.Name]
    d.abortTransaction(); d.recompute()
    assert not getattr(App, '_ElectricCRPlanLifecycleObserver')._pending
    assert d.UndoNames == names
    audit()
    d.openTransaction('A1 rollback new object')
    d.addObject('App::FeaturePython', 'RollbackOnly')
    d.abortTransaction()
    assert d.getObject('RollbackOnly') is None
    return {'queued_before_abort': {k: sorted(v) for k, v in pending.items()}, 'counts': audit()}


def save_reopen():
    d = document()
    audit()
    filename = os.path.join(STATE['temp'], 'ElectricCR_A1_Regression.FCStd')
    d.recompute(); d.saveAs(filename)
    App.closeDocument(d.Name)
    d = App.openDocument(filename)
    STATE['document'] = d.Name
    d.recompute()
    return {'file': filename, 'counts': audit()}


def stage(name, function, *args):
    probe = getattr(App, '_a1_probe', None)
    if probe:
        probe.PHASE = name
    try:
        result = function(*args)
        record = {'stage': name, 'status': 'PASS', 'result': result}
    except Exception:
        record = {'stage': name, 'status': 'FAIL', 'traceback': traceback.format_exc()}
    STATE.setdefault('stages', []).append(record)
    with open(os.path.join(STATE['evidence'], 'regression.json'), 'w', encoding='utf-8') as handle:
        json.dump(STATE, handle, indent=2)
    print(json.dumps(record))
    assert record['status'] == 'PASS', record
    return record


def console_check():
    # Call in a later RPC turn: native exception messages can reach Report View
    # only after the previous GUI callback returns.
    text = Gui.getMainWindow().findChild(QtWidgets.QTextEdit, 'Report view').toPlainText()
    assert '[A1 REGRESSION BEGIN]' in text, 'Run marker missing from Report View'
    text = text.rsplit('[A1 REGRESSION BEGIN]', 1)[-1]
    with open(os.path.join(STATE['evidence'], 'after_console.txt'), 'w', encoding='utf-8') as handle:
        handle.write(text)
    bad = [line for line in text.splitlines() if any(token in line.lower() for token in
           ('access violation', 'exception on undo', 'unknown opcode', "no attribute named", 'traceback', 'error', 'failed'))]
    assert not bad, bad
    return {'native_errors': bad}
