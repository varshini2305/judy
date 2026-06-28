# Judy — Preference-Learning Demo & Baseline Plan

> The end-to-end demo: a user picks among answers, and Judy (the judge) learns
> and generalizes their preference in the background — shown live, with a clear
> improvement over a baseline judge. See `EXPERIMENT_PLAN.md` for method theory.

_Last updated: 2026-06-27_

## What we must SHOW (the demo, per user's spec)
1. Pick a QA case from a dataset; show the user **multiple responses** to a question.
2. The user **picks** the one they prefer (optionally says why).
3. In the background, **Judy infers the user's preference** and updates a profile.
4. Repeat a few rounds → Judy **generalizes** the preference.
5. Show Judy **predict the user's choice on new (held-out) pairs**, beating a
   no-learning baseline.
6. **Simulate different users** (concise / detailed / conditional / drifting) to
   show per-user adaptation — fast, repeatable, falsifiable.

## Baseline RESULTS (vanilla judge vs RewardBench human labels, 2026-06-27)

35-item sample, gemini-3.5-flash, order-swap on:
- **Overall agreement 88.6%** — but **saturated** on easy subsets, so misleading.
- Position-consistency 94.3%; position-consistent agreement 85.7%.
- **Per subset is the real story:**
  - alpacaeval-easy / hep-cpp / hep-java / math-prm: **100%** (no headroom)
  - refusals-offensive 90%, donotanswer (safety) 80%
  - **llmbar-adver-neighbor: 50% (chance!)** — adversarial fluent-but-wrong cases
- **Implication:** improvement must be measured on the HARD subsets (adversarial,
  safety) where the baseline isn't saturated. Sample the eval set toward
  llmbar-adversarial so baseline lands ~60-75% (per brief), leaving headroom.
- **Validates the thesis:** a vanilla judge is fooled exactly where fluency/style
  masks wrongness — which is what self-improvement should fix.

## Baselines (must establish to claim improvement)
- **Preference baseline = vanilla judge with no user info.** On style-tie cases
  (both answers correct), it has no way to know the user's taste → expected
  ~**50%** match with the user's actual choice. Judy-with-preference should rise
  well above this as feedback accumulates (target ~85–90% on learnable policies).
- **Objective baseline (already have)** = vanilla single judge agreement on the
  tiered set / external benchmark. Judy's self-improvement loop must beat it.
- Report both as explicit before/after numbers; the preference one is the
  headline for this demo.

## Two engines (cost-aware)
- **Model-free learner** (built, $0): hypothesis-weighted profile. Proves the
  mechanism and powers fast/cheap iteration + the live UI predictions.
- **Preference-conditioned LLM judge** (to build): the real Gemini judge consumes
  `profile.render_context()` (preference block + ICL examples = "examples as a
  function of the user"). Used for the headline real-credit result.

## Build order (drives to the demo)
1. **Baseline harness** — vanilla judge vs preference-conditioned, scored on
   simulated users' choices. *This is the improvement metric.* (small credits)
2. **Preference dataset** — a handful of QA questions, each with style-varied but
   correctness-equal responses (concise / detailed / repetitive). Generate once
   with Gemini, or a hand fixture for $0 demo.
3. **Preference-conditioned LLM judge** — wire `render_context()` into the judge call.
4. **Preference Lab UI** — interactive pick → live preference belief + confidence
   → learning curve → predict-on-held-out vs baseline → user-simulator toggle.
   Build on the model-free learner first (mock/$0), then wire live.
5. **Critique agent** — read `skills/critique/SKILL.md`; on disagreements, grow
   the hypothesis space beyond the fixed templates (the recursive bridge).

## What I implement FIRST (highest signal, lowest cost)
- The **baseline-vs-Judy preference comparison** (so "improves over baseline" is a
  number, not a claim) — runnable on the model-free learner for $0, then on the
  LLM judge for a small real result.
- The **Preference Lab UI screen** on the learner, so the end-to-end demo exists
  and is clickable before we spend credits.

## Metrics for the demo
- Preference-prediction accuracy vs #feedback examples (the learning curve).
- Accuracy vs the no-learning baseline (the lift).
- Labels-to-target-accuracy; recovery after drift; objective-correctness preserved.
