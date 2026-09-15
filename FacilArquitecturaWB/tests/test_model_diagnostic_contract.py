"""Source contract tests for FA model diagnostic integration.

Version: 0.2.0
Date: 2026-09-09
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_adapter_prefers_claim_children_and_is_read_only_by_contract():
    text = (ROOT / "core" / "model_diagnostic_freecad.py").read_text(encoding="utf-8")
    assert "claimChildren" in text
    assert "Group" in text
    assert "OutList" in text
    assert "openTransaction" not in text
    assert "addObject(" not in text
    assert "removeObject(" not in text


def test_command_is_registered_in_project_toolbar():
    init = (ROOT / "InitGui.py").read_text(encoding="utf-8")
    cmd = (ROOT / "commands" / "cmd_model_diagnostic.py").read_text(encoding="utf-8")
    assert "cmd_model_diagnostic" in init
    assert 'registered["model_diagnostic"]' in init
    assert 'CommandName = COMMAND_NAME' in cmd
    assert 'FA_ModelDiagnostic' in cmd


def test_command_outputs_under_freecad_macro_dir_without_hardcoding_user_path():
    cmd = (ROOT / "commands" / "cmd_model_diagnostic.py").read_text(encoding="utf-8")
    assert "getUserMacroDir(True)" in cmd
    assert '"_reportes_diagnostico"' in cmd
    assert "C:\\Users\\mmfallas" not in cmd


def test_v020_requires_explicit_selection_scope_and_exposes_report_actions():
    cmd = (ROOT / "commands" / "cmd_model_diagnostic.py").read_text(encoding="utf-8")
    assert 'COMMAND_VERSION = "0.2.0"' in cmd
    assert "def _choose_manual_scope(" in cmd
    assert '"Documento completo", "Full document"' in cmd
    assert '"Solo seleccion", "Selection only"' in cmd
    assert "selection = _choose_manual_scope" in cmd
    assert "copy_prompt=False" in cmd
    assert "class DiagnosticResultDialog" in cmd
    assert '"Copiar ruta del MD", "Copy MD path"' in cmd
    assert '"Abrir carpeta", "Open folder"' in cmd
    assert "QDesktopServices.openUrl" in cmd
    assert "QUrl.fromLocalFile" in cmd
    assert '_copy_to_clipboard(path)' in cmd


def test_generate_report_can_force_full_document_and_preserves_macro_prompt_opt_in():
    cmd = (ROOT / "commands" / "cmd_model_diagnostic.py").read_text(encoding="utf-8")
    macro = (ROOT.parent / "CapturarArbolYPrompt.FCMacro").read_text(encoding="utf-8") if (ROOT.parent / "CapturarArbolYPrompt.FCMacro").exists() else ""
    assert "selection=[]" in cmd
    assert "copy_prompt=True" in cmd
    if macro:
        assert "copy_prompt=True" in macro


def test_stair_opening_relations_are_captured():
    adapter = (ROOT / "core" / "model_diagnostic_freecad.py").read_text(encoding="utf-8")
    core = (ROOT / "core" / "model_diagnostic_core.py").read_text(encoding="utf-8")
    assert '"FA_SlabOpening"' in adapter
    assert '"FA_CeilingExclusionPlan"' in adapter
    assert '"FA_CeilingObjects"' in adapter
    assert '"Subtractions"' in adapter
    assert 'STAIR_SLAB_OPENING_APPLIED' in core
    assert 'STAIR_CEILING_EXCLUSION_APPLIED' in core
