"""Schemas for preference-conditioned judging.

A user's evaluation taste is stored as **scoped observations** (not one prose
persona), so retrieval can pull only the observations relevant to the current
task. Feedback events are the raw signal that updates those observations.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Side = Literal["A", "B"]

# Preference dimensions the system reasons about. Extend as needed.
Dimension = Literal[
    "conciseness",      # +1 = prefers shorter, -1 = prefers more detail
    "detail",           # completeness / depth
    "repetition",       # +1 = dislikes repetition
    "structure",        # +1 = prefers bullets/sections
    "tone",             # register/formality
    "caution",          # hedging vs directness
]

FeedbackType = Literal[
    "pairwise_choice",      # chose A or B (high reliability)
    "explicit_correction",  # rewrote/edited (high)
    "preference_statement", # said a preference (high, scope-uncertain)
    "rating",               # numeric (medium)
    "regeneration",         # asked to regenerate (low-medium)
    "continuation",         # continued from a response (low)
]

# How much to trust each feedback type as a label (idea 5's reliability ladder).
FEEDBACK_RELIABILITY: dict[str, float] = {
    "pairwise_choice": 1.0,
    "explicit_correction": 0.95,
    "preference_statement": 0.8,
    "rating": 0.6,
    "regeneration": 0.4,
    "continuation": 0.2,
}


class PreferenceObservation(BaseModel):
    """One scoped belief about how a user evaluates answers."""

    dimension: Dimension
    direction: float = Field(ge=-1.0, le=1.0)  # signed strength
    task_scope: list[str] = Field(default_factory=list)  # task_types it applies to; [] = global
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    evidence_count: int = 0
    source: str = "pairwise_feedback"

    def applies_to(self, task_type: str) -> bool:
        return not self.task_scope or task_type in self.task_scope


class FeedbackEvent(BaseModel):
    """A single observed user signal about a comparison."""

    case_id: str
    task_type: str
    feedback_type: FeedbackType
    selected: Side | None = None
    reason_tags: list[str] = Field(default_factory=list)
    free_text: str = ""
    confidence: float = 1.0

    @property
    def reliability(self) -> float:
        """Effective trust = type reliability x stated confidence."""
        return FEEDBACK_RELIABILITY.get(self.feedback_type, 0.3) * self.confidence


class PreferenceHypothesis(BaseModel):
    """A competing explanation of the user's taste, weighted Bayesian-style.

    Kept *candidate* until it earns weight by predicting held-out choices
    (idea 3's hypothesis approach + idea 2's validated-lesson gate).
    """

    text: str
    weight: float = Field(ge=0.0, default=1.0)
    dimension: Dimension | None = None
    task_scope: list[str] = Field(default_factory=list)
    status: Literal["candidate", "validated"] = "candidate"
    correct_predictions: int = 0
    total_predictions: int = 0

    @property
    def hit_rate(self) -> float:
        return self.correct_predictions / self.total_predictions if self.total_predictions else 0.0
