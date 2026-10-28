import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def first_time(update_id: int, ttl: int = 3600) -> bool:
    r = await get_redis()
    return bool(await r.set(f"upd:{update_id}", "1", ex=ttl, nx=True))


async def acquire_user_lock(user_id: int, ttl: int = 90) -> bool:
    r = await get_redis()
    return bool(await r.set(f"lock:{user_id}", "1", ex=ttl, nx=True))


async def release_user_lock(user_id: int) -> None:
    r = await get_redis()
    await r.delete(f"lock:{user_id}")
