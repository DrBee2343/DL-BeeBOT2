from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from app.services.kv import backend

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

        count = await backend().incr(f"thr:{user.id}", 1)
        if count > PER_SECOND and isinstance(event, CallbackQuery):
            await event.answer("Slow down a moment.")
            return None

        return await handler(event, data)
