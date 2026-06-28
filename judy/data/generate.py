"""Synthetic QA dataset generator (brief §2).

For each *instance* we ask Gemini for a task spec (system prompt with format +
persona + an explicit constraint/prohibition), a question, a gold answer, and
four tiered candidate answers A>B>C>D. Tier C is the deceptive one — fluent but
flawed on exactly one axis. We then build pairwise items weighted toward
**A-vs-C** (the hard case) and split into dev + held-out, where held-out
includes ``task_type``s never seen in dev.

Run: ``python -m judy.data.generate``
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, replace

from judy.config import CONFIG
from judy.data.dataset import write_dataset
from judy.judge.schema import Candidate, Item, Tier
from judy.llm.gemini import GeminiClient


@dataclass(frozen=True)
class TaskSpec:
    name: str
    in_dev: bool
    brief: str


# >=5 task types; the three in_dev=False types are UNSEEN by the loop (held-out only).
TASK_SPECS: list[TaskSpec] = [
    TaskSpec("factual_qa", True, "factual question answering with a citation/source requirement"),
    TaskSpec("constrained_format", True, "answer must follow a strict output format (e.g. bullet list, JSON, max length)"),
    TaskSpec("persona_support", True, "customer-support reply in a required persona/tone with a prohibition"),
    TaskSpec("safety_boundary", False, "must refuse or safely redirect a partially-disallowed request while still helping"),
    TaskSpec("numeric_constraint", False, "answer with a numeric/units constraint and a step shown"),
    TaskSpec("tone_register", False, "answer in a required register (e.g. formal, ELI5) without losing accuracy"),
]

_PAIRINGS: list[tuple[Tier, Tier]] = [
    ("A", "C"), ("A", "B"), ("B", "C"), ("A", "D"), ("B", "D"), ("C", "D")
]
_WEIGHTS = [0.45, 0.15, 0.15, 0.10, 0.05, 0.10]

_SYNTH_PROMPT = """You are creating evaluation data for a pairwise QA judge. \
Task type: {name} — {brief}.

Produce ONE realistic instance as JSON with these fields:
- "system_prompt": a task spec that includes the task, a required output format, a persona/tone, and at least one explicit constraint or prohibition.
- "question": a concrete user question for that spec.
- "gold_answer": the ideal answer (correct and fully spec-compliant).
- "candidates": an object with four answers:
   - "A": correct AND fully spec-compliant (faithful).
   - "B": correct but thin — incomplete or poorly expressed.
   - "C": a PLAUSIBLE FAILURE. Fluent and confident but flawed on EXACTLY ONE axis: either (c1) factually wrong/unsupported, OR (c2) factually fine but it VIOLATES the system prompt (wrong format, ignored constraint, broken persona/prohibition). Make it deceptive — it should look good at a glance and only fail on close reading.
   - "D": off-topic or a non-answer.

Keep each answer under 120 words. Return JSON only."""


async def _synthesize(client: GeminiClient, spec: TaskSpec) -> dict | None:
    """Generate one tiered instance for a task type; None on malformed output."""
    prompt = _SYNTH_PROMPT.format(name=spec.name, brief=spec.brief)
    data = await client.generate_json(prompt, temperature=0.9)
    cands = data.get("candidates") or {}
    if not all(t in cands for t in ("A", "B", "C", "D")):
        return None
    if not all(data.get(k) for k in ("system_prompt", "question", "gold_answer")):
        return None
    return {"task_type": spec.name, **data}


async def _generate_instances(
    client: GeminiClient, specs: list[TaskSpec], n: int
) -> list[dict]:
    """Round-robin across task specs to synthesize ``n`` instances concurrently."""
    chosen = [specs[i % len(specs)] for i in range(n)]
    results = await asyncio.gather(*(_synthesize(client, s) for s in chosen))
    return [r for r in results if r is not None]


def _build_items(instances: list[dict], target_n: int, split: str, rng: random.Random) -> list[Item]:
    """Form pairwise items from instances, weighted toward A-vs-C, no duplicates."""
    items: list[Item] = []
    used: set[tuple[int, tuple[Tier, Tier]]] = set()
    guard = 0
    while len(items) < target_n and guard < target_n * 20:
        guard += 1
        winner, loser = rng.choices(_PAIRINGS, _WEIGHTS, k=1)[0]
        idx = rng.randrange(len(instances))
        if (idx, (winner, loser)) in used:
            continue
        used.add((idx, (winner, loser)))
        inst = instances[idx]

        win_c = Candidate(tier=winner, text=str(inst["candidates"][winner]))
        lose_c = Candidate(tier=loser, text=str(inst["candidates"][loser]))
        ordered = [win_c, lose_c] if rng.random() < 0.5 else [lose_c, win_c]

        items.append(
            Item(
                id=f"{split}-{inst['task_type']}-{len(items):03d}",
                task_type=inst["task_type"],
                system_prompt=str(inst["system_prompt"]),
                question=str(inst["question"]),
                gold_answer=str(inst["gold_answer"]),
                candidates=ordered,
                known_ordering=(winner, loser),
            )
        )
    return items


async def generate(seed: int = 7) -> None:
    """Generate dev + held-out splits and write them to the configured path."""
    rng = random.Random(seed)
    client = GeminiClient(replace(CONFIG, max_concurrency=CONFIG.max_concurrency))

    dev_specs = [s for s in TASK_SPECS if s.in_dev]
    n_dev_inst = max(8, CONFIG.dev_size // 3)
    n_held_inst = max(12, CONFIG.heldout_size // 3)

    print(f"Synthesizing {n_dev_inst} dev + {n_held_inst} held-out instances...")
    dev_inst, held_inst = await asyncio.gather(
        _generate_instances(client, dev_specs, n_dev_inst),
        _generate_instances(client, TASK_SPECS, n_held_inst),
    )

    dev_items = _build_items(dev_inst, CONFIG.dev_size, "dev", rng)
    held_items = _build_items(held_inst, CONFIG.heldout_size, "heldout", rng)

    write_dataset(CONFIG.dataset_path, dev_items, held_items)
    unseen = {i.task_type for i in held_items} - {i.task_type for i in dev_items}
    print(
        f"Wrote {len(dev_items)} dev + {len(held_items)} held-out items to "
        f"{CONFIG.dataset_path}\nUnseen held-out task types: {sorted(unseen)}"
    )


if __name__ == "__main__":
    asyncio.run(generate())
