from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from copytrading_app.domain.enums import (
    BuilderAction,
    CopyMode,
    CopyTradeStatus,
    Exchange,
    FollowerStatus,
    LogType,
    MarginMode,
    OrderType,
    PositionSide,
    QuantityMode,
    QueueName,
    RuntimeEnvironment,
    SignalAction,
    SignalSourceStatus,
    SignalStatus,
    ValidationStatus,
)


class FollowerCreateRequest(BaseModel):
    name: str
    exchange: Exchange
    environment: RuntimeEnvironment = RuntimeEnvironment.TESTNET
    account_group: str = "default"
    scale_factor: Decimal = Decimal("1")
    exact_copy_mode: bool = True
    leverage: int | None = None
    margin_mode: MarginMode = MarginMode.ISOLATED
    hedge_mode: bool = False
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None
    api_key_ciphertext: str | None = None
    api_secret_ciphertext: str | None = None
    api_passphrase_ciphertext: str | None = None
    kms_key_id: str | None = None


class FollowerResponse(BaseModel):
    id: str
    name: str
    exchange: Exchange
    environment: RuntimeEnvironment
    account_group: str
    status: FollowerStatus
    scale_factor: Decimal
    exact_copy_mode: bool
    leverage: int | None = None
    margin_mode: MarginMode
    hedge_mode: bool
    validation_status: ValidationStatus
    validation_message: str | None = None
    credential_status: ValidationStatus = ValidationStatus.PENDING
    permission_status: ValidationStatus = ValidationStatus.PENDING
    connectivity_status: ValidationStatus = ValidationStatus.PENDING
    trading_ready_status: ValidationStatus = ValidationStatus.PENDING
    validation_reasons: list[str] = Field(default_factory=list)
    last_validated_at: datetime | None = None


class FollowerUpdateRequest(BaseModel):
    name: str | None = None
    exchange: Exchange | None = None
    environment: RuntimeEnvironment | None = None
    account_group: str | None = None
    scale_factor: Decimal | None = None
    exact_copy_mode: bool | None = None
    leverage: int | None = None
    margin_mode: MarginMode | None = None
    hedge_mode: bool | None = None
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None
    kms_key_id: str | None = None


class SymbolRuleUpsertRequest(BaseModel):
    symbol: str
    enabled: bool = True
    scale_factor: Decimal | None = None
    max_leverage: int | None = None
    max_notional: Decimal | None = None
    min_notional_override: Decimal | None = None


class SymbolRuleResponse(BaseModel):
    id: str
    follower_account_id: str
    symbol: str
    enabled: bool
    scale_factor: Decimal | None = None
    max_leverage: int | None = None
    max_notional: Decimal | None = None
    min_notional_override: Decimal | None = None


class SignalSourceCreateRequest(BaseModel):
    name: str
    exchange: Exchange
    environment: RuntimeEnvironment = RuntimeEnvironment.TESTNET
    source_account: str
    description: str | None = None
    pairs_scope: str = "ALL"
    default_copy_mode: CopyMode = CopyMode.EXACT
    default_scale_factor: Decimal = Decimal("1")
    default_leverage: int | None = None
    margin_mode: MarginMode = MarginMode.ISOLATED
    hedge_mode: bool = False
    broadcast_trade_enabled: bool = False
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None
    kms_key_id: str | None = None


class SignalSourceUpdateRequest(BaseModel):
    name: str | None = None
    source_account: str | None = None
    description: str | None = None
    pairs_scope: str | None = None
    status: SignalSourceStatus | None = None
    default_copy_mode: CopyMode | None = None
    default_scale_factor: Decimal | None = None
    default_leverage: int | None = None
    margin_mode: MarginMode | None = None
    hedge_mode: bool | None = None
    broadcast_trade_enabled: bool | None = None
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None
    kms_key_id: str | None = None


class SignalSourceResponse(BaseModel):
    id: str
    name: str
    exchange: Exchange
    environment: RuntimeEnvironment
    source_account: str
    description: str | None
    pairs_scope: str
    status: SignalSourceStatus
    default_copy_mode: CopyMode
    default_scale_factor: Decimal
    default_leverage: int | None
    margin_mode: MarginMode
    hedge_mode: bool
    broadcast_trade_enabled: bool
    follower_count: int = 0
    invitation_count: int = 0
    follower_names: list[str] = Field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_message: str | None = None
    credential_status: ValidationStatus = ValidationStatus.PENDING
    permission_status: ValidationStatus = ValidationStatus.PENDING
    connectivity_status: ValidationStatus = ValidationStatus.PENDING
    trading_ready_status: ValidationStatus = ValidationStatus.PENDING
    validation_reasons: list[str] = Field(default_factory=list)
    last_validated_at: datetime | None = None
    stream_status: str = "OFFLINE"
    listener_status: str = "IDLE"
    last_stream_event_at: datetime | None = None


class ValidationResultResponse(BaseModel):
    ok: bool
    message: str | None = None


class CopyTradeCreateRequest(BaseModel):
    name: str
    signal_source_id: str
    follower_account_id: str
    copy_mode: CopyMode = CopyMode.EXACT
    scale_factor: Decimal = Decimal("1")
    override_leverage: int | None = None
    override_margin_mode: MarginMode | None = None
    override_hedge_mode: bool | None = None
    command_template: str | None = None
    notes: str | None = None
    enabled: bool = True


class CopyTradeUpdateRequest(BaseModel):
    name: str | None = None
    status: CopyTradeStatus | None = None
    enabled: bool | None = None
    copy_mode: CopyMode | None = None
    scale_factor: Decimal | None = None
    override_leverage: int | None = None
    override_margin_mode: MarginMode | None = None
    override_hedge_mode: bool | None = None
    command_template: str | None = None
    notes: str | None = None


class CopyTradeResponse(BaseModel):
    id: str
    name: str
    signal_source_id: str
    signal_name: str
    follower_account_id: str
    follower_name: str
    exchange: Exchange
    status: CopyTradeStatus
    enabled: bool
    copy_mode: CopyMode
    scale_factor: Decimal
    override_leverage: int | None = None
    override_margin_mode: MarginMode | None = None
    override_hedge_mode: bool | None = None
    command_template: str | None = None
    notes: str | None = None
    validation_status: ValidationStatus
    validation_message: str | None = None
    validation_reasons: list[str] = Field(default_factory=list)


class MasterEventIn(BaseModel):
    source_exchange: Exchange
    source_account: str
    source_order_or_fill_id: str
    symbol: str
    previous_position_qty: Decimal
    current_position_qty: Decimal
    price: Decimal | None = None
    event_time: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class SignalResponse(BaseModel):
    id: str
    signal_source_id: str
    source_exchange: Exchange
    source_account: str
    symbol: str
    action: SignalAction
    target_side: PositionSide
    target_quantity: Decimal
    delta_quantity: Decimal
    status: SignalStatus
    version: int
    execution_task_ids: list[str] = Field(default_factory=list)


class ExecutionAttemptResponse(BaseModel):
    id: str
    attempt_no: int
    status: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ExecutionTaskResponse(BaseModel):
    id: str
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
    queue_name: QueueName
    status: SignalStatus
    copy_mode: CopyMode
    reduce_only: bool
    error_message: str | None = None
    follower_name: str | None = None
    signal_name: str | None = None
    latest_attempt_status: str | None = None
    latest_attempt_error: str | None = None
    latest_exchange_response: dict[str, Any] | None = None
    queue_latency_ms: int | None = None
    exchange_stage: str | None = None
    attempts: list[ExecutionAttemptResponse] = Field(default_factory=list)


class ExecutionTimelineItemResponse(BaseModel):
    id: str
    timestamp: datetime
    source_type: str
    level: str
    title: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ExecutionAuditResponse(BaseModel):
    task: ExecutionTaskResponse
    related_logs: list[TradeLogResponse]
    timeline: list[ExecutionTimelineItemResponse]


class ReplayResponse(BaseModel):
    signal_id: str
    replayed_task_ids: list[str]
    queue_name: QueueName


class TradeLogResponse(BaseModel):
    id: str
    timestamp: datetime
    exchange: Exchange
    log_type: LogType
    log_key: str
    pnl: Decimal | None = None
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    linked_task_id: str | None = None
    linked_signal_id: str | None = None
    linked_follower_id: str | None = None
    linked_follower_name: str | None = None
    linked_copy_trade_id: str | None = None
    exchange_response: dict[str, Any] | None = None


class PositionSnapshotResponse(BaseModel):
    id: str
    account_id: str
    exchange: Exchange
    symbol: str
    quantity: Decimal
    entry_price: Decimal | None = None
    mark_price: Decimal | None = None
    leverage: int | None = None
    margin_mode: MarginMode | None = None
    source: str
    follower_name: str | None = None
    unrealized_pnl: Decimal | None = None
    notional_exposure: Decimal | None = None
    display_value: Decimal | None = None
    freshness: str = "fresh"
    captured_at: datetime


class TradeLogListResponse(BaseModel):
    items: list[TradeLogResponse]
    total: int
    page: int
    limit: int
    page_count: int


class DashboardMetricResponse(BaseModel):
    label: str
    value: Decimal | int | str
    tone: str = "neutral"
    note: str | None = None


class FxMetaResponse(BaseModel):
    display_currency: str
    source_currency: str = "USD"
    conversion_source: str
    converted: bool
    updated_at: datetime | None = None
    available_rates: list[str] = Field(default_factory=list)


class EquitySummaryResponse(BaseModel):
    total_notional: Decimal = Decimal("0")
    long_exposure: Decimal = Decimal("0")
    short_exposure: Decimal = Decimal("0")
    stale_snapshots: int = 0
    total_unrealized_pnl: Decimal = Decimal("0")


class WorkerStatusResponse(BaseModel):
    status: str = "OFFLINE"
    updated_at: datetime | None = None
    age_seconds: int | None = None


class DeleteResponse(BaseModel):
    deleted: bool
    id: str


class HealthResponse(BaseModel):
    checks: list[dict[str, Any]]


class CommandBuilderRequest(BaseModel):
    name: str
    exchange: Exchange
    environment: RuntimeEnvironment = RuntimeEnvironment.TESTNET
    product_type: str | None = None
    action: BuilderAction
    symbol: str
    order_type: OrderType = OrderType.MARKET
    quantity_mode: QuantityMode = QuantityMode.ABSOLUTE
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
    stop_loss_percent: Decimal | None = None
    delay_seconds: int | None = None
    use_dca: bool = False
    use_fixed_size: bool = False
    use_entire_balance: bool = False
    prevent_pyramiding: bool = False
    close_current_position: bool = False
    cancel_pending_orders: bool = False
    conditional_pyramiding: bool = False
    close_in_profit_only: bool = False
    cancel_all_orders: bool = False
    cancel_dca_orders: bool = False
    partial_close: bool = False
    close_by_limit_order: bool = False
    close_all: bool = False
    close_long: bool = False
    close_short: bool = False
    take_profit_steps: list[dict[str, Any]] = Field(default_factory=list)


class CommandPresetResponse(BaseModel):
    id: str
    name: str
    exchange: Exchange
    environment: RuntimeEnvironment
    account_id: str | None = None
    signal_source_id: str | None = None
    payload: dict[str, Any]
    raw_command: str
    created_at: datetime
    updated_at: datetime


class ManualExecutionResponse(BaseModel):
    accepted: bool
    preset_id: str | None = None
    result: dict[str, Any]


class DashboardResponse(BaseModel):
    signal_sources: list[SignalSourceResponse]
    copy_trades: list[CopyTradeResponse]
    followers: list[FollowerResponse]
    logs: list[TradeLogResponse]
    recent_executions: list[ExecutionTaskResponse]
    command_presets: list[CommandPresetResponse]
    runtime_metrics: list[DashboardMetricResponse] = Field(default_factory=list)
    performance_metrics: list[DashboardMetricResponse] = Field(default_factory=list)
    fx_meta: FxMetaResponse | None = None
    equity_summary: EquitySummaryResponse | None = None
    worker_status: WorkerStatusResponse | None = None
