"""Build a judge prompt from the policy + an item, call the model, parse a verdict.

The policy (``SKILL.md``) is passed as the model's *system instruction* so it
forms a stable prefix (cache-friendly, brief §6). The user message carries only
what the judge is allowed to see: the task spec, the question, and the two
answers as A/B. Order-swap is handled here and the verdict is normalized back to
canonical orientation (A = candidates[0]).
"""

from __future__ import annotations

from typing import Any

from judy.judge.schema import Item, JudgeRecord, Side, Verdict
from judy.llm.gemini import GeminiClient

_OUTPUT_SPEC = (
    'Return JSON only: {"verdict":"A"|"B","margin":1-5,'
    '"rationale":"<=40 words","criteria":[{"name":str,"winner":"A"|"B"|"tie"}]}'
)


def build_user_prompt(system_prompt: str, question: str, answer_a: str, answer_b: str) -> str:
    """Assemble the judge's user message. Reused by the live /judge endpoint."""
    return (
        "SYSTEM PROMPT (the task spec to judge against):\n"
        f"{system_prompt}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"ANSWER A:\n{answer_a}\n\n"
        f"ANSWER B:\n{answer_b}\n\n"
        f"{_OUTPUT_SPEC}"
    )


def _to_canonical(presented: Side, swap: bool) -> Side:
    """Map a verdict expressed over presented A/B back to canonical sides."""
    if not swap:
        return presented
    return "B" if presented == "A" else "A"


def _coerce_verdict(data: dict[str, Any]) -> Verdict:
    """Normalize loosely-shaped model output into a valid Verdict."""
    verdict = str(data.get("verdict", "A")).strip().upper()
    verdict = verdict if verdict in {"A", "B"} else "A"
    try:
        margin = int(data.get("margin", 3))
    except (TypeError, ValueError):
        margin = 3
    margin = max(1, min(5, margin))
    criteria = data.get("criteria") or []
    if not isinstance(criteria, list):
        criteria = []
    return Verdict(
        verdict=verdict,
        margin=margin,
        rationale=str(data.get("rationale", ""))[:400],
        criteria=criteria,
    )


async def judge_item(
    client: GeminiClient, skill_text: str, item: Item, *, swap: bool = False
) -> JudgeRecord:
    """Judge a single item; returns a canonical-orientation record."""
    a_idx, b_idx = (1, 0) if swap else (0, 1)
    prompt = build_user_prompt(
        item.system_prompt,
        item.question,
        item.candidates[a_idx].text,
        item.candidates[b_idx].text,
    )
    data = await client.generate_json(prompt, system_instruction=skill_text, temperature=0.0)
    verdict = _coerce_verdict(data)
    canonical = _to_canonical(verdict.verdict, swap)
    return JudgeRecord(
        item_id=item.id,
        task_type=item.task_type,
        swap=swap,
        verdict=canonical,
        margin=verdict.margin,
        rationale=verdict.rationale,
        criteria=verdict.criteria,
        correct=item.is_correct(canonical),
    )
