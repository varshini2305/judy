"""Offline ($0) test of the V5 teacher-driven continual loop (stub student+teacher)."""

from __future__ import annotations

import asyncio

from judy.judge.schema import Candidate, Item, Tier
from judy.loop.teacher_loop import run_teacher_continual


class StubStudent:
    async def generate_json(self, prompt, *, system_instruction=None, temperature=0.0):
        return {"verdict": "A", "margin": 3, "rationale": "stub", "criteria": []}


class StubTeacher:
    async def generate_json(self, prompt, *, system_instruction=None, temperature=0.0):
        return {
            "student_was": "wrong", "failure_mode": "fluency_bias",
            "why_correct_is_better": "it actually verifies the claim",
            "principle": "verify claims before trusting fluency",
            "procedure": "list the spec constraints first",
            "is_preference_not_correctness": False, "counterexample": "n/a", "confidence": 0.8,
        }


def _item(id_: str, c0: Tier, c1: Tier) -> Item:
    return Item(
        id=id_, task_type="t", system_prompt="spec", question=f"q-{id_}?", gold_answer="g",
        candidates=[Candidate(tier=c0, text=f"x-{id_}"), Candidate(tier=c1, text=f"y-{id_}")],
        known_ordering=(c0, c1) if c0 < c1 else (c1, c0),
    )


def test_teacher_loop_grows_lessons_and_examples():
    # Stub student always picks A; items whose better answer is B are errors the
    # teacher should turn into lessons + example-bank entries.
    dev = [_item("d1", "A", "C"), _item("d2", "C", "A"), _item("d3", "C", "A"),
           _item("d4", "A", "C"), _item("d5", "C", "A"), _item("d6", "C", "A")]
    held = [_item("h1", "A", "C"), _item("h2", "C", "A")]
    seed = "# Judge Policy\n## Known failure modes to avoid\n(none yet)\n## Strategies in use\n- start somewhere\n"

    out = asyncio.run(run_teacher_continual(
        StubStudent(), StubTeacher(), dev, held,
        base_policy=seed, teacher_policy="teacher", batch_size=3, checkpoint_every=3,
    ))

    assert out["example_bank"], "corrected cases should populate the example bank"
    assert out["critiques"], "teacher should have produced critiques"
    assert "verify claims" in out["final_policy"]      # lesson channel
    assert len(out["curve"]) >= 2                        # learning curve checkpoints
    assert len(out["snapshots"]) >= 2                    # policy evolved
