# Judy — Agent Guide (Codex, Antigravity, and others)

This is a **multi-agent project**. Work alternates between Claude Code, Codex,
and Antigravity across separate sessions. To stay coherent:

## Read these first, every session

1. **`PROJECT_CONTEXT.md`** — current project state: vision, architecture,
   decisions, open questions, current work, and the **handoff log** at the
   bottom (who touched what last, and what is unverified).
2. **`CLAUDE.md`** — the single canonical source of the user's standing
   instructions on how to code, ideate, and test/evaluate. These rules apply to
   **every** agent, not just Claude. Do not fork or duplicate them here.

## Standing rules (summary — full text in `CLAUDE.md`)

- Neat, atomic, well-described commits — each a single reviewable unit.
- Modular, readable, reviewable code; efficient practices where reasonable.
- Don't repeat instructions: new "how to" rules go in `CLAUDE.md`, once.

## Before you start coding

- **Reconcile before trusting the docs.** Code may have changed in another
  agent's session. Check `git log`/diff and the actual files against what the
  docs claim, and fix any drift first.

## When you finish

- Update `PROJECT_CONTEXT.md` and append a handoff-log entry: which agent you
  are, what changed, the next step, and anything left unverified.
