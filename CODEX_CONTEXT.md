# Judy — Codex Context

> Codex-owned working context. This is a fast orientation and review aid, not a
> replacement for `PROJECT_CONTEXT.md` or `CLAUDE.md`.

_Last updated: 2026-06-27_

## What Judy is

Judy is a self-improving LLM judge for QA evaluation. Iteration 1's headline is
an anchored-vs-unanchored self-improvement loop on held-out task types the
judge never learns from. "Learning" means rewriting `skills/judge/SKILL.md`,
not training weights.

## Repo reality after one scan

- Backend core exists in `judy/`: config, schemas, dataset loader/guard, judge,
  reflection, metrics, and the loop runner are present.
- The UI exists in `ui/` and is currently mock-driven from
  `ui/src/mock/run.ts`; the shell and four screens are implemented.
- `judy/api/server.py` does not exist yet even though `README.md` and some docs
  describe the API path as if it is available.
- Pointwise judging is described in docs and surfaced in the UI copy, but the
  backend still looks pairwise-first. Treat pointwise backend work as likely
  next.
- The working tree is not clean: `CLAUDE.md` is modified, and
  `docs/DESIGN_DECISIONS.md` plus `docs/INDEX.md` are currently untracked.

## Verified behavior

- The self-improvement loop in `judy/loop/run.py` runs anchored and unanchored
  modes separately, snapshots `SKILL.md`, logs artifacts under `runs/{run_id}/`,
  and stops early on no improvement or score-spread collapse.
- The held-out generalization guard in `judy/data/dataset.py` enforces disjoint
  ids plus at least one held-out-only `task_type`.
- Reflection in `judy/loop/reflect.py` is task-general by prompt design and
  bounded in output shape and token budget.

## Current drift / caveats

- `PROJECT_CONTEXT.md` still says the API and pointwise backend are not built.
  That seems directionally true for the API, but the document lags the fact that
  the UI is now present.
- Plain `pytest -q` from repo root currently fails at collection with
  `ModuleNotFoundError: No module named 'judy'`. That is packaging/test-path
  wiring, not necessarily a logic failure, but it means "tests pass" is not true
  for a default local invocation right now.
- The brief asked for `frontend-design`; this repo instead has a shipped UI plus
  docs noting design choices. That is historical context only unless the user
  wants more UI work.

## Review hotspots for future Claude work

- Any changes around pointwise judging: likely schema expansion, new judge path,
  metrics implications, and API/UI contract changes.
- API wiring: FastAPI endpoints, SSE progress streaming, and replacing the mock
  fixture without breaking the current UI shell.
- Dataset generation and loop economics: these are the highest risk for cost,
  latency, and demo instability once real calls resume.
- Docs drift: the project is moving quickly enough that README, implementation
  notes, and project context can diverge from the code within a session.

## How I should use this file

- Refresh it after any substantial Codex scan, review, or implementation block.
- Keep shared facts in `PROJECT_CONTEXT.md`; keep Codex-specific review notes and
  "what to inspect next" here.
