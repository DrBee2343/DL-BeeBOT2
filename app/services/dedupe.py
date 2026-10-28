import redis.asyncio as aioredis
from app.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def first_time(update_id: int, ttl: int = 3600) -> bool:
    """Telegram retries webhooks. Return False if we already handled this update."""
    r = await get_redis()
    return bool(await r.set(f"upd:{update_id}", "1", ex=ttl, nx=True))
