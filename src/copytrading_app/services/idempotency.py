from __future__ import annotations

import asyncio
from typing import Protocol

from redis.asyncio import Redis


class IdempotencyStore(Protocol):
    async def exists(self, key: str) -> bool: ...

    async def remember(self, key: str, ttl_seconds: int = 86400) -> None: ...


class LocalIdempotencyStore:
    def __init__(self):
        self._keys: set[str] = set()
        self._lock = asyncio.Lock()

    async def exists(self, key: str) -> bool:
        async with self._lock:
            return key in self._keys

    async def remember(self, key: str, ttl_seconds: int = 86400) -> None:
        async with self._lock:
            self._keys.add(key)


class RedisIdempotencyStore:
    def __init__(self, redis: Redis, prefix: str):
        self.redis = redis
        self.prefix = prefix

    async def exists(self, key: str) -> bool:
        return bool(await self.redis.exists(self._full_key(key)))

    async def remember(self, key: str, ttl_seconds: int = 86400) -> None:
        await self.redis.set(self._full_key(key), "1", ex=ttl_seconds, nx=False)

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}:idempotency:{key}"

