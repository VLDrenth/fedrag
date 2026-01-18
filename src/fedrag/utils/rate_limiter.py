"""Async rate limiter using token bucket algorithm."""

import asyncio
import time
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter for async operations.

    Limits the rate of operations to a specified number per second,
    while also limiting concurrent operations via semaphore.
    """

    def __init__(
        self,
        rate: float = 2.0,
        max_concurrent: int = 3,
    ):
        """Initialize the rate limiter.

        Args:
            rate: Maximum operations per second
            max_concurrent: Maximum concurrent operations
        """
        self.rate = rate
        self.min_interval = 1.0 / rate
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a request.

        This method blocks until both:
        1. A semaphore slot is available
        2. Enough time has passed since the last request
        """
        await self._semaphore.acquire()

        async with self._lock:
            now = time.monotonic()
            time_since_last = now - self._last_request_time

            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                await asyncio.sleep(wait_time)

            self._last_request_time = time.monotonic()

    def release(self) -> None:
        """Release the semaphore after request completes."""
        self._semaphore.release()

    async def __aenter__(self) -> "RateLimiter":
        """Context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.release()
