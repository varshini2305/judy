"""Generate the subjective-creative preference benchmark for the judge-jury (V4).

Pipeline (all generation via OpenAI ``gpt-5.4-nano``):
  1. Generate creative pairwise items (two competent pieces that differ on a
     contrasting aesthetic axis) using ``prompts/creative_pref/creative_item.md``.
  2. For every (item, persona) pair, have the persona label which piece IT
     prefers by role-playing its hidden taste policy (the label oracle).
  3. Assign ids + a per-item train/test split and write the dataset JSONL.

The jurors in ``judy/eval/jury.py`` later learn each persona's taste from the
TRAIN labels only and are scored on the TEST labels — so the split lives in the
data, not the eval.

Run (tiny smoke first, then full):
  PYTHONPATH=. python scripts/generate_creative_pref_benchmark.py --n 2 --out smoke.jsonl
  PYTHONPATH=. python scripts/generate_creative_pref_benchmark.py --n 24
"""

from __future__ import annotations

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from judy.data.personas import PERSONAS
from judy.synth_benchmark.openai_client import OpenAIError, OpenAIResponsesClient

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts" / "creative_pref"
DEFAULT_OUT = REPO_ROOT / "judy" / "data" / "datasets" / "creative_pref_benchmark.jsonl"

_ITEM_KEYS = {"form", "system_prompt", "question", "answer_a", "answer_b",
              "style_axis", "style_contrast"}


def generate_items(client: OpenAIResponsesClient, n: int, batch_size: int,
                   rng: random.Random) -> list[dict]:
    """Generate ``n`` creative pairwise items (no labels yet)."""
    template = (PROMPTS_DIR / "creative_item.md").read_text(encoding="utf-8").strip()
    items: list[dict] = []
    batch_idx = 0
    max_attempts = max(8, (n + batch_size - 1) * 4)
    while len(items) < n and batch_idx < max_attempts:
        batch_n = min(batch_size, n - len(items))
        prompt = f"{template}\n\nGenerate exactly {batch_n} cases. Batch id: {batch_idx}."
        data = client.generate_json(prompt)
        for case in data.get("cases") or []:
            if _ITEM_KEYS.issubset(case) and all(case[k] for k in _ITEM_KEYS):
                items.append({k: str(case[k]) for k in _ITEM_KEYS})
                if len(items) >= n:
                    break
        batch_idx += 1
    if len(items) < n:
        raise OpenAIError(f"Only generated {len(items)}/{n} valid creative items")
    return items[:n]


def label_item(client: OpenAIResponsesClient, item: dict, persona, *, flip: bool) -> dict:
    """Have one persona label one item by role-playing its hidden taste.

    ``flip`` presents B as A (and vice versa) to the labeller, then maps the
    verdict back to canonical A/B — this cancels the labeller's position bias so
    a preference reflects taste, not which piece was shown first.
    """
    template = (PROMPTS_DIR / "persona_label.md").read_text(encoding="utf-8")
    fields = dict(item)
    if flip:
        fields["answer_a"], fields["answer_b"] = item["answer_b"], item["answer_a"]
    prompt = template.format(hidden_policy=persona.hidden_policy, **fields)
    data = client.generate_json(prompt)
    shown = str(data.get("preferred", "A")).strip().upper()
    shown = shown if shown in {"A", "B"} else "A"
    canonical = shown if not flip else ("B" if shown == "A" else "A")
    rating_a, rating_b = _clamp(data.get("rating_a")), _clamp(data.get("rating_b"))
    if flip:
        rating_a, rating_b = rating_b, rating_a
    return {
        "preferred": canonical,
        "rating_a": rating_a,
        "rating_b": rating_b,
        "rationale": str(data.get("rationale", ""))[:300],
    }


def _clamp(value: object) -> int:
    try:
        return max(1, min(5, int(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 3


def _split_for(idx: int, n: int, test_frac: float) -> str:
    """Deterministic per-item split: last ``test_frac`` of items are test."""
    n_train = round(n * (1 - test_frac))
    return "train" if idx < n_train else "test"


def main() -> None:
    p = argparse.ArgumentParser(description="Generate the creative preference benchmark.")
    p.add_argument("--n", type=int, default=24, help="number of creative items")
    p.add_argument("--test-frac", type=float, default=0.42, help="fraction of items held out for test")
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--seed", type=int, default=29)
    p.add_argument("--model", default="gpt-5.4-nano")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()

    rng = random.Random(args.seed)
    client = OpenAIResponsesClient(model=args.model)

    print(f"Generating {args.n} creative items via {args.model} ...")
    items = generate_items(client, args.n, args.batch_size, rng)
    rng.shuffle(items)

    print(f"Labelling {len(items)} items x {len(PERSONAS)} personas ...")
    jobs = [(i, item, persona, rng.random() < 0.5)
            for i, item in enumerate(items) for persona in PERSONAS]
    labels: dict[tuple[int, str], dict] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(label_item, client, item, persona, flip=flip): (i, persona.id)
                   for (i, item, persona, flip) in jobs}
        for fut in futures:
            i, pid = futures[fut]
            labels[(i, pid)] = fut.result()

    rows = []
    for i, item in enumerate(items):
        rows.append({
            "id": f"cre-{i:03d}",
            "split": _split_for(i, len(items), args.test_frac),
            **item,
            "labels": {p.id: labels[(i, p.id)] for p in PERSONAS},
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    n_train = sum(1 for r in rows if r["split"] == "train")
    _report_divergence(rows)
    print(f"\nWrote {len(rows)} items ({n_train} train / {len(rows) - n_train} test) "
          f"x {len(PERSONAS)} personas -> {args.out}")


def _report_divergence(rows: list[dict]) -> None:
    """Sanity check: how often do the 5 personas actually disagree on an item?"""
    split_counts = {"unanimous": 0, "split": 0}
    for r in rows:
        prefs = {lab["preferred"] for lab in r["labels"].values()}
        split_counts["split" if len(prefs) > 1 else "unanimous"] += 1
    total = len(rows) or 1
    print(f"Preference divergence: {split_counts['split']}/{total} items have "
          f"persona disagreement (the rest are unanimous).")


if __name__ == "__main__":
    main()
