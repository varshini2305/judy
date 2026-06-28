"""Minimal OpenAI Responses API client for synthetic benchmark generation."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=True)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_KEY_RE = re.compile(r"sk-[A-Za-z0-9_\-*]+")


class OpenAIError(RuntimeError):
    """Raised when an OpenAI call or JSON parse fails."""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = _FENCE_RE.sub("", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


class OpenAIResponsesClient:
    """Tiny client using the standard library so no extra dependency is needed."""

    def __init__(self, *, model: str = "gpt-5.4-nano", timeout: int = 120):
        api_key = _clean_env_value(os.getenv("OPENAI_API_KEY"))
        if not api_key:
            raise OpenAIError("OPENAI_API_KEY is not set in the environment or .env.")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=20))
    def generate_json(self, prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "input": prompt,
            "text": {"verbosity": "medium"},
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # pragma: no cover - networked
            detail = _KEY_RE.sub("[redacted-api-key]", exc.read().decode("utf-8", errors="ignore"))
            raise OpenAIError(f"OpenAI request failed: HTTP {exc.code} {detail}") from exc
        text = body.get("output_text")
        if not text:
            text = _fallback_output_text(body)
        if not text:
            raise OpenAIError(f"OpenAI response missing output text: {body}")
        try:
            return _extract_json(text)
        except (json.JSONDecodeError, ValueError) as exc:
            raise OpenAIError(f"Could not parse JSON from model output: {text[:300]!r}") from exc


def _fallback_output_text(body: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in body.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def _clean_env_value(value: str | None) -> str | None:
    """Trim whitespace and one layer of matching quotes around env values."""
    if value is None:
        return None
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        cleaned = cleaned[1:-1].strip()
    return cleaned or None
