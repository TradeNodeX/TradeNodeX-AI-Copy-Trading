from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import websockets
from sqlalchemy import select

from copytrading_app.core.dependencies import build_container
from copytrading_app.db.models import SignalSourceModel
from copytrading_app.domain.enums import Exchange


@dataclass
class ValidationResult:
    exchange: str
    source_name: str
    source_account: str
    environment: str
    configured: bool
    credential_ok: bool
    stream_ok: bool
    mode: str
    details: str


def _source_proxy(source: SignalSourceModel) -> SimpleNamespace:
    return SimpleNamespace(
        id=source.id,
        environment=source.environment,
        margin_mode=source.margin_mode,
        leverage=source.default_leverage,
        hedge_mode=source.hedge_mode,
    )


async def _recv_json(ws, timeout_seconds: float) -> dict[str, Any]:
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


async def _validate_okx(source: SignalSourceModel, client, api_key: str, api_secret: str, api_passphrase: str | None) -> tuple[bool, str]:
    proxy = _source_proxy(source)
    async with websockets.connect(client.private_stream_url(proxy), ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps(client.ws_login_message(api_key, api_secret, api_passphrase)))
        login = await _recv_json(ws, 8)
        if login.get("event") == "error":
            return False, login.get("msg") or "OKX login error"
        await ws.send(json.dumps(client.ws_subscribe_message()))
        for _ in range(4):
            message = await _recv_json(ws, 8)
            if message.get("event") == "error":
                return False, message.get("msg") or "OKX subscribe error"
            if message.get("event") == "subscribe" or message.get("arg", {}).get("channel") in {"positions", "orders", "orders-algo"}:
                return True, "OKX private stream login + subscribe acknowledged"
    return False, "OKX private stream timed out waiting for subscribe ack"


async def _validate_kraken(source: SignalSourceModel, client, api_key: str, api_secret: str, api_passphrase: str | None) -> tuple[bool, str]:
    proxy = _source_proxy(source)
    challenge = await client.create_ws_challenge(proxy, api_key, api_secret)
    signed = client.ws_signed_challenge(challenge, api_secret)
    async with websockets.connect(client.private_stream_url(proxy), ping_interval=20, ping_timeout=20) as ws:
        for message in client.ws_subscribe_messages(api_key, challenge, signed):
            await ws.send(json.dumps(message))
        for _ in range(6):
            payload = await _recv_json(ws, 8)
            if payload.get("event") == "alert":
                return False, payload.get("message") or "Kraken websocket alert"
            if payload.get("event") in {"subscribed", "subscriptionStatus"}:
                return True, "Kraken private stream subscribed"
            if payload.get("feed") in {"open_positions", "fills"}:
                return True, f"Kraken private stream received {payload.get('feed')}"
    return False, "Kraken private stream timed out waiting for subscription confirmation"


async def _validate_bitmex(source: SignalSourceModel, client, api_key: str, api_secret: str, api_passphrase: str | None) -> tuple[bool, str]:
    proxy = _source_proxy(source)
    async with websockets.connect(client.private_stream_url(proxy), ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps(client.ws_auth_message(api_key, api_secret)))
        auth = await _recv_json(ws, 8)
        if auth.get("error"):
            return False, str(auth["error"])
        await ws.send(json.dumps(client.ws_subscribe_message()))
        for _ in range(5):
            payload = await _recv_json(ws, 8)
            if payload.get("error"):
                return False, str(payload["error"])
            if payload.get("success") is True or payload.get("subscribe") in {"position", "order", "execution"} or payload.get("table") in {"position", "order", "execution"}:
                return True, "BitMEX private stream auth + subscribe acknowledged"
    return False, "BitMEX private stream timed out waiting for subscribe ack"


async def _validate_gateio(source: SignalSourceModel, client, api_key: str, api_secret: str, api_passphrase: str | None) -> tuple[bool, str]:
    proxy = _source_proxy(source)
    async with websockets.connect(client.private_stream_url(proxy), ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps(client.ws_login_message(api_key, api_secret)))
        login = await _recv_json(ws, 8)
        if login.get("event") == "error":
            return False, login.get("error", {}).get("message") or "Gate.io login error"
        for message in client.ws_subscribe_messages():
            await ws.send(json.dumps(message))
        for _ in range(6):
            payload = await _recv_json(ws, 8)
            if payload.get("event") == "error":
                return False, payload.get("error", {}).get("message") or "Gate.io subscribe error"
            if payload.get("event") == "subscribe" or payload.get("channel") in {"futures.positions", "futures.orders", "futures.usertrades"}:
                return True, "Gate.io private stream login + subscribe acknowledged"
    return False, "Gate.io private stream timed out waiting for subscribe ack"


async def _validate_coinbase(source: SignalSourceModel, client, api_key: str, api_secret: str, api_passphrase: str | None) -> tuple[bool, str]:
    proxy = _source_proxy(source)
    async with websockets.connect(client.private_stream_url(proxy), ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps(client.ws_subscribe_message(proxy, api_key, api_secret)))
        for _ in range(5):
            payload = await _recv_json(ws, 8)
            if payload.get("type") == "error":
                return False, payload.get("message") or "Coinbase websocket error"
            if payload.get("type") in {"subscriptions", "subscribed"} or payload.get("channel") == "user":
                return True, "Coinbase private stream subscribed to user channel"
    return False, "Coinbase private stream timed out waiting for subscribe ack"


async def _validate_binance(source: SignalSourceModel, client, api_key: str, api_secret: str, api_passphrase: str | None) -> tuple[bool, str]:
    listen_key = await client.create_listen_key(api_key)
    async with websockets.connect(client.user_stream_url(listen_key), ping_interval=20, ping_timeout=20) as ws:
        payload = await _recv_json(ws, 10)
        return True, f"Binance private stream connected ({payload.get('e', 'connected')})"


async def _validate_bybit(source: SignalSourceModel, client, api_key: str, api_secret: str, api_passphrase: str | None) -> tuple[bool, str]:
    async with websockets.connect(client.private_stream_url(), ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps(client.auth_message(api_key, api_secret)))
        auth = await _recv_json(ws, 8)
        if auth.get("success") is False:
            return False, auth.get("ret_msg") or "Bybit auth error"
        await ws.send(json.dumps({"op": "subscribe", "args": ["position", "execution", "order"]}))
        payload = await _recv_json(ws, 8)
        if payload.get("success") is False:
            return False, payload.get("ret_msg") or "Bybit subscribe error"
        return True, "Bybit private stream auth + subscribe acknowledged"


VALIDATORS = {
    Exchange.BINANCE: _validate_binance,
    Exchange.BYBIT: _validate_bybit,
    Exchange.OKX: _validate_okx,
    Exchange.KRAKEN: _validate_kraken,
    Exchange.BITMEX: _validate_bitmex,
    Exchange.GATEIO: _validate_gateio,
    Exchange.COINBASE: _validate_coinbase,
}


async def validate_source(container, source: SignalSourceModel) -> ValidationResult:
    exchange = Exchange(source.exchange)
    client = container.exchange_clients[exchange]
    proxy = _source_proxy(source)
    api_key = await container.secret_cipher.decrypt(source.api_key_ciphertext)
    api_secret = await container.secret_cipher.decrypt(source.api_secret_ciphertext)
    api_passphrase = await container.secret_cipher.decrypt(source.api_passphrase_ciphertext)
    if not api_key or not api_secret:
        return ValidationResult(
            exchange=source.exchange,
            source_name=source.name,
            source_account=source.source_account,
            environment=source.environment,
            configured=False,
            credential_ok=False,
            stream_ok=False,
            mode="not-configured",
            details="Missing API key or API secret in configured signal source.",
        )
    credential_ok, message = await client.validate_credentials(proxy, api_key, api_secret, api_passphrase)
    if not credential_ok:
        return ValidationResult(
            exchange=source.exchange,
            source_name=source.name,
            source_account=source.source_account,
            environment=source.environment,
            configured=True,
            credential_ok=False,
            stream_ok=False,
            mode="credential-failed",
            details=message or "Credential validation failed.",
        )
    validator = VALIDATORS.get(exchange)
    if validator is None:
        return ValidationResult(
            exchange=source.exchange,
            source_name=source.name,
            source_account=source.source_account,
            environment=source.environment,
            configured=True,
            credential_ok=True,
            stream_ok=False,
            mode="unsupported",
            details="No stream validator is implemented for this exchange.",
        )
    try:
        stream_ok, details = await validator(source, client, api_key, api_secret, api_passphrase)
        return ValidationResult(
            exchange=source.exchange,
            source_name=source.name,
            source_account=source.source_account,
            environment=source.environment,
            configured=True,
            credential_ok=True,
            stream_ok=stream_ok,
            mode="private-websocket" if stream_ok else "stream-failed",
            details=details,
        )
    except Exception as exc:  # noqa: BLE001
        return ValidationResult(
            exchange=source.exchange,
            source_name=source.name,
            source_account=source.source_account,
            environment=source.environment,
            configured=True,
            credential_ok=True,
            stream_ok=False,
            mode="stream-failed",
            details=str(exc),
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate configured TradeNodeX master private streams.")
    parser.add_argument(
        "--exchange",
        action="append",
        choices=[exchange.value for exchange in Exchange],
        help="Exchange(s) to validate. Repeat for multiple exchanges.",
    )
    return parser.parse_args()


async def _run() -> int:
    args = _parse_args()
    container = build_container()
    await container.init_models()
    try:
        async with container.session_factory() as session:
            rows = (await session.execute(select(SignalSourceModel).order_by(SignalSourceModel.exchange, SignalSourceModel.name))).scalars().all()
        selected = {exchange.upper() for exchange in (args.exchange or [])}
        if selected:
            rows = [row for row in rows if row.exchange.upper() in selected]
        requested_exchanges = selected or {exchange.value for exchange in Exchange}
        present_exchanges = {row.exchange.upper() for row in rows}
        for exchange in sorted(requested_exchanges - present_exchanges):
            print(f"[{exchange}] no configured signal source found in local database")
        if not rows:
            return 1
        failures = 0
        for source in rows:
            result = await validate_source(container, source)
            status = "OK" if result.credential_ok and result.stream_ok else "BLOCKED"
            print(
                f"[{status}] {result.exchange} | {result.source_name} | {result.environment} | "
                f"{result.mode} | {result.details}"
            )
            if not (result.credential_ok and result.stream_ok):
                failures += 1
        return 0 if failures == 0 else 2
    finally:
        await container.shutdown()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
