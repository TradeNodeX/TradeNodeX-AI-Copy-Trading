from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from copytrading_app.domain.enums import Exchange
from copytrading_app.domain.types import InstrumentConstraints
from copytrading_app.services.exchanges.base import ExchangeClient


_QUOTE_CANDIDATES = [
    "USDT",
    "USDC",
    "USD",
    "EUR",
    "BTC",
    "ETH",
]

_SYMBOL_PREFIXES = ("PI_", "PF_", "FF_", "FI_", "IN_")
_SYMBOL_SUFFIXES = ("SWAP", "PERP", "PERPETUAL", "FUTURES", "FUTURE")
_ALIAS_OVERRIDES = {"XBT": "BTC"}


@dataclass(slots=True)
class CatalogEntry:
    symbol: str
    canonical: str
    constraints: InstrumentConstraints


class InstrumentCatalogService:
    def __init__(self, exchange_clients: dict[Exchange, ExchangeClient], ttl_seconds: int = 300):
        self.exchange_clients = exchange_clients
        self.ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()
        self._entries: dict[Exchange, list[CatalogEntry]] = {}
        self._loaded_at: dict[Exchange, datetime] = {}

    async def constraints_by_exchange(self, exchanges: set[Exchange] | None = None) -> dict[str, dict[str, InstrumentConstraints]]:
        requested = exchanges or set(self.exchange_clients.keys())
        await self._ensure_loaded(requested)
        result: dict[str, dict[str, InstrumentConstraints]] = {}
        for exchange in requested:
            rows = self._entries.get(exchange, [])
            result[exchange.value] = {entry.symbol: entry.constraints for entry in rows}
        return result

    async def resolve_symbol(self, source_exchange: str, target_exchange: str, symbol: str) -> tuple[str, InstrumentConstraints]:
        await self._ensure_loaded({Exchange(source_exchange), Exchange(target_exchange)})
        source_enum = Exchange(source_exchange)
        target_enum = Exchange(target_exchange)
        source_key = self._canonical_key(source_enum, symbol)
        if source_key:
            for entry in self._entries.get(target_enum, []):
                if entry.canonical == source_key:
                    return entry.symbol, entry.constraints
        for entry in self._entries.get(target_enum, []):
            if self._normalize_symbol(entry.symbol) == self._normalize_symbol(symbol):
                return entry.symbol, entry.constraints
        fallback_symbol = symbol
        if target_enum in {Exchange.OKX, Exchange.COINBASE} and "-" not in fallback_symbol and fallback_symbol.endswith("USDT"):
            fallback_symbol = f"{fallback_symbol[:-4]}-USDT-SWAP" if target_enum == Exchange.OKX else f"{fallback_symbol[:-4]}-USDT"
        return fallback_symbol, InstrumentConstraints(symbol=fallback_symbol)

    async def _ensure_loaded(self, exchanges: set[Exchange]) -> None:
        now = datetime.now(timezone.utc)
        if all(exchange in self._loaded_at and now - self._loaded_at[exchange] < self.ttl for exchange in exchanges):
            return
        async with self._lock:
            now = datetime.now(timezone.utc)
            if all(exchange in self._loaded_at and now - self._loaded_at[exchange] < self.ttl for exchange in exchanges):
                return
            for exchange in exchanges:
                client = self.exchange_clients[exchange]
                try:
                    instruments = await client.fetch_instruments()
                except Exception:
                    self._entries[exchange] = []
                    self._loaded_at[exchange] = now
                    continue
                self._entries[exchange] = self._build_entries(exchange, instruments)
                self._loaded_at[exchange] = now

    def _build_entries(self, exchange: Exchange, instruments: list[dict[str, Any]]) -> list[CatalogEntry]:
        entries: list[CatalogEntry] = []
        for row in instruments:
            symbol = self._symbol_for_exchange(exchange, row)
            if not symbol:
                continue
            canonical = self._canonical_key(exchange, symbol, row=row)
            constraints = InstrumentConstraints(
                symbol=symbol,
                quantity_step=self._decimal_value(
                    row.get("qtyStep")
                    or row.get("lotSz")
                    or row.get("base_increment")
                    or row.get("minOrderQty")
                    or row.get("min_order_size")
                    or row.get("underlyingToPositionMultiplier")
                    or row.get("lotSize")
                    or row.get("multiplier"),
                    default="0.001",
                ),
                min_quantity=self._decimal_value(
                    row.get("minQty")
                    or row.get("minSz")
                    or row.get("minOrderQty")
                    or row.get("base_min_size")
                    or row.get("orderMinSize")
                    or row.get("min_order_size")
                    or row.get("quanto_multiplier")
                    or row.get("order_size_min"),
                    default="0.001",
                ),
                min_notional=self._decimal_value(
                    row.get("minNotional")
                    or row.get("notional")
                    or row.get("minTradeAmount")
                    or row.get("min_cost"),
                    default="5",
                ),
                max_leverage=self._int_value(row.get("maxLever") or row.get("maxLeverage") or row.get("max_leverage")),
            )
            entries.append(CatalogEntry(symbol=symbol, canonical=canonical, constraints=constraints))
        return entries

    def _symbol_for_exchange(self, exchange: Exchange, row: dict[str, Any]) -> str | None:
        if exchange == Exchange.OKX:
            return row.get("instId")
        if exchange == Exchange.COINBASE:
            return row.get("product_id") or row.get("symbol")
        if exchange == Exchange.KRAKEN:
            return row.get("symbol")
        if exchange == Exchange.BITMEX:
            return row.get("symbol")
        if exchange == Exchange.GATEIO:
            return row.get("name") or row.get("contract") or row.get("id")
        return row.get("symbol")

    def _canonical_key(self, exchange: Exchange, symbol: str, row: dict[str, Any] | None = None) -> str:
        base, quote = self._extract_base_quote(exchange, symbol, row=row)
        if base and quote:
            return f"{base}{quote}"
        return self._normalize_symbol(symbol)

    def _extract_base_quote(self, exchange: Exchange, symbol: str, row: dict[str, Any] | None = None) -> tuple[str | None, str | None]:
        row = row or {}
        if exchange == Exchange.BINANCE:
            base, quote = self._alias(row.get("baseAsset")), self._alias(row.get("quoteAsset"))
            if base and quote:
                return base, quote
        if exchange == Exchange.BYBIT:
            base, quote = self._alias(row.get("baseCoin")), self._alias(row.get("quoteCoin"))
            if base and quote:
                return base, quote
        if exchange == Exchange.OKX:
            base, quote = self._alias(row.get("baseCcy")), self._alias(row.get("quoteCcy"))
            if base and quote:
                return base, quote
        if exchange == Exchange.BITMEX:
            base, quote = self._alias(row.get("rootSymbol")), self._alias(row.get("quoteCurrency"))
            if base and quote:
                return base, quote
        if exchange == Exchange.COINBASE:
            base, quote = self._alias(row.get("base_currency")), self._alias(row.get("quote_currency"))
            if base and quote:
                return base, quote
        if exchange == Exchange.GATEIO:
            base, quote = self._alias(row.get("base")), self._alias(row.get("quote"))
            if base and quote:
                return base, quote
        normalized = self._normalize_symbol(symbol)
        for prefix in _SYMBOL_PREFIXES:
            if normalized.startswith(prefix.replace("_", "")):
                normalized = normalized[len(prefix.replace("_", "")):]
                break
        for suffix in _SYMBOL_SUFFIXES:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
                break
        for quote in _QUOTE_CANDIDATES:
            if normalized.endswith(quote):
                base = normalized[: -len(quote)]
                if base:
                    return self._alias(base), self._alias(quote)
        return None, None

    def _normalize_symbol(self, symbol: str | None) -> str:
        if not symbol:
            return ""
        normalized = re.sub(r"[^A-Z0-9]", "", str(symbol).upper())
        for old, new in _ALIAS_OVERRIDES.items():
            normalized = normalized.replace(old, new)
        return normalized

    def _alias(self, value: Any) -> str | None:
        if value is None:
            return None
        upper = str(value).upper()
        return _ALIAS_OVERRIDES.get(upper, upper)

    def _decimal_value(self, value: Any, *, default: str) -> Decimal:
        if value in (None, "", "0", 0):
            return Decimal(default)
        try:
            parsed = Decimal(str(value))
            if parsed <= 0:
                return Decimal(default)
            return parsed
        except Exception:
            return Decimal(default)

    def _int_value(self, value: Any) -> int | None:
        if value in (None, "", 0, "0"):
            return None
        try:
            return int(Decimal(str(value)))
        except Exception:
            return None
