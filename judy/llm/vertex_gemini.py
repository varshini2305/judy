"""Vertex-backed Gemini client for tuned endpoint evaluation.

This mirrors Judy's ``generate_json`` interface so evaluation code can compare
the standard Gemini API path against a tuned Vertex endpoint with minimal
branching. It uses ADC rather than an API key.
"""

from __future__ import annotations

import asyncio
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from judy.llm.gemini import GeminiError, _extract_json
from judy.llm.usage import Usage

try:  # pragma: no cover - surfaced clearly at runtime
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover
    genai = None
    genai_types = None


class VertexGeminiClient:
    """Async-compatible wrapper for Gemini calls routed through Vertex AI."""

    def __init__(
        self,
        *,
        model: str,
        project: str,
        location: str,
        max_concurrency: int = 8,
    ) -> None:
        if genai is None:
            raise GeminiError(
                "google-genai is not installed. Run: pip install -r requirements.txt"
            )
        self.model = model
        self.project = project
        self.location = location
        self._client = genai.Client(vertexai=True, project=project, location=location)
        self._sema = asyncio.Semaphore(max_concurrency)
        self.usage = Usage()

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=20))
    def _raw_generate_sync(
        self, prompt: str, *, system_instruction: str | None, temperature: float
    ) -> str:
        cfg = genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
            system_instruction=system_instruction,
        )
        resp = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=cfg,
        )
        um = getattr(resp, "usage_metadata", None)
        if um is not None:
            self.usage.add(
                getattr(um, "prompt_token_count", 0),
                getattr(um, "candidates_token_count", 0),
            )
        return resp.text or ""

    async def generate_json(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        async with self._sema:
            text = await asyncio.to_thread(
                self._raw_generate_sync,
                prompt,
                system_instruction=system_instruction,
                temperature=temperature,
            )
            try:
                return _extract_json(text)
            except (ValueError, TypeError):
                repair = (
                    f"{prompt}\n\nYour previous reply was not valid JSON. "
                    "Return ONLY a valid JSON object."
                )
                text = await asyncio.to_thread(
                    self._raw_generate_sync,
                    repair,
                    system_instruction=system_instruction,
                    temperature=temperature,
                )
                try:
                    return _extract_json(text)
                except (ValueError, TypeError) as exc:
                    raise GeminiError(f"Could not parse JSON from model: {text[:200]!r}") from exc
