from __future__ import annotations

import hashlib
import hmac
import json
import time
from decimal import Decimal
from typing import Any

import httpx

from copytrading_app.core.config import Settings
from copytrading_app.db.models import FollowerAccountModel
from copytrading_app.domain.enums import Exchange, PositionSide
from copytrading_app.domain.types import HealthCheckResult, OrderRequest, OrderResult, PositionSnapshotPayload


class BybitLinearClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(base_url=settings.bybit_base_url, timeout=settings.api_timeout_seconds)

    async def ping(self) -> HealthCheckResult:
        response = await self._client.get("/v5/market/time")
        return HealthCheckResult(name="bybit", ok=response.is_success, details={"status_code": response.status_code})

    async def fetch_instruments(self) -> list[dict[str, Any]]:
        response = await self._client.get("/v5/market/instruments-info", params={"category": "linear"})
        response.raise_for_status()
        return response.json().get("result", {}).get("list", [])

    async def validate_credentials(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> tuple[bool, str | None]:
        timestamp = str(int(time.time() * 1000))
        recv_window = str(self.settings.default_recv_window_ms)
        query = "accountType=UNIFIED"
        headers = self._signed_headers(api_key, api_secret, timestamp, recv_window, query)
        response = await self._client.get(f"/v5/account/wallet-balance?{query}", headers=headers)
        data = response.json()
        if response.is_success and data.get("retCode") == 0:
            return True, None
        return False, json.dumps(data, ensure_ascii=False)

    async def place_order(
        self,
        account: FollowerAccountModel,
        request: OrderRequest,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> OrderResult:
        payload = {
            "category": "linear",
            "symbol": request.symbol,
            "side": request.side.title(),
            "orderType": "Market" if request.order_type.value == "MARKET" else request.order_type.value.title(),
            "qty": str(request.quantity),
            "reduceOnly": request.reduce_only,
        }
        if request.position_side != PositionSide.FLAT:
            payload["positionIdx"] = 1 if request.position_side == PositionSide.LONG else 2
        if request.client_order_id:
            payload["orderLinkId"] = request.client_order_id
        if request.limit_price is not None:
            payload["price"] = str(request.limit_price)
        if request.stop_price is not None:
            payload["triggerPrice"] = str(request.stop_price)

        timestamp = str(int(time.time() * 1000))
        recv_window = str(self.settings.default_recv_window_ms)
        body = json.dumps(payload, separators=(",", ":"))
        headers = self._signed_headers(api_key, api_secret, timestamp, recv_window, body)
        response = await self._client.post("/v5/order/create", headers=headers, content=body)
        data = response.json()
        accepted = response.is_success and data.get("retCode") == 0
        result = data.get("result", {})
        return OrderResult(
            accepted=accepted,
            external_order_id=result.get("orderId"),
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
        timestamp = str(int(time.time() * 1000))
        recv_window = str(self.settings.default_recv_window_ms)
        query = f"category=linear&symbol={symbol}"
        headers = self._signed_headers(api_key, api_secret, timestamp, recv_window, query)
        response = await self._client.get(f"/v5/position/list?{query}", headers=headers)
        response.raise_for_status()
        data = response.json()
        rows = data.get("result", {}).get("list", [])
        row = rows[0] if rows else {}
        qty = Decimal(str(row.get("size", "0")))
        side = row.get("side", "")
        signed_qty = qty if side == "Buy" else -qty if side == "Sell" else Decimal("0")
        return PositionSnapshotPayload(
            account_id=account.id,
            exchange=Exchange.BYBIT,
            symbol=symbol,
            quantity=signed_qty,
            entry_price=Decimal(str(row["avgPrice"])) if row.get("avgPrice") else None,
            leverage=int(row["leverage"]) if row.get("leverage") else None,
            source="rest",
        )

    async def fetch_open_positions(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> list[PositionSnapshotPayload]:
        timestamp = str(int(time.time() * 1000))
        recv_window = str(self.settings.default_recv_window_ms)
        query = "category=linear&settleCoin=USDT"
        headers = self._signed_headers(api_key, api_secret, timestamp, recv_window, query)
        response = await self._client.get(f"/v5/position/list?{query}", headers=headers)
        response.raise_for_status()
        data = response.json()
        snapshots: list[PositionSnapshotPayload] = []
        for row in data.get("result", {}).get("list", []):
            size = Decimal(str(row.get("size", "0")))
            if size == 0:
                continue
            signed_qty = size if row.get("side") == "Buy" else -size if row.get("side") == "Sell" else Decimal("0")
            mark_price = Decimal(str(row["markPrice"])) if row.get("markPrice") else None
            entry_price = Decimal(str(row["avgPrice"])) if row.get("avgPrice") else None
            snapshots.append(
                PositionSnapshotPayload(
                    account_id=account.id,
                    exchange=Exchange.BYBIT,
                    symbol=row["symbol"],
                    quantity=signed_qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=Decimal(str(row["unrealisedPnl"])) if row.get("unrealisedPnl") else None,
                    notional_exposure=abs(signed_qty * mark_price) if mark_price is not None else None,
                    leverage=int(row["leverage"]) if row.get("leverage") else None,
                    margin_mode=row.get("tradeMode"),
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
        payload = {"category": "linear", "symbol": symbol}
        timestamp = str(int(time.time() * 1000))
        recv_window = str(self.settings.default_recv_window_ms)
        body = json.dumps(payload, separators=(",", ":"))
        headers = self._signed_headers(api_key, api_secret, timestamp, recv_window, body)
        response = await self._client.post("/v5/order/cancel-all", headers=headers, content=body)
        return response.json()

    def private_stream_url(self) -> str:
        return f"{self.settings.bybit_ws_base_url}/v5/private"

    def auth_message(self, api_key: str | None, api_secret: str | None) -> dict[str, Any]:
        expires = int((time.time() + 5) * 1000)
        signature = hmac.new(
            (api_secret or "").encode("utf-8"),
            f"GET/realtime{expires}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {"op": "auth", "args": [api_key or "", expires, signature]}

    def _signed_headers(
        self,
        api_key: str | None,
        secret: str | None,
        timestamp: str,
        recv_window: str,
        payload: str,
    ) -> dict[str, str]:
        sign_payload = f"{timestamp}{api_key or ''}{recv_window}{payload}"
        signature = hmac.new((secret or "").encode("utf-8"), sign_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return {
            "X-BAPI-API-KEY": api_key or "",
            "X-BAPI-SIGN": signature,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json",
        }
