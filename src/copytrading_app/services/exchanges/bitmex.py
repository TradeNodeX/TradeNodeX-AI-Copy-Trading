from __future__ import annotations

import hashlib
import hmac
import json
import time
from decimal import Decimal
from typing import Any
from urllib.parse import quote

import httpx

from copytrading_app.core.config import Settings
from copytrading_app.db.models import FollowerAccountModel
from copytrading_app.domain.enums import Exchange
from copytrading_app.domain.types import HealthCheckResult, OrderRequest, OrderResult, PositionSnapshotPayload


class BitmexClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(timeout=settings.api_timeout_seconds)

    async def ping(self) -> HealthCheckResult:
        response = await self._client.get(f"{self.settings.bitmex_base_url}/api/v1/instrument/active")
        return HealthCheckResult(name="bitmex", ok=response.is_success, details={"status_code": response.status_code})

    async def fetch_instruments(self) -> list[dict[str, Any]]:
        response = await self._client.get(f"{self.settings.bitmex_base_url}/api/v1/instrument/active")
        response.raise_for_status()
        return response.json()

    async def validate_credentials(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> tuple[bool, str | None]:
        path = "/api/v1/user/walletSummary"
        headers = self._signed_headers("GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
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
        path = "/api/v1/order"
        payload: dict[str, Any] = {
            "symbol": request.symbol,
            "side": "Buy" if request.side == "BUY" else "Sell",
            "ordType": "Market" if request.order_type.value == "MARKET" else "Limit",
            "orderQty": float(request.quantity),
        }
        if request.client_order_id:
            payload["clOrdID"] = request.client_order_id[:36]
        if request.limit_price is not None:
            payload["price"] = float(request.limit_price)
        if request.reduce_only:
            payload["execInst"] = "ReduceOnly"
        body = json.dumps(payload, separators=(",", ":"))
        headers = self._signed_headers("POST", path, api_key, api_secret, body=body)
        response = await self._client.post(f"{self._base_url(account)}{path}", headers=headers, content=body)
        data = response.json()
        accepted = response.is_success and data.get("ordStatus") not in {"Rejected", "Canceled"}
        return OrderResult(
            accepted=accepted,
            external_order_id=data.get("orderID"),
            raw_response=data,
            error_message=None if accepted else json.dumps(data, ensure_ascii=False),
        )

    async def fetch_position(
        self,
        account: FollowerAccountModel,
        symbol: str,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> PositionSnapshotPayload:
        filter_query = quote(json.dumps({"symbol": symbol}, separators=(",", ":")))
        path = f"/api/v1/position?filter={filter_query}"
        headers = self._signed_headers("GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        response.raise_for_status()
        rows = response.json()
        row = rows[0] if rows else {}
        qty = Decimal(str(row.get("currentQty", "0")))
        return PositionSnapshotPayload(
            account_id=account.id,
            exchange=Exchange.BITMEX,
            symbol=symbol,
            quantity=qty,
            entry_price=Decimal(str(row["avgEntryPrice"])) if row.get("avgEntryPrice") else None,
            leverage=int(Decimal(str(row["leverage"]))) if row.get("leverage") else account.leverage,
            source="rest",
        )

    async def fetch_open_positions(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> list[PositionSnapshotPayload]:
        path = "/api/v1/position"
        headers = self._signed_headers("GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        response.raise_for_status()
        snapshots: list[PositionSnapshotPayload] = []
        for row in response.json():
            qty = Decimal(str(row.get("currentQty", "0")))
            if qty == 0:
                continue
            mark_price = Decimal(str(row["markPrice"])) if row.get("markPrice") else None
            entry_price = Decimal(str(row["avgEntryPrice"])) if row.get("avgEntryPrice") else None
            snapshots.append(
                PositionSnapshotPayload(
                    account_id=account.id,
                    exchange=Exchange.BITMEX,
                    symbol=row["symbol"],
                    quantity=qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=Decimal(str(row["unrealisedPnlPcnt"])) if row.get("unrealisedPnlPcnt") else None,
                    notional_exposure=abs(qty * mark_price) if mark_price is not None else None,
                    leverage=int(Decimal(str(row["leverage"]))) if row.get("leverage") else account.leverage,
                    margin_mode=row.get("crossMargin") and "CROSS" or "ISOLATED",
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
        query = f"symbol={quote(symbol)}"
        path = f"/api/v1/order/all?{query}"
        headers = self._signed_headers("DELETE", path, api_key, api_secret)
        response = await self._client.delete(f"{self._base_url(account)}{path}", headers=headers)
        data = response.json()
        return {"accepted": response.is_success, "data": data}

    def _base_url(self, account: FollowerAccountModel) -> str:
        if account.environment in {"TESTNET", "DEMO"}:
            return self.settings.bitmex_testnet_base_url
        return self.settings.bitmex_base_url

    def private_stream_url(self, account: FollowerAccountModel) -> str:
        if account.environment in {"TESTNET", "DEMO"}:
            return self.settings.bitmex_testnet_ws_base_url
        return self.settings.bitmex_ws_base_url

    def ws_auth_message(self, api_key: str | None, api_secret: str | None) -> dict[str, Any]:
        expires = int(time.time()) + 5
        signature = hmac.new(
            (api_secret or "").encode("utf-8"),
            f"GET/realtime{expires}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {"op": "authKeyExpires", "args": [api_key or "", expires, signature]}

    def ws_subscribe_message(self) -> dict[str, Any]:
        return {"op": "subscribe", "args": ["position", "order", "execution"]}

    def _signed_headers(
        self,
        method: str,
        path_with_query: str,
        api_key: str | None,
        api_secret: str | None,
        body: str = "",
    ) -> dict[str, str]:
        expires = str(int(time.time()) + 5)
        message = f"{method.upper()}{path_with_query}{expires}{body}"
        signature = hmac.new((api_secret or "").encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
        return {
            "api-key": api_key or "",
            "api-expires": expires,
            "api-signature": signature,
            "Content-Type": "application/json",
        }
