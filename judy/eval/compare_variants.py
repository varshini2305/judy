"""Head-to-head comparison of distinctly-labeled judge variants on one benchmark.

Each variant is the SAME pipeline with a different judging *policy* (system
instruction), run over the identical RewardBench sample, so differences are
attributable to the policy alone. Prints real agreement numbers (no estimates)
and saves them to runs/variants_compare.json.

Run: python -m judy.eval.compare_variants
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from judy.config import CONFIG
from judy.eval.benchmark import DEFAULT_SAMPLE, VANILLA_POLICY, _by_subset, load_benchmark_items
from judy.eval.harness import eval_split
from judy.judge.skill import load_skill
from judy.llm.gemini import GeminiClient
from judy.metrics.metrics import compute_metrics

VARIANTS = [
    {
        "label": "V0-baseline-vanilla",
        "description": "Minimal generic prompt: 'which answer is better overall?' No rubric, no bias guards.",
        "policy": VANILLA_POLICY,
    },
    {
        "label": "V1-structured-rubric",
        "description": ("Engineered policy: derive criteria from the task, check correctness "
                        "independently of fluency, explicit bias guards (fluency!=correctness, "
                        "length!=quality, position-invariance)."),
        "policy": load_skill(CONFIG.skill_path),
    },
]


async def run_variants(path: Path = DEFAULT_SAMPLE) -> dict:
    items = load_benchmark_items(path)
    client = GeminiClient()
    results = []
    for v in VARIANTS:
        records = await eval_split(client, v["policy"], items, order_swap=True)
        overall = compute_metrics(records)
        results.append({
            "label": v["label"],
            "description": v["description"],
            "overall": overall.model_dump(),
            "per_subset": {s: m.agreement for s, m in _by_subset(records).items()},
        })
    return {"n_items": len(items), "variants": results}


def _print(result: dict) -> None:
    variants = result["variants"]
    print(f"\n=== Judge variants on the SAME {result['n_items']} RewardBench items ===\n")
    for v in variants:
        o = v["overall"]
        print(f"[{v['label']}]  {v['description']}")
        print(f"    agreement {o['agreement']:.1%} | position-consistency "
              f"{o['position_consistency']:.1%} | pos-consistent agreement "
              f"{o['position_consistent_agreement']:.1%}\n")

    subsets = sorted(variants[0]["per_subset"])
    head = "  ".join(f"{v['label']:>22}" for v in variants)
    print(f"{'subset':24s}{head}")
    for s in subsets:
        cells = "  ".join(f"{v['per_subset'][s]:>21.0%}" for v in variants)
        print(f"{s:24s}{cells}")
    overall_cells = "  ".join(f"{v['overall']['agreement']:>21.0%}" for v in variants)
    print(f"{'OVERALL':24s}{overall_cells}")


def main() -> None:
    result = asyncio.run(run_variants())
    out = CONFIG.runs_dir / "variants_compare.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    _print(result)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
