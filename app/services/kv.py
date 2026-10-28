import time

from app.config import settings

_mem: dict[str, tuple[str, float]] = {}


def kv_enabled() -> bool:
    return settings.using_redis


class _Memory:
    async def set_nx(self, key: str, ttl: int) -> bool:
        now = time.monotonic()
        entry = _mem.get(key)
        if entry and entry[1] > now:
            return False
        _mem[key] = ("1", now + ttl)
        return True

    async def incr(self, key: str, ttl: int) -> int:
        now = time.monotonic()
        entry = _mem.get(key)
        if not entry or entry[1] <= now:
            _mem[key] = ("1", now + ttl)
            return 1
        value = int(entry[0]) + 1
        _mem[key] = (str(value), entry[1])
        return value

    async def delete(self, key: str) -> None:
        _mem.pop(key, None)


class _Redis:
    def __init__(self, client) -> None:
        self._c = client

    async def set_nx(self, key: str, ttl: int) -> bool:
        return bool(await self._c.set(key, "1", ex=ttl, nx=True))

    async def incr(self, key: str, ttl: int) -> int:
        count = await self._c.incr(key)
        if count == 1:
            await self._c.expire(key, ttl)
        return int(count)

    async def delete(self, key: str) -> None:
        await self._c.delete(key)


_backend = None


def backend():
    global _backend
    if _backend is None:
        if kv_enabled():
            import redis.asyncio as aioredis

            _backend = _Redis(aioredis.from_url(settings.redis_url, decode_responses=True))
        else:
            _backend = _Memory()
    return _backend


async def close() -> None:
    global _backend
    if isinstance(_backend, _Redis):
        await _backend._c.aclose()
    _backend = None
