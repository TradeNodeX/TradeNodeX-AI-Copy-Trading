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


class GateIoFuturesClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(timeout=settings.api_timeout_seconds)

    async def ping(self) -> HealthCheckResult:
        response = await self._client.get(f"{self.settings.gateio_base_url}/api/v4/futures/usdt/contracts")
        return HealthCheckResult(name="gateio", ok=response.is_success, details={"status_code": response.status_code})

    async def fetch_instruments(self) -> list[dict[str, Any]]:
        response = await self._client.get(f"{self.settings.gateio_base_url}/api/v4/futures/usdt/contracts")
        response.raise_for_status()
        return response.json()

    async def validate_credentials(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> tuple[bool, str | None]:
        path = "/api/v4/futures/usdt/accounts"
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
        path = "/api/v4/futures/usdt/orders"
        signed_size = request.quantity if request.side == "BUY" else -request.quantity
        payload: dict[str, Any] = {
            "contract": request.symbol,
            "size": int(signed_size) if signed_size == signed_size.to_integral_value() else float(signed_size),
            "reduce_only": request.reduce_only,
        }
        if request.order_type.value == "MARKET":
            payload["price"] = "0"
            payload["tif"] = "ioc"
        else:
            payload["price"] = self._decimal_to_text(request.limit_price or Decimal("0"))
            payload["tif"] = "gtc"
        if request.client_order_id:
            payload["text"] = f"t-{request.client_order_id[:24]}"
        body = json.dumps(payload, separators=(",", ":"))
        headers = self._signed_headers("POST", path, api_key, api_secret, body=body)
        response = await self._client.post(f"{self._base_url(account)}{path}", headers=headers, content=body)
        data = response.json()
        accepted = response.is_success and data.get("id") is not None
        return OrderResult(
            accepted=accepted,
            external_order_id=str(data.get("id")) if accepted else None,
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
        path = f"/api/v4/futures/usdt/positions/{symbol}"
        headers = self._signed_headers("GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        response.raise_for_status()
        row = response.json()
        qty = Decimal(str(row.get("size", "0")))
        return PositionSnapshotPayload(
            account_id=account.id,
            exchange=Exchange.GATEIO,
            symbol=symbol,
            quantity=qty,
            entry_price=Decimal(str(row["entry_price"])) if row.get("entry_price") else None,
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
        path = "/api/v4/futures/usdt/positions"
        headers = self._signed_headers("GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        response.raise_for_status()
        snapshots: list[PositionSnapshotPayload] = []
        for row in response.json():
            qty = Decimal(str(row.get("size", "0")))
            if qty == 0:
                continue
            mark_price = Decimal(str(row["mark_price"])) if row.get("mark_price") else None
            entry_price = Decimal(str(row["entry_price"])) if row.get("entry_price") else None
            snapshots.append(
                PositionSnapshotPayload(
                    account_id=account.id,
                    exchange=Exchange.GATEIO,
                    symbol=row.get("contract") or row.get("name"),
                    quantity=qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=Decimal(str(row["unrealised_pnl"])) if row.get("unrealised_pnl") else None,
                    notional_exposure=abs(qty * mark_price) if mark_price is not None else None,
                    leverage=int(Decimal(str(row["leverage"]))) if row.get("leverage") else account.leverage,
                    margin_mode=row.get("mode"),
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
        query_string = urlencode({"contract": symbol})
        path = "/api/v4/futures/usdt/orders"
        headers = self._signed_headers("DELETE", path, api_key, api_secret, query_string=query_string)
        response = await self._client.delete(f"{self._base_url(account)}{path}?{query_string}", headers=headers)
        data = response.json()
        return {"accepted": response.is_success, "data": data}

    def _base_url(self, account: FollowerAccountModel) -> str:
        if account.environment in {"TESTNET", "DEMO"}:
            return self.settings.gateio_testnet_base_url
        return self.settings.gateio_base_url

    def private_stream_url(self, account: FollowerAccountModel) -> str:
        if account.environment in {"TESTNET", "DEMO"}:
            return self.settings.gateio_testnet_ws_base_url
        return self.settings.gateio_ws_base_url

    def ws_login_message(self, api_key: str | None, api_secret: str | None) -> dict[str, Any]:
        event_time = int(time.time())
        channel = "futures.login"
        signature_payload = f"{channel}\napi\n\n{event_time}"
        signature = hmac.new((api_secret or "").encode("utf-8"), signature_payload.encode("utf-8"), hashlib.sha512).hexdigest()
        return {
            "time": event_time,
            "channel": channel,
            "event": "api",
            "payload": {"api_key": api_key or "", "signature": signature, "timestamp": str(event_time)},
        }

    def ws_subscribe_messages(self) -> list[dict[str, Any]]:
        event_time = int(time.time())
        return [
            {"time": event_time, "channel": "futures.positions", "event": "subscribe", "payload": []},
            {"time": event_time, "channel": "futures.orders", "event": "subscribe", "payload": []},
            {"time": event_time, "channel": "futures.usertrades", "event": "subscribe", "payload": []},
        ]

    def _signed_headers(
        self,
        method: str,
        path: str,
        api_key: str | None,
        api_secret: str | None,
        *,
        query_string: str = "",
        body: str = "",
    ) -> dict[str, str]:
        timestamp = str(int(time.time()))
        payload_hash = hashlib.sha512(body.encode("utf-8")).hexdigest()
        sign_string = "\n".join([method.upper(), path, query_string, payload_hash, timestamp])
        signature = hmac.new((api_secret or "").encode("utf-8"), sign_string.encode("utf-8"), hashlib.sha512).hexdigest()
        return {
            "KEY": api_key or "",
            "Timestamp": timestamp,
            "SIGN": signature,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _decimal_to_text(self, value: Decimal) -> str:
        return format(value.normalize(), "f")
