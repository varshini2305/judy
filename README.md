# Judy

A **self-improving LLM-as-a-judge** for pairwise QA. Given a task's system
prompt, a question, and two candidate answers, Judy decides which answer better
satisfies the spec — and **rewrites her own evaluation policy**
(`skills/judge/SKILL.md`) by reflecting on her mistakes. Improvement is measured
on a held-out set of *unseen task types* she never learns from.

"Self-learning" here = **context engineering** (rewriting the rubric), not
weight training. See `Judy_Iteration1_Brief.md` for the full iteration-1 spec
and `docs/ROADMAP.md` for what's deferred.

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
uvicorn judy.api.server:app --reload   # FastAPI: /run (SSE), /runs/{id}, /judge, /dataset
cd ui && npm install && npm run dev     # Vite + React dashboard
```

## Layout

- `judy/` — core package (config, data, judge, loop, eval, metrics, llm, api)
- `skills/judge/SKILL.md` — the evolving judging policy
- `runs/` — logged run artifacts (gitignored)
- `ui/` — React dashboard
- `scripts/smoke_antigravity.py` — standalone Antigravity de-risk (v2 prep)

_Status: iteration 1, in active development._
