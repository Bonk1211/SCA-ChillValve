"""WebSocket connection helpers."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator


async def drain_queue(q: asyncio.Queue) -> AsyncIterator[dict]:
    while True:
        msg = await q.get()
        yield msg
