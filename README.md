# Judy

**Judy** is a self-improving **LLM-as-a-judge** for pairwise QA. Given a task's
system prompt, a question, and two candidate answers, Judy decides which answer
better satisfies the spec, then **rewrites her own evaluation policy**
(`skills/judge/SKILL.md`) by reflecting on her mistakes. Improvement is
measured on a held-out set of *unseen task types* she never learns from.

The name plays on the idea of a **judge and jury working together**. The judge
defines the rules, evaluation criteria, and structure. The jurors act as
independent decision-makers who examine the evidence from different angles, such
as correctness, helpfulness, preference, and bias. That court-style setup is
the larger vision for Judy: structured deliberation that reduces the influence
of any single evaluator's blind spots.

"Self-learning" here means **context engineering** and policy improvement, not
weight training. See `Judy_Iteration1_Brief.md` for the full iteration-1 spec
and `docs/ROADMAP.md` for deferred work.

## Model Stack

- **Current primary model:** Google Gemini `gemini-3.5-flash` for judging,
  reflection, and dataset-related synthesis in iteration 1.
- **Secondary / exploratory model path:** OpenAI models are available for later
  comparison, jury-style disagreement analysis, and follow-on experiments where
  a second evaluator adds useful diversity.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your GEMINI_API_KEY
```

## Run (headless)

```bash
python -m judy.data.generate     # synthesize the QA dataset
python -m judy.loop.run          # baseline + N iterations (anchored & unanchored)
```

Artifacts land in `runs/{run_id}/` (per-iter verdicts, SKILL.md snapshots,
metrics). Config and toggles live in `judy/config.py`.

## API + UI

```bash
cd ui && npm install && npm run dev     # Vite + React dashboard
```

Live app: [judy-production-8e7e.up.railway.app](https://judy-production-8e7e.up.railway.app/)

The UI is in active development. The current direction is a clearer landing
page and dashboard that explain the vision, the current baseline, what worked,
what did not, and where the framework is pushing frontier LLM-as-a-judge and
recursive self-improvement ideas.

## Layout

- `judy/` — core package (config, data, judge, loop, eval, metrics, llm, api)
- `skills/judge/SKILL.md` — the evolving judging policy
- `runs/` — logged run artifacts (gitignored)
- `ui/` — React dashboard
- `scripts/smoke_antigravity.py` — standalone Antigravity de-risk (v2 prep)

## What's Next

- Improve README and UI readability/accessibility so the project is easier to
  understand quickly.
- Build a high-quality slide deck focused on the problem, the framework, the
  technical strengths, the limitations, and what makes the approach hard to
  replicate cleanly.
- Ship a landing page that clearly explains the vision, execution, roadmap,
  experiments tried, and lessons learned.
- Measure real performance against baselines so claims about improvement are
  supported by actual evaluation numbers.

_Status: iteration 1, in active development._
