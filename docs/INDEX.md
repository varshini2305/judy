# Judy — Documentation Map

> Meta-index: **which doc holds what**, so any agent or human can navigate our
> notes, context, and policy files fast. Start here when you're lost.

## The docs, by purpose

| File | What's in it | Read it when… | Maintained |
|---|---|---|---|
| **`Judy_Iteration1_Brief.md`** | Authoritative iteration-1 **spec** (scope, domain model, loop spec, metrics, UI spec, DoD) | You need the source of truth for *what to build* | Frozen (user-authored) |
| **`PROJECT_CONTEXT.md`** | Living **state**: vision, timeline, decisions D1–D6, open questions, current state, **handoff log**, session log | Starting any session — what's done, what's next, who touched what | Every ~20 min + session end |
| **`CODEX_CONTEXT.md`** | Codex-owned **orientation + review notes**: repo reality, drift, review hotspots | You want a fast Codex-centric scan before reviewing or resuming work | Codex sessions |
| **`CLAUDE.md`** | Standing **instructions** (how to code/ideate/test) + session protocol; canonical for all agents | You need the rules of how we work | On new "how to" rules |
| **`AGENTS.md`** | Cross-agent pointer (Codex/Antigravity) → CLAUDE.md + PROJECT_CONTEXT.md | Working as a non-Claude agent | Rarely (points elsewhere) |
| **`README.md`** | Setup + run instructions (uv, generate, loop, API, UI) | You want to *run* Judy | On workflow changes |
| **`docs/IMPLEMENTATION.md`** | **What's implemented + how**: module map, run commands, cost-discipline hooks | You need to understand the code structure | When modules land/change |
| **`docs/DESIGN_DECISIONS.md`** | **Why**: design + stack choices, alternatives, trade-offs, visual language | You're questioning or extending a choice | When a decision is made/revised |
| **`docs/VARIANTS.md`** | **Central registry of judge variants** (V0/V1/V2/V5…): what each is, models, train/test data, real results vs baseline; how to add a variant | You're implementing or comparing a judge variant | When a variant is added/run |
| **`docs/EXPERIMENT_PLAN.md`** | Method **theory**: the top methods to beat a vanilla judge + what's deferred | Choosing which improvement method to try | When the method shortlist changes |
| **`docs/DEMO_PLAN.md`** | Preference-learning demo + baseline results (RewardBench/LLMBar) | Building the user-preference demo or baselines | As demo/baselines evolve |
| **`docs/MODEL_TUNING_PLAN.md`** | Concrete **weight-update plan**: Gemini tuning split, GCS layout, dataset schemas, build order | You are working on model updates rather than context-only self-improvement | When the tuning track changes |
| **`docs/VISION_AND_IDEAS.md`** | User's original 8 ideas + promise/feasibility verdicts + the frontier shortlist | Deciding what to explore beyond iter 1 | When vision/ideas evolve |
| **`docs/ROADMAP.md`** | Backlog: **Now / Next / Later** across UI, judge methods, RSI, hackathon, tech debt | Planning what to do next | As items move |
| **`docs/INDEX.md`** | This map | You don't know where to look | When a doc is added/removed |
| **`skills/judge/SKILL.md`** | The **evolving judging policy** (data the loop rewrites — not documentation) | Inspecting/seeding the judge's rubric | By the loop (snapshots in `runs/`) |

## Context outside the repo

| Location | What | Notes |
|---|---|---|
| `~/.claude/.../memory/MEMORY.md` | Index of persistent **memories** (user prefs, feedback, project facts) | One line per memory; loaded each session |
| `~/.claude/.../memory/*.md` | Individual memories: working-principles, project-context, multi-agent-workflow, autonomy-and-ops, curated-research-sources, tech-stack-and-cost | Survive across sessions |
| `.claude/settings.json` | Statusline (context bar + reset countdown) + permission allowlist | Local, **gitignored** (machine-specific) |
| `~/.claude/judy-statusline.py` | The statusline script | User-global |

## "Where do I find…?" quick reference

- **What we're building / the spec** → `Judy_Iteration1_Brief.md`
- **What's done right now / what's next** → `PROJECT_CONTEXT.md` (current state + handoff log)
- **Codex's quick read / review notes** → `CODEX_CONTEXT.md`
- **How the code is organized** → `docs/IMPLEMENTATION.md`
- **Why we chose X (model, framework, approach)** → `docs/DESIGN_DECISIONS.md`
- **Which judge variants we tried + their results vs baseline** → `docs/VARIANTS.md`
- **Which improvement methods to try / the experiment plan** → `docs/EXPERIMENT_PLAN.md`
- **How the Gemini tuning track should work** → `docs/MODEL_TUNING_PLAN.md`
- **How to run it** → `README.md`
- **The backlog / deferred ideas** → `docs/ROADMAP.md`
- **The rules of how we work together** → `CLAUDE.md`
- **User preferences & past guidance** → memory files (`MEMORY.md` index)
