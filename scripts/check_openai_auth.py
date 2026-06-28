"""Minimal OpenAI auth check for Judy's synthetic benchmark tooling.

This makes one small Responses API call and prints a concise pass/fail result.

Run:
  PYTHONPATH=. python scripts/check_openai_auth.py
"""

from __future__ import annotations

import argparse

from judy.synth_benchmark.openai_client import OpenAIError, OpenAIResponsesClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Check OpenAI auth for Judy scripts.")
    parser.add_argument("--model", default="gpt-5.4-nano")
    args = parser.parse_args()

    try:
        client = OpenAIResponsesClient(model=args.model, timeout=30)
        data = client.generate_json('Return JSON only: {"ok": true}')
    except OpenAIError as exc:
        print(f"OPENAI AUTH FAIL ({args.model})")
        print(str(exc))
        raise SystemExit(1) from exc

    print(f"OPENAI AUTH OK ({args.model})")
    print(data)


if __name__ == "__main__":
    main()
