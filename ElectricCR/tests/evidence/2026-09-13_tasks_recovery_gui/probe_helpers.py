# Test evidence helpers; execute only in the recorded FreeCAD probe namespace.

def doc_state():
    docs={}
    for d in App.listDocuments().values():
        objects=[]
        for o in d.Objects:
            attrs={n:str(getattr(o,n)) for n in ('Placement','Length','Width','Height','Radius','Geometry','Constraints') if n in o.PropertiesList}
            objects.append({'name':o.Name,'type':o.TypeId,'attrs':attrs,'state':list(o.State)})
        docs[d.Name]={'file':d.FileName,'objects':objects}
    return docs

def ui_state():
    mw=Gui.getMainWindow()
    docks=[{'name':d.objectName(),'visible':d.isVisible(),'geometry':d.geometry().getRect()} for d in mw.findChildren(QtWidgets.QDockWidget)]
    edits={d.Name:str(Gui.getDocument(d.Name).getInEdit()) for d in App.listDocuments().values()}
    return {'document':App.ActiveDocument.Name if App.ActiveDocument else None,'dialog':bool(Gui.Control.activeDialog()),'central':mw.centralWidget().geometry().getRect(),'docks':docks,'widgets':len(mw.findChildren(QtWidgets.QWidget)),'edit':edits,'selection':[(o.Document.Name,o.Name) for o in Gui.Selection.getSelection()],'cameras':{d.Name:Gui.getDocument(d.Name).activeView().getCamera() for d in App.listDocuments().values()}}

def save_report(name):
    report=Gui.getMainWindow().findChild(QtWidgets.QTextEdit,'Report view')
    if report: open(os.path.join(p['evidence'],name),'w',encoding='utf-8').write(report.toPlainText())

def run(label, button=False):
    before=ui_state(); docs=doc_state()
    if button:
        bar=[t for t in Gui.getMainWindow().findChildren(QtWidgets.QToolBar) if t.objectName()=='Programacion'][0]
        action=[a for a in bar.actions() if a.text()=='Recuperar Tasks'][0]
        action.trigger()
        result=None
    else:
        filename=os.path.join(p['folder'],'RecuperarPanelTareas.FCMacro')
        ns={'__file__':filename,'__name__':'__main__'}
        exec(compile(open(filename,encoding='utf-8-sig').read(),filename,'exec'),ns,ns)
        p['recovery_ns']=ns
        result=ns['TASK_RECOVERY_LAST_RESULT']
    Gui.updateGui()
    after=ui_state()
    record={'label':label,'button':button,'before':before,'after':after,'documents_unchanged':docs==doc_state(),'macro_result':result}
    checks={'documents':record['documents_unchanged'],'active_document':before['document']==after['document'],'task':before['dialog']==after['dialog'],'edit':before['edit']==after['edit'],'selection':before['selection']==after['selection'],'camera':before['cameras']==after['cameras'],'dock_count':len(before['docks'])==len(after['docks'])}
    record['checks']=checks
    p['runs'].append(record)
    open(os.path.join(p['evidence'],'runs.json'),'w',encoding='utf-8').write(json.dumps(p['runs'],indent=2))
    save_report('console.txt')
    print(json.dumps({'label':label,'checks':checks,'geometry':[before['central'],after['central']],'widgets':[before['widgets'],after['widgets']],'macro_diff':result['changes'] if result else None}))
    assert all(checks.values()), 'Recovery regression: '+str(checks)
    if not button: assert result is not None, 'Macro returned None'
    return record
