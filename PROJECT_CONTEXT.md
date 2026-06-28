# Judy — Project Context

> Living document. Refreshed roughly every 20 min of active work so any new
> session (Claude / Codex / Antigravity) can pick up cold. Latest snapshot at
> top; handoff log + session log at bottom. **Authoritative iteration-1 spec is
> `Judy_Iteration1_Brief.md` — read it before coding.**

_Last updated: 2026-06-28_

## What this is

**Judy** — a self-improving **LLM-as-a-judge** for **pairwise QA**. Given a
task's `system_prompt`, a `question`, and two candidate answers, Judy decides
which answer better satisfies the spec.

**Differentiator:** Judy rewrites her own evaluation policy (`skills/judge/SKILL.md`)
by reflecting on her mistakes, and improvement is measured on a **held-out set
of unseen task types** she never learns from. "Self-learning" = **context
engineering** (rewriting instructions/rubric), **not** weight training. No
fine-tuning in iteration 1.

Hackathon theme: *The Self-Improvement Stack* (secondary: *Continual Learning*).

## Working principles (hard requirements)

- **Neat atomic commit history** — each commit a single reviewable unit.
- **Modular, reviewable code**; readability over cleverness.
- **Efficient practices** (esp. token-efficiency — see brief §6).
- See `CLAUDE.md` for full standing rules; `AGENTS.md` mirrors for other agents.

## Timeline & ambition

- **14-hour demo sprint** (clock started 2026-06-27, continuous). Build
  **iteration-1 scope only** (brief §1). Keep a runnable, demoable state at all
  times. Stretch goals (jury, Antigravity grounding) are explicitly OUT.

## Model access & goals

- **Provider (iter 1):** Google **Gemini** `gemini-3.5-flash` for judge,
  reflection, and data synthesis. **VALIDATED** via one live call (google-genai
  2.10.0). No Pro.
- **Second model:** **GPT 5.5 nano** (`gpt-5.5-nano`) available "wherever
  applicable" — natural diverse/jury model for later; OpenAI credits on hand.
- **Database / search:** **MongoDB** (Atlas) for any DB or vector/text search.
- **Cost discipline:** credits must last through iteration + demo. Keep test
  runs TINY, reuse generated datasets, never re-run the full pipeline just to
  check wiring. See [[judy-tech-stack-and-cost]].
- **No Anthropic in the product** — Claude is only the coding agent.

## Self-learning approach (iteration 1)

Structure follows **TRT (Test-time Recursive Thinking)**: the policy carries an
accreting **knowledge list** ("failure modes to avoid") + **strategies**,
updated by pairwise reflection on errors. Loop: `eval → analyze errors →
rewrite SKILL.md → re-eval` (default N=4 iters).

- **Reflection** = one `gemini-3.5-flash` call → JSON `{failure_modes(≤3),
  strategies(≤2), procedure_edits(≤2)}`. **Edits must be task-GENERAL** (how to
  judge any spec), never task-specific — enforced to prevent overfitting/drift.
  SKILL.md kept under ~1.2k tokens.
- **Anchored vs unanchored ablation = the intellectual core.** Anchored = errors
  vs `known_ordering` (real signal); unanchored = judge re-ranks its own
  verdicts, no ground truth. Expect anchored to improve, unanchored to
  plateau/drift → shows self-improvement needs an external anchor.
- Frontier methods (GEPA, meta-rewarding, jury, fine-tuning) are documented in
  `docs/ROADMAP.md` as Next/Later, not built now.

## Architecture

Full layout in brief §3. Headline: Python package `judy/` (config, data,
judge, loop, eval, metrics, llm/gemini client, FastAPI api) + `skills/judge/SKILL.md`
(the evolving policy) + `runs/` (logged artifacts) + `ui/` (Vite+React+TS+
Tailwind+shadcn+Recharts) + `scripts/smoke_antigravity.py` + `docs/ROADMAP.md`.

- Loop runs **headless** (`python -m judy.loop.run`) AND drives UI via the API —
  same engine, two entry points.
- All prompts centralized in `judge/judge.py` + `loop/reflect.py`.
- **Held-out guard:** loop must be structurally unable to read held-out during
  training; assert on it.

## Domain model (brief §2)

- **Item:** `{id, task_type, system_prompt, question, gold_answer (ANCHOR only,
  never shown), candidates[2], known_ordering}`.
- **Quality tiers A>B>C>D** give free ground truth. **Tier C** (plausible
  failure: factually wrong OR spec-violating) is the hard, important tier.
- Judge sees `system_prompt, question, answer_A, answer_B`; outputs `{verdict,
  margin(1-5), rationale(≤40w), criteria[]}`. Never sees gold/tiers.
- Dataset ~100–120 items, ≥5 task_types, weighted toward **A-vs-C**. Baseline
  tuned to **~60–75%** (not 90%). Split: dev(~40) learns, held-out(~80) measured
  — **held-out contains task_types absent from dev**.

## Metrics (brief §5)

- **Agreement** (headline) · **Position-consistency** (under order-swap) ·
  **Score-spread** (stdev of margin; collapse = early saturation warning).

## Key design decisions

- **D1 — Models:** Gemini `gemini-3.5-flash` only in iter 1 (OpenAI parked).
- **D2 — Domain:** pairwise QA judging. (2026-06-27)
- **D3 — Self-learning = context engineering** (SKILL.md rewrite), no
  fine-tuning iter 1. (2026-06-27)
- **D4 — Core demo result:** anchored-vs-unanchored ablation on held-out unseen
  task types. (2026-06-27)
- **D5 — Ground truth by construction** via quality tiers A>B>C>D. (2026-06-27)
- **D6 — Judge supports TWO modes, one shared policy:** *pairwise* (A vs B,
  headline) and *pointwise* (independent eval). Pointwise output is
  **rubric-decomposed**: per-criterion met/unmet + holistic verdict (pass/fail)
  + 1–5 score. Reuses the tiered dataset (tier→label/score is ground truth) and
  the same reflect→rewrite loop. Pairwise stays the demo headline; pointwise is
  a first-class second capability (shown in Try Judy, optional 2nd RSI track).
  (2026-06-27)

## Open questions / to confirm

- **Push timing:** origin added (`git@github.com:varshini2305/judy.git`); push
  held until initial setup done + user confirms. 6 commits waiting.
- **Cost-safe dataset test:** before running the full generator (~42 synth
  calls), confirm a tiny smoke (2 instances) is the right validation step.
- **Design skill:** brief §7 says `frontend-design`; available are gstack's
  (`design-consultation`, `design-html`, `design-shotgun`) + design judgment.
- Antigravity smoke test (brief §9): bleeding-edge preview id; may FAIL
  gracefully. GPT 5.5 nano exact id to confirm when first used.

## Current state

- **Headless backend COMPLETE + offline-tested**: config, schema, Gemini
  client, judge, skill manager, metrics, eval harness, dataset loader+guard,
  data generator, reflect, loop+logging.
- **UI exists and is mock-driven** in `ui/` with the shell and four screens
  already implemented; the main missing integration is wiring it to a live API.
- Benchmarking work now includes a RewardBench baseline, judge-variant
  comparison tooling, and an additional JudgeBench sample fetch helper for a
  harder external baseline track.
- Loop is injectable (stub client) for free testing. Gemini path has been
  validated with a live call.
- **Still missing / unverified:** `judy/api/server.py` (FastAPI+SSE), pointwise
  backend wiring, `scripts/smoke_antigravity.py`, and a real end-to-end run on
  generated data.
- Env: `.venv` via **uv**; deps + pytest installed, and root-level `pytest`
  invocation has been fixed.
- Context system + `docs/IMPLEMENTATION.md` + statusline + allowlist are in
  place.

## Multi-agent workflow

Work alternates between **Claude Code, Codex, and Antigravity** across sessions.

- **Single source of truth:** `PROJECT_CONTEXT.md` (state) + `CLAUDE.md`
  (rules); `AGENTS.md` points other agents here. Rules never forked.
- **Start of session:** read both docs + the brief, then *reconcile against
  actual git/code state* before trusting them.
- **End of session:** refresh this doc + append a handoff-log entry.

---

## Handoff log

> One entry per work block: agent · what changed · next step · unverified.

- **2026-06-28 — Codex** · Added the first concrete weight-update track:
  `docs/MODEL_TUNING_PLAN.md`, offline export helpers in `judy/tuning/`,
  exporter scripts for SFT and simulated-user preference tuning, tests for those
  exporters, and doc updates pointing the rest of the repo at that plan.
  Tightened the JudgeBench fetch helper to produce a broader sample. · Next:
  confirm the exact Agent Platform JSONL schema before cloud job wrappers, then
  compare tuned judges against the current policy-rewrite baseline. ·
  Unverified: final Google Cloud tuning request format, tuned-model quality, and
  the right train/val/test split sizes for the first paid run.
- **2026-06-28 — Codex** · Added synthetic benchmark generation scaffolding with
  a minimal OpenAI Responses client, prompt templates for objective and
  preference pairwise cases, a generator script, a review-row transformer, a
  browser-based annotation page, and offline tests. Also added a lightweight
  OpenAI auth check script. · Next: generate and review a first clean synthetic
  benchmark set, then decide how it should feed evals versus human review. ·
  Unverified: live OpenAI auth in the target environment, output quality of the
  generated benchmark, and the right review workflow once human annotations
  start accumulating.
- **2026-06-28 — Codex** · Expanded the landing page messaging substantially so
  the UI now explains Judy's product vision, current execution strategy, latest
  baseline story, common LLM-as-a-judge limitations, what has worked, what has
  not, and the stack of ideas being explored from policy rewriting to tuning to
  jury-style RSI. The copy is now anchored to the actual docs and benchmark
  notes rather than generic marketing language. Verified `cd ui && npm run build`
  still succeeds. · Next: visually review the page in-browser, tighten density
  and hierarchy if needed, and then connect sections to live API-backed numbers
  as backend work lands. · Unverified: final copy quality after user review,
  live data integration, and whether the benchmark narrative shifts with new
  experiments over the next few hours.
- **2026-06-28 — Codex** · Added a real UI landing/overview screen so the app
  now opens with product messaging instead of dropping users straight into the
  internal dashboard. The new screen explains what Judy does, the judge+jury
  vision, the anchored-vs-unanchored method, current capabilities, and what is
  still mock-driven or unverified. Verified `cd ui && npm run build`
  succeeds after the change. · Next: tighten the narrative further with clearer
  benchmark evidence and replace mock content with live API-backed data once the
  backend is wired. · Unverified: user-facing copy quality after visual review,
  live backend integration, and final benchmark-backed claims.
- **2026-06-28 — Codex** · Added `docs/UI_DEPLOYMENT.md` with a Vercel-first
  hosting recommendation for the current static UI, plus a GCP-friendly
  Firebase Hosting path and a containerized Railway / Cloud Run path. Added
  `ui/Dockerfile`, `ui/Caddyfile`, and `ui/.dockerignore` so the frontend can
  ship as a portable static container. Verified `cd ui && npm run build`
  succeeds. · Next: wire the first real hosted URL if requested, then switch
  the deployed UI from mock data to the live backend once `judy/api/server.py`
  exists. · Unverified: actual deployed environment, custom domains, and live
  backend connectivity.
- **2026-06-28 — Codex** · Added `docs/MODEL_TUNING_PLAN.md` to make the
  weight-update track concrete: Gemini `3.5 Flash` for supervised fine-tuning,
  Gemini `2.5 Flash` for preference tuning, GCS-based dataset layout, JSONL
  intermediate schemas, and a staged build order starting with export scripts.
  Updated the doc map, roadmap, and implementation notes to point to it. ·
  Next: implement dataset exporters for SFT and preference tuning, then add
  thin tuning-job wrappers once the exported schemas are reviewed. ·
  Unverified: exact Agent Platform JSONL field shapes for our exporters, cloud
  credentials/project setup, tuned-model quality on held-out + benchmark evals.
- **2026-06-28 — Codex** · Refreshed the shared context docs for current repo
  reality, tightened the README project framing, added a Codex-specific context
  file for faster cold starts, and prepared coherent commits so completed work
  can be pushed before the log gets noisy. Also included a JudgeBench sample
  fetch helper as a standalone benchmark utility. · Next: keep landing-page /
  deck / evaluation work landing in small pushable slices, and connect any new
  benchmark or weight-update experiments back into the shared context trail. ·
  Unverified: live API wiring, pointwise backend completion, JudgeBench results,
  and whether weight-update methods will enter near-term scope.
- **2026-06-27 — Codex** · Updated `README.md` with a stronger project intro,
  a short judge/jury concept explanation, a concise model-stack section
  covering Gemini + OpenAI, and a public-facing "What's Next" roadmap covering
  readability/accessibility, slide deck, landing page, and real baseline
  measurement. · Next: turn the README roadmap into concrete artifacts starting
  with either landing-page copy structure or a slide-deck outline. ·
  Unverified: final performance numbers, which OpenAI model path will be used
  first, and the exact public narrative once more experiments land.
- **2026-06-27 — Codex** · Reconciled docs against the repo, scanned backend/UI
  once, added `CODEX_CONTEXT.md` for Codex-specific orientation/review notes,
  and noted that plain `pytest` currently fails import discovery (`judy` not on
  path). · Next: review Claude changes as they land, or pick up pointwise
  backend/API work if asked. · Unverified: live Gemini path, API wiring,
  pointwise backend, default test invocation fix.
- **2026-06-27 — Claude** · Set up context system + folded iteration-1 brief
  into this doc (decisions D1–D5). · Next: scaffold. · Unverified: git/model id.
- **2026-06-27 — Claude** · Built headless core + self-improvement loop + offline
  tests (0 credits). Pushed to origin (12 commits total). Decided D6 (pairwise +
  pointwise rubric-decomposed). Built the full UI (4 screens) on mock data — dev
  server runs at :5173; user reviewing the look. · Next: implement pointwise
  backend, then FastAPI+SSE server to replace the mock, then the real run +
  Antigravity smoke test. · Unverified: real-data anchored lift; pointwise
  backend unbuilt; live API unbuilt.

---

## Session log

- **2026-06-27** — Project kicked off. Working principles set (atomic commits,
  modular/reviewable code, efficiency). Context-doc + 20-min refresh cadence.
- **2026-06-27** — Reframed as 14-hour demo sprint (continuous). Multi-agent
  workflow (Claude/Codex/Antigravity) + reconcile-before-trust protocol.
- **2026-06-27** — Models locked: Gemini (showcase 3.5), OpenAI available;
  no Anthropic in product. Discussed frontier self-learning menu (Reflexion,
  GEPA, meta-rewarding, TextGrad). User curates research sources (no unprompted
  web search).
- **2026-06-27** — User delivered `Judy_Iteration1_Brief.md`: full iteration-1
  spec. Resolves prior open questions — self-rewriting SKILL.md judge on
  pairwise QA, anchored-vs-unanchored ablation as the core, Gemini 3.5 Flash,
  jury/Antigravity/fine-tuning deferred to ROADMAP.
- **2026-06-27** — README positioning pass started: project naming now frames
  Judy as a judge/jury-style evaluation framework, with public-facing roadmap
  items for model disclosure, accessibility/readability, a clear landing page,
  a high-quality slide deck, and performance-vs-baseline validation.
- **2026-06-27** — Added an explicit multi-agent process rule: keep context
  files continuously updated so Claude/Codex/other agents can see progress,
  next steps, and in-flight work without duplicating or clobbering each other,
  including any future weight-update-based exploration.
