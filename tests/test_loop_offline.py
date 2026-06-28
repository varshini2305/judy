"""End-to-end loop test with a stub model client — exercises the full pipeline
(eval -> reflect -> skill mutation -> metrics -> logging) with zero API calls.
"""

from __future__ import annotations

import asyncio

from judy.data.dataset import Dataset
from judy.judge.schema import Candidate, Item, Tier
from judy.loop.run import run_mode


class StubClient:
    """Mimics GeminiClient.generate_json without any network calls."""

    def __init__(self) -> None:
        self.calls = 0

    async def generate_json(self, prompt: str, *, system_instruction=None, temperature=0.0):
        self.calls += 1
        if '"failure_modes"' in prompt:  # reflection call
            return {"failure_modes": ["general lesson"], "strategies": [], "procedure_edits": []}
        return {"verdict": "A", "margin": 3, "rationale": "stub", "criteria": []}


def _item(id_: str, ttype: str, win: Tier, lose: Tier) -> Item:
    return Item(
        id=id_,
        task_type=ttype,
        system_prompt="spec with a constraint",
        question="q?",
        gold_answer="gold",
        candidates=[Candidate(tier=win, text=f"good-{id_}"), Candidate(tier=lose, text=f"bad-{id_}")],
        known_ordering=(win, lose),
    )


def _dataset() -> Dataset:
    return Dataset(
        dev=[_item("d1", "factual_qa", "A", "C"), _item("d2", "factual_qa", "A", "B")],
        heldout=[_item("h1", "factual_qa", "A", "C"), _item("h2", "numeric_constraint", "A", "D")],
    )


def test_anchored_run_produces_artifacts(tmp_path):
    stub = StubClient()
    res = asyncio.run(run_mode("anchored", _dataset(), tmp_path, n_iters=2, client=stub))

    assert res["mode"] == "anchored"
    assert len(res["history"]) >= 1
    assert (tmp_path / "anchored" / "iter_0.jsonl").exists()
    assert (tmp_path / "anchored" / "skill_0.md").exists()
    for h in res["history"]:
        assert 0.0 <= h["agreement"] <= 1.0
    assert stub.calls > 0


def test_unanchored_run_uses_self_inconsistency(tmp_path):
    stub = StubClient()
    res = asyncio.run(run_mode("unanchored", _dataset(), tmp_path, n_iters=1, client=stub))
    # Stub always picks presented "A", so every item flips under order-swap and
    # the unanchored error signal should fire (reflection records errors).
    assert res["edits"], "unanchored loop should have reflected at least once"
    assert res["edits"][0]["n_errors"] >= 1
