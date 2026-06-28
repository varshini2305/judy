"""Offline tests for synthetic benchmark helpers."""

from __future__ import annotations

from judy.synth_benchmark.review import make_review_row


def test_make_review_row_strips_hidden_labels():
    row = {
        "id": "obj-001",
        "mode": "objective_pairwise",
        "task_type": "factual_qa",
        "system_prompt": "Answer accurately.",
        "question": "Who created Superman?",
        "answer_a": "Jerry Siegel and Joe Shuster.",
        "answer_b": "Stan Lee.",
        "difficulty": "medium",
        "objectively_better": "A",
        "failure_axis": "factual_error",
        "winner_reason": "A is factually correct.",
    }
    review = make_review_row(row)
    assert "objectively_better" not in review
    assert "winner_reason" not in review
    assert review["mode"] == "objective_pairwise"
    assert review["meta"]["difficulty"] == "medium"
