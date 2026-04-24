from __future__ import annotations

import asyncio

from copytrading_app.core.dependencies import build_container
from copytrading_app.domain.enums import QueueName
from copytrading_app.services.private_streams import MasterStreamSupervisor
from copytrading_app.services.worker_status import write_worker_heartbeat
from copytrading_app.workers.executor import run_executor_loop


async def heartbeat_loop() -> None:
    while True:
        write_worker_heartbeat()
        await asyncio.sleep(5)


async def main() -> None:
    container = build_container()
    await container.init_models()
    supervisor = MasterStreamSupervisor(container)
    try:
        await asyncio.gather(
            run_executor_loop(container, QueueName.NORMAL_EXEC),
            run_executor_loop(container, QueueName.RISK_PRIORITY),
            run_executor_loop(container, QueueName.RECOVERY),
            supervisor.run_forever(),
            heartbeat_loop(),
        )
    finally:
        await container.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
