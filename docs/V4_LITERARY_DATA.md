# V4 — Literary preference benchmark: data contract

> The V4 judge-jury (two-layer) experiment needs **real literary content** +
> **real human ratings**. This file defines the exact inputs so the benchmark is
> reproducible and nothing about the ground truth is fabricated.

## The two layers (and where each comes from)

- **General-population preference = the *average* rating of a work.** This is the
  objective-ish target the **central judge** learns to predict from a work's
  attributes (and learns which attributes are useful vs red herrings).
- **Individual preference = one user's *own* rating.** This is the subjective tilt
  each **juror** learns, on top of the judge's guidelines.

Both are plain aggregations of the ratings you provide — no invented formula.

## Inputs (you provide these two files)

### 1. `works.jsonl` — the literary content + signals
One JSON object per line:

```json
{
  "work_id": "w001",
  "kind": "poem",
  "title": "The Road Not Taken",
  "author": "Robert Frost",
  "text": "<the poem or novel excerpt, full text the model will read>",
  "attributes": {
    "genre": "lyric",
    "author_rating": 4.3,
    "language_complexity": "medium",
    "ambiguity": "high",
    "ending": "open",
    "length_words": 144,
    "popularity": 99000
  }
}
```

- `text` is what the judge/jurors actually read.
- `attributes` are the **signals the judge reasons about**. Include a mix on
  purpose — some genuinely predictive (author_rating, genre), some likely
  **red herrings** (popularity, length) so the judge's self-critique is testable.
- Any attribute keys are fine; the judge treats them generically.

### 2. `ratings.jsonl` — the real human ratings
One JSON object per line:

```json
{"user_id": "u17", "work_id": "w001", "rating": 4}
```

- `rating` on any consistent scale (1–5 assumed). Many users, ideally with
  several users rating overlapping works so the consensus is meaningful and a
  cross-user personalization matrix is possible.

(If your raw ratings are CSV or a different schema, hand them over as-is — I'll
write a one-off adapter to this normalized form rather than make you reformat.)

## Output (the builder produces this)

`judy/data/datasets/literary_pref_benchmark.jsonl`, one line per work:

```json
{
  "work_id": "w001", "kind": "poem", "title": "...", "author": "...",
  "text": "...", "attributes": {...},
  "consensus_rating": 4.1,
  "n_ratings": 12,
  "user_ratings": {"u17": 4, "u3": 5, "...": 3},
  "split": "train"
}
```

Plus a `*_users.json` manifest of which users have enough train/test ratings to
be modeled as jurors.

## How it's used downstream

- **Judge (metacognition loop):** reads `train` works + their `consensus_rating`,
  self-critiques to find which `attributes` predict consensus → writes guidelines.
- **Jurors:** start from the judge's guidelines, learn each modeled user's taste
  from that user's `train` ratings, predict the user's `test` ratings.
- **Ablations:** judge-vs-consensus · juror taste-only vs taste+judge-guidance ·
  jury vs single judge · personalization matrix.

Build: `python scripts/build_literary_benchmark.py --works works.jsonl --ratings ratings.jsonl`
