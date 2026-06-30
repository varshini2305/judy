"""Disagreement-driven self-improvement for the LLM judge.

The loop: the judge evaluates a pair, we compare to the user's choice, and on a
DISAGREEMENT the judge reasons about *why* and triages the disagreement:

- **taste**  — a subjective style preference (both answers acceptable). Stored as a
  per-user note (does NOT change the shared policy → no overfitting one user).
- **flaw**   — a genuine evaluation error (missed a requirement, rewarded fluency
  over correctness). Proposed as a *task-general* lesson, staged for the global
  policy behind a gate (never auto-written).

This is the triage that lets user feedback improve the judge without baking one
user's taste into everyone's judge. Everything here is context engineering — no
weight updates.
"""

from __future__ import annotations

from judy.judge.judge import _coerce_verdict, build_user_prompt
from judy.judge.schema import Side

_SPEC = "Answer the user's request as helpfully, correctly, and completely as possible."
_QUESTION = "Decide which answer better serves the user's request."


async def judge_pair(client, system_instruction: str, answer_a: str, answer_b: str) -> tuple[Side, str]:
    """Run the judge over a presented A/B pair; return (verdict, rationale)."""
    prompt = build_user_prompt(_SPEC, _QUESTION, answer_a, answer_b)
    data = await client.generate_json(prompt, system_instruction=system_instruction, temperature=0.0)
    verdict = _coerce_verdict(data)
    return verdict.verdict, verdict.rationale


# The concrete "how to use this feedback" instruction — the triage prompt.
_TRIAGE = """An LLM judge and a human evaluator DISAGREED on which answer is better.
Decide how the judge should use this, WITHOUT overfitting to one person.

ANSWER A:
{answer_a}

ANSWER B:
{answer_b}

The judge chose {judge_verdict}. Judge's reasoning: {judge_rationale}
The human chose {user_choice}.{user_reason}

Classify the disagreement:
- "taste": both answers are acceptable; the human just prefers a style (length, tone,
  format, verbosity, directness). This must NOT change how the judge scores everyone.
- "flaw": the judge made a real evaluation error (missed a requirement, rewarded
  fluency/length over correctness, misread the task). This is a generalizable lesson.

Rules:
- taste -> write a SHORT note about THIS user's preference, general enough to reuse
  (e.g. "prefers concise answers even when more detail is available"). No topic specifics.
- flaw -> write ONE TASK-GENERAL lesson for judging ANY task. No topic specifics.
- If genuinely unclear, use "unclear" and leave both empty. Do not invent a flaw.

Return JSON only:
{{"kind": "taste"|"flaw"|"unclear", "preference_note": "", "general_lesson": "", "explanation": "<=25 words"}}"""


async def reason_disagreement(
    client,
    *,
    answer_a: str,
    answer_b: str,
    judge_verdict: str,
    judge_rationale: str,
    user_choice: str,
    user_rationale: str = "",
) -> dict:
    """Triage a judge/user disagreement into a taste note or a general lesson."""
    user_reason = f"\nThe human's stated reason: {user_rationale}" if user_rationale.strip() else ""
    prompt = _TRIAGE.format(
        answer_a=answer_a[:600], answer_b=answer_b[:600],
        judge_verdict=judge_verdict, judge_rationale=judge_rationale[:300],
        user_choice=user_choice, user_reason=user_reason,
    )
    data = await client.generate_json(prompt, temperature=0.3)
    kind = str(data.get("kind", "unclear")).strip().lower()
    if kind not in {"taste", "flaw", "unclear"}:
        kind = "unclear"
    return {
        "kind": kind,
        "preference_note": str(data.get("preference_note", "")).strip(),
        "general_lesson": str(data.get("general_lesson", "")).strip(),
        "explanation": str(data.get("explanation", "")).strip(),
    }
