from __future__ import annotations

import asyncio

from copytrading_app.core.dependencies import AppContainer
from copytrading_app.domain.enums import QueueName
from copytrading_app.repositories.execution_repository import ExecutionRepository


async def run_executor_loop(container: AppContainer, queue_name: QueueName, poll_interval_seconds: float = 0.5) -> None:
    while True:
        payload = await container.queue.consume(queue_name.value)
        if payload is None:
            await asyncio.sleep(poll_interval_seconds)
            continue

        async with container.session_factory() as session:
            repository = ExecutionRepository(session)
            task = await repository.get_task(payload.task_id)
            if task is None:
                await asyncio.sleep(poll_interval_seconds)
                continue
            executor = container.account_executor(session)
            await executor.execute_task(task)
            await session.commit()

