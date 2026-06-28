"""Fetch a balanced LLMBar-Adversarial sample (~100 items) from RewardBench.

LLMBar's adversarial subsets are where a strong judge gets fooled: a worse
answer is crafted to look better (fluent, on-topic, well-formatted). These live
inside RewardBench's `filtered` split as `llmbar-adver-{neighbor,GPTInst,GPTOut,
manual}`. We scan the split, collect them, and write a balanced normalized
sample {id, subset, question, chosen, rejected}. No model credits.

Run: python scripts/fetch_llmbar_adversarial.py
"""

from __future__ import annotations

import json
import urllib.request
from collections import defaultdict
from pathlib import Path

DATASET = "allenai/reward-bench"
BASE = "https://datasets-server.huggingface.co/rows"
OUT = Path(__file__).resolve().parent.parent / "judy/data/datasets/llmbar_adversarial_100.jsonl"
PER_SUBSET = 25  # 4 adversarial subsets -> ~100 items


def main() -> None:
    found: dict[str, list[dict]] = defaultdict(list)
    for off in range(0, 2985, 100):
        url = (f"{BASE}?dataset=allenai/reward-bench&config=default"
               f"&split=filtered&offset={off}&length=100")
        try:
            data = json.load(urllib.request.urlopen(url, timeout=30))
        except Exception:
            continue
        for r in data.get("rows", []):
            row = r["row"]
            sub = row["subset"]
            if "llmbar-adver" in sub and len(found[sub]) < PER_SUBSET:
                found[sub].append({
                    "id": f"rb-{sub}-{row['id']}",
                    "subset": sub,
                    "question": row["prompt"],
                    "chosen": row["chosen"],
                    "rejected": row["rejected"],
                })

    sample = [r for bucket in found.values() for r in bucket]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in sample:
            fh.write(json.dumps(r) + "\n")
    for sub, bucket in sorted(found.items()):
        print(f"  {sub}: {len(bucket)}")
    print(f"Wrote {len(sample)} adversarial items to {OUT}")


if __name__ == "__main__":
    main()
