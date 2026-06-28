"""Compare a base Gemini judge and a tuned Gemini judge on held-out synthetic QA pairs.

This evaluates only Judy's objective synthetic cases, so agreement is measured
against hidden `objectively_better` labels rather than human style preferences.

Run:
  PYTHONPATH=. python scripts/eval_tuned_judge.py \
    --dataset judy/data/datasets/judy_benchmark_eval_full.jsonl \
    --base-model gemini-3.5-flash \
    --tuned-model projects/.../locations/us-central1/models/...
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import replace
from pathlib import Path

from judy.config import CONFIG
from judy.eval.benchmark import VANILLA_POLICY, _by_subset
from judy.eval.harness import eval_split
from judy.eval.synthetic import load_synthetic_objective_items
from judy.judge.skill import load_skill
from judy.llm.gemini import GeminiClient
from judy.metrics.metrics import compute_metrics

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = REPO_ROOT / "judy" / "data" / "datasets" / "judy_benchmark_full.jsonl"


async def _run_variant(
    *,
    label: str,
    model: str,
    policy: str,
    dataset: Path,
    order_swap: bool,
) -> dict:
    items = load_synthetic_objective_items(dataset)
    client = GeminiClient(replace(CONFIG, model=model))
    records = await eval_split(client, policy, items, order_swap=order_swap)
    overall = compute_metrics(records)
    return {
        "label": label,
        "model": model,
        "dataset": str(dataset),
        "n_items": len(items),
        "overall": overall.model_dump(),
        "per_subset": {subset: metrics.model_dump() for subset, metrics in _by_subset(records).items()},
        "usage": client.usage.as_dict(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate base vs tuned judge on Judy synthetic benchmark.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--base-model", default=CONFIG.model)
    parser.add_argument("--tuned-model", required=True)
    parser.add_argument("--policy", choices=["vanilla", "skill"], default="skill")
    parser.add_argument("--no-order-swap", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    policy = VANILLA_POLICY if args.policy == "vanilla" else load_skill(CONFIG.skill_path)
    result = asyncio.run(
        _run_compare(
            dataset=args.dataset,
            base_model=args.base_model,
            tuned_model=args.tuned_model,
            policy=policy,
            order_swap=not args.no_order_swap,
        )
    )
    out_path = args.out or CONFIG.runs_dir / "tuned_judge_compare.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    _print(result)
    print(f"\nSaved -> {out_path}")


async def _run_compare(
    *,
    dataset: Path,
    base_model: str,
    tuned_model: str,
    policy: str,
    order_swap: bool,
) -> dict:
    base = await _run_variant(
        label="base",
        model=base_model,
        policy=policy,
        dataset=dataset,
        order_swap=order_swap,
    )
    tuned = await _run_variant(
        label="tuned",
        model=tuned_model,
        policy=policy,
        dataset=dataset,
        order_swap=order_swap,
    )
    return {
        "dataset": str(dataset),
        "policy": "skill" if policy != VANILLA_POLICY else "vanilla",
        "variants": [base, tuned],
    }


def _print(result: dict) -> None:
    print(f"\n=== Base vs tuned judge on {result['dataset']} ===\n")
    for variant in result["variants"]:
        overall = variant["overall"]
        usage = variant["usage"]
        print(f"[{variant['label']}] {variant['model']}")
        print(
            f"  agreement {overall['agreement']:.1%} | "
            f"position-consistency {overall['position_consistency']:.1%} | "
            f"pos-consistent agreement {overall['position_consistent_agreement']:.1%}"
        )
        print(
            f"  cost: {usage['calls']} calls · "
            f"{usage['input_tokens']:,}+{usage['output_tokens']:,} tokens · "
            f"~${usage['cost_usd']:.4f}\n"
        )


if __name__ == "__main__":
    main()
