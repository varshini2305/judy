"""Dataset IO and the dev/held-out split, with the held-out guard (brief §2).

Items are stored as JSONL with a ``split`` field. The loader enforces two
invariants so the self-improvement loop can never memorize the test set:

1. dev and held-out item ids are disjoint;
2. held-out contains at least one ``task_type`` that never appears in dev
   (proving a *general* judging skill, not task memorization).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from judy.judge.schema import Item

Split = str  # "dev" | "heldout"


@dataclass(frozen=True)
class Dataset:
    dev: list[Item]
    heldout: list[Item]

    @property
    def unseen_heldout_types(self) -> set[str]:
        return {i.task_type for i in self.heldout} - {i.task_type for i in self.dev}


def write_dataset(path: Path, dev: list[Item], heldout: list[Item]) -> None:
    """Write dev + held-out items to a single JSONL file with split tags."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for split, items in (("dev", dev), ("heldout", heldout)):
            for item in items:
                fh.write(json.dumps({**item.model_dump(), "split": split}) + "\n")


def load_dataset(path: Path) -> Dataset:
    """Load and validate a dataset, enforcing the held-out guard."""
    dev: list[Item] = []
    heldout: list[Item] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        split = row.get("split", "dev")
        item = Item.model_validate(row)
        (heldout if split == "heldout" else dev).append(item)

    _assert_guard(dev, heldout)
    return Dataset(dev=dev, heldout=heldout)


def _assert_guard(dev: list[Item], heldout: list[Item]) -> None:
    dev_ids = {i.id for i in dev}
    held_ids = {i.id for i in heldout}
    overlap = dev_ids & held_ids
    assert not overlap, f"dev/held-out id overlap: {sorted(overlap)[:5]}"

    unseen = {i.task_type for i in heldout} - {i.task_type for i in dev}
    assert unseen, "held-out must contain task_types absent from dev (generalization guard)"
