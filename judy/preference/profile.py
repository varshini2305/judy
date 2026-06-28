"""A user's learned preference profile: a weighted distribution over competing
preference hypotheses (idea 3's particle approach), updated from feedback.

The profile does two jobs:
1. **predict()** — model-free guess of the user's next choice (cheap, $0 eval).
2. **render_context()** — natural-language preference block + ICL examples to
   condition the LLM judge (Build A: "examples are a function of the user").

The hypothesis *space* is predefined here; discovering new hypotheses (e.g. via
the critique agent) is the recursive extension.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from judy.preference.schema import Side
from judy.preference.simulated_user import Features

# Candidate hypotheses: name -> predictor over style features.
# Each returns the side this hypothesis expects the user to pick.
def _shorter(a: Features, b: Features) -> Side:
    return "A" if a.word_count <= b.word_count else "B"


def _longer(a: Features, b: Features) -> Side:
    return "A" if a.word_count >= b.word_count else "B"


def _less_rep(a: Features, b: Features) -> Side:
    return "A" if a.repetition <= b.repetition else "B"


HYPOTHESES: dict[str, object] = {
    "prefers_concise": lambda a, b, cx: _shorter(a, b),
    "prefers_detailed": lambda a, b, cx: _longer(a, b),
    "prefers_less_repetition": lambda a, b, cx: _less_rep(a, b),
    "concise_simple_detailed_complex": lambda a, b, cx: _longer(a, b) if cx == "complex" else _shorter(a, b),
}

# Plain-English rendering for the judge context.
_HYP_PHRASING: dict[str, str] = {
    "prefers_concise": "prefers concise, to-the-point answers",
    "prefers_detailed": "prefers detailed, thorough answers",
    "prefers_less_repetition": "dislikes repetition; values non-redundant answers",
    "concise_simple_detailed_complex": "prefers concise answers for simple questions and detailed answers for complex ones",
}

_MISS_LIKELIHOOD = 0.25  # weight multiplier when a hypothesis mispredicts


@dataclass
class UserProfile:
    """Weighted belief over preference hypotheses, learned from feedback."""

    user_id: str
    weights: dict[str, float] = field(default_factory=lambda: {h: 1.0 for h in HYPOTHESES})
    stats: dict[str, list[int]] = field(default_factory=lambda: {h: [0, 0] for h in HYPOTHESES})
    examples: list[tuple[str, str, Side]] = field(default_factory=list)  # (answer_a, answer_b, chosen)

    def __post_init__(self) -> None:
        self._normalize()

    def _normalize(self) -> None:
        total = sum(self.weights.values()) or 1.0
        for h in self.weights:
            self.weights[h] /= total

    def predict(self, a: Features, b: Features, complexity: str = "simple") -> Side:
        """Weighted vote across hypotheses for the user's likely choice."""
        score_a = sum(w for h, w in self.weights.items() if HYPOTHESES[h](a, b, complexity) == "A")
        score_b = 1.0 - score_a
        return "A" if score_a >= score_b else "B"

    def observe(self, a: Features, b: Features, chosen: Side, complexity: str = "simple", *,
                reliability: float = 1.0, answer_a: str = "", answer_b: str = "") -> None:
        """Bayesian-style update: up-weight hypotheses that predicted the choice."""
        for h in self.weights:
            pred = HYPOTHESES[h](a, b, complexity)
            hit = pred == chosen
            self.stats[h][1] += 1
            if hit:
                self.stats[h][0] += 1
            like = 1.0 if hit else _MISS_LIKELIHOOD
            # Reliability tempers the update for weak feedback signals.
            self.weights[h] *= like ** reliability
        self._normalize()
        if answer_a and answer_b:
            self.examples.append((answer_a, answer_b, chosen))

    def top_hypothesis(self) -> tuple[str, float]:
        h = max(self.weights, key=self.weights.get)
        return h, self.weights[h]

    def render_context(self, *, k_examples: int = 3) -> str:
        """Preference block + recent ICL examples to condition the judge."""
        h, w = self.top_hypothesis()
        lines = [f"User preference (confidence {w:.0%}): this user {_HYP_PHRASING.get(h, h)}.",
                 "Apply this preference only to break ties; correctness and spec-compliance come first."]
        for a, b, chosen in self.examples[-k_examples:]:
            lines.append(f"Example — the user chose the answer: {(a if chosen == 'A' else b)[:160]}")
        return "\n".join(lines)
