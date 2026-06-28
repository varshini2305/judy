"""Export simulated preference-learning data into tuning-ready JSONL files.

This first pass uses the repo's built-in simulated users so we can validate the
preference-tuning path offline before wiring in real product feedback.

Run:
  python scripts/export_preference_dataset.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from judy.tuning.export import generate_preference_rows, split_list, write_jsonl

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "judy" / "tuning_datasets" / "pref" / "gemini25-flash" / "v1"
DEFAULT_USERS = "concise,detailed,anti_repetition,conditional,drifting"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Judy preference-tuning data.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--users", default=DEFAULT_USERS)
    parser.add_argument("--pairs-per-user", type=int, default=24)
    parser.add_argument("--train-frac", type=float, default=0.6)
    parser.add_argument("--val-frac", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()

    user_keys = [u.strip() for u in args.users.split(",") if u.strip()]
    rows = generate_preference_rows(
        user_keys=user_keys,
        pairs_per_user=args.pairs_per_user,
        seed=args.seed,
    )
    train_rows, val_rows, test_rows = split_list(
        rows,
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

    metadata = {
        "base_model": "gemini-2.5-flash",
        "users": user_keys,
        "pairs_per_user": args.pairs_per_user,
        "counts": {
            "train": len(train_rows),
            "val": len(val_rows),
            "test": len(test_rows),
        },
        "notes": [
            "rows are generated from simulated users with explicit preference context",
            "correctness is assumed tied; the target is which answer the user would prefer",
        ],
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote preference dataset bundle to {out_dir}")
    print(json.dumps(metadata["counts"], indent=2))


if __name__ == "__main__":
    main()

