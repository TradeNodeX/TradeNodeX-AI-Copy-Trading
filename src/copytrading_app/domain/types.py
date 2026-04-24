from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from copytrading_app.domain.enums import (
    BuilderAction,
    CopyMode,
    Exchange,
    MarginMode,
    OrderType,
    PositionSide,
    QuantityMode,
    QueueName,
    RuntimeEnvironment,
    SignalAction,
    SignalStatus,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InstrumentConstraints(BaseModel):
    symbol: str
    quantity_step: Decimal = Decimal("0.001")
    min_quantity: Decimal = Decimal("0.001")
    min_notional: Decimal = Decimal("5")
    max_leverage: int | None = None


class MasterEventPayload(BaseModel):
    source_exchange: Exchange
    source_account: str
    source_order_or_fill_id: str
    symbol: str
    previous_position_qty: Decimal
    current_position_qty: Decimal
    price: Decimal | None = None
    event_time: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)


class NormalizedSignalPayload(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    signal_source_id: str
    master_event_id: str
    source_exchange: Exchange
    source_account: str
    symbol: str
    action: SignalAction
    target_side: PositionSide
    target_quantity: Decimal
    delta_quantity: Decimal
    status: SignalStatus = SignalStatus.NORMALIZED
    version: int = 1
    idempotency_key: str


class ExecutionCommandPayload(BaseModel):
    task_id: str
    signal_id: str
    signal_source_id: str
    copy_trade_id: str | None = None
    follower_account_id: str
    exchange: Exchange
    symbol: str
    action: SignalAction
    target_side: PositionSide
    target_quantity: Decimal
    delta_quantity: Decimal
    copy_mode: CopyMode = CopyMode.EXACT
    reduce_only: bool = False
    queue_name: QueueName
    message_group: str
    version: int = 1
    idempotency_key: str


class OrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: Decimal
    reduce_only: bool = False
    position_side: PositionSide = PositionSide.FLAT
    order_type: OrderType = OrderType.MARKET
    client_order_id: str | None = None
    leverage: int | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None

    @field_validator("side")
    @classmethod
    def validate_side(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        return normalized


class OrderResult(BaseModel):
    accepted: bool
    external_order_id: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class PositionSnapshotPayload(BaseModel):
    account_id: str
    exchange: Exchange
    symbol: str
    quantity: Decimal
    entry_price: Decimal | None = None
    mark_price: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    notional_exposure: Decimal | None = None
    leverage: int | None = None
    margin_mode: str | None = None
    source: str
    captured_at: datetime = Field(default_factory=utc_now)


class HealthCheckResult(BaseModel):
    name: str
    ok: bool
    details: dict[str, Any] = Field(default_factory=dict)


class GeneratedCommand(BaseModel):
    exchange: Exchange
    environment: RuntimeEnvironment
    action: BuilderAction
    symbol: str
    order_type: OrderType
    quantity_mode: QuantityMode
    quantity_value: Decimal | None = None
    leverage: int | None = None
    margin_mode: MarginMode = MarginMode.ISOLATED
    hedge_mode: bool = False
    broadcast_trade: bool = False
    create_copy_trade_signal: bool = False
    signal_source_id: str | None = None
    account_id: str | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    take_profit_steps: list[dict[str, Any]] = Field(default_factory=list)
    raw_command: str
