from app.services.kv import backend


async def first_time(update_id: int, ttl: int = 3600) -> bool:
    return await backend().set_nx(f"upd:{update_id}", ttl)


async def acquire_user_lock(user_id: int, ttl: int = 120) -> bool:
    return await backend().set_nx(f"lock:{user_id}", ttl)


async def release_user_lock(user_id: int) -> None:
    await backend().delete(f"lock:{user_id}")
