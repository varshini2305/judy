"""Simulated users with KNOWN hidden preference policies.

These make preference-learning falsifiable: because we know the policy that
generated a choice, we can measure whether Judy predicts the user's choices
better as she sees more feedback (idea 3 / idea 10). Correctness is always a
hard constraint — a simulated user prefers a correct answer over an incorrect
one regardless of style; preferences only break *style* ties.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from judy.preference.schema import Side


@dataclass(frozen=True)
class Features:
    """Cheap, deterministic style features of an answer."""

    word_count: int
    repetition: float  # 1 - unique/total tokens; higher = more repetitive

    @classmethod
    def of(cls, text: str) -> "Features":
        tokens = re.findall(r"\b\w+\b", text.lower())
        n = len(tokens)
        rep = 1.0 - (len(set(tokens)) / n) if n else 0.0
        return cls(word_count=n, repetition=round(rep, 3))


# A decision fn: (features_a, features_b, task_type, complexity, step) -> side.
DecideFn = Callable[[Features, Features, str, str, int], Side]


@dataclass(frozen=True)
class SimulatedUser:
    """A user with a fixed (possibly drifting) hidden preference policy."""

    name: str
    decide_fn: DecideFn

    def choose(
        self,
        answer_a: str,
        answer_b: str,
        *,
        task_type: str,
        complexity: str = "simple",
        correct_a: bool = True,
        correct_b: bool = True,
        step: int = 0,
    ) -> Side:
        # Hard constraint: correctness dominates style preference.
        if correct_a != correct_b:
            return "A" if correct_a else "B"
        return self.decide_fn(
            Features.of(answer_a), Features.of(answer_b), task_type, complexity, step
        )


def _prefer_shorter(a: Features, b: Features, *_: object) -> Side:
    return "A" if a.word_count <= b.word_count else "B"


def _prefer_longer(a: Features, b: Features, *_: object) -> Side:
    return "A" if a.word_count >= b.word_count else "B"


def _prefer_less_repetition(a: Features, b: Features, *_: object) -> Side:
    return "A" if a.repetition <= b.repetition else "B"


def _conditional(a: Features, b: Features, _tt: str, complexity: str, _step: int) -> Side:
    # Concise for simple questions, detailed for complex ones.
    return _prefer_longer(a, b) if complexity == "complex" else _prefer_shorter(a, b)


# --- Built-in hidden policies ------------------------------------------------

def concise_user() -> SimulatedUser:
    return SimulatedUser("concise-always", lambda a, b, *_: _prefer_shorter(a, b))


def detailed_user() -> SimulatedUser:
    return SimulatedUser("detailed-always", lambda a, b, *_: _prefer_longer(a, b))


def anti_repetition_user() -> SimulatedUser:
    return SimulatedUser("anti-repetition", lambda a, b, *_: _prefer_less_repetition(a, b))


def conditional_user() -> SimulatedUser:
    return SimulatedUser("concise-simple_detailed-complex", _conditional)


def drifting_user(switch_after: int = 6) -> SimulatedUser:
    """Concise early, then flips to detailed — tests recovery after drift."""

    def decide(a: Features, b: Features, _tt: str, _cx: str, step: int) -> Side:
        return _prefer_longer(a, b) if step >= switch_after else _prefer_shorter(a, b)

    return SimulatedUser(f"drift@{switch_after}", decide)


BUILTIN_USERS: dict[str, Callable[[], SimulatedUser]] = {
    "concise": concise_user,
    "detailed": detailed_user,
    "anti_repetition": anti_repetition_user,
    "conditional": conditional_user,
    "drifting": drifting_user,
}
