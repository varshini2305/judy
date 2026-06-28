"""Export Judy synthetic objective benchmark cases into an SFT bundle.

Typical use:
  1) generate 100 cases for training/validation
  2) generate 100 separate cases for held-out testing
  3) export objective-only rows into train/val/test JSONL

Run:
  PYTHONPATH=. python scripts/export_judy_benchmark_sft.py \
    --train-source judy/data/datasets/judy_benchmark_full.jsonl \
    --eval-source judy/data/datasets/judy_benchmark_eval_full.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from judy.tuning.export import (
    load_jsonl,
    split_case_rows,
    synthetic_objective_pair_to_sft_rows,
    write_jsonl,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "judy" / "data" / "datasets" / "judy_benchmark_full.jsonl"
DEFAULT_OUT = REPO_ROOT / "judy" / "tuning_datasets" / "sft" / "gemini35-flash" / "judy_benchmark_v1"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Judy synthetic benchmark to SFT JSONL.")
    parser.add_argument("--train-source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--eval-source", type=Path)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--val-frac", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--no-swaps", action="store_true")
    args = parser.parse_args()

    include_swap = not args.no_swaps
    train_cases = _load_objective_cases(args.train_source)
    if not train_cases:
        raise ValueError(f"No objective benchmark rows found in {args.train_source}")

    if args.eval_source:
        train_case_rows, val_case_rows = _split_train_val_only(
            train_cases,
            val_frac=args.val_frac,
            seed=args.seed,
        )
        eval_cases = _load_objective_cases(args.eval_source)
        if not eval_cases:
            raise ValueError(f"No objective benchmark rows found in {args.eval_source}")
        test_case_rows = eval_cases
    else:
        train_case_rows, val_case_rows, test_case_rows = split_case_rows(
            train_cases,
            train_frac=args.train_frac,
            val_frac=args.val_frac,
            seed=args.seed,
        )

    train_rows = _expand_rows(train_case_rows, split="train", include_swap=include_swap)
    val_rows = _expand_rows(val_case_rows, split="val", include_swap=include_swap)
    test_rows = _expand_rows(test_case_rows, split="test", include_swap=include_swap)

    out_dir = args.out_dir
    write_jsonl(out_dir / "train.jsonl", train_rows)
    write_jsonl(out_dir / "val.jsonl", val_rows)
    write_jsonl(out_dir / "test.jsonl", test_rows)

    metadata = {
        "base_model": "gemini-3.5-flash",
        "task": "llm_as_judge_pairwise_qa",
        "source": "judy_synthetic_benchmark",
        "train_source": str(args.train_source),
        "eval_source": str(args.eval_source) if args.eval_source else None,
        "include_swap": include_swap,
        "seed": args.seed,
        "counts": {
            "train_cases": len(train_case_rows),
            "val_cases": len(val_case_rows),
            "test_cases": len(test_case_rows),
            "train_rows": len(train_rows),
            "val_rows": len(val_rows),
            "test_rows": len(test_rows),
        },
        "notes": [
            "only objective_pairwise cases are exported for SFT",
            "splits happen at the case level before order-swap expansion",
            "provide a separate eval-source file to keep train and test generations fully disjoint",
        ],
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote synthetic SFT bundle to {out_dir}")
    print(json.dumps(metadata["counts"], indent=2))


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


def _split_train_val_only(rows: list[dict], *, val_frac: float, seed: int) -> tuple[list[dict], list[dict]]:
    items = list(rows)
    random.Random(seed).shuffle(items)
    n_val = int(len(items) * val_frac)
    return items[n_val:], items[:n_val]


if __name__ == "__main__":
    main()
