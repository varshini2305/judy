# Judy — Build Brief, Iteration 1

**Hand this whole file to Claude Code. Build exactly the scope in §1. Consult your `frontend-design` skill before building the UI (§7).**

---

## 0. What we're building

**Judy** is a self-improving LLM-as-a-judge for **question-answering (QA)** tasks. Given a task's *system prompt*, a *question*, and two candidate *answers*, Judy decides which answer better satisfies the spec. The differentiator: **Judy rewrites her own evaluation policy (a `SKILL.md` file) by reflecting on her mistakes, and her improvement is measured on a held-out set she never trains on.**

This is an *evaluation-infrastructure* project (hackathon theme: **The Self-Improvement Stack**; secondary: **Continual Learning**). Model provider is **Google Gemini** (`gemini-3.5-flash`), because iteration 2 grounds verdicts using Google's Antigravity managed agent (built on 3.5 Flash).

**"Self-learning" here = context engineering, not weight training.** The judge improves by rewriting its own instructions/rubric from self-generated reflections on its errors, validated out-of-sample. No fine-tuning in iteration 1 (it's a documented later extension in `docs/ROADMAP.md`).

---

## 1. Iteration 1 scope

**IN:**
1. Synthetic QA dataset generator (with system prompts, quality tiers, held-out *unseen task types*).
2. Pairwise judge that reads its policy from `skills/judge/SKILL.md`.
3. Self-improvement loop: evaluate → analyze errors → rewrite `SKILL.md` → re-evaluate.
4. Metrics: agreement, position-consistency, score-spread.
5. Anchored-vs-unanchored ablation (the headline result).
6. A polished UI dashboard (4 screens, §7).
7. A **standalone** Antigravity smoke-test script (de-risk only; not wired into the core).

**OUT (later iterations — see `docs/ROADMAP.md`):** Antigravity grounding integration, fine-tuning/RLHF, jury/panel, persona personalization, active learning. Do **not** build these now. Do lay out code so they slot in cleanly.

---

## 2. Domain model

**Item** (one evaluation unit):
```
Item {
  id: str
  task_type: str            # e.g. "factual_qa", "constrained_format", "persona_support"
  system_prompt: str        # the task spec: task + format + persona + constraints/prohibitions
  question: str
  gold_answer: str          # ANCHOR ONLY — never shown to the judge
  candidates: [Candidate]   # exactly 2 at judge time, drawn from the tiers below
  known_ordering: (winner_tier, loser_tier)  # ground truth, by construction
}
Candidate { tier: "A"|"B"|"C"|"D", text: str }
```

**Quality tiers** (so ground truth is free, by construction — `A > B > C > D`):
- **A** — faithful: correct *and* fully spec-compliant.
- **B** — thin: correct but incomplete or poorly expressed.
- **C** — plausible failure: fluent and confident but flawed on **one of two axes** — (c1) factually wrong/unsupported, or (c2) factually fine but **violates the system prompt** (wrong format, ignores a required constraint, breaks a persona/prohibition). This is the hard, important tier.
- **D** — off-topic / non-answer.

**The judge sees:** `system_prompt`, `question`, `answer_A`, `answer_B`. **Never** the gold answer or the tiers.
**The judge outputs:** `{ verdict: "A"|"B", margin: 1-5, rationale: <=40 words, criteria: [{name, winner}] }`.
**The anchor (`known_ordering`) is used only to score the judge**, never as judge input.

**Dataset construction:**
- ~100–120 items across ≥5 `task_type`s.
- Pairings weighted toward **A-vs-C** (where a naive judge gets fooled — this is where improvement headroom lives).
- **Calibrate difficulty so the baseline judge scores ~60–75%**, not 90%. If the seed judge already aces it, make C answers more deceptive.
- Split: **dev (~40)** the loop learns from; **held-out (~80)** measured, never touched by the loop. **The held-out split must contain `task_type`s that do NOT appear in dev** — this is how we prove a *general* judging skill rather than task memorization.
- **Guard in code:** the loop must be structurally unable to read held-out during training; assert on it.

---

## 3. Architecture

```
judy/
  config.py              # central config + toggles (model, iters, order-swap, anchored/unanchored, sizes)
  data/
    generate.py          # synthetic data generator (uses gemini to synthesize tiered answers)
    datasets/            # generated *.jsonl
  judge/
    schema.py            # pydantic: Item, Candidate, Verdict
    skill.py             # load / save / snapshot / diff SKILL.md
    judge.py             # build prompt from SKILL.md + item -> model -> parse JSON verdict
  loop/
    reflect.py           # error analysis -> proposed SKILL.md edits
    run.py               # the self-improvement loop + run logging
  eval/
    harness.py           # run judge over a split, with order-swap
  metrics/
    metrics.py           # agreement, position_consistency, score_spread
  llm/
    gemini.py            # thin Gemini client: model, JSON output, retries/backoff, async pool
  api/
    server.py            # FastAPI: /run (SSE), /runs/{id}, /judge, /dataset
  skills/
    judge/SKILL.md       # the EVOLVING judging policy (Antigravity-compatible path — do not move)
  runs/                  # logged artifacts: runs/{run_id}/{iter_N.jsonl, skill_N.md, metrics.json}
scripts/
  smoke_antigravity.py   # standalone Antigravity de-risk (§9)
ui/                      # Vite + React + TS + Tailwind + shadcn/ui + Recharts
docs/
  ROADMAP.md             # feedback-organized backlog (§10) — seed it as specified
README.md
.env.example             # GEMINI_API_KEY=
```

Keep modules small and single-purpose. All prompts live in `judge/judge.py` and `loop/reflect.py` (not scattered) so they're easy to iterate. The loop must run **headless** (`python -m judy.loop.run`) and also drive the UI via the API — same engine, two entry points.

---

## 4. The self-improvement loop (precise spec)

Structure follows TRT (Test-time Recursive Thinking): the policy carries an accumulating **knowledge list** ("failure modes to avoid") and **strategies**, updated by pairwise reflection on errors.

```
load SKILL.md  ->  R_0
baseline:
  verdicts = eval(held_out, R_0, order_swap=ON)     # log baseline metrics
for t in 1..N (default N=4):
  dev_verdicts = eval(dev, R_{t-1}, order_swap=per config)
  errors = [items where verdict != known_ordering]
  edits  = reflect(errors, R_{t-1})                 # one gemini call; see below
  R_t    = apply(edits, R_{t-1})                    # append to knowledge/strategies; bounded edits to procedure
  snapshot R_t -> runs/{id}/skill_t.md
  held_metrics = eval(held_out, R_t, order_swap=ON) # log per-iteration
stop early if: held-out agreement fails to improve for 2 iters, OR score-spread collapses below threshold.
```

**`reflect(errors, skill)`** — a single `gemini-3.5-flash` call:
- Input: the current SKILL.md + a compact list of errored items (system prompt, answers, judge's wrong verdict + rationale, and the *correct* ordering with a one-line "why the correct answer was actually better").
- Output (JSON): `{ failure_modes: [<=3 short, task-GENERAL lessons], strategies: [<=2 general tactics], procedure_edits: [optional, <=2] }`.
- **Hard constraint, enforce in the prompt and ideally validate:** edits must be **task-general** (about *how to judge any spec*), never task-specific (no "for travel questions, prefer X"). Task-specific edits don't transfer and cause overfitting/drift. Keep total SKILL.md under a token budget (~1.2k tokens); if exceeded, consolidate.

**Anchored vs unanchored ablation:** add a config flag. *Anchored* = errors defined against `known_ordering` (real signal). *Unanchored* = the judge re-ranks its own verdicts with no ground truth and reflects on that. Run both; expect anchored to improve and unanchored to plateau or drift. **This contrast is the intellectual core of the demo** — it shows self-improvement needs an external anchor.

Log everything to `runs/{run_id}/`: per-iter verdicts (`iter_N.jsonl`), skill snapshots (`skill_N.md`), and `metrics.json`. The UI reads these.

---

## 5. Metrics (define in `metrics/metrics.py`)

- **Agreement** — fraction of held-out pairs where `verdict == known_ordering`. The headline.
- **Position-consistency** — fraction where the verdict is identical under both answer orders (requires order-swap). Also report **position-consistent agreement** (correct under *both* orders). This is the position-bias guard.
- **Score-spread** — stdev of `margin` (1–5) across items, tracked per iteration. A collapse toward uniformly-high margins is the early-warning sign of saturation/over-confidence (it shows up before accuracy degrades). Plot it.

---

## 6. Token-efficiency rules (apply throughout)

- Use **`gemini-3.5-flash`** for judge, reflection, and data synthesis. No Pro.
- **Structured JSON output** (`response_format` / JSON schema) everywhere — no prose parsing, cheap + reliable.
- Cap outputs: judge `rationale <= 40 words`; reflection bounded as in §4.
- **Iterate the loop on the 40-item dev set; run held-out only at iteration boundaries.**
- **Order-swap toggle:** OFF for intermediate dev passes (halves calls); ON for baseline and every held-out eval (position-consistency needs it).
- Async request pool with retry/backoff; batch the eval passes.
- Keep the `SKILL.md + system_prompt` as a stable prefix; if Gemini context caching is quick to wire, use it — otherwise note it as a **Next** item in ROADMAP, don't block on it.

---

## 7. UI spec (this matters — make it genuinely good)

**Consult your `frontend-design` skill first.** Single-page app, sectioned/tabbed. Aesthetic: precise, technical, confident — dark theme, one accent color for *improved/correct*, one for *error/regressed*, monospace for SKILL.md/diffs/verdicts, clean sans (Inter) for chrome, generous spacing, strong hierarchy, zero clutter. Avoid a templated/generic look. Every view needs loading skeletons, empty states, and error toasts — never a blank screen. Copy should be human and specific ("Judy caught 7 mistakes and rewrote her rubric"), not robotic ("Process complete").

**Screen 1 — Control Room (default):**
- Hero line chart (Recharts): **held-out agreement vs iteration**, two series — Anchored (solid) and Unanchored (dashed). Animate the line extending as iterations complete.
- Metric cards: current agreement, position-consistent agreement, score-spread, # errors.
- Run controls: *Run baseline*, *Run N iterations*, dataset selector, toggles (order-swap, anchored/unanchored).
- Live status strip streaming loop progress via SSE ("Iteration 2/4 · evaluating dev · 18/40").

**Screen 2 — Skill Evolution:**
- Iteration selector. **Unified or side-by-side diff of `SKILL.md`** between iter t-1 and t (use a diff component, e.g. `react-diff-viewer-continued`). Highlight appended failure-modes/strategies.
- The growing **"Known failure modes"** list rendered as cards — this is the visible proof the model is rewriting itself.

**Screen 3 — Item Inspector:**
- Table of held-out items: task_type, verdict, correct/incorrect badge, margin. Filters: errors-only, A-vs-C-only, by task_type.
- Expand a row: system prompt, question, both answers, judge rationale + per-criterion winners, the known ordering. Visually mark cases where the judge was fooled by fluency/format.

**Screen 4 — Try Judy (live):**
- Inputs: system prompt, question, answer A, answer B. *Judge* button → calls `/judge` → shows verdict, margin, rationale, criteria.
- Include a **disabled "Ground with Antigravity →" button** with a "coming in v2" tooltip, to foreshadow iteration 2.

**Frontend stack:** Vite + React + TypeScript + Tailwind + shadcn/ui + Recharts + a diff component. **Backend:** FastAPI — `POST /run` (starts a run, **SSE** progress stream), `GET /runs/{id}` (artifacts/metrics), `POST /judge` (single live judgment), `GET /dataset`.

---

## 8. Config & toggles (`judy/config.py`)

`MODEL="gemini-3.5-flash"`, `N_ITERS=4`, `ORDER_SWAP_DEV=False`, `ORDER_SWAP_EVAL=True`, `MODE="anchored"|"unanchored"`, `DEV_SIZE=40`, `HELDOUT_SIZE=80`, `DATASET_PATH`, `SKILL_PATH="skills/judge/SKILL.md"`, `SKILL_TOKEN_BUDGET=1200`, score-spread collapse threshold. Everything tunable in one place.

---

## 9. Antigravity smoke test (`scripts/smoke_antigravity.py`, standalone)

Purpose: prove the bleeding-edge API works for our account **before** iteration 2 depends on it. Do **not** import this into the core. Using `google-genai >= 2.3.0`:
- One `client.interactions.create(agent="antigravity-preview-05-2026", input="write & run a python script that prints 2+2", environment="remote")`.
- Print `interaction.status`, `interaction.output_text`, `interaction.environment_id`.
- A second call reusing `previous_interaction_id` + the `environment_id` to confirm **stateful persistence** (e.g., "read the file you just wrote").
- Print clear PASS/FAIL with the failure reason (auth / unknown agent id / lost context). It's a public preview, so handle non-`completed` statuses gracefully.

---

## 10. `docs/ROADMAP.md` (seed it exactly like this)

This is our living, feedback-organized backlog. Status: **Now** (this iter) · **Next** (right after prototype works) · **Later** (extension/stretch).

```
# Judy Roadmap

## UI / UX
- [Now] Control Room, Skill Evolution, Item Inspector, Try Judy
- [Next] SSE streaming polish; animated skill-diff reveal on each reflection
- [Later] Run comparison view; cost/latency panel

## Judge-Improvement Methods
- [Now] Self-rewriting SKILL.md (rubric + knowledge list + strategies); order-swap debias; spec->checklist
- [Next] Selective Antigravity grounding (code_execution + google_search) on uncertain / claim-heavy items
- [Later] Few-shot error-memory in prompt; sharper criteria extraction
- [Later · compute] Fine-tune judge (Self-Taught Evaluators; Self-Rationalization DPO); RL judge (J1-style consistency reward)

## RSI / Self-Improvement Methods
- [Now] Anchored self-improvement loop; anchored-vs-unanchored ablation (TRT vs Mirror Loop)
- [Next] Persist skill + state across sessions via Antigravity environment_id
- [Later] Jury / panel with blind aggregation + diversity guard (PoLL; GEA Performance-Novelty)
- [Later] Meta-judge loop (Meta-Rewarding); active-learning selection for cheap human labels

## Hackathon Optimizations
- [Now] Self-Improvement Stack theme framing; Gemini 3.5 / Antigravity prize via grounding + persistence
- [Next] DigitalOcean deploy (insurance prize); demo script + one-pager
- [Later] Computer Use combo (only if far ahead); named custom agent via agents.create()

## Tech Debt / Quality
- [Now] Typed schemas, modular layout, token-efficiency rules, run logging, held-out guard assertion
- [Next] Tests for metrics + JSON parser; retry/backoff hardening
```

---

## 11. Seed `skills/judge/SKILL.md` (create with this content)

```markdown
---
name: judge
description: Evaluation policy for Judy, a pairwise QA judge. Defines how to score answer quality against a task's system prompt.
---

# Judge Policy

## Role
You are an impartial evaluator. Given a task's system prompt, a question, and two candidate answers (A and B), decide which answer better satisfies the spec. Judge adherence to the spec, not your own taste.

## Procedure
1. Derive criteria from the system prompt: extract the task, required format, persona/tone, and any constraints or prohibitions. Treat each as a checklist item.
2. Check correctness independently of style: is each answer factually accurate and actually responsive? Do not infer correctness from fluency or confidence.
3. Check spec-compliance: an answer can be correct yet fail the spec (wrong format, ignored constraint, violated prohibition). Penalize these.
4. Compare on the union of criteria. If one answer is correct-but-noncompliant and the other compliant-but-wrong, weigh which failure is more severe for this spec.

## Bias guards (do not violate)
- Fluency is not correctness. A polished but unsupported answer loses to a plainer correct one.
- Length is not quality. Do not default to the longer answer.
- Position is not quality. Your verdict must be identical if A and B are swapped.
- Verify claims against the question, not against assumptions.

## Known failure modes to avoid
(none yet — the self-improvement loop appends task-general lessons here)

## Strategies in use
- Extract a criteria checklist from the system prompt before reading the answers.

## Output
Return JSON only: {"verdict": "A"|"B", "margin": 1-5, "rationale": "<=40 words", "criteria": [{"name": str, "winner": "A"|"B"|"tie"}]}
```

---

## 12. Definition of done (iteration 1)

- `python -m judy.data.generate` writes a dataset with held-out *unseen task types*; baseline tuned to ~60–75%.
- `python -m judy.loop.run` runs baseline + 4 iterations for **both** anchored and unanchored modes, logs to `runs/`, snapshots `SKILL.md` per iteration, computes all metrics.
- UI: all four screens functional, reading from `runs/` and the live `/run` SSE stream; *Try Judy* works.
- `scripts/smoke_antigravity.py` runs and prints PASS/FAIL.
- `README.md`: setup + run instructions; `.env.example` with `GEMINI_API_KEY`.

## 13. Coding standards

Python: type hints + pydantic schemas, docstrings on public functions, small focused modules, no dead code. Frontend: TypeScript strict. Secrets only via `.env` (never in code). Pin `google-genai>=2.3.0`. Robust JSON parsing with one retry on malformed output. Prefer clarity over cleverness — this code will be read and extended every few hours.

---

**Build §1 only. When done, print: (a) the baseline vs final held-out agreement for both anchored and unanchored modes, (b) the smoke-test result, (c) anything that needs my input.**
