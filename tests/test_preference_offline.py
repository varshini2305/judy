"""Offline ($0) tests: does the profile learn simulated users' hidden policies?"""

from __future__ import annotations

from judy.preference.session import make_style_pairs, run_session
from judy.preference.simulated_user import (
    concise_user,
    conditional_user,
    detailed_user,
    drifting_user,
)


def _second_half_accuracy(flags: list[bool]) -> float:
    half = flags[len(flags) // 2 :]
    return sum(half) / len(half)


def test_learns_concise_preference():
    res = run_session(concise_user(), make_style_pairs(16, seed=1))
    assert _second_half_accuracy(res["flags"]) >= 0.85
    assert res["profile"].top_hypothesis()[0] == "prefers_concise"


def test_learns_detailed_preference():
    res = run_session(detailed_user(), make_style_pairs(16, seed=2))
    assert res["profile"].top_hypothesis()[0] == "prefers_detailed"


def test_learns_conditional_preference():
    # Concise-for-simple / detailed-for-complex should beat both pure hypotheses.
    res = run_session(conditional_user(), make_style_pairs(20, seed=3))
    assert res["profile"].top_hypothesis()[0] == "concise_simple_detailed_complex"
    assert _second_half_accuracy(res["flags"]) >= 0.85


def test_recovers_after_preference_drift():
    # User flips concise -> detailed at step 6; the profile should re-converge.
    pairs = make_style_pairs(20, seed=4)
    res = run_session(drifting_user(switch_after=6), pairs)
    assert res["profile"].top_hypothesis()[0] == "prefers_detailed"
    # Accuracy over the final quarter (well after the switch) should be high.
    tail = res["flags"][-5:]
    assert sum(tail) / len(tail) >= 0.6
