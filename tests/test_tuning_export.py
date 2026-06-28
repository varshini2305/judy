"""Offline tests for Judy's tuning dataset exporters."""

from __future__ import annotations

import json
from pathlib import Path

from judy.judge.schema import Candidate, Item
from judy.eval.synthetic import load_synthetic_objective_items
from judy.tuning.export import (
    benchmark_pair_to_sft_rows,
    generate_preference_rows,
    item_to_sft_rows,
    split_list,
    synthetic_objective_pair_to_sft_rows,
)


def _item() -> Item:
    return Item(
        id="dev-factual_qa-001",
        task_type="factual_qa",
        system_prompt="Answer accurately and cite a source.",
        question="Who created Superman?",
        gold_answer="Jerry Siegel and Joe Shuster.",
        candidates=[
            Candidate(tier="A", text="Jerry Siegel and Joe Shuster created Superman."),
            Candidate(tier="C", text="Stan Lee created Superman in the 1960s."),
        ],
        known_ordering=("A", "C"),
    )


def test_item_to_sft_rows_balances_order():
    rows = item_to_sft_rows(_item(), source="judy", split="train", include_swap=True)
    assert len(rows) == 2
    assert rows[0]["winner"] == "A"
    assert rows[0]["target"] == "A"
    assert rows[1]["swap"] is True
    assert rows[1]["winner"] == "B"
    assert rows[1]["target"] == "B"
    assert "Return only which answer is better" in rows[0]["prompt"]


def test_benchmark_pair_to_sft_rows_converts_chosen_rejected():
    row = {
        "id": "rb-1",
        "subset": "rewardbench",
        "question": "What is Atlantis?",
        "chosen": "A myth mentioned by Plato.",
        "rejected": "A real city in the Caribbean.",
    }
    rows = benchmark_pair_to_sft_rows(row, source="rewardbench", split="eval", include_swap=True)
    assert len(rows) == 2
    assert rows[0]["answer_a"] == row["chosen"]
    assert rows[0]["target"] == "A"
    assert rows[1]["answer_b"] == row["chosen"]
    assert rows[1]["target"] == "B"


def test_generate_preference_rows_includes_user_context_and_targets():
    rows = generate_preference_rows(user_keys=["concise"], pairs_per_user=4, seed=3)
    assert len(rows) == 4
    assert all("USER PREFERENCE" in row["prompt"] for row in rows)
    assert all(row["target"] in {"A", "B"} for row in rows)
    assert all(row["chosen_answer"] != row["rejected_answer"] for row in rows)


def test_split_list_partitions_all_rows():
    rows = [{"id": str(i)} for i in range(10)]
    train, val, test = split_list(rows, train_frac=0.6, val_frac=0.2, seed=1)
    assert len(train) + len(val) + len(test) == len(rows)
    assert {r["id"] for r in train} | {r["id"] for r in val} | {r["id"] for r in test} == {
        str(i) for i in range(10)
    }


def test_synthetic_objective_pair_to_sft_rows_uses_hidden_winner():
    row = {
        "id": "obj-1",
        "mode": "objective_pairwise",
        "task_type": "numeric_constraint",
        "system_prompt": "Return only the exact answer.",
        "question": "What is 2+2?",
        "answer_a": "3",
        "answer_b": "4",
        "objectively_better": "B",
        "winner_reason": "4 is correct.",
        "failure_axis": "numeric_error",
    }
    rows = synthetic_objective_pair_to_sft_rows(
        row, source="judy_synth_benchmark", split="train", include_swap=True
    )
    assert len(rows) == 2
    assert rows[0]["answer_a"] == "4"
    assert rows[0]["answer_b"] == "3"
    assert rows[0]["target"] == "A"
    assert rows[1]["target"] == "B"
    assert rows[0]["failure_axis"] == "numeric_error"


def test_load_synthetic_objective_items_maps_hidden_label_to_item(tmp_path: Path):
    path = tmp_path / "synthetic.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "obj-1",
                "mode": "objective_pairwise",
                "task_type": "constrained_format",
                "system_prompt": "Follow format.",
                "question": "Give the answer.",
                "answer_a": "wrong",
                "answer_b": "right",
                "objectively_better": "B",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    items = load_synthetic_objective_items(path)
    assert len(items) == 1
    item = items[0]
    assert item.correct_side() == "B"
    assert item.candidates[1].text == "right"
