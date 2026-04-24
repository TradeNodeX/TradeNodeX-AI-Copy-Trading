from __future__ import annotations

import asyncio
from collections import defaultdict

from copytrading_app.domain.types import ExecutionCommandPayload


class InMemoryTaskQueue:
    def __init__(self):
        self._queues: dict[str, asyncio.Queue[ExecutionCommandPayload]] = defaultdict(asyncio.Queue)

    async def publish(self, payload: ExecutionCommandPayload) -> None:
        await self._queues[payload.queue_name.value].put(payload)

    async def consume(self, queue_name: str) -> ExecutionCommandPayload | None:
        queue = self._queues[queue_name]
        if queue.empty():
            return None
        return await queue.get()

