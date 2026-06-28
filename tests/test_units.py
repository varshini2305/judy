"""Unit tests for metrics, JSON parsing, and skill mutation (no API calls)."""

from __future__ import annotations

from judy.judge.schema import Criterion, JudgeRecord
from judy.judge.skill import FAILURE_MODES_HEADER, append_bullets
from judy.llm.gemini import _extract_json
from judy.metrics.metrics import compute_metrics


def _rec(item_id: str, swap: bool, verdict: str, correct: bool, margin: int = 3) -> JudgeRecord:
    return JudgeRecord(
        item_id=item_id, task_type="t", swap=swap, verdict=verdict,
        margin=margin, rationale="r", criteria=[Criterion(name="c", winner=verdict)],
        correct=correct,
    )


def test_agreement_and_position_consistency():
    records = [
        _rec("i1", False, "A", True), _rec("i1", True, "A", True),    # consistent + correct
        _rec("i2", False, "A", True), _rec("i2", True, "B", False),   # inconsistent
    ]
    m = compute_metrics(records)
    assert m.n_items == 2
    assert m.agreement == 0.75
    assert m.position_consistency == 0.5
    assert m.position_consistent_agreement == 0.5


def test_metrics_without_order_swap_has_no_position_fields():
    m = compute_metrics([_rec("i1", False, "A", True)])
    assert m.position_consistency is None


def test_extract_json_handles_fences_and_prose():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('here it is: {"verdict": "A"} done') == {"verdict": "A"}


def test_append_bullets_dedups_and_clears_placeholder():
    seed = f"{FAILURE_MODES_HEADER}\n(none yet — appended later)\n"
    out = append_bullets(seed, FAILURE_MODES_HEADER, ["lesson one", "lesson one"])
    assert "none yet" not in out
    assert out.count("- lesson one") == 1
    # second pass with a duplicate adds nothing new
    out2 = append_bullets(out, FAILURE_MODES_HEADER, ["lesson one"])
    assert out2.count("- lesson one") == 1
