from __future__ import annotations

import asyncio
from decimal import Decimal

from copytrading_app.domain.enums import Exchange
from copytrading_app.domain.types import PositionSnapshotPayload
from copytrading_app.repositories.signal_repository import SignalRepository
from copytrading_app.services.private_streams import MasterStreamSupervisor


class DummyClient:
    def __init__(self, instruments: list[dict]):
        self._instruments = instruments

    async def fetch_instruments(self) -> list[dict]:
        return self._instruments


def test_rest_reconciliation_creates_signal_and_execution_task(client) -> None:
    source_response = client.post(
        "/v1/signal-sources",
        json={
            "name": "OKX Master",
            "exchange": "OKX",
            "environment": "TESTNET",
            "source_account": "okx-master",
            "pairs_scope": "ALL",
            "default_copy_mode": "EXACT",
            "default_leverage": 5,
            "margin_mode": "ISOLATED",
            "hedge_mode": False,
        },
    )
    assert source_response.status_code == 201, source_response.text
    source_id = source_response.json()["id"]

    follower_response = client.post(
        "/v1/followers",
        json={
            "name": "gate-follower-01",
            "exchange": "GATEIO",
            "environment": "TESTNET",
            "leverage": 5,
            "margin_mode": "ISOLATED",
            "hedge_mode": False,
        },
    )
    assert follower_response.status_code == 201, follower_response.text
    follower_id = follower_response.json()["id"]

    copy_trade_response = client.post(
        "/v1/copy-trades",
        json={
            "name": "OKX -> Gate",
            "signal_source_id": source_id,
            "follower_account_id": follower_id,
            "copy_mode": "EXACT",
            "scale_factor": "1",
        },
    )
    assert copy_trade_response.status_code == 201, copy_trade_response.text

    container = client.app.state.container
    container.exchange_clients[Exchange.OKX] = DummyClient(
        [{"instId": "BTC-USDT-SWAP", "baseCcy": "BTC", "quoteCcy": "USDT", "lotSz": "0.001", "minSz": "0.001"}]
    )
    container.exchange_clients[Exchange.GATEIO] = DummyClient(
        [{"name": "BTC_USDT", "base": "BTC", "quote": "USDT", "quanto_multiplier": "0.001", "order_size_min": "0.001"}]
    )
    container.instrument_catalog.exchange_clients = container.exchange_clients

    async def load_source():
        async with container.session_factory() as session:
            repository = SignalRepository(session)
            return await repository.get_signal_source(source_id)

    signal_source = asyncio.run(load_source())
    supervisor = MasterStreamSupervisor(container)
    asyncio.run(
        supervisor._reconcile_positions(
            signal_source,
            [
                PositionSnapshotPayload(
                    account_id=source_id,
                    exchange=Exchange.OKX,
                    symbol="BTC-USDT-SWAP",
                    quantity=Decimal("2"),
                    source="rest",
                )
            ],
            origin="REST_RECON",
            payload={"positions": []},
        )
    )

    dashboard_response = client.get("/v1/dashboard")
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()

    signal_source_body = dashboard["signal_sources"][0]
    assert signal_source_body["listener_status"] == "RUNNING"
    assert signal_source_body["stream_status"] == "POLLING"
    assert signal_source_body["last_stream_event_at"] is not None

    executions = client.get(f"/v1/followers/{follower_id}/executions")
    assert executions.status_code == 200, executions.text
    execution_items = executions.json()
    assert len(execution_items) == 1
    assert execution_items[0]["exchange"] == "GATEIO"
    assert execution_items[0]["symbol"] == "BTC_USDT"

    logs_response = client.get("/v1/logs/query", params={"page": 1, "limit": 50, "exchange": "OKX"})
    assert logs_response.status_code == 200, logs_response.text
    log_messages = [item["message"] for item in logs_response.json()["items"]]
    assert any("source event created signal" in message for message in log_messages)
