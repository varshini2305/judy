"""Offline ($0) test of the literary benchmark builder (real content + ratings)."""

from __future__ import annotations

from scripts.build_literary_benchmark import (
    assign_splits,
    fold_ratings,
    qualifying_users,
)


def _works():
    return [{"work_id": f"w{i}", "kind": "poem", "title": f"t{i}", "author": "a",
             "text": "x", "attributes": {"genre": "lyric"}} for i in range(6)]


def _ratings():
    # u1 rates all 6, u2 rates all 6, u3 rates only 2 (won't qualify as a juror).
    rs = []
    for i in range(6):
        rs.append({"user_id": "u1", "work_id": f"w{i}", "rating": (i % 5) + 1})
        rs.append({"user_id": "u2", "work_id": f"w{i}", "rating": 5 - (i % 5)})
    rs += [{"user_id": "u3", "work_id": "w0", "rating": 3},
           {"user_id": "u3", "work_id": "w1", "rating": 4}]
    return rs


def test_fold_computes_consensus_and_user_ratings():
    rows = fold_ratings(_works(), _ratings())
    assert len(rows) == 6
    w0 = next(r for r in rows if r["work_id"] == "w0")
    # u1=1, u2=5, u3=3 -> mean 3.0
    assert w0["consensus_rating"] == 3.0
    assert w0["n_ratings"] == 3
    assert w0["user_ratings"]["u1"] == 1


def test_fold_drops_works_without_ratings():
    works = _works() + [{"work_id": "w_unrated", "kind": "poem", "title": "z",
                         "author": "a", "text": "x", "attributes": {}}]
    rows = fold_ratings(works, _ratings())
    assert all(r["work_id"] != "w_unrated" for r in rows)


def test_splits_and_qualifying_users():
    rows = fold_ratings(_works(), _ratings())
    assign_splits(rows, test_frac=0.5, seed=1)
    assert sum(r["split"] == "test" for r in rows) == 3
    users = qualifying_users(rows, min_train=2, min_test=2)
    # u1/u2 rated all 6 (3 train + 3 test) -> qualify; u3 rated only 2 -> not.
    assert set(users) == {"u1", "u2"}
