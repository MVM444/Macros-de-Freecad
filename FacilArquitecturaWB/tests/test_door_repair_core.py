from FacilArquitecturaWB.core.door_repair_core import (
    OPENING_SEMANTIC_AUTO,
    OPENING_SEMANTIC_BUQUE,
    OPENING_SEMANTIC_LEGACY_LEAF,
    endpoint_match_error,
    infer_opening_semantic,
    opening_fit_metrics,
    plan_door_repair,
    plan_jamb_alignment,
    resolve_effective_opening,
)


def _record(**overrides):
    data = {
        "door_name": "Door",
        "authoritative_first": (0.0, 0.0),
        "authoritative_second": (1000.0, 0.0),
        "frame_first": (0.0, 0.0),
        "frame_second": (900.0, 0.0),
        "corner_status": "BOUNDED",
        "authoritative_width_mm": 1000.0,
        "frame_start_mm": 50.0,
        "frame_end_mm": 50.0,
        "outer_width_mm": 900.0,
    }
    data.update(overrides)
    return data


def test_endpoint_error_accepts_reversed_direction():
    result = endpoint_match_error((0, 0), (900, 0), (900, 0), (0, 0))
    assert result["error_mm"] == 0.0
    assert result["reversed"] is True


def test_smaller_door_already_inside_is_not_resized_or_moved():
    plan = plan_door_repair(
        _record(frame_first=(50.0, 0.0), frame_second=(950.0, 0.0)),
        opening_semantic=OPENING_SEMANTIC_BUQUE,
    )
    assert plan["status"] == "OK"
    assert plan["needs_repair"] is False


def test_smaller_door_outside_is_moved_only_and_width_is_preserved():
    plan = plan_door_repair(
        _record(frame_first=(-75.0, 0.0), frame_second=(825.0, 0.0)),
        opening_semantic=OPENING_SEMANTIC_BUQUE,
    )
    assert plan["repairable"] is True
    assert plan["action"]["mode"] == "move_only"
    assert plan["action"]["resize_required"] is False
    assert plan["action"]["target_outer_width_mm"] == 900.0
    assert plan["action"]["shift_vector_xy_mm"] == (75.0, 0.0)


def test_smaller_door_outside_at_far_end_moves_back_only():
    plan = plan_door_repair(
        _record(frame_first=(250.0, 0.0), frame_second=(1150.0, 0.0)),
        opening_semantic=OPENING_SEMANTIC_BUQUE,
    )
    assert plan["action"]["mode"] == "move_only"
    assert plan["action"]["target_outer_width_mm"] == 900.0
    assert plan["action"]["shift_vector_xy_mm"] == (-150.0, 0.0)


def test_perpendicular_offset_is_corrected_without_resizing():
    plan = plan_door_repair(
        _record(frame_first=(50.0, 40.0), frame_second=(950.0, 40.0)),
        opening_semantic=OPENING_SEMANTIC_BUQUE,
    )
    assert plan["action"]["mode"] == "move_only"
    assert plan["action"]["target_outer_width_mm"] == 900.0
    assert plan["action"]["shift_vector_xy_mm"] == (0.0, -40.0)


def test_oversized_door_is_reduced_to_buque_then_positioned():
    plan = plan_door_repair(
        _record(
            frame_first=(-50.0, 0.0),
            frame_second=(1050.0, 0.0),
            outer_width_mm=1100.0,
        ),
        opening_semantic=OPENING_SEMANTIC_BUQUE,
    )
    assert plan["repairable"] is True
    assert plan["action"]["mode"] == "resize_and_move"
    assert plan["action"]["resize_required"] is True
    assert plan["action"]["target_outer_width_mm"] == 1000.0
    assert plan["action"]["shift_vector_xy_mm"] == (50.0, 0.0)


def test_reversed_oversized_door_uses_far_opening_endpoint():
    plan = plan_door_repair(
        _record(
            frame_first=(1050.0, 0.0),
            frame_second=(-50.0, 0.0),
            outer_width_mm=1100.0,
        ),
        opening_semantic=OPENING_SEMANTIC_BUQUE,
    )
    assert plan["action"]["mode"] == "resize_and_move"
    assert plan["action"]["shift_vector_xy_mm"] == (-50.0, 0.0)


def test_non_parallel_frame_is_diagnostic_only():
    plan = plan_door_repair(
        _record(frame_first=(0.0, 0.0), frame_second=(900.0, 20.0)),
        opening_semantic=OPENING_SEMANTIC_BUQUE,
    )
    assert plan["status"] == "OUTSIDE_BUQUE_UNSUPPORTED"
    assert plan["repairable"] is False


def test_non_bounded_outside_frame_is_diagnostic_only():
    plan = plan_door_repair(
        _record(
            frame_first=(-40.0, 0.0),
            frame_second=(860.0, 0.0),
            corner_status="JAMB_ONLY",
        ),
        opening_semantic=OPENING_SEMANTIC_BUQUE,
    )
    assert plan["status"] == "OUTSIDE_BUQUE_UNSUPPORTED"
    assert plan["repairable"] is False


def test_fit_metrics_report_containment_overflow():
    metrics = opening_fit_metrics((0, 0), (1000, 0), (-75, 0), (825, 0))
    assert metrics["overflow_start_mm"] == 75.0
    assert metrics["overflow_end_mm"] == 0.0


def test_legacy_leaf_semantic_expands_segment_by_frame_margins():
    record = _record(
        authoritative_second=(663.850602, 0.0),
        authoritative_width_mm=663.850602,
        outer_width_mm=763.850602,
        frame_first=(-50.0, 75.0),
        frame_second=(713.850602, 75.0),
    )
    opening = resolve_effective_opening(
        record, opening_semantic=OPENING_SEMANTIC_LEGACY_LEAF
    )
    assert opening["used_semantic"] == OPENING_SEMANTIC_LEGACY_LEAF
    assert abs(opening["source_length_mm"] - 663.850602) < 1e-9
    assert abs(opening["effective_length_mm"] - 763.850602) < 1e-9
    assert opening["effective_first"] == (-50.0, 0.0)
    assert abs(opening["effective_second"][0] - 713.850602) < 1e-9


def test_auto_detects_historical_leaf_signature():
    record = _record(
        authoritative_second=(663.850602, 0.0),
        authoritative_width_mm=663.850602,
        outer_width_mm=763.850602,
    )
    inferred = infer_opening_semantic(record)
    assert inferred["semantic"] == OPENING_SEMANTIC_LEGACY_LEAF
    assert inferred["legacy_signature_error_mm"] < 1e-9


def test_historical_upala_signature_moves_only_and_preserves_width():
    record = _record(
        authoritative_second=(663.850602, 0.0),
        authoritative_width_mm=663.850602,
        outer_width_mm=763.850602,
        frame_first=(-50.0, 75.0),
        frame_second=(713.850602, 75.0),
    )
    plan = plan_door_repair(record, opening_semantic=OPENING_SEMANTIC_LEGACY_LEAF)
    assert plan["repairable"] is True
    assert plan["opening_semantic"] == OPENING_SEMANTIC_LEGACY_LEAF
    assert plan["action"]["mode"] == "move_only"
    assert plan["action"]["resize_required"] is False
    assert abs(plan["action"]["target_outer_width_mm"] - 763.850602) < 1e-9
    assert abs(plan["action"]["shift_vector_xy_mm"][0]) < 1e-9
    assert abs(plan["action"]["shift_vector_xy_mm"][1] + 75.0) < 1e-9


def test_same_historical_geometry_can_be_forced_to_complete_buque_contract():
    record = _record(
        authoritative_second=(663.850602, 0.0),
        authoritative_width_mm=663.850602,
        outer_width_mm=763.850602,
        frame_first=(-50.0, 75.0),
        frame_second=(713.850602, 75.0),
    )
    plan = plan_door_repair(record, opening_semantic=OPENING_SEMANTIC_BUQUE)
    assert plan["repairable"] is True
    assert plan["opening_semantic"] == OPENING_SEMANTIC_BUQUE
    assert plan["action"]["mode"] == "resize_and_move"
    assert abs(plan["action"]["target_outer_width_mm"] - 663.850602) < 1e-9


def test_auto_uses_legacy_signature_for_historical_upala_case():
    record = _record(
        authoritative_second=(663.850602, 0.0),
        authoritative_width_mm=663.850602,
        outer_width_mm=763.850602,
        frame_first=(-50.0, 75.0),
        frame_second=(713.850602, 75.0),
    )
    plan = plan_door_repair(record, opening_semantic=OPENING_SEMANTIC_AUTO)
    assert plan["opening_semantic_detected"] == OPENING_SEMANTIC_LEGACY_LEAF
    assert plan["opening_semantic"] == OPENING_SEMANTIC_LEGACY_LEAF
    assert plan["action"]["mode"] == "move_only"



def test_jamb_alignment_uses_nearest_frame_end_and_preserves_width():
    record = _record(
        frame_first=(100.0, 75.0),
        frame_second=(863.850602, 75.0),
        outer_width_mm=763.850602,
    )
    plan = plan_jamb_alignment(record, (100.0, 0.0))
    assert plan["repairable"] is True
    assert plan["action"]["mode"] == "align_to_jamb"
    assert plan["action"]["resize_required"] is False
    assert plan["action"]["frame_endpoint"] == "first"
    assert plan["action"]["shift_vector_xy_mm"] == (0.0, -75.0)
    assert abs(plan["action"]["target_outer_width_mm"] - 763.850602) < 1e-9


def test_jamb_alignment_can_use_second_frame_end():
    record = _record(
        frame_first=(0.0, 0.0),
        frame_second=(900.0, 0.0),
        outer_width_mm=900.0,
    )
    plan = plan_jamb_alignment(record, (975.0, 25.0))
    assert plan["action"]["frame_endpoint"] == "second"
    assert plan["action"]["shift_vector_xy_mm"] == (75.0, 25.0)
    assert plan["action"]["target_outer_width_mm"] == 900.0


def test_jamb_alignment_verification_can_lock_original_endpoint():
    record = _record(
        frame_first=(50.0, 20.0),
        frame_second=(950.0, 20.0),
        outer_width_mm=900.0,
    )
    plan = plan_jamb_alignment(record, (50.0, 0.0), frame_endpoint="first")
    assert plan["action"]["frame_endpoint"] == "first"
    moved = dict(record)
    moved["frame_first"] = (50.0, 0.0)
    moved["frame_second"] = (950.0, 0.0)
    verify = plan_jamb_alignment(moved, (50.0, 0.0), frame_endpoint="first")
    assert verify["status"] == "OK"
    assert verify["error_mm"] == 0.0


def test_jamb_alignment_is_idempotent_when_already_on_jamb():
    record = _record(
        frame_first=(0.0, 0.0),
        frame_second=(900.0, 0.0),
        outer_width_mm=900.0,
    )
    plan = plan_jamb_alignment(record, (0.5, 0.0), tolerance_mm=2.0)
    assert plan["status"] == "OK"
    assert plan["needs_repair"] is False
    assert plan["action"] is None
