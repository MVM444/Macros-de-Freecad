"""Controlled A1 workbench-switch regression in the real FreeCAD 1.1.3 GUI.

Revision: 2026-09-08 17:35 America/Costa_Rica.
Import this module in FreeCAD and construct RuntimeRegression(source, work_dir).
Only its verified temporary copy is modified. Methods are separate so native
selection/Delete/Undo/Redo can be observed between steps. No repair is run.
The existing ElectricCR workbench must be initialized normally before use.
"""
import datetime
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Draft
from PySide2 import QtWidgets
from ElectricCR.electriccr.features import objeto_toma_uno as core
from ElectricCR.electriccr.semantic.freecad_adapter import ensure_device_semantics

_spec = importlib.util.spec_from_file_location(
    'a1_runtime_audit', str(Path(__file__).with_name('freecad_a1_runtime_audit.py')))
_audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_audit)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class RuntimeRegression:
    def __init__(self, source, work_dir):
        assert App.Version()[:3] == ['1','1','3'], App.Version()
        self.source = Path(source).resolve()
        self.work = Path(work_dir).resolve()
        self.work.mkdir(parents=True, exist_ok=True)
        self.copy = self.work / 'A1_workbench_regression.FCStd'
        assert self.source != self.copy and not self.copy.exists()
        self.source_hash = digest(self.source)
        shutil.copy2(self.source, self.copy)
        assert digest(self.copy) == self.source_hash
        self.owner_name = 'ECR_A1_RuntimeProbe'
        self.plan_name = None
        self.uid = None
        self.report_widget = next((w for w in Gui.getMainWindow().findChildren(QtWidgets.QWidget)
                                   if w.objectName()=='Report view' and hasattr(w,'toPlainText')), None)
        self.console_start = len(self.report_widget.toPlainText()) if self.report_widget else 0
        self.results = {'started':datetime.datetime.now().astimezone().isoformat(),
                        'version':App.Version(), 'source':str(self.source),
                        'source_sha256':self.source_hash, 'copy':str(self.copy), 'stages':[]}
        Gui.getMainWindow().statusBar().showMessage('A1 regression: opening verified temporary copy; please wait...')
        Gui.updateGui()
        self.doc = App.openDocument(str(self.copy))
        self.doc.UndoMode = 1
        self.ids = self.observer_ids()
        assert all(self.ids.values())
        initial = self.record('initial')
        self.original_owners = {o['name']:o for o in initial['owners']}
        self.initial_counts = (initial['owner_count'], initial['plan_count'])
        self.doc.recompute()
        self.record('initial_recompute')

    def observer_ids(self):
        return {name:id(getattr(api,name)) if getattr(api,name,None) is not None else None
                for api,name in ((App,'_ElectricCRPlanLifecycleObserver'),
                                 (App,'_ElectricCRPlanLiveSyncObserver'),
                                 (Gui,'_ElectricCRPlanSelectionRedirector'))}

    def record(self, stage, **extra):
        Gui.updateGui()
        report = _audit.audit(self.doc)
        row = {'stage':stage,'workbench':Gui.activeWorkbench().name(),
               'owners':report['owner_count'],'plans':report['plan_count'],
               'errors':report['errors'],'undo':self.doc.UndoCount,'redo':self.doc.RedoCount,
               'observers':self.observer_ids(), **extra}
        self.results['stages'].append(row)
        (self.work/(stage+'.json')).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        self.results['source_unchanged'] = digest(self.source)==self.source_hash
        if self.report_widget:
            (self.work/'console.txt').write_text(self.report_widget.toPlainText()[self.console_start:],encoding='utf-8')
        (self.work/'results.json').write_text(json.dumps(self.results,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps(row))
        assert self.results['source_unchanged'], 'Source file changed'
        assert report['ok'], row
        assert self.observer_ids()==self.ids, 'Runtime singleton changed'
        return report

    def pair(self):
        owner = self.doc.getObject(self.owner_name)
        plan = self.doc.getObject(self.plan_name) if self.plan_name else None
        assert owner is not None and plan is not None
        assert owner.ElementUID==self.uid and plan.Owner is owner
        assert owner.DocumentationRepresentationName==plan.Name
        assert _audit.follows(owner,plan)
        return owner,plan

    def create(self):
        assert self.doc.getObject(self.owner_name) is None and self.plan_name is None
        self.doc.openTransaction('A1 regression create one device')
        try:
            owner = core.crear_toma_link(doc=self.doc,name_prefix='A1 runtime regression',
                key_registro='Apagador_Simple',tipo_logico='Apagador',
                internal_name=self.owner_name,altura_rel=1200.0,
                placement=App.Placement(App.Vector(22000,12000,0),App.Rotation()),
                separate_documentation=True,recompute=False)
            ensure_device_semantics(owner,dry_run=False,manage_transaction=False)
            core.sync_plan_representation(owner,dry_run=False,manage_transaction=False)
            self.doc.recompute()
            self.doc.commitTransaction()
        except Exception:
            self.doc.abortTransaction()
            raise
        self.uid=owner.ElementUID
        self.plan_name=owner.DocumentationRepresentationName
        self.pair()
        report=self.record('created')
        assert (report['owner_count'],report['plan_count'])==tuple(n+1 for n in self.initial_counts)

    def switch_select(self, workbench, stage):
        Gui.activateWorkbench(workbench)
        owner,plan=self.pair()
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(self.doc.Name,plan.Name,'Edge1')
        assert Gui.Selection.getSelection()==[owner], [o.Name for o in Gui.Selection.getSelection()]
        self.record(stage,selection=[o.Name for o in Gui.Selection.getSelection()])

    def move(self, stage, dx=125.0, dy=75.0, angle=25.0):
        owner,plan=self.pair()
        before=App.Placement(owner.Placement)
        assert Gui.Selection.getSelection()==[owner]
        self.doc.openTransaction('A1 regression native Draft move and rotate')
        try:
            Draft.move(Gui.Selection.getSelection(),App.Vector(dx,dy,0),copy=False)
            Draft.rotate([owner],angle,center=App.Vector(owner.Placement.Base),
                         axis=App.Vector(0,0,1),copy=False)
            # No sync, cleanup or document recompute can conceal missing live sync.
            assert _audit.follows(owner,plan)
            assert abs(owner.Placement.Base.x-before.Base.x-dx)<1e-6
            assert abs(owner.Placement.Base.y-before.Base.y-dy)<1e-6
            self.doc.commitTransaction()
        except Exception:
            self.doc.abortTransaction()
            raise
        self.record(stage,live_follow=True,native_operations=['Draft.move','Draft.rotate'])

    def delete(self, stage):
        owner,plan=self.pair()
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(self.doc.Name,plan.Name,'Edge1')
        assert Gui.Selection.getSelection()==[owner]
        Gui.runCommand('Std_Delete')
        assert self.doc.getObject(self.owner_name) is None
        assert self.doc.getObject(self.plan_name) is None
        self.doc.recompute()
        self.record(stage)

    def undo_delete(self, stage):
        Gui.runCommand('Std_Undo')
        self.doc.recompute()
        self.pair()
        self.record(stage)

    def redo_delete(self, stage):
        Gui.runCommand('Std_Redo')
        self.doc.recompute()
        assert self.doc.getObject(self.owner_name) is None
        assert self.doc.getObject(self.plan_name) is None
        self.record(stage)

    def save_reopen(self, stage, pair_expected):
        self.doc.recompute()
        self.doc.save()
        Gui.Selection.clearSelection()
        App.closeDocument(self.doc.Name)
        self.doc=App.openDocument(str(self.copy))
        self.doc.UndoMode=1
        self.doc.recompute()
        if pair_expected:
            self.pair()
        else:
            assert self.doc.getObject(self.owner_name) is None
            assert self.doc.getObject(self.plan_name) is None
        self.record(stage)

    def finish(self):
        report=self.record('final')
        assert (report['owner_count'],report['plan_count'])==self.initial_counts
        # Native reads/evalExpression may mark Link dependencies Touched. Compare
        # identity, geometry and links; audit separately rejects Invalid/Error.
        def stable(row):
            return {k:v for k,v in row.items() if k not in ('State','status')}
        assert {o['name']:stable(o) for o in report['owners']}=={
            name:stable(o) for name,o in self.original_owners.items()
        }, 'Existing owner data changed'
        self.results['existing_owner_data_unchanged']=True
        self.results['final_touched_objects']=report['touched_objects']
        self.results['completed']=datetime.datetime.now().astimezone().isoformat()
        self.results['passed']=True
        (self.work/'results.json').write_text(json.dumps(self.results,indent=2,ensure_ascii=False),encoding='utf-8')
        Gui.Selection.clearSelection()
        App.closeDocument(self.doc.Name)
        print('A1_RUNTIME_REGRESSION_PASSED',str(self.work/'results.json'))
