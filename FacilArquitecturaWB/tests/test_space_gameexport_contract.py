"""Pruebas del contrato FA -> GameEngineExport para Espacios BIM existentes.

Version: 1.1
Fecha: 2026-09-01 America/Costa_Rica.
"""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_migration_function():
    source = (ROOT / "core" / "space_utils.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        item for item in tree.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == "migrate_game_export_exclusions"
    )
    module = ast.Module(body=[node], type_ignores=[])

    def set_prop(obj, _type, name, _group, _desc, value):
        setattr(obj, name, value)

    namespace = {"SPACE_GENERATOR": "FA_CreateBIMSpaces", "set_prop": set_prop}
    exec(compile(module, "space_utils.py", "exec"), namespace)
    return namespace["migrate_game_export_exclusions"]


class Obj:
    def __init__(self, name, role, generator="FA_CreateBIMSpaces", excluded=None):
        self.Name = name
        self.FA_Role = role
        self.FA_GeneratedBy = generator
        if excluded is not None:
            self.GameExportExclude = excluded


class Doc:
    def __init__(self, objects):
        self.Objects = objects
        self.transactions = []

    def openTransaction(self, name):
        self.transactions.append(("open", name))

    def commitTransaction(self):
        self.transactions.append(("commit",))

    def abortTransaction(self):
        self.transactions.append(("abort",))

    def recompute(self):
        pass


def test_migration_updates_only_fa_spaces_and_bases_and_is_idempotent():
    migrate = _load_migration_function()
    space = Obj("Space", "bim_space")
    base = Obj("Base", "space_base", excluded=False)
    unrelated = Obj("Other", "wall")
    foreign = Obj("Foreign", "bim_space", generator="Other")
    doc = Doc([space, base, unrelated, foreign])

    preview = migrate(doc, dry_run=True)
    assert preview["matched"] == 2
    assert not hasattr(space, "GameExportExclude")

    result = migrate(doc, dry_run=False)
    assert result["changed"] == 2
    assert space.GameExportExclude is True
    assert base.GameExportExclude is True
    assert not hasattr(unrelated, "GameExportExclude")
    assert not hasattr(foreign, "GameExportExclude")

    repeated = migrate(doc, dry_run=False)
    assert repeated["matched"] == 0
    assert repeated["changed"] == 0


def _space_utils_source_and_tree():
    source = (ROOT / "core" / "space_utils.py").read_text(encoding="utf-8")
    return source, ast.parse(source)


def test_space_sync_contract_is_non_destructive_and_dry_run_capable():
    source, tree = _space_utils_source_and_tree()
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "plan_bim_space_updates" in functions
    assert "collect_existing_spaces" in functions
    assert "create_bim_spaces" in functions

    create = functions["create_bim_spaces"]
    arg_names = [arg.arg for arg in create.args.args]
    assert "dry_run" in arg_names
    assert "min_iou" in arg_names
    assert "min_overlap" in arg_names
    create_text = ast.get_source_segment(source, create) or ""
    assert "remove_previous_spaces(" not in create_text
    assert 'status == "AMBIGUO"' in create_text
    assert 'status in {"MATCH", "CAMBIO"}' in create_text
    assert "_apply_record_to_pair" in create_text

    collect_text = ast.get_source_segment(source, functions["collect_existing_spaces"]) or ""
    assert "FA_SpaceSchemaVersion" in collect_text
    assert "object_generator" in collect_text
    assert '!= str(generator)' not in collect_text


def test_space_sync_persists_room_uid_and_match_diagnostics():
    source, _tree = _space_utils_source_and_tree()
    assert '"FA_RoomUID"' in source
    assert '"FA_SpaceMatchStatus"' in source
    assert '"FA_SpaceMatchScore"' in source
    assert 'MATCH_STATUS = ("MATCH", "CAMBIO", "NO_MATCH", "AMBIGUO")' in source


def _load_pure_space_helpers(*names):
    source, tree = _space_utils_source_and_tree()
    wanted = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            wanted.append(node)
    module = ast.Module(body=wanted, type_ignores=[])
    namespace = {"math": __import__("math")}
    exec(compile(module, "space_utils.py", "exec"), namespace)
    return [namespace[name] for name in names]


def test_polygon_metrics_are_stable_for_simple_room():
    area_centroid, perimeter = _load_pure_space_helpers(
        "_polygon_area_centroid", "_polygon_perimeter_mm"
    )
    points = [[0.0, 0.0], [4000.0, 0.0], [4000.0, 3000.0], [0.0, 3000.0]]
    area_mm2, centroid = area_centroid(points)
    assert area_mm2 == 12_000_000.0
    assert centroid == (2000.0, 1500.0)
    assert perimeter(points) == 14_000.0
