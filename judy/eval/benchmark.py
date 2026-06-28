"""Baseline LLM-as-a-judge on a public benchmark (RewardBench).

RewardBench rows are (prompt, chosen, rejected) where `chosen` is the
human-preferred answer. We map each pair to an `Item` (chosen = better tier) and
run a deliberately *minimal* vanilla judge policy — this is the baseline we must
beat. Agreement with `chosen` = agreement with aggregated human judgment.

Run: python -m judy.eval.benchmark
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path

from judy.config import CONFIG
from judy.eval.harness import eval_split
from judy.judge.schema import Candidate, Item, JudgeRecord
from judy.llm.gemini import GeminiClient
from judy.metrics.metrics import Metrics, compute_metrics

# The implicit spec for benchmark items (they have no explicit system prompt).
GENERIC_SPEC = "Answer the user's question as helpfully, correctly, and completely as possible."

# A minimal, non-engineered judge policy — the baseline a real improvement must beat.
VANILLA_POLICY = (
    "You are an impartial judge. Given a question and two candidate answers "
    "(A and B), decide which answer is better overall — more helpful, correct, "
    "and complete. Judge holistically and return only the requested JSON."
)

DEFAULT_SAMPLE = CONFIG.runs_dir.parent / "judy/data/datasets/rewardbench_sample.jsonl"


def load_benchmark_items(path: Path) -> list[Item]:
    """Map RewardBench (prompt, chosen, rejected) rows to Items (chosen = tier A)."""
    items: list[Item] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        items.append(
            Item(
                id=row["id"],
                task_type=row["subset"],
                system_prompt=GENERIC_SPEC,
                question=row["question"],
                gold_answer="",
                candidates=[
                    Candidate(tier="A", text=row["chosen"]),
                    Candidate(tier="C", text=row["rejected"]),
                ],
                known_ordering=("A", "C"),
            )
        )
    return items


def _by_subset(records: list[JudgeRecord]) -> dict[str, Metrics]:
    groups: dict[str, list[JudgeRecord]] = defaultdict(list)
    for r in records:
        groups[r.task_type].append(r)
    return {sub: compute_metrics(recs) for sub, recs in sorted(groups.items())}


async def run_baseline(path: Path = DEFAULT_SAMPLE, *, order_swap: bool = True) -> dict:
    """Run the vanilla judge over the benchmark sample; return overall + per-subset."""
    items = load_benchmark_items(path)
    client = GeminiClient()
    records = await eval_split(client, VANILLA_POLICY, items, order_swap=order_swap)
    return {
        "n_items": len(items),
        "overall": compute_metrics(records),
        "per_subset": _by_subset(records),
        "usage": client.usage,
    }


def _print(result: dict) -> None:
    o: Metrics = result["overall"]
    print(f"\n=== Vanilla judge vs RewardBench (human-preferred) — {result['n_items']} items ===")
    print(f"  Agreement with humans:        {o.agreement:.1%}")
    if o.position_consistency is not None:
        print(f"  Position-consistency:         {o.position_consistency:.1%}")
        print(f"  Position-consistent agreement:{o.position_consistent_agreement:.1%}")
    print(f"  Score-spread (margin stdev):  {o.score_spread:.2f}")
    print("\n  By subset:")
    for sub, m in result["per_subset"].items():
        print(f"    {sub:24s} agreement {m.agreement:.0%}  (n={m.n_items})")
    if result.get("usage"):
        print(f"\n  Cost: {result['usage'].summary()}")


def main() -> None:
    result = asyncio.run(run_baseline())
    _print(result)


if __name__ == "__main__":
    main()
