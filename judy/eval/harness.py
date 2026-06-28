"""Run the judge over a split, optionally under order-swap, concurrently.

The harness is the single way the loop and the API evaluate items, so the
order-swap policy and concurrency live in one place. With ``order_swap=True``
each item is judged in both orientations (needed for position-consistency).
"""

from __future__ import annotations

import asyncio
import time

from judy.judge.judge import judge_item
from judy.judge.schema import Item, JudgeRecord
from judy.llm.gemini import GeminiClient


async def eval_split(
    client: GeminiClient,
    skill_text: str,
    items: list[Item],
    *,
    order_swap: bool,
    progress_label: str | None = None,
) -> list[JudgeRecord]:
    """Judge every item (both orders if ``order_swap``); returns flat records."""
    tasks = []
    for item in items:
        tasks.append(asyncio.create_task(judge_item(client, skill_text, item, swap=False)))
        if order_swap:
            tasks.append(asyncio.create_task(judge_item(client, skill_text, item, swap=True)))

    if not progress_label:
        return list(await asyncio.gather(*tasks))

    started = time.monotonic()
    total = len(tasks)
    every = max(1, total // 10)
    done = 0
    results: list[JudgeRecord] = []
    print(f"[{progress_label}] starting {total} judgments...", flush=True)
    for task in asyncio.as_completed(tasks):
        results.append(await task)
        done += 1
        if done == total or done % every == 0:
            elapsed = time.monotonic() - started
            rate = done / elapsed if elapsed > 0 else 0.0
            eta = (total - done) / rate if rate > 0 else 0.0
            print(
                f"[{progress_label}] {done}/{total} "
                f"({done / total:.0%}) · {elapsed:.1f}s elapsed · ~{eta:.1f}s left",
                flush=True,
            )
    return results
