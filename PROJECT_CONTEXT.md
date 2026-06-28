# Judy — Project Context

> Living document. Refreshed roughly every 20 min of active work so any new
> session (Claude / Codex / Antigravity) can pick up cold. Latest snapshot at
> top; handoff log + session log at bottom. **Authoritative iteration-1 spec is
> `Judy_Iteration1_Brief.md` — read it before coding.**

_Last updated: 2026-06-27_

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

- **Headless backend COMPLETE + offline-tested** (6 tests pass, zero API
  credits): config, schema, Gemini client, judge, skill manager, metrics, eval
  harness, dataset loader+guard, data generator, reflect, loop+logging.
- Loop is injectable (stub client) for free testing. Gemini path validated with
  one live call.
- **Not yet built:** `api/server.py` (FastAPI+SSE), `ui/` (React dashboard),
  `scripts/smoke_antigravity.py`. **Not yet done:** a real end-to-end run on
  generated data (costs credits — pending decision).
- Env: `.venv` via **uv**; deps + pytest installed. **9 local commits, none
  pushed.**
- Context system + `docs/IMPLEMENTATION.md` + statusline + allowlist in place.
- Sprint clock: 14 hours to demo (started 2026-06-27).

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

- **2026-06-27 — Claude** · Set up context system + folded iteration-1 brief
  into this doc (decisions D1–D5). · Next: scaffold. · Unverified: git/model id.
- **2026-06-27 — Claude** · Built headless core + the self-improvement loop
  (reflect anchored/unanchored, run+logging). Added `docs/IMPLEMENTATION.md`.
  Wrote offline test suite (stub client, 0 credits) — full loop + metrics +
  JSON + skill mutation; caught/fixed a dedup bug. 9 commits, none pushed. ·
  Next: decide on a cost-bounded REAL end-to-end run to prove anchored improves,
  then build API + UI. · Unverified: real-data behavior (anchored lift),
  Antigravity smoke test.

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
