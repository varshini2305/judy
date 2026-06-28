"""Export Judy pairwise judging data into SFT-ready JSONL files.

The output schema is a Judy-owned intermediate shape with explicit fields plus a
rendered `prompt` and `target`. This keeps local datasets reviewable before we
lock to a cloud-specific request format.

Run:
  python scripts/export_sft_dataset.py
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from judy.config import CONFIG
from judy.data.dataset import load_dataset
from judy.tuning.export import (
    benchmark_pair_to_sft_rows,
    item_to_sft_rows,
    load_jsonl,
    split_list,
    write_jsonl,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "judy" / "tuning_datasets" / "sft" / "gemini35-flash" / "v1"
DEFAULT_REWARDBENCH = REPO_ROOT / "judy" / "data" / "datasets" / "rewardbench_sample.jsonl"
DEFAULT_JUDGEBENCH = REPO_ROOT / "judy" / "data" / "datasets" / "judgebench_sample.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Judy data for SFT.")
    parser.add_argument("--dataset", type=Path, default=CONFIG.dataset_path)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--rewardbench", type=Path, default=DEFAULT_REWARDBENCH)
    parser.add_argument("--judgebench", type=Path, default=DEFAULT_JUDGEBENCH)
    parser.add_argument("--heldout-val-frac", type=float, default=0.5)
    parser.add_argument("--train-frac", type=float, default=0.7)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-swaps", action="store_true")
    parser.add_argument("--benchmark-only", action="store_true")
    parser.add_argument("--allow-missing-dataset", action="store_true")
    args = parser.parse_args()

    include_swap = not args.no_swaps
    rewardbench_rows = _load_benchmark(args.rewardbench, "rewardbench", include_swap)
    judgebench_rows = _load_benchmark(args.judgebench, "judgebench", include_swap)

    train_rows: list[dict] = []
    val_rows: list[dict] = []
    test_rows: list[dict] = []

    use_judy = not args.benchmark_only
    if use_judy:
        if args.dataset.exists():
            dataset = load_dataset(args.dataset)
            for item in dataset.dev:
                train_rows.extend(
                    item_to_sft_rows(item, source="judy", split="train", include_swap=include_swap)
                )

            heldout_rows = []
            for item in dataset.heldout:
                heldout_rows.extend(
                    item_to_sft_rows(item, source="judy", split="heldout", include_swap=include_swap)
                )
            val_rows, test_rows = _split_heldout(
                heldout_rows, val_frac=args.heldout_val_frac, seed=args.seed
            )
        elif not args.allow_missing_dataset:
            raise FileNotFoundError(
                f"Judy dataset not found at {args.dataset}. "
                "Pass --benchmark-only or --allow-missing-dataset."
            )

    if not train_rows and not val_rows and not test_rows:
        benchmark_rows = rewardbench_rows + judgebench_rows
        train_rows, val_rows, test_rows = split_list(
            benchmark_rows,
            train_frac=args.train_frac,
            val_frac=args.val_frac,
            seed=args.seed,
        )
        for row in train_rows:
            row["split"] = "train"
        for row in val_rows:
            row["split"] = "val"
        for row in test_rows:
            row["split"] = "test"

    out_dir = args.out_dir
    write_jsonl(out_dir / "train.jsonl", train_rows)
    write_jsonl(out_dir / "val.jsonl", val_rows)
    write_jsonl(out_dir / "test.jsonl", test_rows)
    if rewardbench_rows and train_rows and train_rows[0]["source"] == "judy":
        write_jsonl(out_dir / "rewardbench_eval.jsonl", rewardbench_rows)
    if judgebench_rows and train_rows and train_rows[0]["source"] == "judy":
        write_jsonl(out_dir / "judgebench_eval.jsonl", judgebench_rows)

    metadata = {
        "base_model": "gemini-3.5-flash",
        "dataset_path": str(args.dataset) if args.dataset.exists() else None,
        "include_swap": include_swap,
        "benchmark_only": not use_judy or not args.dataset.exists(),
        "counts": {
            "train": len(train_rows),
            "val": len(val_rows),
            "test": len(test_rows),
            "rewardbench_eval": len(rewardbench_rows) if train_rows and train_rows[0]["source"] == "judy" else 0,
            "judgebench_eval": len(judgebench_rows) if train_rows and train_rows[0]["source"] == "judy" else 0,
        },
        "notes": [
            "if Judy dataset is available, train uses Judy dev items and val/test come from Judy heldout",
            "if Judy dataset is missing or benchmark-only is set, train/val/test are split from benchmark rows",
            "external benchmark rows are exported separately for eval only in Judy-backed mode",
        ],
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote SFT dataset bundle to {out_dir}")
    print(json.dumps(metadata["counts"], indent=2))


def _split_heldout(
    heldout_rows: list[dict],
    *,
    val_frac: float,
    seed: int,
) -> tuple[list[dict], list[dict]]:
    if not heldout_rows:
        return [], []
    items = list(heldout_rows)
    rng = random.Random(seed)
    rng.shuffle(items)
    cut = int(len(items) * val_frac)
    val, test = items[:cut], items[cut:]
    for row in val:
        row["split"] = "val"
    for row in test:
        row["split"] = "test"
    return val, test


def _load_benchmark(path: Path, source: str, include_swap: bool) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for row in load_jsonl(path):
        rows.extend(
            benchmark_pair_to_sft_rows(
                row,
                source=source,
                split="eval",
                include_swap=include_swap,
            )
        )
    return rows


if __name__ == "__main__":
    main()
