import asyncio
import json
import os
import time

import redis.asyncio as redis


# Fail fast when Redis is down so API requests stay responsive.
_REDIS_TIMEOUT_SEC = float(os.getenv("REDIS_TIMEOUT_SEC", "0.15"))
_REDIS_RETRY_AFTER_SEC = float(os.getenv("REDIS_RETRY_AFTER_SEC", "30"))


_redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=int(os.getenv("REDIS_DB", "0")),
    socket_connect_timeout=_REDIS_TIMEOUT_SEC,
    socket_timeout=_REDIS_TIMEOUT_SEC,
    retry_on_timeout=False,
)

_redis_disabled_until = 0.0
_local_cache: dict[str, tuple[float, str]] = {}


def _redis_ready() -> bool:
    return time.time() >= _redis_disabled_until


def _disable_redis_temporarily():
    global _redis_disabled_until
    _redis_disabled_until = time.time() + _REDIS_RETRY_AFTER_SEC


def _local_get(key: str):
    entry = _local_cache.get(key)
    if not entry:
        return None
    expires_at, payload = entry
    if expires_at and expires_at < time.time():
        _local_cache.pop(key, None)
        return None
    try:
        return json.loads(payload)
    except Exception:
        _local_cache.pop(key, None)
        return None


def _local_set(key: str, value, ttl: int = 3600):
    expires_at = time.time() + max(int(ttl), 1)
    _local_cache[key] = (expires_at, json.dumps(value))


async def get_cache(key):
    if _redis_ready():
        try:
            value = await asyncio.wait_for(_redis_client.get(key), timeout=_REDIS_TIMEOUT_SEC + 0.05)
            if value:
                return json.loads(value)
        except Exception:
            _disable_redis_temporarily()

    return _local_get(key)


async def set_cache(key, value, ttl=3600):
    # Always keep local cache hot to avoid response delays if Redis is down.
    _local_set(key, value, ttl)

    if not _redis_ready():
        return

    try:
        await asyncio.wait_for(_redis_client.setex(key, ttl, json.dumps(value)), timeout=_REDIS_TIMEOUT_SEC + 0.05)
    except Exception:
        _disable_redis_temporarily()
