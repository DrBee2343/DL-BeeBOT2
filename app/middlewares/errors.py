import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import settings
from app.texts import ERR_GENERIC

log = logging.getLogger(__name__)


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            log.exception("handler_failed: %s", exc)
            await self._notify(event, exc)
            return None

    async def _notify(self, event: TelegramObject, exc: Exception) -> None:
        ref = f"`{type(exc).__name__}`"
        try:
            if isinstance(event, CallbackQuery):
                await event.answer(ERR_GENERIC, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(ERR_GENERIC)
        except Exception:
            pass

        bot = event.bot
        for admin in settings.admins:
            try:
                await bot.send_message(admin, f"Error {ref}\n\n`{exc}`")
            except Exception:
                pass
