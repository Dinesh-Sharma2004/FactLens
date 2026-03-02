import redis.asyncio as redis
import json

try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False


async def get_cache(key):
    if not REDIS_AVAILABLE:
        return None

    try:
        value = await r.get(key)
        return json.loads(value) if value else None
    except:
        return None


async def set_cache(key, value, ttl=3600):
    if not REDIS_AVAILABLE:
        return

    try:
        await r.setex(key, ttl, json.dumps(value))
    except:
        pass
