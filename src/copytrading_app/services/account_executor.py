from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
import asyncio

from copytrading_app.db.models import ExecutionTaskModel
from copytrading_app.domain.enums import Exchange, LogType, PositionSide, SignalStatus
from copytrading_app.domain.types import OrderRequest
from copytrading_app.repositories.execution_repository import ExecutionRepository
from copytrading_app.services.exchanges.base import ExchangeClient
from copytrading_app.services.logging_service import TradeLoggingService
from copytrading_app.services.rate_limiter import RateLimiterRegistry
from copytrading_app.services.security import SecretCipher


class AccountExecutor:
    def __init__(
        self,
        execution_repository: ExecutionRepository,
        exchange_clients: dict[Exchange, ExchangeClient],
        rate_limiter_registry: RateLimiterRegistry,
        secret_cipher: SecretCipher,
    ):
        self.execution_repository = execution_repository
        self.exchange_clients = exchange_clients
        self.rate_limiter_registry = rate_limiter_registry
        self.secret_cipher = secret_cipher
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def execute_task(self, task: ExecutionTaskModel) -> None:
        client = self.exchange_clients[Exchange(task.exchange)]
        follower = task.follower_account
        if follower is None:
            raise ValueError(f"task {task.id} missing follower account")

        api_key = await self.secret_cipher.decrypt(follower.api_key_ciphertext)
        api_secret = await self.secret_cipher.decrypt(follower.api_secret_ciphertext)
        api_passphrase = await self.secret_cipher.decrypt(follower.api_passphrase_ciphertext)
        logger = TradeLoggingService(self.execution_repository)
        lock_key = f"{task.follower_account_id}:{task.symbol}"

        async with self._locks[lock_key]:
            if Decimal(task.delta_quantity) == 0:
                await self.execution_repository.update_task_status(task.id, SignalStatus.SKIPPED)
                await logger.info(
                    exchange=Exchange(task.exchange),
                    log_key=follower.name,
                    message=f"Skipped task {task.id} because delta quantity is zero.",
                    details={"task_id": task.id, "symbol": task.symbol, "account_id": follower.id, "account_name": follower.name},
                )
                return

            await self.rate_limiter_registry.acquire(
                key=f"{task.exchange}:{task.follower_account_id}",
                capacity=10 if task.exchange == Exchange.BYBIT.value else 30,
                refill_per_second=10 if task.exchange == Exchange.BYBIT.value else 30,
            )
            side = self._resolve_side(Decimal(task.delta_quantity))
            request = OrderRequest(
                symbol=task.symbol,
                side=side,
                quantity=abs(Decimal(task.delta_quantity)),
                reduce_only=task.reduce_only,
                position_side=PositionSide(task.target_side),
                client_order_id=task.id,
                leverage=follower.leverage,
            )
            attempt = await self.execution_repository.create_attempt(task.id, request.model_dump(mode="json"))
            result = await client.place_order(follower, request, api_key, api_secret, api_passphrase)
            await self.execution_repository.finalize_attempt(attempt.id, result)
            status = SignalStatus.ACKED if result.accepted else SignalStatus.FAILED
            await self.execution_repository.update_task_status(task.id, status, error_message=result.error_message)
            if result.accepted:
                try:
                    snapshot = await client.fetch_position(follower, task.symbol, api_key, api_secret, api_passphrase)
                    await self.execution_repository.save_position_snapshot(snapshot)
                    expected_quantity = self._expected_quantity(task)
                    if snapshot.quantity == expected_quantity:
                        await self.execution_repository.update_task_status(task.id, SignalStatus.FILLED)
                except Exception as exc:
                    await logger.warning(
                        exchange=Exchange(task.exchange),
                        log_key=follower.name,
                        message=f"Position snapshot refresh failed after execution for task {task.id}: {exc}",
                        details={"task_id": task.id, "symbol": task.symbol, "account_id": follower.id, "account_name": follower.name},
                    )
                await logger.execution(
                    exchange=Exchange(task.exchange),
                    log_key=follower.name,
                    message=(
                        f"{task.action} signal executed for {task.symbol}. "
                        f"Sent {side} {abs(Decimal(task.delta_quantity))} via {task.exchange}."
                    ),
                    details={
                        "task_id": task.id,
                        "signal_id": task.signal_id,
                        "copy_trade_id": task.copy_trade_id,
                        "symbol": task.symbol,
                        "delta_quantity": str(task.delta_quantity),
                        "external_order_id": result.external_order_id,
                        "account_id": follower.id,
                        "account_name": follower.name,
                        "response": result.raw_response,
                    },
                )
            else:
                await logger.error(
                    exchange=Exchange(task.exchange),
                    log_key=follower.name,
                    message=f"Execution failed for task {task.id}: {result.error_message}",
                    details={"task_id": task.id, "signal_id": task.signal_id, "copy_trade_id": task.copy_trade_id, "account_id": follower.id, "account_name": follower.name, "response": result.raw_response},
                )

    def _resolve_side(self, delta_quantity: Decimal) -> str:
        if delta_quantity < 0:
            return "SELL"
        return "BUY"

    def _expected_quantity(self, task: ExecutionTaskModel) -> Decimal:
        target = Decimal(task.target_quantity)
        if task.target_side == PositionSide.SHORT.value:
            return -target
        if task.target_side == PositionSide.FLAT.value:
            return Decimal("0")
        return target
