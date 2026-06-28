"""Typed domain schemas for Judy (brief §2).

One evaluation unit is an :class:`Item`: a task spec + question + two tiered
candidate answers. Ground truth is free by construction via quality tiers
(A > B > C > D). The judge sees only the system prompt, question, and the two
answers (as A/B) and returns a :class:`Verdict`; it never sees the gold answer
or the tiers.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Tier = Literal["A", "B", "C", "D"]
Side = Literal["A", "B"]
Winner = Literal["A", "B", "tie"]

# Tier quality ordering, best first. Lower rank index = better answer.
_TIER_RANK: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3}


class Candidate(BaseModel):
    """One candidate answer with its (hidden-from-judge) quality tier."""

    tier: Tier
    text: str


class Criterion(BaseModel):
    """A single spec-derived criterion and which side won it."""

    name: str
    winner: Winner


class Verdict(BaseModel):
    """The judge's structured output for one pairwise comparison."""

    verdict: Side
    margin: int = Field(ge=1, le=5)
    rationale: str
    criteria: list[Criterion] = Field(default_factory=list)


class JudgeRecord(BaseModel):
    """One judged comparison, normalized to canonical orientation, for logging.

    ``verdict`` is the winning *canonical* side (A = candidates[0]) regardless of
    whether answers were presented swapped, so records compare cleanly across
    order-swapped passes.
    """

    item_id: str
    task_type: str
    swap: bool
    verdict: Side
    margin: int
    rationale: str
    criteria: list[Criterion] = Field(default_factory=list)
    correct: bool


class Item(BaseModel):
    """One evaluation unit. ``candidates`` holds exactly two answers at judge time.

    ``gold_answer`` is an anchor for *constructing* tiers and is NEVER shown to
    the judge. ``known_ordering`` is ``(winner_tier, loser_tier)`` ground truth.
    """

    id: str
    task_type: str
    system_prompt: str
    question: str
    gold_answer: str
    candidates: list[Candidate] = Field(min_length=2, max_length=2)
    known_ordering: tuple[Tier, Tier]

    def correct_side(self) -> Side:
        """Return which presented side (A=candidates[0], B=candidates[1]) is better."""
        a, b = self.candidates[0].tier, self.candidates[1].tier
        return "A" if _TIER_RANK[a] < _TIER_RANK[b] else "B"

    def is_correct(self, verdict_side: Side) -> bool:
        """True if a verdict picked the higher-tier candidate."""
        return verdict_side == self.correct_side()
