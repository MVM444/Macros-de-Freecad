"""Static contract tests for the canonical Facil Arquitectura model tree.

Version: 1.0
Fecha y hora: 2026-09-01 14:40 America/Costa_Rica.
"""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def core(name):
    return (ROOT / "core" / name).read_text(encoding="utf-8")


def command(name):
    return (ROOT / "commands" / name).read_text(encoding="utf-8")


def test_native_level_tree_is_authoritative():
    source = core("bim_structure_utils.py")
    assert "def migrate_legacy_support_to_level" in source
    assert "def ensure_auxiliary_parent" in source
    assert "def adopt_auxiliary_sources" in source
    assert "migrate_legacy_support_to_level(doc, level)" in source
    assert 'DEFAULT_AUXILIARY_GROUP_LABEL = "Auxiliares FA"' in source


def test_demo_does_not_create_parallel_fa_project_or_space_group():
    demo = command("cmd_demo_building.py")
    assert "ensure_project_support_structure" not in demo
    assert 'group_name="FA_DemoSpaces"' not in demo
    assert "ensure_parameter_sheet(self.doc, self.sources_group)" in demo
    assert "schedule_group=self.sources_group" in demo
    assert "create_documentary_grid=False" in demo


def test_spaces_are_direct_level_members_by_default():
    source = core("space_utils.py")
    tree = ast.parse(source)
    func = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "create_bim_spaces")
    names = [arg.arg for arg in func.args.args]
    defaults = dict(zip(names[-len(func.args.defaults):], func.args.defaults))
    assert isinstance(defaults["group_name"], ast.Constant)
    assert defaults["group_name"].value is None
    assert "add_to_level(level, space)" in source


def test_ceiling_grid_is_documentary_and_opt_in():
    source = core("ceiling_utils.py")
    assert 'options.get("create_documentary_grid", False)' in source
    assert "if create_documentary_grid:" in source
    assert "FA_DocumentaryOnly" in source
    ui = command("cmd_create_modular_ceiling.py")
    assert "Crear reticula 2D documental (opcional)" in ui
    assert 'GetBool("create_documentary_grid", False)' in ui
    assert "ensure_level_auxiliary_group" in ui


def test_operational_support_commands_no_longer_force_fa_project():
    names = [
        "cmd_centerlines_from_selection.py",
        "cmd_door_centerlines_from_selection.py",
        "cmd_window_centerlines_from_selection.py",
        "cmd_detect_rooms_2d.py",
        "cmd_create_closed_rooms.py",
    ]
    for name in names:
        source = command(name)
        assert "ensure_project_support_structure" not in source, name
        assert "ensure_auxiliary_parent" in source, name


def test_opening_sources_and_rebuild_are_adopted_as_auxiliaries():
    for name in ["cmd_create_doors_bim.py", "cmd_create_windows_bim.py", "cmd_create_openings_bim.py"]:
        assert "adopt_auxiliary_sources(doc, target_level, sources)" in command(name)
    rebuild = core("bim_rebuild_utils.py")
    assert "adopt_auxiliary_sources(doc, level, organized_sources, allow_any_type=True)" in rebuild
    assert "add_to_container(level, source)" not in rebuild


def test_build_id_bumped():
    assert 'BUILD_ID = "2026.09.01.11"' in core("constants.py")


def test_site_does_not_claim_plan_sketches_by_traceability_link():
    source = core("site_floor_utils.py")
    assert '"App::PropertyStringList"' in source
    assert '"FA_SourceSketchNames"' in source
    # Geometry depends on footprint.Sources; Site/Slab traceability must not add a
    # second PropertyLinkList that makes the source Sketches children of Site.
    assert source.count('"App::PropertyLinkList",\n        "FA_SourceSketches"') == 0
