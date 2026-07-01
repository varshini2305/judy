# Judy — SFT methodology & experimental setup (for review)

> How we propose to fine-tune the LLM judge *correctly* and, crucially, how we
> evaluate it. Written for review (incl. an external professor). Focus: data
> construction, the 20→100 scaling curve, and eval rigor. Supersedes the flawed
> setup documented in `SFT_REVIEW_NOTES.md`.

_Prepared 2026-06-30._

## 0. The specific question

"Fine-tune on 100 examples and see how held-out performance changes as we add
examples in steps of 20 (20 → 40 → 60 → 80 → 100)." i.e. a **data-scaling curve**
for an LLM judge.

## 1. Hard reality: this is NOT one training job

Managed Gemini tuning (Vertex) trains for a set number of **epochs over the whole
dataset** and returns a tuned model (with, at most, **per-epoch** checkpoints). It
**cannot emit a checkpoint "after the first 20 of 100 examples."** So a
*data-scaling* curve (x-axis = number of distinct examples) is intrinsically
**multiple fine-tunes on nested subsets**, not one job:

- Tune A on examples 1–20 → eval
- Tune B on examples 1–40 → eval
- … Tune E on 1–100 → eval

Two ways to run this; we recommend the first:

- **(Recommended) 5 independent tunes on nested subsets**, each starting from the
  same base model. Cleanest: no curriculum-order confound; each point is "base +
  N examples." This is what the earlier `checkpoint_{20,40,60,80,100}` dirs were —
  structurally correct.
- **(Alt) 5 continuation tunes** (tune on 20, continue on next 20, …). Fewer total
  training tokens, but introduces order/curriculum effects and continuation tuning
  was finicky on our CLI. Only if cost matters a lot.

We wrap the 5 tunes + 5 evals in **one driver script**, so operationally it is
"run once," even though it submits 5 managed jobs. *(A single job with per-epoch
checkpoints answers a different question — "more epochs on fixed 100" — not
"more examples"; we can add that as a secondary axis if useful.)*

## 2. Training-data construction (the right way)

1. **Format-matched to inference (fixes the prior skew).** Each training row's
   prompt = `build_user_prompt(...)` with the **`SKILL.md` policy as system
   instruction**; target = the **real JSON verdict** `{verdict,margin,rationale,
   criteria}` — exactly what the deployed/eval judge produces. (Prior setup trained
   on a bare `A`/`B` under a different prompt → train/serve skew.)
2. **Verified reasoning traces, not bare labels.** Targets are produced by
   **rejection sampling** (STaR-style): a teacher judge generates a JSON verdict;
   keep the row only if its verdict == gold label, so the target carries a
   *correct* rationale. Bare-label targets erode the judge's reasoning.
   (`scripts/export_sft_format_matched.py`.)
3. **Right distribution / difficulty.** Draw the 100 examples from where the judge
   has **headroom** — adversarial / hard cases — not saturated objective cases the
   base already gets ~92–97% right (no learning signal, forgetting risk). Training
   distribution should match the eval distribution (§3).
4. **"Example" = one unique item.** Swap-balancing (both A/B orders) doubles each
   item into 2 training sequences to suppress position bias, but the curve's
   x-axis counts **unique items** (100 items → 200 sequences).
5. **Stratified nesting.** Order the 100 items with a fixed seed but stratified by
   task type / difficulty so every prefix (20, 40, …) is a *representative* sample,
   not e.g. all-easy-first. This makes the curve interpretable.
6. **No leakage.** The eval sets (§3) share **zero items** with the 100 training
   items; assert this in code.

## 3. Eval-data construction (the part that matters most for SFT)

1. **Fixed, disjoint, reused across all 5 checkpoints.** The *same* held-out test
   set scores 20/40/60/80/100 so the curve is comparable. Base model = the
   **N=0 point** on the same set.
2. **Format-matched eval.** Evaluate with the same format the model was trained on
   (`build_user_prompt` + policy + JSON) — i.e. the existing
   `scripts/eval_tuned_judge.py`. Because training is now JSON-format, this eval is
   finally a fair test (no skew).
3. **Eval where there is headroom.** Objective synthetic saturates at ~92.5% base
   → almost no room to show gains, and the prior deltas (−0.5/−1.5/−1.0pp) sit
   **inside statistical noise**. Use an **adversarial / hard** held-out set
   (e.g. LLMBar-adversarial) as the primary eval so the curve can actually move.
4. **Separate validation vs test.** Use a **val** split to pick epochs / the best
   checkpoint; report only on a **test** split never used for selection. Selecting
   the best checkpoint on the test set is leakage.
5. **Statistical power + CIs.** On 100 test items, binomial 95% CI is ≈ ±8–10pp
   near 90%. So **report confidence intervals** and treat sub-CI deltas as noise.
   Prefer ≥200–300 eval items if feasible; otherwise state the CI explicitly.
6. **Baselines on the same eval.** Always include (a) untuned base (N=0), and ideally
   (b) the context-engineering variants (V1/V2), so "did weights help vs. just a
   better prompt?" is answerable.
7. **Contamination check.** Confirm eval items/answers were not used to *generate*
   or appear in training.

## 4. Metrics

- **Agreement** with the gold/human label (primary), with 95% CI.
- **Position-consistency** (verdict stable under A/B swap) + **pos-consistent
  agreement**.
- Reported per checkpoint (0/20/40/60/80/100) → the scaling curve.

## 5. Fine-tuning setup specifics (to fill in at run time)

| Setting | Value / plan |
|---|---|
| Base model | `gemini-3.5-flash` (Vertex, project you own) |
| Method | managed supervised tuning (parameter-efficient adapter) |
| Subsets | nested: 20/40/60/80/100 unique items (stratified, seed=13) |
| Sequences/subset | 2× items (swap-balanced) |
| Epochs | fixed across subsets (e.g. 3–5); pick via val, report the same policy |
| LR multiplier / adapter size | Vertex defaults unless tuning; hold **constant** across subsets |
| Eval set | fixed held-out **adversarial** set, disjoint; + base as N=0 |
| Seeds | fixed (data order, split) for reproducibility |
| Artifacts | per-subset tuned model/endpoint id, per-checkpoint metrics, curve.json |

**Controls:** everything except the number of training examples is held constant
across the 5 tunes, so the curve isolates the effect of data quantity.

## 6. Protocol (one driver, 5 tunes)

1. `export_sft_format_matched.py` → ordered/stratified 100 train items (JSON,
   reasoning targets) + val + Vertex JSONL; assert disjoint from eval.
2. For `k in [20,40,60,80,100]`: submit a tune on the first `k` items (same base,
   same hyperparams), record the tuned endpoint.
3. For each tuned endpoint **and** the base: run `eval_tuned_judge.py` on the fixed
   held-out set → agreement (+CI), position-consistency.
4. Emit `curve.json` (N → metrics) and plot. Interpret: is the trend upward,
   flat, or noisy? Does it ever beat base beyond the CI? Does it beat V1/V2?

## 7. Is this "the right way"? — summary for the reviewer

- **Fixes vs. the prior setup:** format-matched targets (no train/serve skew),
  reasoning traces (not bare labels), data with headroom, fixed disjoint eval,
  val/test separation, CIs, base + context-engineering baselines.
- **Honest expectation:** 100 examples is small; this measures **data efficiency
  and trend**, not peak performance. A flat/negative curve is still a valid finding
  (it would say: for a strong base judge, SFT at this scale/data doesn't beat
  prompt-based methods — consistent with our other results).

## 8. Open questions for the professor

1. Nested independent tunes vs. continuation tuning for the scaling curve — is
   independent the right call to avoid curriculum confounds?
2. Eval headroom: is moving the primary eval to adversarial (vs saturated objective)
   the right way to make the curve informative?
3. Reasoning targets via rejection sampling (drop teacher-wrong rows) vs. keeping
   corrected targets — which biases the study less?
4. Is 100 examples / this eval size adequate, or should we prioritize a larger eval
   for tighter CIs over more training data?
5. SFT vs. preference optimization (DPO) / RFT given labels are verifiable — is SFT
   even the right tool here, or a baseline to beat?
