"""Disposable NativeIFC experiment; FreeCAD 1.1.3 GUI, 2026-09-09.

Creates exactly four new IfcElement occurrences and generic IFC geometry.
No A1 imports, conversion of existing objects, ports, or production models.
Use a fresh temporary output directory. Invoke phases separately for inspection.
"""
from pathlib import Path
import datetime
import json
import hashlib
import numpy as np
import FreeCAD as App
import FreeCADGui as Gui
import ifcopenshell
import ifcopenshell.util.attribute
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.pset
from nativeifc import ifc_tools, ifc_psets
from PySide import QtWidgets


class NativeIfcProbe:
    def __init__(self, output_dir):
        assert App.Version()[:3] == ['1', '1', '3']
        self.work=Path(output_dir).resolve()
        self.work.mkdir(parents=True,exist_ok=False)
        self.fcstd=self.work/'NativeIFC_four_elements.FCStd'
        self.ifc=self.work/'NativeIFC_four_elements.ifc'
        self.original_documents=list(App.listDocuments())
        self.doc=App.newDocument('NativeIFC_four_elements')
        self.doc.UndoMode=1
        self.console=next((w for w in Gui.getMainWindow().findChildren(QtWidgets.QWidget)
                           if w.objectName()=='Report view' and hasattr(w,'toPlainText')),None)
        self.offset=len(self.console.toPlainText()) if self.console else 0
        self.results={'started':datetime.datetime.now().astimezone().isoformat(),
                      'FreeCAD':App.Version(),'IfcOpenShell':ifcopenshell.version,
                      'output':str(self.work),'stages':[],'exactly_four_occurrences':True,
                      'Type_experiment':'No Type entities or extra occurrences created; sharing investigated in native source/documentation.'}

    def announce(self,text):
        App.Console.PrintMessage('[NativeIFC probe] '+text+'\n')
        Gui.getMainWindow().statusBar().showMessage('NativeIFC experiment: '+text+' ...')
        Gui.updateGui()

    def create(self):
        self.announce('creating four generic IFC elements; this may take several seconds')
        self.project=ifc_tools.create_document_object(self.doc,shapemode=0,strategy=0,silent=True)
        self.file=ifc_tools.get_ifcfile(self.project)
        self.schema=self.file.schema_identifier
        schema=ifcopenshell.ifcopenshell_wrapper.schema_by_name(self.schema)
        board='IfcDistributionBoard' if self.schema.startswith('IFC4X3') else 'IfcElectricDistributionBoard'
        schema.declaration_by_name(board)
        self.classes=['IfcOutlet','IfcSwitchingDevice','IfcLightFixture',board]
        self.results.update(schema=self.schema,board_class=board)
        self.entities=[]
        body=self.file.by_id(ifc_tools.get_body_context_ids(self.file)[0])
        specs=[('POWEROUTLET',(0.08,0.04,0.12)),('TOGGLESWITCH',(0.08,0.04,0.12)),
               ('POINTSOURCE',(0.30,0.30,0.08)),('DISTRIBUTIONBOARD',(0.40,0.18,0.60))]
        self.doc.openTransaction('Disposable NativeIFC four elements')
        try:
            for i,(cls,(predefined,(x,y,z))) in enumerate(zip(self.classes,specs)):
                ent=ifc_tools.api_run('root.create_entity',self.file,ifc_class=cls,
                                     predefined_type=predefined,name='Probe '+cls[3:])
                verts=[(0,0,0),(x,0,0),(x,y,0),(0,y,0),(0,0,z),(x,0,z),(x,y,z),(0,y,z)]
                faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
                rep=ifc_tools.api_run('geometry.add_mesh_representation',self.file,context=body,
                                     vertices=[verts],faces=[faces])
                ifc_tools.api_run('geometry.assign_representation',self.file,product=ent,representation=rep)
                mat=np.eye(4); mat[0,3]=i*0.8
                ifc_tools.api_run('geometry.edit_object_placement',self.file,product=ent,matrix=mat,is_si=True)
                self.entities.append(ent)
            ifc_tools.api_run('aggregate.assign_object',self.file,products=self.entities,
                             relating_object=self.file.by_type('IfcProject')[0])
            self.objects=[ifc_tools.create_object(e,self.doc,self.file,shapemode=0) for e in self.entities]
            self.project.Group=self.objects
            self.doc.recompute()
            self.doc.commitTransaction()
        except Exception:
            self.doc.abortTransaction()
            raise
        assert len(self.file.by_type('IfcElement'))==4
        self.ids=[o.GlobalId for o in self.objects]
        self.record('created')
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
        Gui.activeDocument().activeView().saveImage(str(self.work/'created.png'),1280,900,'Current')

    def inventory(self):
        f=ifc_tools.get_ifcfile(self.project)
        pschema='IFC4X3' if f.schema.startswith('IFC4X3') else f.schema
        templates=ifcopenshell.util.pset.PsetQto(pschema)
        rows=[]
        for obj in self.objects:
            ent=ifc_tools.get_ifc_element(obj,f)
            attrs=ent.wrapped_data.declaration().as_entity().all_attributes()
            attr=next(a for a in attrs if a.name()=='PredefinedType')
            choices=ifcopenshell.util.attribute.get_enum_items(attr)
            typ=ifcopenshell.util.element.get_type(ent)
            row={'name':obj.Name,'label':obj.Label,'schema':f.schema_identifier,'TypeId':obj.TypeId,
                 'Class':str(obj.Class),'IfcClass':obj.IfcClass,'GlobalId':obj.GlobalId,'StepId':obj.StepId,
                 'PredefinedType':str(obj.PredefinedType),'PredefinedType_choices':choices,
                 'Type':getattr(getattr(obj,'Type',None),'Name',None),'Type_property':obj.getTypeIdOfProperty('Type'),
                 'IFC_Type':typ.get_info() if typ else None,
                 'Placement':{'base_mm':list(obj.Placement.Base),'rotation_q':list(obj.Placement.Rotation.Q)},
                 'IFC_Placement_matrix':ifcopenshell.util.placement.get_local_placement(ent.ObjectPlacement).tolist(),
                 'Description':getattr(obj,'Description',None),'ObjectType':getattr(obj,'ObjectType',None),
                 'attached_psets':ifcopenshell.util.element.get_psets(ent),
                 'applicable_pset_templates':templates.get_applicable_names(ent.is_a(),ent.PredefinedType or '',pset_only=True),
                 'property_groups':{p:obj.getGroupOfProperty(p) for p in obj.PropertiesList},
                 'editor_modes':{p:obj.getEditorMode(p) for p in ('Class','IfcClass','GlobalId','StepId','PredefinedType','Placement','Type')},
                 'ShapeMode':str(obj.ShapeMode),'shape_null':obj.Shape.isNull(),
                 'shape_volume_mm3':obj.Shape.Volume,'solids':len(obj.Shape.Solids),
                 'State':list(obj.State),'status':obj.getStatusString()}
            assert row['GlobalId']==ent.GlobalId and row['StepId']==ent.id()
            rows.append(row)
        return rows

    def record(self,stage,**extra):
        rows=self.inventory()
        row={'stage':stage,'timestamp':datetime.datetime.now().astimezone().isoformat(),
             'ifc_elements':len(ifc_tools.get_ifcfile(self.project).by_type('IfcElement')),
             'freecad_objects':len(self.doc.Objects),'objects':rows,**extra}
        assert row['ifc_elements']==4 and len(rows)==4
        assert len({r['GlobalId'] for r in rows})==4
        assert not any('Invalid' in r['State'] or 'Error' in r['State'] for r in rows)
        self.results['stages'].append(row)
        (self.work/'results.json').write_text(json.dumps(self.results,indent=2,ensure_ascii=False),encoding='utf-8')
        if self.console:
            (self.work/'console.txt').write_text(self.console.toPlainText()[self.offset:],encoding='utf-8')
        print(json.dumps({'stage':stage,'schema':self.schema,'count':len(rows),
                          'objects':[{k:r[k] for k in ('Class','TypeId','GlobalId','StepId','PredefinedType','Type','shape_null')} for r in rows]}))
        return rows

    def edit(self):
        self.announce('editing native properties, Placement and a simple attached Pset')
        before=self.results['stages'][0]['objects']
        self.doc.openTransaction('Disposable NativeIFC edits')
        try:
            for i,obj in enumerate(self.objects):
                obj.Label += ' edited'
                obj.Description='Disposable NativeIFC property edit'
                obj.PredefinedType='USERDEFINED'
                obj.ObjectType='ProbeDevice'
                obj.Placement=App.Placement(App.Vector(i*800+100,200,300),App.Rotation(App.Vector(0,0,1),15))
                pset=ifc_psets.add_pset(obj,'Pset_ProbeExperiment')
                ifc_psets.add_property(self.file,pset,'ProbeReference','before')
                ifc_psets.show_psets(obj)
                pname=next(p for p in obj.PropertiesList if obj.getGroupOfProperty(p)=='Pset_ProbeExperiment')
                setattr(obj,pname,'after')
                ent=ifc_tools.get_ifc_element(obj)
                assert ent.Name==obj.Label and ent.Description==obj.Description
                assert ent.PredefinedType=='USERDEFINED' and ent.GlobalId==before[i]['GlobalId']
                assert ifcopenshell.util.element.get_psets(ent)['Pset_ProbeExperiment']['ProbeReference']=='after'
                mat=ifcopenshell.util.placement.get_local_placement(ent.ObjectPlacement)
                assert np.allclose(mat[:3,3],[(i*800+100)/1000,0.2,0.3])
            self.doc.recompute()
            self.doc.commitTransaction()
        except Exception:
            self.doc.abortTransaction()
            raise
        self.expected=self.record('edited')

    def save_reopen(self):
        self.announce('saving companion IFC and FreeCAD document, then reopening')
        self.project.IfcFilePath=str(self.ifc)
        ifc_tools.save(self.project,str(self.ifc))
        self.doc.recompute()
        self.doc.saveAs(str(self.fcstd))
        self.results['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.fcstd,self.ifc)}
        App.closeDocument(self.doc.Name)
        self.doc=App.openDocument(str(self.fcstd))
        self.project=next(o for o in self.doc.Objects if hasattr(o,'IfcFilePath'))
        self.file=ifc_tools.get_ifcfile(self.project)
        self.objects=[next(o for o in self.doc.Objects if getattr(o,'GlobalId',None)==gid) for gid in self.ids]
        self.doc.recompute()
        actual=self.record('fcstd_reopened')
        self.compare(actual)
        App.closeDocument(self.doc.Name)
        self.doc=App.newDocument('NativeIFC_saved_file_reopen')
        self.project=ifc_tools.create_document_object(self.doc,filename=str(self.ifc),shapemode=0,strategy=2,silent=True)
        self.file=ifc_tools.get_ifcfile(self.project)
        self.objects=[next(o for o in self.doc.Objects if getattr(o,'GlobalId',None)==gid) for gid in self.ids]
        for obj in self.objects:
            ifc_psets.show_psets(obj)
        self.doc.recompute()
        actual=self.record('ifc_reopened')
        self.compare(actual)
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
        Gui.activeDocument().activeView().saveImage(str(self.work/'reopened.png'),1280,900,'Current')
        self.results['passed']=True
        self.results['completed']=datetime.datetime.now().astimezone().isoformat()
        (self.work/'results.json').write_text(json.dumps(self.results,indent=2,ensure_ascii=False),encoding='utf-8')
        App.closeDocument(self.doc.Name)
        assert list(App.listDocuments())==self.original_documents
        Gui.getMainWindow().statusBar().clearMessage()
        print('NATIVEIFC_FOUR_ELEMENTS_PASSED',str(self.work))

    def compare(self,rows):
        stable=('label','schema','TypeId','Class','IfcClass','GlobalId','StepId','PredefinedType',
                'Type','Type_property','IFC_Type','Description',
                'attached_psets','ShapeMode','shape_null','solids')
        for expected,actual in zip(self.expected,rows):
            assert {k:expected[k] for k in stable}=={k:actual[k] for k in stable},(expected['Class'],'persistence mismatch')
            assert np.allclose(expected['IFC_Placement_matrix'],actual['IFC_Placement_matrix'],rtol=0,atol=1e-7)
            assert np.allclose(expected['Placement']['base_mm'],actual['Placement']['base_mm'],rtol=0,atol=1e-5)
            old_rot=App.Rotation(*expected['Placement']['rotation_q'])
            new_rot=App.Rotation(*actual['Placement']['rotation_q'])
            assert old_rot.isSame(new_rot,1e-7)
