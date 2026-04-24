from __future__ import annotations

from typing import Protocol

from copytrading_app.domain.types import ExecutionCommandPayload


class TaskQueue(Protocol):
    async def publish(self, payload: ExecutionCommandPayload) -> None: ...

    async def consume(self, queue_name: str) -> ExecutionCommandPayload | None: ...
