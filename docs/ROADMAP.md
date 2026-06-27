# Judy Roadmap

This is our living, feedback-organized backlog. Status: **Now** (this iter) · **Next** (right after prototype works) · **Later** (extension/stretch).

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
