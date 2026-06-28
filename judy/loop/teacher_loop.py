"""V5 — cross-family teacher-driven continual learning.

A Gemini student judges; an OpenAI teacher (gpt-5.4-nano), given the answer key,
diagnoses why the student erred and returns a task-general lesson. The student's
context grows on TWO channels after each mini-batch: (1) lessons (principle +
procedure) appended to its policy, and (2) the corrected case kept in a bounded
few-shot example bank. Held-out accuracy is checkpointed across the stream to
plot the learning curve.

The teacher is any object with ``generate_json`` (real = OpenAIClient; stub for
offline tests). Run wiring lives in a separate entry once OPENAI_API_KEY works.
"""

from __future__ import annotations

from typing import Callable

from judy.config import CONFIG
from judy.judge.judge import judge_item
from judy.judge.schema import Item, JudgeRecord
from judy.judge.skill import (
    FAILURE_MODES_HEADER,
    STRATEGIES_HEADER,
    append_bullets,
    approx_tokens,
)
from judy.eval.harness import eval_split
from judy.metrics.metrics import compute_metrics

Progress = Callable[[str], None]
_SIDE = {"A": 0, "B": 1}
_EXAMPLE_BANK_K = 4  # most-recent corrected cases shown as few-shot

_TEACHER_PROMPT = """A student judge compared two answers to a question and chose one. You have the answer key.

TASK SPEC: {spec}
QUESTION: {question}
ANSWER A: {a}
ANSWER B: {b}

GROUND TRUTH: answer {correct} is the better one.
STUDENT VERDICT: {verdict} (margin {margin})
STUDENT RATIONALE: {rationale}

Diagnose why the student was right or wrong and teach a task-general lesson per your policy. Return JSON only."""


async def teacher_critique(teacher, teacher_policy: str, item: Item, rec: JudgeRecord) -> dict:
    prompt = _TEACHER_PROMPT.format(
        spec=item.system_prompt[:500], question=item.question[:500],
        a=item.candidates[0].text[:500], b=item.candidates[1].text[:500],
        correct=item.correct_side(), verdict=rec.verdict, margin=rec.margin,
        rationale=rec.rationale[:200],
    )
    return await teacher.generate_json(prompt, system_instruction=teacher_policy)


def build_student_context(base_policy: str, bank: list[dict]) -> str:
    """Student system instruction = evolving policy + bounded few-shot examples."""
    if not bank:
        return base_policy
    lines = [
        f"- Q: {e['q'][:140]} -> better answer: {e['correct'][:160]} (because {e['why'][:120]})"
        for e in bank[-_EXAMPLE_BANK_K:]
    ]
    return base_policy.rstrip() + "\n\n## Cases you previously misjudged (learn from these)\n" + "\n".join(lines) + "\n"


def _apply_lesson(policy: str, lesson: dict) -> str:
    principle = str(lesson.get("principle", "")).strip()
    procedure = str(lesson.get("procedure", "")).strip()
    if principle and approx_tokens(policy) < CONFIG.skill_token_budget:
        policy = append_bullets(policy, FAILURE_MODES_HEADER, [principle])
    if procedure and approx_tokens(policy) < CONFIG.skill_token_budget:
        policy = append_bullets(policy, STRATEGIES_HEADER, [procedure])
    return policy


async def run_teacher_continual(
    student,
    teacher,
    dev_items: list[Item],
    held_items: list[Item],
    *,
    base_policy: str,
    teacher_policy: str,
    batch_size: int | None = None,
    checkpoint_every: int = 10,
    progress: Progress = lambda _m: None,
) -> dict:
    """Stream dev; teacher-critique errors every batch; grow lessons + example bank.
    Returns final policy, snapshots, example bank, critiques, and the held-out curve.
    """
    batch_size = batch_size or CONFIG.continual_batch_size
    policy = base_policy
    bank: list[dict] = []
    snapshots = [policy]
    critiques: list[dict] = []
    curve: list[dict] = []

    async def held_agreement() -> float:
        recs = await eval_split(student, build_student_context(policy, bank), held_items, order_swap=True)
        return compute_metrics(recs).agreement

    curve.append({"after": 0, "agreement": await held_agreement()})
    batch: list[tuple[Item, JudgeRecord]] = []

    async def learn(pairs: list[tuple[Item, JudgeRecord]]) -> None:
        nonlocal policy
        for item, rec in pairs:
            if rec.correct:
                continue
            lesson = await teacher_critique(teacher, teacher_policy, item, rec)
            policy = _apply_lesson(policy, lesson)
            bank.append({
                "q": item.question,
                "correct": item.candidates[_SIDE[item.correct_side()]].text,
                "why": str(lesson.get("why_correct_is_better", "")),
            })
            critiques.append({"item_id": item.id, **lesson})
        snapshots.append(policy)

    for i, item in enumerate(dev_items):
        rec = await judge_item(student, build_student_context(policy, bank), item, swap=False)
        batch.append((item, rec))
        if len(batch) >= batch_size:
            await learn(batch)
            batch = []
            if checkpoint_every and (i + 1) % checkpoint_every == 0:
                agr = await held_agreement()
                curve.append({"after": i + 1, "agreement": agr})
                progress(f"  {i + 1}/{len(dev_items)} streamed · held-out {agr:.1%}")
    if batch:
        await learn(batch)

    final = await eval_split(student, build_student_context(policy, bank), held_items, order_swap=True)
    curve.append({"after": len(dev_items), "agreement": compute_metrics(final).agreement})
    return {
        "final_policy": policy,
        "snapshots": snapshots,
        "example_bank": bank,
        "critiques": critiques,
        "curve": curve,
        "held_final": compute_metrics(final).model_dump(),
    }
