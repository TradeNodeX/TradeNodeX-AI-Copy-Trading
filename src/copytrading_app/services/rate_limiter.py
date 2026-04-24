from __future__ import annotations

import asyncio
import time
from collections import defaultdict


class TokenBucketRateLimiter:
    def __init__(self, capacity: int, refill_per_second: float):
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.tokens = capacity
        self.updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.updated_at
                self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
                self.updated_at = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
            await asyncio.sleep(0.01)


class RateLimiterRegistry:
    def __init__(self):
        self._limiters: dict[str, TokenBucketRateLimiter] = {}
        self._locks = defaultdict(asyncio.Lock)

    async def acquire(self, key: str, capacity: int, refill_per_second: float) -> None:
        async with self._locks[key]:
            limiter = self._limiters.get(key)
            if limiter is None:
                limiter = TokenBucketRateLimiter(capacity=capacity, refill_per_second=refill_per_second)
                self._limiters[key] = limiter
        await limiter.acquire()

