"""Fetch a small, balanced RewardBench sample for baseline evaluation.

Pulls a few rows per subset via the HuggingFace datasets-server REST API (no
heavy `datasets` dependency, no model credits) and writes a normalized JSONL:
{id, subset, question, chosen, rejected}. The judge should prefer `chosen`.

Run: python scripts/fetch_benchmark_sample.py
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

DATASET = "allenai/reward-bench"
BASE = "https://datasets-server.huggingface.co/rows"
OUT = Path(__file__).resolve().parent.parent / "judy/data/datasets/rewardbench_sample.jsonl"

# Spread offsets across the filtered split (~2985 rows) to span different subsets.
OFFSETS = [0, 500, 1000, 1500, 2000, 2500, 2800]
PER_OFFSET = 12
PER_SUBSET_CAP = 5  # keep the sample balanced


def _fetch(offset: int, length: int) -> list[dict]:
    url = (f"{BASE}?dataset={urllib.parse.quote(DATASET)}&config=default"
           f"&split=filtered&offset={offset}&length={length}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    out = []
    for r in data.get("rows", []):
        row = r["row"]
        out.append({
            "id": f"rb-{row['subset']}-{row['id']}",
            "subset": row["subset"],
            "question": row["prompt"],
            "chosen": row["chosen"],
            "rejected": row["rejected"],
        })
    return out


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    by_subset: dict[str, list[dict]] = {}
    for off in OFFSETS:
        for r in _fetch(off, PER_OFFSET):
            bucket = by_subset.setdefault(r["subset"], [])
            if len(bucket) < PER_SUBSET_CAP:
                bucket.append(r)

    rows = [r for bucket in by_subset.values() for r in bucket]
    with OUT.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    for subset, bucket in sorted(by_subset.items()):
        print(f"  {subset}: {len(bucket)}")
    print(f"Wrote {len(rows)} rows ({len(by_subset)} subsets) to {OUT}")


if __name__ == "__main__":
    main()
