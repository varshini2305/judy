"""V4 (minimal) — judge-jury for tweet likability, on real Kaggle tweet data.

Two layers, measured against real/transparent ground truth:

- **Central judge (objective layer):** learns, by self-critique over training
  tweets + their real relative popularity, which content features predict
  likability. We then check how well its predicted scores rank-correlate with
  real popularity (normalized like count).
- **Jurors (subjective layer):** 5 simulated users, each with a distinct taste.
  Given only a few of a user's labelled tweets (+ the judge's guidelines), a
  juror predicts that user's likeness for unseen tweets.

Reported: judge↔popularity, each juror↔its own user, the personalization matrix,
whether judge guidance helps jurors (ablation), and whether the **jury mean**
recovers real popularity. Metric: Spearman rank correlation. Model: gemini-3.5-flash.

Run: PYTHONPATH=. python -m judy.eval.tweet_jury
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from scipy.stats import spearmanr

from judy.config import CONFIG
from judy.llm.gemini import GeminiClient

DEFAULT_DATASET = CONFIG.runs_dir.parent / "judy/data/datasets/tweet_pref_benchmark.jsonl"


def load_rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def _tweet_list(rows: list[dict]) -> str:
    return "\n".join(f'[{r["id"]}] {r["text"]}' for r in rows)


def _parse_scores(data: dict, ids: list[str]) -> list[float]:
    """Pull a 0..1 score per id from a loose {id: score} JSON; default 0.5."""
    scores = data.get("scores", data)
    out = []
    for i in ids:
        try:
            out.append(max(0.0, min(1.0, float(scores.get(i, 0.5)))))
        except (TypeError, ValueError, AttributeError):
            out.append(0.5)
    return out


# --------------------------------------------------------------------------- #
# Central judge: learn popularity signals, then score test tweets
# --------------------------------------------------------------------------- #
_METACOG = """You are a central judge learning what makes tweets broadly LIKED.
Below are training tweets, each with its real relative likability (0=low, 1=high,
measured within the same author so fame is controlled).

{examples}

Through self-critique, infer GENERAL, transferable guidelines about which content
features predict higher likability — and call out features that look tempting but
are actually red herrings. Return JSON:
{{"guidelines": [<=5 short rules], "red_herrings": [<=3]}}"""

_SCORE = """{role}

Score each of these tweets for likability on a 0..1 scale (1 = most liked).
{tweets}

Return JSON only: {{"scores": {{"<id>": <0..1>, ...}}}} for every id."""


async def judge_learn(client, train: list[dict]) -> str:
    sample = train[:24]
    ex = "\n".join(f'- ({r["popularity"]:.2f}) {r["text"][:160]}' for r in sample)
    data = await client.generate_json(_METACOG.format(examples=ex), temperature=0.3)
    g = data.get("guidelines", []) or []
    rh = data.get("red_herrings", []) or []
    return ("Guidelines for predicting tweet likability:\n"
            + "\n".join(f"- {x}" for x in g)
            + ("\nIgnore these red herrings:\n" + "\n".join(f"- {x}" for x in rh) if rh else ""))


async def score_tweets(client, role: str, test: list[dict]) -> list[float]:
    ids = [r["id"] for r in test]
    data = await client.generate_json(
        _SCORE.format(role=role, tweets=_tweet_list(test)), temperature=0.0)
    return _parse_scores(data, ids)


# --------------------------------------------------------------------------- #
# Jurors: model one user from a few of their labels (+ optional judge guidance)
# --------------------------------------------------------------------------- #
def juror_role(persona_id: str, train: list[dict], *, guidelines: str | None, k: int = 10) -> str:
    examples = [r for r in train][:k]
    shots = "\n".join(
        f'- score {r["persona_likeness"][persona_id]:.2f}: {r["text"][:140]}' for r in examples)
    role = ("You are modelling ONE specific user's personal taste in tweets. "
            "Here is how this user scored some tweets (0=dislike, 1=love):\n" + shots
            + "\nLearn this user's taste and predict their scores for new tweets.")
    if guidelines:
        role = guidelines + "\n\n" + role + (
            " The guidelines above describe general popularity; weigh them only as "
            "far as they fit THIS user's shown taste.")
    return role


def _spear(a: list[float], b: list[float]) -> float:
    r = spearmanr(a, b).correlation
    return float(r) if r == r else 0.0  # nan -> 0


async def run(dataset: Path, *, client=None) -> dict:
    rows = load_rows(dataset)
    train = [r for r in rows if r["split"] == "train"]
    test = [r for r in rows if r["split"] == "test"]
    personas = list(train[0]["persona_likeness"])
    client = client or GeminiClient()

    # Layer 1: judge learns popularity signals, scores test tweets.
    guidelines = await judge_learn(client, train)
    judge_scores = await score_tweets(client, guidelines, test)
    pop = [r["popularity"] for r in test]
    judge_vs_pop = _spear(judge_scores, pop)

    # Layer 2: per-user jurors, with and without the judge's guidance (ablation).
    juror_scores: dict[str, list[float]] = {}
    taste_only: dict[str, float] = {}
    for pid in personas:
        truth = [r["persona_likeness"][pid] for r in test]
        guided = await score_tweets(client, juror_role(pid, train, guidelines=guidelines), test)
        bare = await score_tweets(client, juror_role(pid, train, guidelines=None), test)
        juror_scores[pid] = guided
        taste_only[pid] = _spear(bare, truth)

    # Personalization matrix (guided jurors): spearman(juror_i, user_j on test).
    matrix = {i: {j: _spear(juror_scores[i], [r["persona_likeness"][j] for r in test])
                  for j in personas} for i in personas}
    diag = {i: matrix[i][i] for i in personas}
    diag_wins = sum(1 for i in personas if matrix[i][i] >= max(matrix[i].values()))

    # Does the JURY MEAN recover real popularity?
    jury_mean = [sum(juror_scores[p][k] for p in personas) / len(personas)
                 for k in range(len(test))]
    jury_vs_pop = _spear(jury_mean, pop)

    summary = {
        "dataset": str(dataset), "n_train": len(train), "n_test": len(test),
        "personas": personas, "guidelines": guidelines,
        "judge_vs_popularity": judge_vs_pop,
        "juror_vs_own_user_guided": diag,
        "juror_vs_own_user_taste_only": taste_only,
        "mean_personalization_guided": sum(diag.values()) / len(diag),
        "mean_personalization_taste_only": sum(taste_only.values()) / len(taste_only),
        "matrix_diagonal_wins": diag_wins,
        "personalization_matrix": matrix,
        "jury_mean_vs_popularity": jury_vs_pop,
        "usage": client.usage.as_dict(),
    }
    _persist(summary)
    _print(summary)
    return summary


def _persist(s: dict) -> None:
    run_dir = CONFIG.runs_dir / f"tweetjury-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metrics.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    s["run_dir"] = str(run_dir)


def _print(s: dict) -> None:
    print("\n=== V4 tweet judge-jury (Spearman rank correlation) ===")
    print(f"  train={s['n_train']} · test={s['n_test']} · {len(s['personas'])} users\n")
    print(f"  CENTRAL JUDGE vs real popularity:      {s['judge_vs_popularity']:+.2f}")
    print(f"  JURY MEAN   vs real popularity:        {s['jury_mean_vs_popularity']:+.2f}\n")
    print(f"  {'user':12s}{'taste-only':>12s}{'+judge':>10s}")
    for p in s["personas"]:
        print(f"  {p:12s}{s['juror_vs_own_user_taste_only'][p]:>+12.2f}"
              f"{s['juror_vs_own_user_guided'][p]:>+10.2f}")
    print(f"  {'MEAN':12s}{s['mean_personalization_taste_only']:>+12.2f}"
          f"{s['mean_personalization_guided']:>+10.2f}")
    print(f"\n  personalization: {s['matrix_diagonal_wins']}/{len(s['personas'])} jurors "
          f"rank their own user highest")
    u = s["usage"]
    print(f"  cost: {u['calls']} calls · ~${u['cost_usd']:.4f}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the minimal tweet judge-jury experiment.")
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    asyncio.run(run(ap.parse_args().dataset))


if __name__ == "__main__":
    main()
