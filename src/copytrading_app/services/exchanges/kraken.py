from __future__ import annotations

import base64
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


class KrakenFuturesClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(timeout=settings.api_timeout_seconds)

    async def ping(self) -> HealthCheckResult:
        response = await self._client.get(f"{self.settings.kraken_base_url}/derivatives/api/v3/tickers")
        return HealthCheckResult(name="kraken", ok=response.is_success, details={"status_code": response.status_code})

    async def fetch_instruments(self) -> list[dict[str, Any]]:
        response = await self._client.get(f"{self.settings.kraken_base_url}/derivatives/api/v3/tickers")
        response.raise_for_status()
        return response.json().get("tickers", [])

    async def validate_credentials(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> tuple[bool, str | None]:
        path = "/derivatives/api/v3/checkapikey"
        headers = self._signed_headers("GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        data = response.json()
        if response.is_success and data.get("result") == "success":
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
        path = "/derivatives/api/v3/sendorder"
        payload = {
            "orderType": "mkt" if request.order_type.value == "MARKET" else "lmt",
            "side": "buy" if request.side == "BUY" else "sell",
            "size": self._decimal_to_text(request.quantity),
            "symbol": request.symbol,
        }
        if request.client_order_id:
            payload["cliOrdId"] = request.client_order_id[:64]
        if request.limit_price is not None:
            payload["limitPrice"] = self._decimal_to_text(request.limit_price)
        if request.reduce_only:
            payload["reduceOnly"] = "true"
        body = urlencode(payload)
        headers = self._signed_headers("POST", path, api_key, api_secret, body)
        response = await self._client.post(
            f"{self._base_url(account)}{path}",
            headers=headers,
            content=body,
        )
        data = response.json()
        send_status = data.get("sendStatus", {})
        accepted = response.is_success and data.get("result") == "success" and send_status.get("status") in {"placed", "attempted"}
        return OrderResult(
            accepted=accepted,
            external_order_id=send_status.get("order_id") or send_status.get("orderId"),
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
        path = "/derivatives/api/v3/openpositions"
        headers = self._signed_headers("GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        response.raise_for_status()
        data = response.json()
        rows = data.get("openPositions") or data.get("positions") or []
        row = next(
            (item for item in rows if item.get("symbol") == symbol or item.get("product_id") == symbol),
            {},
        )
        qty = Decimal(str(row.get("size", "0")))
        side = str(row.get("side", "")).lower()
        signed_qty = -qty if side == "short" else qty
        return PositionSnapshotPayload(
            account_id=account.id,
            exchange=Exchange.KRAKEN,
            symbol=symbol,
            quantity=signed_qty,
            entry_price=Decimal(str(row["price"])) if row.get("price") else None,
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
        path = "/derivatives/api/v3/openpositions"
        headers = self._signed_headers("GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        response.raise_for_status()
        data = response.json()
        rows = data.get("openPositions") or data.get("positions") or []
        snapshots: list[PositionSnapshotPayload] = []
        for row in rows:
            qty = Decimal(str(row.get("size", "0")))
            if qty == 0:
                continue
            side = str(row.get("side", "")).lower()
            signed_qty = -qty if side == "short" else qty
            mark_price = Decimal(str(row["markPrice"])) if row.get("markPrice") else None
            entry_price = Decimal(str(row["price"])) if row.get("price") else None
            snapshots.append(
                PositionSnapshotPayload(
                    account_id=account.id,
                    exchange=Exchange.KRAKEN,
                    symbol=row.get("symbol") or row.get("product_id"),
                    quantity=signed_qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=Decimal(str(row["unrealizedFunding"])) if row.get("unrealizedFunding") else None,
                    notional_exposure=abs(signed_qty * mark_price) if mark_price is not None else None,
                    leverage=int(Decimal(str(row["leverage"]))) if row.get("leverage") else account.leverage,
                    margin_mode=row.get("marginAccount"),
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
        path = "/derivatives/api/v3/cancelallorders"
        body = urlencode({"symbol": symbol})
        headers = self._signed_headers("POST", path, api_key, api_secret, body)
        response = await self._client.post(f"{self._base_url(account)}{path}", headers=headers, content=body)
        data = response.json()
        return {"accepted": response.is_success and data.get("result") == "success", **data}

    def _base_url(self, account: FollowerAccountModel) -> str:
        if account.environment in {"TESTNET", "DEMO"}:
            return self.settings.kraken_demo_base_url
        return self.settings.kraken_base_url

    def private_stream_url(self, account: FollowerAccountModel) -> str:
        if account.environment in {"TESTNET", "DEMO"}:
            return self.settings.kraken_demo_ws_base_url
        return self.settings.kraken_ws_base_url

    async def create_ws_challenge(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
    ) -> str:
        path = "/derivatives/api/v3/getchallenge"
        headers = self._signed_headers("GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("challenge", "")

    def ws_signed_challenge(self, challenge: str, api_secret: str | None) -> str:
        decoded_secret = base64.b64decode(api_secret or "")
        return base64.b64encode(hmac.new(decoded_secret, challenge.encode("utf-8"), hashlib.sha512).digest()).decode("utf-8")

    def ws_subscribe_messages(self, api_key: str | None, challenge: str, signed_challenge: str) -> list[dict[str, Any]]:
        auth_payload = {
            "event": "subscribe",
            "feed": "open_positions",
            "api_key": api_key or "",
            "original_challenge": challenge,
            "signed_challenge": signed_challenge,
        }
        order_payload = {
            "event": "subscribe",
            "feed": "fills",
            "api_key": api_key or "",
            "original_challenge": challenge,
            "signed_challenge": signed_challenge,
        }
        return [auth_payload, order_payload]

    def _signed_headers(
        self,
        method: str,
        path: str,
        api_key: str | None,
        api_secret: str | None,
        body: str = "",
    ) -> dict[str, str]:
        nonce = str(int(time.time() * 1000))
        sha256_hash = hashlib.sha256((body + nonce + path).encode("utf-8")).digest()
        decoded_secret = base64.b64decode(api_secret or "")
        signature = base64.b64encode(hmac.new(decoded_secret, sha256_hash, hashlib.sha512).digest()).decode("utf-8")
        return {
            "APIKey": api_key or "",
            "Nonce": nonce,
            "Authent": signature,
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        }

    def _decimal_to_text(self, value: Decimal) -> str:
        return format(value.normalize(), "f")
