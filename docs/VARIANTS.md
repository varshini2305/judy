# Judge Improvement Strategies (Variants) — vs Baseline

> **Central registry** of every LLM-as-judge variant we try: what it does, how
> it's set up, and how it scores vs the baseline — so parallel agents can add
> variants with shared context. Method *theory* → `EXPERIMENT_PLAN.md`;
> preference demo → `DEMO_PLAN.md`.

_Last updated: 2026-06-28_

## Shared experimental setup (identical across variants)

- **Judge model:** `gemini-3.5-flash`, held **constant** — only the policy/method
  changes between variants, so deltas are attributable to the method, not the model.
- **Benchmark:** **LLMBar-Adversarial** (via RewardBench) — adversarial question-answering judging
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

## Models & what "training" means (read this first)

- **Judge/evaluator model (all variants):** `gemini-3.5-flash`.
- **Teacher model (V5 only):** `gpt-5.4-nano` (OpenAI) — a *different* family, used as a critic.
- **"Training"/"learning" here = updating the judge's CONTEXT** (its policy text and/or
  in-context examples), **not** updating model weights. The model is frozen; what changes
  is what we put in front of it. (The *weight-update* path — SFT/preference tuning — is a
  **separate** track in `judy/tuning/` owned by another session, not these variants.)
- **Data:** all variants are **tested** on the same `llmbar_adversarial_100.jsonl` (100
  items). Learning variants are **trained** on a *disjoint* `llmbar_adversarial_dev40.jsonl`
  (40 items) — never on the test 100.

## Results so far

| ID | Label | Judge | Teacher | Trains on | Tests on | Agreement | Pos-cons. | Cost |
|----|-------|-------|---------|-----------|----------|-----------|-----------|------|
| **V0** | baseline-vanilla | gemini-3.5-flash | — | nothing (static) | 100 | **81.0%** | 90.0% | — |
| **V1** | structured-rubric | gemini-3.5-flash | — | nothing (static) | 100 | **85.5%** | 93.0% | ~$0.8 |
| **V2** | continual-learning | gemini-3.5-flash | — (self) | 40 dev | 100 | **86.0%** | 98.0% | ~$0.81 |
| **V5** | teacher-driven | gemini-3.5-flash | gpt-5.4-nano | 40 dev | 100 | **86.5%** (peak 88.5%) | 93.0% | ~$3.30 |
| **V4** | judge-jury (per-user) | gemini-3.5-flash | gpt-5.4-nano (label oracle) | 18 (creative) | 12 (creative) | see **§V4** | 83.3% | ~$0.60–0.71 |

V0/V1/V2/V5 are all measured on the **same** 100 adversarial items, order-swap on.
**V4 is deliberately on a different benchmark** and answers a different question —
subjective preference *variance*, which LLMBar cannot measure (it carries one
human label per item). V4 therefore has its own in-track baseline (B0) and its
numbers are **not** comparable to the LLMBar agreement column above. See §V4.

### V0 — baseline-vanilla
- **What it is:** the standard LLM-as-judge — a single call with a generic *"which answer
  is better?"* prompt, no rubric or bias guards. The control we measure everything against.
- **Models:** judge = `gemini-3.5-flash`. No teacher.
- **Training:** none (static prompt — nothing is learned).
- **Test data:** the 100 adversarial items.
- **Run:** `python -m judy.eval.benchmark` (uses `VANILLA_POLICY`).
- **Result:** **81.0%** agreement, 90.0% position-consistency.

### V1 — structured-rubric  *(static, hand-engineered)*
- **What it is:** a hand-written, smarter judging *policy* — derive the spec's criteria,
  judge correctness *independently of fluency*, with explicit bias guards (fluency≠correctness,
  length≠quality, position-invariance). Still one call; still no learning — just a better prompt.
- **Models:** judge = `gemini-3.5-flash`. No teacher.
- **Training:** none (the policy is authored by us, in `skills/judge/SKILL.md`).
- **Test data:** the 100 adversarial items.
- **Run:** `python -m judy.eval.compare_variants`.
- **Result:** **85.5%** (+4.5), gains on hard subsets (neighbor +10, manual +6).
  **Caveat:** the *same* rubric *regressed* on easy/safety (RewardBench, −9) — improvements
  are **context-dependent**.

### V2 — continual-learning  *(self-improvement, streaming, batch=3)*
- **What it is:** the judge improves *itself* from experience. It starts from vanilla and
  streams through training examples; **every 3**, it reflects on the cases where its verdict
  disagreed with the ground-truth label, writes **task-general lessons** about why the labeled
  answer was better, and **appends them to its own policy**. No teacher — it critiques itself.
- **Models:** judge = `gemini-3.5-flash` (also does its own reflection). No teacher.
- **Training:** learns on **40 disjoint dev items** (`llmbar_adversarial_dev40.jsonl`) by
  *updating its policy text* (context), not weights. `JUDY_CONTINUAL_BATCH=3`.
- **Test data:** the 100 adversarial items.
- **Run:** `python -m judy.loop.continual`.
- **Result:** 81.0% → **86.0%** (+5.0), pos-consistency → **98.0%**. Only **2** policy
  updates fired (the strong base judge got most dev items right → sparse error signal), yet
  drove the gain. **Reached/beat hand-tuned V1 — but learned it.** Net distinct-item gain +2;
  the rest is robustness (order-consistency 90→98%).
- **Audit:** `runs/continual-<id>/skill_*.md` (the self-written lessons) + `metrics.json`.

### V5 — teacher-driven continual learning  *(cross-family, streaming, batch=3)*
- **What it is:** like V2, but the feedback comes from a **different model family acting as a
  teacher** instead of self-critique. A **Gemini** judge evaluates; when it gets a case wrong,
  a **GPT (`gpt-5.4-nano`)** teacher — which is shown the **answer key** — diagnoses *why* and
  writes a task-general lesson (a *principle* + a *procedure*). The judge's context then grows
  on **two channels** every 3 examples: (1) lessons appended to its policy, (2) the corrected
  case kept as a **few-shot example**. Rationale: a *different* model catches blind spots a
  model can't see in itself (self-critique plateaus); grounding the teacher in the label keeps
  its feedback reliable even though it's a small model.
- **Models:** judge/student = `gemini-3.5-flash`; teacher/critic = `gpt-5.4-nano` (OpenAI).
- **Training:** learns on **40 disjoint dev items**, updating *context* (policy lessons +
  example bank), not weights. Teacher only fires on the judge's errors.
- **Test data:** the 100 adversarial items.
- **Run:** `python scripts/run_v5.py` (full curve, checkpoints held-out accuracy across the stream).
- **Result (started from the V1 structured policy, 85.5%):** learning curve
  **85.5% → 88.5% (after 10) → 88.5% (20) → 88.5% (30) → 86.5% (final, 40)**.
  Only **3** teacher critiques fired (sparse errors). **Key finding: it PEAKED at
  88.5% — the best of any variant — then DRIFTED DOWN to 86.5%.** More continual
  learning was *not* monotonically better; the last batch over-corrected. **With
  early stopping at the peak, V5 = 88.5% (beats V0–V3).** The learning curve is what
  surfaced this — a lean before/after run (85.5%→86.5%) would have hidden it.
  Teacher cost was negligible ($0.0005); the $3.30 was the curve's held-out checkpoints.
- **Audit:** `runs/v5-<id>/skill_*.md` (lessons), `example_bank.json`, `critiques.jsonl`
  (the teacher's diagnoses), `curve.json` (learning curve).

### V4 — judge-jury, per-user preference modelling  *(subjective track; mixed result)*

> V4 tests a **different thesis** from V0–V5. Those improve agreement with a
> *single* human label on an objective-ish benchmark. V4 asks: when the task is
> **subjective** (creative writing) and users genuinely disagree, can a **jury of
> per-user jurors** model each user's individual taste better than one judge can?
> LLMBar can't grade this (one label/item), so V4 ships its own benchmark.

- **The claim it tests:** the judge owns a shared evaluation structure and guides
  the jurors; each juror is assigned **one user** and models that user's taste, so
  the jury covers the *spread* of preferences a single judge must average over.
- **Benchmark (new):** `judy/data/datasets/creative_pref_benchmark.jsonl` — **30**
  creative pairwise items (sonnet/haiku/free-verse/flash-fiction), each piece pair
  built to split opposing aesthetic readers. **5 user personas with hidden
  preference policies** (`judy/data/personas.py`: Imagist / Formalist / Minimalist
  / Romantic / Modernist) each label **all 30** items via `gpt-5.4-nano`
  role-playing the hidden policy (the **label oracle**, never shown to jurors).
  Split **18 train / 12 test** per user; **25/30 items have persona disagreement**.
- **Setup:** judge model `gemini-3.5-flash` (constant). **B0** = one generic judge,
  scored against every user (the in-track baseline). **V4** = one juror/user,
  modelling that user from its **train** labels, scored on its **test** labels.
  Order-swap ON. Two juror modes: `reflect` (distil lessons from disagreements,
  reusing the V2 reflect→apply loop) and `fewshot` (condition directly on the
  user's train choices). Run: `python -m judy.eval.jury [--mode fewshot]`.
- **Metrics:** mean per-user test agreement (V4 vs B0) + a **personalization
  matrix** `agree(juror_i, user_j)` — the diagonal should dominate if jurors truly
  capture *their own* user.

  | Variant | Mean agreement | vs B0 | Personalization (diag wins) | Pos-cons. | Cost |
  |---------|----------------|-------|------------------------------|-----------|------|
  | **B0** single judge | 63.3% | — | — | 83.3% | — |
  | **V4 reflect** | 62.5% | **−0.8** | **1/5** | 85.0% | ~$0.71 |
  | **V4 few-shot** | 65.0% | **+1.7** | **2/5** | 83.3% | ~$0.60 |

- **Honest verdict — mixed/negative, and informative:**
  1. A same-model jury **barely edges** a single judge (+1.7 at best, well inside
     noise on a 12-item test). Prompt-only personas on one frozen model make
     **correlated** decisions — the failure mode flagged before the build.
  2. **Few-shot conditioning > reflection** for this. Reflection produced *muddy,
     self-contradictory* per-user lessons (the Modernist juror learned both
     "anti-sentimental restraint" *and* "earnest emotional resonance") because it
     over-generalised from a tiny, noisy error set — so jurors converged.
  3. **Personalization is real but partial.** Few-shot makes the **Formalist
     (0.71) and Modernist (0.79)** jurors top-match their own user — the two most
     *lexically distinctive* tastes (meter/archaic vs plain/contemporary). The
     subtler tastes (Imagist/Minimalist/Romantic) collapse toward the model's
     default aesthetic and don't separate.
- **Caveats:** small test set (12 items × 2 orders → percentages swing per item);
  the `gpt-5.4-nano` oracle is itself imperfect (it carries an A-/"richer-piece"
  bias we partly corrected with position-randomised labelling), which caps the
  achievable ceiling (B0 only 63%). The result is a **finding, not a failure**:
  per-user modelling needs either genuine **model-family diversity** in the jury
  or a **cleaner, less correlated oracle**, not just persona prompts.
- **Audit:** `runs/jury-<id>/` — `metrics.json` (per-user + full matrix), one
  `juror_<persona>.md` per juror (its learned/conditioned policy).

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
- **Few-shot error-memory:** retrieve similar past mistakes as in-context examples (vector retrieval → the MongoDB use case). *(Partly realized in **V4 few-shot**, which conditions per-user jurors on their own past choices.)*
- **Reliability-weighted role jury:** diverse judges (Gemini + GPT-nano), weighted by per-task historical reliability. *(The jury machinery now exists in `judy/eval/jury.py` (**V4**). V4 found same-model jurors correlate → the clear next step is **GPT-nano as a second juror family** for genuine diversity, then reliability-weight the vote.)*
- **Weight-update track (Codex, `judy/tuning/`):** SFT / preference tuning on Gemini — a *separate*, model-level path (not context-only).
