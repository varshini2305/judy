"""Reflect on judging errors and propose task-GENERAL policy edits (brief §4).

A single Gemini call takes the current policy plus a compact list of mistakes
and returns lessons to append to ``SKILL.md``. The hard constraint — enforced in
the prompt — is that every lesson must generalize to *any* spec; task-specific
edits ("for travel questions, prefer X") overfit and are rejected.
"""

from __future__ import annotations

import json

from judy.judge.schema import Item, JudgeRecord
from judy.judge.skill import (
    FAILURE_MODES_HEADER,
    STRATEGIES_HEADER,
    append_bullets,
    approx_tokens,
)
from judy.llm.gemini import GeminiClient

_SIDE_IDX = {"A": 0, "B": 1}
_MAX_ERROR_BLOCKS = 12

_WHY = {
    "A": "faithful (correct and fully spec-compliant)",
    "B": "correct but thin / incomplete",
    "C": "a plausible failure (fluent but factually wrong OR spec-violating)",
    "D": "off-topic / a non-answer",
}

_RULES = """Propose lessons to add to the policy. CRITICAL RULES:
- Every lesson must be TASK-GENERAL: about how to judge ANY spec, never specific to these topics/domains.
- Be concrete and actionable (e.g. "when one answer is fluent but the spec requires a citation, missing citations lose").
- Do not restate lessons already in the policy.

Return JSON only:
{{"failure_modes": [<=3 short general lessons], "strategies": [<=2 general tactics], "procedure_edits": [<=2 optional]}}"""

# Anchored: real ground-truth signal (the judge picked the worse answer).
_ANCHORED_PROMPT = (
    "You are improving the policy of a pairwise QA judge by learning from its mistakes.\n\n"
    "Current policy:\n---\n{skill}\n---\n\n"
    "The judge got these comparisons WRONG (it picked the worse answer):\n{errors}\n\n" + _RULES
)

# Unanchored: NO ground truth — only the judge's own self-inconsistency.
_UNANCHORED_PROMPT = (
    "You are improving the policy of a pairwise QA judge using only its own self-consistency.\n\n"
    "Current policy:\n---\n{skill}\n---\n\n"
    "On these comparisons the judge gave DIFFERENT verdicts depending on answer order — "
    "a sign its reasoning is unstable (no ground truth is available):\n{errors}\n\n" + _RULES
)


def _why_better(winner_tier: str, loser_tier: str) -> str:
    return f"the better answer is {_WHY.get(winner_tier, '?')}; the other is {_WHY.get(loser_tier, '?')}"


def build_error_blocks(
    records: list[JudgeRecord], items: dict[str, Item], *, anchored: bool
) -> str:
    """Render a compact, token-bounded list of problem comparisons.

    Anchored blocks reveal which answer was actually better; unanchored blocks
    never do — they only show the spec, both answers, and the judge's reason.
    """
    blocks: list[str] = []
    for r in records[:_MAX_ERROR_BLOCKS]:
        item = items[r.item_id]
        picked = item.candidates[_SIDE_IDX[r.verdict]].text
        block = (
            f"- Spec: {item.system_prompt[:300]}\n"
            f"  Judge picked: {picked[:220]}\n"
            f"  Judge's reason: {r.rationale[:160]}"
        )
        if anchored:
            better = item.candidates[_SIDE_IDX[item.correct_side()]].text
            w, l = item.known_ordering
            block += f"\n  Actually better: {better[:220]}\n  Why: {_why_better(w, l)}"
        else:
            other = item.candidates[_SIDE_IDX['B' if r.verdict == 'A' else 'A']].text
            block += f"\n  The other answer: {other[:220]}"
        blocks.append(block)
    return "\n".join(blocks)


async def reflect(
    client: GeminiClient,
    skill_text: str,
    errors: list[JudgeRecord],
    items: dict[str, Item],
    *,
    anchored: bool = True,
) -> dict[str, list[str]]:
    """One reflection call → proposed edits dict (may be empty if no errors)."""
    if not errors:
        return {"failure_modes": [], "strategies": [], "procedure_edits": []}
    template = _ANCHORED_PROMPT if anchored else _UNANCHORED_PROMPT
    prompt = template.format(
        skill=skill_text, errors=build_error_blocks(errors, items, anchored=anchored)
    )
    data = await client.generate_json(prompt, temperature=0.3)
    return {
        "failure_modes": _as_str_list(data.get("failure_modes"))[:3],
        "strategies": _as_str_list(data.get("strategies"))[:2],
        "procedure_edits": _as_str_list(data.get("procedure_edits"))[:2],
    }


def apply_edits(skill_text: str, edits: dict[str, list[str]], token_budget: int) -> str:
    """Append edits to the policy, respecting the token budget (best-effort)."""
    updated = append_bullets(skill_text, FAILURE_MODES_HEADER, edits.get("failure_modes", []))
    strategies = list(edits.get("strategies", [])) + [
        f"Procedure: {p}" for p in edits.get("procedure_edits", [])
    ]
    updated = append_bullets(updated, STRATEGIES_HEADER, strategies)
    if approx_tokens(updated) > token_budget:
        # Over budget: keep the prior version rather than bloat the prefix.
        return skill_text
    return updated


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]
