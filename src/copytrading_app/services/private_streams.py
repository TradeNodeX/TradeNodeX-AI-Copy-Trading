from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import websockets

from copytrading_app.core.dependencies import AppContainer
from copytrading_app.db.models import SignalSourceModel
from copytrading_app.domain.enums import Exchange, LogType, SignalSourceStatus
from copytrading_app.domain.types import PositionSnapshotPayload, utc_now
from copytrading_app.repositories.signal_repository import SignalRepository
from copytrading_app.schemas.api import MasterEventIn
from copytrading_app.services.master_listener import MasterListenerService


class MasterStreamSupervisor:
    def __init__(self, container: AppContainer):
        self.container = container
        self._position_cache: dict[str, dict[str, Decimal]] = defaultdict(dict)

    async def run_forever(self, poll_interval_seconds: float = 15.0) -> None:
        while True:
            async with self.container.session_factory() as session:
                signal_sources = await self.container.orchestrator(session).signal_repository.list_signal_sources()
            active_sources = [
                source
                for source in signal_sources
                if source.status == SignalSourceStatus.ACTIVE.value
                and source.api_key_ciphertext
                and source.api_secret_ciphertext
            ]
            if not active_sources:
                await asyncio.sleep(poll_interval_seconds)
                continue
            tasks = [asyncio.create_task(self._monitor_source(source, poll_interval_seconds)) for source in active_sources]
            try:
                await asyncio.gather(*tasks)
            finally:
                for task in tasks:
                    task.cancel()

    async def _monitor_source(self, signal_source: SignalSourceModel, poll_interval_seconds: float) -> None:
        while True:
            try:
                exchange = Exchange(signal_source.exchange)
                if exchange == Exchange.BINANCE:
                    await self._listen_binance(signal_source)
                elif exchange == Exchange.BYBIT:
                    await self._listen_bybit(signal_source)
                elif exchange == Exchange.OKX:
                    await self._listen_with_poll_fallback(signal_source, poll_interval_seconds, self._listen_okx)
                elif exchange == Exchange.KRAKEN:
                    await self._listen_with_poll_fallback(signal_source, poll_interval_seconds, self._listen_kraken)
                elif exchange == Exchange.BITMEX:
                    await self._listen_with_poll_fallback(signal_source, poll_interval_seconds, self._listen_bitmex)
                elif exchange == Exchange.GATEIO:
                    await self._listen_with_poll_fallback(signal_source, poll_interval_seconds, self._listen_gateio)
                elif exchange == Exchange.COINBASE:
                    await self._listen_with_poll_fallback(signal_source, poll_interval_seconds, self._listen_coinbase)
                else:
                    await self._poll_positions(signal_source, poll_interval_seconds)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await self._set_listener_state(
                    signal_source.id,
                    stream_status="ERROR",
                    listener_status="ERROR",
                    validation_message=str(exc),
                )
                await self._log(
                    signal_source.exchange,
                    signal_source.name,
                    f"{signal_source.exchange} source listener error: {exc}",
                    {"signal_source_id": signal_source.id},
                    log_type=LogType.ERROR,
                )
                await asyncio.sleep(5)

    async def _listen_with_poll_fallback(self, signal_source: SignalSourceModel, poll_interval_seconds: float, listener) -> None:
        try:
            await listener(signal_source, poll_interval_seconds)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self._log(
                signal_source.exchange,
                signal_source.name,
                f"{signal_source.exchange} private websocket unavailable, falling back to REST reconciliation: {exc}",
                {"signal_source_id": signal_source.id},
                log_type=LogType.WARNING,
            )
            await self._poll_positions(signal_source, poll_interval_seconds)

    async def _listen_okx(self, signal_source: SignalSourceModel, poll_interval_seconds: float) -> None:
        client = self.container.exchange_clients[Exchange.OKX]
        account = self._source_account_proxy(signal_source)
        api_key = await self.container.secret_cipher.decrypt(signal_source.api_key_ciphertext)
        api_secret = await self.container.secret_cipher.decrypt(signal_source.api_secret_ciphertext)
        api_passphrase = await self.container.secret_cipher.decrypt(signal_source.api_passphrase_ciphertext)
        async with websockets.connect(client.private_stream_url(account), ping_interval=20, ping_timeout=20) as ws:
            await ws.send(json.dumps(client.ws_login_message(api_key, api_secret, api_passphrase)))
            await ws.send(json.dumps(client.ws_subscribe_message()))
            await self._set_listener_state(signal_source.id, stream_status="CONNECTED", listener_status="RUNNING")
            await self._log(signal_source.exchange, signal_source.name, f"Connected OKX private stream for {signal_source.name}.", {})
            while True:
                raw = await ws.recv()
                message = json.loads(raw)
                if message.get("event") == "error":
                    raise RuntimeError(message.get("msg") or "OKX websocket error")
                if message.get("arg", {}).get("channel") == "positions":
                    await self._handle_okx_positions(signal_source, message)
                elif message.get("arg", {}).get("channel") in {"orders", "orders-algo"}:
                    await self._refresh_positions_from_rest(signal_source, poll_interval_seconds, origin="OKX_WS")

    async def _listen_kraken(self, signal_source: SignalSourceModel, poll_interval_seconds: float) -> None:
        client = self.container.exchange_clients[Exchange.KRAKEN]
        account = self._source_account_proxy(signal_source)
        api_key = await self.container.secret_cipher.decrypt(signal_source.api_key_ciphertext)
        api_secret = await self.container.secret_cipher.decrypt(signal_source.api_secret_ciphertext)
        challenge = await client.create_ws_challenge(account, api_key, api_secret)
        signed_challenge = client.ws_signed_challenge(challenge, api_secret)
        async with websockets.connect(client.private_stream_url(account), ping_interval=20, ping_timeout=20) as ws:
            for message in client.ws_subscribe_messages(api_key, challenge, signed_challenge):
                await ws.send(json.dumps(message))
            await self._set_listener_state(signal_source.id, stream_status="CONNECTED", listener_status="RUNNING")
            await self._log(signal_source.exchange, signal_source.name, f"Connected Kraken private stream for {signal_source.name}.", {})
            while True:
                raw = await ws.recv()
                message = json.loads(raw)
                if message.get("event") == "alert":
                    raise RuntimeError(message.get("message") or "Kraken websocket error")
                feed = message.get("feed")
                if feed == "open_positions":
                    await self._handle_kraken_positions(signal_source, message)
                elif feed in {"fills", "open_orders", "orders"}:
                    await self._refresh_positions_from_rest(signal_source, poll_interval_seconds, origin="KRAKEN_WS")

    async def _listen_bitmex(self, signal_source: SignalSourceModel, poll_interval_seconds: float) -> None:
        client = self.container.exchange_clients[Exchange.BITMEX]
        account = self._source_account_proxy(signal_source)
        api_key = await self.container.secret_cipher.decrypt(signal_source.api_key_ciphertext)
        api_secret = await self.container.secret_cipher.decrypt(signal_source.api_secret_ciphertext)
        async with websockets.connect(client.private_stream_url(account), ping_interval=20, ping_timeout=20) as ws:
            await ws.send(json.dumps(client.ws_auth_message(api_key, api_secret)))
            await ws.send(json.dumps(client.ws_subscribe_message()))
            await self._set_listener_state(signal_source.id, stream_status="CONNECTED", listener_status="RUNNING")
            await self._log(signal_source.exchange, signal_source.name, f"Connected BitMEX private stream for {signal_source.name}.", {})
            while True:
                raw = await ws.recv()
                message = json.loads(raw)
                if message.get("error"):
                    raise RuntimeError(str(message["error"]))
                table = message.get("table")
                if table == "position":
                    await self._handle_bitmex_positions(signal_source, message)
                elif table in {"order", "execution"}:
                    await self._refresh_positions_from_rest(signal_source, poll_interval_seconds, origin="BITMEX_WS")

    async def _listen_gateio(self, signal_source: SignalSourceModel, poll_interval_seconds: float) -> None:
        client = self.container.exchange_clients[Exchange.GATEIO]
        account = self._source_account_proxy(signal_source)
        api_key = await self.container.secret_cipher.decrypt(signal_source.api_key_ciphertext)
        api_secret = await self.container.secret_cipher.decrypt(signal_source.api_secret_ciphertext)
        async with websockets.connect(client.private_stream_url(account), ping_interval=20, ping_timeout=20) as ws:
            await ws.send(json.dumps(client.ws_login_message(api_key, api_secret)))
            for message in client.ws_subscribe_messages():
                await ws.send(json.dumps(message))
            await self._set_listener_state(signal_source.id, stream_status="CONNECTED", listener_status="RUNNING")
            await self._log(signal_source.exchange, signal_source.name, f"Connected Gate.io private stream for {signal_source.name}.", {})
            while True:
                raw = await ws.recv()
                message = json.loads(raw)
                if message.get("event") == "error":
                    raise RuntimeError(message.get("error", {}).get("message") or "Gate.io websocket error")
                channel = message.get("channel")
                if channel == "futures.positions":
                    await self._handle_gateio_positions(signal_source, message)
                elif channel in {"futures.orders", "futures.usertrades"}:
                    await self._refresh_positions_from_rest(signal_source, poll_interval_seconds, origin="GATEIO_WS")

    async def _listen_coinbase(self, signal_source: SignalSourceModel, poll_interval_seconds: float) -> None:
        client = self.container.exchange_clients[Exchange.COINBASE]
        account = self._source_account_proxy(signal_source)
        api_key = await self.container.secret_cipher.decrypt(signal_source.api_key_ciphertext)
        api_secret = await self.container.secret_cipher.decrypt(signal_source.api_secret_ciphertext)
        async with websockets.connect(client.private_stream_url(account), ping_interval=20, ping_timeout=20) as ws:
            await ws.send(json.dumps(client.ws_subscribe_message(account, api_key, api_secret)))
            await self._set_listener_state(signal_source.id, stream_status="CONNECTED", listener_status="RUNNING")
            await self._log(signal_source.exchange, signal_source.name, f"Connected Coinbase private stream for {signal_source.name}.", {})
            while True:
                raw = await ws.recv()
                message = json.loads(raw)
                if message.get("type") == "error":
                    raise RuntimeError(message.get("message") or "Coinbase websocket error")
                if message.get("channel") == "user":
                    await self._refresh_positions_from_rest(signal_source, poll_interval_seconds, origin="COINBASE_WS")

    async def _listen_binance(self, signal_source: SignalSourceModel) -> None:
        client = self.container.exchange_clients[Exchange.BINANCE]
        api_key = await self.container.secret_cipher.decrypt(signal_source.api_key_ciphertext)
        api_secret = await self.container.secret_cipher.decrypt(signal_source.api_secret_ciphertext)
        if not api_key or not api_secret:
            return
        listen_key = await client.create_listen_key(api_key)
        ws_url = client.user_stream_url(listen_key)
        await self._set_listener_state(signal_source.id, stream_status="CONNECTED", listener_status="RUNNING")
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
            await self._log(signal_source.exchange, signal_source.name, f"Connected Binance private stream for {signal_source.name}.", {})
            while True:
                raw = await ws.recv()
                message = json.loads(raw)
                await self._handle_binance_message(signal_source, message)

    async def _listen_bybit(self, signal_source: SignalSourceModel) -> None:
        client = self.container.exchange_clients[Exchange.BYBIT]
        api_key = await self.container.secret_cipher.decrypt(signal_source.api_key_ciphertext)
        api_secret = await self.container.secret_cipher.decrypt(signal_source.api_secret_ciphertext)
        if not api_key or not api_secret:
            return
        async with websockets.connect(client.private_stream_url(), ping_interval=20, ping_timeout=20) as ws:
            await ws.send(json.dumps(client.auth_message(api_key, api_secret)))
            await ws.send(json.dumps({"op": "subscribe", "args": ["position", "execution", "order"]}))
            await self._set_listener_state(signal_source.id, stream_status="CONNECTED", listener_status="RUNNING")
            await self._log(signal_source.exchange, signal_source.name, f"Connected Bybit private stream for {signal_source.name}.", {})
            while True:
                raw = await ws.recv()
                message = json.loads(raw)
                await self._handle_bybit_message(signal_source, message)

    async def _poll_positions(self, signal_source: SignalSourceModel, poll_interval_seconds: float) -> None:
        exchange = Exchange(signal_source.exchange)
        client = self.container.exchange_clients[exchange]
        account = self._source_account_proxy(signal_source)
        api_key = await self.container.secret_cipher.decrypt(signal_source.api_key_ciphertext)
        api_secret = await self.container.secret_cipher.decrypt(signal_source.api_secret_ciphertext)
        api_passphrase = await self.container.secret_cipher.decrypt(signal_source.api_passphrase_ciphertext)
        await self._set_listener_state(signal_source.id, stream_status="POLLING", listener_status="RUNNING")
        await self._log(
            signal_source.exchange,
            signal_source.name,
            f"{signal_source.exchange} source uses REST position reconciliation mode.",
            {"signal_source_id": signal_source.id, "origin": "REST_RECON"},
            log_type=LogType.WARNING,
        )
        while True:
            snapshots = await client.fetch_open_positions(account, api_key, api_secret, api_passphrase)
            await self._reconcile_positions(
                signal_source,
                snapshots,
                origin="REST_RECON",
                payload={"positions": [snapshot.model_dump(mode="json") for snapshot in snapshots]},
            )
            await asyncio.sleep(poll_interval_seconds)

    async def _refresh_positions_from_rest(self, signal_source: SignalSourceModel, poll_interval_seconds: float, *, origin: str) -> None:
        exchange = Exchange(signal_source.exchange)
        client = self.container.exchange_clients[exchange]
        account = self._source_account_proxy(signal_source)
        api_key = await self.container.secret_cipher.decrypt(signal_source.api_key_ciphertext)
        api_secret = await self.container.secret_cipher.decrypt(signal_source.api_secret_ciphertext)
        api_passphrase = await self.container.secret_cipher.decrypt(signal_source.api_passphrase_ciphertext)
        snapshots = await client.fetch_open_positions(account, api_key, api_secret, api_passphrase)
        await self._reconcile_positions(
            signal_source,
            snapshots,
            origin=origin,
            payload={"positions": [snapshot.model_dump(mode="json") for snapshot in snapshots]},
        )

    async def _handle_binance_message(self, signal_source: SignalSourceModel, message: dict) -> None:
        if message.get("e") != "ACCOUNT_UPDATE":
            return
        positions = []
        for position in message.get("a", {}).get("P", []):
            qty = Decimal(str(position.get("pa", "0")))
            mark_price = Decimal(str(position["ep"])) if position.get("ep") else None
            positions.append(
                PositionSnapshotPayload(
                    account_id=signal_source.id,
                    exchange=Exchange.BINANCE,
                    symbol=position.get("s"),
                    quantity=qty,
                    entry_price=mark_price,
                    mark_price=mark_price,
                    notional_exposure=abs(qty * mark_price) if mark_price is not None else None,
                    leverage=signal_source.default_leverage,
                    margin_mode=signal_source.margin_mode,
                    source="ws",
                )
            )
        await self._reconcile_positions(signal_source, positions, origin="BINANCE_WS", payload=message)

    async def _handle_bybit_message(self, signal_source: SignalSourceModel, message: dict) -> None:
        if message.get("topic") != "position":
            return
        positions: list[PositionSnapshotPayload] = []
        for row in message.get("data", []):
            size = Decimal(str(row.get("size", "0")))
            side = row.get("side")
            current = size if side == "Buy" else -size if side == "Sell" else Decimal("0")
            positions.append(
                PositionSnapshotPayload(
                    account_id=signal_source.id,
                    exchange=Exchange.BYBIT,
                    symbol=row.get("symbol"),
                    quantity=current,
                    entry_price=Decimal(str(row["entryPrice"])) if row.get("entryPrice") else None,
                    mark_price=Decimal(str(row["markPrice"])) if row.get("markPrice") else None,
                    unrealized_pnl=Decimal(str(row["unrealisedPnl"])) if row.get("unrealisedPnl") else None,
                    notional_exposure=abs(current * Decimal(str(row["markPrice"]))) if row.get("markPrice") else None,
                    leverage=int(Decimal(str(row["leverage"]))) if row.get("leverage") else signal_source.default_leverage,
                    margin_mode=signal_source.margin_mode,
                    source="ws",
                )
            )
        await self._reconcile_positions(signal_source, positions, origin="BYBIT_WS", payload=message)

    async def _handle_okx_positions(self, signal_source: SignalSourceModel, message: dict) -> None:
        positions: list[PositionSnapshotPayload] = []
        for row in message.get("data", []):
            qty = Decimal(str(row.get("pos", "0")))
            pos_side = str(row.get("posSide", "")).lower()
            signed_qty = -qty if pos_side == "short" else qty
            mark_price = Decimal(str(row["markPx"])) if row.get("markPx") else None
            entry_price = Decimal(str(row["avgPx"])) if row.get("avgPx") else None
            positions.append(
                PositionSnapshotPayload(
                    account_id=signal_source.id,
                    exchange=Exchange.OKX,
                    symbol=row.get("instId"),
                    quantity=signed_qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=Decimal(str(row["upl"])) if row.get("upl") else None,
                    notional_exposure=abs(signed_qty * mark_price) if mark_price is not None else None,
                    leverage=int(Decimal(str(row["lever"]))) if row.get("lever") else signal_source.default_leverage,
                    margin_mode=row.get("mgnMode") or signal_source.margin_mode,
                    source="ws",
                )
            )
        await self._reconcile_positions(signal_source, positions, origin="OKX_WS", payload=message)

    async def _handle_kraken_positions(self, signal_source: SignalSourceModel, message: dict) -> None:
        positions: list[PositionSnapshotPayload] = []
        rows = message.get("positions") or message.get("open_positions") or message.get("data") or []
        for row in rows:
            qty = Decimal(str(row.get("size", "0")))
            side = str(row.get("side", "")).lower()
            signed_qty = -qty if side == "short" else qty
            mark_price = Decimal(str(row["mark_price"])) if row.get("mark_price") else Decimal(str(row["markPrice"])) if row.get("markPrice") else None
            entry_price = Decimal(str(row["price"])) if row.get("price") else None
            positions.append(
                PositionSnapshotPayload(
                    account_id=signal_source.id,
                    exchange=Exchange.KRAKEN,
                    symbol=row.get("symbol") or row.get("product_id"),
                    quantity=signed_qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    notional_exposure=abs(signed_qty * mark_price) if mark_price is not None else None,
                    leverage=int(Decimal(str(row["leverage"]))) if row.get("leverage") else signal_source.default_leverage,
                    margin_mode=row.get("marginAccount") or signal_source.margin_mode,
                    source="ws",
                )
            )
        await self._reconcile_positions(signal_source, positions, origin="KRAKEN_WS", payload=message)

    async def _handle_bitmex_positions(self, signal_source: SignalSourceModel, message: dict) -> None:
        positions: list[PositionSnapshotPayload] = []
        for row in message.get("data", []):
            qty = Decimal(str(row.get("currentQty", "0")))
            mark_price = Decimal(str(row["markPrice"])) if row.get("markPrice") else None
            entry_price = Decimal(str(row["avgEntryPrice"])) if row.get("avgEntryPrice") else None
            positions.append(
                PositionSnapshotPayload(
                    account_id=signal_source.id,
                    exchange=Exchange.BITMEX,
                    symbol=row.get("symbol"),
                    quantity=qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=Decimal(str(row["unrealisedPnlPcnt"])) if row.get("unrealisedPnlPcnt") else None,
                    notional_exposure=abs(qty * mark_price) if mark_price is not None else None,
                    leverage=int(Decimal(str(row["leverage"]))) if row.get("leverage") else signal_source.default_leverage,
                    margin_mode=row.get("crossMargin") and "CROSS" or "ISOLATED",
                    source="ws",
                )
            )
        await self._reconcile_positions(signal_source, positions, origin="BITMEX_WS", payload=message)

    async def _handle_gateio_positions(self, signal_source: SignalSourceModel, message: dict) -> None:
        positions: list[PositionSnapshotPayload] = []
        rows = message.get("result") or message.get("data") or []
        if isinstance(rows, dict):
            rows = [rows]
        for row in rows:
            qty = Decimal(str(row.get("size", "0")))
            mark_price = Decimal(str(row["mark_price"])) if row.get("mark_price") else None
            entry_price = Decimal(str(row["entry_price"])) if row.get("entry_price") else None
            positions.append(
                PositionSnapshotPayload(
                    account_id=signal_source.id,
                    exchange=Exchange.GATEIO,
                    symbol=row.get("contract") or row.get("name"),
                    quantity=qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=Decimal(str(row["unrealised_pnl"])) if row.get("unrealised_pnl") else None,
                    notional_exposure=abs(qty * mark_price) if mark_price is not None else None,
                    leverage=int(Decimal(str(row["leverage"]))) if row.get("leverage") else signal_source.default_leverage,
                    margin_mode=row.get("mode") or signal_source.margin_mode,
                    source="ws",
                )
            )
        await self._reconcile_positions(signal_source, positions, origin="GATEIO_WS", payload=message)

    async def _reconcile_positions(
        self,
        signal_source: SignalSourceModel,
        snapshots: list[PositionSnapshotPayload],
        *,
        origin: str,
        payload: dict[str, Any],
    ) -> None:
        current_positions = {snapshot.symbol: Decimal(snapshot.quantity) for snapshot in snapshots}
        previous_positions = dict(self._position_cache[signal_source.id])
        symbols = sorted(set(previous_positions) | set(current_positions))
        for symbol in symbols:
            previous = previous_positions.get(symbol, Decimal("0"))
            current = current_positions.get(symbol, Decimal("0"))
            if current == previous:
                continue
            self._position_cache[signal_source.id][symbol] = current
            await self._emit_master_event(
                signal_source,
                source_order_or_fill_id=f"{origin.lower()}-{int(time.time() * 1000)}-{symbol}",
                symbol=symbol,
                previous=previous,
                current=current,
                price=None,
                payload={"origin": origin, **payload},
            )
        if symbols:
            await self._set_listener_state(
                signal_source.id,
                stream_status="ACTIVE" if origin.endswith("_WS") else "POLLING",
                listener_status="RUNNING",
                last_stream_event_at=utc_now(),
            )

    async def _emit_master_event(
        self,
        signal_source: SignalSourceModel,
        *,
        source_order_or_fill_id: str,
        symbol: str,
        previous: Decimal,
        current: Decimal,
        price: Decimal | None,
        payload: dict,
    ) -> None:
        async with self.container.session_factory() as session:
            listener = MasterListenerService(self.container.orchestrator(session))
            try:
                await listener.ingest_event(
                    MasterEventIn(
                        source_exchange=signal_source.exchange,
                        source_account=signal_source.source_account,
                        source_order_or_fill_id=source_order_or_fill_id,
                        symbol=symbol,
                        previous_position_qty=previous,
                        current_position_qty=current,
                        price=price,
                        payload=payload,
                    )
                )
                await self.container.orchestrator(session).execution_repository.add_trade_log(
                    exchange=signal_source.exchange,
                    log_type=LogType.SIGNAL,
                    log_key=signal_source.name,
                    message=f"{signal_source.exchange} source event created signal for {symbol}.",
                    details={
                        "signal_source_id": signal_source.id,
                        "symbol": symbol,
                        "origin": payload.get("origin", "MASTER_STREAM"),
                    },
                )
                await session.commit()
            except Exception as exc:
                await self._log(
                    signal_source.exchange,
                    signal_source.name,
                    f"Failed to ingest source event: {exc}",
                    {"signal_source_id": signal_source.id, "symbol": symbol},
                    log_type=LogType.ERROR,
                )

    async def _set_listener_state(
        self,
        signal_source_id: str,
        *,
        stream_status: str | None = None,
        listener_status: str | None = None,
        last_stream_event_at: datetime | None = None,
        validation_message: str | None = None,
    ) -> None:
        async with self.container.session_factory() as session:
            repository = SignalRepository(session)
            await repository.update_signal_source_listener_state(
                signal_source_id,
                stream_status=stream_status,
                listener_status=listener_status,
                last_stream_event_at=last_stream_event_at,
                validation_message=validation_message,
            )
            await session.commit()

    async def _log(self, exchange: str, key: str, message: str, details: dict, log_type: LogType = LogType.INFO) -> None:
        async with self.container.session_factory() as session:
            await self.container.orchestrator(session).execution_repository.add_trade_log(
                exchange=exchange,
                log_type=log_type,
                log_key=key,
                message=message,
                details={"origin": "PRIVATE_STREAM", **details},
            )
            await session.commit()

    def _source_account_proxy(self, signal_source: SignalSourceModel):
        return SimpleNamespace(
            id=signal_source.id,
            exchange=signal_source.exchange,
            environment=signal_source.environment,
            leverage=signal_source.default_leverage,
            margin_mode=signal_source.margin_mode,
            hedge_mode=signal_source.hedge_mode,
        )
