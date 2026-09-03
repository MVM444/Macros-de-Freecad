"""FreeCAD 1.1.3 smoke for the semantic luminaire App::Link prototype.

Only temporary documents and files are created.  No user FCStd is opened,
saved, reorganized or otherwise modified.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import Arch
import FreeCAD as App
import FreeCADGui as Gui
import Part


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from CRBIMCore.freecad_room_adapter import resolve_room_for_point
from ElectricCR.electriccr.features import objeto_toma_uno
from ElectricCR.electriccr.semantic.freecad_adapter import (
    ensure_luminaire_semantics,
    project_lighting_tree,
)


DOC_NAME = "ECR_SemanticLuminairePrototype"
FIXTURE_GROUP = "ECR Prototype Fixture"


def _add_string(obj, name, value, group=FIXTURE_GROUP):
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", name, group)
    setattr(obj, name, str(value))


def _add_bool(obj, name, value=True, group=FIXTURE_GROUP):
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyBool", name, group)
    setattr(obj, name, bool(value))


def _rect_face(x, y, width, depth):
    wire = Part.makePolygon(
        [
            App.Vector(x, y, 0.0),
            App.Vector(x + width, y, 0.0),
            App.Vector(x + width, y + depth, 0.0),
            App.Vector(x, y + depth, 0.0),
            App.Vector(x, y, 0.0),
        ]
    )
    return Part.Face(wire)


def _make_space(doc, level, internal_name, label, x, y, width=4000.0, depth=3000.0):
    base = doc.addObject("Part::Feature", internal_name + "_Boundary")
    base.Label = label + " - base"
    base.Shape = _rect_face(x, y, width, depth)
    _add_bool(base, "ECR_TestFixture")
    space = Arch.makeSpace(base, name=label)
    space.Label = label
    space.LongName = label
    level.addObject(space)
    return space, base


def _find_projection_group(doc, role):
    matches = [
        obj
        for obj in doc.Objects
        if obj.TypeId == "App::DocumentObjectGroup"
        and "ECR_ProjectionRole" in obj.PropertiesList
        and str(obj.ECR_ProjectionRole) == role
    ]
    assert len(matches) == 1, (role, [obj.Name for obj in matches])
    return matches[0]


def _projection_reference(doc, source):
    matches = [
        obj
        for obj in doc.Objects
        if obj.TypeId == "App::Link"
        and "ECR_ProjectionReference" in obj.PropertiesList
        and bool(obj.ECR_ProjectionReference)
        and obj.LinkedObject is source
    ]
    assert len(matches) == 1, [obj.Name for obj in matches]
    return matches[0]


def _master_component_z(master):
    values = []
    for shape in list(master.Shape.childShapes() or []):
        box = shape.BoundBox
        values.append((float(box.ZMin), float(box.ZMax), str(shape.ShapeType)))
    return values


def _space_signature(space):
    return {
        "name": space.Name,
        "label": space.Label,
        "long_name": str(space.LongName),
        "base": getattr(space.Base, "Name", ""),
        "placement": (
            float(space.Placement.Base.x),
            float(space.Placement.Base.y),
            float(space.Placement.Base.z),
            tuple(float(value) for value in space.Placement.Rotation.Q),
        ),
        "properties": tuple(sorted(space.PropertiesList)),
        "shape_hash": int(space.Shape.hashCode()),
    }


def _link_signature(link):
    master = link.LinkedObject
    return {
        "linked": master.Name,
        "placement": (
            float(link.Placement.Base.x),
            float(link.Placement.Base.y),
            float(link.Placement.Base.z),
            tuple(float(value) for value in link.Placement.Rotation.Q),
        ),
        "tipo": str(link.Tipo),
        "key": str(link.KeyRegistro),
        "mode": str(link.ModoVisual),
        "orientation": str(link.OrientacionPared),
        "master_category": str(master.Categoria),
        "master_type": str(master.Tipo),
        "master_key": str(master.KeyRegistro),
    }


def _remove_if_present(path):
    if path and os.path.exists(path):
        os.remove(path)


def run(keep_open=False):
    previous_document = App.ActiveDocument.Name if App.ActiveDocument is not None else ""
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)
    temp_fcstd = os.path.join(tempfile.gettempdir(), DOC_NAME + ".FCStd")
    temp_dxf = os.path.join(tempfile.gettempdir(), DOC_NAME + ".dxf")
    _remove_if_present(temp_fcstd)
    _remove_if_present(temp_dxf)
    doc = App.newDocument(DOC_NAME)
    doc.UndoMode = 1
    kept_open = False
    result = {}
    try:
        building = Arch.makeBuilding(name="ECR Test Building")
        level = Arch.makeBuildingPart(name="Ground Floor")
        level.IfcType = "Building Storey"
        _add_bool(building, "ECR_TestFixture")
        _add_bool(level, "ECR_TestFixture")
        building.addObject(level)

        canonical_space, canonical_base = _make_space(
            doc, level, "CanonicalSpace", "Sala de Espera", 0.0, 0.0
        )
        ambiguous_a, _ambiguous_a_base = _make_space(
            doc, level, "AmbiguousA", "Ambiguo A", 6000.0, 0.0
        )
        ambiguous_b, _ambiguous_b_base = _make_space(
            doc, level, "AmbiguousB", "Ambiguo B", 6000.0, 0.0
        )

        staging = doc.addObject("App::DocumentObjectGroup", "ECR_Staging")
        staging.Label = "ECR Prototype Staging"
        _add_bool(staging, "ECR_TestFixture")
        placement = App.Placement(App.Vector(6500.0, 1000.0, 0.0), App.Rotation(18.0, 0.0, 0.0))
        luminaire = objeto_toma_uno.crear_toma_link(
            doc=doc,
            name_prefix="Luminaria semantica piloto",
            key_registro="Luminaria LED Redonda 1000lm",
            tipo_logico="Luminaria",
            placement=placement,
            modo_visual="Ambos",
            altura_rel=2700.0,
            orientacion_pared="Vertical",
            internal_name="LuminariaSemanticaPiloto",
            recompute=False,
            target_group=staging,
            hide_master=True,
        )
        _add_string(luminaire, "CircuitoID", "IL-TEST")
        doc.recompute()

        initial_link = _link_signature(luminaire)
        initial_master = luminaire.LinkedObject
        assert str(initial_master.Tipo) == "Luminaria"
        assert str(initial_master.KeyRegistro) == "Luminaria LED Redonda 1000lm"
        assert not initial_master.Shape.isNull()
        assert initial_master.ViewObject.Visibility is False
        initial_components = _master_component_z(initial_master)
        assert any(abs(zmin) <= 0.01 for zmin, _zmax, _kind in initial_components)
        assert any(zmin > 2000.0 for zmin, _zmax, _kind in initial_components)

        ambiguous_probe = ensure_luminaire_semantics(luminaire, dry_run=True)
        assert ambiguous_probe["status"] == "AMBIGUOUS"
        assert "ElementUID" not in luminaire.PropertiesList and "Space" not in luminaire.PropertiesList
        ambiguous_apply = ensure_luminaire_semantics(
            luminaire,
            dry_run=False,
            uid_factory=lambda: "78607af3-84af-4eed-bdc7-e3aaaf605ac2",
        )
        assert ambiguous_apply["status"] == "AMBIGUOUS"
        assert luminaire.Space is None
        uid = str(luminaire.ElementUID)
        assert uid == "78607af3-84af-4eed-bdc7-e3aaaf605ac2"
        assert _link_signature(luminaire) == initial_link

        luminaire.Placement = App.Placement(App.Vector(15000.0, 1000.0, 0.0), App.Rotation(18.0, 0.0, 0.0))
        not_found_before = _link_signature(luminaire)
        not_found_apply = ensure_luminaire_semantics(luminaire, dry_run=False)
        assert not_found_apply["status"] == "NOT_FOUND"
        assert luminaire.Space is None and str(luminaire.ElementUID) == uid
        assert _link_signature(luminaire) == not_found_before

        luminaire.Placement = App.Placement(App.Vector(1000.0, 1000.0, 0.0), App.Rotation(18.0, 0.0, 0.0))
        canonical_before = _link_signature(luminaire)
        canonical_space_before = _space_signature(canonical_space)
        resolved_apply = ensure_luminaire_semantics(luminaire, dry_run=False)
        assert resolved_apply["status"] == "RESOLVED"
        assert luminaire.Space is canonical_space
        assert str(luminaire.ElementUID) == uid
        assert _link_signature(luminaire) == canonical_before
        assert _space_signature(canonical_space) == canonical_space_before
        assert canonical_space in list(level.Group or [])

        switch = doc.addObject("App::FeaturePython", "ApagadorS1Fixture")
        switch.Label = "S1"
        _add_bool(switch, "ECR_TestFixture")
        _add_string(switch, "Tipo", "Apagador")
        _add_string(switch, "ApagadorID", "S1")
        control = doc.addObject("App::FeaturePython", "ControlS1Fixture")
        control.Label = "Control temporal S1"
        _add_bool(control, "ECR_TestFixture")
        _add_string(control, "ControlID", "CTRL-TEST")
        control.addProperty("App::PropertyLinkList", "Luminarias", FIXTURE_GROUP)
        control.addProperty("App::PropertyLinkList", "Apagadores", FIXTURE_GROUP)
        control.Luminarias = [luminaire]
        control.Apagadores = [switch]
        doc.recompute()

        count_before_projection = len(doc.Objects)
        projection_dry = project_lighting_tree(doc, [luminaire])
        assert projection_dry["dry_run"] is True and projection_dry["material_changes"] > 0
        assert len(doc.Objects) == count_before_projection

        doc.clearUndos()
        projection_apply = project_lighting_tree(doc, [luminaire], dry_run=False)
        assert projection_apply["material_changes"] > 0
        target = _find_projection_group(doc, "Luminaires")
        projection_reference = _projection_reference(doc, luminaire)
        assert projection_reference in list(target.Group or [])
        assert luminaire not in list(target.Group or [])
        projected_count = len(doc.Objects)
        first_uid = str(luminaire.ElementUID)
        first_space = luminaire.Space
        first_linked = luminaire.LinkedObject
        first_placement = App.Placement(luminaire.Placement)
        assert project_lighting_tree(doc, [luminaire])["material_changes"] == 0
        second_apply = project_lighting_tree(doc, [luminaire], dry_run=False)
        assert second_apply["material_changes"] == 0 and len(doc.Objects) == projected_count, (
            second_apply,
            projected_count,
            len(doc.Objects),
        )
        assert luminaire.ElementUID == first_uid and luminaire.Space is first_space
        assert luminaire.LinkedObject is first_linked
        assert luminaire.Placement.isSame(first_placement, 1.0e-9)
        assert luminaire in list(staging.Group or [])

        room_node = _find_projection_group(doc, "Room")
        switch_node = _find_projection_group(doc, "Switch")
        assert room_node.ECR_SourceSpace is canonical_space
        assert switch_node.ECR_SourceControl is control
        assert canonical_space in list(level.Group or [])
        assert canonical_space not in list(room_node.Group or [])
        master_group = doc.getObject("_lib_devices")
        assert master_group is not None and initial_master in list(master_group.Group or [])
        assert not any(obj is initial_master for obj in list(target.Group or []))

        doc.undo()
        doc.recompute()
        assert not any(
            obj.TypeId == "App::DocumentObjectGroup"
            and "ECR_ProjectionRole" in obj.PropertiesList
            for obj in doc.Objects
        )
        doc.redo()
        doc.recompute()
        luminaire = doc.getObject("LuminariaSemanticaPiloto")
        target = _find_projection_group(doc, "Luminaires")
        assert _projection_reference(doc, luminaire) in list(target.Group or [])

        uid_before_height = str(luminaire.ElementUID)
        space_before_height = luminaire.Space
        placement_before_height = App.Placement(luminaire.Placement)
        old_master = luminaire.LinkedObject
        height_result = objeto_toma_uno.set_installation_elevation(luminaire, 2850.0)
        doc.recompute()
        assert height_result["strategy"] == "electriccr_link"
        assert luminaire.LinkedObject is not old_master
        assert str(luminaire.ElementUID) == uid_before_height
        assert luminaire.Space is space_before_height
        assert luminaire.Placement.isSame(placement_before_height, 1.0e-9)
        raised_components = _master_component_z(luminaire.LinkedObject)
        assert any(abs(zmin) <= 0.01 for zmin, _zmax, _kind in raised_components)
        assert any(zmin > 2500.0 for zmin, _zmax, _kind in raised_components)

        dxf_exported = False
        dxf_error = ""
        try:
            import importDXF

            importDXF.export([luminaire], temp_dxf)
            dxf_exported = os.path.exists(temp_dxf) and os.path.getsize(temp_dxf) > 0
        except Exception as exc:
            dxf_error = repr(exc)

        comparator_base = doc.addObject("Part::Feature", "EquipmentComparatorGeometry")
        comparator_base.Label = "Geometria controlada comparador Equipment"
        comparator_base.Shape = luminaire.LinkedObject.Shape.copy()
        _add_bool(comparator_base, "ECR_TestFixture")
        comparator_placement = App.Placement(
            App.Vector(5000.0, 1000.0, 0.0), luminaire.Placement.Rotation
        )
        doc.openTransaction("ElectricCR Arch Equipment comparator")
        equipment = Arch.makeEquipment(
            comparator_base,
            placement=comparator_placement,
            name="Comparador Arch Equipment - Light Fixture",
        )
        equipment.IfcType = "Light Fixture"
        _add_bool(equipment, "ECR_TestFixture")
        doc.recompute()
        equipment_name = equipment.Name
        doc.commitTransaction()
        assert equipment.Base is comparator_base
        assert str(equipment.IfcType) == "Light Fixture"
        assert str(getattr(equipment.Proxy, "Type", "")) == "Equipment"
        assert not equipment.Shape.isNull()
        assert len(equipment.Shape.Faces) == len(comparator_base.Shape.Faces)
        assert len(equipment.Shape.Edges) == len(comparator_base.Shape.Edges)
        assert abs(float(equipment.Shape.Volume) - float(comparator_base.Shape.Volume)) <= 0.01
        assert equipment.Placement.isSame(comparator_placement, 1.0e-9)
        assert "GlobalId" in equipment.PropertiesList and "IfcProperties" in equipment.PropertiesList

        doc.undo()
        doc.recompute()
        assert doc.getObject(equipment_name) is None
        doc.redo()
        doc.recompute()
        equipment = doc.getObject(equipment_name)
        assert equipment is not None and str(equipment.IfcType) == "Light Fixture"
        assert equipment.Base is doc.getObject("EquipmentComparatorGeometry")

        names = {
            "luminaire": luminaire.Name,
            "space": canonical_space.Name,
            "master": luminaire.LinkedObject.Name,
            "equipment": equipment.Name,
            "level": level.Name,
        }
        expected_uid = str(luminaire.ElementUID)
        expected_placement = App.Placement(luminaire.Placement)
        expected_space_signature = _space_signature(canonical_space)
        doc.recompute()
        doc.saveAs(temp_fcstd)
        App.closeDocument(DOC_NAME)
        doc = App.openDocument(temp_fcstd)
        doc.recompute()
        luminaire = doc.getObject(names["luminaire"])
        canonical_space = doc.getObject(names["space"])
        equipment = doc.getObject(names["equipment"])
        level = doc.getObject(names["level"])
        assert str(luminaire.ElementUID) == expected_uid
        assert luminaire.Space is canonical_space
        assert luminaire.LinkedObject.Name == names["master"]
        assert luminaire.Placement.isSame(expected_placement, 1.0e-9)
        reopened_space_signature = _space_signature(canonical_space)
        for key in ("name", "label", "long_name", "base", "placement", "shape_hash"):
            assert reopened_space_signature[key] == expected_space_signature[key]
        assert not any(
            name.startswith("ECR_") or name in {"ElementUID", "Space", "CircuitoID", "ControlID"}
            for name in canonical_space.PropertiesList
        )
        assert canonical_space in list(level.Group or [])
        assert _projection_reference(doc, luminaire) in list(
            _find_projection_group(doc, "Luminaires").Group or []
        )
        assert str(equipment.IfcType) == "Light Fixture" and equipment.Base is not None
        assert project_lighting_tree(doc, [luminaire])["material_changes"] == 0

        result = {
            "freecad_version": ".".join(App.Version()[:3]),
            "registry_key": str(luminaire.KeyRegistro),
            "element_uid": str(luminaire.ElementUID),
            "space": canonical_space.Name,
            "space_level_name": level.Name,
            "space_level_label": level.Label,
            "roomresolver_ambiguous_safe": True,
            "roomresolver_not_found_safe": True,
            "projection_idempotent": True,
            "projection_reference": True,
            "projection_path": [
                "electrico", "Iluminacion", "Circuitos", "IL-TEST", "Recintos",
                "Sala de Espera", "Apagadores", "S1", "Luminarias",
            ],
            "height_relink": True,
            "symbol_2d_at_local_z0": True,
            "model_3d_at_height": True,
            "dxf_exported": dxf_exported,
            "dxf_error": dxf_error,
            "arch_equipment_ifc_type": str(equipment.IfcType),
            "arch_equipment_base_copy": True,
            "undo_redo_tree": True,
            "undo_redo_equipment": True,
            "save_reopen": True,
            "original_fcstd_touched": False,
            "temp_fcstd": temp_fcstd,
        }
        print("ECR_SEMANTIC_LUMINAIRE_PROTOTYPE_OK " + json.dumps(result, sort_keys=True))
        if keep_open:
            kept_open = True
            Gui.activeDocument().activeView().viewAxonometric()
            Gui.activeDocument().activeView().fitAll()
        return result
    finally:
        Gui.Selection.clearSelection()
        if not kept_open and DOC_NAME in App.listDocuments():
            App.closeDocument(DOC_NAME)
        if not kept_open:
            _remove_if_present(temp_fcstd)
        _remove_if_present(temp_dxf)
        if not kept_open and previous_document and previous_document in App.listDocuments():
            App.setActiveDocument(previous_document)


if __name__ == "__main__":
    run()
