# Judy — Implementation Notes

> Technical reference: **what** is implemented, **how** (high level), and **why**
> (design/stack reasoning). Kept current as the code evolves. For project *state*
> see `PROJECT_CONTEXT.md`; for the *spec* see `Judy_Iteration1_Brief.md`.

_Last updated: 2026-06-28_

## System in one paragraph

Judy is a pairwise question-answering judge whose **policy is a markdown file** (`skills/judge/SKILL.md`).
A loop evaluates the judge, reflects on its mistakes via an LLM, and **appends
task-general lessons** to that policy — then re-measures on a held-out set of
*unseen task types*. The headline experiment compares **anchored** learning
(reflect against ground truth) vs **unanchored** (reflect against the judge's own
self-inconsistency); anchored should improve, unanchored should plateau/drift,
demonstrating that self-improvement needs an external anchor.

## What's implemented (module map)

| Module | Responsibility | How |
|---|---|---|
| `judy/config.py` | Central config + toggles | Frozen dataclass, env-overridable; per-run variants via `replace()` |
| `judy/judge/schema.py` | Domain types | Pydantic: `Item`, `Candidate`, `Verdict`, `Criterion`, `JudgeRecord`. Ground truth via tier rank (`correct_side`) |
| `judy/llm/gemini.py` | Model access | Async `google-genai` client; JSON mode, tenacity retry, semaphore concurrency, one JSON-repair retry |
| `judy/judge/judge.py` | One judgment | Builds prompt (policy = system instruction), handles order-swap, maps verdict → canonical side, coerces loose output |
| `judy/judge/skill.py` | Policy file ops | load/save/snapshot/diff + `append_bullets` (dedup, placeholder-aware) + token estimate |
| `judy/metrics/metrics.py` | Metrics | agreement, position-consistency (+consistent-agreement), score-spread, from records |
| `judy/data/dataset.py` | Dataset IO + split | JSONL with `split` tag; **held-out guard** asserts disjoint ids + unseen task types |
| `judy/data/generate.py` | Synthetic data | LLM synthesizes tiered A/B/C/D answers per instance; A-vs-C-weighted pairings |
| `judy/eval/harness.py` | Run a split | Concurrent `judge_item` over items, both orders if order-swap |
| `judy/eval/synthetic.py` | Synthetic benchmark eval loader | Maps hidden `objectively_better` labels into `Item`s for base-vs-tuned judge comparisons |
| `judy/loop/reflect.py` | Error → edits | One LLM call; anchored vs unanchored prompt; enforces task-GENERAL lessons |
| `judy/loop/run.py` | The loop + logging | baseline + N iters per mode, early stopping, writes `runs/{id}/` |
| `judy/tuning/export.py` | Tuning dataset transforms | Exports Judy/benchmark/synthetic objective rows into SFT-ready JSONL plus preference rows |
| `judy/data/personas.py` | V4 user personas | 5 simulated users with **hidden** taste policies (label oracle; never shown to jurors) |
| `judy/eval/jury.py` | V4 judge-jury (subjective) | B0 single judge vs per-user jurors (`reflect`/`fewshot` modes); reuses harness+metrics+reflect; emits per-user agreement + personalization matrix |
| `scripts/generate_creative_pref_benchmark.py` | V4 benchmark gen | gpt-5.4-nano creative pairs + per-persona labels (position-randomised) → `creative_pref_benchmark.jsonl` |

**UI built (artifact-backed for results):** `ui/` — Vite+React+TS+Tailwind+
Recharts+diff-viewer. The current shipped views are:
- overview/landing page with vision, execution, findings, and next steps
- variant comparison dashboard backed by `ui/public/experiments.json`
- continual-learning curve view backed by `ui/public/curves/*.json`
- weight-update / SFT dashboard backed by `ui/public/sft/judy_sft_v20_eval.json`
- `Try Judy` pairwise/pointwise demo tab, still a local stub until the live API lands

The old mock run fixture (`src/mock/run.ts`) remains in the tree for the
interactive demo surface only; the benchmark/result views no longer depend on it.

**Not yet built:** pointwise backend (D6: rubric-decomposed independent eval —
schema, judge fn, tier→label/score ground truth, harness+metrics+reflect paths),
`judy/api/server.py` (FastAPI + SSE to replace the mock), `scripts/smoke_antigravity.py`.

**Weight-update track (partially implemented):** see
`docs/MODEL_TUNING_PLAN.md`. Local export scaffolding now exists for:
- supervised fine-tuning JSONL from Judy / RewardBench / JudgeBench pairs
- simulated-user preference JSONL for Gemini `2.5 Flash`
- synthetic Judy benchmark export into an objective-only SFT bundle
- base-vs-tuned evaluation wiring on held-out synthetic objective cases

Cloud submission is still a thin prep layer rather than a verified end-to-end
job launcher: `scripts/run_gemini_sft.py` currently writes deterministic GCS
upload commands plus a request stub, and the exact Vertex / Agent Platform
submission payload still needs to be checked against live docs before first use.

## Key design choices (and why)

- **Policy as a markdown file, not weights.** "Self-learning" = context
  engineering. Cheap, fast, fully legible — you can *read* what the judge learned
  (the demo's whole point) and there's no fine-tuning cost in a 14h sprint.
- **Ground truth by construction (tiers A>B>C>D).** Free, reliable labels with no
  human annotation. Tier C (fluent-but-flawed) is where naive judges fail, so
  it's where learning headroom lives → pairings weighted toward A-vs-C.
- **Held-out = unseen task types, guarded in code.** Proves a *general* judging
  skill rather than task memorization; the guard makes leakage structurally
  impossible (asserts on load).
- **Canonical-orientation records.** Verdicts are normalized so order-swapped
  passes compare cleanly; position-consistency falls out naturally.
- **Anchored vs unanchored as separate reflection paths.** Unanchored never sees
  ground truth (only order-inconsistency), keeping the ablation honest.
- **Policy passed as the system instruction.** Stable prefix → cache-friendly and
  token-efficient (credits must last to the demo).
- **Frozen config + `replace()`.** Reproducible runs; mode variants don't mutate
  shared state.

## Stack choices (and why)

- **Gemini 3.5 Flash** — iteration-1 judge/reflector/synthesizer (prize fit +
  sets up v2 Antigravity). Flash, not Pro: cost. `google-genai` SDK (async).
  GPT 5.5 nano reserved as the diverse/jury model later.
- **Pydantic v2** — typed schemas + cheap validation/coercion of model JSON.
- **FastAPI + SSE** (planned) — same loop engine drives headless runs and the UI.
- **MongoDB** — chosen for any DB / vector+text search needs.
- **uv** — fast venv + installs.
- **tenacity / numpy** — retry-backoff; metric stats.

## Token / cost discipline (where it lives in code)

- JSON-only outputs everywhere; judge rationale ≤40 words; reflection bounded
  (≤3 failure modes, ≤2 strategies, ≤2 procedure edits); skill capped at ~1.2k
  tokens (`apply_edits` refuses over-budget growth).
- Order-swap OFF for dev passes, ON only for baseline/held-out (`config.py`).
- Bounded concurrency (semaphore) and dataset reuse to conserve credits.

## How to run (current)

```bash
uv venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m judy.data.generate            # synthesize dataset (LLM calls)
.venv/bin/python -m judy.loop.run --iters 4       # anchored + unanchored ablation
PYTHONPATH=. python scripts/export_judy_benchmark_sft.py
PYTHONPATH=. python scripts/run_gemini_sft.py --dataset-dir ... --bucket-uri gs://... --project-id ...
PYTHONPATH=. python scripts/eval_tuned_judge.py --dataset ... --tuned-model projects/.../models/...
```
