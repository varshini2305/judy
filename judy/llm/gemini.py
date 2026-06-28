"""Thin Gemini client: JSON output, retry/backoff, bounded async concurrency.

All model calls in Judy (judge, reflection, data synthesis) go through here so
retry policy, JSON parsing, and concurrency limits live in one place
(brief §6). Uses the ``google-genai`` SDK (>=2.3.0).
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import replace
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from judy.config import CONFIG, Config

try:  # imported lazily-friendly so importing the module never hard-fails
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover - surfaced clearly at call time
    genai = None
    genai_types = None

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class GeminiError(RuntimeError):
    """Raised when the model call or JSON parsing ultimately fails."""


def _extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from model text, tolerating code fences / prose."""
    cleaned = _FENCE_RE.sub("", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


class GeminiClient:
    """Async-first wrapper around a single Gemini model."""

    def __init__(self, config: Config = CONFIG):
        if genai is None:
            raise GeminiError(
                "google-genai is not installed. Run: pip install -r requirements.txt"
            )
        if not config.gemini_api_key:
            raise GeminiError("GEMINI_API_KEY is not set. Add it to your .env file.")
        self.config = config
        self.model = config.model
        self._client = genai.Client(api_key=config.gemini_api_key)
        self._sema = asyncio.Semaphore(config.max_concurrency)

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=20))
    async def _raw_generate(self, prompt: str, *, system_instruction: str | None, temperature: float) -> str:
        cfg = genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
            system_instruction=system_instruction,
        )
        resp = await self._client.aio.models.generate_content(
            model=self.model, contents=prompt, config=cfg
        )
        return resp.text or ""

    async def generate_json(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Generate and parse a JSON object. One repair retry on malformed output."""
        async with self._sema:
            text = await self._raw_generate(
                prompt, system_instruction=system_instruction, temperature=temperature
            )
            try:
                return _extract_json(text)
            except (json.JSONDecodeError, ValueError):
                repair = f"{prompt}\n\nYour previous reply was not valid JSON. Return ONLY a valid JSON object."
                text = await self._raw_generate(
                    repair, system_instruction=system_instruction, temperature=temperature
                )
                try:
                    return _extract_json(text)
                except (json.JSONDecodeError, ValueError) as exc:
                    raise GeminiError(f"Could not parse JSON from model: {text[:200]!r}") from exc

    async def map_json(
        self,
        prompts: list[str],
        *,
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Run many prompts concurrently (bounded by max_concurrency)."""
        tasks = [
            self.generate_json(p, system_instruction=system_instruction, temperature=temperature)
            for p in prompts
        ]
        return await asyncio.gather(*tasks)

    def generate_json_sync(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Blocking convenience for scripts / single calls."""
        return asyncio.run(self.generate_json(prompt, **kwargs))


def client_for_mode(mode: str) -> GeminiClient:
    """Build a client whose config carries the given loop mode."""
    return GeminiClient(replace(CONFIG, mode=mode))
