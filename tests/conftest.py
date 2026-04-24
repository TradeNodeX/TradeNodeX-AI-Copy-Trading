from __future__ import annotations

from collections.abc import Iterator
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    db_path = tmp_path / "copytrading_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BINANCE_BASE_URL", "https://fapi.binance.com")
    monkeypatch.setenv("BYBIT_BASE_URL", "https://api.bybit.com")
    monkeypatch.setenv("DEFAULT_ENVIRONMENT", "TESTNET")

    from copytrading_app.core import config

    config.get_settings.cache_clear()
    main = importlib.import_module("copytrading_app.main")
    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client

    config.get_settings.cache_clear()
