from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from copytrading_app.db.models import (
    CommandPresetModel,
    CopyTradeModel,
    ExecutionTaskModel,
    MasterEventModel,
    NormalizedSignalModel,
    SignalSourceModel,
    TradeLogModel,
)
from copytrading_app.domain.enums import SignalStatus
from copytrading_app.domain.types import MasterEventPayload, NormalizedSignalPayload


class SignalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_master_event_by_key(self, idempotency_key: str) -> MasterEventModel | None:
        result = await self.session.execute(
            select(MasterEventModel).where(MasterEventModel.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def create_master_event(
        self,
        payload: MasterEventPayload,
        idempotency_key: str,
        signal_source_id: str | None,
    ) -> MasterEventModel:
        model = MasterEventModel(
            signal_source_id=signal_source_id,
            source_exchange=payload.source_exchange.value,
            source_account=payload.source_account,
            source_order_or_fill_id=payload.source_order_or_fill_id,
            symbol=payload.symbol,
            previous_position_qty=payload.previous_position_qty,
            current_position_qty=payload.current_position_qty,
            price=payload.price,
            event_time=payload.event_time,
            payload=payload.payload,
            idempotency_key=idempotency_key,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def get_signal_by_key(self, idempotency_key: str) -> NormalizedSignalModel | None:
        result = await self.session.execute(
            select(NormalizedSignalModel).where(NormalizedSignalModel.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def create_signal(self, payload: NormalizedSignalPayload) -> NormalizedSignalModel:
        model = NormalizedSignalModel(
            id=payload.id,
            signal_source_id=payload.signal_source_id,
            master_event_id=payload.master_event_id,
            source_exchange=payload.source_exchange.value,
            source_account=payload.source_account,
            symbol=payload.symbol,
            action=payload.action.value,
            target_side=payload.target_side.value,
            target_quantity=payload.target_quantity,
            delta_quantity=payload.delta_quantity,
            status=payload.status.value,
            version=payload.version,
            idempotency_key=payload.idempotency_key,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def get_signal(self, signal_id: str) -> NormalizedSignalModel | None:
        result = await self.session.execute(
            select(NormalizedSignalModel)
            .options(
                selectinload(NormalizedSignalModel.signal_source),
                selectinload(NormalizedSignalModel.execution_tasks).selectinload(ExecutionTaskModel.follower_account),
                selectinload(NormalizedSignalModel.execution_tasks).selectinload(ExecutionTaskModel.attempts),
                selectinload(NormalizedSignalModel.execution_tasks).selectinload(ExecutionTaskModel.copy_trade),
            )
            .where(NormalizedSignalModel.id == signal_id)
        )
        return result.scalar_one_or_none()

    async def list_signals(self, limit: int = 50) -> Sequence[NormalizedSignalModel]:
        result = await self.session.execute(
            select(NormalizedSignalModel)
            .options(selectinload(NormalizedSignalModel.execution_tasks))
            .order_by(desc(NormalizedSignalModel.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def update_status(self, signal_id: str, status: SignalStatus) -> None:
        model = await self.get_signal(signal_id)
        if model is None:
            raise ValueError(f"signal {signal_id} not found")
        model.status = status.value
        await self.session.flush()

    async def latest_signal_for_symbol(self, signal_source_id: str, symbol: str) -> NormalizedSignalModel | None:
        result = await self.session.execute(
            select(NormalizedSignalModel)
            .where(
                NormalizedSignalModel.signal_source_id == signal_source_id,
                NormalizedSignalModel.symbol == symbol,
            )
            .order_by(desc(NormalizedSignalModel.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_signal_source_by_locator(
        self,
        exchange: str,
        environment: str,
        source_account: str,
    ) -> SignalSourceModel | None:
        result = await self.session.execute(
            select(SignalSourceModel).where(
                SignalSourceModel.exchange == exchange,
                SignalSourceModel.environment == environment,
                SignalSourceModel.source_account == source_account,
            )
        )
        return result.scalar_one_or_none()

    async def create_signal_source(self, model: SignalSourceModel) -> SignalSourceModel:
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def list_signal_sources(self) -> Sequence[SignalSourceModel]:
        result = await self.session.execute(
            select(SignalSourceModel)
            .options(selectinload(SignalSourceModel.copy_trades).selectinload(CopyTradeModel.follower_account))
            .order_by(desc(SignalSourceModel.created_at))
        )
        return result.scalars().all()

    async def get_signal_source(self, signal_source_id: str) -> SignalSourceModel | None:
        result = await self.session.execute(
            select(SignalSourceModel)
            .options(selectinload(SignalSourceModel.copy_trades).selectinload(CopyTradeModel.follower_account))
            .where(SignalSourceModel.id == signal_source_id)
        )
        return result.scalar_one_or_none()

    async def delete_signal_source(self, signal_source_id: str) -> bool:
        model = await self.get_signal_source(signal_source_id)
        if model is None:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True

    async def count_copy_trades(self, signal_source_id: str) -> int:
        result = await self.session.execute(
            select(func.count(CopyTradeModel.id)).where(CopyTradeModel.signal_source_id == signal_source_id)
        )
        return int(result.scalar() or 0)

    async def update_signal_source_validation(
        self,
        signal_source_id: str,
        *,
        validation_status: str,
        validation_message: str | None,
        credential_status: str,
        permission_status: str,
        connectivity_status: str,
        trading_ready_status: str,
        validation_reasons: list[str],
    ) -> SignalSourceModel | None:
        model = await self.get_signal_source(signal_source_id)
        if model is None:
            return None
        model.validation_status = validation_status
        model.validation_message = validation_message
        model.credential_status = credential_status
        model.permission_status = permission_status
        model.connectivity_status = connectivity_status
        model.trading_ready_status = trading_ready_status
        model.validation_reasons = validation_reasons
        model.last_validated_at = model.updated_at
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_signal_source_listener_state(
        self,
        signal_source_id: str,
        *,
        stream_status: str | None = None,
        listener_status: str | None = None,
        last_stream_event_at=None,
        validation_message: str | None = None,
    ) -> SignalSourceModel | None:
        model = await self.get_signal_source(signal_source_id)
        if model is None:
            return None
        if stream_status is not None:
            model.stream_status = stream_status
        if listener_status is not None:
            model.listener_status = listener_status
        if last_stream_event_at is not None:
            model.last_stream_event_at = last_stream_event_at
        if validation_message is not None:
            model.validation_message = validation_message
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def list_command_presets(self) -> Sequence[CommandPresetModel]:
        result = await self.session.execute(select(CommandPresetModel).order_by(desc(CommandPresetModel.created_at)))
        return result.scalars().all()

    async def list_logs(self, limit: int = 200) -> Sequence[TradeLogModel]:
        result = await self.session.execute(select(TradeLogModel).order_by(desc(TradeLogModel.timestamp)).limit(limit))
        return result.scalars().all()

    async def list_logs_page(
        self,
        *,
        page: int,
        limit: int,
        exchange: str | None = None,
        log_type: str | None = None,
        search: str | None = None,
        linked_task_id: str | None = None,
        linked_signal_id: str | None = None,
        linked_follower_id: str | None = None,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
    ) -> tuple[Sequence[TradeLogModel], int]:
        filters = []
        if exchange:
            filters.append(TradeLogModel.exchange == exchange)
        if log_type:
            filters.append(TradeLogModel.log_type == log_type)
        if search:
            term = f"%{search}%"
            filters.append(or_(TradeLogModel.log_key.ilike(term), TradeLogModel.message.ilike(term)))
        if linked_task_id:
            filters.append(func.json_extract(TradeLogModel.details, "$.task_id") == linked_task_id)
        if linked_signal_id:
            filters.append(func.json_extract(TradeLogModel.details, "$.signal_id") == linked_signal_id)
        if linked_follower_id:
            filters.append(func.json_extract(TradeLogModel.details, "$.account_id") == linked_follower_id)

        query = select(TradeLogModel)
        count_query = select(func.count(TradeLogModel.id))
        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        sort_column = TradeLogModel.pnl if sort_by == "pnl" else TradeLogModel.timestamp
        ordering = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self.session.execute(query.order_by(ordering).offset((page - 1) * limit).limit(limit))
        count_result = await self.session.execute(count_query)
        return result.scalars().all(), int(count_result.scalar() or 0)
