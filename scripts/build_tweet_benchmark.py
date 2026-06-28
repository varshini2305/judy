"""Build a minimal tweet preference benchmark for the V4 judge-jury experiment.

Source: the Kaggle 'tweets-dataset' CSV (content + number_of_likes + author).

Two ground-truth signals are produced, both from real/transparent quantities —
nothing is an opaque formula:

- **popularity** (the central judge's target): the tweet's like count converted to
  a 0..1 percentile **within its author**, so it reflects how a tweet did relative
  to that author's own baseline (controls for fame) — i.e. content likability.
- **persona likeness** (each juror's target): 5 simulated users, each defined by ONE
  clear, interpretable preference over a real tweet feature (short / hashtags /
  conversational / expressive / links). Each persona's likeness for a tweet is the
  0..1 percentile of that feature. Divergent by construction.

Output: judy/data/datasets/tweet_pref_benchmark.jsonl (one tweet per line).

Run: python scripts/build_tweet_benchmark.py --csv <tweets.csv>
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "judy" / "data" / "datasets" / "tweet_pref_benchmark.jsonl"
DEFAULT_AUTHORS = ["BarackObama", "katyperry", "jimmyfallon", "KimKardashian"]

# Each persona = one interpretable preference over a real feature (the feature it
# scores high on). The juror is NOT told this rule; it must infer it from labels.
PERSONA_FEATURE = {
    "concise": "neg_length",      # likes short tweets
    "hashtag_fan": "n_hashtags",  # likes hashtags
    "chatty": "conversational",   # likes mentions / questions
    "expressive": "expressive",   # likes exclamation + CAPS energy
    "linkster": "has_url",        # likes tweets that share links
}


def features(text: str) -> dict:
    letters = [c for c in text if c.isalpha()]
    caps_ratio = sum(c.isupper() for c in letters) / max(1, len(letters))
    return {
        "length": len(text),
        "neg_length": -len(text),
        "n_hashtags": text.count("#"),
        "conversational": text.count("@") + (1 if "?" in text else 0),
        "expressive": text.count("!") + 3 * caps_ratio,
        "has_url": 1.0 if "http" in text else 0.0,
    }


def percentile(values: list[float]) -> list[float]:
    """Rank each value to [0,1] (ties share the average rank)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    for rank, i in enumerate(order):
        ranks[i] = rank / max(1, len(values) - 1)
    return ranks


def main() -> None:
    p = argparse.ArgumentParser(description="Build the tweet preference benchmark.")
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--authors", nargs="+", default=DEFAULT_AUTHORS)
    p.add_argument("--per-author", type=int, default=18)
    p.add_argument("--test-frac", type=float, default=0.35)
    p.add_argument("--seed", type=int, default=5)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()

    rng = random.Random(args.seed)
    df = pd.read_csv(args.csv)
    df = df[(df.language == "en") & df.content.notna()]
    df = df[df.content.str.len().between(20, 280)]

    rows: list[dict] = []
    for author in args.authors:
        sub = df[df.author == author]
        if len(sub) < args.per_author:
            continue
        sub = sub.sample(n=args.per_author, random_state=args.seed)
        likes = sub.number_of_likes.astype(float).tolist()
        pop = percentile(likes)  # within-author popularity
        for (_, tw), pr in zip(sub.iterrows(), pop):
            rows.append({"author": author, "text": str(tw.content).strip(),
                         "popularity": round(pr, 4), "_feat": features(str(tw.content))})

    # Persona likeness = global percentile of each persona's chosen feature.
    for pid, feat in PERSONA_FEATURE.items():
        pcts = percentile([r["_feat"][feat] for r in rows])
        for r, v in zip(rows, pcts):
            r.setdefault("persona_likeness", {})[pid] = round(v, 4)

    rng.shuffle(rows)
    n_test = round(len(rows) * args.test_frac)
    for i, r in enumerate(rows):
        r["id"] = f"tw-{i:03d}"
        r["split"] = "test" if i < n_test else "train"
        r["features"] = {k: round(v, 3) for k, v in r.pop("_feat").items()}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_train = sum(r["split"] == "train" for r in rows)
    print(f"wrote {len(rows)} tweets ({n_train} train / {len(rows)-n_train} test) "
          f"from {len(set(r['author'] for r in rows))} authors -> {args.out}")
    print(f"personas: {list(PERSONA_FEATURE)}")


if __name__ == "__main__":
    main()
