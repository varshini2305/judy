"""Real token-usage + cost tracking for Gemini calls.

Accumulates token counts reported by the API (``usage_metadata``) so cost is
computed from actual usage, not estimates. Pricing comes from config
(Gemini 3.5 Flash standard rates).
"""

from __future__ import annotations

from dataclasses import dataclass

from judy.config import CONFIG


@dataclass
class Usage:
    n_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, input_tokens: int | None, output_tokens: int | None) -> None:
        self.n_calls += 1
        self.input_tokens += input_tokens or 0
        self.output_tokens += output_tokens or 0

    def cost_usd(self) -> float:
        return (
            self.input_tokens / 1e6 * CONFIG.price_input_per_m
            + self.output_tokens / 1e6 * CONFIG.price_output_per_m
        )

    def snapshot(self) -> "Usage":
        return Usage(self.n_calls, self.input_tokens, self.output_tokens)

    def since(self, before: "Usage") -> "Usage":
        return Usage(
            self.n_calls - before.n_calls,
            self.input_tokens - before.input_tokens,
            self.output_tokens - before.output_tokens,
        )

    def as_dict(self) -> dict:
        return {
            "calls": self.n_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd(), 4),
        }

    def summary(self) -> str:
        return (
            f"{self.n_calls} calls · {self.input_tokens:,} in + {self.output_tokens:,} out "
            f"tokens · ~${self.cost_usd():.4f} "
            f"(@ ${CONFIG.price_input_per_m:g}/{CONFIG.price_output_per_m:g} per 1M)"
        )
