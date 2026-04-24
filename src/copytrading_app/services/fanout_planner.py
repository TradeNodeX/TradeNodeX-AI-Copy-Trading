from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from copytrading_app.db.models import CopyTradeModel, ExecutionTaskModel, NormalizedSignalModel
from copytrading_app.domain.enums import CopyMode, Exchange, PositionSide, QueueName, SignalAction, ValidationStatus
from copytrading_app.domain.types import ExecutionCommandPayload, InstrumentConstraints
from copytrading_app.repositories.execution_repository import ExecutionRepository
from copytrading_app.repositories.follower_repository import resolve_effective_scale
from copytrading_app.services.queues.base import TaskQueue
from copytrading_app.services.scaling import ScalingService
from copytrading_app.services.instrument_catalog import InstrumentCatalogService


class FanoutPlanner:
    def __init__(
        self,
        execution_repository: ExecutionRepository,
        queue: TaskQueue,
        scaling_service: ScalingService,
        instrument_catalog: InstrumentCatalogService | None = None,
    ):
        self.execution_repository = execution_repository
        self.queue = queue
        self.scaling_service = scaling_service
        self.instrument_catalog = instrument_catalog

    async def plan(
        self,
        signal: NormalizedSignalModel,
        copy_trades: list[CopyTradeModel],
        constraints_by_exchange: dict[str, dict[str, InstrumentConstraints]],
    ) -> list[ExecutionCommandPayload]:
        planned: list[ExecutionCommandPayload] = []

        for copy_trade in copy_trades:
            follower = copy_trade.follower_account
            if follower is None:
                continue
            if not self._symbol_allowed(signal.symbol, copy_trade.signal_source.pairs_scope if copy_trade.signal_source else None):
                continue
            rule = next((item for item in follower.symbol_rules if item.symbol == signal.symbol), None)
            if rule is not None and not rule.enabled:
                continue
            if follower.validation_status == ValidationStatus.FAILED.value:
                continue

            target_symbol = signal.symbol
            constraints = constraints_by_exchange.get(follower.exchange, {}).get(signal.symbol)
            if self.instrument_catalog is not None:
                target_symbol, constraints = await self.instrument_catalog.resolve_symbol(
                    signal.source_exchange,
                    follower.exchange,
                    signal.symbol,
                )
            constraints = constraints or constraints_by_exchange.get(follower.exchange, {}).get(
                target_symbol,
                InstrumentConstraints(symbol=target_symbol),
            )
            copy_mode = CopyMode(copy_trade.copy_mode)
            scale_factor = resolve_effective_scale(
                Decimal(copy_trade.scale_factor if copy_mode == CopyMode.SCALE else Decimal("1")),
                rule,
            )
            target_quantity = self.scaling_service.scale_target_quantity(
                master_target_quantity=Decimal(signal.target_quantity),
                scale_factor=scale_factor,
                constraints=constraints,
                copy_mode=copy_mode,
            )
            delta_quantity = self.scaling_service.scale_delta_quantity(
                master_delta_quantity=Decimal(signal.delta_quantity),
                scale_factor=scale_factor,
                constraints=constraints,
                copy_mode=copy_mode,
            )
            if target_quantity == 0 and PositionSide(signal.target_side) != PositionSide.FLAT:
                continue
            if delta_quantity == 0 and SignalAction(signal.action) != SignalAction.SYNC_TO_TARGET_POSITION:
                continue

            queue_name = self._queue_for_action(SignalAction(signal.action))
            payload = ExecutionCommandPayload(
                task_id=str(uuid4()),
                signal_id=signal.id,
                signal_source_id=signal.signal_source_id,
                copy_trade_id=copy_trade.id,
                follower_account_id=follower.id,
                exchange=Exchange(follower.exchange),
                symbol=target_symbol,
                action=SignalAction(signal.action),
                target_side=PositionSide(signal.target_side),
                target_quantity=target_quantity,
                delta_quantity=delta_quantity,
                copy_mode=copy_mode,
                reduce_only=SignalAction(signal.action) in {SignalAction.CLOSE, SignalAction.REDUCE},
                queue_name=queue_name,
                message_group=f"{follower.id}:{signal.symbol}",
                idempotency_key=f"{signal.id}:{copy_trade.id}:{signal.action}:{signal.symbol}:{signal.version}",
                version=signal.version,
            )
            if await self.execution_repository.get_task_by_key(payload.idempotency_key):
                continue
            await self.execution_repository.create_task(payload)
            await self.queue.publish(payload)
            planned.append(payload)

        return planned

    def _queue_for_action(self, action: SignalAction) -> QueueName:
        if action in {SignalAction.CLOSE, SignalAction.REDUCE, SignalAction.FLIP}:
            return QueueName.RISK_PRIORITY
        return QueueName.NORMAL_EXEC

    def _symbol_allowed(self, symbol: str, pairs_scope: str | None) -> bool:
        scope = (pairs_scope or "ALL").strip()
        if not scope or scope.upper() == "ALL":
            return True
        normalized_symbol = symbol.replace("-", "").replace("_", "").upper()
        allowed_symbols = {
            item.strip().replace("-", "").replace("_", "").upper()
            for item in scope.replace(";", ",").replace("\n", ",").split(",")
            if item.strip()
        }
        return normalized_symbol in allowed_symbols

    def queue_payload_from_task(self, task: ExecutionTaskModel) -> ExecutionCommandPayload:
        return ExecutionCommandPayload(
            task_id=task.id,
            signal_id=task.signal_id,
            signal_source_id=task.signal_source_id,
            copy_trade_id=task.copy_trade_id,
            follower_account_id=task.follower_account_id,
            exchange=Exchange(task.exchange),
            symbol=task.symbol,
            action=SignalAction(task.action),
            target_side=PositionSide(task.target_side),
            target_quantity=Decimal(task.target_quantity),
            delta_quantity=Decimal(task.delta_quantity),
            copy_mode=CopyMode(task.copy_mode),
            reduce_only=task.reduce_only,
            queue_name=QueueName(task.queue_name),
            message_group=task.message_group,
            version=task.version,
            idempotency_key=task.idempotency_key,
        )
