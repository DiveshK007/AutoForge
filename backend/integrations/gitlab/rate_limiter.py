"""
AutoForge GitLab Integration — Rate limiter.

Monitors GitLab API rate-limit headers and pauses execution when the
remaining quota drops below a safety threshold.
"""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger("autoforge.integrations.gitlab.rate_limiter")


class RateLimiter:
    """
    Token-bucket style rate limiter informed by GitLab's ``RateLimit-*``
    response headers.

    Usage:
        limiter = RateLimiter()
        await limiter.acquire()        # blocks if quota exhausted
        limiter.update_from_headers(response.headers)
    """

    # Safety margin — stop sending when this many calls remain
    SAFETY_MARGIN: int = 10

    def __init__(self, requests_per_second: float = 10.0):
        self._rps = requests_per_second
        self._remaining: Optional[int] = None
        self._reset_at: Optional[float] = None
        self._lock = asyncio.Lock()
        self._last_request: float = 0.0

    async def acquire(self) -> None:
        """Wait until it is safe to issue a request."""
        async with self._lock:
            now = time.monotonic()

            # Respect the simple RPS cap
            elapsed = now - self._last_request
            min_interval = 1.0 / self._rps
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)

            # If GitLab told us we're near the limit, back off
            if self._remaining is not None and self._remaining <= self.SAFETY_MARGIN:
                wait = self._seconds_until_reset()
                if wait > 0:
                    logger.warning(
                        "Rate limit nearly exhausted (%d remaining). "
                        "Pausing %.1fs until reset.",
                        self._remaining,
                        wait,
                    )
                    await asyncio.sleep(wait)

            self._last_request = time.monotonic()

    def update_from_headers(self, headers: dict) -> None:
        """
        Parse GitLab ``RateLimit-Remaining`` and ``RateLimit-Reset``
        headers and adjust internal state.
        """
        remaining = headers.get("RateLimit-Remaining") or headers.get("ratelimit-remaining")
        reset_at = headers.get("RateLimit-Reset") or headers.get("ratelimit-reset")

        if remaining is not None:
            try:
                self._remaining = int(remaining)
            except (ValueError, TypeError):
                pass

        if reset_at is not None:
            try:
                self._reset_at = float(reset_at)
            except (ValueError, TypeError):
                pass

    def _seconds_until_reset(self) -> float:
        """Seconds until the rate-limit window resets (0 if unknown)."""
        if self._reset_at is None:
            return 5.0  # Conservative fallback
        return max(0.0, self._reset_at - time.time())

    @property
    def remaining(self) -> Optional[int]:
        return self._remaining

    def get_stats(self) -> dict:
        return {
            "remaining": self._remaining,
            "reset_at": self._reset_at,
            "rps_limit": self._rps,
        }
