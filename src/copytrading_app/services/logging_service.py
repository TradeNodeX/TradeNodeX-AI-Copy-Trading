from __future__ import annotations

from decimal import Decimal

from copytrading_app.domain.enums import Exchange, LogType
from copytrading_app.repositories.execution_repository import ExecutionRepository


class TradeLoggingService:
    def __init__(self, execution_repository: ExecutionRepository):
        self.execution_repository = execution_repository

    async def info(self, exchange: Exchange, log_key: str, message: str, details: dict, pnl: Decimal | None = None) -> None:
        await self.execution_repository.add_trade_log(
            exchange=exchange.value,
            log_type=LogType.INFO,
            log_key=log_key,
            message=message,
            details=details,
            pnl=pnl,
        )

    async def execution(
        self,
        exchange: Exchange,
        log_key: str,
        message: str,
        details: dict,
        pnl: Decimal | None = None,
    ) -> None:
        await self.execution_repository.add_trade_log(
            exchange=exchange.value,
            log_type=LogType.EXECUTION,
            log_key=log_key,
            message=message,
            details=details,
            pnl=pnl,
        )

    async def error(self, exchange: Exchange, log_key: str, message: str, details: dict) -> None:
        await self.execution_repository.add_trade_log(
            exchange=exchange.value,
            log_type=LogType.ERROR,
            log_key=log_key,
            message=message,
            details=details,
        )

    async def warning(self, exchange: Exchange, log_key: str, message: str, details: dict) -> None:
        await self.execution_repository.add_trade_log(
            exchange=exchange.value,
            log_type=LogType.WARNING,
            log_key=log_key,
            message=message,
            details=details,
        )
