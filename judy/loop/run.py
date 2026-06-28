"""The self-improvement loop + run logging (brief §4).

    load SKILL.md -> R_0
    baseline: eval(held_out, R_0, order_swap=ON)
    for t in 1..N:
        dev_verdicts = eval(dev, R_{t-1})
        errors       = anchored: verdict != truth  |  unanchored: order-inconsistent
        edits        = reflect(errors, R_{t-1})
        R_t          = apply(edits, R_{t-1})  (snapshot)
        held_metrics = eval(held_out, R_t, order_swap=ON)
    stop early if held-out agreement stalls for 2 iters or score-spread collapses.

Runs both anchored and unanchored modes — the headline ablation. Artifacts land
in ``runs/{run_id}/``. Run: ``python -m judy.loop.run [--iters N] [--modes ...]``
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from judy.config import CONFIG
from judy.data.dataset import Dataset, load_dataset
from judy.eval.harness import eval_split
from judy.judge.schema import Item, JudgeRecord
from judy.judge.skill import load_skill, snapshot_skill
from judy.llm.gemini import client_for_mode
from judy.loop.reflect import apply_edits, reflect
from judy.metrics.metrics import Metrics, compute_metrics

ProgressFn = Callable[[str], None]


def _anchored_errors(records: list[JudgeRecord]) -> list[JudgeRecord]:
    """Items the judge got wrong (real ground-truth signal)."""
    return [r for r in records if not r.correct]


def _unanchored_errors(records: list[JudgeRecord]) -> list[JudgeRecord]:
    """Items judged inconsistently across answer order (no ground truth used)."""
    by_item: dict[str, dict[bool, JudgeRecord]] = defaultdict(dict)
    for r in records:
        by_item[r.item_id][r.swap] = r
    out: list[JudgeRecord] = []
    for v in by_item.values():
        if True in v and False in v and v[True].verdict != v[False].verdict:
            out.append(v[False])
    return out


async def run_mode(
    mode: str,
    dataset: Dataset,
    run_dir: Path,
    *,
    n_iters: int = CONFIG.n_iters,
    progress: ProgressFn = lambda _msg: None,
) -> dict:
    """Run baseline + N improvement iterations for one mode; log artifacts."""
    anchored = mode == "anchored"
    client = client_for_mode(mode)
    items_by_id: dict[str, Item] = {i.id: i for i in dataset.dev}
    mode_dir = run_dir / mode
    mode_dir.mkdir(parents=True, exist_ok=True)

    skill = load_skill(CONFIG.skill_path)  # R_0 — fresh seed each run
    snapshot_skill(skill, mode_dir, 0)

    progress(f"[{mode}] baseline eval on {len(dataset.heldout)} held-out items")
    held = await eval_split(client, skill, dataset.heldout, order_swap=CONFIG.order_swap_eval)
    history: list[Metrics] = [compute_metrics(held)]
    _dump_records(mode_dir / "iter_0.jsonl", held)
    edits_log: list[dict] = []

    best = history[0].agreement
    no_improve = 0

    for t in range(1, n_iters + 1):
        # Dev pass: unanchored needs both orders to detect self-inconsistency.
        dev_swap = True if not anchored else CONFIG.order_swap_dev
        progress(f"[{mode}] iter {t}/{n_iters}: judging {len(dataset.dev)} dev items")
        dev = await eval_split(client, skill, dataset.dev, order_swap=dev_swap)
        errors = _anchored_errors(dev) if anchored else _unanchored_errors(dev)

        progress(f"[{mode}] iter {t}: reflecting on {len(errors)} errors")
        edits = await reflect(client, skill, errors, items_by_id, anchored=anchored)
        skill = apply_edits(skill, edits, CONFIG.skill_token_budget)
        snapshot_skill(skill, mode_dir, t)
        edits_log.append({"iter": t, "n_errors": len(errors), **edits})

        progress(f"[{mode}] iter {t}: held-out eval")
        held = await eval_split(client, skill, dataset.heldout, order_swap=CONFIG.order_swap_eval)
        m = compute_metrics(held)
        history.append(m)
        _dump_records(mode_dir / f"iter_{t}.jsonl", held)

        if m.agreement > best + 1e-9:
            best, no_improve = m.agreement, 0
        else:
            no_improve += 1
        if no_improve >= CONFIG.no_improve_patience:
            progress(f"[{mode}] early stop: no improvement for {no_improve} iters")
            break
        if m.score_spread < CONFIG.score_spread_collapse:
            progress(f"[{mode}] early stop: score-spread collapsed ({m.score_spread:.2f})")
            break

    return {
        "mode": mode,
        "history": [h.model_dump() for h in history],
        "edits": edits_log,
    }


async def run_all(
    dataset_path: Path | None = None,
    *,
    modes: list[str] | None = None,
    n_iters: int = CONFIG.n_iters,
    progress: ProgressFn = print,
) -> dict:
    """Run the requested modes sequentially and write a combined metrics.json."""
    modes = modes or ["anchored", "unanchored"]
    dataset = load_dataset(dataset_path or CONFIG.dataset_path)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = CONFIG.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for mode in modes:
        results[mode] = await run_mode(
            mode, dataset, run_dir, n_iters=n_iters, progress=progress
        )

    summary = {
        "run_id": run_id,
        "dataset": str(dataset_path or CONFIG.dataset_path),
        "n_dev": len(dataset.dev),
        "n_heldout": len(dataset.heldout),
        "unseen_heldout_types": sorted(dataset.unseen_heldout_types),
        "results": results,
    }
    (run_dir / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    progress(f"\nWrote run to {run_dir}")
    _print_summary(summary)
    return summary


def _dump_records(path: Path, records: list[JudgeRecord]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(r.model_dump_json() + "\n")


def _print_summary(summary: dict) -> None:
    print("\n=== Held-out agreement: baseline -> final ===")
    for mode, res in summary["results"].items():
        hist = res["history"]
        base, final = hist[0]["agreement"], hist[-1]["agreement"]
        print(f"  {mode:11s}: {base:.1%} -> {final:.1%}  ({len(hist) - 1} iters)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Judy's self-improvement loop.")
    parser.add_argument("--iters", type=int, default=CONFIG.n_iters)
    parser.add_argument("--modes", default="anchored,unanchored")
    parser.add_argument("--dataset", default=None)
    args = parser.parse_args()
    asyncio.run(
        run_all(
            Path(args.dataset) if args.dataset else None,
            modes=[m.strip() for m in args.modes.split(",") if m.strip()],
            n_iters=args.iters,
        )
    )


if __name__ == "__main__":
    main()
