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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from judy.config import CONFIG
from judy.judge.judge import _coerce_verdict, build_user_prompt
from judy.judge.skill import load_skill
from judy.llm.gemini import GeminiClient
from judy.preference.profile import UserProfile
from judy.preference.session import make_style_pairs
from judy.preference.simulated_user import Features

app = FastAPI(title="Judy API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_UI_PUBLIC = CONFIG.runs_dir.parent / "ui/public"
_GENERIC_SPEC = "Answer the user's question as helpfully, correctly, and completely as possible."

# --- Demo session state (single in-memory profile; reset endpoint provided) -----
_PAIRS = make_style_pairs(24, seed=1)
_profile = UserProfile(user_id="demo")
_seen: set[int] = set()


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
    chosen: str  # "A" | "B"


@app.post("/api/preference/feedback")
def feedback(fb: Feedback) -> dict:
    """Record the user's pick, update the learned preference, report what changed."""
    if not (0 <= fb.index < len(_PAIRS)) or fb.chosen not in ("A", "B"):
        raise HTTPException(400, "bad feedback")
    a, b, tt = _PAIRS[fb.index]
    fa, fb_feat = Features.of(a), Features.of(b)
    cx = "complex" if tt == "complex_q" else "simple"
    predicted = _profile.predict(fa, fb_feat, cx)          # before learning
    _profile.observe(fa, fb_feat, fb.chosen, cx, answer_a=a, answer_b=b)
    _seen.add(fb.index)
    h, w = _profile.top_hypothesis()
    return {
        "you_chose": fb.chosen,
        "judy_predicted": predicted,
        "was_correct": predicted == fb.chosen,
        "inferred_preference": h,
        "confidence": round(w, 2),
        "n_feedback": len(_seen),
    }


@app.get("/api/preference/state")
def pref_state() -> dict:
    h, w = _profile.top_hypothesis()
    return {"inferred_preference": h, "confidence": round(w, 2),
            "weights": {k: round(v, 3) for k, v in _profile.weights.items()},
            "n_feedback": len(_seen)}


@app.post("/api/preference/reset")
def pref_reset() -> dict:
    global _profile, _seen
    _profile, _seen = UserProfile(user_id="demo"), set()
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
    prompt = build_user_prompt(req.system_prompt or _GENERIC_SPEC, req.question, req.answer_a, req.answer_b)
    data = await client.generate_json(prompt, system_instruction=policy)
    v = _coerce_verdict(data)
    return {"verdict": v.verdict, "margin": v.margin, "rationale": v.rationale,
            "criteria": [c.model_dump() for c in v.criteria], "cost": client.usage.as_dict()}
