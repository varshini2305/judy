"""Export cumulative SFT checkpoint bundles from the objective synthetic train set.

This creates 20/40/60/80/100-case train bundles by default, each sharing:
- a small validation split from the objective train pool
- the same disjoint held-out objective test set
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from judy.tuning.export import (
    load_jsonl,
    synthetic_objective_pair_to_sft_rows,
    write_jsonl,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRAIN_SOURCE = REPO_ROOT / "judy" / "data" / "datasets" / "judy_benchmark_objective_100_full.jsonl"
DEFAULT_TEST_SOURCE = REPO_ROOT / "judy" / "data" / "datasets" / "judy_benchmark_objective_test_100_full.jsonl"
DEFAULT_OUT_ROOT = REPO_ROOT / "judy" / "tuning_datasets" / "sft" / "gemini35-flash"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export cumulative objective SFT checkpoint bundles.")
    parser.add_argument("--train-source", type=Path, default=DEFAULT_TRAIN_SOURCE)
    parser.add_argument("--test-source", type=Path, default=DEFAULT_TEST_SOURCE)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--sizes", nargs="+", type=int, default=[20, 40, 60, 80, 100])
    parser.add_argument("--val-cases", type=int, default=0)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--no-swaps", action="store_true")
    args = parser.parse_args()

    include_swap = not args.no_swaps
    train_cases = _load_objective_cases(args.train_source)
    test_cases = _load_objective_cases(args.test_source)
    if not train_cases:
        raise ValueError(f"No objective rows found in {args.train_source}")
    if not test_cases:
        raise ValueError(f"No objective rows found in {args.test_source}")

    ordered_train = list(train_cases)
    random.Random(args.seed).shuffle(ordered_train)
    if args.val_cases < 0 or args.val_cases >= len(ordered_train):
        raise ValueError("--val-cases must be between 0 and len(train_source)-1")
    val_cases = ordered_train[: args.val_cases] if args.val_cases else []
    train_pool = ordered_train[args.val_cases :] if args.val_cases else ordered_train
    max_size = max(args.sizes)
    if max_size > len(train_pool):
        raise ValueError(
            f"Requested size {max_size} but only {len(train_pool)} train-pool cases remain after validation split."
        )

    summary = []
    for size in args.sizes:
        out_dir = args.out_root / f"judy_objective_checkpoint_{size}"
        train_subset = train_pool[:size]
        train_rows = _expand_rows(train_subset, split="train", include_swap=include_swap)
        val_rows = _expand_rows(val_cases, split="val", include_swap=include_swap)
        test_rows = _expand_rows(test_cases, split="test", include_swap=include_swap)

        write_jsonl(out_dir / "train.jsonl", train_rows)
        write_jsonl(out_dir / "val.jsonl", val_rows)
        write_jsonl(out_dir / "test.jsonl", test_rows)
        metadata = {
            "base_model": "gemini-3.5-flash",
            "task": "llm_as_judge_pairwise_qa",
            "source": "judy_synthetic_objective_checkpoint",
            "train_source": str(args.train_source),
            "test_source": str(args.test_source),
            "include_swap": include_swap,
            "seed": args.seed,
            "checkpoint_size": size,
            "counts": {
                "train_cases": len(train_subset),
                "val_cases": len(val_cases),
                "test_cases": len(test_cases),
                "train_rows": len(train_rows),
                "val_rows": len(val_rows),
                "test_rows": len(test_rows),
            },
            "notes": [
                "validation cases are held constant across checkpoint sizes",
                "train subsets are cumulative prefixes after one seeded shuffle",
                "test cases come from the disjoint objective_test_100 benchmark",
            ],
        }
        (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        summary.append({"size": size, **metadata["counts"], "out_dir": str(out_dir)})

    print(json.dumps(summary, indent=2))


def _load_objective_cases(path: Path) -> list[dict]:
    return [row for row in load_jsonl(path) if row.get("mode") == "objective_pairwise"]


def _expand_rows(rows: list[dict], *, split: str, include_swap: bool) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        out.extend(
            synthetic_objective_pair_to_sft_rows(
                row,
                source="judy_synth_benchmark",
                split=split,
                include_swap=include_swap,
            )
        )
    return out


if __name__ == "__main__":
    main()
