from __future__ import annotations

from decimal import Decimal

from copytrading_app.domain.enums import Exchange, LogType, QueueName, RuntimeEnvironment, SignalStatus
from copytrading_app.domain.types import InstrumentConstraints, MasterEventPayload, utc_now
from copytrading_app.repositories.execution_repository import ExecutionRepository
from copytrading_app.repositories.follower_repository import FollowerRepository
from copytrading_app.repositories.signal_repository import SignalRepository
from copytrading_app.schemas.api import ReplayResponse
from copytrading_app.services.fanout_planner import FanoutPlanner
from copytrading_app.services.idempotency import IdempotencyStore
from copytrading_app.services.instrument_catalog import InstrumentCatalogService
from copytrading_app.services.signal_normalizer import SignalNormalizer


class Orchestrator:
    def __init__(
        self,
        signal_repository: SignalRepository,
        follower_repository: FollowerRepository,
        execution_repository: ExecutionRepository,
        signal_normalizer: SignalNormalizer,
        fanout_planner: FanoutPlanner,
        idempotency_store: IdempotencyStore,
        default_environment: RuntimeEnvironment,
        instrument_catalog: InstrumentCatalogService,
    ):
        self.signal_repository = signal_repository
        self.follower_repository = follower_repository
        self.execution_repository = execution_repository
        self.signal_normalizer = signal_normalizer
        self.fanout_planner = fanout_planner
        self.idempotency_store = idempotency_store
        self.default_environment = default_environment
        self.instrument_catalog = instrument_catalog

    async def handle_master_event(self, payload: MasterEventPayload):
        event_key = self._master_event_key(payload)
        if await self.idempotency_store.exists(event_key):
            existing = await self.signal_repository.get_signal_by_key(f"{event_key}:v1")
            return existing, []

        signal_source = await self.signal_repository.get_signal_source_by_locator(
            exchange=payload.source_exchange.value,
            environment=self.default_environment.value,
            source_account=payload.source_account,
        )
        if signal_source is None:
            raise ValueError(
                f"signal source not found for {payload.source_exchange.value}/{self.default_environment.value}/{payload.source_account}"
            )

        master_event = await self.signal_repository.get_master_event_by_key(event_key)
        if master_event is None:
            master_event = await self.signal_repository.create_master_event(payload, event_key, signal_source.id)

        signal_key = f"{event_key}:v1"
        signal = await self.signal_repository.get_signal_by_key(signal_key)
        if signal is None:
            normalized = self.signal_normalizer.build_signal(signal_source.id, master_event.id, payload, signal_key)
            signal = await self.signal_repository.create_signal(normalized)

        copy_trades = list(await self.execution_repository.list_active_copy_trades_for_source(signal_source.id))
        exchanges = {Exchange(item.follower_account.exchange) for item in copy_trades if item.follower_account is not None}
        constraints = await self.instrument_catalog.constraints_by_exchange(exchanges)
        planned = await self.fanout_planner.plan(signal, copy_trades, constraints)
        await self.execution_repository.add_trade_log(
            exchange=payload.source_exchange.value,
            log_type=LogType.SIGNAL,
            log_key=signal_source.name,
            message=f"Signal {signal.action} planned for {len(planned)} copy trade(s) on {signal.symbol}",
            details={"signal_id": signal.id, "signal_source_id": signal_source.id, "planned_count": len(planned)},
        )
        await self.signal_repository.update_status(signal.id, SignalStatus.DISPATCHED if planned else SignalStatus.SKIPPED)
        await self.idempotency_store.remember(event_key)
        return signal, planned

    async def replay_signal(self, signal_id: str, operator: str) -> ReplayResponse:
        signal = await self.signal_repository.get_signal(signal_id)
        if signal is None:
            raise ValueError(f"signal {signal_id} not found")

        replayed: list[str] = []
        for task in signal.execution_tasks:
            if task.status in {SignalStatus.FAILED.value, SignalStatus.SKIPPED.value}:
                task.status = SignalStatus.DISPATCHED.value
                task.queue_name = QueueName.RECOVERY.value
                await self.fanout_planner.queue.publish(self.fanout_planner.queue_payload_from_task(task))
                replayed.append(task.id)
        await self.follower_repository.record_operator_action(
            operator=operator,
            action="REPLAY_SIGNAL",
            target_type="signal",
            target_id=signal_id,
            details={"task_ids": replayed, "requested_at": utc_now().isoformat()},
        )
        await self.execution_repository.add_trade_log(
            exchange=signal.source_exchange,
            log_type=LogType.INFO,
            log_key=signal.source_account,
            message=f"Signal replay requested for {len(replayed)} task(s)",
            details={"signal_id": signal_id, "task_ids": replayed},
        )
        await self.signal_repository.update_status(signal_id, SignalStatus.DISPATCHED)
        return ReplayResponse(signal_id=signal_id, replayed_task_ids=replayed, queue_name=QueueName.RECOVERY)

    def _master_event_key(self, payload: MasterEventPayload) -> str:
        return ":".join(
            [
                payload.source_exchange.value,
                self.default_environment.value,
                payload.source_account,
                payload.source_order_or_fill_id,
                "1",
            ]
        )
