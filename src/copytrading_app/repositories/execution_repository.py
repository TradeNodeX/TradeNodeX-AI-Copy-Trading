from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from copytrading_app.db.models import (
    CommandPresetModel,
    CopyTradeModel,
    ExecutionAttemptModel,
    ExecutionTaskModel,
    FollowerAccountModel,
    PositionSnapshotModel,
    ReconciliationResultModel,
    SignalSourceModel,
    TradeLogModel,
)
from copytrading_app.domain.enums import AttemptStatus, CopyTradeStatus, LogType, ReconciliationStatus, SignalStatus
from copytrading_app.domain.types import ExecutionCommandPayload, OrderResult, PositionSnapshotPayload, utc_now


class ExecutionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_task_by_key(self, idempotency_key: str) -> ExecutionTaskModel | None:
        result = await self.session.execute(
            select(ExecutionTaskModel).where(ExecutionTaskModel.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def create_task(self, payload: ExecutionCommandPayload) -> ExecutionTaskModel:
        model = ExecutionTaskModel(
            id=payload.task_id,
            signal_id=payload.signal_id,
            signal_source_id=payload.signal_source_id,
            copy_trade_id=payload.copy_trade_id,
            follower_account_id=payload.follower_account_id,
            exchange=payload.exchange.value,
            symbol=payload.symbol,
            action=payload.action.value,
            target_side=payload.target_side.value,
            target_quantity=payload.target_quantity,
            delta_quantity=payload.delta_quantity,
            copy_mode=payload.copy_mode.value,
            reduce_only=payload.reduce_only,
            queue_name=payload.queue_name.value,
            status=SignalStatus.DISPATCHED.value,
            version=payload.version,
            idempotency_key=payload.idempotency_key,
            message_group=payload.message_group,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def get_task(self, task_id: str) -> ExecutionTaskModel | None:
        result = await self.session.execute(
            select(ExecutionTaskModel)
            .options(
                selectinload(ExecutionTaskModel.attempts),
                selectinload(ExecutionTaskModel.follower_account),
                selectinload(ExecutionTaskModel.copy_trade).selectinload(CopyTradeModel.signal_source),
            )
            .where(ExecutionTaskModel.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks_for_follower(self, follower_id: str, signal_id: str | None = None) -> Sequence[ExecutionTaskModel]:
        query = (
            select(ExecutionTaskModel)
            .options(
                selectinload(ExecutionTaskModel.attempts),
                selectinload(ExecutionTaskModel.follower_account),
                selectinload(ExecutionTaskModel.copy_trade).selectinload(CopyTradeModel.signal_source),
            )
            .where(ExecutionTaskModel.follower_account_id == follower_id)
            .order_by(ExecutionTaskModel.created_at.desc())
        )
        if signal_id:
            query = query.where(ExecutionTaskModel.signal_id == signal_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_recent_tasks(self, limit: int = 50) -> Sequence[ExecutionTaskModel]:
        result = await self.session.execute(
            select(ExecutionTaskModel)
            .options(
                selectinload(ExecutionTaskModel.attempts),
                selectinload(ExecutionTaskModel.follower_account),
                selectinload(ExecutionTaskModel.copy_trade).selectinload(CopyTradeModel.signal_source),
            )
            .order_by(ExecutionTaskModel.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def create_attempt(self, task_id: str, request_payload: dict) -> ExecutionAttemptModel:
        count_result = await self.session.execute(
            select(func.count(ExecutionAttemptModel.id)).where(ExecutionAttemptModel.execution_task_id == task_id)
        )
        attempt_no = int(count_result.scalar() or 0) + 1
        attempt = ExecutionAttemptModel(
            execution_task_id=task_id,
            attempt_no=attempt_no,
            request_payload=request_payload,
            status=AttemptStatus.PENDING.value,
        )
        self.session.add(attempt)
        await self.session.flush()
        await self.session.refresh(attempt)
        return attempt

    async def finalize_attempt(self, attempt_id: str, result: OrderResult) -> ExecutionAttemptModel:
        attempt = await self.session.get(ExecutionAttemptModel, attempt_id)
        if attempt is None:
            raise ValueError(f"attempt {attempt_id} not found")

        attempt.status = AttemptStatus.ACKED.value if result.accepted else AttemptStatus.FAILED.value
        attempt.response_payload = result.raw_response
        attempt.error_message = result.error_message
        attempt.completed_at = utc_now()
        await self.session.flush()
        await self.session.refresh(attempt)
        return attempt

    async def update_task_status(self, task_id: str, status: SignalStatus, error_message: str | None = None) -> None:
        task = await self.session.get(ExecutionTaskModel, task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")
        task.status = status.value
        task.error_message = error_message
        await self.session.flush()

    async def save_position_snapshot(self, payload: PositionSnapshotPayload) -> PositionSnapshotModel:
        model = PositionSnapshotModel(
            account_id=payload.account_id,
            exchange=payload.exchange.value,
            symbol=payload.symbol,
            quantity=payload.quantity,
            entry_price=payload.entry_price,
            mark_price=payload.mark_price,
            unrealized_pnl=payload.unrealized_pnl,
            notional_exposure=payload.notional_exposure,
            leverage=payload.leverage,
            margin_mode=payload.margin_mode,
            source=payload.source,
            captured_at=payload.captured_at,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def list_recent_position_snapshots(self, limit: int = 100) -> Sequence[PositionSnapshotModel]:
        result = await self.session.execute(
            select(PositionSnapshotModel).order_by(PositionSnapshotModel.captured_at.desc()).limit(limit)
        )
        return result.scalars().all()

    async def record_reconciliation(
        self,
        signal_id: str,
        follower_account_id: str,
        symbol: str,
        expected_quantity,
        actual_quantity,
        delta_quantity,
        status: ReconciliationStatus,
        details: dict,
        action_taken: str | None = None,
    ) -> ReconciliationResultModel:
        model = ReconciliationResultModel(
            signal_id=signal_id,
            follower_account_id=follower_account_id,
            symbol=symbol,
            expected_quantity=expected_quantity,
            actual_quantity=actual_quantity,
            delta_quantity=delta_quantity,
            status=status.value,
            action_taken=action_taken,
            details=details,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def create_command_preset(self, model: CommandPresetModel) -> CommandPresetModel:
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def get_command_preset(self, preset_id: str) -> CommandPresetModel | None:
        return await self.session.get(CommandPresetModel, preset_id)

    async def add_trade_log(
        self,
        *,
        exchange: str,
        log_type: LogType,
        log_key: str,
        message: str,
        details: dict,
        pnl=None,
    ) -> TradeLogModel:
        model = TradeLogModel(
            exchange=exchange,
            log_type=log_type.value,
            log_key=log_key,
            pnl=pnl,
            message=message,
            details=details,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def get_copy_trade(self, copy_trade_id: str) -> CopyTradeModel | None:
        result = await self.session.execute(
            select(CopyTradeModel)
            .options(
                selectinload(CopyTradeModel.follower_account).selectinload(FollowerAccountModel.symbol_rules),
                selectinload(CopyTradeModel.signal_source),
            )
            .where(CopyTradeModel.id == copy_trade_id)
        )
        return result.scalar_one_or_none()

    async def list_copy_trades(self) -> Sequence[CopyTradeModel]:
        result = await self.session.execute(
            select(CopyTradeModel)
            .options(
                selectinload(CopyTradeModel.signal_source),
                selectinload(CopyTradeModel.follower_account).selectinload(FollowerAccountModel.symbol_rules),
            )
            .order_by(CopyTradeModel.created_at.desc())
        )
        return result.scalars().all()

    async def list_active_copy_trades_for_source(self, signal_source_id: str) -> Sequence[CopyTradeModel]:
        result = await self.session.execute(
            select(CopyTradeModel)
            .options(
                selectinload(CopyTradeModel.signal_source),
                selectinload(CopyTradeModel.follower_account).selectinload(FollowerAccountModel.symbol_rules),
            )
            .where(
                CopyTradeModel.signal_source_id == signal_source_id,
                CopyTradeModel.enabled.is_(True),
                CopyTradeModel.status == CopyTradeStatus.ACTIVE.value,
            )
        )
        return result.scalars().all()

    async def create_copy_trade(self, model: CopyTradeModel) -> CopyTradeModel:
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_copy_trade_status(
        self,
        copy_trade_id: str,
        *,
        status: CopyTradeStatus | None = None,
        enabled: bool | None = None,
        validation_status: str | None = None,
        validation_message: str | None = None,
        validation_reasons: list[str] | None = None,
    ) -> CopyTradeModel | None:
        model = await self.get_copy_trade(copy_trade_id)
        if model is None:
            return None
        if status is not None:
            model.status = status.value
        if enabled is not None:
            model.enabled = enabled
        if validation_status is not None:
            model.validation_status = validation_status
        if validation_message is not None:
            model.validation_message = validation_message
        if validation_reasons is not None:
            model.validation_reasons = validation_reasons
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_copy_trade_fields(self, copy_trade_id: str, updates: dict) -> CopyTradeModel | None:
        model = await self.get_copy_trade(copy_trade_id)
        if model is None:
            return None
        for key, value in updates.items():
            setattr(model, key, value)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_copy_trade(self, copy_trade_id: str) -> bool:
        model = await self.get_copy_trade(copy_trade_id)
        if model is None:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True

    async def update_signal_source(self, signal_source_id: str, updates: dict) -> SignalSourceModel | None:
        model = await self.session.get(SignalSourceModel, signal_source_id)
        if model is None:
            return None
        for key, value in updates.items():
            setattr(model, key, value)
        await self.session.flush()
        await self.session.refresh(model)
        return model
