"""Generate a synthetic Judy benchmark with OpenAI and a standalone review file.

Outputs:
- full JSONL with hidden labels / metadata for internal use
- review JSONL stripped of hidden labels for human evaluation

Run:
  PYTHONPATH=. python scripts/generate_judy_benchmark.py --n 100
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from judy.synth_benchmark.openai_client import OpenAIResponsesClient
from judy.synth_benchmark.review import make_review_row
from judy.tuning.export import write_jsonl

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts" / "judy_benchmark"
DEFAULT_OUT = REPO_ROOT / "judy" / "data" / "datasets"

OBJECTIVE_TASK_TYPES = [
    "factual_qa",
    "constrained_format",
    "persona_support",
    "safety_boundary",
    "numeric_constraint",
    "tone_register",
]
PREFERENCE_TASK_TYPES = [
    "general_explanation",
    "advice",
    "support_reply",
    "productivity_help",
    "learning_assistance",
]
STYLE_AXES = ["conciseness", "detail", "tone", "structure", "caution", "examples"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Judy synthetic benchmark.")
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--objective-frac", type=float, default=0.7)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--model", default="gpt-5.4-nano")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    client = OpenAIResponsesClient(model=args.model)

    objective_n = int(args.n * args.objective_frac)
    preference_n = args.n - objective_n

    full_rows: list[dict] = []
    full_rows.extend(
        _generate_mode_batches(
            client,
            prompt_path=PROMPTS_DIR / "objective_case.md",
            mode="objective_pairwise",
            n_cases=objective_n,
            batch_size=args.batch_size,
            rng=rng,
        )
    )
    full_rows.extend(
        _generate_mode_batches(
            client,
            prompt_path=PROMPTS_DIR / "preference_case.md",
            mode="preference_pairwise",
            n_cases=preference_n,
            batch_size=args.batch_size,
            rng=rng,
        )
    )

    full_rows = _assign_ids_and_shuffle(full_rows, rng)
    review_rows = [make_review_row(row) for row in full_rows]

    out_dir = args.out_dir
    full_path = out_dir / "judy_benchmark_full.jsonl"
    review_path = out_dir / "judy_benchmark_review.jsonl"
    meta_path = out_dir / "judy_benchmark_metadata.json"

    write_jsonl(full_path, full_rows)
    write_jsonl(review_path, review_rows)
    meta_path.write_text(
        json.dumps(
            {
                "generator_model": args.model,
                "n_cases": len(full_rows),
                "objective_cases": sum(1 for r in full_rows if r["mode"] == "objective_pairwise"),
                "preference_cases": sum(1 for r in full_rows if r["mode"] == "preference_pairwise"),
                "seed": args.seed,
                "prompt_files": {
                    "objective": str(PROMPTS_DIR / "objective_case.md"),
                    "preference": str(PROMPTS_DIR / "preference_case.md"),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote full benchmark to {full_path}")
    print(f"Wrote review benchmark to {review_path}")
    print(f"Wrote metadata to {meta_path}")


def _generate_mode_batches(
    client: OpenAIResponsesClient,
    *,
    prompt_path: Path,
    mode: str,
    n_cases: int,
    batch_size: int,
    rng: random.Random,
) -> list[dict]:
    prompt_template = prompt_path.read_text(encoding="utf-8").strip()
    rows: list[dict] = []
    batch_idx = 0
    attempts = 0
    max_attempts = max(12, (n_cases + batch_size - 1) * 4)
    while len(rows) < n_cases and attempts < max_attempts:
        attempts += 1
        remaining = n_cases - len(rows)
        batch_n = min(batch_size, remaining)
        mode_prompt = _render_mode_prompt(
            prompt_template,
            mode=mode,
            n=batch_n,
            rng=rng,
            batch_idx=batch_idx,
        )
        data = client.generate_json(mode_prompt)
        cases = data.get("cases") or []
        accepted = 0
        for case in cases:
            normalized = _normalize_case(case, mode=mode, prompt_version=prompt_path.name)
            if normalized is None:
                continue
            rows.append(normalized)
            accepted += 1
            if accepted >= batch_n or len(rows) >= n_cases:
                break
        batch_idx += 1
    if len(rows) < n_cases:
        raise ValueError(
            f"Could only generate {len(rows)}/{n_cases} valid {mode} cases from {prompt_path.name}"
        )
    return rows[:n_cases]


def _render_mode_prompt(
    base_prompt: str,
    *,
    mode: str,
    n: int,
    rng: random.Random,
    batch_idx: int,
) -> str:
    if mode == "objective_pairwise":
        task_types = rng.sample(OBJECTIVE_TASK_TYPES, k=min(4, len(OBJECTIVE_TASK_TYPES)))
        extra = (
            f"Generate exactly {n} cases.\n"
            f"Target task types for this batch: {', '.join(task_types)}.\n"
            f"Batch id: {batch_idx}.\n"
        )
    else:
        task_types = rng.sample(PREFERENCE_TASK_TYPES, k=min(3, len(PREFERENCE_TASK_TYPES)))
        axes = rng.sample(STYLE_AXES, k=min(3, len(STYLE_AXES)))
        extra = (
            f"Generate exactly {n} cases.\n"
            f"Target task types for this batch: {', '.join(task_types)}.\n"
            f"Emphasize style axes from this set: {', '.join(axes)}.\n"
            f"Batch id: {batch_idx}.\n"
        )
    return f"{base_prompt}\n\n{extra}"


def _normalize_case(case: dict, *, mode: str, prompt_version: str) -> dict | None:
    required = {"task_type", "system_prompt", "question", "answer_a", "answer_b"}
    if mode == "objective_pairwise":
        required |= {"objectively_better", "failure_axis", "winner_reason"}
    else:
        required |= {"style_axis", "style_contrast"}
    if any(key not in case or case[key] in (None, "") for key in required):
        return None
    base = {
        "id": "",
        "mode": mode,
        "task_type": str(case["task_type"]),
        "system_prompt": str(case["system_prompt"]),
        "question": str(case["question"]),
        "answer_a": str(case["answer_a"]),
        "answer_b": str(case["answer_b"]),
        "difficulty": str(case.get("difficulty", "medium")),
        "generator_prompt": prompt_version,
    }
    if mode == "objective_pairwise":
        base.update(
            {
                "objectively_better": str(case["objectively_better"]),
                "failure_axis": str(case["failure_axis"]),
                "winner_reason": str(case["winner_reason"]),
            }
        )
    else:
        base.update(
            {
                "style_axis": str(case["style_axis"]),
                "style_contrast": str(case["style_contrast"]),
            }
        )
    return base


def _assign_ids_and_shuffle(rows: list[dict], rng: random.Random) -> list[dict]:
    items = list(rows)
    rng.shuffle(items)
    for idx, row in enumerate(items):
        prefix = "obj" if row["mode"] == "objective_pairwise" else "pref"
        row["id"] = f"{prefix}-{idx:03d}"
    return items


if __name__ == "__main__":
    main()
