from __future__ import annotations

import base64
import json
from decimal import Decimal

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from copytrading_app.core.config import Settings
from copytrading_app.db.models import FollowerAccountModel
from copytrading_app.domain.enums import MarginMode, RuntimeEnvironment
from copytrading_app.domain.types import OrderRequest
from copytrading_app.services.exchanges.bitmex import BitmexClient
from copytrading_app.services.exchanges.coinbase import CoinbaseAdvancedClient
from copytrading_app.services.exchanges.gateio import GateIoFuturesClient
from copytrading_app.services.exchanges.kraken import KrakenFuturesClient
from copytrading_app.services.exchanges.okx import OkxSwapClient


def build_settings() -> Settings:
    return Settings(
        okx_base_url="https://okx.test",
        kraken_base_url="https://kraken.test",
        kraken_demo_base_url="https://kraken-demo.test",
        bitmex_base_url="https://bitmex.test",
        bitmex_testnet_base_url="https://bitmex-demo.test",
        gateio_base_url="https://gate.test",
        gateio_testnet_base_url="https://gate-demo.test",
        coinbase_base_url="https://coinbase.test",
        coinbase_sandbox_base_url="https://coinbase-sandbox.test",
    )


def build_account(exchange: str, environment: RuntimeEnvironment = RuntimeEnvironment.TESTNET) -> FollowerAccountModel:
    return FollowerAccountModel(
        id="acc-1",
        name=f"{exchange.lower()}-account",
        exchange=exchange,
        environment=environment.value,
        leverage=5,
        margin_mode=MarginMode.ISOLATED.value,
        hedge_mode=False,
    )


def build_coinbase_private_key() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


@pytest.mark.asyncio
async def test_okx_client_supports_private_actions() -> None:
    settings = build_settings()
    account = build_account("OKX", RuntimeEnvironment.DEMO)
    requests: list[tuple[str, str, dict[str, str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, str(request.url), dict(request.headers)))
        if request.url.path == "/api/v5/account/balance":
            return httpx.Response(200, json={"code": "0", "data": [{"details": []}]})
        if request.url.path == "/api/v5/trade/order":
            return httpx.Response(200, json={"code": "0", "data": [{"ordId": "okx-1"}]})
        if request.url.path == "/api/v5/account/positions":
            return httpx.Response(200, json={"code": "0", "data": [{"pos": "2", "avgPx": "123.4", "lever": "10", "posSide": "long"}]})
        if request.url.path == "/api/v5/trade/orders-pending":
            return httpx.Response(200, json={"code": "0", "data": [{"ordId": "p-1"}]})
        if request.url.path == "/api/v5/trade/cancel-batch-orders":
            return httpx.Response(200, json={"code": "0", "data": [{"ordId": "p-1", "sCode": "0"}]})
        raise AssertionError(f"Unhandled path: {request.url.path}")

    client = OkxSwapClient(settings)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    ok, message = await client.validate_credentials(account, "key", "secret", "pass")
    assert ok is True
    assert message is None

    order = await client.place_order(
        account,
        OrderRequest(symbol="BTC-USDT-SWAP", side="BUY", quantity=Decimal("1")),
        "key",
        "secret",
        "pass",
    )
    assert order.accepted is True
    assert order.external_order_id == "okx-1"

    position = await client.fetch_position(account, "BTC-USDT-SWAP", "key", "secret", "pass")
    assert position.quantity == Decimal("2")

    canceled = await client.cancel_orders(account, "BTC-USDT-SWAP", "key", "secret", "pass")
    assert canceled["accepted"] is True
    assert any(headers.get("x-simulated-trading") == settings.okx_demo_header for _, _, headers in requests)
    assert client.private_stream_url(account).endswith("/ws/v5/private")
    assert client.ws_login_message("key", "secret", "pass")["op"] == "login"
    assert client.ws_subscribe_message()["op"] == "subscribe"

    await client._client.aclose()


@pytest.mark.asyncio
async def test_kraken_client_supports_private_actions() -> None:
    settings = build_settings()
    account = build_account("KRAKEN")
    secret = base64.b64encode(b"kraken-secret").decode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/checkapikey"):
            return httpx.Response(200, json={"result": "success"})
        if request.url.path.endswith("/sendorder"):
            return httpx.Response(200, json={"result": "success", "sendStatus": {"status": "placed", "order_id": "kraken-1"}})
        if request.url.path.endswith("/openpositions"):
            return httpx.Response(200, json={"openPositions": [{"symbol": "PI_XBTUSD", "size": "3", "side": "long", "price": "101", "leverage": "5"}]})
        if request.url.path.endswith("/cancelallorders"):
            return httpx.Response(200, json={"result": "success"})
        raise AssertionError(f"Unhandled path: {request.url.path}")

    client = KrakenFuturesClient(settings)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    ok, _ = await client.validate_credentials(account, "key", secret)
    assert ok is True

    order = await client.place_order(account, OrderRequest(symbol="PI_XBTUSD", side="BUY", quantity=Decimal("1")), "key", secret)
    assert order.accepted is True

    position = await client.fetch_position(account, "PI_XBTUSD", "key", secret)
    assert position.quantity == Decimal("3")

    canceled = await client.cancel_orders(account, "PI_XBTUSD", "key", secret)
    assert canceled["accepted"] is True
    assert client.private_stream_url(account).endswith("/ws/v1")
    challenge_signature = client.ws_signed_challenge("challenge", secret)
    assert isinstance(challenge_signature, str)
    assert len(client.ws_subscribe_messages("key", "challenge", challenge_signature)) == 2

    await client._client.aclose()


@pytest.mark.asyncio
async def test_bitmex_client_supports_private_actions() -> None:
    settings = build_settings()
    account = build_account("BITMEX")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/user/walletSummary":
            return httpx.Response(200, json={"currency": "XBt"})
        if request.url.path == "/api/v1/order":
            return httpx.Response(200, json={"orderID": "bitmex-1", "ordStatus": "New"})
        if request.url.path == "/api/v1/position":
            return httpx.Response(200, json=[{"symbol": "XBTUSD", "currentQty": "4", "avgEntryPrice": "100", "leverage": "5"}])
        if request.url.path == "/api/v1/order/all":
            return httpx.Response(200, json=[{"orderID": "bitmex-1"}])
        raise AssertionError(f"Unhandled path: {request.url.path}")

    client = BitmexClient(settings)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    ok, _ = await client.validate_credentials(account, "key", "secret")
    assert ok is True
    order = await client.place_order(account, OrderRequest(symbol="XBTUSD", side="BUY", quantity=Decimal("1")), "key", "secret")
    assert order.accepted is True
    position = await client.fetch_position(account, "XBTUSD", "key", "secret")
    assert position.quantity == Decimal("4")
    canceled = await client.cancel_orders(account, "XBTUSD", "key", "secret")
    assert canceled["accepted"] is True
    assert client.private_stream_url(account).endswith("/realtime")
    assert client.ws_auth_message("key", "secret")["op"] == "authKeyExpires"
    assert client.ws_subscribe_message()["op"] == "subscribe"

    await client._client.aclose()


@pytest.mark.asyncio
async def test_gateio_client_supports_private_actions() -> None:
    settings = build_settings()
    account = build_account("GATEIO")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v4/futures/usdt/accounts":
            return httpx.Response(200, json={"user": "gate"})
        if request.url.path == "/api/v4/futures/usdt/orders" and request.method == "POST":
            return httpx.Response(200, json={"id": 12})
        if request.url.path == "/api/v4/futures/usdt/positions/BTC_USDT":
            return httpx.Response(200, json={"size": "5", "entry_price": "111", "leverage": "10"})
        if request.url.path == "/api/v4/futures/usdt/orders" and request.method == "DELETE":
            return httpx.Response(200, json=[{"id": 12}])
        raise AssertionError(f"Unhandled path: {request.method} {request.url.path}")

    client = GateIoFuturesClient(settings)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    ok, _ = await client.validate_credentials(account, "key", "secret")
    assert ok is True
    order = await client.place_order(account, OrderRequest(symbol="BTC_USDT", side="BUY", quantity=Decimal("1")), "key", "secret")
    assert order.accepted is True
    position = await client.fetch_position(account, "BTC_USDT", "key", "secret")
    assert position.quantity == Decimal("5")
    canceled = await client.cancel_orders(account, "BTC_USDT", "key", "secret")
    assert canceled["accepted"] is True
    assert client.private_stream_url(account).endswith("/v4/ws/usdt")
    assert client.ws_login_message("key", "secret")["channel"] == "futures.login"
    assert len(client.ws_subscribe_messages()) == 3

    await client._client.aclose()


@pytest.mark.asyncio
async def test_coinbase_advanced_client_supports_private_actions() -> None:
    settings = build_settings()
    account = build_account("COINBASE")
    private_key = build_coinbase_private_key()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"].startswith("Bearer ")
        if request.url.path == "/api/v3/brokerage/accounts":
            return httpx.Response(200, json={"accounts": [{"uuid": "acc"}]})
        if request.url.path == "/api/v3/brokerage/orders":
            return httpx.Response(200, json={"success": True, "order_id": "cb-1"})
        if request.url.path == "/api/v3/brokerage/cfm/positions/BTC-USD":
            return httpx.Response(200, json={"position": {"number_of_contracts": "2", "avg_entry_price": "120", "leverage": "3", "side": "LONG"}})
        if request.url.path == "/api/v3/brokerage/orders/historical/batch":
            return httpx.Response(200, json={"orders": [{"order_id": "cb-1", "status": "OPEN"}]})
        if request.url.path == "/api/v3/brokerage/orders/batch_cancel":
            return httpx.Response(200, json={"results": [{"success": True}]})
        raise AssertionError(f"Unhandled path: {request.url.path}")

    client = CoinbaseAdvancedClient(settings)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    ok, _ = await client.validate_credentials(account, "organizations/test/apiKeys/key", private_key)
    assert ok is True
    order = await client.place_order(account, OrderRequest(symbol="BTC-USD", side="BUY", quantity=Decimal("1")), "organizations/test/apiKeys/key", private_key)
    assert order.accepted is True
    position = await client.fetch_position(account, "BTC-USD", "organizations/test/apiKeys/key", private_key)
    assert position.quantity == Decimal("2")
    canceled = await client.cancel_orders(account, "BTC-USD", "organizations/test/apiKeys/key", private_key)
    assert canceled["accepted"] is True
    assert "advanced-trade-ws" in client.private_stream_url(account)
    subscribe_message = client.ws_subscribe_message(account, "organizations/test/apiKeys/key", private_key)
    assert subscribe_message["type"] == "subscribe"
    assert subscribe_message["channel"] == "user"
    assert isinstance(subscribe_message["jwt"], str)

    await client._client.aclose()
