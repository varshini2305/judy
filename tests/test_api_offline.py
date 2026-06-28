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
        client.post("/api/preference/feedback", json={"index": nxt["index"], "chosen": chosen})
    state = client.get("/api/preference/state").json()
    # a concise-preferring user should drive weight onto the concise hypothesis
    assert state["weights"]["prefers_concise"] > state["weights"]["prefers_detailed"]
    assert state["n_feedback"] >= 5
