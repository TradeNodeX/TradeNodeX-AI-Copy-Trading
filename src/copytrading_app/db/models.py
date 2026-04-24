from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from copytrading_app.db.base import Base
from copytrading_app.domain.enums import (
    AttemptStatus,
    CopyMode,
    CopyTradeStatus,
    Exchange,
    FollowerStatus,
    LogType,
    MarginMode,
    ReconciliationStatus,
    RuntimeEnvironment,
    SignalAction,
    SignalSourceStatus,
    SignalStatus,
    ValidationStatus,
)
from copytrading_app.domain.types import utc_now


class FollowerAccountModel(Base):
    __tablename__ = "follower_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120))
    exchange: Mapped[str] = mapped_column(String(32), default=Exchange.BINANCE.value)
    environment: Mapped[str] = mapped_column(String(16), default=RuntimeEnvironment.TESTNET.value)
    account_group: Mapped[str] = mapped_column(String(64), default="default")
    status: Mapped[str] = mapped_column(String(32), default=FollowerStatus.ACTIVE.value)
    scale_factor: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("1"))
    exact_copy_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    leverage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_mode: Mapped[str] = mapped_column(String(16), default=MarginMode.ISOLATED.value)
    hedge_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    validation_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    credential_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    permission_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    connectivity_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    trading_ready_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    validation_reasons: Mapped[list] = mapped_column(JSON, default=list)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_secret_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_passphrase_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    kms_key_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    symbol_rules: Mapped[list["AccountSymbolRuleModel"]] = relationship(
        back_populates="follower_account",
        cascade="all, delete-orphan",
    )
    execution_tasks: Mapped[list["ExecutionTaskModel"]] = relationship(back_populates="follower_account")
    copy_trades: Mapped[list["CopyTradeModel"]] = relationship(back_populates="follower_account")


class SignalSourceModel(Base):
    __tablename__ = "signal_sources"
    __table_args__ = (
        UniqueConstraint("exchange", "environment", "source_account", name="uq_signal_source_locator"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(140))
    exchange: Mapped[str] = mapped_column(String(32))
    environment: Mapped[str] = mapped_column(String(16), default=RuntimeEnvironment.TESTNET.value)
    source_account: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pairs_scope: Mapped[str] = mapped_column(String(64), default="ALL")
    status: Mapped[str] = mapped_column(String(32), default=SignalSourceStatus.ACTIVE.value)
    default_copy_mode: Mapped[str] = mapped_column(String(16), default=CopyMode.EXACT.value)
    default_scale_factor: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("1"))
    default_leverage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_mode: Mapped[str] = mapped_column(String(16), default=MarginMode.ISOLATED.value)
    hedge_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    broadcast_trade_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    validation_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    credential_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    permission_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    connectivity_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    trading_ready_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    validation_reasons: Mapped[list] = mapped_column(JSON, default=list)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stream_status: Mapped[str] = mapped_column(String(32), default="OFFLINE")
    listener_status: Mapped[str] = mapped_column(String(32), default="IDLE")
    last_stream_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_secret_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_passphrase_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    kms_key_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    copy_trades: Mapped[list["CopyTradeModel"]] = relationship(back_populates="signal_source")
    normalized_signals: Mapped[list["NormalizedSignalModel"]] = relationship(back_populates="signal_source")


class CopyTradeModel(Base):
    __tablename__ = "copy_trades"
    __table_args__ = (
        UniqueConstraint("signal_source_id", "follower_account_id", name="uq_copy_trade_signal_follower"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(140))
    signal_source_id: Mapped[str] = mapped_column(ForeignKey("signal_sources.id", ondelete="CASCADE"))
    follower_account_id: Mapped[str] = mapped_column(ForeignKey("follower_accounts.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), default=CopyTradeStatus.ACTIVE.value)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    copy_mode: Mapped[str] = mapped_column(String(16), default=CopyMode.EXACT.value)
    scale_factor: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("1"))
    override_leverage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    override_margin_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    override_hedge_mode: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    command_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), default=ValidationStatus.PENDING.value)
    validation_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_reasons: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    signal_source: Mapped[SignalSourceModel] = relationship(back_populates="copy_trades")
    follower_account: Mapped[FollowerAccountModel] = relationship(back_populates="copy_trades")
    execution_tasks: Mapped[list["ExecutionTaskModel"]] = relationship(back_populates="copy_trade")


class AccountSymbolRuleModel(Base):
    __tablename__ = "account_symbol_rules"
    __table_args__ = (UniqueConstraint("follower_account_id", "symbol", name="uq_rule_account_symbol"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    follower_account_id: Mapped[str] = mapped_column(ForeignKey("follower_accounts.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(32))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    scale_factor: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    max_leverage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_notional: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    min_notional_override: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    follower_account: Mapped[FollowerAccountModel] = relationship(back_populates="symbol_rules")


class MasterEventModel(Base):
    __tablename__ = "master_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    signal_source_id: Mapped[str | None] = mapped_column(ForeignKey("signal_sources.id", ondelete="SET NULL"), nullable=True)
    source_exchange: Mapped[str] = mapped_column(String(32))
    source_account: Mapped[str] = mapped_column(String(128))
    source_order_or_fill_id: Mapped[str] = mapped_column(String(128))
    symbol: Mapped[str] = mapped_column(String(32))
    previous_position_qty: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    current_position_qty: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    normalized_signal: Mapped["NormalizedSignalModel"] = relationship(back_populates="master_event", uselist=False)


class NormalizedSignalModel(Base):
    __tablename__ = "normalized_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    signal_source_id: Mapped[str] = mapped_column(ForeignKey("signal_sources.id", ondelete="CASCADE"))
    master_event_id: Mapped[str] = mapped_column(ForeignKey("master_events.id", ondelete="CASCADE"))
    source_exchange: Mapped[str] = mapped_column(String(32))
    source_account: Mapped[str] = mapped_column(String(128))
    symbol: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64), default=SignalAction.SYNC_TO_TARGET_POSITION.value)
    target_side: Mapped[str] = mapped_column(String(32))
    target_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    delta_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    status: Mapped[str] = mapped_column(String(32), default=SignalStatus.NORMALIZED.value)
    version: Mapped[int] = mapped_column(Integer, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    signal_source: Mapped[SignalSourceModel] = relationship(back_populates="normalized_signals")
    master_event: Mapped[MasterEventModel] = relationship(back_populates="normalized_signal")
    execution_tasks: Mapped[list["ExecutionTaskModel"]] = relationship(back_populates="signal")


class ExecutionTaskModel(Base):
    __tablename__ = "execution_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    signal_id: Mapped[str] = mapped_column(ForeignKey("normalized_signals.id", ondelete="CASCADE"))
    signal_source_id: Mapped[str] = mapped_column(ForeignKey("signal_sources.id", ondelete="CASCADE"))
    copy_trade_id: Mapped[str | None] = mapped_column(ForeignKey("copy_trades.id", ondelete="SET NULL"), nullable=True)
    follower_account_id: Mapped[str] = mapped_column(ForeignKey("follower_accounts.id", ondelete="CASCADE"))
    exchange: Mapped[str] = mapped_column(String(32))
    symbol: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64))
    target_side: Mapped[str] = mapped_column(String(32))
    target_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    delta_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    copy_mode: Mapped[str] = mapped_column(String(16), default=CopyMode.EXACT.value)
    reduce_only: Mapped[bool] = mapped_column(Boolean, default=False)
    queue_name: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default=SignalStatus.PLANNED.value)
    version: Mapped[int] = mapped_column(Integer, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    message_group: Mapped[str] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    signal: Mapped[NormalizedSignalModel] = relationship(back_populates="execution_tasks")
    follower_account: Mapped[FollowerAccountModel] = relationship(back_populates="execution_tasks")
    copy_trade: Mapped[CopyTradeModel | None] = relationship(back_populates="execution_tasks")
    attempts: Mapped[list["ExecutionAttemptModel"]] = relationship(
        back_populates="execution_task",
        cascade="all, delete-orphan",
    )


class ExecutionAttemptModel(Base):
    __tablename__ = "execution_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    execution_task_id: Mapped[str] = mapped_column(ForeignKey("execution_tasks.id", ondelete="CASCADE"))
    attempt_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default=AttemptStatus.PENDING.value)
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    execution_task: Mapped[ExecutionTaskModel] = relationship(back_populates="attempts")


class PositionSnapshotModel(Base):
    __tablename__ = "position_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(String(36))
    exchange: Mapped[str] = mapped_column(String(32))
    symbol: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    mark_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    notional_exposure: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    leverage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source: Mapped[str] = mapped_column(String(32))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ReconciliationResultModel(Base):
    __tablename__ = "reconciliation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    signal_id: Mapped[str] = mapped_column(ForeignKey("normalized_signals.id", ondelete="CASCADE"))
    follower_account_id: Mapped[str] = mapped_column(ForeignKey("follower_accounts.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(32))
    expected_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    actual_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    delta_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    status: Mapped[str] = mapped_column(String(32), default=ReconciliationStatus.MATCHED.value)
    action_taken: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CommandPresetModel(Base):
    __tablename__ = "command_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(140))
    exchange: Mapped[str] = mapped_column(String(32))
    environment: Mapped[str] = mapped_column(String(16), default=RuntimeEnvironment.TESTNET.value)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("follower_accounts.id", ondelete="SET NULL"), nullable=True)
    signal_source_id: Mapped[str | None] = mapped_column(ForeignKey("signal_sources.id", ondelete="SET NULL"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_command: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class TradeLogModel(Base):
    __tablename__ = "trade_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    exchange: Mapped[str] = mapped_column(String(32))
    log_type: Mapped[str] = mapped_column(String(32), default=LogType.INFO.value)
    log_key: Mapped[str] = mapped_column(String(64))
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class OperatorActionModel(Base):
    __tablename__ = "operator_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    operator: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
