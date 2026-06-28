"""Run the judge over a split, optionally under order-swap, concurrently.

The harness is the single way the loop and the API evaluate items, so the
order-swap policy and concurrency live in one place. With ``order_swap=True``
each item is judged in both orientations (needed for position-consistency).
"""

from __future__ import annotations

import asyncio

from judy.judge.judge import judge_item
from judy.judge.schema import Item, JudgeRecord
from judy.llm.gemini import GeminiClient


async def eval_split(
    client: GeminiClient,
    skill_text: str,
    items: list[Item],
    *,
    order_swap: bool,
) -> list[JudgeRecord]:
    """Judge every item (both orders if ``order_swap``); returns flat records."""
    coros = []
    for item in items:
        coros.append(judge_item(client, skill_text, item, swap=False))
        if order_swap:
            coros.append(judge_item(client, skill_text, item, swap=True))
    return list(await asyncio.gather(*coros))
