"""Load / save / snapshot / diff the evolving judging policy (``SKILL.md``).

The policy is plain markdown with named sections. The self-improvement loop
appends task-general lessons to the "Known failure modes" and "Strategies"
sections; this module owns all reading, writing, section-editing, snapshotting,
and diffing of that file (brief §3).
"""

from __future__ import annotations

import difflib
from pathlib import Path

FAILURE_MODES_HEADER = "## Known failure modes to avoid"
STRATEGIES_HEADER = "## Strategies in use"
_PLACEHOLDER_PREFIX = "(none yet"


def load_skill(path: Path) -> str:
    """Read the current policy text."""
    return Path(path).read_text(encoding="utf-8")


def save_skill(path: Path, content: str) -> None:
    """Write the policy text back to disk."""
    Path(path).write_text(content, encoding="utf-8")


def snapshot_skill(content: str, run_dir: Path, iteration: int) -> Path:
    """Persist a policy snapshot for iteration ``t`` to ``run_dir/skill_t.md``."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    dest = run_dir / f"skill_{iteration}.md"
    dest.write_text(content, encoding="utf-8")
    return dest


def diff_skill(before: str, after: str, *, context: int = 3) -> str:
    """Unified diff between two policy versions (for the UI / logs)."""
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="skill_before.md",
            tofile="skill_after.md",
            n=context,
        )
    )


def approx_tokens(text: str) -> int:
    """Cheap token estimate (~4 chars/token) to enforce the skill budget."""
    return len(text) // 4


def append_bullets(content: str, header: str, bullets: list[str]) -> str:
    """Append ``- bullet`` lines under ``header``, clearing any placeholder.

    Bullets already present (case-insensitive, trimmed) are skipped so the
    policy does not accumulate duplicate lessons across iterations.
    """
    bullets = [b.strip() for b in bullets if b.strip()]
    if not bullets:
        return content

    lines = content.splitlines()
    try:
        h = next(i for i, ln in enumerate(lines) if ln.strip() == header)
    except StopIteration:
        # Header missing: append a fresh section at the end.
        block = "\n".join(f"- {b}" for b in bullets)
        return f"{content.rstrip()}\n\n{header}\n{block}\n"

    # Find the section body (until the next "## " header or EOF).
    end = h + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1

    body = lines[h + 1 : end]
    existing = {ln.lstrip("- ").strip().lower() for ln in body if ln.strip().startswith("-")}
    kept = [ln for ln in body if not ln.strip().lower().startswith(_PLACEHOLDER_PREFIX)]
    new_bullets = [f"- {b}" for b in bullets if b.lower() not in existing]

    rebuilt = lines[: h + 1] + _trim_blanks(kept) + new_bullets + [""] + lines[end:]
    return "\n".join(rebuilt).rstrip() + "\n"


def _trim_blanks(block: list[str]) -> list[str]:
    """Drop leading/trailing blank lines from a section body."""
    start, stop = 0, len(block)
    while start < stop and not block[start].strip():
        start += 1
    while stop > start and not block[stop - 1].strip():
        stop -= 1
    return block[start:stop]
