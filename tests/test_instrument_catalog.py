from __future__ import annotations

from decimal import Decimal

import pytest

from copytrading_app.domain.enums import Exchange
from copytrading_app.domain.types import InstrumentConstraints
from copytrading_app.services.instrument_catalog import InstrumentCatalogService


class DummyClient:
    def __init__(self, instruments: list[dict]):
        self._instruments = instruments

    async def fetch_instruments(self) -> list[dict]:
        return self._instruments


@pytest.mark.asyncio
async def test_instrument_catalog_resolves_okx_swap_to_gateio_contract() -> None:
    catalog = InstrumentCatalogService(
        {
            Exchange.OKX: DummyClient(
                [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "baseCcy": "BTC",
                        "quoteCcy": "USDT",
                        "lotSz": "0.001",
                        "minSz": "0.001",
                        "maxLever": "50",
                    }
                ]
            ),
            Exchange.GATEIO: DummyClient(
                [
                    {
                        "name": "BTC_USDT",
                        "base": "BTC",
                        "quote": "USDT",
                        "quanto_multiplier": "0.001",
                        "order_size_min": "0.001",
                        "leverage_max": "100",
                    }
                ]
            ),
        }
    )

    target_symbol, constraints = await catalog.resolve_symbol("OKX", "GATEIO", "BTC-USDT-SWAP")

    assert target_symbol == "BTC_USDT"
    assert constraints.symbol == "BTC_USDT"
    assert constraints.quantity_step == Decimal("0.001")


@pytest.mark.asyncio
async def test_instrument_catalog_falls_back_to_default_constraints_when_symbol_unknown() -> None:
    catalog = InstrumentCatalogService(
        {
            Exchange.COINBASE: DummyClient([]),
            Exchange.KRAKEN: DummyClient([]),
        }
    )

    target_symbol, constraints = await catalog.resolve_symbol("COINBASE", "KRAKEN", "DOGE-USD")

    assert target_symbol == "DOGE-USD"
    assert constraints == InstrumentConstraints(symbol="DOGE-USD")
