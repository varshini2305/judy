"""Compare a base Gemini judge and a tuned Gemini judge on held-out synthetic question-answering pairs.

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
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from judy.config import CONFIG
from judy.eval.benchmark import VANILLA_POLICY, _by_subset
from judy.eval.harness import eval_split
from judy.eval.synthetic import load_synthetic_objective_items
from judy.judge.skill import load_skill
from judy.llm.gemini import GeminiClient
from judy.llm.vertex_gemini import VertexGeminiClient
from judy.metrics.metrics import compute_metrics

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = REPO_ROOT / "judy" / "data" / "datasets" / "judy_benchmark_full.jsonl"
_VERTEX_ENDPOINT_RE = re.compile(r"^projects/(?P<project>[^/]+)/locations/(?P<location>[^/]+)/endpoints/")


async def _run_variant(
    *,
    label: str,
    model: str,
    policy: str,
    dataset: Path,
    order_swap: bool,
    vertex_project: str | None = None,
    vertex_location: str | None = None,
) -> dict:
    items = load_synthetic_objective_items(dataset)
    client = _build_client(model, vertex_project=vertex_project, vertex_location=vertex_location)
    records = await eval_split(
        client,
        policy,
        items,
        order_swap=order_swap,
        progress_label=label,
    )
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
    parser.add_argument(
        "--dataset",
        type=Path,
        default=REPO_ROOT / "judy" / "data" / "datasets" / "judy_benchmark_objective_test_100_full.jsonl",
    )
    parser.add_argument("--base-model", default=CONFIG.model)
    parser.add_argument("--tuned-model", required=True)
    parser.add_argument("--policy", choices=["vanilla", "skill"], default="skill")
    parser.add_argument("--no-order-swap", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--tuned-project", help="Vertex project for tuned endpoint calls; inferred from endpoint if omitted.")
    parser.add_argument("--tuned-location", help="Vertex location for tuned endpoint calls; inferred from endpoint if omitted.")
    args = parser.parse_args()

    policy = VANILLA_POLICY if args.policy == "vanilla" else load_skill(CONFIG.skill_path)
    result = asyncio.run(
        _run_compare(
            dataset=args.dataset,
            base_model=args.base_model,
            tuned_model=args.tuned_model,
            policy=policy,
            order_swap=not args.no_order_swap,
            tuned_project=args.tuned_project,
            tuned_location=args.tuned_location,
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
    tuned_project: str | None = None,
    tuned_location: str | None = None,
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
        vertex_project=tuned_project,
        vertex_location=tuned_location,
    )
    delta = _metric_delta(base["overall"], tuned["overall"])
    return {
        "dataset": str(dataset),
        "policy": "skill" if policy != VANILLA_POLICY else "vanilla",
        "variants": [base, tuned],
        "delta": delta,
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
    delta = result.get("delta", {})
    if delta:
        print("[delta: tuned - base]")
        print(
            f"  agreement {delta['agreement_pp']:+.1f} pp | "
            f"position-consistency {delta['position_consistency_pp']:+.1f} pp | "
            f"pos-consistent agreement {delta['position_consistent_agreement_pp']:+.1f} pp\n"
        )


def _build_client(model: str, *, vertex_project: str | None, vertex_location: str | None) -> Any:
    if _is_vertex_endpoint(model):
        inferred_project, inferred_location = _infer_vertex_scope(model)
        return VertexGeminiClient(
            model=model,
            project=vertex_project or inferred_project,
            location=vertex_location or inferred_location,
            max_concurrency=CONFIG.max_concurrency,
        )
    return GeminiClient(replace(CONFIG, model=model))


def _is_vertex_endpoint(model: str) -> bool:
    return bool(_VERTEX_ENDPOINT_RE.match(model))


def _infer_vertex_scope(model: str) -> tuple[str, str]:
    match = _VERTEX_ENDPOINT_RE.match(model)
    if not match:
        raise ValueError(
            "Expected a Vertex endpoint resource like "
            "'projects/.../locations/.../endpoints/...'."
        )
    return match.group("project"), match.group("location")


def _metric_delta(base: dict[str, float], tuned: dict[str, float]) -> dict[str, float]:
    return {
        "agreement_pp": round((tuned["agreement"] - base["agreement"]) * 100, 1),
        "position_consistency_pp": round(
            (tuned["position_consistency"] - base["position_consistency"]) * 100, 1
        ),
        "position_consistent_agreement_pp": round(
            (
                tuned["position_consistent_agreement"]
                - base["position_consistent_agreement"]
            )
            * 100,
            1,
        ),
    }


if __name__ == "__main__":
    main()
