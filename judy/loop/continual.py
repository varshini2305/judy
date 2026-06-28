"""Streaming continual-learning judge (V2).

Unlike the batch self-improvement loop (full dev set per iteration), this
processes examples as a *stream* and updates the judge's policy after every N
examples (default 3). On each mini-batch it looks at the cases where its verdict
disagreed with the ground-truth / user label, reflects on *why the labeled
answer was actually better*, and appends task-general lessons to its policy —
so the judge keeps learning how to evaluate as new data arrives.

Learn on a dev stream, measure on a disjoint held-out split. Run:
``python -m judy.loop.continual``
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from judy.config import CONFIG
from judy.eval.benchmark import VANILLA_POLICY, load_benchmark_items
from judy.eval.harness import eval_split
from judy.judge.judge import judge_item
from judy.judge.schema import Item, JudgeRecord
from judy.judge.skill import snapshot_skill
from judy.llm.gemini import GeminiClient
from judy.loop.reflect import apply_edits, reflect
from judy.metrics.metrics import compute_metrics

Progress = Callable[[str], None]


async def continual_learn(
    client,
    skill_text: str,
    dev_items: list[Item],
    items_by_id: dict[str, Item],
    *,
    batch_size: int,
    progress: Progress = lambda _m: None,
) -> tuple[str, list[str], list[bool], list[dict]]:
    """Stream dev items; every ``batch_size`` examples, reflect on disagreements
    and update the policy. Returns (final_policy, snapshots, dev_correct_flags, edits_log).
    """
    snapshots = [skill_text]
    dev_flags: list[bool] = []
    edits_log: list[dict] = []
    batch: list[JudgeRecord] = []

    async def flush(current: str) -> str:
        # Learn only from cases the judge got wrong vs the label (the disagreements).
        errors = [r for r in batch if not r.correct]
        if errors:
            edits = await reflect(client, current, errors, items_by_id, anchored=True)
            current = apply_edits(current, edits, CONFIG.skill_token_budget)
            edits_log.append({"after_example": len(dev_flags), "n_errors": len(errors), **edits})
        return current

    for i, item in enumerate(dev_items):
        rec = await judge_item(client, skill_text, item, swap=False)
        dev_flags.append(rec.correct)
        batch.append(rec)
        if len(batch) >= batch_size:
            skill_text = await flush(skill_text)
            snapshots.append(skill_text)
            batch = []
            progress(f"  {i + 1}/{len(dev_items)} streamed · policy snapshots: {len(snapshots)}")
    if batch:  # flush the remainder
        skill_text = await flush(skill_text)
        snapshots.append(skill_text)
    return skill_text, snapshots, dev_flags, edits_log


async def run_continual_benchmark(
    sample_path: Path,
    *,
    dev_n: int = 40,
    batch_size: int | None = None,
    start_policy: str | None = None,
    progress: Progress = print,
) -> dict:
    """Split a benchmark sample into dev/held-out, learn on dev, measure on held-out."""
    batch_size = batch_size or CONFIG.continual_batch_size
    items = load_benchmark_items(Path(sample_path))
    rng = random.Random(7)
    rng.shuffle(items)  # stratify dev/held-out away from subset ordering
    dev, held = items[:dev_n], items[dev_n:]
    items_by_id = {i.id: i for i in dev}

    client = GeminiClient()
    seed = start_policy if start_policy is not None else VANILLA_POLICY

    progress(f"baseline held-out eval ({len(held)} items)")
    held_base = await eval_split(client, seed, held, order_swap=True)
    progress(f"continual learning on {len(dev)} dev items (batch={batch_size})")
    final_policy, snapshots, dev_flags, edits_log = await continual_learn(
        client, seed, dev, items_by_id, batch_size=batch_size, progress=progress
    )
    progress("final held-out eval")
    held_final = await eval_split(client, final_policy, held, order_swap=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = CONFIG.runs_dir / f"continual-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    for t, s in enumerate(snapshots):
        snapshot_skill(s, run_dir, t)
    for name, recs in (("held_baseline", held_base), ("held_final", held_final)):
        with (run_dir / f"{name}.jsonl").open("w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(r.model_dump_json() + "\n")

    summary = {
        "run_id": run_id,
        "dataset": str(sample_path),
        "dev_n": len(dev),
        "heldout_n": len(held),
        "batch_size": batch_size,
        "held_baseline": compute_metrics(held_base).model_dump(),
        "held_final": compute_metrics(held_final).model_dump(),
        "n_policy_updates": len(edits_log),
        "edits": edits_log,
        "usage": client.usage.as_dict(),
        "run_dir": str(run_dir),
    }
    (run_dir / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _print(summary)
    return summary


def _print(s: dict) -> None:
    b, f = s["held_baseline"], s["held_final"]
    print("\n=== Continual-learning judge (V2) — held-out before/after ===")
    print(f"  dev={s['dev_n']} (batch {s['batch_size']}) · held-out={s['heldout_n']} · "
          f"{s['n_policy_updates']} policy updates")
    print(f"  agreement:        {b['agreement']:.1%}  ->  {f['agreement']:.1%}")
    print(f"  pos-consistency:  {b['position_consistency']:.1%}  ->  {f['position_consistency']:.1%}")
    u = s["usage"]
    print(f"  cost: {u['calls']} calls · {u['input_tokens']:,}+{u['output_tokens']:,} tok · ~${u['cost_usd']:.4f}")
    print(f"  policy snapshots + records in {s['run_dir']}")


def main() -> None:
    p = argparse.ArgumentParser(description="Run the streaming continual-learning judge.")
    p.add_argument("--sample", default=str(CONFIG.runs_dir.parent / "judy/data/datasets/llmbar_adversarial_100.jsonl"))
    p.add_argument("--dev", type=int, default=40)
    p.add_argument("--batch", type=int, default=CONFIG.continual_batch_size)
    args = p.parse_args()
    asyncio.run(run_continual_benchmark(Path(args.sample), dev_n=args.dev, batch_size=args.batch))


if __name__ == "__main__":
    main()
