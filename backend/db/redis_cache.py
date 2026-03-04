"""
AutoForge Redis Cache — Fast read cache for hot memory paths.

Provides:
- Skills cache (avoid DB reads on every recall)
- Experience count cache
- Failure pattern cache
- Graceful fallback: if Redis is unavailable, silently skip caching
"""

import json
from typing import Any, Optional

from config import settings
from logging_config import get_logger

log = get_logger("db.redis_cache")

_redis = None
_available = False


async def init_redis():
    """Connect to Redis, or silently disable if unavailable."""
    global _redis, _available
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        await _redis.ping()
        _available = True
        log.info("redis_connected", url=settings.REDIS_URL)
    except Exception as exc:
        _available = False
        _redis = None
        log.warning("redis_unavailable", error=str(exc), detail="Caching disabled — in-memory only")


async def close_redis():
    """Gracefully close Redis connection."""
    global _redis, _available
    if _redis:
        await _redis.aclose()
        _redis = None
        _available = False


def is_available() -> bool:
    return _available


async def cache_set(key: str, value: Any, ttl: int = 300):
    """Set a cache key with TTL (seconds). Silently fails if Redis is down."""
    if not _available:
        return
    try:
        await _redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


async def cache_get(key: str) -> Optional[Any]:
    """Get a cache key. Returns None on miss or failure."""
    if not _available:
        return None
    try:
        raw = await _redis.get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


async def cache_delete(key: str):
    """Delete a cache key."""
    if not _available:
        return
    try:
        await _redis.delete(key)
    except Exception:
        pass


async def cache_incr(key: str, ttl: int = 3600) -> int:
    """Atomic increment with TTL. Returns new value, or 0 on failure."""
    if not _available:
        return 0
    try:
        val = await _redis.incr(key)
        if val == 1:
            await _redis.expire(key, ttl)
        return val
    except Exception:
        return 0
