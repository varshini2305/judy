"""Merge multiple synthetic benchmark batches into one combined benchmark bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from judy.synth_benchmark.review import make_review_row
from judy.tuning.export import load_jsonl, write_jsonl

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = REPO_ROOT / "judy" / "data" / "datasets"


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge multiple Judy synthetic benchmark files.")
    parser.add_argument("--sources", nargs="+", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--output-prefix", default="judy_benchmark_combined")
    args = parser.parse_args()

    full_rows: list[dict] = []
    for source in args.sources:
        rows = load_jsonl(source)
        full_rows.extend(rows)

    ids = [row["id"] for row in full_rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate benchmark ids detected across sources.")

    review_rows = [make_review_row(row) for row in full_rows]
    out_dir = args.out_dir
    full_path = out_dir / f"{args.output_prefix}_full.jsonl"
    review_path = out_dir / f"{args.output_prefix}_review.jsonl"
    meta_path = out_dir / f"{args.output_prefix}_metadata.json"

    write_jsonl(full_path, full_rows)
    write_jsonl(review_path, review_rows)
    meta_path.write_text(
        json.dumps(
            {
                "sources": [str(source) for source in args.sources],
                "n_cases": len(full_rows),
                "objective_cases": sum(1 for row in full_rows if row["mode"] == "objective_pairwise"),
                "preference_cases": sum(1 for row in full_rows if row["mode"] == "preference_pairwise"),
                "output_prefix": args.output_prefix,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote merged benchmark to {full_path}")
    print(f"Wrote merged review file to {review_path}")
    print(f"Wrote merged metadata to {meta_path}")


if __name__ == "__main__":
    main()
