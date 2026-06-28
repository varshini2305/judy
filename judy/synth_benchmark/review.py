"""Helpers for synthetic benchmark review exports."""

from __future__ import annotations

from typing import Any


def make_review_row(row: dict[str, Any]) -> dict[str, Any]:
    """Strip hidden labels and keep only human-review fields."""
    return {
        "id": row["id"],
        "mode": row["mode"],
        "task_type": row["task_type"],
        "system_prompt": row["system_prompt"],
        "question": row["question"],
        "answer_a": row["answer_a"],
        "answer_b": row["answer_b"],
        "review_axes": ["independent_score", "pairwise_preference", "comment"],
        "meta": {
            "difficulty": row.get("difficulty"),
            "style_axis": row.get("style_axis"),
        },
    }

