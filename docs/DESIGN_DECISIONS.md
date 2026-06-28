# Judy — Design & Stack Decisions (with reasoning)

> The **why** behind the build: each decision, the alternative considered, and
> the trade-off. For *what's implemented and how*, see `IMPLEMENTATION.md`; for
> the authoritative spec, `Judy_Iteration1_Brief.md`.

_Last updated: 2026-06-27_

## Architecture decisions

| Decision | Chosen | Alternative | Why this way |
|---|---|---|---|
| What "self-learning" means | Rewrite a markdown **policy** (`SKILL.md`) from reflections | Fine-tuning / RLHF on weights | No training cost in a 14h sprint; **legible** — you can read what was learned (the demo's point); reversible/inspectable |
| Judging modes | **Pairwise + pointwise**, one shared policy | Pairwise only | Real eval needs both (A/B preference *and* "did this one pass?"); the spec-criteria logic generalizes, so it's an addition not a rewrite |
| Pointwise output | **Rubric-decomposed** (per-criterion met/unmet + pass/fail + 1–5) | Single absolute score | Absolute LLM scores are noisy; decomposition improves agreement and is far more legible/defensible |
| Ground truth | **By construction** via quality tiers A>B>C>D | Human labels | Free, reliable, instant; tier C (fluent-but-flawed) is exactly where naive judges fail |
| Generalization proof | Held-out has **unseen task types**, guarded in code | Random split | Proves a *general* judging skill, not memorization; code guard makes leakage structurally impossible |
| Headline experiment | **Anchored vs unanchored** ablation | Just "it improves" | Shows self-improvement *needs an external anchor* — unanchored never sees ground truth, keeping it honest |
| Record orientation | Normalize verdicts to **canonical** sides | Store raw A/B | Order-swapped passes compare cleanly; position-consistency falls out for free |
| Policy placement in prompt | Passed as **system instruction** | Inline in user message | Stable prefix → cache-friendly + token-efficient (credits must last to demo) |
| Config | **Frozen dataclass** + `replace()` per run | Mutable globals | Reproducible runs; mode variants don't mutate shared state |
| Model client | **Async** + semaphore + tenacity retry + JSON-repair | Sync, naive | Bounded concurrency controls cost; robust to flaky output |
| Loop testability | **Injectable client** (stub) | Real calls only | Full pipeline tested for **$0**; caught a real bug already |
| Run artifacts | Plain **files** (jsonl/md/json) in `runs/` | A database | Legible, diff-able, multi-agent-friendly; the UI/API just read them |

## Stack & framework choices

| Layer | Choice | Why |
|---|---|---|
| Judge model | **Gemini 3.5 Flash** (not Pro) | Iteration-1 judge/reflector/synthesizer; prize fit + sets up v2 Antigravity; Flash for cost |
| 2nd model | **GPT 5.5 nano** (reserved) | Natural diverse/jury model later; we have OpenAI credits |
| Model SDK | `google-genai` (async) | First-party, async, JSON mode |
| Validation | **Pydantic v2** | Typed schemas + cheap coercion of loose model JSON |
| API (planned) | **FastAPI + SSE** | Same loop engine drives headless runs and the live UI; SSE streams progress |
| Database (planned) | **MongoDB** (Atlas) | Chosen for any DB / vector+text search need |
| Env tooling | **uv** | Fast venv + installs (must target `.venv` explicitly) |
| Frontend | **Vite + React + TypeScript** | Fast dev loop, typed, standard |
| Styling | **Tailwind, hand-rolled components** | Chose speed over `shadcn/ui` scaffolding to "see the look" fast; shadcn deferrable (Roadmap) |
| Charts | **Recharts** | Lightweight, declarative; fits the animated agreement curve |
| Diff view | **react-diff-viewer-continued** | Renders the SKILL.md evolution — the visible "rewriting itself" |
| Icons | **lucide-react** | Clean, consistent line icons |
| UI data | **Mock fixture first** (`src/mock/run.ts`) | See the look with $0 spend; shapes mirror the API for a clean swap |

## Visual design language (UI)

- **Dark, precise, technical** — befits an eval/infra tool; reduces chrome noise.
- **Two semantic accents:** green = improved/correct, rose = error/regressed;
  blue as neutral accent. Color *means* something (no decorative color).
- **Monospace for policy, diffs, verdicts**; Inter for chrome — signals "this is
  the machine's reasoning" vs "this is UI."
- **Every view has empty/loading states**; copy is human and specific.

## Notable trade-offs / debts (tracked in ROADMAP)

- Tailwind hand-rolled instead of shadcn/ui — faster now, less component polish.
- No Gemini context caching yet — flagged as a Next token-saver.
- Pointwise backend not yet built (UI mocks it) — next coding block.
- Single judge, not a jury — deliberately deferred (Later).
