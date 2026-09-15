"""Tests for FA model diagnostic independent core.

Version: 0.1.0
Date: 2026-09-09
"""

from FacilArquitecturaWB.core.model_diagnostic_core import analyze_snapshot, render_markdown


def _snapshot():
    return {
        "meta": {"generated_at": "2026-09-09T14:40:00-06:00", "freecad_version": "1.1.3", "workbench_version": "0.14.11", "workbench_build": "2026.09.09.3", "scope": "documento_completo"},
        "document": {"name": "Demo", "label": "Casa demo", "file": "(documento aun no guardado)"},
        "roots": [
            {"name": "Site", "label": "Sitio BIM", "type_id": "Part::FeaturePython", "visibility": True, "children": []},
            {"name": "Wire", "label": "Wire", "type_id": "Part::FeaturePython", "visibility": True, "children": []},
        ],
        "objects": [
            {"name": "Building", "label": "Casa demo", "type_id": "App::GeometryPython", "ifc_type": "Building", "tree_parents": ["Site"], "is_root": False, "properties": {}, "state": []},
            {"name": "L0", "label": "Nivel 00", "type_id": "App::GeometryPython", "ifc_type": "Building Storey", "tree_parents": ["Building"], "is_root": False, "properties": {}, "state": []},
            {"name": "L1", "label": "Nivel 01", "type_id": "App::GeometryPython", "ifc_type": "Building Storey", "tree_parents": ["Building"], "is_root": False, "properties": {}, "state": []},
            {"name": "S1", "label": "FA Escalera entre losas", "type_id": "Part::FeaturePython", "ifc_type": "", "tree_parents": ["L0"], "is_root": False, "properties": {"FA_GeneratedBy": "FA_StairBetweenSlabs_v0.1.0"}, "state": []},
            {"name": "S2", "label": "FA Escalera entre losas008", "type_id": "Part::FeaturePython", "ifc_type": "", "tree_parents": ["L0"], "is_root": False, "properties": {"FA_GeneratedBy": "FA_StairBetweenSlabs_v0.1.0"}, "state": []},
            {"name": "Wire", "label": "Wire", "type_id": "Part::FeaturePython", "ifc_type": "", "tree_parents": [], "is_root": True, "properties": {}, "state": []},
            {"name": "Slab0", "label": "Losa 0", "type_id": "Part::FeaturePython", "ifc_type": "", "tree_parents": ["L0"], "is_root": False, "properties": {}, "state": []},
            {"name": "Slab1", "label": "Losa 1", "type_id": "Part::FeaturePython", "ifc_type": "", "tree_parents": ["L1"], "is_root": False, "properties": {}, "state": []},
        ],
        "relations": [],
        "tree_cycles": [],
        "capture_errors": [],
    }


def _add_rel(snapshot, source, field, target):
    snapshot["relations"].append({"source": source, "field": field, "targets": [{"name": target, "label": target, "type_id": ""}]})


def test_detects_duplicate_stairs_and_root_source():
    snap = _snapshot()
    for stair in ("S1", "S2"):
        _add_rel(snap, stair, "FA_LowerSlab", "Slab0")
        _add_rel(snap, stair, "FA_UpperSlab", "Slab1")
        _add_rel(snap, stair, "FA_LowerLevel", "L0")
        _add_rel(snap, stair, "FA_UpperLevel", "L1")
        _add_rel(snap, stair, "FA_SourceWire", "Wire")
    result = analyze_snapshot(snap)
    codes = [item["code"] for item in result["findings"]]
    assert "DUPLICATE_STAIRS_SAME_SLABS" in codes
    assert codes.count("STAIR_SOURCE_IS_ROOT") == 2
    assert codes.count("STAIR_CONNECTS_TWO_LEVELS") == 2


def test_markdown_contains_summary_findings_and_tree():
    snap = _snapshot()
    result = analyze_snapshot(snap)
    text = render_markdown(snap, result)
    assert "# FA Informe diagnostico" in text
    assert "## Hallazgos" in text
    assert "## Arbol del modelo" in text
    assert "Nivel 00" in text or "Sitio BIM" in text


def test_confirms_applied_stair_openings():
    snap = _snapshot()
    snap["objects"] = [obj for obj in snap["objects"] if obj["name"] != "S2"]
    stair = next(obj for obj in snap["objects"] if obj["name"] == "S1")
    stair["properties"]["FA_SlabOpeningStatus"] = "native_subtraction_applied"
    stair["properties"]["FA_CeilingExclusionStatus"] = "generator_exclusion_applied"
    snap["objects"].extend([
        {"name": "Void", "label": "Buque escalera", "type_id": "Part::Feature", "ifc_type": "", "tree_parents": ["Slab1"], "is_root": False, "properties": {}, "state": []},
        {"name": "Ceiling", "label": "Cielo", "type_id": "Part::Feature", "ifc_type": "Covering", "tree_parents": ["L0"], "is_root": False, "properties": {}, "state": []},
        {"name": "CeilingPlan", "label": "PLAN exclusion", "type_id": "Part::Feature", "ifc_type": "", "tree_parents": ["L0"], "is_root": False, "properties": {}, "state": []},
    ])
    _add_rel(snap, "S1", "FA_LowerSlab", "Slab0")
    _add_rel(snap, "S1", "FA_UpperSlab", "Slab1")
    _add_rel(snap, "S1", "FA_LowerLevel", "L0")
    _add_rel(snap, "S1", "FA_UpperLevel", "L1")
    _add_rel(snap, "S1", "FA_SourceWire", "Wire")
    _add_rel(snap, "S1", "FA_SlabOpening", "Void")
    _add_rel(snap, "Slab1", "Subtractions", "Void")
    _add_rel(snap, "S1", "FA_CeilingObjects", "Ceiling")
    _add_rel(snap, "S1", "FA_CeilingExclusionPlan", "CeilingPlan")
    result = analyze_snapshot(snap)
    codes = [item["code"] for item in result["findings"]]
    assert "STAIR_SLAB_OPENING_APPLIED" in codes
    assert "STAIR_CEILING_EXCLUSION_APPLIED" in codes
    assert "STAIR_SLAB_OPENING_INCOMPLETE" not in codes
    assert "STAIR_CEILING_EXCLUSION_INCOMPLETE" not in codes
