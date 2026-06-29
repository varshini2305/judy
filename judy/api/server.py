"""FastAPI backend for Judy's interactive demo.

Powers two things the UI shows interactively:
1. **Live user feedback** — serve a QA pair, the user picks the better answer, and
   Judy learns their preference on the fly (model-free, $0): /api/preference/*.
2. **Performance gains** — serve the consolidated variant results + learning
   curves so the UI can render the method comparison: /api/experiments, /api/curves.
Plus a live single judgment for "Try Judy": /api/judge (uses Gemini, costs credits).

Run: uvicorn judy.api.server:app --reload
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from judy.config import CONFIG
from judy.judge.judge import _coerce_verdict, build_user_prompt
from judy.judge.skill import load_skill
from judy.llm.gemini import GeminiClient
from judy.preference.profile import UserProfile
from judy.preference.schema import FeedbackEvent
from judy.preference.session import make_style_pairs
from judy.preference.simulated_user import Features

app = FastAPI(title="Judy API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_UI_PUBLIC = CONFIG.runs_dir.parent / "ui/public"
_GENERIC_SPEC = "Answer the user's question as helpfully, correctly, and completely as possible."

# --- Demo session state ---------------------------------------------------------
# The learned preference is PERSISTED so it improves the judge across runs; the
# per-session pair cursor (_seen) and feedback log (_events) stay in-memory.
_PAIRS = make_style_pairs(24, seed=1)
_PROFILE_PATH = CONFIG.runs_dir / "preference_profile.json"


def _load_profile() -> UserProfile:
    """Load the persisted preference if present, else start fresh."""
    if _PROFILE_PATH.exists():
        try:
            return UserProfile.load(_PROFILE_PATH)
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass
    return UserProfile(user_id="demo")


_profile = _load_profile()
_seen: set[int] = set()
_events: list[dict] = []
_SIM_METHODS = {
    "winner_only": "Use only explicit winner labels from best-pick and ranking feedback.",
    "weighted_feedback": "Use all collected feedback with confidence weighting, including score gaps.",
    "note_aware": "Use weighted feedback and lightly boost hypotheses from user-written notes.",
}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": CONFIG.model}


# === 1) Live user-feedback / preference learning ($0, model-free) ===============

@app.get("/api/preference/next")
def next_pair() -> dict:
    """Serve the next QA pair for the user to rate (or done)."""
    for i, (a, b, tt) in enumerate(_PAIRS):
        if i not in _seen:
            return {"index": i, "answer_a": a, "answer_b": b, "task_type": tt, "remaining": len(_PAIRS) - len(_seen)}
    return {"done": True}


class Feedback(BaseModel):
    index: int
    feedback_mode: Literal["best", "ranking", "score"] = "best"
    chosen: str | None = None  # "A" | "B"
    ranking: list[str] | None = None
    score_a: int | None = None
    score_b: int | None = None
    note: str = ""


def _complexity_of(task_type: str) -> str:
    return "complex" if task_type == "complex_q" else "simple"


def _normalize_feedback(fb: Feedback) -> tuple[str | None, float, dict]:
    if fb.feedback_mode == "best":
        if fb.chosen not in ("A", "B"):
            raise HTTPException(400, "best-response mode requires chosen=A|B")
        return fb.chosen, 1.0, {
            "mode": "best",
            "selected": fb.chosen,
            "summary": f"user selected {fb.chosen} as the better response",
        }

    if fb.feedback_mode == "ranking":
        if not fb.ranking or len(fb.ranking) != 2 or sorted(fb.ranking) != ["A", "B"]:
            raise HTTPException(400, "ranking mode requires ranking=['A','B'] or ['B','A']")
        chosen = fb.ranking[0]
        return chosen, 0.95, {
            "mode": "ranking",
            "selected": chosen,
            "ranking": fb.ranking,
            "summary": f"user ranked {fb.ranking[0]} over {fb.ranking[1]}",
        }

    if fb.score_a is None or fb.score_b is None:
        raise HTTPException(400, "score mode requires score_a and score_b")
    if not (1 <= fb.score_a <= 5 and 1 <= fb.score_b <= 5):
        raise HTTPException(400, "scores must be between 1 and 5")
    chosen = "A" if fb.score_a > fb.score_b else "B" if fb.score_b > fb.score_a else None
    gap = abs(fb.score_a - fb.score_b)
    reliability = 0.55 if gap == 0 else min(0.9, 0.55 + 0.1 * gap)
    return chosen, reliability, {
        "mode": "score",
        "selected": chosen,
        "score_a": fb.score_a,
        "score_b": fb.score_b,
        "summary": f"user scored A={fb.score_a}, B={fb.score_b}",
    }


def _boost_from_note(profile: UserProfile, note: str, reliability: float) -> None:
    text = note.lower()
    boosts: dict[str, float] = {}
    if any(word in text for word in ("concise", "short", "brief", "direct")):
        boosts["prefers_concise"] = 1.0 + 0.25 * reliability
    if any(word in text for word in ("detail", "detailed", "thorough", "depth", "complete")):
        boosts["prefers_detailed"] = 1.0 + 0.25 * reliability
    if any(word in text for word in ("repetition", "repetitive", "redundant")):
        boosts["prefers_less_repetition"] = 1.0 + 0.25 * reliability
    if "simple" in text and "complex" in text:
        boosts["concise_simple_detailed_complex"] = 1.0 + 0.35 * reliability
    if not boosts:
        return
    for key, factor in boosts.items():
        profile.weights[key] *= factor
    profile._normalize()


def _predict_accuracy(profile: UserProfile, eval_events: list[dict]) -> float:
    labeled = [event for event in eval_events if event.get("selected") in {"A", "B"}]
    if not labeled:
        return 0.0
    correct = 0
    for event in labeled:
        fa = Features.of(event["answer_a"])
        fb = Features.of(event["answer_b"])
        predicted = profile.predict(fa, fb, event["complexity"])
        if predicted == event["selected"]:
            correct += 1
    return correct / len(labeled)


def _replay_method(method: str, train_events: list[dict], eval_events: list[dict]) -> dict:
    profile = UserProfile(user_id=f"sim-{method}")
    curve = [{"after": 0, "accuracy": round(_predict_accuracy(profile, eval_events), 4)}]

    for step, event in enumerate(train_events, start=1):
        selected = event.get("selected")
        reliability = float(event.get("confidence", 1.0))
        fa = Features.of(event["answer_a"])
        fb = Features.of(event["answer_b"])

        if selected in {"A", "B"}:
            effective_reliability = reliability
            if method == "winner_only":
                effective_reliability = 1.0 if event["feedback_mode"] in {"best", "ranking"} else 0.75
            profile.observe(
                fa,
                fb,
                selected,
                event["complexity"],
                reliability=effective_reliability,
                answer_a=event["answer_a"],
                answer_b=event["answer_b"],
            )

        if method == "note_aware":
            _boost_from_note(profile, event.get("free_text", ""), reliability)

        curve.append({"after": step, "accuracy": round(_predict_accuracy(profile, eval_events), 4)})

    final_accuracy = curve[-1]["accuracy"] if curve else 0.0
    baseline_accuracy = curve[0]["accuracy"] if curve else 0.0
    top_hypothesis, top_weight = profile.top_hypothesis()
    return {
        "method": method,
        "description": _SIM_METHODS[method],
        "train_events": len(train_events),
        "eval_events": len([event for event in eval_events if event.get("selected") in {"A", "B"}]),
        "baseline_accuracy": baseline_accuracy,
        "final_accuracy": final_accuracy,
        "delta_pp": round((final_accuracy - baseline_accuracy) * 100, 1),
        "curve": curve,
        "top_hypothesis": top_hypothesis,
        "top_weight": round(top_weight, 3),
        "feedback_modes": sorted({event["feedback_mode"] for event in train_events}),
    }


@app.post("/api/preference/feedback")
def feedback(fb: Feedback) -> dict:
    """Record the user's pick, update the learned preference, report what changed."""
    if not (0 <= fb.index < len(_PAIRS)):
        raise HTTPException(400, "bad feedback index")
    a, b, tt = _PAIRS[fb.index]
    fa, fb_feat = Features.of(a), Features.of(b)
    cx = _complexity_of(tt)
    chosen, reliability, details = _normalize_feedback(fb)
    predicted = _profile.predict(fa, fb_feat, cx)          # before learning

    if chosen is not None:
        _profile.observe(
            fa,
            fb_feat,
            chosen,
            cx,
            reliability=reliability,
            answer_a=a,
            answer_b=b,
        )
        _profile.save(_PROFILE_PATH)  # persist so subsequent judge runs use it

    event = FeedbackEvent(
        case_id=f"pair-{fb.index}",
        task_type=tt,
        feedback_type="pairwise_choice" if fb.feedback_mode in {"best", "ranking"} else "rating",
        selected=chosen,
        free_text=fb.note,
        confidence=reliability,
    )
    _events.append(
        {
            "case_id": event.case_id,
            "task_type": tt,
            "answer_a": a,
            "answer_b": b,
            "complexity": cx,
            "feedback_mode": fb.feedback_mode,
            "selected": chosen,
            "ranking": fb.ranking,
            "score_a": fb.score_a,
            "score_b": fb.score_b,
            "confidence": round(reliability, 2),
            "summary": details["summary"],
            "note": fb.note,
            # This is the normalized training signal later loops can consume.
            "loop_ready": {
                "case_id": event.case_id,
                "task_type": tt,
                "complexity": cx,
                "feedback_type": event.feedback_type,
                "selected": chosen,
                "score_a": fb.score_a,
                "score_b": fb.score_b,
                "confidence": round(reliability, 2),
                "answer_a": a,
                "answer_b": b,
                "free_text": fb.note,
            },
        }
    )
    _seen.add(fb.index)
    h, w = _profile.top_hypothesis()
    return {
        "you_chose": chosen,
        "judy_predicted": predicted,
        "was_correct": chosen is not None and predicted == chosen,
        "inferred_preference": h,
        "confidence": round(w, 2),
        "n_feedback": len(_seen),
        "feedback_mode": fb.feedback_mode,
        "feedback_summary": details["summary"],
        "loop_ready": _events[-1]["loop_ready"],
    }


@app.get("/api/preference/state")
def pref_state() -> dict:
    h, w = _profile.top_hypothesis()
    return {
        "inferred_preference": h,
        "confidence": round(w, 2),
        "weights": {k: round(v, 3) for k, v in _profile.weights.items()},
        "n_feedback": len(_seen),
        "feedback_modes_seen": sorted({event["feedback_mode"] for event in _events}),
        "recent_events": _events[-5:],
    }


@app.get("/api/preference/loop-ready")
def pref_loop_ready() -> dict:
    return {
        "events": [event["loop_ready"] for event in _events],
        "how_to_use": [
            "pairwise/ranking selections can be used as anchored winner labels for recursive judge updates",
            "absolute scores can be converted into weighted pairwise preference signals using the score gap as confidence",
            "free-text notes can be summarized into task-general lessons for policy rewriting",
        ],
    }


@app.get("/api/preference/simulate-run")
def pref_simulate_run() -> dict:
    labeled = [event for event in _events if event.get("selected") in {"A", "B"}]
    if len(labeled) < 4:
        raise HTTPException(400, "Need at least 4 labeled feedback events to simulate a run.")

    split = max(3, int(len(labeled) * 0.7))
    split = min(split, len(labeled) - 1)
    train_events = labeled[:split]
    eval_events = labeled[split:]

    results = [
        _replay_method(method, train_events, eval_events)
        for method in _SIM_METHODS
    ]
    best = max(results, key=lambda result: result["final_accuracy"])
    return {
        "train_events": len(train_events),
        "eval_events": len(eval_events),
        "results": results,
        "best_method": best["method"],
        "best_delta_pp": best["delta_pp"],
        "summary": (
            "This simulates recursive improvement by replaying collected user feedback as training data, "
            "then evaluating the learned preference model on held-out user-labeled events."
        ),
    }


@app.post("/api/preference/reset")
def pref_reset() -> dict:
    global _profile, _seen, _events
    _profile, _seen, _events = UserProfile(user_id="demo"), set(), []
    _PROFILE_PATH.unlink(missing_ok=True)
    return {"ok": True}


# === 2) Performance gains (static results + curves) =============================

def _read_json(path: Path) -> dict | list:
    if not path.exists():
        raise HTTPException(404, f"{path.name} not found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/experiments")
def experiments() -> dict | list:
    return _read_json(_UI_PUBLIC / "experiments.json")


@app.get("/api/curves")
def curves() -> dict | list:
    return _read_json(_UI_PUBLIC / "curves" / "index.json")


@app.get("/api/curves/{run_id}")
def curve(run_id: str) -> dict | list:
    return _read_json(_UI_PUBLIC / "curves" / f"{run_id}.json")


# === 3) Live single judgment (Try Judy) — uses Gemini, costs credits ============

class JudgeReq(BaseModel):
    system_prompt: str = ""
    question: str
    answer_a: str
    answer_b: str


@app.post("/api/judge")
async def judge(req: JudgeReq) -> dict:
    client = GeminiClient()
    policy = load_skill(CONFIG.skill_path)
    # Condition the judge on the learned user preference (only once we have signal),
    # so accumulated feedback actually changes subsequent judgments.
    applied = _profile.has_signal()
    system = policy
    if applied:
        system = (
            f"{policy}\n\n## Learned user preference (from this user's feedback)\n"
            f"{_profile.render_context()}"
        )
    prompt = build_user_prompt(req.system_prompt or _GENERIC_SPEC, req.question, req.answer_a, req.answer_b)
    data = await client.generate_json(prompt, system_instruction=system)
    v = _coerce_verdict(data)
    return {"verdict": v.verdict, "margin": v.margin, "rationale": v.rationale,
            "criteria": [c.model_dump() for c in v.criteria],
            "preference_applied": applied,
            "inferred_preference": _profile.top_hypothesis()[0] if applied else None,
            "cost": client.usage.as_dict()}
