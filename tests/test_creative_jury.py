"""Offline ($0) test of the V4 judge-jury preference experiment (judy.eval.jury).

Uses an injected stub client so the full pipeline — per-user Item construction,
B0 scoring, juror learning via preference-reflection, and the personalization
matrix — runs end-to-end with zero model calls.
"""

from __future__ import annotations

import asyncio
import json

from judy.data.personas import PERSONAS
from judy.eval.jury import persona_item, run_jury, score_against


class _Usage:
    def as_dict(self):
        return {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}


class StubClient:
    """Always votes 'A' presented; reflection returns a taste lesson."""

    def __init__(self):
        self.usage = _Usage()

    async def generate_json(self, prompt, *, system_instruction=None, temperature=0.0):
        if '"failure_modes"' in prompt:  # persona-reflection call
            return {"failure_modes": ["this reader dislikes cliché"], "strategies": [], "procedure_edits": []}
        return {"verdict": "A", "margin": 3, "rationale": "stub", "criteria": []}


def _row(idx: int, split: str, prefs: dict[str, str]) -> dict:
    return {
        "id": f"cre-{idx:03d}", "split": split, "form": "haiku",
        "system_prompt": "write a haiku", "question": "about rain",
        "answer_a": f"a-{idx}", "answer_b": f"b-{idx}",
        "style_axis": "imagery vs restraint", "style_contrast": "A vivid, B spare",
        "labels": {pid: {"preferred": prefs[pid], "rating_a": 4, "rating_b": 3,
                         "rationale": "taste"} for pid in prefs},
    }


def _dataset(path) -> None:
    # 5 train + 4 test items; personas split A/B differently so users disagree.
    rows = []
    pids = [p.id for p in PERSONAS]
    for i in range(9):
        split = "train" if i < 5 else "test"
        # rotate which personas prefer A vs B so the matrix is non-degenerate
        prefs = {pid: ("A" if (i + k) % 2 == 0 else "B") for k, pid in enumerate(pids)}
        rows.append(_row(i, split, prefs))
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def test_persona_item_encodes_preference():
    row = _row(0, "test", {p.id: "B" for p in PERSONAS})
    item = persona_item(row, PERSONAS[0].id)
    assert item.correct_side() == "B"  # tiers set so preferred side is "correct"


def test_score_against_counts_agreement():
    rows = [_row(0, "test", {PERSONAS[0].id: "A", **{p.id: "B" for p in PERSONAS[1:]}})]
    verdicts = [("cre-000", False, "A"), ("cre-000", True, "A")]
    m = score_against(verdicts, rows, PERSONAS[0].id)
    assert m.agreement == 1.0
    other = score_against(verdicts, rows, PERSONAS[1].id)
    assert other.agreement == 0.0


def test_run_jury_end_to_end(tmp_path):
    ds = tmp_path / "creative.jsonl"
    _dataset(ds)
    summary = asyncio.run(run_jury(ds, batch_size=3, client=StubClient()))

    assert summary["n_personas"] == len(PERSONAS)
    assert summary["n_train"] == 5 and summary["n_test"] == 4
    # full 5x5 personalization matrix present
    matrix = summary["personalization_matrix"]
    assert len(matrix) == len(PERSONAS)
    assert all(len(row) == len(PERSONAS) for row in matrix.values())
    # B0 and V4 means computed over all users
    assert 0.0 <= summary["b0_mean_agreement"] <= 1.0
    assert 0.0 <= summary["v4_mean_agreement"] <= 1.0
    # jurors with training errors should have learned at least once
    assert sum(summary["v4_juror_updates"].values()) > 0
