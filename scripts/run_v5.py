"""Run V5 (cross-family teacher-driven continual learning) — full curve.

Gemini student + GPT teacher. Learn on the 40 disjoint dev items, measure on the
same 100 as V0-V3, checkpointing held-out accuracy across the stream. Saves
policy snapshots, the learning curve, the teacher's critiques, and the example
bank; reports the three-way comparison + dual-model cost.

Run: python scripts/run_v5.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from judy.config import CONFIG
from judy.eval.benchmark import load_benchmark_items
from judy.judge.skill import load_skill, snapshot_skill
from judy.llm.gemini import GeminiClient
from judy.llm.openai_client import OpenAIClient
from judy.loop.teacher_loop import run_teacher_continual

DEV = CONFIG.runs_dir.parent / "judy/data/datasets/llmbar_adversarial_dev40.jsonl"
TEST = CONFIG.runs_dir.parent / "judy/data/datasets/llmbar_adversarial_100.jsonl"
TEACHER_SKILL = CONFIG.runs_dir.parent / "skills/teacher/SKILL.md"

# Prior results on the same 100, for the comparison.
PRIORS = {"V0 vanilla": 0.81, "V1 structured-rubric": 0.855, "V2 continual": 0.86}


async def main() -> None:
    student, teacher = GeminiClient(), OpenAIClient()
    dev, held = load_benchmark_items(DEV), load_benchmark_items(TEST)
    base_policy = load_skill(CONFIG.skill_path)        # robust structured judge policy
    teacher_policy = load_skill(TEACHER_SKILL)

    print(f"V5: learn on {len(dev)} dev, test on {len(held)}, teacher={CONFIG.teacher_model}")
    out = await run_teacher_continual(
        student, teacher, dev, held,
        base_policy=base_policy, teacher_policy=teacher_policy,
        batch_size=CONFIG.continual_batch_size, checkpoint_every=10, progress=print,
    )

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = CONFIG.runs_dir / f"v5-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    for t, s in enumerate(out["snapshots"]):
        snapshot_skill(s, run_dir, t)
    (run_dir / "curve.json").write_text(json.dumps(out["curve"], indent=2))
    (run_dir / "example_bank.json").write_text(json.dumps(out["example_bank"], indent=2))
    with (run_dir / "critiques.jsonl").open("w") as fh:
        for c in out["critiques"]:
            fh.write(json.dumps(c) + "\n")

    final = out["held_final"]["agreement"]
    g, tch = student.usage, teacher.usage
    summary = {
        "run_id": run_id, "dev_n": len(dev), "heldout_n": len(held),
        "curve": out["curve"], "held_final": out["held_final"],
        "n_critiques": len(out["critiques"]), "example_bank_size": len(out["example_bank"]),
        "cost": {"gemini": g.as_dict(), "openai_teacher": tch.as_dict(),
                 "total_usd": round(g.cost_usd() + tch.cost_usd(), 4)},
    }
    (run_dir / "metrics.json").write_text(json.dumps(summary, indent=2))

    # Emit UI-consumable curve data so the dashboard can chart this run.
    ui_dir = CONFIG.runs_dir.parent / "ui/public/curves"
    ui_dir.mkdir(parents=True, exist_ok=True)
    ui_refs = {"V0 vanilla": 0.81, "V1 rubric": 0.855, "V2 self-critique": 0.86}
    ui_data = {
        "run_id": run_id, "variant": "V5 — teacher-driven continual learning",
        "description": "Gemini judge learns from a GPT (gpt-5.4-nano) teacher: every 3 examples it "
                       "appends the teacher's lessons + the corrected case as a few-shot example.",
        "benchmark": "LLMBar-Adversarial (100-item test, 40-item dev)",
        "judge_model": CONFIG.model, "teacher_model": CONFIG.teacher_model,
        "curve": out["curve"], "references": ui_refs,
        "peak": max(p["agreement"] for p in out["curve"]), "final": final,
        "cost_usd": round(g.cost_usd() + tch.cost_usd(), 4),
    }
    (ui_dir / f"{run_id}.json").write_text(json.dumps(ui_data, indent=2))
    idx_path = ui_dir / "index.json"
    idx = json.loads(idx_path.read_text()) if idx_path.exists() else []
    idx = [r for r in idx if r["run_id"] != run_id]
    idx.insert(0, {"run_id": run_id, "variant": ui_data["variant"], "final": final, "peak": ui_data["peak"]})
    idx_path.write_text(json.dumps(idx, indent=2))

    print("\n=== V5 learning curve (held-out agreement) ===")
    for p in out["curve"]:
        print(f"  after {p['after']:>2} examples: {p['agreement']:.1%}")
    print("\n=== Three-way (same 100 adversarial items) ===")
    for k, v in PRIORS.items():
        print(f"  {k:24s} {v:.1%}")
    print(f"  {'V5 teacher-driven':24s} {final:.1%}")
    print(f"\n  critiques: {len(out['critiques'])} · example bank: {len(out['example_bank'])}")
    print(f"  cost: Gemini {g.summary()}")
    print(f"        Teacher {tch.summary()}")
    print(f"        TOTAL ~${g.cost_usd() + tch.cost_usd():.4f}")
    print(f"  artifacts in {run_dir}")


if __name__ == "__main__":
    asyncio.run(main())
