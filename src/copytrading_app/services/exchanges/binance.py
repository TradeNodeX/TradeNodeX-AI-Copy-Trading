from __future__ import annotations

import hashlib
import hmac
import json
import time
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import httpx

from copytrading_app.core.config import Settings
from copytrading_app.db.models import FollowerAccountModel
from copytrading_app.domain.enums import Exchange
from copytrading_app.domain.types import HealthCheckResult, OrderRequest, OrderResult, PositionSnapshotPayload


class BinanceFuturesClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(base_url=settings.binance_base_url, timeout=settings.api_timeout_seconds)

    async def ping(self) -> HealthCheckResult:
        response = await self._client.get("/fapi/v1/ping")
        return HealthCheckResult(name="binance", ok=response.is_success, details={"status_code": response.status_code})

    async def fetch_instruments(self) -> list[dict[str, Any]]:
        response = await self._client.get("/fapi/v1/exchangeInfo")
        response.raise_for_status()
        data = response.json()
        return data.get("symbols", [])

    async def validate_credentials(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> tuple[bool, str | None]:
        params = {"timestamp": int(time.time() * 1000), "recvWindow": self.settings.default_recv_window_ms}
        headers = self._signed_headers(api_key)
        signed_query = self._sign_query(api_secret, params)
        response = await self._client.get(f"/fapi/v2/balance?{signed_query}", headers=headers)
        if response.is_success:
            return True, None
        return False, response.text

    async def place_order(
        self,
        account: FollowerAccountModel,
        request: OrderRequest,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> OrderResult:
        params = {
            "symbol": request.symbol,
            "side": request.side,
            "type": request.order_type.value,
            "quantity": str(request.quantity),
            "timestamp": int(time.time() * 1000),
            "recvWindow": self.settings.default_recv_window_ms,
        }
        if request.reduce_only:
            params["reduceOnly"] = "true"
        if request.client_order_id:
            params["newClientOrderId"] = request.client_order_id
        if request.limit_price is not None:
            params["price"] = str(request.limit_price)
            params["timeInForce"] = "GTC"
        if request.stop_price is not None:
            params["stopPrice"] = str(request.stop_price)

        headers = self._signed_headers(api_key)
        signed_query = self._sign_query(api_secret, params)
        response = await self._client.post(f"/fapi/v1/order?{signed_query}", headers=headers)
        data = response.json()
        return OrderResult(
            accepted=response.is_success,
            external_order_id=str(data.get("orderId")) if response.is_success else None,
            raw_response=data,
            error_message=None if response.is_success else json.dumps(data, ensure_ascii=False),
        )

    async def fetch_position(
        self,
        account: FollowerAccountModel,
        symbol: str,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> PositionSnapshotPayload:
        params = {
            "timestamp": int(time.time() * 1000),
            "recvWindow": self.settings.default_recv_window_ms,
        }
        headers = self._signed_headers(api_key)
        signed_query = self._sign_query(api_secret, params)
        response = await self._client.get(f"/fapi/v2/positionRisk?{signed_query}", headers=headers)
        response.raise_for_status()
        rows = response.json()
        row = next((item for item in rows if item["symbol"] == symbol), None)
        qty = Decimal(str(row["positionAmt"])) if row else Decimal("0")
        return PositionSnapshotPayload(
            account_id=account.id,
            exchange=Exchange.BINANCE,
            symbol=symbol,
            quantity=qty,
            entry_price=Decimal(str(row["entryPrice"])) if row and row.get("entryPrice") else None,
            leverage=int(row["leverage"]) if row and row.get("leverage") else None,
            source="rest",
        )

    async def fetch_open_positions(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> list[PositionSnapshotPayload]:
        params = {
            "timestamp": int(time.time() * 1000),
            "recvWindow": self.settings.default_recv_window_ms,
        }
        headers = self._signed_headers(api_key)
        signed_query = self._sign_query(api_secret, params)
        response = await self._client.get(f"/fapi/v2/positionRisk?{signed_query}", headers=headers)
        response.raise_for_status()
        snapshots: list[PositionSnapshotPayload] = []
        for row in response.json():
            qty = Decimal(str(row.get("positionAmt", "0")))
            if qty == 0:
                continue
            mark_price = Decimal(str(row["markPrice"])) if row.get("markPrice") else None
            entry_price = Decimal(str(row["entryPrice"])) if row.get("entryPrice") else None
            snapshots.append(
                PositionSnapshotPayload(
                    account_id=account.id,
                    exchange=Exchange.BINANCE,
                    symbol=row["symbol"],
                    quantity=qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=Decimal(str(row["unRealizedProfit"])) if row.get("unRealizedProfit") else None,
                    notional_exposure=abs(qty * mark_price) if mark_price is not None else None,
                    leverage=int(row["leverage"]) if row.get("leverage") else None,
                    margin_mode=row.get("marginType"),
                    source="rest",
                )
            )
        return snapshots

    async def cancel_orders(
        self,
        account: FollowerAccountModel,
        symbol: str,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "symbol": symbol,
            "timestamp": int(time.time() * 1000),
            "recvWindow": self.settings.default_recv_window_ms,
        }
        headers = self._signed_headers(api_key)
        signed_query = self._sign_query(api_secret, params)
        response = await self._client.delete(f"/fapi/v1/allOpenOrders?{signed_query}", headers=headers)
        return response.json()

    async def create_listen_key(self, api_key: str | None) -> str:
        headers = self._signed_headers(api_key)
        response = await self._client.post("/fapi/v1/listenKey", headers=headers)
        response.raise_for_status()
        return response.json()["listenKey"]

    async def keepalive_listen_key(self, api_key: str | None, listen_key: str) -> None:
        headers = self._signed_headers(api_key)
        await self._client.put(f"/fapi/v1/listenKey?listenKey={listen_key}", headers=headers)

    def user_stream_url(self, listen_key: str) -> str:
        return f"{self.settings.binance_ws_base_url}/ws/{listen_key}"

    def _signed_headers(self, api_key: str | None) -> dict[str, str]:
        return {"X-MBX-APIKEY": api_key or ""}

    def _sign_query(self, secret: str | None, params: dict) -> str:
        query = urlencode(params)
        signature = hmac.new((secret or "").encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{query}&signature={signature}"
