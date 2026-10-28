from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from app.services.dedupe import get_redis

PER_SECOND = 4


class ThrottleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        r = await get_redis()
        key = f"thr:{user.id}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 1)

        if count > PER_SECOND and isinstance(event, CallbackQuery):
            await event.answer("Slow down a moment.")
            return None

        return await handler(event, data)
