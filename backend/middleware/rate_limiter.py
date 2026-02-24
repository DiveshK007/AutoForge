"""
AutoForge Rate Limiting — Token bucket rate limiter with per-client tracking.

Provides:
- Per-IP rate limiting
- Per-API-key rate limiting
- Configurable limits per endpoint group
- Sliding window with token bucket algorithm
- Returns standard Retry-After headers
"""

import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from config import settings
from logging_config import get_logger

log = get_logger("rate_limiter")


class TokenBucket:
    """Token bucket rate limiter for a single client."""

    __slots__ = ("capacity", "tokens", "refill_rate", "last_refill")

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def retry_after(self) -> float:
        """Seconds until a token is available."""
        if self.tokens >= 1:
            return 0.0
        return (1 - self.tokens) / self.refill_rate


# ─── Rate Limit Configuration ───────────────────────────────────

# Requests per minute per client
RATE_LIMITS = {
    "/api/v1/webhooks": {"capacity": 30, "refill_rate": 0.5},       # 30/min
    "/api/v1/dashboard": {"capacity": 120, "refill_rate": 2.0},     # 120/min
    "/api/v1/telemetry": {"capacity": 120, "refill_rate": 2.0},     # 120/min
    "/api/v1/agents": {"capacity": 60, "refill_rate": 1.0},         # 60/min
    "/api/v1/workflows": {"capacity": 60, "refill_rate": 1.0},      # 60/min
    "/ws": {"capacity": 10, "refill_rate": 0.17},                   # 10/min
    "default": {"capacity": 60, "refill_rate": 1.0},                # 60/min
}


def _get_limit_config(path: str) -> dict:
    """Get rate limit config for a path."""
    for prefix, config in RATE_LIMITS.items():
        if prefix != "default" and path.startswith(prefix):
            return config
    return RATE_LIMITS["default"]


def _get_client_key(request: Request) -> str:
    """Extract client identifier from request."""
    # Prefer API key for identification
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return f"key:{api_key[:16]}"

    # Fall back to IP
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"

    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enterprise rate limiting middleware with token bucket per client."""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self._buckets: dict[str, TokenBucket] = {}
        self._cleanup_counter = 0

    def _get_bucket(self, client_key: str, path: str) -> TokenBucket:
        """Get or create a token bucket for a client+path combo."""
        config = _get_limit_config(path)
        bucket_key = f"{client_key}:{path.split('/')[3] if len(path.split('/')) > 3 else 'root'}"

        if bucket_key not in self._buckets:
            self._buckets[bucket_key] = TokenBucket(
                capacity=config["capacity"],
                refill_rate=config["refill_rate"],
            )

        return self._buckets[bucket_key]

    def _cleanup_stale_buckets(self):
        """Periodically clean up old buckets to prevent memory leaks."""
        self._cleanup_counter += 1
        if self._cleanup_counter % 1000 == 0:
            now = time.monotonic()
            stale_keys = [
                k for k, b in self._buckets.items()
                if now - b.last_refill > 300  # 5 minutes idle
            ]
            for k in stale_keys:
                del self._buckets[k]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting in demo mode or if disabled
        if not self.enabled or settings.DEMO_MODE:
            response = await call_next(request)
            return response

        # Skip health checks
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)

        client_key = _get_client_key(request)
        bucket = self._get_bucket(client_key, request.url.path)

        if not bucket.consume():
            retry_after = int(bucket.retry_after) + 1
            log.warning(
                "rate_limited",
                client=client_key,
                path=request.url.path,
                retry_after=retry_after,
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

        self._cleanup_stale_buckets()

        response = await call_next(request)

        # Add rate limit headers
        config = _get_limit_config(request.url.path)
        response.headers["X-RateLimit-Limit"] = str(config["capacity"])
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))

        return response
