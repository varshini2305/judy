# Judy — Original Vision & Idea Backlog

> The user's original brainstorm for a self-learning LLM-as-a-judge, captured
> verbatim-in-spirit, with for each idea: **how it maps to what we've built**,
> the **known technique** it relates to, and an honest **promise/feasibility
> verdict**. This is the strategic "where could this go" doc; `ROADMAP.md` is the
> ordered backlog; `PROJECT_CONTEXT.md` is current state.

_Last updated: 2026-06-27_

## North star

> **Judy should not just give better scores. She should learn from evaluation
> failures, user corrections, other judges, and her own diagnostics, then update
> how she evaluates future responses.**

Four learning signals in that sentence — current coverage:

| Signal | Status |
|---|---|
| Evaluation **failures** (vs ground truth) | ✅ Built — anchored loop |
| Her own **diagnostics** (self-critique) | 🟡 Partial — unanchored loop |
| **Other judges** (jury / shared experience) | ⬜ Frontier — idea 1 |
| **User corrections** (preferences) | ⬜ Frontier — ideas 3, 5, 6 |

## The 8 ideas

### 1. Jury of personalized judges (deliberation + experience sharing)
Several judges, each a different preference/perspective; judge independently,
then inspect each other's evaluations and **learn** from shared experience —
better future judgments, not forced consensus.
- **Maps to:** ROADMAP "Jury / panel" (Later). Our two providers (Gemini +
  GPT 5.5 nano) make a *genuinely diverse* jury natural.
- **Known technique:** Panel-of-LLM-evaluators (PoLL), LLM-as-jury, multi-agent
  debate. The "learn from peers" twist is the novel, on-thesis part.
- **Verdict:** 🔥 High-value, novel, but scope-heavy. Strong **stretch/v2**;
  the experience-sharing angle is a real research contribution.

### 2. Self-critique of the judge's reasoning
Judge inspects its own rationale, finds weak assumptions/mistakes, improves
later evaluations.
- **Maps to:** Our **unanchored** loop already reflects on self-inconsistency.
  Self-critique is a richer unanchored signal.
- **Known technique:** Reflexion, Self-Refine, Meta-Rewarding (judge judges its
  own judgments).
- **Verdict:** ✅ Partly built. Honest caveat: pure self-critique *without* an
  external anchor tends to **plateau/drift** — which is exactly what our
  anchored-vs-unanchored ablation is designed to *demonstrate*. Most valuable as
  the **contrast arm**, not the hero.

### 3. Learning & representing user preferences
Gradually learn how a *specific user* evaluates (detail, tone, concision, style,
completeness); preferences are contextual and may not generalize.
- **Maps to:** ROADMAP "persona personalization" (OUT for iter 1).
- **Known technique:** Preference modeling / personalization; reward modeling
  per user.
- **Verdict:** 🧭 Big, promising **product** direction — but a shift from
  *objective* spec-compliance (our free tier-based ground truth) to *subjective*
  taste (no free ground truth; needs real user feedback → ties to ideas 5/6).
  Hard to demo credibly in 14h. **Later**, likely a v2 theme of its own.

### 4. Automatic correction of evaluator biases
A process to detect/correct position, confirmation, verbosity, self-preference /
model-family bias.
- **Maps to:** ✅ Partly built — we measure **position-consistency** (order-swap)
  and SKILL.md already guards fluency≠correctness, length≠quality. Self-preference
  is testable once we have a diverse jury (Gemini judging GPT vs itself).
- **Known technique:** Documented LLM-judge biases + mitigations (swap-and-average
  for position, length-controlled scoring for verbosity).
- **Verdict:** ⭐ Most grounded & measurable extension. A **bias-audit pass**
  (quantify each bias before/after self-improvement) is a strong, demoable
  **Next**.

### 5. Better feedback collection with fewer human labels
Capture explicit + implicit signal (ratings, pairwise, edits, regenerations,
which response the user continues from); **actively select** the most useful
cases to label rather than random.
- **Maps to:** ROADMAP "active-learning selection for cheap human labels."
- **Known technique:** Active learning (uncertainty sampling — pick items where
  the judge is least confident or where jurors disagree); implicit-feedback
  mining.
- **Verdict:** 🔥 Active-learning selection is **frontier, feasible, and
  demoable** (show that labeling the 10 highest-uncertainty items beats 10
  random). Implicit-feedback capture is product tooling → Later.

### 6. Synthetic preference expansion
When user feedback is scarce, generate/extrapolate more preference examples —
without inventing preferences the user never demonstrated.
- **Maps to:** We already do **synthetic data generation**; this extends it to
  *preference-conditioned* expansion (ties to 3 & 5).
- **Known technique:** Synthetic data augmentation / self-instruct, constrained
  to demonstrated preferences.
- **Verdict:** 🧭 Useful data-efficiency play, but **risk: hallucinating
  preferences**. Promising only alongside idea 3. **Later**.

### 7. Harness improvements vs. actual model learning (the method spectrum)
Where should improvement come from? Instructions · rubrics · few-shot · context/
evidence · multi-agent · fine-tuning · RLHF/preference-opt · recursive self-improvement.
- **Maps to:** This is the project's **organizing axis**, not one feature. Iter 1
  deliberately sits at the *context-engineering* end (instructions + rubric
  rewriting). Fine-tuning/RLHF are ROADMAP Later.
- **Verdict:** 📐 Framing, not a task. Worth a slide: "we explore the cheapest,
  most legible point on this spectrum first; here's what each step up would add."

### 8. Benchmarking baseline LLM-judge vs. Judy
Clear comparison on agreement, preference-capture, bias-resistance, consistency,
calibration, performance on unseen QA.
- **Maps to:** ✅ Core of what we're building — baseline vs improved on held-out
  *unseen* types. Have: agreement, position-consistency, score-spread.
- **Known technique:** Judge benchmarks (RewardBench, LLMBar, JudgeBench);
  calibration metrics (ECE).
- **Verdict:** ⭐ Essential and in progress. Extend metrics with **calibration**
  and a **bias-resistance score**; add an external benchmark (LLMBar/RewardBench)
  as the credible yardstick.

## Where this leaves us — the promising shortlist

Ranked by (promise × feasibility-in-sprint × fit-with-thesis):

1. **#8 Benchmark baseline-vs-Judy** — core, in progress; add calibration + external benchmark.
2. **#4 Bias-audit pass** — measurable, grounded, demoable; quantify bias reduction.
3. **#5 Active-learning selection** — frontier + data-efficient + demoable.
4. **#1 Jury with experience-sharing** — highest-ceiling, novel; v2 stretch (uses Gemini + GPT diversity).
5. **#2 Self-critique** — keep as the unanchored *contrast* (expected to plateau).
6. **#3/#6 Preference learning + synthetic expansion** — biggest vision, but a subjective-eval pivot; a v2 theme, not a 14h add.
7. **#7** — the framing axis for the narrative, not a build item.

**Through-line:** iteration 1 already proves the *failures → policy rewrite*
loop. The most natural, in-budget expansions are **measurement depth (#8)** and
**bias resistance (#4)**; the most exciting v2 bets are **jury experience-sharing
(#1)** and **preference learning (#3)**.
