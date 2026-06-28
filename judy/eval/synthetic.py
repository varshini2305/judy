"""Helpers for evaluating judges on Judy's synthetic objective benchmark."""

from __future__ import annotations

import json
from pathlib import Path

from judy.judge.schema import Candidate, Item


def load_synthetic_objective_items(path: Path) -> list[Item]:
    """Map synthetic objective rows into Judy Items for evaluation."""
    items: list[Item] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("mode") != "objective_pairwise":
            continue
        better = str(row.get("objectively_better", "A")).strip().upper()
        left_tier, right_tier = ("A", "C") if better == "A" else ("C", "A")
        items.append(
            Item(
                id=str(row["id"]),
                task_type=str(row["task_type"]),
                system_prompt=str(row["system_prompt"]),
                question=str(row["question"]),
                gold_answer="",
                candidates=[
                    Candidate(tier=left_tier, text=str(row["answer_a"])),
                    Candidate(tier=right_tier, text=str(row["answer_b"])),
                ],
                known_ordering=("A", "C"),
            )
        )
    return items
