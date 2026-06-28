"""Thin OpenAI client for the cross-family TEACHER model (gpt-5.4-nano).

Mirrors GeminiClient's ``generate_json`` interface so the teacher can be dropped
into the same loops. Tracks usage with OpenAI pricing. NOTE: the exact call shape
for gpt-5.x nano (chat.completions vs responses API, temperature support) must be
validated against the live API once a working OPENAI_API_KEY is set.
"""

from __future__ import annotations

import asyncio
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from judy.config import CONFIG
from judy.llm.gemini import _extract_json  # reuse robust JSON parsing
from judy.llm.usage import Usage

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover
    AsyncOpenAI = None


class OpenAIError(RuntimeError):
    pass


class OpenAIClient:
    """Async OpenAI client used as Judy's teacher/critic."""

    def __init__(self, model: str | None = None):
        if AsyncOpenAI is None:
            raise OpenAIError("openai is not installed. Run: pip install -r requirements.txt")
        if not CONFIG.openai_api_key:
            raise OpenAIError("OPENAI_API_KEY is not set. Add it to your .env file.")
        self.model = model or CONFIG.teacher_model
        self._client = AsyncOpenAI(api_key=CONFIG.openai_api_key)
        self._sema = asyncio.Semaphore(CONFIG.max_concurrency)
        self.usage = Usage(
            price_in=CONFIG.teacher_price_input_per_m,
            price_out=CONFIG.teacher_price_output_per_m,
        )

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=20))
    async def generate_json(
        self, prompt: str, *, system_instruction: str | None = None, temperature: float = 0.0
    ) -> dict[str, Any]:
        async with self._sema:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            u = getattr(resp, "usage", None)
            if u is not None:
                self.usage.add(getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0))
            text = resp.choices[0].message.content or ""
            return _extract_json(text)
