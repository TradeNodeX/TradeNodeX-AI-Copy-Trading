from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import httpx

from copytrading_app.core.config import Settings
from copytrading_app.db.models import FollowerAccountModel
from copytrading_app.domain.enums import Exchange, MarginMode, PositionSide
from copytrading_app.domain.types import HealthCheckResult, OrderRequest, OrderResult, PositionSnapshotPayload


class OkxSwapClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(timeout=settings.api_timeout_seconds)

    async def ping(self) -> HealthCheckResult:
        response = await self._client.get(f"{self.settings.okx_base_url}/api/v5/public/time")
        return HealthCheckResult(name="okx", ok=response.is_success, details={"status_code": response.status_code})

    async def fetch_instruments(self) -> list[dict[str, Any]]:
        response = await self._client.get(
            f"{self.settings.okx_base_url}/api/v5/public/instruments",
            params={"instType": "SWAP"},
        )
        response.raise_for_status()
        return response.json().get("data", [])

    async def validate_credentials(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> tuple[bool, str | None]:
        path = "/api/v5/account/balance"
        query = "ccy=USDT"
        headers = self._signed_headers(
            account=account,
            method="GET",
            path=path,
            query_string=query,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
        )
        response = await self._client.get(f"{self._base_url(account)}{path}?{query}", headers=headers)
        data = response.json()
        if response.is_success and data.get("code") == "0":
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
        path = "/api/v5/trade/order"
        payload: dict[str, Any] = {
            "instId": request.symbol,
            "tdMode": "cross" if account.margin_mode == MarginMode.CROSS.value else "isolated",
            "side": "buy" if request.side == "BUY" else "sell",
            "ordType": "market" if request.order_type.value == "MARKET" else "limit",
            "sz": self._decimal_to_text(request.quantity),
        }
        if request.client_order_id:
            payload["clOrdId"] = request.client_order_id[:32]
        if request.limit_price is not None:
            payload["px"] = self._decimal_to_text(request.limit_price)
        if request.reduce_only:
            payload["reduceOnly"] = True
        if account.hedge_mode and request.position_side != PositionSide.FLAT:
            payload["posSide"] = "long" if request.position_side == PositionSide.LONG else "short"

        body = json.dumps(payload, separators=(",", ":"))
        headers = self._signed_headers(
            account=account,
            method="POST",
            path=path,
            body=body,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
        )
        response = await self._client.post(f"{self._base_url(account)}{path}", headers=headers, content=body)
        data = response.json()
        accepted = response.is_success and data.get("code") == "0"
        result = data.get("data", [{}])[0] if data.get("data") else {}
        return OrderResult(
            accepted=accepted,
            external_order_id=result.get("ordId") if accepted else None,
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
        path = "/api/v5/account/positions"
        query = urlencode({"instId": symbol})
        headers = self._signed_headers(
            account=account,
            method="GET",
            path=path,
            query_string=query,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
        )
        response = await self._client.get(f"{self._base_url(account)}{path}?{query}", headers=headers)
        response.raise_for_status()
        data = response.json()
        rows = data.get("data", [])
        row = rows[0] if rows else {}
        quantity = Decimal(str(row.get("pos", "0")))
        pos_side = (row.get("posSide") or "").lower()
        signed_quantity = -quantity if pos_side == "short" else quantity
        leverage = row.get("lever")
        return PositionSnapshotPayload(
            account_id=account.id,
            exchange=Exchange.OKX,
            symbol=symbol,
            quantity=signed_quantity,
            entry_price=Decimal(str(row["avgPx"])) if row.get("avgPx") else None,
            leverage=int(Decimal(str(leverage))) if leverage else account.leverage,
            source="rest",
        )

    async def fetch_open_positions(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> list[PositionSnapshotPayload]:
        path = "/api/v5/account/positions"
        headers = self._signed_headers(
            account=account,
            method="GET",
            path=path,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
        )
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        response.raise_for_status()
        data = response.json()
        snapshots: list[PositionSnapshotPayload] = []
        for row in data.get("data", []):
            quantity = Decimal(str(row.get("pos", "0")))
            if quantity == 0:
                continue
            pos_side = (row.get("posSide") or "").lower()
            signed_quantity = -quantity if pos_side == "short" else quantity
            leverage = row.get("lever")
            mark_price = Decimal(str(row["markPx"])) if row.get("markPx") else None
            entry_price = Decimal(str(row["avgPx"])) if row.get("avgPx") else None
            snapshots.append(
                PositionSnapshotPayload(
                    account_id=account.id,
                    exchange=Exchange.OKX,
                    symbol=row["instId"],
                    quantity=signed_quantity,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=Decimal(str(row["upl"])) if row.get("upl") else None,
                    notional_exposure=abs(signed_quantity * mark_price) if mark_price is not None else None,
                    leverage=int(Decimal(str(leverage))) if leverage else account.leverage,
                    margin_mode=row.get("mgnMode"),
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
        pending_path = "/api/v5/trade/orders-pending"
        query = urlencode({"instId": symbol})
        pending_headers = self._signed_headers(
            account=account,
            method="GET",
            path=pending_path,
            query_string=query,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
        )
        pending_response = await self._client.get(f"{self._base_url(account)}{pending_path}?{query}", headers=pending_headers)
        pending_response.raise_for_status()
        pending_data = pending_response.json()
        orders = pending_data.get("data", [])
        if not orders:
            return {"accepted": True, "data": [], "message": "No pending orders."}

        cancel_payload = [{"instId": symbol, "ordId": row["ordId"]} for row in orders if row.get("ordId")]
        path = "/api/v5/trade/cancel-batch-orders"
        body = json.dumps(cancel_payload, separators=(",", ":"))
        headers = self._signed_headers(
            account=account,
            method="POST",
            path=path,
            body=body,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
        )
        response = await self._client.post(f"{self._base_url(account)}{path}", headers=headers, content=body)
        data = response.json()
        return {"accepted": response.is_success and data.get("code") == "0", **data}

    def _base_url(self, account: FollowerAccountModel) -> str:
        return self.settings.okx_base_url

    def private_stream_url(self, account: FollowerAccountModel) -> str:
        base = self.settings.okx_demo_ws_base_url if account.environment in {"TESTNET", "DEMO"} else self.settings.okx_ws_base_url
        return f"{base}/ws/v5/private"

    def ws_login_message(self, api_key: str | None, api_secret: str | None, api_passphrase: str | None) -> dict[str, Any]:
        timestamp = str(int(time.time()))
        message = f"{timestamp}GET/users/self/verify"
        signature = base64.b64encode(
            hmac.new((api_secret or "").encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")
        return {
            "op": "login",
            "args": [
                {
                    "apiKey": api_key or "",
                    "passphrase": api_passphrase or "",
                    "timestamp": timestamp,
                    "sign": signature,
                }
            ],
        }

    def ws_subscribe_message(self) -> dict[str, Any]:
        return {
            "op": "subscribe",
            "args": [
                {"channel": "positions", "instType": "SWAP"},
                {"channel": "orders", "instType": "SWAP"},
            ],
        }

    def _signed_headers(
        self,
        *,
        account: FollowerAccountModel,
        method: str,
        path: str,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None,
        query_string: str = "",
        body: str = "",
    ) -> dict[str, str]:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        request_path = f"{path}?{query_string}" if query_string else path
        message = f"{timestamp}{method.upper()}{request_path}{body}"
        signature = base64.b64encode(
            hmac.new((api_secret or "").encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")
        headers = {
            "OK-ACCESS-KEY": api_key or "",
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": api_passphrase or "",
            "Content-Type": "application/json",
        }
        if account.environment in {"TESTNET", "DEMO"}:
            headers["x-simulated-trading"] = self.settings.okx_demo_header
        return headers

    def _decimal_to_text(self, value: Decimal) -> str:
        return format(value.normalize(), "f")
