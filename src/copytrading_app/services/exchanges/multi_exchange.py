from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

import httpx

from copytrading_app.db.models import FollowerAccountModel
from copytrading_app.domain.enums import Exchange
from copytrading_app.domain.types import HealthCheckResult, OrderRequest, OrderResult, PositionSnapshotPayload


class ReadOnlyExchangeClient:
    def __init__(
        self,
        *,
        exchange: Exchange,
        name: str,
        base_url: str,
        timeout_seconds: float,
        ping_path: str,
        instruments_path: str,
        instruments_parser: Callable[[dict[str, Any]], list[dict[str, Any]]],
    ) -> None:
        self.exchange = exchange
        self.name = name
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)
        self._ping_path = ping_path
        self._instruments_path = instruments_path
        self._instruments_parser = instruments_parser

    async def ping(self) -> HealthCheckResult:
        response = await self._client.get(self._ping_path)
        return HealthCheckResult(name=self.name, ok=response.is_success, details={"status_code": response.status_code})

    async def fetch_instruments(self) -> list[dict[str, Any]]:
        response = await self._client.get(self._instruments_path)
        response.raise_for_status()
        return self._instruments_parser(response.json())

    async def validate_credentials(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> tuple[bool, str | None]:
        if not api_key or not api_secret:
            return False, f"{self.exchange.value} API key and secret are required."
        return False, f"{self.exchange.value} private credential validation is not implemented in this build."

    async def place_order(
        self,
        account: FollowerAccountModel,
        request: OrderRequest,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> OrderResult:
        return OrderResult(
            accepted=False,
            raw_response={},
            error_message=f"{self.exchange.value} order placement is not implemented in this build.",
        )

    async def fetch_position(
        self,
        account: FollowerAccountModel,
        symbol: str,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> PositionSnapshotPayload:
        return PositionSnapshotPayload(
            account_id=account.id,
            exchange=self.exchange,
            symbol=symbol,
            quantity=Decimal("0"),
            entry_price=None,
            leverage=account.leverage,
            source="unsupported",
        )

    async def cancel_orders(
        self,
        account: FollowerAccountModel,
        symbol: str,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> dict[str, Any]:
        return {
            "accepted": False,
            "exchange": self.exchange.value,
            "symbol": symbol,
            "error": f"{self.exchange.value} cancel-orders is not implemented in this build.",
        }


def okx_instruments_parser(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("data", [])
    return [{"symbol": row.get("instId"), "base": row.get("baseCcy"), "quote": row.get("quoteCcy")} for row in rows]


def coinbase_instruments_parser(data: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    rows = data if isinstance(data, list) else data.get("products", [])
    return [{"symbol": row.get("product_id") or row.get("id"), "base": row.get("base_currency"), "quote": row.get("quote_currency")} for row in rows]


def kraken_instruments_parser(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("result", {})
    instruments = []
    for symbol, row in rows.items():
        instruments.append({"symbol": symbol, "base": row.get("base"), "quote": row.get("quote")})
    return instruments


def bitmex_instruments_parser(data: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    rows = data if isinstance(data, list) else data.get("data", [])
    return [{"symbol": row.get("symbol"), "base": row.get("rootSymbol"), "quote": row.get("quoteCurrency")} for row in rows]


def gateio_instruments_parser(data: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    rows = data if isinstance(data, list) else data.get("result", [])
    return [{"symbol": row.get("name") or row.get("id") or row.get("currency_pair"), "base": row.get("base"), "quote": row.get("quote")} for row in rows]
