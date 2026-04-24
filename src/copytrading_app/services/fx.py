from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

from copytrading_app.core.config import Settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FxRateService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(timeout=min(settings.api_timeout_seconds, 1.5))
        self._rates: dict[str, Decimal] = {
            "USD": Decimal("1"),
            "EUR": Decimal("0.92"),
            "JPY": Decimal("154.25"),
            "CNY": Decimal("7.25"),
            "HKD": Decimal("7.81"),
            "SGD": Decimal("1.35"),
            "GBP": Decimal("0.79"),
            "AUD": Decimal("1.53"),
            "CAD": Decimal("1.37"),
            "CHF": Decimal("0.91"),
            "KRW": Decimal("1370"),
            "VND": Decimal("25500"),
            "TWD": Decimal("32.5"),
            "THB": Decimal("36.4"),
            "TRY": Decimal("32.1"),
            "RUB": Decimal("91.0"),
            "UAH": Decimal("39.4"),
            "ZAR": Decimal("18.4"),
            "BRL": Decimal("5.1"),
            "MXN": Decimal("16.8"),
            "INR": Decimal("83.5"),
            "IDR": Decimal("16125"),
        }
        self._updated_at: datetime = _utc_now()
        self._source = "embedded-fallback"
        self._ttl = timedelta(minutes=30)

    async def close(self) -> None:
        await self._client.aclose()

    async def maybe_refresh(self) -> None:
        if _utc_now() - self._updated_at < self._ttl:
            return
        await self.refresh()

    async def refresh(self) -> None:
        try:
            response = await self._client.get("https://api.frankfurter.app/latest", params={"from": "USD"})
            response.raise_for_status()
            payload = response.json()
            rates = payload.get("rates", {})
            normalized = {"USD": Decimal("1")}
            for code, value in rates.items():
                normalized[code.upper()] = Decimal(str(value))
            if normalized:
                self._rates = normalized
                self._updated_at = _utc_now()
                self._source = "frankfurter.app"
        except Exception:
            # Keep the embedded cache if remote FX is unavailable.
            pass

    async def convert(self, amount: Decimal | int | float | None, currency: str) -> Decimal | None:
        if amount is None:
            return None
        await self.maybe_refresh()
        target = currency.upper()
        rate = self._rates.get(target)
        if rate is None:
            return None
        return (Decimal(str(amount)) * rate).quantize(Decimal("0.01"))

    def metadata(self, display_currency: str) -> dict:
        return {
            "display_currency": display_currency.upper(),
            "source_currency": "USD",
            "conversion_source": self._source,
            "converted": display_currency.upper() in self._rates,
            "updated_at": self._updated_at,
            "available_rates": sorted(self._rates.keys()),
        }
