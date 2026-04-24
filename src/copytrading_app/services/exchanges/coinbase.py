from __future__ import annotations

import json
import secrets
import time
from decimal import Decimal
from typing import Any

import httpx
import jwt

from copytrading_app.core.config import Settings
from copytrading_app.db.models import FollowerAccountModel
from copytrading_app.domain.enums import Exchange
from copytrading_app.domain.types import HealthCheckResult, OrderRequest, OrderResult, PositionSnapshotPayload


class CoinbaseAdvancedClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(timeout=settings.api_timeout_seconds)

    async def ping(self) -> HealthCheckResult:
        response = await self._client.get(f"{self.settings.coinbase_base_url}/api/v3/brokerage/time")
        return HealthCheckResult(name="coinbase", ok=response.is_success, details={"status_code": response.status_code})

    async def fetch_instruments(self) -> list[dict[str, Any]]:
        response = await self._client.get(f"{self.settings.coinbase_base_url}/api/v3/brokerage/products")
        response.raise_for_status()
        return response.json().get("products", [])

    async def validate_credentials(
        self,
        account: FollowerAccountModel,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> tuple[bool, str | None]:
        path = "/api/v3/brokerage/accounts"
        headers = self._auth_headers(account, "GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        data = response.json()
        if response.is_success and data.get("accounts") is not None:
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
        path = "/api/v3/brokerage/orders"
        order_configuration: dict[str, Any]
        if request.order_type.value == "MARKET":
            order_configuration = {"market_market_ioc": {"base_size": self._decimal_to_text(request.quantity)}}
        else:
            order_configuration = {
                "limit_limit_gtc": {
                    "base_size": self._decimal_to_text(request.quantity),
                    "limit_price": self._decimal_to_text(request.limit_price or Decimal("0")),
                }
            }
        payload = {
            "client_order_id": request.client_order_id or f"tnx-{int(time.time() * 1000)}",
            "product_id": request.symbol,
            "side": request.side,
            "order_configuration": order_configuration,
        }
        body = json.dumps(payload, separators=(",", ":"))
        headers = self._auth_headers(account, "POST", path, api_key, api_secret)
        response = await self._client.post(f"{self._base_url(account)}{path}", headers=headers, content=body)
        data = response.json()
        success = bool(data.get("success")) or response.is_success and data.get("order_id") is not None
        return OrderResult(
            accepted=success,
            external_order_id=data.get("order_id"),
            raw_response=data,
            error_message=None if success else json.dumps(data, ensure_ascii=False),
        )

    async def fetch_position(
        self,
        account: FollowerAccountModel,
        symbol: str,
        api_key: str | None,
        api_secret: str | None,
        api_passphrase: str | None = None,
    ) -> PositionSnapshotPayload:
        path = f"/api/v3/brokerage/cfm/positions/{symbol}"
        headers = self._auth_headers(account, "GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        if response.status_code == 404:
            return PositionSnapshotPayload(
                account_id=account.id,
                exchange=Exchange.COINBASE,
                symbol=symbol,
                quantity=Decimal("0"),
                entry_price=None,
                leverage=account.leverage,
                source="rest",
            )
        response.raise_for_status()
        data = response.json()
        row = data.get("position") or data
        qty = Decimal(str(row.get("number_of_contracts") or row.get("size") or row.get("qty") or "0"))
        side = str(row.get("side", "")).upper()
        if side == "SHORT":
            qty = -abs(qty)
        return PositionSnapshotPayload(
            account_id=account.id,
            exchange=Exchange.COINBASE,
            symbol=symbol,
            quantity=qty,
            entry_price=Decimal(str(row["avg_entry_price"])) if row.get("avg_entry_price") else None,
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
        path = "/api/v3/brokerage/cfm/positions"
        headers = self._auth_headers(account, "GET", path, api_key, api_secret)
        response = await self._client.get(f"{self._base_url(account)}{path}", headers=headers)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()
        rows = data.get("positions") or data.get("results") or data.get("products") or []
        snapshots: list[PositionSnapshotPayload] = []
        for row in rows:
            qty = Decimal(str(row.get("number_of_contracts") or row.get("size") or row.get("qty") or "0"))
            if qty == 0:
                continue
            side = str(row.get("side", "")).upper()
            if side == "SHORT":
                qty = -abs(qty)
            mark_price = Decimal(str(row["mark_price"])) if row.get("mark_price") else None
            entry_price = Decimal(str(row["avg_entry_price"])) if row.get("avg_entry_price") else None
            snapshots.append(
                PositionSnapshotPayload(
                    account_id=account.id,
                    exchange=Exchange.COINBASE,
                    symbol=row.get("product_id") or row.get("symbol"),
                    quantity=qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=Decimal(str(row["unrealized_pnl"])) if row.get("unrealized_pnl") else None,
                    notional_exposure=abs(qty * mark_price) if mark_price is not None else None,
                    leverage=int(Decimal(str(row["leverage"]))) if row.get("leverage") else account.leverage,
                    margin_mode=row.get("margin_type"),
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
        list_path = "/api/v3/brokerage/orders/historical/batch"
        list_headers = self._auth_headers(account, "GET", list_path, api_key, api_secret)
        list_response = await self._client.get(
            f"{self._base_url(account)}{list_path}",
            headers=list_headers,
            params={"product_id": symbol},
        )
        list_response.raise_for_status()
        orders = list_response.json().get("orders", [])
        open_ids = [
            order["order_id"]
            for order in orders
            if str(order.get("status", "")).upper() in {"OPEN", "PENDING", "QUEUED"}
        ]
        if not open_ids:
            return {"accepted": True, "message": "No open orders.", "results": []}

        path = "/api/v3/brokerage/orders/batch_cancel"
        payload = {"order_ids": open_ids}
        body = json.dumps(payload, separators=(",", ":"))
        headers = self._auth_headers(account, "POST", path, api_key, api_secret)
        response = await self._client.post(f"{self._base_url(account)}{path}", headers=headers, content=body)
        data = response.json()
        return {"accepted": response.is_success, **data}

    def _base_url(self, account: FollowerAccountModel) -> str:
        if account.environment in {"TESTNET", "DEMO"}:
            return self.settings.coinbase_sandbox_base_url
        return self.settings.coinbase_base_url

    def private_stream_url(self, account: FollowerAccountModel) -> str:
        if account.environment in {"TESTNET", "DEMO"}:
            return self.settings.coinbase_sandbox_ws_base_url
        return self.settings.coinbase_ws_base_url

    def ws_jwt(self, account: FollowerAccountModel, api_key: str | None, api_secret: str | None) -> str:
        now = int(time.time())
        return jwt.encode(
            {
                "sub": api_key or "",
                "iss": "cdp",
                "nbf": now,
                "exp": now + 120,
            },
            api_secret or "",
            algorithm="ES256",
            headers={"kid": api_key or "", "nonce": secrets.token_hex()},
        )

    def ws_subscribe_message(self, account: FollowerAccountModel, api_key: str | None, api_secret: str | None) -> dict[str, Any]:
        return {
            "type": "subscribe",
            "channel": "user",
            "jwt": self.ws_jwt(account, api_key, api_secret),
        }

    def _auth_headers(
        self,
        account: FollowerAccountModel,
        method: str,
        path: str,
        api_key: str | None,
        api_secret: str | None,
    ) -> dict[str, str]:
        now = int(time.time())
        host = self._base_url(account).replace("https://", "").replace("http://", "")
        token = jwt.encode(
            {
                "sub": api_key or "",
                "iss": "cdp",
                "nbf": now,
                "exp": now + 120,
                "uri": f"{method.upper()} {host}{path}",
            },
            api_secret or "",
            algorithm="ES256",
            headers={"kid": api_key or "", "nonce": secrets.token_hex()},
        )
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _decimal_to_text(self, value: Decimal) -> str:
        return format(value.normalize(), "f")
