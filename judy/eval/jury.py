"""V4 — continually self-improving judge-and-jury for subjective preference.

The idea this variant tests: when a task is *subjective* (creative writing),
there is no single ground truth — different users genuinely disagree. A single
judge can match at most one point of that distribution. A **jury of per-user
jurors** can model each user individually:

- The **judge** owns a shared evaluation structure (the aesthetic axes that
  creative pieces vary on) and guides every juror — ``SHARED_CREATIVE_RUBRIC``.
- Each **juror** is assigned one user (persona) and *learns that user's taste*
  from the user's TRAINING labels via preference-reflection, then predicts the
  user's held-out TEST preferences.

We compare:
- **B0** — one generic judge, scored against every user (the baseline to beat).
- **V4** — per-user jurors, each scored against its own user.

Headline metrics: mean per-user test agreement (V4 vs B0) and the
**personalization matrix** ``agree(juror_i, user_j)`` whose diagonal should
dominate — strong, falsifiable evidence that jurors capture user-specific taste.

Model is held constant at ``gemini-3.5-flash`` (only the method changes).
Learn on TRAIN labels, measure on TEST labels (disjoint by item).

Run: ``PYTHONPATH=. python -m judy.eval.jury``
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from judy.config import CONFIG
from judy.data.personas import PERSONAS, PERSONAS_BY_ID, Persona
from judy.eval.harness import eval_split
from judy.judge.judge import judge_item
from judy.judge.schema import Candidate, Item, JudgeRecord, Side
from judy.judge.skill import FAILURE_MODES_HEADER, STRATEGIES_HEADER
from judy.llm.gemini import GeminiClient
from judy.loop.reflect import apply_edits
from judy.metrics.metrics import compute_metrics

DEFAULT_DATASET = CONFIG.runs_dir.parent / "judy/data/datasets/creative_pref_benchmark.jsonl"

# B0: a single generic judge of creative writing. It has no notion of *whose*
# taste it serves, so it can match at most one point of the preference spread.
B0_POLICY = (
    "You are an impartial judge of creative writing. Given a writing task and two "
    "pieces (A and B), decide which piece is better overall. Judge holistically and "
    "return only the requested JSON."
)

# The judge's shared guidance to every juror: the aesthetic axes creative work
# varies on, plus the job (model THIS reader's taste) and a position-bias guard.
# Jurors append user-specific taste lessons to the two sections below.
SHARED_CREATIVE_RUBRIC = f"""You are a juror modelling ONE specific reader's taste in creative writing.
Creative quality is subjective; your job is NOT to pick the objectively better
piece but the piece THIS reader would prefer.

Read both pieces along these aesthetic axes, then apply this reader's taste:
- imagery: concrete sensory detail and fresh metaphor vs abstraction/cliché
- form: meter, rhyme, classical structure vs free verse / modern diction
- economy: brevity and restraint vs richness and ornament
- emotion: earnest intensity and personal voice vs cool, ironic detachment
- diction: archaic/elevated vs plain/contemporary/experimental

Position guard: your verdict must not depend on whether a piece is shown as A or B.

{FAILURE_MODES_HEADER}
(none yet — this reader's dislikes are learned from examples)

{STRATEGIES_HEADER}
(none yet — this reader's preferences are learned from examples)
"""

_SIDE_IDX = {"A": 0, "B": 1}


# --------------------------------------------------------------------------- #
# Dataset → Items
# --------------------------------------------------------------------------- #
def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def persona_item(row: dict, persona_id: str) -> Item:
    """Build an Item whose ``correct`` side is the persona's preferred piece.

    answer_a is always canonical candidate[0]; we set tiers so that the
    persona's preferred side is the higher tier — letting us reuse ``judge_item``,
    ``is_correct`` and ``compute_metrics`` to score agreement with that user.
    """
    pref: Side = row["labels"][persona_id]["preferred"]
    tier_a, tier_b = ("A", "C") if pref == "A" else ("C", "A")
    return Item(
        id=row["id"],
        task_type=row.get("form", "creative"),
        system_prompt=row["system_prompt"],
        question=row["question"],
        gold_answer="",
        candidates=[Candidate(tier=tier_a, text=row["answer_a"]),
                    Candidate(tier=tier_b, text=row["answer_b"])],
        known_ordering=("A", "C"),
    )


# --------------------------------------------------------------------------- #
# Verdict capture + persona-agnostic scoring (for B0 and the matrix)
# --------------------------------------------------------------------------- #
async def collect_verdicts(client: GeminiClient, policy: str, rows: list[dict],
                           *, order_swap: bool) -> list[tuple[str, bool, Side]]:
    """Judge each row (canonical/swap) with ``policy``; return (item_id, swap, verdict).

    Verdicts are persona-independent, so one pass can be scored against any user.
    """
    neutral = [persona_item(r, PERSONAS[0].id) for r in rows]  # tiers irrelevant here
    records = await eval_split(client, policy, neutral, order_swap=order_swap)
    return [(r.item_id, r.swap, r.verdict) for r in records]


def score_against(verdicts: list[tuple[str, bool, Side]], rows: list[dict],
                  persona_id: str):
    """Turn captured verdicts into JudgeRecords scored vs one persona; metrics."""
    pref_by_id = {r["id"]: r["labels"][persona_id]["preferred"] for r in rows}
    form_by_id = {r["id"]: r.get("form", "creative") for r in rows}
    recs = [
        JudgeRecord(
            item_id=iid, task_type=form_by_id[iid], swap=swap, verdict=verdict,
            margin=3, rationale="", correct=(verdict == pref_by_id[iid]),
        )
        for iid, swap, verdict in verdicts
    ]
    return compute_metrics(recs)


# --------------------------------------------------------------------------- #
# Preference-aware reflection (learn ONE user's taste from disagreements)
# --------------------------------------------------------------------------- #
_PERSONA_REFLECT = """You are learning ONE specific reader's subjective taste in creative writing
so you can predict their preferences. Below are pieces where you predicted the
WRONG one — the reader actually preferred the other. Infer what this reader
values and dislikes.

Current notes on this reader:
---
{skill}
---

Mispredictions (the reader preferred the piece marked PREFERRED):
{errors}

Write general lessons about THIS reader's taste (not about these specific poems).
Return JSON only:
{{"failure_modes": [<=3 things this reader dislikes/penalises], "strategies": [<=2 things this reader prefers], "procedure_edits": []}}"""


def _error_blocks(records: list[JudgeRecord], rows_by_id: dict[str, dict],
                  persona_id: str) -> str:
    blocks = []
    for r in records:
        row = rows_by_id[r.item_id]
        lab = row["labels"][persona_id]
        pref_text = row["answer_a"] if lab["preferred"] == "A" else row["answer_b"]
        other_text = row["answer_b"] if lab["preferred"] == "A" else row["answer_a"]
        blocks.append(
            f"- Task: {row['system_prompt'][:140]}\n"
            f"  PREFERRED (this reader): {pref_text[:240]}\n"
            f"  Not preferred: {other_text[:240]}\n"
            f"  Reader's reason: {lab.get('rationale', '')[:140]}"
        )
    return "\n".join(blocks)


async def persona_reflect(client: GeminiClient, skill: str, errors: list[JudgeRecord],
                          rows_by_id: dict[str, dict], persona_id: str) -> dict:
    if not errors:
        return {"failure_modes": [], "strategies": [], "procedure_edits": []}
    prompt = _PERSONA_REFLECT.format(
        skill=skill, errors=_error_blocks(errors, rows_by_id, persona_id))
    data = await client.generate_json(prompt, temperature=0.3)
    return {
        "failure_modes": _as_list(data.get("failure_modes"))[:3],
        "strategies": _as_list(data.get("strategies"))[:2],
        "procedure_edits": [],
    }


def _as_list(value: object) -> list[str]:
    return [str(v).strip() for v in value if str(v).strip()] if isinstance(value, list) else []


# --------------------------------------------------------------------------- #
# Few-shot conditioning (model a user directly from their TRAIN labels)
# --------------------------------------------------------------------------- #
def build_fewshot_policy(train_rows: list[dict], persona_id: str, *, k: int = 10) -> str:
    """Condition a juror on its user's actual choices — no reflection, no calls.

    Faithfully shows the user's TRAIN preferences (which piece they chose + their
    reason) as exemplars, so the juror imitates *this* user rather than distilling
    a lossy, blended rule set. This is the 'few-shot error-memory' style of
    personalisation and is cheaper than the reflection loop.
    """
    blocks = []
    for r in train_rows[:k]:
        lab = r["labels"][persona_id]
        chose, other = ("A", "B") if lab["preferred"] == "A" else ("B", "A")
        blocks.append(
            f"- Task: {r['system_prompt'][:120]}\n"
            f"  Piece {chose} (CHOSEN): {(r['answer_a'] if chose=='A' else r['answer_b'])[:160]}\n"
            f"  Piece {other}: {(r['answer_a'] if other=='A' else r['answer_b'])[:160]}\n"
            f"  This reader chose {chose} because: {lab.get('rationale','')[:120]}"
        )
    examples = "\n".join(blocks)
    return (
        SHARED_CREATIVE_RUBRIC
        + "\n\n## This reader's past choices (imitate this exact taste)\n"
        + examples
    )


# --------------------------------------------------------------------------- #
# Juror learning (continual, on TRAIN labels for one persona)
# --------------------------------------------------------------------------- #
async def learn_juror(client: GeminiClient, persona: Persona, train_rows: list[dict],
                      *, batch_size: int) -> tuple[str, int]:
    """Learn one persona's taste from its TRAIN labels. Returns (policy, n_updates)."""
    policy = SHARED_CREATIVE_RUBRIC
    rows_by_id = {r["id"]: r for r in train_rows}
    items = [persona_item(r, persona.id) for r in train_rows]
    batch: list[JudgeRecord] = []
    n_updates = 0

    async def flush() -> None:
        nonlocal policy, n_updates
        errors = [r for r in batch if not r.correct]
        if errors:
            edits = await persona_reflect(client, policy, errors, rows_by_id, persona.id)
            policy = apply_edits(policy, edits, CONFIG.skill_token_budget)
            n_updates += 1

    for item in items:
        rec = await judge_item(client, policy, item, swap=False)
        batch.append(rec)
        if len(batch) >= batch_size:
            await flush()
            batch = []
    if batch:
        await flush()
    return policy, n_updates


# --------------------------------------------------------------------------- #
# Top-level run
# --------------------------------------------------------------------------- #
async def run_jury(dataset: Path, *, batch_size: int | None = None,
                   juror_mode: str = "reflect", client=None) -> dict:
    batch_size = batch_size or CONFIG.continual_batch_size
    rows = load_rows(dataset)
    train_rows = [r for r in rows if r["split"] == "train"]
    test_rows = [r for r in rows if r["split"] == "test"]
    assert train_rows and test_rows, "dataset needs both train and test splits"
    assert juror_mode in {"reflect", "fewshot"}, juror_mode

    client = client or GeminiClient()

    # B0: one generic judge over the TEST items, scored against every user.
    b0_verdicts = await collect_verdicts(client, B0_POLICY, test_rows, order_swap=True)
    b0_by_user = {p.id: score_against(b0_verdicts, test_rows, p.id) for p in PERSONAS}

    # V4: learn one juror per user on TRAIN, then capture its TEST verdicts.
    jurors: dict[str, dict] = {}
    juror_verdicts: dict[str, list] = {}
    for persona in PERSONAS:
        if juror_mode == "fewshot":
            policy, n_updates = build_fewshot_policy(train_rows, persona.id), 0
        else:
            policy, n_updates = await learn_juror(client, persona, train_rows, batch_size=batch_size)
        verdicts = await collect_verdicts(client, policy, test_rows, order_swap=True)
        juror_verdicts[persona.id] = verdicts
        jurors[persona.id] = {"n_updates": n_updates, "policy": policy}

    # Personalization matrix: agree(juror_i, user_j); diagonal = V4 per-user score.
    matrix = {
        i: {j: score_against(juror_verdicts[i], test_rows, j).agreement for j in PERSONAS_BY_ID}
        for i in PERSONAS_BY_ID
    }
    v4_by_user = {p.id: score_against(juror_verdicts[p.id], test_rows, p.id) for p in PERSONAS}

    summary = {
        "dataset": str(dataset),
        "juror_mode": juror_mode,
        "n_train": len(train_rows), "n_test": len(test_rows), "n_personas": len(PERSONAS),
        "batch_size": batch_size,
        "b0_per_user": {p: m.agreement for p, m in b0_by_user.items()},
        "b0_mean_agreement": _mean(m.agreement for m in b0_by_user.values()),
        "b0_mean_pos_consistency": _mean(m.position_consistency or 0 for m in b0_by_user.values()),
        "v4_per_user": {p: m.agreement for p, m in v4_by_user.items()},
        "v4_mean_agreement": _mean(m.agreement for m in v4_by_user.values()),
        "v4_mean_pos_consistency": _mean(m.position_consistency or 0 for m in v4_by_user.values()),
        "v4_juror_updates": {p: jurors[p]["n_updates"] for p in jurors},
        "personalization_matrix": matrix,
        "matrix_diagonal_wins": _diagonal_wins(matrix),
        "usage": client.usage.as_dict(),
    }
    _persist(summary, jurors)
    _print(summary)
    return summary


def _mean(values) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def _diagonal_wins(matrix: dict) -> int:
    """How many jurors agree most with THEIR OWN user (diagonal is the row max)."""
    wins = 0
    for i, row in matrix.items():
        if row[i] >= max(row.values()):
            wins += 1
    return wins


def _persist(summary: dict, jurors: dict) -> None:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = CONFIG.runs_dir / f"jury-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    for pid, j in jurors.items():
        (run_dir / f"juror_{pid}.md").write_text(j["policy"], encoding="utf-8")
    summary["run_dir"] = str(run_dir)
    (run_dir / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _print(s: dict) -> None:
    print("\n=== V4 judge-jury vs B0 single judge (subjective creative preference) ===")
    print(f"  {s['n_personas']} users · train={s['n_train']} · test={s['n_test']} items\n")
    print(f"  {'user':14s}{'B0 agree':>10s}{'V4 agree':>10s}{'delta':>8s}")
    for p in s["b0_per_user"]:
        b, v = s["b0_per_user"][p], s["v4_per_user"][p]
        print(f"  {p:14s}{b:>10.1%}{v:>10.1%}{v - b:>+8.1%}")
    print(f"  {'MEAN':14s}{s['b0_mean_agreement']:>10.1%}{s['v4_mean_agreement']:>10.1%}"
          f"{s['v4_mean_agreement'] - s['b0_mean_agreement']:>+8.1%}")
    print(f"\n  position-consistency: B0 {s['b0_mean_pos_consistency']:.1%} · "
          f"V4 {s['v4_mean_pos_consistency']:.1%}")
    print(f"  personalization: {s['matrix_diagonal_wins']}/{s['n_personas']} jurors agree "
          f"most with their own user (diagonal dominance)")
    u = s["usage"]
    print(f"  cost: {u['calls']} calls · {u['input_tokens']:,}+{u['output_tokens']:,} tok · "
          f"~${u['cost_usd']:.4f}")
    print(f"  artifacts -> {s['run_dir']}")


def main() -> None:
    p = argparse.ArgumentParser(description="Run the V4 judge-jury preference experiment.")
    p.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    p.add_argument("--batch", type=int, default=CONFIG.continual_batch_size)
    p.add_argument("--mode", choices=["reflect", "fewshot"], default="reflect")
    args = p.parse_args()
    asyncio.run(run_jury(args.dataset, batch_size=args.batch, juror_mode=args.mode))


if __name__ == "__main__":
    main()
