from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from copytrading_app.core.config import Settings, get_settings
from copytrading_app.db.base import Base
from copytrading_app.db.session import build_engine, build_session_factory
from copytrading_app.domain.enums import Exchange, RuntimeEnvironment
from copytrading_app.repositories.execution_repository import ExecutionRepository
from copytrading_app.repositories.follower_repository import FollowerRepository
from copytrading_app.repositories.signal_repository import SignalRepository
from copytrading_app.services.account_executor import AccountExecutor
from copytrading_app.services.command_builder import CommandBuilderService
from copytrading_app.services.exchanges.base import ExchangeClient
from copytrading_app.services.exchanges.bitmex import BitmexClient
from copytrading_app.services.exchanges.binance import BinanceFuturesClient
from copytrading_app.services.exchanges.bybit import BybitLinearClient
from copytrading_app.services.exchanges.coinbase import CoinbaseAdvancedClient
from copytrading_app.services.exchanges.gateio import GateIoFuturesClient
from copytrading_app.services.exchanges.kraken import KrakenFuturesClient
from copytrading_app.services.exchanges.okx import OkxSwapClient
from copytrading_app.services.fx import FxRateService
from copytrading_app.services.fanout_planner import FanoutPlanner
from copytrading_app.services.instrument_catalog import InstrumentCatalogService
from copytrading_app.services.idempotency import IdempotencyStore, LocalIdempotencyStore, RedisIdempotencyStore
from copytrading_app.services.orchestrator import Orchestrator
from copytrading_app.services.queues.in_memory import InMemoryTaskQueue
from copytrading_app.services.queues.sqs import SqsTaskQueue
from copytrading_app.services.rate_limiter import RateLimiterRegistry
from copytrading_app.services.reconciler import Reconciler
from copytrading_app.services.scaling import ScalingService
from copytrading_app.services.security import AwsKmsSecretCipher, LocalSecretCipher, SecretCipher
from copytrading_app.services.signal_normalizer import SignalNormalizer


class AppContainer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = build_engine(settings)
        self.session_factory = build_session_factory(self.engine)
        self.redis: Redis | None = None
        self.queue = SqsTaskQueue(settings) if settings.queue_backend.lower() == "sqs" else InMemoryTaskQueue()
        self.secret_cipher: SecretCipher = (
            AwsKmsSecretCipher(settings) if settings.kms_backend.lower() == "aws" else LocalSecretCipher()
        )
        self.idempotency_store: IdempotencyStore = LocalIdempotencyStore()
        self.rate_limiter_registry = RateLimiterRegistry()
        self.scaling_service = ScalingService()
        self.signal_normalizer = SignalNormalizer()
        self.command_builder = CommandBuilderService()
        self.fx = FxRateService(settings)
        self.exchange_clients: dict[Exchange, ExchangeClient] = {
            Exchange.BINANCE: BinanceFuturesClient(settings),
            Exchange.BYBIT: BybitLinearClient(settings),
            Exchange.OKX: OkxSwapClient(settings),
            Exchange.COINBASE: CoinbaseAdvancedClient(settings),
            Exchange.KRAKEN: KrakenFuturesClient(settings),
            Exchange.BITMEX: BitmexClient(settings),
            Exchange.GATEIO: GateIoFuturesClient(settings),
        }
        self.instrument_catalog = InstrumentCatalogService(self.exchange_clients)
        self.project_root = Path(__file__).resolve().parents[3]
        self.static_dir = self.project_root / "src" / "copytrading_app" / "static"

    async def init_models(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(self._run_schema_migrations)
        if self.settings.queue_backend.lower() == "sqs":
            self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)
            self.idempotency_store = RedisIdempotencyStore(self.redis, self.settings.redis_prefix)

    async def shutdown(self) -> None:
        for client in self.exchange_clients.values():
            http_client = getattr(client, "_client", None)
            if http_client is not None:
                await http_client.aclose()
        if self.redis is not None:
            await self.redis.aclose()
        await self.fx.close()
        await self.engine.dispose()

    def orchestrator(self, session: AsyncSession) -> Orchestrator:
        signal_repository = SignalRepository(session)
        follower_repository = FollowerRepository(session)
        execution_repository = ExecutionRepository(session)
        fanout_planner = FanoutPlanner(
            execution_repository,
            self.queue,
            self.scaling_service,
            self.instrument_catalog,
        )
        return Orchestrator(
            signal_repository=signal_repository,
            follower_repository=follower_repository,
            execution_repository=execution_repository,
            signal_normalizer=self.signal_normalizer,
            fanout_planner=fanout_planner,
            idempotency_store=self.idempotency_store,
            default_environment=RuntimeEnvironment(self.settings.default_environment),
            instrument_catalog=self.instrument_catalog,
        )

    def account_executor(self, session: AsyncSession) -> AccountExecutor:
        return AccountExecutor(
            execution_repository=ExecutionRepository(session),
            exchange_clients=self.exchange_clients,
            rate_limiter_registry=self.rate_limiter_registry,
            secret_cipher=self.secret_cipher,
        )

    def reconciler(self, session: AsyncSession) -> Reconciler:
        return Reconciler(
            signal_repository=SignalRepository(session),
            execution_repository=ExecutionRepository(session),
            exchange_clients=self.exchange_clients,
            queue=self.queue,
            tolerance=Decimal(str(self.settings.reconciler_tolerance)),
            secret_cipher=self.secret_cipher,
        )

    def _run_schema_migrations(self, sync_conn) -> None:
        inspector = inspect(sync_conn)
        copy_trade_columns = {column["name"] for column in inspector.get_columns("copy_trades")}
        follower_columns = {column["name"] for column in inspector.get_columns("follower_accounts")}
        signal_source_columns = {column["name"] for column in inspector.get_columns("signal_sources")}
        position_snapshot_columns = {column["name"] for column in inspector.get_columns("position_snapshots")}
        if "command_template" not in copy_trade_columns:
            sync_conn.execute(text("ALTER TABLE copy_trades ADD COLUMN command_template TEXT"))
        if "notes" not in copy_trade_columns:
            sync_conn.execute(text("ALTER TABLE copy_trades ADD COLUMN notes TEXT"))
        if "validation_reasons" not in copy_trade_columns:
            sync_conn.execute(text("ALTER TABLE copy_trades ADD COLUMN validation_reasons JSON"))
        if "api_passphrase_ciphertext" not in follower_columns:
            sync_conn.execute(text("ALTER TABLE follower_accounts ADD COLUMN api_passphrase_ciphertext TEXT"))
        if "credential_status" not in follower_columns:
            sync_conn.execute(text("ALTER TABLE follower_accounts ADD COLUMN credential_status VARCHAR(32) DEFAULT 'PENDING'"))
        if "permission_status" not in follower_columns:
            sync_conn.execute(text("ALTER TABLE follower_accounts ADD COLUMN permission_status VARCHAR(32) DEFAULT 'PENDING'"))
        if "connectivity_status" not in follower_columns:
            sync_conn.execute(text("ALTER TABLE follower_accounts ADD COLUMN connectivity_status VARCHAR(32) DEFAULT 'PENDING'"))
        if "trading_ready_status" not in follower_columns:
            sync_conn.execute(text("ALTER TABLE follower_accounts ADD COLUMN trading_ready_status VARCHAR(32) DEFAULT 'PENDING'"))
        if "validation_reasons" not in follower_columns:
            sync_conn.execute(text("ALTER TABLE follower_accounts ADD COLUMN validation_reasons JSON"))
        if "api_passphrase_ciphertext" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN api_passphrase_ciphertext TEXT"))
        if "validation_status" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN validation_status VARCHAR(32) DEFAULT 'PENDING'"))
        if "validation_message" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN validation_message TEXT"))
        if "credential_status" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN credential_status VARCHAR(32) DEFAULT 'PENDING'"))
        if "permission_status" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN permission_status VARCHAR(32) DEFAULT 'PENDING'"))
        if "connectivity_status" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN connectivity_status VARCHAR(32) DEFAULT 'PENDING'"))
        if "trading_ready_status" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN trading_ready_status VARCHAR(32) DEFAULT 'PENDING'"))
        if "validation_reasons" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN validation_reasons JSON"))
        if "last_validated_at" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN last_validated_at DATETIME"))
        if "stream_status" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN stream_status VARCHAR(32) DEFAULT 'OFFLINE'"))
        if "listener_status" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN listener_status VARCHAR(32) DEFAULT 'IDLE'"))
        if "last_stream_event_at" not in signal_source_columns:
            sync_conn.execute(text("ALTER TABLE signal_sources ADD COLUMN last_stream_event_at DATETIME"))
        if "mark_price" not in position_snapshot_columns:
            sync_conn.execute(text("ALTER TABLE position_snapshots ADD COLUMN mark_price NUMERIC(24, 8)"))
        if "unrealized_pnl" not in position_snapshot_columns:
            sync_conn.execute(text("ALTER TABLE position_snapshots ADD COLUMN unrealized_pnl NUMERIC(24, 8)"))
        if "notional_exposure" not in position_snapshot_columns:
            sync_conn.execute(text("ALTER TABLE position_snapshots ADD COLUMN notional_exposure NUMERIC(24, 8)"))
        if "margin_mode" not in position_snapshot_columns:
            sync_conn.execute(text("ALTER TABLE position_snapshots ADD COLUMN margin_mode VARCHAR(16)"))


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


async def get_session(container: AppContainer = Depends(get_container)) -> AsyncSession:
    async_session_factory: async_sessionmaker[AsyncSession] = container.session_factory
    async with async_session_factory() as session:
        yield session


def build_container() -> AppContainer:
    return AppContainer(get_settings())
