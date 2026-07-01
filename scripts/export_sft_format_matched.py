"""Export FORMAT-MATCHED SFT data — fixes the train/serve skew.

Unlike the existing bare-letter export, every training row here uses the *exact*
format the judge is evaluated/served in:
- prompt  = `build_user_prompt(...)` (the real judge user message),
- system  = the `SKILL.md` policy,
- target  = the real JSON verdict `{verdict,margin,rationale,criteria}`.

Targets are produced by **rejection sampling**: a teacher judge generates a JSON
verdict; we keep the row only if its verdict matches the gold label (so the target
carries a *verified-correct* reasoning trace). Rows the teacher gets wrong are
dropped (STaR-style) unless `--no-reasoning`, which emits a minimal correct verdict
with an empty rationale (weaker baseline; labelled as such).

Outputs Vertex tuning JSONL (`systemInstruction`/`contents`) for
`scripts/submit_vertex_sft.py`, plus a flat inspection file. After tuning, evaluate
with the EXISTING `scripts/eval_tuned_judge.py` (JSON format) — which now matches
training, so it's a fair test.

Run (needs judge creds for reasoning targets):
  PYTHONPATH=. python scripts/export_sft_format_matched.py \
    --dataset judy/data/datasets/judy_benchmark_objective_100_full.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from pathlib import Path

from judy.config import CONFIG
from judy.eval.synthetic import load_synthetic_objective_items
from judy.judge.judge import _coerce_verdict, build_user_prompt
from judy.judge.schema import Item
from judy.judge.skill import load_skill
from judy.llm.gemini import GeminiClient

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = REPO_ROOT / "judy/data/datasets/judy_benchmark_objective_100_full.jsonl"
DEFAULT_OUT = REPO_ROOT / "judy/tuning_datasets/sft/gemini35-flash/judy_format_matched_v1"


def _presented(item: Item, swap: bool) -> tuple[str, str, str]:
    """Return (answer_a_shown, answer_b_shown, presented_winner_letter)."""
    a_idx, b_idx = (1, 0) if swap else (0, 1)
    canonical_winner = item.correct_side()  # "A"/"B" over canonical candidates
    presented_winner = canonical_winner if not swap else ("B" if canonical_winner == "A" else "A")
    return item.candidates[a_idx].text, item.candidates[b_idx].text, presented_winner


async def make_target(client, policy: str, item: Item, swap: bool, *, reasoning: bool) -> dict | None:
    """Build one format-matched target (JSON verdict). None => drop (teacher was wrong)."""
    a, b, winner = _presented(item, swap)
    prompt = build_user_prompt(item.system_prompt, item.question, a, b)
    if not reasoning:
        target = {"verdict": winner, "margin": 4, "rationale": "", "criteria": []}
        return {"prompt": prompt, "system": policy, "target": target}
    data = await client.generate_json(prompt, system_instruction=policy)
    v = _coerce_verdict(data)
    if v.verdict != winner:  # rejection sampling: keep only verified-correct traces
        return None
    target = {"verdict": v.verdict, "margin": v.margin, "rationale": v.rationale,
              "criteria": [c.model_dump() for c in v.criteria]}
    return {"prompt": prompt, "system": policy, "target": target}


def to_vertex_row(row: dict) -> dict:
    """Wrap a flat row into Vertex Gemini tuning format (systemInstruction/contents)."""
    return {
        "systemInstruction": {"parts": [{"text": row["system"]}]},
        "contents": [
            {"role": "user", "parts": [{"text": row["prompt"]}]},
            {"role": "model", "parts": [{"text": json.dumps(row["target"])}]},
        ],
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


async def run(dataset: Path, out_dir: Path, *, val_frac: float, reasoning: bool, seed: int) -> None:
    items = load_synthetic_objective_items(dataset)
    policy = load_skill(CONFIG.skill_path)
    client = GeminiClient() if reasoning else None

    tasks = [(item, swap) for item in items for swap in (False, True)]
    results = await asyncio.gather(*(make_target(client, policy, it, sw, reasoning=reasoning)
                                     for it, sw in tasks))
    rows = [r for r in results if r is not None]
    dropped = len(results) - len(rows)

    rng = random.Random(seed)
    rng.shuffle(rows)
    n_val = max(1, round(len(rows) * val_frac))
    val, train = rows[:n_val], rows[n_val:]

    _write_jsonl(out_dir / "train.jsonl", train)
    _write_jsonl(out_dir / "val.jsonl", val)
    _write_jsonl(out_dir / "vertex_train.jsonl", [to_vertex_row(r) for r in train])
    _write_jsonl(out_dir / "vertex_val.jsonl", [to_vertex_row(r) for r in val])
    (out_dir / "metadata.json").write_text(json.dumps({
        "dataset": str(dataset), "format": "matched_json_verdict",
        "reasoning_targets": reasoning, "n_train": len(train), "n_val": len(val),
        "dropped_rejection_sampled": dropped,
        "note": "targets match build_user_prompt + SKILL.md + JSON verdict; eval with eval_tuned_judge.py",
    }, indent=2), encoding="utf-8")

    if client is not None:
        print(f"teacher cost: {client.usage.summary()}")
    print(f"wrote {len(train)} train / {len(val)} val rows (dropped {dropped} wrong-teacher) -> {out_dir}")
    print(f"Vertex files: {out_dir/'vertex_train.jsonl'} , {out_dir/'vertex_val.jsonl'}")


def main() -> None:
    p = argparse.ArgumentParser(description="Export format-matched (JSON-verdict) SFT data.")
    p.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--val-frac", type=float, default=0.1)
    p.add_argument("--no-reasoning", action="store_true",
                   help="skip rejection sampling: emit correct verdict + empty rationale (weaker)")
    p.add_argument("--seed", type=int, default=13)
    args = p.parse_args()
    asyncio.run(run(args.dataset, args.out, val_frac=args.val_frac,
                    reasoning=not args.no_reasoning, seed=args.seed))


if __name__ == "__main__":
    main()
