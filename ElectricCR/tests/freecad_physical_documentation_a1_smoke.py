"""ElectricCR A1 physical/documentation prototype smoke test.

Revision: 2026-09-03, FreeCAD 1.1.3.

The test creates only temporary documents/files.  It proves that the placed
App::Link keeps a physical-only Shape while a DocumentationOnly PLAN object can
be changed, hidden and exported independently.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import Arch
import FreeCAD as App
import FreeCADGui as Gui
import Part


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ElectricCR.electriccr.features import objeto_toma_uno
from ElectricCR.electriccr.semantic.freecad_adapter import ensure_luminaire_semantics


DOC_NAME = "ECR_PhysicalDocumentation_A1"
FIXTURE_GROUP = "ElectricCR A1 Test"


def _rect_face(x, y, width, depth):
    points = [
        App.Vector(x, y, 0.0),
        App.Vector(x + width, y, 0.0),
        App.Vector(x + width, y + depth, 0.0),
        App.Vector(x, y + depth, 0.0),
        App.Vector(x, y, 0.0),
    ]
    return Part.Face(Part.makePolygon(points))


def _add_bool(obj, name, value=True):
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyBool", name, FIXTURE_GROUP)
    setattr(obj, name, bool(value))


def _metrics(shape):
    box = shape.BoundBox
    return {
        "volume": round(float(shape.Volume), 6),
        "bound_box": [
            round(float(box.XMin), 6),
            round(float(box.YMin), 6),
            round(float(box.ZMin), 6),
            round(float(box.XMax), 6),
            round(float(box.YMax), 6),
            round(float(box.ZMax), 6),
        ],
        "solids": len(shape.Solids),
        "faces": len(shape.Faces),
    }


def _placement_signature(obj):
    placement = obj.Placement
    return (
        round(float(placement.Base.x), 9),
        round(float(placement.Base.y), 9),
        round(float(placement.Base.z), 9),
        tuple(round(float(value), 12) for value in placement.Rotation.Q),
    )


def _remove_temp(path):
    if path and os.path.isfile(path):
        os.remove(path)


def _make_space(doc):
    building = Arch.makeBuilding(name="ECR A1 Building")
    level = Arch.makeBuildingPart(name="Ground Floor")
    level.IfcType = "Building Storey"
    building.addObject(level)
    boundary = doc.addObject("Part::Feature", "A1SpaceBoundary")
    boundary.Shape = _rect_face(0.0, 0.0, 4000.0, 3000.0)
    _add_bool(boundary, "ECR_TestFixture")
    space = Arch.makeSpace(boundary, name="Sala de Espera A1")
    space.Label = "Sala de Espera A1"
    space.LongName = "Sala de Espera A1"
    level.addObject(space)
    return building, level, space


def run(keep_open=False):
    previous_document = App.ActiveDocument.Name if App.ActiveDocument is not None else ""
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)
    temp_fcstd = os.path.join(tempfile.gettempdir(), DOC_NAME + ".FCStd")
    temp_dxf = os.path.join(tempfile.gettempdir(), DOC_NAME + ".dxf")
    _remove_temp(temp_fcstd)
    _remove_temp(temp_dxf)
    doc = App.newDocument(DOC_NAME)
    doc.UndoMode = 1
    kept_open = False
    try:
        _building, level, space = _make_space(doc)
        staging = doc.addObject("App::DocumentObjectGroup", "ECR_A1_Staging")
        staging.Label = "ElectricCR A1 staging"
        _add_bool(staging, "ECR_TestFixture")
        doc.recompute()

        placement = App.Placement(
            App.Vector(1000.0, 1200.0, 0.0),
            App.Rotation(App.Vector(0.0, 0.0, 1.0), 18.0),
        )
        doc.clearUndos()
        doc.openTransaction("ElectricCR A1 create owner and PLAN")
        luminaire = objeto_toma_uno.crear_toma_link(
            doc=doc,
            name_prefix="Luminaria LED Redonda 1000lm A1",
            key_registro="Luminaria LED Redonda 1000lm",
            tipo_logico="Luminaria",
            placement=placement,
            modo_visual="Ambos",
            altura_rel=2700.0,
            orientacion_pared="Vertical",
            internal_name="LuminariaPhysicalDocumentationA1",
            recompute=False,
            target_group=staging,
            hide_master=True,
            separate_documentation=True,
        )
        doc.recompute()
        create_sync = objeto_toma_uno.sync_plan_representation(
            luminaire,
            dry_run=False,
            manage_transaction=False,
        )
        plan = objeto_toma_uno.get_plan_representation(luminaire)
        owner_name = luminaire.Name
        plan_name = plan.Name
        master_2700_name = luminaire.LinkedObject.Name
        doc.commitTransaction()

        assert create_sync["material_changes"] == 1
        assert plan is not None and plan.Owner is luminaire
        assert plan.DocumentationOnly is True and str(plan.RepresentationRole) == "PLAN"
        assert "ElementUID" not in plan.PropertiesList
        assert str(luminaire.RepresentationContract) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1
        assert str(luminaire.LinkedObject.RepresentationContract) == objeto_toma_uno.REPRESENTATION_CONTRACT_A1

        doc.undo()
        doc.recompute()
        assert doc.getObject(owner_name) is None and doc.getObject(plan_name) is None
        doc.redo()
        doc.recompute()
        luminaire = doc.getObject(owner_name)
        plan = objeto_toma_uno.get_plan_representation(luminaire)
        assert luminaire is not None and plan is not None
        creation_undo_redo = True

        semantics = ensure_luminaire_semantics(
            luminaire,
            dry_run=False,
            uid_factory=lambda: "5f745f62-6daa-4f54-9cf0-f2598d99f6f7",
        )
        assert semantics["status"] == "RESOLVED"
        assert luminaire.Space is space
        uid = str(luminaire.ElementUID)
        placement_before = _placement_signature(luminaire)
        master_before = luminaire.LinkedObject
        physical_before = _metrics(luminaire.Shape)
        plan_before = _metrics(plan.Shape)
        assert physical_before["volume"] > 0.0
        assert physical_before["solids"] > 0
        assert physical_before["bound_box"][2] > 2600.0
        assert plan_before["volume"] == 0.0
        assert plan_before["solids"] == 0
        assert plan_before["bound_box"][2] == 0.0
        assert _metrics(luminaire.Shape) == _metrics(
            objeto_toma_uno.get_physical_shape(luminaire)
        )

        # Visibility is independent and neither branch is rebuilt.
        doc.openTransaction("ElectricCR A1 visibility")
        visibility_plan_only = objeto_toma_uno.set_representation_visibility(
            luminaire, show_model_3d=False, show_plan=True
        )
        doc.commitTransaction()
        assert visibility_plan_only == {"show_model_3d": False, "show_plan": True}
        assert _metrics(luminaire.Shape) == physical_before
        doc.undo()
        doc.recompute()
        assert bool(luminaire.MostrarModelo3D) is True
        doc.redo()
        doc.recompute()
        assert bool(luminaire.MostrarModelo3D) is False and bool(luminaire.MostrarSimboloPlano) is True
        visibility_undo_redo = True
        objeto_toma_uno.set_representation_visibility(luminaire, show_model_3d=True, show_plan=False)
        assert _metrics(luminaire.Shape) == physical_before
        objeto_toma_uno.set_representation_visibility(luminaire, show_model_3d=True, show_plan=True)

        # Modify and scale only PLAN.  The same auxiliary object is reused.
        luminaire.PlanSymbolScale = 1.40
        scale_sync = objeto_toma_uno.sync_plan_representation(luminaire, dry_run=False)
        plan = objeto_toma_uno.get_plan_representation(luminaire)
        plan_scaled = _metrics(plan.Shape)
        assert scale_sync["material_changes"] == 1
        assert plan.Name == plan_name
        assert plan_scaled["bound_box"] != plan_before["bound_box"]
        assert _metrics(luminaire.Shape) == physical_before
        object_count_after_scale = len(doc.Objects)
        sync_second = objeto_toma_uno.sync_plan_representation(luminaire, dry_run=False)
        assert sync_second["material_changes"] == 0
        assert len(doc.Objects) == object_count_after_scale

        # Height relink changes only physical Z; identity/context/placement persist.
        doc.openTransaction("ElectricCR A1 height 2850")
        height_result = objeto_toma_uno.set_installation_elevation(luminaire, 2850.0)
        doc.recompute()
        doc.commitTransaction()
        master_2850 = luminaire.LinkedObject
        physical_2850 = _metrics(luminaire.Shape)
        assert height_result["strategy"] == "electriccr_link"
        assert master_2850 is not master_before
        assert str(luminaire.ElementUID) == uid and luminaire.Space is space
        assert _placement_signature(luminaire) == placement_before
        assert physical_2850["volume"] == physical_before["volume"]
        assert physical_2850["solids"] == physical_before["solids"]
        assert physical_2850["faces"] == physical_before["faces"]
        assert physical_2850["bound_box"][2] > physical_before["bound_box"][2]
        assert objeto_toma_uno.get_plan_representation(luminaire) is plan
        assert _metrics(plan.Shape) == plan_scaled
        doc.undo()
        doc.recompute()
        luminaire = doc.getObject(owner_name)
        assert luminaire.LinkedObject.Name == master_2700_name
        assert str(luminaire.ElementUID) == uid and luminaire.Space is space
        doc.redo()
        doc.recompute()
        luminaire = doc.getObject(owner_name)
        assert luminaire.LinkedObject.Name == master_2850.Name
        assert str(luminaire.ElementUID) == uid and luminaire.Space is space
        height_undo_redo = True

        # The experimental DXF route consumes PLAN, never owner.Shape.
        exported = objeto_toma_uno.export_plan_dxf([luminaire], temp_dxf)
        assert len(exported) == 1 and exported[0].Name == plan_name
        assert os.path.isfile(temp_dxf) and os.path.getsize(temp_dxf) > 0
        dxf_size = os.path.getsize(temp_dxf)

        # Save/reopen preserves owner, master, PLAN and independent visibility.
        objeto_toma_uno.set_representation_visibility(luminaire, True, True)
        doc.recompute()
        space_name = space.Name
        level_name = level.Name
        staging_name = staging.Name
        doc.saveAs(temp_fcstd)
        App.closeDocument(DOC_NAME)
        doc = App.openDocument(temp_fcstd)
        doc.recompute()
        luminaire = doc.getObject(owner_name)
        plan = objeto_toma_uno.get_plan_representation(luminaire)
        space = doc.getObject(space_name)
        level = doc.getObject(level_name)
        staging = doc.getObject(staging_name)
        assert luminaire is not None and plan is not None
        assert str(luminaire.ElementUID) == uid and luminaire.Space is space
        assert _placement_signature(luminaire) == placement_before
        assert plan.Owner is luminaire and plan.DocumentationOnly is True
        assert "ElementUID" not in plan.PropertiesList
        assert str(plan.RepresentationRole) == "PLAN"
        assert _metrics(luminaire.Shape) == physical_2850
        assert _metrics(plan.Shape) == plan_scaled
        assert luminaire in list(staging.Group or [])
        assert space in list(level.Group or [])
        assert objeto_toma_uno.sync_plan_representation(luminaire, dry_run=False)["material_changes"] == 0
        assert objeto_toma_uno.cleanup_orphan_documentation(doc, dry_run=True) == []
        if hasattr(plan.ViewObject, "ShowInTree"):
            assert plan.ViewObject.ShowInTree is False

        # Controlled deletion API leaves no orphan and is itself undoable.
        disposable = objeto_toma_uno.crear_toma_link(
            doc=doc,
            name_prefix="A1 disposable",
            key_registro="Luminaria LED Redonda 1000lm",
            tipo_logico="Luminaria",
            placement=App.Placement(App.Vector(2600.0, 1200.0, 0.0), App.Rotation()),
            altura_rel=2850.0,
            internal_name="A1Disposable",
            separate_documentation=True,
        )
        disposable_plan = objeto_toma_uno.get_plan_representation(disposable)
        disposable_names = (disposable.Name, disposable_plan.Name)
        objeto_toma_uno.remove_device_with_documentation(disposable)
        assert all(doc.getObject(name) is None for name in disposable_names)
        assert objeto_toma_uno.cleanup_orphan_documentation(doc, dry_run=True) == []
        controlled_deletion = True

        result = {
            "freecad_version": ".".join(App.Version()[:3]),
            "alternative_selected": "C_DOCUMENTATION_ONLY_AUXILIARY",
            "registry_key": str(luminaire.KeyRegistro),
            "element_uid": str(luminaire.ElementUID),
            "space": space.Name,
            "linked_master": luminaire.LinkedObject.Name,
            "physical_before_plan_change": physical_before,
            "physical_after_plan_change": _metrics(luminaire.Shape),
            "physical_after_height_2850": physical_2850,
            "plan_before_scale": plan_before,
            "plan_after_scale": plan_scaled,
            "plan_object": plan.Name,
            "plan_hidden_from_tree": bool(
                not getattr(plan.ViewObject, "ShowInTree", True)
                if hasattr(plan, "ViewObject")
                else True
            ),
            "dxf_exported": True,
            "dxf_size_bytes": dxf_size,
            "save_reopen": True,
            "creation_undo_redo": creation_undo_redo,
            "visibility_undo_redo": visibility_undo_redo,
            "height_undo_redo": height_undo_redo,
            "controlled_deletion": controlled_deletion,
            "projection_idempotent": True,
            "orphan_documentation": 0,
            "original_fcstd_touched": False,
            "temp_fcstd": temp_fcstd,
        }
        print("ECR_PHYSICAL_DOCUMENTATION_A1_OK " + json.dumps(result, sort_keys=True))
        if keep_open:
            kept_open = True
            objeto_toma_uno.set_representation_visibility(luminaire, True, True)
            Gui.activeDocument().activeView().viewAxonometric()
            Gui.activeDocument().activeView().fitAll()
        return result
    finally:
        try:
            Gui.Selection.clearSelection()
        except Exception:
            pass
        if not kept_open and DOC_NAME in App.listDocuments():
            App.closeDocument(DOC_NAME)
        if not kept_open:
            _remove_temp(temp_fcstd)
        _remove_temp(temp_dxf)
        if not kept_open and previous_document and previous_document in App.listDocuments():
            App.setActiveDocument(previous_document)


if __name__ == "__main__":
    run()
