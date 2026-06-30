"""Offline ($0) test of the disagreement-driven self-improvement loop."""

from __future__ import annotations

import asyncio

from judy.preference.profile import UserProfile
from judy.preference.reasoning import judge_pair, reason_disagreement


class StubClient:
    """Judge always picks A; triage returns a 'taste' note (or 'flaw' if primed)."""

    def __init__(self, kind: str = "taste"):
        self.kind = kind

    async def generate_json(self, prompt, *, system_instruction=None, temperature=0.0):
        if '"kind"' in prompt:  # triage call
            if self.kind == "flaw":
                return {"kind": "flaw", "preference_note": "",
                        "general_lesson": "verify claims before rewarding fluent phrasing",
                        "explanation": "judge rewarded style over correctness"}
            return {"kind": "taste", "preference_note": "prefers concise answers",
                    "general_lesson": "", "explanation": "both fine; user likes brevity"}
        return {"verdict": "A", "margin": 3, "rationale": "A reads better", "criteria": []}


def test_judge_pair_returns_verdict():
    v, rationale = asyncio.run(judge_pair(StubClient(), "policy", "short", "long answer"))
    assert v == "A" and rationale


def test_taste_disagreement_becomes_user_note():
    reasoning = asyncio.run(reason_disagreement(
        StubClient("taste"), answer_a="short", answer_b="long",
        judge_verdict="A", judge_rationale="A reads better", user_choice="B"))
    assert reasoning["kind"] == "taste"
    profile = UserProfile(user_id="demo")
    profile.add_preference_note(reasoning["preference_note"])
    assert profile.has_signal()
    assert "concise" in profile.render_context()


def test_flaw_disagreement_yields_general_lesson():
    reasoning = asyncio.run(reason_disagreement(
        StubClient("flaw"), answer_a="x", answer_b="y",
        judge_verdict="A", judge_rationale="A reads better", user_choice="B",
        user_rationale="A is factually wrong"))
    assert reasoning["kind"] == "flaw"
    assert reasoning["general_lesson"] and not reasoning["preference_note"]


def test_preference_notes_persist_roundtrip(tmp_path):
    p = UserProfile(user_id="demo")
    p.add_preference_note("prefers concise answers")
    f = tmp_path / "profile.json"
    p.save(f)
    q = UserProfile.load(f)
    assert q.preference_notes == ["prefers concise answers"]
    assert q.has_signal()
