from __future__ import annotations

from core.process_feedback import LONG_PROCESS_MARKER, LONG_PROCESS_MESSAGE, long_process_message, process_stage


def test_long_process_message_warns_before_work_and_has_marker():
    assert LONG_PROCESS_MARKER == "\u23f3"
    assert "El siguiente proceso" in LONG_PROCESS_MESSAGE
    assert "varios segundos" in LONG_PROCESS_MESSAGE
    text = long_process_message("FA Ventanas BIM")
    assert text.startswith(LONG_PROCESS_MARKER)
    assert "FA Ventanas BIM" in text
    assert "mientras se realiza el calculo" in text


def test_process_stage_keeps_visible_activity_marker():
    text = process_stage("FA Techo", "Creando objetos BIM")
    assert text.startswith(LONG_PROCESS_MARKER)
    assert "FA Techo | Creando objetos BIM" in text
