# Judy — Experiment Plan: Top 3 Methods to Beat a Vanilla Judge

> From the user's 10 implementation-oriented ideas, the three methods most worth
> testing — chosen for **provable improvement** (objective ground truth, not
> circular preference demos), **sprint feasibility**, and **fit with the
> self-improvement thesis**. Plus what we defer and why. See
> `docs/VISION_AND_IDEAS.md` for the full idea set.

_Last updated: 2026-06-27_

## Selection filter (why some strong ideas are cut)

- **Provable, not circular.** Methods are kept only if improvement is measurable
  against *objective* ground truth (our tiers, or LLMBar/RewardBench). The
  preference track (ideas 3/5/6/7) has no free ground truth in production.
  *Caveat / credit to the user:* the proposed **simulated users with known hidden
  policies** DO make preference-learning falsifiable — that resolves the
  "unfalsifiable demo" risk I raised earlier. It's sound; it's just a separate
  subjective track and scope-heavy → **v2**, not a 14h add.
- **Budget-aware.** Jury multiplies cost 3–4×; probes add calls. Gated to
  uncertain cases where possible.
- **Composability.** The three chosen methods stack into one narrative.

## The baseline (what we're beating)

A **vanilla single LLM-as-a-judge**: one Gemini call, fixed generic prompt,
no order-swap, no learning. Measured on held-out unseen task types + an external
benchmark. Everything below is measured as a delta over this.

---

## Method 1 — Validated-lesson self-critique loop  ⭐ (core)

**What:** Upgrade our anchored loop from free-form reflection to a *gated* one.
On each error: structured failure diagnosis (`failed_stage`, `missed_evidence`,
`incorrect_assumption`, `proposed_lesson`, `counterexample`) → **candidate**
lesson → **validate** on a held-back validation slice *and* the counterexample →
promote to `SKILL.md` only if it improves and doesn't break the counterexample.
Track lesson **provenance** so a lesson can be revoked if it later regresses
(idea 8's good part, without needing a jury).

**Why it beats baseline:** the baseline is static. This learns — and the
validation gate is what prevents the overfitting/drift that naive
"append-a-reflection" loops suffer (the failure mode our unanchored arm shows).

**Measure:** agreement (held-out unseen types + benchmark), baseline→final.
Ablation: **validated-lesson vs naive-append** (does gating actually help, or
just add cost?). Catastrophic-forgetting check across iterations.

**Cost:** moderate — reflection + a small validation pass per iteration.
**Risk:** validation costs calls; keep the validation slice small. If gating
shows no lift over naive-append, that's a *finding*, not a failure.

**Lit:** Reflexion / Self-Refine, plus the well-known result that self-generated
lessons need external validation to avoid confident drift.

---

## Method 2 — Counterfactual bias probes (detect → correct → learn)  ⭐ (most demo-obvious)

**What:** Deterministic perturbation probes — **position** (swap, have it),
**verbosity** (shorten the longer answer, preserve meaning), **formatting**
(normalize markdown/bullets), **identity** (strip model/provider names). A probe
"fails" if the verdict changes. Use the failures two ways: (a) as a **robustness
metric**, (b) as a **learning signal** — feed probe failures into Method 1's loop
so the policy grows explicit bias guards. At inference, a flipped/low-confidence
verdict triggers re-sample or escalate.

**Why it beats baseline:** a vanilla judge *visibly* flips under these
perturbations; Judy is measurably more invariant. This is the most
**demo-legible** win — "watch the normal judge change its mind when we pad the
answer; Judy doesn't."

**Measure:** flip-rate per probe (vanilla vs Judy), agreement before/after
correction. **Watch false positives:** verbosity/format transforms can subtly
change meaning → verify equivalence with a checker before counting a flip as bias.

**Cost:** each probe = extra call(s) per item → run on a **sampled subset**, not
every item. **Risk:** meaning-changing transforms create false bias signals
(the user flagged this — real concern); mitigate with an equivalence check.

**Lit:** documented position/verbosity/format biases in LLM judges + swap-and-
average / length-controlled mitigations.

---

## Method 3 — Role-diverse, reliability-weighted jury  🔥 (highest ceiling, highest cost)

**What:** A small jury of **role-specialized** judges (correctness,
completeness/helpfulness, conciseness/communication, bias-auditor), **private-
first** (independent verdicts, never shown the majority → no conformity).
Aggregate by **per-task-type historical reliability** (learned online from
agreement with ground truth), not equal vote. Optional **evidence-only
deliberation** (share missed requirements, not votes) then re-vote. Use **Gemini
+ GPT 5.5 nano** for genuine model-family diversity.

**Why it beats baseline:** panels of judges reliably match/beat a single strong
judge (PoLL); reliability-weighting adds a *learned* component, and role
diversity catches errors a single perspective misses.

**Measure:** single vs equal-vote vs reliability-weighted vs +deliberation, on
agreement; **error-correlation** between jurors; **correct-minority-opinions
lost** during deliberation; cost/latency.

**Cost:** HIGHEST — 3–4× calls per judgment. **Mitigate:** cheap single judge
first, **escalate to the jury only on high-disagreement/uncertain items**. This
is the method to **cut first** if budget/clock runs short.
**Risk:** deliberation conformity (mitigate with private-first + evidence-only);
cost blowup (mitigate with gating).

**Lit:** Panel-of-LLM-evaluators (PoLL), LLM-as-jury.

---

## How they compose (the story)

> Judy is a judge that **(1) learns from its failures with validated lessons,
> (2) is provably robust to position/verbosity/format/identity bias, and
> (3) aggregates diverse expert perspectives weighted by proven reliability** —
> and every one of those claims is measured against objective ground truth.

Probes (2) feed the self-critique loop (1); the jury (3) supplies disagreement
that gates both probes and human review. One coherent system, three measurable
deltas over the vanilla baseline.

## Evaluation framework (adopt idea 10's structure)

- **Layer A — Objective question-answering:** our tiers + LLMBar/RewardBench. Primary.
- **Layer B — Bias/robustness:** the Method-2 probes as a scored suite.
- **Layer C — Preference:** simulated users with hidden policies → **v2**.
- **Metrics:** agreement, position-consistency, calibration (ECE, esp. pointwise),
  high-confidence error rate, **improvement per iteration**, catastrophic
  forgetting, cost/latency.

## Deferred (with reasons)

- **Preference learning + probes + active selection (3/5/6/7):** falsifiable via
  simulated users (good design), but a subjective track with no production
  ground truth and meaningful build cost → **v2 theme**.
- **Active selection (6):** saves nothing while ground truth is free (tiers); only
  pays off once labels are costly (preference regime).
- **Intervention-selection policy (9):** elegant meta-layer, too heavy for 14h.
  Keep the *taxonomy* (failure → intervention) as narrative.
- **Full shared-lesson memory (8):** contingent on the jury; its best part
  (provenance + revocation) is folded into Method 1.

## Suggested build order (budget-aware)

1. **Method 1** — it's an upgrade to code we already have; highest ROI, core thesis.
2. **Method 2** — cheap-ish, most demo-legible, feeds Method 1.
3. **Method 3** — only if 1+2 land and budget allows; the stretch/closer.
