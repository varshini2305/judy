"""Central configuration and runtime toggles for Judy.

Everything tunable lives here so experiments stay reproducible and the loop,
eval harness, and API all read from one source (brief §8). Values can be
overridden via environment variables (loaded from ``.env``) without code edits.

The config is a frozen dataclass; per-run variants (e.g. anchored vs
unanchored) are made with :func:`dataclasses.replace`, never by mutation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None else default


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_path(name: str, default: str) -> Path:
    return REPO_ROOT / _env_str(name, default)


@dataclass(frozen=True)
class Config:
    """Immutable run configuration. Override fields via env vars or replace()."""

    # --- Model -------------------------------------------------------------
    model: str = field(default_factory=lambda: _env_str("JUDY_MODEL", "gemini-3.5-flash"))
    gemini_api_key: str | None = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    max_concurrency: int = field(default_factory=lambda: _env_int("JUDY_MAX_CONCURRENCY", 8))

    # Gemini 3.5 Flash standard pricing (USD per 1M tokens), as of May 2026.
    # Verify at https://ai.google.dev/gemini-api/docs/pricing. Batch/Flex is ~50% off.
    price_input_per_m: float = field(default_factory=lambda: _env_float("JUDY_PRICE_INPUT_PER_M", 1.50))
    price_output_per_m: float = field(default_factory=lambda: _env_float("JUDY_PRICE_OUTPUT_PER_M", 9.00))

    # Teacher model (cross-family critic): OpenAI gpt-5.4-nano. Pricing TBD — verify.
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    teacher_model: str = field(default_factory=lambda: _env_str("JUDY_TEACHER_MODEL", "gpt-5.4-nano"))
    teacher_price_input_per_m: float = field(default_factory=lambda: _env_float("JUDY_TEACHER_PRICE_INPUT_PER_M", 0.05))
    teacher_price_output_per_m: float = field(default_factory=lambda: _env_float("JUDY_TEACHER_PRICE_OUTPUT_PER_M", 0.40))

    # --- Self-improvement loop --------------------------------------------
    n_iters: int = field(default_factory=lambda: _env_int("JUDY_N_ITERS", 4))
    # "anchored" = errors scored against known_ordering (real signal);
    # "unanchored" = judge re-ranks its own verdicts (no ground truth).
    mode: str = field(default_factory=lambda: _env_str("JUDY_MODE", "anchored"))

    # Continual learning: reflect + update the policy after every N streamed examples.
    continual_batch_size: int = field(default_factory=lambda: _env_int("JUDY_CONTINUAL_BATCH", 3))

    # --- Position-bias control (order swap) -------------------------------
    # OFF for intermediate dev passes (halves calls); ON for baseline + every
    # held-out eval, where position-consistency must be measured.
    order_swap_dev: bool = field(default_factory=lambda: _env_bool("JUDY_ORDER_SWAP_DEV", False))
    order_swap_eval: bool = field(default_factory=lambda: _env_bool("JUDY_ORDER_SWAP_EVAL", True))

    # --- Dataset -----------------------------------------------------------
    dev_size: int = field(default_factory=lambda: _env_int("JUDY_DEV_SIZE", 40))
    heldout_size: int = field(default_factory=lambda: _env_int("JUDY_HELDOUT_SIZE", 80))
    dataset_path: Path = field(
        default_factory=lambda: _env_path("JUDY_DATASET_PATH", "judy/data/datasets/judy_v1.jsonl")
    )

    # --- Evolving policy ---------------------------------------------------
    skill_path: Path = field(
        default_factory=lambda: _env_path("JUDY_SKILL_PATH", "skills/judge/SKILL.md")
    )
    skill_token_budget: int = field(
        default_factory=lambda: _env_int("JUDY_SKILL_TOKEN_BUDGET", 1200)
    )

    # --- Early stopping / saturation guards -------------------------------
    # Stop if held-out agreement fails to improve for this many iters, or if
    # score-spread (stdev of margin) collapses below this threshold.
    no_improve_patience: int = field(default_factory=lambda: _env_int("JUDY_NO_IMPROVE_PATIENCE", 2))
    score_spread_collapse: float = field(
        default_factory=lambda: _env_float("JUDY_SCORE_SPREAD_COLLAPSE", 0.3)
    )

    # --- Artifacts ---------------------------------------------------------
    runs_dir: Path = field(default_factory=lambda: REPO_ROOT / "runs")


CONFIG = Config()
