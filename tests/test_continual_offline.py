"""Offline ($0) test of the streaming continual-learning loop (batch updates)."""

from __future__ import annotations

import asyncio

from judy.judge.schema import Candidate, Item, Tier
from judy.loop.continual import continual_learn


class StubClient:
    async def generate_json(self, prompt: str, *, system_instruction=None, temperature=0.0):
        if '"failure_modes"' in prompt:  # reflection call
            return {"failure_modes": ["a general lesson about judging"], "strategies": [], "procedure_edits": []}
        return {"verdict": "A", "margin": 3, "rationale": "stub", "criteria": []}


def _item(id_: str, c0: Tier, c1: Tier) -> Item:
    return Item(
        id=id_, task_type="t", system_prompt="spec", question="q?", gold_answer="g",
        candidates=[Candidate(tier=c0, text=f"x-{id_}"), Candidate(tier=c1, text=f"y-{id_}")],
        known_ordering=(c0, c1) if c0 < c1 else (c1, c0),
    )


def test_continual_updates_policy_every_batch():
    # 6 items; the stub always picks side A, so items whose better answer is on
    # side B are errors that should trigger reflection + a policy update.
    dev = [
        _item("d1", "A", "C"),  # correct (better is A)
        _item("d2", "C", "A"),  # error   (better is B)
        _item("d3", "C", "A"),  # error
        _item("d4", "A", "C"),  # correct
        _item("d5", "C", "A"),  # error
        _item("d6", "C", "A"),  # error
    ]
    items_by_id = {i.id: i for i in dev}
    seed = "# Judge Policy\n## Known failure modes to avoid\n(none yet)\n"

    final, snapshots, flags, edits = asyncio.run(
        continual_learn(StubClient(), seed, dev, items_by_id, batch_size=3)
    )

    assert len(flags) == 6                       # every example was judged
    assert len(snapshots) >= 3                   # initial + one per batch of 3
    assert edits, "batches with errors should produce policy updates"
    assert final != seed                         # the policy changed (learned)
    assert "general lesson" in final             # a lesson was appended
