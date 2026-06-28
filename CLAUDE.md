# Judy — Standing Instructions

> Canonical home for the user's standing instructions on **how to code, how to
> ideate, and how to test/evaluate**. Auto-loaded every session. When the user
> gives a new instruction of this kind, add it here (concisely) so it never has
> to be repeated. Project *state* lives in `PROJECT_CONTEXT.md`.
>
> **Multi-agent project.** This codebase is worked on by multiple coding agents
> (Claude, Codex, Antigravity) across separate sessions. `AGENTS.md` mirrors
> this file for other agents — keep instructions here as the single source and
> let `AGENTS.md` point to it. Never fork the rules.

## Start-of-session protocol (every agent, every session)

0. Lost? `docs/INDEX.md` maps which doc holds what.
1. Read `PROJECT_CONTEXT.md` (state) and this file (rules).
2. **Reconcile before trusting:** check `git log`/diff and actual files against
   what the docs claim. Code may have changed in another agent's session. Fix
   doc drift before doing new work.
3. Read the latest handoff-log entry in `PROJECT_CONTEXT.md` to see who touched
   what last and what's unverified.

## End-of-session protocol

- Refresh `PROJECT_CONTEXT.md` and append a handoff-log entry: agent, what
  changed, next step, what's unverified.

## How to code

- **Neat, atomic commit history.** Small, well-described commits — each a
  single reviewable unit of thought. Makes design and code easy to review and
  correct.
- **Modular.** Clear separation of concerns; components reviewable and
  swappable in isolation.
- **Reviewable.** Readability over cleverness; the reviewer's experience is a
  first-class concern.
- **Efficient practices** wherever reasonable, without sacrificing the above.

## How to ideate

- All ideas are thought through and documented concisely (in
  `PROJECT_CONTEXT.md`).
- _(More to be added as the user specifies.)_

## How to test / evaluate

- _(To be added as the user specifies.)_

## Process

- Keep `PROJECT_CONTEXT.md` refreshed roughly every 20 min of active work and
  before any stopping point.
- Keep `docs/IMPLEMENTATION.md` current: what's implemented, a high-level of how,
  and concise reasoning for design/stack choices. Update it when modules land or
  change.
- Don't repeat instructions: when the user states a new "how to" preference,
  record it here.
