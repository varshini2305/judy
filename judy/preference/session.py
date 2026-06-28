"""Run a preference-learning session and measure the learning curve.

Each step: present a style-pair, the profile *predicts* the user's choice
(scored before learning), the (simulated) user reveals their true choice, then
the profile updates. Rising prediction accuracy = Judy is learning the user.
This runs entirely offline ($0); the LLM judge consumes ``render_context()``
separately.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from judy.preference.profile import UserProfile
from judy.preference.simulated_user import Features, SimulatedUser

# A style-pair: (answer_a, answer_b, task_type).
StylePair = tuple[str, str, str]


def make_style_pairs(n: int, *, seed: int = 0) -> list[StylePair]:
    """Synthesize correctness-equal pairs that differ on style (length/repetition).

    A/B order is randomized so a learner cannot cheat by always picking a side.
    task_type alternates simple/complex to expose conditional preferences.
    """
    rng = random.Random(seed)
    topics = ["the water cycle", "photosynthesis", "inflation", "gravity",
              "the French Revolution", "TCP handshakes", "vaccines", "tides"]
    pairs: list[StylePair] = []
    for i in range(n):
        topic = topics[i % len(topics)]
        short = f"{topic.capitalize()} explained briefly."
        long = (f"{topic.capitalize()} explained in depth, covering the key "
                f"mechanisms, causes, and effects with supporting detail and context.")
        task_type = "complex_q" if i % 2 else "simple_q"
        if rng.random() < 0.5:
            pairs.append((short, long, task_type))
        else:
            pairs.append((long, short, task_type))
    return pairs


def _complexity_of(task_type: str) -> str:
    return "complex" if task_type == "complex_q" else "simple"


def run_session(
    user: SimulatedUser,
    pairs: list[StylePair],
    *,
    complexity_of: Callable[[str], str] = _complexity_of,
) -> dict:
    """Run the learning loop; return per-step correctness + the final profile."""
    profile = UserProfile(user_id=user.name)
    flags: list[bool] = []
    for step, (a, b, task_type) in enumerate(pairs):
        fa, fb = Features.of(a), Features.of(b)
        cx = complexity_of(task_type)
        predicted = profile.predict(fa, fb, cx)
        true = user.choose(a, b, task_type=task_type, complexity=cx, step=step)
        flags.append(predicted == true)
        profile.observe(fa, fb, true, cx, answer_a=a, answer_b=b)
    return {"flags": flags, "profile": profile, "accuracy": sum(flags) / len(flags) if flags else 0.0}
