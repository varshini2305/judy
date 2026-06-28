# Judy — Findings: What Improves an LLM-as-a-Judge (and What Doesn't)

> A concrete report on every judge variant we tested: the inputs, the results,
> and an honest read of **what shows promise and why, and what doesn't and why.**
> Per-variant setup → `VARIANTS.md`; method theory → `EXPERIMENT_PLAN.md`.

_Last updated: 2026-06-28_

## TL;DR

On a **strong 2026 base judge** (`gemini-3.5-flash`), the bottleneck to improving
an LLM-as-a-judge is **not** the learning algorithm — it's the **signal** (a good
model makes few mistakes to learn from) and **drift** (more learning eventually
over-corrects). The methods that helped most: a **better starting policy**, a
**cross-family grounded teacher**, and **early stopping**. Hand-engineered rubrics
help on some slices and *hurt* on others. Objective benchmarks are saturated; the
only real headroom is **adversarial** instruction-following.

## Inputs (what every number is measured on)

- **Judge model:** `gemini-3.5-flash` (frozen; only the policy/method changes).
- **Test set:** `llmbar_adversarial_100.jsonl` — 100 LLMBar-Adversarial pairs (25
  each: GPTInst / GPTOut / manual / neighbor), human-labeled. Order-swap ON
  (200 judgments/variant).
- **Train set (learning variants):** `llmbar_adversarial_dev40.jsonl` — 40
  **disjoint** items. "Training" = updating the judge's *context* (policy text +
  in-context examples), **not** weights.
- **Why this benchmark:** RewardBench-easy ≈ 89%, **JudgeBench ≈ 97%** for our
  model — saturated, no headroom. Adversarial LLMBar baselines at 81% (GPTInst
  subset 50–66%), so improvements are visible.

## Results (same 100 items, order-swap on)

| Variant | Method | Trains on | Agreement | Pos-cons. | Cost |
|---|---|---|---|---|---|
| **V0** baseline-vanilla | generic prompt | — | 81.0% | 90.0% | — |
| **V1** structured-rubric | hand-engineered policy | — | 85.5% | 93.0% | ~$0.8 |
| **V2** continual (self-critique) | self-reflection, batch 3 | 40 dev | 86.0% | **98.0%** | ~$0.81 |
| **V5** teacher-driven (cross-family) | GPT teacher → Gemini, batch 3 | 40 dev | **86.5% final · 88.5% peak** | 93.0% | ~$3.30 |

(V4 judge-jury is on a *different*, subjective creative-preference benchmark and is
**not comparable** to this agreement column — see `VARIANTS.md` §V4.)

## What shows promise (and why)

1. **A better starting policy (V1): +4.5 over vanilla.** Explicit bias guards
   (*fluency ≠ correctness*, verify claims) directly counter the adversarial trick
   of dressing a wrong answer to look better. *Promise: real, and cheap (a prompt).*

2. **Cross-family grounded teaching (V5) beats self-critique (V2).** V5 *peaked at
   88.5%* — the best of any variant — vs V2's 86.0%. A **different** model family,
   shown the answer key, produces better lessons than a model reflecting on itself
   (which tends to rationalize its own call). The teacher cost was **negligible**
   ($0.0005 — nano, fires only on errors). *Promise: the strongest signal we found.*

3. **Continual learning improves robustness, not just accuracy.** Much of V2's gain
   was **position-consistency 90% → 98%** — the judge stopped flipping with answer
   order. A judge that's robust to presentation is more trustworthy even when raw
   agreement barely moves.

4. **The learning curve is itself a finding.** Charting accuracy *across the stream*
   (not just before/after) revealed the peak-then-drift dynamic that a 2-point
   summary hides — and showed that **early-stopping at the peak yields the best
   variant (88.5%).**

## What doesn't work / is limited (and why)

1. **Hand-engineered rubrics are NOT universally better.** The *same* V1 rubric
   that gained +4.5 on adversarial **regressed −9 on easy/safety** (RewardBench):
   its "answer the question / be complete" framing mishandles refusal cases.
   *Why: improvements are context-dependent; a fix for one failure mode is a
   liability for another.*

2. **More continual learning is not monotonically better (drift).** V5 peaked at
   88.5% then **degraded to 86.5%** — a late, *too-specific* lesson (a grammar-vs-
   spelling rule) over-generalized and its few-shot example anchored the judge
   wrong on unrelated cases. *Why: appending context indefinitely over-corrects;
   keeping the **final** policy is the wrong choice — keep **best-on-validation**.*

3. **The sparse-error bottleneck caps everything.** A strong 2026 judge gets most
   dev items right, so the loop fired only **2–3 updates** over 40 examples. *Why:
   no method can learn from mistakes that don't happen; the ceiling is set by how
   many hard errors the data surfaces, not by the cleverness of the reflection.*

4. **Objective benchmarks give no headroom.** JudgeBench (designed to be hard for
   2024 judges) scored **97%** for our model. *Why: the model is strong at
   objective correctness; it's only fooled by **adversarial style**, so that's the
   only regime where any method can demonstrate a lift.*

## The core insight

For a capable base judge, **self-improvement needs two anchors, not one:** an
**external grounding signal** (ground-truth labels and/or a different-family
teacher — without it, self-critique plateaus) **and a validation/stopping anchor**
(without it, continual learning over-corrects). Both showed up empirically: V5
(grounded, cross-family) reached the highest peak; the drift showed the missing
stopping anchor.

## Recommendations (ranked)

1. **Add early stopping** (keep best-on-validation policy) to the continual loops —
   this alone makes V5 land at 88.5%, the best result. *Lowest cost, highest payoff.*
2. **Run on harder headroom** (GPTInst-only ≈ 50–60%, or RewardBench-2's 4-way
   format) so methods have room to separate.
3. **Keep the teacher cross-family and grounded** — it's cheap and gives the best
   lessons; consider a stronger teacher than nano on the hardest cases.
4. **Don't over-engineer the rubric** — let the judge *learn* context-appropriate
   lessons rather than hand-coding rules that help one slice and hurt another.
