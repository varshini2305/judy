# Judge Improvement Strategies (Variants) — vs Baseline

> **Central registry** of every LLM-as-judge variant we try: what it does, how
> it's set up, and how it scores vs the baseline — so parallel agents can add
> variants with shared context. Method *theory* → `EXPERIMENT_PLAN.md`;
> preference demo → `DEMO_PLAN.md`.

_Last updated: 2026-06-28_

## Shared experimental setup (identical across variants)

- **Judge model:** `gemini-3.5-flash`, held **constant** — only the policy/method
  changes between variants, so deltas are attributable to the method, not the model.
- **Benchmark:** **LLMBar-Adversarial** (via RewardBench) — adversarial QA judging
  where a fluent-but-wrong answer is crafted to look better. **100-item test set**
  (`judy/data/datasets/llmbar_adversarial_100.jsonl`, 25 each from GPTInst / GPTOut
  / manual / neighbor). Labels are human-preferred answers.
- **Why this benchmark:** easy/objective benchmarks are saturated for our 2026
  model — RewardBench-easy ≈ 89%, **JudgeBench ≈ 97%** (incl. coding). Adversarial
  LLMBar has real headroom (baseline 81%; GPTInst subset 50–66%).
- **Metrics:** agreement with human labels (headline) · position-consistency ·
  pos-consistent agreement. **Order-swap ON** (each item judged in both A/B orders).
- **Fair-learning rule:** any variant that *learns* must learn on a **disjoint dev
  set**, never on the test 100 (no training-on-test).
- **Audit:** `scripts/build_comparison_report.py` → `runs/comparison_report.html`
  (per-item, both judges' rationales). Learning variants also snapshot the evolving
  policy to `runs/.../skill_*.md`.

## Results so far

| ID | Label | What it does | Agreement | Pos-consistency | Cost |
|----|-------|--------------|-----------|-----------------|------|
| **V0** | baseline-vanilla | minimal generic prompt, no rubric | **81.0%** | 90.0% | — |
| **V1** | structured-rubric | engineered policy + bias guards (static) | **85.5%** | 93.0% | ~$0.8 |
| **V2** | continual-learning | stream; reflect+update policy every 3 examples | **86.0%** | 98.0% | ~$0.81 |

All measured on the same 100 adversarial items, order-swap on.

### V0 — baseline-vanilla
- **What:** standard LLM-as-judge — one call, generic *"which answer is better?"* prompt, no rubric/guards.
- **Run:** `python -m judy.eval.benchmark` (uses `VANILLA_POLICY`).
- **Result:** 81.0%. The bar to beat.

### V1 — structured-rubric  *(static improvement, hand-engineered)*
- **What:** engineered policy — derive the spec's criteria, judge correctness *independently of fluency*, explicit bias guards (fluency≠correctness, length≠quality, position-invariance).
- **Set up:** policy lives in `skills/judge/SKILL.md`; run via `python -m judy.eval.compare_variants`.
- **Result:** 85.5% (+4.5), gains on hard subsets (neighbor +10, manual +6). **Caveat:** the *same* rubric *regressed* on easy/safety (RewardBench, −9) — improvements are **context-dependent**.

### V2 — continual-learning  *(streaming, batch=3)*
- **What:** starts from vanilla; streams dev examples; **every 3**, reflects on the cases where its verdict disagreed with the label, writes **task-general lessons** about why the labeled answer was better, and updates its policy. Keeps compounding.
- **Set up:** `python -m judy.loop.continual` — learns on `llmbar_adversarial_dev40.jsonl` (40 disjoint), tested on the 100. `JUDY_CONTINUAL_BATCH=3`.
- **Result:** 81.0% → **86.0%** (+5.0), pos-consistency → **98.0%**. Only **2** policy updates fired (vanilla got most dev items right → sparse error signal), yet drove the gain. **Reached/beat the hand-tuned V1 — but learned it.**
- **Audit:** `runs/continual-<id>/skill_*.md` (the self-written lessons) + `metrics.json`.

## How to add a variant (for parallel sessions)

1. Implement the method: a new policy string, or a new loop under `judy/loop/` or `judy/eval/`.
2. Evaluate on the **same** `llmbar_adversarial_100.jsonl` with order-swap, via `eval_split` + `compute_metrics` (reuse `judy/eval/benchmark.py` helpers).
3. Log per-item records and (re)generate the comparison report for auditability.
4. If the method **learns**, learn on a **disjoint** dev set (e.g. `llmbar_adversarial_dev40.jsonl`).
5. **Add a row + a section here** with real numbers + cost. Keep the model constant.

## Planned / candidate variants

### V3 — MARS-style metacognitive reflection  *(candidate — analyzed, recommended)*
Paper: **"Learn Like Humans: Use Meta-cognitive Reflection for Efficient Self-Improvement"** (MARS), ACL 2026 (Hou et al.). Code: github.com/Paparare/MARS.
- **Core method:** convert failures into **two** reflection types — *principle-based*
  (abstract normative rules/constraints to avoid errors) and *procedural* (step-by-step
  strategies for success) — then a **Synthesizer** merges them into an enhanced prompt.
  Key claim: self-evolution in a **single recurrence cycle** (efficient vs. expensive
  multi-turn loops). Context/prompt-based, **no weights**. RSI lineage (Gödel machine).
- **Fit for our judge: HIGH.** Maps almost 1:1 onto `SKILL.md`: principles ≈
  "Known failure modes to avoid", procedures ≈ "Strategies / Procedure". Our
  `reflect.py` already emits `failure_modes` + `strategies` + `procedure_edits`, so
  we're ~70% there.
- **What V3 adds over V2:** (1) explicit *principle vs procedure* split in the
  reflection; (2) a **synthesis/consolidation** step (merge accumulated lessons into a
  coherent policy, not just append); (3) **efficiency** — a single synthesis pass over
  accumulated failures instead of per-batch reflection (fewer calls).
- **Is it RSI?** Efficient self-improvement in the RSI lineage, but not strongly
  "improver-improves" recursive — its headline is efficiency + principled structure.
- **Simple implementation:** reuse the continual loop; swap reflection for a MARS
  reflect producing `{principles[], procedures[]}` + a synthesis pass that rewrites
  both `SKILL.md` sections; single-pass variant = collect dev-stream failures → one
  synthesis call → enhanced policy → eval on the 100.
- **Verdict: worth trying as V3.** Low build cost (extends `reflect.py`), citeable
  SOTA, and it tests whether structured principle+procedure *synthesis* beats our
  current append-style reflection (V2).
- **Few-shot error-memory:** retrieve similar past mistakes as in-context examples (vector retrieval → the MongoDB use case).
- **Reliability-weighted role jury:** diverse judges (Gemini + GPT-nano), weighted by per-task historical reliability.
- **Weight-update track (Codex, `judy/tuning/`):** SFT / preference tuning on Gemini — a *separate*, model-level path (not context-only).
