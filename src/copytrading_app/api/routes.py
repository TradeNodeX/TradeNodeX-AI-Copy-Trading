from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from copytrading_app.core.dependencies import AppContainer, get_container, get_session
from copytrading_app.db.models import CommandPresetModel, CopyTradeModel, SignalSourceModel
from copytrading_app.domain.enums import (
    BuilderAction,
    CopyTradeStatus,
    Exchange,
    FollowerStatus,
    LogType,
    OrderType,
    PositionSide,
    QueueName,
    SignalAction,
    SignalSourceStatus,
    SignalStatus,
    ValidationStatus,
)
from copytrading_app.domain.types import HealthCheckResult, OrderRequest
from copytrading_app.repositories.execution_repository import ExecutionRepository
from copytrading_app.repositories.follower_repository import FollowerRepository
from copytrading_app.repositories.signal_repository import SignalRepository
from copytrading_app.schemas.api import (
    CommandBuilderRequest,
    CommandPresetResponse,
    CopyTradeCreateRequest,
    CopyTradeResponse,
    CopyTradeUpdateRequest,
    DashboardMetricResponse,
    DashboardResponse,
    DeleteResponse,
    EquitySummaryResponse,
    ExecutionAuditResponse,
    ExecutionAttemptResponse,
    ExecutionTaskResponse,
    ExecutionTimelineItemResponse,
    FollowerCreateRequest,
    FollowerResponse,
    FollowerUpdateRequest,
    FxMetaResponse,
    HealthResponse,
    ManualExecutionResponse,
    MasterEventIn,
    PositionSnapshotResponse,
    ReplayResponse,
    SignalResponse,
    SignalSourceCreateRequest,
    SignalSourceResponse,
    SignalSourceUpdateRequest,
    SymbolRuleResponse,
    SymbolRuleUpsertRequest,
    TradeLogListResponse,
    TradeLogResponse,
    ValidationResultResponse,
    WorkerStatusResponse,
)
from copytrading_app.services.copy_trade_validation import validate_copy_trade
from copytrading_app.services.master_listener import MasterListenerService
from copytrading_app.services.worker_status import read_worker_status

router = APIRouter(prefix="/v1")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _okx_passphrase_missing(exchange: str, api_passphrase: str | None) -> bool:
    return exchange == Exchange.OKX.value and not (api_passphrase or "").strip()


def _validation_reasons(model) -> list[str]:
    reasons = list(getattr(model, "validation_reasons", []) or [])
    message = getattr(model, "validation_message", None)
    if message and message not in reasons:
        reasons.append(message)
    return reasons


def _queue_latency_ms(task) -> int:
    created_at = _ensure_utc(task.created_at)
    if created_at is None:
        return 0
    delta = _utc_now() - created_at
    return max(0, int(delta.total_seconds() * 1000))


def _execution_stage(task) -> str:
    if task.status in {SignalStatus.FILLED.value, SignalStatus.RECONCILED.value}:
        return "FILLED"
    if task.status == SignalStatus.ACKED.value:
        return "ACKED"
    if task.status == SignalStatus.FAILED.value:
        return "FAILED"
    latest_attempt = max(task.attempts, key=lambda attempt: attempt.attempt_no, default=None)
    if latest_attempt and latest_attempt.status == "ACKED":
        return "EXCHANGE_ACK"
    if latest_attempt and latest_attempt.status == "FAILED":
        return "ERROR"
    if task.status == SignalStatus.DISPATCHED.value:
        return "QUEUED"
    return task.status


def _extract_log_links(model) -> dict[str, object]:
    details = model.details or {}
    return {
        "linked_task_id": details.get("task_id"),
        "linked_signal_id": details.get("signal_id"),
        "linked_follower_id": details.get("account_id") or details.get("follower_id"),
        "linked_follower_name": details.get("account_name") or details.get("follower_name"),
        "linked_copy_trade_id": details.get("copy_trade_id"),
        "exchange_response": details.get("response"),
    }


def _position_freshness(captured_at: datetime) -> str:
    captured_at_utc = _ensure_utc(captured_at)
    if captured_at_utc is None:
        return "stale"
    age_seconds = (_utc_now() - captured_at_utc).total_seconds()
    if age_seconds >= 300:
        return "stale"
    if age_seconds >= 120:
        return "aging"
    return "fresh"


def follower_to_response(model) -> FollowerResponse:
    return FollowerResponse(
        id=model.id,
        name=model.name,
        exchange=Exchange(model.exchange),
        environment=model.environment,
        account_group=model.account_group,
        status=FollowerStatus(model.status),
        scale_factor=model.scale_factor,
        exact_copy_mode=model.exact_copy_mode,
        leverage=model.leverage,
        margin_mode=model.margin_mode,
        hedge_mode=model.hedge_mode,
        validation_status=ValidationStatus(model.validation_status),
        validation_message=model.validation_message,
        credential_status=ValidationStatus(model.credential_status),
        permission_status=ValidationStatus(model.permission_status),
        connectivity_status=ValidationStatus(model.connectivity_status),
        trading_ready_status=ValidationStatus(model.trading_ready_status),
        validation_reasons=_validation_reasons(model),
        last_validated_at=model.last_validated_at,
    )


def signal_source_to_response(model, follower_count: int, follower_names: list[str] | None = None) -> SignalSourceResponse:
    return SignalSourceResponse(
        id=model.id,
        name=model.name,
        exchange=Exchange(model.exchange),
        environment=model.environment,
        source_account=model.source_account,
        description=model.description,
        pairs_scope=model.pairs_scope,
        status=SignalSourceStatus(model.status),
        default_copy_mode=model.default_copy_mode,
        default_scale_factor=model.default_scale_factor,
        default_leverage=model.default_leverage,
        margin_mode=model.margin_mode,
        hedge_mode=model.hedge_mode,
        broadcast_trade_enabled=model.broadcast_trade_enabled,
        follower_count=follower_count,
        invitation_count=0,
        follower_names=follower_names or [],
        validation_status=ValidationStatus(model.validation_status),
        validation_message=model.validation_message,
        credential_status=ValidationStatus(model.credential_status),
        permission_status=ValidationStatus(model.permission_status),
        connectivity_status=ValidationStatus(model.connectivity_status),
        trading_ready_status=ValidationStatus(model.trading_ready_status),
        validation_reasons=_validation_reasons(model),
        last_validated_at=model.last_validated_at,
        stream_status=getattr(model, "stream_status", "OFFLINE"),
        listener_status=getattr(model, "listener_status", "IDLE"),
        last_stream_event_at=getattr(model, "last_stream_event_at", None),
    )


def copy_trade_to_response(model) -> CopyTradeResponse:
    return CopyTradeResponse(
        id=model.id,
        name=model.name,
        signal_source_id=model.signal_source_id,
        signal_name=model.signal_source.name if model.signal_source else "",
        follower_account_id=model.follower_account_id,
        follower_name=model.follower_account.name if model.follower_account else "",
        exchange=Exchange(model.follower_account.exchange if model.follower_account else model.signal_source.exchange),
        status=CopyTradeStatus(model.status),
        enabled=model.enabled,
        copy_mode=model.copy_mode,
        scale_factor=model.scale_factor,
        override_leverage=model.override_leverage,
        override_margin_mode=model.override_margin_mode,
        override_hedge_mode=model.override_hedge_mode,
        command_template=model.command_template,
        notes=model.notes,
        validation_status=ValidationStatus(model.validation_status),
        validation_message=model.validation_message,
        validation_reasons=_validation_reasons(model),
    )


def execution_task_to_response(task) -> ExecutionTaskResponse:
    latest_attempt = max(task.attempts, key=lambda item: item.attempt_no, default=None)
    return ExecutionTaskResponse(
        id=task.id,
        signal_id=task.signal_id,
        signal_source_id=task.signal_source_id,
        copy_trade_id=task.copy_trade_id,
        follower_account_id=task.follower_account_id,
        exchange=Exchange(task.exchange),
        symbol=task.symbol,
        action=SignalAction(task.action),
        target_side=PositionSide(task.target_side),
        target_quantity=task.target_quantity,
        delta_quantity=task.delta_quantity,
        queue_name=QueueName(task.queue_name),
        status=SignalStatus(task.status),
        copy_mode=task.copy_mode,
        reduce_only=task.reduce_only,
        error_message=task.error_message,
        follower_name=task.follower_account.name if task.follower_account else None,
        signal_name=task.copy_trade.signal_source.name if task.copy_trade and task.copy_trade.signal_source else None,
        latest_attempt_status=latest_attempt.status if latest_attempt else None,
        latest_attempt_error=latest_attempt.error_message if latest_attempt else None,
        latest_exchange_response=latest_attempt.response_payload if latest_attempt else None,
        queue_latency_ms=_queue_latency_ms(task),
        exchange_stage=_execution_stage(task),
        attempts=[
            ExecutionAttemptResponse(
                id=attempt.id,
                attempt_no=attempt.attempt_no,
                status=attempt.status,
                request_payload=attempt.request_payload,
                response_payload=attempt.response_payload,
                error_message=attempt.error_message,
                created_at=attempt.created_at,
                completed_at=attempt.completed_at,
            )
            for attempt in task.attempts
        ],
    )


def command_preset_to_response(model) -> CommandPresetResponse:
    return CommandPresetResponse(
        id=model.id,
        name=model.name,
        exchange=Exchange(model.exchange),
        environment=model.environment,
        account_id=model.account_id,
        signal_source_id=model.signal_source_id,
        payload=model.payload,
        raw_command=model.raw_command,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def trade_log_to_response(model) -> TradeLogResponse:
    links = _extract_log_links(model)
    return TradeLogResponse(
        id=model.id,
        timestamp=model.timestamp,
        exchange=Exchange(model.exchange),
        log_type=LogType(model.log_type),
        log_key=model.log_key,
        pnl=model.pnl,
        message=model.message,
        details=model.details,
        linked_task_id=links["linked_task_id"],
        linked_signal_id=links["linked_signal_id"],
        linked_follower_id=links["linked_follower_id"],
        linked_follower_name=links["linked_follower_name"],
        linked_copy_trade_id=links["linked_copy_trade_id"],
        exchange_response=links["exchange_response"],
    )


def position_snapshot_to_response(model, follower_name: str | None = None) -> PositionSnapshotResponse:
    return PositionSnapshotResponse(
        id=model.id,
        account_id=model.account_id,
        exchange=Exchange(model.exchange),
        symbol=model.symbol,
        quantity=model.quantity,
        entry_price=model.entry_price,
        mark_price=model.mark_price,
        leverage=model.leverage,
        margin_mode=model.margin_mode,
        source=model.source,
        follower_name=follower_name,
        unrealized_pnl=model.unrealized_pnl,
        notional_exposure=model.notional_exposure,
        freshness=_position_freshness(model.captured_at),
        captured_at=model.captured_at,
    )


def _timeline_level_from_log(log_type: LogType | str) -> str:
    normalized = log_type.value if hasattr(log_type, "value") else str(log_type)
    if normalized == LogType.ERROR.value:
        return "error"
    if normalized == LogType.WARNING.value:
        return "warning"
    if normalized == LogType.EXECUTION.value:
        return "success"
    if normalized == LogType.SIGNAL.value:
        return "signal"
    if normalized == LogType.RECONCILE.value:
        return "warning"
    if normalized == LogType.MANUAL.value:
        return "info"
    return "info"


def _source_type_from_log(model) -> str:
    details = model.details or {}
    if details.get("origin"):
        return str(details["origin"])
    if details.get("task_id"):
        return "TASK_LOG"
    if details.get("signal_id"):
        return "SIGNAL"
    return "SYSTEM"


def build_execution_timeline(task, related_logs) -> list[ExecutionTimelineItemResponse]:
    items: list[ExecutionTimelineItemResponse] = [
        ExecutionTimelineItemResponse(
            id=f"task-created:{task.id}",
            timestamp=task.created_at,
            source_type="TASK",
            level="info",
            title="Task dispatched",
            message=f"{task.action} {task.symbol} routed to {task.queue_name}.",
            payload={
                "task_id": task.id,
                "signal_id": task.signal_id,
                "copy_trade_id": task.copy_trade_id,
                "target_quantity": str(task.target_quantity),
                "delta_quantity": str(task.delta_quantity),
            },
        )
    ]

    for attempt in sorted(task.attempts, key=lambda item: item.attempt_no):
        items.append(
            ExecutionTimelineItemResponse(
                id=f"attempt-request:{attempt.id}",
                timestamp=attempt.created_at,
                source_type="ATTEMPT",
                level="info",
                title=f"Attempt #{attempt.attempt_no} submitted",
                message="Execution request built and sent to exchange client.",
                payload=attempt.request_payload,
            )
        )
        completed_at = attempt.completed_at or attempt.created_at
        level = "success" if attempt.status in {"ACKED", "FILLED"} else "error" if attempt.status == "FAILED" else "warning"
        items.append(
            ExecutionTimelineItemResponse(
                id=f"attempt-result:{attempt.id}",
                timestamp=completed_at,
                source_type="ATTEMPT_RESULT",
                level=level,
                title=f"Attempt #{attempt.attempt_no} {attempt.status.lower()}",
                message=attempt.error_message or "Exchange response captured.",
                payload=attempt.response_payload or {},
            )
        )

    if task.updated_at and task.updated_at != task.created_at:
        items.append(
            ExecutionTimelineItemResponse(
                id=f"task-status:{task.id}",
                timestamp=task.updated_at,
                source_type="TASK_STATUS",
                level="error" if task.status == SignalStatus.FAILED.value else "success" if task.status in {SignalStatus.ACKED.value, SignalStatus.FILLED.value, SignalStatus.RECONCILED.value} else "warning",
                title=f"Task status: {task.status}",
                message=task.error_message or "Task state updated.",
                payload={"status": task.status, "error_message": task.error_message},
            )
        )

    for log in related_logs:
        items.append(
            ExecutionTimelineItemResponse(
                id=f"log:{log.id}",
                timestamp=log.timestamp,
                source_type=_source_type_from_log(log),
                level=_timeline_level_from_log(log.log_type),
                title=f"{log.log_type} log",
                message=log.message,
                payload=log.details or {},
            )
        )

    return sorted(items, key=lambda item: item.timestamp, reverse=True)


def _sum_decimal(values) -> Decimal:
    total = Decimal("0")
    for value in values:
        if value is not None:
            total += Decimal(str(value))
    return total


async def build_fx_meta(container: AppContainer, currency: str) -> FxMetaResponse:
    return FxMetaResponse(**container.fx.metadata(currency))


async def build_equity_summary(container: AppContainer, snapshots, currency: str) -> EquitySummaryResponse:
    total_notional = _sum_decimal(abs(Decimal(str(item.notional_exposure or 0))) for item in snapshots)
    long_exposure = _sum_decimal(
        abs(Decimal(str(item.notional_exposure or 0))) for item in snapshots if Decimal(str(item.quantity or 0)) > 0
    )
    short_exposure = _sum_decimal(
        abs(Decimal(str(item.notional_exposure or 0))) for item in snapshots if Decimal(str(item.quantity or 0)) < 0
    )
    total_unrealized = _sum_decimal(item.unrealized_pnl for item in snapshots)
    converted_total = await container.fx.convert(total_notional, currency)
    converted_long = await container.fx.convert(long_exposure, currency)
    converted_short = await container.fx.convert(short_exposure, currency)
    converted_pnl = await container.fx.convert(total_unrealized, currency)
    return EquitySummaryResponse(
        total_notional=converted_total or total_notional,
        long_exposure=converted_long or long_exposure,
        short_exposure=converted_short or short_exposure,
        stale_snapshots=sum(1 for item in snapshots if _position_freshness(item.captured_at) == "stale"),
        total_unrealized_pnl=converted_pnl or total_unrealized,
    )


async def build_dashboard_metrics(container: AppContainer, dashboard: DashboardResponse, currency: str) -> tuple[list[DashboardMetricResponse], list[DashboardMetricResponse]]:
    execution_items = dashboard.recent_executions
    successful = sum(
        1
        for item in execution_items
        if item.status in {SignalStatus.ACKED, SignalStatus.FILLED, SignalStatus.RECONCILED}
    )
    fill_ratio = Decimal("0")
    if execution_items:
        fill_ratio = (Decimal(successful) / Decimal(len(execution_items)) * Decimal("100")).quantize(Decimal("0.01"))
    runtime = [
        DashboardMetricResponse(label="Signals", value=len(dashboard.signal_sources), tone="neutral", note="registered strategies"),
        DashboardMetricResponse(label="Active Copy Trades", value=len([item for item in dashboard.copy_trades if item.enabled]), tone="neutral", note="active routes"),
        DashboardMetricResponse(label="Followers", value=len(dashboard.followers), tone="neutral", note="API accounts"),
        DashboardMetricResponse(label="Live Logs", value=len(dashboard.logs), tone="neutral", note="realtime audit"),
    ]
    equity_summary = dashboard.equity_summary or EquitySummaryResponse()
    performance = [
        DashboardMetricResponse(label="Asset Value", value=str(equity_summary.total_notional), tone="neutral", note=f"display {currency}"),
        DashboardMetricResponse(
            label="Today PnL",
            value=str(equity_summary.total_unrealized_pnl),
            tone="good" if equity_summary.total_unrealized_pnl >= 0 else "danger",
            note="display converted",
        ),
        DashboardMetricResponse(
            label="Position Exposure",
            value=str((equity_summary.long_exposure + equity_summary.short_exposure).quantize(Decimal('0.01'))),
            tone="warning" if equity_summary.stale_snapshots else "neutral",
            note="long + short notional",
        ),
        DashboardMetricResponse(
            label="Fill Success Ratio",
            value=f"{fill_ratio}%",
            tone="good" if fill_ratio >= Decimal("85") else "warning" if fill_ratio >= Decimal("60") else "danger",
            note="recent execution outcomes",
        ),
    ]
    return runtime, performance


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    display_currency: str = Query(default="USD", min_length=3, max_length=3),
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> DashboardResponse:
    signal_repository = SignalRepository(session)
    execution_repository = ExecutionRepository(session)
    follower_repository = FollowerRepository(session)
    signal_sources = await signal_repository.list_signal_sources()
    copy_trades = await execution_repository.list_copy_trades()
    followers = await follower_repository.list()
    logs = await signal_repository.list_logs(limit=100)
    recent_tasks = await execution_repository.list_recent_tasks(limit=50)
    presets = await signal_repository.list_command_presets()
    snapshots = await execution_repository.list_recent_position_snapshots(limit=250)
    fx_meta = await build_fx_meta(container, display_currency)
    equity_summary = await build_equity_summary(container, snapshots, display_currency)
    response = DashboardResponse(
        signal_sources=[
            signal_source_to_response(
                source,
                follower_count=len(source.copy_trades),
                follower_names=[
                    copy_trade.follower_account.name
                    for copy_trade in source.copy_trades
                    if copy_trade.follower_account is not None
                ],
            )
            for source in signal_sources
        ],
        copy_trades=[copy_trade_to_response(item) for item in copy_trades],
        followers=[follower_to_response(item) for item in followers],
        logs=[trade_log_to_response(item) for item in logs],
        recent_executions=[execution_task_to_response(item) for item in recent_tasks],
        command_presets=[command_preset_to_response(item) for item in presets],
        fx_meta=fx_meta,
        equity_summary=equity_summary,
        worker_status=WorkerStatusResponse(**read_worker_status()),
    )
    runtime_metrics, performance_metrics = await build_dashboard_metrics(container, response, display_currency)
    response.runtime_metrics = runtime_metrics
    response.performance_metrics = performance_metrics
    return response


@router.get("/followers", response_model=list[FollowerResponse])
async def list_followers(session: AsyncSession = Depends(get_session)) -> list[FollowerResponse]:
    repository = FollowerRepository(session)
    return [follower_to_response(item) for item in await repository.list()]


@router.post("/followers", response_model=FollowerResponse, status_code=status.HTTP_201_CREATED)
async def create_follower(
    payload: FollowerCreateRequest,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> FollowerResponse:
    repository = FollowerRepository(session)
    api_key_ciphertext = await container.secret_cipher.encrypt(payload.api_key)
    api_secret_ciphertext = await container.secret_cipher.encrypt(payload.api_secret)
    api_passphrase_ciphertext = await container.secret_cipher.encrypt(payload.api_passphrase)
    model = await repository.create(
        payload,
        api_key_ciphertext=api_key_ciphertext,
        api_secret_ciphertext=api_secret_ciphertext,
        api_passphrase_ciphertext=api_passphrase_ciphertext,
    )
    await ExecutionRepository(session).add_trade_log(
        exchange=payload.exchange.value,
        log_type=LogType.INFO,
        log_key=model.name,
        message=f"Follower account {model.name} created.",
        details={"follower_id": model.id},
    )
    await session.commit()
    return follower_to_response(model)


@router.patch("/followers/{follower_id}", response_model=FollowerResponse)
async def update_follower(
    follower_id: str,
    payload: FollowerUpdateRequest,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> FollowerResponse:
    repository = FollowerRepository(session)
    updates = {k: (v.value if hasattr(v, "value") else v) for k, v in payload.model_dump(exclude_none=True).items()}
    if payload.api_key is not None:
        updates["api_key_ciphertext"] = await container.secret_cipher.encrypt(payload.api_key)
    if payload.api_secret is not None:
        updates["api_secret_ciphertext"] = await container.secret_cipher.encrypt(payload.api_secret)
    if payload.api_passphrase is not None:
        updates["api_passphrase_ciphertext"] = await container.secret_cipher.encrypt(payload.api_passphrase)
    updates.pop("api_key", None)
    updates.pop("api_secret", None)
    updates.pop("api_passphrase", None)
    model = await repository.update_fields(follower_id, updates)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="follower not found")
    await session.commit()
    return follower_to_response(model)


@router.post("/followers/{follower_id}/validate", response_model=FollowerResponse)
async def validate_follower(
    follower_id: str,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> FollowerResponse:
    follower_repository = FollowerRepository(session)
    follower = await follower_repository.get(follower_id)
    if follower is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="follower not found")
    api_key = await container.secret_cipher.decrypt(follower.api_key_ciphertext)
    api_secret = await container.secret_cipher.decrypt(follower.api_secret_ciphertext)
    api_passphrase = await container.secret_cipher.decrypt(follower.api_passphrase_ciphertext)
    if _okx_passphrase_missing(follower.exchange, api_passphrase):
        message = "OKX API passphrase is required for credential validation."
        await follower_repository.update_validation(
            follower_id,
            ValidationStatus.FAILED,
            message,
            credential_status=ValidationStatus.FAILED,
            permission_status=ValidationStatus.PENDING,
            connectivity_status=ValidationStatus.PENDING,
            trading_ready_status=ValidationStatus.FAILED,
            validation_reasons=[message],
        )
        await ExecutionRepository(session).add_trade_log(
            exchange=follower.exchange,
            log_type=LogType.ERROR,
            log_key=follower.name,
            message=f"Credential validation failed for {follower.name}: {message}",
            details={"follower_id": follower.id, "account_id": follower.id, "account_name": follower.name, "message": message, "origin": "API_VALIDATION"},
        )
        await session.commit()
        refreshed = await follower_repository.get(follower_id)
        return follower_to_response(refreshed)
    client = container.exchange_clients[Exchange(follower.exchange)]
    ok, message = await client.validate_credentials(follower, api_key, api_secret, api_passphrase)
    status_value = ValidationStatus.VERIFIED if ok else ValidationStatus.FAILED
    await follower_repository.update_validation(
        follower_id,
        status_value,
        message,
        credential_status=status_value,
        permission_status=status_value,
        connectivity_status=status_value,
        trading_ready_status=status_value,
        validation_reasons=[message] if message else [],
    )
    await ExecutionRepository(session).add_trade_log(
        exchange=follower.exchange,
        log_type=LogType.INFO if ok else LogType.ERROR,
        log_key=follower.name,
        message=f"Credential validation {'passed' if ok else 'failed'} for {follower.name}.",
        details={"follower_id": follower.id, "account_id": follower.id, "account_name": follower.name, "message": message, "origin": "API_VALIDATION"},
    )
    await session.commit()
    refreshed = await follower_repository.get(follower_id)
    return follower_to_response(refreshed)


@router.post("/followers/{follower_id}/rules", response_model=SymbolRuleResponse)
async def upsert_rule(
    follower_id: str,
    payload: SymbolRuleUpsertRequest,
    session: AsyncSession = Depends(get_session),
) -> SymbolRuleResponse:
    repository = FollowerRepository(session)
    try:
        model = await repository.upsert_rule(follower_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return SymbolRuleResponse(
        id=model.id,
        follower_account_id=model.follower_account_id,
        symbol=model.symbol,
        enabled=model.enabled,
        scale_factor=model.scale_factor,
        max_leverage=model.max_leverage,
        max_notional=model.max_notional,
        min_notional_override=model.min_notional_override,
    )


@router.post("/followers/{follower_id}/pause", response_model=FollowerResponse)
async def pause_follower(
    follower_id: str,
    x_operator: str = Header(default="system"),
    session: AsyncSession = Depends(get_session),
) -> FollowerResponse:
    repository = FollowerRepository(session)
    model = await repository.set_status(follower_id, FollowerStatus.PAUSED)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="follower not found")
    await repository.record_operator_action(x_operator, "PAUSE_FOLLOWER", "follower", follower_id, {})
    await session.commit()
    return follower_to_response(model)


@router.post("/followers/{follower_id}/resume", response_model=FollowerResponse)
async def resume_follower(
    follower_id: str,
    x_operator: str = Header(default="system"),
    session: AsyncSession = Depends(get_session),
) -> FollowerResponse:
    repository = FollowerRepository(session)
    model = await repository.set_status(follower_id, FollowerStatus.ACTIVE)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="follower not found")
    await repository.record_operator_action(x_operator, "RESUME_FOLLOWER", "follower", follower_id, {})
    await session.commit()
    return follower_to_response(model)


@router.delete("/followers/{follower_id}", response_model=DeleteResponse)
async def delete_follower(
    follower_id: str,
    session: AsyncSession = Depends(get_session),
) -> DeleteResponse:
    repository = FollowerRepository(session)
    deleted = await repository.delete(follower_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="follower not found")
    await session.commit()
    return DeleteResponse(deleted=True, id=follower_id)


@router.get("/signal-sources", response_model=list[SignalSourceResponse])
async def list_signal_sources(session: AsyncSession = Depends(get_session)) -> list[SignalSourceResponse]:
    repository = SignalRepository(session)
    sources = await repository.list_signal_sources()
    return [
        signal_source_to_response(
            item,
            len(item.copy_trades),
            [
                copy_trade.follower_account.name
                for copy_trade in item.copy_trades
                if copy_trade.follower_account is not None
            ],
        )
        for item in sources
    ]


@router.post("/signal-sources", response_model=SignalSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_signal_source(
    payload: SignalSourceCreateRequest,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> SignalSourceResponse:
    repository = SignalRepository(session)
    api_key_ciphertext = await container.secret_cipher.encrypt(payload.api_key)
    api_secret_ciphertext = await container.secret_cipher.encrypt(payload.api_secret)
    api_passphrase_ciphertext = await container.secret_cipher.encrypt(payload.api_passphrase)
    model = SignalSourceModel(
        name=payload.name,
        exchange=payload.exchange.value,
        environment=payload.environment.value,
        source_account=payload.source_account,
        description=payload.description,
        pairs_scope=payload.pairs_scope,
        default_copy_mode=payload.default_copy_mode.value,
        default_scale_factor=payload.default_scale_factor,
        default_leverage=payload.default_leverage,
        margin_mode=payload.margin_mode.value,
        hedge_mode=payload.hedge_mode,
        broadcast_trade_enabled=payload.broadcast_trade_enabled,
        api_key_ciphertext=api_key_ciphertext,
        api_secret_ciphertext=api_secret_ciphertext,
        api_passphrase_ciphertext=api_passphrase_ciphertext,
        kms_key_id=payload.kms_key_id,
    )
    await repository.create_signal_source(model)
    await ExecutionRepository(session).add_trade_log(
        exchange=payload.exchange.value,
        log_type=LogType.INFO,
        log_key=payload.name,
        message=f"Signal source {payload.name} created.",
        details={"signal_source_id": model.id},
    )
    await session.commit()
    return signal_source_to_response(model, 0, [])


@router.patch("/signal-sources/{signal_source_id}", response_model=SignalSourceResponse)
async def update_signal_source(
    signal_source_id: str,
    payload: SignalSourceUpdateRequest,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> SignalSourceResponse:
    repository = ExecutionRepository(session)
    signal_repository = SignalRepository(session)
    updates = {k: (v.value if hasattr(v, "value") else v) for k, v in payload.model_dump(exclude_none=True).items()}
    if payload.api_key is not None:
        updates["api_key_ciphertext"] = await container.secret_cipher.encrypt(payload.api_key)
    if payload.api_secret is not None:
        updates["api_secret_ciphertext"] = await container.secret_cipher.encrypt(payload.api_secret)
    if payload.api_passphrase is not None:
        updates["api_passphrase_ciphertext"] = await container.secret_cipher.encrypt(payload.api_passphrase)
    updates.pop("api_key", None)
    updates.pop("api_secret", None)
    updates.pop("api_passphrase", None)
    model = await repository.update_signal_source(signal_source_id, updates)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="signal source not found")
    await session.commit()
    refreshed = await signal_repository.get_signal_source(signal_source_id)
    return signal_source_to_response(
        refreshed,
        follower_count=len(refreshed.copy_trades),
        follower_names=[
            copy_trade.follower_account.name
            for copy_trade in refreshed.copy_trades
            if copy_trade.follower_account is not None
        ],
    )


@router.post("/signal-sources/{signal_source_id}/validate", response_model=ValidationResultResponse)
async def validate_signal_source(
    signal_source_id: str,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> ValidationResultResponse:
    repository = SignalRepository(session)
    source = await repository.get_signal_source(signal_source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="signal source not found")

    api_key = await container.secret_cipher.decrypt(source.api_key_ciphertext)
    api_secret = await container.secret_cipher.decrypt(source.api_secret_ciphertext)
    api_passphrase = await container.secret_cipher.decrypt(source.api_passphrase_ciphertext)
    if _okx_passphrase_missing(source.exchange, api_passphrase):
        message = "OKX API passphrase is required for signal source validation."
        await repository.update_signal_source_validation(
            signal_source_id,
            validation_status=ValidationStatus.FAILED.value,
            validation_message=message,
            credential_status=ValidationStatus.FAILED.value,
            permission_status=ValidationStatus.PENDING.value,
            connectivity_status=ValidationStatus.PENDING.value,
            trading_ready_status=ValidationStatus.FAILED.value,
            validation_reasons=[message],
        )
        await ExecutionRepository(session).add_trade_log(
            exchange=source.exchange,
            log_type=LogType.ERROR,
            log_key=source.name,
            message=f"Signal source credential validation failed for {source.name}: {message}",
            details={"signal_source_id": source.id, "message": message, "origin": "SIGNAL_VALIDATION"},
        )
        await session.commit()
        return ValidationResultResponse(ok=False, message=message)
    client = container.exchange_clients[Exchange(source.exchange)]
    ok, message = await client.validate_credentials(source, api_key, api_secret, api_passphrase)
    status_value = ValidationStatus.VERIFIED.value if ok else ValidationStatus.FAILED.value
    reasons = [message] if message else []
    await repository.update_signal_source_validation(
        signal_source_id,
        validation_status=status_value,
        validation_message=message,
        credential_status=status_value,
        permission_status=status_value,
        connectivity_status=status_value,
        trading_ready_status=status_value,
        validation_reasons=reasons,
    )
    await ExecutionRepository(session).add_trade_log(
        exchange=source.exchange,
        log_type=LogType.INFO if ok else LogType.ERROR,
        log_key=source.name,
        message=f"Signal source credential validation {'passed' if ok else 'failed'} for {source.name}.",
        details={"signal_source_id": source.id, "message": message, "origin": "SIGNAL_VALIDATION"},
    )
    await session.commit()
    return ValidationResultResponse(ok=ok, message=message)


@router.delete("/signal-sources/{signal_source_id}", response_model=DeleteResponse)
async def delete_signal_source(
    signal_source_id: str,
    session: AsyncSession = Depends(get_session),
) -> DeleteResponse:
    repository = SignalRepository(session)
    deleted = await repository.delete_signal_source(signal_source_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="signal source not found")
    await session.commit()
    return DeleteResponse(deleted=True, id=signal_source_id)


@router.get("/copy-trades", response_model=list[CopyTradeResponse])
async def list_copy_trades(session: AsyncSession = Depends(get_session)) -> list[CopyTradeResponse]:
    repository = ExecutionRepository(session)
    return [copy_trade_to_response(item) for item in await repository.list_copy_trades()]


@router.post("/copy-trades", response_model=CopyTradeResponse, status_code=status.HTTP_201_CREATED)
async def create_copy_trade(
    payload: CopyTradeCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> CopyTradeResponse:
    execution_repository = ExecutionRepository(session)
    signal_repository = SignalRepository(session)
    follower_repository = FollowerRepository(session)
    signal_source = await signal_repository.get_signal_source(payload.signal_source_id)
    follower = await follower_repository.get(payload.follower_account_id)
    if signal_source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="signal source not found")
    if follower is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="follower not found")

    model = CopyTradeModel(
        name=payload.name,
        signal_source_id=payload.signal_source_id,
        follower_account_id=payload.follower_account_id,
        status=CopyTradeStatus.ACTIVE.value if payload.enabled else CopyTradeStatus.PAUSED.value,
        enabled=payload.enabled,
        copy_mode=payload.copy_mode.value,
        scale_factor=payload.scale_factor,
        override_leverage=payload.override_leverage,
        override_margin_mode=payload.override_margin_mode.value if payload.override_margin_mode else None,
        override_hedge_mode=payload.override_hedge_mode,
        command_template=payload.command_template,
        notes=payload.notes,
    )
    validation_status, validation_message, validation_reasons = validate_copy_trade(model, follower, signal_source)
    model.validation_status = validation_status.value
    model.validation_message = validation_message
    model.validation_reasons = validation_reasons
    await execution_repository.create_copy_trade(model)
    await execution_repository.add_trade_log(
        exchange=signal_source.exchange,
        log_type=LogType.INFO if validation_status != ValidationStatus.FAILED else LogType.WARNING,
        log_key=payload.name,
        message=f"Copy trade {payload.name} created in {payload.copy_mode.value} mode.",
        details={"copy_trade_id": model.id, "validation_message": validation_message, "validation_reasons": validation_reasons},
    )
    await session.commit()
    created = await execution_repository.get_copy_trade(model.id)
    return copy_trade_to_response(created)


@router.patch("/copy-trades/{copy_trade_id}", response_model=CopyTradeResponse)
async def update_copy_trade(
    copy_trade_id: str,
    payload: CopyTradeUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> CopyTradeResponse:
    execution_repository = ExecutionRepository(session)
    model = await execution_repository.get_copy_trade(copy_trade_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="copy trade not found")
    updates = {k: (v.value if hasattr(v, "value") else v) for k, v in payload.model_dump(exclude_none=True).items()}
    updated = await execution_repository.update_copy_trade_fields(copy_trade_id, updates)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="copy trade not found")
    if updated.follower_account and updated.signal_source:
        validation_status, validation_message, validation_reasons = validate_copy_trade(updated, updated.follower_account, updated.signal_source)
        await execution_repository.update_copy_trade_status(
            copy_trade_id,
            validation_status=validation_status.value,
            validation_message=validation_message,
            validation_reasons=validation_reasons,
        )
    await session.commit()
    refreshed = await execution_repository.get_copy_trade(copy_trade_id)
    return copy_trade_to_response(refreshed)


@router.get("/copy-trades/{copy_trade_id}", response_model=CopyTradeResponse)
async def get_copy_trade(copy_trade_id: str, session: AsyncSession = Depends(get_session)) -> CopyTradeResponse:
    execution_repository = ExecutionRepository(session)
    model = await execution_repository.get_copy_trade(copy_trade_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="copy trade not found")
    return copy_trade_to_response(model)


@router.delete("/copy-trades/{copy_trade_id}", response_model=DeleteResponse)
async def delete_copy_trade(copy_trade_id: str, session: AsyncSession = Depends(get_session)) -> DeleteResponse:
    execution_repository = ExecutionRepository(session)
    deleted = await execution_repository.delete_copy_trade(copy_trade_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="copy trade not found")
    await session.commit()
    return DeleteResponse(deleted=True, id=copy_trade_id)


@router.get("/followers/{follower_id}/executions", response_model=list[ExecutionTaskResponse])
async def get_follower_executions(
    follower_id: str,
    signal_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[ExecutionTaskResponse]:
    repository = ExecutionRepository(session)
    tasks = await repository.list_tasks_for_follower(follower_id, signal_id)
    return [execution_task_to_response(task) for task in tasks]


@router.get("/executions/{task_id}/audit", response_model=ExecutionAuditResponse)
async def get_execution_audit(
    task_id: str,
    session: AsyncSession = Depends(get_session),
) -> ExecutionAuditResponse:
    execution_repository = ExecutionRepository(session)
    signal_repository = SignalRepository(session)
    task = await execution_repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execution task not found")

    recent_logs = await signal_repository.list_logs(limit=250)
    follower_name = task.follower_account.name if task.follower_account else None
    related_logs = []
    for log in recent_logs:
        details = log.details or {}
        if details.get("task_id") == task.id:
            related_logs.append(log)
            continue
        if details.get("signal_id") == task.signal_id:
            related_logs.append(log)
            continue
        if (
            follower_name
            and log.log_key == follower_name
            and details.get("symbol") == task.symbol
            and log.timestamp >= task.created_at
        ):
            related_logs.append(log)

    related_logs = sorted(related_logs, key=lambda item: item.timestamp, reverse=True)[:40]
    return ExecutionAuditResponse(
        task=execution_task_to_response(task),
        related_logs=[trade_log_to_response(item) for item in related_logs],
        timeline=build_execution_timeline(task, related_logs),
    )


@router.post("/internal/master-events", response_model=SignalResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_master_event(
    payload: MasterEventIn,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> SignalResponse:
    service = MasterListenerService(container.orchestrator(session))
    try:
        signal, planned = await service.ingest_event(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return SignalResponse(
        id=signal.id,
        signal_source_id=signal.signal_source_id,
        source_exchange=Exchange(signal.source_exchange),
        source_account=signal.source_account,
        symbol=signal.symbol,
        action=SignalAction(signal.action),
        target_side=PositionSide(signal.target_side),
        target_quantity=signal.target_quantity,
        delta_quantity=signal.delta_quantity,
        status=SignalStatus(signal.status),
        version=signal.version,
        execution_task_ids=[item.task_id for item in planned],
    )


@router.get("/signals/{signal_id}", response_model=SignalResponse)
async def get_signal(signal_id: str, session: AsyncSession = Depends(get_session)) -> SignalResponse:
    repository = SignalRepository(session)
    signal = await repository.get_signal(signal_id)
    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="signal not found")
    return SignalResponse(
        id=signal.id,
        signal_source_id=signal.signal_source_id,
        source_exchange=Exchange(signal.source_exchange),
        source_account=signal.source_account,
        symbol=signal.symbol,
        action=SignalAction(signal.action),
        target_side=PositionSide(signal.target_side),
        target_quantity=signal.target_quantity,
        delta_quantity=signal.delta_quantity,
        status=SignalStatus(signal.status),
        version=signal.version,
        execution_task_ids=[task.id for task in signal.execution_tasks],
    )


@router.post("/signals/{signal_id}/replay", response_model=ReplayResponse)
async def replay_signal(
    signal_id: str,
    x_operator: str = Header(default="system"),
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> ReplayResponse:
    try:
        replay = await container.orchestrator(session).replay_signal(signal_id, x_operator)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return replay


@router.get("/logs", response_model=list[TradeLogResponse])
async def list_logs(
    limit: int = Query(default=200, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[TradeLogResponse]:
    repository = SignalRepository(session)
    return [trade_log_to_response(item) for item in await repository.list_logs(limit=limit)]


@router.get("/logs/query", response_model=TradeLogListResponse)
async def list_logs_page(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=200),
    exchange: Exchange | None = Query(default=None),
    log_type: LogType | None = Query(default=None),
    search: str | None = Query(default=None),
    linked_task_id: str | None = Query(default=None),
    linked_signal_id: str | None = Query(default=None),
    linked_follower_id: str | None = Query(default=None),
    sort_by: str = Query(default="timestamp", pattern="^(timestamp|pnl)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
) -> TradeLogListResponse:
    repository = SignalRepository(session)
    items, total = await repository.list_logs_page(
        page=page,
        limit=limit,
        exchange=exchange.value if exchange else None,
        log_type=log_type.value if log_type else None,
        search=search,
        linked_task_id=linked_task_id,
        linked_signal_id=linked_signal_id,
        linked_follower_id=linked_follower_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    page_count = max(1, (total + limit - 1) // limit)
    return TradeLogListResponse(
        items=[trade_log_to_response(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        page_count=page_count,
    )


@router.get("/instruments", response_model=list[dict])
async def instruments(
    exchange: Exchange,
    container: AppContainer = Depends(get_container),
) -> list[dict]:
    client = container.exchange_clients[exchange]
    instruments = await client.fetch_instruments()
    return instruments


@router.post("/commands/generate", response_model=CommandPresetResponse)
async def generate_command(
    payload: CommandBuilderRequest,
    session: AsyncSession = Depends(get_session),
    container: AppContainer = Depends(get_container),
) -> CommandPresetResponse:
    generated = container.command_builder.build(payload)
    model = CommandPresetModel(
        name=payload.name,
        exchange=payload.exchange.value,
        environment=payload.environment.value,
        account_id=payload.account_id,
        signal_source_id=payload.signal_source_id,
        payload=payload.model_dump(mode="json"),
        raw_command=generated.raw_command,
    )
    await ExecutionRepository(session).create_command_preset(model)
    await session.commit()
    return command_preset_to_response(model)


@router.get("/command-presets", response_model=list[CommandPresetResponse])
async def list_command_presets(session: AsyncSession = Depends(get_session)) -> list[CommandPresetResponse]:
    repository = SignalRepository(session)
    return [command_preset_to_response(item) for item in await repository.list_command_presets()]


async def _place_attached_orders(
    *,
    client,
    follower,
    payload: CommandBuilderRequest,
    api_key: str | None,
    api_secret: str | None,
    api_passphrase: str | None,
) -> list[dict]:
    if payload.action not in {BuilderAction.BUY, BuilderAction.SELL} or payload.quantity_value is None:
        return []

    attached: list[dict] = []
    opposite_side = "SELL" if payload.action == BuilderAction.BUY else "BUY"
    position_side = PositionSide.LONG if payload.action == BuilderAction.BUY else PositionSide.SHORT

    snapshot = None
    if payload.stop_loss_percent is not None or payload.take_profit_steps:
        try:
            snapshot = await client.fetch_position(follower, payload.symbol, api_key, api_secret, api_passphrase)
        except Exception as exc:  # pragma: no cover - exchange-specific network failures are reported to audit.
            attached.append({"type": "POSITION_REFERENCE", "accepted": False, "error": str(exc)})

    stop_trigger = payload.stop_price if payload.stop_price is not None and payload.order_type != OrderType.STOP_MARKET else None
    if payload.stop_loss_percent is not None and snapshot is not None:
        reference_price = snapshot.entry_price or snapshot.mark_price
        if reference_price is not None:
            pct = payload.stop_loss_percent / Decimal("100")
            stop_trigger = reference_price * (Decimal("1") - pct if payload.action == BuilderAction.BUY else Decimal("1") + pct)

    if stop_trigger is not None:
        stop_result = await client.place_order(
            follower,
            OrderRequest(
                symbol=payload.symbol,
                side=opposite_side,
                quantity=payload.quantity_value,
                reduce_only=True,
                position_side=position_side,
                order_type=OrderType.STOP_MARKET,
                stop_price=stop_trigger,
                leverage=payload.leverage or follower.leverage,
            ),
            api_key,
            api_secret,
            api_passphrase,
        )
        attached.append({"type": "STOP_LOSS", "trigger_price": str(stop_trigger), **stop_result.model_dump(mode="json")})

    if snapshot is not None and payload.take_profit_steps:
        reference_price = snapshot.entry_price or snapshot.mark_price
        if reference_price is None:
            attached.append({"type": "TAKE_PROFIT", "accepted": False, "error": "No entry or mark price available for take-profit orchestration."})
        else:
            for index, step in enumerate(payload.take_profit_steps, start=1):
                amount = Decimal(str(step.get("amount", "0") or "0"))
                take_profit_percent = Decimal(str(step.get("takeProfitPercent", "0") or "0"))
                if amount <= 0 or take_profit_percent <= 0:
                    continue
                take_profit_price = reference_price * (
                    Decimal("1") + take_profit_percent / Decimal("100")
                    if payload.action == BuilderAction.BUY
                    else Decimal("1") - take_profit_percent / Decimal("100")
                )
                take_profit_quantity = payload.quantity_value * amount / Decimal("100") if amount <= 100 else amount
                take_profit_result = await client.place_order(
                    follower,
                    OrderRequest(
                        symbol=payload.symbol,
                        side=opposite_side,
                        quantity=take_profit_quantity,
                        reduce_only=True,
                        position_side=position_side,
                        order_type=OrderType.LIMIT,
                        limit_price=take_profit_price,
                        leverage=payload.leverage or follower.leverage,
                    ),
                    api_key,
                    api_secret,
                    api_passphrase,
                )
                attached.append(
                    {
                        "type": "TAKE_PROFIT",
                        "step": index,
                        "limit_price": str(take_profit_price),
                        "quantity": str(take_profit_quantity),
                        **take_profit_result.model_dump(mode="json"),
                    }
                )

    if payload.use_dca:
        attached.append({"type": "DCA", "accepted": False, "error": "DCA requires explicit ladder step prices before live orchestration."})
    return attached


@router.post("/commands/execute", response_model=ManualExecutionResponse)
async def execute_command(
    payload: CommandBuilderRequest,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> ManualExecutionResponse:
    if not payload.account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account_id is required for execution")
    if not payload.symbol.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="symbol is required for execution")

    follower_repository = FollowerRepository(session)
    execution_repository = ExecutionRepository(session)
    follower = await follower_repository.get(payload.account_id)
    if follower is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="account not found")

    client = container.exchange_clients[Exchange(follower.exchange)]
    api_key = await container.secret_cipher.decrypt(follower.api_key_ciphertext)
    api_secret = await container.secret_cipher.decrypt(follower.api_secret_ciphertext)
    api_passphrase = await container.secret_cipher.decrypt(follower.api_passphrase_ciphertext)

    if payload.action == BuilderAction.CANCEL_ORDERS:
        result = await client.cancel_orders(follower, payload.symbol, api_key, api_secret, api_passphrase)
        await execution_repository.add_trade_log(
            exchange=follower.exchange,
            log_type=LogType.MANUAL,
            log_key=follower.name,
            message=f"Cancel orders executed for {payload.symbol}.",
            details={
                "origin": "MANUAL_EXECUTION",
                "action": payload.action.value,
                "symbol": payload.symbol,
                "account_id": follower.id,
                "account_name": follower.name,
                "accepted": True,
                "response": result,
            },
        )
        await session.commit()
        return ManualExecutionResponse(accepted=True, result=result)

    if payload.action == BuilderAction.CLOSE_POSITION:
        snapshot = await client.fetch_position(follower, payload.symbol, api_key, api_secret, api_passphrase)
        if snapshot.quantity == 0:
            result = {"message": "No open position to close."}
            await execution_repository.add_trade_log(
                exchange=follower.exchange,
                log_type=LogType.MANUAL,
                log_key=follower.name,
                message=f"Close position requested for {payload.symbol}, but no open position was found.",
                details={
                    "origin": "MANUAL_EXECUTION",
                    "action": payload.action.value,
                    "symbol": payload.symbol,
                    "account_id": follower.id,
                    "account_name": follower.name,
                    "accepted": True,
                    "response": result,
                },
            )
            await session.commit()
            return ManualExecutionResponse(accepted=True, result=result)
        order_request = OrderRequest(
            symbol=payload.symbol,
            side="SELL" if snapshot.quantity > 0 else "BUY",
            quantity=abs(snapshot.quantity),
            reduce_only=True,
            position_side=PositionSide.LONG if snapshot.quantity > 0 else PositionSide.SHORT,
            order_type=OrderType.LIMIT if payload.close_by_limit_order and payload.limit_price is not None else payload.order_type,
            leverage=payload.leverage or follower.leverage,
            limit_price=payload.limit_price if payload.close_by_limit_order else None,
            stop_price=payload.stop_price,
        )
        result = await client.place_order(follower, order_request, api_key, api_secret, api_passphrase)
        await execution_repository.add_trade_log(
            exchange=follower.exchange,
            log_type=LogType.MANUAL if result.accepted else LogType.ERROR,
            log_key=follower.name,
            message=f"Close position command executed for {payload.symbol}.",
            details={
                "origin": "MANUAL_EXECUTION",
                "action": payload.action.value,
                "symbol": payload.symbol,
                "account_id": follower.id,
                "account_name": follower.name,
                "accepted": result.accepted,
                "external_order_id": result.external_order_id,
                "response": result.raw_response,
                "error_message": result.error_message,
            },
        )
        await session.commit()
        return ManualExecutionResponse(accepted=result.accepted, result=result.model_dump(mode="json"))

    if payload.action not in {BuilderAction.BUY, BuilderAction.SELL}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported command action")
    if payload.quantity_value is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity_value is required")

    order_request = OrderRequest(
        symbol=payload.symbol,
        side=payload.action.value,
        quantity=payload.quantity_value,
        order_type=payload.order_type,
        position_side=PositionSide.LONG if payload.action == BuilderAction.BUY else PositionSide.SHORT,
        leverage=payload.leverage or follower.leverage,
        limit_price=payload.limit_price,
        stop_price=payload.stop_price,
    )
    result = await client.place_order(follower, order_request, api_key, api_secret, api_passphrase)
    attached_orders = []
    if result.accepted:
        attached_orders = await _place_attached_orders(
            client=client,
            follower=follower,
            payload=payload,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
        )
    result_payload = result.model_dump(mode="json")
    if attached_orders:
        result_payload["attached_orders"] = attached_orders
    await execution_repository.add_trade_log(
        exchange=follower.exchange,
        log_type=LogType.MANUAL if result.accepted else LogType.ERROR,
        log_key=follower.name,
        message=f"Manual {payload.action.value} command executed for {payload.symbol}.",
        details={
            "origin": "MANUAL_EXECUTION",
            "action": payload.action.value,
            "symbol": payload.symbol,
            "account_id": follower.id,
            "account_name": follower.name,
            "accepted": result.accepted,
            "external_order_id": result.external_order_id,
            "response": result.raw_response,
            "error_message": result.error_message,
            "attached_orders": attached_orders,
        },
    )
    await session.commit()
    return ManualExecutionResponse(accepted=result.accepted, result=result_payload)


@router.get("/health/exchanges", response_model=HealthResponse)
async def exchange_health(container: AppContainer = Depends(get_container)) -> HealthResponse:
    checks: list[HealthCheckResult] = []
    for client in container.exchange_clients.values():
        checks.append(await client.ping())
    return HealthResponse(checks=[item.model_dump(mode="json") for item in checks])


@router.get("/positions", response_model=list[PositionSnapshotResponse])
async def positions(
    display_currency: str = Query(default="USD", min_length=3, max_length=3),
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> list[PositionSnapshotResponse]:
    repository = ExecutionRepository(session)
    follower_repository = FollowerRepository(session)
    snapshots = await repository.list_recent_position_snapshots(limit=100)
    followers = await follower_repository.list()
    follower_names = {item.id: item.name for item in followers}
    responses: list[PositionSnapshotResponse] = []
    for item in snapshots:
        follower_name = follower_names.get(item.account_id)
        response = position_snapshot_to_response(item, follower_name=follower_name)
        response.display_value = await container.fx.convert(
            Decimal(str(item.notional_exposure or 0)),
            display_currency,
        )
        responses.append(response)
    return responses


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    container: AppContainer = websocket.app.state.container
    last_log_id: str | None = None
    last_task_id: str | None = None
    last_counts: tuple[int, int, int] | None = None

    try:
        while True:
            async with container.session_factory() as session:
                signal_repository = SignalRepository(session)
                execution_repository = ExecutionRepository(session)
                follower_repository = FollowerRepository(session)
                logs = await signal_repository.list_logs(limit=20)
                _, total_logs = await signal_repository.list_logs_page(page=1, limit=1)
                tasks = await execution_repository.list_recent_tasks(limit=10)
                sources = await signal_repository.list_signal_sources()
                copy_trades = await execution_repository.list_copy_trades()
                followers = await follower_repository.list()
                snapshots = await execution_repository.list_recent_position_snapshots(limit=50)

            current_log_id = logs[0].id if logs else None
            current_task_id = tasks[0].id if tasks else None
            current_counts = (len(sources), len(copy_trades), len(followers))

            if (current_log_id != last_log_id) or (current_task_id != last_task_id) or (current_counts != last_counts):
                fx_meta = await build_fx_meta(container, "USD")
                equity_summary = await build_equity_summary(container, snapshots, "USD")
                await websocket.send_json(
                    {
                        "type": "snapshot",
                        "counts": {
                            "signals": len(sources),
                            "copy_trades": len(copy_trades),
                            "followers": len(followers),
                            "logs": total_logs,
                        },
                        "logs": [trade_log_to_response(item).model_dump(mode="json") for item in logs],
                        "executions": [execution_task_to_response(item).model_dump(mode="json") for item in tasks],
                        "fx_meta": fx_meta.model_dump(mode="json"),
                        "equity_summary": equity_summary.model_dump(mode="json"),
                        "worker_status": read_worker_status(),
                    }
                )
                last_log_id = current_log_id
                last_task_id = current_task_id
                last_counts = current_counts

            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
                if message == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        return
