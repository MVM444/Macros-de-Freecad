"""Read/audit smoke for the existing ElectricCR semantic tree contract."""

from __future__ import annotations

import os
import runpy

import FreeCAD as App
import FreeCADGui as Gui
import Part


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ORGANIZER = os.path.join(REPO_ROOT, "Configuracion del proyecto", "Organizar_Documento_Electrico.FCMacro")


def _string(obj, name, value, group="ElectricCR"):
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", name, group)
    setattr(obj, name, value)


def _group_path(doc, obj):
    labels = []
    current = obj
    seen = set()
    while current is not None:
        parent = current.getParentGroup() if hasattr(current, "getParentGroup") else None
        if parent is None or parent.Name in seen:
            break
        seen.add(parent.Name)
        labels.append(parent.Label)
        current = parent
    return list(reversed(labels))


def run():
    name = "ECR_SemanticTreeContract"
    if App.listDocuments().get(name) is not None:
        App.closeDocument(name)
    doc = App.newDocument(name)
    try:
        library = doc.addObject("App::DocumentObjectGroup", "Componentes")
        library.Label = "Componentes"
        master = doc.addObject("Part::Feature", "MasterLuminaria")
        master.Label = "Master luminaria"
        master.Shape = Part.makeBox(600, 600, 50)
        _string(master, "Tipo", "Luminaria")
        library.addObject(master)

        misleading = doc.addObject("App::DocumentObjectGroup", "RecintoVisualIncorrecto")
        misleading.Label = "Recinto visual incorrecto"
        luminaire = doc.addObject("App::Link", "LuminariaPiloto")
        luminaire.Label = "Luminaria piloto"
        luminaire.LinkedObject = master
        luminaire.Placement.Base = App.Vector(1200, 800, 2600)
        _string(luminaire, "Tipo", "Luminaria")
        _string(luminaire, "CircuitoID", "IL-07")
        _string(luminaire, "Recinto", "Oficina Semantica")
        _string(luminaire, "ApagadorID", "S-03")
        misleading.addObject(luminaire)

        switch = doc.addObject("Part::Feature", "ApagadorPiloto")
        switch.Label = "Apagador S-03"
        _string(switch, "Tipo", "Apagador")

        control = doc.addObject("App::FeaturePython", "ControlPiloto")
        _string(control, "ControlID", "CTRL-03")
        control.addProperty("App::PropertyLinkList", "Luminarias", "Control")
        control.addProperty("App::PropertyLinkList", "Apagadores", "Control")
        control.Luminarias = [luminaire]
        control.Apagadores = [switch]

        circuit = doc.addObject("App::DocumentObjectGroup", "CircuitoPiloto")
        circuit.Label = "IL-07"
        _string(circuit, "CircuitoID", "IL-07", "Circuito")
        _string(circuit, "Tablero", "TP-01", "Circuito")
        doc.recompute()

        ns = runpy.run_path(ORGANIZER, run_name="electriccr_semantic_tree_audit")
        assert ns["_resolve_circuito"](doc, luminaire) == "IL-07"
        assert ns["_resolve_recinto"](doc, luminaire, []) == "Oficina Semantica"
        assert ns["_resolve_apagador"](doc, luminaire, "Oficina Semantica") == "S-03"

        placement_before = App.Placement(luminaire.Placement)
        linked_before = luminaire.LinkedObject
        target_path = ns["_target_path_for"](
            "Luminaria",
            ns["_resolve_circuito"](doc, luminaire),
            ns["_resolve_recinto"](doc, luminaire, []),
            ns["_resolve_apagador"](doc, luminaire, "Oficina Semantica"),
            "",
        )
        assert target_path == [
            "electrico", "Iluminacion", "Circuitos", "IL-07", "Recintos",
            "Oficina Semantica", "Apagadores", "S-03", "Luminarias",
        ]
        assert luminaire.LinkedObject is linked_before
        assert luminaire.Placement.isSame(placement_before, 1.0e-9)
        assert list(control.Luminarias) == [luminaire]
        assert list(control.Apagadores) == [switch]
        assert circuit.Tablero == "TP-01" and "Tablero" in circuit.PropertiesList

        # Current gaps are intentional audit findings, not migrated here.
        assert "Space" not in luminaire.PropertiesList
        assert "Level" not in luminaire.PropertiesList
        assert "System" not in luminaire.PropertiesList
        assert circuit.getTypeIdOfProperty("Tablero") == "App::PropertyString"

        print(
            "ECR_SEMANTIC_TREE_CONTRACT_OK property_precedence=1 deterministic_path=1 "
            "linkedobject_unchanged=1 placement_unchanged=1 control_links=1 "
            "room_link_pending=1 panel_link_pending=1 level_system_pending=1 "
            "tree_rebuild_pending=1"
        )
    finally:
        Gui.Selection.clearSelection()
        if App.listDocuments().get(name) is not None:
            App.closeDocument(name)


if __name__ == "__main__":
    run()
