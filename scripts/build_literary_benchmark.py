"""Build the V4 literary preference benchmark from real content + real ratings.

Inputs (see docs/V4_LITERARY_DATA.md):
  works.jsonl   -- one literary work per line (text + attributes the judge reasons about)
  ratings.jsonl -- one {user_id, work_id, rating} per line (real human ratings)

Output:
  literary_pref_benchmark.jsonl -- each work with its consensus (average) rating,
  its per-user ratings, and a train/test split.
  <prefix>_users.json -- which users have enough train/test ratings to be jurors.

Consensus rating = mean of the real ratings (the general-population signal the
judge learns). Per-user rating = the individual taste a juror learns. Both are
plain aggregations of the ratings you supply — nothing is invented here.

Run: python scripts/build_literary_benchmark.py --works works.jsonl --ratings ratings.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "judy" / "data" / "datasets" / "literary_pref_benchmark.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def fold_ratings(works: list[dict], ratings: list[dict]) -> list[dict]:
    """Attach consensus (mean) + per-user ratings to each work."""
    by_work: dict[str, dict[str, float]] = defaultdict(dict)
    for r in ratings:
        by_work[str(r["work_id"])][str(r["user_id"])] = float(r["rating"])

    out = []
    for w in works:
        user_ratings = by_work.get(str(w["work_id"]), {})
        if not user_ratings:
            continue  # no ratings -> can't be used
        consensus = sum(user_ratings.values()) / len(user_ratings)
        out.append({**w,
                    "consensus_rating": round(consensus, 3),
                    "n_ratings": len(user_ratings),
                    "user_ratings": user_ratings})
    return out


def assign_splits(rows: list[dict], *, test_frac: float, seed: int) -> None:
    """Deterministic per-work train/test split (mutates rows in place)."""
    rng = random.Random(seed)
    order = list(range(len(rows)))
    rng.shuffle(order)
    n_test = round(len(rows) * test_frac)
    test_ids = set(order[:n_test])
    for i, row in enumerate(rows):
        row["split"] = "test" if i in test_ids else "train"


def qualifying_users(rows: list[dict], *, min_train: int, min_test: int) -> dict[str, dict]:
    """Users with enough rated works on BOTH splits to be modeled as jurors."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"train": 0, "test": 0})
    for row in rows:
        for user in row["user_ratings"]:
            counts[user][row["split"]] += 1
    return {u: c for u, c in counts.items()
            if c["train"] >= min_train and c["test"] >= min_test}


def main() -> None:
    p = argparse.ArgumentParser(description="Build the V4 literary preference benchmark.")
    p.add_argument("--works", type=Path, required=True)
    p.add_argument("--ratings", type=Path, required=True)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--test-frac", type=float, default=0.3)
    p.add_argument("--min-train", type=int, default=8, help="min train ratings for a juror user")
    p.add_argument("--min-test", type=int, default=5, help="min test ratings for a juror user")
    p.add_argument("--seed", type=int, default=11)
    args = p.parse_args()

    works = load_jsonl(args.works)
    ratings = load_jsonl(args.ratings)
    rows = fold_ratings(works, ratings)
    if not rows:
        raise SystemExit("No works had any ratings — check work_id alignment between the two files.")
    assign_splits(rows, test_frac=args.test_frac, seed=args.seed)
    users = qualifying_users(rows, min_train=args.min_train, min_test=args.min_test)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest = args.out.with_name(args.out.stem + "_users.json")
    manifest.write_text(json.dumps(users, indent=2), encoding="utf-8")

    n_train = sum(r["split"] == "train" for r in rows)
    print(f"works with ratings: {len(rows)} ({n_train} train / {len(rows) - n_train} test)")
    print(f"modeled users (jurors): {len(users)} "
          f"(>= {args.min_train} train & >= {args.min_test} test ratings each)")
    print(f"wrote {args.out}\n      {manifest}")
    if not users:
        print("WARNING: no users qualify as jurors — lower --min-train/--min-test or "
              "provide denser ratings.")


if __name__ == "__main__":
    main()
