"""Offline ($0) test of the API: feedback loop learns; data endpoints serve."""

from __future__ import annotations

from fastapi.testclient import TestClient

from judy.api.server import app

client = TestClient(app)


def test_health_and_experiments():
    assert client.get("/api/health").json()["ok"] is True
    exp = client.get("/api/experiments").json()
    assert "variants" in exp and len(exp["variants"]) >= 4


def test_preference_feedback_learns_concise():
    client.post("/api/preference/reset")
    for _ in range(10):
        nxt = client.get("/api/preference/next").json()
        if nxt.get("done"):
            break
        chosen = "A" if len(nxt["answer_a"]) <= len(nxt["answer_b"]) else "B"
        client.post(
            "/api/preference/feedback",
            json={"index": nxt["index"], "feedback_mode": "best", "chosen": chosen},
        )
    state = client.get("/api/preference/state").json()
    # a concise-preferring user should drive weight onto the concise hypothesis
    assert state["weights"]["prefers_concise"] > state["weights"]["prefers_detailed"]
    assert state["n_feedback"] >= 5


def test_preference_rating_and_loop_ready_export():
    client.post("/api/preference/reset")
    nxt = client.get("/api/preference/next").json()
    resp = client.post(
        "/api/preference/feedback",
        json={
            "index": nxt["index"],
            "feedback_mode": "score",
            "score_a": 5,
            "score_b": 2,
            "note": "Prefer the more detailed but still clear answer here.",
        },
    )
    body = resp.json()
    assert body["feedback_mode"] == "score"
    assert body["loop_ready"]["selected"] == "A"

    loop_ready = client.get("/api/preference/loop-ready").json()
    assert len(loop_ready["events"]) == 1
    assert loop_ready["events"][0]["feedback_type"] == "rating"


def test_preference_simulate_run_returns_method_comparison():
    client.post("/api/preference/reset")
    for _ in range(6):
        nxt = client.get("/api/preference/next").json()
        if nxt.get("done"):
            break
        chosen = "A" if len(nxt["answer_a"]) <= len(nxt["answer_b"]) else "B"
        client.post(
            "/api/preference/feedback",
            json={
                "index": nxt["index"],
                "feedback_mode": "ranking",
                "ranking": [chosen, "B" if chosen == "A" else "A"],
                "note": "Prefer concise answers for simpler questions.",
            },
        )
    sim = client.get("/api/preference/simulate-run").json()
    assert sim["train_events"] >= 3
    assert sim["eval_events"] >= 1
    assert len(sim["results"]) == 3
    assert {result["method"] for result in sim["results"]} == {
        "winner_only",
        "weighted_feedback",
        "note_aware",
    }
