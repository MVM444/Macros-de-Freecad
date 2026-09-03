"""Regression contract for programmatic roof feedback isolation."""

from pathlib import Path


def test_programmatic_roof_feedback_is_optional_and_guarded():
    source = (Path(__file__).parents[1] / "commands" / "cmd_roof_axis_prototype.py").read_text(encoding="utf-8")
    start = source.index("def create_roof_from_rectangle_programmatic(")
    end = source.index("\ndef _run_from_rectangle()", start)
    block = source[start:end]
    assert "feedback=None" in block
    assert 'if feedback is not None:\n            feedback.stage("Creando clavadores")' in block
    assert 'if feedback is not None:\n            feedback.stage("Creando cubierta BIM")' in block
    assert 'if feedback is not None:\n            feedback.stage("Recomputando y validando geometria")' in block


def test_toolbar_path_keeps_its_own_feedback_instance():
    source = (Path(__file__).parents[1] / "commands" / "cmd_roof_axis_prototype.py").read_text(encoding="utf-8")
    assert 'feedback = LongOperationFeedback("FA Techo desde rectangulo"' in source
