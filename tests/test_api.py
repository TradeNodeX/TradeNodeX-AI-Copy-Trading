def test_dashboard_flow_creates_signal_copytrade_and_logs(client) -> None:
    signal_source = client.post(
        "/v1/signal-sources",
        json={
            "name": "Lucky Trend",
            "exchange": "BINANCE",
            "environment": "TESTNET",
            "source_account": "master-01",
            "pairs_scope": "ALL",
            "default_copy_mode": "EXACT",
            "default_leverage": 10,
            "margin_mode": "ISOLATED",
            "hedge_mode": False,
        },
    )
    assert signal_source.status_code == 201, signal_source.text
    signal_source_id = signal_source.json()["id"]

    follower_response = client.post(
        "/v1/followers",
        json={
            "name": "binance-follower-01",
            "exchange": "BINANCE",
            "environment": "TESTNET",
            "leverage": 10,
            "margin_mode": "ISOLATED",
            "hedge_mode": False,
        },
    )
    assert follower_response.status_code == 201, follower_response.text
    follower_id = follower_response.json()["id"]

    copy_trade = client.post(
        "/v1/copy-trades",
        json={
            "name": "Follower A",
            "signal_source_id": signal_source_id,
            "follower_account_id": follower_id,
            "copy_mode": "EXACT",
            "scale_factor": "1",
            "command_template": '{"unitsType":"signalSource"}',
            "notes": "primary route",
        },
    )
    assert copy_trade.status_code == 201, copy_trade.text
    assert copy_trade.json()["validation_status"] == "VERIFIED"
    assert copy_trade.json()["command_template"] == '{"unitsType":"signalSource"}'

    signal_response = client.post(
        "/v1/internal/master-events",
        json={
            "source_exchange": "BINANCE",
            "source_account": "master-01",
            "source_order_or_fill_id": "fill-01",
            "symbol": "BTCUSDT",
            "previous_position_qty": "0",
            "current_position_qty": "2",
            "price": "85000",
            "payload": {"source": "test"},
        },
    )
    assert signal_response.status_code == 202, signal_response.text
    signal_body = signal_response.json()
    assert signal_body["action"] == "OPEN"
    assert signal_body["signal_source_id"] == signal_source_id
    assert len(signal_body["execution_task_ids"]) == 1

    execution_response = client.get(f"/v1/followers/{follower_id}/executions", params={"signal_id": signal_body["id"]})
    assert execution_response.status_code == 200, execution_response.text
    execution_body = execution_response.json()
    assert len(execution_body) == 1
    assert execution_body[0]["target_quantity"] == "2.00000000"
    assert execution_body[0]["copy_mode"] == "EXACT"

    dashboard = client.get("/v1/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    dashboard_body = dashboard.json()
    assert len(dashboard_body["signal_sources"]) == 1
    assert len(dashboard_body["copy_trades"]) == 1
    assert len(dashboard_body["logs"]) >= 3
    assert dashboard_body["signal_sources"][0]["follower_names"] == ["binance-follower-01"]


def test_command_generation_and_logs_endpoint(client) -> None:
    follower_response = client.post(
        "/v1/followers",
        json={
            "name": "bybit-follower-01",
            "exchange": "BYBIT",
            "environment": "TESTNET",
            "leverage": 10,
            "margin_mode": "ISOLATED",
            "hedge_mode": False,
        },
    )
    follower_id = follower_response.json()["id"]

    preset_response = client.post(
        "/v1/commands/generate",
        json={
            "name": "Bybit Buy Preset",
            "exchange": "BYBIT",
            "environment": "TESTNET",
            "product_type": "FUTURES",
            "action": "BUY",
            "symbol": "BTCUSDT",
            "order_type": "MARKET",
            "quantity_mode": "ABSOLUTE",
            "quantity_value": "1",
            "account_id": follower_id,
            "stop_loss_percent": "4.5",
            "use_dca": True,
        },
    )
    assert preset_response.status_code == 200, preset_response.text
    body = preset_response.json()
    assert body["exchange"] == "BYBIT"
    assert '"action":"BUY"' in body["raw_command"]
    assert '"productType":"FUTURES"' in body["raw_command"]
    assert '"useDca":true' in body["raw_command"]

    close_preset_response = client.post(
        "/v1/commands/generate",
        json={
            "name": "Bybit Close Preset",
            "exchange": "BYBIT",
            "environment": "TESTNET",
            "product_type": "FUTURES",
            "action": "CLOSE_POSITION",
            "symbol": "BTCUSDT",
            "order_type": "MARKET",
            "quantity_mode": "ABSOLUTE",
            "quantity_value": "1",
            "account_id": follower_id,
            "close_all": True,
            "partial_close": True,
            "close_by_limit_order": True,
        },
    )
    assert close_preset_response.status_code == 200, close_preset_response.text
    assert '"closeAll":true' in close_preset_response.json()["raw_command"]
    assert '"partialClose":true' in close_preset_response.json()["raw_command"]

    logs_response = client.get("/v1/logs")
    assert logs_response.status_code == 200, logs_response.text
    assert isinstance(logs_response.json(), list)

    paged_logs_response = client.get("/v1/logs/query", params={"page": 1, "limit": 50, "exchange": "BYBIT"})
    assert paged_logs_response.status_code == 200, paged_logs_response.text
    assert paged_logs_response.json()["page"] == 1
    assert paged_logs_response.json()["limit"] == 50


def test_signal_and_copy_trade_crud_endpoints(client) -> None:
    source = client.post(
        "/v1/signal-sources",
        json={
            "name": "Scalp Source",
            "exchange": "BYBIT",
            "environment": "TESTNET",
            "source_account": "master-scalp",
            "pairs_scope": "ALL",
        },
    )
    source_id = source.json()["id"]

    follower = client.post(
        "/v1/followers",
        json={
            "name": "Scalp Follower",
            "exchange": "BYBIT",
            "environment": "TESTNET",
            "leverage": 5,
            "margin_mode": "ISOLATED",
        },
    )
    follower_id = follower.json()["id"]

    updated_follower = client.patch(
        f"/v1/followers/{follower_id}",
        json={
          "name": "Scalp Follower Updated",
          "leverage": 8,
        },
    )
    assert updated_follower.status_code == 200, updated_follower.text
    assert updated_follower.json()["name"] == "Scalp Follower Updated"

    copy_trade = client.post(
        "/v1/copy-trades",
        json={
            "name": "Scalp Link",
            "signal_source_id": source_id,
            "follower_account_id": follower_id,
            "copy_mode": "EXACT",
            "command_template": '{"exchange":"BYBIT"}',
        },
    )
    copy_trade_id = copy_trade.json()["id"]

    updated_copy_trade = client.patch(
        f"/v1/copy-trades/{copy_trade_id}",
        json={
            "notes": "updated notes",
            "enabled": False,
        },
    )
    assert updated_copy_trade.status_code == 200, updated_copy_trade.text
    assert updated_copy_trade.json()["notes"] == "updated notes"
    assert updated_copy_trade.json()["enabled"] is False

    delete_copy_trade = client.delete(f"/v1/copy-trades/{copy_trade_id}")
    assert delete_copy_trade.status_code == 200, delete_copy_trade.text
    assert delete_copy_trade.json()["deleted"] is True

    delete_signal = client.delete(f"/v1/signal-sources/{source_id}")
    assert delete_signal.status_code == 200, delete_signal.text
    assert delete_signal.json()["deleted"] is True

    delete_follower = client.delete(f"/v1/followers/{follower_id}")
    assert delete_follower.status_code == 200, delete_follower.text
    assert delete_follower.json()["deleted"] is True


def test_frontend_includes_api_fields(client) -> None:
    response = client.get("/")
    assert response.status_code == 200, response.text
    assert "TradeNodeX Control Center" in response.text
    assert "Studio" in response.text
    assert "Audit Logs" in response.text
    assert "Realtime stream offline" in response.text
    assert "Live Execution Queue" in response.text
    assert "Cancel Scope" in response.text
    assert "Close Position Scope" in response.text
    assert "OKX" in response.text
    assert "COINBASE" in response.text
    assert "KRAKEN" in response.text
    assert "BITMEX" in response.text
    assert "GATEIO" in response.text


def test_websocket_stream_returns_snapshot(client) -> None:
    with client.websocket_connect("/v1/ws/stream") as websocket:
        payload = websocket.receive_json()
        assert payload["type"] == "snapshot"
        assert "counts" in payload
        assert "logs" in payload
        assert "executions" in payload


def test_positions_endpoint_returns_list(client) -> None:
    response = client.get("/v1/positions")
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
