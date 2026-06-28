"""Dataset export helpers for Gemini SFT and preference tuning.

These functions convert Judy's internal datasets into flat JSONL rows that are
easy to inspect, version, upload to GCS, and later adapt to the exact Agent
Platform schema required by Google Cloud.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

from judy.judge.schema import Item
from judy.preference.session import make_style_pairs
from judy.preference.simulated_user import BUILTIN_USERS, SimulatedUser

_PREFERENCE_CONTEXT = {
    "concise": "This user prefers concise, to-the-point answers.",
    "detailed": "This user prefers detailed, thorough answers.",
    "anti_repetition": "This user dislikes repetition and prefers less redundant answers.",
    "conditional": (
        "This user prefers concise answers for simple questions and more detailed "
        "answers for complex questions."
    ),
    "drifting": (
        "This user has changing preferences over time; use the stated preference "
        "signal in-context rather than assuming one fixed style."
    ),
}


def build_sft_prompt(system_prompt: str, question: str, answer_a: str, answer_b: str) -> str:
    """Prompt template for pairwise supervised judge tuning."""
    return (
        "You are a question-answering judge.\n\n"
        f"SYSTEM PROMPT:\n{system_prompt}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"ANSWER A:\n{answer_a}\n\n"
        f"ANSWER B:\n{answer_b}\n\n"
        "Return only which answer is better: A or B."
    )


def build_preference_prompt(
    preference_context: str,
    system_prompt: str,
    question: str,
    answer_a: str,
    answer_b: str,
) -> str:
    """Prompt template for preference-tuning answer selection."""
    return (
        "You are selecting between two question-answering answers for a specific user's taste.\n"
        f"USER PREFERENCE:\n{preference_context}\n\n"
        "Correctness and spec-compliance come first. If both answers are "
        "acceptable, choose the one that better matches the user's preference.\n\n"
        f"SYSTEM PROMPT:\n{system_prompt}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"ANSWER A:\n{answer_a}\n\n"
        f"ANSWER B:\n{answer_b}\n\n"
        "Return only which answer the user would prefer: A or B."
    )


def item_to_sft_rows(
    item: Item,
    *,
    source: str,
    split: str,
    include_swap: bool = True,
) -> list[dict[str, Any]]:
    """Convert one Judy item into one or two pairwise SFT rows."""
    winner = item.correct_side()
    rows = [_make_sft_row(item, source=source, split=split, swap=False, winner=winner)]
    if include_swap:
        swapped_winner = "B" if winner == "A" else "A"
        rows.append(_make_sft_row(item, source=source, split=split, swap=True, winner=swapped_winner))
    return rows


def benchmark_pair_to_sft_rows(
    row: dict[str, Any],
    *,
    source: str,
    split: str,
    include_swap: bool = True,
) -> list[dict[str, Any]]:
    """Convert a benchmark {chosen, rejected} pair into one or two SFT rows."""
    system_prompt = str(
        row.get(
            "system_prompt",
            "Answer the user's question accurately and follow any explicit constraints.",
        )
    )
    question = str(row["question"])
    chosen = str(row["chosen"])
    rejected = str(row["rejected"])
    task_type = str(row.get("subset", source))
    base = {
        "id": str(row["id"]),
        "source": source,
        "split": split,
        "task_type": task_type,
        "system_prompt": system_prompt,
        "question": question,
        "rationale": str(row.get("rationale", "")),
    }
    rows = [
        {
            **base,
            "swap": False,
            "answer_a": chosen,
            "answer_b": rejected,
            "winner": "A",
            "prompt": build_sft_prompt(system_prompt, question, chosen, rejected),
            "target": "A",
        }
    ]
    if include_swap:
        rows.append(
            {
                **base,
                "swap": True,
                "answer_a": rejected,
                "answer_b": chosen,
                "winner": "B",
                "prompt": build_sft_prompt(system_prompt, question, rejected, chosen),
                "target": "B",
            }
        )
    return rows


def synthetic_objective_pair_to_sft_rows(
    row: dict[str, Any],
    *,
    source: str,
    split: str,
    include_swap: bool = True,
) -> list[dict[str, Any]]:
    """Convert one synthetic objective benchmark row into SFT rows."""
    better = str(row["objectively_better"]).strip().upper()
    answer_a = str(row["answer_a"])
    answer_b = str(row["answer_b"])
    winner = better if better in {"A", "B"} else "A"
    base = {
        "id": str(row["id"]),
        "source": source,
        "split": split,
        "task_type": str(row["task_type"]),
        "system_prompt": str(row["system_prompt"]),
        "question": str(row["question"]),
        "difficulty": str(row.get("difficulty", "unknown")),
        "rationale": str(row.get("winner_reason", "")),
        "failure_axis": str(row.get("failure_axis", "")),
    }
    chosen = answer_a if winner == "A" else answer_b
    rejected = answer_b if winner == "A" else answer_a
    rows = [
        {
            **base,
            "swap": False,
            "answer_a": chosen,
            "answer_b": rejected,
            "winner": "A",
            "prompt": build_sft_prompt(base["system_prompt"], base["question"], chosen, rejected),
            "target": "A",
        }
    ]
    if include_swap:
        rows.append(
            {
                **base,
                "swap": True,
                "answer_a": rejected,
                "answer_b": chosen,
                "winner": "B",
                "prompt": build_sft_prompt(base["system_prompt"], base["question"], rejected, chosen),
                "target": "B",
            }
        )
    return rows


def split_list(
    rows: list[dict[str, Any]],
    *,
    train_frac: float,
    val_frac: float,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Shuffle and split rows into train/val/test buckets."""
    assert 0.0 < train_frac < 1.0
    assert 0.0 <= val_frac < 1.0
    assert train_frac + val_frac < 1.0
    items = list(rows)
    random.Random(seed).shuffle(items)
    n = len(items)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    train = items[:n_train]
    val = items[n_train : n_train + n_val]
    test = items[n_train + n_val :]
    return train, val, test


def split_case_rows(
    rows: list[dict[str, Any]],
    *,
    train_frac: float,
    val_frac: float,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Shuffle and split source cases before expanding to swap-balanced rows."""
    train_cases, val_cases, test_cases = split_list(
        rows, train_frac=train_frac, val_frac=val_frac, seed=seed
    )
    return train_cases, val_cases, test_cases


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL rows from disk."""
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write JSONL rows to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def generate_preference_rows(
    *,
    user_keys: list[str],
    pairs_per_user: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Generate mixed-user simulated preference examples."""
    rows: list[dict[str, Any]] = []
    for idx, key in enumerate(user_keys):
        factory = BUILTIN_USERS[key]
        user = factory()
        pairs = make_style_pairs(pairs_per_user, seed=seed + idx)
        context = _PREFERENCE_CONTEXT.get(key, f"This user has preference profile: {key}.")
        for step, (answer_a, answer_b, task_type) in enumerate(pairs):
            complexity = "complex" if task_type == "complex_q" else "simple"
            chosen = user.choose(
                answer_a,
                answer_b,
                task_type=task_type,
                complexity=complexity,
                step=step,
            )
            rejected = "B" if chosen == "A" else "A"
            question = _infer_question(answer_a, answer_b)
            system_prompt = (
                "Answer the user's question accurately and clearly. Both answers are "
                "assumed correct unless stated otherwise."
            )
            rows.append(
                {
                    "id": f"pref-{key}-{step:03d}",
                    "source": "simulated_preference",
                    "split": "unspecified",
                    "user_id": user.name,
                    "preference_key": key,
                    "preference_context": context,
                    "task_type": task_type,
                    "complexity": complexity,
                    "system_prompt": system_prompt,
                    "question": question,
                    "answer_a": answer_a,
                    "answer_b": answer_b,
                    "chosen": chosen,
                    "rejected": rejected,
                    "chosen_answer": answer_a if chosen == "A" else answer_b,
                    "rejected_answer": answer_b if chosen == "A" else answer_a,
                    "prompt": build_preference_prompt(
                        context, system_prompt, question, answer_a, answer_b
                    ),
                    "target": chosen,
                }
            )
    return rows


def _make_sft_row(
    item: Item,
    *,
    source: str,
    split: str,
    swap: bool,
    winner: str,
) -> dict[str, Any]:
    a_idx, b_idx = (1, 0) if swap else (0, 1)
    answer_a = item.candidates[a_idx].text
    answer_b = item.candidates[b_idx].text
    return {
        "id": item.id,
        "source": source,
        "split": split,
        "task_type": item.task_type,
        "system_prompt": item.system_prompt,
        "question": item.question,
        "answer_a": answer_a,
        "answer_b": answer_b,
        "winner": winner,
        "swap": swap,
        "rationale": "",
        "prompt": build_sft_prompt(item.system_prompt, item.question, answer_a, answer_b),
        "target": winner,
    }


def _infer_question(answer_a: str, answer_b: str) -> str:
    """Best-effort question recovery for simulated style pairs."""
    source = answer_a if len(answer_a) <= len(answer_b) else answer_b
    stem = re.sub(r"\s+explained.*$", "", source.strip(), flags=re.IGNORECASE)
    stem = stem.rstrip(". ")
    return f"Explain {stem.lower()}."
