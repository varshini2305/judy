"""Evaluation metrics over judged records (brief §5).

- **agreement** — fraction of judged records matching ground truth (headline).
- **position_consistency** — fraction of items whose canonical verdict is
  identical under both answer orders (needs order-swap); plus
  **position_consistent_agreement** — correct under *both* orders.
- **score_spread** — stdev of ``margin``; a collapse toward uniform-high margins
  is an early saturation / over-confidence warning.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from pydantic import BaseModel

from judy.judge.schema import JudgeRecord


class Metrics(BaseModel):
    n_items: int
    n_records: int
    n_errors: int
    agreement: float
    score_spread: float
    # Present only when order-swap produced both orientations per item.
    position_consistency: float | None = None
    position_consistent_agreement: float | None = None


def compute_metrics(records: list[JudgeRecord]) -> Metrics:
    """Aggregate a list of judged records into the headline metrics."""
    if not records:
        return Metrics(
            n_items=0, n_records=0, n_errors=0, agreement=0.0, score_spread=0.0
        )

    margins = np.array([r.margin for r in records], dtype=float)
    correct = np.array([r.correct for r in records], dtype=bool)

    by_item: dict[str, dict[bool, JudgeRecord]] = defaultdict(dict)
    for r in records:
        by_item[r.item_id][r.swap] = r

    paired = [v for v in by_item.values() if True in v and False in v]
    pos_consistency: float | None = None
    pos_consistent_agreement: float | None = None
    if paired:
        consistent = [v[False].verdict == v[True].verdict for v in paired]
        both_correct = [v[False].correct and v[True].correct for v in paired]
        pos_consistency = float(np.mean(consistent))
        pos_consistent_agreement = float(np.mean(both_correct))

    return Metrics(
        n_items=len(by_item),
        n_records=len(records),
        n_errors=int((~correct).sum()),
        agreement=float(correct.mean()),
        score_spread=float(margins.std()),
        position_consistency=pos_consistency,
        position_consistent_agreement=pos_consistent_agreement,
    )
